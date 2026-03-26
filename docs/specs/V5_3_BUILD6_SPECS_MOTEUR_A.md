# V5.3 — BUILD-6 SPECS MODULES
## Moteur A Pack — Premium Trend / Expansion
### Specs détaillées du premier moteur live
### Sixième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-6** du plan officiel V5.3.

Build-6 a une mission unique :

> rendre opérationnel le **Moteur A — Premium Trend / Expansion**, c’est-à-dire le moteur haute conviction héritier du cœur V5.2, mais dans une version compatible avec la V5.3, donc moins stérile, plus lisible économiquement et mieux intégrée au portefeuille.

Le Build-6 couvre le pack logique du moteur A, pas l’ensemble du portefeuille.  
Le moteur A doit être spécifié de manière à pouvoir être :

- testé en shadow
- audité ex post
- comparé au moteur B
- limité par le risk backbone
- classé par le scoring backbone
- exécuté par le build exécution déjà défini

---

# 1. Principes Build-6

## 1.1 Objectif stratégique

Le moteur A doit rester :
- le moteur de plus haute conviction
- le moteur qui peut justifier les meilleures allocations
- le moteur de référence qualitative du système

Mais il ne doit plus être :
- un moteur “parfait mais inutilisable”
- une machine à veto implicites
- un moteur si rare qu’il devient économiquement décoratif
- un moteur qui absorbe toutes les logiques de trend, breakout et re-entry en une seule boîte opaque

## 1.2 Position dans l’architecture

Le moteur A est :
- **autorisé en Light**
- **autorisé en Complete**
- **priorité P0**
- **moteur de référence pour la conviction**
- **candidat principal au Tier 3**, sous contraintes strictes

## 1.3 Critère de réussite

Build-6 est réussi si :

- le moteur A produit des signaux clairement définis
- le moteur A n’est pas une boîte noire
- le moteur A ne duplique pas déjà le moteur C
- le moteur A garde une qualité de coût acceptable
- le moteur A a une fréquence utile non nulle
- le moteur A peut être audité par paire, régime et coût
- le moteur A reste compatible avec les budgets corrélation et portefeuille

## 1.4 Critère d’échec

Build-6 échoue si :

- le moteur A devient trop rare
- le moteur A réclame trop de confirmations
- le moteur A absorbe toute la logique breakout de façon floue
- le moteur A dépend d’un score impossible à lire
- le moteur A ne justifie pas réellement une meilleure allocation
- le moteur A est structurellement trop cher à exécuter

---

# 2. Vocabulaire officiel du moteur A

## 2.1 Premium setup
Opportunité de tendance / expansion de qualité supérieure, caractérisée par :
- structure lisible
- contexte favorable
- coût supportable
- invalidation compréhensible
- CE attendue élevée

## 2.2 Trend continuation
Poursuite d’un mouvement déjà engagé et encore exploitable.

## 2.3 Expansion propre
Extension de mouvement sans désorganisation excessive du coût ou de la structure.

## 2.4 Conviction
Qualité relative du signal, en pratique reflétée par :
- score brut élevé
- faibles pénalités
- bon break-even
- compatibilité portefeuille
- régime favorable

---

# 3. Mission canonique du moteur A

Le moteur A doit capturer les situations où :

1. la structure de marché est clairement favorable  
2. le contexte de régime ne contredit pas l’entrée  
3. le coût attendu reste acceptable  
4. le budget portefeuille autorise une prise de risque proportionnée  
5. l’opportunité a une CE attendue supérieure au minimum requis  

Le moteur A n’est pas un moteur de fréquence.  
C’est un moteur de **qualité supérieure**, qui doit néanmoins rester **économiquement présent**.

---

# 4. Périmètre du Build-6

## 4.1 Inclus

- définition du moteur A
- inputs requis
- outputs requis
- logique structurelle
- logique contextuelle
- scoring minimal attendu
- contraintes coût
- contraintes sizing
- logs spécifiques
- métriques de validation
- tests dédiés
- conditions de désactivation

## 4.2 Exclus

- moteur B
- moteur C
- moteur D
- orchestration portefeuille multi-moteurs complète
- allocation finale inter-moteurs
- UI enrichie spécifique moteur au-delà du minimum

---

# 5. Positionnement du moteur A dans les profils

