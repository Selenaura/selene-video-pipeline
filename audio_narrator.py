"""Generate audio narration using ElevenLabs SDK."""

import json
import os
from pathlib import Path

from validator import SETTINGS

API_CONFIG = SETTINGS["api"]
SSML_CONFIG = SETTINGS["narration_ssml"]
VOICES = SETTINGS["voices"]


def get_voice_id() -> str:
    """Get the configured voice ID (first recommended voice by default)."""
    return VOICES["recommended"][0]["id"]


def prepare_narration_text(slides: list[dict]) -> list[dict]:
    """Prepare narration text with SSML pauses for each slide."""
    prepared = []
    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            continue

        # Add SSML inter-slide pause at the beginning (except first slide)
        if i > 0:
            narration = SSML_CONFIG["between_slides"] + " " + narration

        # Add pause before citations
        citation = slide.get("citation")
        if citation and slide["type"] == "science":
            narration = narration.rstrip() + " " + SSML_CONFIG["before_citation"]

        prepared.append({
            "slide_index": i,
            "slide_type": slide.get("type", "content"),
            "text": narration,
            "char_count": len(narration),
        })

    return prepared


def synthesize_audio(text: str, output_path: str, voice_id: str = None,
                     dry_run: bool = False) -> dict:
    """Synthesize audio for a single text segment.

    Returns dict with: path, duration_seconds, char_count
    """
    if dry_run:
        # Create a tiny silent MP3 placeholder
        _create_silent_mp3(output_path)
        return {
            "path": output_path,
            "duration_seconds": len(text.split()) / (SETTINGS["video"]["words_per_minute"] / 60),
            "char_count": len(text),
            "cost_estimate": 0,
        }

    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

    client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
    voice_id = voice_id or get_voice_id()

    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=API_CONFIG["elevenlabs_model"],
        voice_settings=VoiceSettings(
            stability=API_CONFIG["elevenlabs_stability"],
            similarity_boost=API_CONFIG["elevenlabs_similarity"],
            style=API_CONFIG["elevenlabs_style"],
            use_speaker_boost=API_CONFIG["elevenlabs_use_speaker_boost"],
        ),
        language_code=API_CONFIG["elevenlabs_language_code"],
        output_format=SETTINGS["video"]["audio_format"],
    )

    # Write audio bytes to file
    audio_bytes = b"".join(audio_generator)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    # Estimate duration from word count (actual duration requires decoding)
    word_count = len(text.split())
    est_duration = word_count / (SETTINGS["video"]["words_per_minute"] / 60)

    return {
        "path": output_path,
        "duration_seconds": est_duration,
        "char_count": len(text),
        "cost_estimate": len(text) * 0.00003,  # ~$0.30 per 10K chars on Creator plan
    }


def narrate_lesson(script_path: str | Path, output_dir: str | Path = None,
                   dry_run: bool = False) -> dict:
    """Generate audio for all slides in a lesson script.

    Returns summary dict with total chars, cost, duration, and per-slide info.
    """
    script_path = Path(script_path)
    with open(script_path) as f:
        script = json.load(f)

    if output_dir is None:
        output_dir = script_path.parent / "audio"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slides = script.get("slides", [])
    prepared = prepare_narration_text(slides)

    total_chars = 0
    total_cost = 0
    total_duration = 0
    slide_audio = []

    for item in prepared:
        audio_file = output_dir / f"slide_{item['slide_index']:03d}.mp3"

        # Resume: skip existing files > 1KB
        if audio_file.exists() and audio_file.stat().st_size > 1024 and not dry_run:
            print(f"  ⏭ Slide {item['slide_index']}: already exists, skipping")
            # Estimate duration from text
            word_count = len(item["text"].split())
            est_duration = word_count / (SETTINGS["video"]["words_per_minute"] / 60)
            slide_audio.append({
                "slide_index": item["slide_index"],
                "path": str(audio_file),
                "duration_seconds": est_duration,
                "skipped": True,
            })
            continue

        print(f"  🎙 Slide {item['slide_index']} ({item['slide_type']}): "
              f"{item['char_count']} chars...")

        result = synthesize_audio(
            text=item["text"],
            output_path=str(audio_file),
            dry_run=dry_run,
        )

        total_chars += result["char_count"]
        total_cost += result.get("cost_estimate", 0)
        total_duration += result["duration_seconds"]

        slide_audio.append({
            "slide_index": item["slide_index"],
            "path": result["path"],
            "duration_seconds": result["duration_seconds"],
            "skipped": False,
        })

    summary = {
        "total_chars": total_chars,
        "total_cost_estimate": round(total_cost, 4),
        "total_duration_seconds": round(total_duration, 1),
        "total_duration_minutes": round(total_duration / 60, 1),
        "slides": slide_audio,
    }

    # Save audio manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    mode = "dry-run" if dry_run else "ElevenLabs"
    print(f"  🔊 Audio complete ({mode}): {len(slide_audio)} slides, "
          f"{total_chars} chars, ~{summary['total_duration_minutes']} min, "
          f"~€{total_cost:.4f}")

    return summary


def _create_silent_mp3(path: str):
    """Create a minimal valid MP3 file (silence) for dry-run testing."""
    # Minimal MP3 frame: MPEG1 Layer3, 128kbps, 44100Hz, ~0.026s of silence
    # Frame header: 0xFFFB9004 = sync + MPEG1, Layer3, 128kbps, 44100Hz, stereo
    frame_header = bytes([0xFF, 0xFB, 0x90, 0x04])
    # Pad rest of frame (417 bytes for 128kbps/44100Hz)
    frame_data = b'\x00' * 413
    # Write a few frames for ~0.1s
    with open(path, "wb") as f:
        for _ in range(4):
            f.write(frame_header + frame_data)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python audio_narrator.py <script.json> [--dry-run]")
        sys.exit(1)
    dry = "--dry-run" in sys.argv
    narrate_lesson(sys.argv[1], dry_run=dry)
