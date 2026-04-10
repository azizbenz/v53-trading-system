# Briques V3.7 à incorporer dans V5.3 — sélection raisonnée

> **Principe** : on ne migre pas vers V3.7. On pioche **3 idées** doctrinales que V5.3 n'a pas, et on les implémente en version **simplifiée** alignée sur la philosophie V5.3 (file-based, artifact-governed, single-process).
> **Ce qu'on ne fait PAS** : importer du code V3.7 (il n'existe pas), reproduire la stack Redis/Timescale, ou recoder OSCAE.

---

## Vue d'ensemble

| # | Brique V3.7 | Statut V5.3 | Version retenue | LOC | Sessions |
|---|---|---|---|---|---|
| V37-1 | Regime awareness | Tag string passif | Regime lite 3 états (couvert en P1-1) | 400-600 | 0.5 |
| V37-2 | Execution Gatekeeper central | Distribué, non centralisé | Wrapper `authorize()` non destructif | 400-700 | 0.75-1 |
| V37-3 | Information Stress Monitor (MAS light) | Absent | Détecteur veto temps réel | 300-500 | 0.5 |

**Total V3.7 incorporé** : ~1100-1800 LOC, **~1.75-2 sessions Opus**.

> **Note** : V37-1 (regime lite) est déjà détaillé dans `04_GAPS_P1.md` sous P1-1. Ne pas double-compter dans le total global. Ce fichier le mentionne pour traçabilité doctrinale.

---

## V37-1 — Regime awareness lite

### Statut

**Couvert dans P1-1** (`04_GAPS_P1.md`). Voir là pour les détails techniques.

### Pourquoi c'est inspiré V3.7 (et pas reproduit)

V3.7 propose un `RegimeDetector` à 7 états :
- R1 TrendUp
- R2 TrendDown
- R3 Ranging
- R4 Volatile
- R5 Capitulation
- R6 Rotation
- R∅ Unknown

Avec une matrice de paramètres par régime et une liste de stratégies autorisées/interdites par régime.

**Pourquoi pas tel quel** :
1. **Surdimensionné** pour 4 engines + 10 k$
2. La matrice param × régime = 4 × 7 × N params → explosion combinatoire à calibrer
3. Calibrer les seuils de transition entre 7 états demande beaucoup de données labelisées
4. À 10 k$, le bénéfice marginal entre 3 états et 7 états est négligeable

**Version retenue** : 3 états (CALM / STRESSED / EXTREME) avec hystérésis. Suffit pour le bénéfice principal : **désactiver des engines dans les régimes inadaptés**.

### Ce qui passe au scope futur

Si plus tard tu scales à 100 k$+, l'upgrade vers 5-7 régimes devient pertinent. Le contrat `RegimeState` doit être conçu pour permettre cet upgrade sans casser l'API consommatrice.

---

## V37-2 — Execution Gatekeeper central

### Pourquoi cette brique

V5.3 a tout ce qu'il faut pour autoriser un trade — mais l'autorisation est **distribuée** sur plusieurs modules :
- `risk_backbone/risk_runtime.py`
- `risk_backbone/loss_budgeter/`
- `risk_backbone/exposure_budgeter/`
- `risk_backbone/correlation_cluster_guard/`
- `risk_backbone/btc_factor_guard/`
- `risk_backbone/emergency_kill_switch/circuit_breaker.py`
- `execution_backbone/order_decider/execution_guard.py`
- `scoring_backbone/hard_block_gate/`

Plus, en P0/P1 :
- `sharia_compliance/sharia_runtime.py` (P0-2)
- `fee_aware_edge_gate.py` (P0-3)
- `regime_provider` gating (P1-1)
- `pnl_circuit_breaker_wiring` (P1-3)

**Conséquence** : quand un trade est rejeté, **pour comprendre pourquoi il faut chercher dans 10+ modules**. C'est dur à auditer en post-mortem et c'est fragile (un module ajouté plus tard peut être oublié dans la chaîne).

