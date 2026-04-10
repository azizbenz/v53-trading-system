# Risk Register — V5.3 production halal spot 10 k$

> **Objectif** — Lister les risques identifiés, leur probabilité, leur impact, leur mitigation existante (si déjà couverte par V5.3) ou à coder, et le **trigger** qui déclenche une réponse.
>
> **Méthode** — Risques regroupés en 6 catégories : Technique, Marché, Halal, Opérationnel, Sécurité, Juridique. Chaque risque a un identifiant `R<cat>-<num>` pour traçabilité.
>
> **Échelle** : probabilité {Faible / Moyen / Élevé} × impact {Faible / Moyen / Élevé / Catastrophique}. Un risque "Élevé × Catastrophique" est un **kill criterion** : si non mitigé, **pas de Phase 3**.

---

## 1. Catégorie TECHNIQUE (RT)

### RT-1 — Bug d'arrondi LOT_SIZE / MIN_NOTIONAL

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé |
| **Impact** | Moyen |
| **Description** | Un order soumis ne respecte pas les contraintes Binance (`stepSize`, `minNotional`) → rejet exchange → trade raté |
| **Conséquence chiffrée** | Trade raté = perte de l'edge attendu (~5-30 bps de PnL latent) |
| **Mitigation V5.3** | `venue_constraints_provider.py` existe, à câbler dans le pre-trade check |
| **Mitigation à coder** | P0-1 : pre-trade simulation contre les contraintes Binance live |
| **Trigger** | 1 trade rejeté pour cette raison → alerte Telegram + investigation |
| **Test** | Conformance test suite Binance (P0-1) |

### RT-2 — WebSocket gap silencieux

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (2-10 fois/jour réseau VPS standard) |
| **Impact** | Moyen→Élevé (selon timing et durée) |
| **Description** | WS Binance déconnecte, code reconnecte sans gap recovery → état marché stale → trades sur orderbook obsolète |
| **Conséquence chiffrée** | Slippage 50-200 bps, fills à des prix défavorables |
| **Mitigation V5.3** | `data_backbone/freshness_checker/` ✓ pour la freshness, mais le reconnect protocol Binance n'existe pas |
| **Mitigation à coder** | P0-1 : reconnect protocol officiel Binance + gap detector + freshness gate |
| **Trigger** | Gap > 5 secondes → blocage automatique des nouveaux trades + alerte |
| **Test** | Simulation de coupure WS sur testnet pendant 30s → vérifier comportement |

### RT-3 — Process crash / VPS reboot

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-3 fois/an typique) |
| **Impact** | Catastrophique si pas de recovery |
| **Description** | Crash Python (OOM, exception non catchée) ou reboot VPS (kernel update) → état local en RAM perdu → décisions sur état faux au restart |
| **Conséquence chiffrée** | Position oubliée qui dévisse 24h sans surveillance = perte 5-20 % du capital |
| **Mitigation V5.3** | `smoke_bootstrap_recovery/` ✓ + kill switch persistant ✓ + reconciliation_layer ✓ |
| **Mitigation à coder** | P1-2 : forcer reconciliation au boot ET périodique. Vérifier le déclenchement effectif. |
| **Trigger** | Toute restart sans reconciliation OK → kill switch ARMED → refus de trader |
| **Test** | Tuer le process en plein trade → restart → vérifier que la position est récupérée |

### RT-4 — Double-soumission d'ordre (idempotency)

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen |
| **Impact** | Élevé |
| **Description** | Timeout réseau sur l'envoi d'order → retry → l'order a été reçu et exécuté 2 fois |
| **Conséquence chiffrée** | Position double = exposition double = perte ou gain × 2 |
| **Mitigation V5.3** | `reconciliation_layer/` ✓ détecte la divergence ex-post |
| **Mitigation à coder** | P0-1 : `clientOrderId` déterministe par intent, pas de retry HTTP automatique, vérification ex-ante via REST `/openOrders` avant tout retry |
| **Trigger** | Reconciliation détecte position > expected → kill switch + alerte |
| **Test** | Mock latence réseau intentionnelle → vérifier qu'aucun double n'arrive |