## 5.1 Light
- autorisé
- prioritaire
- activable sur 6 paires max
- principal moteur de conviction

## 5.2 Complete
- autorisé
- reste moteur premium de référence
- comparé à C et D pour éviter la duplication
- toujours soumis aux caps portefeuille

---

# 6. Paires autorisées

## 6.1 Profil Light
- BTC/USDT
- ETH/USDT
- BNB/USDT
- SOL/USDT
- XRP/USDT
- LINK/USDT

## 6.2 Profil Complete
- toutes les paires validées
- priorité aux classes A et B
- classes C seulement si coût et santé paire sont démontrés

## 6.3 Règle de prudence

Même en Complete, le moteur A ne doit pas être activé indistinctement sur toutes les paires en permanence.  
Il doit rester préférentiellement orienté vers les actifs les plus exploitables.

---

# 7. Régimes compatibles

## 7.1 Favorables
- trend propre
- expansion structurée
- reprise de mouvement après consolidation propre
- continuation cohérente dans un régime directionnel
- contexte non stressé

## 7.2 Défavorables
- range sale
- chop rapide sans direction
- expansion déjà trop tardive
- régime stressé incohérent
- santé paire dégradée
- coût d’entrée excessif

## 7.3 Règle

Un régime défavorable n’est pas nécessairement un hard block, sauf si la dégradation atteint le niveau fatal.  
Sinon, il doit se traduire en pénalité ou en baisse de priorité.

---

# 8. Inputs minimaux obligatoires

## 8.1 Inputs structurels
- direction dominante locale
- qualité de structure
- qualité de continuation
- proximité / franchissement de zones pertinentes
- stabilité relative de la tendance

## 8.2 Inputs contextuels
- régime courant
- confiance régime
- santé paire
- fraîcheur data
- cohérence flux

## 8.3 Inputs économiques
- coût attendu
- break-even prudent
- CE attendue
- taille candidate
- budget corrélation libre
- budget perte libre

## 8.4 Inputs optionnels encadrés
- confirmation microstructure minimale
- volume utile
- persistances courtes

---

# 9. Outputs obligatoires

Le moteur A doit produire :

- `SignalCandidate` moteur A
- score brut A
- composantes du score A
- coût attendu
- CE attendue
- invalidation structurelle
- horizon de détention attendu
- suggestion de tier sizing
- niveau de conviction interne
- raisons de non-émission si aucun signal

---

# 10. Architecture interne recommandée du moteur A

## 10.1 Sous-composants

### 10.1.1 structure_detector_A
Rôle :
- identifier la présence d’une structure tendance / expansion exploitable

### 10.1.2 context_validator_A
Rôle :
- vérifier que le contexte ne contredit pas fortement la structure

### 10.1.3 cost_feasibility_A
Rôle :
- vérifier que l’exécution potentielle ne tue pas l’edge

### 10.1.4 conviction_builder_A
Rôle :
- construire le niveau de conviction moteur A

### 10.1.5 invalidation_mapper_A
Rôle :
- définir l’invalidation structurelle ou logique

### 10.1.6 signal_reporter_A
Rôle :
- produire un objet de sortie complet et audit-able

---

# 11. Logique structurelle du moteur A

## 11.1 Principe

Le moteur A doit reposer sur une structure exploitable, pas sur un “sentiment de momentum”.

Le minimum est :

- direction lisible
- continuité cohérente
- absence de contradiction structurelle majeure
- contexte compatible avec la poursuite

## 11.2 Variables mathématiques utiles

Espérance conditionnelle :

\[
\mu_{A,j,s} = \mathbb{E}[r \mid moteur=A, paire=j, régime=s]
\]

Variance conditionnelle :

\[
\sigma^2_{A,j,s} = \mathbb{V}[r \mid moteur=A, paire=j, régime=s]
\]

Sharpe par trade conditionnel :

\[
Sh_{A,j,s} = \frac{\mu_{A,j,s}}{\sigma_{A,j,s}}
\]

Capital efficiency attendue :

\[
CE_{A,j,s} = \frac{\mathbb{E}[PnL \mid A,j,s]}{x \cdot h}
\]

## 11.3 Conditions minimales implicites

Un signal A doit satisfaire, conceptuellement :

\[
\mathbb{E}[g_i \mid A,j,s] > \mathbb{E}[c_i \mid A,j,s] + \delta_{safe}
\]

