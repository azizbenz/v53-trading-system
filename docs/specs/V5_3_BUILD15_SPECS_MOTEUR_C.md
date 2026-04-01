# V5.3 — BUILD-15 SPECS MODULES
## Moteur C Pack — Breakout Continuation
### Specs détaillées du troisième moteur cible
### Quinzième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-15** du plan officiel V5.3.

Build-15 a une mission unique :

> spécifier et valider le **Moteur C — Breakout Continuation**, c’est-à-dire le moteur chargé d’exploiter les sorties de range et les expansions confirmées qui méritent une logique de continuation distincte du moteur A.

Le moteur C ne doit pas exister pour “ajouter un moteur”.  
Il ne doit exister que s’il démontre :

- une utilité économique propre
- une fréquence utile additionnelle
- une contribution portefeuille distincte
- une non-duplication avec le moteur A

---

# 1. Mission du Moteur C

Le moteur C doit capturer les situations où :

1. un range, une compression ou une structure d’attente identifiable existe  
2. une cassure ou expansion se produit avec confirmation suffisante  
3. la poursuite du mouvement a encore une probabilité exploitable  
4. le coût d’entrée n’a pas déjà détruit l’edge  
5. l’opportunité n’est pas déjà couverte de manière satisfaisante par le moteur A  

Autrement dit :

> le moteur C n’exploite pas la “qualité premium” générale d’un move, il exploite spécifiquement la **continuation post-breakout** quand cette continuation garde un edge net défendable.

---

# 2. Ce que Build-15 n’est pas

Build-15 n’est pas :

- un doublon nerveux du moteur A
- une permission de traiter chaque spike comme breakout
- une excuse pour trader davantage en payant plus de coût
- un moteur de momentum brut sans lecture structurelle
- une activation automatique en production Complete

Build-15 est :

- une **spécification de continuation disciplinée**
- une **couche testant une hypothèse économique distincte**
- une **formalisation d’un moteur natif de la solution complète**
- une **phase de validation de non-redondance**

## Doctrine d’activation Shadow

