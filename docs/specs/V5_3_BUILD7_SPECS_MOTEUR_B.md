# V5.3 â€” BUILD-7 SPECS MODULES
## Moteur B Pack â€” Mean Reversion Intraday
### Specs dÃ©taillÃ©es du deuxiÃ¨me moteur live
### SeptiÃ¨me Ã©tape officielle du dÃ©veloppement
### Sans code â€” prod-safe

---

# 0. Objet du document

Ce document couvre **Build-7** du plan officiel V5.3.

Build-7 a une mission unique :

> rendre opÃ©rationnel le **Moteur B â€” Mean Reversion Intraday**, câ€™est-Ã -dire le moteur chargÃ© dâ€™augmenter la frÃ©quence utile et la rotation du capital, sans tomber dans le piÃ¨ge classique des systÃ¨mes crypto : beaucoup de trades, peu dâ€™edge net, et une destruction progressive par les coÃ»ts.

Le Build-7 couvre le pack logique du moteur B, pas lâ€™ensemble du portefeuille.  
Le moteur B doit Ãªtre spÃ©cifiÃ© de maniÃ¨re Ã  pouvoir Ãªtre :

- testÃ© en shadow
- comparÃ© proprement au moteur A
- contraint par le risk backbone
- pÃ©nalisÃ© par le scoring backbone
- exÃ©cutÃ© sous vraie discipline de coÃ»t
- dÃ©sactivÃ© rapidement sâ€™il devient un moteur â€œvolume pour volumeâ€

---

# 1. Principes Build-7

## 1.1 Objectif stratÃ©gique

Le moteur B nâ€™existe pas pour â€œfaire des tradesâ€.  
Il existe pour rÃ©soudre le problÃ¨me Ã©conomique central de la V5.2/V5.3 :

- faible frÃ©quence utile
- capital peu mobilisÃ©
- lenteur de convergence statistique
- faible rotation du capital en spot only

Le moteur B doit donc apporter :

- plus de frÃ©quence utile que A
- une durÃ©e moyenne plus courte
- une meilleure rotation du capital
- une CE correcte malgrÃ© un edge unitaire plus fin

## 1.2 Position dans lâ€™architecture

Le moteur B est :
- **autorisÃ© en Light**
- **autorisÃ© en Complete**
- **prioritÃ© P0**
- **moteur principal dâ€™augmentation de frÃ©quence utile**
- **moteur plus sensible aux coÃ»ts que A**

## 1.3 CritÃ¨re de rÃ©ussite

Build-7 est rÃ©ussi si :

- le moteur B produit des signaux mean reversion lisibles
- le moteur B reste compatible avec les coÃ»ts rÃ©els
- le moteur B nâ€™attaque pas des cassures structurelles Ã©videntes
- le moteur B produit une CE crÃ©dible
- le moteur B augmente rÃ©ellement la frÃ©quence utile
- le moteur B ne devient pas un moteur de bruit

## 1.4 CritÃ¨re dâ€™Ã©chec

Build-7 Ã©choue si :

- le moteur B traite toute baisse comme un â€œretour Ã  la moyenneâ€
- le moteur B sâ€™oppose trop souvent Ã  de vrais breakouts
- le moteur B a un edge brut positif mais un edge net nÃ©gatif
- le moteur B a des durÃ©es trop longues
- le moteur B gonfle la frÃ©quence brute sans amÃ©liorer la frÃ©quence utile
- le moteur B ne sait pas dire â€œno-tradeâ€ quand le coÃ»t tue le setup

---

# 2. Vocabulaire officiel du moteur B

## 2.1 ExcÃ¨s local
Ã‰cart local significatif entre le prix courant et une moyenne locale exploitable.

## 2.2 Mean reversion propre
Retour vers une moyenne locale dans un contexte qui ne suggÃ¨re pas une vraie rupture de structure.

## 2.3 Reversion toxique
Trade de mean reversion dÃ©clenchÃ© contre une cassure rÃ©elle, un rÃ©gime de stress ou un coÃ»t trop Ã©levÃ©.

## 2.4 Rotation du capital
CapacitÃ© du moteur Ã  produire des trades plus courts, plus frÃ©quents et Ã©conomiquement utiles.

---

# 3. Mission canonique du moteur B

Le moteur B doit capturer les situations oÃ¹ :

1. un excÃ¨s local existe rÃ©ellement  
2. la moyenne locale utilisÃ©e a un sens Ã©conomique  
3. le contexte ne suggÃ¨re pas une vraie continuation directionnelle hostile  
4. le coÃ»t attendu ne mange pas le petit edge  
5. la durÃ©e attendue reste courte ou raisonnable  
6. la CE attendue reste au-dessus du minimum requis  

