# V5.3 — TABLE DÉTAILLÉE DES MOTEURS
## Spécification développeur / quant / risk
### Complément canonique au `V5_3_MASTER_FINAL_CANONICAL.md`
### Sans code — prod-safe

---

# 0. Objet du document

Ce document définit **les 4 moteurs canoniques** de la V5.3 :

- Moteur A — Premium Trend / Expansion
- Moteur B — Mean Reversion Intraday
- Moteur C — Breakout Continuation
- Moteur D — Re-entry / Second Chance Logic

Pour chaque moteur, il précise :

- rôle exact
- logique économique
- profil d’activation
- paires autorisées
- régimes compatibles
- inputs minimaux
- outputs
- scoring minimal
- contraintes de coût
- risques structurels
- conditions de désactivation
- logs obligatoires
- métriques de validation
- dérives à éviter
- verdict d’implémentation

---

# 1. Règles globales

## 1.1 Aucun moteur n’a le droit d’exister sans :

- estimation de coût réel
- lecture du budget de corrélation
- scoring hard / soft / rank
- budget risque
- tracking de capital efficiency
- logs de décision suffisants

## 1.2 Aucun moteur n’est validé par :

- un win rate isolé
- un backtest propre sur papier
- un bon mois isolé
- une moyenne brute sans coûts

## 1.3 Un moteur n’est conservé que s’il apporte :

- soit de l’alpha net
- soit une vraie diversification d’edge
- soit une meilleure capital efficiency
- idéalement les trois

---

# 2. Tableau maître des moteurs

| Moteur | Profil Light | Profil Complete | Priorité | Fréquence attendue | Qualité de signal | Risque majeur |
|---|---:|---:|---:|---|---|---|
| A — Premium Trend | oui | oui | P0 | faible à modérée | très élevée | sur-rareté / sur-filtrage |
| B — Mean Reversion | oui | oui | P0 | modérée | moyenne à élevée | mean reversion contre cassure réelle |
| C — Breakout | non | oui | P1 | modérée | moyenne | faux breakout / duplication A |
| D — Re-entry | non | oui | P1 | faible à modérée | dépend du contexte | doublon de A / surconcentration |

---

# 3. MOTEUR A — PREMIUM TREND / EXPANSION

## 3.1 Mission

Le moteur A est le **cœur héritier de la V5.2**.

Il doit conserver la vocation haute conviction du système, mais sans rester stérile économiquement.

Son rôle est de prendre les setups :

- les plus propres
- les plus cohérents avec le contexte
- les plus défendables après coûts
- les plus compatibles avec une concentration contrôlée

## 3.2 Philosophie économique

Ce moteur n’existe pas pour produire beaucoup de trades.  
Il existe pour produire les trades qui justifient :

- un fort score
- une taille plus élevée
- une meilleure conviction
- une meilleure CE attendue

## 3.3 Profil d’activation

- Light : **autorisé**
- Complete : **autorisé**

## 3.4 Priorité

- P0 absolue

## 3.5 Paires autorisées

### Light
- BTC/USDT
- ETH/USDT
- BNB/USDT
- SOL/USDT
- XRP/USDT
- LINK/USDT

### Complete
- toutes les paires autorisées du profil
- avec priorité structurelle aux classes A et B

## 3.6 Régimes compatibles

Régimes favorables :
- trend propre
- expansion propre
- breakout déjà validé et stabilisé
- reprise de structure après compression

Régimes défavorables :
- chop agressif
- range sale
- stress incohérent
- data quality faible
- coût anormalement élevé

## 3.7 Inputs minimaux

- direction structurelle
- score contexte
- coût attendu
- liquidité exploitable
- santé paire
- budget corrélation disponible
- état de marché compatible

## 3.8 Variables mathématiques utiles

Espérance conditionnelle :

\[
\mu_{A,j,s} = \mathbb{E}[r \mid moteur=A, paire=j, régime=s]
\]

Variance conditionnelle :

\[
\sigma^2_{A,j,s} = \mathbb{V}[r \mid moteur=A, paire=j, régime=s]
\]

Break-even prudent :

\[
BE_{A,j} = \mathbb{E}[c \mid moteur=A, paire=j]
\]

Capital efficiency attendue :

\[
CE_{A,j} = \frac{\mathbb{E}[PnL \mid A,j]}{x \cdot h}
\]

## 3.9 Inputs recommandés par famille

