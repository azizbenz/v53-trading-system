"""V5.3 Canary — Engine A trend-pure provoker.

Diagnostic standalone : construit un EngineAInput synthetique en mode
"trend pur" (toutes les features structurelles + contextuelles + flow
maximisees, cost favorable) et appelle directement run_engine_a().

Objectif : discriminer entre :
  - Engine A REFUSE meme sur conditions ideales -> bug interne engine
  - Engine A EMIT -> engine OK, le 0-trade vient de l'orchestration
    (engine_native_mode, candidate_discovery, preselection, etc.)

Usage:
    python scripts/canary_engine_a_trend_provoker.py
    python scripts/canary_engine_a_trend_provoker.py --json   # output JSON pour pipe / dashboards

Pas de side effects : ne touche pas au filesystem, ne lance pas le pipeline
complet. Lecture-seule sur la doctrine de l'engine A.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Repo path bootstrap.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from engines.engine_a.engine_a_runner import (  # noqa: E402
    EngineADecision,
    EngineAInput,
    EngineAOutput,
    run_engine_a,
)


def build_trend_pure_input(
    *,
    pair: str = "BTCUSDT",
    entry_price: float = 50_000.0,
    atr: float = 250.0,
    candidate_size: float = 1_000.0,
) -> EngineAInput:
    """Forge an EngineAInput that SHOULD trigger an EMIT on Engine A.

    Doctrine targeted :
      - direction_score = +1.0      (max bullish)
      - continuation_score = 0.92   (continuation tres forte)
      - structure_quality = 0.95    (HH/HL pattern net)
      - zone_proximity = 0.88       (entree proche d'une zone valide)
      - trend_stability = 0.90      (peu de pullback)
      - regime_favorability = 0.90, regime_confidence = 0.90  (CALM/uptrend)
      - pair_health = 0.95, data_freshness = 0.98 (donnees fraiches)
      - flow_coherence = 0.92, flow_score = 0.85, ofi_flow_score = 0.80
      - execution_fragility = 0.05, market_toxicity = 0.05 (book sain)
      - spread_regime_penalty = 0.02
      - competition_density = 0.30
      - expected_gain = 0.025 (250 bps), expected_cost = 0.0008 (8 bps)
      - ce_min default, delta_safe default, holding_period default

    Si l'engine refuse ce candidat, il y a un bug structurel (ou la doctrine
    a change depuis cette version du canary -> verifier les seuils calibres).
    """

    return EngineAInput(
        pair=pair,
        # Structure
        direction_score=1.0,
        continuation_score=0.92,
        structure_quality=0.95,
        zone_proximity=0.88,
        trend_stability=0.90,
        # Microstructure provenance (optional fields, set to favorable values)
        realized_kernel_vol_scale=0.35,
        realized_vol_current=0.0085,
        # Context
        regime="TRENDING_UP",
        regime_favorability=0.90,
        regime_confidence=0.90,
        pair_health=0.95,
        data_freshness=0.98,
        flow_coherence=0.92,
        flow_score=0.85,
        ofi_flow_score=0.80,
        cost_preference_score=0.75,
        delta_confirmation=0.85,
        # Execution / market state
        execution_fragility=0.05,
        market_toxicity=0.05,
        spread_regime_penalty=0.02,
        competition_density=0.30,
        # Economics
        expected_gain=0.025,
        expected_cost=0.0008,
        kyle_lambda_cost_uplift=0.0001,
        candidate_size=candidate_size,
        # Invalidation
        entry_price=entry_price,
        atr=atr,
    )


@dataclass(frozen=True)
class CanaryVerdict:
    """Decoded verdict for human and machine consumption."""

    decision: str
    accepted: bool
    raw_score: float
    structure_verdict: str
    context_verdict: str
    cost_verdict: str
    conviction: str
    tier: str
    no_trade_reasons: tuple[str, ...]
    reason_codes: tuple[str, ...]
    log_events: tuple[str, ...]

    @classmethod
    def from_output(cls, output: EngineAOutput) -> "CanaryVerdict":
        return cls(
            decision=output.decision.value,
            accepted=output.decision == EngineADecision.EMIT,
            raw_score=float(output.raw_score),
            structure_verdict=output.structure_verdict.value,
            context_verdict=output.context_verdict.value,
            cost_verdict=output.cost_verdict.value,
            conviction=output.conviction.value,
            tier=output.tier_suggestion.value,
            no_trade_reasons=tuple(r.value for r in output.no_trade_reasons),
            reason_codes=tuple(output.reason_codes),
            log_events=tuple(entry.event for entry in output.log_entries),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "accepted": self.accepted,
            "raw_score": self.raw_score,
            "structure_verdict": self.structure_verdict,
            "context_verdict": self.context_verdict,
            "cost_verdict": self.cost_verdict,
            "conviction": self.conviction,
            "tier": self.tier,
            "no_trade_reasons": list(self.no_trade_reasons),
            "reason_codes": list(self.reason_codes),
            "log_events": list(self.log_events),
        }


def _format_human(verdict: CanaryVerdict) -> str:
    sep = "-" * 72
    lines: list[str] = []
    lines.append(sep)
    lines.append("V5.3 Canary - Engine A Trend-Pure Provoker")
    lines.append(sep)
    if verdict.accepted:
        lines.append("RESULT : EMIT [Engine A accepts the trend-pure candidate]")
        lines.append("  -> Engine A internals are healthy.")
        lines.append("  -> 0-trade in the live backtest is an ORCHESTRATION issue,")
        lines.append("     most likely engine_native_mode=False on the runner.")
        lines.append("     Fix: add --engine-native-mode to the CLI invocation,")
        lines.append("     or set request.engine_native_mode=True via the cockpit.")
    else:
        lines.append("RESULT : NO_TRADE [Engine A refuses even on trend-pure input]")
        lines.append("  -> Engine A internals reject this canary.")
        lines.append("  -> Possible causes:")
        lines.append("     * Calibrated thresholds drifted (engine_a_cost_thresholds).")
        lines.append("     * One of the gating stages (structure / context / cost /")
        lines.append("       conviction) has been hardened beyond the canary inputs.")
        lines.append("     * Doctrine of Engine A changed (re-tune canary inputs).")
        lines.append("  -> Inspect the per-stage verdicts and reasons below.")
    lines.append(sep)
    lines.append("Per-stage verdicts:")
    lines.append(f"  structure_verdict = {verdict.structure_verdict}")
    lines.append(f"  context_verdict   = {verdict.context_verdict}")
    lines.append(f"  cost_verdict      = {verdict.cost_verdict}")
    lines.append(f"  conviction        = {verdict.conviction}")
    lines.append(f"  tier_suggestion   = {verdict.tier}")
    lines.append(f"  raw_score         = {verdict.raw_score:.6f}")
    if verdict.no_trade_reasons:
        lines.append("No-trade reasons (typed):")
        for reason in verdict.no_trade_reasons:
            lines.append(f"  - {reason}")
    if verdict.reason_codes:
        lines.append("Reason codes (free-form):")
        for code in verdict.reason_codes:
            lines.append(f"  - {code}")
    if verdict.log_events:
        lines.append("Log event timeline:")
        for event in verdict.log_events:
            lines.append(f"  > {event}")
    lines.append(sep)
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V5.3 Canary - provoke Engine A with a trend-pure synthetic input.",
    )
    parser.add_argument("--pair", default="BTCUSDT")
    parser.add_argument("--entry-price", type=float, default=50_000.0)
    parser.add_argument("--atr", type=float, default=250.0)
    parser.add_argument("--candidate-size", type=float, default=1_000.0)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the verdict as JSON (machine-readable).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    inputs = build_trend_pure_input(
        pair=args.pair,
        entry_price=args.entry_price,
        atr=args.atr,
        candidate_size=args.candidate_size,
    )
    output = run_engine_a(inputs)
    verdict = CanaryVerdict.from_output(output)
    if args.json:
        print(json.dumps(verdict.to_dict(), indent=2, sort_keys=True))
    else:
        print(_format_human(verdict))
    return 0 if verdict.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
