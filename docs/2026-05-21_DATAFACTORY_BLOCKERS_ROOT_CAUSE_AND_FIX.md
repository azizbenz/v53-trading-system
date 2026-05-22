# Datafactory Blockers — Root Cause Analysis + Fix Plan

**Date :** 2026-05-21
**Run audité :** `L:\output backtest\runs\strategy_ladder_workflow-f9bb2bdc0c8ce1fd`
**Objectif :** comprendre pourquoi A2 produit ces blockers + patcher le code pour produire un dataset prod-safe (pas juste gater downstream)
**Doc compagnon :** [`2026-05-20_A2_FAILCLOSE_BUG_PATCH_PLAN.md`](2026-05-20_A2_FAILCLOSE_BUG_PATCH_PLAN.md) (gate downstream — orthogonal à ce travail)

---

## 1. Liste exhaustive des blockers observés

```json
"blocker_codes": [
    "RAW_SOURCE_TYPE_INFERRED",                       // F1 — research-acceptable
    "CURRENT_METADATA_PROXY",                          // F4 — research-acceptable
    "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED",          // ⚠ CRITIQUE
    "OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED",         // ⚠ CRITIQUE
    "SINGLE_PAIR_RESEARCH_ONLY",                       // F13 — research-acceptable
    "BRONZE_GAPS_PRESENT",                             // F2 partial — severity à classifier
    "BRONZE_SCHEMA_BLOCKER"                            // ⚠ CRITIQUE
]
```

Pour un dataset prod-safe, focus sur les 3 CRITIQUES + clarifier les 4 research-acceptable.

---

## 2. Root cause BLOCKER #1 — `OHLCV_<tf>_TEMPORAL_COMPLETENESS_BLOCKED`

### Code source

[`strategy_ladder_data_factory.py:155-201`](../src/local_replay_runtime/strategy_ladder_data_factory.py:155)

### Constantes-clés (lignes 99-106)

```python
_CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS: dict[str, int] = {
    "1m": 60_000,
    "10m": 10 * 60_000,
}
_CRITICAL_OHLCV_EXPECTED_ROWS_PER_DAY: dict[str, int] = {
    "1m": 1_440,
    "10m": 144,
}
```

**⚠ DÉCOUVERTE 1 :** Seuls **1m et 10m** sont considérés "critiques" pour temporal completeness. Pas 5m, pas 15m. C'est pourquoi les blockers ne concernent QUE ces 2 timeframes — ce n'est PAS un signe que 5m/15m sont OK, c'est qu'ils ne sont **pas vérifiés du tout**.

### Logique de déclenchement (lignes 180-188)

```python
if (
    entry.expected_interval_ms != expected_interval_ms     # mauvais interval
    or entry.row_count != expected_rows                     # row count != 1440 (1m) ou 144 (10m)
    or entry.missing_candle_count > 0                       # gaps dans la séquence
    or entry.duplicate_candle_count > 0                     # bars dupliquées
):
    blocker_codes.append(f"OHLCV_{tf.upper()}_TEMPORAL_COMPLETENESS_BLOCKED")
```

**4 causes potentielles** chacune suffisante pour déclencher le blocker.

### Pourquoi 1m et 10m bloqués SPÉCIFIQUEMENT

Hypothèses ordonnées par probabilité :

| Hypothèse | Vraisemblance | Action diag |
|---|---|---|
| **H1 : 10m n'est PAS un kline natif Bybit** | 🔴 TRÈS HAUTE | Bybit supporte 1m/3m/5m/15m/30m/60m... **PAS 10m**. Le 10m est probablement dérivé/aggrégé depuis 1m. Si la dérivation a des bugs → row_count ≠ 144 |
| **H2 : 1m a un missing candle (Bybit maintenance/halt)** | 🟡 MOYENNE | Bybit halts ponctuels créent 1 minute manquante. Sur 1440 attendus → 1439 → blocker |
| **H3 : Dupli sur boundary minuit UTC** | 🟡 MOYENNE | Bar à 23:59 jour N et bar à 23:59 jour N+1 si fichier coupe mal |
| **H4 : 10m derivé incorrectement** | 🟡 MOYENNE | Si 1m a un trou, 10m aggrégé hérite du trou |

