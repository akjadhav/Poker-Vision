from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .analyzer import FrameObservation


ACTION_KEYWORDS = ("ALL IN", "RAISE", "BET", "CALL", "CHECK", "FOLD")


@dataclass(frozen=True)
class TimelineEvent:
    frame_index: int
    time_s: float | None
    type: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "time_s": self.time_s,
            "type": self.type,
            "payload": self.payload,
        }


def parse_amount(text: str) -> int | None:
    digits = re.findall(r"\d+", text.replace(",", ""))
    if not digits:
        return None
    return int("".join(digits))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.upper()).strip()


def parse_action(text: str) -> dict[str, Any]:
    clean = normalize_text(text)
    action = None
    for keyword in ACTION_KEYWORDS:
        if keyword in clean:
            action = keyword
            break
    amount = parse_amount(clean)
    player = clean
    if action:
        player = clean.split(action, 1)[0].strip()
    return {
        "raw": clean,
        "player": player or None,
        "action": action,
        "amount": amount,
    }


def street_for_board(board: list[str]) -> str:
    count = len(board)
    if count == 0:
        return "preflop"
    if count == 3:
        return "flop"
    if count == 4:
        return "turn"
    if count >= 5:
        return "river"
    return "board_update"


class HandStateTracker:
    def __init__(self, min_chip_delta: int = 120) -> None:
        self.events: list[TimelineEvent] = []
        self.last_board: list[str] = []
        self.last_pot_text = ""
        self.last_action_text = ""
        self.last_player_cards: dict[str, list[str]] = {}
        self.last_chip_levels: dict[str, int] | None = None
        self.last_chip_owners: dict[str, str | None] = {}
        self.last_chip_kinds: dict[str, str] = {}
        self.final_pot: int | None = None
        self.min_chip_delta = min_chip_delta

    def process(self, observation: FrameObservation) -> None:
        board = observation.community_cards()
        if board != self.last_board:
            self.last_board = board
            if board:
                self._append(
                    observation,
                    "street",
                    {"street": street_for_board(board), "board": board},
                )

        for player, detections in observation.players.items():
            cards = [item.card for item in detections if item.card]
            if cards and cards != self.last_player_cards.get(player):
                self.last_player_cards[player] = cards
                self._append(observation, "hole_cards", {"player": player, "cards": cards})

        for detection in observation.texts.values():
            text = normalize_text(detection.text)
            if not text:
                continue
            if detection.kind == "pot" and text != self.last_pot_text:
                self.last_pot_text = text
                self.final_pot = parse_amount(text)
                self._append(observation, "pot", {"text": text, "amount": self.final_pot})
            elif detection.kind == "action" and text != self.last_action_text:
                self.last_action_text = text
                self._append(observation, "action", parse_action(text))

        self._process_chips(observation)

    def _process_chips(self, observation: FrameObservation) -> None:
        if not observation.chips:
            return

        current = {detection.name: detection.chip_pixels for detection in observation.chips}
        self.last_chip_owners = {detection.name: detection.owner for detection in observation.chips}
        self.last_chip_kinds = {detection.name: detection.kind for detection in observation.chips}
        if self.last_chip_levels is None:
            self.last_chip_levels = current
            return

        pot_regions = [
            name for name, kind in self.last_chip_kinds.items()
            if kind == "pot"
        ]
        player_regions = [
            name for name, kind in self.last_chip_kinds.items()
            if kind == "player_stack"
        ]
        action = parse_action(self.last_action_text) if self.last_action_text else {}

        for pot_region in pot_regions:
            pot_delta = current.get(pot_region, 0) - self.last_chip_levels.get(pot_region, 0)
            if pot_delta < self.min_chip_delta:
                continue

            source_region = None
            source_delta = 0
            for player_region in player_regions:
                delta = current.get(player_region, 0) - self.last_chip_levels.get(player_region, 0)
                if delta < source_delta:
                    source_region = player_region
                    source_delta = delta

            if source_region is None or abs(source_delta) < self.min_chip_delta:
                continue

            source_owner = self.last_chip_owners.get(source_region) or source_region
            self._append(
                observation,
                "chip_movement",
                {
                    "source": source_owner,
                    "source_region": source_region,
                    "target": pot_region,
                    "visual_pot_delta_pixels": pot_delta,
                    "visual_source_delta_pixels": source_delta,
                    "action": action.get("action"),
                    "amount": action.get("amount"),
                },
            )

        self.last_chip_levels = current

    def _append(self, observation: FrameObservation, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append(
            TimelineEvent(
                frame_index=observation.frame_index,
                time_s=observation.time_s,
                type=event_type,
                payload=payload,
            )
        )

    def to_hand_history(self) -> dict[str, Any]:
        return {
            "summary": {
                "final_board": self.last_board,
                "players": self.last_player_cards,
                "final_pot": self.final_pot,
                "street": street_for_board(self.last_board),
                "chip_movements": len([event for event in self.events if event.type == "chip_movement"]),
                "final_chip_pixels": self.last_chip_levels or {},
            },
            "events": [event.to_dict() for event in self.events],
        }
