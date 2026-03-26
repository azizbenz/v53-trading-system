# V5.3 — BUILD-7 SPECS MODULES
## Moteur B Pack — Mean Reversion Intraday
### Specs détaillées du deuxième moteur live
### Septième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-7** du plan officiel V5.3.

Build-7 a une mission unique :

> rendre opérationnel le **Moteur B — Mean Reversion Intraday**, c’est-à-dire le moteur chargé d’augmenter la fréquence utile et la rotation du capital, sans tomber dans le piège classique des systèmes crypto : beaucoup de trades, peu d’edge net, et une destruction progressive par les coûts.

Le Build-7 couvre le pack logique du moteur B, pas l’ensemble du portefeuille.  
Le moteur B doit être spécifié de manière à pouvoir être :

- testé en shadow
- comparé proprement au moteur A
- contraint par le risk backbone
- pénalisé par le scoring backbone
- exécuté sous vraie discipline de coût
- désactivé rapidement s’il devient un moteur “volume pour volume”

---

# 1. Principes Build-7

## 1.1 Objectif stratégique

Le moteur B n’existe pas pour “faire des trades”.  
Il existe pour résoudre le problème économique central de la V5.2/V5.3 :

- faible fréquence utile
- capital peu mobilisé
- lenteur de convergence statistique
- faible rotation du capital en spot only

Le moteur B doit donc apporter :

- plus de fréquence utile que A
- une durée moyenne plus courte
- une meilleure rotation du capital
- une CE correcte malgré un edge unitaire plus fin

## 1.2 Position dans l’architecture

Le moteur B est :
- **autorisé en Light**
- **autorisé en Complete**
- **priorité P0**
- **moteur principal d’augmentation de fréquence utile**
- **moteur plus sensible aux coûts que A**

## 1.3 Critère de réussite

Build-7 est réussi si :

- le moteur B produit des signaux mean reversion lisibles
- le moteur B reste compatible avec les coûts réels
- le moteur B n’attaque pas des cassures structurelles évidentes
- le moteur B produit une CE crédible
- le moteur B augmente réellement la fréquence utile
- le moteur B ne devient pas un moteur de bruit

## 1.4 Critère d’échec

Build-7 échoue si :

- le moteur B traite toute baisse comme un “retour à la moyenne”
- le moteur B s’oppose trop souvent à de vrais breakouts
- le moteur B a un edge brut positif mais un edge net négatif
- le moteur B a des durées trop longues
- le moteur B gonfle la fréquence brute sans améliorer la fréquence utile
- le moteur B ne sait pas dire “no-trade” quand le coût tue le setup

---

# 2. Vocabulaire officiel du moteur B

## 2.1 Excès local
Écart local significatif entre le prix courant et une moyenne locale exploitable.

## 2.2 Mean reversion propre
Retour vers une moyenne locale dans un contexte qui ne suggère pas une vraie rupture de structure.

## 2.3 Reversion toxique
Trade de mean reversion déclenché contre une cassure réelle, un régime de stress ou un coût trop élevé.

## 2.4 Rotation du capital
Capacité du moteur à produire des trades plus courts, plus fréquents et économiquement utiles.

---

# 3. Mission canonique du moteur B

Le moteur B doit capturer les situations où :

1. un excès local existe réellement  
2. la moyenne locale utilisée a un sens économique  
3. le contexte ne suggère pas une vraie continuation directionnelle hostile  
4. le coût attendu ne mange pas le petit edge  
5. la durée attendue reste courte ou raisonnable  
6. la CE attendue reste au-dessus du minimum requis  

Le moteur B est un moteur de **fréquence utile**, pas un moteur de prestige.

---

# 4. Périmètre du Build-7

## 4.1 Inclus

- définition du moteur B
- inputs requis
- outputs requis
- logique d’excès local
- logique de rejet des faux reversions
- contraintes coût
- contraintes de durée
- contraintes de sizing
- logs spécifiques
- métriques de validation
- conditions de désactivation

## 4.2 Exclus

- logique détaillée du moteur A
- moteur C
- moteur D
- allocation finale multi-moteurs globale
- heuristiques discretionary de trader

---

# 5. Positionnement du moteur B dans les profils

## 5.1 Light
- autorisé
- prioritaire
- activable sur 6 paires max
- principal moteur de fréquence utile

## 5.2 Complete
- autorisé
- reste moteur structurel de rotation
- comparé à C et D pour éviter doublons inutiles
- toujours borné par les caps portefeuille

---

# 6. Paires autorisées

## 6.1 Profil Light
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- ADA/USDT
- LINK/USDT

## 6.2 Profil Complete
- classes A et B validées
- classes C seulement si coût réel et santé paire restent acceptables
- DOGE/TRX/TON/DOT seulement après validation explicite, pas par défaut

