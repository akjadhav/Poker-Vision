from __future__ import annotations

import unittest

from pokervision.analyzer import CardDetection, FrameObservation, TextDetection
from pokervision.tracker import HandStateTracker, parse_action, parse_amount


class TrackerTest(unittest.TestCase):
    def test_parse_amount(self) -> None:
        self.assertEqual(parse_amount("POT 1,250"), 1250)
        self.assertIsNone(parse_amount("CHECK"))

    def test_parse_action(self) -> None:
        parsed = parse_action("ALICE RAISE 60")
        self.assertEqual(parsed["player"], "ALICE")
        self.assertEqual(parsed["action"], "RAISE")
        self.assertEqual(parsed["amount"], 60)

    def test_tracker_builds_timeline(self) -> None:
        tracker = HandStateTracker()
        tracker.process(
            FrameObservation(
                frame_index=0,
                time_s=None,
                community=[
                    CardDetection("b1", None, 0.1),
                    CardDetection("b2", None, 0.1),
                    CardDetection("b3", None, 0.1),
                ],
                players={
                    "ALICE": [
                        CardDetection("a1", "KD", 1.0),
                        CardDetection("a2", "QD", 1.0),
                    ]
                },
                texts={
                    "pot": TextDetection("pot", "pot", "POT 30", 0.9),
                    "action": TextDetection("action", "action", "BOB CHECK", 0.9),
                },
            )
        )
        tracker.process(
            FrameObservation(
                frame_index=1,
                time_s=None,
                community=[
                    CardDetection("b1", "7H", 1.0),
                    CardDetection("b2", "8D", 1.0),
                    CardDetection("b3", "2C", 1.0),
                ],
                players={
                    "ALICE": [
                        CardDetection("a1", "KD", 1.0),
                        CardDetection("a2", "QD", 1.0),
                    ]
                },
                texts={
                    "pot": TextDetection("pot", "pot", "POT 150", 0.9),
                    "action": TextDetection("action", "action", "ALICE BET 120", 0.9),
                },
            )
        )

        history = tracker.to_hand_history()
        self.assertEqual(history["summary"]["final_board"], ["7H", "8D", "2C"])
        self.assertEqual(history["summary"]["final_pot"], 150)
        self.assertEqual(history["summary"]["street"], "flop")
        self.assertTrue(any(event["type"] == "street" for event in history["events"]))
        self.assertTrue(any(event["type"] == "action" for event in history["events"]))


if __name__ == "__main__":
    unittest.main()
