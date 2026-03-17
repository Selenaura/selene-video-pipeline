# Video Pipeline — Task Plan

## Phase 0: Evaluate slide-stream [CRITICAL — DO THIS FIRST]
- [ ] `pip install slide-stream[all-ai]` and run `slide-stream providers`
- [ ] Create a test Markdown file with 3 slides and Spanish narration text
- [ ] Run `slide-stream create test.md test.mp4` with ElevenLabs configured
- [ ] **DECISION**: Does slide-stream produce usable output? Y → use it as assembly layer. N → build custom ffmpeg pipeline.
- [ ] Document decision and reasoning in README.md

**Acceptance**: A 30-second test video exists that plays correctly.
**If slide-stream fails**: Skip to Phase 1-ALT below. The script generator and PPTX template work regardless.

## Phase 1: Script Generator
- [ ] Build `script_generator.py` with Claude API call
- [ ] System prompt enforces: Spanish, no banned terms, ≥2 citations, conversational tone
- [ ] Input: lesson object from config/courses.json
- [ ] Output: `script.json` with structured slides (hook → content → evidence → practice → summary → CTA)
- [ ] Each slide: type, title, bullets (max 4, max 12 words each), narration (20-150 words), citation
- [ ] Validation function: checks banned terms, citation count, narration length, slide count (6-16)
- [ ] 3 quiz questions per lesson saved in script.json
- [ ] Test: generate script for Lesson 0, verify it passes all quality checks in settings.json

**Acceptance**: `python pipeline.py --lesson 0 --steps script` produces valid script.json with 0 validation errors.

## Phase 2: PPTX Template (Quantum Ethereal)
- [ ] Create reusable PPTX template file `templates/quantum_ethereal.pptx` with slide masters
- [ ] OR create programmatic slide builder in `slide_builder.py` using python-pptx
- [ ] Slide types: hook (violet accent), content (gold), science (blue), quote, practice (teal), summary (gold)
- [ ] Background: solid #0A0A0F (gradients optional — LibreOffice may not render them)
- [ ] Gold line separators, corner ornaments (✦), "SELENE ACADEMIA" watermark
- [ ] Fonts: Georgia/Calibri as fallbacks (Cormorant Garamond may not be installed)
- [ ] Speaker notes = narration text (for slide-stream compatibility)
- [ ] Test: generate PPTX for Lesson 0, open in LibreOffice and PowerPoint to verify

**Acceptance**: PPTX opens cleanly in both LibreOffice and PowerPoint with correct styling.

## Phase 3: Audio Narration
- [ ] Use official `elevenlabs` Python SDK (`from elevenlabs.client import ElevenLabs`)
- [ ] Model: `eleven_multilingual_v2`, language_code: `es`
- [ ] Settings from config/settings.json (stability 0.40, similarity 0.78, style 0.15, speed 0.95)
- [ ] Add SSML `<break>` tags between sentences for natural pacing
- [ ] Save per-slide MP3 files in `audio/slide_NNN.mp3`
- [ ] Get word-level timestamps from ElevenLabs API (enable `timestamps: true` in request)
- [ ] Resume: skip audio files that already exist and are >1KB
- [ ] Log: characters consumed, estimated cost per lesson
- [ ] Test: generate audio for 3 slides of Lesson 0, listen for natural Spanish

**Acceptance**: Audio plays naturally in Spanish, no English accent, proper pauses.

## Phase 4: Subtitles & Transcript
- [ ] Generate SRT from narration text + estimated timing (or ElevenLabs timestamps if available)
- [ ] SRT rules: max 42 chars/line, max 2 lines, sentence-aligned
- [ ] Generate `transcript.md` per lesson (full narration text + citations as footnotes)
- [ ] Test: load SRT in VLC with a test video, verify sync

**Acceptance**: SRT plays in sync with audio in VLC player.

## Phase 5: Video Assembly
**If using slide-stream**: 
- [ ] Convert script.json → slide-stream compatible Markdown
- [ ] Run slide-stream with custom config to produce final MP4

**If custom pipeline**:
- [ ] Export PPTX → PNG frames via LibreOffice headless (`libreoffice --headless --convert-to png`)
- [ ] For each slide: combine PNG + audio MP3 → segment MP4 using ffmpeg
- [ ] Concatenate all segments with crossfade transitions (0.5s)
- [ ] Burn SRT subtitles into video (or keep as sidecar file)
- [ ] Output: `{lesson_name}.mp4` in output directory

**Acceptance**: Final MP4 plays correctly, audio synced to slides, subtitles visible.

## Phase 6: Thumbnails & Batch
- [ ] Generate 1280x720 thumbnail per lesson with Pillow
- [ ] Design: dark bg, gold glow, module tag, lesson title, moon symbol, corner ornaments
- [ ] Batch mode: `--course brujula-interior` generates all 24 lessons sequentially
- [ ] Resume: skip lessons that already have complete output
- [ ] Summary report at end: total duration, total cost, files per lesson

**Acceptance**: `python pipeline.py --course brujula-interior` completes all 24 lessons without manual intervention.

## Phase 7: Quality & Polish
- [ ] A/B test 2-3 ElevenLabs voices with same script, pick best for Selene
- [ ] Review 3 random scripts for citation accuracy (Google Scholar the references)
- [ ] Add ambient music option (low volume, royalty-free, via ffmpeg audio mix)
- [ ] Final README with: usage, cost breakdown, voice selection guide, troubleshooting
- [ ] `.gitignore` for output/, audio/, *.mp3, *.mp4

---

## Mejoras aplicadas (por iniciativa propia)
_Documenta aquí cualquier mejora, cambio de arquitectura o decisión técnica que hayas tomado fuera del plan original. Formato: fecha, qué, por qué._

Ejemplo:
- 2026-03-18: Reemplazado slide-stream por pipeline custom porque no soportaba templates PPTX personalizados.

---

## Nota sobre autonomía
Este plan es una guía, no una camisa de fuerza. Si descubres una forma mejor de hacer algo — un paquete más adecuado, un workflow más eficiente, un bug en las instrucciones — tienes libertad total para cambiarlo. Solo:
1. Documéntalo arriba en "Mejoras aplicadas"
2. Haz commit con mensaje descriptivo
3. Respeta los hard constraints del CLAUDE.md (idioma, banned terms, citas, estética)
