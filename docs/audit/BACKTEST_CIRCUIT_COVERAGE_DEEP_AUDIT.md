# Backtest Circuit Coverage Deep Audit — Run `strategy_ladder_workflow-2df91d9d5c48dfbf`

**Audit mode** : `READ_ONLY_ROOT_CAUSE`
**Trading logic modified** : `false`
**Thresholds modified** : `false`
**Run window** : `2025-07-25 → 2025-07-26` (1 day, BTCUSDT, 15m)
**Date audit** : 2026-05-27

---

## 0. Verdict racine en 1 paragraphe

Le run **n'est pas un échec de logique trading**. Les "4 trades exécutés" sont **1 candidat unique** (`ae5c57f5197f33fcab27b346`, engine_a) **répliqué sur 4 capital buckets** (400/500/1500/4000). Les blockers en première ligne (`B2_COST_MEASUREMENT_BLOCKED`, `ENGINE_NATIVE_RUNNER_NOT_INVOKED`) sont présents sur **388/388 records, y compris les 4 exécutés** — ce qui prouve qu'ils sont des **diagnostics informationnels coarsement nommés**, pas des hard gates. Les vrais problèmes sont **du reporting et du naming**, pas de la logique trading.

---

## 1. Funnel canonique du run

| Étape | Compte | Note |
|---|---:|---|
| Discovery pre-candidates | 200 | OK |
| Engine native candidates | 200 | OK |
| Engine native preselected (B2) | 97 | OK |
| B2 replay candidates | 97 | OK |
| **Trade-eligible distinct candidates** | **1** | Le vrai chiffre |
| Engine emit valid (avant block) | 4 | dont 1 exécuté, 3 hard-blocked après emit |
| Replay records (bucket expansion) | **388 = 97 × 4 buckets** | |
| **Canonical selected_count (bucket-records)** | **4** | 1 × 4 buckets |
| **Canonical executed_count (bucket-records)** | **4** | 1 × 4 buckets |
| Distinct executed candidate | **1** | `ae5c57f5197f33fcab27b346` |
| Hard-blocked records | 384 | |

**Le mot "selected_count=4" est juste mais trompeur** : c'est 1 candidat × 4 buckets.

---

## 2. Q&A des 12 questions du brief

### Q1 — Pourquoi 384/388 sont `B2_COST_MEASUREMENT_BLOCKED` ?

**Réponse** : c'est **388/388** (y compris les 4 exécutés). Le code agrège (a) `spread_model_proxy` + (b) `slippage_model_proxy` + (c) `adverse_selection_proxy` + (d) `cost_parity_telemetry_missing` en un seul reason code coarsé. Déclenché dès qu'**une** composante est proxy. Voir Section 4.

### Q2 — Pourquoi 384/388 ont `ENGINE_NATIVE_RUNNER_NOT_INVOKED` ?

**Réponse** : c'est **388/388** (idem). Le runner natif **a effectivement tourné** : `engine_native_records_built = 958` ≈ 200 candidates × 5 records canoniques (Kyle/VPIN/OFI/QueuePressure/RealizedKernelVol). Le code signale juste que **B2 réutilise la décision B1** plutôt que de ré-invoquer le runner. **Code mal nommé.** Voir Section 5.

### Q3 — selected_count=4 et executed_count=4 mais first_gate dit que la sélection s'effondre avant exécution ?

**Réponse** : les 4 records exécutés portent les **mêmes** reason codes que les bloqués (`B2_COST_MEASUREMENT_BLOCKED` + `ENGINE_NATIVE_RUNNER_NOT_INVOKED`), **plus** `engine_a.emit.valid` et `execution_state=executed`. Le rapport `first_gate_analysis` agrège tous les records sans distinguer exécutés/bloqués et désigne donc des codes coarsiés comme "first gate". C'est un **artefact de reporting**, pas un vrai gate.

### Q4 — `real_selected_count=1` vs `selected_count=4` ?

