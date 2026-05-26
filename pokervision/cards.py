from __future__ import annotations

from dataclasses import dataclass


RANKS = "23456789TJQKA"
SUITS = "CDHS"
RED_SUITS = {"D", "H"}


@dataclass(frozen=True, order=True)
class Card:
    rank: str
    suit: str

    def __post_init__(self) -> None:
        rank = self.rank.upper()
        suit = self.suit.upper()
        if rank == "10":
            rank = "T"
        if rank not in RANKS:
            raise ValueError(f"invalid rank: {self.rank!r}")
        if suit not in SUITS:
            raise ValueError(f"invalid suit: {self.suit!r}")
        object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "suit", suit)

    @classmethod
    def parse(cls, value: str) -> "Card":
        clean = value.strip().upper()
        if len(clean) == 3 and clean.startswith("10"):
            return cls("T", clean[2])
        if len(clean) != 2:
            raise ValueError(f"card must look like AS or TD: {value!r}")
        return cls(clean[0], clean[1])

    @property
    def code(self) -> str:
        return f"{self.rank}{self.suit}"

    @property
    def is_red(self) -> bool:
        return self.suit in RED_SUITS

    def __str__(self) -> str:
        return self.code


def full_deck() -> list[Card]:
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]
