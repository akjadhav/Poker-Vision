from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .cards import Card, full_deck
from .rendering import render_card


def image_to_array(image: Image.Image, size: tuple[int, int]) -> np.ndarray:
    resized = image.convert("RGB").resize(size, Image.Resampling.BILINEAR)
    return np.asarray(resized, dtype=np.float32) / 255.0


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a - b) ** 2))
    return max(0.0, min(1.0, 1.0 - mse * 3.0))


@dataclass(frozen=True)
class MatchResult:
    label: str
    score: float


class TemplateMatcher:
    def __init__(self, templates: dict[str, Image.Image], size: tuple[int, int]) -> None:
        if not templates:
            raise ValueError("at least one template is required")
        self.size = size
        self.templates = {
            label: image_to_array(template, size)
            for label, template in templates.items()
        }

    def match(self, image: Image.Image) -> MatchResult:
        target = image_to_array(image, self.size)
        return self._match_array(target)

    def match_region(self, image: Image.Image) -> MatchResult:
        width, height = self.size
        if image.width < width or image.height < height:
            return self.match(image)

        working = image.convert("RGB")
        best = MatchResult("", -1.0)
        for y in range(0, image.height - height + 1):
            for x in range(0, image.width - width + 1):
                crop = working.crop((x, y, x + width, y + height))
                result = self.match(crop)
                if result.score > best.score:
                    best = result
        return best

    def _match_array(self, target: np.ndarray) -> MatchResult:
        best_label = ""
        best_score = -1.0
        for label, template in self.templates.items():
            score = similarity(target, template)
            if score > best_score:
                best_label = label
                best_score = score
        return MatchResult(best_label, best_score)


class CardRecognizer:
    def __init__(self, matcher: TemplateMatcher, min_score: float = 0.82) -> None:
        self.matcher = matcher
        self.min_score = min_score

    @classmethod
    def from_standard_deck(cls, card_size: tuple[int, int] = (72, 100), min_score: float = 0.82) -> "CardRecognizer":
        templates = {card.code: render_card(card, card_size) for card in full_deck()}
        return cls(TemplateMatcher(templates, card_size), min_score)

    @classmethod
    def from_template_dir(
        cls,
        directory: str | Path,
        card_size: tuple[int, int] = (72, 100),
        min_score: float = 0.82,
    ) -> "CardRecognizer":
        path = Path(directory)
        templates: dict[str, Image.Image] = {}
        for file_path in sorted(path.iterdir()):
            if file_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            label = file_path.stem.upper().replace("10", "T")
            Card.parse(label)
            templates[label] = Image.open(file_path).convert("RGB")
        return cls(TemplateMatcher(templates, card_size), min_score)

    def best_match(self, image: Image.Image) -> MatchResult:
        return self.matcher.match_region(image)

    def recognize(self, image: Image.Image) -> MatchResult | None:
        result = self.best_match(image)
        if result.score < self.min_score:
            return None
        return result
