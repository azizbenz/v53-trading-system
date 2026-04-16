# 27 — Opus → Codex : Audit docs 21 & 22 + brief pass-2

**Date** : 2026-04-16 (rev-2 aligné sur docs 25/26/28)
**Auteur** : Opus (critical audit)
**Destinataire** : Codex (implementation + doc revision)
**Statut audit** : PARTIAL — ACCEPT-WITH-FIXES
**Score global** : 7.5/10
**Cibles auditées** : `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` + `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` (post-édition Codex)
**Fonction du doc** : canal de communication Opus ↔ Codex. Toute exécution Codex sur les fixes ci-dessous doit référencer ce doc par son numéro (doc 27) dans les commits et rapports.
**Protocoles référencés** :
- doc 25 `25_UPDATE_AUDIT_PROTOCOL.md` (format audit pack)
- doc 26 `26_UPDATE_AUDIT_PACK_TEMPLATE.md` (template audit pack)
- doc 28 `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` (résolution des désaccords, 4 rangs d'autorité)

**Audit pack compagnon** : `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`

---

## Convention de marquage (lecture obligatoire)

Dans ce doc, chaque proposition est étiquetée :

- **`CONSTRAINT_DOCTRINAL`** — rang 1 (littérature) ou rang 2 (canon V5.3) au sens doc 28. **Non-négociable.** Codex applique tel quel.
- **`PROPOSAL_OPUS`** — suggestion Opus **sans** rang 1/2 sourcé. Codex doit soit (a) trouver un rang 1/2 qui la confirme, soit (b) proposer une alternative rang 1/2, soit (c) ouvrir un bloc Dispute (doc 28 §5) et escalader rang 3 (shadow) ou rang 4 (user).
- **`CODEX_TO_MEASURE`** — valeur à extraire du code existant par Codex (pas une proposition Opus). Codex lit, rapporte, pas d'invention.

Toute formule ou constante non étiquetée est lue par défaut comme `PROPOSAL_OPUS`. Si Codex détecte un doute sur le marquage, il ouvre un bloc Dispute.

---

## 0. Règles de collaboration

1. Codex applique les P0 avant tout merge ; les P1 peuvent être pipelinés en PR séparée.
2. Chaque fix produit une entrée datée en §8 "Journal d'exécution Codex" + une entrée audit pack compagnon.
3. Pas de `silent strategy change` : toute substitution de formule/constante non listée ici requiert un bloc Dispute (doc 28).
4. TEXT ONLY quand Codex répond à un audit ; CODE + DOC pour les fixes.
5. Source of truth doctrinale : docs 19, 20, 23 + `CLAUDE.md`. Ce doc 27 ne peut pas les contredire.
6. **Désaccord Opus ↔ Codex** → protocole doc 28. Ni l'un ni l'autre ne tranche par opinion ; arbitrage par rang 1 (paper) > rang 2 (canon) > rang 3 (shadow) > rang 4 (user).
7. **Collision avec code existant** : si Codex trouve qu'un contrat/module proposé ici existe déjà partiellement ailleurs (ex : un `EpisodeMemory` dans `exit_pipeline`), il **ne fusionne pas silencieusement** — il ouvre un bloc Dispute pour arbitrer entre (a) reuse, (b) rename, (c) create-new-and-deprecate.
8. **Rollback** : chaque fix P0 devrait idéalement être un commit atomique sur une branche dédiée `fix/doc27-P0-<n>` pour rollback `git revert` propre. **Déviation acceptée pour ce pass** : Codex a appliqué les 4 P0 sur la branche existante `codex/full-shadow-abcd-migration-20260403` (340 fichiers modifiés). Les fichiers P0 sont identifiables par path (voir audit pack §Files Changed). Pour les futurs pass, la règle branche atomique reste recommandée.

---

## 1. Verdict d'audit

| Dimension | Score | Statut |
|---|---|---|
| Fidélité architecturale (canon V5.3, A/B/C/D, pas de greenfield) | 9/10 | ✅ |
| Fidélité MD (cohérence inter-docs 19/20/23) | 8/10 | ✅ |
| Code-quant (formules Carver, microstructure, HLZ) | 5/10 | ⚠️ |
| Stratégie (R-AC, R-D, strategy β, exclusion mutuelle) | 8/10 | ✅ |
| Objectifs Opus (side buy/sell, no meta_engine, calibration seam) | 9/10 | ✅ |
| Testabilité (contrats explicites, pyramide ≥50 tests) | 7/10 | ⚠️ |
| **Global pondéré** | **7.5/10** | **PARTIAL** |

---

## 2. Ce que Codex a BIEN fait (à conserver tel quel)

1. **Greenfield → doctrinal deepening** : les deux docs mappent correctement les fichiers existants (`src/engines/engine_c/`, `src/engines/engine_d/`). Ne pas régresser.
2. **`side="flat"` éliminé** : remplacé par `ConditioningRecord(family=HARD_BLOCK) + RefusalRecord(category=HARD_BLOCK)`, emit no canonical `SignalCandidate`. Conforme `Side ∈ {buy, sell}` (`src/interface_contracts/domain_types.py:150-153`).
3. **Test paths** : `tests/test_protocols/test_engine_coordination_rules/` (pas `test_meta_engine`). `src/meta_engine/` n'existe pas.
4. **Grammaire Narang 4-familles** respectée : `HARD_BLOCK | ENGINE_INTERNAL | SCORING | PORTFOLIO`.
5. **Strategy β** : pseudocode explicite doc 22 §4 (states + reset on fresh A + failsafe R-D-3).
6. **R-D-4 hardcodé** : sizing `0.5×` dans `vol_target_sizer`, pas calibration-driven.

---

## 3. P0 — BLOQUANTS (à corriger avant tout merge)

### P0-1. Définir `revenge_risk_penalty = f(...)` — doc 22 §3 Stage 4

**Problème** : doc 22 dit `revenge_risk_penalty = f(consecutive_stop_count, time_since_last_stop)` sans définir `f`. Un implémenteur choisira arbitrairement → `silent strategy change`.

**Rang d'autorité attendu (doc 28)** : rang 1 si littérature (prospect theory Kahneman-Tversky 1979, behavioral microstructure Lo-Repin 2002, Odean 1998 disposition effect) couvre une forme fonctionnelle exploitable ; sinon rang 4 (escalade user pour choix doctrinal).

**Action Codex — étape 1 (obligatoire)** : recherche rang 1, timebox 30 min. Rapport dans bloc Dispute `D-2026-04-16-001`. Sources à consulter :
- Kahneman-Tversky 1979 (prospect theory, loss aversion λ ≈ 2.25)
- Odean 1998 (disposition effect — reluctance to realize losses)
- Lo-Repin 2002 (psychophysiology of trading — revenge trading patterns)
- Coval-Shumway 2005 (do behavioral biases affect prices — loss-chasing)
- Linnainmaa 2010 (why do (some) households trade so much — revenge)

**Propositions Opus (étiquetées)** :

`PROPOSAL_OPUS` — forme exponentielle décroissante :
```
revenge_risk_penalty(n, Δt) = α · n² · exp(-Δt / τ)
  n  = consecutive_stop_count  (int, bornée à THR-X11)
  Δt = time_since_last_stop    (hours)
  α  = THR-D_REVENGE_SCALE     (default 0.25, cap 1.0, calibrated)
  τ  = THR-D_REVENGE_DECAY     (default 12h, cap 48h, calibrated)
```

`PROPOSAL_OPUS` — alternative linéaire-seuil :
```
revenge_risk_penalty(n, Δt) = α · n · max(0, 1 − Δt/τ)
```

**Aucune des deux n'est `CONSTRAINT_DOCTRINAL`.** Codex doit :
1. Appliquer étape 1 (recherche rang 1) avant toute implémentation.
2. Si rang 1 trouvé → utilise la forme du paper, écrit ça dans doc 22 Annexe A avec citation complète (author year eq DOI), et clôt la Dispute.
3. Si rang 1 non trouvé → bloc Dispute escaladé rang 4 avec options A/B/C (A = forme exponentielle Opus, B = linéaire-seuil Opus, C = alternative Codex sourcée).

**Propriétés minimales (CONSTRAINT_DOCTRINAL, quelle que soit la forme retenue)** :
- monotone croissante en `n`
- monotone décroissante en `Δt`
- bornée supérieurement (pas d'explosion)
- `n=0 ⇒ penalty=0`
- `lim_{Δt→∞} penalty = 0`

**Acceptance** : `marginal_value_estimator_d.py` implémente la formule arbitrée avec paramètres via calibration seam `risk_runtime_drawdown_calibration`. Test unitaire vérifiant les 5 propriétés ci-dessus + test `paper_repro` sur un cas figure du paper cité (si rang 1). Bloc Dispute `D-2026-04-16-001` clôturé `RESOLVED`.

### P0-2. Spécifier contrat `ClosedEpisodeJournal` + `EpisodeRef`

**Problème** : doc 22 §3 Stage 1 invoque `closed_episode_journal` sans contrat. N'existe dans aucun doc 19/20/23/24.

**Rang d'autorité attendu (doc 28)** : rang 2 — dérivation directe de la grammaire Narang (doc 20 §3) + Pydantic V5.3 patterns (`SignalCandidate`, `RefusalRecord`). Pas de controverse scientifique, seulement discipline de contrat.

**Étape 0 obligatoire (CODEX_TO_MEASURE)** : avant d'implémenter, Codex **scan le repo** pour détecter l'existence partielle :
```bash
rtk grep -r "episode_memory\|closed_episode\|episode_journal\|EpisodeRef\|episode_reference" src/
rtk grep -r "class.*Episode" src/ --include="*.py"
```
Rapport dans bloc Dispute `D-2026-04-16-002` si match non-trivial → arbitrage reuse/rename/create-new avant d'écrire quoi que ce soit.

**Action Codex (après étape 0)** :
1. Ajouter Annexe B à doc 22 avec les contrats Pydantic v2 frozen :

```python
class EpisodeRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    episode_id: UUID
    engine_id_of_origin: Literal["A", "C"]          # D ne peut pas référencer un D
    pair: str
    direction: Literal["long", "short"]
    entry_level: Decimal
    exit_level: Decimal
    bet_structure: BetStructure
    forecast_horizon_class: ForecastHorizonClass
    forecast_target_class: ForecastTargetClass
    closed_at: int                                   # ns UTC
    close_reason: Literal["take_profit", "structural_exit", "time_stop", "stop_out"]
    realized_pnl_decimal: Decimal

class ClosedEpisodeJournal(BaseModel):
    """Frozen append-only record of closed A/C episodes, queried by engine_d."""
    model_config = ConfigDict(frozen=True)
    episodes: tuple[EpisodeRef, ...]                 # append-only tuple
    schema_version: str
    last_append_at: int                              # ns UTC
```

2. Remonter dans **doc 19 un nouveau livrable P3-10.5** : `closed_episode_journal.py` (path : `src/protocols/closed_episode_journal.py`) branché sur les hooks d'exit du portfolio/execution pipeline. `CONSTRAINT_DOCTRINAL` : path `src/protocols/` (canon V5.3 CLAUDE.md), pas `src/meta_engine/`.
3. Rappel R-D contractuel : R-D-1 refuse `close_reason == "stop_out"` (D ne réengage que sur sorties valides). Doc 22 §8 Prohibition 4 déjà présente — la renforcer par une validation Pydantic (`model_validator` levant `ValueError` si engine D reçoit un EpisodeRef stop_out).

**Acceptance** : `closed_episode_journal.py` existe, testé (append-only invariant + filter stop_out + property-based hypothesis sur append ordering), et `first_episode_resolver_d.py` l'utilise. Bloc Dispute `D-2026-04-16-002` clôturé.

### P0-3. Trancher "optional/required" par helper

**Problème** : §2 des deux docs liste "optional additive helpers". Ambiguïté : le §3 invoque ces helpers par nom → implémentation et tests divergeraient si absents.

**Rang d'autorité attendu (doc 28)** : rang 2 — principe Narang "isolation of hard rules for testability" (doc 20 §11 + Narang ch.3 §3.3 grammaire conditioning). Les helpers qui portent des règles HARD_BLOCK doivent être testables indépendamment du runtime → REQUIS. Les helpers qui sont seulement factorisation esthétique → OPTIONNEL.

**Action Codex** — modifier §2 comme suit :

**Doc 21 §2** :
| Helper | Status final |
|---|---|
| `a_exclusion_guard_c.py` | **REQUIS** — isolation R-AC est un contrat testable critique |
| `continuation_validator_c.py` | **REQUIS** — sépare OFI/VPIN/queue du math continuation |
| `signal_reporter_c.py` | OPTIONNEL — peut rester dans `engine_c_runtime.py` |

**Doc 22 §2** :
| Helper | Status final |
|---|---|
| `first_episode_resolver_d.py` | **REQUIS** — lecture `closed_episode_journal` |
| `historical_linkage_guard_d.py` | **REQUIS** — R-D-1/R-D-2/R-D-3 |
| `consecutive_stop_counter_d.py` | **REQUIS** — state strategy β |
| `anti_revenge_cooldown_d.py` | OPTIONNEL — peut fusionner avec `historical_linkage_guard_d` |
| `signal_reporter_d.py` | OPTIONNEL — peut rester dans `engine_d_runtime.py` |

**Acceptance** : §2 réécrit avec tableau ci-dessus. Les §7 (tests) listent des suites explicitement pour chaque helper REQUIS.

### P0-4. Spécifier `k_HLZ` explicite dans barres de promotion

**Problème** : docs 21 §8 et 22 §9 invoquent "Sharpe-deflated" sans énoncer `k` utilisé dans `SR_deflated = SR × √((N−k)/(N−1))`. Sans `k` déclaré, la déflation est ajustable → contournable.

**Rang d'autorité attendu (doc 28)** : rang 1 (Harvey-Liu-Zhu 2016 eq.(8)) pour la formule + rang 2 (`multiple_testing_guard.py` module V5.3) pour la valeur numérique de `k`.

**Étape 0 obligatoire (CODEX_TO_MEASURE)** : Codex **lit** `src/calibration_methods/multiple_testing_guard.py` (ou équivalent — scanner si le path exact diffère) et **rapporte la valeur réelle de `k`** déjà implémentée, incluant la règle de calcul. Pas de guess.

```bash
rtk grep -r "multiple_testing_guard\|k_hlz\|deflated_sharpe\|harvey_liu_zhu" src/
rtk read src/calibration_methods/multiple_testing_guard.py
```

**Propositions Opus (étiquetées PROPOSAL_OPUS, à confirmer contre module réel)** :
```
k_HLZ = n_engines_candidates × n_pairs_shadow × n_regimes_evaluated
     = 4 × 20 × 4                        # hypothèse V5.3 si module absent
     = 320
```

Pour D spécifiquement (doc 22 §9), la règle `n_engines_candidates` dépend de l'ordre d'évaluation (A/B/C puis D, ou A/B/C/D ensemble). Codex mesure et rapporte.

**Action Codex après étape 0** :
- Si module existe → utiliser valeur réelle + formule réelle. Mettre à jour doc 21/22 avec nombres exacts et référence git hash du module.
- Si module n'existe pas → créer bloc Dispute `D-2026-04-16-004`, escalade rang 1 (re-dériver de HLZ 2016) + livrable doc 19 nouveau pour créer `multiple_testing_guard.py`.

**Acceptance** : §8 (doc 21) et §9 (doc 22) citent `k_HLZ` avec (a) la règle de composition, (b) la valeur numérique courante V5.3, (c) la référence HLZ 2016 eq.(8), (d) le git hash du module `multiple_testing_guard.py`. Test parity : `SR_deflated(SR=1.0, N=50, k=<valeur réelle>)` produit valeur hardcodée dans test.

**Closure note 2026-04-16 (Rang 1 + 2 + 4)** :
- `src/calibration_methods/multiple_testing_guard.py` exists.
- Formula source remains Harvey-Liu-Zhu 2016 eq.(8) [Rang 1].
- Current V5.3 composition is `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode [Rang 2 via doc 20 §12.2 + module].
- Current default used by docs 21/22 is the user-selected observed-shadow mode, so `k_HLZ = pairs_tested` [Rang 4].
- Current numeric default in the repo pair catalogue is `k_HLZ = 12`; `promotion_floor` remains available as an explicit non-default conservative option.
- Module blob hash: `b2aafc74bd5abdefc8810e69f1562e9cc6881007`.

---

## 4. P0-5 — BLOQUANT (élevé depuis P1 — règle R-QUANT-FIRST, doc 28 §2bis)

> **Justification de l'élévation** : un dev qui code sans formule complète produit un `silent strategy change` par omission. Les formules quant doivent être complètes AVANT toute implémentation. Ce n'est pas un "nice-to-have" — c'est la première chose qu'un dev doit avoir sous les yeux.

### P0-5a. Compléter formules quant en Annexe A — doc 21

Ajouter **§Annexe A "Formules microstructure — spécification complète"** à doc 21 :

**a) Realized kernel volatility** `CONSTRAINT_DOCTRINAL` (Barndorff-Nielsen-Hansen-Lunde-Shephard 2008)
```
σ_RK = Σ_{h=-H}^{H} k(h/H) · γ(h)

γ(h) = Σ_j r_j · r_{j+h}              # autocovariance réalisée d'ordre h
r_j  = log(P_j) - log(P_{j-1})         # log-return sur bucket
k(x) = Parzen kernel:
       k(x) = 1 - 6x² + 6|x|³         si |x| ≤ 0.5
       k(x) = 2(1 - |x|)³             si 0.5 < |x| ≤ 1
       k(x) = 0                         sinon
H    = ⌈c · n^(3/5)⌉                   # bandwidth
c    = THR-C_RK_BANDWIDTH_C            # default 0.4, cap 1.0, calibration seam
n    = nombre de buckets dans fenêtre
bucket_size = THR-C_RK_BUCKET_SIZE     # default 5 min, cap 15 min

Source: Barndorff-Nielsen et al. 2008 eq.(3.1)-(3.7)
DOI: 10.3982/ECTA6495
```

**b) OFI** `CONSTRAINT_DOCTRINAL` (Cont-Kukanov-Stoikov 2014)
```
OFI_t = Σ_{i=t-N+1}^{t} [ΔQ^b_i · 𝟙(P^b_i ≥ P^b_{i-1}) - ΔQ^a_i · 𝟙(P^a_i ≤ P^a_{i-1})]

ΔQ^b_i = changement de quantité au meilleur bid à l'event i
ΔQ^a_i = changement de quantité au meilleur ask à l'event i
N       = THR-C_OFI_WINDOW             # default 500 events, cap 2000

Source: Cont, Kukanov, Stoikov 2014 eq.(1)-(3)
DOI: 10.1093/jjfinec/nbt003
```

**c) Kyle λ** `CONSTRAINT_DOCTRINAL` (Kyle 1985)
```
ΔP_t = λ · SignedVolume_t + ε_t

estimation: OLS rolling sur fenêtre de THR-C_KYLE_WINDOW
SignedVolume = volume × sign(trade_direction)   # Lee-Ready ou tick rule
λ = coefficient de régression (price impact / unité de volume signé)
THR-C_KYLE_WINDOW = default 1h, cap 4h

Source: Kyle 1985 eq.(1)
DOI: 10.2307/1913210
```

**d) VPIN** `CONSTRAINT_DOCTRINAL` (Easley-López de Prado-O'Hara 2012)
```
VPIN = (1/n) · Σ_{τ=1}^{n} |V^S_τ - V^B_τ| / V_bucket

V_bucket = DailyVolume / THR-C_VPIN_BUCKETS    # default 50, cap 100
V^S_τ, V^B_τ = volume sell/buy par bucket (classification Bulk Volume)
n = nombre de buckets dans fenêtre glissante (default 50)
THR-C_VPIN_BUCKETS = default 50, cap 100

Source: Easley, López de Prado, O'Hara 2012 eq.(2)-(4)
DOI: 10.1093/rfs/hhs053
```

**Nouveaux thresholds à ajouter à la table §5 de doc 21** :

| ID | Meaning | Default | Hard cap | Module |
|---|---|---|---|---|
| THR-C_RK_BANDWIDTH_C | Realized kernel bandwidth constant | 0.4 | 1.0 | `structure_detector_c` |
| THR-C_RK_BUCKET_SIZE | Realized kernel bucket duration | 5 min | 15 min | `structure_detector_c` |
| THR-C_OFI_WINDOW | OFI cumulation window (events) | 500 | 2000 | `continuation_validator_c` |
| THR-C_KYLE_WINDOW | Kyle λ regression window | 1h | 4h | `continuation_validator_c` |
| THR-C_VPIN_BUCKETS | VPIN bucket count per day | 50 | 100 | `continuation_validator_c` |

### P0-5b. Compléter formules quant en Annexe A — doc 22

Pour Engine D, les mêmes formules s'appliquent mais avec deux précisions D-spécifiques :
- OFI est **recalculé** sur la fenêtre post-close du `first_episode_ref` (pas hérité)
- Realized kernel est **recalculé** (le contexte vol change entre l'épisode original et le re-entry)
- Kyle λ est recalculé sur la fenêtre courante

### P0-5c. Tests paper_repro obligatoires (couplé avec P0-5a/b)

Ajouter à la test matrix de doc 21 §6 et doc 22 §7 :

| Suite | Test | Paper reproduit |
|---|---|---|
| `test_realized_kernel_repro.py` | σ_RK sur données simulées (seed fixe) reproduit Barndorff-Nielsen 2008 Table 1 order of magnitude | ECTA6495 Table 1 |
| `test_ofi_repro.py` | OFI positif quand bid queue croît + ask queue décroît | Cont-Kukanov 2014 §3 directional prediction |
| `test_kyle_lambda_repro.py` | λ > 0 sur données synthétiques avec informed trader | Kyle 1985 basic prediction eq.(1) |
| `test_vpin_repro.py` | VPIN → 1.0 quand 100% informed flow (tous trades du même côté) | Easley-López 2012 boundary case |

---

## 4bis. P1 — NON-BLOQUANTS (pass séparé OK)

### P1-6. Tests hypothesis + published-paper reproduction

Doc 21 §6 et doc 22 §7 listent boundary tests. Ajouter colonne "hypothesis" (property-based) et "paper_repro" au-delà des 4 tests minimaux de P0-5c — obligation CODEX_PROMPT R34.

### P1-7. Table "D-sur-A vs D-sur-C" — doc 22 §3 Stage 8

`first_episode_ref.bet_structure` héritée peut être `DIRECTIONAL_LONG` (si A) ou `BREAKOUT` (si C). Clarifier conviction profile et invalidation behavior pour chaque cas.

### P1-8. Référence calibration seam explicite

Dans les tables §5 (doc 21) et §6 (doc 22), ajouter colonne "calibration_module" pointant vers `risk_runtime_drawdown_calibration.py` ou équivalent.

### P1-9. Version-pin renvois doc 23

Doc 21/22 invoquent doc 23 sans hash ni version. Ajouter `doc_23@<hash>` dans header.

### P1-10. Sources VPIN threshold crypto

`THR-C_VPIN_MAX ≤ 0.5` sans citation. Soit citer étude crypto, soit marquer explicitement "TBD_shadow_calibration".

---

## 5. Corrections parallèles à propager sur docs 19 et 20 (hors scope pass-2 21/22 mais dépendant)

Ces corrections étaient identifiées avant l'audit et restent dues — Codex peut les regrouper dans un PR dédié :

1. Remplacer toute référence `src/meta_engine/` par `src/meta_minimal/` (runtime), `src/meta_learning/` (governance), ou `src/protocols/` (coordination) selon contexte.
2. Supprimer toute occurrence résiduelle de `side="flat"` dans doc 20 §11 si présente.
3. Requalifier "drop-in replacement" (doc 20 P2-06) en "backward-compatible extension with optional fields then per-engine migration".
4. Doc 19 §2 : corriger "A/B only coded" → "A/B/C/D codés ; C/D requièrent doctrinal deepening (voir docs 21, 22)".

---

## 6. Ordre d'exécution recommandé

1. **P0-2** en premier (`ClosedEpisodeJournal` débloque R-D-1 et donc tout `first_episode_resolver_d`).
2. **P0-1** ensuite (`revenge_risk_penalty` débloque `marginal_value_estimator_d` + tests).
3. **P0-3** (impact test matrix — les suites changent selon status REQUIS/OPTIONNEL).
4. **P0-4** (gate promotion, pas gate implémentation — peut venir en dernier mais requis avant shadow gate check).
5. **P0-5** (formules quant complètes — **BLOQUANT**, élevé depuis P1-5 par règle R-QUANT-FIRST doc 28 §2bis). Doit être fait AVANT toute implémentation de feature microstructure. Branche `fix/doc27-P0-5-quant-formulas`.
6. Puis P1-6 → P1-10 en PR séparée.
7. §5 (corrections docs 19/20) en PR parallèle indépendant.

---

## 7. Format de livrable attendu de Codex

Chaque fix P0 produit :

```
BLOC FIX P0-<n>
-----------------------------
files_touched:
  - <path> (modified|created)
diff_summary: <2-3 lignes>
acceptance_checks:
  - [✓|✗] <criterion 1>
  - [✓|✗] <criterion 2>
tests_added:
  - tests/<path>::<testname>
calibration_thresholds_added:
  - THR-<ID> = default/cap (module)
open_questions: <liste ou "none">
status: COMPLETE | PARTIAL | BLOCKED
next_safe_step: <une ligne>
```

---

## 8. Journal d'exécution Codex

*(Codex ajoute une entrée datée après chaque fix appliqué. Format : `YYYY-MM-DD | fix_id | status | commit_hash | dispute_id | notes`.)*

| Date | Fix ID | Status | Commit | Dispute | Notes |
|---|---|---|---|---|---|
| 2026-04-16 | P0-1 | COMPLETE | pending_local_commit | D-2026-04-16-001 | User option C applied: no continuous penalty, explicit replay/backtest observability added on Engine D validation rail |
| 2026-04-16 | P0-2 | COMPLETE | pending_local_commit | D-2026-04-16-002 | `closed_episode_journal.py` created with frozen append-only `EpisodeRef` / `ClosedEpisodeJournal` + persistence + eligibility filtering |
| 2026-04-16 | P0-3 | COMPLETE | pending_local_commit | — | Helpers reclassified REQUIRED/OPTIONAL in docs 21/22 per rank-2 doctrine |
| 2026-04-16 | P0-4 | COMPLETE | pending_local_commit | D-2026-04-16-004 | `multiple_testing_guard.py` created with HLZ eq.(8) seam; docs 21/22 now default to user-selected `k_HLZ = pairs_tested`, with `promotion_floor = max(pairs_tested, 20)` kept explicit and non-default; module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007` |
| 2026-04-16 | P0-5 | COMPLETE | pending_local_commit | — | Docs 21/22 now include rank-1 Annex A microstructure formulas, new THR-C microstructure threshold rows with `calibration_module`, explicit `paper_repro` tests, and the measured OFI DOI correction to `10.1093/jjfinec/nbt003` |

## 9. Registre des disputes ouvertes par ce doc

*(Synchronisé avec doc 28 §7.)*

| ID | Sujet | Rang visé | Responsable initial | Statut |
|---|---|---|---|---|
| `D-2026-04-16-001` | Forme fonctionnelle `revenge_risk_penalty` | 1 (papier) sinon 4 (user) | Codex (recherche) | RESOLVED — user option C + replay/backtest observability required |
| `D-2026-04-16-002` | Collision `ClosedEpisodeJournal` avec code existant | 2 (canon) | Codex (scan repo) | RESOLVED — create-new |
| `D-2026-04-16-003` | Réservé — P0-3 REQUIS/OPTIONNEL helpers | 2 | Codex | CLOSED_WITHOUT_DISPUTE — P0-3 applied without Codex objection |
| `D-2026-04-16-004` | `k_HLZ` valeur réelle vs proposition Opus 320 | 1 + 2 + 4 | Codex (lit module) | RESOLVED — Opus k=320 rejected; pair-count seam retained per HLZ eq.(8) + doc 20 §12.2, and docs 21/22 default switched by user choice to `k_HLZ = pairs_tested`; `promotion_floor` kept explicit non-default; module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007` |

---

## 10. Hand-back Opus + audit pack obligatoire

Après chaque P0 Codex produit :
1. Commit atomique sur branche `fix/doc27-P0-<n>`.
2. Entrée dans §8 Journal ci-dessus.
3. Mise à jour de `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md` (sections `Files Changed`, `Claims Implemented`, `Tests and Proof`, `Completion Status`) conforme template doc 26.
4. Clôture du bloc Dispute associé dans doc 28 §7 (statut RESOLVED + evidence).

Après les 5 P0 complets : Codex signale à Opus pour re-audit selon protocole 25. Si re-audit verdict ≥ 8.5/10 → merge autorisé et docs 21/22 passent de `SPEC` à `APPROVED as SPEC`.

---

## 11. Ordre d'exécution canonique

1. `D-2026-04-16-002` (scan repo collision `ClosedEpisodeJournal`) — 10 min.
2. `D-2026-04-16-004` (lecture module `multiple_testing_guard`) — 10 min.
3. `D-2026-04-16-001` (recherche littérature `revenge_risk_penalty`) — 30 min timebox.
4. Si rang 1 trouvé sur P0-1 → appliquer ; sinon ouvrir escalade rang 4 user et appliquer strictement la décision user (ici: option C = pas de pénalité continue, mais observabilité replay/backtest obligatoire).
5. P0-2 implémentation (après 1).
6. P0-4 implémentation (après 2).
7. P0-1 implémentation (après 3 ou escalade résolue).
8. P0-3 implémentation (indépendant, peut se paralléliser).
9. P1 en PR séparée après merge P0.

---

**Fin du brief. Codex : commencer par les 3 mesures `CODEX_TO_MEASURE` (disputes 002, 004, 001) AVANT toute écriture de code.**

---

## 12. Addendum P0-5 closure (2026-04-16)

**Rang utilise** : `1 + 2`

- P0-5 is now complete. Docs 21/22 carry Annex A formula blocks with complete equations, variable definitions, defaults, hard caps, and calibration seams.
- Tables §5 (doc 21) and §6 (doc 22) now include the explicit `calibration_module` column and the new `THR-C_RK_*`, `THR-C_OFI_WINDOW`, `THR-C_KYLE_WINDOW`, `THR-C_VPIN_BUCKETS` rows.
- Test matrices now include authoritative replacement visibility for both `hypothesis` and `paper_repro`, plus the explicit suites for realized kernel, OFI, Kyle lambda, and VPIN.
- Measured DOI correction: the Cont-Kukanov-Stoikov paper DOI is `10.1093/jjfinec/nbt003` [Rang 1], not the stale placeholder DOI carried in the raw brief.
- Final paper-repro suite names are `test_realized_kernel_repro.py`, `test_ofi_repro.py`, `test_kyle_lambda_repro.py`, and `test_vpin_repro.py`.
- Docs 21/22 now pin `doc_23@834f7fae4a06847121670559dd5bfd65c28d82da` and mark `THR-C_VPIN_MAX` as `TBD_shadow_calibration` rather than keeping the uncited `≤ 0.5` claim as authoritative.
- Effective handback condition is now "after the 5 P0 complets" rather than "after the 4 P0 complets".
