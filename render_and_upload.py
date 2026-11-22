#!/usr/bin/env python3
"""Render an original illustrated 2D horror story and upload it to YouTube.

The visuals are generated procedurally with Pillow (not text-to-video footage).
Narration uses the community edge-tts client and Microsoft's online Edge TTS service.
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1280, 720
FPS = 24
VOICE = os.getenv("TTS_VOICE") or "hi-IN-MadhurNeural"
WORK = Path("work")
OUTPUT = Path("output")


def run(command: list[str], *, cwd: Path | None = None) -> str:
    """Run a command and raise a useful, bounded error on failure."""
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        tail = completed.stdout[-5000:] if completed.stdout else "No command output"
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command[:3])}\n{tail}")
    return completed.stdout


def font_path(bold: bool = False) -> str:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return ""


def load_ascii_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if Path(path).exists():
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = font_path(bold)
    if not path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        return ImageFont.truetype(path, size)


def gradient_background(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = img.load()
    top = (8, 10, 22)
    bottom = (39, 17, 31)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(WIDTH):
            pixels[x, y] = color
    draw = ImageDraw.Draw(img, "RGBA")
    # Moon glow and moon.
    moon_x, moon_y = rng.randint(890, 1080), rng.randint(100, 190)
    draw.ellipse((moon_x - 118, moon_y - 118, moon_x + 118, moon_y + 118), fill=(174, 180, 199, 18))
    draw.ellipse((moon_x - 75, moon_y - 75, moon_x + 75, moon_y + 75), fill=(201, 205, 209, 225))
    draw.ellipse((moon_x - 57, moon_y - 83, moon_x + 82, moon_y + 56), fill=(8, 10, 22, 255))
    # Stars.
    for _ in range(75):
        x, y = rng.randrange(WIDTH), rng.randrange(20, 420)
        r = rng.choice([1, 1, 2])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(218, 220, 231, rng.randint(60, 150)))
    return img


def draw_tree(draw: ImageDraw.ImageDraw, x: int, base: int, scale: float, color: tuple[int, int, int, int]) -> None:
    trunk_w = int(20 * scale)
    draw.rectangle((x - trunk_w // 2, base - int(90 * scale), x + trunk_w // 2, base), fill=color)
    for layer in range(4):
        y = base - int((70 + layer * 47) * scale)
        half = int((72 - layer * 10) * scale)
        top = y - int(100 * scale)
        draw.polygon([(x, top), (x - half, y + 20), (x + half, y + 20)], fill=color)


def draw_scene(visual: str, index: int, output: Path) -> None:
    """Create a unique dark 2D illustrated frame from a scene description."""
    rng = random.Random(index * 997 + sum(ord(ch) for ch in visual[:100]))
    img = gradient_background(index * 29 + 11)
    draw = ImageDraw.Draw(img, "RGBA")
    words = visual.lower()
    ground = 570
    draw.rectangle((0, ground, WIDTH, HEIGHT), fill=(7, 8, 14, 255))

    if any(k in words for k in ("forest", "jungle", "tree", "woods")):
        for x in range(-40, WIDTH + 60, 145):
            draw_tree(draw, x + rng.randint(-30, 30), ground + 80, rng.uniform(0.85, 1.45), (5, 12, 15, 255))
        draw.ellipse((440, 525, 840, 650), fill=(28, 21, 28, 180))
    elif any(k in words for k in ("hospital", "clinic", "ward", "medical")):
        draw.rectangle((300, 270, 980, 590), fill=(15, 20, 29, 255), outline=(68, 73, 86, 255), width=5)
        for x in (380, 540, 700, 860):
            draw.rectangle((x, 330, x + 88, 430), fill=(27, 42, 50, 255), outline=(104, 111, 119, 255), width=4)
        draw.rectangle((600, 440, 720, 590), fill=(7, 9, 16, 255))
        draw.rectangle((605, 215, 675, 255), fill=(95, 18, 28, 220))
        draw.rectangle((631, 200, 649, 270), fill=(220, 218, 210, 240))
        draw.rectangle((607, 226, 670, 244), fill=(220, 218, 210, 240))
    elif any(k in words for k in ("grave", "cemetery", "graveyard", "tomb")):
        for x in range(90, WIDTH, 185):
            y = rng.randint(475, 565)
            draw.rounded_rectangle((x, y, x + 88, ground + 20), radius=25, fill=(45, 48, 57, 255), outline=(97, 99, 108, 180), width=3)
            draw.ellipse((x + 34, y + 12, x + 52, y + 30), outline=(126, 127, 134, 150), width=2)
    elif any(k in words for k in ("road", "street", "village", "highway", "car")):
        draw.polygon([(420, ground), (570, 360), (710, 360), (880, ground)], fill=(22, 23, 31, 255))
        draw.line((640, 390, 640, 700), fill=(180, 164, 130, 150), width=5)
        for x in (35, 1030):
            draw.polygon([(x, 390), (x + 100, 315), (x + 200, 390), (x + 200, 575), (x, 575)], fill=(13, 17, 22, 255))
            draw.rectangle((x + 55, 425, x + 95, 485), fill=(164, 110, 47, 170))
    elif any(k in words for k in ("water", "lake", "river", "well", "pond")):
        draw.rectangle((0, 465, WIDTH, HEIGHT), fill=(9, 24, 31, 255))
        for y in range(500, 700, 32):
            x = rng.randint(0, 500)
            draw.arc((x, y, x + rng.randint(150, 450), y + 25), 0, 180, fill=(77, 119, 129, 110), width=3)
        if "well" in words:
            draw.ellipse((485, 440, 795, 575), fill=(49, 48, 54, 255), outline=(111, 108, 113, 255), width=12)
            draw.ellipse((540, 455, 740, 545), fill=(3, 5, 10, 255))
    elif any(k in words for k in ("house", "haveli", "mansion", "home", "room", "corridor", "hall")):
        draw.rectangle((260, 300, 1030, 600), fill=(17, 18, 27, 255), outline=(83, 75, 82, 255), width=5)
        draw.polygon([(200, 315), (640, 130), (1090, 315)], fill=(11, 13, 20, 255), outline=(83, 75, 82, 255))
        for x in (365, 820):
            draw.rectangle((x, 365, x + 115, 475), fill=(165, 87, 45, 110), outline=(76, 67, 74, 255), width=5)
            draw.line((x + 57, 365, x + 57, 475), fill=(42, 40, 45, 255), width=4)
        draw.rectangle((565, 410, 710, 600), fill=(4, 5, 10, 255), outline=(68, 57, 65, 255), width=5)
    else:
        # Unspecified settings become an abandoned building at night.
        draw.rectangle((330, 315, 950, 590), fill=(15, 17, 25, 255), outline=(73, 74, 84, 255), width=5)
        draw.polygon([(280, 320), (640, 175), (1000, 320)], fill=(9, 11, 17, 255))
        for x in (420, 750):
            draw.rectangle((x, 370, x + 100, 475), fill=(147, 80, 43, 120))

    # Add a shadow creature / mysterious silhouette to each frame.
    cx = rng.randint(730, 1040)
    cy = rng.randint(435, 535)
    height = rng.randint(190, 275)
    figure = (cx - 42, cy - height + 45, cx + 42, cy + 85)
    draw.ellipse(figure, fill=(2, 3, 8, 245))
    draw.polygon(
        [(cx - 42, cy - height + 105), (cx - 78, cy + 92), (cx + 77, cy + 92), (cx + 42, cy - height + 105)],
        fill=(2, 3, 8, 245),
    )
    eye_y = cy - height + 82
    draw.ellipse((cx - 22, eye_y, cx - 9, eye_y + 7), fill=(211, 24, 38, 245))
    draw.ellipse((cx + 9, eye_y, cx + 22, eye_y + 7), fill=(211, 24, 38, 245))

    # Low fog and a small vignette-like dark wash.
    fog = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog, "RGBA")
    for _ in range(16):
        fx = rng.randint(-100, WIDTH)
        fy = rng.randint(480, 710)
        fw = rng.randint(150, 360)
        fh = rng.randint(20, 70)
        fog_draw.ellipse((fx, fy, fx + fw, fy + fh), fill=(160, 166, 174, rng.randint(5, 15)))
    img = Image.alpha_composite(img.convert("RGBA"), fog.filter(ImageFilter.GaussianBlur(22))).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((28, 24, 205, 63), fill=(0, 0, 0, 125))
    draw.text((44, 31), f"SCENE {index:02d}", font=load_ascii_font(21, True), fill=(225, 220, 220, 210))
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, quality=92)


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_thumbnail(title: str, first_scene: Path, output: Path) -> None:
    img = Image.open(first_scene).convert("RGBA").resize((WIDTH, HEIGHT))
    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    shade_draw.rectangle((0, 425, WIDTH, HEIGHT), fill=(0, 0, 0, 205))
    img = Image.alpha_composite(img, shade).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = load_font(66, True)
    title = (title or "रात का आख़िरी रहस्य").strip()[:70]
    lines = wrap_text(title, font, 1130, draw)[:2]
    y = 470 if len(lines) == 2 else 515
    for line in lines:
        draw.text((70, y), line, font=font, fill=(255, 247, 236), stroke_width=3, stroke_fill=(83, 9, 22))
        y += 82
    draw.text((75, 665), "HINDI 2D HORROR STORY", font=load_ascii_font(24, True), fill=(241, 190, 179))
    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "JPEG", quality=90, optimize=True)


def parse_srt_time(value: str) -> int:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return ((int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000) + int(millis)


def fmt_srt_time(ms: int) -> str:
    ms = max(0, ms)
    hours, remain = divmod(ms, 3_600_000)
    minutes, remain = divmod(remain, 60_000)
    seconds, millis = divmod(remain, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def combine_srt(srt_path: Path, offset_ms: int, output_lines: list[str]) -> None:
    if not srt_path.exists():
        return
    raw = srt_path.read_text(encoding="utf-8", errors="ignore").strip()
    blocks = re.split(r"\n\s*\n", raw)
    for block in blocks:
        lines = block.splitlines()
        timing_idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_idx is None:
            continue
        match = re.match(r"\s*(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})", lines[timing_idx])
        if not match:
            continue
        start = parse_srt_time(match.group(1)) + offset_ms
        end = parse_srt_time(match.group(2)) + offset_ms
        caption = " ".join(line.strip() for line in lines[timing_idx + 1:] if line.strip())
        if caption:
            output_lines.extend([f"{fmt_srt_time(start)} --> {fmt_srt_time(end)}", caption, ""])


def synthesize_scene(text: str, number: int, folder: Path) -> tuple[Path, Path]:
    audio = folder / f"scene_{number:02d}.mp3"
    subtitles = folder / f"scene_{number:02d}.srt"
    run([
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", VOICE,
        "--rate", "-4%",
        "--pitch", "-7Hz",
        "--write-media", str(audio),
        "--write-subtitles", str(subtitles),
    ])
    if not audio.exists() or audio.stat().st_size < 1000:
        raise RuntimeError(f"TTS did not create a valid audio file for scene {number}.")
    return audio, subtitles


def probe_duration(media: Path) -> float:
    output = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(media),
    ]).strip()
    return max(0.1, float(output))


def render_video(story: dict[str, Any]) -> tuple[Path, Path, float]:
    WORK.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    scene_folder = WORK / "scenes"
    scene_folder.mkdir(exist_ok=True)
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or not 5 <= len(scenes) <= 12:
        raise ValueError("Story must contain between 5 and 12 scenes.")

    clips: list[Path] = []
    captions: list[str] = []
    total_offset_ms = 0
    first_image: Path | None = None

    for idx, scene in enumerate(scenes, start=1):
        narration = str(scene.get("narration", "")).strip()
        visual = str(scene.get("visual", "abandoned building at night")).strip()
        if len(narration) < 25:
            raise ValueError(f"Scene {idx} narration is too short or missing.")
        image = scene_folder / f"scene_{idx:02d}.jpg"
        draw_scene(visual, idx, image)
        if first_image is None:
            first_image = image
        audio, srt = synthesize_scene(narration, idx, scene_folder)
        duration = probe_duration(audio)
        clip = scene_folder / f"clip_{idx:02d}.mp4"
        zoom_filter = (
            "zoompan=z='min(zoom+0.00045,1.06)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-i", str(image),
            "-i", str(audio),
            "-vf", zoom_filter,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
            "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "112k", "-shortest", str(clip),
        ])
        clips.append(clip)
        combine_srt(srt, total_offset_ms, captions)
        total_offset_ms += int(probe_duration(clip) * 1000)
        print(f"Rendered scene {idx}/{len(scenes)} ({duration:.1f}s)", flush=True)

    if first_image is None:
        raise RuntimeError("No scene images were produced.")

    concat_file = WORK / "clips.txt"
    concat_file.write_text("\n".join(f"file '{clip.resolve()}'" for clip in clips), encoding="utf-8")
    joined = WORK / "joined.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(joined)])

    srt_file = WORK / "captions.srt"
    # Re-number cues accurately; captions is [timing, text, blank] triplets.
    cue_lines: list[str] = []
    cue_number = 1
    cursor = 0
    while cursor < len(captions):
        if "-->" in captions[cursor] and cursor + 1 < len(captions):
            cue_lines.extend([str(cue_number), captions[cursor], captions[cursor + 1], ""])
            cue_number += 1
            cursor += 2
        else:
            cursor += 1
    srt_file.write_text("\n".join(cue_lines), encoding="utf-8")

    duration = probe_duration(joined)
    final_video = OUTPUT / "hindi_2d_horror_story.mp4"
    style = "FontName=Noto Sans Devanagari,FontSize=23,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=34,Alignment=2"
    subtitle_filter = f"subtitles=filename='{srt_file.resolve()}':force_style='{style}'"
    ambience = f"anoisesrc=color=pink:sample_rate=44100:amplitude=0.012:duration={duration:.3f}"
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(joined), "-f", "lavfi", "-i", ambience,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-vf", subtitle_filter,
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(final_video),
    ])
    thumbnail = OUTPUT / "thumbnail.jpg"
    create_thumbnail(str(story.get("thumbnail_text") or story.get("title") or "रात का आख़िरी रहस्य"), first_image, thumbnail)
    return final_video, thumbnail, probe_duration(final_video)


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram notification skipped: missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()


def upload_to_youtube(story: dict[str, Any], video_path: Path, thumbnail_path: Path) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing GitHub Actions secrets: " + ", ".join(missing))

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=scopes,
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    title = str(story.get("title") or "Hindi 2D Horror Story").strip()[:100]
    description = str(story.get("description") or "एक नई हिंदी हॉरर कहानी।").strip()
    description += "\n\nयह कहानी काल्पनिक है। वीडियो में original 2D illustrated visuals और AI-assisted narration का उपयोग किया गया है।"
    tags = [str(tag).strip().lstrip("#") for tag in story.get("tags", []) if str(tag).strip()]
    tags = tags[:20]
    if sum(len(tag) + 1 for tag in tags) > 480:
        trimmed: list[str] = []
        total = 0
        for tag in tags:
            if total + len(tag) + 1 > 480:
                break
            trimmed.append(tag)
            total += len(tag) + 1
        tags = trimmed

    privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "unlisted").lower().strip()
    if privacy not in {"public", "unlisted", "private"}:
        privacy = "unlisted"
    made_for_kids = os.getenv("YOUTUBE_MADE_FOR_KIDS", "false").lower().strip() == "true"
    body = {
        "snippet": {
            "title": title,
            "description": description[:4900],
            "tags": tags,
            "categoryId": "24",
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"YouTube upload: {int(status.progress() * 100)}%", flush=True)
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("YouTube API completed without returning a video ID.")
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
        ).execute()
    except Exception as exc:
        print(f"Thumbnail upload warning: {type(exc).__name__}: {exc}", flush=True)
    return f"https://www.youtube.com/watch?v={video_id}"


def load_story() -> dict[str, Any]:
    raw = os.getenv("STORY_JSON", "").strip()
    if not raw:
        raise RuntimeError("STORY_JSON input is empty. Trigger the GitHub Action from n8n.")
    story = json.loads(raw)
    if not isinstance(story, dict):
        raise ValueError("STORY_JSON must be a JSON object.")
    return story


def main() -> None:
    try:
        story = load_story()
        print(f"Starting story: {story.get('title', 'Untitled')}", flush=True)
        video, thumbnail, duration = render_video(story)
        print(f"Rendered {video} ({duration / 60:.1f} minutes)", flush=True)
        url = upload_to_youtube(story, video, thumbnail)
        title = str(story.get("title") or "New horror story")
        send_telegram(f"✅ YouTube upload complete!\n\n{title}\nDuration: {duration / 60:.1f} min\nVisibility: {os.getenv('YOUTUBE_PRIVACY_STATUS', 'unlisted')}\n\n{url}")
        print(f"Upload complete: {url}", flush=True)
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