**Diagnostic ciblé requis :** lire un fichier `silver/.../ohlcv/1m/.../22.jsonl.gz` et `10m/.../22.jsonl.gz` pour voir row_count exact et missing/duplicate counts.

### 3 options de fix

**Option A — Backfill (fix source data)**
- Détecter missing candles et les compléter par interpolation OHLCV (forward-fill close, V=0)
- ⚠ DANGER : interpolation OHLCV biaise les features microstructure
- ⚠ Doctrine V5.3 fail-closed déconseille interpolation silencieuse

**Option B — Severity classifier (relax tolerance)**
- Ajouter seuil de tolerance : si `missing_candle_count / expected_rows < 0.001` (0.1%) → TOLERATED
- Pour 1m sur 1 jour : 1 missing minute sur 1440 = 0.07% → TOLERATED
- Status : `OHLCV_TEMPORAL_COMPLETENESS_TOLERATED_WITHIN_THRESHOLD`
- Reste audit-visible mais ne bloque pas
- ⚠ Question doctrinale : 1 minute manquante sur 1440 = acceptable pour research, peut-être pas promotion

**Option C — Retirer 10m du critical list**
- Si 10m n'est pas natif Bybit et donc dérivé incorrectement, le retirer de `_CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS`
- Tracker 10m comme `OHLCV_10M_DERIVED_FROM_1M` (statut informationnel, pas blocker)
- ⚠ Implique : engines C/D qui utilisent 10m devraient soit utiliser 5m/15m, soit accepter la dérivation

**Recommandation :** **B + C combinées** :
1. Retirer 10m du critical list (10m derivé, pas natif Bybit)
2. Ajouter severity classifier pour 1m (TOLERATED si gaps < 0.1%)
3. Forcer fail-close si gaps > 0.5% (promotion-grade)

---

## 3. Root cause BLOCKER #2 — `BRONZE_SCHEMA_BLOCKER`

### Code source

[`silver_market_synchronizer.py:87-88`](../src/local_replay_runtime/silver_market_synchronizer.py:87)

```python
if bronze_index.index_status == "BRONZE_INDEX_BLOCKED_BY_SCHEMA":
    blocker_codes.append("BRONZE_SCHEMA_BLOCKER")
```

### Origine de `BRONZE_INDEX_BLOCKED_BY_SCHEMA`

[`raw_market_data_indexer.py:627-628`](../src/local_replay_runtime/raw_market_data_indexer.py:627)

```python
if any(item.source_status == "RAW_FILE_SCHEMA_UNKNOWN" for item in relevant):
    status = "BRONZE_INDEX_BLOCKED_BY_SCHEMA"
```

### Origine de `RAW_FILE_SCHEMA_UNKNOWN`

[`raw_market_data_indexer.py:354 et 375`](../src/local_replay_runtime/raw_market_data_indexer.py:354)

Le `RAW_FILE_SCHEMA_UNKNOWN` est appliqué quand :
1. CSV : structure ne match aucun des schémas connus
2. JSON : parse error OU records=empty OU schéma non reconnu

**⚠ DÉCOUVERTE 2 :** Au moins 1 fichier raw L: sur ce run a un schéma non reconnu par le parseur V5.3. **C'est probablement un fichier corrompu, ou un nouveau format Bybit que le parseur ne connaît pas.**

### Diagnostic ciblé requis

Il faut trouver QUEL fichier est `SCHEMA_UNKNOWN`. Le `raw_file_manifest.jsonl.gz` du run contient cette info per-file.

### 3 options de fix

**Option A — Améliorer le parseur**
- Si nouveau format Bybit (ex: changement colonnes 2025) : ajouter le schéma au parseur
- Effort variable (dépend du diff de format)

**Option B — Exclure les fichiers SCHEMA_UNKNOWN du bronze index**
- Ne pas inclure les fichiers UNKNOWN dans l'agrégation
- Promouvoir status à `BRONZE_INDEX_PARTIAL_SCHEMA_EXCLUDED`
- ⚠ Risque : exclure silencieusement des données pourrait masquer des problèmes

