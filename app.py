import argparse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from brainrot import Config, run_pipeline

load_dotenv(Path(__file__).parent / ".env")


def main():
    parser = argparse.ArgumentParser(description="Generate a Brainrot Video")
    parser.add_argument("--topic", required=True, help="Topic for Peter and Stewie to debate")
    parser.add_argument("--bg", required=True, help="Path to 9:16 background video cut")
    parser.add_argument("--output", default="final_brainrot.mp4", help="Output video path")
    parser.add_argument("--lines", type=int, default=8, help="Dialogue lines")
    parser.add_argument("--speed", type=float, default=1.2, help="TTS speed")
    parser.add_argument("--shake", type=float, default=15, help="Shake speed (lower=slower)")
    args = parser.parse_args()

    bg_path = Path(args.bg)
    if not bg_path.exists():
        print(f"Error: Could not find bg video {args.bg}")
        return

    cfg = Config(topic=args.topic, dialogue_lines=args.lines, tts_speed=args.speed, shake_speed=args.shake)
    temp_dir = Path("temp_build")
    temp_dir.mkdir(exist_ok=True)
    out = run_pipeline(cfg, bg_path, Path(args.output), OpenAI(), temp_dir)
    print(f"Done: {out}")


if __name__ == "__main__":
    main()
