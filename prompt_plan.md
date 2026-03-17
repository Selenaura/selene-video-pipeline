# Video Pipeline — Task Plan

## Phase 0: Evaluate slide-stream [COMPLETED ✓]
- [x] `pip install slide-stream[all-ai]` and run `slide-stream providers`
- [x] Create a test Markdown file with 3 slides and Spanish narration text
- [x] Run `slide-stream create test.md test.mp4` with gTTS (sin API keys de ElevenLabs)
- [x] **DECISION**: slide-stream NO produce output utilizable para Selene → **pipeline custom**
- [x] Document decision and reasoning in `docs/phase0_slide_stream_evaluation.md`

**Resultado**: Video de 51s generado correctamente (1920x1080, 24fps), pero slide-stream tiene limitaciones críticas:
- Hardcoded `eleven_monolingual_v1` (necesitamos `eleven_multilingual_v2` con settings custom)
- No soporta templates PPTX (solo extrae texto, ignora diseño Quantum Ethereal)
- No genera SRT, no pasa SSML, no pasa `language_code: "es"`
- Sin validación pedagógica ni enforcement de hard constraints

**Decisión**: Pipeline custom con python-pptx + elevenlabs SDK + moviepy/ffmpeg.

## Phase 1: Script Generator [COMPLETED ✓]
- [x] Build `script_generator.py` with Claude API call
- [x] System prompt enforces: Spanish, no banned terms, ≥2 citations, conversational tone
- [x] Input: lesson object from config/courses.json
- [x] Output: `script.json` with structured slides (hook → content → science → practice → summary → CTA)
- [x] Each slide: type, title, bullets (max 4, max 12 words each), narration (20-150 words), citation
- [x] Validation function: checks banned terms, citation count, narration length, slide count (6-16)
- [x] 3 quiz questions per lesson saved in script.json
- [x] Test: generate script for Lesson 0, verify it passes all quality checks in settings.json
- [x] `--dry-run` mode for testing without API keys

**Resultado**: `python pipeline.py --lesson 0 --steps script --dry-run` produce script.json válido con 0 errores.
- `script_generator.py`: system prompt + user prompt + Claude API call + retry logic + dry-run sample
- `validator.py`: banned terms, citation count, narration length, bullets, slide types, quiz count
- `pipeline.py`: CLI with --list, --lesson N, --course ID, --steps, --dry-run, --validate

## Phase 2: PPTX Template (Quantum Ethereal) [COMPLETED ✓]
- [x] Programmatic slide builder in `slide_builder.py` using python-pptx
- [x] Slide types: hook (violet ✧), content (gold ◆), science (blue 🔬), practice (teal 🧘), summary (gold ✦), cta (gold)
- [x] Background: solid #0A0A0F
- [x] Gold line separators, corner ornaments (✦), "SELENE ACADEMIA" watermark
- [x] Fonts: Georgia/Calibri (safe fallbacks)
- [x] Speaker notes = narration text
- [x] Slide counter (N/total) top-right, type badge top-left
- [x] Citations rendered at bottom with 📚 icon when present
- [x] Integrated into pipeline: `--steps script,slides`
- [x] Test: generated 8-slide PPTX for Lesson 0 with correct structure

**Resultado**: `python pipeline.py --lesson 0 --steps script,slides --dry-run` produce slides.pptx válido con 8 slides, colores Quantum Ethereal, narración en speaker notes.

## Phase 3: Audio Narration [COMPLETED ✓]
- [x] Use official `elevenlabs` Python SDK (`from elevenlabs.client import ElevenLabs`)
- [x] Model: `eleven_multilingual_v2`, language_code: `es`
- [x] Settings from config/settings.json (stability 0.40, similarity 0.78, style 0.15, speed 0.95)
- [x] Add SSML `<break>` tags between slides for natural pacing
- [x] Save per-slide MP3 files in `audio/slide_NNN.mp3`
- [x] Resume: skip audio files that already exist and are >1KB
- [x] Log: characters consumed, estimated cost per lesson
- [x] Audio manifest (manifest.json) with per-slide durations
- [x] Dry-run mode with silent MP3 placeholders

**Resultado**: `audio_narrator.py` generates per-slide MP3 + manifest.json. Lesson 0: 8 slides, 2999 chars, ~3.1 min estimated.
**Nota**: word-level timestamps pendientes — requiere `with_timestamps` que depende de la versión del SDK. Se resolverá al integrar con subtítulos (Phase 4).

## Phase 4: Subtitles & Transcript [COMPLETED ✓]
- [x] Generate SRT from narration text + audio manifest timing
- [x] SRT rules: max 42 chars/line, max 2 lines, sentence-aligned
- [x] SSML tags stripped from subtitle text
- [x] Proportional timing by word count per sentence
- [x] Generate `transcript.md` per lesson (full narration + bibliography)
- [x] Integrated into pipeline as 'subtitles' step

**Resultado**: Lesson 0 genera 27 cues SRT sentence-aligned + transcript.md con referencias.

