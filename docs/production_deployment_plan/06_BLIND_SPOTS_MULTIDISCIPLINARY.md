# Angles morts multidisciplinaires

> **Objectif** — Lister ce qu'un humain seul (toi) ne voit pas naturellement parce qu'il n'a pas simultanément les 5 chapeaux : trader senior, quant PhD, data scientist, dev fintech, conseil halal. Chaque angle mort = un piège qui te coûte de l'argent réel s'il n'est pas adressé avant la phase MICRO_LIVE.

> **Important** — Ce document n'est pas du FUD. Chaque angle est ranké par sévérité (P0 / P1 / P2) et accompagné d'une mitigation concrète chiffrée. Si la mitigation existe déjà dans V5.3, c'est noté.

---

## 1. Méthode

J'ai listé 12 angles morts répartis en 5 perspectives :
- **Trader senior** (4 angles, A1-A4) — réflexes terrain qu'on n'a pas si on n'a jamais perdu d'argent réel
- **Quant PhD** (4 angles, Q1-Q4) — pièges statistiques classiques que la littérature documente
- **Data scientist** (3 angles, D1-D3) — biais de pipeline ML appliqué au trading
- **Dev fintech** (5 angles, F1-F5) — réalités exchange/API/ops oubliées par les devs généralistes
- **Conseil halal** (4 angles, H1-H4) — zones grises charia que `grep halal` ne trouve pas

Chaque angle suit la même structure : **Le piège** → **Pourquoi tu ne le vois pas** → **Conséquence chiffrée** → **Mitigation concrète** → **Statut V5.3**.

---

## 2. Trader senior (A1-A4)

### A1 — La barrière des frais ne se franchit pas par optimisme

**Le piège** — Tu construis une stratégie qui a un edge théorique de 0.15 % par trade. Tu ouvres-fermes une position : 0.10 % maker × 2 = 0.20 % de frais round-trip (Binance Spot taker, sans VIP, sans BNB). Edge net = **−0.05 %**. Tu perds à chaque trade.

**Pourquoi tu ne le vois pas** — En backtest, on raisonne en bps "alpha brut" et on oublie que les fees sont *fixes* alors que l'edge est *probabiliste*. Tu vois 60 % de hit rate avec un edge moyen de 0.30 %, tu te dis "facile" — sauf que les 40 % de losers t'effacent l'avantage et les fees achèvent le compte.

**Conséquence chiffrée** — Sur 10 000 USD avec 5 trades/jour à 200 USD chaque, des fees de 0.20 % round-trip = 2 USD/trade × 5 = **10 USD/jour de drag**. Soit **3650 USD/an = 36.5 % du capital en frais purs**. Pour break-even, ton edge net doit être > 0.20 % par trade, ce qui en vrai veut dire ton edge brut doit être > 0.40 % (avec slippage).

**Mitigation concrète** :
1. **Edge multiplier ≥ 2** : ne pas trader si `expected_edge_bps < 2 × (fee_round_trip_bps + slippage_estimate_bps)`
2. **Maker first** : sur Binance, taker = 0.10 %, maker = 0.10 % aussi par défaut, mais avec **BNB discount** = 0.075 %. Décision à prendre : utiliser BNB pour discount ? (BNB ≠ USDT donc à intégrer dans halal screening)
3. **Trade frequency cap** : pas plus de 3-5 trades/jour totaux toute la flotte. Pas 30.
4. **Min position size** : pas de trade < 100 USD (à 0.20 % round-trip = 0.20 USD de fees, qui doivent être négligeables vs alpha attendu)

**Statut V5.3** — `execution_cost_meter/fee_meter.py` calcule les fees exactes mais **aucun gate `min_edge_after_fees`**. C'est le P0-3 (`03_GAPS_P0.md`).

---

### A2 — Drawdown psychologique > drawdown statistique

**Le piège** — Backtest dit max DD = 8 %. Tu te dis "OK je tolère 8 %". Le système touche 6 % de DD le 3ème jour de live. Tu paniques, tu kill, tu redémarres en mode dégradé, tu fais une bêtise. Le DD réel devient 15 % parce que tu as **toi-même cassé le système**.

**Pourquoi tu ne le vois pas** — En backtest, le DD est une stat passive : tu vois la courbe une fois, tu rationalises. En live, tu vis chaque tick, chaque perte est un événement émotionnel. Le cerveau humain n'est pas câblé pour observer un compte qui descend sans agir.

**Conséquence chiffrée** — Non quantifiable directement, mais **80 % des retail traders auto-sabotent leur edge** en intervenant manuellement après une perte. Tu es retail. Tu n'es pas immunisé.

