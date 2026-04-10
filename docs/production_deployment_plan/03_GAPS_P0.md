# Gaps P0 — Manques bloquants avant tout live trade

> **Définition P0** : sans cette brique, **aucun trade live n'est acceptable**. P0 = "no-go" absolu.
> Ces 5 manques doivent être tous comblés avant la phase MICRO_LIVE (ordre réel le plus petit).

> **Gabarit MD attendu pour chaque chantier ci-dessous** (rappel `00_README.md` § 0) :
> 1. Objectif — 2. Périmètre — 3. Invariants — 4. Modules touchés — 5. Interfaces I/O — 6. Ce qu'il ne faut PAS faire — 7. Critères d'acceptation — 8. Ordre de réalisation — 9. Preuves / tests attendus.
> Les sections ci-dessous fournissent le contenu utile pour ces 9 points. L'agent codeur Sonnet doit s'aligner sur ce gabarit avant chaque tranche.

> **Seuils dynamiques** (rappel) — Aucun seuil P0 ne doit être hardcodé. Chaque seuil candidat est listé dans `11_DYNAMIC_THRESHOLDS_CATALOG.md` avec sa source de calibration (artefact backtest) et son protocole de validation shadow.

---

## Vue d'ensemble

| # | Manque | Sévérité | LOC estimées | Tranches code (agent codeur) |
|---|---|---|---|---|
| P0-1 | Exchange adapter Binance Spot production-grade | **Critique** | 2500-4000 | 3-4 |
| P0-2 | Halal compliance layer | **Critique** | 800-1200 | 1-2 |
| P0-3 | Fee-aware minimum-edge filter | **Critique** | 150-300 | 0.5 |
| P0-4 | Sealed secrets / API key loader | **Critique** | 200-400 | 0.5 |
| P0-5 | Engine C / D rattrapage tests + audit | **Élevé** | 600-1500 | 1-3 |

**Total P0** : ~4250-7400 LOC, **6-10 tranches** pour l'agent codeur. Voir `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` pour le détail.

---

## P0-1 — Exchange adapter Binance Spot production-grade

### Pourquoi P0

Sans connecteur exchange concret, le système ne peut **littéralement pas** soumettre d'ordres réels. L'`execution_runtime.py` actuel semble abstrait (à confirmer S5a). Même s'il y a un stub, il n'a probablement pas la robustesse nécessaire pour 24/7 sur VPS avec capital réel.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Pas de trade possible | 100 % blocage |
| Si stub utilisé en live | Bugs silencieux, ordres perdus, double-soumission, désync |

### Localisation cible

```
src/venue_adapters/
└── binance_spot/
    ├── __init__.py
    ├── rest_client.py              [HTTP signed REST, retry, rate limit]
    ├── ws_client.py                [WebSocket: account stream, market stream]
    ├── order_translator.py         [V5.3 OrderIntent → Binance API + return mapping]
    ├── account_snapshotter.py      [source of truth: balances, positions, open orders]
    ├── error_classifier.py         [retryable vs fatal vs ban-warning]
    ├── credential_loader.py        [sealed secrets, never plaintext]
    ├── time_sync.py                [serverTime check, NTP drift detect]
    ├── contracts.py                [pydantic models pour les payloads]
    └── tests/
        ├── test_rest_client.py
        ├── test_ws_client.py
        ├── test_order_translator.py
        ├── test_account_snapshotter.py
        ├── test_error_classifier.py
        ├── test_idempotency.py
        └── test_integration_testnet.py    [contre Binance testnet]
```

### Spécifications techniques détaillées

#### `rest_client.py`

**Responsabilités** :
- HMAC-SHA256 signing avec timestamp + recvWindow
- Rate limiter token bucket (Binance : 1200 req/min REST, 50 orders/10s, 160k orders/24h)
- Retry exponentiel sur erreurs réseau et 5xx, **PAS sur 4xx** (sauf 429 Rate Limit)
- Backoff sur 418 (IP banned warning) et 429 avec lecture du `Retry-After`
- Métriques exposées : latence p50/p95/p99, taux d'erreur, requests count
- **Idempotency** : tout POST `/api/v3/order` doit utiliser `newClientOrderId` déterministe (UUIDv5 sur intent_id)

