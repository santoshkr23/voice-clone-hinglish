# Santosh's Voice Clone (Hinglish TTS + video pipeline)

This repo is my own voice, cloned with [Chatterbox Multilingual TTS](https://github.com/resemble-ai/chatterbox). It speaks Hindi, Hinglish and English. It also includes the pipeline I used to make a full explainer video and Instagram reels from a script.

> **About the voice:** the clips in `refs/` are my voice, and I've shared them on purpose. Use them only for your own creative or educational content. Don't use my voice to impersonate me, for scams or calls, or to make fake statements. Chatterbox adds an invisible Perth watermark to every clip it generates.

## Try it free in Google Colab (no GPU needed)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santoshkr23/voice-clone-hinglish/blob/main/Voice_Clone_Colab.ipynb)

Choose **Runtime → T4 GPU**, run cell 1 once, then type your text in cell 2.

## What's inside

| Path | What it is |
|---|---|
| `refs/*.wav` | My voice reference clips, one per style: calm, reel, question, excited, soft, clear, english, outro |
| `say.py` | Turns any text into a clean MP3 in the cloned voice |
| `Recording_Script.md` | The script I read to record the clips (use it to clone **your own** voice) |
| `docker_video/` | Example video project: script → voice lines → whisper check → graphics → SFX/music mix |
| `skill/my-voice/SKILL.md` | A Claude Code skill, so Claude can make audio or videos in this voice in any chat |

## Setup (Windows, NVIDIA GPU)

```powershell
python -m venv .venv
.venv\Scripts\pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.venv\Scripts\pip install -r requirements.txt
```

You also need `ffmpeg` on your PATH. The first run downloads the model, a few GB.

The scripts expect the repo at `D:\VoiceClone`. Clone it there, or change the paths inside the scripts.

## Make audio

```powershell
.venv\Scripts\python say.py "आज हम सीखेंगे डॉकर, आसान भाषा में।" -s clear -o output\test.mp3
```

- `-s` picks the style: `calm reel question excited soft clear english outro`.
- `-f file.txt` reads the text from a file.
- `--seed N` gives a different take.
- `--exaggeration 0.25-1.0` sets how much emotion it uses.

Tips:
- For Hindi and Hinglish, write the text in Devanagari, including English tech words (डॉकर, सर्वर).
- Lines that are very short or full of rare English words can come out mispronounced. Reword them, or make them a bit longer.

## Use with Claude Code

Copy `skill/my-voice` to `%USERPROFILE%\.claude\skills\my-voice`. Then ask Claude "make a reel in my voice about …" or type `/my-voice`.

## Clone your own voice instead

1. Record the sections of `Recording_Script.md`: a quiet room, phone or mic about 15 cm from your mouth, WAV.
2. Cut a clean 8–15 s clip for each style and save it to `refs/<style>.wav` (24 kHz, mono).
3. Run `say.py` as above.

## Not included

- The model weights, which download automatically.
- My raw recordings.
- The sound-effects pack and background music, which are licensed and can't be shared. `docker_video/mix.py` expects your own SFX in `sfx/lib` and your own music file.