## Phase 5: Video Assembly [COMPLETED ✓]
**Custom pipeline** (slide-stream descartado en Phase 0):
- [x] Export PPTX → PNG frames via Pillow (LibreOffice headless only exports first slide as PNG)
- [x] For each slide: combine PNG + audio MP3 → segment using moviepy ImageClip + AudioFileClip
- [x] Concatenate all segments with `concatenate_videoclips(method="compose")`
- [x] SRT subtitles as sidecar file (generated in Phase 4)
- [x] Output: `lesson.mp4` in lesson output directory
- [x] Duration from slide `duration_seconds` field, manifest, or word-count estimation

**Resultado**: `video_assembler.py` renders PPTX→PNG via Pillow, assembles with moviepy. Supports dry-run mode (skips audio attachment). Codec: libx264, preset medium, AAC audio.

## Phase 6: Thumbnails & Batch [COMPLETED ✓]
- [x] Generate 1280x720 thumbnail per lesson with Pillow
- [x] Design: dark bg, gold glow circle, module tag, lesson title (word-wrapped), moon symbol (☽), corner ornaments (✦), SELENE ACADEMIA watermark, gold separator
- [x] Batch mode: `--course brujula-interior` generates all lessons sequentially
- [x] Resume: skip lessons with valid script.json in course batch mode
- [x] Summary report: completed/skipped/failed counts

**Resultado**: `thumbnail_generator.py` genera PNG 1280x720 Quantum Ethereal. Pipeline completo integrado: script→slides→audio→subtitles→video→thumbnail. Dry-run testado exitosamente.

## Phase 7: Quality & Polish
- [ ] A/B test 2-3 ElevenLabs voices with same script, pick best for Selene
- [ ] Review 3 random scripts for citation accuracy (Google Scholar the references)
- [ ] Add ambient music option (low volume, royalty-free, via ffmpeg audio mix)
- [ ] Final README with: usage, cost breakdown, voice selection guide, troubleshooting
- [ ] `.gitignore` for output/, audio/, *.mp3, *.mp4

---

## Mejoras aplicadas (por iniciativa propia)
_Documenta aquí cualquier mejora, cambio de arquitectura o decisión técnica que hayas tomado fuera del plan original. Formato: fecha, qué, por qué._

- 2026-03-17: **Phase 0 — slide-stream descartado, pipeline custom confirmado.** Análisis exhaustivo del código fuente de slide-stream (1,550 líneas, 11 archivos). El paquete produce vídeo funcional pero tiene ElevenLabs hardcoded a `eleven_monolingual_v1`, no soporta templates PPTX, no genera SRT, no pasa SSML ni `language_code`. Requeriría parchear 5 de 6 componentes internos. Más eficiente construir sobre las librerías subyacentes (python-pptx, elevenlabs SDK, moviepy) que ya vienen instaladas como dependencias. Evaluación detallada en `docs/phase0_slide_stream_evaluation.md`.
- 2026-03-17: **Creado directorio `docs/` para documentación técnica.** Separa las evaluaciones y decisiones de arquitectura del código y la configuración. Primer documento: evaluación de slide-stream.
- 2026-03-17: **Eliminada referencia a slide-stream en Phase 2** (speaker notes "for slide-stream compatibility" ya no aplica, pero se mantienen speaker notes por utilidad general).
- 2026-03-17: **Añadido `--dry-run` mode al pipeline.** Permite testar toda la cadena sin API keys. Genera un script de ejemplo realista para Lesson 0 con citas reales (Lazar 2005, Davidson 2003, Hölzel 2011) que pasa todas las validaciones. Útil para CI/CD y desarrollo offline.
- 2026-03-17: **Slide type "evidence" renombrado a "science"** en la estructura real para mayor claridad. El plan original decía "evidence" pero "science" describe mejor el contenido (citas + visuales de hallazgos).
- 2026-03-17: **Phase 5 — Pillow rendering en lugar de LibreOffice.** LibreOffice headless `--convert-to png` solo exporta la primera slide del PPTX. Se implementó renderizado con Pillow: extrae textos de cada shape de python-pptx y los dibuja sobre fondo oscuro. No es pixel-perfect respecto al PPTX pero es funcional y no requiere dependencias externas.
- 2026-03-17: **Phase 5 — moviepy en lugar de ffmpeg directo.** moviepy (ImageClip + AudioFileClip + concatenate_videoclips) simplifica la lógica de ensamblaje vs. ffmpeg con concat demuxer. Produce libx264/AAC MP4.
- 2026-03-17: **Adaptación al formato golden examples.** Tras recibir los scripts M01 del usuario, se adaptaron validator.py, script_generator.py y slide_builder.py para soportar el formato golden (lesson_id, citations_used, citations_bibliography, meta block, SSML inline, duration_seconds por slide, slide types title/quote). El script_generator usa M01_L01 como few-shot example para Claude.

---

## Nota sobre autonomía
Este plan es una guía, no una camisa de fuerza. Si descubres una forma mejor de hacer algo — un paquete más adecuado, un workflow más eficiente, un bug en las instrucciones — tienes libertad total para cambiarlo. Solo:
1. Documéntalo arriba en "Mejoras aplicadas"
2. Haz commit con mensaje descriptivo
3. Respeta los hard constraints del CLAUDE.md (idioma, banned terms, citas, estética)
