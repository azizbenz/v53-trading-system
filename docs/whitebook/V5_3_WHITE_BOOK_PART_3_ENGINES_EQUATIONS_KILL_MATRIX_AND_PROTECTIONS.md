# V5.3 WHITE BOOK - PARTIE 3
## Moteurs, équations, kill matrix, logique de downgrade et protections

---

# 0. Périmètre

Cette partie couvre :

- les moteurs A/B/C/D
- les équations des readers Build-14
- les équations portefeuille
- la kill matrix et la logique de dégradation
- la manière dont V5.3 se protège contre l’échec data, marché, opérateur et IA

---

# 1. Philosophie moteurs

La doctrine moteurs est simple :

- A/B sont le noyau de monétisation
- C/D sont des moteurs d’extension, pas des excuses pour relâcher la discipline
- chaque moteur doit justifier son existence économiquement après coût
- chaque moteur doit être distinguable des autres

La famille moteurs ne survit que si elle apporte au moins une des choses suivantes :

- alpha net
- vraie diversification d’edge
- meilleure capital efficiency

---

# 2. Engine A - Premium Trend / Expansion

## 2.1 Rôle économique

Engine A est le moteur de conviction premium.

Il existe pour capturer :

- les structures directionnelles les plus propres
- les continuations stables
- les expansions de qualité
- les trades qui justifient une taille plus crédible que le reste

## 2.2 Maths coeur

Équations canoniques :

- espérance conditionnelle :
  - `mu_A,j,s = E[r | A, j, s]`
- variance conditionnelle :
  - `sigma_A,j,s^2 = V[r | A, j, s]`
- break-even prudent :
  - `BE_A,j = E[c | A, j]`
- capital efficiency attendue :
  - `CE_A,j = E[PnL | A, j] / (x * h)`

## 2.3 Logique

Engine A ne doit survivre que si :

- le coût reste nettement inférieur au gross edge attendu
- la structure reste cohérente
- le régime est compatible
- le budget corrélation est disponible
- le contexte portefeuille reste acceptable

## 2.4 Forces

- forte identité de trade
- bonne justification d’un sizing plus élevé
- plus facile à expliquer que beaucoup de moteurs complexes

## 2.5 Négatifs

- risque de faible fréquence
- risque élevé de stérilisation
- peut devenir “beau mais inutile” avec petit capital

## 2.6 Angle mort

Le principal angle mort est le purisme excessif :

- si A devient trop sélectif, le système peut rester techniquement juste et économiquement sous-exploité

---

# 3. Engine B - Mean Reversion Intraday

## 3.1 Rôle économique

Engine B existe pour restaurer de la fréquence utile sans s’effondrer dans le bruit.

Il essaie de monétiser :

- les dislocations locales
- les reversions de court horizon contrôlées
- les inefficiences intraday

## 3.2 Lecture coeur

B doit être plus fréquent que A, mais rester gouverné par :

- le réalisme du coût
- la santé de la paire
- la compatibilité de régime
- la disponibilité des budgets de risque

## 3.3 Forces

- fréquence plus élevée
- bon complément de A
- probablement important pour la monétisabilité à petit capital

## 3.4 Négatifs

- peut souffrir fortement lors de vraies cassures
- peut devenir trop bavard dans des ranges sales

## 3.5 Angle mort

Si la lecture de régime est faible, B peut trader contre une vraie transition au lieu de trader contre du bruit.

---

# 4. Engine C - Breakout Continuation

## 4.1 Rôle économique

Engine C cherche à capturer la continuation après validation de breakout.

Il ne doit pas être :

- une copie bruitée de A
- une machine à chase les breakouts
- un moteur d’expansion ignorant les coûts

## 4.2 Équations canoniques

Les docs exposent :

- CE conditionnelle :
  - `CE_C,j,s = E[PnL | C, j, s] / (x * h)`
- CE réalisée moteur :
  - `CE_C = sum_{i in C} PnL_i / sum_{i in C} x_i h_i`
- Sharpe par trade C :
  - lecture pratique standard : moyenne des returns trade / volatilité des returns trade

## 4.3 Blockers structurels

Les specs citent explicitement comme conditions de kill :

- stale hard
- loss budget breach
- beta BTC breach
- cluster breach

## 4.4 Forces

- peut augmenter la fréquence utile en continuation
- peut diversifier au-delà de la logique premium de A
- devient plus utile quand la continuation est réelle mais que A reste trop conservateur

## 4.5 Négatifs

- exposition aux faux breakouts
- fort risque de duplication avec A
- vulnérabilité à la microstructure bruyante

## 4.6 Angle mort

C échoue s’il ne prouve pas une famille d’edge distincte.

Si C n’est que “A mais un peu plus tard et un peu moins bien”, il doit rester dormant.

---

# 5. Engine D - Re-entry / Second Chance

## 5.1 Rôle économique

Engine D cherche à capturer les secondes entrées :

- après un premier move
- après un pullback
- après un reset structurel local

Il est structurellement plus subtil.

## 5.2 Équations canoniques

