from __future__ import annotations

from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterable

from .analyzer import CardDetection, ChipDetection, FrameObservation, TextDetection
from .config import LayoutConfig
from .demo import DEMO_SCENARIOS, DEMO_STATES, create_demo_frames, demo_layout
from .io import write_json
from .pipeline import PipelineResult, run_pipeline
from .tracker import HandStateTracker, normalize_text


DEFAULT_EVALUATION_SCENARIOS = ("clean", "compressed", "noisy", "soft")


@dataclass(frozen=True)
class Metric:
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "correct": self.correct,
            "total": self.total,
            "accuracy": round(self.accuracy, 4),
        }


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario: str
    description: str
    metrics: dict[str, Metric]
    expected_hand_history: dict[str, Any]
    actual_hand_history: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "description": self.description,
            "metrics": {
                name: metric.to_dict()
                for name, metric in self.metrics.items()
            },
            "expected_hand_history": self.expected_hand_history,
            "actual_hand_history": self.actual_hand_history,
        }


def expected_hand_history(
    states: Iterable[dict[str, Any]] = DEMO_STATES,
    layout: LayoutConfig | None = None,
) -> dict[str, Any]:
    layout = layout or demo_layout()
    tracker = HandStateTracker()
    for frame_index, state in enumerate(states):
        tracker.process(expected_observation(frame_index, state, layout))
    return tracker.to_hand_history()


def expected_observation(frame_index: int, state: dict[str, Any], layout: LayoutConfig) -> FrameObservation:
    board = state["board"]
    community = [
        CardDetection(slot.name, board[idx] if idx < len(board) else None, 1.0)
        for idx, slot in enumerate(layout.community)
    ]
    players = {}
    for player in layout.players:
        cards = state["players"].get(player.name, [])
        players[player.name] = [
            CardDetection(slot.name, cards[idx] if idx < len(cards) else None, 1.0)
            for idx, slot in enumerate(player.cards)
        ]
    texts = {
        region.name: TextDetection(region.name, region.kind, expected_text(state, region.kind), 1.0)
        for region in layout.texts
    }
    chips = [
        ChipDetection(
            region.name,
            region.kind,
            region.owner,
            expected_chip_count(state, region) * 400,
            1.0,
        )
        for region in layout.chips
    ]
    return FrameObservation(frame_index, None, community, players, texts, chips)


def expected_text(state: dict[str, Any], kind: str) -> str:
    if kind == "pot":
        return str(state["pot"])
    if kind == "action":
        return str(state["action"])
    return str(state.get(kind, ""))


def expected_chip_count(state: dict[str, Any], region) -> int:
    if region.kind == "pot":
        return int(state.get("chips", {}).get("POT", 0))
    if region.owner:
        return int(state.get("chips", {}).get(region.owner, 0))
    return int(state.get("chips", {}).get(region.name, 0))


def evaluate_result(
    result: PipelineResult,
    layout: LayoutConfig,
    states: list[dict[str, Any]] | None = None,
) -> ScenarioEvaluation:
    states = states or list(DEMO_STATES)
    counts: dict[str, list[int]] = {}

    def add(name: str, ok: bool) -> None:
        correct, total = counts.get(name, [0, 0])
        counts[name] = [correct + int(ok), total + 1]

    for observation, state in zip_longest(result.observations, states):
        if observation is None or state is None:
            add("frames_processed", False)
            continue
        add("frames_processed", True)
        _score_cards(add, layout, observation, state)
        _score_text(add, layout, observation, state)
        _score_chips(add, layout, observation, state)

    expected_history = expected_hand_history(states, layout)
    _score_summary(add, result.hand_history["summary"], expected_history["summary"])
    _score_events(add, result.hand_history["events"], expected_history["events"])

    metrics = {
        name: Metric(correct, total)
        for name, (correct, total) in counts.items()
    }
    return ScenarioEvaluation(
        scenario="custom",
        description="Evaluation over supplied observations.",
        metrics=metrics,
        expected_hand_history=expected_history,
        actual_hand_history=result.hand_history,
    )


