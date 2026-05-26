from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from pokervision.cards import Card
from pokervision.ocr import CandidateOCR, GlyphOCR
from pokervision.rendering import cached_font, draw_centered_text, render_card
from pokervision.templates import CardRecognizer


class RecognitionTest(unittest.TestCase):
    def test_standard_deck_recognizer_identifies_rendered_card(self) -> None:
        recognizer = CardRecognizer.from_standard_deck(min_score=0.82)
        result = recognizer.recognize(render_card(Card.parse("QS")))
        self.assertIsNotNone(result)
        self.assertEqual(result.label, "QS")
        self.assertGreater(result.score, 0.98)

    def test_glyph_ocr_reads_broadcast_overlay(self) -> None:
        image = Image.new("RGB", (180, 46), (8, 12, 16))
        draw = ImageDraw.Draw(image)
        font = cached_font(26, bold=True)
        draw_centered_text(draw, (0, 0, 180, 46), "POT 390", font, (246, 246, 236), tracking=2)

        result = GlyphOCR().read(image)
        self.assertEqual(result.text, "POT 390")
        self.assertGreater(result.score, 0.65)

    def test_candidate_ocr_resolves_action_phrase(self) -> None:
        image = Image.new("RGB", (318, 46), (8, 12, 16))
        draw = ImageDraw.Draw(image)
        font = cached_font(26, bold=True)
        draw_centered_text(draw, (0, 0, 318, 46), "ALICE RAISE 60", font, (246, 246, 236), tracking=2)

        result = CandidateOCR().read(image, ["BOB CHECK", "ALICE RAISE 60", "BOB FOLD"])
        self.assertEqual(result.text, "ALICE RAISE 60")
        self.assertGreater(result.score, 0.95)


if __name__ == "__main__":
    unittest.main()
