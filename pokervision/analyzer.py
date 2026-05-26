from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

from .config import LayoutConfig
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
class FrameObservation:
    frame_index: int
    time_s: float | None
    community: list[CardDetection]
    players: dict[str, list[CardDetection]]
    texts: dict[str, TextDetection]

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
            self._read_card(image, slot.name, slot.rect.crop(image))
            for slot in self.layout.community
        ]

        players: dict[str, list[CardDetection]] = {}
        for player in self.layout.players:
            players[player.name] = [
                self._read_card(image, slot.name, slot.rect.crop(image))
                for slot in player.cards
            ]

        texts: dict[str, TextDetection] = {}
        for region in self.layout.texts:
            crop = region.rect.crop(image)
            result = self.ocr.read(crop)
            if region.candidates:
                candidate_result = self.candidate_ocr.read(crop, region.candidates)
                if candidate_result.score >= result.score:
                    result = candidate_result
            text = result.text if result.score >= self.layout.min_text_score else ""
            texts[region.name] = TextDetection(region.name, region.kind, text, result.score)

        return FrameObservation(frame_index, time_s, community, players, texts)

    def _read_card(self, image: Image.Image, slot_name: str, crop: Image.Image) -> CardDetection:
        result: MatchResult | None = self.card_recognizer.recognize(crop)
        if result is None:
            raw = self.card_recognizer.matcher.match(crop)
            return CardDetection(slot_name, None, raw.score)
        return CardDetection(slot_name, result.label, result.score)