V3.7 propose un `ExecutionGatekeeper` central qui exécute 6 checks séquentiels et retourne un `ExecutionPermit` avec la liste des checks passés. **C'est la bonne idée, pas la bonne implémentation** (V3.7 est papier).

### Version retenue : wrapper `authorize()` non destructif

**Principe non négociable** : ne pas réécrire la logique existante. **Wrapper** seulement.

```
src/execution_backbone/gatekeeper/
├── __init__.py
├── contracts.py                    [ExecutionPermit, GateCheck, GateResult]
├── gate_chain.py                   [chaîne de checks composable]
├── gate_definitions.py             [enregistre les guards V5.3 existants comme checks]
├── central_authorizer.py           [API publique: authorize(intent) -> ExecutionPermit]
└── tests/
    ├── test_gate_chain.py
    ├── test_central_authorizer.py
    └── test_audit_trail.py
```

### Spécifications techniques

#### `contracts.py`

```python
class GateResult(StrEnum):
    PASS = "pass"
    REJECT = "reject"
    SKIP = "skip"   # check non applicable

class GateCheck(BaseModel, frozen=True):
    name: str                      # "sharia_trade_type", "loss_budget", etc.
    result: GateResult
    reason: str = ""               # vide si PASS, raison de rejet sinon
    detail: str = ""               # détail debug
    duration_ms: float = 0.0

class ExecutionPermit(BaseModel, frozen=True):
    intent_id: str
    timestamp: float
    authorized: bool
    checks: list[GateCheck]
    reject_reason: str = ""        # vide si autorisé
    rejected_at_check: str = ""    # nom du check qui a rejeté

    def first_failure(self) -> GateCheck | None:
        return next((c for c in self.checks if c.result == GateResult.REJECT), None)
```

#### `gate_chain.py`

```python
class GateChain:
    """
    Chaîne ordonnée de checks. Premier check qui rejette stoppe la chaîne.
    """

    def __init__(self, checks: list[Callable[[OrderIntent], GateCheck]]) -> None:
        self._checks = checks

    def evaluate(self, intent: OrderIntent) -> ExecutionPermit:
        results: list[GateCheck] = []
        for check_fn in self._checks:
            start = time.perf_counter()
            check = check_fn(intent)
            check = check.model_copy(update={"duration_ms": (time.perf_counter() - start) * 1000})
            results.append(check)
            if check.result == GateResult.REJECT:
                return ExecutionPermit(
                    intent_id=intent.intent_id,
                    timestamp=time.time(),
                    authorized=False,
                    checks=results,
                    reject_reason=check.reason,
                    rejected_at_check=check.name,
                )
        return ExecutionPermit(
            intent_id=intent.intent_id,
            timestamp=time.time(),
            authorized=True,
            checks=results,
        )
```

#### `gate_definitions.py`

C'est ici que les guards V5.3 existants sont **enregistrés comme checks**. Chaque guard reste en place, on ne l'arrache pas. Le gatekeeper l'**appelle**.

```python
def make_default_chain(
    sharia_runtime: ShariaRuntime,
    fee_gate: FeeAwareEdgeGate,
    risk_runtime: RiskRuntime,
    regime_provider: RegimeProvider,
    circuit_breaker: EmergencyCircuitBreaker,
    pnl_breaker: PnLCircuitBreakerWiring,
) -> GateChain:
    return GateChain([
        # Ordre important : du moins coûteux et plus bloquant au plus coûteux
        lambda i: _check_circuit_breaker(circuit_breaker, i),
        lambda i: _check_pnl_state(pnl_breaker, i),
        lambda i: _check_sharia(sharia_runtime, i),
        lambda i: _check_regime_gating(regime_provider, i),
        lambda i: _check_fee_edge(fee_gate, i),
        lambda i: _check_risk_runtime(risk_runtime, i),
    ])

def _check_sharia(runtime: ShariaRuntime, intent: OrderIntent) -> GateCheck:
    verdict = runtime.evaluate(intent)
    return GateCheck(
        name="sharia",
        result=GateResult.PASS if verdict.allowed else GateResult.REJECT,
        reason=verdict.reason,
        detail=verdict.detail,
    )

# ... idem pour les autres
```

