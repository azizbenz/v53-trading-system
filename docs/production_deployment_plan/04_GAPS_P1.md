# Gaps P1 — Manques bloquants pour scaler au-delà de MICRO_LIVE

> **Définition P1** : sans cette brique, la phase MICRO_LIVE peut tourner (capital ≤5 % du target = 500 USD), mais **pas LIVE** (capital cible 10 000 USD).
> Ces 5 manques doivent être tous comblés avant la fin de la phase MICRO_LIVE et avant le passage en LIVE.

---

## Vue d'ensemble

> **Rappel gabarit MD Opus** (`00_README.md` § 0) : chaque chantier P1 ci-dessous devrait, au moment de sa prise en charge par l'agent codeur, être vérifié contre le gabarit standardisé (objectif / périmètre / invariants / modules / interfaces / ce qu'il ne faut pas faire / critères d'acceptation / ordre / preuves). Le repo gagne contre le MD.

| # | Manque | Sévérité | LOC estimées | Tranches code (agent codeur) |
|---|---|---|---|---|
| P1-1 | Regime awareness lite (3 états) | Élevé | 400-600 | T9 |
| P1-2 | Reconciliation périodique + au boot | Élevé | 200-300 | T10 |
| P1-3 | Daily P&L circuit breaker câblé | Élevé | 100-200 | T10 |
| P1-4 | Alerting externe (Telegram/email) | Élevé | 200-300 | T11 |
| P1-5 | Disk monitor + log rotation | Moyen | 150-250 | T11 |

**Total P1** : ~1050-1650 LOC, **~3 tranches code** (T9, T10, T11 — voir `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md`).

---

## P1-1 — Regime awareness lite (3 états)

### Pourquoi P1

V5.3 utilise actuellement "regime" comme un **simple tag string** passé en entrée aux engines (`engine_inputs.regime`). Aucun composant ne **détecte** le régime de marché. Les engines tournent identiquement en bull, range, capitulation.

**Conséquence quant** : la majorité des stratégies retail crypto ont une perf qui dépend du régime. Une stratégie qui fait +60 % en bull peut faire -40 % en bear. Sans détection de régime, **tu vas livrer de la perf 6 mois puis tout perdre quand le régime change**.

V3.7 a un `RegimeDetector` à 7 états (R1-R6 + R∅). C'est trop granulaire pour 10 k$. Une version **lite à 3 états** suffit largement.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Stratégie qui marche en bull, meurt en bear | -30 à -50 % de drawdown sur changement de régime |
| Pas de désactivation conditionnelle d'engines | Décisions à contre-régime |
| Surface d'alpha non maximisée | Sharpe sous-optimal |

### Localisation cible

```
src/data_backbone/regime_lite/
├── __init__.py
├── contracts.py                    [RegimeState enum + RegimeSnapshot]
├── regime_calculator.py            [calcul des indicateurs et vote final]
├── regime_provider.py              [API publique consommée par les engines]
└── tests/
    ├── test_regime_calculator.py
    └── test_regime_transitions.py
```

### Spécifications techniques

#### États

```python
class RegimeState(StrEnum):
    CALM = "calm"           # vol modérée, spreads tight, range
    STRESSED = "stressed"   # vol élevée, spreads wide, mouvements directionnels
    EXTREME = "extreme"     # capitulation, flash crash, ou euphorie blow-off
```

3 états seulement. Critères :
- **CALM** : vol réalisée 24h BTC < 30 % annualisée, spread médian < 5 bps, drawdown 7j > -5 %
- **STRESSED** : vol réalisée 24h BTC entre 30 % et 80 %, ou spread médian entre 5 et 15 bps, ou DD 7j entre -5 et -15 %
- **EXTREME** : vol > 80 %, ou spread > 15 bps, ou DD 7j < -15 %, ou move > 8 σ en 1h

#### Sources des indicateurs

Pour rester pragmatique : utiliser uniquement les données BTC (proxy macro crypto).
- Vol réalisée 24h BTC : depuis `data_backbone/`
- Spread médian BTC/USDT : depuis order book stream
- Drawdown 7j BTC : compute interne sur klines

**Pas de dépendance externe** (pas de VIX, pas de news feed).

#### Calcul

