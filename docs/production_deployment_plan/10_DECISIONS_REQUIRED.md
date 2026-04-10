# Décisions humaines requises avant chaque phase

> **Objectif** — Lister toutes les décisions structurantes à prendre par l'humain **avant** que l'agent codeur démarre, et **avant chaque gate** de phase. Aucune décision implicite. Aucune décision laissée à l'agent codeur.
>
> **Format** — Chaque décision a : la question, les options, l'option par défaut recommandée, l'impact si on choisit autre chose, et l'endroit où la décision doit être tracée (fichier signé).

---

## 1. Décisions Phase 0 (avant tout code)

### D-01 — Exchange cible

**Question** : Sur quel exchange déployer en MICRO_LIVE et LIVE ?

**Options** :
- **A. Binance Spot** (recommandé)
- **B. Kraken Spot**
- **C. Coinbase Pro / Advanced Trade**
- **D. Multi-exchange (Binance + Kraken en parallèle)**

**Recommandation** : **A. Binance Spot**

**Justification** :
- Liquidité maximale sur les paires halal whitelistables (BTC, ETH, large caps spot)
- API et WebSocket les plus matures et documentés
- Fees compétitives (0.10 % par défaut, 0.075 % avec BNB discount, 0.05 % VIP)
- Testnet disponible pour validation P0-1
- Support de tous les types d'order utiles (LIMIT, MARKET, STOP_LOSS_LIMIT)

**Impact si autre choix** :
- Kraken : meilleur côté régulation EU, mais liquidité plus faible et fees plus élevées (0.16 % maker / 0.26 % taker base)
- Coinbase : régulation US-friendly mais fees très élevées (0.40 % retail) → kill l'edge à 10 k$
- Multi-exchange : double l'effort P0-1 (~2x sessions code), gain marginal à 10 k$

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § exchange

---

### D-02 — École fiqh / référence sharia

**Question** : Quelle école juridique / fatwa de référence utiliser pour les décisions halal ?

**Options** :
- **A. AAOIFI** (Accounting and Auditing Organization for Islamic Financial Institutions) — standard institutionnel
- **B. Fatwa Mufti Taqi Usmani** sur la crypto (la plus citée)
- **C. Sheikh Joe Bradford** (vulgarisation crypto US)
- **D. Mufti Faraz Adam** (spécialiste crypto/DeFi UK)
- **E. Ton propre conseil local + revue par tiers annuelle**

**Recommandation** : **B + E** — base AAOIFI/Usmani, validation tiers annuelle

**Justification** :
- AAOIFI/Usmani = base la plus défendable et documentée
- Revue annuelle par tiers crypto-spécialiste = défense en profondeur
- Pas besoin d'avoir un avis "définitif" sur tout — la posture conservative suffit pour 10 k$ à condition d'être documentée

**Impact** : la décision conditionne la whitelist d'assets, la stablecoin policy, le traitement des airdrops. À ne pas changer en cours de route sans purification rétroactive.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § sharia + `config/sharia/policy_v1.yml` (référence en commentaire)

---

### D-03 — Stablecoin policy

**Question** : Quel stablecoin utiliser comme contrepartie principale et avec quel régime de purification ?

**Options** :
- **A. USDT** (Tether) — liquide, mais réserves opaques, papier commercial intérêt-bearing
- **B. USDC** (Circle) — backed T-Bills US (intérêt indirect), plus transparent
- **C. DAI** (MakerDAO) — over-collateralisé crypto, stability fee = riba structurel
- **D. PYUSD** (PayPal/Paxos) — récent, similaire USDC
- **E. USDT avec purification calculée mensuellement**
- **F. Pas de stablecoin — uniquement quote BTC** (sortie en BTC, pas en stable)

**Recommandation** : **E. USDT + purification mensuelle calculée**

**Justification** :
- Liquidité USDT > USDC sur Binance Spot
- Aucun stable n'est 100 % halal selon les juristes les plus stricts → choisir le plus liquide et purifier
- L'approche "purification calculée" est documentée par AAOIFI pour les zones grises
- Option F (BTC quote) éviterait le débat mais réduit drastiquement l'univers tradable et augmente la vol du portefeuille

**Impact** :
- Influence directement P0-2 (`stablecoin_policy.py` + `purification_calculator.py`)
- Détermine la base mensuelle à donner en charity
- Si tu changes plus tard, il faut re-purifier rétroactivement

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § stablecoin + `config/sharia/stablecoin_policy.yml`

---

### D-04 — VPS confirmé

**Question** : VPS Hetzner CX43 (proposé) ou autre ?

