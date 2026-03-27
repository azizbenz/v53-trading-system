# V5.3 — BUILD-14 AI EDGE & MICROSTRUCTURE COMBATIVITY ADDENDUM
## Addendum spécialisé pour rendre V5.3 plus combative face aux flux manipulés, crowdés ou dominés par comportements machine
### Document dérivé du Build-14 canonique — sans remplacement du spec officiel
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : ADDENDUM BUILD-14 / V1
- Portée : compléter le Build-14 canonique avec des briques ciblées pour :
  - détecter les environnements microstructure trompeurs
  - mieux estimer la toxicité locale du marché
  - détecter le crowding comportemental
  - mesurer la durée de vie réelle de l’edge
  - améliorer le timing d’entrée/sortie d’un edge déjà validé
- Nature : addendum spécialisé de microstructure enrichie, régime enrichi et diversité effective d’edge
- Objectif : rendre V5.3 plus combative **sans** transformer la Light en pseudo-HFT ni introduire de logique opaque

## 0.1 Règle de hiérarchie documentaire

Ce document **ne remplace pas** :
- le master canonique V5.3
- le build plan officiel
- le `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`

Il doit être compris comme :
- un addendum ciblé
- une extension spécialisée du Build-14
- un guide d’implémentation pour des briques anti-flux trompeur / anti-crowding / timing enrichi

En cas de conflit :
1. le master canonique prime
2. le build plan officiel prime
3. le spec Build-14 officiel prime
4. ce document enrichit Build-14 sans le redéfinir

---

# 1. Principe central

Le but n’est pas de rendre V5.3 “plus IA” au sens marketing.

Le but est de rendre V5.3 plus **combative** en améliorant sa capacité à :

- détecter quand le carnet ment
- détecter quand le coût a déjà tué l’edge
- détecter quand plusieurs signaux sont en réalité le même edge crowdé
- détecter quand un comportement machine domine localement le flow
- améliorer le timing d’entrée/sortie d’un edge déjà validé
- éviter les faux signaux microstructure et les faux multi-edge

---

# 2. Règles non négociables

## 2.1 Cet addendum reste dans l’esprit Build-14

Toutes les briques proposées ici doivent respecter le mode d’introduction Build-14 :

### Étape 1
- lecture seule
- monitoring / analyse
- sans impact direct live

### Étape 2
- influence limitée
- pénalité légère
- meilleure lecture portefeuille
- alerte enrichie

### Étape 3
- seulement si utilité démontrée
- préparation éventuelle de Build-15 / 16 / 17

## 2.2 Interdictions absolues

Ces briques ne doivent jamais :
- devenir des moteurs autonomes
- créer un moteur E/F/G
- remplacer A/B/C/D
- remplacer le portfolio engine
- remplacer le risk backbone
- piloter seules l’entrée d’un trade
- imposer immédiatement un veto hard central
- introduire RL live
- introduire POMDP live
- introduire un “agent IA libre” de carnet

## 2.3 Principe d’influence

Une brique Build-14 enrichie doit influencer au début seulement :

- un score contextuel enrichi
- un score de toxicité
- une pénalité légère
- une alerte
- une lecture portefeuille plus fine
- une aide au timing d’exécution

Elle ne doit pas :
- casser la logique Light
- réécrire A/B
- recoder le sizing live
- ouvrir Complete implicitement

---

# 3. Gabarit mathématique obligatoire pour chaque brique

Chaque module de cet addendum doit être spécifié avec les 8 blocs suivants :

1. **Mission**
2. **Inputs**
3. **Formule / score**
4. **Seuils**
5. **Output contract**
6. **Politique d’influence**
7. **Métriques de validation**
8. **Dérives à éviter**

Aucun module ne doit “deviner”.
Tout module doit **calculer explicitement**.

---

# 4. Variables de référence

## 4.1 Variables canoniques héritées du Build-14

Order Flow Imbalance :
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]

Book imbalance :
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Microprice :
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Diversité effective spectrale :
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

## 4.2 Variables enrichies proposées

