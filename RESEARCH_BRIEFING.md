# Selene Video Pipeline — Briefing de Investigación
> Última actualización: marzo 2026

## 1. DECISIÓN TÉCNICA: slide-stream

**Qué es**: Paquete open-source (`pip install slide-stream[all-ai]`) que convierte Markdown/PPTX → Video con ElevenLabs + Claude. v2.0.0, junio 2025, MIT, 23KB.

**Riesgo**: Proyecto pequeño (1 desarrollador, ~10 estrellas GitHub), Beta. Puede tener bugs o no soportar configuraciones complejas. No hay comunidad real.

**Estrategia**: Evaluar en Phase 0. Si funciona: usarlo para el ensamblaje (ahorra semanas de ffmpeg). Si no: pipeline custom con LibreOffice + ffmpeg. El script generator y las slides PPTX funcionan en ambos casos.

Lo que slide-stream NO tiene y debemos construir:
- Generación de guiones pedagógicos con citas peer-reviewed (Claude)
- Estética Quantum Ethereal en slides (python-pptx custom)
- Validación de calidad (banned terms, citation count)
- Quiz questions
- Thumbnails branded
- Batch por curso completo
- SSML pauses optimization

---

## 2. ELEVENLABS — ESTADO ACTUAL (Marzo 2026)

### Modelos disponibles
| Modelo | Idiomas | Chars/request | Coste | Latencia | Uso ideal |
|---|---|---|---|---|---|
| eleven_v3 | 74 | 5,000 | 1 crédito/char | Alta | Diálogos expresivos, audiobooks cortos |
| eleven_multilingual_v2 | 29 | 40,000 | 1 crédito/char | Media | **Educación, e-learning, narración larga** |
| eleven_flash_v2_5 | 32 | 40,000 | 0.5 créditos/char | 75ms | Real-time, chatbots |

**Decisión: eleven_multilingual_v2** para Selene porque:
- Recomendado específicamente para "corporate videos and e-learning materials" (docs oficiales)
- 8× más caracteres por request que v3 (40K vs 5K)
- Más estable en scripts largos
- v3 es alpha y "requires more prompt engineering" — no fiable para batch automatizado

### Settings óptimos para educación (fuente: docs oficiales + tests comunidad)
```json
{
  "stability": 0.40,       // 0.35-0.50: expresivo sin inestabilidad. <0.30 causa errores
  "similarity_boost": 0.78, // 0.75-0.80: fiel sin artefactos. >0.85 introduce ruido
  "style": 0.15,           // 0.10-0.30: emoción sutil. >0.50 falla en scripts largos
  "speed": 0.95,           // Ligeramente más lento = mejor comprensión
  "use_speaker_boost": true // Mejora claridad general
}
```

### SSML para pausas naturales
```
Entre slides:     <break time="1.2s"/>
Tras pregunta:    <break time="0.8s"/>
Antes de cita:    <break time="0.5s"/>
Pausa narrativa:  ... (ellipsis — ElevenLabs lo interpreta como pausa corta)
Pausa media:      — (em-dash)
```
**NOTA**: SSML `<break>` funciona en multilingual_v2 pero NO en eleven_v3.

### Voice Design (si las voces recomendadas no convencen)
Formato oficial de ElevenLabs para Voice Design:
```
[Idioma y dialecto]. [Género], [edad]. [Calidad]. 
Persona: [descripción del personaje]. 
Emotion: [emociones primarias]. 
[Descripción detallada del timbre, ritmo, entonación].
```

Prompt optimizado para Selene:
```
Native Spanish speaker from Spain, specifically Castilian accent without 
Latin American features. Female, age 32. High audio quality. 
Persona: a university professor who also practices yoga and meditation. 
Emotion: warm, curious, gently passionate. 
Her voice has a smooth, natural timbre with gentle intonation and forward 
proximity. She speaks at a relaxed pace with clear emphasis on key concepts, 
projecting warmth and intellectual curiosity. Speaks as if sharing fascinating 
discoveries with a close friend over tea.
```

