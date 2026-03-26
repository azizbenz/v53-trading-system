# V5.3 — PROMPT PACK CLAUDE PRO / CHATGPT PRO
## Développer chaque build sans dérive
### Pack opératoire complet
### Sans code produit ici — uniquement prompts, protocoles et garde-fous
### Version française

---

# 0. Objet du document

Ce document fournit un **prompt pack complet** pour utiliser **Claude Pro** et **ChatGPT Pro** de façon disciplinée sur la V5.3, build par build, sans dérive d’architecture, de scope, de logique risque ou de production.

Le but est simple :

> empêcher qu’un bon corpus documentaire se transforme en code incohérent, sur-complexe, contradictoire ou non prod-safe à cause d’une mauvaise orchestration des IA.

Ce pack couvre :

- les règles globales d’utilisation des IA
- la répartition des rôles Claude Pro / ChatGPT Pro
- les prompts maîtres permanents
- les prompts par étape de travail
- les prompts de contrôle anti-dérive
- les prompts build par build
- le workflow officiel de développement
- les sorties attendues à chaque itération

---

# 1. Philosophie du pack

## 1.1 Règle fondamentale

Tu n’utilises pas Claude Pro et ChatGPT Pro comme deux assistants “qui donnent des idées”.  
Tu les utilises comme deux **rôles complémentaires dans une chaîne d’ingénierie disciplinée**.

## 1.2 Répartition officielle des rôles

### ChatGPT Pro
À utiliser prioritairement pour :
- architecture
- logique quant
- risk review
- arbitrage entre options
- spécification détaillée
- audit logique d’un module
- détection de dérive conceptuelle
- critique des angles morts
- cohérence avec le master

### Claude Pro
À utiliser prioritairement pour :
- génération de code modulaire
- implémentation d’un module à partir d’une spec figée
- refactorisation
- wiring de composants
- écriture de tests
- correction ciblée après audit
- mise en forme de fichiers techniques longs

## 1.3 Règle critique

On ne demande **jamais** à Claude Pro de définir seul l’architecture.  
On ne demande **jamais** à ChatGPT Pro de produire un gros volume de code sans spec gelée.

---

# 2. Règles non négociables anti-dérive

Avant chaque usage de Claude Pro ou ChatGPT Pro, les règles suivantes doivent être rappelées ou intégrées au prompt :

1. **la source de vérité unique est le master V5.3**
2. **aucune invention hors scope**
3. **aucun changement d’architecture implicite**
4. **aucun ajout de module non demandé**
5. **aucune simplification silencieuse des garde-fous**
6. **aucun bypass des hard blockers / budgets risque / profils**
7. **aucune activation Complete implicite quand on travaille en Light**
8. **aucune réécriture globale non explicitement demandée**
9. **aucun code avant clarification de l’interface et des invariants**
10. **toujours séparer : spec / code / audit / correction / merge gate**

---

# 3. Documents à garder comme base de travail

À chaque session IA, il faut rappeler qu’on travaille à partir de :

- `V5_3_MASTER_FINAL_UNIQUE.md`
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- le fichier spec du build concerné
- éventuellement les fichiers moteur, UI, merge gates, annexe math, etc.

## Règle
Toujours fournir au modèle :
- le **nom exact du build**
- le **nom exact du ou des modules**
- le **type de tâche demandé**
- la **sortie attendue**
- les **interdits**

---

# 4. Workflow officiel d’utilisation des IA

Pour chaque build ou module, utiliser l’ordre suivant :

## Étape 1 — Spécification
ChatGPT Pro  
Objectif :
- définir ou rappeler la spec exacte du module
- lister inputs / outputs / invariants / dépendances / tests / dérives

## Étape 2 — Implémentation
Claude Pro  
Objectif :
- écrire le code du module
- écrire les tests associés
- respecter strictement la spec donnée

## Étape 3 — Audit logique
ChatGPT Pro  
Objectif :
- vérifier :
  - cohérence au master
  - conformité à la spec
  - angles morts
  - erreurs de logique
  - dérive de scope
  - dérive risque / prod

## Étape 4 — Correction ciblée
Claude Pro  
Objectif :
- corriger uniquement ce qui a été identifié
- ne pas réinventer l’architecture
- ne pas élargir le scope

