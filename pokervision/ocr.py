from __future__ import annotations

import string
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .rendering import cached_font
from .rendering import draw_centered_text
from .templates import similarity


OCR_ALPHABET = string.ascii_uppercase + string.digits + "$.,:-/"


@dataclass(frozen=True)
class OCRResult:
    text: str
    score: float


def foreground_mask(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    bright = gray > 145
    dark = gray < 90
    total = max(1, gray.size)
    candidates = []
    for mask in (bright, dark):
        ratio = float(mask.sum()) / total
        if 0.003 <= ratio <= 0.65:
            candidates.append((ratio, mask))
    if candidates:
        return min(candidates, key=lambda item: item[0])[1]
    return bright if gray.mean() < 128 else dark


def tight_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def normalize_glyph(image: Image.Image, size: tuple[int, int] = (20, 28)) -> np.ndarray:
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    corners = np.array([gray[0, 0], gray[0, -1], gray[-1, 0], gray[-1, -1]])
    if corners.mean() < 128 and gray.max() > gray.min():
        mask = gray > 127
    else:
        mask = foreground_mask(image)
    bbox = tight_bbox(mask)
    if bbox is None:
        return np.zeros((size[1], size[0]), dtype=np.float32)
    x1, y1, x2, y2 = bbox
    crop = Image.fromarray((mask[y1:y2, x1:x2].astype(np.uint8) * 255), mode="L")
    canvas = Image.new("L", (max(crop.width + 6, 8), max(crop.height + 6, 8)), 0)
    canvas.paste(crop, (3, 3))
    resized = canvas.resize(size, Image.Resampling.BILINEAR)
    return np.asarray(resized, dtype=np.float32) / 255.0


def split_glyphs(mask: np.ndarray) -> list[tuple[int, int] | None]:
    columns = mask.any(axis=0)
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for idx, active in enumerate(columns):
        if active and start is None:
            start = idx
        elif not active and start is not None:
            if idx - start >= 2:
                runs.append((start, idx))
            start = None
    if start is not None and len(columns) - start >= 2:
        runs.append((start, len(columns)))

    if not runs:
        return []

    merged: list[tuple[int, int] | None] = []
    previous = runs[0]
    for current in runs[1:]:
        gap = current[0] - previous[1]
        if gap <= 2:
            previous = (previous[0], current[1])
        else:
            merged.append(previous)
            if gap >= 9:
                merged.append(None)
            previous = current
    merged.append(previous)
    return merged


class GlyphOCR:
    def __init__(
        self,
        alphabet: str = OCR_ALPHABET,
        font_size: int = 26,
        glyph_size: tuple[int, int] = (20, 28),
    ) -> None:
        self.alphabet = alphabet
        self.font = cached_font(font_size, bold=True)
        self.glyph_size = glyph_size
        self.templates = self._build_templates()

    def _build_templates(self) -> dict[str, np.ndarray]:
        templates: dict[str, np.ndarray] = {}
        for char in self.alphabet:
            image = Image.new("L", (48, 56), 0)
            draw = ImageDraw.Draw(image)
            draw.text((8, 8), char, font=self.font, fill=255)
            templates[char] = normalize_glyph(image, self.glyph_size)
        return templates

    def read(self, image: Image.Image) -> OCRResult:
        working = image
        if image.width > 16 and image.height > 16:
            working = image.crop((4, 4, image.width - 4, image.height - 4))
        mask = foreground_mask(working)
        bbox = tight_bbox(mask)
        if bbox is None:
            return OCRResult("", 0.0)

        x1, y1, x2, y2 = bbox
        cropped_mask = mask[y1:y2, x1:x2]
        segments = split_glyphs(cropped_mask)
        if not segments:
            return OCRResult("", 0.0)

        chars: list[str] = []
        scores: list[float] = []
        for segment in segments:
            if segment is None:
                if chars and chars[-1] != " ":
                    chars.append(" ")
                continue
            sx1, sx2 = segment
            glyph_mask = cropped_mask[:, sx1:sx2]
            glyph_image = Image.fromarray((glyph_mask.astype(np.uint8) * 255), mode="L")
            normalized = normalize_glyph(glyph_image, self.glyph_size)
            best_char = ""
            best_score = -1.0
            for char, template in self.templates.items():
                score = similarity(normalized, template)
                if score > best_score:
                    best_char = char
                    best_score = score
            chars.append(best_char)
            scores.append(best_score)

        text = "".join(chars).strip()
        return OCRResult(text, float(np.mean(scores)) if scores else 0.0)


class CandidateOCR:
    def __init__(self, font_size: int = 26, tracking: int = 2) -> None:
        self.font = cached_font(font_size, bold=True)
        self.tracking = tracking

    def read(self, image: Image.Image, candidates: list[str]) -> OCRResult:
        if not candidates:
            return OCRResult("", 0.0)

        working = image
        if image.width > 16 and image.height > 16:
            working = image.crop((4, 4, image.width - 4, image.height - 4))
        target = foreground_mask(working).astype(np.float32)

        best_text = ""
        best_score = -1.0
        for candidate in candidates:
            rendered = Image.new("L", working.size, 0)
            draw = ImageDraw.Draw(rendered)
            draw_centered_text(draw, (0, 0, working.width, working.height), candidate.upper(), self.font, 255, tracking=self.tracking)
            template = foreground_mask(rendered).astype(np.float32)
            score = similarity(target, template)
            if score > best_score:
                best_text = candidate.upper()
                best_score = score
        return OCRResult(best_text, best_score)
