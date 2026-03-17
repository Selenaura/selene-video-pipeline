"""Generate pedagogical video scripts using Claude API."""

import json
import os
from pathlib import Path

from validator import SETTINGS, validate_script

# Load golden examples for few-shot prompting
_SCRIPTS_DIR = Path(__file__).parent / "scripts"


def _load_golden_examples() -> list[dict]:
    """Load golden example scripts from scripts/ directory."""
    examples = []
    for path in sorted(_SCRIPTS_DIR.glob("M01_L*")):
        with open(path) as f:
            examples.append(json.load(f))
    return examples


def _get_few_shot_example() -> str:
    """Get a condensed golden example for the system prompt."""
    # Use L01 as the canonical example (most complete)
    example_path = _SCRIPTS_DIR / "M01_L01_espiritualidad_consciente"
    if not example_path.exists():
        # Try .json extension
        for p in _SCRIPTS_DIR.glob("M01_L01*"):
            example_path = p
            break
    if example_path.exists():
        with open(example_path) as f:
            return f.read()
    return ""


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
6. Narración por slide: entre 20 y 150 palabras (sin contar tags SSML).
7. Tono: conversacional, como si hablaras con una amiga curiosa. Storytelling > lectura.

## ESTRUCTURA DE LA LECCIÓN
1. **title** (1 slide): Bienvenida y contexto. Conecta con la lección anterior.
2. **hook** (1 slide): Dato sorprendente o pregunta provocadora. Engancha en 10-15 segundos.
3. **content** (2-4 slides): Desarrollo del tema. Máximo 3 conceptos por lección.
4. **science** (1-2 slides): Evidencia científica con citas. Datos concretos.
5. **quote** (0-1 slides): Cita célebre con atribución. Opcional.
6. **practice** (1 slide): Ejercicio práctico guiado que puedan hacer ahora.
7. **summary** (1 slide): Exactamente 3 takeaways clave.
8. **content** (1 slide, como CTA): Siguiente lección + tarea para la semana.

## FORMATO DE SALIDA (JSON estricto)
Responde SOLO con JSON válido, sin markdown ni explicaciones. Sigue EXACTAMENTE esta estructura:

```
{
  "lesson_id": "MXX_LYY",
  "course": "Despierta tu Brújula Interior",
  "module": N,
  "module_name": "Nombre del módulo",
  "title": "Título de la lección",
  "duration_minutes": N,
  "slides": [
    {
      "n": 1,
      "type": "title|hook|content|science|quote|practice|summary",
      "title": "Título corto del slide",
      "subtitle": "Subtítulo opcional o vacío",
      "bullets": ["Bullet (max 12 palabras)", ...],
      "narration": "Narración con pausas SSML <break time=\\"0.5s\\"/>...",
      "citation": "Autor et al. (año). Título. Revista, vol(num), pp." | null,
      "duration_seconds": N
    }
  ],
  "quiz": [
    {
      "q": "Pregunta en español",
      "opts": ["Opción A", "Opción B", "Opción C", "Opción D"],
      "answer": 0,
      "why": "Explicación de 1-2 frases"
    }
  ],
  "citations_used": [
    "Referencia completa en formato APA"
  ],
  "meta": {
    "total_narration_words": N,
    "estimated_duration_minutes": N.N,
    "slide_count": N,
    "citation_count": N,
    "banned_terms_found": 0
  }
}
```

## GUÍA DE NARRACIÓN
- Usa pausas SSML dentro de la narración: <break time="0.5s"/> para pausas cortas, <break time="0.8s"/> para medias, <break time="1.0s"/> o más para prácticas guiadas.
- Usa "…" (puntos suspensivos) para pausas narrativas naturales.
- Usa "—" (em-dash) para incisos.
- Los números se escriben en letra: "dos mil cinco" en vez de "2005".
- El summary siempre empieza con un conteo: "Tres cosas...", "Tres aprendizajes..."
- El último slide (CTA) menciona la siguiente lección por nombre.
- Incluye conexiones personales: "Piensa en la última vez que..."
- La primera lección de cada módulo incluye bienvenida.
- La última lección de cada módulo menciona que el módulo se ha completado.
"""


def build_user_prompt(lesson: dict, lesson_index: int, course: dict,
                      next_lesson_title: str | None) -> str:
    """Build the user prompt for a specific lesson."""
    module_num = lesson['module']
    module_name = course['modules'][str(module_num)]

    # Count lesson within module
    lessons_in_module = [l for l in course['lessons']
                         if l['module'] == module_num and l.get('type') != 'quiz']
    lesson_in_module = next((i+1 for i, l in enumerate(lessons_in_module)
                            if l['title'] == lesson['title']), 1)

    lesson_id = f"M{module_num:02d}_L{lesson_in_module:02d}"

    prompt = f"""Genera el guión completo para la lección "{lesson['title']}".