## Étape 5 — Merge gate
ChatGPT Pro  
Objectif :
- décider si le module est mergeable
- ou lister ce qu’il manque avant merge

---

# 5. Prompt maître permanent — ChatGPT Pro

Ce prompt doit être réutilisé souvent, ou intégré au début de chaque session d’architecture/audit.

```text
Tu travailles sur le projet V5.3 de trading crypto spot halal.

Règles absolues :
1. La source de vérité unique est le master V5.3 et les specs de build déjà validées.
2. Tu ne dois jamais inventer un module, un moteur, une règle de risque, un profil ou une interface non demandés.
3. Tu ne dois jamais élargir le scope.
4. Tu dois toujours séparer clairement :
   - ce qui est dans la spec
   - ce qui manque
   - ce qui est incorrect
   - ce qui doit être corrigé
5. Tu dois raisonner comme :
   - senior quant
   - senior risk manager
   - senior architecte logiciel
   - reviewer prod-safe
6. Tu dois être dur avec :
   - la dérive de scope
   - les contradictions avec le master
   - les bypass de risque
   - les simplifications silencieuses
   - les scores opaques
   - les modules non testables
7. Tu ne dois jamais proposer RL live, POMDP live, ou sophistication non validée si elle n’est pas explicitement demandée.
8. Tu dois toujours signaler :
   - les angles morts
   - les contradictions
   - les parties non prod-safe
   - les ambiguïtés d’interface
   - les oublis de tests
9. Tu dois répondre en français, de façon structurée, précise et exploitable.
10. Tu ne dois jamais réécrire toute l’architecture si la demande porte sur un module précis.

Ta tâche du moment est : [REMPLIR ICI]
Sortie attendue : [REMPLIR ICI]
Contexte build : [REMPLIR ICI]
Module(s) concerné(s) : [REMPLIR ICI]
Interdits spécifiques : [REMPLIR ICI]
```

---

# 6. Prompt maître permanent — Claude Pro

Ce prompt doit être réutilisé souvent, ou intégré au début de chaque session de code.

```text
Tu implémentes un module du projet V5.3 de trading crypto spot halal.

Règles absolues :
1. Tu dois respecter strictement le master V5.3 et la spec de build fournie.
2. Tu ne dois pas inventer d’architecture alternative.
3. Tu ne dois pas ajouter de module non demandé.
4. Tu ne dois pas élargir le scope.
5. Tu dois écrire un code modulaire, lisible, testable, prod-safe.
6. Tu dois respecter les interfaces, invariants, dépendances autorisées et interdictions définies dans la spec.
7. Tu dois fournir :
   - le code du module
   - les tests nécessaires
   - les stubs / interfaces minimales si explicitement demandés
8. Tu ne dois jamais contourner :
   - les hard blockers
   - le risk backbone
   - les profils Light / Complete
   - la journalisation
   - la réconciliation
9. Tu ne dois pas “simplifier” en supprimant des garde-fous.
10. Si la spec est insuffisante ou contradictoire, tu dois le signaler explicitement avant d’implémenter.

Ta tâche du moment est : [REMPLIR ICI]
Build concerné : [REMPLIR ICI]
Module concerné : [REMPLIR ICI]
Sortie attendue : [REMPLIR ICI]
Interdits spécifiques : [REMPLIR ICI]

Je fournis ci-dessous la spec officielle à respecter mot pour mot dans son esprit :
[COLLER LA SPEC]
```

---

# 7. Prompt type — ChatGPT Pro pour spécifier un module avant code

```text
Travaille uniquement sur le module suivant du projet V5.3 :

Build : [BUILD]
Module : [MODULE]

Je veux une fiche de spécification exécutable pour Claude Pro, sans code.
Ta réponse doit contenir uniquement :
1. mission
2. responsabilités exactes
3. sous-composants
4. inputs
5. outputs
6. état interne
7. invariants obligatoires
8. dépendances autorisées
9. dépendances interdites
10. logs attendus
11. tests obligatoires
12. dérives à ne pas faire
13. critères de sortie du module

Contraintes :
- respecte strictement le master V5.3
- pas d’élargissement de scope
- pas d’ajout de modules non demandés
- pas de réécriture globale
- réponse en français
- niveau prod-safe
```

