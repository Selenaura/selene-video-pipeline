# Selene Video Pipeline

## Why
Automated video lesson production for Selene Academia. Target: 24 lessons/course, ~€5 total cost, studio quality. Replaces €5,000-15,000 professional production.

## What
Python pipeline: Claude generates pedagogical scripts → python-pptx renders Quantum Ethereal slides → ElevenLabs narrates in Spanish → ffmpeg assembles final MP4 + SRT subtitles + thumbnails.

## Architecture decision: slide-stream vs custom

`slide-stream` (pip install slide-stream[all-ai]) is an open-source package that does Markdown → Video with ElevenLabs + Claude. Version 2.0.0, released June 2025, MIT license.

**Evaluate it first (Phase 0).** If it works well:
- Use it as the video assembly layer (Markdown → Video)
- Build our own script generator on top (Claude → Markdown)
- Build our own slide template (Quantum Ethereal PPTX)

**If slide-stream fails or is too limited** (it's Beta, small project, 23KB):
- Fall back to custom pipeline: python-pptx → LibreOffice PNG export → ffmpeg assembly
- The script generator and slide template work either way

## How
```bash
pip install python-pptx elevenlabs Pillow requests
pip install slide-stream[all-ai]  # Optional — evaluate first
export ANTHROPIC_API_KEY=sk-ant-...
export ELEVENLABS_API_KEY=...

python pipeline.py --list                    # See available lessons
python pipeline.py --lesson 0 --steps script # Generate script only
python pipeline.py --lesson 0               # Full pipeline
python pipeline.py --course brujula-interior # Entire course
```

## Key context
- Read RESEARCH_BRIEFING.md for competitive analysis and technical decisions
- Read config/settings.json — has detailed inline notes for EVERY setting
- Read config/courses.json for the 24 lessons of Course 1
- Brand: SelenaUra. Design: Quantum Ethereal (dark #0A0A0F, gold #C9A84C, Cormorant Garamond + Outfit)
- Voice: warm Spanish female, 30-35, knowledgeable but intimate

## Hard constraints (NEVER violate)
1. ALL content in Spanish
2. NEVER mention "IA", "AI", "inteligencia artificial", "algoritmo", "chatbot", "modelo de lenguaje"
3. EVERY lesson must cite ≥2 real peer-reviewed studies (author, year, journal)
4. NEVER make pseudoscientific claims without citation
5. Slides: max 4 bullets, max 12 words per bullet
6. Narration tone: conversational ("amiga brillante"), not academic

## ElevenLabs guidance (from official docs March 2026)
- **Primary model**: `eleven_multilingual_v2` — best for education, stable, 40K char/request
- **Alternative**: `eleven_v3` — more expressive but 5K char limit, alpha stage
- **Language**: always pass `language_code: "es"` for proper Spanish pronunciation
- **Settings**: stability 0.40, similarity 0.78, style 0.15, speed 0.95
- **SSML pauses**: `<break time="1.2s"/>` between slides; `…` for natural pauses
- **Speaker boost**: `use_speaker_boost: true` for clarity
- **Voice selection > settings**: pick a voice natively trained in Spanish
- Voice Design prompt and recommended voices in config/settings.json

## Video structure (from educational research)
1. **Hook** (10-15s): surprising question or data point
2. **Context** (30-60s): why this matters, personal connection
3. **Content** (3-5 min): max 3 concepts per video
4. **Evidence** (30-60s): citation + visual
5. **Practice** (1-2 min): actionable exercise
6. **Summary** (30s): exactly 3 key takeaways
7. **CTA** (15s): next lesson

Research: engagement drops after 10 min. 85% watch mobile without sound → subtitles mandatory. Audio quality > video quality. Storytelling > lecturing.

## Tu rol: colaborador, no ejecutor

Los archivos de este repo son un punto de partida basado en investigación, NO un spec cerrado. Tienes autonomía para:

1. **Mejorar cualquier cosa que veas mejorable** — si encuentras un enfoque mejor, impleméntalo. Solo documenta qué cambiaste y por qué en los commits.
2. **Buscar en la red** si tienes dudas técnicas (ElevenLabs API, ffmpeg flags, python-pptx tricks). La documentación oficial siempre gana sobre lo que diga este archivo.
3. **Proponer cambios de arquitectura** si descubres que slide-stream no sirve, o que hay un paquete mejor, o que el flujo debería ser diferente.
4. **Refactorizar** si el código crece y necesita mejor estructura (módulos, clases, tests).
5. **Añadir features** que tengan sentido aunque no estén en el plan: logs, progress bars, dry-run mode, cost estimator, etc.
6. **Cuestionar las decisiones** del briefing. Si crees que eleven_v3 es mejor que multilingual_v2 después de probarlo, cámbialo y documenta.

Lo único que NO debes cambiar sin preguntar:
- Los hard constraints (idioma, banned terms, citas obligatorias, estética de marca)
- La estructura de courses.json (las 24 lecciones ya están validadas)

Cuando termines cada Phase, además de marcarla como completada, añade una sección `## Mejoras aplicadas` en prompt_plan.md con lo que hayas cambiado por iniciativa propia.

## Quality checklist
- [ ] ≥2 peer-reviewed citations with (author, year, journal)
- [ ] Zero banned terms in any text
- [ ] 20-150 words narration per slide
- [ ] ≤4 bullets/slide, ≤12 words/bullet
- [ ] Has hook + content + summary slide types
- [ ] SRT generated, sentence-synced
- [ ] Thumbnail 1280x720, Quantum Ethereal
- [ ] Spanish narration without English accent bleed
