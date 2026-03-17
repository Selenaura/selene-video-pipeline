# 🌙 Selene Video Pipeline

Genera lecciones completas en vídeo para los cursos de Selene Academia.

## Arquitectura

```
config/courses.json (24 lecciones)
        │
        ▼
┌──────────────────┐  Claude API   ┌────────────────┐
│ script_generator  │ ────────────► │  script.json   │
│ (guión + quiz)    │               │  (validated)   │
└──────────────────┘               └───────┬────────┘
                                           │
                              ┌────────────┼──────────────┐
                              ▼            ▼              ▼
                        slide_builder  elevenlabs SDK  srt_generator
                         (python-pptx)  (narración)    (subtítulos)
                              │            │              │
                              ▼            ▼              ▼
                         slides.pptx   audio/*.mp3    lesson.srt
                              │            │
                              └─────┬──────┘
                                    ▼
                              ffmpeg / slide-stream
                                    │
                         ┌──────────┼──────────┐
                         ▼          ▼          ▼
                    video.mp4   thumb.png  transcript.md
```

## Quick Start

```bash
pip install python-pptx elevenlabs Pillow requests
export ANTHROPIC_API_KEY=sk-ant-...
export ELEVENLABS_API_KEY=...

python pipeline.py --list                    # Ver lecciones
python pipeline.py --lesson 0 --steps script # Solo guión
python pipeline.py --lesson 0               # Pipeline completo
python pipeline.py --course brujula-interior # Curso entero
```

## Coste

| Componente | Por lección | Curso (24 lecciones) |
|---|---|---|
| Claude (guión) | ~€0.05 | €1.20 |
| ElevenLabs (audio) | ~€0.15 | €3.60 |
| **Total** | **~€0.20** | **€4.80** |

## Documentación

| Archivo | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude Code |
| `RESEARCH_BRIEFING.md` | Competencia, best practices, decisiones técnicas |
| `prompt_plan.md` | 7 fases de trabajo con criterios de aceptación |
| `config/settings.json` | Toda la configuración (con notas inline detalladas) |
| `config/courses.json` | 24 lecciones del Curso 1 definidas |