et

\[
CE_{A,j,s} > CE_{min}
\]

---

# 12. Logique contextuelle du moteur A

## 12.1 Rôle du contexte

Le contexte ne doit pas “décider à la place” de la structure, mais il doit :
- confirmer raisonnablement
- dégrader si contexte sale
- bloquer uniquement si contexte fatal

## 12.2 Composantes contextuelles recommandées
- régime compatible
- pair health acceptable
- data non stale
- cohérence flux acceptable
- état infra non critique
- budget risque disponible

## 12.3 Dérive à éviter

Faire de la couche contextuelle une collection de prétextes pour ne jamais prendre de trade.

---

# 13. Score brut A

## 13.1 Construction

Le score brut A doit être composé de blocs interprétables :

\[
S_A^{raw} = S_A^{structure} + S_A^{context} + S_A^{flow} + S_A^{cost\_preference}
\]

### Blocs recommandés

#### Structure
- qualité directionnelle
- continuité
- cohérence de mouvement

#### Contexte
- régime favorable
- qualité paire
- absence de contradiction majeure

#### Flow
- confirmation minimale, non dominante

#### Préférence de coût
- avantage relatif des setups moins chers à exécuter

## 13.2 Interdits
- score purement opaque
- 25 composantes sans sens clair
- dépendance à des features instables non validées
- intégrer les hard blocks dans le score brut

---

# 14. Pénalités spécifiques au moteur A

Le moteur A peut subir des soft penalties pour :

- coût un peu élevé mais pas fatal
- contexte pas parfait
- qualité microstructure moyenne
- volatilité moins propre
- conviction un peu dégradée

## 14.1 Formules utiles

Pénalité additive :
\[
Pen_{A,i} = \sum_{\ell=1}^{L} pen_{A,i,\ell}
\]

Score pénalisé :
\[
S_{A,i} = S_{A,i}^{raw} - Pen_{A,i}
\]

Multiplicateur de taille :
\[
m_{A,i} = \prod_{\ell=1}^{L} m_{A,i,\ell}
\]

## 14.2 Règle critique

Une pénalité A ne doit jamais devenir un hard blocker caché.  
Si une condition est vraiment fatale, elle doit être déplacée dans le `hard_block_gate`.

---

# 15. Hard blockers spécifiques au moteur A

Les hard blockers possibles pour A doivent rester dans la liste canonique, par exemple :

- stale hard
- pair suspended
- cost impossible
- exposure cap breach
- loss budget breach
- beta BTC breach
- cluster breach
- divergence critique de réconciliation
- état infra critique

Le moteur A ne doit pas inventer ses propres hard blockers “confort”.

---

# 16. Contraintes de coût

## 16.1 Principe

Le moteur A peut accepter un coût légèrement supérieur à B si la conviction est bien meilleure, mais il ne doit jamais devenir un moteur “cher par habitude”.

## 16.2 Formules utiles

Break-even prudent :

\[
BE_{A,j} = \mathbb{E}[c \mid moteur=A, paire=j]
\]

Valeur nette attendue :

\[
EV_{A,i}^{net} = x_i \cdot (\mathbb{E}[g_i \mid A] - \mathbb{E}[c_i \mid A])
\]

Condition minimale :

\[
EV_{A,i}^{net} > \epsilon
\]

## 16.3 Dérives à éviter
- accepter des entrées tardives trop chères
- confondre qualité de setup et tolérance illimitée au coût
- ne regarder que le coût moyen sans p90

---

# 17. Contraintes de sizing

## 17.1 Principe

Le moteur A est le meilleur candidat au Tier 3, mais seulement si :
- les caps portefeuille le permettent
- le budget perte le permet
- le budget BTC le permet
- le cluster corrélé le permet
- la santé système est bonne

## 17.2 Formules utiles

Taille candidate :
\[
x_i = x_{base} \cdot m_i \cdot \psi(S_i)
\]

Cap par position :
\[
x_i \le x_{max,pos}
\]

Cap Tier 3 :
\[
\sum_{i \in Tier3} x_i \le X_{Tier3,max}
\]

## 17.3 Interdits
- Tier 3 automatique parce que moteur A
- sizing agressif sans CE attendue élevée
- concentration sans budget corrélation libre

---

# 18. Invalidation et sortie logique

