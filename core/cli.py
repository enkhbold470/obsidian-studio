"""CLI entry — topic + background video → final render."""
import argparse
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

from core.paths import PROJECT_ROOT
from core.brainrot import Config, get_llm_client, run_pipeline

load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Brainrot Video")
    parser.add_argument("--topic", required=True, help="Topic for Peter and Inky to debate")
    parser.add_argument("--bg", required=True, help="Path to 9:16 background video cut")
    parser.add_argument("--output", default="final_brainrot.mp4", help="Output video path")
    parser.add_argument("--lines", type=int, default=8, help="Dialogue lines")
    parser.add_argument("--speed", type=float, default=1.2, help="TTS speed")
    parser.add_argument("--shake", type=float, default=15, help="Shake speed (lower=slower)")
    parser.add_argument(
        "--peter-width",
        type=int,
        default=420,
        metavar="PX",
        help="Scaled width in px for peter.png (FFmpeg scale=w:-1, default 420)",
    )
    parser.add_argument(
        "--inky-width",
        type=int,
        default=420,
        metavar="PX",
        help="Scaled width in px for inky.png (default 420)",
    )
    parser.add_argument(
        "--single-voice-id",
        default="",
        metavar="VOICE_ID",
        help="MOSS TTSD: use this voice ID for BOTH [S1] Peter and [S2] Inky (optional test)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less logging (default is verbose timings per step)",
    )
    args = parser.parse_args()

    bg_path = Path(args.bg)
    if not bg_path.exists():
        print(f"Error: Could not find bg video {args.bg}")
        sys.exit(1)

    verbose = not args.quiet
    cfg = Config(
        topic=args.topic,
        dialogue_lines=args.lines,
        tts_speed=args.speed,
        shake_speed=args.shake,
        overlay_peter_width=args.peter_width,
        overlay_inky_width=args.inky_width,
        single_voice_id=args.single_voice_id.strip(),
        verbose=verbose,
    )
    temp_dir = PROJECT_ROOT / "temp_build" / "cli"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        out = run_pipeline(cfg, bg_path, Path(args.output), get_llm_client(), temp_dir, PROJECT_ROOT)
    except BaseException as e:
        if verbose:
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"Done: {out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
