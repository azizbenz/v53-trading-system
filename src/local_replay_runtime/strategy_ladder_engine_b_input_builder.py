"""Strategy Ladder engine_b input builder — comble la limitation P3a pour
engine_b (Audit 2026-05-07).

Construit un `EngineBInput` COMPLET (incluant les 4 champs REQUIRED) depuis un
raw_window backtest, sans toucher au code des engines.

PHILOSOPHIE ENGINE B (selon doc 14_ENGINE_B_AUDITS + comments du runner) :
  > B = Mean Reversion (cote LONG) avec sub-signal toxic_flow_fade.
  > Active quand z_score = (current_price - local_mean) / local_std < 0
  > (prix sous le mean local) ET dispersion non degeneree.
  > Hard-block sur breakout (B != engine_a/c) ; engine_b ne fait que la
  > mean-reversion.

Champs REQUIRED dans `engines/engine_b/engine_b_runner.py:96-130` :
  pair: str
  current_price: float = Field(gt=0.0)
  local_mean: float = Field(gt=0.0)
  local_std: float = Field(ge=0.0)

Le pont microstructure `build_engine_b_microstructure_inputs_from_window`
calcule deja ces 4 champs depuis les trades de la fenetre :
  - current_price = prix du dernier trade
  - local_mean = moyenne arithmetique des prix
  - local_std = ecart-type empirique non-biaise

Plus VPIN comme additif.

Le builder ici est donc **fin** : il delegue au pont pour les 4 REQUIRED +
vpin, et ajoute juste les champs de defaults explicites + provenance flag.

PHILOSOPHIE PRESERVEE :
- AUCUN fichier dans `src/engines/engine_b/` modifie
- Builder vit dans `local_replay_runtime/` cote caller
- Pas de calcul de sweep_score / absorption_score / poc_reversion_score /
  false_breakout_score (modules walls_and_spoofing.py existent mais demandent
  calibration finalisee — laissés en defaults TO_CALIBRATE)
- Provenance flag : `engine_b_input_provenance="BUILDER_FROM_BRIDGE_HEURISTIC_TO_CALIBRATE"`

LIMITATION : ce builder n'apporte pas de microstructure-specific scores
(sweep/absorption/poc_reversion/false_breakout). Pour l'integration complete
de ces sub-scores, il faudra cabler `walls_and_spoofing.py` dans une session
ulterieure une fois la calibration land par `risk_runtime_drawdown_calibration.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    EngineBBridgeResult,
    build_engine_b_microstructure_inputs_from_window,
)


@dataclass(frozen=True)
class EngineBInputBuilderResult:
    """Resultat audit-ready du builder engine_b."""

    candidate_id: str
    pair: str
    builder_status: str
    bridge_result: EngineBBridgeResult | None
    engine_b_input_payload: dict[str, object] = field(default_factory=dict)
    builder_warnings: tuple[str, ...] = ()
    engine_b_input_provenance: str = "BUILDER_FROM_BRIDGE_HEURISTIC_TO_CALIBRATE"


def build_engine_b_input_from_window(
    *,
    candidate_id: str,
    pair: str,
    window_start_ms: int,
    window_end_ms: int,
    raw_trade_path: Path | str | None,
    expected_gain: float = 0.0,
    expected_cost: float = 0.0,
    candidate_size: float = 0.0,
    holding_period: float | None = None,
    scoring_version: str = "engine_b.builder.v1",
    base_payload: dict[str, object] | None = None,
) -> EngineBInputBuilderResult:
    """Construit un EngineBInput.model_validate-compatible depuis raw_window.

    Combine :
      - Pont microstructure engine_b (current_price, local_mean, local_std, vpin)
        depuis les trades de la fenetre
      - Defaults canoniques pour les autres champs (regime/health/freshness/
        coherence/sweep/absorption/...)
      - Cost/economics fournis par le caller ou defaults

    Le caller peut alors faire `run_engine_b(EngineBInput(**payload))`.

    Si le pont microstructure echoue a calculer les 4 REQUIRED (trade tape
    insuffisant), retourne un statut FAILED. La validation Pydantic
    rejettera de toute facon current_price <= 0 ou local_mean <= 0.
    """
    warnings: list[str] = []

    bridge = build_engine_b_microstructure_inputs_from_window(
        candidate_id=candidate_id,
        pair=pair,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        raw_trade_path=raw_trade_path,
    )

    # Si le pont n'a pas reussi a fournir les 4 critiques, le builder ne peut
    # pas produire de payload Pydantic-valide.
    if (
        bridge.current_price is None
        or bridge.local_mean is None
        or bridge.local_std is None
    ):
        warnings.append(
            f"BRIDGE_INSUFFICIENT_REQUIRED:"
            f"current_price={bridge.current_price},"
            f"local_mean={bridge.local_mean},"
            f"local_std={bridge.local_std}"
        )
        warnings.extend(bridge.bridge_warnings)
        return EngineBInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_B_INPUT_BUILDER_FAILED_BRIDGE",
            bridge_result=bridge,
            engine_b_input_payload={},
            builder_warnings=tuple(warnings),
        )

    if bridge.current_price <= 0.0 or bridge.local_mean <= 0.0:
        warnings.append(
            f"BRIDGE_NON_POSITIVE_PRICE:current={bridge.current_price},mean={bridge.local_mean}"
        )
        return EngineBInputBuilderResult(
            candidate_id=candidate_id,
            pair=pair,
            builder_status="ENGINE_B_INPUT_BUILDER_FAILED_NON_POSITIVE_PRICE",
            bridge_result=bridge,
            engine_b_input_payload={},
            builder_warnings=tuple(warnings),
        )

    base = dict(base_payload or {})
    payload: dict[str, object] = {
        "pair": pair,
        # 4 REQUIRED depuis le pont
        "current_price": bridge.current_price,
        "local_mean": bridge.local_mean,
        "local_std": bridge.local_std,
        # Defaults canoniques (regime/health/freshness/coherence)
        "regime": "",
        "regime_favorability": 0.5,
        "pair_health": 0.5,
        "data_freshness": 0.5,
        "flow_coherence": 0.5,
        # Cost/economics — fournis par caller
        "expected_gain": expected_gain,
        "expected_cost": expected_cost,
        "candidate_size": candidate_size,
        "scoring_version": scoring_version,
    }
    if holding_period is not None:
        payload["holding_period"] = holding_period

    # Microstructure additif depuis le pont :
    # vpin_current accepte par EngineBInput
    if bridge.vpin_record is not None:
        payload["vpin_current"] = bridge.vpin_record.value

    # Permettre au caller d'overrider via base_payload
    payload.update(base)

    # Determine status final
    n_critical = sum(
        1
        for v in (
            bridge.current_price,
            bridge.local_mean,
            bridge.local_std,
            bridge.vpin_record,
        )
        if v is not None
    )
    if n_critical == 4:
        builder_status = "ENGINE_B_INPUT_BUILDER_READY"
    else:
        builder_status = "ENGINE_B_INPUT_BUILDER_PARTIAL"

    # Propage les warnings du pont
    warnings.extend(bridge.bridge_warnings)

    return EngineBInputBuilderResult(
        candidate_id=candidate_id,
        pair=pair,
        builder_status=builder_status,
        bridge_result=bridge,
        engine_b_input_payload=payload,
        builder_warnings=tuple(warnings),
    )


__all__ = [
    "EngineBInputBuilderResult",
    "build_engine_b_input_from_window",
]