**Réponse** : confusion sémantique non-documentée :
- `real_selected_count = 1` = **candidats distincts** sélectionnés
- `canonical_selected_count = 4` = **bucket-records** sélectionnés

Les deux sont corrects, mais le naming est ambigu. **Le cockpit doit afficher les deux** avec labels clairs.

### Q5 — Les 4 trades sont-ils 4 candidats réels ou un artefact ?

**Réponse** : **artefact de bucket expansion**. 1 candidat distinct (`ae5c57f5197f33fcab27b346`) × 4 buckets capital = 4 records identiques. Outcomes 100% identiques (mêmes timestamps, mêmes reason codes, mêmes fwd_h1/mfe/mae).

### Q6 — Les 4 trades sont-ils cohérents ?

**Réponse** : **cohérents entre eux car identiques**. Sources : `entry_ref.reference_type=decision_price_proxy`, `exit_ref.reference_type=post_window_close_proxy`. Pas de wiring bug. Mais **proxy entry/exit** = pas promotion-grade.

### Q7 — Pourquoi les 4 trades perdent-ils ?

**Réponse** : signal **marginal**. Reason codes du candidat exécuté :
- `engine_a.structure.marginal` (pas favorable)
- `engine_a.context.neutral` (pas convaincu)
- `engine_a.conviction.medium` (medium, pas high)
- `engine_a.cost.feasible` (OK côté coût)

Sur la fenêtre `h1`, le prix a baissé : `fwd_h1 = -67.75 bps`, `mae = -99.36 bps`, `mfe = 0.0 bps`. **Perte légitime sur signal faible**. Aucune anomalie d'execution ou de cost.

### Q8 — Engine C absent ou filtré upstream ?

**Réponse** : **filtré upstream** par direction (non-long-breakout). Le label `engine_c.microstructure.not_applied = SUSPECTED_WIRING_ISSUE` du `healthy_vs_suspected` est **un faux-positif de reporting**. Pas un wiring bug. Le label devrait être `engine_c.filtered_upstream_by_direction`.

### Q9 — Engine D bloqué uniquement par closed_episode missing ?

**Réponse** : **oui**. 200/200 engine_d records portent :
- `ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE`
- `engine_d.no_trade.history_weak`
- `history_weak`

Doctrinalement correct : Engine D dépend d'un trade A/C exécuté précédent. **Cold start sans warmup closed_episode_journal**. Pas un bug, juste un état initial.

### Q10 — Coût/fill réellement mesuré ou partial proxy ?

**Réponse** : **moitié-moitié**.

| Composant | Mesuré | Proxy |
|---|---:|---:|
| Book depth | 196 (50.5%) `BOOK_DEPTH20_AVAILABLE` | 192 (49.5%) `BOOK_DEPTH_NOT_PROVEN` |
| Fill realism | 196 `FILL_REALISM_SHADOW_MEASURED` | 192 `FILL_REALISM_BLOCKED_BY_MISSING_MEASUREMENT` |
| Impact source | 196 `IMPACT_SOURCE_DEPTH20_MODEL` | 192 `IMPACT_SOURCE_MISSING` |
| **Spread** | 0 measured | 388 `SPREAD_MODEL_PROXY` |
| **Slippage** | 0 measured | 388 `SLIPPAGE_MODEL_PROXY` |
| **Adverse selection** | 0 measured | 388 `ADVERSE_SELECTION_PROXY` |

**Même les 196 records avec book mesuré gardent `B2_COST_MEASUREMENT_BLOCKED`** parce que spread/slippage/adverse_selection restent proxy. Le code agrégé n'expose pas la granularité.

### Q11 — Le wording `ranked` / `top_pair` / `top_timeframe` est-il trop positif ?

