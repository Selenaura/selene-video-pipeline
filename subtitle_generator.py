"""Generate SRT subtitles and transcripts from script + audio manifest."""

import json
import re
from pathlib import Path

from validator import SETTINGS

SRT_MAX_CHARS = SETTINGS["output"]["srt_max_chars_per_line"]
SRT_MAX_LINES = SETTINGS["output"]["srt_max_lines"]
WPM = SETTINGS["video"]["words_per_minute"]


def _format_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_into_sentences(text: str) -> list[str]:
    """Split narration text into sentences for subtitle cues."""
    # Remove SSML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _wrap_subtitle(text: str, max_chars: int = SRT_MAX_CHARS,
                   max_lines: int = SRT_MAX_LINES) -> str:
    """Wrap text into subtitle-friendly lines."""
    if len(text) <= max_chars:
        return text

    words = text.split()
    lines = []
    current_line = []
    current_len = 0

    for word in words:
        if current_len + len(word) + (1 if current_line else 0) > max_chars:
            if current_line:
                lines.append(" ".join(current_line))
                if len(lines) >= max_lines:
                    break
                current_line = [word]
                current_len = len(word)
            else:
                lines.append(word[:max_chars])
                current_line = []
                current_len = 0
        else:
            current_line.append(word)
            current_len += len(word) + (1 if len(current_line) > 1 else 0)

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


def generate_srt(script: dict, manifest: dict) -> str:
    """Generate SRT subtitle content from script and audio manifest."""
    slides = script.get("slides", [])
    slide_timings = {s["slide_index"]: s for s in manifest.get("slides", [])}

    srt_entries = []
    cue_index = 1
    cumulative_time = 0.0

    for i, slide in enumerate(slides):
        narration = slide.get("narration", "")
        if not narration:
            continue

        # Get slide duration from manifest
        timing = slide_timings.get(i, {})
        slide_duration = timing.get("duration_seconds", len(narration.split()) / (WPM / 60))

        # Split narration into sentences for cues
        sentences = _split_into_sentences(narration)
        if not sentences:
            cumulative_time += slide_duration
            continue

        # Distribute time across sentences proportionally by word count
        total_words = sum(len(s.split()) for s in sentences)
        if total_words == 0:
            cumulative_time += slide_duration
            continue

        for sentence in sentences:
            word_count = len(sentence.split())
            sentence_duration = (word_count / total_words) * slide_duration
            # Minimum 1.5s per cue for readability
            sentence_duration = max(sentence_duration, 1.5)

            start_time = cumulative_time
            end_time = cumulative_time + sentence_duration

            wrapped = _wrap_subtitle(sentence)

            srt_entries.append(
                f"{cue_index}\n"
                f"{_format_timestamp(start_time)} --> {_format_timestamp(end_time)}\n"
                f"{wrapped}\n"
            )
            cue_index += 1
            cumulative_time = end_time

    return "\n".join(srt_entries)


def generate_transcript(script: dict) -> str:
    """Generate a markdown transcript with full narration and citations."""
    title = script.get("lesson_title", "Lección")
    slides = script.get("slides", [])
    citations = script.get("citations_bibliography", [])

    lines = [f"# {title}\n"]

    for i, slide in enumerate(slides):
        slide_type = slide.get("type", "content")
        slide_title = slide.get("title", f"Slide {i+1}")
        narration = slide.get("narration", "")

        lines.append(f"\n## [{slide_type.upper()}] {slide_title}\n")
        # Clean SSML from narration for transcript
        clean_narration = re.sub(r'<[^>]+>', '', narration)
        lines.append(f"{clean_narration}\n")

    # Bibliography
    if citations:
        lines.append("\n---\n")
        lines.append("## Referencias\n")
        for j, cite in enumerate(citations, 1):
            lines.append(f"{j}. {cite}\n")

    return "\n".join(lines)


def process_lesson(script_path: str | Path, output_dir: str | Path = None) -> dict:
    """Generate SRT and transcript for a lesson."""
    script_path = Path(script_path)
    with open(script_path) as f:
        script = json.load(f)

    if output_dir is None:
        output_dir = script_path.parent
    output_dir = Path(output_dir)

    # Load audio manifest if available
    manifest_path = output_dir / "audio" / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)

    # Generate SRT
    srt_content = generate_srt(script, manifest)
    srt_path = output_dir / "lesson.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    cue_count = srt_content.count("\n\n")
    print(f"  📝 SRT saved: {srt_path} ({cue_count} cues)")

    # Generate transcript
    transcript_content = generate_transcript(script)
    transcript_path = output_dir / "transcript.md"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_content)
    print(f"  📄 Transcript saved: {transcript_path}")

    return {
        "srt_path": str(srt_path),
        "transcript_path": str(transcript_path),
        "cue_count": cue_count,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python subtitle_generator.py <script.json>")
        sys.exit(1)
    process_lesson(sys.argv[1])