---

# 8. Prompt type — Claude Pro pour coder un module à partir de la spec

```text
Implémente le module suivant du projet V5.3 :

Build : [BUILD]
Module : [MODULE]

Tu dois produire :
1. le code du module
2. les tests du module
3. les éventuels contrats / types minimaux nécessaires si explicitement requis
4. rien d’autre hors scope

Contraintes absolues :
- respecte la spec fournie
- pas de module supplémentaire
- pas d’architecture alternative
- pas de logique cachée
- pas de bypass des caps de risque / hard blockers / profils
- code testable et modulaire
- journalisation explicite si prévue par la spec
- réponse en français ou pseudo-technique, mais le code lui-même doit être propre

Spec officielle :
[COLLER LA SPEC]
```

---

# 9. Prompt type — ChatGPT Pro pour auditer le code produit par Claude

```text
Tu audites le code suivant pour le projet V5.3.

Build : [BUILD]
Module : [MODULE]

Je veux un audit en tant que :
- senior architecte logiciel
- senior quant
- senior risk reviewer
- reviewer prod-safe

Ta mission :
1. vérifier la conformité à la spec
2. vérifier la conformité au master V5.3
3. détecter :
   - erreurs de logique
   - angles morts
   - dérive de scope
   - oublis de tests
   - journaux insuffisants
   - problèmes de prod safety
   - dépendances interdites
4. classer les problèmes en :
   - critique
   - majeur
   - mineur
5. proposer des corrections ciblées, sans réécrire tout le module

Je ne veux pas une réponse vague.
Je veux :
- un verdict global
- la liste précise des écarts
- les corrections minimales nécessaires avant merge

Spec officielle :
[COLLER LA SPEC]

Code à auditer :
[COLLER LE CODE]
```

---

# 10. Prompt type — Claude Pro pour corriger après audit

```text
Corrige le module suivant du projet V5.3 à partir de l’audit ci-dessous.

Build : [BUILD]
Module : [MODULE]

Règles :
- corriger uniquement ce qui a été identifié
- ne pas élargir le scope
- ne pas modifier l’architecture si ce n’est pas explicitement nécessaire
- garder le module conforme à la spec
- conserver les garde-fous et la journalisation
- mettre à jour les tests si nécessaire

Spec officielle :
[COLLER LA SPEC]

Audit à corriger :
[COLLER L’AUDIT]

Code actuel :
[COLLER LE CODE]
```

---

# 11. Prompt type — ChatGPT Pro pour merge gate final

```text
Tu joues le rôle de merge gate reviewer final pour le projet V5.3.

Build : [BUILD]
Module : [MODULE]

À partir de :
- la spec officielle
- le code final
- les tests
- l’audit précédent

Tu dois rendre un verdict :

- MERGEABLE
ou
- NON MERGEABLE

Si NON MERGEABLE, tu dois lister uniquement les points bloquants restants.

Vérifie obligatoirement :
1. conformité à la spec
2. conformité au master
3. dépendances autorisées
4. présence des tests obligatoires
5. logs attendus
6. absence de dérive de scope
7. absence de faille prod-safe

Réponse attendue :
- verdict
- blocants
- risques résiduels non bloquants
- recommandation de merge ou de non-merge
```

---

# 12. Prompt type — ChatGPT Pro pour audit transversal d’un build entier

```text
Tu audites transversalement le build suivant du projet V5.3 :

Build : [BUILD]

Je veux un audit build-level, pas un audit vague.
Tu dois vérifier :
1. cohérence des modules entre eux
2. cohérence avec le master V5.3
3. cohérence avec le plan de build
4. présence des dépendances interdites
5. trous de logging
6. trous de tests
7. angles morts opérationnels
8. risques de dérive future

Classe les conclusions en :
- critique
- majeur
- mineur

Termine par :
- ce qu’il faut corriger avant la suite
- si le build est prêt pour l’étape suivante ou non
```

---

# 13. Prompt type — Claude Pro pour produire le code d’un build complet module par module

À utiliser seulement après que les modules du build ont été spécifiés séparément.

