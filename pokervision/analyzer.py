from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from .config import LayoutConfig, Rect
from .ocr import CandidateOCR, GlyphOCR, OCRResult
from .templates import CardRecognizer, MatchResult


@dataclass(frozen=True)
class CardDetection:
    slot: str
    card: str | None
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"slot": self.slot, "card": self.card, "score": round(self.score, 4)}


@dataclass(frozen=True)
class TextDetection:
    name: str
    kind: str
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "text": self.text, "score": round(self.score, 4)}


@dataclass(frozen=True)
class ChipDetection:
    name: str
    kind: str
    owner: str | None
    chip_pixels: int
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "owner": self.owner,
            "chip_pixels": self.chip_pixels,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class FrameObservation:
    frame_index: int
    time_s: float | None
    community: list[CardDetection]
    players: dict[str, list[CardDetection]]
    texts: dict[str, TextDetection]
    chips: list[ChipDetection] = field(default_factory=list)

    def community_cards(self) -> list[str]:
        return [item.card for item in self.community if item.card]

    def player_cards(self, player: str) -> list[str]:
        return [item.card for item in self.players.get(player, []) if item.card]

    def text_value(self, name: str) -> str:
        detection = self.texts.get(name)
        return detection.text if detection else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "time_s": self.time_s,
            "community": [item.to_dict() for item in self.community],
            "players": {
                player: [item.to_dict() for item in detections]
                for player, detections in self.players.items()
            },
            "texts": {
                name: detection.to_dict()
                for name, detection in self.texts.items()
            },
            "chips": [item.to_dict() for item in self.chips],
        }


class FrameAnalyzer:
    def __init__(
        self,
        layout: LayoutConfig,
        card_recognizer: CardRecognizer | None = None,
        ocr: GlyphOCR | None = None,
    ) -> None:
        self.layout = layout
        self.card_recognizer = card_recognizer or CardRecognizer.from_standard_deck(min_score=layout.min_card_score)
        self.ocr = ocr or GlyphOCR()
        self.candidate_ocr = CandidateOCR()

    def analyze(self, frame: Image.Image, frame_index: int, time_s: float | None = None) -> FrameObservation:
        image = frame.convert("RGB")
        community = [
            self._read_card(image, slot.name, self._card_crop(image, slot.rect))
            for slot in self.layout.community
        ]

        players: dict[str, list[CardDetection]] = {}
        for player in self.layout.players:
            players[player.name] = [
                self._read_card(image, slot.name, self._card_crop(image, slot.rect))
                for slot in player.cards
            ]

        texts: dict[str, TextDetection] = {}
        for region in self.layout.texts:
            crop = region.rect.crop(image)
            result = self.ocr.read(crop)
            if region.candidates:
                candidate_result = self.candidate_ocr.read(crop, region.candidates)
                if candidate_result.score >= self.layout.min_text_score or candidate_result.score >= result.score:
                    result = candidate_result
            text = result.text if result.score >= self.layout.min_text_score else ""
            texts[region.name] = TextDetection(region.name, region.kind, text, result.score)

        chips = [
            self._read_chips(region.name, region.kind, region.owner, region.rect.crop(image))
            for region in self.layout.chips
        ]

        return FrameObservation(frame_index, time_s, community, players, texts, chips)

    def _card_crop(self, image: Image.Image, rect: Rect) -> Image.Image:
        margin = self.layout.card_search_margin
        if margin <= 0:
            return rect.crop(image)
        return image.crop(
            (
                max(0, rect.x - margin),
                max(0, rect.y - margin),
                min(image.width, rect.x + rect.w + margin),
                min(image.height, rect.y + rect.h + margin),
            )
        )

    def _read_card(self, image: Image.Image, slot_name: str, crop: Image.Image) -> CardDetection:
        result: MatchResult | None = self.card_recognizer.recognize(crop)
        if result is None:
            raw = self.card_recognizer.best_match(crop)
            return CardDetection(slot_name, None, raw.score)
        return CardDetection(slot_name, result.label, result.score)

    def _read_chips(self, name: str, kind: str, owner: str | None, crop: Image.Image) -> ChipDetection:
        array = np.asarray(crop.convert("RGB"), dtype=np.uint8)
        red = (array[:, :, 0] > 135) & (array[:, :, 1] < 120) & (array[:, :, 2] < 130)
        blue = (array[:, :, 2] > 135) & (array[:, :, 0] < 140) & (array[:, :, 1] < 170)
        white = (array[:, :, 0] > 205) & (array[:, :, 1] > 205) & (array[:, :, 2] > 190)
        yellow = (array[:, :, 0] > 190) & (array[:, :, 1] > 150) & (array[:, :, 2] < 120)
        mask = red | blue | white | yellow
        chip_pixels = int(mask.sum())
        score = min(1.0, chip_pixels / max(1, crop.width * crop.height * 0.18))
        return ChipDetection(name, kind, owner, chip_pixels, score)
