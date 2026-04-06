# V5.3 — PATCH P2 MATH CORRECTION AND NORMALIZATION
## Feature Dictionary Unification / Equation Hygiene / Canonical Runtime Math Fixes
### Date : 2026-04-05
### Statut : PATCH NORMATIF MATHÉMATIQUE
### Portée : Local AI Lab / VPS Annexe Math / Engines A-B-C-D / Risk / Scoring / Artifact Features

---

# 0. Objet

Ce document corrige les ambiguïtés mathématiques restantes du corpus V5.3 après :
- le freeze P0 du langage partagé
- le patch P1 de politiques transverses

Il traite uniquement les problèmes de math / features / normalisation qui peuvent provoquer :
- du code incohérent entre Lab et VPS
- des implémentations divergentes entre Claude / Codex
- des variables non définies en runtime
- des poids inventés localement sans traçabilité
- des formules circulaires ou semi-orphelines

Ce document n’a pas pour but de “sur-optimiser” la recherche.
Il fixe une **base canonique minimale, stable, codable et audit-able**.

---

# 1. Décisions centrales

Ce patch tranche cinq points :

1. **unifier le Physics Feature Dictionary**
2. **donner un statut canonique à `Participation_t`**
3. **fixer la lecture correcte du double delta proxy**
4. **définir `Fragility_t` sans circularité**
5. **retirer `ReformationScore_t` du runtime canonique V1 et le remplacer par des grandeurs déjà définies**

Règle directrice :

> aucune équation runtime canonique ne doit dépendre
> - d’une variable non définie
> - d’un coefficient implicite
> - d’une normalisation laissée à l’interprétation du développeur

---

# 2. Physics Feature Dictionary — version canonique corrigée

## 2.1 Source de vérité

La liste suivante devient la version canonique unifiée des familles autorisées pour :
- le Lab
- la distillation
- les artifacts
- les hooks VPS
- les annexes math

Familles autorisées :

1. `delta_proxy`
2. `cumulative_delta`
3. `order_flow_imbalance`
4. `book_imbalance`
5. `microprice_deviation`
6. `spread_regime`
7. `slippage_friction_proxy`
8. `volume_profile`
9. `poc_vah_val`
10. `hvn_lvn`
11. `void_score`
12. `sweep_score`
13. `absorption_score`
14. `false_breakout_score`
15. `toxcity_fragility_survivability`
16. `book_resiliency`
17. `refill_speed`
18. `regime_hurst_context_enrichment`
19. `portfolio_overlap_crowding_cluster`

## 2.2 Clarification de nomenclature

Les correspondances autorisées sont :

- `OFI` = `order_flow_imbalance`
- `OBI` = `book_imbalance`
- `delta proxy` = `delta_proxy`
- `cumulative delta` = `cumulative_delta`
- `book resiliency` = `book_resiliency`
- `execution survivability score` = inclus dans la famille `toxcity_fragility_survivability` mais exporté comme feature distincte `execution_survivability_score`

## 2.3 False Breakout et Void Score

Les deux sont canoniques.
Aucun document ne doit plus en inclure un en oubliant l’autre.

- `void_score` = canonique
- `false_breakout_score` = canonique

## 2.4 Participation_t

`Participation_t` n’est **pas** une famille autonome.

C’est une **helper feature autorisée** appartenant à la famille :

- `slippage_friction_proxy`

Donc :

- autorisée dans le Lab
- autorisée dans les calculs de `SlipProxy`
- autorisée comme feature intermédiaire documentée
- non listée comme “famille racine” indépendante

Formule canonique :

\[
Participation_t = \frac{OrderSize_t}{\overline{Vol}_{1m,t} + \epsilon}
\]

---

# 3. Delta proxy — correction canonique

## 3.1 Deux formes admises

Deux formes restent autorisées :

### A. Version douce — défaut canonique

\[
\Delta V_t^{proxy,soft} =
\frac{C_t - O_t}{\max(H_t - L_t,\epsilon)} \cdot V_t
\]

Usage par défaut :
- Lab
- replay
- calibration
- distillation
- diagnostics
- comparaisons inter-régimes

### B. Version signe — fallback robuste