### Structure / tendance
- tendance locale
- pente propre
- maintien au-dessus / au-dessous de zones
- qualité de continuation

### Coût
- spread
- ELW
- fill quality attendue

### Qualité contextuelle
- régime
- data freshness
- santé paire
- budget BTC

### Confirmation
- volume utile
- persistance minimale
- absence de contradiction microstructure majeure

## 3.10 Outputs

- signal candidat A
- score brut A
- coût attendu A
- CE attendue A
- recommandation de tier sizing

## 3.11 Scoring minimal

Le moteur A doit avoir :

- score brut élevé
- peu de pénalités
- aucun hard blocker
- coût inférieur au seuil prudent
- budget corrélation disponible

## 3.12 Contraintes de coût

Ne jamais exécuter A si :

\[
\mathbb{E}[g_i \mid A] \le \mathbb{E}[c_i \mid A] + \delta_{safe}
\]

Le moteur A doit rester le plus exigeant en qualité de coût parmi les 4 moteurs.

## 3.13 Contraintes de sizing

Le moteur A est le seul qui peut justifier un Tier 3 de façon naturelle, mais uniquement si :

- budget portefeuille libre
- budget cluster libre
- budget BTC libre
- santé infra stable
- coût réel maîtrisé

## 3.14 Logs obligatoires

- score A
- raisons de non-activation
- coût attendu vs coût réalisé
- CE attendue vs CE réalisée
- tier proposé
- hard / soft / rank détaillés

## 3.15 Métriques de validation

- fréquence utile A
- rendement net A
- Sharpe par trade A
- coût moyen et p90
- CE A
- drawdown A
- taux de stérilisation A
- contribution réelle au portefeuille

## 3.16 Conditions de désactivation

Désactiver ou réduire A si :
- fréquence utile trop basse
- coût réel dégrade l’edge
- CE insuffisante
- trop de trades phantom
- duplication excessive avec C ou D
- régimes détectés devenus défavorables durablement

## 3.17 Dérives à éviter

- en faire un moteur “trop parfait pour trader”
- ajouter des confirmations sans fin
- transformer tout doute en veto
- dupliquer la logique breakout
- utiliser Tier 3 sans budget portefeuille explicite

## 3.18 Verdict

- implémenter **maintenant** en Light
- garder comme moteur référence du portefeuille

---

# 4. MOTEUR B — MEAN REVERSION INTRADAY

## 4.1 Mission

Le moteur B augmente la fréquence utile du système en captant des excès de court terme exploitables en spot, avec sortie rapide et discipline stricte sur les coûts.

## 4.2 Philosophie économique

Le moteur B compense la rareté du moteur A.

Il existe pour générer :
- plus de trades utiles
- des détentions plus courtes
- une meilleure rotation du capital
- une CE potentiellement élevée même avec edge par trade plus faible

## 4.3 Profil d’activation

- Light : **autorisé**
- Complete : **autorisé**

## 4.4 Priorité

- P0 absolue

## 4.5 Paires autorisées

### Light
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- ADA/USDT
- LINK/USDT

### Complete
- classes A et B
- classes C seulement si coût réel validé

## 4.6 Régimes compatibles

Favorables :
- range propre
- excès local
- micro-dislocation sans rupture de structure
- volatilité exploitable mais non chaotique

Défavorables :
- breakout violent
- trend explosif
- marché stressé
- spread / coût élevé
- carnet trompeur

## 4.7 Inputs minimaux

- moyenne locale
- dispersion locale
- score d’excès
- coût attendu
- qualité de retour vers moyenne
- budget corrélation

## 4.8 Variables mathématiques utiles

Z-score local :

\[
z_t = \frac{p_t - \mu_t^{loc}}{\sigma_t^{loc}}
\]

Condition d’entrée type :

\[
|z_t| > z^\star
\]

Edge net conditionnel :

\[
\mu_{B,j,s} = \mathbb{E}[r \mid moteur=B, paire=j, régime=s]
\]

Capital efficiency :

\[
CE_{B,j} = \frac{\mathbb{E}[PnL \mid B,j]}{x \cdot h}
\]

## 4.9 Inputs recommandés

### Excès local
- z-score
- distance à moyenne locale
- vitesse d’éloignement

### Coût
- spread
- slippage attendu
- ELW

### Confirmation
- absence de cassure structurelle
- volume non toxique
- régime non breakout

