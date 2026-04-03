# V5.3 — BUILD-16 SPECS MODULES
## Moteur D Pack — Re-entry / Second Chance Logic
### Specs détaillées du quatrième moteur cible
### Seizième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-16** du plan officiel V5.3.

## Migration note - Full Shadow branch

On the dedicated migration branch `codex/full-shadow-abcd-migration-20260403`,
Engine D is no longer treated as absent from the initial Build-11 Shadow phase.
The active migration reading is:

- Build-11 Shadow observes `A/B/C/D + Build-14`
- Build-16 remains the dedicated implementation, hardening, and industrialization
  wave for Engine D
- downstream Micro-live/Live promotion remains governed per component verdict

If older wording in this spec still sounds like Engine D starts only after
Build-11 or only after a separate Build-15-only Shadow window, read that wording
as superseded by this migration note.

Build-16 a une mission unique :

> spécifier et valider le **Moteur D — Re-entry / Second Chance Logic**, c’est-à-dire le moteur chargé de réengager du capital après une première opportunité déjà validée, lorsque le marché reforme une structure exploitable et qu’une seconde entrée a une valeur marginale positive.

Le moteur D ne doit pas exister pour “rattraper” un trade raté.  
Il ne doit exister que s’il démontre :

- une utilité économique marginale propre
- une capacité à réallouer du capital intelligemment
- une non-confusion avec le moteur A
- une non-dérive vers la surconcentration ou le revenge trading automatisé

---

# 1. Mission du Moteur D

Le moteur D doit capturer les situations où :

1. un premier trade ou un premier contexte valide a déjà existé  
2. la structure de marché se reforme proprement  
3. une nouvelle entrée devient économiquement intéressante  
4. le coût marginal reste défendable  
5. la nouvelle exposition n’aggrave pas excessivement la concentration portefeuille  
6. la valeur marginale du re-entry est positive par rapport à l’absence de réentrée  

Autrement dit :

> le moteur D n’est pas un moteur d’origine, c’est un moteur de **ré-engagement discipliné**.

---

# 2. Ce que Build-16 n’est pas

Build-16 n’est pas :

- un mécanisme pour “reprendre le trade raté”
- un moteur de surtrading émotionnel automatisé
- un doublon caché du moteur A
- une permission de réentrer plusieurs fois sans limite
- une justification pour augmenter la concentration parce qu’un signal paraît beau

Build-16 est :

- une **logique de seconde chance sous contrainte**
- une **brique de réallocation conditionnelle**
- une **phase de test de valeur marginale**
- une **phase de protection contre la redondance stratégique**

## Doctrine d'activation Shadow

Le moteur D n’appartient ni au **Build-11 Light Shadow**, ni au Shadow dédié de
Build-15.