Les docs exposent :

- CE marginale :
  - `CE_D,j,s^marg = E[PnL | D, j, s] / (x * h)`
- CE réalisée moteur :
  - `CE_D = sum_{i in D} PnL_i / sum_{i in D} x_i h_i`
- contrainte de concentration :
  - la concentration marginale doit rester sous le budget disponible

## 5.3 Blockers structurels

Comme C, les blockers explicites sont :

- stale hard
- loss budget breach
- beta BTC breach
- cluster breach

## 5.4 Forces

- peut monétiser des entrées ratées ou retardées
- peut apporter une vraie diversification si son edge est réellement distinct
- peut être stratégiquement utile dans des marchés de tendance incomplète

## 5.5 Négatifs

- le risque de duplication avec A est très élevé
- le risque de concentration est structurellement plus fort
- les recouvrements de thème peuvent être cachés

## 5.6 Angle mort

D est particulièrement vulnérable à la fausse originalité.

Il peut ressembler à un nouveau moteur alors qu’il ne fait que reconditionner une exposition déjà possédée.

---

# 6. Équations portefeuille et système

Ces équations comptent parce que V5.3 ne doit jamais optimiser le win rate isolément.

## 6.1 Capital efficiency

- Shadow :
  - `CE_shadow = sum_i PnL_i_shadow / sum_i x_i h_i`
- Réel :
  - `CE_real = sum_i PnL_i_real / sum_i x_i h_i`

Interprétation :

- la CE est la métrique économique canonique du système
- ici elle est plus pertinente que le simple PnL brut ou le win rate

## 6.2 Beta portefeuille

- `Beta_port = sum_j w_j beta_j`

Interprétation :

- V5.3 veut une exposition spot diversifiée, pas un “long beta déguisé”

## 6.3 Pression cluster

- `ClusterExp_c = sum_{i in cluster c} x_i`

Interprétation :

- la concentration cluster est un objet de risque de premier rang

## 6.4 Dynamique de backlog

- `B(t+1) = B(t) + A(t) - S(t)`

Interprétation :

- la saturation infra fait partie du risque de trading, pas d’un sujet ops séparé

## 6.5 Fraîcheur de donnée

- `Delta = t_local - t_exchange`

Seuil clé :

- stale threshold exchange dur par défaut : `0.2s`
- en `MICRO_LIVE` et `LIVE`, le dépassement bloque la décision
- en `SHADOW`, le dépassement dégrade et loggue au lieu de laisser trader silencieusement

---

# 7. Readers Build-14 et leurs équations

Les readers Build-14 sont des readers analytiques bornés.  
Ce ne sont pas des moteurs.

## 7.1 Market toxicity

Formule :

- `toxicity = 0.35*backlog + 0.25*stale + 0.20*loss + 0.20*cra`

Avec :

- `backlog = min(queue_backlog / 100, 1)`
- `stale = min(stale_pair_count / 2, 1)`
- `loss = min((dtr_loss_count + log_loss_count) / 2, 1)`
- `cra = cra_sterilization_rate`

Bandes de sévérité :

- `>= 0.75` : critical
- `>= 0.40` : elevated

Utilité :

- détecter si l’environnement devient toxique opérationnellement avant de prétendre que la qualité d’edge est intacte

Angle mort :

- cela reste un score synthétique, pas un théorème universel de microstructure

## 7.2 Execution fragility

Formule :

- `fragility = 0.35*drift + 0.30*edge_degraded + 0.20*ce_component + 0.15*loss`

Bandes de sévérité :

- `>= 0.75` : critical
- `>= 0.40` : elevated

Utilité :

- relier break-even drift, edge dégradé, faiblesse de CE et pertes d’observabilité dans une même alerte d’exécution

## 7.3 LOB deep filter / VWA

Formule :

- `depth_fragility = 0.40*(1-vwa_absorption) + 0.35*ghost_liquidity + 0.15*stale + 0.10*backlog`

Bandes de sévérité :

- `>= 0.70` : critical
- `>= 0.35` : elevated

Utilité :

- essayer de quantifier le risque de faible absorption et de ghost liquidity

Angle mort :

- ce reader n’est aussi bon que les faits depth qui lui sont réellement fournis

## 7.4 Order-book imbalance

Formule :

- `obi_pressure = 0.55*adverse_obi + 0.20*cra + 0.15*stale + 0.10*ce_negative`

Bandes de sévérité :

- `>= 0.70` : critical
- `>= 0.35` : elevated

Utilité :

- relier pression order-book, stérilisation et faiblesse économique

## 7.5 False breakout model

Formule :

- `false_breakout = 0.45*breakout_failure + 0.30*(1-volume_support) + 0.15*cra + 0.10*drift`

Bandes de sévérité :

- `>= 0.70` : critical
- `>= 0.35` : elevated

Utilité :

- particulièrement utile pour A et C

## 7.6 Hurst regime classifier

Formule :

- `hurst_distance = abs(hurst - 0.50) * 2`
- `regime_instability = 0.55*hurst_distance + 0.25*edge_degraded + 0.20*drift`