## 4.10 Outputs

- signal candidat B
- direction mean reversion
- score brut B
- cible de retour
- coût attendu
- temps de détention attendu

## 4.11 Contraintes de coût

Le moteur B a un edge plus fin que A.

Donc la contrainte de coût est encore plus critique :

\[
\mathbb{E}[g_i \mid B] - \mathbb{E}[c_i \mid B] > \delta_{safe,B}
\]

Le \(\delta_{safe,B}\) doit être plus strict qu’en apparence, car le moteur est plus sensible au coût.

## 4.12 Contraintes de sizing

Le moteur B ne doit généralement pas recevoir de Tier 3 sauf exception rarissime.  
Il est un moteur de rotation, pas de concentration forte.

## 4.13 Logs obligatoires

- z-score d’entrée
- moyenne locale
- coût attendu / réalisé
- durée réelle
- retour vers cible ou échec
- CE par trade
- raison de sortie

## 4.14 Métriques de validation

- fréquence utile B
- durée moyenne
- coût moyen / p90
- hit rate net
- CE B
- rendement net B
- sensibilité aux coûts
- drawdown B
- corrélation avec moteur A

## 4.15 Conditions de désactivation

Désactiver ou réduire B si :
- coût absorbe l’edge
- trop de trades contre de vrais breakouts
- durée dérive à la hausse
- CE devient insuffisante
- corrélation trop élevée avec A sans alpha propre

## 4.16 Dérives à éviter

- mean reversion dans un marché cassé
- z-score pur sans contexte
- utiliser B comme machine à “faire du volume”
- ignorer la structure de cassure
- le traiter comme moteur principal du portefeuille

## 4.17 Verdict

- implémenter **maintenant** en Light
- c’est le moteur complémentaire prioritaire de A

---

# 5. MOTEUR C — BREAKOUT CONTINUATION

## 5.1 Mission

Le moteur C exploite les sorties de range ou expansions validées qui méritent une logique de continuation propre, distincte du moteur A.

## 5.2 Philosophie économique

Le moteur C existe uniquement s’il apporte quelque chose que A n’apporte pas déjà :

- plus de fréquence utile
- meilleure couverture des expansions courtes
- edge spécifique de continuation

S’il n’apporte qu’une duplication du moteur A, il doit être supprimé.

## 5.3 Profil d’activation

- Light : **interdit**
- Complete : **autorisé**

## 5.4 Priorité

- P1

## 5.5 Paires autorisées

### Complete seulement
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- BNB/USDT
- AVAX/USDT
- LINK/USDT

Les paires plus fragiles doivent être validées explicitement par coût réel.

## 5.6 Régimes compatibles

Favorables :
- compression préalable
- expansion confirmée
- volume réel en hausse
- coût encore acceptable malgré accélération

Défavorables :
- faux breakout
- expansion tardive
- extension déjà épuisée
- marché trop stressé

## 5.7 Inputs minimaux

- range identifié
- seuil de cassure
- volume utile
- microstructure non contradictoire
- coût attendu
- budget corrélation

## 5.8 Variables mathématiques utiles

Condition type :

\[
p_t > p_{range,max} + \delta
\]

ou

\[
p_t < p_{range,min} - \delta
\]

avec confirmation :

\[
Vol_t > \theta_{Vol}
\]

et qualité :

\[
M_t > \theta_M
\]

## 5.9 Outputs

- signal breakout valide
- force de cassure
- score brut C
- coût attendu
- contexte de continuation

## 5.10 Contraintes de coût

Le moteur C a souvent un coût d’entrée plus élevé que A et B.  
Il doit être désactivé immédiatement si le marché devient trop cher à capturer.

## 5.11 Contraintes de sizing

Le moteur C ne doit jamais recevoir Tier 3 lors de son introduction.  
Il doit d’abord prouver :
- alpha net
- CE correcte
- non-duplication de A

## 5.12 Logs obligatoires

- range source
- niveau cassure
- volume à l’entrée
- coût attendu
- slippage réalisé
- continuation réussie / échouée
- corrélation ex post avec A

## 5.13 Métriques de validation

- taux de faux breakout
- coût de capture
- CE C
- rendement net C
- temps de poursuite exploitable
- corrélation avec A
- gain marginal vs absence du moteur C

## 5.14 Conditions de désactivation

Désactiver C si :
- duplication de A
- coût trop élevé
- faux breakout fréquents
- CE trop faible
- stress marché fréquent

