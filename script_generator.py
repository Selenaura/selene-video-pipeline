"""Generate pedagogical video scripts using Claude API."""

import json
import os
from pathlib import Path

from validator import SETTINGS, validate_script

SYSTEM_PROMPT = """\
Eres la guionista de Selene Academia, una plataforma de formación en español sobre consciencia, \
espiritualidad basada en evidencia y autoconocimiento. Tu marca personal: "amiga brillante" — \
cálida, cercana, inteligente, conversacional. Nunca clínica ni fantasiosa.

## REGLAS ABSOLUTAS (nunca violar)
1. TODO el contenido en español de España (tú/vosotros, no usted/ustedes).
2. NUNCA mencionar: "inteligencia artificial", "IA", "AI", "algoritmo", "machine learning", \
"chatbot", "bot", "modelo de lenguaje", "LLM".
3. CADA lección DEBE citar al menos 2 estudios peer-reviewed REALES con (autor, año, revista). \
NO inventes citas. Usa solo estudios que existan realmente.
4. NUNCA hacer afirmaciones pseudocientíficas sin respaldo de cita.
5. Cada slide: máximo 4 bullets, máximo 12 palabras por bullet.
6. Narración por slide: entre 20 y 150 palabras.
7. Tono: conversacional, como si hablaras con una amiga curiosa. Storytelling > lectura.

## ESTRUCTURA DE LA LECCIÓN (seguir siempre)
1. **hook** (1 slide): Pregunta provocadora o dato sorprendente. Engancha en 10-15 segundos.
2. **content** (2-4 slides): Desarrollo del tema. Máximo 3 conceptos por lección.
3. **science** (1-2 slides): Evidencia científica con citas. Visual del hallazgo.
4. **practice** (1 slide): Ejercicio práctico que puedan hacer ahora mismo.
5. **summary** (1 slide): Exactamente 3 takeaways clave.
6. **cta** (1 slide): Siguiente lección o acción concreta.

## FORMATO DE SALIDA (JSON estricto)
Responde SOLO con JSON válido, sin markdown ni explicaciones:
{
  "lesson_title": "...",
  "lesson_id": 0,
  "total_slides": N,
  "slides": [
    {
      "type": "hook|content|science|practice|summary|cta",
      "title": "Título corto del slide (max 8 palabras)",
      "bullets": ["Bullet 1 (max 12 palabras)", "..."],
      "narration": "Texto completo de narración (20-150 palabras). Conversacional, cálido.",
      "citation": "Autor (año). Título. Revista. DOI si disponible." // null si no aplica
    }
  ],
  "quiz": [
    {
      "question": "Pregunta en español",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": "A",
      "explanation": "Por qué esta es la respuesta correcta (1-2 frases)"
    }
  ],
  "citations_bibliography": [
    "Autor (año). Título completo del estudio. Revista, volumen(número), páginas. DOI."
  ]
}

## GUÍA DE NARRACIÓN
- Empieza cada hook con una pregunta directa: "¿Sabías que...?", "¿Te has preguntado...?"
- Usa "…" (puntos suspensivos) para pausas narrativas naturales
- Usa "—" (em-dash) para pausas medias
- El summary siempre dice: "Vamos a repasar los tres puntos clave de hoy:"
- El CTA menciona la siguiente lección por nombre
- Incluye conexiones personales: "Piensa en la última vez que..."
"""


def build_user_prompt(lesson: dict, lesson_index: int, course: dict, next_lesson_title: str | None) -> str:
    """Build the user prompt for a specific lesson."""
    prompt = f"""Genera el guión completo para la lección {lesson_index} del curso "{course['title']}".

## Datos de la lección
- **Título**: {lesson['title']}
- **Módulo**: {lesson['module']} — {course['modules'][str(lesson['module'])]}
- **Descripción y contenido clave**: {lesson['description']}
- **Duración objetivo**: {lesson['duration_target']} minutos
- **Nivel del curso**: {course['level']}
- **Público**: {course['target_audience']}
"""
    if next_lesson_title:
        prompt += f"\n- **Siguiente lección** (para el CTA): {next_lesson_title}\n"
    else:
        prompt += "\n- **Siguiente paso** (para el CTA): Completar la evaluación final del curso.\n"

    prompt += """
## Recordatorios
- Mínimo 2 citas peer-reviewed REALES (de las mencionadas en la descripción u otras relevantes)
- Entre 6 y 16 slides total
- Responde SOLO con JSON válido
"""
    return prompt