**Réponse** : **oui**.
- `timeframe_ranking_report` : `ranking_status="ranked"`, `top_timeframe="15m"` — mais **1 seul timeframe testé** + `missing_fields=["psr","dsr","mfe_bps","mae_bps"]`. Le wording induit l'opérateur en erreur.
- `pair_ranking_report` : `top_pair="BTCUSDT"` — **1 seul pair testé**. `cost_infeasible_count=388` (100% des records sont cost-infeasible). Le wording masque la réalité.

### Q12 — Evidence ledgers SCRATCH_ONLY ?

**Réponse** : **confirmé**. Tous les ledgers ex-post sont scratch-only :
- `governed_evidence_status = EVIDENCE_AUDIT_NOT_CONFIRMED`
- `refusal_ledger_evidence_class = SCRATCH_ONLY`
- `sample_size_survival_evidence_class = SCRATCH_ONLY`
- `trade_detail_ledger_evidence_class = SCRATCH_ONLY`

Pour passer promotion-grade : `shadow_measured` + entry_reference non-proxy + `execution_fidelity` > `PARTIALLY_MEASURED` + min_TRL satisfait.

---

## 3. Count semantics deep audit

| Rapport | selected_count valeur | Sémantique | Cohérent ? |
|---|---:|---|---|
| `run_manifest` | 4 | bucket-records | ✓ |
| `post_b2_refusal_audit.canonical_selected_count` | 4 | bucket-records | ✓ |
| `post_b2_refusal_audit.capital_bucket_distribution[bucket].selected_count` | **0** par bucket | ??? | ✗ **contradictoire** |
| `capital_bucket_matrix[bucket].selected_count` | **1** par bucket | distinct candidates per bucket | ✓ |
| `threshold_governance_survival_report.real_selected_count` | **1** | candidats distincts | ✓ |
| `threshold_governance_survival_report.real_executed_count` | **4** | bucket-records | ✓ |
| `candidate_trade_semantics_audit.canonical_selected_count` | 4 | bucket-records | ✓ |
| `candidate_trade_semantics_audit.candidate_semantic_class_counts.ENGINE_NATIVE_CANDIDATE` | **1** | candidat émis valid | ✓ |
| `timeframe_ranking_report.rows[0].selected_count` | 4 | bucket-records | ✓ |
| `pair_ranking_report.rows[0].selected_count` | 4 | bucket-records | ✓ |
| `engine_no_trade_diagnosis.engines.engine_a.selected_count` | 4 | bucket-records | ✓ |

**Verdict** : `COUNT_SEMANTICS_BUCKET_EXPANSION_CONFUSING`

**Contradiction réelle trouvée** : `post_b2_refusal_audit.capital_bucket_distribution` dit `selected_count=0` partout, mais `capital_bucket_matrix` dit `selected_count=1` partout. **Même champ, deux valeurs**.

---

## 4. B2_COST_MEASUREMENT_BLOCKED — pourquoi 388/388 ?

### Stats agrégées sur 388 records

```
ENGINE_NATIVE_RUNNER_NOT_INVOKED : 388
B2_COST_MEASUREMENT_BLOCKED      : 388
BOTH                              : 388
BOTH + execution_state=executed   :   4
```

Tous les records ont les deux codes, **y compris les 4 exécutés**.

### Sub-conditions réelles

| Status | Count | % |
|---|---:|---:|
| `book_depth_source_status = BOOK_DEPTH20_AVAILABLE` | 196 | 50.5% |
| `book_depth_source_status = BOOK_DEPTH_NOT_PROVEN` | 192 | 49.5% |
| `fill_realism_status = FILL_REALISM_SHADOW_MEASURED` | 196 | 50.5% |
| `fill_realism_status = FILL_REALISM_BLOCKED_BY_MISSING_MEASUREMENT` | 192 | 49.5% |
| `impact_source_status = IMPACT_SOURCE_DEPTH20_MODEL` | 196 | 50.5% |
| `impact_source_status = IMPACT_SOURCE_MISSING` | 192 | 49.5% |

