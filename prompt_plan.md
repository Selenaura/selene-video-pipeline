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

## Phase 7: Quality & Polish [COMPLETED ✓]
- [x] A/B voice testing utility (`voice_tester.py`) — tests all 3 recommended voices with config settings
- [x] Citation accuracy review: verified Kabat-Zinn 1982 (General Hospital Psychiatry), Maguire 2000 (PNAS), Goyal 2014 (JAMA Internal Medicine) — all exact matches on author, year, journal, volume, pages
- [x] Ambient music mixing in `video_assembler.py` — auto-detects `ambient.mp3` in lesson dir or `assets/`, loops and mixes at 8% volume
- [x] Final README with: architecture, usage, cost breakdown, voice selection guide, output structure, troubleshooting
- [x] `.gitignore` for output/, audio/, *.mp3, *.mp4 (done in earlier phase)

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
- 2026-03-17: **Phase 7 — Voice tester utility.** `voice_tester.py` permite hacer A/B testing de las 3 voces recomendadas (Sarah, Lily, Jessica) con el mismo texto de prueba y settings idénticos. Genera MP3 samples para comparación auditiva.
- 2026-03-17: **Phase 7 — Ambient music auto-mix.** El video_assembler detecta automáticamente `ambient.mp3` (per-lesson o global en `assets/`), lo loopea si es más corto que el vídeo, y lo mezcla al 8% de volumen como música de fondo. Sin archivo, no hace nada.
- 2026-03-17: **Phase 7 — Citas verificadas contra Google Scholar.** Kabat-Zinn 1982 (GHP 4:33-47), Maguire 2000 (PNAS 97:4398-4403) confirmados con datos exactos. Las citas de los golden examples son reales y de alta calidad.

### Investigación open-source y mejoras (Phase 8)
- 2026-03-17: **Investigación de herramientas open-source.** Evaluación comparativa de: MovieLite vs moviepy vs ffmpeg directo (video), pptxtoimages vs Pillow (rendering), Chatterbox vs Kokoro vs ElevenLabs (TTS). Fuentes: GitHub, PyPI, papers, benchmarks.
- 2026-03-17: **ffmpeg directo reemplaza moviepy.** El video_assembler ahora usa ffmpeg subprocess para ensamblar segmentos: ~10x más rápido que moviepy (no carga frames en numpy). moviepy se mantiene como fallback si ffmpeg no está instalado. Concat demuxer + per-segment encoding → concat file → final MP4.
- 2026-03-17: **pptxtoimages integrado como rendering premium.** LibreOffice→PDF→PNG vía pptxtoimages para slides pixel-perfect. Fallback automático a Pillow si LibreOffice falla o no está disponible. En este entorno LibreOffice no puede convertir PPTX con imágenes embebidas; el Pillow fallback funciona correctamente.
- 2026-03-17: **Kokoro TTS (82M params, Apache) como alternativa gratuita.** `--tts kokoro` en pipeline.py activa Kokoro para narración española sin coste. 82M parámetros, corre en CPU, ~$0.06/h de audio. Ideal para desarrollo, pruebas, y producción low-cost. ElevenLabs sigue como default para calidad máxima.
- 2026-03-17: **Assets visuales integrados en slide_builder y thumbnail.** Backgrounds por tipo de slide (bg_title, bg_content, bg_science, bg_practice, bg_quote, bg_summary), moon_face.png en title slides, divider_star.png como separador, corner_ornaments.png como overlay, constellation_overlay.png al 12% opacidad en content/science. Fallback a diseño procedural si assets no existen.
- 2026-03-17: **Thumbnail mejorado con assets.** bg_title.png como fondo, moon_face.png redimensionado, divider_star.png, corner_ornaments.png — todo con fallback procedural.

---

## Nota sobre autonomía
Este plan es una guía, no una camisa de fuerza. Si descubres una forma mejor de hacer algo — un paquete más adecuado, un workflow más eficiente, un bug en las instrucciones — tienes libertad total para cambiarlo. Solo:
1. Documéntalo arriba en "Mejoras aplicadas"
2. Haz commit con mensaje descriptivo
3. Respeta los hard constraints del CLAUDE.md (idioma, banned terms, citas, estética)