### Annulation relative
\[
CancelRate_t = \frac{N_t^{cancel}}{N_t^{add}+N_t^{cancel}+\varepsilon}
\]

### Persistance d’un mur de liquidité
\[
WallPersist_t = \frac{1}{w}\sum_{u=t-w+1}^{t}\mathbf{1}\{Q_u^{wall} \ge \theta_{wall}\}
\]

### Vitesse de disparition d’un mur
\[
WallDrop_t = \frac{Q_{t-1}^{wall} - Q_t^{wall}}{\max(Q_{t-1}^{wall},\varepsilon)}
\]

### Confirmation par volume exécuté
\[
ExecConfirm_t = \frac{V_t^{exec,aligned}}{V_t^{exec,total}+\varepsilon}
\]

### Évaporation de liquidité
\[
LiqEvap_t = \frac{\Delta Q_t^{-}}{Q_{t-1}+\varepsilon}
\]

### Pression microprice
\[
MicroDrift_t = \frac{MP_t - Mid_t}{Spread_t+\varepsilon}
\]

### Fraîcheur d’un signal
\[
Fresh_t = \exp(-\lambda \Delta t_{signal})
\]

### Fragilité d’exécution
\[
FragExec_t = \alpha_1 \cdot SpreadStress_t + \alpha_2 \cdot SlipRisk_t + \alpha_3 \cdot LatencyRisk_t + \alpha_4 \cdot LiqEvap_t
\]

### Demi-vie de l’edge
\[
HalfLife_{edge} = \inf\{\tau > 0 \mid Edge(\tau) \le 0.5 \cdot Edge(0)\}
\]

---

# 5. Module 1 — SPOOFING_SUSPICION_FILTER

## 5.1 Mission

Détecter les contextes où le carnet semble afficher de la liquidité trompeuse non confirmée par l’exécution réelle.

## 5.2 Inputs

- `CancelRate_t`
- `WallPersist_t`
- `WallDrop_t`
- `ExecConfirm_t`
- `BI_t`
- `ΔBI_t`
- `MicroDrift_t`

## 5.3 Score proposé

\[
S_{spoof,t} =
0.30 \cdot CancelRate_t
+ 0.25 \cdot WallDrop_t
+ 0.20 \cdot |\Delta BI_t|
+ 0.15 \cdot (1-ExecConfirm_t)
+ 0.10 \cdot |MicroDrift_t|
\]

Score normalisé dans \([0,1]\).

## 5.4 Seuils

- `CLEAR` si \(S_{spoof,t} < 0.35\)
- `WARNING` si \(0.35 \le S_{spoof,t} < 0.65\)
- `HIGH_SUSPICION` si \(S_{spoof,t} \ge 0.65\)

## 5.5 Output contract

- `spoof_score`
- `spoof_verdict`
- `top_components`
- `supporting_metrics`
- `reason_codes`

## 5.6 Politique d’influence

### Étape 1
- lecture seule
- logs / monitoring

### Étape 2
- pénalité légère sur contexte ou coût probable
- alerte enrichie

### Étape 3
- éventuellement dégradation plus forte si validé
- jamais hard veto central initial

## 5.7 Métriques de validation

- faux signaux évités
- amélioration de sélection
- drift du score
- fréquence utile
- coût CPU

## 5.8 Dérives à éviter

- confondre carnet vide et spoofing
- sur-réagir aux petits échantillons
- faire du spoof score une vérité absolue

---

# 6. Module 2 — LIQUIDITY_WALL_PERSISTENCE_MONITOR

## 6.1 Mission

Distinguer :
- mur réel/persistant
- mur décoratif
- mur possiblement spoofé

## 6.2 Inputs

- `Q_t^{wall}`
- `WallPersist_t`
- `WallDrop_t`
- `ExecConfirm_t`
- `OFI_t`
- `MicroDrift_t`

## 6.3 Scores proposés

### Solidité du mur
\[
S_{wall\_solid,t} =
0.40 \cdot WallPersist_t
+ 0.30 \cdot ExecConfirm_t
+ 0.20 \cdot \max(0, OFI_t^{aligned})
+ 0.10 \cdot \max(0, MicroDrift_t^{aligned})
\]