#### `central_authorizer.py`

```python
class CentralAuthorizer:
    """
    API publique unique pour autoriser un trade.

    Remplace la chaîne distribuée actuelle dans execution_runtime.py
    par un point d'entrée unique auditable.
    """

    def __init__(self, gate_chain: GateChain, audit_logger: AuditLogger) -> None:
        self._chain = gate_chain
        self._audit = audit_logger

    def authorize(self, intent: OrderIntent) -> ExecutionPermit:
        permit = self._chain.evaluate(intent)
        self._audit.log(permit)
        return permit
```

#### Intégration avec `execution_runtime.py`

**Modification minimale** dans `execution_runtime.py` :

```python
# AVANT (distribué)
def execute_intent(intent: OrderIntent) -> ExecutionResult:
    if circuit_breaker.is_tripped():
        return ExecutionResult.rejected("circuit_breaker")
    if not risk_runtime.allow(intent):
        return ExecutionResult.rejected("risk")
    if not sharia.allow(intent):
        return ExecutionResult.rejected("sharia")
    # ... etc
    return execute(intent)

# APRÈS (centralisé)
def execute_intent(intent: OrderIntent) -> ExecutionResult:
    permit = central_authorizer.authorize(intent)
    if not permit.authorized:
        return ExecutionResult.rejected(permit.reject_reason)
    return execute(intent)
```

### Bénéfices

1. **Audit post-mortem trivial** : `permit.checks` contient l'historique complet de la décision
2. **Ajout d'un nouveau check** : 1 ligne dans `gate_definitions.py`, jamais besoin de toucher `execution_runtime.py`
3. **Tests** : on teste la chaîne en isolation, mockable
4. **Métriques** : `permit.checks[i].duration_ms` permet de profiler quel check est lent
5. **Alertes** : sur n trades rejetés consécutifs avec même `rejected_at_check`, alerte pattern (peut-être un bug ou une dérive)

### Risques de cette refacto

| Risque | Mitigation |
|---|---|
| Casser des chemins d'autorisation existants | Tests d'intégration sur tous les chemins existants AVANT et APRÈS |
| Performance dégradée (overhead de la chaîne) | Bench : chaque check < 1 ms, total < 10 ms — négligeable |
| Régression dans `execution_runtime.py` | Conserver les guards en place, juste les **appeler** depuis la chaîne |

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `gate_chain.py` | 150-200 | 0.15 |
| `gate_definitions.py` (registration des 6+ guards) | 150-250 | 0.20 |
| `central_authorizer.py` + `audit_logger` | 100-150 | 0.15 |
| Refacto `execution_runtime.py` | 50-100 | 0.15 |
| Tests intégration (chemins avant/après) | 200-300 | 0.25 |
| **Total** | **650-1000** | **~0.9** |

### Critères d'acceptation

- [ ] Tous les guards V5.3 existants sont enregistrés dans la chaîne
- [ ] Les guards P0/P1 (sharia, fee, regime, pnl breaker) sont enregistrés
- [ ] `execution_runtime.py` n'appelle plus directement les guards individuellement
- [ ] Tests d'intégration : 1026 tests existants ne régressent pas
- [ ] Tests unitaires : chaque check testé en isolation (mock du guard sous-jacent)
- [ ] Audit log immutable : chaque permit persisté avec timestamp et chain version
- [ ] Tableau de bord : nombre de rejets par check sur 24h disponible

---

## V37-3 — Information Stress Monitor (MAS light)

### Pourquoi cette brique

