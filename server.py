"""Flask server for brainrot web UI."""
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from openai import OpenAI

from brainrot import Config, run_pipeline, TTS_VOICES, TTS_MODELS, GPT_MODELS, ASS_FONTS

load_dotenv(Path(__file__).parent / ".env")
app = Flask(__name__, static_folder="web", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
ROOT = Path(__file__).parent
DEFAULT_BG = ROOT / "minecraft_parkour1.mp4"
UPLOADS = ROOT / "temp_build" / "uploads"
OUTPUTS = ROOT / "temp_build" / "outputs"


@app.route("/")
def index():
    return send_file(ROOT / "web" / "index.html")


@app.route("/api/options")
def options():
    return jsonify({
        "tts_voices": TTS_VOICES,
        "tts_models": TTS_MODELS,
        "gpt_models": GPT_MODELS,
        "fonts": ASS_FONTS,
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({"error": "OPENAI_API_KEY not set"}), 500
    data = request.form
    use_default_bg = data.get("lucky") == "1"
    bg = request.files.get("bg")
    uid = str(uuid.uuid4())[:8]
    UPLOADS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    if use_default_bg and DEFAULT_BG.exists():
        bg_path = DEFAULT_BG
    elif bg:
        bg_path = UPLOADS / f"{uid}_bg{Path(bg.filename).suffix}"
        bg.save(bg_path)
    else:
        return jsonify({"error": "bg video required or use I'm feeling lucky"}), 400
    out_ext = data.get("output_format", "mp4")
    out_path = OUTPUTS / f"{uid}_out.{out_ext}"
    dialogue_raw = data.get("dialogue", "[]")
    try:
        dialogue = __import__("json").loads(dialogue_raw) if dialogue_raw else []
    except Exception:
        dialogue = []
    cfg = Config(
        topic=data.get("topic", ""),
        dialogue=dialogue,
        dialogue_lines=int(data.get("dialogue_lines", 8)),
        tts_speed=float(data.get("tts_speed", 1.2)),
        shake_speed=float(data.get("shake_speed", 15)),
        font_name=data.get("font_name", "Arial"),
        font_size=int(data.get("font_size", 100)),
        text_color=data.get("text_color", "#FFFFFF"),
        outline_color=data.get("outline_color", "#000000"),
        peter_voice=data.get("peter_voice", "echo"),
        stewie_voice=data.get("stewie_voice", "alloy"),
        tts_model=data.get("tts_model", "tts-1"),
        gpt_model=data.get("gpt_model", "gpt-4o"),
        output_format=out_ext,
    )
    try:
        run_pipeline(cfg, bg_path, out_path, OpenAI(), ROOT / "temp_build" / uid, ROOT)
        return jsonify({"ok": True, "file": f"/api/output/{uid}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/output/<uid>")
def output(uid):
    for ext in ["mp4", "mkv"]:
        p = OUTPUTS / f"{uid}_out.{ext}"
        if p.exists():
            return send_file(p, mimetype=f"video/{ext}", download_name=f"brainrot.{ext}")
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(port=5001)
