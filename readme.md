# brainrot video generator

generate absolute cinema right from your terminal. 

![screenshot](screenshot.png)

## the stars
here are our world-class actors:

<p align="center">
  <img src="peter.png" width="150" />
  <img src="stewie.png" width="150" />
</p>

## what it is
a cli tool that takes a topic, asks open ai to write an unhinged debate between peter and stewie, grabs tts, and uses a cursed ffmpeg command to smash it all over minecraft parkour footage. 

words pop up one by one. characters slide in and furiously vibrate when they talk. peak 9:16 content.

## how to run

**CLI:**
```bash
uv run app.py --topic "pineapple on pizza" --bg "path/to/video.mp4" [--lines 8] [--speed 1.2] [--shake 15]
```

**Web UI:**
```bash
uv run server.py
```
Open http://localhost:5000 — single page: topic, dialogue editor, TTS/GPT options, font/color, output format (mp4/mkv), bg upload. Video plays when done.

1. Set `OPENAI_API_KEY` in `.env`
2. macOS: FFmpeg auto-downloads if needed (~50MB)

## license
mit. free to steal and get famous.
