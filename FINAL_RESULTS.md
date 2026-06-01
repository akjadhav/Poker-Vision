# PokerVision Final Results

## Demo Artifacts

Run the complete presentation bundle with:

```bash
python -m pokervision.cli final-demo --out outputs/final_demo
```

The bundle contains:

- `outputs/final_demo/index.html`: presentation-ready dashboard with annotated demo clip, timeline, metrics, and findings.
- `outputs/final_demo/demo/annotated.gif`: annotated frame sequence.
- `outputs/final_demo/demo/hand_history.json`: reconstructed structured hand history.
- `outputs/final_demo/evaluation/summary.json`: labeled validation metrics.
- `outputs/final_demo/findings.md`: short talk-track and limitations.

## Reconstructed Hand

PokerVision reconstructs the demo hand as:

- Board: `7H 8D 2C QS AD`
- Alice: `KD QD`
- Bob: `AH TS`
- Final pot: `390`
- Final street: `river`
- Chip movements: `3`
- Timeline length: `18` events

## Validation Results

| Scenario | Card slots | Chip ROIs | Text | Events | Summary |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 100.0% (45/45) | 100.0% (15/15) | 100.0% (10/10) | 100.0% (18/18) | 100.0% (5/5) |
| compressed | 100.0% (45/45) | 100.0% (15/15) | 100.0% (10/10) | 100.0% (18/18) | 100.0% (5/5) |
| noisy | 100.0% (45/45) | 100.0% (15/15) | 100.0% (10/10) | 100.0% (18/18) | 100.0% (5/5) |
| soft | 100.0% (45/45) | 100.0% (15/15) | 100.0% (10/10) | 100.0% (18/18) | 100.0% (5/5) |

## Findings

- Fixed-layout ROI extraction is sufficient for stable poker broadcast graphics.
- Template matching recovers visible cards reliably for this controlled layout, including compressed, noisy, and softly blurred validation frames.
- Candidate-constrained OCR stabilizes pot/action overlays better than raw glyph OCR alone.
- Chip movement is inferred from color-segmented chip mass changes between fixed player-stack ROIs and the pot ROI.
- Temporal tracking converts repeated detections into a concise hand-history timeline with street, pot, action, chip-movement, and hole-card events.

## Limitations

- The final validation is controlled fixed-layout validation, not broad real-broadcast generalization.
- A new broadcast source still needs ROI calibration and card templates from that overlay style.
- Chip tracking assumes visible, color-separable chips inside calibrated stack/pot regions and does not estimate denomination from arbitrary footage.
- The action parser is intentionally small: `CHECK`, `CALL`, `BET`, `RAISE`, `FOLD`, and `ALL IN`.
