"""Quality validation for Selene video pipeline scripts."""

import json
import re
from pathlib import Path

# Load settings once
_SETTINGS_PATH = Path(__file__).parent / "config" / "settings.json"
with open(_SETTINGS_PATH) as f:
    SETTINGS = json.load(f)

BANNED_TERMS = [t.strip().lower() for t in SETTINGS["brand"]["banned_terms"]]
QC = SETTINGS["quality_checks"]

# Strip SSML tags for word counting
_SSML_RE = re.compile(r'<[^>]+>')


def _clean_ssml(text: str) -> str:
    """Remove SSML tags from text for word counting."""
    return _SSML_RE.sub('', text).strip()


def check_banned_terms(text: str) -> list[str]:
    """Return list of banned terms found in text."""
    text_lower = _clean_ssml(text).lower()
    found = []
    for term in BANNED_TERMS:
        if len(term) <= 3:
            if re.search(rf'\b{re.escape(term.strip())}\b', text_lower):
                found.append(term.strip())
        else:
            if term in text_lower:
                found.append(term.strip())
    return found


def validate_script(script: dict) -> list[str]:
    """Validate a generated script. Returns list of error strings (empty = valid).

    Supports both the original pipeline format and the golden example format:
    - quiz: [{question, options, correct, explanation}] or [{q, opts, answer, why}]
    - citations: citations_bibliography or citations_used
    """
    errors = []
    slides = script.get("slides", [])

    # Quiz-only scripts (type: "quiz") have different validation
    if script.get("type") == "quiz":
        questions = script.get("questions", [])
        if len(questions) < 3:
            errors.append(f"Too few quiz questions: {len(questions)} < 3")
        # Check banned terms in questions
        all_text = " ".join(q.get("q", "") for q in questions)
        banned = check_banned_terms(all_text)
        if banned:
            errors.append(f"Banned terms found in quiz: {banned}")
        return errors

    # Slide count
    if len(slides) < QC["min_slides"]:
        errors.append(f"Too few slides: {len(slides)} < {QC['min_slides']}")
    if len(slides) > QC["max_slides"]:
        errors.append(f"Too many slides: {len(slides)} > {QC['max_slides']}")

    # Required slide types
    slide_types = {s.get("type") for s in slides}
    for required in QC["required_slide_types"]:
        if required not in slide_types:
            errors.append(f"Missing required slide type: '{required}'")

    # Per-slide checks
    all_citations = []
    all_text = []

    for i, slide in enumerate(slides):
        slide_num = slide.get("n", i + 1)
        prefix = f"Slide {slide_num} ({slide.get('type', '?')})"

        # Bullets (title/quote/hook may have no bullets — that's OK)
        bullets = slide.get("bullets", [])
        if len(bullets) > QC["max_bullets_per_slide"]:
            errors.append(f"{prefix}: {len(bullets)} bullets > max {QC['max_bullets_per_slide']}")
        for j, bullet in enumerate(bullets):
            word_count = len(bullet.split())
            if word_count > QC["max_words_per_bullet"]:
                errors.append(f"{prefix}, bullet {j+1}: {word_count} words > max {QC['max_words_per_bullet']}")

        # Narration length (strip SSML before counting)
        narration = slide.get("narration", "")
        clean_narration = _clean_ssml(narration)
        word_count = len(clean_narration.split())
        if word_count < QC["min_narration_words_per_slide"]:
            errors.append(f"{prefix}: narration too short ({word_count} words < {QC['min_narration_words_per_slide']})")
        if word_count > QC["max_narration_words_per_slide"]:
            errors.append(f"{prefix}: narration too long ({word_count} words > {QC['max_narration_words_per_slide']})")

        # Collect text for banned terms check
        all_text.append(slide.get("title", ""))
        all_text.append(slide.get("subtitle", ""))
        all_text.extend(bullets)
        all_text.append(narration)

        # Collect citations (from per-slide or bibliography)
        if slide.get("citation"):
            all_citations.append(slide["citation"])

    # Also count citations from bibliography lists
    bib = script.get("citations_used", script.get("citations_bibliography", []))
    citation_count = max(len(all_citations), len(bib))

    if citation_count < QC["min_citations_per_lesson"]:
        errors.append(f"Too few citations: {citation_count} < {QC['min_citations_per_lesson']}")

    # Banned terms across all text
    full_text = " ".join(all_text)
    banned_found = check_banned_terms(full_text)
    if banned_found:
        errors.append(f"Banned terms found: {banned_found}")

    # Quiz questions (support both formats)
    quiz = script.get("quiz", [])
    if len(quiz) < 3:
        errors.append(f"Too few quiz questions: {len(quiz)} < 3")

    return errors


def validate_script_file(path: str | Path) -> list[str]:
    """Load and validate a script JSON file."""
    with open(path) as f:
        script = json.load(f)
    return validate_script(script)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validator.py <script.json>")
        sys.exit(1)
    errors = validate_script_file(sys.argv[1])
    if errors:
        print(f"❌ {len(errors)} validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("✅ Script passes all quality checks.")
