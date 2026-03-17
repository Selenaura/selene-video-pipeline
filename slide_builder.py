"""Build Quantum Ethereal PPTX slides from script.json using python-pptx."""

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

from validator import SETTINGS

# Design constants from config
COLORS = SETTINGS["design"]["colors"]
FONTS = SETTINGS["design"]["fonts"]
SLIDE_TYPES = SETTINGS["design"]["slide_types"]

# Dimensions (16:9 widescreen)
SLIDE_WIDTH = Inches(13.333)  # Standard 16:9
SLIDE_HEIGHT = Inches(7.5)

# Color palette
BG_COLOR = RGBColor.from_string(COLORS["bg"])
GOLD = RGBColor.from_string(COLORS["gold"])
GOLD_LIGHT = RGBColor.from_string(COLORS["gold_light"])
GOLD_DIM = RGBColor.from_string(COLORS["gold_dim"])
WHITE = RGBColor.from_string(COLORS["white"])
DIM = RGBColor.from_string(COLORS["dim"])
BLUE = RGBColor.from_string(COLORS["blue"])
VIOLET = RGBColor.from_string(COLORS["violet"])
TEAL = RGBColor.from_string(COLORS["teal"])
ROSE = RGBColor.from_string(COLORS["rose"])

ACCENT_COLORS = {
    "gold": GOLD,
    "blue": BLUE,
    "violet": VIOLET,
    "teal": TEAL,
    "rose": ROSE,
}

# Font names (with fallbacks)
FONT_DISPLAY = FONTS["fallback_display"]  # Georgia (safe fallback)
FONT_BODY = FONTS["fallback_body"]        # Calibri (safe fallback)

# Asset paths
ASSETS_DIR = Path(__file__).parent / "assets"
BG_MAP = {
    "title": "bg_title.png",
    "hook": "bg_title.png",
    "content": "bg_content.png",
    "science": "bg_science.png",
    "practice": "bg_practice.png",
    "quote": "bg_quote.png",
    "summary": "bg_summary.png",
    "cta": "bg_summary.png",
}
MOON_PATH = ASSETS_DIR / "decorations" / "moon_face.png"
DIVIDER_PATH = ASSETS_DIR / "decorations" / "divider_star.png"
CORNER_PATH = ASSETS_DIR / "decorations" / "corner_ornaments.png"
CONSTELLATION_PATH = ASSETS_DIR / "decorations" / "constellation_overlay.png"


def _set_slide_bg(slide, prs, slide_type="content"):
    """Set slide background: image if available, else solid color."""
    bg_file = BG_MAP.get(slide_type, "bg_content.png")
    bg_path = ASSETS_DIR / "backgrounds" / bg_file
    if bg_path.exists():
        slide.shapes.add_picture(
            str(bg_path), 0, 0, prs.slide_width, prs.slide_height
        )
    else:
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = BG_COLOR