**Mitigation concrète** :
1. **Pas de monitoring temps réel** : tu ne dois PAS regarder ton équity intraday. Une fois par jour à heure fixe (ex : 09:00 du matin avec ton café). Pas Telegram à chaque trade.
2. **Daily P&L circuit breaker** automatique (P1-3) : si DD intraday > −2 %, le système se met en SHADOW automatiquement et alerte. Tu ne peux pas le réactiver le jour même. Sauvegarde toi de toi-même.
3. **Cooldown post-perte** : après un trade losing, le système suspend les nouveaux trades pendant 30 min. Empêche le revenge trading même algorithmique (clusters de trades dans la même direction après un loser).
4. **Pré-engagement écrit** : tu écris dans un fichier `DECISION_PRE_LIVE.md` les conditions exactes auxquelles tu as le droit de toucher au système une fois en live. Tu te tiens à ces règles.

**Statut V5.3** — Kill switch existe, daily P&L breaker manquant (P1-3). Cooldown post-perte n'existe pas — à ajouter.

---

### A3 — Weekend et fériés US — l'illiquidité que tu n'as jamais ressentie

**Le piège** — Le marché crypto est 24/7. Tu te dis "ça ferme jamais, parfait". Faux. Le **vendredi soir UTC** vers 22:00, et le **dimanche après-midi UTC**, la liquidité s'effondre car les market makers institutionnels US (qui font 60 %+ du volume sur les paires majeures) sont absents. Spreads × 3-5, slippage × 2-4, flash crashes plus fréquents.

**Pourquoi tu ne le vois pas** — En backtest avec données 1m closes, tu vois des prix moyens. Tu ne vois pas la microstructure : profondeur de book, spread bid-ask, latence des updates. Le backtest ment par construction sur la liquidité weekend.

**Conséquence chiffrée** — Un trade exécuté samedi 14:00 UTC sur une mid-cap halal (genre AVAX, SOL) peut subir **10-30 bps de slippage en plus** vs un trade lundi 14:00 UTC. Sur 5 trades de 200 USD le weekend, slippage extra = 1.5-9 USD perdus pour rien.

**Mitigation concrète** :
1. **Halal weekend mode** : suspendre tous les nouveaux trades du **vendredi 22:00 UTC au dimanche 22:00 UTC**. Maintenir uniquement les exits (stops, take-profit). Pas de nouvelles entries.
2. **Black list horaires** : configurable dans `config/trading_hours.yml`, avec option par symbole.
3. **Spread guard** : refuser un trade si `(ask - bid) / mid > 30 bps` (configurable). Le spread élargit = signal de fuir.

**Statut V5.3** — Aucun mécanisme de trading hours. À ajouter en P1 (peut être greffé sur la regime lite : "weekend = STRESSED automatique").

---

### A4 — Position size minimum et "exchange minimums" tueurs

**Le piège** — Binance Spot a un `MIN_NOTIONAL` par symbole (typiquement 5-10 USDT) et un `LOT_SIZE` (step size sur la quantité). À 10 k$ avec 5 positions max, position = 2 k$. Tu veux take-profit 25 % → ordre de 500 USD, ça passe. Mais si tu fais des **partial fills** ou des **exits scalés** (3 niveaux à 33 %), tu te retrouves avec des ordres de 165 USD, et selon le pair tu peux te faire **rejeter par MIN_NOTIONAL** pour les altcoins.

**Pourquoi tu ne le vois pas** — Le code V5.3 (`venue_constraints_provider.py`) connaît théoriquement ces limites mais aucun test ne valide qu'un partial exit scaled est faisable sur tous les pairs cibles à 10 k$.

**Conséquence chiffrée** — Sur les altcoins moins liquides du whitelist halal (DOT, AVAX, ATOM), le `MIN_NOTIONAL` est ~10 USDT, donc OK. Mais le `LOT_SIZE` peut casser un exit : si tu veux vendre 3.7 unités d'un asset à `step_size=0.1`, tu vendras 3.7 (OK), mais si `step_size=1`, tu vendras 3, le reste reste bloqué. Sur 1 année, ça peut bloquer 50-100 USD en "dust" non-liquidable.

**Mitigation concrète** :
1. **Pre-trade simulation** : avant chaque trade, simuler les exits (TP1/TP2/SL) avec les constraints réels du venue. Refuser le trade si un exit est inviable.
2. **Dust auto-cleanup** : tâche hebdomadaire qui détecte les dust < 1 USD par asset et tente une conversion auto (Binance "Convert Small Balances to BNB" → puis BNB → USDT, mais BNB problème halal à clarifier).
3. **Tests d'intégration "min_notional"** : pour chaque symbole du whitelist, vérifier au boot que `position_size_min × price > min_notional × 1.5` (marge de sécurité).

**Statut V5.3** — `venue_constraints_provider.py` existe, l'utilisation effective dans le path d'exécution est à vérifier. Le pre-trade simulation des exits n'existe pas.

---

## 3. Quant PhD (Q1-Q4)

### Q1 — Sample size problem (le tueur silencieux des stratégies retail)

