from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .cards import Card


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


@lru_cache(maxsize=128)
def cached_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return load_font(size, bold)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    tracking: int = 0,
) -> None:
    left, top, right, bottom = box
    if tracking > 0:
        widths = [draw.textlength(char, font=font) for char in text]
        width = sum(widths) + tracking * max(0, len(text) - 1)
        bbox = draw.textbbox((0, 0), text, font=font)
        height = bbox[3] - bbox[1]
        x = left + (right - left - width) / 2
        y = top + (bottom - top - height) / 2 - 1
        for char, char_width in zip(text, widths):
            draw.text((x, y), char, font=font, fill=fill)
            x += char_width + tracking
        return
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + (right - left - width) / 2
    y = top + (bottom - top - height) / 2 - 1
    draw.text((x, y), text, font=font, fill=fill)


def render_card(card: Card, size: tuple[int, int] = (72, 100)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, (18, 92, 68))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=8, fill=(246, 246, 238), outline=(34, 34, 34), width=2)
    fill = (188, 35, 35) if card.is_red else (24, 24, 24)
    corner_font = cached_font(max(14, int(height * 0.18)), bold=True)
    center_font = cached_font(max(24, int(height * 0.34)), bold=True)
    draw.text((7, 5), card.rank, font=corner_font, fill=fill)
    draw.text((7, 23), card.suit, font=corner_font, fill=fill)
    draw_centered_text(draw, (0, 18, width, height - 10), card.rank + card.suit, center_font, fill)
    return image


def render_blank_card(size: tuple[int, int] = (72, 100)) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, (18, 92, 68))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=8, fill=(36, 78, 116), outline=(234, 234, 224), width=2)
    return image
