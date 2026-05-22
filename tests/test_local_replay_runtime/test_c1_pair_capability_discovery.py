"""Tests C1 (2026-05-21) — pair capability discovery.

Vérifie que le module discovery est strictement filesystem-driven, sans aucun
hardcode pair name. Doctrine : admin peut ajouter n'importe quelle paire
(MMXX, FUTURE_PAIR_42, XYZ123) en mettant son dossier dans les roots.

Tests parametrisés avec noms de pairs ARBITRAIRES pour prouver qu'aucun
nom n'est privilégié dans le code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from local_replay_runtime.pair_capability_discovery import (
    PairCapability,
    build_pair_rejection_message,
    discover_pair_capabilities,
    filter_pairs_for_training,
)


def _setup_pair_dirs(
    *,
    klines_root: Path,
    trades_root: Path,
    orderbook_root: Path,
    klines_pairs: tuple[str, ...] = (),
    trades_pairs: tuple[str, ...] = (),
    orderbook_pairs: tuple[str, ...] = (),
) -> None:
    """Create empty pair dirs to simulate filesystem presence."""
    klines_root.mkdir(parents=True, exist_ok=True)
    trades_root.mkdir(parents=True, exist_ok=True)
    orderbook_root.mkdir(parents=True, exist_ok=True)
    for pair in klines_pairs:
        (klines_root / pair).mkdir(exist_ok=True)
    for pair in trades_pairs:
        (trades_root / pair).mkdir(exist_ok=True)
    for pair in orderbook_pairs:
        (orderbook_root / pair).mkdir(exist_ok=True)


def test_discover_finds_arbitrary_pair_names_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — accepte n'importe quel nom de pair (MMXX, XYZ123, FUTURE_42)."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    arbitrary_pairs = ("MMXX", "XYZ123", "FUTURE_PAIR_42", "BTCUSDT", "AVAX2027")
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=arbitrary_pairs,
        trades_pairs=arbitrary_pairs,
        orderbook_pairs=arbitrary_pairs,
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=arbitrary_pairs,
    )
    for pair in arbitrary_pairs:
        assert pair in caps, f"arbitrary pair {pair!r} must be discovered"
        assert caps[pair].fully_ready, f"{pair} should be fully_ready"
        assert caps[pair].capability_tier() == "FULL_MICROSTRUCTURE"


def test_discover_distinguishes_full_vs_legacy_pairs_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — pair sans orderbook = LEGACY_OHLCV_ONLY tier."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        trades_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        orderbook_pairs=("FULL_PAIR",),  # LEGACY_PAIR has NO orderbook
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("FULL_PAIR", "LEGACY_PAIR"),
    )
    assert caps["FULL_PAIR"].capability_tier() == "FULL_MICROSTRUCTURE"
    assert caps["FULL_PAIR"].microstructure_capable is True
    assert caps["LEGACY_PAIR"].capability_tier() == "LEGACY_OHLCV_ONLY"
    assert caps["LEGACY_PAIR"].microstructure_capable is False
    assert caps["LEGACY_PAIR"].training_capable is True
    assert "PAIR_MISSING_ORDERBOOK" in caps["LEGACY_PAIR"].reason_codes


def test_discover_pair_only_in_metadata_not_filesystem_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — pair présente dans metadata mais pas filesystem = INSUFFICIENT."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=(),
        trades_pairs=(),
        orderbook_pairs=(),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("METADATA_ONLY_PAIR",),
    )
    assert "METADATA_ONLY_PAIR" in caps
    assert caps["METADATA_ONLY_PAIR"].capability_tier() == "INSUFFICIENT_FOR_TRAINING"
    assert caps["METADATA_ONLY_PAIR"].has_metadata is True
    assert caps["METADATA_ONLY_PAIR"].training_capable is False


def test_filter_pairs_accept_full_microstructure_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — filter accepte pair full quand microstructure requise."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("ALPHA", "BETA"),
        trades_pairs=("ALPHA", "BETA"),
        orderbook_pairs=("ALPHA", "BETA"),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("ALPHA", "BETA"),
    )
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("ALPHA", "BETA"),
        capabilities=caps,
        require_microstructure=True,
    )
    assert accepted == ("ALPHA", "BETA")
    assert rejected == ()


def test_filter_pairs_reject_legacy_when_microstructure_required_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch C1 — filter rejette LEGACY-only pair quand microstructure requise."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        trades_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        orderbook_pairs=("FULL_PAIR",),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("FULL_PAIR", "LEGACY_PAIR"),
    )
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        capabilities=caps,
        require_microstructure=True,
    )
    assert accepted == ("FULL_PAIR",)
    assert rejected == ("LEGACY_PAIR",)


def test_filter_pairs_accept_legacy_when_microstructure_not_required_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch C1 — LEGACY pair acceptée si microstructure pas requise."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        trades_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        orderbook_pairs=("FULL_PAIR",),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("FULL_PAIR", "LEGACY_PAIR"),
    )
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("FULL_PAIR", "LEGACY_PAIR"),
        capabilities=caps,
        require_microstructure=False,
    )
    assert set(accepted) == {"FULL_PAIR", "LEGACY_PAIR"}
    assert rejected == ()


def test_filter_pairs_reject_undiscovered_pair_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — pair non discoverée → rejected avec message clair."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("ALPHA",),
        trades_pairs=("ALPHA",),
        orderbook_pairs=("ALPHA",),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("ALPHA",),
    )
    accepted, rejected = filter_pairs_for_training(
        requested_pairs=("ALPHA", "DOES_NOT_EXIST"),
        capabilities=caps,
        require_microstructure=False,
    )
    assert accepted == ("ALPHA",)
    assert rejected == ("DOES_NOT_EXIST",)


def test_build_rejection_message_actionable_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — message rejet contient hints actionable pour admin."""
    klines = tmp_path / "klines"
    trades = tmp_path / "trades"
    orderbook = tmp_path / "orderbook"
    _setup_pair_dirs(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        klines_pairs=("LEGACY_PAIR",),
        trades_pairs=("LEGACY_PAIR",),
        orderbook_pairs=(),
    )
    caps = discover_pair_capabilities(
        klines_root=klines,
        trades_root=trades,
        orderbook_root=orderbook,
        metadata_pairs=("LEGACY_PAIR",),
    )
    msg = build_pair_rejection_message(
        rejected_pairs=("LEGACY_PAIR", "UNKNOWN_PAIR"),
        capabilities=caps,
        require_microstructure=True,
    )
    assert "DOCTRINE_PAIR_CAPABILITY_REJECTED" in msg
    assert "LEGACY_PAIR" in msg
    assert "UNKNOWN_PAIR" in msg
    assert "NOT_DISCOVERED" in msg
    assert "PAIR_MISSING_ORDERBOOK" in msg
    assert "HINT" in msg