**Endpoints minimum** :
- `GET /api/v3/exchangeInfo` (au boot, cache 24h)
- `GET /api/v3/account` (snapshot balances)
- `GET /api/v3/openOrders` (état réel)
- `POST /api/v3/order` (placement)
- `DELETE /api/v3/order` (cancel)
- `GET /api/v3/order` (lookup par clientOrderId)
- `GET /api/v3/myTrades` (historique fills pour reconciliation)

**Anti-pattern** : ne pas utiliser `python-binance` ou `ccxt` directement. Wrapper minimal si besoin, mais le code production doit avoir le contrôle total des erreurs.

#### `ws_client.py`

**Responsabilités** :
- 2 streams : `userDataStream` (account events) et `marketStream` (book + trades)
- Heartbeat : ping toutes les 3 min, pong attendu sous 10 min sinon reconnect
- **Gap detection** : sur reconnect, REST replay obligatoire des events manqués
- Session keepalive : `PUT /api/v3/userDataStream` toutes les 30 min (sinon disconnect après 60 min)
- Auto-reconnect avec backoff exponentiel (max 30 s)
- **Buffering** : pendant le reconnect, événements en queue avec timestamp pour reconstruction post-recovery

**Critique** : pendant un disconnect, le système doit refuser tout nouveau trade (état "stale") jusqu'à reconciliation complète.

#### `order_translator.py`

