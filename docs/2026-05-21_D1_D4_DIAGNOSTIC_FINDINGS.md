# Diagnostic D1-D4 — Résultats réels (run f9bb2bdc)

**Date :** 2026-05-21
**Méthode :** lecture fichiers réels (silver jsonl.gz décompressés + raw_file_manifest.jsonl.gz)
**Status :** DIAGNOSTIC TERMINÉ — hypothèses pré-diag MAJORITAIREMENT FAUSSES, vraie cause différente

---

## RÉCAP — réalité vs hypothèses

| # | Hypothèse pré-diag | Réalité confirmée | Verdict |
|---|---|---|---|
| D1 | 1m a missing minute Bybit (1439 sur 1440) | **Les RAW fichiers L: contiennent 1000 lignes MAX par jour** (pas 1440). Couvre seulement ~16h40 (02:00→18:39 UTC). | ❌ Hypothèse fausse — cause RÉELLE = **limite de download Bybit à 1000 lignes** |
| D2 | 10m dérivé incorrectement | **Idem 10m : 100 lignes MAX par fichier raw** (pas 144). Même limite, couvre ~16h40. | ❌ Hypothèse fausse — **PAS dérivé, est natif Bybit mais tronqué à 100** |
| D3 | Nouveau format Bybit ou fichier corrompu | **`symbol_metadata.jsonl` (METADATA, pas market data) a SCHEMA_UNKNOWN**. Bug parseur sur format JSONL metadata. | 🟢 Cause trouvée — **bug parseur metadata jsonl** |
| D4 | 2 gaps + boundaries jour mineurs | **`duplicate_timestamp_count=4`** vient de l'indexer qui compte ZIP ET le contenu EXTRACT comme 2 fichiers distincts | 🟢 Cause trouvée — **bug indexer zip vs extracted** |

---

## D1 — Détail réel OHLCV 1m

**Fichier raw inspecté :** `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_2025-07-23.csv`

```
row_count: 1000           ← devrait être 1440 (24h × 60min)
start_ts:  1753255200000  → 2025-07-23 02:00:00 UTC
end_ts:    1753315140000  → 2025-07-23 18:39:00 UTC
durée:     ~16h39 minutes
```

**Idem pour 2025-07-24 :** 1000 lignes, 02:00→18:39 UTC.

### Interprétation

Les fichiers raw `L:` 1m sont **systématiquement à 1000 lignes**, ne couvrent QUE 16h40 par jour. C'est probablement parce que le download Bybit a utilisé un endpoint paginé limité à 1000 candles par request, et personne n'a fait la pagination.

**Manque par fichier : 440 lignes (de minuit UTC à 02:00 + de 18:39 à minuit)** — environ 30% des données manquent.

### Cela explique LE blocker `OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED`

- `row_count != expected_rows` (1000 vs 1440) ⇒ condition ligne 182 du check `data_factory.py` ⇒ blocker

---

## D2 — Détail réel OHLCV 10m

**Fichier raw inspecté :** `L:\klines\BTCUSDT\10\BTCUSDT_10_2025-07-23.csv`

```
row_count: 100            ← devrait être 144 (24h × 6 bars/h)
start_ts:  1753255200000  → 2025-07-23 02:00:00 UTC
end_ts:    1753314600000  → 2025-07-23 18:30:00 UTC
durée:     ~16h30
```

### Interprétation

**10m EST natif Bybit** (mon hypothèse pré-diag était fausse). Même limite 1000-rows que 1m, mais 100 lignes max ici (peut-être un autre paramètre de download).

**Manque par fichier : 44 lignes** (~30% comme 1m).

### Bonus — comparaison 5m / 15m (non-critique mais inspectés)

| Timeframe | row_count réel | row_count attendu (24h) | Statut |
|---|---|---|---|
| 1m | **1000** | 1440 | ❌ -30% |
| 5m | **288** | 288 | ✅ COMPLET ! |
| 10m | **100** | 144 | ❌ -30% |
| 15m | **96** | 96 | ✅ COMPLET ! |

**Pattern :** 1m et 10m sont tronqués à un cap fixe (1000 et 100). 5m et 15m sont complets (288 et 96 — dans la limite 1000).

**Conclusion :** la limite de download Bybit est probablement à **1000 lignes max par fichier**. Quand le timeframe permet ≤1000 lignes/jour (5m=288, 15m=96), c'est complet. Pour 1m (1440) et 10m (144 mais cappé à 100 pour raison inconnue), c'est tronqué.

**Très étrange pour 10m** : 144 lignes < 1000, donc en théorie ça devrait passer. Mais on a 100. **Hypothèse :** le 10m a été téléchargé par batches de 100 (autre limite) et personne n'a paginé.