Le moteur B est un moteur de **frÃ©quence utile**, pas un moteur de prestige.

---

# 4. PÃ©rimÃ¨tre du Build-7

## 4.1 Inclus

- dÃ©finition du moteur B
- inputs requis
- outputs requis
- logique dâ€™excÃ¨s local
- logique de rejet des faux reversions
- contraintes coÃ»t
- contraintes de durÃ©e
- contraintes de sizing
- logs spÃ©cifiques
- mÃ©triques de validation
- conditions de dÃ©sactivation

## 4.2 Exclus

- logique dÃ©taillÃ©e du moteur A
- moteur C
- moteur D
- allocation finale multi-moteurs globale
- heuristiques discretionary de trader

---

# 5. Positionnement du moteur B dans les profils

## 5.1 Light
- autorisÃ©
- prioritaire
- activable sur 6 paires max
- principal moteur de frÃ©quence utile

## 5.2 Complete
- autorisÃ©
- reste moteur structurel de rotation
- comparÃ© Ã  C et D pour Ã©viter doublons inutiles
- toujours bornÃ© par les caps portefeuille

---

# 6. Paires autorisÃ©es

## 6.1 Profil Light
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- ADA/USDT
- LINK/USDT

## 6.2 Profil Complete
- classes A et B validÃ©es
- classes C seulement si coÃ»t rÃ©el et santÃ© paire restent acceptables
- DOGE/TRX/TON/DOT seulement aprÃ¨s validation explicite, pas par dÃ©faut

## 6.3 RÃ¨gle de prudence

Le moteur B ne doit pas Ãªtre activÃ© sur une paire simplement parce quâ€™elle â€œbouge beaucoupâ€.  
Il doit Ãªtre activÃ© lÃ  oÃ¹ :
- la moyenne locale a du sens
- les coÃ»ts sont tolÃ©rables
- la paire nâ€™est pas structurellement trop sale pour des reversions courtes

---

# 7. RÃ©gimes compatibles

## 7.1 Favorables
- range propre
- excÃ¨s local sur structure non cassÃ©e
- marchÃ© relativement stable
- volatilitÃ© exploitable mais pas chaotique
- absence de continuation forte en cours

## 7.2 DÃ©favorables
- breakout violent
- trend directionnel explosif
- stress de marchÃ©
- coÃ»t Ã©levÃ©
- santÃ© paire dÃ©gradÃ©e
- flux trÃ¨s dÃ©sordonnÃ©

## 7.3 RÃ¨gle

Le moteur B doit Ãªtre sÃ©vÃ¨rement pÃ©nalisÃ©, voire bloquÃ©, dans les environnements oÃ¹ la probabilitÃ© de continuation dÃ©passe la probabilitÃ© de retour Ã  moyenne.

---

# 8. Inputs minimaux obligatoires

## 8.1 Inputs structurels
- prix courant
- moyenne locale
- dispersion locale
- mesure dâ€™Ã©cart / excÃ¨s
- Ã©tat local de structure (range vs cassure)

## 8.2 Inputs contextuels
- rÃ©gime courant
- pair health
- fraÃ®cheur data
- cohÃ©rence flux
- absence de contradiction structurelle majeure

## 8.3 Inputs Ã©conomiques
- coÃ»t attendu
- break-even prudent
- horizon de dÃ©tention attendu
- CE attendue
- taille candidate
- budget corrÃ©lation libre

## 8.4 Inputs optionnels encadrÃ©s
- confirmation microstructure lÃ©gÃ¨re
- retour vers microprice / zone locale
- Ã©tat du flux rÃ©el

---

# 9. Outputs obligatoires

Le moteur B doit produire :

- `SignalCandidate` moteur B
- score brut B
- composantes du score B
- z-score ou Ã©quivalent dâ€™excÃ¨s
- coÃ»t attendu
- durÃ©e attendue
- CE attendue
- invalidation logique
- suggestion de tier sizing
- raisons de non-Ã©mission

---

# 10. Architecture interne recommandÃ©e du moteur B

## 10.1 Sous-composants

### 10.1.1 local_mean_estimator_B
Rôle :
- estimer la moyenne locale pertinente
- fournir aussi la dispersion locale exploitable et le z-score associé

### 10.1.2 excess_detector_B
Rôle :
- détecter un excès exploitable

### 10.1.3 anti_breakout_filter_B
Rôle :
- réduire ou rejeter les reversions contre vraie cassure

