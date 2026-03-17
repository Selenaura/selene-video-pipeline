"""Assemble final MP4 video from slides (PNG) + audio (MP3)."""

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

from validator import SETTINGS

VIDEO_CONFIG = SETTINGS["video"]
RESOLUTION = tuple(int(x) for x in VIDEO_CONFIG["resolution"].split("x"))
FPS = 24
SILENCE_GAP = VIDEO_CONFIG["inter_slide_silence"]
MIN_SLIDE_SECS = VIDEO_CONFIG["min_slide_seconds"]
WPM = VIDEO_CONFIG["words_per_minute"]


def render_slides_to_png(pptx_path: str | Path, output_dir: str | Path) -> list[Path]:
    """Render PPTX slides to PNG images using Pillow."""
    pptx_path = Path(pptx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prs = Presentation(str(pptx_path))
    png_files = []
    width, height = RESOLUTION

    for i, slide in enumerate(prs.slides):
        img = Image.new("RGB", (width, height), color=(10, 10, 15))
        draw = ImageDraw.Draw(img)

        texts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                texts.append(shape.text.strip())

        y_pos = 80
        for j, text in enumerate(texts):
            if not text or text == "✦":
                continue

            if j == 0 and len(text) < 20:
                font_size, color = 22, (201, 168, 76)
            elif j <= 1:
                font_size, color, y_pos = 48, (232, 213, 160), 160
            else:
                font_size, color = 32, (240, 237, 228)
                y_pos += 20

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

            max_w = width - 200
            words = text.split()
            lines = []
            cur = []
            for word in words:
                test = " ".join(cur + [word])
                bbox = draw.textbbox((0, 0), test, font=font)
                if bbox[2] - bbox[0] > max_w and cur:
                    lines.append(" ".join(cur))
                    cur = [word]
                else:
                    cur.append(word)
            if cur:
                lines.append(" ".join(cur))

            for line in lines:
                draw.text((100, y_pos), line, fill=color, font=font)
                y_pos += font_size + 10
            y_pos += 15

        try:
            wm_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except (OSError, IOError):
            wm_font = ImageFont.load_default()
        draw.text((width // 2 - 80, height - 40), "SELENE ACADEMIA",
                  fill=(64, 64, 69), font=wm_font)

        png_path = output_dir / f"slide_{i:03d}.png"
        img.save(str(png_path), "PNG")
        png_files.append(png_path)

    return png_files


def assemble_video(lesson_dir: str | Path, dry_run: bool = False) -> Path:
    """Assemble final MP4 from slides + audio using moviepy."""
    lesson_dir = Path(lesson_dir)
    script_path = lesson_dir / "script.json"
    pptx_path = lesson_dir / "slides.pptx"
    audio_dir = lesson_dir / "audio"
    manifest_path = audio_dir / "manifest.json"

    with open(script_path) as f:
        script = json.load(f)

    manifest = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    slide_timings = {s["slide_index"]: s for s in manifest.get("slides", [])}

    # Step 1: Export slides to PNG
    frames_dir = lesson_dir / "frames"
    print(f"  🖼 Exporting slides to PNG...")
    png_files = render_slides_to_png(pptx_path, frames_dir)
    print(f"  🖼 {len(png_files)} slide frames exported")

    # Step 2: Create video clips using moviepy
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

    clips = []
    slides = script.get("slides", [])

    for i, slide in enumerate(slides):
        if i >= len(png_files):
            break

        png_path = png_files[i]
        audio_path = audio_dir / f"slide_{i:03d}.mp3"

        # Get duration from slide data or estimate
        slide_duration = slide.get("duration_seconds")
        if not slide_duration:
            timing = slide_timings.get(i, {})
            slide_duration = timing.get("duration_seconds")
        if not slide_duration:
            narration = slide.get("narration", "")
            word_count = len(narration.split())
            slide_duration = max(word_count / (WPM / 60) + SILENCE_GAP, MIN_SLIDE_SECS)

        # Create image clip
        img_clip = ImageClip(str(png_path), duration=float(slide_duration))
        img_clip = img_clip.resized(RESOLUTION)

        # Attach audio if available and valid (not dry-run placeholders)
        if (audio_path.exists() and audio_path.stat().st_size > 2048
                and not dry_run):
            try:
                audio_clip = AudioFileClip(str(audio_path))
                img_clip = img_clip.with_audio(audio_clip)
            except Exception as e:
                print(f"  ⚠ Could not load audio for slide {i}: {e}")

        clips.append(img_clip)

    if not clips:
        raise RuntimeError("No clips to assemble")

    # Step 3: Concatenate
    print(f"  🎬 Assembling {len(clips)} clips...")
    final = concatenate_videoclips(clips, method="compose")

    # Step 3b: Mix ambient music if available
    music_path = lesson_dir / "ambient.mp3"
    if not music_path.exists():
        music_path = Path("assets") / "ambient.mp3"
    if music_path.exists() and not dry_run:
        try:
            music = AudioFileClip(str(music_path))
            if music.duration < final.duration:
                # Loop music to match video length
                loops_needed = int(final.duration / music.duration) + 1
                from moviepy import concatenate_audioclips
                music = concatenate_audioclips([music] * loops_needed)
            music = music.subclipped(0, final.duration)
            music = music.with_volume_scaled(0.08)  # ~8% volume for background
            if final.audio is not None:
                from moviepy import CompositeAudioClip
                final = final.with_audio(CompositeAudioClip([final.audio, music]))
            else:
                final = final.with_audio(music)
            print(f"  🎵 Ambient music mixed at 8% volume")
        except Exception as e:
            print(f"  ⚠ Could not mix ambient music: {e}")

    # Step 4: Write output
    output_path = lesson_dir / "lesson.mp4"
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec=VIDEO_CONFIG["codec"],
        preset=VIDEO_CONFIG["preset"],
        audio_codec="aac",
        audio_bitrate=VIDEO_CONFIG["audio_bitrate"],
        logger=None,
    )

    total_duration = sum(c.duration for c in clips)
    print(f"  🎥 Video saved: {output_path} ({total_duration:.0f}s / {total_duration/60:.1f} min)")

    # Cleanup
    final.close()
    for clip in clips:
        clip.close()

    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python video_assembler.py <lesson_dir> [--dry-run]")
        sys.exit(1)
    dry = "--dry-run" in sys.argv
    assemble_video(sys.argv[1], dry_run=dry)
