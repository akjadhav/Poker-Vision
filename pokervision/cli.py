from __future__ import annotations

import argparse
from pathlib import Path

from .config import LayoutConfig
from .demo import run_demo
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconstruct poker hand history from broadcast-style frames.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze an image, GIF, frame directory, or video.")
    analyze.add_argument("input", help="Input image, GIF, video, or directory of frames.")
    analyze.add_argument("--config", required=True, help="ROI layout JSON file.")
    analyze.add_argument("--out", default="outputs/run", help="Output directory.")
    analyze.add_argument("--every", type=int, default=None, help="Analyze every Nth frame.")
    analyze.add_argument("--no-annotations", action="store_true", help="Skip annotated frame outputs.")

    demo = subparsers.add_parser("demo", help="Create and analyze a synthetic broadcast demo.")
    demo.add_argument("--out", default="outputs/demo", help="Output directory.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        result = run_demo(args.out)
        print_summary(Path(args.out), result.hand_history, len(result.observations))
        return 0

    if args.command == "analyze":
        layout = LayoutConfig.from_json(args.config)
        result = run_pipeline(
            args.input,
            layout,
            args.out,
            every=args.every,
            write_annotations=not args.no_annotations,
        )
        print_summary(Path(args.out), result.hand_history, len(result.observations))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def print_summary(out_dir: Path, hand_history: dict, frame_count: int) -> None:
    summary = hand_history["summary"]
    print(f"Analyzed {frame_count} frame(s)")
    print(f"Final board: {' '.join(summary['final_board']) or '(none)'}")
    print(f"Final pot: {summary['final_pot']}")
    print(f"Events: {len(hand_history['events'])}")
    print(f"Wrote {out_dir / 'hand_history.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
