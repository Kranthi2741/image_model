"""Render exact Unicode copy in model-selected space, with font coverage checks."""
import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageColor, features

FONT_NAMES = {"English": "NotoSans", "Hindi": "NotoSansDevanagari", "Marathi": "NotoSansDevanagari",
              "Bengali": "NotoSansBengali", "Telugu": "NotoSansTelugu",
              "Tamil": "NotoSansTamil", "Gujarati": "NotoSansGujarati"}

def validate_box(box):
    if (not isinstance(box, list) or len(box) != 4 or
        any(type(v) not in (int, float) or not math.isfinite(v) for v in box)):
        raise ValueError("copy_box must have four finite numbers")
    x, y, w, h = box
    if min(x, y) < 0 or w < .30 or h < .20 or x + w > 1 or y + h > 1:
        raise ValueError("copy_box is outside canvas or too small")
    if x < .24 and y < .13:
        raise ValueError("copy_box overlaps the logo region")
    return box

def font_for(language, text, size, bold=False, serif=False):
    from fontTools.ttLib import TTFont
    name = FONT_NAMES.get(language)
    if name and serif:
        name = name.replace("NotoSans", "NotoSerif")
    if not name:
        raise ValueError("Unsupported poster language: " + language)
    if language != "English" and not features.check_feature("raqm"):
        raise RuntimeError("Pillow RAQM shaping is required for Indian languages.")
    root = Path(os.getenv("CAMPAIGN_FONT_DIR", "/usr/share/fonts/truetype/noto"))
    path = root / (name + ("-Bold.ttf" if bold else "-Regular.ttf"))
    if not path.is_file():
        raise RuntimeError(f"Missing font {path}. Install fonts-noto-core; see GPU_SETUP.md.")
    with TTFont(path) as font:
        cmap = font.getBestCmap()
        missing = [c for c in text if not c.isspace() and c not in "\u200c\u200d" and ord(c) not in cmap]
    if missing:
        raise ValueError(f"Selected font cannot render: {''.join(sorted(set(missing)))}")
    return ImageFont.truetype(str(path), size)

def wrapped(draw, text, font, width):
    lines = []
    for word in text.split():
        if draw.textlength(word, font=font) > width:
            return None
        if lines and draw.textlength(lines[-1] + " " + word, font=font) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines

def typeset(base, brief, logo_path):
    x, y, w, h = validate_box(brief["copy_box"])
    image = base.convert("RGBA")
    W, H = image.size
    left, top, width, height = int(x*W), int(y*H), int(w*W), int(h*H)
    pad = max(12, int(W*.018))
    heading = brief["visible_copy"]["headline"]
    body = brief["visible_copy"].get("short_copy", "")
    language = brief.get("language", "English")
    layer = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(layer)
    for size in range(int(W*.065), max(17, int(W*.021)), -2):
        large = font_for(language, heading, size, True, brief.get("font_style") == "serif")
        small = font_for(language, body, max(16, int(size*.53)))
        title = wrapped(draw, heading, large, width-2*pad)
        lines = wrapped(draw, body, small, width-2*pad)
        lh, sh = sum(large.getmetrics()) + 4, sum(small.getmetrics()) + 3
        if title and lines is not None and len(title)*lh + len(lines)*sh + 3*pad <= height:
            break
    else:
        raise ValueError("Copy does not fit the planned space. Shorten it or enlarge copy_box.")
    background = brief.get("copy_background", "#10212b")
    color = ImageColor.getrgb(brief.get("copy_color", "#ffffff"))
    if background != "transparent":
        draw.rounded_rectangle((left, top, left+width, top+height), radius=pad,
                               fill=(*ImageColor.getrgb(background), 220))
    cursor = top + pad
    for line in title:
        draw.text((left+pad, cursor), line, font=large, fill=color)
        cursor += lh
    cursor += pad
    for line in lines:
        draw.text((left+pad, cursor), line, font=small, fill=color)
        cursor += sh
    image = Image.alpha_composite(image, layer)
    with Image.open(logo_path) as original:
        logo = original.convert("RGBA")
        logo.thumbnail((int(W*.18), int(H*.08)), Image.Resampling.LANCZOS)
        image.alpha_composite(logo, (int(W*.035), int(H*.03)))
    return image.convert("RGB")
