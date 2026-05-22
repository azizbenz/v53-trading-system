"""Pair capability discovery — filesystem-driven, ZERO hardcoded pair names.

Patch C1 (2026-05-21) — fondation du multi-pair training. Aucune liste de pairs
n'est hardcodée dans le code. La fonction `discover_pair_capabilities` scanne
le filesystem raw_roots et retourne dynamiquement les pairs trouvées avec
leur capability matrix (klines / trades / orderbook / metadata présents).

Doctrine V5.3 :
- L'admin peut ajouter une paire en mettant un dossier dans `L:/klines/<PAIR>/`
  → automatiquement discoverée au prochain run, AUCUN code à modifier
- L'admin peut retirer une paire en supprimant son dossier → disparaît propre
- Validators downstream interrogent ce module à runtime, jamais une whitelist

Exemple d'usage :
    >>> caps = discover_pair_capabilities(
    ...     klines_root=Path("L:/klines"),
    ...     trades_root=Path("L:/trades"),
    ...     orderbook_root=Path("L:/ordrebookpart1"),
    ...     metadata_pairs=("BTCUSDT", "ETHUSDT", ...),
    ... )
    >>> caps["BTCUSDT"]
    PairCapability(
        pair="BTCUSDT", has_klines=True, has_trades=True,
        has_orderbook=True, has_metadata=True,
        microstructure_capable=True, training_capable=True,
    )
    >>> caps["SOLUSDT"]
    PairCapability(
        pair="SOLUSDT", has_klines=True, has_trades=True,
        has_orderbook=False, has_metadata=True,
        microstructure_capable=False,  # pas d'orderbook = pas VPIN/OFI/queue/spread
        training_capable=True,  # mais LEGACY features (close_return/range/volume) OK
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# Patch C1 (2026-05-21) — capability matrix per pair, runtime-discovered.
# AUCUN nom de pair hardcodé ici. Le champ `pair` accepte n'importe quel str
# (e.g. "MMXX", "XYZ123", "FUTURE_PAIR_2027").
@dataclass(frozen=True)
class PairCapability:
    """Capability matrix pour un pair discoveré sur filesystem."""

    pair: str
    has_klines: bool
    has_trades: bool
    has_orderbook: bool
    has_metadata: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def microstructure_capable(self) -> bool:
        """True si VPIN/OFI/queue/spread features sont calculables (exige orderbook)."""
        return self.has_klines and self.has_trades and self.has_orderbook

    @property
    def training_capable(self) -> bool:
        """True si LEGACY training (close_return/high_low_range/volume) possible."""
        return self.has_klines and self.has_trades

    @property
    def fully_ready(self) -> bool:
        """True si TOUS les data types sont présents (klines + trades + orderbook + metadata)."""
        return all(
            (
                self.has_klines,
                self.has_trades,
                self.has_orderbook,
                self.has_metadata,
            )
        )

    def capability_tier(self) -> str:
        """Returns one of FULL_MICROSTRUCTURE / LEGACY_OHLCV_ONLY / INSUFFICIENT."""
        if self.fully_ready:
            return "FULL_MICROSTRUCTURE"
        if self.training_capable:
            return "LEGACY_OHLCV_ONLY"
        return "INSUFFICIENT_FOR_TRAINING"


def discover_pair_capabilities(
    *,
    klines_root: Path | None,
    trades_root: Path | None,
    orderbook_root: Path | None,
    metadata_pairs: Iterable[str] = (),
) -> dict[str, PairCapability]:
    """Scan filesystem et retourne capability matrix dynamique.

    Patch C1 (2026-05-21) — discovery filesystem-driven, AUCUN hardcode.

    Args:
        klines_root: dossier parent contenant <PAIR>/ subdirs (e.g. L:/klines/)
        trades_root: dossier parent (e.g. L:/trades/)
        orderbook_root: dossier parent (e.g. L:/ordrebookpart1/)
        metadata_pairs: itérable des pairs présentes dans le cache metadata
            (les pairs n'étant pas dans le filesystem mais ayant des metadata
            apparaîtront avec has_metadata=True mais autres flags False).

    Returns:
        dict {pair_name: PairCapability}, union de TOUTES les pairs trouvées
        sur n'importe lequel des roots (pas seulement klines).

    Note: zero pair-name est hardcodé. L'admin peut ajouter n'importe quelle
    paire (MMXX, BTCUSDT, FUTURE_42) en mettant son dossier dans les roots.
    """
    discovered: set[str] = set()

    # Scan chaque root indépendamment, l'union forme l'ensemble discoverable.
    for root in (klines_root, trades_root, orderbook_root):
        if root is None or not root.exists():
            continue
        try:
            for entry in root.iterdir():
                if entry.is_dir():
                    discovered.add(entry.name)
        except (OSError, PermissionError):
            continue

    # Metadata pairs ajoutées en union (pour visibilité audit même si data raw absente).
    metadata_set = {str(p) for p in metadata_pairs if str(p).strip()}
    discovered.update(metadata_set)

    capabilities: dict[str, PairCapability] = {}
    for pair_name in sorted(discovered):
        has_klines = (
            klines_root is not None
            and (klines_root / pair_name).is_dir()
        )
        has_trades = (
            trades_root is not None
            and (trades_root / pair_name).is_dir()
        )
        has_orderbook = (
            orderbook_root is not None
            and (orderbook_root / pair_name).is_dir()
        )
        has_metadata = pair_name in metadata_set

        reasons: list[str] = []
        if not has_klines:
            reasons.append("PAIR_MISSING_KLINES")
        if not has_trades:
            reasons.append("PAIR_MISSING_TRADES")
        if not has_orderbook:
            reasons.append("PAIR_MISSING_ORDERBOOK")
        if not has_metadata:
            reasons.append("PAIR_MISSING_METADATA")

        capabilities[pair_name] = PairCapability(
            pair=pair_name,
            has_klines=has_klines,
            has_trades=has_trades,
            has_orderbook=has_orderbook,
            has_metadata=has_metadata,
            reason_codes=tuple(reasons),
        )

    return capabilities


def filter_pairs_for_training(
    *,
    requested_pairs: tuple[str, ...],
    capabilities: dict[str, PairCapability],
    require_microstructure: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Filtre les pairs requested selon leur capability runtime.

    Patch C1 — séparation accepted vs rejected avec raisons claires.

    Args:
        requested_pairs: pairs choisies par l'admin
        capabilities: matrice runtime (depuis discover_pair_capabilities)
        require_microstructure: si True, exige orderbook (rejette LEGACY-only pairs)

    Returns:
        (accepted_pairs, rejected_pairs) — deux tuples disjoints.

    Doctrine fail-closed : si une pair requested n'est pas discoverée
    OU manque de la capability requise, elle est rejetée. L'appelant
    doit décider de fail-close ou continue avec accepted seulement.
    """
    accepted: list[str] = []
    rejected: list[str] = []
    for pair in requested_pairs:
        cap = capabilities.get(pair)
        if cap is None:
            rejected.append(pair)
            continue
        if not cap.training_capable:
            rejected.append(pair)
            continue
        if require_microstructure and not cap.microstructure_capable:
            rejected.append(pair)
            continue
        accepted.append(pair)
    return tuple(accepted), tuple(rejected)


