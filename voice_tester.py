"""A/B voice testing utility for ElevenLabs voices.

Usage:
    python voice_tester.py                    # Test all recommended voices
    python voice_tester.py --voice Sarah      # Test a specific voice
    python voice_tester.py --list             # List available voices
"""

import json
import sys
from pathlib import Path

from validator import SETTINGS

VOICE_SETTINGS = SETTINGS["api"]
VOICES = SETTINGS["voices"]["recommended"]
FREE_VOICES = SETTINGS["voices"].get("free_tier_fallback", [])

TEST_TEXT = SETTINGS["voices"]["custom_voice_design"]["preview_text"]


def list_voices() -> None:
    """Print available voices."""
    print("\n🎤 Recommended voices (require Starter+ plan):\n")
    for v in VOICES:
        print(f"  {v['name']:12s} — {v['desc']}")
        print(f"  {'':12s}   Use: {v['use_for']}")
        print()
    if FREE_VOICES:
        print("🆓 Free-tier premade voices:\n")
        for v in FREE_VOICES:
            print(f"  {v['name']:12s} — {v['desc']}")
            print(f"  {'':12s}   Use: {v['use_for']}")
            print()


def test_voice(voice: dict, output_dir: Path) -> Path:
    """Generate a test audio clip with a specific voice."""
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs()
    output_dir.mkdir(parents=True, exist_ok=True)

    name = voice["name"].lower()
    output_path = output_dir / f"voice_test_{name}.mp3"

    print(f"  🎤 Testing voice: {voice['name']} ({voice['id'][:8]}...)")
    print(f"     Text: {TEST_TEXT[:60]}...")

    audio = client.text_to_speech.convert(
        voice_id=voice["id"],
        text=TEST_TEXT,
        model_id=VOICE_SETTINGS["elevenlabs_model"],
        language_code=VOICE_SETTINGS["elevenlabs_language_code"],
        voice_settings={
            "stability": VOICE_SETTINGS["elevenlabs_stability"],
            "similarity_boost": VOICE_SETTINGS["elevenlabs_similarity"],
            "style": VOICE_SETTINGS["elevenlabs_style"],
            "use_speaker_boost": VOICE_SETTINGS["elevenlabs_use_speaker_boost"],
        },
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    size_kb = output_path.stat().st_size / 1024
    print(f"     Saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def test_all_voices(output_dir: Path = Path("output/voice_tests")) -> list[Path]:
    """Test all recommended voices and save samples."""
    print("\n🎤 A/B Voice Testing — Selene Academia\n")
    print(f"   Model: {VOICE_SETTINGS['elevenlabs_model']}")
    print(f"   Settings: stability={VOICE_SETTINGS['elevenlabs_stability']}, "
          f"similarity={VOICE_SETTINGS['elevenlabs_similarity']}, "
          f"style={VOICE_SETTINGS['elevenlabs_style']}")
    print(f"   Voices: {len(VOICES)} recommended + {len(FREE_VOICES)} free-tier\n")

    results = []
    used_free_fallback = False
    for voice in VOICES:
        try:
            path = test_voice(voice, output_dir)
            results.append(path)
        except Exception as e:
            err_msg = str(e)
            if "402" in err_msg or "payment_required" in err_msg or "paid_plan_required" in err_msg:
                print(f"     ⚠️  Library voice '{voice['name']}' requires paid plan, skipping.")
                used_free_fallback = True
            else:
                print(f"     ❌ Failed: {e}")

    if used_free_fallback and FREE_VOICES:
        print(f"\n🆓 Testing free-tier premade voices instead...\n")
        for voice in FREE_VOICES:
            try:
                path = test_voice(voice, output_dir)
                results.append(path)
            except Exception as e:
                print(f"     ❌ Failed: {e}")

    print(f"\n{'='*50}")
    print(f"📊 Generated {len(results)} voice samples in {output_dir}/")
    print(f"   Listen and compare, then set the chosen voice_id in config/settings.json")
    if used_free_fallback:
        print(f"   💡 Tip: upgrade to Starter ($5/mo) for native Spanish voices,")
        print(f"      or use --tts kokoro (free, local, native Spanish)")
    print(f"{'='*50}\n")
    return results


def main():
    if "--list" in sys.argv:
        list_voices()
        return

    voice_name = None
    if "--voice" in sys.argv:
        idx = sys.argv.index("--voice")
        if idx + 1 < len(sys.argv):
            voice_name = sys.argv[idx + 1]

    if voice_name:
        all_voices = VOICES + FREE_VOICES
        voice = next((v for v in all_voices if v["name"].lower() == voice_name.lower()), None)
        if not voice:
            print(f"❌ Voice '{voice_name}' not found. Use --list to see options.")
            sys.exit(1)
        test_voice(voice, Path("output/voice_tests"))
    else:
        test_all_voices()


if __name__ == "__main__":
    main()
