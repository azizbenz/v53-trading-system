from __future__ import annotations

from pathlib import Path

from engines.engine_a.engine_a_runner import EngineAInput
from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_d.engine_d_models import EngineDInput


_ENGINE_A_MICROSTRUCTURE_FIELDS = {
    "ofi_flow_score",
    "realized_kernel_vol_scale",
    "realized_vol_current",
    "kyle_lambda_cost_uplift",
}
_ENGINE_C_MICROSTRUCTURE_FIELDS = {
    "cumulative_ofi",
    "queue_pressure",
    "vpin",
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
}
_ENGINE_D_MICROSTRUCTURE_FIELDS = {
    "realized_vol_current",
    "realized_vol_post_close",
}
_NO_CALCULATOR_IMPORT_FILES = (
    Path("src/engines/engine_a/engine_a_runner.py"),
    Path("src/engines/engine_a/conviction_builder_a.py"),
    Path("src/engines/engine_a/structure_detector_a.py"),
    Path("src/engines/engine_a/cost_feasibility_a.py"),
    Path("src/engines/engine_c/engine_c_runner.py"),
    Path("src/engines/engine_c/continuation_validator_c.py"),
)
_CANONICAL_CALCULATOR_TOKENS = (
    "from data_backbone.microstructure",
    "import data_backbone.microstructure",
    "compute_order_flow_imbalance",
    "compute_vpin",
    "compute_kyle_lambda",
    "compute_realized_kernel_vol",
    "compute_queue_pressure",
    "compute_hawkes_intensity",
)


def test_engine_a_and_c_expose_canonical_microstructure_input_seams() -> None:
    assert _ENGINE_A_MICROSTRUCTURE_FIELDS.issubset(EngineAInput.model_fields)
    assert _ENGINE_C_MICROSTRUCTURE_FIELDS.issubset(EngineCInput.model_fields)
    assert _ENGINE_D_MICROSTRUCTURE_FIELDS.issubset(EngineDInput.model_fields)


def test_engine_a_and_c_runner_surfaces_do_not_hide_microstructure_calculators() -> None:
    offenders: list[str] = []

    for path in _NO_CALCULATOR_IMPORT_FILES:
        content = path.read_text(encoding="utf-8")
        for token in _CANONICAL_CALCULATOR_TOKENS:
            if token in content:
                offenders.append(f"{path.as_posix()}:{token}")

    assert offenders == []
