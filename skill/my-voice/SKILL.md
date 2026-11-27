---
name: my-voice
description: Generate speech, voiceovers and full videos in the user's own cloned voice (Hinglish/Hindi/English). Use whenever the user says "my voice", "meri awaaz", "in my voice", "voiceover", "VO", "make a reel/video with my voice", or asks for narration for a travel reel, tech/education video, Instagram reel or YouTube video.
---

# My cloned voice

Everything lives in `D:\VoiceClone`. Python: `D:\VoiceClone\.venv\Scripts\python.exe` (Python 3.11, torch cu124, chatterbox-tts 0.1.7, GPU). Set `HF_HOME=D:\VoiceClone\hf_cache` (the scripts do this themselves).

## 1. Quick audio (one clip)

```
D:\VoiceClone\.venv\Scripts\python.exe D:\VoiceClone\say.py "टेक्स्ट यहाँ" -s reel -o D:\VoiceClone\output\name.mp3
```

- `-f file.txt` instead of inline text (UTF-8).
- `-s` style: `calm, reel, question, excited, soft, clear, english, outro`.
  - Reels/hooks → `reel` or `excited`.
  - Tech explainers → `clear`.
  - Endings/CTA → `outro`.
  - English lines → `english` with `--lang en`.
- `--exaggeration` 0.25–1.0 (emotion), `--cfg 0.3` = slower pacing, `--gap` pause between sentences, `--seed N` for a different take.
- Output is already cleaned: highpass, de-ess, loudnorm -16 LUFS, MP3.

## 2. Writing text for the voice (important)

- Hindi/Hinglish: give the model **Devanagari** (`language_id="hi"`). Write English tech words phonetically in Devanagari: डॉकर, कंटेनर, सर्वर, री-कैप.
- Keep the Roman version of each line too, for captions.
- Very short lines (2–3 words) or rare English words often get mispronounced or babbled. Make the line a bit longer or reword it.
- One sentence per generation works best.

## 3. Full video pipeline (copy this project)

Template: `D:\VoiceClone\docker_video`. For a new video, copy the folder to `D:\VoiceClone\<topic>_video` and edit:

1. `script.json`: scenes → lines as `[roman, devanagari]`, each scene with a `style`.
2. `gen_vo.py [--only 3,7] [--seed N]` → `lines/NN.wav`.
3. `check_lines.py`: faster-whisper transcribes each line and compares to the script. Regenerate any low-scoring line with a new seed.
   - GPU whisper needs `os.add_dll_directory(r'D:\VoiceClone\.venv\Lib\site-packages\torch\lib')`, `compute_type='int8_float16'`.
4. **Trim every line at last-word end + 0.30 s, with a 0.12 s fade** (word end from whisper word timestamps). Otherwise the TTS leaves a grunt/"fart" noise after the last word. Re-check after trimming.
5. `render.py --plan full|reel1|reel2 [--preview secs]`: PIL frames → ffmpeg libx264 (CPU; NVENC is unavailable). Scene functions are keyed to line start times. Rewrite the scene graphics for the new topic.
6. `mix.py <plan>`: voice + SFX + music, sidechain-ducked, final about -14 LUFS.
   - Then remux into `FINAL\` with `-map 0:v:0 -map 0:a:0 -map_metadata -1`.

Formats: YouTube 1920×1080; reels 1080×1920, with the stage at the top and big captions below. Reels end with "Pura video dekhne ke liye YouTube pe jao, link bio mein hai" plus the comment CTA.

## 4. Sounds and music

- SFX: `D:\VoiceClone\sfx\lib\*.wav` (normalized, with `info.json` holding the peak times). Keys: woosh1, woosh2, swish, l2r, r2l, riser1-4, hit1, hit2, metal, click, mclick, kbfast, kbslow, notif, msg, paper, glass, drone1, drone2.
  - Source pack: `F:\Sounds for adding in vlogs\Essential SFX-20251230T183542Z-3-001\Essential SFX`.
- Rules (from the pack's guide):
  - whoosh on transitions and movement;
  - riser peak exactly on the reveal;
  - hits only on big statements;
  - foley (keyboard, click, paper) where the action is on screen;
  - drone low under the hook;
  - SFX always below the voice.
- Music: `E:\PROJECT BC\Ai Video Editor\Brand Kit\ES_Informer - Wendel Scherer.mp3` at -25 dB, ducked under the voice.

## 5. Always

- Verify every line by transcription before rendering.
- Tell the user the result was checked by transcription and measurement, not by ear.
- Final files go in a `FINAL\` folder.