```python
def calculate_regime(snapshot: MarketSnapshot) -> RegimeSnapshot:
    vol_24h = snapshot.btc_realized_vol_24h_annualized
    spread_med = snapshot.btc_spread_median_bps
    dd_7d = snapshot.btc_drawdown_7d_pct
    move_1h_sigma = snapshot.btc_move_1h_in_sigmas

    if (vol_24h > 0.80
        or spread_med > 15
        or dd_7d < -0.15
        or abs(move_1h_sigma) > 8):
        state = RegimeState.EXTREME
    elif (vol_24h > 0.30
          or spread_med > 5
          or dd_7d < -0.05):
        state = RegimeState.STRESSED
    else:
        state = RegimeState.CALM

    return RegimeSnapshot(
        state=state,
        timestamp=now(),
        vol_24h=vol_24h,
        spread_median_bps=spread_med,
        drawdown_7d=dd_7d,
        move_1h_sigma=move_1h_sigma,
    )
```

#### Hystérésis

**Important** : pour éviter les bascules rapides entre régimes (qui flapperaient les engines), implémenter une **hystérésis temporelle** :
- Pour passer de CALM → STRESSED, condition vraie pendant 15 min consécutives
- Pour passer de STRESSED → CALM, condition vraie pendant 60 min consécutives
- EXTREME est instantané dans les deux sens (sécurité)

#### Intégration avec les engines

Les engines V5.3 acceptent déjà un `regime` string en input. **Aucune modification des engines nécessaire**, juste alimenter ce champ depuis `regime_provider`.

Ajouter dans `protocols/{shadow,micro_live,live_light}_runtime.py` :
```python
regime = regime_provider.get_current_regime()
engine_input = EngineInput(..., regime=regime.state.value)
```

#### Désactivation conditionnelle d'engines

C'est le **vrai bénéfice** du régime : permettre à chaque engine de déclarer dans quels régimes il est actif.

Ajouter une config :
```python
ENGINE_REGIME_GATING = {
    "engine_a": ["calm", "stressed"],          # désactivé en EXTREME
    "engine_b": ["calm"],                      # actif en CALM uniquement
    "engine_c": ["stressed", "extreme"],       # actif en mode mouvant
    "engine_d": ["calm", "stressed", "extreme"],  # always-on
}
```

Le gating se fait dans `portfolio_minimal/opportunity_selector/candidate_pool_builder.py` (ou équivalent) : si engine X propose une opportunité dans un régime non autorisé → reject avec raison `REGIME_GATED`.

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `regime_calculator.py` + tests | 250-350 | 0.25 |
| `regime_provider.py` (API + cache + hystérésis) | 100-150 | 0.1 |
| Intégration engines + config gating | 50-100 | 0.1 |
| Tests transitions et hystérésis | 100-150 | 0.05 |
| **Total** | **400-600** | **0.5** |

### Critères d'acceptation

- [ ] Calculateur passe par les 3 états sur données historiques de référence (2020-03 = EXTREME, 2021-Q3 = CALM, 2022-05 = STRESSED, etc.)
- [ ] Hystérésis vérifiée : flapping bloqué
- [ ] Gating désactive les engines dans les régimes non autorisés
- [ ] Tests : 100 % couverture du `calculate_regime`
- [ ] Régime exposé dans le dashboard `monitoring/`
- [ ] Régime persisté dans les artifacts pour audit post-mortem

---

## P1-2 — Reconciliation périodique + au boot

### Pourquoi P1

V5.3 a une `reconciliation_layer/` complète (5 modules) mais **il faut vérifier qu'elle est appelée** :
1. **Au boot** du process (obligatoire avant tout trade)
2. **Périodiquement** pendant le runtime (toutes les 5-10 min)

Si la reconciliation n'est qu'**event-driven** (déclenchée par une discordance détectée par autre moyen), il y a un trou : un drift silencieux peut s'accumuler.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Drift silencieux entre état local et exchange | Décisions sur fausse base, pertes |
| Crash récupéré sans reconciliation | Re-trade d'ordres déjà soumis |
| Position fantôme (ouverte côté exchange, fermée côté local) | Risque non géré |

### Localisation cible

Modification de `src/protocols/{shadow,micro_live,live_light}_runtime.py` pour ajouter :
1. Hook au démarrage qui invoque `reconciliation_layer/recovery_trigger.py`
2. Scheduler périodique (asyncio.create_task ou apscheduler) pour reconciliation toutes les N minutes

