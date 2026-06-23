"""Text -> video pipeline using Gemini for script + images, gTTS for voice, moviepy for stitching."""
import os
import json
import re
import uuid
import tempfile
from pathlib import Path

import google.generativeai as genai
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip,
)

from models import Setting

VIDEOS_DIR = Path(__file__).parent / "generated_videos"
VIDEOS_DIR.mkdir(exist_ok=True)


def _configure():
    key = os.environ.get("GEMINI_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        raise RuntimeError("GEMINI_API_KEY missing — set it in .env")
    genai.configure(api_key=key)


def generate_scenes(prompt: str):
    """Ask Gemini for a structured scene list."""
    _configure()
    model_name = Setting.get("gemini_model", "gemini-2.0-flash-exp")
    system = Setting.get("system_prompt", "")
    model = genai.GenerativeModel(model_name, system_instruction=system)
    resp = model.generate_content(f"Topic: {prompt}\n\nReturn the JSON array now.")
    text = resp.text.strip()
    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        scenes = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: split lines as narration, reuse prompt as image
        lines = [l for l in prompt.split(".") if l.strip()][:5]
        scenes = [{"narration": l.strip(), "image_prompt": l.strip()} for l in lines]
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("Failed to parse scenes")
    return scenes[:8]


def _placeholder_image(text: str, size=(1280, 720), color=(30, 30, 40)) -> str:
    """Generate a styled placeholder when image API unavailable."""
    img = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
    except Exception:
        font = ImageFont.load_default()
    # word-wrap
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=font) < size[0] - 100:
            line = test
        else:
            lines.append(line); line = w
    if line: lines.append(line)
    y = (size[1] - len(lines) * 60) // 2
    for ln in lines:
        tw = draw.textlength(ln, font=font)
        draw.text(((size[0] - tw) / 2, y), ln, fill=(240, 240, 250), font=font)
        y += 60
    path = tempfile.mktemp(suffix=".png")
    img.save(path)
    return path


def generate_image(prompt: str) -> str:
    """Try Gemini image gen; fallback to styled placeholder."""
    try:
        _configure()
        img_model = Setting.get("image_model", "gemini-2.0-flash-exp")
        model = genai.GenerativeModel(img_model)
        resp = model.generate_content(
            f"Generate a cinematic 16:9 image: {prompt}",
            generation_config={"response_modalities": ["IMAGE"]},
        )
        for part in resp.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                path = tempfile.mktemp(suffix=".png")
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
    except Exception as e:
        print(f"[image] gemini failed, using placeholder: {e}")
    return _placeholder_image(prompt[:120])


def make_video(prompt: str) -> str:
    """Full pipeline. Returns filename (in generated_videos/)."""
    scenes = generate_scenes(prompt)
    duration = max(2, Setting.get_int("scene_duration", 4))
    lang = Setting.get("voice_lang", "en")
    res = Setting.get_int("video_resolution", 720)
    w, h = (1920, 1080) if res >= 1080 else (1280, 720)

    clips = []
    tmp_files = []
    for scene in scenes:
        narration = scene.get("narration", "")
        img_prompt = scene.get("image_prompt", narration)

        img_path = generate_image(img_prompt)
        tmp_files.append(img_path)

        # TTS
        audio_path = tempfile.mktemp(suffix=".mp3")
        try:
            gTTS(text=narration or "scene", lang=lang).save(audio_path)
            tmp_files.append(audio_path)
            audio = AudioFileClip(audio_path)
            clip_dur = max(duration, audio.duration + 0.5)
            clip = ImageClip(img_path).set_duration(clip_dur).resize((w, h)).set_audio(audio)
        except Exception as e:
            print(f"[tts] failed: {e}")
            clip = ImageClip(img_path).set_duration(duration).resize((w, h))
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    out_name = f"{uuid.uuid4().hex}.mp4"
    out_path = VIDEOS_DIR / out_name
    final.write_videofile(
        str(out_path), fps=24, codec="libx264", audio_codec="aac",
        threads=2, verbose=False, logger=None,
    )

    for f in tmp_files:
        try: os.remove(f)
        except Exception: pass

    return out_name