**Donc 50.5% des records ont book + fill + impact mesurés** et restent quand même `B2_COST_MEASUREMENT_BLOCKED`. Le code ne suffit pas à identifier le vrai blocker. Composantes manquantes systématiques :
- `SPREAD_MODEL_PROXY` sur 388/388
- `SLIPPAGE_MODEL_PROXY` sur 388/388
- `ADVERSE_SELECTION_PROXY` sur 388/388
- `cost_parity_status = REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY`

**Verdict** : `B2_COST_MEASUREMENT_BLOCKED_TOO_COARSE` — splitter en sub-codes par composant.

---

## 5. ENGINE_NATIVE_RUNNER_NOT_INVOKED — diagnostic mal nommé

### Évidence directe que le runner a tourné

- `engine_native_status = ENGINE_NATIVE_FULL_PATH_READY`
- `engine_native_records_built = 958`
- `engine_native_candidate_count = 200`
- 958 / 200 ≈ 4.79 ≈ 5 records canoniques par candidat (Kyle/VPIN/OFI/QueuePressure/RealizedKernelVol)
- Le candidat exécuté `ae5c57f5197f33fcab27b346` a `engine_a.emit.valid` + `execution_state=executed` ET porte aussi `ENGINE_NATIVE_RUNNER_NOT_INVOKED`

### Interprétation

Le code signale que **B2 ne ré-invoque PAS le runner natif** : B2 réutilise la décision déjà prise en B1/B1.5. Ce n'est **pas un blocker**, c'est un marqueur descriptif. Le mot **"NOT_INVOKED"** est trompeur.

### Suggested rename

```
ENGINE_NATIVE_RUNNER_NOT_INVOKED
  → B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1
```

Classifier comme `informational`, pas dans `hard_blockers`.

---

## 6. Engine A execution autopsy

| Field | Value |
|---|---|
| candidate_id | `ae5c57f5197f33fcab27b346` |
| engine_id | `engine_a` |
| decision_timestamp_ms | 1753491600000 |
| capital buckets executed on | 400 / 500 / 1500 / 4000 (4 records identiques) |
| entry_reference_status | `ENTRY_REFERENCE_DECISION_PRICE_PROXY` |
| entry_ref.price | (decision_price, proxy) |
| exit_ref.reference_type | `post_window_close_proxy` |
| holding_time_ms | 9 000 000 (= 2h30) |
| forward_return_h1 | **-67.75 bps** |
| mfe_bps | **0.0** |
| mae_bps | **-99.36 bps** |
| executed_only_net_return | null (status `NOT_PROVEN`) |
| Net edge across run | -46.04 bps |

### Reason codes co-présents

Signaux pré-exécution :
- `engine_a.emit.valid` (engine a émis)
- `engine_a.structure.marginal` (signal marginal, pas favorable)
- `engine_a.context.neutral`
- `engine_a.conviction.medium`
- `engine_a.cost.feasible`
- `economics.engine_a.cost.feasible`

Marqueurs informationnels :
- `ENGINE_NATIVE_RUNNER_NOT_INVOKED` (descriptif B2 reuse, voir Section 5)
- `B2_COST_MEASUREMENT_BLOCKED` (coarse, voir Section 4)

### Verdict

`ENGINE_A_EXECUTIONS_VALID_BUT_BUCKET_DUPLICATED_AND_LOSSMAKING_ON_MARGINAL_SIGNAL`

- 1 candidat distinct × 4 buckets = 4 trades répliqués
- Signal marginal/neutral/medium (pas une high-conviction emit)
- Forward returns adverse (-67 bps h1)
- Pas d'anomalie d'execution ou de cost — c'est une perte légitime sur signal faible
- Mais l'opérateur croit avoir 4 trades distincts → bug de **reporting**, pas de logique

---

## 7. Engines B, C, D — verdicts