### 10.1.4 cost_feasibility_B
Rôle :
- rejeter les setups où le coût tue l’edge

### 10.1.5 conviction_builder_B
Rôle :
- construire la conviction du moteur B à partir de l’excès, de la structure, du contexte et de la préférence de coût
- plafonner le moteur B à une conviction compatible avec une logique spot halal prudente

### 10.1.6 invalidation_mapper_B
Rôle :
- définir la cible de reversion, le stop de confirmation breakout et l’horizon maximal de détention

### 10.1.7 signal_reporter_B
Rôle :
- produire une sortie complète et audit-able

---
# 11. Logique fondamentale du moteur B

## 11.1 Principe

Le moteur B ne doit pas reposer sur lâ€™idÃ©e naÃ¯ve :
â€œle prix sâ€™est Ã©loignÃ©, donc il va revenirâ€.

Il doit reposer sur :
- une moyenne locale pertinente
- une dispersion locale exploitable
- un contexte compatible
- une absence de preuve forte de continuation hostile

## 11.2 Variables mathÃ©matiques utiles

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

Condition type dâ€™entrÃ©e :
\[
|z_t| > z^\star
\]

EspÃ©rance conditionnelle :
\[
\mu_{B,j,s} = \mathbb{E}[r \mid moteur=B, paire=j, rÃ©gime=s]
\]

Variance conditionnelle :
\[
\sigma^2_{B,j,s} = \mathbb{V}[r \mid moteur=B, paire=j, rÃ©gime=s]
\]

Capital efficiency attendue :
\[
CE_{B,j,s} = \frac{\mathbb{E}[PnL \mid B,j,s]}{x \cdot h}
\]

## 11.3 Condition Ã©conomique minimale

\[
\mathbb{E}[g_i \mid B,j,s] > \mathbb{E}[c_i \mid B,j,s] + \delta_{safe,B}
\]

avec \(\delta_{safe,B}\) gÃ©nÃ©ralement plus exigeant que pour A, car lâ€™edge de B est plus fin.

---

# 12. Logique dâ€™excÃ¨s local

## 12.1 RÃ´le

Identifier un Ã©cart suffisamment fort pour justifier une probabilitÃ© crÃ©dible de retour.

## 12.2 Variables recommandÃ©es
- z-score
- distance absolue Ã  moyenne locale
- vitesse dâ€™Ã©loignement
- contexte de compression / Ã©largissement rÃ©cent
- structure range ou non

## 12.3 DÃ©rives Ã  Ã©viter
- excÃ¨s mesurÃ© sur fenÃªtre arbitraire non stable
- mÃªme fenÃªtre pour toutes les paires / rÃ©gimes sans justification
- dispersion locale trop rÃ©active ou trop lente

---

# 13. Anti-breakout filter du moteur B

## 13.1 RÃ´le

EmpÃªcher le moteur B de vendre/acheter contre une vraie continuation directionnelle.

## 13.2 Composantes recommandÃ©es
- regime dÃ©favorable au mean reversion
- volume anormalement fort dans le sens du move
- confirmation structurelle de cassure
- microstructure orientÃ©e continuation
- coÃ»t qui sâ€™Ã©lÃ¨ve avec lâ€™accÃ©lÃ©ration

## 13.3 Formulation conceptuelle

Le moteur B doit Ãªtre pÃ©nalisÃ© ou refusÃ© si :

\[
\mathbb{P}(\text{continuation hostile} \mid contexte) > \mathbb{P}(\text{reversion exploitable} \mid contexte)
\]

## 13.4 DÃ©rive critique Ã  Ã©viter

Le moteur B ne doit jamais devenir un moteur qui â€œattrape des couteaux qui tombentâ€ ou â€œshorte chaque spikeâ€.

---

# 14. Score brut B

## 14.1 Construction

Le score brut B doit Ãªtre composÃ© de blocs interprÃ©tables :

\[
S_B^{raw} = S_B^{excess} + S_B^{structure} + S_B^{context} + S_B^{cost\_preference}
\]

### Blocs recommandÃ©s

#### ExcÃ¨s
- amplitude de lâ€™Ã©cart
- qualitÃ© statistique de lâ€™Ã©cart

#### Structure
- compatibilitÃ© range / non-cassure
- absence de confirmation dâ€™une rupture forte

#### Contexte
- rÃ©gime compatible
- santÃ© paire
- qualitÃ© data

#### PrÃ©fÃ©rence de coÃ»t
- setups plus â€œpropresâ€ Ã  exÃ©cuter