**Le piège** — Tu as 2 ans de données historiques, 5 trades/jour = ~3650 trades total. Sur une stratégie multi-engine avec routage, ces 3650 trades sont splittés en sous-populations : Engine A bull = 400, Engine A bear = 200, Engine B sideways = 600, etc. **Aucune sous-population n'a > 1000 trades**, donc **aucune n'a une significativité statistique acceptable**. Tu calibres sur du bruit.

**Pourquoi tu ne le vois pas** — On regarde la métrique globale (Sharpe global = 1.4, génial !) sans réaliser que le Sharpe global est une moyenne pondérée de 8 sous-stratégies dont 6 sont du bruit. Le Sharpe par sous-stratégie est ininterprétable.

**Conséquence chiffrée** — Variance de l'estimateur Sharpe sur 200 trades ≈ ±0.5 absolu. Donc un Sharpe estimé "1.2" sur 200 trades a un IC95% = [0.2, 2.2]. Tu ne sais pas si tu as une bonne stratégie ou une marche aléatoire.

**Mitigation concrète** :
1. **Pas plus de 2 stratégies actives en MICRO_LIVE** au début. Engine A (trend) et Engine B (mean-reversion) suffisent.
2. **Significativité minimale** : refuser de promouvoir une stratégie en LIVE si N_trades < 500 sur le sous-régime concerné. Un fast-fail explicite si pas atteint.
3. **Bootstrap des metrics** : recalculer Sharpe et max DD via bootstrap (5000 resamples) et reporter l'IC95%, pas la valeur ponctuelle.
4. **Walk-forward** : refuser de croire un backtest qui n'a pas survécu à un walk-forward sur 4-6 windows out-of-sample.

**Statut V5.3** — `meta_learning/` et `validation_runtime/` existent, à vérifier s'ils font du bootstrap ou du walk-forward réel ou juste du holdout single split. **Likely insuffisant** vu les standards retail.

---

### Q2 — Survivorship bias (les morts ne parlent pas)

**Le piège** — Ton univers de trading actuel = top 50 par market cap *aujourd'hui*. Tu backtest sur 2 ans avec ces 50 symboles. Mais en 2024-01, certains de ces symboles n'existaient pas, et certains qui existaient à l'époque ont **disparu** (FTT, LUNA, USTC, etc.). Tu testes uniquement les survivants → ton edge est artificiellement gonflé.

**Pourquoi tu ne le vois pas** — Sourcer les "morts" demande un dataset historique propre avec listings/delistings horodatés. Binance ne fournit pas ça facilement, CoinGecko non plus. Le retail builder utilise ce qu'il a, pas ce qu'il faut.

**Conséquence chiffrée** — Sur backtest crypto 2020-2024, le survivorship bias gonfle le Sharpe de **0.2-0.5** points en moyenne (papier Hougan & Lawant 2023). Ton vrai Sharpe est plus bas que ce que tu vois.

**Mitigation concrète** :
1. **Fixer l'univers à un instant T passé** : choisir le top 50 *au 2024-01-01*, pas *aujourd'hui*. Inclure les morts.
2. **Tracker les delistings** : quand un symbole de l'univers est delisted en backtest, le marquer comme "−100 % loss du jour" même si techniquement la position aurait été récupérée à 0 puis 0.001 puis hors-listing.
3. **Halal compliance dynamique** : un symbole peut devenir non-halal en cours de route (ex : un projet pivote vers funding / DeFi lending). Tracker cette évolution.
4. **Restriction de l'univers réel à du blue chip** : à 10 k$, trader uniquement BTC, ETH, et 5-10 large caps halal-compliant. Le survivorship bias devient marginal sur ces noms-là.

**Statut V5.3** — Univers de trading non audité dans cette session. À vérifier dans S5 ou en pré-phase 0. **Risque P1.**

---

### Q3 — Look-ahead bias via timestamp et lag de données

**Le piège** — Ton feature `volume_5min` calculée à 12:00 utilise les données de 11:55 à 12:00. Mais en réalité, à 12:00:00.000 tu n'as pas encore reçu la dernière barre 11:59 — il y a 200-2000 ms de lag réseau + parsing. Donc en backtest tu utilises de l'info que tu n'as pas en live. Edge backtest > edge live, parfois de manière dramatique sur des features hyper-court-terme.

**Pourquoi tu ne le vois pas** — Le code utilise des timestamps "barre fermée" sans modéliser la latence d'arrivée. C'est un biais systémique invisible si tu ne fais pas de comparaison shadow-vs-backtest sur les MÊMES features avec lag réel.

**Conséquence chiffrée** — Sur features de momentum 5m, le look-ahead par lag réseau gonfle le PnL backtest de **5-15 %** sur des stratégies HF. Sur swing-trade > 1h, l'effet est marginal (< 1 %).

