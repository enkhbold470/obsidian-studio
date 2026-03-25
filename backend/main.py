"""Flask API + optional SPA static; Postgres auth + generation history."""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
import traceback
import uuid
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from backend.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from werkzeug.exceptions import RequestEntityTooLarge
from backend.brainrot import (
    ASS_FONTS,
    Config,
    generate_dialogue,
    get_default_gpt_model,
    get_default_peter_voice,
    get_default_stewie_voice,
    get_default_tts_model,
    get_dynamic_options_cached,
    get_llm_client,
    get_tts_client,
    is_valid_dialogue,
    run_pipeline,
)
from backend.db.session import SessionLocal
from backend.db import (
    create_user,
    delete_user_background,
    get_generation_by_job_uid,
    get_user_background,
    get_user_by_id,
    init_db,
    insert_generation,
    insert_user_background_record,
    list_generations_for_user,
    list_user_backgrounds,
    set_user_gallery_public,
    verify_user,
)
from backend import s3_storage
from backend import thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)
_log = logging.getLogger("brainrot.api")


def _gen_print(msg: str) -> None:
    line = f"[generate] {msg}"
    print(line, flush=True)
    _log.info(msg)


DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
BG_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}

app = Flask(__name__)
_max_upload_mb = int(os.environ.get("MAX_UPLOAD_MB", "256"))
app.config["MAX_CONTENT_LENGTH"] = _max_upload_mb * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-only-change-me"
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if o.strip()]
# Applies to all routes; API is the cross-origin surface. Use explicit origins (required with credentials).
CORS(
    app,
    origins=_cors_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)


def _client_ip() -> str:
    """Client IP behind Traefik / Dokploy (first X-Forwarded-For hop)."""
    xff = (request.headers.get("X-Forwarded-For") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


_rl_enabled = os.environ.get("RATELIMIT_ENABLED", "1").lower() not in ("0", "false", "no")
app.config["RATELIMIT_ENABLED"] = _rl_enabled
_limiter_storage = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
limiter = Limiter(
    key_func=_client_ip,
    app=app,
    default_limits=["120 per minute", "8000 per day"],
    storage_uri=_limiter_storage,
    headers_enabled=True,
    enabled=_rl_enabled,
)

# Cheap 404 for common scanner paths (never used by this API).
_SCAN_PATH_MARKERS = (
    ".env",
    ".git",
    "wp-admin",
    "wp-login",
    "wp-content",
    "wp-includes",
    "xmlrpc.php",
    "phpmyadmin",
    "pgadmin",
    "vendor/php",
    "cgi-bin",
    "shell.php",
    "administrator",
    "boaform",
    "solr/",
    "phpinfo",
    "setup.php",
    "config.php",
    "aws/credentials",
)


@app.before_request
def block_obvious_scans():
    p = request.path.lower()
    if p.startswith("/api/"):
        return None
    for m in _SCAN_PATH_MARKERS:
        if m in p:
            return ("", 404)
    return None


@app.errorhandler(RateLimitExceeded)
def _rate_limit_exceeded(_e: RateLimitExceeded):
    return jsonify({"error": "Too many requests. Please try again in a minute."}), 429


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(_e: RequestEntityTooLarge):
    return jsonify(
        {
            "error": (
                f"Upload too large (max {_max_upload_mb} MB). "
                "Set MAX_UPLOAD_MB in the environment or use a smaller / more compressed video."
            )
        }
    ), 413


@app.route("/")
@limiter.exempt
def root_welcome():
    return jsonify(
        {
            "message": "Welcome to ReelMaker API",
            "service": "brainrot",
            "api": "/api",
            "health": "/health",
        }
    )


@app.route("/health")
@limiter.exempt
def health():
    checks: dict[str, object] = {"database": False}
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        _log.warning("health check: database failed: %s", e)
        checks["error"] = str(e)[:200]
        return jsonify(
            {
                "status": "unhealthy",
                "message": "Database unavailable",
                "checks": checks,
            }
        ), 503

    checks["s3_configured"] = s3_storage.is_enabled()
    return jsonify(
        {
            "status": "healthy",
            "checks": checks,
        }
    )


def skip_auth() -> bool:
    return os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if skip_auth() or session.get("user_id"):
            return fn(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401

    return wrapper


def _require_s3():
    if not s3_storage.is_enabled():
        return (
            jsonify(
                {
                    "error": "Object storage is not configured. Set S3_ENDPOINT_URL (e.g. run with Docker Compose + MinIO).",
                }
            ),
            503,
        )
    return None


@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("12 per minute")
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = create_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email/password or email already registered."}), 400
    session["user_id"] = user.id
    session.permanent = True
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "galleryPublic": user.gallery_public}})


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("12 per minute")
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = verify_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    session["user_id"] = user.id
    session.permanent = True
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "galleryPublic": user.gallery_public}})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def auth_me():
    if skip_auth():
        return jsonify({"user": None, "skipAuth": True})
    uid = session.get("user_id")
    if not uid:
        return jsonify({"user": None}), 200
    user = get_user_by_id(int(uid))
    if not user:
        session.clear()
        return jsonify({"user": None}), 200
    return jsonify({"user": {"id": user.id, "email": user.email, "galleryPublic": user.gallery_public}})