```text
Nous allons implémenter le build suivant du projet V5.3 :

Build : [BUILD]

Règle absolue :
- tu dois traiter les modules un par un
- tu ne dois pas fusionner plusieurs modules critiques dans un bloc opaque
- pour chaque module, tu dois fournir :
  1. code du module
  2. tests du module
  3. éventuels ajustements minimaux de contrats si explicitement requis

Modules à traiter, dans l’ordre :
[COLLER LA LISTE]

Pour cette réponse, travaille UNIQUEMENT sur :
[COLLER LE MODULE COURANT]

Spec officielle du module :
[COLLER LA SPEC]
```

---

# 14. Prompt type — ChatGPT Pro pour comparer une implémentation au master final

```text
Compare cette implémentation au master final V5.3.

Je veux une réponse strictement orientée dérive :
1. ce qui est conforme
2. ce qui diverge
3. ce qui manque
4. ce qui a été ajouté à tort
5. si cela menace :
   - l’architecture
   - le risk backbone
   - la lisibilité
   - la prod safety

Je ne veux pas de réécriture complète.
Je veux une comparaison précise et exploitable.

Master / spec :
[COLLER EXTRAIT PERTINENT]

Implémentation :
[COLLER CODE OU RÉSUMÉ]
```

---

# 15. Prompt type — ChatGPT Pro pour audit économique d’un moteur

```text
Audite économiquement ce moteur du projet V5.3.

Moteur : [A/B/C/D]

Je veux un audit en tant que :
- senior quant
- senior trader
- senior risk manager

Tu dois vérifier :
1. la logique structurelle
2. la logique de coût
3. la logique de CE
4. la logique de sizing
5. la logique de non-duplication
6. les angles morts
7. les dérives possibles
8. si ce moteur mérite vraiment d’exister

Réponse attendue :
- verdict global
- faiblesses critiques
- faiblesses majeures
- corrections prioritaires
- décision : implémenter maintenant / plus tard / ne pas implémenter
```

---

# 16. Prompt type — ChatGPT Pro pour verdict de passage entre builds

```text
Tu dois rendre un verdict de passage entre deux builds du projet V5.3.

Build actuel : [BUILD ACTUEL]
Build suivant : [BUILD SUIVANT]

À partir des éléments fournis, réponds :
- GO
ou
- NO-GO

En vérifiant :
1. critères de sortie du build actuel
2. critères d’entrée du build suivant
3. risques résiduels
4. angles morts
5. conditions supplémentaires éventuelles

Réponse attendue :
- verdict
- raisons
- blocants
- corrections à faire avant passage
```

---

# 17. Prompt type — ChatGPT Pro pour post-mortem shadow / micro-live / live

```text
Réalise un post-mortem structuré de la phase suivante du projet V5.3 :

Phase : [SHADOW / MICRO-LIVE / LIVE-LIGHT / LIVE-COMPLETE]

Je veux une lecture de niveau hedge-fund / prod-safe.

Analyse obligatoirement :
1. stabilité technique
2. qualité data / infra
3. exécution
4. coûts
5. réconciliation
6. moteurs
7. portefeuille
8. meta / DTR / CRA / break-even / edge
9. supervision opérateur
10. verdict GO / NO-GO

Je veux :
- faits observés
- interprétation
- erreurs probables
- corrections prioritaires
- décision finale
```

---

# 18. Format de réponse à exiger des modèles

Pour éviter les réponses floues, ajouter souvent cette contrainte :

```text
Je ne veux pas :
- de réponse vague
- de brainstorming large
- d’idées hors scope
- de réécriture complète inutile
- de généralités

Je veux :
- une réponse directement exploitable
- structurée
- centrée sur le build/module demandé
- cohérente avec le master V5.3
- prod-safe
```

---

# 19. Prompt pack Build-1 à Build-17 — format court réutilisable

Cette section donne, pour chaque build, le prompt de travail minimal à envoyer.

---

# 20. Build-1 — Dependency Architecture

