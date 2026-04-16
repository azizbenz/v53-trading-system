# 28 — Arbitration Protocol Opus ↔ Codex

**Date** : 2026-04-16
**Statut** : RÈGLE DURE — source de vérité pour tout désaccord entre agents
**Scope** : toute proposition quant (formule, constante, seuil, contrat, placement, test) produite par Opus ou Codex dans le cadre V5.3
**Principe** : *ni Opus ni Codex ne sont source de vérité. Toute décision est tranchée par autorité externe vérifiable.*

---

## 1. Hiérarchie d'autorité (4 rangs, ordre strict)

| Rang | Source | Preuve acceptable | Exemples V5.3 |
|---|---|---|---|
| **1** | **Littérature publiée vérifiable** | paper + équation/figure citées + DOI ou arXiv ID | Cont-Kukanov 2014 eq.(3) pour OFI ; Easley-López-O'Hara 2012 §4 pour VPIN ; Harvey-Liu-Zhu 2016 eq.(8) pour déflation ; Kyle 1985 pour λ ; Barndorff-Nielsen et al. 2008 pour realized kernel |
| **2** | **Canon V5.3 figé** | doc path + section/ligne + hash git | `CLAUDE.md` capital €300-400 ; doc 20 §11 R-AC rules ; `domain_types.py:150` Side enum ; doc 19 Prohibitions 1-21 |
| **3** | **Évidence empirique shadow ≥ 4 sem.** | artefact `build/shadow_evidence/<slice>/` avec ≥ 20 pairs, logs + métriques + seed + version_hash | Calibration `THR-C_VPIN_MAX` crypto si aucune source rang 1 ; bandwidth realized kernel si paramètre crypto-spécifique |
| **4** | **Escalade utilisateur** (non-délégable) | réponse datée utilisateur avec option retenue et justification | Choix stratégie β vs γ ; ceiling capital ; tolérance drawdown ; prohibition d'une classe de features |

**Règle dure** : toute proposition doit être rangée dans exactement un de ces 4 rangs. Une proposition qui ne peut être rangée est **refusée**. Pas de "Opus pense que" ni "Codex pense que".

---

## 2. Sujets toujours rang 1-2 (jamais délégation à opinion d'agent)

- Formules de features microstructure (OFI, VPIN, Kyle λ, Amihud, Roll, Corwin-Schultz, realized kernel, Hawkes, PIN)
- Normalisation Carver (`ForecastScalar = 10/E[|F|]`, `VolScalar`, `N`)
- FDM Carver (corrélation-based)
- Déflation Harvey-Liu-Zhu (`SR_deflated = SR × √((N−k)/(N−1))`)
- Grammaire Narang 4-familles conditioning
- Contrats Pydantic v2 frozen (SignalCandidate, RefusalRecord, EpisodeRef, etc.)
- Path discipline (`src/meta_minimal/`, `src/meta_learning/`, `src/protocols/`)
- Prohibitions 1990s TA (liste doc 23 §6 + CLAUDE.md)

---

## 2bis. Règle R-QUANT-FIRST — formule complète avant tout code

**Règle dure (rang 2 canon)** : aucune feature microstructure ou formule quantitative ne peut être implémentée dans le codebase V5.3 sans que la spec correspondante contienne :

1. **Équation complète** — toutes les variables définies, pas de "uses X" sans formule
2. **Paper source** — DOI + numéro d'équation/figure exacte (rang 1 obligatoire)
3. **Paramètres** — chaque paramètre avec default, cap, et calibration_seam pointé
4. **Test paper_repro** — au moins un test reproduisant un résultat publié du paper (figure, table, boundary case)

**Justification** : un dev qui code sans formule complète produit un `silent strategy change` par omission. C'est le risque le plus fréquent et le plus invisible — le code compile, les tests passent, mais la stratégie n'est pas celle qu'on pense.

**Application** :
- Toute spec qui dit "uses realized kernel" sans Parzen/bandwidth/bucket est **INCOMPLETE** et ne peut pas être codée contre
- Toute spec qui dit "OFI persistence" sans window N / formule ΔQ^b/ΔQ^a est **INCOMPLETE**
- Un dev qui trouve une formule incomplète dans une spec doit **bloquer et remonter** avant de coder — jamais inventer les paramètres manquants
- Cette règle s'applique **avant** la priorisation P0/P1/P2 : une formule quant incomplète dans un P0 bloque le P0