---

## D3 — Fichier SCHEMA_UNKNOWN identifié

**Fichier coupable :** `K:\v5.3 backtest\metadata\bybit\spot\symbol_metadata.jsonl`

```json
{
  "path": "K:\\v5.3 backtest\\metadata\\bybit\\spot\\symbol_metadata.jsonl",
  "row_count": 1,
  "source_status": "RAW_FILE_SCHEMA_UNKNOWN",  ← ICI
  "source_type": "metadata"
}
```

### Interprétation

C'est le fichier METADATA (pair tick_size / fees / etc.) en format JSONL. La version CSV `symbol_metadata.csv` est marquée `RAW_FILE_READY` mais la version `.jsonl` est `SCHEMA_UNKNOWN`.

**Diagnostic :** le parseur V5.3 `raw_market_data_indexer.py:_build_json_manifests` ne reconnaît pas le schéma du metadata JSONL. C'est probablement un fichier généré par `bybit_historical_metadata.py` qui a un schéma propre, mais l'indexer cherche un schéma "market data" et ne le trouve pas.

**Cela explique LE blocker `BRONZE_SCHEMA_BLOCKER`** :
- `raw_market_data_indexer.py:627` : `if any(item.source_status == "RAW_FILE_SCHEMA_UNKNOWN") : status = BRONZE_INDEX_BLOCKED_BY_SCHEMA`
- 1 seul fichier UNKNOWN suffit pour bloquer tout le bronze index

### Pourquoi le fichier `.jsonl` existe à côté du `.csv`

Le module `bybit_historical_metadata.py` écrit **deux versions** : `symbol_metadata.csv` (pour humans) et `symbol_metadata.jsonl` (pour processing). Le système consomme le CSV mais indexe les deux dans le bronze. Le jsonl n'a pas de schéma "market data" donc UNKNOWN.

---

## D4 — Gaps + duplicates root cause

### Duplicate timestamps = 4

Examination des entrées orderbook dans `raw_file_manifest.jsonl.gz` :

| Path | source_type | start_ts | end_ts |
|---|---|---|---|
| `2025-07-23_BTCUSDT_ob200.data.zip` | **orderbook_delta** | 1753228802474 | 1753315202474 |
| `2025-07-23_BTCUSDT_ob200.data` (extrait) | **orderbook_delta** | 1753228802474 | 1753315202474 |
| `2025-07-24_BTCUSDT_ob200.data.zip` | **orderbook_delta** | 1753315202474 | 1753401601765 |
| `2025-07-24_BTCUSDT_ob200.data` (extrait) | **orderbook_delta** | 1753315202474 | 1753401601765 |
| `2025-07-23_BTCUSDT_ob200.data.zip` | **orderbook_snapshot** | 1753228802474 | 1753315202474 |
| `2025-07-23_BTCUSDT_ob200.data` (extrait) | **orderbook_snapshot** | 1753228802474 | 1753315202474 |
| `2025-07-24_BTCUSDT_ob200.data.zip` | **orderbook_snapshot** | 1753315202474 | 1753401601765 |
| `2025-07-24_BTCUSDT_ob200.data` (extrait) | **orderbook_snapshot** | 1753315202474 | 1753401601765 |

**8 entrées du même CONTENU** comptées comme fichiers distincts ! Le contenu `.data.zip` ET son extrait `.data` sont indexés deux fois pour deux source_types (delta + snapshot).

**Bug :** [`raw_market_data_indexer.py`](src/local_replay_runtime/raw_market_data_indexer.py) considère le zip et le contenu extrait comme deux fichiers indépendants. Plus, le même fichier est classifié comme `orderbook_delta` ET `orderbook_snapshot`.

### Gaps = 2

Probablement entre les fichiers consécutifs jour J et J+1. Avec les klines 1m :
- File 2025-07-23 : end_ts = 1753315140000 (18:39 UTC)
- File 2025-07-24 : start_ts = 1753341600000 (02:00 UTC)
- Gap réel : ~7h21 minutes

Mais le manifest dit `largest_gap_ms = 60000` (60s). **Calcul incohérent** — probablement l'indexer compare seulement les boundaries fichiers du même type avec ordering bizarre.

---

## SYNTHÈSE — Les vrais problèmes (très différents du diagnostic initial)

### Problème #1 — Raw data L: INCOMPLET (cause externe, pas bug code)

- 1m et 10m sont tronqués à respectivement 1000 et 100 lignes/jour
- Couvre ~16h40 sur 24h
- **Origine :** download Bybit limité (probablement non-paginé)

