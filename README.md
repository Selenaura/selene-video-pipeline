# Selene Video Pipeline

Automated video lesson production for Selene Academia. Generates complete video lessons from course definitions: scripts, slides, narration, subtitles, thumbnails, and final MP4.

**Target**: 24 lessons/course, ~5 EUR total cost, studio-quality output.

## Architecture

```
config/courses.json (24 lessons)
        │
        ▼
┌──────────────────┐  Claude API   ┌────────────────┐
│ script_generator  │ ────────────► │  script.json   │
│ (script + quiz)   │               │  (validated)   │
└──────────────────┘               └───────┬────────┘
                                           │
                              ┌────────────┼──────────────┐
                              ▼            ▼              ▼
                        slide_builder  audio_narrator  subtitle_generator
                         (python-pptx) (ElevenLabs)    (SRT + transcript)
                              │            │              │
                              ▼            ▼              ▼
                         slides.pptx   audio/*.mp3    lesson.srt
                              │            │
                              └─────┬──────┘
                                    ▼
                             video_assembler
                              (moviepy)
                                    │
                         ┌──────────┼──────────┐
                         ▼          ▼          ▼
                    lesson.mp4  thumbnail.png  transcript.md
```

## Quick Start

```bash
# Install dependencies
pip install python-pptx elevenlabs Pillow requests moviepy anthropic

# Set API keys
export ANTHROPIC_API_KEY=sk-ant-...
export ELEVENLABS_API_KEY=...

# List available lessons
python pipeline.py --list

# Generate script only (dry-run, no API keys needed)
python pipeline.py --lesson 0 --steps script --dry-run

# Full pipeline for one lesson
python pipeline.py --lesson 0

# Entire course (24 lessons, with resume support)
python pipeline.py --course brujula-interior

# Validate an existing script
python pipeline.py --validate output/lesson_00/script.json
```

## Pipeline Steps

| Step | Module | Output | Requires |
|------|--------|--------|----------|
| `script` | `script_generator.py` | `script.json` | Anthropic API |
| `slides` | `slide_builder.py` | `slides.pptx` | script.json |
| `audio` | `audio_narrator.py` | `audio/*.mp3` + `manifest.json` | ElevenLabs API |
| `subtitles` | `subtitle_generator.py` | `lesson.srt` + `transcript.md` | script.json |
| `video` | `video_assembler.py` | `lesson.mp4` | slides.pptx + audio |
| `thumbnail` | `thumbnail_generator.py` | `thumbnail.png` | script.json |

Run specific steps: `--steps script,slides,audio`

## Dry-Run Mode

Test the full pipeline without API calls:

```bash
python pipeline.py --lesson 0 --dry-run
```

This uses golden example scripts (from `scripts/`) or generates realistic samples. Audio files are replaced with silent placeholders. Useful for development and CI.

## Voice Selection

Three recommended voices are pre-configured in `config/settings.json`:

| Voice | Character | Use Case |
|-------|-----------|----------|
| Sarah | Expressive, energetic | Standard lessons |
| Lily | Calm, soothing | Meditations, practices |
| Jessica | Warm, conversational | Alternative for education |

Test voices with the A/B utility:

```bash
python voice_tester.py --list          # List voices
python voice_tester.py                 # Generate samples for all
python voice_tester.py --voice Sarah   # Test one voice
```

Samples are saved to `output/voice_tests/`. Listen and compare, then set the chosen `voice_id` in the audio narrator config.

To create a custom voice, use the Voice Design prompt in `config/settings.json` → `voices.custom_voice_design.prompt`.

## Ambient Music

Place an `ambient.mp3` file in either:
- The lesson directory (`output/lesson_00/ambient.mp3`) for per-lesson music
- `assets/ambient.mp3` for a global default

The video assembler automatically mixes it at ~8% volume. Use royalty-free tracks only.

## Cost Estimate

| Component | Per Lesson | Course (24 lessons) |
|-----------|-----------|---------------------|
| Claude (script) | ~0.05 EUR | 1.20 EUR |
| ElevenLabs (audio) | ~0.15 EUR | 3.60 EUR |
| **Total** | **~0.20 EUR** | **~4.80 EUR** |

## Output Structure

```
output/
└── lesson_00/
    ├── script.json       # Full script with slides, narration, citations
    ├── slides.pptx       # Quantum Ethereal presentation
    ├── audio/
    │   ├── slide_000.mp3 # Per-slide narration
    │   ├── slide_001.mp3
    │   └── manifest.json # Timing and metadata
    ├── frames/
    │   ├── slide_000.png # Rendered slide images
    │   └── ...
    ├── lesson.mp4        # Final video
    ├── lesson.srt        # Subtitles (sentence-aligned)
    ├── transcript.md     # Full transcript with bibliography
    └── thumbnail.png     # 1280x720 thumbnail
```

## Golden Examples

The `scripts/` directory contains hand-crafted Module 1 scripts that serve as quality references and few-shot examples for the script generator:

- `M01_L01` — Espiritualidad consciente (title lesson)
- `M01_L02` — Atención entrenada (mindfulness)
- `M01_L03` — Neuroplasticidad (neuroscience)
- `M01_Q01` — Quiz: Fundamentos

These define the target format: slide types (hook/content/science/practice/summary), SSML pauses, real citations, conversational tone, and meta validation blocks.

## Hard Constraints

1. All content in Spanish (Spain)
2. Never mention AI/IA/algorithms/chatbot/LLM
3. Every lesson cites 2+ peer-reviewed studies (author, year, journal)
4. No pseudoscientific claims without citation
5. Max 4 bullets/slide, max 12 words/bullet
6. Narration: 20-150 words/slide, conversational tone

## Design: Quantum Ethereal

- Background: `#0A0A0F` (near-black)
- Gold accent: `#C9A84C` with light/dim variants
- Fonts: Cormorant Garamond (display) / Outfit (body), with Georgia/Calibri fallbacks
- Corner ornaments, gold separators, moon symbols
- SELENE ACADEMIA watermark

## Troubleshooting

**No API key**: Use `--dry-run` to test the pipeline without API access.

**Video encoding slow**: moviepy + libx264 encoding is CPU-intensive. Expected: 2-5 min per lesson on modern hardware.

**Missing fonts**: The pipeline falls back to DejaVu Sans/Serif, then to Pillow's default font. For best results, install Cormorant Garamond and Outfit.

**ElevenLabs quota**: Each lesson uses ~3000-5000 characters. The free tier allows 10K chars/month. Use `audio_narrator.py`'s resume feature to avoid re-generating existing audio.

**LibreOffice not needed**: The pipeline renders slides to PNG using Pillow directly from python-pptx, no LibreOffice installation required.

## Documentation

| File | Content |
|------|---------|
| `CLAUDE.md` | Project instructions and constraints |
| `RESEARCH_BRIEFING.md` | Competitive analysis and technical decisions |
| `prompt_plan.md` | 7 implementation phases with status |
| `config/settings.json` | Full configuration with inline documentation |
| `config/courses.json` | 24 lessons for Course 1 |
| `docs/phase0_slide_stream_evaluation.md` | slide-stream evaluation and rejection |