\[
\Delta V_t^{proxy,sign} =
\operatorname{sign}(C_t - O_t) \cdot V_t
\]

Usage :
- fallback runtime
- validation croisée
- données appauvries
- scénarios dégradés

## 3.2 Règle de nommage

Les deux variantes ne doivent jamais coexister sous le même identifiant.

Nommage recommandé :
- `delta_proxy_soft_1m`
- `delta_proxy_sign_1m`

## 3.3 Règle de priorité

En absence de justification contraire :
- le Lab utilise `delta_proxy_soft`
- la VPS peut utiliser `delta_proxy_sign` comme fallback documenté
- toute substitution doit être tracée dans le lineage

---

# 4. Primitives de normalisation obligatoires

## 4.1 Objet

Les poids `w_i`, `d_i`, `c_i`, `b_i`, `beta_i`, `gamma_i`, `eta_i`, `theta_i`
ne suffisent pas.
Encore faut-il que les entrées soient comparables.

Donc le corpus doit figer des primitives minimales de normalisation.

## 4.2 Clip unitaire

\[
clip01(x) = \min(1,\max(0,x))
\]

## 4.3 Z-score positif borné

\[
zplus(x; z_{cap}) = clip01\left(\frac{\max(x,0)}{z_{cap}}\right)
\]

Par défaut en V1 :

\[
z_{cap} = 3.0
\]

sauf justification documentaire explicite.

## 4.4 Ratio borné

\[
capratio(x;c) = clip01\left(\frac{x}{c}\right)
\]

où `c` est un cap documenté et versionné.

## 4.5 Règle runtime

Aucune formule composite runtime ne doit consommer :
- une grandeur non bornée
- ou une z-value brute
sans préciser la normalisation utilisée.

---

# 5. Sweep Score — correction canonique

## 5.1 Variables d’entrée

\[
WickRatio_t = \frac{|Wick_t|}{ATR_t + \epsilon}
\]

\[
VolBurst_t = \frac{V_t}{\overline{V}_{20}(t) + \epsilon}
\]

\[
Reject_t \in \{0,1\}
\]

avec :
- `Reject_t = 1` si le close réintègre la plage de référence définie par la logique moteur
- `Reject_t = 0` sinon

## 5.2 Forme corrigée

La forme canonique runtime V1 devient :

\[
SweepScore_t =
0.45 \cdot capratio(WickRatio_t; 3.0)
+ 0.35 \cdot capratio(VolBurst_t; 3.0)
+ 0.20 \cdot Reject_t
\]

## 5.3 Règle de calibration

Le Lab peut recalibrer les poids et caps, mais seulement si :
- les poids restent non négatifs
- la somme des poids vaut 1
- les caps sont explicités dans l’artifact / config / lineage
- la nouvelle version passe preuve et validation

## 5.4 Classe

- runtime V1 : **Classe A** si implémenté avec la forme corrigée ci-dessus
- sinon : **Classe B** ou retrait du runtime

---

# 6. Fragility Score — définition canonique

## 6.1 Objet

`Fragility_t` doit mesurer une fragilité microstructurelle
sans dépendre de `Toxicity_t`.

La circularité est interdite.

## 6.2 Forme canonique

La forme canonique V1 est :

\[
Fragility_t =
0.40 \cdot zplus(SpreadZ_t; 3.0)
+ 0.35 \cdot (1 - clip01(Resiliency_t))
+ 0.25 \cdot (1 - clip01(RefillSpeed_t^{norm}))
\]

où :

\[
RefillSpeed_t^{norm} = capratio(\max(RefillSpeed_t,0); refill_{cap})
\]

## 6.3 Lecture

La fragilité augmente si :
- le spread s’élargit
- la résilience est mauvaise
- le refill est lent

## 6.4 Règle de cap

`refill_cap` doit être :
- documenté
- versionné
- fixé par paire / marché / environnement si nécessaire
- calibré dans le Lab
- jamais laissé implicite

## 6.5 Classe

- par défaut : **Classe B**
- devient runtime si la calibration de `refill_cap` est tracée

---

# 7. Toxicity Score — correction canonique

## 7.1 Objet

La toxicité ne doit plus dépendre d’une variable non définie
ni d’une grandeur non bornée sans règle.