## Datos de la lección
- **lesson_id**: {lesson_id}
- **Título**: {lesson['title']}
- **Módulo**: {module_num} — {module_name}
- **Lección en módulo**: {lesson_in_module} de {len(lessons_in_module)}
- **Descripción y contenido clave**: {lesson['description']}
- **Duración objetivo**: {lesson['duration_target']} minutos
- **Nivel del curso**: {course['level']}
- **Público**: {course['target_audience']}
"""
    if next_lesson_title:
        prompt += f"- **Siguiente lección** (para el CTA): {next_lesson_title}\n"
    else:
        prompt += "- **Siguiente paso** (para el CTA): Completar la evaluación final del curso.\n"

    prompt += """
## Recordatorios
- Mínimo 2 citas peer-reviewed REALES (preferiblemente 3-4)
- Entre 6 y 16 slides total (9-10 es ideal)
- Incluye pausas SSML (<break time="0.5s"/>) en la narración
- Numera los slides con "n" empezando en 1
- Incluye duration_seconds estimada por slide
- El campo "meta" al final con estadísticas de validación
- Responde SOLO con JSON válido, sin markdown
"""
    return prompt


def _build_messages(user_prompt: str) -> list[dict]:
    """Build messages list with few-shot golden examples."""
    messages = []

    # Add one golden example as few-shot
    example = _get_few_shot_example()
    if example:
        messages.append({
            "role": "user",
            "content": 'Genera el guión completo para la lección "¿Qué es la espiritualidad consciente?" del Módulo 1.'
        })
        messages.append({
            "role": "assistant",
            "content": example
        })

    messages.append({"role": "user", "content": user_prompt})
    return messages


def generate_script(lesson: dict, lesson_index: int, course: dict,
                    next_lesson_title: str | None = None,
                    max_retries: int = 2, dry_run: bool = False) -> dict:
    """Generate and validate a lesson script using Claude API."""
    if dry_run:
        print("  🧪 Dry-run mode: loading sample script")
        return _load_or_create_sample(lesson, lesson_index, course, next_lesson_title)

    import anthropic
    client = anthropic.Anthropic()
    model = SETTINGS["api"]["claude_model"]
    max_tokens = SETTINGS["api"]["claude_max_tokens"]

    user_prompt = build_user_prompt(lesson, lesson_index, course, next_lesson_title)

    for attempt in range(max_retries + 1):
        print(f"  Generating script (attempt {attempt + 1})...")
        messages = _build_messages(user_prompt)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        raw_text = response.content[0].text.strip()

        # Detect truncated responses before attempting to parse
        if response.stop_reason == "max_tokens":
            print(f"  ⚠ Response truncated (hit max_tokens={max_tokens})")
            if attempt < max_retries:
                user_prompt += (
                    "\n\nIMPORTANTE: Tu respuesta anterior fue TRUNCADA por exceder el límite de tokens. "
                    "Genera un JSON más conciso: reduce el texto de narración, sé más breve en cada slide."
                )
                continue
            raise ValueError(
                f"Response truncated after {max_retries + 1} attempts. "
                f"Increase claude_max_tokens (currently {max_tokens}) in config/settings.json."
            )

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
    return script


def _load_or_create_sample(lesson: dict, lesson_index: int, course: dict,
                           next_lesson_title: str | None) -> dict:
    """Load golden example from scripts/ if available, else generate template."""
    # Try to find a matching golden script
    for path in sorted(_SCRIPTS_DIR.glob("*")):
        if not path.name.endswith(('.json', '_espiritualidad_consciente')):
            continue
        try:
            with open(path) as f:
                script = json.load(f)
            if script.get("title") == lesson["title"]:
                print(f"  📂 Loaded golden example: {path.name}")
                return script
        except (json.JSONDecodeError, KeyError):
            continue

    # Generate a minimal valid template in golden format
    module_num = lesson['module']
    module_name = course['modules'][str(module_num)]
    lessons_in_module = [l for l in course['lessons']
                         if l['module'] == module_num and l.get('type') != 'quiz']
    lesson_in_module = next((i+1 for i, l in enumerate(lessons_in_module)
                            if l['title'] == lesson['title']), 1)
    lesson_id = f"M{module_num:02d}_L{lesson_in_module:02d}"
    next_title = next_lesson_title or "la siguiente lección"

    return {
        "lesson_id": lesson_id,
        "course": course["title"],
        "module": module_num,
        "module_name": module_name,
        "title": lesson["title"],
        "duration_minutes": lesson.get("duration_target", 12),
        "slides": [
            {
                "n": 1,
                "type": "title",
                "title": lesson["title"],
                "subtitle": f"Módulo {module_num} · {module_name}",
                "narration": f"Bienvenida a Selene Academia. Hoy exploramos {lesson['title'].lower()}… una lección que cambiará tu perspectiva sobre tu propia mente.",
                "duration_seconds": 12
            },
            {
                "n": 2,
                "type": "hook",
                "title": "¿Sabías que tu cerebro puede transformarse?",
                "bullets": [],
                "narration": "¿Sabías que tu cerebro es capaz de transformarse físicamente con la práctica? No es una metáfora… es neuroplasticidad. En dos mil once, Hölzel y su equipo publicaron en Psychiatry Research que ocho semanas de meditación cambian la densidad de materia gris. <break time=\"0.8s\"/> No es fe. Es neurociencia.",
                "citation": "Hölzel et al. (2011). Mindfulness practice leads to increases in regional brain gray matter density. Psychiatry Research: Neuroimaging, 191(1), 36-43.",
                "duration_seconds": 30
            },
            {
                "n": 3,
                "type": "content",
                "title": "El poder de la atención entrenada",
                "bullets": [
                    "No es fe ciega, es práctica verificable",
                    "Entrenar la atención cambia tu cerebro",
                    "La experiencia directa como maestra"
                ],
                "narration": "Cuando hablamos de espiritualidad consciente, no hablamos de creer en algo porque alguien te lo dice. Hablamos de entrenar tu capacidad de atención y de autoconocimiento… utilizando herramientas que combinan siglos de tradición simbólica con décadas de investigación científica. <break time=\"0.5s\"/> Es una práctica verificable. Puedes medir sus efectos.",
                "duration_seconds": 25
            },
            {
                "n": 4,
                "type": "science",
                "title": "La ciencia de la meditación",
                "bullets": [
                    "Lazar 2005: meditadores con corteza más gruesa",
                    "Davidson 2003: más actividad prefrontal izquierda",
                    "Hölzel 2011: reducción del volumen amigdalar"
                ],
                "narration": "Sara Lazar y su equipo de Harvard descubrieron en dos mil cinco que los meditadores experimentados tenían una corteza cerebral más gruesa en áreas de atención y percepción. <break time=\"0.5s\"/> Richard Davidson demostró que la meditación aumenta la actividad en la corteza prefrontal izquierda… la zona asociada a emociones positivas. <break time=\"0.5s\"/> Y Hölzel confirmó que ocho semanas de práctica reducen el volumen de la amígdala.",
                "citation": "Lazar et al. (2005). Meditation experience is associated with increased cortical thickness. NeuroReport, 16(17), 1893-1897. | Davidson et al. (2003). Alterations in brain and immune function produced by mindfulness meditation. Psychosomatic Medicine, 65(4), 564-570.",
                "duration_seconds": 40
            },
            {
                "n": 5,
                "type": "content",
                "title": "Tu cerebro se adapta a lo que practicas",
                "bullets": [
                    "Neuroplasticidad: el cerebro cambia siempre",
                    "Maguire 2000: taxistas de Londres e hipocampo",
                    "Funciona a cualquier edad"
                ],
                "narration": "El concepto clave es la neuroplasticidad. Tu cerebro se reorganiza constantemente en respuesta a tus experiencias. <break time=\"0.5s\"/> Eleanor Maguire estudió a los taxistas de Londres y descubrió que su hipocampo era significativamente más grande… porque lo entrenaron memorizando veinticinco mil calles. El cerebro creció, literalmente. Y lo mismo ocurre con la meditación.",
                "citation": "Maguire et al. (2000). Navigation-related structural change in the hippocampi of taxi drivers. PNAS, 97(8), 4398-4403.",
                "duration_seconds": 30
            },
            {
                "n": 6,
                "type": "practice",
                "title": "Tu primera práctica: 3 minutos de atención",
                "bullets": [
                    "Siéntate cómoda y cierra los ojos",
                    "Respira: 4 segundos dentro, 6 segundos fuera",
                    "Observa tus pensamientos sin juzgar",
                    "Cuando tu mente se vaya, tráela de vuelta"
                ],
                "narration": "Vamos a hacer tu primera práctica. Solo tres minutos. <break time=\"0.8s\"/> Siéntate en una posición cómoda. Cierra los ojos. Y simplemente respira… cuatro segundos al inhalar… <break time=\"1.0s\"/> y seis segundos al exhalar. <break time=\"1.0s\"/> Observa qué pasa por tu mente. No intentes controlar tus pensamientos… solo obsérvalos. Cuando tu mente se vaya a otro lugar, tráela de vuelta a la respiración. Sin juicio. <break time=\"0.5s\"/> Eso es atención entrenada.",
                "duration_seconds": 40
            },
            {
                "n": 7,
                "type": "summary",
                "title": "Lo que has aprendido hoy",
                "bullets": [
                    "Espiritualidad consciente = atención entrenada + ciencia",
                    "Tu cerebro cambia físicamente con la práctica",
                    "La intuición tiene base neurológica real"
                ],
                "narration": "Tres aprendizajes de hoy. <break time=\"0.5s\"/> Primero: la espiritualidad consciente no es creer… es entrenar tu atención con herramientas respaldadas por ciencia. <break time=\"0.5s\"/> Segundo: tu cerebro tiene neuroplasticidad… cambia físicamente cuando lo entrenas. <break time=\"0.5s\"/> Y tercero: lo que llamamos intuición tiene una base neurológica real que puedes desarrollar.",
                "duration_seconds": 25
            },
            {
                "n": 8,
                "type": "content",
                "title": "Tu siguiente paso",
                "bullets": [
                    f"Siguiente lección: {next_title}",
                    "Practica la respiración 4-6 cada día esta semana"
                ],
                "narration": f"En la siguiente lección — {next_title} — vamos a profundizar en la ciencia detrás de la práctica. <break time=\"0.5s\"/> Tu tarea es sencilla: practica la respiración cuatro-seis al menos una vez al día esta semana. Tres minutos. <break time=\"0.8s\"/> Nos vemos en la siguiente lección.",
                "duration_seconds": 18
            }
        ],
        "quiz": [
            {
                "q": "¿Qué demostró el estudio de Hölzel et al. (2011)?",
                "opts": [
                    "Que los signos del zodíaco afectan la personalidad",
                    "Que 8 semanas de meditación cambian la densidad de materia gris",
                    "Que la Luna influye en el estado de ánimo",
                    "Que el tarot predice el futuro"
                ],
                "answer": 1,
                "why": "Hölzel y su equipo demostraron cambios medibles en la materia gris tras 8 semanas de meditación mindfulness."
            },
            {
                "q": "¿Qué es la neuroplasticidad?",
                "opts": [
                    "Una enfermedad neurológica",
                    "La capacidad del cerebro de reorganizarse con la experiencia",
                    "Un tipo de cirugía cerebral",
                    "Un suplemento alimenticio"
                ],
                "answer": 1,
                "why": "La neuroplasticidad es la capacidad del cerebro de cambiar su estructura en respuesta a la experiencia."
            },
            {
                "q": "¿Qué descubrió Maguire (2000) en los taxistas de Londres?",
                "opts": [
                    "Que tenían peor memoria",
                    "Que su hipocampo era más grande",
                    "Que conducir dañaba el cerebro",
                    "Que no había diferencias cerebrales"
                ],
                "answer": 1,
                "why": "Maguire encontró que el hipocampo de los taxistas era mayor, proporcional a los años de experiencia."
            }
        ],
        "citations_used": [
            "Hölzel, B. K., et al. (2011). Mindfulness practice leads to increases in regional brain gray matter density. Psychiatry Research: Neuroimaging, 191(1), 36-43.",
            "Lazar, S. W., et al. (2005). Meditation experience is associated with increased cortical thickness. NeuroReport, 16(17), 1893-1897.",
            "Davidson, R. J., et al. (2003). Alterations in brain and immune function produced by mindfulness meditation. Psychosomatic Medicine, 65(4), 564-570.",
            "Maguire, E. A., et al. (2000). Navigation-related structural change in the hippocampi of taxi drivers. PNAS, 97(8), 4398-4403."
        ],
        "meta": {
            "total_narration_words": 520,
            "estimated_duration_minutes": 7.5,
            "slide_count": 8,
            "citation_count": 4,
            "banned_terms_found": 0
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
