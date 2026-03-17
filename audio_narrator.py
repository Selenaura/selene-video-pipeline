"""Generate audio narration using ElevenLabs SDK or Kokoro TTS (free fallback).

TTS Engine selection:
  1. ElevenLabs (default): Best quality, requires API key, ~€0.15/lesson
  2. Kokoro (--tts kokoro): Free, local, 82M params, Apache license, Spanish support
  3. Dry-run: Silent MP3 placeholders, no API needed
"""

import json
import os
import re
from pathlib import Path

from validator import SETTINGS

API_CONFIG = SETTINGS["api"]
SSML_CONFIG = SETTINGS["narration_ssml"]
VOICES = SETTINGS["voices"]

# TTS engine detection
_KOKORO_AVAILABLE = False
try:
    import kokoro
    _KOKORO_AVAILABLE = True
except ImportError:
    pass


def get_voice_id() -> str:
    """Get the configured voice ID (first recommended voice by default)."""
    return VOICES["recommended"][0]["id"]


def get_fallback_voice_id() -> str:
    """Get a free-tier premade voice ID as fallback."""
    fallback = VOICES.get("free_tier_fallback", [])
    if fallback:
        return fallback[0]["id"]
    # Hardcoded Rachel as last resort
    return "21m00Tcm4TlvDq8ikWAM"


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

    def _call_tts(vid: str):
        return client.text_to_speech.convert(
            text=text,
            voice_id=vid,
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

    try:
        audio_generator = _call_tts(voice_id)
        audio_bytes = b"".join(audio_generator)
    except Exception as e:
        err_msg = str(e)
        if "402" in err_msg or "payment_required" in err_msg or "paid_plan_required" in err_msg:
            fallback_id = get_fallback_voice_id()
            fallback_name = next(
                (v["name"] for v in VOICES.get("free_tier_fallback", []) if v["id"] == fallback_id),
                "premade"
            )
            print(f"  ⚠️  Library voice requires paid plan. Falling back to '{fallback_name}' (premade, free tier).")
            print(f"     Tip: upgrade to Starter ($5/mo) for native Spanish voices, or use --tts kokoro (free).")
            audio_generator = _call_tts(fallback_id)
            audio_bytes = b"".join(audio_generator)
        else:
            raise
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


def _strip_ssml(text: str) -> str:
    """Remove SSML tags for TTS engines that don't support them."""
    return re.sub(r'<[^>]+>', '', text).strip()


def synthesize_kokoro(text: str, output_path: str) -> dict:
    """Synthesize audio using Kokoro TTS (free, local, 82M params)."""
    import soundfile as sf
    from kokoro import KPipeline

    # Strip SSML tags — Kokoro doesn't support them
    clean_text = _strip_ssml(text)

    pipeline = KPipeline(lang_code='e')  # 'e' = Spanish
    samples = None
    sr = 24000

    for _, _, audio in pipeline(clean_text):
        if samples is None:
            samples = audio
        else:
            import numpy as np
            samples = np.concatenate([samples, audio])

    if samples is not None:
        # Save as WAV first, then convert to MP3 if ffmpeg available
        wav_path = output_path.replace('.mp3', '.wav') if output_path.endswith('.mp3') else output_path
        sf.write(wav_path, samples, sr)

        # Convert to MP3 if ffmpeg is available
        import shutil
        if shutil.which("ffmpeg") and output_path.endswith('.mp3'):
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-i", wav_path,
                "-b:a", "128k", output_path
            ], capture_output=True, timeout=30)
            Path(wav_path).unlink(missing_ok=True)
        elif output_path.endswith('.mp3'):
            # No ffmpeg — keep as WAV
            Path(wav_path).rename(output_path)

    duration = len(samples) / sr if samples is not None else 0
    return {
        "path": output_path,
        "duration_seconds": duration,
        "char_count": len(clean_text),
        "cost_estimate": 0,
    }


def narrate_lesson(script_path: str | Path, output_dir: str | Path = None,
                   dry_run: bool = False, tts_engine: str = "elevenlabs") -> dict:
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

        if tts_engine == "kokoro" and _KOKORO_AVAILABLE and not dry_run:
            result = synthesize_kokoro(
                text=item["text"],
                output_path=str(audio_file),
            )
        else:
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

    engine_name = "dry-run" if dry_run else ("Kokoro" if tts_engine == "kokoro" else "ElevenLabs")
    print(f"  🔊 Audio complete ({engine_name}): {len(slide_audio)} slides, "
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
        print("Usage: python audio_narrator.py <script.json> [--dry-run] [--tts kokoro|elevenlabs]")
        sys.exit(1)
    dry = "--dry-run" in sys.argv
    engine = "elevenlabs"
    if "--tts" in sys.argv:
        idx = sys.argv.index("--tts")
        if idx + 1 < len(sys.argv):
            engine = sys.argv[idx + 1]
    narrate_lesson(sys.argv[1], dry_run=dry, tts_engine=engine)
