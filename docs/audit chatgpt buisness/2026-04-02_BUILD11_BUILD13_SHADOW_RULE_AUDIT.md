# V5.3 — AUDIT CIBLÉ BUILD-11 / BUILD-13
## Règle officielle Shadow 30j vs `shadow_report_ready`
### Date : 2026-04-02
### Statut : ACTIF

---

# 0. Objet

Ce document fixe le résultat de l'audit ciblé demandé sur la règle de passage
`Build-11 -> Build-12 -> Build-13`.

Question auditée :

> la règle officielle est-elle seulement `30 jours de Shadow`, ou bien
> `30 jours + rapport shadow exploitable/complet` ?

---

# 1. Conclusion courte

La règle officielle n'est **pas** simplement :

- `30 jours atteints`

La règle officielle réelle est plus stricte :

- `30 jours calendaires consécutifs minimum en Shadow`
- `rapport shadow exploitable / produit / approuvé`
- `verdict post-Shadow composant par composant`
- puis seulement Micro-live, puis Live-Light

Dans le code actuel, le booléen `shadow_report_ready` est la traduction
technique de cette exigence documentaire de rapport Shadow exploitable et
complet.

Conclusion opérationnelle :

- `30/30` seul ne suffit pas
- `30/30 + rapport incomplet` doit rester bloqué
- les tests qui attendaient `30 jours seuls` sont en retard sur le canon réel

---

# 2. Base documentaire retenue

## 2.1 Canon principal

Le canon principal impose :

- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
  - Light Shadow 30 jours obligatoires
  - rapport shadow exploitable obligatoire
  - comparaison inter-moteurs et contribution Build-14 dans le rapport

- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
  - 30 jours calendaires consécutifs minimum
  - DTR complet
  - rapport shadow exploitable à l'issue
  - aucune activation Micro-live ou Live-Light avant expiration

- `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
  - Shadow complet 30 jours minimum
  - verdict post-Shadow rendu composant par composant
  - micro-live stable minimum 7 jours
  - rapport shadow produit, exploitable et approuvé

- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
  - 30 jours consécutifs minimum
  - rapport shadow produit et approuvé
  - verdict composant par composant obligatoire

## 2.2 Interprétation retenue

Le canon n'emploie pas partout le nom technique `shadow_report_ready`,
mais l'exigence métier est clairement celle d'un rapport final complet,
exploitable et approuvé avant promotion.

Donc :

- `shadow_report_ready` n'est pas une invention de code arbitraire
- c'est une matérialisation runtime raisonnable du canon documentaire

---

# 3. Traduction code retenue

## 3.1 Build-11

Dans `src/protocols/shadow_runtime.py`, la gate Shadow bloque si :

- les 30 jours ne sont pas atteints
- le rapport Shadow complet n'est pas prêt

Dans `src/protocols/shadow_day_counter.py`, `shadow_report_ready` n'est vrai
que si les sections obligatoires du rapport sont présentes, notamment :

- data / infra
- décisions / DTR
- coûts / break-even
- comparaison A/B/C/D
- contribution Build-14
- portefeuille
- UI / alerting
- GO / NO-GO

## 3.2 Build-12

Dans `src/protocols/micro_live_runtime.py`, le passage vers Micro-live exige :

- Shadow 30 jours terminé
- `shadow_report_ready=True`
- comparaison inter-moteurs prête
- contribution Build-14 prête
- verdicts composants disponibles

## 3.3 Build-13

Dans `src/protocols/contracts.py` et `src/protocols/live_light_runtime.py`,
Live-Light exige :

- `shadow_required_days=30`
- `shadow_days_completed >= 30`
- `shadow_report_ready=True`
- verdicts composants rendus
- Micro-live stable 7 jours

---

# 4. Implication réelle de la règle

La règle officielle implique que Build-11 n'est pas un simple compteur
calendaire.

Elle transforme Build-11 en phase de vérité avec preuve exploitable :

- on doit accumuler 30 jours
- mais aussi produire un rapport final suffisamment complet pour justifier
  une promotion

Autrement dit :

- `30 jours sans rapport final exploitable` = **NO-GO**
- `30 jours avec rapport final incomplet` = **NO-GO**
- `30 jours + rapport complet + verdicts` = **candidat au passage suivant**

---

# 5. Conséquence sur les tests

Les tests historiques de régression qui attendaient seulement :

- `30 jours atteints => gate passe`

ne sont plus alignés avec le canon réel ni avec le code actuel.

Les tests doivent désormais encoder :

- succès si `30 jours + rapport complet`
- blocage si `30 jours mais rapport incomplet`

---

# 6. Verdict d'audit

Verdict retenu :

- le problème principal n'est pas un durcissement illégitime du code
- le code actuel est globalement cohérent avec le canon principal
- l'écart venait surtout des tests de régression restés sur une ancienne lecture
  trop faible de la règle Shadow

Action correcte :

- conserver la logique stricte actuelle
- réaligner les tests de régression
- conserver la surveillance sur les docs secondaires et handoffs qui pourraient
  encore parler trop vaguement de "30 jours" sans mentionner le rapport final

---

# 7. Décision de travail

Décision prise pour cette reprise :

1. enregistrer cet audit
2. corriger les tests de régression pour refléter la règle officielle
3. ne pas assouplir le code Build-11 / Build-13 sur ce point sans décision
   explicite de gouvernance
