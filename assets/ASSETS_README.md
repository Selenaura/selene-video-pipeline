# Assets — Selene Video Pipeline

## Backgrounds (1920x1080 slide backgrounds)

| File | Use for | Description |
|---|---|---|
| `bg_content.png` | Content slides (default) | Dark celestial, blue nebula center, gold star dots |
| `bg_science.png` | Science/citation slides | Dark with sacred geometry pattern, blue-teal glow |
| `bg_practice.png` | Practice/meditation slides | Dark with teal radial glow center, gold stars |
| `bg_title.png` | Title slides | Dark with gold light from top center, gold dust |
| `bg_quote.png` | Quote slides | Dark with warm gold glow from upper-left corner |
| `bg_summary.png` | Summary/closing slides | Dark with violet-gold aurora arc at top |

## Decorations (overlay elements)

| File | Use for | How to use |
|---|---|---|
| `moon_face.png` | Title slides | Center-top, ~200px wide. The hero element. |
| `corner_ornaments.png` | All slides (optional) | Contains 4 corners in one image. Crop each corner and place at slide edges. Reduce opacity to 40-60%. |
| `divider_star.png` | Between title and content | Center horizontally below title text. ~60% of slide width. |
| `constellation_overlay.png` | Content/science slides | Full-slide overlay at 8-15% opacity. Too dense at 100%. |

## How Code should use these

```python
# In slide builder (python-pptx):
from pptx.util import Inches

# 1. Set background image based on slide type
slide_type_bg = {
    "title": "bg_title.png",
    "hook": "bg_title.png", 
    "content": "bg_content.png",
    "science": "bg_science.png",
    "practice": "bg_practice.png",
    "quote": "bg_quote.png",
    "summary": "bg_summary.png",
}

# 2. Add background as full-slide image (behind everything)
bg_path = f"assets/backgrounds/{slide_type_bg[slide_type]}"
slide.shapes.add_picture(bg_path, 0, 0, prs.slide_width, prs.slide_height)

# 3. Add moon on title slides
if slide_type == "title":
    moon = slide.shapes.add_picture("assets/decorations/moon_face.png", 
                                      Inches(6.5), Inches(0.3), 
                                      Inches(3), Inches(3))

# 4. Add divider below titles
divider = slide.shapes.add_picture("assets/decorations/divider_star.png",
                                     Inches(3), Inches(1.8),
                                     Inches(10), Inches(0.5))
```