## 18.1 Principe

Le moteur A doit produire une invalidation compréhensible.  
Un signal premium sans invalidation lisible n’est pas un signal premium exploitable.

## 18.2 Contenu minimal
- niveau ou condition d’invalidation
- raison d’invalidation
- horizon de détention attendu
- dégradation logique possible

## 18.3 Dérive à éviter
- invalidation floue de type “si le marché n’est plus bon”
- logique de sortie inexistante au niveau signal

---

# 19. Logs obligatoires du moteur A

Le moteur A doit logger, au minimum :

- paire
- régime
- score brut
- score pénalisé
- composantes du score
- coût attendu
- CE attendue
- conviction
- invalidation proposée
- tier proposé
- raisons de non-émission
- raisons de rejet par hard block
- raisons de rejet par ranking

---

# 20. Métriques de validation du moteur A

## 20.1 Métriques principales
- fréquence utile A
- rendement net A
- coût moyen A
- coût p90 A
- CE A
- Sharpe par trade A
- drawdown A
- taux de stérilisation A

## 20.2 Métriques secondaires
- corrélation A / portefeuille
- corrélation A / B
- part de no-trade due au coût
- part de no-trade due aux hard blocks
- part de rejet due au ranking

## 20.3 Formules utiles

Fréquence utile A :
\[
F_{utile,A} = \frac{\text{trades A à expectancy utile}}{\text{temps}}
\]

CE A :
\[
CE_A = \frac{\sum_{i \in A} PnL_i}{\sum_{i \in A} x_i h_i}
\]

Sharpe A :
\[
Sh_A = \frac{\mu_A}{\sigma_A}
\]

Stérilisation A :
\[
SterilRate_A = \frac{\sum_{i \in A}\mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_{i \in A}A_i}
\]

---

# 21. Tests obligatoires Build-6

## 21.1 Tests de structure
- signal A émis dans un contexte tendance propre
- pas de signal A en range sale évident
- pas de signal A si coût impossible
- invalidation présente

## 21.2 Tests de cohérence
- même inputs → même sortie A
- composantes du score visibles
- score brut versionné
- pénalités visibles
- hard blocks séparés

## 21.3 Tests économiques
- coût attendu calculé
- CE attendue calculée
- tier sizing proposé cohérent
- no-trade explicite si EV net insuffisante

## 21.4 Tests portefeuille
- refus si caps exposition / perte / BTC / cluster dépassés
- ranking possible contre un autre signal
- pas de bypass risk backbone

---

# 22. Conditions de sortie de Build-6

Build-6 est terminé si :

- le moteur A est complètement spécifié
- les signaux A sont auditables
- les coûts A sont visibles
- l’invalidation A est définie
- le moteur A respecte hard/soft/rank
- le moteur A ne contourne aucun guard portefeuille
- les logs et métriques de validation sont en place

---

# 23. Critères de refus de sortie

Refuser Build-6 si :

- le moteur A n’a pas de logique claire
- le score A est opaque
- le moteur A demande trop de confirmations
- la fréquence utile attendue est quasi nulle
- le moteur A ne peut pas expliquer un no-trade
- le moteur A ne produit pas de CE attendue
- le moteur A justifie du Tier 3 sans garde-fous explicites

---

# 24. Dérives globales Build-6 à ne pas faire

- reconstruire la V5.2 telle quelle
- faire du moteur A un moteur “élite” jamais activé
- absorber le breakout C dans A sans distinction
- lier la conviction à des features trop instables
- multiplier les confirmations jusqu’à tuer la fréquence utile
- permettre au moteur A de se croire au-dessus du portefeuille

---

# 25. Verdict final Build-6

Build-6 est la première vraie épreuve du projet :

> réussir à conserver une haute conviction sans retomber dans la stérilité.

Si Build-6 est bien fait :
- le système garde un moteur premium
- la V5.3 reste fidèle à son ambition
- le portefeuille a un moteur de référence de qualité

Si Build-6 est mal fait :
- le moteur A redeviendra trop rare
- le portefeuille perdra son meilleur levier qualitatif
- le reste de la V5.3 s’organisera autour d’un cœur déjà fragilisé

Donc :

> Build-6 doit être traité comme un **build bloquant de qualité stratégique**, pas comme une simple fiche moteur.

---

## Fin du document
