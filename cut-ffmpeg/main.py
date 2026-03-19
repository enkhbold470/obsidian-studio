import os
import subprocess
import sys
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is installed and available in the system PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def setup_directories(base_path):
    """Create the output directories for 30s and 60s cuts."""
    dir_30 = base_path / '30_sec_cuts'
    dir_60 = base_path / '60_sec_cuts'
    dir_30.mkdir(exist_ok=True)
    dir_60.mkdir(exist_ok=True)
    return dir_30, dir_60

def process_video(input_path):
    """Process the input video to create 30s and 60s portrait segments."""
    if not check_ffmpeg():
        print("Error: FFmpeg is not installed or not found in system PATH.")
        print("Please install FFmpeg to use this script (e.g., 'sudo apt install ffmpeg').")
        return

    input_file = Path(input_path).resolve()
    if not input_file.exists():
        print(f"Error: Could not find file {input_path}")
        return

    print(f"Processing: {input_file.name}")
    dir_30, dir_60 = setup_directories(input_file.parent)

    # Crop filter for 9:16 aspect ratio (portrait)
    # iw and ih are input width and height.
    # This crops the width to match a 9:16 ratio of the original height, kept mathematically centered.
    crop_filter = "crop=ih*9/16:ih"

    try:
        # Command for 30-second segments
        print(f"\n-> Creating 30-second portrait segments in {dir_30.name}...")
        output_30_pattern = str(dir_30 / f"{input_file.stem}_30s_%03d.mp4")
        cmd_30 = [
            "ffmpeg", "-y", "-i", str(input_file),
            "-vf", crop_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "segment", "-segment_time", "30",
            "-reset_timestamps", "1",
            output_30_pattern
        ]
        # We use quiet flags for a cleaner terminal output unless it fails
        subprocess.run(cmd_30, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("   Done with 30-second segments!")

        # Command for 60-second segments
        print(f"\n-> Creating 60-second portrait segments in {dir_60.name}...")
        output_60_pattern = str(dir_60 / f"{input_file.stem}_60s_%03d.mp4")
        cmd_60 = [
            "ffmpeg", "-y", "-i", str(input_file),
            "-vf", crop_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "segment", "-segment_time", "60",
            "-reset_timestamps", "1",
            output_60_pattern
        ]
        subprocess.run(cmd_60, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("   Done with 60-second segments!")

        print("\n✅ Video preparation complete!")
        print(f"Files saved in:\n- {dir_30}\n- {dir_60}")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error occurred during video processing. FFmpeg exited with an error.")
        print("Try running the command manually without quiet flags to see the issue.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_video>")
        print("Example: python main.py my_video.mp4")
        sys.exit(1)
        
    process_video(sys.argv[1])
