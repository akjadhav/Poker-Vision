from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .analyzer import FrameAnalyzer, FrameObservation
from .annotate import annotate_frame
from .config import LayoutConfig
from .io import iter_frames, save_gif, write_json
from .tracker import HandStateTracker


@dataclass(frozen=True)
class PipelineResult:
    observations: list[FrameObservation]
    hand_history: dict
    annotated_paths: list[Path]


def run_pipeline(
    input_path: str | Path,
    layout: LayoutConfig,
    out_dir: str | Path,
    every: int | None = None,
    write_annotations: bool = True,
) -> PipelineResult:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    annotated_dir = out_path / "annotated"
    if write_annotations:
        annotated_dir.mkdir(parents=True, exist_ok=True)

    analyzer = FrameAnalyzer(layout)
    tracker = HandStateTracker()
    observations: list[FrameObservation] = []
    annotated_paths: list[Path] = []
    annotated_images = []

    for output_idx, (frame_index, frame) in enumerate(iter_frames(input_path, every or layout.frame_step)):
        observation = analyzer.analyze(frame, frame_index)
        tracker.process(observation)
        observations.append(observation)

        if write_annotations:
            annotated = annotate_frame(frame, layout, observation)
            target = annotated_dir / f"frame_{output_idx:04d}.png"
            annotated.save(target)
            annotated_paths.append(target)
            annotated_images.append(annotated)

    hand_history = tracker.to_hand_history()
    write_json(out_path / "detections.json", [observation.to_dict() for observation in observations])
    write_json(out_path / "hand_history.json", hand_history)
    if write_annotations and len(annotated_images) > 1:
        save_gif(annotated_images, out_path / "annotated.gif")

    return PipelineResult(observations, hand_history, annotated_paths)