### Mur trompeur
\[
S_{wall\_fake,t} =
0.45 \cdot WallDrop_t
+ 0.30 \cdot (1-ExecConfirm_t)
+ 0.15 \cdot CancelRate_t
+ 0.10 \cdot |\Delta BI_t|
\]

## 6.4 Seuils

- `REAL_WALL`
- `UNCERTAIN_WALL`
- `FAKE_WALL_SUSPECTED`

## 6.5 Output contract

- `wall_solid_score`
- `wall_fake_score`
- `wall_verdict`
- `side`
- `reason_codes`

## 6.6 Politique d’influence

- meilleure lecture contexte continuation/réversion
- pénalité légère si mur fake suspected
- pas de trade créé automatiquement

## 6.7 Validation

- amélioration de qualité d’entrée
- réduction des faux supports/résistances
- cohérence avec exécutions réelles

## 6.8 Dérives

- traiter toute grosse taille comme mur réel
- ignorer l’absence de confirmation par prints

---

# 7. Module 3 — LIQUIDITY_EVAPORATION_DETECTOR

## 7.1 Mission

Détecter les contextes où la liquidité visible s’évapore avant ou pendant l’exécution.

## 7.2 Inputs

- `LiqEvap_t`
- `CancelRate_t`
- spread
- slippage attendu
- `ExecConfirm_t`

## 7.3 Score proposé

\[
S_{evap,t} =
0.35 \cdot LiqEvap_t
+ 0.25 \cdot CancelRate_t
+ 0.20 \cdot SpreadStress_t
+ 0.20 \cdot SlipRisk_t
\]

## 7.4 Seuils

- `STABLE`
- `FRAGILE`
- `EVAPORATING`

## 7.5 Politique d’influence

- dégradation de la qualité d’entrée
- hausse du coût prudent attendu
- aide au sniper d’entrée/sortie

## 7.6 Validation

- amélioration CE
- réduction des entrées dans des trous de liquidité
- baisse des phantom trades

---

# 8. Module 4 — MARKET_TOXICITY_LAYER

## 8.1 Mission

Fournir une lecture synthétique de la toxicité locale du marché.

## 8.2 Inputs

- `S_spoof`
- `S_evap`
- `FragExec_t`
- `|MicroDrift_t|`
- `OFI_t` instable
- spread stress

## 8.3 Score proposé

\[
S_{tox,t} =
0.25 \cdot S_{spoof,t}
+ 0.20 \cdot S_{evap,t}
+ 0.20 \cdot FragExec_t
+ 0.15 \cdot SpreadStress_t
+ 0.10 \cdot OFIInstab_t
+ 0.10 \cdot |MicroDrift_t|
\]

## 8.4 Seuils

- `LOW_TOXICITY`
- `MEDIUM_TOXICITY`
- `HIGH_TOXICITY`

## 8.5 Politique d’influence

- lecture seule puis pénalité légère
- dégradation du score de timing d’entrée
- dégradation de la confiance
- aide au ranking portefeuille

## 8.6 Validation

- faux signaux évités
- coût attendu mieux aligné avec coût observé
- amélioration CE conditionnelle

---

# 9. Module 5 — MACHINE_DOMINATED_REGIME_DETECTOR

## 9.1 Mission

Détecter des régimes de flow dominés par comportements machine ou très réactionnels.

## 9.2 États recommandés

- `NORMAL_FLOW`
- `DIRECTIONAL_FLOW`
- `CANCEL_HEAVY_FLOW`
- `CROWDED_REACTIONAL_FLOW`
- `LIQUIDITY_EVACUATION_FLOW`
- `PSEUDO_BREAKOUT_FLOW`

## 9.3 Inputs

- `CancelRate_t`
- `OFI_t`
- `BI_t`
- `MicroDrift_t`
- spread stress
- rythme des changements de carnet
- persistance du flow

## 9.4 Score d’état conceptuel

\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]