**Options** :
- **A. Hetzner CX43** (recommandé) : 8 vCPU, 16 GB RAM, 160 GB SSD, 20 TB traffic, €12.49/mois, EU
- **B. Hetzner CX42 ou plus petit** (économie marginale)
- **C. Contabo / Vultr / DigitalOcean** (alternatives EU/global)
- **D. Multi-VPS avec failover actif** (overkill à 10 k$, ~2x coût + complexité)
- **E. Single active VPS + vue flotte passive multi-VPS** (option future) : plusieurs VPS peuvent être résumées dans une vue `health/status/artifact`, mais le trading reste porté par une seule VPS active à la fois

**Recommandation** : **A. Hetzner CX43** aujourd'hui. `E` reste compatible plus tard si l'objectif est seulement une vue flotte read-only.

**Justification** :
- Marge confortable sur ressources (5x marge RAM, 4x marge disque vs estimation V5.3)
- Coût annuel = 1.6 % du capital, raisonnable
- Localisation EU = latence acceptable vers Binance + RGPD compliance pour logs personnels
- Single active VPS suffisant à 10 k$ : kill switch + reconciliation gèrent les pannes

**Impact** :
- CX42 (4 vCPU / 8 GB) : risque de saturation lors des calibrations locales si on les fait sur le VPS — mais on ne les fait PAS sur le VPS (cf. `12_LOCAL_LAB_VS_VPS_SEPARATION.md`). Donc OK marginalement, mais la marge est moins confortable.
- Multi-VPS avec failover actif : ne se justifie qu'à >100 k$ et avec un trader full-time
- Vue flotte passive multi-VPS : reste acceptable plus tôt si elle reste purement read-only et ne remplace pas le drill-down sur la VPS concernée

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § infra

---

### D-05 — Capital initial MICRO_LIVE

**Question** : Quel capital pour démarrer Phase 3 (MICRO_LIVE) ?

**Options** :
- **A. 200 USD** (2 % du target)
- **B. 500 USD** (5 % du target, recommandé)
- **C. 1000 USD** (10 % du target)

**Recommandation** : **B. 500 USD**

**Justification** :
- Suffisamment grand pour générer ≥ 30 trades en 30 jours sur des positions ≥ 100 USD (respectant min_notional Binance avec marge)
- Suffisamment petit pour qu'une perte totale (-100 % très improbable, -20 % vraiment plausible si bug) soit absorbée sans casser la trajectoire (= 100 USD perte = 1 % du target)
- 200 USD = trop faible : trades < 50 USD donc edge dilué par fees fixes
- 1000 USD = trop élevé : si bug, perte de 200 USD avant d'avoir validé la stabilité

**Impact** :
- Détermine la durée minimum MICRO_LIVE (besoin de 30+ trades)
- Influence le `capital_cap` dans la config runtime

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § microlive

---

### D-06 — Plan de scaling Phase 4 LIVE

**Question** : Comment monter en capital après MICRO_LIVE validé ?

**Options** :
- **A. Saut direct 500 → 10000** (rapide mais risqué)
- **B. Paliers 500 → 2000 → 5000 → 10000** avec 2 semaines minimum entre chaque
- **C. Paliers continus +20 % par semaine**

**Recommandation** : **B**