Bandes de sévérité :

- `>= 0.70` : critical
- `>= 0.35` : elevated

Utilité :

- produire un signal borné d’instabilité de régime

Angle mort :

- Hurst peut être mathématiquement élégant et économiquement tardif

## 7.7 Competition monitor

Formule :

- `crowding = 0.60*competition_density + 0.20*stale + 0.20*ce_negative`

Bandes de sévérité :

- `>= 0.70` : critical
- `>= 0.35` : elevated

Utilité :

- estimer le crowding et le risque d’edge déjà sur-occupé

Angle mort :

- la compétition est difficile à observer directement ; cela reste un proxy

---

# 8. Pile de protection

## 8.1 Protection data

- rejet crossed book
- tolérance contradiction timestamp
- stale hard guard exchange
- dégradation et suspension par paire
- observabilité backlog

## 8.2 Protection risque

- budget perte
- budget beta
- budget cluster
- caps d’exposition
- posture prudente sous drawdown

## 8.3 Protection exécution

- réconciliation
- gestion timeout
- log du coût réel
- pas de divergence silencieuse compte / état local

## 8.4 Protection gouvernance

- interdiction live mutation path
- intégrité des profils
- review gating
- validation d’import
- interdiction des forks cachés local/live

## 8.5 Protection Build-14

Build-14 est explicitement borné par contrat :

- ne peut pas override les moteurs
- ne peut pas bypass le risque
- ne peut pas bypass le portefeuille
- ne peut pas trader de façon autonome

C’est un des choix de sécurité les plus importants du système entier.

---

# 9. Kill matrix

La kill matrix V5.3 n’est pas un seul switch.  
C’est une hiérarchie explicite de refus, de downgrade ou de blocage.

| Trigger | Couche | Source typique | Effet | Conséquence runtime |
| --- | --- | --- | --- | --- |
| crossed book | data | état depth invalide | rejet event | aucune décision à partir d’un book invalide |
| exchange stale > seuil | data | donnée retardée ou trop vieille | degrade en Shadow, hard block en Micro-live/Live | protection contre trading sur état périmé |
| backlog surge | data / infra | saturation routeur ou worker | warning puis interprétation dégradée | prudence paire ou système |
| reconciliation divergence | execution | mismatch compte / état local | alerte opérationnelle dure | halt ou rollback possible |
| loss budget breach | risk | budget perte dépassé | refus dur | candidat bloqué |
| cluster breach | risk | concentration trop élevée | refus dur | candidat bloqué |
| beta BTC breach | risk | beta portefeuille trop élevée | refus dur | candidat bloqué |
| CE sous économie acceptable | scoring / engine | coût > edge | rejet ou downgrade candidat | pas de trade |
| break-even drift alert | meta / Build-14 | économie réelle pire que prévue | downgrade de confiance | baisse de confiance promotion |
| DTR/log loss | meta / ops | vérité d’audit incomplète | learning/review bloqués | freeze gouvernance |
| opérateur `set_halted` | opérateur | safing manuel | demande de halt | plus d’exposition supérieure autorisée |
| opérateur downgrade vers `MICRO_LIVE` | opérateur | requalification manuelle | downgrade runtime | exposition live réduite |
| opérateur downgrade vers `SHADOW` | opérateur | requalification manuelle | downgrade runtime | plus d’exécution réelle |
| kill switch externe | ops | flag fichier / API admin | logique de halt immédiat | le système doit cesser de trader |

---

# 10. Logique de downgrade opérateur

Le contrat de safing opérateur autorise actuellement :

- `set_halted`
- `downgrade_to_micro_live`
- `downgrade_to_shadow`

Contraintes déjà codées :

- aucune requête de safing depuis `LOCAL_REPLAY`
- downgrade vers `MICRO_LIVE` seulement depuis `LIVE`
- downgrade vers `SHADOW` seulement depuis `MICRO_LIVE` ou `LIVE`
- chaque requête impose un motif

Pourquoi c’est un bon design :

- ça empêche la mutation libre des phases
- ça garde l’intervention opérateur audit-ready

---

# 11. Comment V5.3 se protège globalement

V5.3 se protège de quatre façons imbriquées :

1. en refusant les données invalides
2. en refusant les trades économiquement cassés
3. en refusant les abus de concentration et de budgets
4. en refusant les progressions de rollout non gouvernées

C’est pour cela que le système paraît plus lourd qu’une stack de stratégie classique.

Mais cette lourdeur est volontaire.  
La thèse de design est :

> si le système ne peut pas expliquer pourquoi il est sûr, alors il n’est pas sûr.

---

# 12. Conclusion de la partie 3

La couche moteurs de V5.3 ne parle pas seulement d’alpha.

Elle parle aussi de :

- la survie de l’alpha après coût
- la réalité de la diversification
- la visibilité de la concentration de risque
- la capacité du contexte enrichi à rester borné sans devenir autonome

C’est pour cela que l’architecture reste crédible même quand certains builds sont encore ouverts.