**Mitigation concrète** :
1. **Feature lock contracts** : V5.3 a déjà ce système (`feature_lock_contracts`), à vérifier qu'il enregistre bien le `as_of_timestamp` ET le `arrival_timestamp` pour chaque feature.
2. **Shadow vs backtest delta monitoring** : durant la phase SHADOW, comparer chaque trade signal entre le simulé (sur données historiques) et le live (sur ticks réels). Tout delta > 1 bps moyen = symptôme de look-ahead.
3. **Buffer de sécurité explicite** : forcer toutes les features intra-day à avoir un `min_age_seconds = 1` avant utilisation. Coût : 1 seconde de retard. Bénéfice : plus de look-ahead par lag.

**Statut V5.3** — `feature_lock_contracts/` existe, à auditer pour `arrival_timestamp` tracking. **Probable gap.**

---

### Q4 — Regime dependency (tes engines n'ont jamais vu du vrai bear)

**Le piège** — Si tes données historiques sont 2023-2025, tu n'as jamais entraîné/validé les engines sur du **vrai bear capitulation** (mars 2020 COVID crash, mai 2021 Chine ban, novembre 2022 FTX collapse). Le système peut être bon en sideways/bull et **catastrophique** en capitulation. Tu ne le sauras qu'en perdant 30-50 % en 24h.

**Pourquoi tu ne le vois pas** — Le marché crypto a tendance à oublier vite. 2 ans de bull market efface la mémoire émotionnelle des bears précédents. Le builder amateur sur-fit naturellement au régime récent.

**Conséquence chiffrée** — En mars 2020, BTC a fait −50 % en 24h. Si ton système n'a pas de circuit breaker calibré pour ça, tu peux perdre ton stop loss (gap-down sous le SL), et te retrouver short le marché involontairement (pas en spot heureusement, mais avec une grosse moins-value latente).

**Mitigation concrète** :
1. **Stress test obligatoire** sur les 3 windows de capitulation historiques (mars 2020, mai 2021, novembre 2022). Si max DD > 25 % sur l'une des trois, **pas de promotion en LIVE**. Point.
2. **Regime aware avec circuit breaker à 3 états** (= V37-1 = P1-1) : EXTREME → toutes les positions exit, plus de nouvelles entries pendant 24h.
3. **BTC factor guard** déjà codé dans V5.3 (`risk_backbone/btc_factor_guard/`) : à câbler effectivement en blocking guard, pas juste en monitoring.

**Statut V5.3** — BTC factor guard codé mais pas validé qu'il blocque effectivement. Stress test capitulation historique non documenté. **À ajouter en P1.**

---

## 4. Data scientist (D1-D3)

### D1 — Feature drift silencieux

**Le piège** — Une feature `relative_volume_24h` calibrée sur 2023 (où le volume moyen BTC = 30 B/jour) devient inopérante en 2026 si le volume moyen passe à 60 B/jour. La feature renvoie des valeurs "anormalement basses" en permanence, et la stratégie ne trade plus jamais (ou trade tout le temps, selon le sens).

**Pourquoi tu ne le vois pas** — Une feature qui dérive ne casse rien visiblement : elle continue de produire un nombre. Tu ne vois la conséquence que via la baisse de fréquence de trading ou via un Sharpe live qui dévisse sans raison apparente.

**Conséquence chiffrée** — Sur des features de microstructure (depth ratio, taker imbalance), le drift annuel peut atteindre 30-50 % de la valeur moyenne. C'est énorme.

**Mitigation concrète** :
1. **Feature monitoring** : pour chaque feature critique, calculer la moyenne et l'écart-type sur fenêtre glissante 30j vs fenêtre de référence (calibration). Alerter si |mean_30d - mean_ref| > 2σ.
2. **Recalibration trimestrielle** : rebaseliner les features sur les 90 derniers jours, manuellement, après revue.
3. **Population stability index (PSI)** : standard finance/credit, à utiliser ici aussi. Si PSI > 0.2, drift significatif.

**Statut V5.3** — `meta_learning/` peut faire ça, à vérifier. Probablement absent.

---

### D2 — Outliers et règles `winsorize` cachées

**Le piège** — Un flash crash de −20 % sur une mid-cap en 1 minute génère un return outlier. En backtest, si tu n'as pas wisorisé, cet outlier domine ton calcul de Sharpe et de DD. En live, ce flash arrive parfois et **ton stop loss saute par gap** — tu prends tout le gap.

**Pourquoi tu ne le vois pas** — Backtest et live traitent les outliers différemment : backtest avec un `clip(-0.10, +0.10)` masque le risque réel, live ne masque rien.

**Conséquence chiffrée** — Sur une mid-cap, un gap-down de 5 % au-delà d'un SL est une perte de 5 % de la position en une fraction de seconde. Sur 5 positions de 2 k$, ça fait 100 USD de perte sur 1 trade, soit 1 % du capital sur 1 incident.

