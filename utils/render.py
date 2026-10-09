"""Shared text-to-image rendering for tasks.

Fonts resolve in this order:
1. Bundled ``assets/fonts/`` (works everywhere, incl. Streamlit Cloud).
2. System DejaVu / Liberation paths (local dev convenience).
3. Pillow's built-in default (last resort, Latin-only).
"""

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"



def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in [
        _ASSETS_DIR / "Montserrat[wght].ttf",
        _ASSETS_DIR / "DejaVuSans.ttf"
    ]:
        try:
            font = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        try:  # variable font: default instance is Thin, use Medium instead
            font.set_variation_by_axes([500])
        except (AttributeError, OSError):
            pass
        return font
    return ImageFont.load_default()


def render_text(
    text: str, font_size: int = 64, padding: int = 30, uppercase: bool = False
) -> Image.Image:
    if uppercase:
        text = text.upper()
    font = get_font(font_size)
    dummy = Image.new("RGB", (10, 10))
    box = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    # textbbox can return floats; Image.new expects integer sizes
    img = Image.new(
        "RGB",
        (
            int(math.ceil(box[2] - box[0])) + padding * 2,
            int(math.ceil(box[3] - box[1])) + padding * 2,
        ),
        "white",
    )
    ImageDraw.Draw(img).text(
        (int(math.floor(padding - box[0])), int(math.floor(padding - box[1]))),
        text,
        font=font,
        fill="black",
    )
    return img


def _wrap_text(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int
) -> list[str]:
    words = text.strip().split()
    if not words:
        return []
    dummy = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy)
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def with_instruction(
    content: Image.Image,
    instruction: str,
    font_size: int = 32,
    padding: int = 30,
    gap: int = 16,
    min_width: int = 520,
) -> Image.Image:
    """Stack a short instruction line(s) on top of a finished task image.

    The canvas is at least ``min_width`` wide, so short words (like "cat")
    still get a balanced image with room for the instruction to wrap.
    """
    instruction = instruction.strip()
    if not instruction:
        return content
    font = get_font(font_size)
    width = max(content.width, min_width)
    max_text_width = width - 2 * padding
    lines = _wrap_text(instruction, font, max_text_width)
    dummy = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy)
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [box[3] - box[1] for box in boxes]
    leading = max(4, font_size // 8)
    text_h = sum(line_heights) + leading * (len(lines) - 1) if lines else 0
    text_w = max((box[2] - box[0] for box in boxes), default=0)
    header_w = max(width, int(math.ceil(text_w)) + 2 * padding)
    header_h = padding + int(math.ceil(text_h)) + gap
    img = Image.new("RGB", (header_w, header_h + content.height), "white")
    draw = ImageDraw.Draw(img)
    y = padding
    for line, box, lh in zip(lines, boxes, line_heights):
        x = (header_w - (box[2] - box[0])) // 2
        draw.text((x - box[0], y - box[1]), line, font=font, fill=(80, 80, 80))
        y += lh + leading
    img.paste(content, ((header_w - content.width) // 2, header_h))
    return img