**Checklist R-QUANT-FIRST (Codex doit vérifier avant chaque implémentation de feature quant)** :
- [ ] Équation complète écrite avec toutes les variables
- [ ] DOI + eq./fig. number cités
- [ ] Chaque paramètre a un `THR-*` avec default + cap + module
- [ ] Test `paper_repro` spécifié dans la test matrix
- [ ] Si un de ces 4 manque → STOP, ouvrir Dispute, ne pas coder

---

## 3. Sujets toujours rang 4 (non-délégables, escalade user obligatoire)

- Capital réel de départ, capital ceiling, vitesse de ramp
- Choix doctrinaux A/B/C/D (définition, séparation structurelle, strategy β/γ)
- Tolérance drawdown, kill switch thresholds
- Ajout ou suppression d'un engine canonique
- Modification des gates Shadow → Micro-live → Live
- Passage d'une règle HARD_BLOCK en règle SCORING (ou inverse)
- Ajout d'une nouvelle famille conditioning

---

## 4. Sujets typiquement rang 3 (empirique shadow)

- Calibration fine de thresholds crypto non-couverts par littérature equities/FX
- Bandwidth / window sizes des features microstructure sur Binance spot
- Détermination `k_HLZ` effectif après énumération réelle des tests
- Seuils `THR-D_REVENGE_SCALE`, `THR-D_REVENGE_DECAY` après shadow

---

## 5. Format du bloc Dispute

Chaque désaccord Opus ↔ Codex produit un bloc Dispute ajouté au registre §7 :

```
DISPUTE-ID: D-<YYYY-MM-DD>-<n>
SUBJECT: <description courte>
OPUS_POSITION:
  proposal: <ce qu'Opus propose>
  rank_claimed: <1|2|3|4>
  evidence: <paper/doc/artefact>
CODEX_POSITION:
  proposal: <ce que Codex propose>
  rank_claimed: <1|2|3|4>
  evidence: <paper/doc/artefact>
ARBITRATION_RANK_USED: <1|2|3|4>
DECIDING_EVIDENCE:
  source: <paper + eq/fig OU doc V5.3 + §/ligne OU shadow artefact + hash>
  hash: <DOI | git_hash | artefact_hash>
RESOLUTION:
  winner: <OPUS | CODEX | NEITHER_NEW_POSITION>
  final_position: <ce qui est retenu>
  justification: <1-3 lignes>
NEXT_ACTION:
  - <code change> OR
  - <test to run> OR
  - <escalation to user with options A/B/C>
STATUS: OPEN | RESOLVED | ESCALATED
```

**Règles d'application** :
- Rangs 1-3 → résolution automatique, pas de ping user.
- Rang 4 → bloc ESCALATED vers user avec options chiffrées (A/B/C) et conséquences par option.
- Si Opus et Codex revendiquent des rangs différents → on prend le rang le plus élevé (1 > 2 > 3 > 4) et on exige sa preuve. Si absente → downgrade au rang suivant.
- Si les deux revendiquent rang 1 avec papiers contradictoires → escalade rang 4 (doctrine user arbitre).

---

## 6. Étapes opérationnelles pour résoudre une dispute

1. **Formalisation** : agent déclencheur ouvre un bloc Dispute (statut OPEN).
2. **Preuve rang 1** : chercher paper (Google Scholar + arXiv + journals quant). Timebox 30 min. Si trouvé → `RANK_USED=1`, résolution.
3. **Preuve rang 2** : relire `CLAUDE.md` + docs 19/20/23 + module source. Timebox 15 min. Si trouvé → `RANK_USED=2`, résolution.
4. **Preuve rang 3** : déclarer besoin d'une shadow experiment, rédiger protocole court dans le bloc Dispute, suspendre le fix jusqu'à artefact disponible. Statut = BLOCKED_ON_SHADOW.
5. **Escalade rang 4** : statut = ESCALATED, ping user avec options A/B/C + conséquences + recommandation par défaut. User décide, décision datée, statut = RESOLVED.
6. **Clôture** : entrée ajoutée au registre §7 + référence dans le doc cible (doc 27, etc.).

---

## 7. Registre des disputes

