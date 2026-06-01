from __future__ import annotations

import argparse
from pathlib import Path

from .config import LayoutConfig
from .demo import DEMO_SCENARIOS, run_demo
from .evaluation import DEFAULT_EVALUATION_SCENARIOS, run_demo_evaluation
from .pipeline import run_pipeline
from .reporting import build_final_demo


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
    demo.add_argument("--scenario", choices=sorted(DEMO_SCENARIOS), default="clean", help="Demo rendering scenario.")

    evaluate = subparsers.add_parser("evaluate", help="Run labeled validation scenarios and write metrics.")
    evaluate.add_argument("--out", default="outputs/evaluation", help="Output directory.")
    evaluate.add_argument(
        "--scenarios",
        nargs="+",
        choices=sorted(DEMO_SCENARIOS),
        default=list(DEFAULT_EVALUATION_SCENARIOS),
        help="Validation scenarios to run.",
    )
    evaluate.add_argument("--no-annotations", action="store_true", help="Skip annotated frame outputs.")

    final = subparsers.add_parser("final-demo", help="Generate presentation-ready demo page, findings, and metrics.")
    final.add_argument("--out", default="outputs/final_demo", help="Output directory.")
    final.add_argument(
        "--scenarios",
        nargs="+",
        choices=sorted(DEMO_SCENARIOS),
        default=list(DEFAULT_EVALUATION_SCENARIOS),
        help="Validation scenarios to include.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        result = run_demo(args.out, scenario=args.scenario)
        print_summary(Path(args.out), result.hand_history, len(result.observations))
        return 0

    if args.command == "evaluate":
        evaluations = run_demo_evaluation(
            args.out,
            scenarios=args.scenarios,
            write_annotations=not args.no_annotations,
        )
        print_evaluation_summary(Path(args.out), evaluations)
        return 0

    if args.command == "final-demo":
        paths = build_final_demo(args.out, scenarios=args.scenarios)
        print(f"Wrote demo page: {paths['index']}")
        print(f"Wrote findings: {paths['findings']}")
        print(f"Wrote hand history: {paths['hand_history']}")
        print(f"Wrote evaluation summary: {paths['evaluation_summary']}")
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


def print_evaluation_summary(out_dir: Path, evaluations) -> None:
    print(f"Evaluated {len(evaluations)} scenario(s)")
    for evaluation in evaluations:
        card = evaluation.metrics["card_slots"]
        chips = evaluation.metrics["chip_regions"]
        text = evaluation.metrics["text_exact"]
        events = evaluation.metrics["event_sequence"]
        print(
            f"{evaluation.scenario}: "
            f"cards {card.accuracy * 100:.1f}% ({card.correct}/{card.total}), "
            f"chips {chips.accuracy * 100:.1f}% ({chips.correct}/{chips.total}), "
            f"text {text.accuracy * 100:.1f}% ({text.correct}/{text.total}), "
            f"events {events.accuracy * 100:.1f}% ({events.correct}/{events.total})"
        )
    print(f"Wrote {out_dir / 'summary.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
