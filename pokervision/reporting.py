from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

from .demo import run_demo
from .evaluation import DEFAULT_EVALUATION_SCENARIOS, ScenarioEvaluation, run_demo_evaluation


def build_final_demo(
    out_dir: str | Path,
    scenarios: Iterable[str] = DEFAULT_EVALUATION_SCENARIOS,
) -> dict[str, Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    demo_dir = out_path / "demo"
    result = run_demo(demo_dir, scenario="clean")
    evaluations = run_demo_evaluation(out_path / "evaluation", scenarios=scenarios)

    findings_path = out_path / "findings.md"
    findings_path.write_text(render_findings(evaluations, result.hand_history), encoding="utf-8")

    index_path = out_path / "index.html"
    index_path.write_text(render_html(evaluations, result.hand_history), encoding="utf-8")

    return {
        "index": index_path,
        "findings": findings_path,
        "hand_history": demo_dir / "hand_history.json",
        "annotated_gif": demo_dir / "annotated.gif",
        "evaluation_summary": out_path / "evaluation" / "summary.json",
    }


def render_findings(evaluations: list[ScenarioEvaluation], hand_history: dict) -> str:
    summary = hand_history["summary"]
    lines = [
        "# PokerVision Final Results",
        "",
        "## Completed demo",
        "",
        (
            f"PokerVision reconstructs the demo hand as board {' '.join(summary['final_board'])}, "
            f"Alice {' '.join(summary['players']['ALICE'])}, Bob {' '.join(summary['players']['BOB'])}, "
            f"final pot {summary['final_pot']}, and street {summary['street']}."
        ),
        "",
        f"The reconstructed hand history contains {len(hand_history['events'])} timeline events: "
        "hole-card reveals, pot updates, parsed actions, chip movements, and flop/turn/river transitions.",
        "",
        "## Evaluation",
        "",
        "| Scenario | Card slots | Chip ROIs | Text | Events | Summary |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for evaluation in evaluations:
        lines.append(
            "| "
            + " | ".join(
                [
                    evaluation.scenario,
                    _metric_cell(evaluation, "card_slots"),
                    _metric_cell(evaluation, "chip_regions"),
                    _metric_cell(evaluation, "text_exact"),
                    _metric_cell(evaluation, "event_sequence"),
                    _metric_cell(evaluation, "summary_fields"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            "- Fixed-layout ROI extraction is enough to recover a full hand when the broadcast graphics are stable.",
            "- Card template matching is highly reliable for this layout, including compressed, noisy, and softly blurred validation frames.",
            "- Candidate-constrained OCR is more reliable than raw glyph OCR for short action overlays because it regularizes small character-level mistakes.",
            "- Chip movement is inferred from color-segmented chip mass changes between fixed player-stack ROIs and the pot ROI.",
            "- The finite-state tracker removes repeated frame detections and turns visual changes into a concise hand-history timeline.",
            "",
            "## Limitations",
            "",
            "- The current evaluation is a controlled fixed-layout validation, not a claim of broad real-video generalization.",
            "- A new broadcast layout still needs manually defined ROIs and card templates from that overlay style.",
            "- Chip tracking assumes visible, color-separable chips inside calibrated stack/pot regions and does not estimate denomination from arbitrary footage.",
            "- The action parser expects a small vocabulary: CHECK, CALL, BET, RAISE, FOLD, and ALL IN.",
            "",
            "## Demo script",
            "",
            "1. Show `index.html` and play the annotated GIF.",
            "2. Point out the colored ROIs: yellow board cards, green player cards, cyan text overlays, and orange chip regions.",
            "3. Open `hand_history.json` to show the structured timeline produced by the tracker.",
            "4. Use the metrics table to explain what was evaluated and where the current assumptions remain.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html(evaluations: list[ScenarioEvaluation], hand_history: dict) -> str:
    summary = hand_history["summary"]
    events = hand_history["events"]
    metrics_rows = "\n".join(_metrics_row(evaluation) for evaluation in evaluations)
    timeline = "\n".join(_timeline_item(event) for event in events)
    final_board = " ".join(summary["final_board"])
    alice = " ".join(summary["players"]["ALICE"])
    bob = " ".join(summary["players"]["BOB"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PokerVision Final Demo</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111820;
      --panel: #17232d;
      --panel-2: #1f2f3a;
      --text: #f4f0e6;
      --muted: #b9c4c9;
      --gold: #ffd85a;
      --cyan: #65d1ff;
      --green: #7ee787;
      --red: #ff7a7a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 22px;
      align-items: end;
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 54px;
      line-height: 1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    p {{ margin: 0; color: var(--muted); }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .stat, section {{
      background: var(--panel);
      border: 1px solid #294252;
      border-radius: 8px;
    }}
    .stat {{
      padding: 14px;
      min-height: 74px;
    }}
    .stat strong {{
      display: block;
      color: var(--text);
      font-size: 22px;
      margin-top: 4px;
    }}
    .visual {{
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(330px, 0.55fr);
      gap: 18px;
      margin-bottom: 18px;
    }}
    section {{ padding: 18px; }}
    img {{
      width: 100%;
      border-radius: 8px;
      border: 1px solid #365060;
      display: block;
      background: #0b1116;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 8px;
    }}
    th, td {{
      padding: 10px 12px;
      text-align: right;
      border-bottom: 1px solid #2c4352;
      white-space: nowrap;
    }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ color: var(--muted); font-weight: 650; }}
    tr:last-child td {{ border-bottom: 0; }}
    .timeline {{
      display: grid;
      gap: 8px;
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }}
    .event {{
      display: grid;
      grid-template-columns: 64px 92px 1fr;
      gap: 10px;
      align-items: center;
      background: var(--panel-2);
      border: 1px solid #315064;
      border-radius: 8px;
      padding: 10px;
    }}
    .badge {{
      color: #101820;
      background: var(--gold);
      border-radius: 999px;
      padding: 4px 8px;
      text-align: center;
      font-weight: 700;
    }}
    .type {{ color: var(--cyan); font-weight: 700; text-transform: uppercase; font-size: 12px; }}
    .payload {{ color: var(--text); overflow-wrap: anywhere; }}
    .findings {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .finding {{
      border-left: 4px solid var(--green);
      padding: 12px;
      background: #14212a;
      border-radius: 8px;
      color: var(--muted);
    }}
    .finding strong {{ display: block; color: var(--text); margin-bottom: 4px; }}
    @media (max-width: 920px) {{
      header, .visual, .findings {{ grid-template-columns: 1fr; }}
      .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 560px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 16px; }}
      h1 {{ font-size: 36px; }}
      .summary {{ grid-template-columns: 1fr; }}
      .event {{ grid-template-columns: 54px 1fr; }}
      .payload {{ grid-column: 1 / -1; }}
      th, td {{ padding: 8px 6px; font-size: 12px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>PokerVision</h1>
        <p>Automated hand-history reconstruction from fixed-layout poker broadcast frames.</p>
      </div>
      <div class="summary">
        <div class="stat">Final board<strong>{escape(final_board)}</strong></div>
        <div class="stat">Final pot<strong>{escape(str(summary["final_pot"]))}</strong></div>
        <div class="stat">Alice<strong>{escape(alice)}</strong></div>
        <div class="stat">Bob<strong>{escape(bob)}</strong></div>
      </div>
    </header>

    <div class="visual">
      <section>
        <h2>Annotated Demo Clip</h2>
        <img src="demo/annotated.gif" alt="Annotated PokerVision demo clip">
      </section>
      <section>
        <h2>Reconstructed Timeline</h2>
        <div class="timeline">{timeline}</div>
      </section>
    </div>

    <section>
      <h2>Validation Results</h2>
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Card slots</th>
            <th>Chip ROIs</th>
            <th>Text</th>
            <th>Events</th>
            <th>Summary</th>
          </tr>
        </thead>
        <tbody>{metrics_rows}</tbody>
      </table>
    </section>

    <div class="findings">
      <div class="finding"><strong>ROI model works</strong>Stable broadcast graphics make fixed regions a practical first stage.</div>
      <div class="finding"><strong>Templates are enough</strong>Rendered card templates recover all visible slots in validation.</div>
      <div class="finding"><strong>Constrained OCR helps</strong>Candidate matching stabilizes short pot and action overlays.</div>
      <div class="finding"><strong>Chips are tracked</strong>Orange ROIs detect stack-to-pot movement for raise, call, and bet actions.</div>
    </div>
  </main>
</body>
</html>
"""


def _metric_cell(evaluation: ScenarioEvaluation, metric_name: str) -> str:
    metric = evaluation.metrics[metric_name]
    return f"{metric.accuracy * 100:.1f}% ({metric.correct}/{metric.total})"


def _metrics_row(evaluation: ScenarioEvaluation) -> str:
    return (
        "<tr>"
        f"<td>{escape(evaluation.scenario)}</td>"
        f"<td>{escape(_metric_cell(evaluation, 'card_slots'))}</td>"
        f"<td>{escape(_metric_cell(evaluation, 'chip_regions'))}</td>"
        f"<td>{escape(_metric_cell(evaluation, 'text_exact'))}</td>"
        f"<td>{escape(_metric_cell(evaluation, 'event_sequence'))}</td>"
        f"<td>{escape(_metric_cell(evaluation, 'summary_fields'))}</td>"
        "</tr>"
    )


def _timeline_item(event: dict) -> str:
    payload = event["payload"]
    if event["type"] == "street":
        detail = f"{payload['street']}: {' '.join(payload['board'])}"
    elif event["type"] == "hole_cards":
        detail = f"{payload['player']} {' '.join(payload['cards'])}"
    elif event["type"] == "pot":
        detail = f"{payload['text']} ({payload['amount']})"
    elif event["type"] == "action":
        amount = f" {payload['amount']}" if payload["amount"] is not None else ""
        detail = f"{payload['player']} {payload['action']}{amount}"
    elif event["type"] == "chip_movement":
        amount = f" for {payload['amount']}" if payload.get("amount") is not None else ""
        detail = f"{payload['source']} chips to {payload['target']}{amount}"
    else:
        detail = str(payload)
    return (
        '<div class="event">'
        f'<div class="badge">F{escape(str(event["frame_index"]))}</div>'
        f'<div class="type">{escape(event["type"])}</div>'
        f'<div class="payload">{escape(detail)}</div>'
        "</div>"
    )