### RT-5 — Time sync drift

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (NTP par défaut OK) |
| **Impact** | Élevé si non détecté |
| **Description** | Horloge VPS dérive de > 1 seconde par rapport à Binance → erreur `-1021 Timestamp for this request was 1000ms ahead of the server's time` |
| **Conséquence chiffrée** | 100 % des orders rejetés tant que pas resynchronisé |
| **Mitigation à coder** | P0-1 : `time_sync.py` qui sync sur Binance `/api/v3/time` au boot et toutes les heures |
| **Trigger** | Erreur `-1021` → resync immédiat + retry. Si > 3 erreurs en 5 min → kill switch |
| **Test** | Forcer drift de 5 sec sur clock locale → vérifier auto-resync |

### RT-6 — Rate limiting Binance

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (limites larges pour spot retail) |
| **Impact** | Moyen |
| **Description** | Trop de calls REST → ban temporaire 1-5 min |
| **Conséquence chiffrée** | Décisions et reconciliations bloquées pendant la durée du ban |
| **Mitigation à coder** | P0-1 : rate limiter local avec tracking du `X-MBX-USED-WEIGHT` header, throttle préemptif à 80 % du quota |
| **Trigger** | `X-MBX-USED-WEIGHT > 800/1200` → throttle. `429` reçu → backoff exponentiel |
| **Test** | Stress test 100 calls/sec → vérifier throttle |

---

## 2. Catégorie MARCHÉ (RM)

### RM-1 — Flash crash / capitulation soudaine

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-2 fois/an sur 24 mois historiques) |
| **Impact** | Catastrophique |
| **Description** | Mouvement de marché −20 % en 1h, gap-down sous le SL, exécution à des prix loin du SL prévu |
| **Conséquence chiffrée** | Perte d'une position entière (−2 % du capital) |
| **Mitigation V5.3** | `risk_backbone/btc_factor_guard/` codé mais pas câblé en blocking |
| **Mitigation à coder** | P1-1 : regime lite → état EXTREME → exit toutes positions + plus d'entries 24h. P0-3 : edge multiplier × 2 + spread guard. P1-3 : daily P&L breaker. |
| **Trigger** | BTC −5 % en 1h → état EXTREME automatique. DD intraday > 2 % → SHADOW automatique. |
| **Test** | Replay des 3 windows de capitulation historiques (mars 2020, mai 2021, novembre 2022). Max DD doit rester < 25 %. |

### RM-2 — Stratégie qui drift sans qu'on le voie

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (toutes les stratégies drift à terme) |
| **Impact** | Moyen→Élevé selon vitesse |
| **Description** | Sharpe live qui dévisse silencieusement vs backtest, sans event évident |
| **Conséquence chiffrée** | DD progressif jusqu'à −10/15 % avant qu'on s'en rende compte |
| **Mitigation à coder** | P2 : feature drift monitoring (PSI < 0.2). Recalibration trimestrielle obligatoire. |
| **Trigger** | Sharpe rolling 30j live < 50 % du Sharpe backtest → revue humaine forcée. |
| **Test** | A/B sur fenêtre rolling : backtest reproduit sur les mêmes 30j que le live, comparaison |

### RM-3 — Exchange delisting d'un asset whitelisté

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (1-2 par an sur les majors) |
| **Impact** | Moyen |
| **Description** | Binance annonce delisting de XYZ. Les positions doivent être liquidées avant la deadline. |
| **Conséquence chiffrée** | Slippage forcé 50-500 bps + taxe potentielle |
| **Mitigation à coder** | Polling périodique de la liste des delistings annoncés (`exchangeInfo` + RSS Binance announcements). Auto-blacklist des assets en cours de delisting. |
| **Trigger** | Asset whitelist marqué `delisting_pending` → bloquer entries, déclencher exit progressif |
| **Test** | Mock annonce delisting → vérifier comportement |

### RM-4 — Liquidité weekend / fériés

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (chaque weekend) |
| **Impact** | Moyen |
| **Description** | Spreads × 3-5, slippage × 2-4, flash moves plus fréquents |
| **Conséquence chiffrée** | Slippage moyen +10-30 bps sur les trades weekend |
| **Mitigation à coder** | Trading hours blacklist : pas de nouvelles entries vendredi 22:00 UTC → dimanche 22:00 UTC. Exits seulement. |
| **Trigger** | Heure dans la blacklist → refus d'entry, log `BLACKLIST_HOURS` |
| **Test** | Backtest avec et sans la blacklist → comparer métriques |