**Justification** : 4 paliers permettent de détecter les pathologies de scale (ex : impact orderbook qui apparaît à 5000 et n'existait pas à 2000) avant que tout le capital soit exposé.

**Impact** : prolonge le temps avant capital cible (4 × 2 semaines = ~2 mois après G3).

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § scaling

---

### D-07 — Qui valide les gates SHADOW (G2.1, G2.2, G2.3) ?

**Question** : Qui signe les gates humains ? Toi seul, ou peer-review obligatoire ?

**Options** :
- **A. Toi seul** (recommandé pour 10 k$ personnel)
- **B. Toi + 1 peer technique** (ami dev qui revoit la métriques)
- **C. Toi + audit charia** (pour les questions halal uniquement)

**Recommandation** : **A** pour les aspects techniques + **C** pour audit halal annuel

**Justification** :
- À 10 k$ personnel, le coût d'un peer review formel est disproportionné
- Mais l'audit halal annuel par un tiers spécialisé (mufti crypto) reste recommandé pour la pureté du capital

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § gates

---

### D-08 — Qui produit et signe les artefacts de calibration ?

**Question** : Le Local IA Lab produit les artefacts. Qui signe pour usage VPS ?

**Options** :
- **A. Signature humaine manuelle** : tu lis l'artefact, tu valides, tu signes (clé GPG ou simple `signed_by: <name> <date>` dans le YAML)
- **B. Signature automatique** si critères de validation atteints
- **C. Hybride** : auto-validation des seuils déjà connus, signature manuelle des nouveaux

**Recommandation** : **A** pour Phase 0/1, **C** pour les recalibrations trimestrielles

**Justification** : la première calibration doit être lue avec attention car elle conditionne toutes les phases suivantes. Les recalibrations ultérieures peuvent être plus automatisées tant que les critères sont stables.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § calibration_signing

---

## 2. Décisions Phase 1 (avant code)

### D-09 — Engine C/D : Option A ou B ?

**Question** : Pour `P0-5`, on choisit l'Option A (feature flag, désactivés en MICRO_LIVE) ou Option B (refactor complet) ?

**Options** :
- **A. Feature flag** : 0.25 session code, Engine C/D off en MICRO_LIVE, refactor reporté à post-LIVE
- **B. Refactor complet** : 1-3 sessions code, Engine C/D actifs en MICRO_LIVE

**Recommandation** : **A. Feature flag**

**Justification** : à 10 k$, 2 engines (A + B) suffisent. Le refactor C/D peut attendre d'avoir des données live qui justifieraient l'investissement.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § engines

---

### D-10 — V37 bricks : on les fait avant ou après SHADOW ?

**Question** : T12 (Gatekeeper central) et T13 (Info stress monitor) : avant SHADOW (Phase 2) ou après ?

**Options** :
- **A. Avant SHADOW** : tranches T12+T13 dans la fin de Phase 1bis
- **B. Après SHADOW** : seulement après G2.3 si on juge nécessaire
- **C. Skip totalement** si V5.3 suffit

**Recommandation** : **A. Avant SHADOW**

**Justification** :
- T12 (Gatekeeper) ajoute de l'audit trail = précieux pour la review SHADOW
- T13 (Info stress monitor) protège contre les flash crashes pendant SHADOW (et oui, on shadow contre du marché réel donc le risque existe... même sans capital exposé, un mauvais test révèle peu)

**Impact** : ajoute ~1 session code à Phase 1bis. Décale Phase 2 de ~1 semaine.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § v37_bricks_timing

---

## 3. Décisions Phase 2 (avant SHADOW)

### D-11 — Métriques de validation SHADOW : valeurs cibles

**Question** : Quels seuils chiffrés pour valider chaque gate SHADOW ? (Phase 0 doit produire les valeurs calibrées, mais l'humain doit les valider.)

**Champs à définir** (valeurs proposées indicatives) :
- **Sharpe simulé minimum** pour passer chaque palier : 0.5 / 0.6 / 0.7 (S2.1 / S2.2 / S2.3) ?
- **Max DD simulé maximum** : 15 % / 13 % / 12 % ?
- **Nb décisions cumulées minimum** : 30 / 60 / 100 ?
- **Uptime minimum** : 99 % / 99 % / 99.5 % ?

**Recommandation** : commencer avec les chiffres ci-dessus, ajustables en Phase 0 selon ce que la calibration produit comme bornes réalistes.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § shadow_thresholds (et `config/calibration_v1.yml` § shadow_gates)

---

### D-12 — Comportement humain pendant SHADOW

**Question** : Combien de temps tu t'engages à monitorer SHADOW chaque jour ?

**Options** :
- **A. 5 min/jour** (lecture rapide du résumé matin)
- **B. 15 min/jour** (incl. revue des décisions)
- **C. 30 min/jour ou plus**

**Recommandation** : **B**, avec 1h hebdomadaire pour la revue de fin de palier.

**Important** : l'engagement doit être réaliste. Si tu sais que tu ne pourras pas tenir 30 min/jour, choisis 5 min/jour et n'autorise pas plus de signaux/jour à générer.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § human_engagement

---

## 4. Décisions Phase 3 (avant MICRO_LIVE)

### D-13 — Pré-engagement écrit "anti-panique"

**Question** : Quelles règles tu t'imposes par écrit pour éviter d'intervenir manuellement par panique ?

**Template** :
```
Je m'engage à NE PAS :
- Modifier le code en LIVE pendant un drawdown
- Liquider manuellement une position sans valider via le kill switch
- Augmenter le capital plus vite que le plan de scaling D-06
- Désactiver le daily P&L breaker pour "voir ce qui se passe"

Je m'engage à :
- Lire le résumé matinal chaque jour ouvré
- Respecter le plan de scaling D-06
- Convoquer une revue formelle si DD > 5 % en 1 jour
```

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § pre_engagement_personal (rédigé à la main, signé)

---

### D-14 — Plan d'urgence

**Question** : Que fais-tu si Hetzner tombe pendant 24h ?

**Options proposées** :
- **A. Rien** : le système est en pause naturelle, kill switch s'active au reboot
- **B. Migration manuelle** vers un VPS de backup déjà préparé
- **C. Liquidation manuelle** depuis l'interface web Binance

**Recommandation** : **A** par défaut, avec doc de B en backup au cas où la panne dure > 48h.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § emergency_plan

---

## 5. Décisions Phase 4 (avant LIVE)

### D-15 — Fréquence de revue mensuelle

**Question** : Combien de temps par mois pour la revue obligatoire ?

**Options** : 30 min / 1h / 2h

**Recommandation** : **1h/mois minimum** + 1h supplémentaire en cas d'incident.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § monthly_review

---

### D-16 — Recalibration trimestrielle : qui, comment ?

**Question** : Qui lance la recalibration et selon quel rythme ?

**Recommandation** :
- **Rythme** : tous les 90 jours en fixe + déclenchement exceptionnel si Sharpe rolling 30j divise par 2 vs backtest
- **Procédure** : Local IA Lab → nouveau backtest sur N+90j de données → nouvel artefact → revue humaine → signature → déploiement VPS via méthode prouvée
- **Versioning** : `calibration_v1.json`, `calibration_v2.json`, ... toujours conservés pour audit

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § recalibration

---

### D-17 — Tax export

**Question** : On code un module d'export tax CSV ou pas ?

**Options** :
- **A. Oui** : export annuel automatique au format de la juridiction (FR, DE, etc.)
- **B. Non** : export manuel via interface Binance une fois par an

**Recommandation** : **B** pour Phase 4 V1, **A** si jugé nécessaire après 1 an.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § tax_export

---

### D-18 — Audit halal annuel

**Question** : Qui réalise l'audit halal annuel ?

**Options** :
- **A. Mufti spécialisé crypto** (Joe Bradford, Faraz Adam, ou équivalent local) — coût ~200-500 USD/an
- **B. Auto-audit basé sur policy versioning** — gratuit mais moins défendable
- **C. Skip jusqu'à ce que le capital justifie le coût (> 50 k$)**

**Recommandation** : **A** dès Phase 4 si le budget le permet, sinon **B** + **A** en Phase 4 V2.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § halal_audit

---

## 6. Récapitulatif — toutes les décisions

| ID | Décision | Phase | Statut attendu avant phase |
|---|---|---|---|
| D-01 | Exchange cible | 0 | Prise et signée |
| D-02 | École fiqh | 0 | Prise et signée |
| D-03 | Stablecoin policy | 0 | Prise et signée |
| D-04 | VPS confirmé | 0 | Prise et signée |
| D-05 | Capital MICRO_LIVE | 0 | Prise et signée |
| D-06 | Plan scaling LIVE | 0 | Prise et signée |
| D-07 | Qui valide les gates | 0 | Prise et signée |
| D-08 | Qui signe calibrations | 0 | Prise et signée |
| D-09 | Engine C/D Option A/B | 1 | Prise avant T7/T8 |
| D-10 | V37 bricks timing | 1bis | Prise avant T12/T13 |
| D-11 | Seuils SHADOW | 2 | Prise avant SHADOW |
| D-12 | Engagement humain SHADOW | 2 | Prise avant SHADOW |
| D-13 | Pré-engagement anti-panique | 3 | Signée avant MICRO_LIVE |
| D-14 | Plan d'urgence | 3 | Documentée avant MICRO_LIVE |
| D-15 | Revue mensuelle | 4 | Engagement signé |
| D-16 | Recalibration trimestrielle | 4 | Procédure documentée |
| D-17 | Tax export | 4 | Décidée |
| D-18 | Audit halal annuel | 4 | Décidée |

**18 décisions** au total. **8 dès Phase 0** (avant tout code).

---

## 7. Format du fichier `DECISIONS_FROZEN_<date>.md`

Template attendu :

```markdown
# Decisions Frozen — V5.3 production deployment
**Date** : 2026-XX-XX
**Signé par** : <nom>
**Version** : 1

## Phase 0 — Décisions structurantes

### D-01 Exchange cible
Choix : Binance Spot
Justification : (brève)

### D-02 École fiqh
Choix : AAOIFI + Usmani, validation tiers annuelle
Justification : (brève)

[...etc pour D-01 à D-08...]

## Phase 1 — Décisions de code

[...]

## Phase 2 — Décisions SHADOW

[...]

## Phase 3 — Décisions MICRO_LIVE

[...]

## Phase 4 — Décisions LIVE

[...]

---

**Signature** : ___________ (date : ___________)
```

Ce fichier doit être committé dans le repo (`docs/decisions/`) avant le démarrage de chaque phase.

---

**Suite logique** : `11_DYNAMIC_THRESHOLDS_CATALOG.md` — catalogue exhaustif des seuils à calibrer.