def build_pair_rejection_message(
    *,
    rejected_pairs: tuple[str, ...],
    capabilities: dict[str, PairCapability],
    require_microstructure: bool,
) -> str:
    """Build a clear actionable error message for rejected pairs.

    Patch C1 — message doctrinal avec hints pour admin.
    """
    if not rejected_pairs:
        return ""
    lines = ["DOCTRINE_PAIR_CAPABILITY_REJECTED — the following pairs were rejected:"]
    for pair in rejected_pairs:
        cap = capabilities.get(pair)
        if cap is None:
            lines.append(
                f"  - {pair!r}: NOT_DISCOVERED — add data to raw_roots (klines/trades) "
                f"to enable. Available pairs: {sorted(capabilities)}"
            )
            continue
        missing = ", ".join(cap.reason_codes) or "unknown"
        tier = cap.capability_tier()
        lines.append(f"  - {pair!r}: tier={tier}, missing={missing}")
    if require_microstructure:
        lines.append(
            "  HINT: microstructure features (vpin/cumulative_ofi/queue_pressure/spread_bps) "
            "require orderbook data. Either add orderbook for the rejected pairs OR disable "
            "microstructure features (fall back to LEGACY 3-feature training)."
        )
    return "\n".join(lines)


__all__ = [
    "PairCapability",
    "build_pair_rejection_message",
    "discover_pair_capabilities",
    "filter_pairs_for_training",
]