Ou nouveau module :
```
src/protocols/reconciliation_scheduler.py
```

### Spécifications

```python
class ReconciliationScheduler:
    def __init__(
        self,
        recovery_trigger: RecoveryTrigger,
        circuit_breaker: EmergencyCircuitBreaker,
        period_seconds: int = 300,  # 5 min
    ) -> None:
        ...

    async def boot_reconcile(self) -> ReconciliationResult:
        """Au démarrage. Bloquant. Refuse de continuer si divergence non résolue."""
        result = await self.recovery_trigger.full_recovery()
        if result.has_unresolved_divergences():
            self.circuit_breaker.trip(
                reason=KillSwitchReason.CRITICAL_DIVERGENCE,
                detail=f"boot reconciliation failed: {result.divergences}",
            )
        return result

    async def periodic_reconcile_loop(self) -> None:
        """Tourne en arrière-plan. Trip kill switch sur divergence critique."""
        while True:
            await asyncio.sleep(self.period_seconds)
            result = await self.recovery_trigger.full_recovery()
            if result.has_critical_divergences():
                self.circuit_breaker.trip(...)
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `reconciliation_scheduler.py` + tests | 200-300 | 0.25 |

### Critères d'acceptation

- [ ] Boot reconciliation obligatoire avant tout trade
- [ ] Période configurable (default 300 s)
- [ ] Trip kill switch sur divergence critique non résolue
- [ ] Tests : simulation de divergence → trip vérifié
- [ ] Logs structurés avec types de divergence

---

## P1-3 — Daily P&L circuit breaker câblé

### Pourquoi P1

`risk_backbone/loss_budgeter/drawdown_guard.py` existe mais à **vérifier** s'il déclenche automatiquement le `circuit_breaker.py`. Si c'est juste un module de reporting, il faut le câbler pour qu'il **trip le kill switch** automatiquement à des seuils prédéfinis.

### Seuils recommandés à 10 k$

| Seuil | Action |
|---|---|
| DD intraday > -2 % (200 USD) | Warning, alerte Telegram |
| DD intraday > -3 % (300 USD) | Halt nouveaux trades, attente fermeture positions |
| DD intraday > -5 % (500 USD) | Trip kill switch, fermeture forcée si possible |
| DD 7j > -10 % (1000 USD) | Trip kill switch, review humaine obligatoire avant restart |
| DD 30j > -15 % (1500 USD) | Trip kill switch + review du système entier |

Ces seuils sont **conservateurs**. À 10 k$ tu n'as pas le luxe de risque-tolérance "VC-style".

### Risque si pas fait

| Risque | Impact |
|---|---|
| Drawdown non borné | Perte > seuil tolérable, panique humaine |
| Pas de halt automatique | Le système continue de creuser |
| Recovery sans review | Restart immédiat sur même bug |

### Localisation cible

Modification ou ajout dans :
```
src/risk_backbone/loss_budgeter/
└── pnl_circuit_breaker_wiring.py    [nouveau ou ajout dans drawdown_guard]
```

### Spécifications

```python
class PnLCircuitBreakerWiring:
    """
    Surveille le P&L courant et trip le circuit breaker à seuils.

    Appelé après chaque fill (event-driven) et périodiquement (sécurité).
    """

    INTRADAY_WARNING = -0.02     # -2 %
    INTRADAY_HALT = -0.03        # -3 %
    INTRADAY_KILL = -0.05        # -5 %
    WEEK_KILL = -0.10            # -10 %
    MONTH_KILL = -0.15           # -15 %

    def __init__(
        self,
        circuit_breaker: EmergencyCircuitBreaker,
        alert_manager: AlertManager,
        pnl_provider: PnLProvider,
    ) -> None: ...

    def check(self) -> PnLCheckResult:
        intraday = self.pnl_provider.get_intraday_pnl_pct()
        week = self.pnl_provider.get_rolling_pnl_pct(days=7)
        month = self.pnl_provider.get_rolling_pnl_pct(days=30)

        if intraday < self.INTRADAY_KILL:
            self.circuit_breaker.trip(
                reason=KillSwitchReason.LOSS_BUDGET_BREACH,
                detail=f"intraday DD {intraday:.2%} < {self.INTRADAY_KILL:.2%}",
            )
            return PnLCheckResult(action="KILL", level="intraday")

        if week < self.WEEK_KILL:
            self.circuit_breaker.trip(...)
            return PnLCheckResult(action="KILL", level="week")

        if month < self.MONTH_KILL:
            self.circuit_breaker.trip(...)
            return PnLCheckResult(action="KILL", level="month")

        if intraday < self.INTRADAY_HALT:
            # halt nouveau trades sans tripper full kill
            return PnLCheckResult(action="HALT_NEW_TRADES", level="intraday")

        if intraday < self.INTRADAY_WARNING:
            self.alert_manager.send(
                level="WARNING",
                message=f"Intraday DD at {intraday:.2%}",
            )
            return PnLCheckResult(action="WARN", level="intraday")

        return PnLCheckResult(action="OK")
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| Wiring + tests | 100-200 | 0.25 |