---

## 3. Catégorie HALAL (RH)

### RH-1 — Activation accidentelle d'une feature interest-bearing Binance

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (UI Binance pousse activement Earn) |
| **Impact** | Catastrophique (pollue 100 % du P&L) |
| **Description** | Earn / Margin / Futures activé par mégarde → revenus interest-bearing automatiques |
| **Conséquence chiffrée** | 100 % du P&L contaminé tant que pas désactivé |
| **Mitigation à coder** | P0-2 : audit hebdomadaire du compte Binance, vérifier `balance.staking == 0`, `balance.earn == 0`, `balance.margin == 0`. API key sans permissions Margin/Futures/Earn. |
| **Trigger** | Détection d'un balance.earn > 0 → kill switch + alerte CRITICAL |
| **Test** | Activer Simple Earn manuellement → vérifier que l'audit script alerte en < 24h |

### RH-2 — Whitelist asset perd sa conformité

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (mais pas nul, projets pivotent) |
| **Impact** | Moyen |
| **Description** | Un asset whitelisté lance une feature DeFi/lending/staking interest-bearing → devient questionnable |
| **Conséquence chiffrée** | Positions ouvertes sur cet asset deviennent à purifier |
| **Mitigation à coder** | P0-2 : revue trimestrielle de la whitelist + `policy_audit_logger.py` versioning |
| **Trigger** | Annonce projet ou alerte communautaire → revue manuelle |
| **Test** | Mock changement de status → vérifier qu'on peut updater la whitelist sans casser le système |

### RH-3 — Stablecoin conformité ambiguë

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (tous les stables ont des questionnements) |
| **Impact** | Moyen |
| **Description** | USDT, USDC, etc. ont des composantes interest-bearing dans leurs reserves |
| **Conséquence chiffrée** | Part du P&L à purifier (calculable) |
| **Mitigation à coder** | P0-2 : `purification_calculator.py` + décision documentée Phase 0 |
| **Trigger** | Calcul mensuel automatique → output dans le rapport mensuel |
| **Test** | Calcul manuel sur 1 mois de balance → vérifier cohérence |

### RH-4 — Airdrops / forks non sollicités

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-3 par an) |
| **Impact** | Faible (financièrement) mais Élevé (pureté capital) |
| **Description** | Tokens reçus sans contrepartie → statut halal ambigu |
| **Conséquence chiffrée** | 50-200 USD/an typique |
| **Mitigation à coder** | P0-2 : détection automatique des assets reçus non whitelist → marquer `purification_candidate` → liquider → donate |
| **Trigger** | Balance d'un asset non whitelist > 0 → alerte + workflow de purification |
| **Test** | Mock reception d'airdrop → vérifier détection |

---

## 4. Catégorie OPÉRATIONNEL (RO)

### RO-1 — Disque saturé sur VPS

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen sans rotation, Faible avec |
| **Impact** | Élevé (write artefacts/logs échoue → état corrompu) |
| **Description** | Logs et artefacts s'accumulent jusqu'à remplir 160 GB |
| **Conséquence chiffrée** | Pannes silencieuses, écritures partielles, kill switch peut ne pas s'activer |
| **Mitigation à coder** | P1-5 : disk monitor avec alerte à 70 %, log rotation gzip avec retention 90j, snapshots compressés |
| **Trigger** | Free disk < 30 % → alerte. < 10 % → kill switch CRITIQUE. |
| **Test** | Remplir le disque manuellement → vérifier alerte et comportement |

### RO-2 — Humain panique et intervient manuellement

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (humains paniquent) |
| **Impact** | Élevé (auto-sabotage) |
| **Description** | Voir A2 dans `06_BLIND_SPOTS_MULTIDISCIPLINARY.md` |
| **Conséquence chiffrée** | 80 % des retail traders auto-sabotent leur edge |
| **Mitigation à coder** | P1-3 : daily P&L breaker (auto-pause). Cooldown post-perte. **Pré-engagement écrit** par l'humain dans un fichier signé. |
| **Trigger** | Pré-engagement violé → revue post-incident obligatoire |
| **Test** | Pas testable techniquement. Discipline humaine. |