avec des features enrichies incluant microstructure, cancellations et crowding local.

## 9.5 Politique d’influence

- lecture seule initialement
- pénalité légère si état fortement hostile à A/B
- préparation pour Build-15/16 seulement après preuve

## 9.6 Validation

- stabilité des états
- ambiguïtés détectées
- amélioration segmentation utile
- non-régression A/B

---

# 10. Module 6 — EDGE_HALF_LIFE_MONITOR

## 10.1 Mission

Mesurer la durée de vie économique d’un edge après apparition du signal.

## 10.2 Inputs

- timestamp signal
- timestamp entrée
- coût attendu à différents horizons
- CE attendue conditionnelle
- MFE/MAE conditionnelles
- distance à invalidation

## 10.3 Mesures proposées

### Demi-vie de l’edge
\[
HalfLife_{edge} = \inf\{\tau > 0 \mid Edge(\tau) \le 0.5 \cdot Edge(0)\}
\]

### Dégradation relative
\[
Decay_t = 1 - \frac{Edge(t)}{Edge(0)+\varepsilon}
\]

## 10.4 Sorties

- `half_life_estimate`
- `decay_score`
- `entry_urgency`
- `exit_urgency`

## 10.5 Politique d’influence

- aide au timing d’entrée
- aide au governor de sortie
- alerte sur edge crowdé ou vite consommé

## 10.6 Validation

- meilleure qualité d’entrée
- réduction des entrées tardives
- meilleure CE conditionnelle

---

# 11. Module 7 — CROWDING_SIGNATURE_MONITOR

## 11.1 Mission

Détecter quand plusieurs signaux différents sont en réalité la même exposition comportementale crowdée.

## 11.2 Inputs

- corrélations moteur/moteur
- corrélations moteur/paire
- simultanéité des activations
- facteur BTC caché
- similarité des patterns de carnet
- `K_eff^{spec}`

## 11.3 Score proposé

\[
S_{crowd} =
0.30 \cdot PairSynchrony
+ 0.25 \cdot EngineCorr
+ 0.20 \cdot HiddenBTCFactor
+ 0.15 \cdot PatternSimilarity
+ 0.10 \cdot \left(1-\frac{K_{eff}^{spec}}{K}\right)
\]

## 11.4 Seuils

- `DIVERSE`
- `PARTLY_CROWDED`
- `HIGHLY_CROWDED`

## 11.5 Politique d’influence

- lecture portefeuille enrichie
- alerte redondance
- pénalité légère de diversification
- jamais justification automatique d’un veto central

## 11.6 Validation

- meilleure lecture de faux multi-edge
- amélioration arbitrage portefeuille
- cohérence avec `K_eff`

---

# 12. Module 8 — EXECUTION_FRAGILITY_SCORE

## 12.1 Mission

Mesurer la fragilité économique d’un trade à l’exécution.

## 12.2 Inputs

- spread stress
- slippage risk
- latency risk
- `S_evap`
- phantom trade risk

## 12.3 Score proposé

\[
S_{frag,t} =
0.25 \cdot SpreadStress_t
+ 0.25 \cdot SlipRisk_t
+ 0.20 \cdot LatencyRisk_t
+ 0.20 \cdot S_{evap,t}
+ 0.10 \cdot PhantomRisk_t
\]

## 12.4 Seuils

- `ROBUST_EXECUTION`
- `FRAGILE_EXECUTION`
- `VERY_FRAGILE_EXECUTION`

## 12.5 Politique d’influence

- pénalité légère sur timing
- meilleure lecture CE
- alerte portefeuille/exécution

## 12.6 Validation

- réduction des trades stériles
- meilleure cohérence coût attendu / coût observé
- baisse des phantom trades

---

# 13. Module 9 — CONDITIONAL_CE_SURFACE

## 13.1 Mission

Construire une lecture conditionnelle de la capital efficiency attendue selon le contexte.

## 13.2 Variables conditionnantes

- moteur
- paire
- régime
- état toxicité
- état crowding
- fenêtre horaire
- facteur BTC
- niveau de coût

## 13.3 Surface conceptuelle

