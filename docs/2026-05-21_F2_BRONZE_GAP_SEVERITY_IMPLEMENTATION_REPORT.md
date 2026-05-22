# F2 Bronze Gap Severity Classifier — Implementation Report

**Date :** 2026-05-21
**Statut :** ✅ CODE LIVRÉ + 11 nouveaux tests PASS + 28/28 régression complète
**Run référence :** `f9bb2bdc0c8ce1fd` (gap_count=2, largest=60s)
**Quote user :** *« f2 bronze gaps »*

---

## Résumé exécutif

Remplacement du check binaire `BRONZE_GAPS_PRESENT` (déclenché par n'importe quel gap_count > 0) par un classifier **3-tiers** qui distingue research-acceptable des fail-close.

| Aspect | Avant F2 | Après F2 |
|---|---|---|
| Logique | `if gap_count > 0: BRONZE_GAPS_PRESENT` (binaire) | 3-tier severity classifier |
| Status code | `BRONZE_GAPS_PRESENT` (générique) | `WITHIN_TOLERANCE` / `TOLERATED_RESEARCH_GRADE` / `BLOCKED` |
| Blocker propagation | Tout gap = SILVER_SYNC_PARTIAL | Promotion-only blockers pour research-grade, hard blockers pour fail-close |
| Audit visibility | Pas de tier | `bronze_gap_severity_status` exposé dans silver_quality_report |

---

## Code modifié

### [`silver_market_synchronizer.py`](../src/local_replay_runtime/silver_market_synchronizer.py)

**Changement #1 — Nouveau dataclass `BronzeGapSeverityThresholds`** :
```python
@dataclass(frozen=True)
class BronzeGapSeverityThresholds:
    research_max_gap_ms: int = 60_000          # 1 min individual (research OK)
    research_max_total_gap_count: int = 10     # ≤10 gaps total (research OK)
    promotion_max_gap_ms: int = 5_000          # 5 sec (promotion strict)
    promotion_max_total_gap_count: int = 2     # ≤2 gaps (promotion strict)
```

**Changement #2 — Nouvelle fonction `classify_bronze_gap_severity()`** :
- Tier 1 : `gap_count = 0` → `BRONZE_GAPS_WITHIN_TOLERANCE`, aucun blocker
- Tier 2 : gaps mineurs (≤10 total, ≤60s individuel) → `TOLERATED_RESEARCH_GRADE`, blockers PROMOTION-only
- Tier 3 : gaps massifs → `BLOCKED`, blockers RESEARCH (hard fail-close)

**Changement #3 — `build_silver_synchronized_market_manifest`** :
- Remplace `if bronze_index.gap_count > 0: BRONZE_GAPS_PRESENT` par appel au classifier
- Propage les blockers granulaires au manifest

**Changement #4 — `build_silver_quality_report`** :
- Ajoute le champ `bronze_gap_severity_status` au report dict
- Permet aux scripts downstream de différencier les 3 tiers

**Export** :
- `BronzeGapSeverityThresholds` et `classify_bronze_gap_severity` exposés dans `__all__`

---

## Taxonomie de blocker codes

### AVANT F2 (binaire)
```
BRONZE_GAPS_PRESENT          # générique, déclenché par n'importe quel gap
```

### APRÈS F2 (granulaire)
```
# Tier RESEARCH-blocked (hard fail-close)
BRONZE_GAP_LARGEST_EXCEEDS_RESEARCH_TOLERANCE
BRONZE_GAP_COUNT_EXCEEDS_RESEARCH_TOLERANCE

# Tier RESEARCH-acceptable, PROMOTION-blocked
BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE
BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE
```

---

## Impact sur le run f9bb2bdc

| Métrique | Avant F2 | Après F2 |
|---|---|---|
| `bronze_gap_count` | 2 | 2 (inchangé, c'est de la mesure) |
| `bronze_largest_gap_ms` | 60_000 | 60_000 (inchangé) |
| `blocker_codes` contient | `BRONZE_GAPS_PRESENT` | `BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE`, `BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE` |
| `bronze_gap_severity_status` | absent | **`BRONZE_GAPS_TOLERATED_RESEARCH_GRADE`** ✅ |
| `silver_sync_status` | `SILVER_SYNC_PARTIAL` | `SILVER_SYNC_PARTIAL` (inchangé — promotion-blocked) |

**Conséquence majeure :** sur ce run, les 2 gaps × 60s deviennent explicitement **research-acceptable**. Le blocker `BRONZE_GAPS_PRESENT` (générique, alarmiste) est éliminé et remplacé par 2 blockers PROMOTION-only qui sont semantiquement plus clairs et permettent la consommation downstream différenciée (research-grade pipelines peuvent ignorer, promotion-grade doivent block).

---

## Garde-fous doctrinaux V5.3 préservés

- ✅ **Fail-close strict** : > 60s OR > 10 gaps → BLOCKED (hard)
- ✅ **No magic numbers** : tous seuils dans dataclass `BronzeGapSeverityThresholds` (overridable pour tests/calibration)
- ✅ **Audit-ready** : `bronze_gap_severity_status` exposé explicit dans quality_report
- ✅ **Backward-compat semantique** : tout gap continue à produire `SILVER_SYNC_PARTIAL` (le silver n'est plus "READY" si gaps présents, juste différenciation du tier)
- ✅ **Cohérence avec P1** (OHLCV severity classifier) : même pattern 3-tier WITHIN/TOLERATED/BLOCKED

---

## Tests dédiés (11 nouveaux, tous PASS)

| Test | Cible |
|---|---|
| `test_bronze_gap_severity_within_tolerance_no_gaps_2026_05_21` | Tier 1 : 0 gaps |
| `test_bronze_gap_severity_research_grade_minor_gaps_2026_05_21` | Tier 2 : 60s/3 gaps |
| `test_bronze_gap_severity_blocked_largest_gap_exceeds_research_2026_05_21` | Tier 3 : > 60s |
| `test_bronze_gap_severity_blocked_count_exceeds_research_2026_05_21` | Tier 3 : > 10 gaps |
| `test_bronze_gap_severity_blocked_combined_count_and_size_2026_05_21` | Tier 3 : combined |
| `test_bronze_gap_severity_research_grade_promotion_only_count_2026_05_21` | Tier 2 : 5 gaps × 4s |
| `test_bronze_gap_severity_within_tolerance_promotion_grade_2026_05_21` | Tier 1 : 1 gap × 3s (promotion OK) |
| `test_bronze_gap_severity_custom_thresholds_2026_05_21` | Override thresholds |
| `test_silver_quality_report_exposes_bronze_gap_severity_status_2026_05_21` | Quality report exposition |
| `test_silver_quality_report_severity_when_no_gaps_2026_05_21` | Quality report 0 gaps |
| `test_run_f9bb2bdc_gap_pattern_resolves_to_research_grade_2026_05_21` | Validation pattern réel run audit-é |

**Régression complète :** 28/28 tests passent (F2 + F16-B + indexer P2/P3 + OHLCV P1).

---

## Couverture des scénarios

| Scenario | gap_count | largest_gap_ms | Tier | Blockers |
|---|---|---|---|---|
| Idéal | 0 | 0 | WITHIN_TOLERANCE | aucun |
| Promotion-grade strict | 1 | 3_000 | WITHIN_TOLERANCE | aucun |
| Promotion-blocked (size) | 1 | 60_000 | TOLERATED_RESEARCH | LARGEST_EXCEEDS_PROMOTION |
| Promotion-blocked (count) | 5 | 4_000 | TOLERATED_RESEARCH | COUNT_EXCEEDS_PROMOTION |
| Run f9bb2bdc (réel) | 2 | 60_000 | TOLERATED_RESEARCH | LARGEST + COUNT promotion |
| Research-blocked (size) | 1 | 120_000 | BLOCKED | LARGEST_EXCEEDS_RESEARCH |
| Research-blocked (count) | 15 | 10_000 | BLOCKED | COUNT_EXCEEDS_RESEARCH |
| Research-blocked combined | 20 | 120_000 | BLOCKED | LARGEST + COUNT research |

---

## Reste à faire (hors scope F2)

| # | Item | Effort |
|---|---|---|
| F4 | Metadata historical date-by-date | 0.5j |
| F1 | Venue VERIFIED par hash | 0.5-1j |
| P6 | Fail-close A2→B1/B2 | 1j |
| Calibration thresholds engines a/b | À décider | 3-5j |
| P0-A Phase 1 (re-run A2 6 mois) | Lancer avec patches déjà appliqués | 2-3h |

---

## Quote utilisateur

- *« f2 bronze gaps »* — autorisation directe pour F2

---

## Tasks complétées

- ✅ #2 F2 Bronze gaps severity classifier (Patch 2) — done

---

## NEXT — options pour suite

| # | Action | Effort |
|---|---|---|
| A | F4 metadata switch (drop CURRENT_METADATA_PROXY) | 0.5j |
| B | F1 venue VERIFIED (drop RAW_SOURCE_TYPE_INFERRED) | 0.5-1j |
| C | P6 fail-close A2→B1/B2 gate | 1j |
| D | Diagnostic upstream inputs engine_a/b (Option 1 P0-B) | 1j |
| E | Calibration thresholds engines (Option 2 P0-B) | 3-5j |
| F | Re-run A2 sur 6 mois δ pour mesurer effet patches | 2-3h |
| G | Tous en parallèle (4+ worktrees) | varies |
