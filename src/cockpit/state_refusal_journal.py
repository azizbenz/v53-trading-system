"""Phase 2 adapter — Taleb Refusal Journal (placeholder until persisted).

The runtime module exists at ``src/meta_minimal/refusal_journal/refusal_journal.py``
but the journal is not yet flushed to disk by the Shadow service. Until
Phase 2.1 wires the flush, the cockpit surfaces the tail-risk breakers
(via ``state_tail_risk``) as a visible substitute and uses this adapter to
render a banner explaining the situation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error", "not_yet_persisted"]


class RefusalMotif(BaseModel, frozen=True):
    motif: str
    count: int = 0
    last_observed_at: str = ""


class RefusalJournalSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "not_yet_persisted"
    source_path: str = ""
    top_motifs: tuple[RefusalMotif, ...] = ()
    tail_risk_meter: float = 0.0
    quadruple_filter_bayes_evidence: bool = False
    quadruple_filter_oos_validation: bool = False
    quadruple_filter_tail_risk_audit: bool = False
    quadruple_filter_regime_stationarity: bool = False
    anti_survivorship: bool = False
    info_message: str = (
        "Refusal Journal not yet persisted to disk. "
        "Phase 2.1 will wire src/meta_minimal/refusal_journal/refusal_journal.py "
        "to dump motifs every Shadow cycle. In the meantime, see the Tail-Risk "
        "Breakers card below for the closest doctrinal substitute."
    )


def read_refusal_journal(service_dir: Path) -> RefusalJournalSnapshot:
    path = service_dir / "refusal_journal.snapshot.json"
    if not path.is_file():
        return RefusalJournalSnapshot(source_status="not_yet_persisted")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse refusal journal %s: %s", path, exc)
        return RefusalJournalSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return RefusalJournalSnapshot(source_status="parse_error", source_path=str(path))
    motifs_raw = payload.get("top_motifs") or ()
    motifs = tuple(
        RefusalMotif(
            motif=str(m.get("motif", "")),
            count=int(m.get("count", 0) or 0),
            last_observed_at=str(m.get("last_observed_at", "")),
        )
        for m in motifs_raw
        if isinstance(m, dict)
    )
    qf = payload.get("quadruple_filter") or {}
    if not isinstance(qf, dict):
        qf = {}
    return RefusalJournalSnapshot(
        source_status="ok",
        source_path=str(path),
        top_motifs=motifs,
        tail_risk_meter=float(payload.get("tail_risk_meter", 0.0) or 0.0),
        quadruple_filter_bayes_evidence=bool(qf.get("bayes_evidence", False)),
        quadruple_filter_oos_validation=bool(qf.get("out_of_sample_validation", False)),
        quadruple_filter_tail_risk_audit=bool(qf.get("tail_risk_audit", False)),
        quadruple_filter_regime_stationarity=bool(qf.get("regime_stationarity", False)),
        anti_survivorship=bool(payload.get("anti_survivorship", False)),
    )


__all__ = ["RefusalJournalSnapshot", "RefusalMotif", "read_refusal_journal"]