\[
CE_{cond} = \mathbb{E}\left[\frac{PnL}{x \cdot h} \middle| moteur, paire, régime, toxicité, crowding, temps\right]
\]

## 13.4 Politique d’influence

- lecture enrichie portefeuille
- support au ranking
- meilleure comparaison opportunités

## 13.5 Validation

- amélioration arbitrage entre opportunités
- meilleure stabilité CE live/shadow
- lisibilité opérateur

---

# 14. Module 10 — MICRO_EDGE_ENTRY_TIMING_LAYER

## 14.1 Mission

Améliorer **le timing d’entrée** d’un trade déjà validé par A/B/C/D, sans créer de trade de manière autonome.

## 14.2 Inputs

- `CE_cond`
- `expected_cost_now`
- `expected_cost_baseline`
- `S_tox`
- `S_frag`
- `Fresh_t`
- `wall_verdict`
- `spoof_verdict`
- `support_micro`
- `HalfLife_edge`

## 14.3 Score d’entrée proposé

\[
S_{entry} =
0.25 \cdot \Delta CE^{+}
+ 0.20 \cdot \Delta Cost^{-}
+ 0.20 \cdot SupportMicro
+ 0.15 \cdot (1-S_{tox})
+ 0.10 \cdot Fresh_t
+ 0.10 \cdot (1-S_{frag})
\]

où :
- \(\Delta CE^{+}\) = gain relatif de CE attendu
- \(\Delta Cost^{-}\) = amélioration relative du coût attendu

## 14.4 Seuils

- `ENTER_NOW` si \(S_{entry} \ge 0.65\)
- `WAIT` si \(0.35 \le S_{entry} < 0.65\)
- `ABORT` si \(S_{entry} < 0.35\)

## 14.5 Politique d’influence

- lecture seule initialement
- ensuite raffinement de timing
- jamais création autonome de trade
- jamais bypass du moteur ou du portfolio

## 14.6 Validation

- amélioration coût moyen d’entrée
- amélioration CE
- moins d’entrées toxiques
- pas de baisse de fréquence utile excessive

## 14.7 Dérives à éviter

- transformer ce module en mini-moteur autonome
- chercher un timing parfait au prix de signaux perdus
- introduire de l’optimal stopping opaque en Light

---

# 15. Module 11 — MICRO_EDGE_EXIT_GOVERNOR

## 15.1 Mission

Améliorer **le timing de sortie** d’un trade déjà vivant.

## 15.2 Inputs

- `edge_decay`
- `S_tox`
- `S_frag`
- `breakout_hostility`
- coût de maintien
- proximité invalidation
- MFE/MAE conditionnelles

## 15.3 Score de sortie proposé

\[
S_{exit} =
0.30 \cdot EdgeDecay
+ 0.20 \cdot S_{tox}
+ 0.15 \cdot S_{frag}
+ 0.15 \cdot BreakoutHostility
+ 0.10 \cdot CostToStay
+ 0.10 \cdot InvalidationProximity
\]

## 15.4 Seuils

- `HOLD`
- `TRIM`
- `EXIT`

## 15.5 Politique d’influence

- lecture/analyse initiale
- ensuite aide à sortie / trim / protection
- jamais remplacement complet de la logique d’invalidation des moteurs

## 15.6 Validation

- amélioration CE réalisée
- réduction des sorties tardives
- drawdown local mieux contrôlé

---

# 16. Module 12 — ADVERSARIAL_BREAKOUT_FALSE_POSITIVE_MODEL

## 16.1 Mission

Détecter les cassures visibles mais économiquement déjà compromises ou manipulées.

## 16.2 Inputs

- distance à la cassure
- volume de confirmation
- persistance
- réintégration rapide du range
- `S_tox`
- `S_spoof`
- `S_frag`

## 16.3 Score proposé

\[
S_{fake\_brk} =
0.25 \cdot ReentryRisk
+ 0.20 \cdot (1-Persistence)
+ 0.20 \cdot (1-VolumeConfirm)
+ 0.15 \cdot S_{tox}
+ 0.10 \cdot S_{spoof}
+ 0.10 \cdot DistanceOverextension
\]