## 6.3 Règle de prudence

Le moteur B ne doit pas être activé sur une paire simplement parce qu’elle “bouge beaucoup”.  
Il doit être activé là où :
- la moyenne locale a du sens
- les coûts sont tolérables
- la paire n’est pas structurellement trop sale pour des reversions courtes

---

# 7. Régimes compatibles

## 7.1 Favorables
- range propre
- excès local sur structure non cassée
- marché relativement stable
- volatilité exploitable mais pas chaotique
- absence de continuation forte en cours

## 7.2 Défavorables
- breakout violent
- trend directionnel explosif
- stress de marché
- coût élevé
- santé paire dégradée
- flux très désordonné

## 7.3 Règle

Le moteur B doit être sévèrement pénalisé, voire bloqué, dans les environnements où la probabilité de continuation dépasse la probabilité de retour à moyenne.

---

# 8. Inputs minimaux obligatoires

## 8.1 Inputs structurels
- prix courant
- moyenne locale
- dispersion locale
- mesure d’écart / excès
- état local de structure (range vs cassure)

## 8.2 Inputs contextuels
- régime courant
- pair health
- fraîcheur data
- cohérence flux
- absence de contradiction structurelle majeure

## 8.3 Inputs économiques
- coût attendu
- break-even prudent
- horizon de détention attendu
- CE attendue
- taille candidate
- budget corrélation libre

## 8.4 Inputs optionnels encadrés
- confirmation microstructure légère
- retour vers microprice / zone locale
- état du flux réel

---

# 9. Outputs obligatoires

Le moteur B doit produire :

- `SignalCandidate` moteur B
- score brut B
- composantes du score B
- z-score ou équivalent d’excès
- coût attendu
- durée attendue
- CE attendue
- invalidation logique
- suggestion de tier sizing
- raisons de non-émission

---

# 10. Architecture interne recommandée du moteur B

## 10.1 Sous-composants

### 10.1.1 local_mean_estimator_B
Rôle :
- estimer la moyenne locale pertinente

### 10.1.2 local_dispersion_estimator_B
Rôle :
- estimer la dispersion locale utile

### 10.1.3 excess_detector_B
Rôle :
- détecter un excès exploitable

### 10.1.4 anti_breakout_filter_B
Rôle :
- réduire ou rejeter les reversions contre vraie cassure

### 10.1.5 cost_feasibility_B
Rôle :
- rejeter les setups où le coût tue l’edge

### 10.1.6 horizon_mapper_B
Rôle :
- définir l’horizon attendu de retour

### 10.1.7 signal_reporter_B
Rôle :
- produire une sortie complète et audit-able

---

# 11. Logique fondamentale du moteur B

## 11.1 Principe

Le moteur B ne doit pas reposer sur l’idée naïve :
“le prix s’est éloigné, donc il va revenir”.

Il doit reposer sur :
- une moyenne locale pertinente
- une dispersion locale exploitable
- un contexte compatible
- une absence de preuve forte de continuation hostile

## 11.2 Variables mathématiques utiles

Moyenne locale :
\[
\mu_t^{loc}
\]

Dispersion locale :
\[
\sigma_t^{loc}
\]

Z-score local :
\[
z_t = \frac{p_t - \mu_t^{loc}}{\sigma_t^{loc}}
\]

Condition type d’entrée :
\[
|z_t| > z^\star
\]

Espérance conditionnelle :
\[
\mu_{B,j,s} = \mathbb{E}[r \mid moteur=B, paire=j, régime=s]
\]

Variance conditionnelle :
\[
\sigma^2_{B,j,s} = \mathbb{V}[r \mid moteur=B, paire=j, régime=s]
\]

Capital efficiency attendue :
\[
CE_{B,j,s} = \frac{\mathbb{E}[PnL \mid B,j,s]}{x \cdot h}
\]

## 11.3 Condition économique minimale

\[
\mathbb{E}[g_i \mid B,j,s] > \mathbb{E}[c_i \mid B,j,s] + \delta_{safe,B}
\]

avec \(\delta_{safe,B}\) généralement plus exigeant que pour A, car l’edge de B est plus fin.

---

# 12. Logique d’excès local

## 12.1 Rôle

Identifier un écart suffisamment fort pour justifier une probabilité crédible de retour.

## 12.2 Variables recommandées
- z-score
- distance absolue à moyenne locale
- vitesse d’éloignement
- contexte de compression / élargissement récent
- structure range ou non

## 12.3 Dérives à éviter
- excès mesuré sur fenêtre arbitraire non stable
- même fenêtre pour toutes les paires / régimes sans justification
- dispersion locale trop réactive ou trop lente

---