V3.7 propose le **MAS** (Microstructure Anomaly Sentinel) : un détecteur en temps réel d'**anomalies microstructure** qui peut véto une décision de trading même si tous les autres guards sont OK. Le but : détecter quand "le marché ment" — c'est-à-dire quand les prix qu'on observe ne reflètent pas une réalité tradable.

**Cas typiques détectés** :
- Spread anormal (5-10x la médiane) → liquidity black hole
- Volume burst sans nouvelles connues → manipulation possible
- Liquidité divisée (book vide d'un côté) → wash trading possible
- Latence exchange anormale → l'exchange est sous stress
- Désync entre book et trades → flux toxique

V5.3 a `data_backbone/freshness_checker/stale_hard_guard.py` qui couvre une partie (data freshness), mais pas la dimension **anomalie active** du marché.

### Version retenue

**Pas le MAS V3.7 complet** (qui inclut beaucoup de calculs ML). Une version simple et réactive :

```
src/data_backbone/info_stress_monitor/
├── __init__.py
├── contracts.py                    [StressSnapshot, StressLevel]
├── stress_calculator.py            [calcul des indicateurs]
├── stress_veto_provider.py         [API: should_veto(pair) -> bool]
└── tests/
    ├── test_stress_calculator.py
    └── test_veto_logic.py
```

### Spécifications techniques

#### Indicateurs calculés (par pair)

| Indicateur | Source | Seuil veto |
|---|---|---|
| `spread_zscore_60min` | order book stream | > 5 σ |
| `volume_zscore_5min` | trade stream | > 6 σ |
| `book_imbalance_extreme` | order book L5 | < 0.05 ou > 0.95 |
| `latency_p95_ms` | REST/WS health | > 1000 ms |
| `book_trade_desync_ms` | book ts vs trade ts | > 5000 ms |

#### Logique veto

Chaque indicateur en alerte → 1 point. Total > 2 → veto temporaire (bloque nouveaux trades sur cette pair pendant N minutes).

```python
class StressLevel(StrEnum):
    NORMAL = "normal"           # 0 alerte
    ELEVATED = "elevated"       # 1 alerte
    HIGH = "high"               # 2 alertes — warning, pas de veto
    CRITICAL = "critical"       # 3+ alertes — veto temporaire

class StressVetoProvider:
    def __init__(self, calculator: StressCalculator, veto_duration_seconds: int = 600) -> None:
        ...

    def should_veto(self, pair: str) -> StressVetoResult:
        snapshot = self._calculator.snapshot(pair)
        level = self._classify(snapshot)
        if level == StressLevel.CRITICAL:
            self._mark_pair_vetoed(pair, until=time.time() + self._veto_duration)
            return StressVetoResult(veto=True, reason=snapshot.alerts, level=level)
        if self._is_pair_in_veto(pair):
            return StressVetoResult(veto=True, reason="cooldown", level=level)
        return StressVetoResult(veto=False, level=level)
```

#### Intégration

S'enregistre comme un check supplémentaire dans `gate_definitions.py` (V37-2) :

```python
def make_default_chain(...):
    return GateChain([
        ...
        lambda i: _check_info_stress(stress_veto_provider, i),
        ...
    ])
```

### Bénéfices

1. **Protection contre flash crashes** : pendant un flash crash, spread + book imbalance + latence explosent → veto automatique
2. **Protection contre wash trading** : volume burst + book imbalance détectés
3. **Protection contre exchange degradation** : latence + désync détectés → veto avant que l'exchange officialise un incident
4. **Aucun ML, aucun training** : seuils fixes basés sur statistiques rolling

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `stress_calculator.py` | 150-250 | 0.25 |
| `stress_veto_provider.py` | 100-150 | 0.15 |
| Tests + intégration gatekeeper | 50-100 | 0.10 |
| **Total** | **300-500** | **0.5** |

### Critères d'acceptation

- [ ] Calculateur produit un `StressSnapshot` par pair monitorée
- [ ] Veto déclenché à partir de 3 alertes simultanées
- [ ] Cooldown de 10 minutes après veto avant retry
- [ ] Tests : injection de données simulant flash crash → veto vérifié
- [ ] Métriques : nombre de vetos déclenchés / 24h dans le dashboard

---

## Briques V3.7 explicitement REJETÉES

Pour traçabilité, voici les briques V3.7 qu'on ne reprend **pas** et pourquoi.

| Brique V3.7 | Raison du rejet | Reconsidération possible si... |
|---|---|---|
| **OSCAE** (composite scoring 5-dim) | scoring_backbone V5.3 fait déjà ce travail. Réécrire = casser 1026 tests. ROI négatif. | Jamais. Le canon scoring V5.3 est différent et fonctionne. |
| **Strategy Registry + StrategyManifest** | Les 4 engines V5.3 sont les "stratégies de fait", hard-codées. Pas de besoin dynamique. | Si tu scales à 6+ stratégies, à reconsidérer. |
| **Shadow Trading Engine** (entité séparée) | `protocols/shadow_runtime.py` couvre déjà ce besoin sous une forme différente (protocole de promotion système, pas de stratégie). | Jamais — les deux sont orthogonaux. |
| **Pipeline R&D SHG → SQL → SOE** | Surdimensionné. `meta_learning/` couvre l'apprentissage hyperparamètres, suffisant à 10 k$. | Si tu scales et que tu veux un pipeline structuré pour générer/valider de nouvelles stratégies. |
| **StrategyRandomizer** | Anti-RL adverse, pertinent à 1 M$+. À 10 k$ tu n'es pas une cible. | Si tu scales à 100 k$+ et que tu détectes du toxic flow ciblé. |
| **ExploitationDetector** | Idem. | Idem. |
| **Stack Redis + TimescaleDB + Docker Compose** | Coût > 2 % du capital. File-based V5.3 plus appropriée pour single-node 10 k$. | Si tu passes à un cluster multi-node ou >100 k$. |
| **REST API FastAPI** | Aucun client externe. Inutile à 10 k$. | Si tu construis une UI web ou un mobile app. |
| **MAS complet** (avec ML) | Surdimensionné. La version "info stress monitor lite" suffit. | Si tu trades sur 50+ pairs et tu veux du detection ML. |
| **7 régimes (R1-R6 + R∅)** | Surdimensionné. 3 états (CALM/STRESSED/EXTREME) suffisent. | Si tu scales à 100 k$+ et tu veux un alpha matrix par régime. |

---

## Synthèse incorporation V3.7

| Brique | Prio | Sessions Opus |
|---|---|---|
| V37-1 Regime lite (= P1-1) | P1 | 0.5 |
| V37-2 Gatekeeper central | P2 | 0.9 |
| V37-3 Info stress monitor | P2 | 0.5 |
| **Total nouveau** (V37-2 + V37-3) | | **1.4 sessions** |
| **Total avec V37-1 déjà compté en P1** | | **1.4 sessions** (V37-1 est dans P1) |

> **Note importante** : V37-1 ne s'ajoute **pas** au total global parce qu'il est compté dans P1-1. V37-2 et V37-3 sont **nouveaux** et viennent s'ajouter au total global de sessions Opus.

---

## Ordre d'exécution recommandé

```
1. V37-2 (Gatekeeper central) — APRÈS que les P0 et P1 critiques sont en place
   parce qu'il enregistre les guards qui doivent exister
2. V37-3 (Info stress monitor) — peut être fait en parallèle de V37-2 si une autre session est dispo
```

Les briques V3.7 sont **non bloquantes pour MICRO_LIVE** mais **recommandées avant LIVE** pour la qualité d'audit (V37-2) et la robustesse marché (V37-3).

**Suite logique** : `06_BLIND_SPOTS_MULTIDISCIPLINARY.md` — les 12 angles morts.