## 20.1 Prompt ChatGPT Pro — spécification / audit
```text
Travaille sur Build-1 du projet V5.3.

Objectif :
verrouiller l’architecture logicielle avant tout développement métier.

Modules concernés :
- interface_contracts
- manifest_registry
- dag_validator
- contract_test_suite
- smoke_bootstrap_recovery

Ta tâche :
[spécifier / auditer / rendre verdict merge gate]

Contraintes :
- pas de logique métier
- pas d’élargissement de scope
- niveau prod-safe
- détecter toute dérive de dépendances, de contrats ou de tests
```

## 20.2 Prompt Claude Pro — implémentation
```text
Implémente Build-1 du projet V5.3, module par module, sans dérive.

Module courant :
[INDIQUER LE MODULE]

Tu dois respecter strictement la spec officielle.
Tu ne dois rien ajouter hors scope.
Tu dois fournir :
- code du module
- tests du module
- aucun bypass architectural
```

---

# 21. Build-2 — Data Backbone

## 21.1 Prompt ChatGPT Pro
```text
Travaille sur Build-2 du projet V5.3.

Objectif :
construire une couche data / qualité de données robuste.

Modules concernés :
- websocket_gateway
- rest_bootstrap
- event_normalizer
- internal_router
- freshness_checker
- consistency_checker
- pair_health_scorer

Ta tâche :
[spécifier / auditer / verdict]

Points critiques à surveiller :
- stale data
- backlog
- disorder
- pair health
- contamination inter-paires
- usage abusif du REST
```

## 21.2 Prompt Claude Pro
```text
Implémente Build-2 du projet V5.3, module par module, sans dérive.

Module courant :
[INDIQUER LE MODULE]

Respecte strictement :
- la spec du build
- les contrats
- les invariants de fraîcheur, cohérence et santé paire
- l’interdiction d’ajouter de la logique métier
```

---

# 22. Build-3 — Execution Backbone

## 22.1 Prompt ChatGPT Pro
```text
Travaille sur Build-3 du projet V5.3.

Objectif :
rendre l’exécution réelle mesurable, réconciliable et économiquement interprétable.

Modules concernés :
- order_decider
- fill_tracker
- execution_cost_meter
- reconciliation_layer

Surveille en priorité :
- coût réel
- partial fills
- diver gence local/remote
- no-trade économique
- auditabilité de l’exécution
```

## 22.2 Prompt Claude Pro
```text
Implémente Build-3 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Interdits absolus :
- exécution implicite sans intent explicite
- coût réduit aux fees
- réconciliation silencieuse
- perte d’état d’ordre/fill
```

---

# 23. Build-4 — Risk Backbone

## 23.1 Prompt ChatGPT Pro
```text
Travaille sur Build-4 du projet V5.3.

Objectif :
bloquer les sur-expositions, pertes excessives, concentrations BTC et clusters corrélés.

Modules concernés :
- exposure_budgeter
- loss_budgeter
- btc_factor_guard
- correlation_cluster_guard

Ta réponse doit être impitoyable sur :
- les caps contournables
- la fausse diversification
- l’absence de L_i explicite
- le beta BTC ignoré
```

## 23.2 Prompt Claude Pro
```text
Implémente Build-4 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Tu dois :
- respecter les caps
- exposer les refus
- rendre les budgets auditables
- ne jamais permettre un contournement via plusieurs petits trades
```

---

# 24. Build-5 — Scoring Backbone

## 24.1 Prompt ChatGPT Pro
```text
Travaille sur Build-5 du projet V5.3.

Objectif :
mettre en place hard / soft / rank sans recréer la stérilité de V5.2.

Modules concernés :
- raw_score_builder
- penalty_aggregator
- hard_block_gate
- ranking_router

Surveille en priorité :
- score opaque
- soft penalties qui deviennent des veto cachés
- hard block inflation
- ranking qui ignore coût/CE/portefeuille
```

## 24.2 Prompt Claude Pro
```text
Implémente Build-5 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Interdits :
- règles cachées
- score non versionné
- pénalités non traçables
- hard blockers de confort
- ranking au score brut seul
```

---

# 25. Build-6 — Moteur A

## 25.1 Prompt ChatGPT Pro
```text
Travaille sur Build-6 du projet V5.3.

Objectif :
spécifier / auditer le Moteur A — Premium Trend / Expansion.

Je veux vérifier :
- haute conviction
- non-stérilité
- coût supportable
- invalidation claire
- compatibilité portefeuille
- risques de duplication avec C
```

