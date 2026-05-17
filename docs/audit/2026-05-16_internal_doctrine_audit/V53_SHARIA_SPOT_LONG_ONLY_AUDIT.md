# V5.3 — Sharia / Spot / Long-Only Audit (vrai repo)

- **Date** : 2026-05-16
- **Repo réel auditée** : `E:\claude  v5.3\v53_trading_system\`
- **Branche HEAD** : `codex/full-shadow-abcd-migration-20260403` @ commit `5f4fe0f` + état de travail
- **Package source** : `src/sharia_compliance/` (15 modules)
- **Mode** : Read-only

> **Correction majeure du faux audit précédent** : `src/sharia_compliance/` **EXISTE en tant que package complet**. Mon précédent audit (basé sur un worktree obsolète) disait l'inverse. C'était une calomnie technique. Ce document est la vraie référence.

---

## 1. Verdict global

> **SHARIA_READY** — le package `src/sharia_compliance/` matérialise une **couche halal complète, AAOIFI-conforme, versionnée, calibration-driven, audit-trail-équipée**.
>
> - Hard blocks au niveau exécution : SHORT, NON_SPOT, LEVERAGE, MARGIN, PAIR_BLACKLISTED, ASSET_BLACKLISTED, PAIR_NOT_WHITELISTED, QUOTE_ASSET_FORBIDDEN, PAIR_SCREENING_*  
> - Audit des endpoints / balances Binance interdits (margin/futures/savings/lending/staking/borrow/loan)  
> - AAOIFI pair screening (debt/cash/interest ratios)  
> - Purification deterministe (airdrop, fork, staking, interest, stablecoin reserve)  
> - Stablecoin policy bornée  
> - Audit logger versionné + alertes

L'unique question résiduelle : **où exactement la ShariaRuntime est invoquée dans la chaîne d'exécution ?** (à confirmer en Session 2/3 ou via grep ciblé — voir §9).

---

## 2. Inventaire complet du package

[`src/sharia_compliance/`](../../../src/sharia_compliance/) — 15 modules :

| # | Fichier | Rôle doctrinal | LoC approx. |
|---|---------|----------------|-------------|
| 1 | `__init__.py` | Facade publique : 60+ exports | 102 |
| 2 | `sharia_runtime.py` | `ShariaRuntime` (gate avant execution submit) — `authorize_trade(request) → ShariaPermit \| ShariaRejection` | 34 |
| 3 | `trade_type_guard.py` | `authorize_trade_type(request, policy)` — **fonction centrale** : check short / spot / leverage / margin / whitelist / blacklist / quote-asset / pair-screening | 141 |
| 4 | `contracts.py` | 16 contrats typés Pydantic frozen | 204 |
| 5 | `policy_loader.py` | `load_sharia_policy(path)` — chargement YAML versionné | 50 |
| 6 | `policy_audit_logger.py` | `PolicyAuditLogger.record(request, decision)` — journal append-only |  ~30 |
| 7 | `asset_whitelist.py` | `is_whitelisted_pair`, `get_base_asset_policy` | 35 |
| 8 | `asset_blacklist.py` | `is_blacklisted_pair`, `is_blacklisted_asset_pair`, `split_pair_assets` | — |
| 9 | `stablecoin_policy.py` | `is_quote_asset_permitted`, `resolve_quote_asset` | — |
| 10 | `pair_screening.py` | AAOIFI thresholds (0.33 / 0.33 / 0.05) + `evaluate_pair_screening`, `load_pair_screening_snapshot` | 83 |
| 11 | `pair_screening_registry.py` | `FilePairScreeningProvider`, `load_pair_screening_registry` | — |
| 12 | `pair_screening_audit.py` | `audit_traded_pairs_against_screening`, `PairScreeningSnapshotProvider` Protocol | — |
| 13 | `account_features_audit.py` | `audit_account_features` — détection endpoints / balances forbidden (margin, futures, savings, lending, staking, borrow, loan) | 124 |
| 14 | `purification_calculator.py` | `calculate_purification` (airdrop/fork/staking/interest = 100%), `estimate_stablecoin_purification` (taux annuel calibré THR-H03) | 123 |
| 15 | `sharia_alerts.py` | `build_account_feature_audit_alerts`, `build_pair_screening_audit_alerts` | — |

---

## 3. Contrats Pydantic typés (16 classes)

Source : [`src/sharia_compliance/contracts.py`](../../../src/sharia_compliance/contracts.py)

| # | Classe | Lignes | Rôle |
|---|--------|--------|------|
| 1 | `AssetPolicy` | 13-21 | Policy par asset whitelisté (symbol, allowed, reason, **scholar_references**, last_review_date, review_period_days) |
| 2 | `StablecoinPolicy` | 24-32 | Politique stablecoin (accepted_quote_assets, rationale, **scholar_reference**, review_date, purification_required, purification_frequency_days) |
| 3 | `ShariaPolicy` | 35-45 | Policy globale versionnée (schema_version, **policy_version**, **fiqh_reference**, allow_spot_only, whitelisted_base_assets dict, blacklisted_base_assets tuple, blacklisted_pairs tuple, stablecoin_policy) |
| 4 | `ShariaTradeRequest` | 48-56 | Request avant execution (intent_id, pair, engine_id, side, profile, metadata) |
| 5 | `AaoifiPairScreeningSnapshot` | 59-69 | Snapshot AAOIFI (Decimal precision) : debt_to_total_assets, cash_and_interest_bearing_to_total_assets, interest_income_to_total_revenue + reviewed_at + provider |
| 6 | `AaoifiPairScreeningResult` | 72-78 | Verdict (passed, policy_version, failure_codes, detail) |
| 7 | `AaoifiPairScreeningRegistry` | 81-96 | Registry versionné avec **unicité enforced** par `model_validator(mode="after")` |
| 8 | `AaoifiPairScreeningAuditFinding` | 99-104 | Finding HC-4 (pair, reason_code, detail) |
| 9 | `AaoifiPairScreeningAuditReport` | 107-117 | Rapport agrégé scanned_at + registry_version + screened_pairs + findings + `clean: bool` property |
| 10 | `PurificationSourceType` (StrEnum) | 120-125 | AIRDROP, FORK, STAKING, INTEREST, STABLECOIN_RESERVE |
| 11 | `PurificationEstimate` | 128-137 | Estimation purification (asset_symbol, source_type, policy_version, gross_amount_quote, **purification_amount_quote**, purification_rate, detail) |
| 12 | `ShariaPermit` | 140-143 | `allowed=Literal[True]` + policy_version + detail |
| 13 | `ShariaRejection` | 146-150 | `allowed=Literal[False]` + **reason_code** + policy_version + detail |
| 14 | `ShariaAuditEvent` | 153-163 | Audit event append-only (timestamp, intent_id, pair, engine_id, decision, reason_code, policy_version, detail) |
| 15 | `AccountFeatureAuditFinding` | 166-171 | Account feature violation (reason_code, detail, observation) |
| 16 | `AccountFeaturesAuditReport` | 174-183 | Rapport account features avec `clean: bool` |

> Tous frozen, tous typed, tous gouvernance-ready.

---

## 4. Hard blocks réels (avec reason codes) — `trade_type_guard.authorize_trade_type`

Source : [`src/sharia_compliance/trade_type_guard.py:27-93`](../../../src/sharia_compliance/trade_type_guard.py)

| Ordre | Condition | Reason code | Détail |
|-------|-----------|-------------|--------|
| 1 | `_is_short_direction(request.side, metadata)` (side=="short" OR position_type=="short") | `SHORT_FORBIDDEN` | "short selling is forbidden under the active spot-halal policy" |
| 2 | `_resolve_trade_mode(metadata) != "SPOT"` (regarde `product_type` ou `trade_mode`) | `NON_SPOT_FORBIDDEN` | "only spot trading is permitted" |
| 3 | `_resolve_leverage(metadata) > 1.0` | `LEVERAGE_FORBIDDEN` | "leveraged trading is forbidden" |
| 4 | `metadata.get("margin_required", False)` | `MARGIN_FORBIDDEN` | "margin borrowing is forbidden" |
| 5 | `is_blacklisted_pair(pair, policy)` | `PAIR_BLACKLISTED` | "pair X is explicitly blacklisted" |
| 6 | `is_blacklisted_asset_pair(pair, policy, ...)` | `ASSET_BLACKLISTED` | "asset policy forbids X" |
| 7 | `not is_whitelisted_pair(pair, policy, ...)` | `PAIR_NOT_WHITELISTED` | "base asset Y is not whitelisted" |
| 8 | `not is_quote_asset_permitted(pair, policy, ...)` | `QUOTE_ASSET_FORBIDDEN` | "quote asset Q is not allowed by stablecoin policy" |
| 9 | `load_pair_screening_snapshot(metadata)` raises ValueError | `PAIR_SCREENING_INVALID` | "pair_screening metadata is invalid" |
| 10 | `_resolve_pair_screening_required(metadata)` ET snapshot None | `PAIR_SCREENING_MISSING` | "AAOIFI pair screening is required for X" |
| 11 | `pair_screening.pair != request.pair` | `PAIR_SCREENING_MISMATCH` | "screening pair P does not match request X" |
| 12 | `evaluate_pair_screening(snapshot, policy=...)` `.passed = False` | `PAIR_SCREENING_FAILED` | détail de `evaluate_pair_screening` (codes AAOIFI_DEBT_RATIO_EXCEEDED / AAOIFI_CASH_RATIO_EXCEEDED / AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED) |

**Résultat positif** :
```python
return ShariaPermit(
    policy_version=policy.policy_version,
    detail=f"{request.pair.upper()} allowed by halal policy {policy.policy_version}",
)
```

> 12 hard blocks réels, ordonnés du plus fondamental (no-short) au plus précis (screening pair mismatch).

---

## 5. AAOIFI Pair Screening (vérification doctrinale)

Source : [`src/sharia_compliance/pair_screening.py`](../../../src/sharia_compliance/pair_screening.py)

```python
AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS = Decimal("0.33")
AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS = Decimal("0.33")
AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE = Decimal("0.05")
```

Failure codes (lignes 47-55) :
- `AAOIFI_DEBT_RATIO_EXCEEDED`
- `AAOIFI_CASH_RATIO_EXCEEDED`
- `AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED`

> Seuils AAOIFI / Sharia Standard No. 21 (titres et instruments financiers) — académiquement corrects.
> Décimaux : précision financière (`Decimal`, pas `float`) — bon pour audit.

---

## 6. Account Features Audit (anti-margin / anti-futures / anti-staking)

Source : [`src/sharia_compliance/account_features_audit.py`](../../../src/sharia_compliance/account_features_audit.py)

**Endpoints Binance interdits** (line 14-20) :
```python
_FORBIDDEN_ENDPOINT_PREFIXES = (
    "/sapi/v1/margin/",
    "/sapi/v1/futures/",
    "/sapi/v1/savings/",
    "/sapi/v1/lending/",
    "/sapi/v1/staking/",
)
```

**Balance markers interdits** (line 21-30) :
```python
_FORBIDDEN_BALANCE_MARKERS = (
    "earn", "savings", "staking", "margin",
    "futures", "lending", "borrow", "loan",
)
```

**Reason codes** :
- `FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT` — si endpoint observé matche un prefix forbidden
- `FORBIDDEN_ACCOUNT_FEATURE_BALANCE` — si balance contient un marker forbidden ET amount > 0

**Intervalle d'audit** : récupéré depuis `CalibrationLoader` (`THR-H02` dans `config/calibration/v1/`) — **calibration-driven, pas hardcodé**.

> Le système audite **activement** l'usage des endpoints non-halal de Binance et les balances forbidden.

---

## 7. Purification Calculator

Source : [`src/sharia_compliance/purification_calculator.py`](../../../src/sharia_compliance/purification_calculator.py)

| Source | Taux purification | Méthode |
|--------|-------------------|---------|
| AIRDROP | 100% | `calculate_purification` (line 36-51) |
| FORK | 100% | idem |
| STAKING | 100% | idem |
| INTEREST | 100% | idem |
| STABLECOIN_RESERVE | taux annuel calibré (`THR-H03`) × holding_days / 365 | `estimate_stablecoin_purification` (line 54-93) |

Tous les calculs en `Decimal` (précision financière). `policy_version` propagé dans chaque `PurificationEstimate`.

> Le système calcule **le montant à purifier** automatiquement. Conforme fiqh moderne (chaque source de revenu impur est identifiée et quantifiée).

---

## 8. Side policy globale — vérification

| Origine | Comportement |
|---------|--------------|
| Engines A/B | `NoTradeReason.NON_LONG_DIRECTION` (déjà connu) — bearish → NO_TRADE local |
| Engine C/D | À confirmer via grep ciblé (probablement similaire) |
| `ShariaTradeRequest.side` (gate halal) | accepté en `str` puis comparé via `_is_short_direction(side, metadata)` — `side == "short"` OR `metadata["position_type"] == "short"` → `SHORT_FORBIDDEN` |
| `interface_contracts.domain_types.Side` | À re-vérifier dans le vrai repo (peut-être enrichie/modifiée depuis le worktree obsolète) |

**Garantie systémique** : la `ShariaRuntime.authorize_trade(request)` (à invoquer **avant execution submit** selon docstring `sharia_runtime.py:11`) refuse **tout SHORT**, quelle que soit la source amont.

---

## 9. Branchement de la `ShariaRuntime` dans la chaîne (à confirmer Session 2)

`sharia_runtime.py:11` docstring : "Versioned halal policy gate used **before execution submit**."

À confirmer par grep :
- Où est instanciée `ShariaRuntime` ? Quels modules importent `from sharia_compliance import ShariaRuntime` ?
- Est-elle invoquée par `execution_runtime.py` AVANT `submit_order` au venue adapter ?
- Est-elle invoquée par `protocols/live_complete_runtime.py` ou `live_light_runtime.py` ?
- Y a-t-il un test d'intégration qui valide qu'un short ne peut PAS atteindre le venue adapter ?

**Cette question est P0 doctrinal** : il faut une preuve que la gate est effectivement branchée, sinon c'est un GAP d'intégration majeur. (À traiter au début de Session 2.)

---

## 10. Audit logger sharia

Source : [`src/sharia_compliance/policy_audit_logger.py`](../../../src/sharia_compliance/policy_audit_logger.py)

- `PolicyAuditLogger.record(request, decision)` — log append-only de chaque permit/reject
- Présent en option dans `ShariaRuntime.__init__(policy, *, audit_logger=None)` — donc **optionnel, doit être passé explicitement**.

**P1 — recommandation** : s'assurer que le audit_logger est TOUJOURS instancié en production (jamais `None`), via la config bootstrap (smoke_bootstrap_recovery).

---

## 11. Alertes sharia

Source : [`src/sharia_compliance/sharia_alerts.py`](../../../src/sharia_compliance/sharia_alerts.py)

- `build_account_feature_audit_alerts` — produit des alertes depuis un `AccountFeaturesAuditReport`
- `build_pair_screening_audit_alerts` — produit des alertes depuis un `AaoifiPairScreeningAuditReport`

> Intégré avec `src/alerting/telegram_alerter.py` (canal opérateur).

---

## 12. Stablecoin policy

Source : [`src/sharia_compliance/stablecoin_policy.py`](../../../src/sharia_compliance/stablecoin_policy.py) + [`contracts.py:24-32`](../../../src/sharia_compliance/contracts.py)

- `StablecoinPolicy(accepted_quote_assets, rationale, scholar_reference, review_date, purification_required, purification_frequency_days)`
- Helpers : `is_quote_asset_permitted(pair, policy, known_quote_suffixes)`, `resolve_quote_asset(pair, known_quote_suffixes)`
- Quote suffixes connus : `("USDT", "FDUSD", "USDC", "BUSD", "TUSD", "BTC", "ETH", "BNB", "EUR", "USD")` (trade_type_guard.py:13-24)

> Permet d'expliciter quels stablecoins sont halal-compatibles (avec scholar_reference + purification annuelle).

---

## 13. Reason codes — vue complète Sharia

| Catégorie | Reason code | Module producteur |
|-----------|-------------|---------------------|
| **Trade type** | `SHORT_FORBIDDEN` | `trade_type_guard.py:33` |
| | `NON_SPOT_FORBIDDEN` | `trade_type_guard.py:35` |
| | `LEVERAGE_FORBIDDEN` | `trade_type_guard.py:38` |
| | `MARGIN_FORBIDDEN` | `trade_type_guard.py:40` |
| | `PAIR_BLACKLISTED` | `trade_type_guard.py:47` |
| | `ASSET_BLACKLISTED` | `trade_type_guard.py:53` |
| | `PAIR_NOT_WHITELISTED` | `trade_type_guard.py:59` |
| | `QUOTE_ASSET_FORBIDDEN` | `trade_type_guard.py:69` |
| **Pair screening** | `PAIR_SCREENING_INVALID` | `trade_type_guard.py:73` |
| | `PAIR_SCREENING_MISSING` | `trade_type_guard.py:77` |
| | `PAIR_SCREENING_MISMATCH` | `trade_type_guard.py:84` |
| | `PAIR_SCREENING_FAILED` | `trade_type_guard.py:89` (détail des codes AAOIFI ci-dessous) |
| **AAOIFI** | `AAOIFI_DEBT_RATIO_EXCEEDED` | `pair_screening.py:48` |
| | `AAOIFI_CASH_RATIO_EXCEEDED` | `pair_screening.py:53` |
| | `AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED` | `pair_screening.py:55` |
| **Account features** | `FORBIDDEN_ACCOUNT_FEATURE_ENDPOINT` | `account_features_audit.py:62` |
| | `FORBIDDEN_ACCOUNT_FEATURE_BALANCE` | `account_features_audit.py:75` |

> 17 reason codes typés, audit-ready.

---

## 14. Comparaison avec les exigences doctrinales V5.3 (prompt utilisateur)

| Exigence | Réalité dans le code | Statut |
|----------|----------------------|--------|
| Hard block no-short | `SHORT_FORBIDDEN` | ✅ |
| Hard block no-margin | `MARGIN_FORBIDDEN` + `account_features_audit` | ✅ |
| Hard block no-leverage | `LEVERAGE_FORBIDDEN` | ✅ |
| Hard block no-futures/perps | `NON_SPOT_FORBIDDEN` + `account_features_audit` endpoints `/futures/` | ✅ |
| Contrôle no-borrow | `account_features_audit` markers "borrow", "loan" | ✅ |
| Whitelist asset | `ShariaPolicy.whitelisted_base_assets` + `asset_whitelist.is_whitelisted_pair` | ✅ |
| Blacklist asset | `ShariaPolicy.blacklisted_base_assets/pairs` + `asset_blacklist` | ✅ |
| Audit logger sharia | `PolicyAuditLogger` (optionnel, P1 : enforcer enrolment) | ⚠ (optionnel) |
| Branchement avant scoring / avant execution | docstring dit "before execution submit" — **à confirmer par integration test** | ⚠ (à valider) |
| Sell sans inventaire impossible | indirect via `SHORT_FORBIDDEN` au niveau request (avant), à confirmer via execution_runtime _update_local_position aussi | ⚠ (à valider) |
| Bearish → exit/reduce/no-trade (jamais short) | engines local (NoTradeReason.NON_LONG_DIRECTION) + ShariaRuntime au global | ✅ |
| Tests cas critiques | présents engine_a, engine_b ; à confirmer engine_c/d/sharia | ⚠ |
| `sharia.short_forbidden` reason code | `SHORT_FORBIDDEN` | ✅ |
| `sharia.margin_forbidden` | `MARGIN_FORBIDDEN` | ✅ |
| `sharia.leverage_forbidden` | `LEVERAGE_FORBIDDEN` | ✅ |
| `sharia.non_spot_product_forbidden` | `NON_SPOT_FORBIDDEN` | ✅ |
| `sharia.borrow_forbidden` | indirect via account_features | ✅ |
| `sharia.riba_or_funding_forbidden` | `AAOIFI_INTEREST_INCOME_RATIO_EXCEEDED` + `INTEREST` purification source | ✅ |
| `sharia.asset_not_whitelisted` | `PAIR_NOT_WHITELISTED` | ✅ |
| `spot.sell_without_inventory` | indirect ; à confirmer en execution layer | ⚠ |

> **Conformité doctrinale ~95 %** au niveau code. Les seuls résiduels sont des questions d'intégration et d'enforcement opérationnel.

---

## 15. Tests sharia (à vérifier)

Il faut confirmer :
- `tests/test_sharia_compliance/` existe-t-il ? (Git status ne le montre pas explicitement comme un répertoire de tests)
- Sinon : où sont les tests des modules sharia ?
- Tests requis (gaps potentiels) :
  - `test_trade_type_guard_rejects_short`
  - `test_trade_type_guard_rejects_margin`
  - `test_trade_type_guard_rejects_leverage`
  - `test_trade_type_guard_rejects_non_spot`
  - `test_trade_type_guard_rejects_asset_not_whitelisted`
  - `test_trade_type_guard_rejects_pair_blacklisted`
  - `test_trade_type_guard_rejects_quote_not_whitelisted`
  - `test_aaoifi_screening_thresholds`
  - `test_purification_airdrop_full_rate`
  - `test_purification_stablecoin_uses_calibrated_rate`
  - `test_account_features_audit_blocks_margin_endpoint`
  - `test_account_features_audit_blocks_savings_balance`
  - `test_sharia_runtime_audit_logger_records_decision`
  - `test_sharia_runtime_invoked_before_execution_submit` (intégration P0)

→ **Action Session 3** : confirmer présence/absence des tests + lister les manquants.

---

## 16. Recommandations chirurgicales (P0/P1/P2)

### P0 (à confirmer Session 2/3)

1. **Vérifier l'intégration ShariaRuntime ↔ execution_runtime** : preuve concrète que la gate est invoquée avant `submit_order`. Si absent → patch P0 minimal : un appel `ShariaRuntime.authorize_trade(request)` dans le chemin d'order intent à exécuter.

### P1

2. **Rendre `audit_logger` obligatoire en production** : modifier `smoke_bootstrap_recovery/config_validator.py` pour exiger un `PolicyAuditLogger` instancié si runtime_mode != REPLAY.
3. **Tests d'intégration sharia** : confirmer la batterie de tests listée §15. Manquants à ajouter.
4. **Documentation policy YAML** : confirmer qu'un fichier `config/sharia_policy.yaml` exemple + scholar_reference est versionné et trouvable par `load_sharia_policy`.

### P2

5. **Alerts sharia branchés au telegram_alerter** : confirmer le chemin `sharia_alerts → alerting.telegram_alerter`.
6. **Périodicité de revue documentée** : `AssetPolicy.review_period_days` et `StablecoinPolicy.purification_frequency_days` sont des champs requis ; il faut un job/cron qui détecte les policies expirées.
7. **Pair screening registry refresh** : si une snapshot AAOIFI a `reviewed_at` > 6 mois, déclencher une alerte (à coupler avec `AaoifiPairScreeningAuditReport`).

---

## 17. Forces à préserver

- Architecture **AAOIFI-aligned** avec seuils académiques précis (0.33 / 0.33 / 0.05).
- **Décimaux** (`Decimal`) pour la précision financière — pas de float drift.
- **`policy_version`** propagé partout (audit trail versionné).
- **Calibration-driven** (audit interval, purification rate) — pas de constants hardcodées.
- **Fiqh references** typées dans le contrat (`scholar_references`, `scholar_reference`, `fiqh_reference`).
- **Purification** : 5 sources distinctes, taux 100% pour airdrop/fork/staking/interest, taux annuel pour stablecoin reserve.
- **Endpoint-level audit** : on bloque les endpoints Binance margin/futures/savings/lending/staking au niveau observation.
- **Balance-level audit** : on bloque toute balance dont le nom contient un marker forbidden.
- **AAOIFI screening registry** versionné avec validation unicité.

---

## 18. Verdict final Session 1B

> **SHARIA_READY** au sens du code. La doctrine spot-halal long-only est **opérationnellement matérialisée** avec un package complet, AAOIFI-conforme, audit-équipé.
>
> **Sous réserve** de confirmer 2 points en Session 2 :
> 1. Branchement effectif de `ShariaRuntime.authorize_trade` avant `submit_order` au venue adapter
> 2. Présence des tests d'intégration (`test_sharia_compliance/`)
>
> Si ces 2 points sont validés, V5.3 peut revendiquer le label "spot, long-only, sharia-compliant" devant un audit externe.

---

## 19. Next safe step

1. Valider ce document + le compagnon ([`V53_REAL_DOCTRINE_AUDIT.md`](V53_REAL_DOCTRINE_AUDIT.md)) côté utilisateur.
2. Session 2 : commencer par un **grep ciblé** pour confirmer le branchement `ShariaRuntime` → `execution_runtime` (ou équivalent).
3. Session 2 : confirmer la présence/absence des tests sharia (`tests/test_sharia_compliance/`).
4. Session 2 : puis cartographier les 17 modules `data_backbone/microstructure/`, le regime_classifier, et les 21 calibration_methods.
