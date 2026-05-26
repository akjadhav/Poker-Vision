from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .cards import Card
from .config import LayoutConfig
from .pipeline import run_pipeline
from .rendering import cached_font, draw_centered_text, render_blank_card, render_card


FRAME_SIZE = (1280, 720)


DEMO_STATES = [
    {
        "board": [],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 30",
        "action": "BOB CHECK",
    },
    {
        "board": [],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 90",
        "action": "ALICE RAISE 60",
    },
    {
        "board": ["7H", "8D", "2C"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 150",
        "action": "BOB CALL 60",
    },
    {
        "board": ["7H", "8D", "2C", "QS"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 270",
        "action": "ALICE BET 120",
    },
    {
        "board": ["7H", "8D", "2C", "QS", "AD"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 390",
        "action": "BOB FOLD",
    },
]


def demo_layout() -> LayoutConfig:
    return LayoutConfig.from_dict(
        {
            "frame_step": 1,
            "min_card_score": 0.82,
            "min_text_score": 0.50,
            "community": [
                {"name": f"board_{idx + 1}", "rect": {"x": 442 + idx * 84, "y": 286, "w": 72, "h": 100}}
                for idx in range(5)
            ],
            "players": [
                {
                    "name": "ALICE",
                    "cards": [
                        {"name": "alice_1", "rect": {"x": 290, "y": 506, "w": 72, "h": 100}},
                        {"name": "alice_2", "rect": {"x": 374, "y": 506, "w": 72, "h": 100}},
                    ],
                },
                {
                    "name": "BOB",
                    "cards": [
                        {"name": "bob_1", "rect": {"x": 836, "y": 506, "w": 72, "h": 100}},
                        {"name": "bob_2", "rect": {"x": 920, "y": 506, "w": 72, "h": 100}},
                    ],
                },
            ],
            "texts": [
                {
                    "name": "pot",
                    "kind": "pot",
                    "rect": {"x": 560, "y": 212, "w": 160, "h": 44},
                    "candidates": [state["pot"] for state in DEMO_STATES],
                },
                {
                    "name": "action",
                    "kind": "action",
                    "rect": {"x": 482, "y": 414, "w": 318, "h": 46},
                    "candidates": [state["action"] for state in DEMO_STATES],
                },
            ],
        }
    )


def render_demo_frame(state: dict, layout: LayoutConfig) -> Image.Image:
    image = Image.new("RGB", FRAME_SIZE, (20, 25, 31))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, FRAME_SIZE[0], FRAME_SIZE[1]), fill=(24, 30, 38))
    draw.ellipse((230, 150, 1050, 650), fill=(20, 111, 80), outline=(201, 158, 86), width=8)
    draw.ellipse((340, 230, 940, 560), outline=(33, 139, 99), width=4)

    title_font = cached_font(28, bold=True)
    small_font = cached_font(20, bold=True)
    overlay_font = cached_font(26, bold=True)
    draw.text((36, 30), "PokerVision Demo Broadcast", font=title_font, fill=(238, 238, 230))
    draw.text((300, 474), "ALICE", font=small_font, fill=(230, 230, 220))
    draw.text((858, 474), "BOB", font=small_font, fill=(230, 230, 220))

    board = state["board"]
    for idx, slot in enumerate(layout.community):
        card = board[idx] if idx < len(board) else None
        card_image = render_card(Card.parse(card)) if card else render_blank_card()
        image.paste(card_image, (slot.rect.x, slot.rect.y))

    player_map = {player.name: player for player in layout.players}
    for player, cards in state["players"].items():
        for idx, card in enumerate(cards):
            slot = player_map[player].cards[idx]
            image.paste(render_card(Card.parse(card)), (slot.rect.x, slot.rect.y))

    text_regions = {region.name: region for region in layout.texts}
    draw_text_panel(draw, text_regions["pot"].rect.to_box(), state["pot"], overlay_font)
    draw_text_panel(draw, text_regions["action"].rect.to_box(), state["action"], overlay_font)
    return image


def draw_text_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font,
) -> None:
    draw.rounded_rectangle(box, radius=6, fill=(8, 12, 16), outline=(210, 210, 190), width=2)
    draw_centered_text(draw, box, text, font, (246, 246, 236), tracking=2)


def create_demo_frames(out_dir: str | Path) -> tuple[Path, LayoutConfig]:
    out_path = Path(out_dir)
    frames_dir = out_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    layout = demo_layout()
    layout.write_json(out_path / "layout.json")
    for idx, state in enumerate(DEMO_STATES):
        frame = render_demo_frame(state, layout)
        frame.save(frames_dir / f"frame_{idx:04d}.png")
    return frames_dir, layout


def run_demo(out_dir: str | Path):
    out_path = Path(out_dir)
    frames_dir, layout = create_demo_frames(out_path)
    return run_pipeline(frames_dir, layout, out_path)
