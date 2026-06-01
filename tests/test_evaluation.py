from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import ImageChops

from pokervision.analyzer import FrameAnalyzer
from pokervision.demo import DEMO_STATES, demo_layout, render_demo_frame
from pokervision.evaluation import expected_hand_history, evaluate_demo_scenario


class EvaluationTest(unittest.TestCase):
    def test_expected_history_matches_demo_story(self) -> None:
        history = expected_hand_history()
        self.assertEqual(history["summary"]["final_board"], ["7H", "8D", "2C", "QS", "AD"])
        self.assertEqual(history["summary"]["final_pot"], 390)
        self.assertEqual(history["summary"]["street"], "river")
        self.assertEqual(history["summary"]["chip_movements"], 3)
        self.assertEqual(len(history["events"]), 18)

    def test_clean_demo_evaluation_is_perfect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evaluation = evaluate_demo_scenario("clean", Path(tmp), write_annotations=False)
        self.assertEqual(evaluation.metrics["card_slots"].accuracy, 1.0)
        self.assertEqual(evaluation.metrics["chip_regions"].accuracy, 1.0)
        self.assertEqual(evaluation.metrics["text_exact"].accuracy, 1.0)
        self.assertEqual(evaluation.metrics["event_sequence"].accuracy, 1.0)

    def test_card_search_margin_handles_small_overlay_shift(self) -> None:
        layout = demo_layout()
        analyzer = FrameAnalyzer(layout)
        shifted = ImageChops.offset(render_demo_frame(DEMO_STATES[-1], layout), 2, 0)

        observation = analyzer.analyze(shifted, frame_index=0)

        self.assertEqual(observation.community_cards(), ["7H", "8D", "2C", "QS", "AD"])
        self.assertEqual(observation.player_cards("ALICE"), ["KD", "QD"])
        self.assertEqual(observation.text_value("action"), "BOB FOLD")


if __name__ == "__main__":
    unittest.main()