@app.route("/api/me", methods=["PATCH"])
@require_login
def api_me_patch():
    if skip_auth():
        return jsonify({"error": "Not available with SKIP_AUTH"}), 400
    data = request.get_json(force=True, silent=True) or {}
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    if "galleryPublic" in data:
        set_user_gallery_public(int(uid), bool(data["galleryPublic"]))
    user = get_user_by_id(int(uid))
    if not user:
        return jsonify({"error": "not found"}), 404
    return jsonify({"user": {"id": user.id, "email": user.email, "galleryPublic": user.gallery_public}})


@app.route("/api/script", methods=["POST"])
@require_login
def api_script():
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500
    data = request.get_json(force=True, silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if len(topic) < 10:
        return jsonify({"error": "Topic must be at least 10 characters."}), 400
    lines_n = int(data.get("dialogue_lines", 8))
    gpt_model = data.get("gpt_model", get_default_gpt_model())
    try:
        lines = generate_dialogue(get_llm_client(), topic, lines_n, gpt_model)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not is_valid_dialogue(lines):
        return jsonify({"error": "Model returned invalid dialogue shape."}), 500
    return jsonify({"dialogue": lines})


@app.route("/api/backgrounds", methods=["GET"])
@require_login
def api_backgrounds_list():
    if skip_auth():
        return jsonify({"items": []})
    err = _require_s3()
    if err:
        return err
    uid = session.get("user_id")
    if not uid:
        return jsonify({"items": []})
    rows = list_user_backgrounds(int(uid))
    return jsonify(
        {
            "items": [
                {
                    "id": r.id,
                    "filename": r.original_filename,
                    "createdAt": r.created_at.isoformat(),
                    "streamUrl": f"/api/backgrounds/{r.id}/stream",
                    "thumbUrl": f"/api/backgrounds/{r.id}/thumb",
                }
                for r in rows
            ],
        }
    )


@app.route("/api/backgrounds", methods=["POST"])
@require_login
def api_backgrounds_upload():
    err = _require_s3()
    if err:
        return err
    if skip_auth():
        return jsonify({"error": "Upload requires a logged-in user."}), 400
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    f = request.files.get("file")
    if not f or not getattr(f, "filename", None):
        return jsonify({"error": "Missing file."}), 400
    ext = Path(f.filename).suffix.lower()
    if ext not in BG_VIDEO_EXTS:
        return jsonify({"error": "Unsupported video type."}), 400
    bg_uuid = str(uuid.uuid4())
    key = f"users/{int(uid)}/backgrounds/{bg_uuid}{ext}"
    tmp = PROJECT_ROOT / "temp_build" / f"up_{bg_uuid}{ext}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(tmp))
    thumb_local = tmp.with_suffix(".thumb.jpg")
    try:
        s3_storage.put_file(key, tmp)
        if thumbnail.extract_video_thumbnail_jpg(tmp, thumb_local):
            s3_storage.put_file(thumbnail.thumb_key_for_video_key(key), thumb_local)
    finally:
        tmp.unlink(missing_ok=True)
        thumb_local.unlink(missing_ok=True)
    insert_user_background_record(bg_uuid, int(uid), key, Path(f.filename).name)
    return jsonify(
        {
            "item": {
                "id": bg_uuid,
                "filename": Path(f.filename).name,
                "streamUrl": f"/api/backgrounds/{bg_uuid}/stream",
                "thumbUrl": f"/api/backgrounds/{bg_uuid}/thumb",
            }
        }
    )


@app.route("/api/backgrounds/<bg_id>/stream")
@require_login
def api_background_stream(bg_id):
    err = _require_s3()
    if err:
        return err
    if skip_auth():
        return jsonify({"error": "Unauthorized"}), 401
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    row = get_user_background(int(uid), bg_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    ext = Path(row.original_filename).suffix.lower().lstrip(".") or "mp4"
    if ext not in ("mp4", "mov", "webm", "mkv"):
        ext = "mp4"
    mt = f"video/{ext}" if ext != "mov" else "video/quicktime"
    return s3_storage.response_for_key(row.storage_key, row.original_filename, mimetype=mt)


@app.route("/api/backgrounds/<bg_id>/thumb")
@require_login
def api_background_thumb(bg_id):
    err = _require_s3()
    if err:
        return err
    if skip_auth():
        return jsonify({"error": "Unauthorized"}), 401
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    row = get_user_background(int(uid), bg_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    tkey = thumbnail.thumb_key_for_video_key(row.storage_key)
    if not s3_storage.exists(tkey):
        return jsonify({"error": "not found"}), 404
    return s3_storage.response_for_key(tkey, "thumb.jpg", mimetype="image/jpeg")


@app.route("/api/backgrounds/<bg_id>", methods=["DELETE"])
@require_login
def api_backgrounds_delete(bg_id):
    err = _require_s3()
    if err:
        return err
    if skip_auth():
        return jsonify({"error": "Not available with SKIP_AUTH"}), 400
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    row = get_user_background(int(uid), bg_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    s3_storage.delete_object(row.storage_key)
    tk = thumbnail.thumb_key_for_video_key(row.storage_key)
    if s3_storage.exists(tk):
        s3_storage.delete_object(tk)
    delete_user_background(int(uid), bg_id)
    return jsonify({"ok": True})


@app.route("/api/users/<int:user_id>/renders")
def api_user_renders(user_id):
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "not found"}), 404
    viewer = session.get("user_id")
    if viewer is not None and int(viewer) == user_id:
        rows = list_generations_for_user(user_id)
    elif target.gallery_public:
        rows = list_generations_for_user(user_id)
    else:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(
        {
            "items": [
                {
                    "id": r.id,
                    "jobUid": r.job_uid,
                    "topic": r.topic,
                    "outputFormat": r.output_format,
                    "bgSource": r.bg_source,
                    "createdAt": r.created_at.isoformat(),
                    "elapsedSeconds": r.elapsed_seconds,
                    "renderMeta": r.render_meta,
                    "watchUrl": f"/u/{user_id}/renders/{r.job_uid}",
                    "thumbUrl": f"/api/output/{r.job_uid}/thumb",
                }
                for r in rows
            ],
            "galleryPublic": target.gallery_public,
        }
    )


@app.route("/api/options")
def api_options():
    opts = get_dynamic_options_cached()
    return jsonify({
        "tts_voices": opts.get("tts_voices") or [],
        "tts_models": opts.get("tts_models") or [],
        "gpt_models": opts.get("gpt_models") or [],
        "default_gpt_model": get_default_gpt_model(),
        "fonts": ASS_FONTS,
    })


@app.route("/api/history")
@require_login
def api_history():
    if skip_auth():
        return jsonify({"items": []})
    sid = session.get("user_id")
    if not sid:
        return jsonify({"items": []})
    rows = list_generations_for_user(int(sid))
    return jsonify({
        "items": [
            {
                "id": r.id,
                "jobUid": r.job_uid,
                "topic": r.topic,
                "outputFormat": r.output_format,
                "bgSource": r.bg_source,
                "createdAt": r.created_at.isoformat(),
                "elapsedSeconds": r.elapsed_seconds,
                "renderMeta": r.render_meta,
                "watchUrl": f"/u/{int(sid)}/renders/{r.job_uid}",
                "thumbUrl": f"/api/output/{r.job_uid}/thumb",
            }
            for r in rows
        ],
    })


@app.route("/api/generate", methods=["POST"])
@require_login
def api_generate():
    t0 = time.perf_counter()
    _gen_print(
        f"start content_length={request.content_length!r} "
        f"content_type={request.content_type!r} remote={request.remote_addr!r}"
    )
    err = _require_s3()
    if err:
        _gen_print("abort: S3 not configured")
        return err
    if not os.getenv("OPENAI_API_KEY"):
        _gen_print("abort: OPENAI_API_KEY missing")
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500
    _gen_print(f"parsing multipart form (elapsed {time.perf_counter() - t0:.2f}s) …")
    data = request.form
    bg_saved_id = (data.get("bg_saved_id") or "").strip()
    bg = request.files.get("bg")
    if bg_saved_id and bg and getattr(bg, "filename", None):
        return jsonify({"error": "Choose either a saved background or a new upload, not both."}), 400
    if not bg_saved_id and not (bg and getattr(bg, "filename", None)):
        return jsonify({"error": "Upload a video or select a saved background."}), 400

    _gen_print(f"multipart parsed (elapsed {time.perf_counter() - t0:.2f}s) bg_saved_id={bg_saved_id!r}")

    uid = str(uuid.uuid4())[:8]
    work_dir = PROJECT_ROOT / "temp_build" / uid
    work_dir.mkdir(parents=True, exist_ok=True)

    sid = session.get("user_id")
    uid_user = int(sid) if sid is not None and not skip_auth() else None
    if skip_auth():
        uid_user = None

    bg_path: Path | None = None
    bg_label = "upload"
    uploaded_new_file = False
    upload_original_name = ""

    if bg_saved_id:
        if uid_user is None:
            return jsonify({"error": "Saved backgrounds require login."}), 400
        row = get_user_background(uid_user, bg_saved_id)
        if not row:
            return jsonify({"error": "Invalid saved background."}), 400
        ext = Path(row.original_filename).suffix.lower() or ".mp4"
        if ext not in BG_VIDEO_EXTS:
            ext = ".mp4"
        bg_path = work_dir / f"bg{ext}"
        _gen_print(f"downloading saved bg from S3 key={row.storage_key!r} …")
        s3_storage.download_to_path(row.storage_key, bg_path)
        _gen_print(f"saved bg on disk bytes={bg_path.stat().st_size} (elapsed {time.perf_counter() - t0:.2f}s)")
        bg_label = f"saved:{bg_saved_id}"
    else:
        upload_original_name = Path(bg.filename).name
        bg_path = work_dir / f"bg{Path(bg.filename).suffix}"
        _gen_print(f"writing upload to disk {bg_path.name!r} …")
        bg.save(str(bg_path))
        uploaded_new_file = True
        bg_label = "upload"
        try:
            sz = bg_path.stat().st_size
        except OSError:
            sz = -1
        _gen_print(f"upload saved bytes={sz} (elapsed {time.perf_counter() - t0:.2f}s)")

    out_ext = data.get("output_format", "mp4")
    out_path = work_dir / f"out.{out_ext}"
    dialogue_raw = data.get("dialogue", "[]")
    try:
        dialogue = json.loads(dialogue_raw) if dialogue_raw else []
    except Exception:
        return jsonify({"error": "Dialogue must be valid JSON array."}), 400
    if not is_valid_dialogue(dialogue):
        return jsonify({"error": "Dialogue: need at least one line; each {speaker: Peter|Stewie, text: ...}."}), 400
    cfg = Config(
        topic=data.get("topic", ""),
        dialogue=dialogue,
        dialogue_lines=int(data.get("dialogue_lines", 8)),
        tts_speed=float(data.get("tts_speed", 1.2)),
        shake_speed=float(data.get("shake_speed", 10)),
        font_name=data.get("font_name", "Arial"),
        font_size=int(data.get("font_size", 100)),
        text_color=data.get("text_color", "#FDE047"),
        outline_color=data.get("outline_color", "#000000"),
        peter_voice=data.get("peter_voice", get_default_peter_voice()),
        stewie_voice=data.get("stewie_voice", get_default_stewie_voice()),
        tts_model=data.get("tts_model", get_default_tts_model()),
        gpt_model=data.get("gpt_model", get_default_gpt_model()),
        output_format=out_ext,
    )
    out_key = f"outputs/{uid}_out.{out_ext}"
    try:
        _gen_print(
            f"run_pipeline begin job_uid={uid} user_id={uid_user!r} out_key={out_key!r} "
            f"(elapsed {time.perf_counter() - t0:.2f}s)"
        )
        run_pipeline(cfg, bg_path, out_path, get_llm_client(), get_tts_client(), work_dir, PROJECT_ROOT)
        _gen_print(f"run_pipeline done (elapsed {time.perf_counter() - t0:.2f}s), uploading output to S3 …")
        s3_storage.put_file(out_key, out_path)
        _gen_print(f"output uploaded to S3 (elapsed {time.perf_counter() - t0:.2f}s)")
        out_thumb = work_dir / f"{uid}_out_thumb.jpg"
        if thumbnail.extract_video_thumbnail_jpg(out_path, out_thumb):
            s3_storage.put_file(thumbnail.thumb_key_for_video_key(out_key), out_thumb)

        if uploaded_new_file and uid_user is not None and bg_path and bg_path.is_file():
            bg_uuid = str(uuid.uuid4())
            uext = Path(upload_original_name).suffix.lower()
            if uext not in BG_VIDEO_EXTS:
                uext = ".mp4"
            ukey = f"users/{uid_user}/backgrounds/{bg_uuid}{uext}"
            _gen_print(f"uploading background copy to library {ukey!r} …")
            s3_storage.put_file(ukey, bg_path)
            lib_thumb = work_dir / f"lib_thumb_{bg_uuid}.jpg"
            if thumbnail.extract_video_thumbnail_jpg(bg_path, lib_thumb):
                s3_storage.put_file(thumbnail.thumb_key_for_video_key(ukey), lib_thumb)
            insert_user_background_record(
                bg_uuid,
                uid_user,
                ukey,
                upload_original_name,
            )
            bg_label = f"upload+library:{bg_uuid}"

        shutil.rmtree(work_dir, ignore_errors=True)
        total_s = time.perf_counter() - t0
        render_meta = {
            "topic": (data.get("topic", "") or "").strip(),
            "dialogue_lines": int(data.get("dialogue_lines", 8)),
            "tts_speed": float(data.get("tts_speed", 1.2)),
            "shake_speed": float(data.get("shake_speed", 10)),
            "font_name": data.get("font_name", "Arial"),
            "font_size": int(data.get("font_size", 100)),
            "text_color": data.get("text_color", "#FDE047"),
            "outline_color": data.get("outline_color", "#000000"),
            "peter_voice": data.get("peter_voice", get_default_peter_voice()),
            "stewie_voice": data.get("stewie_voice", get_default_stewie_voice()),
            "tts_model": data.get("tts_model", get_default_tts_model()),
            "gpt_model": data.get("gpt_model", get_default_gpt_model()),
            "output_format": out_ext,
            "bg_source": bg_label,
            "dialogue": dialogue,
            "elapsed_seconds": total_s,
        }
        insert_generation(
            user_id=uid_user,
            job_uid=uid,
            output_key=out_key,
            output_format=out_ext,
            topic=(data.get("topic", "") or "").strip(),
            dialogue=dialogue,
            bg_source=bg_label,
            elapsed_seconds=total_s,
            render_meta=render_meta,
        )
        _gen_print(f"SUCCESS job_uid={uid} total_s={total_s:.2f}")
        return jsonify({"ok": True, "file": f"/api/output/{uid}", "elapsedSeconds": total_s})
    except Exception as e:
        _log.exception("generate failed: %s", e)
        print(f"[generate] EXCEPTION after {time.perf_counter() - t0:.2f}s: {e!r}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({"error": str(e)}), 500


def _output_access_allowed(gen) -> bool:
    if not gen or not gen.user_id:
        return False
    owner_id = gen.user_id
    if skip_auth():
        return True
    sid = session.get("user_id")
    if sid is not None and int(sid) == owner_id:
        return True
    owner = get_user_by_id(owner_id)
    return owner is not None and owner.gallery_public


@app.route("/api/output/<uid>/thumb")
def api_output_thumb(uid):
    """JPEG thumbnail (S3 key: same as video with `.thumb.jpg` suffix)."""
    err = _require_s3()
    if err:
        return err
    gen = get_generation_by_job_uid(uid)
    if not _output_access_allowed(gen):
        return jsonify({"error": "not found"}), 404
    tkey = thumbnail.thumb_key_for_video_key(gen.output_key)
    if not s3_storage.exists(tkey):
        return jsonify({"error": "not found"}), 404
    return s3_storage.response_for_key(tkey, "thumb.jpg", mimetype="image/jpeg")


@app.route("/api/output/<uid>")
def api_output(uid):
    err = _require_s3()
    if err:
        return err
    gen = get_generation_by_job_uid(uid)
    if not _output_access_allowed(gen):
        return jsonify({"error": "not found"}), 404
    ext = (gen.output_format or "mp4").lower().lstrip(".")
    if ext not in ("mp4", "mkv"):
        ext = "mp4"
    mimetype = f"video/{ext}"
    name = f"brainrot.{ext}"
    return s3_storage.response_for_key(gen.output_key, name, mimetype=mimetype)


def _serve_spa(path: str):
    if path.startswith("api"):
        return jsonify({"error": "not found"}), 404
    if path:
        candidate = DIST_DIR / path
        try:
            candidate.resolve().relative_to(DIST_DIR.resolve())
        except ValueError:
            return send_from_directory(DIST_DIR, "index.html")
        if candidate.is_file():
            return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


@app.route("/<path:path>")
def spa(path):
    if not DIST_DIR.is_dir() or not (DIST_DIR / "index.html").is_file():
        return (
            jsonify(
                {
                    "error": "No SPA in this image. Deploy the frontend separately; API is at /api/*",
                    "hint": "Set CORS_ORIGINS to your SPA origin; use VITE_API_BASE_URL on the client.",
                }
            ),
            503,
        )
    return _serve_spa(path)


init_db()
s3_storage.ensure_bucket()


def _run_server() -> None:
    """Production entry: uvicorn (WSGI) on 0.0.0.0 — works behind Traefik/Dokploy."""
    import uvicorn

    port = int(os.environ.get("PORT", "5001"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG") == "1"
    ep = (os.environ.get("S3_ENDPOINT_URL") or "").strip()
    print(
        f"[startup] host={host!r} port={port} MAX_UPLOAD_MB={_max_upload_mb} "
        f"S3_ENDPOINT_URL={'set' if ep else 'unset'} S3_BUCKET={os.environ.get('S3_BUCKET', 'brainrot')!r} "
        f"CORS_ORIGINS={len(_cors_origins)} origin(s)",
        flush=True,
    )
    _log.info(
        "listening host=%s port=%s max_upload_mb=%s s3=%s",
        host,
        port,
        _max_upload_mb,
        ep or "(disabled)",
    )
    uvicorn.run(
        app,
        host=host,
        port=port,
        interface="wsgi",
        log_level="debug" if debug else "info",
        access_log=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    _run_server()