## 25.2 Prompt Claude Pro
```text
Implémente le Moteur A du projet V5.3 à partir de la spec officielle.

Interdits :
- trop de confirmations
- logique opaque
- absence d’invalidation
- Tier 3 implicite
- moteur premium mais inutilisable
```

---

# 26. Build-7 — Moteur B

## 26.1 Prompt ChatGPT Pro
```text
Travaille sur Build-7 du projet V5.3.

Objectif :
spécifier / auditer le Moteur B — Mean Reversion Intraday.

Je veux vérifier :
- fréquence utile
- filtre anti-breakout
- coût supportable
- durée compatible
- CE crédible
- risque de moteur “volume pour volume”
```

## 26.2 Prompt Claude Pro
```text
Implémente le Moteur B du projet V5.3 à partir de la spec officielle.

Interdits :
- mean reversion naïve
- z-score seul
- durée trop longue
- coût ignoré
- sizing trop agressif
```

---

# 27. Build-8 — Portfolio Minimal

## 27.1 Prompt ChatGPT Pro
```text
Travaille sur Build-8 du projet V5.3.

Objectif :
transformer A et B en portefeuille Light cohérent.

Modules concernés :
- opportunity_selector
- allocation_router

Je veux vérifier :
- arbitrage A/B
- coût d’opportunité du capital
- phantom trades
- caps respectés
- refus relatifs explicites
```

## 27.2 Prompt Claude Pro
```text
Implémente Build-8 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Interdits :
- score brut seul
- allocations stériles invisibles
- fragmentation pour contourner les caps
- favoritisme dogmatique A ou B
```

---

# 28. Build-9 — Meta Minimal

## 28.1 Prompt ChatGPT Pro
```text
Travaille sur Build-9 du projet V5.3.

Objectif :
rendre le système explicable et économiquement lisible.

Modules concernés :
- dtr_core
- cra_monitor
- break_even_dashboard
- edge_tracker_prudent_minimal

Je veux vérifier :
- DTR coverage
- détection des phantom trades
- break-even réel
- prudence statistique sur l’edge
```

## 28.2 Prompt Claude Pro
```text
Implémente Build-9 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Interdits :
- logs non structurés à la place des DTR
- edge tracker trop ambitieux
- CRA flou
- break-even purement cosmétique
```

---

# 29. Build-10 — Monitoring + UI Light

## 29.1 Prompt ChatGPT Pro
```text
Travaille sur Build-10 du projet V5.3.

Objectif :
rendre la Light observable, gouvernable et non contournable.

Modules concernés :
- metrics_collector
- alert_manager
- health_dashboard_backend
- ui_light_locked

Je veux vérifier :
- coût / CE / risque visibles
- alertes actionnables
- UI non permissive
- impossibilité d’activer C/D ou > 6 paires
```

## 29.2 Prompt Claude Pro
```text
Implémente Build-10 du projet V5.3, module par module.

Module courant :
[INDIQUER LE MODULE]

Interdits :
- UI décorative
- profils custom
- bypass hard blockers
- dashboards sans métriques critiques
```

---

# 30. Build-11 — Shadow Light

## 30.1 Prompt ChatGPT Pro
```text
Tu dois piloter / auditer Build-11 du projet V5.3.

Objectif :
valider le Shadow Light avant micro-live.

Je veux un protocole ou un audit centré sur :
- coûts shadow prudents
- DTR complets
- fréquence utile
- CE shadow
- pair health
- backlog
- verdict GO / NO-GO vers micro-live
```

## 30.2 Prompt Claude Pro
Claude Pro est moins prioritaire ici, sauf pour :
- scripts de collecte
- scripts de reporting
- outils techniques de support Shadow

Prompt :
```text
Construis uniquement les outils techniques nécessaires au Shadow Light du projet V5.3.

Ne modifie pas l’architecture.
Ne change pas les moteurs.
Ne change pas les caps.
Produis uniquement les utilitaires explicitement demandés.
```

---

# 31. Build-12 — Micro-live Light