**Mitigation concrète** :
1. **Pas de wisorisation cachée** : si tu wisorises en backtest, tu wisorises *exactement pareil* en live (= tu rejettes les ticks avec gap > X comme "spurious"). Sinon backtest et live divergent.
2. **Stop loss "soft"** au lieu de hard : déclencher le SL via *check de la dernière bougie close*, pas via le tick instantané. Évite d'exécuter sur un wick spurious. Coût : un peu plus de slippage en cas de vrai mouvement.
3. **Position sizing conservateur** sur les mid-caps : facteur 0.5 vs blue chips.

**Statut V5.3** — Non audité. À vérifier dans `feature_lock_contracts/` et dans le code des engines.

---

### D3 — Look-ahead par CV mal partitionnée

**Le piège** — Si tu fais du k-fold standard sur une time series, tu mélanges passé et futur : ton modèle est entraîné sur 80 % de données qui incluent du futur par rapport aux 20 % de test. Look-ahead massif. Validation surévaluée de 20-50 %.

**Pourquoi tu ne le vois pas** — `sklearn.model_selection.KFold` ne te crie pas dessus. Tu lances, ça marche, tu fais confiance. Sauf que c'est faux pour de la time series.

**Conséquence chiffrée** — Sur les papers reproduits par Marcos López de Prado, ~70 % des stratégies retail "validées par CV standard" perdent leur edge en walk-forward purgé. **70 %.**

**Mitigation concrète** :
1. **Purged k-fold avec embargo** (López de Prado, *Advances in Financial Machine Learning*) : entre chaque fold train et test, supprimer une fenêtre `embargo_days = max(label_horizon, feature_lookback)`.
2. **Walk-forward** par défaut, pas de k-fold. Et walk-forward **expanding** (pas rolling) pour avoir un échantillon train qui grandit.
3. **Combinatorial Purged CV** pour les évaluations de modèles quand la quantité de données le permet (rare à 2 ans crypto).

**Statut V5.3** — `validation_runtime/` à auditer. Si k-fold standard, c'est rouge.

---

## 5. Dev fintech (F1-F5)

### F1 — Exchange adapter abstrait = bombe à retardement

**Le piège** — `execution_runtime/` est designed contre une interface abstraite. Aucun adapter Binance/Kraken/Coinbase concret n'existe. Tu vas écrire l'adapter en P0-1, et tu vas découvrir 50 cas particuliers Binance que tu ne soupçonnais pas : `MIN_NOTIONAL`, `PRICE_FILTER`, rate limiting par poids, error codes spécifiques (`-2010`, `-1013`, `-1021`), reconnect WebSocket avec snapshot REST, time sync (NTP), idempotency via clientOrderId 36 chars max, etc.

**Pourquoi tu ne le vois pas** — L'abstraction te rassure faussement. "L'interface est définie, donc l'implémentation suivra." En réalité, l'implémentation est où vivent 100 % des bugs de prod.

**Conséquence chiffrée** — Un bug de mauvais arrondi `LOT_SIZE` peut faire échouer 10 % de tes orders → tu rates des entries → ton edge baisse de 10-30 % vs backtest.

**Mitigation concrète** :
1. **2 sessions Opus** consacrées à l'adapter Binance (P0-1) avec **tests intégration sur testnet** Binance avant promotion.
2. **Conformance test suite** : 30+ scénarios qui exercent les error codes Binance documentés (rate limit, insufficient balance, lot size, etc.).
3. **Sandbox first** : déployer l'adapter sur Binance Testnet pendant 1 semaine avant de toucher au mainnet.

**Statut V5.3** — Non commencé. C'est le P0-1, le plus gros chantier.

---

### F2 — WebSocket gap recovery

**Le piège** — Ton WS Binance déconnecte (ça arrive 2-10 fois par jour selon la qualité réseau VPS). Tu reconnectes. **Mais tu as raté X messages pendant la déconnexion.** Si tu ne fais pas de **REST replay** pour combler le gap, tu as un trou dans ta vue marché et tu peux trader sur de la donnée stale.

**Pourquoi tu ne le vois pas** — Le code "ça marche" la plupart du temps, donc tu présumes que la reconnect WS suffit. Faux. Il faut un protocole : "à la reconnexion, snapshot REST + replay des deltas manqués via depth update."

**Conséquence chiffrée** — Trades sur orderbook stale = entries à des prix qui n'existent plus → slippage massif (50-200 bps), risk de fill partial à des prix défavorables.

**Mitigation concrète** :
1. **Reconnect protocol Binance officiel** : voir docs Binance "How to manage a local order book". Snapshot REST `/depth?limit=1000`, puis WS `depth@100ms`, puis appliquer les updates dont `U <= snapshot.lastUpdateId + 1 <= u`.
2. **Gap detector** : si gap > 5 secondes, refuser tout nouveau trade jusqu'à resynchronisation.
3. **Heartbeat monitoring** : si WS silent > 30s, force reconnect.