def generate_script(lesson: dict, lesson_index: int, course: dict,
                    next_lesson_title: str | None = None,
                    max_retries: int = 2, dry_run: bool = False) -> dict:
    """Generate and validate a lesson script using Claude API."""
    if dry_run:
        print("  🧪 Dry-run mode: loading sample script")
        return _load_or_create_sample(lesson, lesson_index, next_lesson_title)

    import anthropic
    client = anthropic.Anthropic()
    model = SETTINGS["api"]["claude_model"]
    max_tokens = SETTINGS["api"]["claude_max_tokens"]

    user_prompt = build_user_prompt(lesson, lesson_index, course, next_lesson_title)

    for attempt in range(max_retries + 1):
        print(f"  Generating script (attempt {attempt + 1})...")
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].strip()

        try:
            script = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON parse error: {e}")
            if attempt < max_retries:
                user_prompt += "\n\nIMPORTANTE: Tu respuesta anterior no era JSON válido. Responde SOLO con JSON."
                continue
            raise ValueError(f"Failed to get valid JSON after {max_retries + 1} attempts") from e

        # Validate
        errors = validate_script(script)
        if not errors:
            print(f"  ✅ Script valid ({len(script['slides'])} slides, "
                  f"{len(script.get('quiz', []))} quiz questions)")
            # Add metadata
            script["lesson_id"] = lesson_index
            script["_generation"] = {
                "model": model,
                "attempt": attempt + 1,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return script

        print(f"  ⚠ {len(errors)} validation errors:")
        for e in errors:
            print(f"    - {e}")

        if attempt < max_retries:
            error_feedback = "\n".join(f"- {e}" for e in errors)
            user_prompt += f"""

Tu respuesta anterior tenía estos errores de validación:
{error_feedback}

Corrígelos y genera el JSON de nuevo. Responde SOLO con JSON válido."""

    # Return last attempt even with errors, caller can decide
    script["_validation_errors"] = errors
    script["lesson_id"] = lesson_index
    return script


def _load_or_create_sample(lesson: dict, lesson_index: int,
                           next_lesson_title: str | None) -> dict:
    """Load sample script from samples/ or generate a template for dry-run testing."""
    sample_path = Path(__file__).parent / "samples" / f"lesson_{lesson_index:02d}_script.json"
    if sample_path.exists():
        with open(sample_path) as f:
            return json.load(f)

    # Generate a minimal valid template
    next_title = next_lesson_title or "la siguiente lección"
    return {
        "lesson_title": lesson["title"],
        "lesson_id": lesson_index,
        "total_slides": 8,
        "slides": [
            {
                "type": "hook",
                "title": "¿Sabías esto sobre tu mente?",
                "bullets": [
                    "Tu cerebro cambia con cada experiencia",
                    "La ciencia lo demuestra desde 2005"
                ],
                "narration": f"¿Sabías que tu cerebro es capaz de transformarse físicamente con la práctica? No es una metáfora… es neuroplasticidad. Y hoy vamos a explorar qué significa esto para ti en el contexto de {lesson['title'].lower()}.",
                "citation": None
            },
            {
                "type": "content",
                "title": "Consciencia: más allá de la creencia",
                "bullets": [
                    "No es fe ciega, es atención entrenada",
                    "Diferencia entre creer y practicar",
                    "La experiencia directa como maestra"
                ],
                "narration": "Cuando hablamos de espiritualidad consciente, no estamos hablando de creer en algo sin evidencia. Estamos hablando de entrenar tu atención — de observar tu experiencia interna con la misma curiosidad con la que un científico observa sus datos. La diferencia entre creer y practicar es enorme, y es justo lo que vamos a explorar hoy.",
                "citation": None
            },
            {
                "type": "content",
                "title": "Tu cerebro: una antena adaptable",
                "bullets": [
                    "Neuroplasticidad: el cerebro cambia siempre",
                    "Nuevas conexiones se forman con práctica",
                    "No importa tu edad para empezar"
                ],
                "narration": "Tu cerebro no es una estructura fija — es más bien como una antena que se reconfigura constantemente. Cada vez que aprendes algo nuevo, que meditas, que prestas atención de forma deliberada… estás literalmente cambiando la estructura física de tu cerebro. Y lo más fascinante es que esto funciona a cualquier edad.",
                "citation": None
            },
            {
                "type": "science",
                "title": "La evidencia: meditación y cerebro",
                "bullets": [
                    "Lazar (2005): meditación aumenta grosor cortical",
                    "Davidson (2003): activación prefrontal izquierda",
                    "Cambios medibles en solo 8 semanas"
                ],
                "narration": "En 2005, la neurocientífica Sara Lazar y su equipo en Harvard descubrieron algo revolucionario: las personas que meditaban regularmente tenían mayor grosor en la corteza cerebral — la parte del cerebro responsable de la atención y el procesamiento sensorial. Y en 2003, Richard Davidson demostró que la meditación activa la corteza prefrontal izquierda, asociada con emociones positivas y bienestar.",
                "citation": "Lazar, S. et al. (2005). Meditation experience is associated with increased cortical thickness. Neuroreport, 16(17), 1893-1897."
            },
            {
                "type": "science",
                "title": "Más evidencia: el poder del entrenamiento",
                "bullets": [
                    "Hölzel (2011): reducción del volumen amigdalar",
                    "La amígdala gestiona el miedo y el estrés",
                    "Menos reactividad, más calma interior"
                ],
                "narration": "Britta Hölzel y su equipo publicaron en Psychiatry Research en 2011 un hallazgo impresionante: después de solo ocho semanas de práctica de mindfulness, los participantes mostraron una reducción significativa en el volumen de la amígdala — esa pequeña estructura cerebral que gestiona nuestras respuestas de miedo y estrés. Menos amígdala hiperactiva significa más calma, más claridad, más capacidad de respuesta consciente.",
                "citation": "Hölzel, B. et al. (2011). Mindfulness practice leads to increases in regional brain gray matter density. Psychiatry Research: Neuroimaging, 191(1), 36-43."
            },
            {
                "type": "practice",
                "title": "Tu primer ejercicio de atención",
                "bullets": [
                    "Cierra los ojos durante 60 segundos",
                    "Observa tu respiración sin cambiarla",
                    "Nota pensamientos sin juzgarlos",
                    "Al terminar, observa cómo te sientes"
                ],
                "narration": "Ahora vamos a hacer algo muy sencillo pero poderoso. Quiero que cierres los ojos — sí, ahora mismo — y durante sesenta segundos simplemente observes tu respiración. No intentes cambiarla, no intentes respirar más profundo ni más lento. Solo observa. Si aparecen pensamientos — y aparecerán — simplemente nota que están ahí y vuelve tu atención a la respiración. Esto es atención entrenada en su forma más pura.",
                "citation": None
            },
            {
                "type": "summary",
                "title": "Tres claves de hoy",
                "bullets": [
                    "Espiritualidad consciente es atención entrenada",
                    "Tu cerebro cambia con la práctica meditativa",
                    "La ciencia respalda estos cambios desde 2003"
                ],
                "narration": "Vamos a repasar los tres puntos clave de hoy: Primero, la espiritualidad consciente no es creer a ciegas — es entrenar tu atención de forma deliberada. Segundo, tu cerebro tiene la capacidad de cambiar físicamente con la práctica meditativa, gracias a la neuroplasticidad. Y tercero, esto no es especulación: la ciencia lo respalda con estudios rigurosos desde hace más de veinte años.",
                "citation": None
            },
            {
                "type": "cta",
                "title": "Tu siguiente paso",
                "bullets": [
                    f"Próxima lección: {next_title}",
                    "Practica el ejercicio de atención esta semana"
                ],
                "narration": f"En la próxima lección — {next_title} — vamos a profundizar en cómo pasar de la teoría a la práctica diaria. Mientras tanto, te propongo un reto: practica el ejercicio de atención que acabamos de hacer al menos una vez al día durante esta semana. Solo sesenta segundos. Tu cerebro te lo agradecerá.",
                "citation": None
            }
        ],
        "quiz": [
            {
                "question": "¿Qué demostró el estudio de Sara Lazar (2005) sobre la meditación?",
                "options": [
                    "A) Que la meditación aumenta el grosor de la corteza cerebral",
                    "B) Que la meditación reduce la presión arterial",
                    "C) Que la meditación mejora la memoria a corto plazo",
                    "D) Que la meditación cambia el color de la materia gris"
                ],
                "correct": "A",
                "explanation": "Lazar et al. descubrieron que los meditadores experimentados tenían mayor grosor cortical en áreas asociadas con la atención y el procesamiento sensorial."
            },
            {
                "question": "¿Qué es la neuroplasticidad?",
                "options": [
                    "A) La capacidad del cerebro de cambiar su estructura con la experiencia",
                    "B) Un tipo de meditación oriental",
                    "C) Una técnica de respiración profunda",
                    "D) La resistencia del cerebro a los cambios"
                ],
                "correct": "A",
                "explanation": "La neuroplasticidad es la capacidad del cerebro de reorganizar sus conexiones neuronales en respuesta a nuevas experiencias y aprendizajes."
            },
            {
                "question": "Según el estudio de Hölzel (2011), ¿qué ocurre tras 8 semanas de mindfulness?",
                "options": [
                    "A) Aumenta el tamaño del cerebelo",
                    "B) Se reduce el volumen de la amígdala",
                    "C) Se duplican las conexiones neuronales",
                    "D) Desaparece el estrés por completo"
                ],
                "correct": "B",
                "explanation": "Hölzel et al. demostraron que la práctica de mindfulness reduce el volumen de la amígdala, la estructura cerebral asociada con las respuestas de miedo y estrés."
            }
        ],
        "citations_bibliography": [
            "Lazar, S. W., Kerr, C. E., Wasserman, R. H., Gray, J. R., Greve, D. N., Treadway, M. T., ... & Fischl, B. (2005). Meditation experience is associated with increased cortical thickness. Neuroreport, 16(17), 1893-1897.",
            "Davidson, R. J., Kabat-Zinn, J., Schumacher, J., Rosenkranz, M., Muller, D., Santorelli, S. F., ... & Sheridan, J. F. (2003). Alterations in brain and immune function produced by mindfulness meditation. Psychosomatic Medicine, 65(4), 564-570.",
            "Hölzel, B. K., Carmody, J., Vangel, M., Congleton, C., Yerramsetti, S. M., Gard, T., & Lazar, S. W. (2011). Mindfulness practice leads to increases in regional brain gray matter density. Psychiatry Research: Neuroimaging, 191(1), 36-43."
        ],
        "_generation": {
            "model": "dry-run",
            "attempt": 1,
            "input_tokens": 0,
            "output_tokens": 0
        }
    }


def load_course(course_id: str = "brujula-interior") -> dict:
    """Load course data from config."""
    courses_path = Path(__file__).parent / "config" / "courses.json"
    with open(courses_path) as f:
        data = json.load(f)
    for course in data["courses"]:
        if course["id"] == course_id:
            return course
    raise ValueError(f"Course '{course_id}' not found")


def get_next_lesson_title(course: dict, lesson_index: int) -> str | None:
    """Get the title of the next non-quiz lesson."""
    lessons = course["lessons"]
    for i in range(lesson_index + 1, len(lessons)):
        if lessons[i].get("type") != "quiz":
            return lessons[i]["title"]
    return None


def generate_and_save(lesson_index: int, course_id: str = "brujula-interior",
                      output_dir: str = "output", dry_run: bool = False) -> Path:
    """Generate script for a lesson and save to disk."""
    course = load_course(course_id)
    lessons = course["lessons"]

    if lesson_index < 0 or lesson_index >= len(lessons):
        raise ValueError(f"Lesson index {lesson_index} out of range (0-{len(lessons)-1})")

    lesson = lessons[lesson_index]

    # Skip quiz/exam lessons
    if lesson.get("type") in ("quiz", "exam"):
        print(f"  ⏭ Skipping {lesson['type']} lesson: {lesson['title']}")
        return None

    next_title = get_next_lesson_title(course, lesson_index)

    print(f"📝 Generating: [{lesson_index}] {lesson['title']}")
    script = generate_script(lesson, lesson_index, course, next_title, dry_run=dry_run)

    # Save
    out_path = Path(output_dir) / f"lesson_{lesson_index:02d}"
    out_path.mkdir(parents=True, exist_ok=True)
    script_file = out_path / "script.json"

    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"  💾 Saved: {script_file}")

    # Report validation status
    if script.get("_validation_errors"):
        print(f"  ⚠ Script has {len(script['_validation_errors'])} unresolved validation errors")
    else:
        print(f"  ✅ All quality checks passed")

    return script_file