**Option C — Severity classifier**
- 1 fichier UNKNOWN sur 100 = WARN, pas BLOCK
- Tous fichiers UNKNOWN = BLOCK
- Status intermédiaire : `BRONZE_SCHEMA_PARTIAL_UNKNOWN`

**Recommandation :** **A d'abord** (diag + fix parseur), puis B/C selon ce qu'on trouve.

---

## 4. Root cause BLOCKER #3 — `BRONZE_GAPS_PRESENT`

### Code source

[`raw_market_data_indexer.py:608-624`](../src/local_replay_runtime/raw_market_data_indexer.py:608)

```python
gap_count = 0
largest_gap_ms = 0
for manifest in ordered_by_type:
    previous = previous_by_type.get(manifest.source_type)
    if previous is not None:
        if (manifest.start_timestamp_ms or 0) > (previous.end_timestamp_ms or 0):
            gap = (manifest.start_timestamp_ms or 0) - (previous.end_timestamp_ms or 0)
            if gap > 0:
                gap_count += 1
                largest_gap_ms = max(largest_gap_ms, gap)
```

### Sur le run actuel

```json
"bronze_gap_count": 2,
"bronze_largest_gap_ms": 60000
```

**Interprétation :** 2 gaps temporels entre fichiers raw consécutifs, max 60 secondes. Probablement les boundaries jour entre fichiers (ex: fichier jour J finit à 23:59:00, fichier jour J+1 commence à 00:00:00 → 60s gap si pas chevauchant).

### Fix

C'est exactement la **F2 — Patch 2 (Bronze severity classifier)** déjà planifiée. Pas de nouveau fix nécessaire si F2 est implémenté.

**Rappel taxonomie F2 :**
- `bronze_gap_max_ms_research = 60_000` (1 min) → TOLERATED
- `bronze_gap_max_ms_promotion = 5_000` (5 sec) → BLOCKED promotion
- `bronze_gap_count_max_per_day = 5` → BLOCKED si dépassé

Sur ce run : 2 gaps × 60s/jour → TOLERATED (research) mais BLOCKED (promotion).

---

## 5. Blockers research-acceptable — clarification

| Blocker | Statut actuel | Fix planifié |
|---|---|---|
| `RAW_SOURCE_TYPE_INFERRED` | Research-acceptable | **F1 Patch** (venue verified by hash, ~80L) — déjà planifié |
| `CURRENT_METADATA_PROXY` | Research-acceptable | **F4 mode switch** (bybit_historical_metadata.py existe déjà, 0.5j) — déjà planifié |
| `SINGLE_PAIR_RESEARCH_ONLY` | Research-acceptable | **F13** — multi-pair (1-2j, dépend disponibilité dumps) — planifié |

**Note :** Sur le run `f9bb2bdc`, le `RAW_SOURCE_TYPE_INFERRED` paraît dans `blocker_codes` MAIS le `raw_source_typing_status` est marqué `RAW_SOURCE_TYPED_READY`. **Incohérence interne du manifest** — F1 partiellement appliqué mais propagation des blockers pas à jour.

---

## 6. Synthèse — Plan d'attaque chirurgical

### Tier 0 — Diagnostic ciblé AVANT tout code (~2h)

Avant de patcher, il faut **lire les fichiers réels** pour confirmer les hypothèses :

| # | Diagnostic | Fichier à inspecter | Question |
|---|---|---|---|
| D1 | OHLCV 1m row count | `silver/.../ohlcv/1m/.../22.jsonl.gz` | row_count = 1440 ou autre ? Missing where ? |
| D2 | OHLCV 10m row count | `silver/.../ohlcv/10m/.../22.jsonl.gz` | row_count = 144 ou autre ? Dérivé ou natif ? |
| D3 | Fichier SCHEMA_UNKNOWN | `raw_file_manifest.jsonl.gz` | Quel fichier (csv ou json) a status UNKNOWN ? |
| D4 | Bronze gap localisation | `bronze_market_index.json` | Quels 2 gaps précisément (entre quels fichiers) ? |

### Tier 1 — Patches code (par ordre de criticité)

