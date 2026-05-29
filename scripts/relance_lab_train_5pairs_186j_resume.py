"""Relance le run mort `lab_train-2026-05-28-5pairs-186j` en mode --resume.

Ce script reconstitue la commande Data Factory du run mort
(K:/output lab/runs/lab_train-2026-05-28-5pairs-186j) en s'appuyant sur
`phase_a2_data_factory/a2_gold_progress_report.json` (request) et active
le flag --resume nouvellement patché (RESUME-SILVER 2026-05-29) pour
short-circuiter les normalizers trades/klines/orderbook quand le silver
existe déjà.

Cas particulier ETHUSDT 10/23 : le snapshot existe (process mort juste
après écriture) mais le delta manque. La règle resume "both files must
exist" force la re-normalisation correcte de cette journée.

Usage :
    python scripts/relance_lab_train_5pairs_186j_resume.py

Sortie :
    JSON sur stdout avec status data_factory + counters.

Pour modifier les hypothèses (raw-root, économic provenance) édite les
constantes au début du fichier.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
for _path in (SRC_ROOT, SCRIPTS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# --- Hypothèses de relance ---------------------------------------------------
# Le run mort n'a pas écrit de manifest exploitable ; on s'appuie sur le
# progress report + structure connue du disque L:/. Édite si nécessaire.

RUN_ID = "lab_train-2026-05-28-5pairs-186j"
OUTPUT_ROOT = Path(
    "K:/output lab/runs/lab_train-2026-05-28-5pairs-186j/phase_a2_data_factory"
)
SILVER_ROOT = OUTPUT_ROOT / "silver"
GOLD_ROOT = OUTPUT_ROOT / "gold"

# L:/ contient les 3 sous-dossiers trades/, klines/, ordrebookpart1/. Le data
# factory scanne récursivement → un seul --raw-root suffit.
RAW_ROOTS: tuple[Path, ...] = (Path("L:/"),)

# Reproduit la request du progress report (5 pairs, 15m, 22 features, fenêtre
# 2025-04-29 → 2025-10-31).
PAIRS = ("ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT")
TIMEFRAMES = ("15m",)
FEATURE_NAMES = (
    "close_return",
    "high_low_range",
    "volume",
    "spread_bps",
    "slippage_bps",
    "book_depth_levels",
    "break_even_bps",
    "fragility_score",
    "false_breakout_context",
    "vpin",
    "cumulative_ofi",
    "queue_pressure",
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
    "latency_penalty_bps",
    "micro_edge_exit_governor_observed",
    "micro_edge_entry_timing_observed",
    "history_score",
    "marginal_value_score",
    "reentry_lateness",
    "concentration_headroom",
)
START = "2025-04-29"
END = "2025-10-31"

# Storage : on conserve le format jsonl-gz observé sur disque, budget relevé
# à 100 GB (silver existant = 38 GB) pour éviter un re-déclenchement de
# STORAGE_BUDGET_EXCEEDED.
STORAGE_FORMAT = "jsonl-gz"
STORAGE_BUDGET_LIMIT_BYTES = 100 * 1024 * 1024 * 1024  # 100 GB

# Hypothèse : run original probablement lancé avec --use-measured-economic-
# provenance (sinon spread/slippage restent DEFAULT_BY_BOOK_STATUS et le
# diagnostic backbone-METRICS reste muet). Mets à False si tu sais que
# l'original ne l'utilisait pas.
USE_MEASURED_ECONOMIC_PROVENANCE = True

# Fenêtre > 7 jours → requis pour passer le scope guard du data factory.
ALLOW_BROAD_RUN = True

# --- Exec --------------------------------------------------------------------


def _csv(values: tuple[str, ...]) -> str:
    return ",".join(values)


def main() -> int:
    from run_strategy_ladder_data_factory import main as df_main

    argv: list[str] = [
        "--run-id",
        RUN_ID,
        "--output-root",
        str(OUTPUT_ROOT.resolve()),
        "--silver-root",
        str(SILVER_ROOT.resolve()),
        "--gold-root",
        str(GOLD_ROOT.resolve()),
        "--storage-format",
        STORAGE_FORMAT,
        "--storage-budget-limit-bytes",
        str(STORAGE_BUDGET_LIMIT_BYTES),
        "--pairs",
        _csv(PAIRS),
        "--timeframes",
        _csv(TIMEFRAMES),
        "--feature-names",
        _csv(FEATURE_NAMES),
        "--start",
        START,
        "--end",
        END,
        "--resume",
    ]
    for raw_root in RAW_ROOTS:
        argv.extend(["--raw-root", str(raw_root.resolve())])
    if ALLOW_BROAD_RUN:
        argv.append("--allow-broad-run")
    if USE_MEASURED_ECONOMIC_PROVENANCE:
        argv.append("--use-measured-economic-provenance")

    print(
        "[relance] cmd: python scripts/run_strategy_ladder_data_factory.py "
        + " ".join(repr(arg) if " " in arg else arg for arg in argv),
        flush=True,
    )
    return df_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
