# V5.3 — TARGET DOCTRINE DECISION: SINGLE PROD-SAFE CHAIN
## Date : 2026-04-02
## Statut : PROPOSITION DE GOUVERNANCE

---

# 0. Objet

Ce document formalise une **doctrine cible proposée** pour simplifier la V5.3
et la rendre plus lisible en production.

Il ne remplace pas encore le canon actif.

Son rôle est de décider explicitement si la V5.3 doit rester sur :

- le canon actuel `LIGHT -> COMPLETE`

ou basculer vers :

- une **chaîne unique prod-safe**

---

# 1. Constats

Le canon actif a déjà beaucoup convergé vers une réalité opérationnelle :

- toute l'architecture utile est développée
- le `Shadow intégral` active déjà A/B/C/D + Build-14 à 100% en observation
- les gates Build-11 / Build-12 / Build-13 sont déjà stricts

Mais il reste une tension doctrinale :

- le canon conserve deux profils de rollout : `LIGHT` et `COMPLETE`
- alors que la phase Build-11 observe déjà la solution intégrale utile

Cette tension crée trois risques :

- ambiguïté documentaire
- ambiguïté de code sur ce qui est “profil” vs “phase”
- ambiguïté opérateur sur ce qui est réellement prêt à passer en réel

---

# 2. Canon actif

Le canon actuel dit en substance :

1. `profil=LIGHT`, `runtime_mode=SHADOW`
   - `Shadow intégral`
   - 30 jours minimum
2. `profil=LIGHT`, `runtime_mode=MICRO_LIVE`
   - minimum 7 jours
3. `profil=LIGHT`, `runtime_mode=LIVE`
   - `Live-Light`
4. `profil=COMPLETE`, `runtime_mode=SHADOW`
   - `Complete Shadow`
   - 30 jours minimum supplémentaires
5. `profil=COMPLETE`, `runtime_mode=LIVE`
   - `Live-Complete`

Lecture critique :

- la doctrine garde une seconde rampe `COMPLETE`
- mais le Build-11 a déjà déplacé beaucoup de validation utile en amont

---

# 3. Doctrine cible proposée

La doctrine cible proposée est :

## 3.1 Principe général

- une seule solution V5.3 complète, développée dès le départ
- une seule chaîne de montée en preuve puis en réel
- aucune seconde doctrine `LIGHT puis COMPLETE` pour la promotion réelle

## 3.2 Chaîne cible

1. **Développement complet prod-safe**
   - toutes les composantes existent
   - tous les garde-fous existent
   - aucun moteur ou enabler critique laissé “théorique”

2. **Shadow preuve — 30 jours**
   - tous les modules utiles actifs
   - données réelles
   - rapport, logs, validation, verdicts

3. **Shadow confirmation — 15 jours**
   - après approbation du rapport Shadow 30 jours
   - sur release gelée
   - destiné à confirmer que le système tient sans dérive avant capital réel

4. **Micro-live — 15 jours**
   - validation coût réel
   - validation exécution réelle
   - validation réconciliation réelle

5. **Live**
   - seulement après réussite des phases précédentes

## 3.3 Règle d'interprétation

Dans cette doctrine cible :

- le système ne parle plus de `LIGHT rollout` puis `COMPLETE rollout`
- il parle d'une seule V5.3 complète
- les phases sont :
  - `SHADOW_PROOF_30D`
  - `SHADOW_CONFIRMATION_15D`
  - `MICRO_LIVE_15D`
  - `LIVE`

## 3.4 Souveraineté opérateur et contrôles manuels

La doctrine cible proposée ajoute une exigence forte :

- toutes les dégradations visibles de phase doivent être **déclenchées
  manuellement par l'opérateur** via l'UI locale
- un **kill manuel d'urgence** doit exister comme action opérateur explicite
- aucune descente de phase ne doit dépendre d'un bricolage shell non traçable

Transitions manuelles à prévoir :

- `LIVE -> MICRO_LIVE_15D`
- `LIVE -> SHADOW_CONFIRMATION_15D`
- `LIVE -> SHADOW_PROOF_30D`
- `MICRO_LIVE_15D -> SHADOW_CONFIRMATION_15D`
- `MICRO_LIVE_15D -> SHADOW_PROOF_30D`
- `LIVE -> HALTED`
- `MICRO_LIVE_15D -> HALTED`

Exigences UI locales futures :

- bouton `KILL MANUEL`
- action `SET_HALTED`
- action `DOWNGRADE_TO_MICRO_LIVE`
- action `DOWNGRADE_TO_SHADOW_CONFIRMATION`
- action `DOWNGRADE_TO_SHADOW_PROOF`
- confirmation explicite
- saisie du motif opérateur
- journalisation structurée obligatoire

Nuance prod-safe importante :

- le **changement de phase** reste manuel et gouverné via UI
- mais un **interlock de sécurité dur** peut toujours refuser automatiquement
  l'envoi d'ordres si un invariant critique casse
- ce refus automatique n'est pas considéré comme une “dégradation de phase” ;
  c'est une protection locale immédiate avant décision opérateur