| Engine | Verdict | Justification |
|---|---|---|
| Engine A | `BUCKET_DUPLICATED_LOSSMAKING_ON_MARGINAL` | voir Section 6 |
| Engine B | `HEALTHY_COST_BLOCKER_CONFIRMED` | reason codes conviction_low / no_excess / break_even_not_cleared / cost_infeasible cohérents avec doctrine. Cost-blocker mixé proxy/measured mais logique intacte. |
| Engine C | `REPORTING_LABEL_MISLEADING` | filtré upstream par direction (non-long-breakout). Le label `engine_c.microstructure.not_applied = SUSPECTED_WIRING_ISSUE` est un faux-positif. Pas de bug wiring confirmé. |
| Engine D | `HEALTHY_COLD_START_BLOCKER_CONFIRMED` | 200 records × `ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE` + `history_weak`. Doctrine correcte : D dépend d'un trade A/C exécuté précédent. Cold start sans warmup. |

---

## 8. Expected-edge + statistical validation

### Expected-edge governance
- `expected_edge_proxy_count = 200` (100%)
- `expected_edge_governed_count = 0`
- `expected_edge_model_status = EXPECTED_EDGE_MODEL_NOT_REQUESTED`

Verdict : `EXPECTED_EDGE_GOVERNANCE_BLOCKER_HEALTHY`. Aucun artifact ML fourni → fail-closed proxy correctement déclenché.

### Statistical validation

- `executed_trade_count = 4` (bucket-records)
- `statistical_validation_observation_count = 0`
- `statistical_validation_status = STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS`

Pourquoi 0 observations malgré 4 executions :
1. Les 4 records sont **1 candidat répliqué** → observation effective ≤ 1
2. `executed_only_net_return_status = EXECUTED_NET_RETURN_NOT_PROVEN` (proxy entry reference)
3. Evidence class = `SCRATCH_ONLY` (pas promotion-grade)

Verdict : `STAT_VALIDATION_REPORTING_NEEDS_SPLIT` — afficher `raw_bucket_executions=4 / distinct_trades=1 / promotion_grade_observations=0`.

---

## 9. Report wording — `ranked` / `top_X` sur N=1

### timeframe_ranking_report

```json
{
  "ranking_status": "ranked",
  "top_timeframe": "15m",
  "rows": [{"timeframe": "15m", ...}],
  "missing_fields": ["psr", "dsr", "mfe_bps", "mae_bps"]
}
```

**Issue** : 1 timeframe testé. `ranked` + `top_timeframe` + 4 stats canoniques manquantes. Wording induit en erreur.

### pair_ranking_report

```json
{
  "top_pair": "BTCUSDT",
  "rows": [{"pair": "BTCUSDT", "cost_infeasible_count": 388, ...}]
}
```

**Issue** : 1 pair. La pair est 100% `cost_infeasible` mais reste "top".

### Verdict : `REPORT_WORDING_OVERSTATES_RANKING`

Patches suggérés :
- `ranking_status: "ranked"` → `"ONLY_AVAILABLE_PARTIAL_NO_RANK"` quand N=1
- `top_timeframe` → `only_timeframe_tested`
- `top_pair` → `only_pair_tested`
- Ajouter `pairs_tested_count` / `timeframes_tested_count` explicites
- Bloquer le mot "top" si N < 2

---

## 10. Root causes ranked