**Statut V5.3** — `data_backbone/freshness_checker/` existe (côté freshness), mais le WS adapter n'existe pas (P0-1).

---

### F3 — Idempotency : commande envoyée 2 fois

**Le piège** — Tu envoies un order, tu n'as pas la réponse (timeout réseau), tu retry. **L'order a été reçu et exécuté 2 fois.** Tu as 2× la position attendue. Si tu n'as pas un `clientOrderId` unique par tentative logique (pas par tentative réseau), c'est garanti d'arriver.

**Pourquoi tu ne le vois pas** — Les bibliothèques HTTP genre `requests` retry automatiquement parfois. Tu ne contrôles pas l'idempotency.

**Conséquence chiffrée** — Position double = exposition double = risque double. Si ça arrive sur un trade losing, tu prends 2× la perte. Sur 10 k$, c'est −2 % au lieu de −1 %.

**Mitigation concrète** :
1. **`clientOrderId` déterministe par "intention de trade"** : `f"{strategy_id}_{symbol}_{intent_id}"` où `intent_id` est généré une seule fois par décision logique.
2. **Pas de retry HTTP automatique** : retry explicite contrôlé par le code applicatif après vérif que l'order n'a pas été placé (via REST `/openOrders` query).
3. **Reconciliation post-trade** : `execution_backbone/reconciliation_layer/` doit fire après chaque order envoyé pour vérifier que le state local match l'exchange.

**Statut V5.3** — `reconciliation_layer/` existe ✓. `clientOrderId` strategy à définir dans P0-1.

---

### F4 — State recovery au reboot

**Le piège** — VPS reboot (panne, mise à jour kernel, oom kill). Ton process redémarre. **Tu as oublié quelles positions tu avais.** Tu commences "à zéro", tu prends des décisions sur la base d'un état faux. Tu peux double-buyer une position que tu avais déjà, ou pire, ne jamais sortir d'une position que tu pensais avoir liquidée.

**Pourquoi tu ne le vois pas** — Tu testes en local avec des sessions courtes. Le reboot inattendu n'arrive pas en dev.

**Conséquence chiffrée** — Catastrophique. Une position oubliée qui dévisse pendant 24h sans surveillance = drawdown qui peut excéder le DD max théorique.

**Mitigation concrète** :
1. **`smoke_bootstrap_recovery/` est codé en V5.3** ✓ — vérifier qu'il fait bien :
   - snapshot des positions exchange via REST `/account` au boot
   - reconciliation avec le state local persisté
   - refus de trader si divergence détectée (stuck en `RECOVERY_REQUIRED`)
2. **Force reconciliation au boot** : avant tout trade, query exchange et reconcilier (= P1-2).
3. **Persisted state** : positions, orders open, kill switch state, dernière équity = tout sur disque dans des fichiers atomiques.

**Statut V5.3** — `smoke_bootstrap_recovery/` existe, à vérifier le déclenchement effectif et le couverture du `RECOVERY_REQUIRED` state. **À auditer en S5.**

---

### F5 — Logs confidentiels et leak de credentials

**Le piège** — En debug, tu ajoutes un `logger.info(f"Order params: {order}")` qui sérialize l'order entier. **L'order contient parfois la clé API en header HTTP** (selon comment tu wrap). Ou pire, tu logs une réponse exchange qui contient ton balance complet. Si quelqu'un (ou un outil tiers genre Sentry, Datadog) accède à tes logs, il a tes positions et potentiellement tes clés.

**Pourquoi tu ne le vois pas** — Les loggers sont permissifs par défaut. Le pattern "log everything for debug" est culturel.

**Conséquence chiffrée** — Si tes API keys leak, vol potentiel de 100 % du capital sur l'exchange (même avec withdraw lock, un attaquant peut exécuter des trades pump-and-dump pour drainer via slippage).

**Mitigation concrète** :
1. **Allowlist de logs** : seuls les champs explicitement marqués `safe_to_log = True` dans les pydantic models sont sérialisés.
2. **Sanitization layer** dans le logger : regex sur `api_key`, `secret`, `signature`, `Authorization` → remplacer par `[REDACTED]`.
3. **Logs locaux only** : pas de Sentry, pas de Datadog, pas de cloud logging dans la phase 0-2. Plus tard si nécessaire avec sanitization stricte.
4. **Audit log rotation** : logs archivés gzippés, jamais transmis en clair sur le réseau.

**Statut V5.3** — Non audité. **À ajouter dans P0-1 (sealed secrets) et P1-5 (log rotation).**

---

## 6. Conseil halal (H1-H4)

### H1 — Stablecoins : le débat USDT vs USDC vs DAI

**Le piège** — Tu vas trader contre du stable. Mais quel stable ? **USDT (Tether)** est backed par un mix d'actifs dont **du papier commercial productif d'intérêts** = riba. **USDC** est backed à ~80 % par des **T-Bills US productives d'intérêts** = riba indirect. **DAI** est over-collateralisé avec des positions qui paient un *stability fee* = riba structurel. **PYUSD** est plus récent, similaire à USDC. **Aucun stablecoin majeur n'est 100 % halal selon les juristes les plus stricts.**

