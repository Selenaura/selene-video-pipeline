# Phase 0: Evaluación de slide-stream v2.0.0

> Fecha: 2026-03-17
> Decisión: **NO USAR slide-stream como capa de ensamblaje. Pipeline custom.**

## Resumen

slide-stream (MIT, v2.0.0, ~1,550 líneas) produce un vídeo funcional de 51s/1080p a partir de Markdown con gTTS. Sin embargo, tiene limitaciones críticas que lo hacen inviable como componente principal del pipeline de Selene.

## Test realizado

```bash
pip install slide-stream[all-ai]  # OK, v2.0.0
slide-stream providers             # OK: text + gtts disponibles
slide-stream create test.md test.mp4 --config slidestream_test.yaml
# Resultado: MP4 de 51s, 1920x1080, 24fps, ~985KB
```

## Análisis de capacidades vs. requisitos

| Requisito Selene | slide-stream | Veredicto |
|---|---|---|
| Template PPTX Quantum Ethereal | ❌ Solo extrae texto, ignora diseño | **FALLO CRÍTICO** |
| ElevenLabs: model, stability, similarity, style, speed, boost, lang_code | ❌ Hardcoded `eleven_monolingual_v1`, sin settings | **FALLO CRÍTICO** |
| SSML `<break>` para pausas naturales | ❌ Texto se pasa verbatim | **FALLO** |
| Generación de SRT | ❌ No implementado | **FALLO** |
| language_code: "es" en ElevenLabs | ❌ No se pasa | **FALLO** |
| Estructura pedagógica (hook → CTA) | ❌ Sin validación ni enforcement | **FALLO** |
| Enforcement de hard constraints (banned terms, citas) | ❌ Prompt LLM genérico | **FALLO** |
| Control de timing por slide | ⚠️ Solo audio + padding fijo | Limitado |
| Transiciones/crossfade entre slides | ❌ Concatenación simple | Limitado |
| Thumbnails 1280x720 branded | ❌ No implementado | **FALLO** |
| Batch por curso (24 lecciones) | ❌ Solo un archivo a la vez | **FALLO** |

## Código ElevenLabs de slide-stream (problema central)

```python
# Lo que hace slide-stream (providers/tts.py):
audio = generate(text=text, voice="Rachel", model="eleven_monolingual_v1")

# Lo que necesita Selene:
audio = client.text_to_speech.convert(
    text=text_with_ssml,
    voice_id="EXAVITQu4vr4xnSDxMaL",
    model_id="eleven_multilingual_v2",
    voice_settings=VoiceSettings(
        stability=0.40,
        similarity_boost=0.78,
        style=0.15,
        use_speaker_boost=True
    ),
    language_code="es"
)
```

## Qué SÍ funciona bien en slide-stream

- ✅ Parsing de Markdown → estructura de slides (simple pero funcional)
- ✅ Abstracción de providers de imagen (DALL-E, Pexels, Unsplash, text)
- ✅ Ensamblaje MoviePy (imagen + audio → fragmento → concatenación)
- ✅ CLI limpio con Typer

## Decisión

**Pipeline custom** usando componentes directos:
1. **python-pptx** → slides con estética Quantum Ethereal
2. **LibreOffice headless** → export PPTX → PNG
3. **elevenlabs SDK** → narración con settings completos en español
4. **moviepy/ffmpeg** → ensamblaje con transiciones
5. **Pillow** → thumbnails branded

slide-stream se descarta porque requeriría parchear 5 de sus 6 componentes internos. Es más eficiente construir directamente sobre las librerías subyacentes (que ya están instaladas como dependencias de slide-stream).

## Ventajas del pipeline custom

- Control total sobre ElevenLabs (modelo, settings, SSML, language_code)
- Template PPTX con la identidad visual de Selene
- Generación de SRT sincronizado
- Validación de calidad integrada (banned terms, citas, estructura)
- Batch processing con resume
- Estimación de costes por lección