---

# 4. Pourquoi cette doctrine peut être meilleure

## 4.1 Avantages

- supprime la tension `LIGHT` vs “solution complète observée”
- rend la chaîne de promotion beaucoup plus lisible
- rapproche la doctrine documentaire du ressenti métier réel
- évite de maintenir deux récits de rollout pour une seule architecture utile

## 4.2 Bénéfices opératoires

- meilleur pilotage humain
- meilleure lisibilité des jalons
- moins de confusion entre :
  - ce qui est codé
  - ce qui est activé en Shadow
  - ce qui est autorisé en réel

---

# 5. Risques et objections

## 5.1 Risque principal

Ce changement n'est **pas** un simple patch lexical.

C'est une **refonte de gouvernance** qui impacte :

- le master
- le build plan
- Build-11
- Build-12
- Build-13
- Build-14
- les merge gates
- les contrats code
- les tests de protocole
- l'UI / monitoring

## 5.2 Objection raisonnable

Le canon actuel sépare `LIGHT` et `COMPLETE` pour une raison prod-safe :

- garder un rollout initial plus discipliné
- puis ouvrir une extension plus large seulement après stabilité réelle

Donc supprimer `LIGHT / COMPLETE` trop vite pourrait :

- casser des garde-fous utiles
- brouiller les budgets de risque
- rendre le code plus flou au lieu de le simplifier

Conclusion :

- la doctrine cible est défendable
- mais elle doit être migrée avec méthode, pas “renommée” brutalement

---

# 6. Impact concret sur le code

La doctrine cible imposerait au minimum :

## 6.1 Contrats et types

- revoir `ProfileId`
- revoir l'usage de `RuntimeMode`
- ajouter des phases Shadow distinctes
- remplacer les gates figées `30j + 7j` par `30j + 15j + 15j`

## 6.2 Gates

- Build-11 deviendrait `Shadow preuve 30j`
- un nouveau gate explicite serait requis pour `Shadow confirmation 15j`
- Build-12 deviendrait `Micro-live 15j`
- Build-13 deviendrait la porte d'entrée `Live`

## 6.3 UI / monitoring

- l'UI ne devrait plus exprimer une logique `Light locked` comme vérité
  produit centrale
- elle devrait exposer les phases réelles :
  - `SHADOW_PROOF`
  - `SHADOW_CONFIRMATION`
  - `MICRO_LIVE`
  - `LIVE`
- elle devrait être la **seule surface autorisée** pour les transitions
  descendantes visibles
- elle devrait exposer un **kill manuel d'urgence** et des actions de
  downgrade gouvernées
- chaque action opérateur devrait imposer :
  - confirmation
  - motif
  - audit log

## 6.4 Contrats opérateur

- prévoir des actions opérateur typées dès les contrats, avant même la future
  UI locale finale
- distinguer :
  - `operator_requested_state_transition`
  - `hard_safety_interlock_triggered`
- ne jamais confondre blocage automatique d'ordre et transition de phase
  approuvée par l'opérateur

## 6.5 Tests

- tests de contrats
- tests de promotion
- tests de régression
- tests de monitoring / UI
- tests d'actions opérateur et de kill manuel
- tests de non-régression sur la journalisation des dégradations manuelles

tous devraient être réalignés

---

# 7. Décision recommandée

Je recommande de traiter cette doctrine cible comme une **décision de
gouvernance explicite**, avec deux options nettes :

## Option A — Conserver le canon actuel

- garder `LIGHT / COMPLETE`
- continuer seulement la clarification documentaire
- réaligner ensuite le code sur ce canon

## Option B — Adopter la chaîne unique prod-safe

- une seule V5.3 complète
- une seule chaîne :
  - Shadow 30 jours
  - Shadow confirmation 15 jours
  - Micro-live 15 jours
  - Live

Ma lecture honnête :

- si l'objectif prioritaire est la **lisibilité métier et opératoire**, l'Option B
  est plus forte
- si l'objectif prioritaire est la **stabilité de migration à court terme**,
  l'Option A est moins risquée

---

# 8. Recommandation de migration si Option B retenue

Ordre prod-safe recommandé :

1. **Décision de gouvernance approuvée**
   - figer noir sur blanc que `LIGHT / COMPLETE` ne pilotent plus la montée en réel

2. **Réécriture canonique**
   - master
   - build plan
   - builds 11 à 14
   - merge gates

3. **Contrats + tests**
   - types
   - durations
   - gates
   - régressions

4. **Runtimes**
   - shadow counters
   - reporting
   - micro-live
   - live

5. **Contrats opérateur**
   - transitions manuelles
   - kill manuel
   - distinction entre interlock dur et downgrade UI

6. **Monitoring / UI**
   - nouveaux états exposés
   - suppression du récit `Light` comme vérité opératoire
   - contrôle local opérateur

---

# 9. Statut

Statut retenu dans ce document :

- **proposition sérieuse**
- **non encore appliquée au canon**
- **nécessite décision explicite avant patch global des specs et du code**