## 31.1 Prompt ChatGPT Pro
```text
Tu dois piloter / auditer Build-12 du projet V5.3.

Objectif :
valider le micro-live Light à taille ultra-prudente.

Je veux vérifier :
- coûts réels
- ACK/fills/partial fills
- réconciliation
- CE réelle
- respect de la discipline de taille
- kill / halt conditions
- verdict GO / NO-GO vers Live-Light
```

## 31.2 Prompt Claude Pro
Claude Pro peut aider à :
- scripts de collecte micro-live
- outils de comparaison shadow/réel
- outils de reporting

Prompt :
```text
Construis uniquement les utilitaires techniques nécessaires au micro-live Light du projet V5.3.

Interdits :
- augmentation implicite des tailles
- modifications des moteurs
- modification des caps ou profils
- simplification de la réconciliation
```

---

# 32. Build-13 — Live-Light

## 32.1 Prompt ChatGPT Pro
```text
Tu dois piloter / auditer Build-13 du projet V5.3.

Objectif :
valider la production Live-Light.

Je veux vérifier :
- stabilité technique
- coûts réels
- CE Light
- utilité réelle de A et B
- DEGRADED / HALTED / rollback
- readiness ou non pour Complete Enablers
```

## 32.2 Prompt Claude Pro
Claude Pro peut aider à :
- tableaux de bord techniques
- automatisation des rapports
- outils de rollback / degraded si explicitement spécifiés

Prompt :
```text
Produis uniquement les composants techniques explicitement demandés pour le Live-Light du projet V5.3.

Ne modifie ni les moteurs, ni les caps, ni les profils.
Ne transforme pas le scope Light en Complete.
```

---

# 33. Build-14 — Complete Enablers

## 33.1 Prompt ChatGPT Pro
```text
Travaille sur Build-14 du projet V5.3.

Objectif :
évaluer les enablers de la Complete sans casser la Light.

Composants concernés :
- microstructure enrichie
- régime enrichi
- covariance robuste
- risk contribution monitor
- diversité effective d’edge

Je veux vérifier :
- utilité réelle
- stabilité
- coût de complexité
- non-régression Light
- readiness ou non pour C / D
```

## 33.2 Prompt Claude Pro
```text
Implémente ou outille les composants Build-14 du projet V5.3 uniquement dans le cadre demandé.

Interdits :
- activation implicite Complete
- hard blockers nouveaux
- surcharge CPU sans mesure
- complexification gratuite
```

---

# 34. Build-15 — Moteur C

## 34.1 Prompt ChatGPT Pro
```text
Travaille sur Build-15 du projet V5.3.

Objectif :
spécifier / auditer le Moteur C — Breakout Continuation.

Je veux vérifier :
- qualité du breakout
- anti-faux-breakout
- coût net
- non-duplication avec A
- valeur marginale portefeuille
```

## 34.2 Prompt Claude Pro
```text
Implémente le Moteur C du projet V5.3 à partir de la spec officielle.

Interdits :
- breakout naïf
- A plus nerveux déguisé
- coût ignoré
- sizing agressif initial
- invalidation floue
```

---

# 35. Build-16 — Moteur D

## 35.1 Prompt ChatGPT Pro
```text
Travaille sur Build-16 du projet V5.3.

Objectif :
spécifier / auditer le Moteur D — Re-entry / Second Chance Logic.

Je veux vérifier :
- valeur marginale réelle
- anti-revenge
- coût marginal
- concentration marginale
- non-duplication avec A
```

## 35.2 Prompt Claude Pro
```text
Implémente le Moteur D du projet V5.3 à partir de la spec officielle.

Interdits :
- réengagement émotionnel déguisé
- duplication de A
- réentrées multiples sans garde-fous
- concentration supplémentaire non mesurée
```

---

# 36. Build-17 — UI Complete + Live-Complete

## 36.1 Prompt ChatGPT Pro
```text
Travaille sur Build-17 du projet V5.3.

Objectif :
définir / auditer la UI Complete et le protocole Live-Complete.

Je veux vérifier :
- gouvernance opératoire
- lisibilité 12 paires / 4 moteurs
- coût marginal de la Complete
- apport réel de C et D
- corrélation réelle
- rollback Complete → Light
```