### RO-3 — Agent codeur introduit une régression silencieuse

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (toutes les modifs ont un risque) |
| **Impact** | Moyen→Élevé selon module |
| **Description** | Une tranche code casse un comportement existant qui n'était pas testé |
| **Conséquence chiffrée** | Variable, peut être catastrophique sur execution_backbone |
| **Mitigation à coder** | Tests restent verts (1026+nouveau) après chaque tranche. Audit grep sur les changements. Pas de promotion sans `replay_p0_v1` validé. |
| **Trigger** | Test rouge → rollback immédiat |
| **Test** | CI complète après chaque tranche |

### RO-4 — Calibration obsolète

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (à terme) |
| **Impact** | Moyen→Élevé |
| **Description** | Les seuils calibrés en Phase 0 deviennent inadaptés au régime de marché actuel |
| **Conséquence chiffrée** | Stratégie sur/sous-trade, Sharpe live dévisse |
| **Mitigation à coder** | Recalibration trimestrielle obligatoire via Local IA Lab. Versioning des artefacts (v1, v2, v3...). |
| **Trigger** | Délai > 90 jours depuis dernière calibration → alerte |
| **Test** | Workflow de recalibration testé en Phase 0 |

---

## 5. Catégorie SÉCURITÉ (RS)

### RS-1 — API key Binance compromise

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible avec hygiène, Moyen sans |
| **Impact** | Catastrophique (vol potentiel via pump-and-dump même sans withdraw) |
| **Description** | Clé fuit (logs, repo, machine compromise) → attaquant exécute des trades à perte pour drainer via slippage |
| **Conséquence chiffrée** | Jusqu'à 100 % du capital |
| **Mitigation à coder** | P0-4 : sealed secrets (`age` ou `sops`), pas de clé en clair sur disque. Permissions API restreintes (SPOT TRADING + READ uniquement, pas de WITHDRAW, pas de MARGIN, pas de FUTURES). IP whitelist VPS. Logs sanitization. |
| **Trigger** | Détection d'orders non émis par le système → kill switch immédiat |
| **Test** | Audit grep credentials dans logs et repo |

### RS-2 — VPS compromis (root access)

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible avec hardening |
| **Impact** | Catastrophique |
| **Description** | Attaquant root sur VPS → accès aux secrets sealed (déchiffrables si la clé de session est en RAM) |
| **Conséquence chiffrée** | 100 % du capital |
| **Mitigation à coder** | OS hardening (firewall, fail2ban, SSH key only, pas de password, port custom). Updates automatiques security. Audit logs. |
| **Trigger** | Login SSH non whitelist → alerte CRITICAL |
| **Test** | Audit SSH config + scan ports externe |

### RS-3 — Logs leak credentials

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé sans sanitization |
| **Impact** | Élevé (équivalent à RS-1) |
| **Description** | `logger.info(f"Order: {order}")` sérialise headers HTTP avec API key |
| **Conséquence chiffrée** | Idem RS-1 |
| **Mitigation à coder** | P0-1 / P1-5 : logger sanitization layer (regex sur `api_key`, `secret`, `signature`, `Authorization`). Allowlist de logs sur les pydantic models. |
| **Trigger** | Audit grep périodique sur les logs |
| **Test** | Test unitaire qui force un log et vérifie qu'aucun secret n'apparaît |

---

## 6. Catégorie JURIDIQUE (RJ)

### RJ-1 — Régulation crypto change dans la juridiction de l'humain

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (la régulation crypto évolue vite en Europe avec MiCA) |
| **Impact** | Moyen→Élevé |
| **Description** | Nouvelle obligation déclarative, KYC, ou interdiction de certaines activités |
| **Mitigation** | Veille manuelle. Pause + revue si changement significatif. |
| **Trigger** | Annonce régulateur → revue manuelle |

### RJ-2 — Exchange (Binance) bloque l'accès à la juridiction

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (Binance EU OK pour MiCA-compliant) |
| **Impact** | Élevé (besoin de migrer vers un autre exchange) |
| **Description** | Binance se retire d'un pays → comptes restreints |
| **Mitigation** | Adapter design abstrait (P0-1) permet de switcher vers Kraken si nécessaire. Mais l'effort de migration reste 1-2 sessions code. |
| **Trigger** | Annonce Binance → migration Kraken planifiée |

### RJ-3 — Tax reporting

