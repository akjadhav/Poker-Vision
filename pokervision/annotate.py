from __future__ import annotations

from PIL import Image, ImageDraw

from .analyzer import FrameObservation
from .config import LayoutConfig
from .rendering import cached_font


CARD_COLOR = (255, 213, 74)
TEXT_COLOR = (101, 209, 255)
PLAYER_COLOR = (126, 231, 135)
CHIP_COLOR = (255, 152, 77)


def annotate_frame(image: Image.Image, layout: LayoutConfig, observation: FrameObservation) -> Image.Image:
    annotated = image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    font = cached_font(16, bold=True)

    community_by_slot = {item.slot: item for item in observation.community}
    for slot in layout.community:
        detection = community_by_slot.get(slot.name)
        label = detection.card if detection and detection.card else "-"
        draw.rectangle(slot.rect.to_box(), outline=CARD_COLOR, width=3)
        draw_label(draw, slot.rect.x, slot.rect.y - 22, f"{slot.name}: {label}", CARD_COLOR, font)

    for player in layout.players:
        detections = {item.slot: item for item in observation.players.get(player.name, [])}
        for slot in player.cards:
            detection = detections.get(slot.name)
            label = detection.card if detection and detection.card else "-"
            draw.rectangle(slot.rect.to_box(), outline=PLAYER_COLOR, width=3)
            draw_label(draw, slot.rect.x, slot.rect.y - 22, f"{player.name}: {label}", PLAYER_COLOR, font)

    for region in layout.texts:
        detection = observation.texts.get(region.name)
        label = detection.text if detection else ""
        draw.rectangle(region.rect.to_box(), outline=TEXT_COLOR, width=3)
        draw_label(draw, region.rect.x, region.rect.y - 22, f"{region.name}: {label}", TEXT_COLOR, font)

    chips_by_name = {item.name: item for item in observation.chips}
    for region in layout.chips:
        detection = chips_by_name.get(region.name)
        pixels = detection.chip_pixels if detection else 0
        owner = f"{region.owner} " if region.owner else ""
        draw.rectangle(region.rect.to_box(), outline=CHIP_COLOR, width=3)
        label_y = region.rect.y + region.rect.h + 4 if region.kind == "pot" else region.rect.y - 22
        draw_label(draw, region.rect.x, label_y, f"{owner}{region.name}: {pixels}", CHIP_COLOR, font)

    return annotated


def draw_label(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    font,
) -> None:
    bbox = draw.textbbox((x, y), text, font=font)
    pad = 3
    draw.rectangle(
        (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad),
        fill=(17, 22, 28),
    )
    draw.text((x, y), text, font=font, fill=color)