## 36.2 Prompt Claude Pro
```text
Implémente uniquement les composants techniques explicitement demandés pour la UI Complete / Live-Complete du projet V5.3.

Interdits :
- cockpit permissif
- activation sauvage de Complete
- bypass des gates
- suppression des mécanismes DEGRADED / HALTED / rollback
```

---

# 37. Prompt de contrôle anti-dérive à réinjecter régulièrement

À utiliser si une session commence à dériver.

```text
Stop.

Reviens strictement au cadre suivant :
- projet V5.3
- build : [BUILD]
- module / moteur / protocole : [ÉLÉMENT]
- source de vérité : master V5.3 + spec officielle
- aucune invention hors scope
- aucune architecture alternative
- aucun ajout de module
- aucune simplification silencieuse
- aucune réécriture globale
- pas de Complete si on est en Light
- pas de bypass des hard blockers / caps / profils

Ta prochaine réponse doit uniquement :
1. corriger la dérive
2. revenir à la tâche exacte
3. produire une sortie exploitable
```

---

# 38. Prompt de comparaison Claude vs ChatGPT

Très utile quand les deux IA donnent des sorties différentes.

```text
Compare les deux propositions suivantes pour le projet V5.3.

Je veux une analyse de divergence :
1. ce qui est compatible avec le master
2. ce qui diverge
3. ce qui est plus prod-safe
4. ce qui est plus risqué
5. ce qui doit être conservé
6. ce qui doit être rejeté

Je ne veux pas une fusion vague.
Je veux un arbitrage explicite.

Proposition 1 :
[COLLER]

Proposition 2 :
[COLLER]
```

---

# 39. Prompt de synthèse avant merge d’un build complet

```text
Fais la synthèse finale du build [BUILD] du projet V5.3.

Je veux :
1. liste des modules du build
2. statut de chacun
3. blocants restants
4. risques résiduels
5. conformité au master
6. conformité au plan de build
7. verdict GO / NO-GO vers le build suivant
8. corrections minimales restantes

Réponse exigée :
- directe
- structurée
- sans élargissement de scope
- orientée prod-safe
```

---

# 40. Comment utiliser ce pack en pratique

## 40.1 Pour développer un module
Utiliser l’ordre :
1. prompt ChatGPT de spécification
2. prompt Claude d’implémentation
3. prompt ChatGPT d’audit
4. prompt Claude de correction
5. prompt ChatGPT de merge gate

## 40.2 Pour un protocole de phase (Shadow, Micro-live, Live)
Utiliser :
1. prompt ChatGPT de protocole
2. prompt Claude uniquement pour outils techniques de support
3. prompt ChatGPT de post-mortem
4. prompt ChatGPT de verdict GO / NO-GO

## 40.3 Pour gérer un désaccord entre modèles
Utiliser :
- prompt de comparaison Claude vs ChatGPT
- puis arbitrage final ChatGPT centré master V5.3

---

# 41. Erreurs à éviter absolument

- demander à Claude “fais tout Build-X”
- demander à ChatGPT “écris tout le code du projet”
- travailler sans coller la spec officielle
- faire confiance à une réponse IA non confrontée au master
- merger du code avant audit croisé
- laisser les prompts devenir vagues
- oublier d’indiquer le build exact
- oublier d’indiquer le module exact
- oublier les interdits spécifiques

---

# 42. Verdict final du pack

Ce prompt pack doit être utilisé comme **outil de pilotage**, pas comme simple collection de prompts.

S’il est utilisé correctement :
- chaque build peut être développé sans dérive majeure
- Claude Pro et ChatGPT Pro restent dans leurs rôles
- le master V5.3 reste la source de vérité
- les merges deviennent beaucoup plus disciplinés
- la probabilité de dette technique et de dérive conceptuelle chute fortement

S’il est utilisé mal :
- les IA réinventeront des pans entiers du système
- les builds se mélangeront
- les profils Light / Complete seront confondus
- la prod safety se dégradera
- le corpus documentaire perdra sa valeur

Donc :

> ce pack doit être traité comme un **manuel opératoire IA**, pas comme un simple aide-mémoire.

---

## Fin du document