| Champ | Valeur |
|---|---|
| **Probabilité** | Certain (chaque année) |
| **Impact** | Moyen (temps + coût expert-comptable) |
| **Description** | Déclaration des plus-values crypto annuelle |
| **Mitigation à coder** | Export CSV trades + P&L par fiscal year (à décider en Phase 0 si on l'inclut ou pas). Si non inclus : export manuel via Binance interface annuelle. |

---

## 7. Tableau de synthèse — risques par catégorie et sévérité

| ID | Risque | Proba | Impact | Mitigation où | Statut |
|---|---|---|---|---|---|
| **RT-1** | Bug LOT_SIZE | E | M | P0-1 | À coder |
| **RT-2** | WS gap silencieux | E | M-E | P0-1 | À coder |
| **RT-3** | Process crash | M | **CAT** | P1-2 + V5.3 ✓ | À valider |
| **RT-4** | Double-soumission | M | E | P0-1 + V5.3 ✓ | À coder |
| **RT-5** | Time sync drift | F | E | P0-1 | À coder |
| **RT-6** | Rate limit Binance | F | M | P0-1 | À coder |
| **RM-1** | Flash crash | M | **CAT** | P1-1 + P0-3 + P1-3 + V5.3 ✓ | À coder + valider |
| **RM-2** | Stratégie drift | E | M-E | P2 | À coder plus tard |
| **RM-3** | Asset delisted | F | M | P0-2 (auto-blacklist) | À coder |
| **RM-4** | Liquidité weekend | E | M | P1 (trading hours) | À coder |
| **RH-1** | Earn activé par mégarde | M | **CAT** | P0-2 | À coder |
| **RH-2** | Whitelist drift halal | F | M | P0-2 + revue trim. | À coder |
| **RH-3** | Stablecoin ambiguïté | E | M | P0-2 + décision Phase 0 | À décider |
| **RH-4** | Airdrops non sollicités | M | F-M | P0-2 | À coder |
| **RO-1** | Disk saturé | M | E | P1-5 | À coder |
| **RO-2** | Humain panique | E | E | P1-3 + pré-engagement | À coder + discipline |
| **RO-3** | Régression code | M | M-E | Tests verts + replay validé | Process |
| **RO-4** | Calibration obsolète | E | M-E | Recalibration trimestrielle | Process |
| **RS-1** | API key compromise | F-M | **CAT** | P0-4 + permissions strictes | À coder |
| **RS-2** | VPS compromis root | F | **CAT** | OS hardening | Setup VPS |
| **RS-3** | Logs leak credentials | E | E | P0-1 + P1-5 sanitization | À coder |
| **RJ-1** | Régulation change | M | M-E | Veille manuelle | Process |
| **RJ-2** | Binance bloque juridiction | F | E | Adapter design abstrait | OK |
| **RJ-3** | Tax reporting | Certain | M | Export CSV ou manuel | À décider |

**Comptage** :
- **5 risques Catastrophique** (RT-3, RM-1, RH-1, RS-1, RS-2) → **tous bloquants** pour Phase 3
- **8 risques Élevé**
- **9 risques Moyen**
- **2 risques Faible**

**Tous les Catastrophique sont mitigés par les chantiers P0/P1.** Aucun n'est laissé sans mitigation. C'est la condition non-négociable pour passer en MICRO_LIVE.

---

## 8. Triggers globaux qui forcent une régression de phase

| Trigger | Action automatique | Action humaine |
|---|---|---|
| Drawdown live > 5 % en 1 jour | Daily P&L breaker → SHADOW automatique | Investigation 24h |
| Drawdown live > 10 % en 1 semaine | Kill switch ARMED | Retour Phase 2 SHADOW |
| Drawdown live > 15 % cumulé | Kill switch CRITICAL | Retour Phase 1 + revue complète |
| Reconciliation divergence critique | Kill switch | Investigation immédiate |
| Halal violation détectée | Kill switch + alerte CRITICAL | Audit policy + purification |
| API key suspecte (orders non émis) | Kill switch + révocation clé | Recréation environnement |
| 3 incidents techniques en 7 jours | Kill switch | Revue stabilité + retour Phase 2 |
| Sharpe rolling 30j < 0 (deux mois consécutifs) | Aucune (pas auto) | Recalibration + revue |
| Free disk < 10 % | Kill switch + alerte | Cleanup |

---

**Suite logique** : `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` — découpage des tranches de code pour l'agent codeur.