### language_code
SIEMPRE pasar `language_code: "es"` en la API. Sin esto, las voces "default" (entrenadas en inglés) pronuncian números y abreviaturas con fonética inglesa. Ej: "11" como "eleven" en vez de "once".

---

## 3. COMPETENCIA EN FORMACIÓN ESPIRITUAL/TAROT

### Inglés (precio alto, sin español)
| Plataforma | Precio | Formato | Diferenciador |
|---|---|---|---|
| Biddy Tarot | $997 certificación | Vídeo + comunidad | Reconocimiento industria |
| Tarot Readers Academy | $37-287/curso | Vídeo, lifetime access | 11 cursos, comunidad |
| The Magickal Path | $97-497 | Vídeo + 1:1 practicum | Diploma con prácticas |
| Labyrinthos | App gratuita + baraja | App + workbook | Diseño premium, app gamificada |
| Upskillist | $39.99/mes | Vídeo + AI tools | Certificación global |
| Centre of Excellence | £29-127 | Vídeo self-paced | Diploma CPD acreditado |

### Español (débil)
| Plataforma | Precio | Problema |
|---|---|---|
| InfoBrujas (Yolanda Hermes) | €600-840 | Web anticuada, caro |
| Escuelas presenciales | €300-600 | No escalable |
| Udemy tarot español | €12-20 | Calidad baja, sin marca |

### Ventaja competitiva de Selene
- Único en español con base científica peer-reviewed
- 70-85% más barato que competencia seria (€0-59.99 vs €300-997)
- IA integrada en práctica (carta natal, tarot, quirología)
- Certificación digital verificable
- Sin cara del instructor → voz IA premium (escalable, consistente)

---

## 4. BEST PRACTICES VÍDEO EDUCATIVO (investigación 2025-2026)

### Duración
- **Engagement cae drásticamente después de 10 minutos** (múltiples estudios)
- Sweet spot: **8-15 minutos** por lección
- Segmentar internamente en bloques de 3-5 min con transiciones visuales

### Estructura probada (por lección)
1. **Hook** (10-15s): pregunta provocadora o dato sorprendente
2. **Contexto** (30-60s): por qué importa, conexión personal
3. **Contenido** (3-5 min): máx 3 conceptos por vídeo
4. **Evidencia** (30-60s): cita científica + visual del hallazgo
5. **Práctica** (1-2 min): ejercicio que pueden hacer ahora
6. **Resumen** (30s): exactamente 3 takeaways
7. **CTA** (15s): siguiente lección o acción

### Producción
- **Audio > vídeo**: mala calidad de audio arruina credibilidad (prioridad #1)
- **Subtítulos obligatorios**: 85% de vídeos en móvil sin sonido
- **Consistencia visual**: misma plantilla, colores, posición de elementos
- **Storytelling > lecturing**: narrar historias, no dar clases magistrales
- **97% dice vídeo mejora retención** (Synthesia 2025)
- **30% más engagement** con vídeo vs PPT estáticos (BSH case study)
- Editar en MOV/AVI, exportar a **MP4 H.264** para compatibilidad

### Gamificación
- Quiz después de cada módulo (3 lecciones + 1 quiz)
- Progress bar visible en la plataforma
- XP/puntos por lección completada
- Certificado como "premio final"
- Streak counter (días consecutivos)

---

## 5. COSTES ESTIMADOS

| Concepto | Por lección | Curso 1 (24) | 10 cursos |
|---|---|---|---|
| Claude API (guión) | ~€0.05 | ~€1.20 | ~€12 |
| ElevenLabs (10 min audio) | ~€0.15 | ~€3.60 | ~€36 |
| **Total** | **~€0.20** | **~€4.80** | **~€48** |

Comparativa: producción profesional externa = €5,000-15,000 por curso.

### ElevenLabs plan necesario
- Free: 10,000 chars/mes (≈1 lección)
- Starter: $5/mes, 30,000 chars (≈3 lecciones)
- Creator: $22/mes, 100,000 chars (≈10 lecciones)
- **Recomendado**: Creator por 1 mes para producir el Curso 1 completo (24 lecciones × ~4,000 chars = ~96,000 chars)