## 16.4 Politique d’influence

- lecture préparatoire Build-15
- légère pénalité sur continuation si validé
- jamais moteur C implicite

---

# 17. Module 13 — CAPITAL_COMPETITION_MONITOR

## 17.1 Mission

Mesurer quelles opportunités consomment du capital alors qu’elles dominent mal économiquement les alternatives.

## 17.2 Inputs

- ranking final
- coût d’opportunité
- `CE_cond`
- diversité d’edge
- consommation de caps portefeuille
- crowding signature

## 17.3 Mesure proposée

\[
OppCost_i = \max_{j \in \mathcal{A}_t}\left(CE_{cond,j} - CE_{cond,i}\right)^{+}
\]

\[
S_{capital\_competition,i} =
0.50 \cdot OppCost_i
+ 0.30 \cdot CrowdPenalty_i
+ 0.20 \cdot CapConsumption_i
\]

## 17.4 Politique d’influence

- lecture portefeuille enrichie
- alerte d’arbitrage sous-optimal
- support aux choix Build-8/9

---

# 18. Synthèse des influences autorisées

## 18.1 Lecture seule
Tous les modules commencent en lecture seule.

## 18.2 Influence limitée autorisée
Après validation, influence limitée possible via :
- pénalité légère
- alerte enrichie
- lecture portefeuille enrichie
- timing d’entrée/sortie amélioré

## 18.3 Influences interdites au début
- hard block central
- sizing live réécrit
- reclassification brutale des moteurs
- activation implicite Build-15/16
- passage automatique à Complete

---

# 19. Métriques globales obligatoires de validation

Chaque module proposé ici doit être évalué au minimum sur :

- coût CPU / latence induite
- amélioration éventuelle de sélection
- faux signaux évités
- drift des features
- fréquence d’activation utile
- amélioration CE
- amélioration de coût prudent
- amélioration de lecture portefeuille
- non-régression Light
- lisibilité opérateur

---

# 20. Merge gates spécifiques à cet addendum

Refuser l’implémentation si :
- le module ne possède pas de formule explicite
- le module “devine” au lieu de calculer
- le module crée des trades seul
- le module devient un hard block central immédiat
- le module dégrade A/B sans gain économique clair
- le coût CPU devient disproportionné
- le module sert seulement à faire “plus IA”

---

# 21. Instructions directes à Claude

Tu dois implémenter ces briques comme **enablers Build-14** et respecter strictement les règles suivantes :

1. ne remplace pas le Build-14 canonique
2. implémente ces briques comme addendum spécialisé
3. chaque brique doit avoir :
   - mission
   - inputs
   - formule/score
   - seuils
   - output contract
   - politique d’influence
   - métriques de validation
4. aucune brique ne doit devenir un moteur autonome
5. aucune brique ne doit créer un moteur E/F/G
6. aucune brique ne doit introduire RL/POMDP live
7. toutes les briques commencent en lecture seule
8. influence limitée seulement après preuve d’utilité
9. le `micro_edge_entry_timing_layer` et le `micro_edge_exit_governor` ne doivent jamais bypass moteurs/risk/portfolio
10. la validation doit mesurer :
   - faux signaux évités
   - amélioration CE
   - qualité de lecture coût
   - stabilité
   - coût CPU
   - non-régression Light

---

# 22. Verdict final

Le bon modèle pour rendre V5.3 plus combative est :

> **plus lucide sur la toxicité**
>
> **plus lucide sur le crowding**
>
> **plus lucide sur la durée de vie de l’edge**
>
> **plus lucide sur la qualité d’exécution**
>
> **sans devenir un bot opaque ou un pseudo-HFT**

Autrement dit :

- moins naïve sur le carnet
- moins naïve sur les faux breakouts
- moins naïve sur la fausse diversité d’edge
- meilleure sur le timing d’entrée/sortie
- toujours disciplinée par le canon V5.3

> oui à la combativité,
> non au gadget “IA”.