# 13. Anti-breakout filter du moteur B

## 13.1 Rôle

Empêcher le moteur B de vendre/acheter contre une vraie continuation directionnelle.

## 13.2 Composantes recommandées
- regime défavorable au mean reversion
- volume anormalement fort dans le sens du move
- confirmation structurelle de cassure
- microstructure orientée continuation
- coût qui s’élève avec l’accélération

## 13.3 Formulation conceptuelle

Le moteur B doit être pénalisé ou refusé si :

\[
\mathbb{P}(\text{continuation hostile} \mid contexte) > \mathbb{P}(\text{reversion exploitable} \mid contexte)
\]

## 13.4 Dérive critique à éviter

Le moteur B ne doit jamais devenir un moteur qui “attrape des couteaux qui tombent” ou “shorte chaque spike”.

---

# 14. Score brut B

## 14.1 Construction

Le score brut B doit être composé de blocs interprétables :

\[
S_B^{raw} = S_B^{excess} + S_B^{structure} + S_B^{context} + S_B^{cost\_preference}
\]

### Blocs recommandés

#### Excès
- amplitude de l’écart
- qualité statistique de l’écart

#### Structure
- compatibilité range / non-cassure
- absence de confirmation d’une rupture forte

#### Contexte
- régime compatible
- santé paire
- qualité data

#### Préférence de coût
- setups plus “propres” à exécuter

## 14.2 Interdits
- score pur basé sur z-score seul
- score opaque
- intégrer les hard blockers dans le score brut

---

# 15. Pénalités spécifiques au moteur B

Le moteur B peut être pénalisé pour :
- coût un peu élevé mais pas fatal
- régime ambigu
- qualité moyenne de la structure locale
- flux un peu toxique
- horizon de retour trop long

## 15.1 Formules utiles

Pénalité additive :
\[
Pen_{B,i} = \sum_{\ell=1}^{L} pen_{B,i,\ell}
\]

Score pénalisé :
\[
S_{B,i} = S_{B,i}^{raw} - Pen_{B,i}
\]

Multiplicateur de taille :
\[
m_{B,i} = \prod_{\ell=1}^{L} m_{B,i,\ell}
\]

## 15.2 Règle critique

Le moteur B est très sensible aux pénalités de coût et de durée.  
Mais ces pénalités ne doivent pas reconstituer un veto caché sans trace.

---

# 16. Hard blockers compatibles

Le moteur B n’a pas de hard blockers propriétaires.  
Il utilise les hard blockers canoniques :

- stale hard
- pair suspended
- cost impossible
- risk budget breach
- beta BTC breach
- cluster breach
- reconciliation critical
- infra critical

Le moteur B peut en revanche produire plus souvent des **no-trade économiques** que A.

---

# 17. Contraintes de coût

## 17.1 Principe

Le moteur B est plus fragile au coût que le moteur A.

Un setup B doit donc être traité comme **plus exigeant économiquement**, même s’il semble plus fréquent.

## 17.2 Formules utiles

Break-even prudent :

\[
BE_{B,j} = \mathbb{E}[c \mid moteur=B, paire=j]
\]

Valeur nette attendue :

\[
EV_{B,i}^{net} = x_i \cdot (\mathbb{E}[g_i \mid B] - \mathbb{E}[c_i \mid B])
\]

Condition minimale :

\[
EV_{B,i}^{net} > \epsilon
\]

## 17.3 Dérives à éviter
- penser “petit move = petit coût”
- ignorer que les petits edges meurent les premiers
- regarder seulement le coût moyen et non le p90

---

# 18. Contraintes de durée

## 18.1 Principe

Le moteur B doit rester plutôt court en détention.

S’il devient long, il perd une grande partie de son intérêt économique.

## 18.2 Variables utiles

Durée attendue :
\[
h_{B,i}^{exp}
\]

Capital efficiency attendue :
\[
CE_{B,i}^{exp} = \frac{\mathbb{E}[PnL_i \mid B]}{x_i \cdot h_{B,i}^{exp}}
\]

## 18.3 Règle

Le moteur B doit être pénalisé si la durée attendue devient trop longue.

## 18.4 Dérives à éviter
- transformer un trade B en “investissement de patience”
- laisser la logique B dériver vers une pseudo re-entry lente

---

# 19. Contraintes de sizing

## 19.1 Principe

Le moteur B n’est pas naturellement un moteur Tier 3.

Il doit en général recevoir :
- Tier 1
- parfois Tier 2
- presque jamais Tier 3

## 19.2 Formules utiles

Taille candidate :
\[
x_i = x_{base} \cdot m_i \cdot \psi(S_i)
\]

Cap par position :
\[
x_i \le x_{max,pos}
\]