**Implication majeure :** le dataset L: est INCOMPLET pour 1m+10m. Les engines qui utilisent ces timeframes voient seulement 70% du temps de marché.

**Fix possibles :**
- (a) **Re-télécharger les L: dumps avec pagination correcte** ← LE VRAI FIX (effort dépend du process de DL)
- (b) Accepter la troncature et ajuster expected_rows à 1000 (1m) et 100 (10m) ← FIX SUR le check, mais pas la cause
- (c) Concaténer plusieurs fichiers raw par jour pour atteindre 1440/144

### Problème #2 — Parseur metadata JSONL buggé

- `symbol_metadata.jsonl` est classifié SCHEMA_UNKNOWN alors que le CSV est READY
- C'est notre propre output (généré par `bybit_historical_metadata.py`) qu'on ne sait pas indexer

**Fix simple :**
- Ajouter un schéma reconnu pour metadata JSONL dans `_build_json_manifests`
- OU déduplication : si CSV existe, ne pas indexer le JSONL

### Problème #3 — Indexer compte ZIP + extract comme doublons

- Bug : `2025-07-23_BTCUSDT_ob200.data.zip` ET `2025-07-23_BTCUSDT_ob200.data` (extrait) tous deux indexés
- Multiplié par 2 source_types (delta + snapshot) = 4 doublons

**Fix simple :**
- Déduplication par contenu (sha256) — si même hash, garder un seul
- OU exclure les zip si extract existe (ou inverse)

---

## Plan de fix RÉVISÉ (suite à diagnostic)

| # | Patch | Effort | Bloquant prod-safe ? |
|---|---|---|---|
| **D1+D2 (P1 révisé)** | (a) Re-télécharger L: avec pagination OU (b) accepter row_count via severity classifier | Variable | OUI |
| **D3 (P2 nouveau)** | Ajouter schéma metadata JSONL dans `_build_json_manifests` ou déduplication CSV/JSONL | 0.5j | OUI |
| **D4 (P3 nouveau)** | Déduplication ZIP/extracted dans `raw_market_data_indexer` | 0.5j | OUI |
| P3 F2 bronze severity (déjà planifié) | déjà planifié | 1j | secondaire (D4 fixe la vraie cause) |
| P4 F4 metadata switch | 0.5j | NON |
| P5 F1 venue verified | 0.5-1j | NON |
| P6 fail-close A2→B1/B2 | 1j | OUI sécurité |

**Total révisé : ~3-4 jours** (sans re-download L:) + le re-download L: si on choisit option (a) = variable.

---

## Décision majeure à prendre

### Pour D1+D2 (OHLCV temporal)

**Option A — Re-télécharger L: complets** (vrai fix)
- Pro : dataset propre, complete, pas de hack
- Con : effort variable, dépend de qui contrôle le download Bybit
- Doctrine V5.3 : préférée

**Option B — Severity classifier accepte row_count partial**
- Pro : rapide, pas besoin de re-DL
- Con : on accepte 30% de données manquantes — risque biaiser features microstructure
- Doctrine V5.3 : flag obligatoire `OHLCV_PARTIAL_DAY_ACCEPTED`

**Option C — Concaténer multiples raw files par jour**
- Pro : si le download a fait plusieurs petits fichiers
- Con : exige modifier le pipeline raw → silver
- ⚠ Mais d'après le manifest, **il n'y a qu'UN fichier par jour** dans L: → option C non applicable telle quelle

**Recommandation :** **Investiguer si re-download est faisable AVANT de coder severity classifier**. Si re-download facile → Option A. Sinon → Option B avec flag explicite.

### Pour D3 (parseur metadata JSONL)

**Recommandation :** **déduplication CSV/JSONL** — si `symbol_metadata.csv` existe, ne pas indexer `symbol_metadata.jsonl` (le JSONL est juste un duplicate). 0.5j effort.

### Pour D4 (indexer ZIP/extracted)

**Recommandation :** **déduplication par sha256** dans `raw_market_data_indexer.py`. Si 2 fichiers ont le même hash, garder un seul (préférer le format non-compressé pour le parsing). 0.5j effort.

---

## NEXT — décisions utilisateur

1. **D1+D2** : tu peux re-télécharger les L: dumps avec pagination correcte (Option A) ? Ou on accepte la troncature (Option B) ?
2. **D3** : OK pour déduplication CSV/JSONL metadata ?
3. **D4** : OK pour déduplication ZIP/extracted par sha256 ?

Réponds aux 3 → je code immédiatement les patches D3+D4 (rapide), et tu décides en parallèle pour D1+D2.