**Pourquoi tu ne le vois pas** — On suppose que "le stable est neutre" parce qu'il vaut 1 $. Mais la mécanique sous-jacente est interest-bearing.

**Conséquence chiffrée** — Si tu décides ex-post que USDT est haram, tu dois t'en débarrasser → tu liquides → spread + fees + opportunité ratée. Mieux vaut décider ex-ante.

**Mitigation concrète** :
1. **Décision documentée** dans `DECISIONS_REQUIRED.md` : choisir USDT, USDC, ou autre, avec **justification écrite + référence à une fatwa explicite** (par ex. AAOIFI, Mufti Taqi Usmani, ou Sheikh Joe Bradford pour le contexte crypto US).
2. **Purification policy** : si tu choisis un stablecoin marginalement non-conforme, tu calcules la part d'intérêt indirect attribuable à ton balance et tu la donnes en charity. Mécanisme : `purification_calculator.py` (P0-2).
3. **Minimiser le temps en stable** : ne pas rester > 90 % en stable plus de 24h (ce qui de toute façon n'est pas désirable pour une stratégie active).

**Statut V5.3** — Aucune mention de stablecoin policy. **Décision à prendre AVANT P0-2.**

---

### H2 — Airdrops, forks, dust : revenu non-sollicité

**Le piège** — Tu as 1 ETH. Un projet airdrop te donne 100 tokens X. Tu n'as rien fait pour les obtenir : c'est-à-dire **tu reçois un revenu sans contrepartie commerciale**. Selon plusieurs juristes, un airdrop peut être assimilé à un don si tu ne savais pas qu'il viendrait, ou à une promotion publicitaire (similaire à un cashback). **Statut halal = ambigu.**

**Pourquoi tu ne le vois pas** — Tu ne planifies pas les airdrops. Ils tombent dans ton wallet par surprise. Tu les vois 6 mois après, tu vends pour 50 USD, tu te dis "bonus". Tu ne réalises pas que tu as peut-être pollué ton P&L halal.

**Conséquence chiffrée** — Marginal financièrement (50-200 USD/an typique), mais pollue la pureté du capital.

**Mitigation concrète** :
1. **Airdrop policy explicite** : par défaut, tout token reçu en airdrop est marqué comme "purification candidate" et liquidé en USDT à la prochaine occasion, avec le proceeds donné en charity (purification).
2. **Forks de chains** : pareil. Si BTC fork en BCH, le BCH reçu = purification candidate.
3. **Dust < 1 USD** : ignoré par le système trading (pas tradable de toute façon), audit annuel pour purification.

**Statut V5.3** — Aucune logique. À ajouter dans `sharia_compliance/` (P0-2).

---

### H3 — Funding rates et lending accidentels (le piège Binance)

**Le piège** — Binance propose **automatiquement** des features comme :
- **Binance Earn / Simple Earn** : tes USDT inactives génèrent du yield
- **Binance Margin** : tu peux activer "auto-borrow" sans le savoir
- **Binance Futures** : avec funding rate (riba pure)
- **BNB Vault** : staking auto avec rewards

Si tu actives n'importe laquelle de ces features par mégarde (genre tu cliques sur "Enable Earn" en pensant que c'est un toggle anodin), **tu génères du riba sans t'en rendre compte.**

**Pourquoi tu ne le vois pas** — L'UI Binance est designed pour pousser ces produits. Tu peux activer Simple Earn en 1 clic. Tu peux ne pas savoir que c'est activé.

**Conséquence chiffrée** — Si Earn est activé sur 10 k$ USDT @ 2 % APY = 200 USD/an de revenus interest-bearing → **100 % de ton P&L peut devenir contaminé** si tu n'as pas la rigueur de séparer les sources de revenus.

**Mitigation concrète** :
1. **API key permissions strictes** : créer une API key qui n'a QUE `SPOT TRADING` et `READ`. Pas de `MARGIN`, pas de `FUTURES`, pas de `EARN`, pas de `WITHDRAW`.
2. **Audit hebdomadaire des features actives** : script qui query Binance et alerte si Earn / Margin / Futures sont activés sur le compte.
3. **Read-only du balance avec breakdown** : vérifier que `balance.staking == 0`, `balance.earn == 0`, `balance.margin == 0`. Toute déviation = alerte critique.
4. **Documentation visuelle** : screenshot du compte Binance dans l'état "tout désactivé" comme référence.

**Statut V5.3** — Aucune logique. **Critique. À ajouter dans P0-2.**

---

### H4 — Audit fatwa et accountability

**Le piège** — Tu construis un système "halal" selon ton interprétation personnelle. 5 ans plus tard, un juriste te dit "non, ton X était haram". Ton P&L cumulé est contaminé rétroactivement. Pas de mécanisme d'audit, pas de trace, pas de purification calculée.