| Rank | Issue | Severity | Class | Patch type | Audit-only? |
|---:|---|:---:|:---:|:---:|:---:|
| 1 | `COUNT_SEMANTICS_BUCKET_EXPANSION_HIDDEN_FROM_OPERATOR` | P0 | reporting | reporting | no |
| 2 | `ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED` | P0 | reporting | reporting (rename) | no |
| 3 | `B2_COST_MEASUREMENT_BLOCKED_TOO_COARSE` | P0 | reporting | reporting (split) | no |
| 4 | `POST_B2_REFUSAL_AUDIT_INTERNAL_CONTRADICTION_ON_BUCKET_SELECTED` | P1 | reporting | reporting | no |
| 5 | `RANKING_REPORTS_OVERSTATE_TOP_ON_SINGLE_UNIT` | P1 | reporting | reporting | no |
| 6 | `ENGINE_C_MICROSTRUCTURE_NOT_APPLIED_LABEL_AMBIGUOUS` | P2 | reporting | reporting | no |
| 7 | `STATISTICAL_VALIDATION_OBSERVATION_REPORTING_OPAQUE` | P2 | reporting | reporting | no |
| 8 | `ENGINE_D_COLD_START_WARMUP_AUTOMATION_MISSING` | P3 | engine_logic | audit_only | yes |
| 9 | `EXPECTED_EDGE_PROXY_RUN_LAUNCHED_WITHOUT_ARTIFACT` | P3 | governance | audit_only | yes |

**Aucun root-cause classé** `engine_logic` réel. Tous les P0/P1/P2 sont des fixes **reporting** non-invasifs (renaming, splitting, ajout de champs descriptifs). La logique trading, les thresholds, les engines A/B/C/D, le SignalCandidate, les hard blockers sont **intacts et corrects**.

---

## 11. Next patch plan (audit/reporting only)

| Patch ID | Scope | Files | Risk |
|---|---|:---:|:---:|
| `P0-COUNT-1` | Ajouter `selected_distinct_candidate_count` + `selected_bucket_record_count` aux 5+ rapports concernés | ~5 | low |
| `P0-RENAME-1` | Renommer `ENGINE_NATIVE_RUNNER_NOT_INVOKED` → `B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1` | ~3 + tests | medium |
| `P0-SPLIT-1` | Splitter `B2_COST_MEASUREMENT_BLOCKED` en sub-codes par composant | ~4 + tests | medium |
| `P1-RECONCILE-1` | Réconcilier `post_b2_refusal.capital_bucket_distribution.selected_count` vs `capital_bucket_matrix.selected_count` | ~2 | low |
| `P1-RANKING-WORDING-1` | Bloquer `ranked` / `top_X` quand N=1 | ~2 + tests | low |
| `P2-ENGINE-C-LABEL-1` | Splitter `engine_c.microstructure.not_applied` filtered_upstream vs wiring_bug | ~2 | low |
| `P2-STAT-VAL-DETAIL-1` | Ajouter `raw_bucket_executions / distinct_executed_trades / promotion_grade_observations` au stat_validation_report | ~1 | low |

**Aucun patch ne touche** : Engine A/B/C/D, SignalCandidate, thresholds, gates, hard blockers, selected/executed logic, expected-edge gates, fail-closed Talab.

---

## 12. Conclusion

Le run **a fonctionné correctement**. Sur 200 candidats, 1 seul a vraiment émis valide (engine_a, signal marginal), 4 bucket-records ont été exécutés (= ce 1 candidat × 4 buckets capital), et la perte de -46 bps est légitime sur un signal faible avec proxy entry/exit.

Les "blockers" visibles dans tous les rapports (`B2_COST_MEASUREMENT_BLOCKED`, `ENGINE_NATIVE_RUNNER_NOT_INVOKED`) sont des **diagnostics descriptifs**, pas des gates réels. Ils sont présents même sur les 4 records EXÉCUTÉS, prouvant leur nature informationnelle.

**Les vrais problèmes sont du reporting** : count semantics ambigus, reason codes coarsiés, ranking reports qui parlent de "top" sur N=1, contradictions internes entre rapports sur le même champ. Tous fixables sans toucher la logique trading.

---

## Artifact paths

- JSON canonique : `L:/output backtest/runs/strategy_ladder_workflow-2df91d9d5c48dfbf/audit_outputs/backtest_circuit_coverage_deep_audit.json`
- Ce MD : `docs/audit/BACKTEST_CIRCUIT_COVERAGE_DEEP_AUDIT.md`