### Critères d'acceptation

- [ ] Trip kill switch effectif aux seuils définis
- [ ] HALT bloque nouveaux trades sans fermer les existants
- [ ] Alertes Telegram envoyées aux warnings
- [ ] Tests : simulation de chaque seuil, action vérifiée
- [ ] Reset manuel obligatoire après trip

---

## P1-4 — Alerting externe (Telegram/email)

### Pourquoi P1

`alert_manager.py` existe dans `monitoring/` mais à **vérifier** où il sort. Sans push externe, tu **ne sais pas** quand le système trip. Tu pourrais découvrir 12h plus tard que le kill switch a été activé pendant une réunion.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trip kill switch non détecté | Système halt, opportunité ratée OU bug non investigué |
| Crash VPS non détecté | Système down silencieusement |
| Drawdown progressif sans alerte | Pas de signal humain pour décision |

### Solution recommandée

**Telegram bot personnel** — gratuit, simple, push instantané sur smartphone.

Alternative : webhook Discord, ou ntfy.sh pour minimalisme.

**À éviter** : email (latence, spam folder), SMS (coût, complexité).

### Localisation cible

```
src/monitoring/alerters/
├── __init__.py
├── telegram_alerter.py
├── alerter_contracts.py
└── tests/
    └── test_telegram_alerter.py
```

Wire dans `alert_manager.py` existant.

### Spécifications

```python
class TelegramAlerter:
    """
    Push alerts to a personal Telegram bot.

    Pas de réponse, pas d'interaction. Send-only.
    Token et chat_id chargés via credential_loader (sealed secrets).
    """

    def __init__(self, bot_token: str, chat_id: str) -> None: ...

    def send(self, level: AlertLevel, message: str, context: dict = None) -> bool:
        """
        AlertLevel: INFO, WARNING, ERROR, CRITICAL.
        CRITICAL également envoie un sound notification.
        """
        formatted = self._format(level, message, context)
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": formatted,
                    "parse_mode": "Markdown",
                    "disable_notification": level not in (AlertLevel.ERROR, AlertLevel.CRITICAL),
                },
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            # FALLBACK: log local mais ne pas crasher
            logger.error(f"Telegram alert failed: {e}")
            return False
```

### Événements à alerter

| Event | Niveau |
|---|---|
| Boot OK | INFO |
| Boot KO (reconciliation failed, etc.) | CRITICAL |
| Kill switch trip | CRITICAL |
| Trade executed | INFO (configurable, peut être désactivé) |
| Trade rejected (sharia, fee gate, etc.) | INFO |
| Drawdown warning | WARNING |
| Drawdown halt | ERROR |
| Drawdown kill | CRITICAL |
| Reconciliation divergence détectée | ERROR |
| Reconciliation divergence non résolue | CRITICAL |
| Disk > 80 % | WARNING |
| Disk > 95 % | CRITICAL |
| Connectivity lost (WS/REST) > 5 min | ERROR |

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `telegram_alerter.py` + tests | 150-200 | 0.15 |
| Wiring dans `alert_manager.py` + 13 events | 50-100 | 0.10 |
| **Total** | **200-300** | **0.25** |

### Critères d'acceptation

- [ ] Bot Telegram configuré, message de boot reçu
- [ ] Tous les événements de la liste émettent une alerte
- [ ] Si Telegram down → log local + retry sur les events critiques
- [ ] Token + chat_id stockés via `credential_loader` (jamais en clair)
- [ ] Tests : mock du endpoint Telegram, vérification format Markdown

---

## P1-5 — Disk monitor + log rotation

### Pourquoi P1

