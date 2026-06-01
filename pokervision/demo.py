from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from PIL import ImageFilter

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
        "chips": {"ALICE": 5, "BOB": 5, "POT": 2},
    },
    {
        "board": [],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 90",
        "action": "ALICE RAISE 60",
        "chips": {"ALICE": 4, "BOB": 5, "POT": 4},
    },
    {
        "board": ["7H", "8D", "2C"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 150",
        "action": "BOB CALL 60",
        "chips": {"ALICE": 4, "BOB": 4, "POT": 6},
    },
    {
        "board": ["7H", "8D", "2C", "QS"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 270",
        "action": "ALICE BET 120",
        "chips": {"ALICE": 2, "BOB": 4, "POT": 9},
    },
    {
        "board": ["7H", "8D", "2C", "QS", "AD"],
        "players": {"ALICE": ["KD", "QD"], "BOB": ["AH", "TS"]},
        "pot": "POT 390",
        "action": "BOB FOLD",
        "chips": {"ALICE": 2, "BOB": 4, "POT": 9},
    },
]


DEMO_SCENARIOS = {
    "clean": "Crisp synthetic broadcast frames with exact fixed ROIs.",
    "compressed": "JPEG-compressed frames to mimic screen-recorded or streamed video.",
    "noisy": "Mild sensor/compression noise over the broadcast overlay.",
    "soft": "Slight Gaussian blur to mimic scaled or resampled footage.",
}


def demo_layout() -> LayoutConfig:
    return LayoutConfig.from_dict(
        {
            "frame_step": 1,
            "min_card_score": 0.82,
            "min_text_score": 0.50,
            "card_search_margin": 4,
            "min_chip_delta": 120,
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
            "chips": [
                {
                    "name": "alice_stack",
                    "kind": "player_stack",
                    "owner": "ALICE",
                    "rect": {"x": 198, "y": 512, "w": 72, "h": 82},
                },
                {
                    "name": "bob_stack",
                    "kind": "player_stack",
                    "owner": "BOB",
                    "rect": {"x": 1010, "y": 512, "w": 72, "h": 82},
                },
                {
                    "name": "pot_chips",
                    "kind": "pot",
                    "rect": {"x": 548, "y": 470, "w": 184, "h": 26},
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
    chip_regions = {region.name: region for region in layout.chips}
    render_chip_stack(draw, chip_regions["alice_stack"].rect.to_box(), state["chips"]["ALICE"], compact=False)
    render_chip_stack(draw, chip_regions["bob_stack"].rect.to_box(), state["chips"]["BOB"], compact=False)
    render_chip_stack(draw, chip_regions["pot_chips"].rect.to_box(), state["chips"]["POT"], compact=True)

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


def render_chip_stack(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    count: int,
    compact: bool,
) -> None:
    left, top, right, bottom = box
    colors = [
        ((214, 48, 64), (255, 220, 220)),
        ((54, 106, 210), (225, 235, 255)),
        ((238, 238, 226), (80, 80, 80)),
        ((230, 180, 58), (255, 242, 170)),
    ]
    radius = 8 if compact else 11
    step_x = 18 if compact else 21
    step_y = 18 if compact else 20
    columns = max(1, (right - left - 10) // step_x)
    for idx in range(count):
        column = idx % columns
        row = idx // columns
        cx = left + 12 + column * step_x
        cy = bottom - (10 if compact else 13) - row * step_y
        fill, stripe = colors[idx % len(colors)]
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=fill, outline=(20, 24, 28), width=2)
        draw.line((cx - radius + 4, cy, cx + radius - 4, cy), fill=stripe, width=3)
        draw.line((cx, cy - radius + 4, cx, cy + radius - 4), fill=stripe, width=3)


def apply_demo_scenario(image: Image.Image, scenario: str, frame_index: int) -> Image.Image:
    if scenario not in DEMO_SCENARIOS:
        choices = ", ".join(sorted(DEMO_SCENARIOS))
        raise ValueError(f"unknown demo scenario {scenario!r}; choose one of: {choices}")
    if scenario == "clean":
        return image
    if scenario == "compressed":
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=45, optimize=True)
        buffer.seek(0)
        return Image.open(buffer).convert("RGB")
    if scenario == "noisy":
        rng = np.random.default_rng(1000 + frame_index)
        array = np.asarray(image, dtype=np.int16)
        noise = rng.normal(0, 8, array.shape)
        return Image.fromarray(np.clip(array + noise, 0, 255).astype(np.uint8))
    if scenario == "soft":
        return image.filter(ImageFilter.GaussianBlur(radius=0.6))
    return image


def draw_text_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font,
) -> None:
    draw.rounded_rectangle(box, radius=6, fill=(8, 12, 16), outline=(210, 210, 190), width=2)
    draw_centered_text(draw, box, text, font, (246, 246, 236), tracking=2)


def create_demo_frames(out_dir: str | Path, scenario: str = "clean") -> tuple[Path, LayoutConfig]:
    out_path = Path(out_dir)
    frames_dir = out_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    layout = demo_layout()
    layout.write_json(out_path / "layout.json")
    for idx, state in enumerate(DEMO_STATES):
        frame = render_demo_frame(state, layout)
        frame = apply_demo_scenario(frame, scenario, idx)
        frame.save(frames_dir / f"frame_{idx:04d}.png")
    return frames_dir, layout


def run_demo(out_dir: str | Path, scenario: str = "clean"):
    out_path = Path(out_dir)
    frames_dir, layout = create_demo_frames(out_path, scenario=scenario)
    return run_pipeline(frames_dir, layout, out_path)