**Pourquoi tu ne le vois pas** — La conformité halal est traitée comme un état binaire ("c'est halal ou pas") au lieu d'un processus continu qui inclut traçabilité et purification.

**Conséquence chiffrée** — Spirituelle d'abord (le but du halal). Pratique ensuite : la purification rétroactive sur 5 ans peut représenter des milliers de USD à donner.

**Mitigation concrète** :
1. **Audit log dédié** : `policy_audit_logger.py` (P0-2) loggue chaque décision halal prise par le système avec timestamp, pair, raison de l'autorisation/refus, version de la policy.
2. **Versioning des policies** : `sharia_policy_v1.yml`, `sharia_policy_v2.yml`, etc. Si tu changes d'avis, tu peux re-tracer ce qui a été tradé sous v1.
3. **Référence explicite à une fatwa** : pour chaque règle (whitelist/blacklist), un commentaire avec lien vers la source juridique. Pas de règle "parce que je l'ai décidé".
4. **Revue annuelle** : audit annuel par un tiers (ami juriste, ou consultation payante d'un mufti spécialisé crypto comme Joe Bradford ou Mufti Faraz Adam).

**Statut V5.3** — Inexistant. À construire from scratch en P0-2.

---

## 7. Tableau de synthèse — sévérité × statut V5.3

| # | Angle mort | Sévérité | Statut V5.3 actuel | Mitigation où |
|---|---|---|---|---|
| **A1** | Fees barrier | **P0** | ❌ pas de gate min-edge | P0-3 |
| **A2** | Drawdown psychologique | **P1** | ⚠ kill switch oui, daily breaker non | P1-3 |
| **A3** | Weekend illiquidity | **P1** | ❌ pas de trading hours | P1 (à intégrer regime lite) |
| **A4** | Min position size | **P1** | ⚠ venue_constraints existe, pas câblé | P1 |
| **Q1** | Sample size problem | **P0** | ⚠ validation_runtime existe, à auditer | Phase 0 |
| **Q2** | Survivorship bias | **P1** | ❓ univers non audité | Phase 0 |
| **Q3** | Look-ahead via timestamp | **P1** | ⚠ feature_lock_contracts à valider | Phase 0 / P1 |
| **Q4** | Regime dependency (capitulation) | **P0** | ⚠ btc_factor_guard codé non câblé | P1-1 + stress test |
| **D1** | Feature drift | **P1** | ❓ probable absent | P2 |
| **D2** | Outliers / wisorisation | **P2** | ❓ non audité | Phase 0 |
| **D3** | Look-ahead par CV | **P1** | ❓ validation à auditer | Phase 0 |
| **F1** | Exchange adapter abstrait | **P0** | ❌ inexistant | P0-1 |
| **F2** | WebSocket gap recovery | **P0** | ❌ inexistant | P0-1 |
| **F3** | Idempotency | **P0** | ⚠ reconciliation oui, clientOrderId à définir | P0-1 |
| **F4** | State recovery au reboot | **P1** | ✓ smoke_bootstrap_recovery existe, à valider | P1-2 |
| **F5** | Log leaks credentials | **P0** | ❓ non audité | P0-1 / P1-5 |
| **H1** | Stablecoin policy | **P0** | ❌ inexistant | Décision + P0-2 |
| **H2** | Airdrops / forks / dust | **P1** | ❌ inexistant | P0-2 |
| **H3** | Earn / Margin / Futures accidentels | **P0** | ❌ inexistant | P0-2 |
| **H4** | Audit fatwa | **P1** | ❌ inexistant | P0-2 |

**Comptage par sévérité** :
- P0 : **8 angles morts** (critique pour MICRO_LIVE)
- P1 : **10 angles morts** (à traiter avant LIVE)
- P2 : **2 angles morts** (à traiter en continu après LIVE)

---

## 8. Conclusion opérationnelle

Sur 20 angles morts identifiés :
- **5 sont déjà adressés** par des modules V5.3 codés (kill switch, BTC factor, reconciliation, smoke bootstrap, fee meter — ~25 %)
- **15 sont à compléter** (75 %), dont **8 critiques P0**.

**La bonne nouvelle** : tous les P0 sont adressés par les chantiers `03_GAPS_P0.md` (5 chantiers couvrent 7 des 8 P0). Le P0 manquant — **stress test capitulation historique (Q4)** — est ajouté à la phase 0 du `07_PHASE_PLAN_0_TO_4.md`.

**La moins bonne** : il y a 10 angles P1 qui ne sont **pas couverts par le plan actuel des P1** (`04_GAPS_P1.md`). À intégrer dans le phase plan.

**Suite logique** : `07_PHASE_PLAN_0_TO_4.md` — comment séquencer les chantiers en phases avec critères d'entrée/sortie.
