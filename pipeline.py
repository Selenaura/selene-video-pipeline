#!/usr/bin/env python3
"""Selene Video Pipeline — main CLI entry point.

Usage:
    python pipeline.py --list                        # List all lessons
    python pipeline.py --lesson 0 --steps script     # Generate script only
    python pipeline.py --lesson 0                    # Full pipeline (all steps)
    python pipeline.py --course brujula-interior     # Entire course
    python pipeline.py --lesson 0 --steps script --dry-run  # Test without API
"""

import argparse
import json
import sys
from pathlib import Path

from audio_narrator import narrate_lesson
from script_generator import generate_and_save, load_course
from slide_builder import build_from_script_file
from validator import validate_script_file

ALL_STEPS = ["script", "slides", "audio", "subtitles", "video", "thumbnail"]


def list_lessons(course_id: str) -> None:
    """Print all lessons in a course."""
    course = load_course(course_id)
    print(f"\n📚 {course['title']} ({course['level']})")
    print(f"   {len(course['lessons'])} lecciones\n")
    for i, lesson in enumerate(course["lessons"]):
        lesson_type = lesson.get("type", "lesson")
        marker = "📝" if lesson_type == "lesson" else "❓" if lesson_type == "quiz" else "📋"
        print(f"  {marker} [{i:2d}] M{lesson['module']}: {lesson['title']} ({lesson['duration_target']}min)")
    print()


def run_step_script(lesson_index: int, course_id: str, output_dir: str,
                    dry_run: bool = False) -> Path | None:
    """Run the script generation step."""
    return generate_and_save(lesson_index, course_id, output_dir, dry_run=dry_run)


def run_pipeline(lesson_index: int, course_id: str, steps: list[str],
                 output_dir: str, dry_run: bool = False) -> None:
    """Run pipeline steps for a single lesson."""
    course = load_course(course_id)
    lesson = course["lessons"][lesson_index]
    print(f"\n{'='*60}")
    print(f"🎬 Lesson {lesson_index}: {lesson['title']}")
    print(f"   Steps: {', '.join(steps)}")
    if dry_run:
        print(f"   Mode: DRY RUN (no API calls)")
    print(f"{'='*60}\n")

    if "script" in steps:
        script_path = run_step_script(lesson_index, course_id, output_dir, dry_run=dry_run)
        if script_path is None:
            return  # Quiz/exam lesson, skipped

    if "slides" in steps:
        lesson_dir = Path(output_dir) / f"lesson_{lesson_index:02d}"
        script_file = lesson_dir / "script.json"
        if script_file.exists():
            build_from_script_file(script_file)
        else:
            print(f"  ⚠ No script.json found — run 'script' step first")

    if "audio" in steps:
        lesson_dir = Path(output_dir) / f"lesson_{lesson_index:02d}"
        script_file = lesson_dir / "script.json"
        if script_file.exists():
            narrate_lesson(script_file, dry_run=dry_run)
        else:
            print(f"  ⚠ No script.json found — run 'script' step first")

    # Future steps (Phase 4+)
    for step in steps:
        if step in ("script", "slides", "audio"):
            continue
        print(f"\n⏳ Step '{step}' not yet implemented (coming in Phase {ALL_STEPS.index(step) + 1})")


def run_course(course_id: str, steps: list[str], output_dir: str,
               dry_run: bool = False) -> None:
    """Run pipeline for all lessons in a course."""
    course = load_course(course_id)
    lessons = course["lessons"]
    total = len(lessons)
    completed = 0
    skipped = 0
    failed = 0

    print(f"\n🚀 Starting course: {course['title']} ({total} lessons)")
    print(f"   Steps: {', '.join(steps)}")
    if dry_run:
        print(f"   Mode: DRY RUN")
    print()

    for i in range(total):
        lesson = lessons[i]

        # Check if output already exists (resume support)
        script_path = Path(output_dir) / f"lesson_{i:02d}" / "script.json"
        if "script" in steps and script_path.exists() and not dry_run:
            errors = validate_script_file(script_path)
            if not errors:
                print(f"  ⏭ [{i}] Already complete: {lesson['title']}")
                skipped += 1
                continue

        try:
            run_pipeline(i, course_id, steps, output_dir, dry_run=dry_run)
            completed += 1
        except Exception as e:
            print(f"  ❌ [{i}] Failed: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"📊 Course summary: {completed} completed, {skipped} skipped, {failed} failed")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Selene Video Pipeline — automated lesson production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--list", action="store_true",
                        help="List all lessons in the course")
    parser.add_argument("--lesson", type=int, metavar="N",
                        help="Generate a specific lesson by index")
    parser.add_argument("--course", type=str, metavar="ID",
                        help="Generate all lessons for a course")
    parser.add_argument("--steps", type=str, default=",".join(ALL_STEPS),
                        help=f"Comma-separated steps to run (default: all). "
                             f"Options: {', '.join(ALL_STEPS)}")
    parser.add_argument("--output", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test mode: use sample scripts instead of API calls")
    parser.add_argument("--validate", type=str, metavar="PATH",
                        help="Validate an existing script.json file")

    args = parser.parse_args()
    steps = [s.strip() for s in args.steps.split(",")]

    if args.validate:
        errors = validate_script_file(args.validate)
        if errors:
            print(f"❌ {len(errors)} errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("✅ Valid.")
        return

    if args.list:
        course_id = args.course or "brujula-interior"
        list_lessons(course_id)
        return

    if args.lesson is not None:
        course_id = args.course or "brujula-interior"
        run_pipeline(args.lesson, course_id, steps, args.output, dry_run=args.dry_run)
        return

    if args.course:
        run_course(args.course, steps, args.output, dry_run=args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
