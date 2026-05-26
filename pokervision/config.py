from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rect":
        return cls(int(data["x"]), int(data["y"]), int(data["w"]), int(data["h"]))

    def crop(self, image: Image.Image) -> Image.Image:
        return image.crop((self.x, self.y, self.x + self.w, self.y + self.h))

    def to_box(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.w, self.y + self.h

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass(frozen=True)
class CardSlot:
    name: str
    rect: Rect

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardSlot":
        return cls(str(data["name"]), Rect.from_dict(data["rect"]))


@dataclass(frozen=True)
class PlayerConfig:
    name: str
    cards: list[CardSlot]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerConfig":
        return cls(str(data["name"]), [CardSlot.from_dict(item) for item in data.get("cards", [])])


@dataclass(frozen=True)
class TextRegion:
    name: str
    kind: str
    rect: Rect
    candidates: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TextRegion":
        return cls(
            str(data["name"]),
            str(data.get("kind", data["name"])),
            Rect.from_dict(data["rect"]),
            [str(item) for item in data.get("candidates", [])],
        )


@dataclass(frozen=True)
class LayoutConfig:
    frame_step: int
    min_card_score: float
    min_text_score: float
    community: list[CardSlot]
    players: list[PlayerConfig]
    texts: list[TextRegion]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LayoutConfig":
        return cls(
            frame_step=max(1, int(data.get("frame_step", 1))),
            min_card_score=float(data.get("min_card_score", 0.82)),
            min_text_score=float(data.get("min_text_score", 0.50)),
            community=[CardSlot.from_dict(item) for item in data.get("community", [])],
            players=[PlayerConfig.from_dict(item) for item in data.get("players", [])],
            texts=[TextRegion.from_dict(item) for item in data.get("texts", [])],
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "LayoutConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_step": self.frame_step,
            "min_card_score": self.min_card_score,
            "min_text_score": self.min_text_score,
            "community": [
                {"name": slot.name, "rect": slot.rect.to_dict()}
                for slot in self.community
            ],
            "players": [
                {
                    "name": player.name,
                    "cards": [
                        {"name": slot.name, "rect": slot.rect.to_dict()}
                        for slot in player.cards
                    ],
                }
                for player in self.players
            ],
            "texts": [
                {
                    "name": text.name,
                    "kind": text.kind,
                    "rect": text.rect.to_dict(),
                    "candidates": text.candidates,
                }
                for text in self.texts
            ],
        }

    def write_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")
