"""Flask API + optional SPA static; SQLite auth."""
from __future__ import annotations

import json
import os
import uuid
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
from openai import OpenAI

from backend.brainrot import (
    ASS_FONTS,
    Config,
    GPT_MODELS,
    TTS_MODELS,
    TTS_VOICES,
    generate_dialogue,
    is_valid_dialogue,
    run_pipeline,
)
from backend.db import create_user, get_user_by_id, init_db, verify_user
from backend.paths import PROJECT_ROOT, STORAGE_PUBLIC, STORAGE_UPLOADS

load_dotenv(PROJECT_ROOT / ".env")

DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
OUTPUTS = PROJECT_ROOT / "temp_build" / "outputs"
BG_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "dev-only-change-me"
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if o.strip()]
CORS(
    app,
    resources={r"/api/*": {"origins": _cors_origins}},
    supports_credentials=True,
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


def _resolve_bundled_bg(filename: str) -> Path | None:
    if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
        return None
    base = STORAGE_PUBLIC.resolve()
    p = (STORAGE_PUBLIC / filename).resolve()
    try:
        p.relative_to(base)
    except ValueError:
        return None
    if not p.is_file() or p.suffix.lower() not in BG_VIDEO_EXTS:
        return None
    return p


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = create_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email/password or email already registered."}), 400
    session["user_id"] = user.id
    session.permanent = True
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email}})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    user = verify_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401
    session["user_id"] = user.id
    session.permanent = True
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email}})


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
    return jsonify({"user": {"id": user.id, "email": user.email}})


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
    gpt_model = data.get("gpt_model", "gpt-5.4")
    try:
        lines = generate_dialogue(OpenAI(), topic, lines_n, gpt_model)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not is_valid_dialogue(lines):
        return jsonify({"error": "Model returned invalid dialogue shape."}), 500
    return jsonify({"dialogue": lines})


@app.route("/api/backgrounds")
def api_backgrounds():
    STORAGE_PUBLIC.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    try:
        for p in sorted(STORAGE_PUBLIC.iterdir()):
            if p.is_file() and p.suffix.lower() in BG_VIDEO_EXTS:
                files.append(p.name)
    except OSError:
        pass
    return jsonify({"files": files, "storage": "storage/public"})


@app.route("/api/options")
def api_options():
    return jsonify({
        "tts_voices": TTS_VOICES,
        "tts_models": TTS_MODELS,
        "gpt_models": GPT_MODELS,
        "fonts": ASS_FONTS,
    })


@app.route("/api/generate", methods=["POST"])
@require_login
def api_generate():
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500
    data = request.form
    bundled = (data.get("bg_bundled") or "").strip()
    bg = request.files.get("bg")
    uid = str(uuid.uuid4())[:8]
    STORAGE_UPLOADS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    bg_path: Path | None = None
    if bg and getattr(bg, "filename", None):
        bg_path = STORAGE_UPLOADS / f"{uid}_bg{Path(bg.filename).suffix}"
        bg.save(bg_path)
    elif bundled:
        bg_path = _resolve_bundled_bg(bundled)
        if not bg_path:
            return jsonify({"error": "Invalid or missing bundled background file."}), 400
    if bg_path is None:
        return jsonify({"error": "Choose a storage video or upload a background file."}), 400
    out_ext = data.get("output_format", "mp4")
    out_path = OUTPUTS / f"{uid}_out.{out_ext}"
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
        shake_speed=float(data.get("shake_speed", 15)),
        font_name=data.get("font_name", "Arial"),
        font_size=int(data.get("font_size", 100)),
        text_color=data.get("text_color", "#FDE047"),
        outline_color=data.get("outline_color", "#000000"),
        peter_voice=data.get("peter_voice", "echo"),
        stewie_voice=data.get("stewie_voice", "alloy"),
        tts_model=data.get("tts_model", "tts-1"),
        gpt_model=data.get("gpt_model", "gpt-5.4"),
        output_format=out_ext,
    )
    try:
        run_pipeline(cfg, bg_path, out_path, OpenAI(), PROJECT_ROOT / "temp_build" / uid, PROJECT_ROOT)
        return jsonify({"ok": True, "file": f"/api/output/{uid}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/output/<uid>")
@require_login
def api_output(uid):
    for ext in ["mp4", "mkv"]:
        p = OUTPUTS / f"{uid}_out.{ext}"
        if p.exists():
            return send_file(p, mimetype=f"video/{ext}", download_name=f"brainrot.{ext}")
    return jsonify({"error": "not found"}), 404


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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    if not DIST_DIR.is_dir() or not (DIST_DIR / "index.html").is_file():
        return (
            jsonify({
                "error": "Frontend not built. Run: cd frontend && bun install && bun run build",
                "hint": "API lives at /api/*",
            }),
            503,
        )
    return _serve_spa(path)


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
