import os
import json
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())

def generate_script(topic):
    print(f"Generating script for topic: {topic}")
    prompt = f"""
    Create a very short, unhinged "brainrot" style text block debate between Peter Griffin and Stewie Griffin about {topic}.
    Format as a JSON object with a single key "dialogue" containing an array of objects.
    Each object must have "speaker" (either "Peter" or "Stewie") and "text".
    No more than 4-6 fast-paced lines total, very short dialogue.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content)
    return data["dialogue"]

def generate_audio(script_lines, temp_dir):
    print("Generating TTS audio...")
    audio_segments = []
    voices = {"Peter": "echo", "Stewie": "alloy"} 
    
    for i, line in enumerate(script_lines):
        speaker = line["speaker"]
        text = line["text"]
        voice = voices.get(speaker, "onyx")
        
        file_path = temp_dir / f"line_{i}.mp3"
        print(f" -> [{speaker}]: {text}")
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        response.write_to_file(file_path)
        
        duration = get_duration(file_path)
        audio_segments.append({
            "file": file_path,
            "speaker": speaker,
            "duration": duration,
            "text": text
        })
        
    return audio_segments

def build_combined_audio(audio_segments, output_audio_path):
    print("Combining audio segments...")
    list_file = output_audio_path.parent / "concat_list.txt"
    with open(list_file, "w") as f:
        for seg in audio_segments:
            f.write(f"file '{seg['file'].name}'\n")
            
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
        "-i", str(list_file), "-c", "copy", str(output_audio_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    current_time = 0.0
    speaker_timings = []
    for seg in audio_segments:
        start = current_time
        current_time += seg["duration"]
        speaker_timings.append({
            "speaker": seg["speaker"],
            "start": start,
            "end": current_time
        })
        
    return speaker_timings, current_time

def transcribe_audio(audio_path):
    print("Transcribing for word-level timestamps...")
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            file=f,
            model="whisper-1",
            response_format="verbose_json",
            timestamp_granularities=["word"]
        )
    return response.words

def generate_ass(words, ass_path):
    print("Generating ASS subtitles...")
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brainrot,Arial,100,&H0000FFFF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,8,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for w in words:
            start = w.start if hasattr(w, 'start') else w['start']
            end = w.end if hasattr(w, 'end') else w['end']
            text = (w.word if hasattr(w, 'word') else w['word']).strip()
            
            start_fmt = format_time(start)
            end_fmt = format_time(end)
            f.write(f"Dialogue: 0,{start_fmt},{end_fmt},Brainrot,,0,0,0,,{{\\an5}}{text.strip()}\n")

def build_video(bg_video, final_audio, speaker_timings, ass_file, total_duration, output_path):
    print("Building final Brainrot video...")
    
    # Construct slide and shake expressions
    p_x_exprs, p_y_exprs, p_enables = [], [], []
    s_x_exprs, s_y_exprs, s_enables = [], [], []

    for seg in speaker_timings:
        s = seg['start']
        e = seg['end']
        if seg['speaker'] == "Peter":
            p_enables.append(f"between(t,{s},{e})")
            # Starts at right edge + 400 (offscreen), slides to exactly W-w+50 in 0.2s
            p_x_exprs.append(f"(between(t,{s},{e})*((W-w+50) + max(0,0.2-(t-{s}))*2000))")
            p_y_exprs.append(f"(between(t,{s},{e})*((H/2-h/2) + sin((t-{s})*40)*15))")
        elif seg['speaker'] == "Stewie":
            s_enables.append(f"between(t,{s},{e})")
            # Starts at left edge - 400 (offscreen), slides to exactly 0 in 0.2s
            s_x_exprs.append(f"(between(t,{s},{e})*(0 - max(0,0.2-(t-{s}))*2000))")
            s_y_exprs.append(f"(between(t,{s},{e})*((H/2-h/2) + sin((t-{s})*40)*15))")

    peter_enable = "+".join(p_enables) if p_enables else "0"
    peter_x = "+".join(p_x_exprs) if p_x_exprs else "-w"
    peter_y = "+".join(p_y_exprs) if p_y_exprs else "-h"

    stewie_enable = "+".join(s_enables) if s_enables else "0"
    stewie_x = "+".join(s_x_exprs) if s_x_exprs else "-w"
    stewie_y = "+".join(s_y_exprs) if s_y_exprs else "-h"

    # Make absolute path for ASS because FFmpeg gets confused
    ass_abs_path = str(ass_file.resolve()).replace('\\', '/')
    # FFmpeg ass filter requires escaping colons and backslashes
    ass_filter_path = ass_abs_path.replace(':', '\\:')
    
    filter_complex = f"""
    [1:v]scale=300:-1[p]; 
    [2:v]scale=200:-1[s];
    [0:v][p]overlay=x='{peter_x}':y='{peter_y}':enable='{peter_enable}'[v1];
    [v1][s]overlay=x='{stewie_x}':y='{stewie_y}':enable='{stewie_enable}'[v2];
    [v2]ass='{ass_filter_path}'[v_out];
    [0:a]volume=0.1[a_bg];
    [3:a]volume=1.0[a_dialogue];
    [a_bg][a_dialogue]amix=inputs=2:duration=first:dropout_transition=2[a_out]
    """
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg_video),
        "-i", "peter.png",
        "-i", "stewie.png",
        "-i", str(final_audio),
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        "-t", str(total_duration),
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ Success! Brainrot video saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a Brainrot Video")
    parser.add_argument("--topic", required=True, help="Topic for Peter and Stewie to debate")
    parser.add_argument("--bg", required=True, help="Path to 9:16 background video cut")
    parser.add_argument("--output", default="final_brainrot.mp4", help="Output video path")
    args = parser.parse_args()
    
    bg_path = Path(args.bg)
    if not bg_path.exists():
        print(f"Error: Could not find bg video {args.bg}")
        return

    # Setup temp dir
    temp_dir = Path("temp_build")
    temp_dir.mkdir(exist_ok=True)
    
    # 1. Generate Script
    script = generate_script(args.topic)
    
    # 2. Generate Audio
    audio_segments = generate_audio(script, temp_dir)
    
    # 3. Combine Audio
    final_audio = temp_dir / "dialogue.mp3"
    speaker_timings, total_duration = build_combined_audio(audio_segments, final_audio)
    
    # 4. Transcribe Word-Level
    words = transcribe_audio(final_audio)
    
    # 5. Generate ASS Subtitles
    ass_file = temp_dir / "subs.ass"
    generate_ass(words, ass_file)
    
    # 6. Build Video
    build_video(bg_path, final_audio, speaker_timings, ass_file, total_duration, args.output)

if __name__ == "__main__":
    main()
