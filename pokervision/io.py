from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from PIL import Image, ImageSequence


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def iter_frames(path: str | Path, every: int = 1) -> Iterator[tuple[int, Image.Image]]:
    source = Path(path)
    every = max(1, every)
    if source.is_dir():
        files = [
            item for item in sorted(source.iterdir())
            if item.suffix.lower() in IMAGE_EXTENSIONS
        ]
        for idx, file_path in enumerate(files):
            if idx % every == 0:
                with Image.open(file_path) as image:
                    yield idx, image.convert("RGB")
        return

    suffix = source.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        with Image.open(source) as image:
            yield 0, image.convert("RGB")
        return

    if suffix == ".gif":
        with Image.open(source) as image:
            for idx, frame in enumerate(ImageSequence.Iterator(image)):
                if idx % every == 0:
                    yield idx, frame.convert("RGB")
        return

    if suffix in VIDEO_EXTENSIONS:
        yield from _iter_video_frames(source, every)
        return

    raise ValueError(f"unsupported input type: {source}")


def _iter_video_frames(path: Path, every: int) -> Iterator[tuple[int, Image.Image]]:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "video files require opencv-python. Export the clip to frames or install the optional video dependency."
        ) from exc

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"could not open video: {path}")
    idx = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if idx % every == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yield idx, Image.fromarray(rgb)
            idx += 1
    finally:
        capture.release()


def write_json(path: str | Path, data: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def save_gif(frames: Iterable[Image.Image], path: str | Path, duration_ms: int = 700) -> None:
    images = [frame.convert("P", palette=Image.Palette.ADAPTIVE) for frame in frames]
    if not images:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        target,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,
    )