**Responsabilités** :
- Conversion `OrderIntent` (contrat V5.3 interne) → payload Binance
- Application des `venue_constraints` : minNotional, stepSize, lotSize, tickSize
- Truncation propre (PAS d'arrondi vers le haut qui pourrait dépasser balance)
- Mapping retour : Binance order response → `OrderState` interne
- **Validation pré-envoi** : refuse si quantity < minQty, notional < minNotional, prix > 5x mid (sécurité fat-finger)

**Cas d'erreur à gérer explicitement** :
- `INSUFFICIENT_BALANCE` → log + skip
- `LOT_SIZE` → recalcul après truncation
- `MIN_NOTIONAL` → skip avec raison loggée
- `PRICE_FILTER` → skip
- `MARKET_LOT_SIZE` → skip

#### `account_snapshotter.py`

**Responsabilités** :
- Snapshot complet du compte : balances par asset, open orders, positions (= balances non-zéro pour spot)
- **Source of truth** pour `position_reconciler.py` (V5.3 existant)
- Snapshot au boot OBLIGATOIRE
- Snapshot périodique (toutes les 5 min minimum)
- Persist snapshot dans artifact pour audit post-mortem

#### `error_classifier.py`

**Responsabilités** :
Classification de toute erreur Binance en 3 catégories :
- **RETRYABLE** : 5xx, network timeout, 429 → retry avec backoff
- **FATAL_LOCAL** : -2010 INSUFFICIENT_BALANCE, -2011 UNKNOWN_ORDER → log + skip ce trade
- **FATAL_GLOBAL** : -1003 TOO_MANY_REQUESTS si répété, 418 IP_BANNED, -2014 BAD_API_KEY → **trip kill switch immédiat**

#### `credential_loader.py`

**Responsabilités** :
- **Jamais** de plaintext en variable d'environnement ou fichier non chiffré
- Options de stockage (à choisir) :
  1. **OS keyring** (`keyring` package, intégré à libsecret/keychain)
  2. **Sealed secrets** (chiffrement local avec passphrase saisie au démarrage)
  3. **HashiCorp Vault** (overkill à 10 k$, écarter)
- Au démarrage, prompt passphrase si sealed secrets, ou unlock keyring
- Vérification API key permissions au boot : **trading uniquement, withdraw désactivé**, sinon refuse de démarrer

#### `time_sync.py`

**Responsabilités** :
- Au boot et toutes les heures, comparer `time.time()` avec `GET /api/v3/time`
- Si drift > 500 ms → warning
- Si drift > 1000 ms → kill switch trip (les ordres timestampés vont être rejetés par Binance)
- Recommandation : `chronyd` ou `ntpd` actif sur le VPS

### Coût en sessions Opus

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `rest_client.py` + tests | 600-900 | 0.5 |
| `ws_client.py` + tests | 500-800 | 0.5 |
| `order_translator.py` + tests | 400-600 | 0.25 |
| `account_snapshotter.py` + tests | 300-400 | 0.25 |
| `error_classifier.py` + tests | 200-300 | 0.1 |
| `credential_loader.py` + tests | 200-400 | 0.1 |
| `time_sync.py` + tests | 100-200 | 0.05 |
| Integration testnet | — | 0.25 |
| **Total** | **2500-4000** | **2.0** |

### Dépendances

- Aucune dépendance interne avant. Premier chantier à attaquer.
- Intégration avec `execution_runtime.py` : à faire après que l'adapter passe les tests testnet.

### Critères d'acceptation

- [ ] 100 % des endpoints minimum implémentés
- [ ] Tests unitaires couverture > 80 %
- [ ] Tests d'intégration testnet passent (au moins 10 trades de cycle complet)
- [ ] Idempotency vérifiée (double soumission rejetée par clientOrderId)
- [ ] Reconnect WebSocket vérifié (kill manuel du process WS, recovery sous 30 s)
- [ ] Time drift simulation : drift > 1 s déclenche kill switch
- [ ] Aucun plaintext de clé API détectable dans le code, les logs, ou les artifacts

---

## P0-2 — Halal compliance layer

### Pourquoi P0

`grep halal\|sharia` dans `src/` → **0 fichier**. Le système peut actuellement trader **n'importe quoi** y compris des futures, perpétuels, margin, ou tokens explicitement non-halal. **Ce n'est pas négociable** : sans cette couche, la cible "halal" est fictive.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trader un asset non-halal par défaut | Drift sharia silencieux, gains à purifier |
| Soumettre un short par accident (bug futur) | Violation halal directe |
| Activer Binance Earn par erreur | Riba, violation totale |
| Pas d'audit trail des décisions sharia | Impossible de prouver la conformité |

### Localisation cible

```
src/sharia_compliance/
├── __init__.py
├── contracts.py                    [pydantic: AssetPolicy, TradePolicy, AuditEvent]
├── asset_whitelist.py              [liste de pairs autorisées + raison]
├── asset_blacklist.py              [exclusions explicites: gambling, riba, etc.]
├── stablecoin_policy.py            [USDT/USDC/FDUSD: décision documentée]
├── trade_type_guard.py             [HARD REJECT toute action non-spot, no-short, no-margin]
├── purification_calculator.py      [si dividend/staking accidentel: portion à purifier]
├── policy_audit_logger.py          [log immutable de toutes les décisions sharia]
├── sharia_runtime.py               [orchestrateur, exposé comme gate global]
└── tests/
    ├── test_asset_whitelist.py
    ├── test_trade_type_guard.py
    ├── test_stablecoin_policy.py
    ├── test_purification.py
    └── test_integration_with_scoring_backbone.py
```

### Spécifications techniques détaillées

#### `asset_whitelist.py`

**Format** :
```python
HALAL_WHITELIST: dict[str, AssetPolicy] = {
    "BTC": AssetPolicy(
        symbol="BTC",
        allowed=True,
        reason="Bitcoin is widely accepted as halal by major scholars (...)",
        scholar_references=["AAOIFI Standard 17", "Mufti Faraz Adam (2018)"],
        last_review_date="2026-04-01",
        review_period_days=180,
    ),
    "ETH": AssetPolicy(...),
    # ... 10-20 pairs maximum
}
```

**Règles** :
- Whitelist explicite, pas de "autorisé par défaut"
- Chaque entrée a une `reason` documentée et au moins une `scholar_reference`
- `last_review_date` + `review_period_days` : périodiquement, le système alerte si une review est due
- À la review, on vérifie si l'asset est toujours conforme (ex: un coin qui ajoute des features de lending devient non-conforme)

#### `asset_blacklist.py`

**Catégories** :
- Gambling (FUN, etc.)
- Lending protocols (AAVE, COMP, MKR — débat, prudence)
- Privacy coins (XMR, ZEC — débat AML, certains pays)
- Tokens explicitement riba (toute stablecoin non-asset-backed)
- Tokens d'exchanges non-conformes
- Tokens identifiés comme scam ou pump-and-dump

#### `stablecoin_policy.py`

**Décision à documenter explicitement** :
```python
STABLECOIN_POLICY = StablecoinPolicy(
    accepted=["USDT"],          # ou ["USDC"] ou ["FDUSD"] ou combinaison
    rejected=[],
    rationale="...",
    scholar_reference="...",
    review_date="2026-04-01",
)
```

USDT/USDC sont **débattus**. La décision doit être prise et **figée** dans le code, pas laissée au hasard.

#### `trade_type_guard.py`

**Hard reject** au niveau du `intent_builder` (V5.3 existant). Refuse :
- Tout `OrderIntent` avec `side=SHORT` ou `position_type=SHORT`
- Tout `OrderIntent` avec `leverage > 1.0` ou `margin_required=True`
- Tout `OrderIntent` sur une pair non-whitelist
- Tout `OrderIntent` sur un type de produit non-spot (futures, perp, swap)

**Code structure** :
```python
def authorize_trade_type(intent: OrderIntent) -> SharaiVerdict:
    if intent.side == Side.SHORT:
        return SharaiVerdict(
            allowed=False,
            reason="SHORT_FORBIDDEN",
            detail="Short selling is not permitted under spot halal policy",
        )
    if intent.leverage > 1.0:
        return SharaiVerdict(allowed=False, reason="LEVERAGE_FORBIDDEN", ...)
    if intent.pair not in HALAL_WHITELIST:
        return SharaiVerdict(allowed=False, reason="PAIR_NOT_WHITELISTED", ...)
    # ... etc
    return SharaiVerdict(allowed=True, ...)
```

**Intégration** : appelé **avant** `execution_guard.py` dans `execution_runtime.py`. Si refus → log + skip + audit.

#### `purification_calculator.py`

Cas d'usage : un airdrop, fork, ou staking accidentel a généré un revenu non-halal. Le module calcule la portion à purifier (à donner en charité).

**À 10 k$ ce n'est pas central** mais doit exister pour être complet. Implémentation minimale :
```python
def calculate_purification(
    asset_received: str,
    quantity: Decimal,
    source: SourceType,  # AIRDROP, FORK, STAKING, INTEREST
) -> PurificationAmount:
    ...
```

#### `policy_audit_logger.py`

**Log immutable** de toutes les décisions sharia :
- Format JSON Lines append-only
- Champs : timestamp, intent_id, decision (allow/reject), reason, policy_version
- Stockage dans artifact `sharia_audit_log/` rotaté quotidien
- Jamais effaçable depuis le code

### Coût en sessions Opus

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `asset_whitelist.py` + `asset_blacklist.py` | 200-300 | 0.15 |
| `stablecoin_policy.py` | 50-100 | 0.05 |
| `trade_type_guard.py` + tests | 200-300 | 0.15 |
| `purification_calculator.py` + tests | 150-200 | 0.10 |
| `policy_audit_logger.py` + tests | 100-150 | 0.05 |
| `sharia_runtime.py` (orchestrateur) | 100-150 | 0.05 |
| Intégration avec `execution_runtime.py` + tests | — | 0.25 |
| **Total** | **800-1200** | **~0.8** |

### Dépendances

- Aucune dépendance externe.
- Décision préalable : choix de la doctrine fiqh + scholar references (voir `10_DECISIONS_REQUIRED.md`).

### Critères d'acceptation

- [ ] Whitelist contient 10-20 pairs validés avec scholar reference
- [ ] Stablecoin policy figée et documentée
- [ ] Tests démontrent que SHORT, LEVERAGE, MARGIN, FUTURES sont **impossibles à passer**
- [ ] Tests démontrent qu'une pair non-whitelist est rejetée avant `execution_guard`
- [ ] Audit log immutable vérifié (essai de modification rétro échoue)
- [ ] Au moins 1 review check : si `review_date + review_period_days < today`, warning au boot

---

## P0-3 — Fee-aware minimum-edge filter

### Pourquoi P0

À 10 k$ avec fees Binance ~0.10 % par leg, un round-trip coûte 0.20 %. Une stratégie qui ne bat pas **2× cette barre (= 0.40 %)** brûle de la valeur. Le `fee_meter.py` existant mesure ex-post mais **aucun gate ex-ante** n'empêche un trade à edge insuffisant.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trades à edge < fees | Saigne lente garantie. À 5 trades/jour ratant ce gate, **-30 à -50 USD/jour de drag pur** = **-9 000 à -15 000 USD/an**. |
| À 10 k$ → ruine annuelle si non corrigé | 100 % du capital |

### Localisation cible

Greffé dans `execution_backbone/order_decider/execution_guard.py` (existant) ou comme nouveau module :

```
src/execution_backbone/order_decider/
└── fee_aware_edge_gate.py    [nouveau]
```

### Spécifications techniques

```python
class FeeAwareEdgeGate:
    """
    Refuse un trade dont l'edge attendu est inférieur au seuil de couverture des fees.

    Règle : edge_expected_bps >= K * fees_round_trip_bps
    Default K = 2.0 (chaque trade doit théoriquement faire au moins 2x les fees)
    """

    def __init__(
        self,
        fee_provider: FeeProvider,
        edge_multiplier: float = 2.0,
        min_absolute_edge_bps: float = 30.0,  # absolu plancher
    ) -> None:
        ...

    def check(self, intent: OrderIntent, expected_edge_bps: float) -> EdgeGateVerdict:
        fees_round_trip = self.fee_provider.estimate_round_trip_bps(intent.pair)
        threshold = max(
            fees_round_trip * self.edge_multiplier,
            self.min_absolute_edge_bps,
        )
        if expected_edge_bps < threshold:
            return EdgeGateVerdict(
                allowed=False,
                reason="EDGE_INSUFFICIENT_VS_FEES",
                detail=f"edge={expected_edge_bps:.1f}bps < threshold={threshold:.1f}bps",
            )
        return EdgeGateVerdict(allowed=True, ...)
```

**Intégration** :
- Appelé après `sharia_runtime` (P0-2) et avant `execution_guard` (existant)
- L'`expected_edge_bps` doit être fourni par le scoring (ajouter le champ dans `OrderIntent` si absent)

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `fee_aware_edge_gate.py` + tests | 150-300 | 0.25 |

### Critères d'acceptation

- [ ] Gate refuse correctement les trades en dessous du seuil
- [ ] Configuration `edge_multiplier` exposée (pour tuning futur)
- [ ] `min_absolute_edge_bps` configurable
- [ ] Logs structurés contenant edge, threshold, fees calculés
- [ ] Tests unitaires couvrent les cas limites (edge = threshold, edge = 0, fees = 0)

---

## P0-4 — Sealed secrets / API key loader

### Pourquoi P0

Stocker les clés API exchange en variable d'environnement ou dans un fichier en clair sur le VPS = risque inacceptable. Une seule exfiltration (compromission SSH, log accidentel, backup non chiffré) = perte totale du capital si la clé a `withdraw=true`. Mais même avec `withdraw=false`, l'attaquant peut trader contre toi (wash trading, vendre tes positions à zéro).

### Risque si pas fait

| Risque | Impact |
|---|---|
| Compromission VPS → clés en clair | 100 % du capital |
| Clé API loggée accidentellement | 100 % du capital |
| Backup VPS non chiffré → clé exposée | 100 % du capital |

### Solution recommandée

**Option A — OS keyring** (recommandé pour single-VPS)
- Package Python `keyring`
- Backend : `SecretService` sur Linux (libsecret/gnome-keyring)
- Pro : standard OS, pas de gestion de passphrase
- Con : nécessite que le keyring soit déverrouillé au boot

**Option B — Sealed secrets avec passphrase**
- Chiffrement local avec `cryptography.fernet` + passphrase
- Au boot, le système prompte la passphrase (saisie SSH manuelle)
- Pro : indépendant du keyring OS, fonctionne en mode minimal
- Con : nécessite saisie manuelle au boot (incompatible avec restart automatique)

**Recommandation** : Option A en principal, Option B en fallback documenté.

### Localisation cible

Déjà couvert dans P0-1 sous `venue_adapters/binance_spot/credential_loader.py`. Ce gap est juste l'aspect "stockage" du problème.

### Coût

Compté dans P0-1 (200-400 LOC, 0.25 session).

### Critères d'acceptation

- [ ] Aucun plaintext de clé API détectable par grep dans `src/`, `tests/`, `logs/`, `artifacts/`
- [ ] Loader vérifie au boot que la clé a `enable_spot_trading=true` et `enable_withdrawals=false`
- [ ] Si keyring inaccessible → refuse de démarrer (pas de fallback silencieux vers env var)
- [ ] Test unitaire : tentative de log de la clé via `repr()` ou `str()` ne révèle rien

---

## P0-5 — Engine C / D rattrapage tests + audit

### Pourquoi P0 (ou P1, à arbitrer)

Audit S3 a identifié : engines C et D ont **~7 tests chacun** vs ~67-70 pour A et B. Ratio 1:10. À 10 k$ tu peux décider de :

**Option A** : démarrer LIVE avec **engine A seul** (le plus mature) → engines C/D restent à durcir mais ne bloquent pas le live → C/D rattrapés en P1
**Option B** : tu veux les 4 engines actifs en live → C/D doivent être rattrapés en P0

**Ma recommandation** : **Option A**. Démarre avec engine A seul, valide le pipeline complet (adapter + halal + fee gate + risk + reconciliation) sur une seule stratégie. Tu réduis la surface de bugs et tu apprends. Engines C/D arrivent en Phase 3 ou Phase 4.

### Risque si non rattrapé (Option B)

| Risque | Impact |
|---|---|
| Bug silencieux dans engine_c/d | Pertes non détectées |
| Désync entre engines | Décisions contradictoires |
| Pas d'edge réel mesuré | Trades aveugles |

### Localisation

Si Option B retenue :
```
tests/test_engines/test_engine_c/    [à étoffer de ~7 à ~70 tests]
tests/test_engines/test_engine_d/    [idem]
```

Et possiblement refactor de :
```
src/engines/engine_c/engine_c_runtime.py    [monolithe → modules]
src/engines/engine_c/engine_c_runner.py
```

### Spécifications

#### Si Option A (engine A seul en démarrage)

- Pas de code engine_c/d en P0
- Ajouter un **feature flag** dans `protocols/` qui permet d'activer engines selectivement : `engines_active = ["engine_a"]`
- Engines C/D restent dans le repo, marqués `experimental` en docstring
- Décision de les rattraper différée à Phase 3 ou Phase 4

#### Si Option B (rattrapage immédiat)

- Audit fonctionnel : que fait exactement engine_c et engine_d ? (S5a obligatoire)
- Décomposer le monolithe en modules (à l'image d'engine_b/) si nécessaire
- Couvrir au moins :
  - `test_engine_c_runtime.py` : runtime intégré
  - `test_engine_c_runner.py` : runner
  - `test_engine_c_scoring.py` : scoring spécifique
  - `test_engine_c_invalidation.py` : invalidation logic
  - `test_engine_c_edge_cases.py` : cas limites
  - + idem pour engine_d

### Coût

| Option | LOC | Sessions |
|---|---|---|
| **A** (feature flag) | 50-100 | 0.1 |
| **B** (refactor + tests) | 600-1500 | 0.5-1.5 |

### Critères d'acceptation

#### Option A
- [ ] Feature flag opérationnel
- [ ] Engines C/D désactivés par défaut en MICRO_LIVE et LIVE
- [ ] Documentation `BUILD_AUDIT_LOG.md` mise à jour avec décision

#### Option B
- [ ] Couverture test engines C/D ≥ 80 %
- [ ] Tests d'intégration runner ↔ runtime passent
- [ ] Tests cas limites (input vide, input invalide, dégradation gracieuse)
- [ ] 1026 tests existants ne régressent pas

---

## Synthèse P0

### Si Option A engine C/D (recommandée)

| Chantier | LOC | Sessions |
|---|---|---|
| P0-1 Exchange adapter Binance Spot | 2500-4000 | 2.0 |
| P0-2 Halal compliance | 800-1200 | 0.8 |
| P0-3 Fee-aware filter | 150-300 | 0.25 |
| P0-4 Sealed secrets (inclus dans P0-1) | — | — |
| P0-5 Feature flag engines C/D | 50-100 | 0.1 |
| **Total P0** | **3500-5600** | **3.15 sessions** |

### Si Option B engine C/D (max ambition)

| Chantier | LOC | Sessions |
|---|---|---|
| P0-1 Exchange adapter | 2500-4000 | 2.0 |
| P0-2 Halal compliance | 800-1200 | 0.8 |
| P0-3 Fee-aware filter | 150-300 | 0.25 |
| P0-4 Sealed secrets | — | — |
| P0-5 Refactor engines C/D | 600-1500 | 1.5 |
| **Total P0** | **4050-7000** | **4.55 sessions** |

---

## Ordre d'exécution recommandé

```
1. P0-1 (Exchange adapter)         [chantier le plus risqué, à attaquer en premier]
   ├── REST client + sealed secrets
   ├── Order translator
   ├── WebSocket client
   └── Tests testnet                [validation avant de continuer]

2. P0-2 (Halal compliance)
   ├── Whitelist + blacklist
   ├── Trade type guard
   └── Intégration scoring_backbone

3. P0-3 (Fee-aware filter)
   └── Greffe sur execution_guard

4. P0-5 (Décision A ou B sur engines C/D)
```

**Suite logique** : `04_GAPS_P1.md` — manques pour scaler après MICRO_LIVE.
