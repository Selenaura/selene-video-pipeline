"""Generate lesson thumbnails with Quantum Ethereal design."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from validator import SETTINGS

THUMB_SIZE = tuple(SETTINGS["video"]["thumbnail_size"])
COLORS = SETTINGS["design"]["colors"]


def _hex_to_rgb(hex_str: str) -> tuple:
    """Convert hex color string to RGB tuple."""
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


BG = _hex_to_rgb(COLORS["bg"])
GOLD = _hex_to_rgb(COLORS["gold"])
GOLD_LIGHT = _hex_to_rgb(COLORS["gold_light"])
GOLD_DIM = _hex_to_rgb(COLORS["gold_dim"])
WHITE = _hex_to_rgb(COLORS["white"])
DIM = _hex_to_rgb(COLORS["dim"])


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a font with fallback."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _draw_text_centered(draw, y, text, font, color, width):
    """Draw centered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, y), text, fill=color, font=font)


def _draw_text_wrapped(draw, x, y, text, font, color, max_width):
    """Draw word-wrapped text, return final y position."""
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_x = x + (max_width - line_w) // 2
        draw.text((line_x, y), line, fill=color, font=font)
        y += bbox[3] - bbox[1] + 8
    return y


def generate_thumbnail(script: dict, output_path: str | Path) -> Path:
    """Generate a 1280x720 thumbnail for a lesson."""
    output_path = Path(output_path)
    width, height = THUMB_SIZE

    img = Image.new("RGB", (width, height), color=BG)
    draw = ImageDraw.Draw(img)

    # Gold glow circle (center)
    glow_center = (width // 2, height // 2 - 20)
    for r in range(180, 0, -2):
        alpha = int(25 * (r / 180))
        glow_color = (GOLD[0] // 6, GOLD[1] // 6, GOLD[2] // 8)
        draw.ellipse(
            [glow_center[0] - r, glow_center[1] - r,
             glow_center[0] + r, glow_center[1] + r],
            fill=glow_color
        )

    # Corner ornaments ✦
    ornament_font = _load_font(20)
    positions = [(30, 20), (width - 50, 20), (30, height - 40), (width - 50, height - 40)]
    for px, py in positions:
        draw.text((px, py), "✦", fill=GOLD_DIM, font=ornament_font)

    # Moon symbol ☽
    moon_font = _load_font(60)
    _draw_text_centered(draw, 100, "☽", moon_font, GOLD, width)

    # Module tag
    module = script.get("module", 1)
    module_name = script.get("module_name", "")
    tag_font = _load_font(20)
    tag_text = f"MÓDULO {module}"
    if module_name:
        tag_text += f" · {module_name}"
    _draw_text_centered(draw, 200, tag_text, tag_font, GOLD_DIM, width)

    # Lesson title (centered, wrapped)
    title = script.get("title", "Lección")
    title_font = _load_font(44)
    _draw_text_wrapped(draw, 80, 260, title, title_font, GOLD_LIGHT, width - 160)

    # Gold separator line
    line_y = 450
    line_w = 300
    draw.rectangle(
        [(width // 2 - line_w // 2, line_y),
         (width // 2 + line_w // 2, line_y + 2)],
        fill=GOLD_DIM
    )

    # Brand watermark
    brand_font = _load_font(24)
    _draw_text_centered(draw, 480, "SELENE ACADEMIA", brand_font, DIM, width)

    # Course name
    course = script.get("course", "")
    if course:
        course_font = _load_font(16)
        _draw_text_centered(draw, 520, course, course_font, GOLD_DIM, width)

    # Bottom border line
    draw.rectangle([(0, height - 4), (width, height)], fill=GOLD_DIM)

    img.save(str(output_path), "PNG", quality=95)
    print(f"  🖼 Thumbnail saved: {output_path}")
    return output_path


def generate_from_script_file(script_path: str | Path, output_path: str | Path = None) -> Path:
    """Generate thumbnail from a script.json file."""
    script_path = Path(script_path)
    with open(script_path) as f:
        script = json.load(f)

    if output_path is None:
        output_path = script_path.parent / "thumbnail.png"

    return generate_thumbnail(script, output_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python thumbnail_generator.py <script.json> [output.png]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    generate_from_script_file(sys.argv[1], out)