## 19.3 Interdits
- Tier 3 par défaut sur B
- concentration de capital sur une mean reversion simplement “jolie”
- sizing agressif parce que fréquence plus élevée

---

# 20. Invalidation et sortie logique

## 20.1 Principe

Le moteur B doit produire une invalidation logique claire :
- retour vers moyenne locale invalidé
- cassure confirmée contre le trade
- durée qui s’allonge trop
- contexte qui se transforme en continuation hostile

## 20.2 Contenu minimal
- moyenne cible ou zone cible
- condition d’échec de reversion
- horizon attendu
- condition de dégradation de CE

## 20.3 Dérive à éviter
- laisser vivre indéfiniment un trade B “parce qu’il finira peut-être par revenir”

---

# 21. Logs obligatoires du moteur B

Le moteur B doit logger, au minimum :

- paire
- régime
- moyenne locale
- dispersion locale
- z-score
- score brut
- score pénalisé
- coût attendu
- durée attendue
- CE attendue
- invalidation proposée
- tier proposé
- raisons de non-émission
- raisons de rejet par hard block
- raisons de rejet par ranking

---

# 22. Métriques de validation du moteur B

## 22.1 Métriques principales
- fréquence utile B
- rendement net B
- coût moyen B
- coût p90 B
- CE B
- Sharpe par trade B
- durée moyenne B
- drawdown B
- taux de stérilisation B

## 22.2 Métriques secondaires
- corrélation B / A
- part des trades B stoppés par cassure
- part de no-trade due au coût
- part de no-trade due au régime défavorable
- temps moyen de retour

## 22.3 Formules utiles

Fréquence utile B :
\[
F_{utile,B} = \frac{\text{trades B à expectancy utile}}{\text{temps}}
\]

CE B :
\[
CE_B = \frac{\sum_{i \in B} PnL_i}{\sum_{i \in B} x_i h_i}
\]

Sharpe B :
\[
Sh_B = \frac{\mu_B}{\sigma_B}
\]

Stérilisation B :
\[
SterilRate_B = \frac{\sum_{i \in B}\mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_{i \in B}A_i}
\]

Taux d’échec contre cassure :
\[
BreakFailRate_B = \frac{N_{B,\text{stop par breakout}}}{N_{B,\text{trades}}}
\]

---

# 23. Tests obligatoires Build-7

## 23.1 Tests de structure
- signal B sur excès local cohérent
- pas de signal B en trend explosif évident
- pas de signal B si coût impossible
- invalidation présente

## 23.2 Tests de cohérence
- même inputs → même sortie B
- z-score versionné
- composantes de score visibles
- pénalités visibles
- hard blocks séparés

## 23.3 Tests économiques
- coût attendu calculé
- durée attendue calculée
- CE attendue calculée
- no-trade explicite si EV net insuffisante

## 23.4 Tests portefeuille
- refus si caps portefeuille dépassés
- ranking possible contre A
- pas de bypass risk backbone

---

# 24. Conditions de sortie de Build-7

Build-7 est terminé si :

- le moteur B est complètement spécifié
- les signaux B sont auditables
- le moteur B distingue bien reversion propre et cassure hostile
- les coûts et la durée attendus sont visibles
- la CE attendue est calculée
- le moteur B respecte hard/soft/rank
- le moteur B ne contourne aucun guard portefeuille

---

# 25. Critères de refus de sortie

Refuser Build-7 si :

- le moteur B ressemble à une simple stratégie “acheter les baisses”
- le moteur B ignore le risque de continuation hostile
- le moteur B n’a pas de no-trade économique clair
- le moteur B ne produit pas de durée attendue
- le moteur B n’a pas de CE attendue
- le moteur B réclame un sizing trop agressif
- le moteur B ne peut pas expliquer ses rejets

---

# 26. Dérives globales Build-7 à ne pas faire

- utiliser B pour gonfler artificiellement la fréquence
- croire qu’un z-score élevé suffit
- oublier que le coût tue plus vite B que A
- laisser B dériver en holding long
- transformer B en moteur anti-trend systématique
- sous-estimer l’importance de l’anti-breakout filter

---

# 27. Verdict final Build-7

Build-7 est la seconde épreuve stratégique du projet :

> réussir à augmenter la fréquence utile sans dégrader l’économie du système.

Si Build-7 est bien fait :
- la V5.3 Light gagne un moteur réellement utile
- la convergence statistique s’améliore
- la rotation du capital devient plus crédible

Si Build-7 est mal fait :
- la fréquence brute monte
- la fréquence utile ne suit pas
- le coût détruit l’edge
- le portefeuille devient bruyant et fragile

Donc :

> Build-7 doit être traité comme un **build bloquant de productivité économique**, pas comme une simple stratégie secondaire.

---

## Fin du document
