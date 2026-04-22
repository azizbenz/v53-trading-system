# Spec Opus→Codex — Smoke Build-9 Engine B : alignement `flow_coherence` sur fixture canonique

**Date** : 2026-04-21
**Auteur Opus** : arbitrage doctrinal session 2026-04-21
**Verdict** : `SMOKE_OBSOLETE` (arbitrage A — `project_v53_arbitration_2026_04_21_engine_b_smoke_and_manifest_naming.md`)
**Target Codex** : exécution mécanique, 1 slice, <15 min

---

## Objective

Corriger le drift du scénario "canonical favorable inputs" du smoke Build-1..9 pour Engine B. Le smoke invoque actuellement `run_engine_b(EngineBInput(...))` sans passer `flow_coherence`, ce qui laisse le défaut Pydantic `0.5` et fait échouer l'étape conviction (raw_score = 0.54974 < seuil MEDIUM 0.55).

Aligner le smoke sur le fixture canonique `_emit_inputs()` de `tests/test_engines/test_engine_b/test_engine_b.py` L741-767 en passant explicitement `flow_coherence=0.8`.

**Ce n'est PAS** une modification moteur. La formule conviction B est gelée per doctrine **R-QUANT-FIRST** (memory 2026-04-21).

---

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` §4 Taleb — justifie la pénalité `false_breakout_score` sur exposition inconnue (default 0.5 → −0.05)
- `docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md` — cadre W-01..W-25 (aucun item ne touche le moteur B)
- `src/engines/engine_b/conviction_builder_b.py` L105-108 : seuils `ENGINE_B_CONVICTION_THRESHOLDS = {medium: 0.55, low: 0.30}`
- `src/engines/engine_b/engine_b_runner_support.py` L266-268 : `context_score = (regime_favorability + pair_health + data_freshness + flow_coherence) / ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT` avec `ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT = 4.0`
- Fixture canonique unit-test : `tests/test_engines/test_engine_b/test_engine_b.py` L741-767 `_emit_inputs(flow_coherence=0.8, ...)`

---

## Current Code Seam

### Fichier cible : `scripts/run_build9_core_smoke.py`

Fonction `_run_engine_chain()` L129-201. Bloc à modifier :

```python
# L163-184 (état courant)
engine_b_output = run_engine_b(
    EngineBInput(
        pair="ETHUSDT",
        current_price=97.0,
        local_mean=100.0,
        local_std=1.5,
        structure_is_range=0.7,
        recent_expansion=0.1,
        regime="range",
        regime_trend_strength=0.1,
        volume_anomaly=0.1,
        structural_break=0.0,
        continuation_momentum=0.1,
        regime_favorability=0.7,
        pair_health=0.8,
        data_freshness=0.9,
        expected_gain=0.003,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=2.0,
        scoring_version="build9_core_smoke_b",
    )
)
```

### Preuve arithmétique du drift (Opus)

| Bloc | Valeur avec défauts smoke | Valeur avec `flow_coherence=0.8` |
|---|---|---|
| excess_score | 0.4183 | 0.4183 |
| structure_score | 0.70 | 0.70 |
| context_score | (0.7+0.8+0.9+**0.5**)/4 = **0.725** | (0.7+0.8+0.9+**0.8**)/4 = **0.80** |
| cost_preference | 0.6667 | 0.6667 |
| legacy_raw | 0.59974 | 0.61474 |
| false_breakout_penalty | −0.05 | −0.05 |
| **raw (clip01)** | **0.54974** ❌ | **0.56474** ✅ |
| conviction | LOW (NO_TRADE) | MEDIUM (EMIT) |

---

## Placement

Modification exclusive de `scripts/run_build9_core_smoke.py` L163-184 (bloc `EngineBInput` dans `_run_engine_chain`).

Aucun autre fichier touché. Aucune modification de `src/`. Aucune modification de docs.

---

## Files Changed

| Fichier | Type | Nature |
|---|---|---|
| `scripts/run_build9_core_smoke.py` | modif | +1 ligne dans `_run_engine_chain` L163-184 : `flow_coherence=0.8,` |

Diff attendu ≈ 1 ligne ajoutée, 0 supprimée. `git diff --stat` doit montrer `1 file changed, 1 insertion(+)`.

---

## Claims Implemented

### C-1. Ajout de `flow_coherence=0.8` dans l'`EngineBInput` du smoke

**Localisation** : `scripts/run_build9_core_smoke.py` L163-184, à insérer entre `data_freshness=0.9,` et `expected_gain=0.003,` (ordre cosmétique conforme au fixture unit-test).

**Valeur** : `0.8` — strictement alignée sur `_emit_inputs()` du fixture canonique Engine B (`tests/test_engines/test_engine_b/test_engine_b.py` L759).

**Ne PAS changer** : toute autre valeur déjà présente dans le bloc. Pas d'ajout spéculatif (`microstructure_breakout_confirmation` reste au défaut, `sweep_score`/`absorption_score`/`poc_reversion_score` restent aux défauts 0.5 — ces défauts sont explicitement actés par `test_engine_b_runner_false_breakout_default_is_neutral` L782-787).

### C-2. Aucune mutation moteur

`src/engines/engine_b/**` **NE DOIT PAS** être modifié. Interdit par doctrine R-QUANT-FIRST.

---

## Tests and Proof (slots)

Codex doit fournir les 3 preuves requises par CLAUDE.md §"Never claim COMPLETE without proof".

### T-1. Pytest ciblé — smoke Build-9 engine chain

```bash
rtk python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py::test_engine_chain_smoke_check_passes_via_canonical_engine_facades -xvs
```

Attendu : `1 passed`. Output doit montrer `engine_a_output.engine_id == "engine_a"` et `engine_b_output.engine_id == "engine_b"`.

**Slot résultat Codex** : `___`

### T-2. Pytest non-régression — fixture canonique Engine B

```bash
rtk python -m pytest tests/test_engines/test_engine_b/test_engine_b.py::TestEngineBRunner::test_emit_favorable tests/test_engines/test_engine_b/test_engine_b.py::test_engine_b_runner_false_breakout_default_is_neutral tests/test_engines/test_engine_b/test_engine_b.py::test_engine_b_runner_conventions_are_explicitly_governed -xvs
```

Attendu : `3 passed`. Vérifie que le fixture canonique reste émetteur après intervention.

**Slot résultat Codex** : `___`

### T-3. Pytest full smoke — invariance des autres checks

```bash
rtk python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py -xvs
```

Attendu : `5 passed` (tous les tests du fichier). Les 4 autres tests (`execution_bootstrap_smoke_check_passes`, `accepts_execution_runtime_projection`, `accepts_reconciliation_calibration_root`, `accepts_gatekeeper_audit_path`) ne doivent pas régresser.

**Slot résultat Codex** : `___`

### T-4. Engineering guardrails baseline

```bash
rtk python -m engineering_guardrails --format=stat
```

Attendu : `new_violations=0`. Le smoke ne doit pas franchir le cap 700L (fichier actuel <700L, +1 ligne ne change rien).

**Slot résultat Codex** : `___`

### T-5. DAG validator

```bash
rtk python -m dag_validator
```

Attendu : `PASS` (aucune mutation d'import, strictement cosmétique).

**Slot résultat Codex** : `___`

### T-6. Git diff stat

```bash
rtk git diff --stat
```

Attendu exact :
```
 scripts/run_build9_core_smoke.py | 1 +
 1 file changed, 1 insertion(+)
```

**Slot résultat Codex** : `___`

---

## Deferred / Not Done

- **Amélioration du fixture unit-test** : vérifier que `_emit_inputs()` reste en phase avec `ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT` si un 5ème composant context est ajouté plus tard → hors scope, tracker en note.
- **Anti-drift structurel** : test invariant "smoke `EngineBInput` ⊇ `_emit_inputs`" → mentionné comme Next Safe Step mais pas implémenté ici.
- **Documentation du default `false_breakout_score=0.5`** : la sémantique Taleb-pénalité est déjà actée par `test_engine_b_runner_false_breakout_default_is_neutral` ; pas de doc supplémentaire à écrire ici.
- **Arbitrage B (manifest naming)** : spec séparée `2026-04-21_manifest_registry_stage_naming_restore.md`.
- **Splits pending** : `execution_runtime.py` 1238L, `monitoring.py` 1299L — P2 S32, hors scope.
- **PermissionError Windows** (`build/...`, `pytest-of-azizbez`) : infra hors arbitrage doctrinal.

---

## Risks

1. **Risque quasi-nul** : modification cosmétique d'un paramètre de scénario, aucun impact runtime, aucun impact moteur.
2. **Risque d'ajout accidentel** : Codex ne doit PAS "améliorer" d'autres paramètres du scénario ni modifier `src/`. **Garde-fou** : `git diff --stat` doit montrer exactement 1 fichier, 1 insertion.
3. **Risque de régression tests** : les 3 autres tests du fichier `test_build9_core_smoke_script.py` (execution_bootstrap_*) ne touchent pas `_run_engine_chain` → intact.
4. **Risque doctrinal** : zéro — le fixture canonique Engine B est déjà la référence, on s'y aligne.

---

## Completion Status (slot)

**Codex remplit** : `COMPLETE` / `PARTIAL` / `BLOCKED` avec justification.

**Slot** : `___`

---

## Next Safe Step (slot)

**Codex propose** : prochain pas sûr (ex: "ajouter un test d'invariant `smoke_inputs ⊇ canonical_fixture`").

**Slot** : `___`

---

## Opus audit checklist

Après exécution Codex, Opus vérifie :

1. [ ] `git diff --stat` = `1 file changed, 1 insertion(+)` exact (pas plus, pas moins)
2. [ ] `git diff scripts/run_build9_core_smoke.py` montre uniquement `+        flow_coherence=0.8,` dans le bloc `EngineBInput` de `_run_engine_chain`
3. [ ] Aucune modification de `src/engines/engine_b/**`
4. [ ] Aucune modification de `tests/**`
5. [ ] Aucune modification de `docs/**`
6. [ ] T-1 passe (1 test)
7. [ ] T-2 passe (3 tests)
8. [ ] T-3 passe (5 tests, non-régression)
9. [ ] T-4 `new_violations=0`
10. [ ] T-5 DAG PASS
11. [ ] Output observé réel (relancer le smoke via `python scripts/run_build9_core_smoke.py`) — la section `[Build-2..9]` doit montrer `- engine_chain: PASS - Engine A and Engine B emit on canonical favorable inputs`

Verdict Opus attendu : `GREENLIGHT` si 11/11 ; `REQUEST_FIX` sinon avec feedback ligne-à-ligne.