def _score_cards(add, layout: LayoutConfig, observation: FrameObservation, state: dict[str, Any]) -> None:
    board = state["board"]
    expected_community = {
        slot.name: board[idx] if idx < len(board) else None
        for idx, slot in enumerate(layout.community)
    }
    actual_community = {item.slot: item.card for item in observation.community}
    for slot_name, expected in expected_community.items():
        predicted = actual_community.get(slot_name)
        add("card_slots", predicted == expected)
        add("visible_cards" if expected else "empty_card_slots", predicted == expected)

    for player in layout.players:
        expected_cards = state["players"].get(player.name, [])
        actual_cards = {
            item.slot: item.card
            for item in observation.players.get(player.name, [])
        }
        for idx, slot in enumerate(player.cards):
            expected = expected_cards[idx] if idx < len(expected_cards) else None
            predicted = actual_cards.get(slot.name)
            add("card_slots", predicted == expected)
            add("visible_cards" if expected else "empty_card_slots", predicted == expected)


def _score_text(add, layout: LayoutConfig, observation: FrameObservation, state: dict[str, Any]) -> None:
    for region in layout.texts:
        expected = normalize_text(expected_text(state, region.kind))
        predicted = normalize_text(observation.text_value(region.name))
        add("text_exact", predicted == expected)
        add(f"{region.kind}_text", predicted == expected)


def _score_chips(add, layout: LayoutConfig, observation: FrameObservation, state: dict[str, Any]) -> None:
    actual = {item.name: item.chip_pixels for item in observation.chips}
    for region in layout.chips:
        expected_present = expected_chip_count(state, region) > 0
        predicted_present = actual.get(region.name, 0) >= 80
        add("chip_regions", predicted_present == expected_present)


def _score_summary(add, actual: dict[str, Any], expected: dict[str, Any]) -> None:
    for key in ("final_board", "players", "final_pot", "street", "chip_movements"):
        add("summary_fields", actual.get(key) == expected.get(key))


def _score_events(add, actual_events: list[dict[str, Any]], expected_events: list[dict[str, Any]]) -> None:
    actual = [_event_signature(event) for event in actual_events]
    expected = [_event_signature(event) for event in expected_events]
    for actual_event, expected_event in zip_longest(actual, expected):
        add("event_sequence", actual_event == expected_event)


def _event_signature(event: dict[str, Any] | None) -> tuple[Any, ...] | None:
    if event is None:
        return None
    payload = event.get("payload", {})
    if event.get("type") == "chip_movement":
        payload = {
            "source": payload.get("source"),
            "target": payload.get("target"),
            "action": payload.get("action"),
            "amount": payload.get("amount"),
        }
    return (
        event.get("frame_index"),
        event.get("type"),
        tuple(_freeze(payload)),
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze(value[key])) for key in sorted(value))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def evaluate_demo_scenario(
    scenario: str,
    out_dir: str | Path,
    write_annotations: bool = True,
) -> ScenarioEvaluation:
    out_path = Path(out_dir)
    frames_dir, layout = create_demo_frames(out_path, scenario=scenario)
    result = run_pipeline(frames_dir, layout, out_path, write_annotations=write_annotations)
    evaluation = evaluate_result(result, layout)
    evaluation = ScenarioEvaluation(
        scenario=scenario,
        description=DEMO_SCENARIOS[scenario],
        metrics=evaluation.metrics,
        expected_hand_history=evaluation.expected_hand_history,
        actual_hand_history=evaluation.actual_hand_history,
    )
    write_json(out_path / "metrics.json", evaluation.to_dict())
    return evaluation


def run_demo_evaluation(
    out_dir: str | Path,
    scenarios: Iterable[str] = DEFAULT_EVALUATION_SCENARIOS,
    write_annotations: bool = True,
) -> list[ScenarioEvaluation]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    evaluations = [
        evaluate_demo_scenario(scenario, out_path / scenario, write_annotations=write_annotations)
        for scenario in scenarios
    ]
    write_json(
        out_path / "summary.json",
        {
            "scenarios": [evaluation.to_dict() for evaluation in evaluations],
        },
    )
    return evaluations