## 7.2 Entrées

On impose :

\[
OFIAbs_t^{norm} = clip01(|OFI_t^{norm}|)
\]

\[
Spread_t^{tox} = zplus(SpreadZ_t; 3.0)
\]

\[
VolJump_t^{norm} = capratio(\max(VolJump_t,0); voljump_{cap})
\]

et `Fragility_t` est celui défini à la section 6.

## 7.3 Forme canonique

\[
Toxicity_t =
0.35 \cdot OFIAbs_t^{norm}
+ 0.25 \cdot Spread_t^{tox}
+ 0.20 \cdot VolJump_t^{norm}
+ 0.20 \cdot Fragility_t
\]

## 7.4 Règle de cap

`voljump_cap` :
- doit être documenté
- peut être calibré par paire / régime
- ne doit jamais être implicite

## 7.5 Classe

- par défaut : **Classe B**
- activable runtime seulement après validation shadow / replay

---

# 8. Execution Survivability Score — correction canonique

## 8.1 Forme corrigée

\[
ESS_t =
0.30 \cdot (1 - zplus(SpreadZ_t; 3.0))
+ 0.30 \cdot clip01(Resiliency_t)
+ 0.20 \cdot clip01(RefillSpeed_t^{norm})
- 0.10 \cdot Toxicity_t
- 0.10 \cdot Fragility_t
\]

## 8.2 Interprétation

L’ESS augmente si :
- le spread reste maîtrisé
- la résilience est correcte
- le refill est bon

Il baisse si :
- la toxicité grimpe
- la fragilité grimpe

## 8.3 Classe

- **Classe B** par défaut
- peut entrer en filtre runtime après preuve

---

# 9. SlipProxy et MicroFriction — correction de discipline

## 9.1 SlipProxy

La formule canonique reste :

\[
SlipProxy_t = a_1 SpreadRel_t + a_2 \sigma_{1m,t} + a_3 Participation_t
\]

mais avec règle impérative :

- les `a_i` doivent être non négatifs
- la somme recommandée vaut 1
- la configuration doit être documentée
- à défaut, ils sont marqués `TO_CALIBRATE`

## 9.2 MicroFriction

La forme canonique V1 devient :

\[
MicroFriction_t =
0.40 \cdot zplus(SpreadZ_t; 3.0)
+ 0.35 \cdot SlipProxy_t^{norm}
+ 0.15 \cdot Fragility_t
+ 0.10 \cdot Toxicity_t
\]

avec :

\[
SlipProxy_t^{norm} = capratio(SlipProxy_t; slip_{cap})
\]

## 9.3 Statut

- `SlipProxy_t` = runtime sobre possible
- `MicroFriction_t` = **Classe B** tant que `slip_cap` n’est pas calibré par environnement

---

# 10. False Breakout Score — correction de statut

## 10.1 Forme conservée

\[
FBO_t =
\alpha_1 SweepScore_t
+ \alpha_2 AbsorptionScore_t
+ \alpha_3 \mathbb{1}\{d_t^{HVN} < \tau_{hvn}\}
- \alpha_4 DeltaConfirm_t
\]

## 10.2 Discipline

Cette formule reste valide conceptuellement,
mais tant que :
- `DeltaConfirm_t`
- `d_t^{HVN}`
- `\tau_{hvn}`

ne sont pas tous définis de manière homogène dans le corpus,
elle doit rester :

- **Classe B** au mieux
- ou **Classe C** si les readers / caps / unités ne sont pas figés

## 10.3 Règle

Aucun développeur ne doit promouvoir `FBO_t` en runtime canonique
sur une interprétation locale de `DeltaConfirm_t`.

---

# 11. Engine A / B / C / D — corrections ciblées

## 11.1 Engine A

La formule peut conserver `Fragility_t`
car celui-ci est désormais défini.

## 11.2 Engine B

La formule peut conserver `SweepScore_t`, `AbsorptionScore_t`, `SpreadZ_t`, `Toxicity_t`
sous réserve d’utiliser les versions normalisées / canonisées.

## 11.3 Engine C

La formule peut conserver `Fragility_t`,
mais `VoidScore_t`, `HVNProximity_t` et `FBO_t` doivent rester shadow-validés si leurs readers ne sont pas encore figés.