## 5.15 Dérives à éviter

- construire un moteur C qui n’est qu’un A “plus nerveux”
- exécuter trop tard
- prendre des breakouts sans vrai volume
- traiter la volatilité seule comme signal

## 5.16 Verdict

- ne pas implémenter en Light
- implémenter **plus tard** en Complete après validation de A + B

---

# 6. MOTEUR D — RE-ENTRY / SECOND CHANCE LOGIC

## 6.1 Mission

Le moteur D permet de ré-engager du capital après un premier trade valide, quand une structure propre se reforme.

## 6.2 Philosophie économique

Le moteur D n’est pas un moteur autonome d’origine.  
Il doit être conçu comme une extension contrôlée d’un edge déjà validé, pas comme un nouveau générateur de trades sans mémoire.

## 6.3 Profil d’activation

- Light : **interdit**
- Complete : **autorisé**

## 6.4 Priorité

- P1

## 6.5 Paires autorisées

Priorité aux paires les plus propres :
- BTC/USDT
- ETH/USDT
- BNB/USDT
- SOL/USDT
- LINK/USDT

Pas de D sur paires fragiles tant que la qualité d’exécution n’est pas clairement validée.

## 6.6 Régimes compatibles

Favorables :
- reformation claire de structure
- reprise après pullback propre
- continuation déjà démontrée

Défavorables :
- marché devenu erratique
- re-entry contre fatigue de move
- contexte de stress
- coût trop élevé

## 6.7 Inputs minimaux

- existence d’un premier trade valide
- état de sortie précédent
- nouvelle structure exploitable
- budget de risque encore libre
- corrélation portefeuille encore acceptable

## 6.8 Variables mathématiques utiles

Edge conditionnel de réentrée :

\[
\mu_{D,j,s \mid history} = \mathbb{E}[r \mid moteur=D, paire=j, régime=s, historique]
\]

Coût marginal de seconde entrée :

\[
c_{D,2nd} = \mathbb{E}[c \mid reentry]
\]

CE marginale :

\[
CE_{D} = \frac{\mathbb{E}[PnL \mid D]}{x \cdot h}
\]

## 6.9 Outputs

- signal re-entry valide
- score D
- relation avec le premier trade
- coût marginal
- budget corrélation résiduel

## 6.10 Contraintes de coût

Un re-entry tardif est très souvent moins bon qu’il n’en a l’air.  
Le moteur D doit être très strict sur le coût marginal.

## 6.11 Contraintes de sizing

Le moteur D ne doit pas bénéficier d’un sizing agressif au départ.  
Il doit être traité comme un moteur de ré-allocation opportuniste, jamais comme moteur de concentration principale.

## 6.12 Logs obligatoires

- trade d’origine lié
- motif de sortie initiale
- motif de réentrée
- temps écoulé
- coût marginal
- CE marginale
- contribution nette au portefeuille

## 6.13 Métriques de validation

- gain additionnel net par rapport à l’absence de réentrée
- coût marginal moyen / p90
- durée moyenne des réentrées
- drawdown spécifique D
- corrélation avec A

## 6.14 Conditions de désactivation

Désactiver D si :
- il double A sans gain
- il augmente la concentration
- coût marginal trop élevé
- il sert de mécanisme de “revenge trading” automatisé
- CE marginale négative ou faible

## 6.15 Dérives à éviter

- ré-entrer par frustration algorithmique
- considérer D comme moteur principal
- ignorer l’impact sur concentration et budget BTC
- réentrée sans nouvelle information structurelle

## 6.16 Verdict

- ne pas implémenter en Light
- implémenter **plus tard** en Complete
- le traiter comme extension disciplinée, pas comme moteur autonome majeur

---

# 7. Tableau comparatif des paires par moteur

| Paire | A | B | C | D | Remarque |
|---|---:|---:|---:|---:|---|
| BTC/USDT | oui | oui | oui | oui | paire de référence |
| ETH/USDT | oui | oui | oui | oui | pilier principal |
| BNB/USDT | oui | non/option | oui | oui | plutôt structurel |
| SOL/USDT | oui | oui | oui | oui | riche mais plus nerveuse |
| XRP/USDT | oui | oui | oui | non/option | utile pour B et C |
| ADA/USDT | non/option | oui | non/option | non | plutôt B |
| LINK/USDT | oui | oui | oui | oui | bonne paire intermédiaire |
| AVAX/USDT | non/option | non/option | oui | non | plutôt C |
| DOGE/USDT | non | non/option | non/option | non | très encadrée |
| TRX/USDT | non/option | oui/option | non | non | plutôt B tactique |
| TON/USDT | non | non | option | non | à valider tardivement |
| DOT/USDT | non/option | non/option | non/option | non | à usage prudent |