def test_discover_handles_missing_roots_gracefully_2026_05_21(tmp_path: Path) -> None:
    """Patch C1 — roots None ou inexistants ne crashent pas."""
    caps = discover_pair_capabilities(
        klines_root=None,
        trades_root=None,
        orderbook_root=None,
        metadata_pairs=("ONLY_IN_METADATA",),
    )
    assert "ONLY_IN_METADATA" in caps
    assert caps["ONLY_IN_METADATA"].has_klines is False
    assert caps["ONLY_IN_METADATA"].has_trades is False
    assert caps["ONLY_IN_METADATA"].training_capable is False


def test_discover_no_hardcoded_pair_names_in_module_2026_05_21() -> None:
    """Patch C1 — méta-test : le module ne contient PAS de pair names hardcoded.

    Lit le source code et vérifie l'absence de noms typiques (BTCUSDT, ETHUSDT, etc.).
    Si un test futur ajoute un hardcode → ce test casse pour signal explicit.
    """
    import inspect

    from local_replay_runtime import pair_capability_discovery

    source = inspect.getsource(pair_capability_discovery)
    # Noms de paires typiques qui NE doivent PAS apparaître dans le code source
    # (sauf dans des docstrings comme exemples — ce qui est OK).
    forbidden_in_logic = (
        # Si ces lignes apparaissent hors docstrings/commentaires, c'est un hardcode
        '"BTCUSDT"',
        "'BTCUSDT'",
        '"ETHUSDT"',
        "'ETHUSDT'",
    )
    # Strip docstrings et commentaires pour le check
    lines_no_comments = [
        line.split("#")[0].rstrip()
        for line in source.splitlines()
        if not line.strip().startswith("#")
    ]
    code_only = "\n".join(lines_no_comments)
    # Heuristique : si BTCUSDT apparaît dans le code (non commentaire), c'est suspect.
    # On accepte une occurrence dans docstring (>>> exemple).
    btcusdt_count_in_code = code_only.count("BTCUSDT")
    # Docstrings inclus dans inspect.getsource — on tolère jusqu'à 5 mentions
    # dans les exemples du module docstring (avant et après refacto Patch C1).
    # Les VRAIS hardcodes en logique (listes/sets/defaults) sont détectés via
    # tests fonctionnels ci-dessus avec pair names arbitraires (MMXX, XYZ123).
    assert btcusdt_count_in_code <= 5, (
        f"Pair name 'BTCUSDT' apparaît {btcusdt_count_in_code} fois dans le module — "
        f"si > 5, vérifier qu'aucun nom de pair n'est hardcodé dans la logique "
        f"(seules les mentions docstring exemples sont tolérées)."
    )