## 11.4 Engine D — correction majeure

`ReformationScore_t` est retiré du runtime canonique V1.

La forme corrigée devient :

\[
D_t^{phys} =
D_t^{base}
+ \theta_1 AbsorptionScore_t^{norm}
+ \theta_2 clip01(Resiliency_t)
+ \theta_3 clip01(RefillSpeed_t^{norm})
- \theta_4 Toxicity_t
- \theta_5 Overextension_t^{norm}
\]

avec :
- `theta_i >= 0`
- calibration documentée
- somme recommandée = 1 sur les composantes positives et négatives séparément, ou autre convention explicitée

## 11.5 Conséquence

`ReformationScore_t` peut rester :
- concept de recherche
- variable de futur addendum
- feature de Lab si formellement définie plus tard

Mais il n’appartient plus au runtime canonique V1.

---

# 12. Règle de coefficients

## 12.1 Règle générale

Tout coefficient non défini dans le corpus doit être soit :

- remplacé par une valeur canonique par défaut
- soit marqué `TO_CALIBRATE`
- soit retirer la formule du runtime

## 12.2 Valeurs canonisées par ce patch

Sont désormais canonisés :
- les poids de `SweepScore_t`
- les poids de `Fragility_t`
- les poids de `Toxicity_t`
- les poids de `ESS_t`
- les poids de `MicroFriction_t`

## 12.3 Valeurs restant à calibrer

Restent `TO_CALIBRATE` par défaut :
- `a_i` de `SlipProxy_t`
- `alpha_i` de `FBO_t`
- `beta_i`, `gamma_i`, `eta_i`, `theta_i` moteurs
- `slip_cap`
- `refill_cap`
- `voljump_cap`

Ces paramètres peuvent être proposés par le Lab,
mais ne deviennent canoniques que si :
- documentés
- versionnés
- validés
- promus explicitement

---

# 13. Règle de classes A / B / C

## 13.1 Règle automatique

Toute équation qui contient :
- une variable non définie
- un cap non défini
- un reader non défini
- une unité non définie
- une normalisation implicite

est automatiquement dégradée au minimum en **Classe C**
jusqu’à correctif documentaire.

## 13.2 Conséquence pratique

Le label “Classe A” ne suffit pas.
Il doit être cohérent avec :
- la définition complète des entrées
- la calibration minimale
- la stabilité d’implémentation

---

# 14. Propagation documentaire requise

Les corrections de ce patch doivent être propagées au minimum dans :

- `2026-04-04_V53_LOCAL_AI_LAB_FINAL_UNIQUE_CANON.md`
- `2026-04-04_V53_LOCAL_AI_LAB_ANNEXE_MATH_AND_BUILD_PLAN.md`
- `2026-04-04_V53_VPS_ANNEXE_MATH_RUNTIME_MARKET_PHYSICS.md`
- `2026-04-04_V53_LOCAL_AI_LAB_IMPLEMENTATION_BLUEPRINT.md`

## 14.1 Dans le canon final
- feature dictionary unifié
- statut de `Participation_t`
- retrait de `ReformationScore_t` du runtime canonique

## 14.2 Dans l’annexe math Lab
- delta proxy par défaut
- weights fixés ou `TO_CALIBRATE`
- `Fragility_t` défini
- `ESS_t` aligné
- note explicite sur `false_breakout_score` et `void_score`

## 14.3 Dans l’annexe math VPS
- normalisation canonique
- `SweepScore_t`, `Toxicity_t`, `ESS_t`, `MicroFriction_t` corrigés
- Engine D sans `ReformationScore_t`

## 14.4 Dans le blueprint
- champ `equation_id`
- référence au feature dictionary source of truth
- caps / weights versionnés dans le lineage ou config

---

# 15. Conclusion finale

Le correctif mathématique ne doit pas transformer le corpus en thèse.

Il doit empêcher trois choses :
- le code contradictoire
- la magie locale
- les scores composites impossibles à auditer

La règle correcte devient :

> une feature doit être définie
>
> une normalisation doit être bornée
>
> un coefficient doit être canonique ou `TO_CALIBRATE`
>
> une variable runtime non définie n’a pas le droit d’exister