---

# 8. Tableau comparatif des signatures économiques

| Moteur | Edge par trade | Fréquence | Durée moyenne | Sensibilité aux coûts | Probabilité Tier 3 | CE attendue |
|---|---|---|---|---|---|---|
| A | élevée | faible/modérée | moyenne | moyenne | élevée | élevée si bien choisi |
| B | moyenne | modérée | courte | élevée | faible | potentiellement élevée |
| C | moyenne | modérée | courte/moyenne | très élevée | faible au départ | incertaine avant validation |
| D | variable | faible/modérée | variable | élevée | faible | dépend du contexte |

---

# 9. Tableau des dérives typiques par moteur

| Moteur | Dérive typique | Conséquence |
|---|---|---|
| A | sur-filtrage extrême | stérilité économique |
| B | mean reversion contre cassure réelle | pertes en série |
| C | duplication de A | complexité sans alpha |
| D | re-entry émotionnelle automatisée | surconcentration / overtrading |

---

# 10. Conditions minimales de validation par moteur

## 10.1 Moteur A
Doit prouver :
- edge net positif
- coût soutenable
- CE correcte
- fréquence utile non nulle
- capacité de concentration contrôlée

## 10.2 Moteur B
Doit prouver :
- rotation plus forte que A
- CE correcte malgré coûts
- absence de destruction systématique en phase breakout
- drawdown acceptable

## 10.3 Moteur C
Doit prouver :
- non-duplication de A
- gain marginal portefeuille
- coût d’entrée soutenable
- faible taux de faux breakout

## 10.4 Moteur D
Doit prouver :
- valeur marginale positive
- coût marginal acceptable
- non-augmentation excessive de concentration
- utilité par rapport à l’absence de réentrée

---

# 11. Conditions minimales de désactivation par moteur

| Moteur | Désactivation si |
|---|---|
| A | fréquence utile trop faible, coût réel trop élevé, CE insuffisante |
| B | coût absorbe edge, trop de pertes en cassure, CE faible |
| C | duplication de A, faux breakout fréquents, coût trop élevé |
| D | pas d’alpha additionnel, surconcentration, coût marginal excessif |

---

# 12. Logs canoniques par moteur

## 12.1 Logs minimums communs
- moteur
- paire
- régime
- score
- hard blockers
- pénalités
- taille
- coût attendu
- coût réalisé
- rendement net
- CE réalisée
- motif de sortie

## 12.2 Logs spécifiques A
- structure premium
- tier proposé
- conviction

## 12.3 Logs spécifiques B
- z-score
- moyenne locale
- distance au retour

## 12.4 Logs spécifiques C
- range source
- niveau de cassure
- volume de confirmation

## 12.5 Logs spécifiques D
- trade d’origine
- délai depuis sortie
- justification de réentrée

---

# 13. Ordre canonique d’implémentation des moteurs

## Étape 1
- Moteur A
- Moteur B

## Étape 2
- validation shadow
- micro-live
- live-light

## Étape 3
- Moteur C
- réévaluation corrélation A/C

## Étape 4
- Moteur D
- uniquement si A est déjà stable

---

# 14. Verdict final par moteur

| Moteur | Verdict |
|---|---|
| A | implémenter maintenant |
| B | implémenter maintenant |
| C | implémenter plus tard |
| D | implémenter plus tard |

---

# 15. Conclusion

La V5.3 n’a pas besoin de 4 moteurs actifs immédiatement pour être cohérente.

Elle a besoin :

1. d’une **architecture cible complète**
2. d’un **ordre d’activation discipliné**
3. de **2 moteurs immédiatement rentables ou prometteurs**
4. de **2 moteurs supplémentaires seulement s’ils ajoutent un vrai edge ou une vraie diversification**

Le rôle de ce document est précisément d’empêcher :

- la confusion entre ambition cible et activation réelle
- la duplication d’edge sous des noms différents
- la création de moteurs “prestige” sans utilité économique

---

## Fin du document