*(À remplir chronologiquement. Pas d'entrée fictive.)*

| ID | Date | Sujet | Rang utilisé | Gagnant | Statut |
|---|---|---|---|---|---|
| `D-2026-04-16-001` | 2026-04-16 | Forme fonctionnelle `revenge_risk_penalty` | 4 | USER_OPTION_C | RESOLVED |
| `D-2026-04-16-002` | 2026-04-16 | Collision `ClosedEpisodeJournal` avec code existant | 2 | CODEX | RESOLVED |
| `D-2026-04-16-004` | 2026-04-16 | `k_HLZ` valeur réelle vs proposition Opus 320 | 1 + 2 + 4 | CODEX_POSITION + USER_OVERRIDE | RESOLVED |

### D-2026-04-16-001

```
DISPUTE-ID: D-2026-04-16-001
SUBJECT: Functional form for revenge_risk_penalty(n, Δt)
OPUS_POSITION:
  proposal: exponential or linear-threshold penalty tied to consecutive_stop_count and time_since_last_stop
  rank_claimed: 4
  evidence: doc 27 P0-1 marks both forms as PROPOSAL_OPUS, not doctrinal
CODEX_POSITION:
  proposal: no rank-1 paper found for an exact f(n, Δt); escalate to user with bounded options
  rank_claimed: 4
  evidence: literature search on Kahneman-Tversky 1979, Odean 1998, Lo-Repin 2002, Coval-Shumway 2005, Linnainmaa 2011
ARBITRATION_RANK_USED: 4
DECIDING_EVIDENCE:
  source: Kahneman-Tversky 1979 DOI 10.2307/1914185 gives value-function shape only; Odean 1998 DOI 10.1111/0022-1082.00072 gives disposition effect evidence; Lo-Repin 2002 DOI 10.1162/089892902317361877 gives psychophysiology correlations; Coval-Shumway 2005 DOI 10.1111/j.1540-6261.2005.00723.x gives loss-chasing evidence; Linnainmaa 2011 DOI 10.1093/rfs/hhr009 gives trade-to-learn model. None provides an exact penalty in consecutive stops and elapsed time.
  hash: 10.2307/1914185 | 10.1111/0022-1082.00072 | 10.1162/089892902317361877 | 10.1111/j.1540-6261.2005.00723.x | 10.1093/rfs/hhr009
RESOLUTION:
  winner: USER_OPTION_C
  final_position: No continuous revenge_risk_penalty is introduced at this stage. Anti-revenge discipline remains enforced by the hard rules already specified for Engine D, and the corresponding anti-revenge state must be surfaced explicitly in replay/backtest evidence so that this behavior is observable and auditable.
  justification: Rank-1 literature supports the phenomenon but not a unique functional form. The user selected option C at rank 4 and additionally required explicit replay/backtest observability rather than hidden runtime logic.
NEXT_ACTION:
  - implement ClosedEpisodeJournal and EpisodeRef contracts
  - add explicit anti-revenge observability fields on the Engine D validation rail and preserve them in replay/backtest-facing outputs
STATUS: RESOLVED
```

### D-2026-04-16-002

```
DISPUTE-ID: D-2026-04-16-002
SUBJECT: Collision between ClosedEpisodeJournal proposal and existing repo code
OPUS_POSITION:
  proposal: scan repo first, then arbitrate reuse | rename | create-new
  rank_claimed: 2
  evidence: doc 27 P0-2 step-0 is CODEX_TO_MEASURE
CODEX_POSITION:
  proposal: create-new in src/protocols/closed_episode_journal.py
  rank_claimed: 2
  evidence: RTK scan found no existing episode contracts, no EpisodeRef, and no closed-episode journal implementation; only refusal_journal and existing engine_d reentry hooks exist
ARBITRATION_RANK_USED: 2
DECIDING_EVIDENCE:
  source: current codebase scan on 2026-04-16 via `rtk grep/rg` over src/
  hash: codebase@2026-04-16
RESOLUTION:
  winner: CODEX
  final_position: create-new
  justification: There is no non-trivial existing episode contract to reuse or rename. Reusing refusal journaling would be a semantic mismatch.
NEXT_ACTION:
  - implement src/protocols/closed_episode_journal.py as a new protocol contract
STATUS: RESOLVED
```

### D-2026-04-16-004

```
DISPUTE-ID: D-2026-04-16-004
SUBJECT: Actual k_HLZ value versus Opus proposal k=320
OPUS_POSITION:
  proposal: k_HLZ = 4 × 20 × 4 = 320 if module absent
  rank_claimed: 1 and 2
  evidence: doc 27 P0-4 marks 320 as PROPOSAL_OPUS pending measurement
CODEX_POSITION:
  proposal: use Harvey-Liu-Zhu eq.(8) for the haircut, but resolve `k_HLZ` with the V5.3 pair-count canon: `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode
  rank_claimed: 1 and 2
  evidence: doc 20 §12.2 says HLZ uses `k = pairs tested` and the shadow universe is `>= 20 instruments always`; module `src/calibration_methods/multiple_testing_guard.py` implements that seam explicitly
USER_OVERRIDE:
  proposal: make observed-shadow (`k_HLZ = pairs_tested`) the default mode for docs 21/22, while keeping `promotion_floor` explicit and available as a non-default conservative option
  rank_claimed: 4
  evidence: explicit user instruction after the arbitration review
ARBITRATION_RANK_USED: 1 + 2 + 4
DECIDING_EVIDENCE:
  source: Harvey-Liu-Zhu 2016 eq.(8) + docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md §12.2 + src/calibration_methods/multiple_testing_guard.py
  hash: b2aafc74bd5abdefc8810e69f1562e9cc6881007
RESOLUTION:
  winner: CODEX_POSITION
  final_position: Opus value `320` is rejected. Current V5.3 promotion-gate seam uses pair-count composition, not `engines × pairs × regimes`. By rank 1+2, the valid seam is `pairs_tested` / `promotion_floor`; by rank 4 user choice, docs 21/22 now default to observed-shadow `k_HLZ = pairs_tested`. `promotion_floor = max(pairs_tested, 20)` remains explicit and available, but non-default.
  justification: Rank-1 controls the formula, rank-2 canon controls the V5.3 pair-count seam, and rank-4 user authority can choose the default mode between the already-valid seam options. The Opus multiplication proposal is negotiable and loses to the canon pair-count rule.
NEXT_ACTION:
  - keep docs 21/22 aligned with the module blob hash when the seam changes
STATUS: RESOLVED
```

---

## 8. Pour les fixes du doc 27 : rang attendu par P0

| Fix doc 27 | Rang attendu | Source de preuve | Responsable |
|---|---|---|---|
| P0-1 `revenge_risk_penalty` formule | Rang 1 si littérature (prospect theory / behavioral microstructure) sinon Rang 4 | Kahneman-Tversky 1979 / Lo-Repin 2002 / escalade user | Codex cherche, Opus revue |
| P0-2 `ClosedEpisodeJournal` contrat | Rang 2 (grammaire Narang + doc 20 §3 + Pydantic V5.3) | doc 20 + domain_types.py | Codex dérive, Opus valide |
| P0-3 helpers REQUIS/OPTIONNEL | Rang 2 (principe Narang "isolation hard rules for testability") | doc 20 §11 + test matrix §6/§7 | Opus propose, Codex confirme |
| P0-4 `k_HLZ` valeur | Rang 1 (HLZ 2016) + Rang 2 (`multiple_testing_guard.py`) | Codex lit le module, rapporte valeur réelle | Codex mesure, Opus audit |

Toute valeur produite par Codex sans source rang 1/2/3 déclenche un bloc Dispute automatique.

---

## 9. Anti-patterns interdits

1. **"D'après mon expérience"** (Opus ou Codex) — refusé. Expérience ≠ source.
2. **"Cela semble raisonnable"** — refusé. Raisonnable ≠ prouvé.
3. **Moyenne arithmétique de deux propositions** — refusé. Splitting the difference n'est pas science.
4. **Citation de papier sans équation / figure / page précise** — refusé. Citation floue = pas de citation.
5. **Invoquer doctrine V5.3 sans §/ligne** — refusé. Faire pointer exactement.
6. **Empirique sans artefact persisté** — refusé. "J'ai testé" ≠ shadow evidence.
7. **Proposition rang 4 déguisée en rang 1-3** (agent qui décide à la place du user) — interdit strict.

---

## 10. Amendements

Ce protocole est canon. Toute modification requiert escalade rang 4 et mise à jour du hash en header. Le protocole lui-même ne peut pas être l'objet d'une dispute rang 1-3.

---

**Fin du protocole. Tout agent Opus/Codex doit citer doc 28 en header de ses rapports d'audit et de ses fixes quant.**
