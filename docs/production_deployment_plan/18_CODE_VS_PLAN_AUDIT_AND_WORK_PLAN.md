# Code vs Plan Audit — Angles morts & Plan de travail critique

> **Date** : 2026-04-13. Auteur : Opus (planification) + Sonnet (audit code).
>
> **Niveau** : production-safe / quant PhD / trader senior PhD / PhD algebra / PhD fintech / PhD developer.
>
> **Méthode** : audit lecture seule de `src/` + `tests/` contre l'ensemble des MD `00 → 17A`.
> Le repo gagne contre le MD. Aucun code modifié par ce fichier.

---

## 0. Executive Summary

**Constat principal** : l'état réel du code est **bien plus avancé** que ce que les MD de planification décrivaient comme "future target" ou "partial". L'agent codeur a implémenté la majorité des P0/P1 entre les sessions. Le système est à **~70-75 % de prêt pour SHADOW**, pas 62 % comme estimé en `16_...`.

**Mais** : 5 catégories d'angles morts critiques ont été identifiés qui **ne sont pas dans le plan actuel** et qui peuvent compromettre la production.

### Verdict par pilier (état réel 2026-04-13)

| Pilier | Plan disait | Réalité code | Écart |
|---|---|---|---|
| `venue_adapters/binance_spot/` | future target | **13 fichiers complets** | +++ |
| `sharia_compliance/` | future target | **16 fichiers + 9 tests** | +++ |
| `calibration_methods/` | planifié (13-A→13-G) | **8 fichiers : DSR, POT/GPD, bootstrap, walkforward, stationarity, multiple_testing** | +++ |
| `calibration_loader/` | W2 (fermée) | **Complet + intégré fee gate + regime + daily breaker** | = |
| `fee_aware_edge_gate.py` | partial | **Complet (100L, calibration-aware)** | ++ |
| `regime_classifier/regime_lite.py` | partial | **Complet + calibration seam** | ++ |
| `risk_backbone/loss_budgeter/daily_pnl_breaker.py` | partial | **Complet + calibration seam** | ++ |
| `execution_backbone/gatekeeper/gatekeeper.py` | partial | **Complet (24 KB, intègre sharia)** | ++ |
| `spread_guard.py`, `slippage_model.py` | partial | **Complets** | ++ |
| `alerting/telegram_alerter.py` | partial | **Complet** | ++ |
| Engine C/D unit tests | "7+7 tests" | **Imports cassés** (3 fichiers) | --- |
| `rate_limiter.py` (THR-X03) | future target | **Toujours absent** | = |
| PSR / KS / Energy / Hansen SPA | planifiés dans 14 | **Non visibles dans calibration_methods/** | --- |
| Linux VPS deployment scripts | implicite dans plan | **Inexistants (tout en Windows PowerShell)** | --- |

---

## 1. Bugs bloquants immédiats

### BUG-1 — Engine C/D imports cassés (P0 pour la confiance en test)

**Fichiers** :
- `tests/test_engines/test_engine_c/test_engine_c.py:5`
- `tests/test_engines/test_engine_d/test_engine_d.py:5`
- `tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py:11`

**Erreur** :
```python
from engine_c import EngineCDecision, EngineCInput, run_engine_c  # CASSÉ
from engine_d import EngineDDecision, EngineDInput, run_engine_d  # CASSÉ
```

**Correction** :
```python
from engines.engine_c import EngineCDecision, EngineCInput, run_engine_c
from engines.engine_d import EngineDDecision, EngineDInput, run_engine_d
```

**Impact** : les tests unitaires de C et D ne tournent pas. Seuls les runtime tests (`test_engine_c_runtime.py`, `test_engine_d_runtime.py`) fonctionnent car ils utilisent le bon préfixe.

**Acteur** : **Sonnet** — fix trivial (3 lignes), haute priorité.

---

## 2. Angles morts par dimension

### 2.1 Trading — 5 angles morts

#### AS-T1 — Rate limiter actif absent

**Constat** : `rest_client.py` **parse** les rate limits depuis `exchangeInfo` (ligne 260-266) mais il n'y a **pas d'enforcement actif** (pas de token bucket, pas de `rate_limiter.py`). Le plan identifiait `THR-X03` comme "future target" (11A) — toujours vrai.

**Risque production** : Binance interdit IP sur dépassement quota (1200 req/min, 50 orders/10s). Sans token bucket, le système peut se faire bannir en conditions de marché agitées (retry storm sur erreur, reconciliation urgente).

**Acteur** : **Sonnet** — créer `src/venue_adapters/binance_spot/rate_limiter.py`, token bucket simple, intégrer dans `rest_client.py`.

#### AS-T2 — Aucune preuve testnet réelle

**Constat** : `test_integration_testnet.py` planifié dans `03_GAPS_P0.md` n'existe pas. Le file 17A montre Shadow tournant sur réseau réel (authenticated) mais **sans test structuré** contre le testnet Binance.

**Risque** : le Binance adapter n'a jamais soumis un ordre réel au testnet. Les bugs de serialization, d'auth, de timing peuvent exister et ne se révèleront qu'en live.

**Acteur** : **Sonnet** — créer `tests/test_venue_adapters/test_integration_testnet.py` avec au moins : auth, order submit → cancel, balance query.

#### AS-T3 — Partial fill handling non spécifié

**Constat** : `order_translator.py` gère les ordres mais aucune trace de gestion des **partial fills** dans la chaîne execution_backbone → risk_backbone. Si Binance remplit 60 % d'un ordre :
- Le 40 % restant est-il annulé automatiquement ?
- Est-il géré comme une position partielle ?
- Le moteur engine est-il notifié ?

**Risque** : positions orphelines, capital bloqué, double comptage en reconciliation.

**Acteur** : **Opus** — spec dans un nouveau MD `19_PARTIAL_FILL_HANDLING.md` avant que Sonnet code. Décision humaine requise (D-19 à ajouter dans `10_...`).

#### AS-T4 — Ordre de démarrage du système non documenté

**Constat** : plusieurs composants dépendent l'un de l'autre au boot (calibration_loader → engine → gatekeeper → venue_adapter → execution_runtime). Aucun document ne spécifie l'**ordre de démarrage** ni les vérifications de prêt-à-trader ("readiness checks").

**Risque** : le système démarre mais un composant est en état invalide (calibration non chargée, WS non connecté), ce qui peut entraîner un trade avec des thresholds par défaut.

**Acteur** : **Opus** — ajouter spec readiness sequence dans `07_PHASE_PLAN_0_TO_4.md` ou nouveau MD.

#### AS-T5 — Idempotency UUIDv5 non standard

**Constat** : `order_translator.py:23-26` implémente `build_binance_client_order_id` via `f"v53_{engine_id}_{intent_id}"` (truncated, not UUIDv5). Le plan `03_GAPS_P0.md` spécifiait explicitement **"UUIDv5 sur intent_id"**. Si l'implémentation est juste une f-string tronquée, des collisions sont possibles.

**Acteur** : **Sonnet** — vérifier l'implémentation exacte de `build_binance_client_order_id` et corriger si non-UUIDv5.

---

### 2.2 Quant — 5 angles morts

#### AS-Q1 — `ce_min` et `delta_safe` absents du catalogue de calibration

**Constat** : chaque engine runner (A/B/C/D) a des valeurs hardcodées :
- Engine A : `ce_min=0.0001`, `delta_safe=0.0005`
- Engine B : `ce_min=0.0002`, `delta_safe=0.0008`
- Engine C : `ce_min=0.00015`, `delta_safe=0.0005`
- Engine D : `ce_min=0.00012`, `delta_safe=0.0005`

Ces valeurs **ne sont pas dans `11_DYNAMIC_THRESHOLDS_CATALOG.md`** (catalogue actuel : THR-E01 à THR-I04). Elles ne sont donc pas calibrées via backtest ni validées via shadow. Ce sont les seuils d'edge minimum **les plus critiques** du système — et ils ne sont pas dans le catalogue.

**Risque** : si les conditions de marché changent (fees augmentent, spread s'élargit), ces seuils seront sous-calibrés.

**Acteur** : **Opus** — ajouter `THR-E03` (ce_min par engine), `THR-E04` (delta_safe par engine) dans `11_DYNAMIC_THRESHOLDS_CATALOG.md`, avec méthode de calibration dans `13_CALIBRATION_METHODS.md`.

#### AS-Q2 — PSR, KS test, Energy distance, Hansen SPA absents du code

**Constat** : `14_SHADOW_GATE_MATH.md` spécifie des tests requis pour les gates :
- PSR (Probabilistic Sharpe Ratio) — **absent** de `calibration_methods/`
- KS 2-sample test — **absent**
- Energy distance (Székely-Rizzo) — **absent**
- Hansen SPA test — **absent**
- Mann-Kendall trend test — **absent**

`calibration_methods/` a : `dsr.py`, `pot_gpd.py`, `bootstrap.py`, `walkforward.py`, `stationarity.py`, `multiple_testing.py`. Mais pas les 5 tests gates.

**Risque** : quand le premier gate G2.1 (1m→2m) arrive, aucun code ne calcule les critères du rapport. Le gate ne peut pas être produit.

**Acteur** : **Sonnet** — implémenter `calibration_methods/psr.py`, `calibration_methods/ks_test.py`, `calibration_methods/energy_distance.py`, `calibration_methods/hansen_spa.py`, `calibration_methods/mann_kendall.py`. Spec fournie dans `14_...`.

#### AS-Q3 — `risk_runtime.py` drawdown thresholds hardcodés sans calibration seam

**Constat** : `src/risk_backbone/risk_runtime.py:57-58` :
```python
drawdown_warning_threshold_pct: float = 0.02
drawdown_observe_threshold_pct: float = 0.04
```
Ces valeurs ne sont reliées à **aucun `threshold_id`** du catalogue, et `risk_runtime.py` n'importe pas `calibration_loader`. Ce sont des `Field(default=...)` Pydantic qui seront utilisés si rien ne les écrase.

**Risque** : si le capital réel perd 2% en une journée, le système observe mais ne breake pas — parce que `daily_pnl_breaker.py` (qui a un seam) et `risk_runtime.py` (qui n'en a pas) peuvent avoir des seuils divergents.

**Acteur** : **Sonnet** — ajouter calibration seam dans `risk_runtime.py` pour `drawdown_warning` et `drawdown_observe`. Mapper vers `THR-R01`/`THR-R02` ou créer `THR-W01`/`THR-W02`.

#### AS-Q4 — DSR formula : vérification du terme d'ajustement multi-essais

**Constat** : `calibration_methods/dsr.py` utilise `from statistics import NormalDist` (stdlib Python). La formule DSR de Bailey-López de Prado 2014 nécessite :
$$\text{SR}^* = \sqrt{V[\widehat{\text{SR}}]} \cdot \left((1-\gamma_E)\Phi^{-1}(1-1/N) + \gamma_E\Phi^{-1}(1-1/(Ne))\right)$$
avec la constante d'Euler-Mascheroni $\gamma_E = 0.5772$.

**Vérification nécessaire** : est-ce que `dsr.py` implique ce terme $\text{SR}^*$ correctement ? Si N=1 (pas de multi-essais), la formule se simplifie, mais pour N>1 (multi-engine), l'ajustement est critique.

**Acteur** : **Sonnet** — ajouter un test `tests/test_calibration_methods/test_dsr_multiengine.py` qui valide le résultat DSR pour N=4 contre le résultat attendu du paper (Bailey-López de Prado 2014, Table 1).

#### AS-Q5 — `shadow_runtime.py` : `max_allowed_ce_net_drop: 0.0005` hardcodé

**Constat** : `src/protocols/shadow_runtime.py:554` a un seuil hardcodé non présent dans `11_...`.

**Acteur** : **Opus** — ajouter `THR-S06` (max_ce_net_drop_shadow) dans `11_...` et méthode de calibration dans `13_...`. **Sonnet** — ajouter calibration seam dans `shadow_runtime.py`.

---

### 2.3 Code — 5 angles morts

#### AS-C1 — Engine C/D imports cassés (déjà listé en BUG-1)

Cf. § 1. Fix immédiat Sonnet.

#### AS-C2 — `calibration_methods/` sans tests suffisants

**Constat** : les implémentations PhD-level dans `calibration_methods/` (`pot_gpd.py`, `dsr.py`, `bootstrap.py`, `walkforward.py`, `stationarity.py`) sont du code qui ne doit jamais échouer silencieusement — car il produit les artefacts qui pilotent le trading. Aucune trace de tests de validation mathématique (contre des exemples connus du paper).

**Risque** : une erreur de signe dans `dsr.py`, un mauvais sens de l'IC dans `pot_gpd.py` → calibration fausse → seuil mal calibré → perte.

**Acteur** : **Sonnet** — créer `tests/test_calibration_methods/` avec cas de validation vs valeurs connues des papers pour : DSR (Bailey-López de Prado table 1), POT/GPD (Coles 2001 exemple), bootstrap IC (série i.i.d. dont la distribution est connue).

#### AS-C3 — `rate_limiter.py` absent (déjà listé en AS-T1)

Cf. AS-T1.

#### AS-C4 — Tests coverage de `calibration_methods/` non mesurée

**Constat** : `calibration_methods/` a 8 modules mais aucun répertoire de tests ne lui correspond (pas de `tests/test_calibration_methods/` visible).

**Acteur** : **Sonnet** — créer `tests/test_calibration_methods/` avec au minimum : test DSR, test POT/GPD, test bootstrap IC.

#### AS-C5 — `shadow_runtime.py` hardcode non documenté

Cf. AS-Q5.

---

### 2.4 Math — 5 angles morts

#### AS-M1 — `ce_min`/`delta_safe` engines : méthode de calibration non définie

Cf. AS-Q1. Non seulement ils manquent dans le catalogue, mais la **méthode de calibration** de `ce_min` et `delta_safe` n'est pas dans `13_CALIBRATION_METHODS.md`.

`ce_min` est le seuil d'edge minimum net du coût. Il devrait être calibré comme `THR-E02` (plancher en bps) mais **par engine**, car chaque engine a un profile risque/fréquence différent.

**Acteur** : **Opus** — section dans `13_...` pour les seuils per-engine.

#### AS-M2 — Aucune méthode de calibration pour `drawdown_warning` / `drawdown_observe`

**Constat** : `THR-R01` à `THR-R03` couvrent les breakers (daily/weekly/monthly). Mais `drawdown_warning` et `drawdown_observe` (niveaux intermédiaires, pas des breakers) ne sont dans **aucune méthode de calibration**. Ce sont des niveaux d'alerte, pas de stop, mais leur calibration est aussi importante (sinon le système est en alerte permanente ou jamais).

**Acteur** : **Opus** — ajouter `THR-W01` (drawdown_warning) et `THR-W02` (drawdown_observe) dans `11_...` avec méthode dans `13_...` (ex: quantile 80-90% de la distribution DD historique).

#### AS-M3 — `POT/GPD` : vérification refus ξ > 1 implémentée ?

**Constat** : `13_CALIBRATION_METHODS.md §5.2.1` spécifie : "Refus si ξ̂ > 1 (variance infinie, GPD pas exploitable)". Cette condition est-elle dans `calibration_methods/pot_gpd.py` ?

**Acteur** : **Sonnet** — vérifier `pot_gpd.py` et ajouter si absent : `if xi_hat > 1: raise CalibrationRejectError("xi > 1")`.

#### AS-M4 — Bootstrap stationnaire (Politis-Romano) vs bootstrap i.i.d.

**Constat** : `calibration_methods/bootstrap.py` existe. Est-ce le bootstrap **stationnaire** (block bootstrap, Politis-Romano) ou le simple bootstrap i.i.d. ? Pour des séries temporelles financières, le bootstrap i.i.d. est **incorrect** (ignore l'autocorrélation).

**Acteur** : **Sonnet** — vérifier que `bootstrap.py` implémente bien un block bootstrap stationnaire. Si c'est i.i.d., corriger et ajouter test.

#### AS-M5 — `hard_cap_floor.py` : logique de safety floor

**Constat** : `calibration_methods/hard_cap_floor.py` existe (concept de MI-7 dans `13_...`). Est-ce que cette fonction est **appelée par le calibration_loader** avant de publier un artefact ? Ou est-ce un utilitaire standalone non intégré ?

**Acteur** : **Sonnet** — vérifier l'intégration de `hard_cap_floor.py` dans le pipeline calibration_loader → artefact. Si absent, ajouter.

---

### 2.5 Software Engineering — 5 angles morts

#### AS-SE1 — Aucun script de déploiement Linux VPS

**Constat** : Le plan cible Hetzner CX43 Linux. `17A_...` montre Windows PowerShell. Il n'existe **aucun** script Linux pour :
- installer Python 3.13 sur Ubuntu 24.04
- créer un service `systemd` pour `shadow_vps_service.py`
- déployer les secrets via `age/sops`
- configurer `node_exporter`
- configurer les cron jobs pour log rotation et disk monitoring

**Risque** : quand vient le moment de déployer sur le vrai VPS, le temps de mise en place sera sous-estimé et il y aura des surprises (différences Python version, permissions, paths).

**Acteur** : **Opus** — spec dans un nouveau MD `19_VPS_DEPLOYMENT_RUNBOOK.md`. **Sonnet** — scripts shell/Ansible/Makefile correspondants.

#### AS-SE2 — Log rotation non implémentée (P1-5 partiellement)

**Constat** : `disk_monitor.py` existe (partiel d'après `16_...`). Mais **log rotation** (P1-5) n'a pas de confirmation de code. Sans log rotation sur un VPS 160 GB avec Shadow tournant 24/7, les logs peuvent remplir le disque en quelques semaines.

**Acteur** : **Sonnet** — implémenter rotation des logs runtime (taille ou date), intégrer avec `THR-I03` (log retention).

#### AS-SE3 — Aucun processus de CI/CD documenté

**Constat** : aucune trace de `.github/workflows/`, `Jenkinsfile`, `Makefile` de CI. Les 1026+ tests tournent... comment ? Manuellement ? Ce n'est pas production-safe.

**Risque** : une regression se glisse sans être détectée.

**Acteur** : **Opus** — décision (D-19 ou D-20) sur le CI choisi. **Sonnet** — écrire `Makefile` ou script de test minimal pour `pytest src/ tests/ -q`.

#### AS-SE4 — Startup/readiness checks non formalisés

Cf. AS-T4.

#### AS-SE5 — Aucune procédure de rollback d'artefact de calibration

**Constat** : `12_LOCAL_LAB_VS_VPS_SEPARATION.md §6.2` décrit le flux artefact mais la règle F-3 dit "un rollback = nouvelle version vN+1". Comment concrètement déclencher un rollback en urgence à 3h du matin ? Aucun script, aucun runbook.

**Acteur** : **Opus** — spec dans `19_VPS_DEPLOYMENT_RUNBOOK.md`. Procédure : `rsync calibration_v2.json → VPS → restart service`.

---

## 3. Plan de travail critique

### Priorité P0 — Avant tout premier gate Shadow

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-01** | Fix Engine C/D imports cassés (3 fichiers) | **Sonnet** | < 30 min | IMMÉDIAT |
| **W-02** | Implémenter `rate_limiter.py` (token bucket Binance) | **Sonnet** | 2-4h | AVANT shadow live |
| **W-03** | Vérifier `build_binance_client_order_id` = UUIDv5 (pas f-string) | **Sonnet** | 30 min | AVANT ordres réels |
| **W-04** | Vérifier `bootstrap.py` = stationnaire Politis-Romano (pas i.i.d.) | **Sonnet** | 1h | AVANT calibration |
| **W-05** | Vérifier `pot_gpd.py` inclut refus ξ > 1 | **Sonnet** | 30 min | AVANT calibration |
| **W-06** | Ajouter tests `tests/test_calibration_methods/` (DSR, GPD, bootstrap vs paper) | **Sonnet** | 4-8h | AVANT calibration signée |
| **W-07** | Spec `THR-E03`/`THR-E04` (ce_min/delta_safe par engine) dans `11_...` + méthode `13_...` | **Opus** | 2h | AVANT calibration v1 |
| **W-08** | Spec `THR-W01`/`THR-W02` (drawdown_warning, drawdown_observe) dans `11_...` + `13_...` | **Opus** | 1h | AVANT shadow |

### Priorité P1 — Avant gate G2.1 (fin du 1er mois Shadow)

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-09** | Implémenter `calibration_methods/psr.py` (PSR formula) | **Sonnet** | 2h | AVANT G2.1 |
| **W-10** | Implémenter `calibration_methods/ks_test.py` | **Sonnet** | 1h | AVANT G2.1 |
| **W-11** | Implémenter `calibration_methods/energy_distance.py` | **Sonnet** | 2h | AVANT G2.1 |
| **W-12** | Implémenter `calibration_methods/mann_kendall.py` | **Sonnet** | 1h | AVANT G2.1 |
| **W-13** | Implémenter `calibration_methods/hansen_spa.py` | **Sonnet** | 4h | AVANT G2.2 (peut attendre) |
| **W-14** | Ajouter calibration seam `risk_runtime.py` (drawdown_warning/observe) | **Sonnet** | 1h | AVANT shadow |
| **W-15** | Implémenter `scripts/shadow_gate_check.py` (rapport JSON `14_...` §12) | **Sonnet** | 8h | AVANT G2.1 |
| **W-16** | Spec partial fill handling | **Opus** | 2h | AVANT MICRO_LIVE |
| **W-17** | Vérifier `hard_cap_floor.py` intégré dans pipeline calibration → artefact | **Sonnet** | 1h | AVANT calibration v1 |
| **W-18** | Test integration testnet Binance (`test_integration_testnet.py`) | **Sonnet** | 4h | AVANT MICRO_LIVE |

### Priorité P2 — Avant MICRO_LIVE

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-19** | Spec + scripts déploiement Linux VPS (`19_VPS_DEPLOYMENT_RUNBOOK.md`) | **Opus + Sonnet** | 4h spec + 8h code | AVANT VPS |
| **W-20** | Log rotation + disk monitor wiring (THR-I01/I02/I03) | **Sonnet** | 3h | AVANT shadow long |
| **W-21** | DSR test multi-engine (N=4, valeur Bailey-López de Prado table 1) | **Sonnet** | 2h | AVANT calibration v1 |
| **W-22** | Spec D-19 (partial fill decision) + D-20 (CI/CD choice) dans `10_...` | **Opus** | 1h | AVANT implémentation |
| **W-23** | Makefile / script CI minimal (`pytest` complet en 1 commande) | **Sonnet** | 1h | AVANT shadow |
| **W-24** | Spec startup readiness sequence dans `07_...` | **Opus** | 1h | AVANT MICRO_LIVE |
| **W-25** | Spec + procédure rollback calibration artefact d'urgence | **Opus** | 1h | AVANT LIVE |

---

## 4. Tableau récapitulatif angles morts

| # | Dimension | Angle mort | Sévérité | Acteur |
|---|---|---|---|---|
| AS-T1 | Trading | Rate limiter actif absent | **P0** | Sonnet |
| AS-T2 | Trading | Aucune preuve testnet réelle | **P0** | Sonnet |
| AS-T3 | Trading | Partial fill handling non spécifié | **P1** | Opus |
| AS-T4 | Trading | Ordre de démarrage non documenté | **P1** | Opus |
| AS-T5 | Trading | Idempotency non-UUIDv5 à vérifier | **P0** | Sonnet |
| AS-Q1 | Quant | `ce_min`/`delta_safe` absents du catalogue | **P1** | Opus |
| AS-Q2 | Quant | PSR/KS/Energy/Hansen SPA absents du code | **P1** | Sonnet |
| AS-Q3 | Quant | `risk_runtime.py` drawdown sans calibration seam | **P1** | Sonnet |
| AS-Q4 | Quant | DSR multi-engine non validé contre paper | **P1** | Sonnet |
| AS-Q5 | Quant | `shadow_runtime.py` hardcode non catalogué | **P2** | Opus+Sonnet |
| AS-C1 | Code | Engine C/D imports cassés | **P0** | Sonnet |
| AS-C2 | Code | `calibration_methods/` sans tests paper | **P0** | Sonnet |
| AS-C3 | Code | `rate_limiter.py` absent | **P0** | Sonnet |
| AS-C4 | Code | Pas de `tests/test_calibration_methods/` | **P0** | Sonnet |
| AS-C5 | Code | `shadow_runtime.py` hardcode | **P2** | Sonnet |
| AS-M1 | Math | Méthode calibration `ce_min`/`delta_safe` absente | **P1** | Opus |
| AS-M2 | Math | Méthode calibration `drawdown_warning/observe` absente | **P1** | Opus |
| AS-M3 | Math | Refus ξ>1 dans `pot_gpd.py` à vérifier | **P0** | Sonnet |
| AS-M4 | Math | Bootstrap i.i.d. vs stationnaire à vérifier | **P0** | Sonnet |
| AS-M5 | Math | `hard_cap_floor.py` intégration pipeline à vérifier | **P1** | Sonnet |
| AS-SE1 | SWE | Aucun script déploiement Linux VPS | **P1** | Opus+Sonnet |
| AS-SE2 | SWE | Log rotation non confirmée | **P1** | Sonnet |
| AS-SE3 | SWE | Aucun CI/CD | **P2** | Opus+Sonnet |
| AS-SE4 | SWE | Startup readiness checks absents | **P1** | Opus |
| AS-SE5 | SWE | Procédure rollback artefact absente | **P1** | Opus |

---

## 5. Ce qui est plus avancé que prévu (positif)

**Ne pas re-coder ce qui existe** :

| Ce qu'on croyait manquer | Réalité |
|---|---|
| `venue_adapters/binance_spot/` | **Complet** (13 fichiers, idempotency via `build_binance_client_order_id`) |
| `sharia_compliance/` | **Complet** (16 fichiers, 9 tests, intégré gatekeeper) |
| `calibration_methods/` | **8 modules** (DSR, POT/GPD, bootstrap, walkforward, stationarity, multiple_testing) |
| `fee_aware_edge_gate.py` | **100L, calibration-aware** |
| `telegram_alerter.py` | **Présent** dans `alerting/` |
| `gatekeeper.py` | **24 KB, intègre sharia + risk + edge** |
| `spread_guard.py`, `slippage_model.py` | **Présents** |

---

## 6. Qui fait quoi : règle de répartition

| Type de travail | Acteur |
|---|---|
| Spec math nouvelle (nouveaux threshold_id, méthodes calibration) | **Opus** |
| Mise à jour catalogue `11_...` et méthodes `13_...` | **Opus** |
| Spec architecture, décisions humaines, runbooks | **Opus** |
| Fix bugs simples (imports cassés, refus manquant) | **Sonnet** |
| Implémentation nouvelles fonctions math (PSR, KS, Hansen SPA) | **Sonnet** |
| Tests de validation vs papers | **Sonnet** |
| Scripts déploiement Linux (systemd, Makefile, log rotation) | **Sonnet** |
| Vérification `bootstrap.py` stationnaire vs i.i.d. | **Sonnet** |
| Arbitrage "doit-on implémenter ça maintenant ?" | **Humain** |

---

## 7. Prochaine session recommandée

**Session Sonnet (code)** — priorité immédiate :
1. W-01 : fix Engine C/D imports (< 30 min)
2. W-04 : vérifier bootstrap stationnaire
3. W-05 : vérifier POT/GPD refus ξ > 1
4. W-06 : créer `tests/test_calibration_methods/` (DSR + GPD + bootstrap)
5. W-03 : vérifier `build_binance_client_order_id`

**Session Opus (spec)** — en parallèle ou après :
1. W-07 : spec `THR-E03`/`THR-E04` (ce_min/delta_safe engines)
2. W-08 : spec `THR-W01`/`THR-W02` (drawdown_warning/observe)
3. W-16 : spec partial fill handling
4. W-19 : runbook déploiement VPS Linux

**Avant de lancer shadow long (>2 semaines)** :
- W-02 (rate limiter), W-09→W-12 (PSR, KS, Energy, Mann-Kendall), W-15 (shadow_gate_check.py), W-18 (testnet)

---

## 8. Suite logique dans le dossier

Le dossier `production_deployment_plan/` a maintenant besoin de :
- `19_VPS_DEPLOYMENT_RUNBOOK.md` — déploiement Linux VPS pas à pas
- Une mise à jour `11_DYNAMIC_THRESHOLDS_CATALOG.md` avec THR-E03/E04/W01/W02/S06
- Une mise à jour `13_CALIBRATION_METHODS.md` avec méthodes pour ces nouveaux seuils