## 14.2 Interdits
- score pur basÃ© sur z-score seul
- score opaque
- intÃ©grer les hard blockers dans le score brut

---

# 15. PÃ©nalitÃ©s spÃ©cifiques au moteur B

Le moteur B peut Ãªtre pÃ©nalisÃ© pour :
- coÃ»t un peu Ã©levÃ© mais pas fatal
- rÃ©gime ambigu
- qualitÃ© moyenne de la structure locale
- flux un peu toxique
- horizon de retour trop long

## 15.1 Formules utiles

PÃ©nalitÃ© additive :
\[
Pen_{B,i} = \sum_{\ell=1}^{L} pen_{B,i,\ell}
\]

Score pÃ©nalisÃ© :
\[
S_{B,i} = S_{B,i}^{raw} - Pen_{B,i}
\]

Multiplicateur de taille :
\[
m_{B,i} = \prod_{\ell=1}^{L} m_{B,i,\ell}
\]

## 15.2 RÃ¨gle critique

Le moteur B est trÃ¨s sensible aux pÃ©nalitÃ©s de coÃ»t et de durÃ©e.  
Mais ces pÃ©nalitÃ©s ne doivent pas reconstituer un veto cachÃ© sans trace.

---

# 16. Hard blockers compatibles

Le moteur B nâ€™a pas de hard blockers propriÃ©taires.  
Il utilise les hard blockers canoniques :

- stale hard
- pair suspended
- cost impossible
- risk budget breach
- beta BTC breach
- cluster breach
- reconciliation critical
- infra critical

Le moteur B peut en revanche produire plus souvent des **no-trade Ã©conomiques** que A.

---

# 17. Contraintes de coÃ»t

## 17.1 Principe

Le moteur B est plus fragile au coÃ»t que le moteur A.

Un setup B doit donc Ãªtre traitÃ© comme **plus exigeant Ã©conomiquement**, mÃªme sâ€™il semble plus frÃ©quent.

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

## 17.3 DÃ©rives Ã  Ã©viter
- penser â€œpetit move = petit coÃ»tâ€
- ignorer que les petits edges meurent les premiers
- regarder seulement le coÃ»t moyen et non le p90

---

# 18. Contraintes de durÃ©e

## 18.1 Principe

Le moteur B doit rester plutÃ´t court en dÃ©tention.

Sâ€™il devient long, il perd une grande partie de son intÃ©rÃªt Ã©conomique.

## 18.2 Variables utiles

DurÃ©e attendue :
\[
h_{B,i}^{exp}
\]

Capital efficiency attendue :
\[
CE_{B,i}^{exp} = \frac{\mathbb{E}[PnL_i \mid B]}{x_i \cdot h_{B,i}^{exp}}
\]

## 18.3 RÃ¨gle

Le moteur B doit Ãªtre pÃ©nalisÃ© si la durÃ©e attendue devient trop longue.

## 18.4 DÃ©rives Ã  Ã©viter
- transformer un trade B en â€œinvestissement de patienceâ€
- laisser la logique B dÃ©river vers une pseudo re-entry lente

---

# 19. Contraintes de sizing

## 19.1 Principe

Le moteur B nâ€™est pas naturellement un moteur Tier 3.

Il doit en gÃ©nÃ©ral recevoir :
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
- Tier 3 par dÃ©faut sur B
- concentration de capital sur une mean reversion simplement â€œjolieâ€
- sizing agressif parce que frÃ©quence plus Ã©levÃ©e

---

# 20. Invalidation et sortie logique

## 20.1 Principe

Le moteur B doit produire une invalidation logique claire :
- retour vers moyenne locale invalidÃ©
- cassure confirmÃ©e contre le trade
- durÃ©e qui sâ€™allonge trop
- contexte qui se transforme en continuation hostile

## 20.2 Contenu minimal
- moyenne cible ou zone cible
- condition dâ€™Ã©chec de reversion
- horizon attendu
- condition de dÃ©gradation de CE

## 20.3 DÃ©rive Ã  Ã©viter
- laisser vivre indÃ©finiment un trade B â€œparce quâ€™il finira peut-Ãªtre par revenirâ€

---

# 21. Logs obligatoires du moteur B

Le moteur B doit logger, au minimum :

- paire
- rÃ©gime
- moyenne locale
- dispersion locale
- z-score
- score brut
- score pÃ©nalisÃ©
- coÃ»t attendu
- durÃ©e attendue
- CE attendue
- invalidation proposÃ©e
- tier proposÃ©
- raisons de non-Ã©mission
- raisons de rejet par hard block
- raisons de rejet par ranking