def _add_text_box(slide, left, top, width, height, text, font_name=FONT_BODY,
                  font_size=Pt(18), font_color=WHITE, bold=False,
                  alignment=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    """Add a text box with styled text to a slide."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    # Set vertical anchor
    try:
        tf.paragraphs[0].alignment = alignment
    except Exception:
        pass

    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = font_size
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.alignment = alignment
    return txBox


def _add_separator_line(slide, left, top, width, color=GOLD_DIM):
    """Add a thin horizontal gold separator line."""
    from pptx.oxml.ns import qn
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE.RECTANGLE
        left, top, width, Pt(1.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _add_watermark(slide):
    """Add 'SELENE ACADEMIA' watermark at bottom."""
    _add_text_box(
        slide,
        left=Inches(0.5), top=Inches(6.8),
        width=Inches(12), height=Inches(0.4),
        text="SELENE ACADEMIA",
        font_name=FONT_BODY, font_size=Pt(9),
        font_color=RGBColor(0x40, 0x40, 0x45),
        alignment=PP_ALIGN.CENTER
    )


def _add_corner_ornaments(slide, color=GOLD_DIM):
    """Add corner ornaments: image asset if available, else text ✦."""
    if CORNER_PATH.exists():
        # Corner ornaments image is a single image with 4 corners.
        # Place it as a full-slide overlay — the PNG has transparent center.
        slide.shapes.add_picture(
            str(CORNER_PATH), 0, 0,
            Inches(13.333), Inches(7.5)
        )
    else:
        positions = [
            (Inches(0.3), Inches(0.2)),
            (Inches(12.5), Inches(0.2)),
            (Inches(0.3), Inches(6.9)),
            (Inches(12.5), Inches(6.9)),
        ]
        for left, top in positions:
            _add_text_box(
                slide, left, top, Inches(0.5), Inches(0.4),
                text="✦",
                font_size=Pt(14), font_color=color,
                alignment=PP_ALIGN.CENTER
            )


def _add_moon(slide):
    """Add moon_face decoration on title slides."""
    if MOON_PATH.exists():
        slide.shapes.add_picture(
            str(MOON_PATH),
            Inches(5.2), Inches(0.2),
            Inches(3), Inches(3)
        )


def _add_divider(slide):
    """Add star divider below title."""
    if DIVIDER_PATH.exists():
        slide.shapes.add_picture(
            str(DIVIDER_PATH),
            Inches(3), Inches(1.8),
            Inches(7.333), Inches(0.5)
        )


def _add_constellation(slide):
    """Add constellation overlay at low opacity for content/science slides."""
    if CONSTELLATION_PATH.exists():
        pic = slide.shapes.add_picture(
            str(CONSTELLATION_PATH), 0, 0,
            Inches(13.333), Inches(7.5)
        )
        # Set opacity via XML (alpha = 12% = 12000 out of 100000)
        from pptx.oxml.ns import qn
        from lxml import etree
        spPr = pic._element.find(qn('p:blipFill'))
        if spPr is not None:
            blip = spPr.find(qn('a:blip'))
            if blip is not None:
                alphaModFix = etree.SubElement(blip, qn('a:alphaModFix'))
                alphaModFix.set('amt', '12000')


def _get_accent_color(slide_type: str) -> RGBColor:
    """Get the accent color for a slide type."""
    type_config = SLIDE_TYPES.get(slide_type, SLIDE_TYPES.get("content", {}))
    accent_name = type_config.get("accent", "gold")
    return ACCENT_COLORS.get(accent_name, GOLD)


def _get_icon(slide_type: str) -> str:
    """Get the icon for a slide type."""
    type_config = SLIDE_TYPES.get(slide_type, SLIDE_TYPES.get("content", {}))
    return type_config.get("icon", "◆")


def build_slide(prs, slide_data: dict, slide_number: int, total_slides: int):
    """Build a single slide from slide data."""
    slide_type = slide_data.get("type", "content")
    title = slide_data.get("title", "")
    bullets = slide_data.get("bullets", [])
    narration = slide_data.get("narration", "")
    citation = slide_data.get("citation")

    accent = _get_accent_color(slide_type)
    icon = _get_icon(slide_type)

    # Use blank layout
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    _set_slide_bg(slide, prs, slide_type)
    _add_corner_ornaments(slide, GOLD_DIM)

    # Add constellation overlay on content/science slides
    if slide_type in ("content", "science"):
        _add_constellation(slide)

    _add_watermark(slide)

    # Slide type badge (top-left area) — skip for title slides
    if slide_type != "title":
        badge_text = f"{icon}  {slide_type.upper()}"
        _add_text_box(
            slide,
            left=Inches(1.5), top=Inches(0.5),
            width=Inches(3), height=Inches(0.35),
            text=badge_text,
            font_name=FONT_BODY, font_size=Pt(10),
            font_color=accent, bold=True
        )

    # Slide counter (top-right)
    _add_text_box(
        slide,
        left=Inches(11), top=Inches(0.5),
        width=Inches(1.5), height=Inches(0.35),
        text=f"{slide_number}/{total_slides}",
        font_name=FONT_BODY, font_size=Pt(10),
        font_color=DIM,
        alignment=PP_ALIGN.RIGHT
    )

    # Title — centered and larger for title/quote slides
    if slide_type == "title":
        _add_moon(slide)
        _add_text_box(
            slide,
            left=Inches(1.5), top=Inches(3.2),
            width=Inches(10), height=Inches(1.5),
            text=title,
            font_name=FONT_DISPLAY, font_size=Pt(44),
            font_color=GOLD_LIGHT, bold=True,
            alignment=PP_ALIGN.CENTER
        )
        _add_divider(slide)
        subtitle = slide_data.get("subtitle", "")
        if subtitle:
            _add_text_box(
                slide,
                left=Inches(1.5), top=Inches(4.8),
                width=Inches(10), height=Inches(0.5),
                text=subtitle,
                font_name=FONT_BODY, font_size=Pt(18),
                font_color=DIM,
                alignment=PP_ALIGN.CENTER
            )
    elif slide_type == "quote":
        # Large italic quote centered
        _add_text_box(
            slide,
            left=Inches(1.5), top=Inches(1.5),
            width=Inches(10), height=Inches(2.5),
            text=f"❝ {title}",
            font_name=FONT_DISPLAY, font_size=Pt(28),
            font_color=GOLD_LIGHT, bold=False,
            alignment=PP_ALIGN.CENTER
        )
        subtitle = slide_data.get("subtitle", "")
        if subtitle:
            _add_divider(slide)
            _add_text_box(
                slide,
                left=Inches(1.5), top=Inches(4.5),
                width=Inches(10), height=Inches(0.5),
                text=f"— {subtitle}",
                font_name=FONT_BODY, font_size=Pt(16),
                font_color=DIM,
                alignment=PP_ALIGN.CENTER
            )
    else:
        # Standard title — inset from corner ornaments
        title_top = Inches(1.3)
        _add_text_box(
            slide,
            left=Inches(1.5), top=title_top,
            width=Inches(10), height=Inches(0.8),
            text=title,
            font_name=FONT_DISPLAY, font_size=Pt(32),
            font_color=GOLD_LIGHT, bold=True
        )
        # Separator line under title
        _add_separator_line(slide, Inches(1.5), Inches(2.2), Inches(10), accent)

    # Bullets (skip for title and quote slides)
    if slide_type not in ("title", "quote"):
        bullet_top = Inches(2.5)
        for i, bullet in enumerate(bullets):
            bullet_text = f"  •  {bullet}"
            _add_text_box(
                slide,
                left=Inches(1.5), top=bullet_top + Inches(i * 0.55),
                width=Inches(10), height=Inches(0.45),
                text=bullet_text,
                font_name=FONT_BODY, font_size=Pt(20),
                font_color=WHITE
            )

    # Citation (if present, at bottom — above corner ornaments)
    if citation:
        _add_separator_line(slide, Inches(1.5), Inches(5.5), Inches(5), GOLD_DIM)
        _add_text_box(
            slide,
            left=Inches(1.5), top=Inches(5.6),
            width=Inches(10), height=Inches(0.7),
            text=f"📚 {citation}",
            font_name=FONT_BODY, font_size=Pt(11),
            font_color=DIM
        )

    # Speaker notes = narration text
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = narration

    return slide


def build_presentation(script: dict) -> Presentation:
    """Build a full PPTX presentation from a script."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    slides = script.get("slides", [])
    total = len(slides)

    for i, slide_data in enumerate(slides):
        build_slide(prs, slide_data, i + 1, total)

    return prs


def build_from_script_file(script_path: str | Path, output_path: str | Path = None) -> Path:
    """Load a script.json and generate a PPTX file."""
    script_path = Path(script_path)
    with open(script_path) as f:
        script = json.load(f)

    if output_path is None:
        output_path = script_path.parent / "slides.pptx"
    else:
        output_path = Path(output_path)

    prs = build_presentation(script)
    prs.save(str(output_path))
    print(f"  📊 PPTX saved: {output_path} ({len(script['slides'])} slides)")
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python slide_builder.py <script.json> [output.pptx]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    build_from_script_file(sys.argv[1], out)