| # | Patch | Effort | Bloque dataset prod-safe ? |
|---|---|---|---|
| **P1** | Severity classifier OHLCV temporal (Option B+C section 2) | 1j | OUI — bloque 1m+10m readiness |
| **P2** | Diag + fix parseur SCHEMA_UNKNOWN (Option A section 3) | 0.5-2j (dépend du diag) | OUI — bloque schema readiness |
| **P3** | F2 bronze gaps severity classifier (déjà planifié) | 1j | OUI — bloque gaps readiness |
| **P4** | F4 metadata mode switch (déjà planifié) | 0.5j | NON (research-acceptable) |
| **P5** | F1 venue verified by hash (déjà planifié) | 0.5-1j | NON (research-acceptable) |
| **P6** | Fail-close A2→B1/B2 (déjà planifié) | 1j | OUI — sécurité downstream |

**Effort total Tier 1 : ~4-6 jours** pour avoir un dataset vraiment prod-safe (pas juste research).

### Tier 2 — Doctrine multi-pair (F13)

Hors scope immédiat. Multi-pair = phase ultérieure une fois dataset 1-pair propre.

---

## 7. Recommandation séquence d'exécution

```
J0 (2h)   Diagnostic D1-D4 — confirmer hypothèses
          ↓
J1 (1j)   P1 OHLCV severity classifier (retirer 10m du critical + tolérance 1m)
J1 (1j)   P3 F2 bronze gaps severity classifier (en parallèle)
          ↓
J2 (0.5-2j) P2 fix SCHEMA_UNKNOWN (selon diag D3)
          ↓
J3 (0.5j) P4 F4 metadata switch
J3 (0.5j) P5 F1 venue verified
          ↓
J4 (1j)   P6 fail-close A2→B1/B2 (assurance)
          ↓
J5        Re-run dataset → vérifier que blockers CRITIQUES = 0
```

**Total : ~5 jours ouvrés** pour un dataset que A2 marquerait comme `DATA_FACTORY_READY` (au lieu de `DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS`).

---

## 8. Définition de DATASET PROD-SAFE (post-fix)

A2 manifeste après patches doit avoir :

```json
{
    "data_factory_status": "DATA_FACTORY_READY",
    "blocker_codes": [],                                        // VIDE
    "ohlcv_temporal_completeness_status": "OHLCV_TEMPORAL_COMPLETENESS_READY_WITH_TOLERANCE",  // OU READY
    "bronze_schema_status": "BRONZE_SCHEMA_READY",
    "bronze_gap_severity_status": "BRONZE_GAPS_WITHIN_TOLERANCE",
    "raw_source_typing_status": "RAW_SOURCE_TYPED_READY",      // déjà OK
    "metadata_temporal_status": "HISTORICAL_METADATA_DATE_RESOLVED",  // après F4
    "raw_source_provenance_status": "RAW_SOURCE_MANIFEST_VERIFIED"   // après F1
}
```

Et workflow_manifest dérive `phase_status: PHASE_A2_DATA_FACTORY_READY` sans contradiction.

---

## 9. Risques + caveats

| Risque | Mitigation |
|---|---|
| Severity tolerances trop laxistes → laisse passer du vrai garbage | Tests régression avec fixtures de gaps connus |
| Retirer 10m du critical → engines C/D mal alimentés | Vérifier que engines acceptent 10m dérivé ou ne l'utilisent pas |
| Parseur SCHEMA_UNKNOWN cache un changement de format Bybit | Diagnostic D3 obligatoire avant fix code |
| F2 + P1 ensemble → double comptage si pas attention | Tests integration A2 complet |

---

## 10. NEXT — confirmation utilisateur

Tu valides :
1. **Tier 0 diagnostic d'abord** (2h) avant tout code ?
2. **Severity classifier OHLCV** comme approche (Option B+C section 2) plutôt que backfill ?
3. **Retirer 10m du critical list** (10m derivé, pas natif Bybit) ?
4. **Sequence J0→J5 (~5 jours)** pour dataset prod-safe ?

Si oui sur les 4 → je lance D1-D4 immédiatement.