Le moteur C est **activé à 100% pendant le Shadow 30 jours** (`SHADOW_ENABLED`) :
- scoré, classé, arbitré et observé aux côtés de A/B
- ses performances sont comparées à A pour vérifier la non-duplication
- sa contribution portefeuille est mesurée (fréquence utile, edge marginal, coût)
- sa promotion live reste strictement conditionnelle au verdict post-Shadow
- activation Shadow ≠ promotion live automatique
- Hard State : `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

---

# 3. Position de Build-15 dans le plan global

## Avant Build-15
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-14 validés
- Light stable
- A et B compris et surveillés
- Complete Enablers évalués
- microstructure enrichie et régime enrichi au moins lisibles
- lecture portefeuille suffisamment mature pour juger la contribution marginale de C

## Activation en Shadow
- C est **activé à 100% en Shadow** dès le début des 30 jours, aux côtés de A/B/D
- son utilité est prouvée pendant ces 30 jours de Shadow complet
- sa promotion réelle dépend des résultats observés (verdict post-Shadow)
- il n'est plus "attendu seulement plus tard" : il est essayé tôt en Shadow, promu tard si validé

---

# 4. Objectifs stratégiques de Build-15

Build-15 doit établir quatre vérités :

## 4.1 Vérité structurelle
Le système sait-il reconnaître une cassure exploitable, différente d’un simple move déjà premium traité par A ?

## 4.2 Vérité économique
Le moteur C produit-il un edge net qui survit aux coûts souvent élevés des breakouts ?

## 4.3 Vérité de non-duplication
C apporte-t-il quelque chose que A n’apporte pas déjà ?

## 4.4 Vérité portefeuille
C améliore-t-il la fréquence utile ou la diversité d’edge, sans détériorer exagérément la concentration et le coût ?

---

# 5. Périmètre du Build-15

## 5.1 Inclus

- définition détaillée du moteur C
- logique de range / compression / cassure / continuation
- logique anti-faux-breakout
- contraintes de coût
- contraintes de sizing
- métriques de validation
- conditions de désactivation
- tests de non-duplication avec A

## 5.2 Exclus

- moteur D
- activation Complete pleine
- UI Complete finale
- sizing tiers agressif
- mise en production automatique

---

# 6. Positionnement du moteur C dans les profils

## 6.1 Light
- **non interdit par principe**
- activable seulement sous gates spécifiques, budget coût strict, observabilité
  renforcée et bornes runtime très serrées
- shadow analytique autorisé si explicitement prévu

## 6.2 Complete
- **candidat autorisé**
- uniquement après validation spécifique Build-15
- jamais activé par défaut sur toutes les paires

## 6.3 Règle fondamentale

Le moteur C n’a pas le droit d’exister en production simplement parce qu’il est “cohérent théoriquement”.  
Il doit prouver une valeur marginale.

---

# 7. Paires autorisées

## 7.1 Univers prioritaire
- BTC/USDT
- ETH/USDT
- SOL/USDT
- BNB/USDT
- XRP/USDT
- LINK/USDT
- AVAX/USDT

## 7.2 Univers optionnel tardif
- ADA/USDT
- TON/USDT
- DOGE/USDT
- DOT/USDT
- TRX/USDT

## 7.3 Règle de prudence

Les paires les plus “cassantes” ne sont pas automatiquement les meilleures paires pour C.  
C doit privilégier :
- la lisibilité structurelle
- la continuité exploitable
- des coûts encore défendables
- une profondeur compatible avec l’exécution

---

# 8. Régimes compatibles

## 8.1 Favorables
- compression identifiable
- sortie de range propre
- expansion confirmée
- continuation non encore trop avancée
- contexte de marché directionnel ou semi-directionnel compatible

## 8.2 Défavorables
- faux spike sans structure
- expansion déjà trop tardive
- stress désordonné
- marché “headline-driven” trop violent
- coût explosif
- régime incohérent

## 8.3 Règle critique

Le moteur C doit accepter que le meilleur breakout est souvent celui qu’il **ne prend pas**, si le coût ou la maturité du move ont déjà absorbé l’edge.

---

# 9. Inputs minimaux obligatoires

## 9.1 Inputs structurels
- borne haute / basse du range
- qualité du range ou de la compression
- durée de la compression
- position relative du prix à la cassure
- état de continuation déjà réalisé

## 9.2 Inputs contextuels
- régime courant
- confiance de régime
- pair health
- data freshness
- consistency
- contexte directionnel plus large

## 9.3 Inputs économiques
- coût attendu
- break-even prudent
- CE attendue
- taille candidate
- budget corrélation libre
- budget perte libre

## 9.4 Inputs enrichis recommandés
- microstructure enrichie si disponible
- volume de cassure
- OFI/BI/MP contextuels
- lecture de toxicité de l’expansion

---

# 10. Outputs obligatoires

Le moteur C doit produire :

- `SignalCandidate` moteur C
- score brut C
- composantes du score C
- type de cassure détectée
- contexte de continuation
- coût attendu
- CE attendue
- invalidation de breakout
- horizon attendu
- suggestion de tier sizing
- raison de non-émission

---

# 11. Architecture interne recommandée du moteur C

## 11.1 Sous-composants

### 11.1.1 range_structure_detector_C
Rôle :
- identifier un range / une compression exploitable

### 11.1.2 breakout_detector_C
Rôle :
- identifier la cassure de la structure

### 11.1.3 continuation_viability_checker_C
Rôle :
- juger si la continuation a encore un edge

### 11.1.4 anti_fake_breakout_filter_C
Rôle :
- réduire les faux breakouts et spikes sans suite

### 11.1.5 cost_feasibility_C
Rôle :
- rejeter les cassures déjà trop chères

### 11.1.6 invalidation_mapper_C
Rôle :
- définir l’invalidation du breakout

### 11.1.7 signal_reporter_C
Rôle :
- produire la sortie complète audit-able

---

# 12. Logique structurelle du moteur C

## 12.1 Principe

Un breakout exploitable n’est pas “un prix qui dépasse un niveau”.

Il faut au minimum :
- une structure préalable identifiable
- une cassure effective
- une probabilité crédible de continuation
- une absence de sur-extension évidente

## 12.2 Variables et formules utiles

Bornes du range :
\[
p_{range,max},\quad p_{range,min}
\]

Largeur du range :
\[
W_{range} = p_{range,max} - p_{range,min}
\]

Condition de cassure haussière :
\[
p_t > p_{range,max} + \delta
\]

Condition de cassure baissière :
\[
p_t < p_{range,min} - \delta
\]

Distance normalisée à la cassure :
\[
d_t^{brk} = \frac{p_t - p_{range,max}}{W_{range}}
\]

ou en version baissière symétrique.

Probabilité économique conceptuelle :
\[
\mathbb{P}(\text{continuation exploitable} \mid \text{breakout structuré}) > \mathbb{P}(\text{faux breakout})
\]

## 12.3 Règle

Le moteur C doit explicitement distinguer :
- cassure initiale
- confirmation
- continuation exploitable
- sur-extension tardive

---

# 13. Logique de confirmation / continuation

## 13.1 Rôle

Un breakout C n’est valable que si la cassure n’est pas déjà entièrement consommée par le coût et la distance parcourue.

## 13.2 Variables recommandées
- distance depuis le niveau de cassure
- volume ou activité de confirmation
- persistance du mouvement
- qualité microstructure éventuelle
- absence de re-entrée immédiate dans le range

## 13.3 Formules utiles

Volume de cassure :
\[
Vol_t > \theta_{Vol}
\]

Persistance :
\[
\bar{M}_{t,w} = \frac{1}{w}\sum_{u=t-w+1}^{t} M_u
\]

Continuation moyenne conditionnelle :
\[
\mu_{C,j,s} = \mathbb{E}[r \mid moteur=C,\ paire=j,\ régime=s]
\]

Capital efficiency attendue :
\[
CE_{C,j,s} = \frac{\mathbb{E}[PnL \mid C,j,s]}{x \cdot h}
\]

## 13.4 Dérive à éviter

Confondre “cassure visible” et “continuation encore rentable”.

---

# 14. Anti-fake-breakout filter du moteur C

## 14.1 Rôle

Réduire les cas où :
- le prix dépasse juste le range
- puis réintègre rapidement la zone
- ou s’étend trop brièvement sans suite exploitable

## 14.2 Composantes recommandées
- manque de persistance
- manque de volume utile
- réintégration rapide du range
- coût trop élevé
- microstructure contradictoire
- régime incohérent

## 14.3 Formulation conceptuelle

Le moteur C doit être pénalisé ou refusé si :

\[
\mathbb{P}(\text{réintégration / fake breakout} \mid contexte) \ge \mathbb{P}(\text{continuation exploitable} \mid contexte)
\]

## 14.4 Dérive critique à éviter

Le moteur C ne doit jamais devenir un moteur “acheter tout ce qui dépasse un niveau”.

---

# 15. Score brut C

## 15.1 Construction

Le score brut C doit être composé de blocs interprétables :

\[
S_C^{raw} = S_C^{structure} + S_C^{breakout} + S_C^{continuation} + S_C^{cost\_preference}
\]

### Blocs recommandés

#### Structure
- qualité du range / de la compression
- propreté du niveau cassé

#### Breakout
- qualité de la cassure
- caractère non ambigu de la sortie

#### Continuation
- persistance
- volume
- absence de réintégration

#### Préférence de coût
- opportunités moins chères et moins tardives favorisées

## 15.2 Interdits
- score opaque
- score reposant sur un seul seuil de cassure
- hard blocks cachés dans le score

---

# 16. Pénalités spécifiques au moteur C

Le moteur C peut être pénalisé pour :
- cassure trop tardive
- coût un peu élevé mais pas fatal
- confirmation incomplète
- régime ambigu
- contexte microstructure mitigé
- distance déjà importante au point de breakout

## 16.1 Formules utiles

Pénalité additive :
\[
Pen_{C,i} = \sum_{\ell=1}^{L} pen_{C,i,\ell}
\]

Score pénalisé :
\[
S_{C,i} = S_{C,i}^{raw} - Pen_{C,i}
\]

Multiplicateur de taille :
\[
m_{C,i} = \prod_{\ell=1}^{L} m_{C,i,\ell}
\]

## 16.2 Règle critique

La “tardiveté” du breakout doit être traitée explicitement.  
Un breakout tardif peut rester visuellement beau tout en étant économiquement mauvais.

---

# 17. Hard blockers compatibles

Le moteur C n’a pas de hard blockers propriétaires hors registre canonique.  
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

Le moteur C doit éviter d’introduire des blocages “de confort”.

---

# 18. Contraintes de coût

## 18.1 Principe

Le moteur C est souvent **plus coûteux** à exécuter que A ou B, parce qu’il intervient dans des zones d’expansion.

Il doit donc être plus exigeant en lecture économique.

## 18.2 Formules utiles

Break-even prudent :
\[
BE_{C,j} = \mathbb{E}[c \mid moteur=C,\ paire=j]
\]

Valeur nette attendue :
\[
EV_{C,i}^{net} = x_i \cdot (\mathbb{E}[g_i \mid C] - \mathbb{E}[c_i \mid C])
\]

Condition minimale :
\[
EV_{C,i}^{net} > \epsilon
\]

## 18.3 Règles

- le coût p90 doit compter fortement
- le moteur C doit être refusé si l’expansion déjà réalisée rend le coût prohibitif
- le moteur C doit être comparé à A non seulement en signal, mais en coût net

## 18.4 Dérives à éviter
- breakout “spectaculaire” mais trop tardif
- coût moyen uniquement
- sous-estimer adverse selection post-breakout

---

# 19. Contraintes de sizing

## 19.1 Principe

Le moteur C n’est **pas** un moteur à Tier 3 initialement.

Il doit commencer comme moteur d’essai discipliné.

## 19.2 Règles
- Tier 1 par défaut
- Tier 2 éventuellement après validation
- Tier 3 interdit au démarrage de C
- pas de concentration spéciale “parce que breakout”

## 19.3 Formules utiles

Taille candidate :
\[
x_i = x_{base} \cdot m_i \cdot \psi(S_i)
\]

Cap par position :
\[
x_i \le x_{max,pos}
\]

Cap spécifique démarrage C :
\[
x_i^{(C)} \le x_{C,start,max}
\]

## 19.4 Dérives à éviter
- augmenter la taille parce que la cassure “semble évidente”
- accepter un sizing agressif sans historique réel de coût
- négliger la corrélation avec A

---

# 20. Invalidation et sortie logique

## 20.1 Principe

Le moteur C doit produire une invalidation claire du breakout :
- retour dans le range
- absence de continuation après la cassure
- confirmation avortée
- coût devenu défavorable si entrée retardée

## 20.2 Contenu minimal
- niveau ou condition de retour dans le range
- condition d’échec de continuation
- horizon attendu
- niveau de dégradation de CE

## 20.3 Dérive à éviter
- “tant que ça monte on garde”
- invalidation floue non codée

---

# 21. Logs obligatoires du moteur C

Le moteur C doit logger, au minimum :

- paire
- régime
- bornes du range
- largeur du range
- type de cassure
- distance à la cassure
- score brut
- score pénalisé
- coût attendu
- CE attendue
- invalidation proposée
- tier proposé
- raison de non-émission
- raison de rejet par hard block
- raison de rejet par ranking
- indicateur de duplication possible avec A

---

# 22. Métriques de validation du moteur C

## 22.1 Métriques principales
- fréquence utile C
- rendement net C
- coût moyen C
- coût p90 C
- CE C
- Sharpe par trade C
- drawdown C
- taux de faux breakout C

## 22.2 Métriques de non-duplication
- corrélation C / A
- gain marginal portefeuille avec C
- part des signaux C déjà couverts par A
- contribution C à \(K_{eff}\)

## 22.3 Métriques secondaires
- temps moyen de continuation
- part des no-trade due au coût
- part des no-trade due à la tardiveté
- réintégration du range rate

## 22.4 Formules utiles

Fréquence utile C :
\[
F_{utile,C} = \frac{\text{trades C à expectancy utile}}{\text{temps}}
\]

CE C :
\[
CE_C = \frac{\sum_{i \in C} PnL_i}{\sum_{i \in C} x_i h_i}
\]

Sharpe C :
\[
Sh_C = \frac{\mu_C}{\sigma_C}
\]

Taux de faux breakout :
\[
FakeBrkRate_C = \frac{N_{C,\text{fake breakout}}}{N_{C,\text{trades}}}
\]

Gain marginal portefeuille :
\[
\Delta CE_{port}^{(C)} = CE_{port}^{A,B,C} - CE_{port}^{A,B}
\]

---

# 23. Tests obligatoires Build-15

## 23.1 Tests de structure
- range détecté correctement
- cassure détectée correctement
- pas de signal si pas de structure préalable
- invalidation définie

## 23.2 Tests anti-faux-breakout
- réintégration rapide détectée
- cassure trop tardive pénalisée / refusée
- coût trop élevé refusé
- confirmation insuffisante pénalisée

## 23.3 Tests économiques
- coût attendu calculé
- CE attendue calculée
- no-trade explicite si EV net insuffisante
- comparaison coût C vs A possible

## 23.4 Tests portefeuille
- refus si budgets dépassés
- comparaison C vs A
- non-duplication partielle mesurable
- sizing de démarrage respecté

---

# 24. Conditions de sortie de Build-15

Build-15 est terminé si :

- le moteur C est complètement spécifié
- les signaux C sont auditables
- le coût de C est explicitement intégré
- l’anti-fake-breakout filter est en place
- la non-duplication avec A peut être mesurée
- le sizing de démarrage est borné
- les logs et métriques de validation existent

---

# 25. Critères de refus de sortie

Refuser Build-15 si :

- C ressemble à un A plus nerveux
- C repose surtout sur du coût élevé et du momentum tardif
- le taux de faux breakout prévisible est trop élevé
- la non-duplication avec A n’est pas démontrable
- C ne produit pas de CE attendue
- C n’a pas d’invalidation claire
- C nécessite une taille agressive pour exister

---

# 26. Dérives globales Build-15 à ne pas faire

- créer C pour “faire plus de trades”
- faire de C un pur moteur breakout sans structure préalable
- oublier que le coût tue les breakouts tardifs
- sous-estimer la redondance avec A
- complexifier C avant d’avoir prouvé une valeur économique minimale

---

# 27. Verdict final Build-15

Build-15 est la phase où la V5.3 doit prouver qu’un moteur de continuation
mérite une activation réelle **en plus** du coeur initial A/B.

Si Build-15 est bien fait :
- C apporte une logique identifiable
- le portefeuille gagne potentiellement une fréquence utile ou une diversité réelle
- l’extension COMPLETE du rollout repose sur une vraie base

Si Build-15 est mal fait :
- C ne sera qu’un doublon coûteux
- le portefeuille gagnera du bruit au lieu d’un edge
- la Complete se compliquera sans bénéfice

Donc :

> Build-15 doit être traité comme un **build bloquant de justification économique d’un moteur supplémentaire**, pas comme une simple étape de remplissage de la Complete.

---

## Fin du document