---

# 22. MÃ©triques de validation du moteur B

## 22.1 MÃ©triques principales
- frÃ©quence utile B
- rendement net B
- coÃ»t moyen B
- coÃ»t p90 B
- CE B
- Sharpe par trade B
- durÃ©e moyenne B
- drawdown B
- taux de stÃ©rilisation B

## 22.2 MÃ©triques secondaires
- corrÃ©lation B / A
- part des trades B stoppÃ©s par cassure
- part de no-trade due au coÃ»t
- part de no-trade due au rÃ©gime dÃ©favorable
- temps moyen de retour

## 22.3 Formules utiles

FrÃ©quence utile B :
\[
F_{utile,B} = \frac{\text{trades B Ã  expectancy utile}}{\text{temps}}
\]

CE B :
\[
CE_B = \frac{\sum_{i \in B} PnL_i}{\sum_{i \in B} x_i h_i}
\]

Sharpe B :
\[
Sh_B = \frac{\mu_B}{\sigma_B}
\]

StÃ©rilisation B :
\[
SterilRate_B = \frac{\sum_{i \in B}\mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_{i \in B}A_i}
\]

Taux dâ€™Ã©chec contre cassure :
\[
BreakFailRate_B = \frac{N_{B,\text{stop par breakout}}}{N_{B,\text{trades}}}
\]

---

# 23. Tests obligatoires Build-7

## 23.1 Tests de structure
- signal B sur excÃ¨s local cohÃ©rent
- pas de signal B en trend explosif Ã©vident
- pas de signal B si coÃ»t impossible
- invalidation prÃ©sente

## 23.2 Tests de cohÃ©rence
- mÃªme inputs â†’ mÃªme sortie B
- z-score versionnÃ©
- composantes de score visibles
- pÃ©nalitÃ©s visibles
- hard blocks sÃ©parÃ©s

## 23.3 Tests Ã©conomiques
- coÃ»t attendu calculÃ©
- durÃ©e attendue calculÃ©e
- CE attendue calculÃ©e
- no-trade explicite si EV net insuffisante

## 23.4 Tests portefeuille
- refus si caps portefeuille dÃ©passÃ©s
- ranking possible contre A
- pas de bypass risk backbone

---

# 24. Conditions de sortie de Build-7

Build-7 est terminÃ© si :

- le moteur B est complÃ¨tement spÃ©cifiÃ©
- les signaux B sont auditables
- le moteur B distingue bien reversion propre et cassure hostile
- les coÃ»ts et la durÃ©e attendus sont visibles
- la CE attendue est calculÃ©e
- le moteur B respecte hard/soft/rank
- le moteur B ne contourne aucun guard portefeuille

---

# 25. CritÃ¨res de refus de sortie

Refuser Build-7 si :

- le moteur B ressemble Ã  une simple stratÃ©gie â€œacheter les baissesâ€
- le moteur B ignore le risque de continuation hostile
- le moteur B nâ€™a pas de no-trade Ã©conomique clair
- le moteur B ne produit pas de durÃ©e attendue
- le moteur B nâ€™a pas de CE attendue
- le moteur B rÃ©clame un sizing trop agressif
- le moteur B ne peut pas expliquer ses rejets

---

# 26. DÃ©rives globales Build-7 Ã  ne pas faire

- utiliser B pour gonfler artificiellement la frÃ©quence
- croire quâ€™un z-score Ã©levÃ© suffit
- oublier que le coÃ»t tue plus vite B que A
- laisser B dÃ©river en holding long
- transformer B en moteur anti-trend systÃ©matique
- sous-estimer lâ€™importance de lâ€™anti-breakout filter

---

# 27. Verdict final Build-7

Build-7 est la seconde Ã©preuve stratÃ©gique du projet :

> rÃ©ussir Ã  augmenter la frÃ©quence utile sans dÃ©grader lâ€™Ã©conomie du systÃ¨me.

Si Build-7 est bien fait :
- la V5.3 Light gagne un moteur rÃ©ellement utile
- la convergence statistique sâ€™amÃ©liore
- la rotation du capital devient plus crÃ©dible

Si Build-7 est mal fait :
- la frÃ©quence brute monte
- la frÃ©quence utile ne suit pas
- le coÃ»t dÃ©truit lâ€™edge
- le portefeuille devient bruyant et fragile

Donc :

> Build-7 doit Ãªtre traitÃ© comme un **build bloquant de productivitÃ© Ã©conomique**, pas comme une simple stratÃ©gie secondaire.

---

## Fin du document