V5.3 est file-based : artifacts + logs s'accumulent. Sur un VPS avec disque limité (typique 25-50 GB), **le disque va se remplir**. Sans monitoring + rotation, le système crashera silencieusement quand il n'y aura plus d'espace pour écrire un artifact.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Disque plein → écriture artifact échoue | Crash, halte trading silencieuse |
| Logs non rotatés → fichier de plusieurs GB | Lecture impossible, espace gaspillé |
| Pas d'alerte préventive | Pas de fenêtre pour intervenir |

### Localisation cible

```
src/monitoring/
├── disk_monitor.py            [nouveau]
└── log_rotation_config.py     [nouveau ou config externe]

ops/
└── logrotate.conf             [config système si logs externes]
```

### Spécifications

#### `disk_monitor.py`

```python
class DiskMonitor:
    """
    Surveille l'usage disque et alerte / trip à seuils.
    """

    def __init__(
        self,
        paths_to_monitor: list[Path],
        alert_manager: AlertManager,
        circuit_breaker: EmergencyCircuitBreaker,
        warning_pct: float = 0.80,
        critical_pct: float = 0.95,
        check_interval_seconds: int = 300,
    ) -> None: ...

    def check_now(self) -> DiskUsageReport:
        for path in self.paths_to_monitor:
            usage = shutil.disk_usage(path)
            pct = usage.used / usage.total
            if pct > self.critical_pct:
                self.circuit_breaker.trip(
                    reason=KillSwitchReason.DATA_CORRUPTION,
                    detail=f"Disk {path} at {pct:.1%}",
                )
                self.alert_manager.send(AlertLevel.CRITICAL, ...)
            elif pct > self.warning_pct:
                self.alert_manager.send(AlertLevel.WARNING, ...)
        ...
```

#### Log rotation

Deux options :

**Option A — Python `RotatingFileHandler`** (intégré)
- Configuration dans le logger global
- Rotation par taille (ex: 100 MB par fichier, 10 fichiers max)
- Compression gzip des anciens fichiers

**Option B — `logrotate` système** (Linux)
- Config dans `/etc/logrotate.d/v53_trading.conf`
- Rotation quotidienne, retention 30 jours, compression
- Plus standard sur VPS Linux

**Recommandation** : Option A en interne, Option B en complément si logs vers fichier système.

#### Artifact TTL

Les artifacts produits par V5.3 vont s'accumuler. Ajouter un module de cleanup :
```python
class ArtifactRetentionManager:
    """
    Supprime les artifacts plus anciens que N jours.
    Conserve les artifacts marqués `keep_forever`.
    """

    def cleanup(self, retention_days: int = 90) -> CleanupReport:
        ...
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `disk_monitor.py` + tests | 100-150 | 0.15 |
| Log rotation config (Python ou system) | 50-100 | 0.05 |
| `ArtifactRetentionManager` + tests | — | 0.05 (couvert dans P2 si différé) |
| **Total** | **150-250** | **0.25** |

### Critères d'acceptation

- [ ] Disk monitor tourne en background
- [ ] Warning à 80 %, critical + kill à 95 %
- [ ] Logs rotatés automatiquement
- [ ] Tests : simulation disk full → trip vérifié

---

## Synthèse P1

| Chantier | LOC | Sessions |
|---|---|---|
| P1-1 Regime lite | 400-600 | 0.5 |
| P1-2 Reconciliation périodique | 200-300 | 0.25 |
| P1-3 Daily P&L circuit breaker | 100-200 | 0.25 |
| P1-4 Telegram alerting | 200-300 | 0.25 |
| P1-5 Disk monitor + log rotation | 150-250 | 0.25 |
| **Total P1** | **1050-1650** | **1.5 sessions** |

---

## Ordre d'exécution recommandé

**Tous les P1 sont indépendants entre eux**, l'ordre est libre. Suggestion :

```
1. P1-2 (Reconciliation) — fondation safety
2. P1-3 (P&L circuit breaker) — câble drawdown_guard sur kill switch existant
3. P1-4 (Telegram alerting) — visibilité externe
4. P1-5 (Disk monitor) — sécurité long-running
5. P1-1 (Regime lite) — alpha enabler, le plus créatif et le plus volumineux
```

**Suite logique** : `05_V37_BRICKS_INCORPORATION.md` — les 3 briques V3.7 retenues.
