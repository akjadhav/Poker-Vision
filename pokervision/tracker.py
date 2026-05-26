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
    def __init__(self) -> None:
        self.events: list[TimelineEvent] = []
        self.last_board: list[str] = []
        self.last_pot_text = ""
        self.last_action_text = ""
        self.last_player_cards: dict[str, list[str]] = {}
        self.final_pot: int | None = None

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
            },
            "events": [event.to_dict() for event in self.events],
        }