Une fois **Build-16** ouvert, le moteur D est **activé à 100% pendant sa propre
fenêtre Shadow gouvernée** (`SHADOW_ENABLED`) :
- scoré, classé, arbitré et observé aux côtés de A/B/C
- sa valeur marginale est mesurée (économique, concentration, corrélation)
- ses performances sont comparées pour vérifier la non-redondance avec A
- sa contribution portefeuille est auditée (edge marginal, churn, coût)
- sa promotion live reste strictement conditionnelle au verdict post-Shadow
- activation Shadow ≠ promotion live automatique
- Hard State : `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

---

# 3. Position de Build-16 dans le plan global

## Avant Build-16
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-15 validés
- Light stable
- A/B compris
- C au moins spécifié
- Complete Enablers analysés
- lecture portefeuille suffisamment mature
- compréhension explicite des effets de concentration et de redondance

## Activation en Shadow
- D est **activé à 100% pendant la fenêtre Shadow dédiée de Build-16**
- cette fenêtre n’est ni le `Shadow intégral` initial de Build-11, ni la
  fenêtre Shadow dédiée de Build-15
- sa valeur marginale est prouvée pendant cette phase Shadow dédiée, aux côtés
  de A/B/C
- sa promotion réelle dépend des résultats observés (verdict post-Shadow)
- D reste un moteur essayé plus tard dans le rollout, puis promu seulement si validé

---

# 4. Objectifs stratégiques de Build-16

Build-16 doit établir quatre vérités :

## 4.1 Vérité structurelle
Le système sait-il distinguer une vraie reformation de structure d’un simple bruit post-move ?

## 4.2 Vérité économique
La réentrée a-t-elle une valeur marginale nette positive après coûts, ou ne fait-elle qu’ajouter une exposition redondante ?

## 4.3 Vérité de non-duplication
D apporte-t-il quelque chose que A n’apporte pas déjà en première entrée ?

## 4.4 Vérité portefeuille
D peut-il exister sans faire exploser la concentration, les budgets corrélés ou la stérilisation ?

---

# 5. Périmètre du Build-16

## 5.1 Inclus

- définition détaillée du moteur D
- logique de re-entry et de second chance
- logique de lien avec l’historique du trade initial
- contraintes de coût marginal
- contraintes de concentration
- métriques de validation
- conditions de désactivation
- tests de non-duplication avec A

## 5.2 Exclus

- activation automatique de D en production
- re-entry illimitée en cascade
- politique Complete globale
- moteur discrétionnaire d’overtrading
- UI Complete finale

---

# 6. Positionnement du moteur D dans les profils

## 6.1 Light
- **non interdit par principe**
- activable seulement sous gates spécifiques, budget corrélation strict,
  historique trade-aware et bornes runtime très serrées
- observable analytiquement si explicitement prévu

## 6.2 Complete
- **candidat autorisé**
- uniquement après validation spécifique Build-16
- jamais activé par défaut sur toutes les paires

## 6.3 Règle fondamentale

Le moteur D n’a pas le droit d’exister simplement parce qu’il est “intuitivement logique”.  
Il doit prouver une valeur marginale mesurable.

---

# 7. Paires autorisées

## 7.1 Univers prioritaire
- BTC/USDT
- ETH/USDT
- BNB/USDT
- SOL/USDT
- LINK/USDT

## 7.2 Univers optionnel tardif
- XRP/USDT
- AVAX/USDT
- ADA/USDT

## 7.3 Règle de prudence

Le moteur D doit commencer sur les paires :
- les plus liquides
- les plus lisibles structurellement
- les moins susceptibles de faux second souffle
- les moins coûteuses à réengager

---

# 8. Régimes compatibles

## 8.1 Favorables
- pullback propre après un premier move valide
- consolidation courte / réaccumulation propre
- reformation claire de structure
- continuation encore exploitable sans être trop tardive
- contexte de marché non stressé

## 8.2 Défavorables
- fatigue avancée du move
- marché devenu erratique
- contexte headline / stress
- coût marginal trop élevé
- réentrée motivée uniquement par “le move est reparti”
- contexte déjà sur-étendu

## 8.3 Règle critique

Le moteur D doit accepter que beaucoup de réentrées séduisantes soient en réalité mauvaises économiquement, car le move a déjà livré l’essentiel de sa valeur.

---

# 9. Inputs minimaux obligatoires

## 9.1 Inputs historiques
- existence d’un trade ou contexte initial valide
- type du premier moteur / premier setup
- timing de sortie ou non-exécution du premier trade
- motif principal de fin ou d’absence du premier engagement

## 9.2 Inputs structurels
- reformation de structure
- pullback / consolidation exploitable
- point de réengagement identifiable
- invalidation du re-entry

## 9.3 Inputs contextuels
- régime courant
- pair health
- data freshness
- consistency
- contexte directionnel plus large

## 9.4 Inputs économiques
- coût marginal attendu
- CE marginale attendue
- budget corrélation libre
- budget perte libre
- exposition déjà présente ou non sur la paire / cluster

---

# 10. Outputs obligatoires

Le moteur D doit produire :

- `SignalCandidate` moteur D
- score brut D
- composantes du score D
- lien vers le contexte ou trade d’origine
- coût marginal attendu
- CE marginale attendue
- concentration marginale induite
- invalidation de re-entry
- horizon attendu
- suggestion de tier sizing
- raison de non-émission

---

# 11. Architecture interne recommandée du moteur D

## 11.1 Sous-composants

### 11.1.1 prior_context_linker_D
Rôle :
- relier la réentrée au contexte / trade initial

### 11.1.2 structure_reformation_detector_D
Rôle :
- détecter la reformation exploitable de structure

### 11.1.3 marginal_value_checker_D
Rôle :
- vérifier que la valeur marginale est positive

### 11.1.4 concentration_guard_D
Rôle :
- vérifier que la réentrée n’aggrave pas excessivement la concentration

### 11.1.5 anti_revenge_filter_D
Rôle :
- exclure les réentrées motivées uniquement par le manque à gagner émotionnel déguisé

### 11.1.6 invalidation_mapper_D
Rôle :
- définir l’invalidation du re-entry

### 11.1.7 signal_reporter_D
Rôle :
- produire la sortie complète audit-able

---

# 12. Logique fondamentale du moteur D

## 12.1 Principe

Une réentrée exploitable n’est pas :
- “le marché repart, on y retourne”
- “on avait raison, on veut remettre”
- “on a manqué le move, on chasse le prix”

Une réentrée exploitable suppose :
- une première lecture valide
- une pause ou déformation identifiable
- une nouvelle structure suffisamment propre
- une valeur marginale qui survit au coût supplémentaire

## 12.2 Variables et formules utiles

Espérance conditionnelle de réentrée :
\[
\mu_{D,j,s \mid history} = \mathbb{E}[r \mid moteur=D,\ paire=j,\ régime=s,\ historique]
\]

Variance conditionnelle :
\[
\sigma^2_{D,j,s \mid history} = \mathbb{V}[r \mid moteur=D,\ paire=j,\ régime=s,\ historique]
\]

Capital efficiency marginale :
\[
CE_{D,j,s}^{marg} = \frac{\mathbb{E}[PnL \mid D,j,s]}{x \cdot h}
\]

Valeur marginale nette :
\[
MV_{D,i}^{net} = x_i \cdot \left(\mathbb{E}[g_i \mid D] - \mathbb{E}[c_i \mid D]\right)
\]

Condition minimale :
\[
MV_{D,i}^{net} > \epsilon
\]

## 12.3 Règle

Le moteur D doit être évalué **marginalement**, pas comme s’il s’agissait d’un moteur de première entrée.

---

# 13. Logique de reformation de structure

## 13.1 Rôle

Le moteur D n’est valable que si la structure s’est reformée de façon identifiable après le premier épisode.

## 13.2 Variables recommandées
- pullback structuré
- consolidation propre
- reprise de direction après pause
- maintien de zones clés
- invalidation claire

## 13.3 Dérives à éviter
- réengager sur simple accélération tardive
- appeler “reformation” un simple bruit de continuation
- ignorer la fatigue du move

---

# 14. Anti-revenge filter du moteur D

## 14.1 Rôle

Empêcher les réentrées dont la justification réelle serait :
- avoir raté le premier move
- vouloir “récupérer” un profit manqué
- se ré-exposer sans nouveau fondement économique

## 14.2 Composantes recommandées
- absence de nouvelle structure exploitable
- coût marginal trop élevé
- concentration déjà importante sur le thème
- move déjà trop avancé
- CE marginale insuffisante
- proximité excessive avec la première entrée sans nouveau contexte

## 14.3 Formulation conceptuelle

Le moteur D doit être rejeté si :

\[
\mathbb{E}[g_i \mid D,\ history] - \mathbb{E}[c_i \mid D,\ history] \le \epsilon
\]

ou si :

\[
\text{Concentration marginale} > \text{budget disponible}
\]

## 14.4 Dérive critique à éviter

Le moteur D ne doit jamais servir d’alibi algorithmique à une émotion de trade.

---

# 15. Score brut D

## 15.1 Construction

Le score brut D doit être composé de blocs interprétables :

\[
S_D^{raw} = S_D^{history} + S_D^{reformation} + S_D^{marginal\_value} + S_D^{cost\_preference}
\]

### Blocs recommandés

#### History
- qualité du contexte initial
- validité du premier épisode

#### Reformation
- qualité du pullback / reformation
- lisibilité de la nouvelle entrée

#### Marginal value
- valeur additionnelle attendue
- absence de redondance totale

#### Préférence de coût
- coût marginal raisonnable
- réengagement pas trop tardif

## 15.2 Interdits
- score opaque
- réutiliser exactement le score A avec un nom différent
- hard blocks cachés dans le score

---

# 16. Pénalités spécifiques au moteur D

Le moteur D peut être pénalisé pour :
- reformation peu convaincante
- coût marginal un peu élevé
- proximité excessive avec la première entrée
- concentration déjà élevée
- régime ambigu
- move possiblement trop avancé

## 16.1 Formules utiles

Pénalité additive :
\[
Pen_{D,i} = \sum_{\ell=1}^{L} pen_{D,i,\ell}
\]

Score pénalisé :
\[
S_{D,i} = S_{D,i}^{raw} - Pen_{D,i}
\]

Multiplicateur de taille :
\[
m_{D,i} = \prod_{\ell=1}^{L} m_{D,i,\ell}
\]

## 16.2 Règle critique

Le moteur D doit intégrer explicitement une pénalité de concentration marginale ou un garde dédié, même si la décision finale reste dans le risk backbone global.

---

# 17. Hard blockers compatibles

Le moteur D n’a pas de hard blockers propriétaires hors registre canonique.  
Il doit utiliser les hard blockers existants :

- stale hard
- pair suspended
- cost impossible
- exposure breach
- loss budget breach
- beta BTC breach
- cluster breach
- reconciliation critical
- infra critical

Le moteur D doit éviter d’inventer des blocages “psychologiques” déguisés.

---

# 18. Contraintes de coût

## 18.1 Principe

Le coût marginal d’un re-entry est souvent sous-estimé :
- le move est plus avancé
- la liquidité peut être moins favorable
- l’adverse selection peut être plus élevée
- le coût d’erreur est plus grand car on se réexpose

## 18.2 Formules utiles

Break-even prudent :
\[
BE_{D,j} = \mathbb{E}[c \mid moteur=D,\ paire=j]
\]

Valeur marginale nette :
\[
EV_{D,i}^{net} = x_i \cdot (\mathbb{E}[g_i \mid D] - \mathbb{E}[c_i \mid D])
\]

Condition minimale :
\[
EV_{D,i}^{net} > \epsilon
\]

## 18.3 Règles

- le coût marginal doit être mesuré spécifiquement
- D doit être refusé si le re-entry est trop tardif
- D doit être comparé à l’option “ne rien faire”

## 18.4 Dérives à éviter
- considérer la réentrée comme “quasi gratuite”
- oublier adverse selection
- comparer D à un moteur d’entrée initiale sans notion de marge

---

# 19. Contraintes de sizing

## 19.1 Principe

Le moteur D est un moteur de réengagement prudent.  
Il ne doit pas commencer comme moteur de concentration.

## 19.2 Règles
- Tier 1 par défaut
- Tier 2 éventuellement après validation
- Tier 3 interdit au démarrage de D
- interdiction de cumuler plusieurs réentrées agressives sur un même thème

## 19.3 Formules utiles

Taille candidate :
\[
x_i = x_{base} \cdot m_i \cdot \psi(S_i)
\]

Cap spécifique démarrage D :
\[
x_i^{(D)} \le x_{D,start,max}
\]

Cap de réexposition thématique :
\[
\sum_{i \in thème} x_i^{existing} + x_i^{(D)} \le X_{theme,max}
\]

## 19.4 Dérives à éviter
- “on remet plus petit donc ce n’est pas risqué”
- utiliser D pour reconstruire une position trop concentrée
- ignorer le thème ou cluster déjà présent

---

# 20. Invalidation et sortie logique

## 20.1 Principe

Le moteur D doit produire une invalidation claire :
- reformation échouée
- reprise avortée
- coût / temps devenu défavorable
- réengagement invalidé par le contexte

## 20.2 Contenu minimal
- condition d’échec de la reformation
- horizon attendu
- condition de dégradation de CE marginale
- lien explicite avec le contexte initial

## 20.3 Dérive à éviter
- réentrée “ouverte” sans vraie thèse de sortie

---

# 21. Logs obligatoires du moteur D

Le moteur D doit logger, au minimum :

- paire
- régime
- identifiant du contexte / trade initial
- type de lien avec le premier épisode
- structure reformée détectée
- score brut
- score pénalisé
- coût marginal attendu
- CE marginale attendue
- concentration marginale induite
- invalidation proposée
- tier proposé
- raison de non-émission
- raison de rejet par hard block
- raison de rejet par ranking
- indicateur de duplication possible avec A

---

# 22. Métriques de validation du moteur D

## 22.1 Métriques principales
- fréquence utile D
- rendement net D
- coût moyen D
- coût p90 D
- CE D
- Sharpe par trade D
- drawdown D
- taux de concentration induite D

## 22.2 Métriques de valeur marginale
- gain marginal portefeuille avec D
- coût marginal de réengagement
- part des D qui auraient dû être des A
- part des D sans valeur marginale

## 22.3 Métriques secondaires
- délai moyen après le premier épisode
- part des re-entries trop tardifs
- part des no-trade due au coût marginal
- part des no-trade due à la concentration

## 22.4 Formules utiles

Fréquence utile D :
\[
F_{utile,D} = \frac{\text{trades D à expectancy utile}}{\text{temps}}
\]

CE D :
\[
CE_D = \frac{\sum_{i \in D} PnL_i}{\sum_{i \in D} x_i h_i}
\]

Sharpe D :
\[
Sh_D = \frac{\mu_D}{\sigma_D}
\]

Gain marginal portefeuille :
\[
\Delta CE_{port}^{(D)} = CE_{port}^{A,B,C,D} - CE_{port}^{A,B,C}
\]

Taux de redondance avec A :
\[
RedundancyRate_{D/A} = \frac{N_{D,\text{quasi-identiques à A}}}{N_D}
\]

---

# 23. Tests obligatoires Build-16

## 23.1 Tests de structure
- lien avec contexte initial correctement établi
- reformation détectée correctement
- pas de signal sans nouvel appui structurel
- invalidation définie

## 23.2 Tests anti-revenge
- refus si seule justification = move reparti
- refus si coût marginal trop élevé
- refus si concentration trop élevée
- refus si absence de valeur marginale

## 23.3 Tests économiques
- coût marginal calculé
- CE marginale calculée
- no-trade explicite si EV net insuffisante
- comparaison D vs ne rien faire possible

## 23.4 Tests portefeuille
- refus si budgets dépassés
- refus si réexposition thématique excessive
- non-duplication partielle avec A mesurable
- sizing de démarrage respecté

---

# 24. Conditions de sortie de Build-16

Build-16 est terminé si :

- le moteur D est complètement spécifié
- les signaux D sont auditables
- le coût marginal de D est explicitement intégré
- l’anti-revenge filter est en place
- la non-duplication avec A peut être mesurée
- la concentration marginale est visible
- le sizing de démarrage est borné
- les logs et métriques de validation existent

---

# 25. Critères de refus de sortie

Refuser Build-16 si :

- D ressemble à un A déguisé
- D sert principalement à remettre une exposition déjà consommée
- la valeur marginale n’est pas démontrable
- le coût marginal n’est pas correctement mesuré
- D n’a pas d’invalidation claire
- D nécessite une taille agressive pour exister
- le risque de concentration supplémentaire n’est pas mesuré

---

# 26. Dérives globales Build-16 à ne pas faire

- créer D pour “ne pas rater la suite”
- oublier que la meilleure réentrée est souvent de ne pas réentrer
- sous-estimer la concentration marginale
- ignorer le coût marginal réel
- complexifier D avant d’avoir prouvé une valeur économique minimale

---

# 27. Verdict final Build-16

Build-16 est la phase où la V5.3 doit prouver qu’une logique de réentrée
mérite une activation réelle **en plus** du coeur initial A/B.

Si Build-16 est bien fait :
- D apporte une vraie valeur marginale
- le portefeuille peut réallouer intelligemment du capital
- l’extension COMPLETE du rollout gagne un moteur discipliné supplémentaire

Si Build-16 est mal fait :
- D deviendra un moteur de surconcentration
- le portefeuille gagnera du bruit émotionnel déguisé
- la Complete s’encombrera d’un moteur inutile

Donc :

> Build-16 doit être traité comme un **build bloquant de justification marginale d’un moteur de réengagement**, pas comme une simple extension “logique” du système.

---

## Fin du document
