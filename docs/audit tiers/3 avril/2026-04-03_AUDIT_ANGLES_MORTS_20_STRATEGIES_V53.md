# Audit V5.3 — angles morts structurants + 20 stratégies de trading

## Date

2026-04-03


## Objet

Ce document consolide les 5 audits/upload du 2026-04-03 avec le canon V5.3 et les specs Build-1 à Build-17. Il répond à trois demandes :

1. **analyser et auditer en profondeur** la V5.3 sous les angles quant, fintech, développeur, mathématique et trader senior ;
2. **identifier les angles morts réels** du système, non pas dans l’abstrait, mais à partir des surfaces code-backed et des règles canoniques ;
3. **proposer 20 stratégies** compatibles avec le canon V5.3, classées sans créer de moteur hors A/B/C/D.


## Note d’honnêteté sur “ligne par ligne”

Je traite ici les documents **rubrique par rubrique et composant par composant**, ce qui est la bonne granularité utile pour V5.3. Un audit littéral phrase par phrase sur tout le corpus serait beaucoup plus long, plus bruité, et moins exploitable pour la suite du projet.


## Corpus réellement relu

- `2026-04-03_LOT1_RISK_SCORING_EXPLICABILITY_SLICE_AUDIT.md`
- `2026-04-03_V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md`
- `2026-04-03_V53_CODE_FIRST_STRATEGY_ENRICHMENT_AUDIT.md`
- `2026-04-03_V53_FINAL_MODULE_COMPONENT_AUDIT_AND_STRATEGY_ENRICHMENT_PLAN.md`
- `2026-04-03_V53_STRATEGY_ENRICHMENT_BACKLOG_CODE_FIRST.md`
- `V5_3_MASTER_FINAL_CANONICAL.md`
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- `V5_3_TABLE_DETAILLEE_MOTEURS.md`
- `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
- `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md`
- `V5_3_BUILD4_SPECS_MODULES.md`
- `V5_3_BUILD5_SPECS_MODULES.md`
- `V5_3_BUILD6_SPECS_MOTEUR_A.md`
- `V5_3_BUILD7_SPECS_MOTEUR_B.md`
- `V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md`
- `V5_3_BUILD9_SPECS_META_MINIMAL.md`
- `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md`
- `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
- `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`
- `V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
- `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
- `V5_3_BUILD15_SPECS_MOTEUR_C.md`
- `V5_3_BUILD16_SPECS_MOTEUR_D.md`
- `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md`

## Verdict exécutif


**Verdict global : V5.3 est une architecture réellement code-backed, déjà très forte en gouvernance de preuve, mais encore asymétrique en explicabilité interne.**

### Ce qui est solide
- la colonne vertébrale **Build-1 -> Build-16** existe réellement ;
- la chaîne **data -> execution -> risk -> scoring -> engines -> portfolio -> meta -> replay -> protocols -> monitoring** est bien présente ;
- les meilleures surfaces d’audit et de gouvernance sont déjà :
  - `meta_learning`
  - `local_replay_runtime`
  - `protocols`
  - `complete_enablers`
  - `monitoring`

### Ce qui est encore faible
- `risk_backbone`, `scoring_backbone`, `portfolio_minimal` et une partie de `meta_minimal` restent **moins riches en lineage textuel** que Build-9X/11/14 ;
- `Build-17` reste **partiel** : la surface Complete existe, mais la fermeture runtime Complete n’est pas encore un module isolé et totalement fermé ;
- `engine_c` et `engine_d` sont **existants mais encore fragiles conceptuellement** : le vrai danger n’est pas “l’absence”, mais la **promotion prématurée**.

### Conséquence stratégique
Vous ne devez pas chercher l’alpha futur principalement en ajoutant des moteurs.
Le levier le plus rentable est :

1. finir l’explicabilité risk/scoring,
2. exploiter Build-14 reader-by-reader,
3. reconnecter data/exécution aux diagnostics,
4. durcir portefeuille et non-duplication A/B/C/D,
5. puis seulement enrichir les variantes.

### Conséquence de gouvernance
Le bon modèle n’est pas :
- idée -> code -> live

Le bon modèle est :
- idée -> classification (`A_variant`, `B_variant`, `C_candidate`, `D_candidate`) -> versioning -> `LOCAL_REPLAY` -> evidence bundle -> `protocols` -> shadow -> promotion conditionnelle.


# 1. Audit rubrique par rubrique des 5 documents uploadés


## 2026-04-03_LOT1_RISK_SCORING_EXPLICABILITY_SLICE_AUDIT.md

### Objet
Bonne direction: la tranche Lot 1 ajoute enfin des reason codes stables côté risque et une lecture dominante côté scoring.

### Build-4 risk_backbone
Progrès clair: `RiskEvaluation` expose maintenant `reason_details`, `dominant_reason_code`, `explain_summary`. Cela réduit l'opacité structurelle de Build-4, mais la couverture reste partielle tant que ces raisons ne remontent pas pleinement dans `meta_learning`, `Pairs`, `Risk` et `Replay & Import`.

### Build-5 scoring_backbone
Progrès fort: `ScoringCandidateAudit` devient racontable. C'est critique pour séparer problème d'alpha, de coût, de pénalité, de portefeuille et de hard block.

### Artifacts LOCAL_REPLAY -> SHADOW
Très bon choix d'architecture: les résumés scoring/risk sont poussés jusqu'aux sidecars et aux payloads techniques, ce qui renforce la continuité preuve -> rollout.

### UI / monitoring
La visibilité au niveau `EngineMetrics` est une vraie amélioration, mais elle reste centrée sur les cartes Engines; l'absence de projection systématique au niveau paire, portefeuille et protocole laisse un angle mort opératoire.

### Ce qui reste ouvert
Point majeur: Lot 1 n'est pas fermé. La tranche livre une première couche d'explicabilité, pas encore un système complet de causalité gouvernée.


## 2026-04-03_V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md

### Objet / méthode
Document très solide méthodologiquement: audit code-first, honnêteté de surface, refus de reconstruire fictivement ce qui n'est pas réellement dans `src/`.

### Inventaire réel confirmé
Verdict positif: la colonne vertébrale V5.3 existe réellement du Build-1 au Build-16; Build-17 reste partiel et surtout surfacique côté UI/Complete.

### Build-1
Socle structurel sain. Point fort: langage métier, manifests, DAG, smoke/recovery. Sans cela, aucun onboarding stratégie sérieux n'est possible.

### Build-2
Data backbone réel et net, mais la preuve de qualité passe plus par monitoring que par contrats textuels riches; cela limite l'audit causale directe.

### Build-3
Execution backbone robuste et transactionnellement traçable (`order_id`, `fill_id`), mais encore plus orienté événements qu'explicabilité économique complète.

### Build-4 / Build-5
Risque et scoring sont bien isolés, mais leur preuve textuelle/lineage reste plus faible que Build-9X/11/14. C'est l'une des asymétries majeures du système.

### Builds 6/7/15/16
A/B sont plus modulaires que C/D. C et D existent, mais leur décomposition interne est plus compacte: ils sont code-backed, pas encore au même niveau de fermeture explicative.

### Build-8 / Build-9
Portfolio et meta existent mais une partie des capacités canoniques reste absorbée plutôt qu'isolée en packages distincts.

### Build-10 à 14
Très forte richesse en preuves côté monitoring, protocols, local replay et complete enablers. C'est le vrai moteur de gouvernance du système.

### Gaps et zones implicites
Constat très important: `microstructure_engine`, `regime_engine`, `risk_contribution_monitor`, `effective_edge_diversity`, et `live_complete` n'apparaissent pas toujours comme modules top-level isolés. Cela ne casse pas V5.3, mais complique l'audit et l'évolutivité.


## 2026-04-03_V53_CODE_FIRST_STRATEGY_ENRICHMENT_AUDIT.md

### Règles de travail
Excellent cadrage: ne pas commencer par les moteurs seuls, ne pas contourner risk/scoring/protocols, ne pas traiter Build-14 comme un moteur, ne pas utiliser Build-9X pour muter le live.

### Vue d'ensemble des vraies capacités
Très juste: la valeur stratégique réelle n'est pas seulement dans A/B/C/D, mais dans la chaîne data -> risk -> scoring -> engine -> portfolio -> meta -> replay -> shadow -> monitoring.

### Data backbone
Angle fort: permet déjà des stratégies conditionnelles par qualité de flux; angle mort: le lien data -> scoring/risk/meta reste sous-exploité.

### Execution backbone
Angle fort: protège contre les faux edges papier; angle mort: le feedback exécution n'est pas encore suffisamment rétro-injecté dans les hypothèses et pénalités.

### Risk backbone
Angle fort: vraie borne de survie; angle mort majeur: raisonne fort mais raconte encore insuffisamment au niveau lineage.

### Scoring backbone
Angle fort: classe des moteurs hétérogènes sur une base économique; angle mort: explicabilité encore inégale stratégie par stratégie.

### Engines A/B/C/D
Lecture correcte des risques spécifiques: A peut sur-détecter, B peut combattre un trend, C est hypersensible aux faux breakouts, D peut dériver en revenge trade.

### Portfolio / Meta / Build-9X
Très bon diagnostic: sans portefeuille lisible et sans Build-9X fort, l'enrichissement devient intuitif et non gouverné.

### Protocols / Build-14 / Monitoring
Très juste: protocols décide de la promouvabilité réelle; Build-14 est la meilleure réserve d'enrichissement transverse; monitoring/UI doit raconter 'pourquoi', pas seulement 'quoi'.


## 2026-04-03_V53_FINAL_MODULE_COMPONENT_AUDIT_AND_STRATEGY_ENRICHMENT_PLAN.md

### Objet / règles anti-hallucination
Document essentiel pour cadrer l'audit complet. Il impose la bonne grille: rôle, inputs, outputs, équations, blockers, dépendances, logs, tests, usage, enrichissement, angle mort, risque d'enrichissement.

### Matrice anti-oubli
Point fort méthodologique: couverture de Build-1 à Build-17, plus sous-composants canoniques; c'est la meilleure protection contre l'oubli de brique.

### Phases A à F / plan d'exécution
Bonne hiérarchie de travail. La stratégie est correctement repositionnée comme conséquence d'un audit de capacité, pas comme brainstorming de features.

### Angle mort résiduel
Le document planifie parfaitement l'audit, mais ne résout pas encore le delta entre canon et surfaces réellement isolées dans le code.


## 2026-04-03_V53_STRATEGY_ENRICHMENT_BACKLOG_CODE_FIRST.md

### Principes de gouvernance
Très bon backlog: il interdit les contournements, refuse les moteurs hors A/B/C/D, recentre la preuve sur replay/shadow/protocols.

### Vue d'ensemble par lots
Structure saine: Lot 0 instrumentation, Lot 1 explicabilité risk/scoring, Lot 2 A/B, Lots 3/4 C/D, Lot 5 portefeuille, Lot 6 Build-14, Lot 7 data/execution feedback loop, Lot 8 supervision.

### Ordre recommandé
L'ordre proposé est cohérent. Le point le plus intelligent est de faire Lot 6 tôt: Build-14 est déjà la réserve la plus rentable d'enrichissement transverse.

### Ce qu'il ne faut pas faire
Très juste: ne pas rouvrir Build-12/13 comme zone d'expérimentation, ne pas enrichir C/D sans feedback execution, ne pas complexifier l'UI avant d'avoir des reason codes propres.

### Angle mort résiduel
Le backlog est excellent comme gouvernance, mais il suppose une discipline d'exécution continue; sans ownership fort, il peut redevenir une liste d'intentions.


# 2. Lecture transversale par angle métier

## 2.1 Angle quant


### Forces
- Le système sait déjà séparer **hard blockers**, **soft penalties** et **ranking**.
- Les moteurs A/B/C/D sont définis comme des **hypothèses d’edge distinctes**, pas comme de simples filtres de style.
- Le canon insiste correctement sur la **capital efficiency**, le coût réel, la non-duplication et la fréquence utile.

### Faiblesses
- La séparation entre **problème d’alpha**, **problème de coût**, **problème de portefeuille** et **problème de veto dur** reste encore trop souvent visible seulement dans des agrégats.
- C et D peuvent facilement créer une **illusion de diversification** alors qu’ils ne font que recycler A.

### Verdict quant
Le système est déjà bon pour **gouverner** l’alpha.
Il n’est pas encore assez bon pour **autopsier** l’alpha perdu avec une causalité parfaite sur tous les niveaux.


## 2.2 Angle fintech / produit / gouvernance


### Forces
- Très bonne discipline de profils (`LIGHT`, `COMPLETE`) et de runtime modes (`LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`).
- La chaîne de promotion est bien pensée : pas de bypass direct du replay local vers le live.
- `protocols` et `monitoring` donnent déjà une base solide pour un produit opérable et auditable.

### Faiblesses
- L’asymétrie d’explicabilité entre modules “gouvernance” et modules “métier” peut compliquer le produit long terme.
- Si les dashboards n’exposent pas les vraies causes, l’organisation enrichit “au ressenti”, ce qui est un risque produit et d’exploitation.

### Verdict fintech
Le système est déjà proche d’un **produit de desk discipliné**, mais pas encore d’un produit où chaque refus/reduction est lisible partout de manière homogène.


## 2.3 Angle développeur / architecture logicielle


### Forces
- Le travail code-first est propre.
- Les packages réels existent et la méthode d’audit refuse l’hallucination structurelle.
- Build-1 est suffisamment robuste pour empêcher une dérive anarchique.

### Faiblesses
- Plusieurs concepts canoniques ne vivent pas comme modules top-level isolés :
  - `microstructure_engine`
  - `regime_engine`
  - `risk_contribution_monitor`
  - `effective_edge_diversity`
  - `live_complete`
- Cela augmente le coût cognitif et le couplage latent.

### Verdict développeur
L’architecture n’est pas sale.
Elle est plutôt **dense et partiellement absorbée**, ce qui rend le futur enrichissement plus difficile à industrialiser sans cartographie très stricte.


## 2.4 Angle mathématique


### Forces
- Les équations utiles sont bien choisies : coût total réel, break-even prudent, CE, budgets cluster/BTC, ranking, variance portefeuille, MRC, K_eff.
- Le canon refuse correctement le Kelly naïf, le RL décoratif et la sophistication non justifiée.

### Faiblesses
- Le système mathématiquement documenté est plus riche que le système mathématiquement **exposé** dans les surfaces d’audit code-first.
- Le sizing prudent (`kelly_guard_prudent`) mérite une projection beaucoup plus visible que son statut actuel.

### Verdict math
Le niveau mathématique canonique est bon.
Le niveau de **projection math -> diagnostic -> dashboard -> décision** n’est pas encore uniforme.


## 2.5 Angle trader / opérateur senior


### Forces
- A = haute conviction.
- B = rotation utile.
- C = breakout distinct.
- D = seconde chance sous mémoire.

La logique économique des moteurs est cohérente.

### Faiblesses
- A peut rester trop “parfait”.
- B peut combattre un vrai move.
- C peut acheter des faux breakouts chers.
- D peut réintroduire une logique émotionnelle si mal encadré.

### Verdict trader
Le danger n’est pas l’absence d’idées.
Le danger est de **promouvoir trop tôt** des idées qui n’ont pas encore prouvé qu’elles améliorent réellement la CE nette après coûts.


## 2.6 Angle senior / PhD / gouvernance de recherche


### Forces
- Le meilleur point de toute la V5.3 est la présence de `meta_learning`, `local_replay_runtime`, `protocols` et `complete_enablers`.
- Cela permet de transformer une intuition en hypothèse gouvernée.

### Faiblesses
- Sans discipline, Build-14 peut devenir une machine à pénaliser.
- Sans rétroaction exécution/data, l’équipe peut sur-travailler l’alpha alors que le vrai problème est ailleurs.

### Verdict senior
Votre architecture est déjà beaucoup plus mûre que beaucoup de projets quant “élégants”.
Le prochain saut de qualité n’est pas un saut d’intelligence brute.
C’est un saut de **causalité, preuve et non-duplication**.


# 3. Scorecard module par module

| Zone | État | Forces | Angle mort principal | Action recommandée |
| --- | --- | --- | --- | --- |
| Build-1 fondations | Fort | Socle contractuel, DAG, smoke/recovery | Ownership stratégique d'une nouvelle stratégie possible sans dette structurelle | Maintenir freeze documentaire et contrats stricts |
| Build-2 data_backbone | Fort | Pipeline réel, pair health, suspension contrôlée | Qualité de flux encore insuffisamment branchée dans scoring/risk/meta | Monter les facts data au rang de causes explicites |
| Build-3 execution_backbone | Fort | Traçabilité ordre/fill/coût/réconciliation | Feedback exécution encore trop peu utilisé pour tuer les faux edges | Réinjecter dans scoring, meta_learning et protocoles |
| Build-4 risk_backbone | Moyen+ | Guards d'exposition, perte, beta, cluster, drawdown | Lineage explicatif encore moins riche que Build-9X/11/14 malgré Lot 1 | Terminer la causalité risk multi-niveaux |
| Build-5 scoring_backbone | Moyen+ | Hard/soft/rank bien séparés, plus explicable depuis Lot 1 | Explication stratégie par stratégie encore inégale | Standardiser les raisons dominantes et la lecture portefeuille |
| Build-6 engine_a | Fort | Moteur premium, modulable, economic-first | Peut sur-détecter si microstructure/régime restent faibles | Brancher Build-14 avec parcimonie |
| Build-7 engine_b | Fort | Moteur de fréquence utile bien défini | Risque de combattre des cassures réelles | Durcir anti-breakout et coût |
| Build-8 portfolio_minimal | Moyen | Sélection/allocation Light réelles | Overlap, diversité effective et contribution au risque pas assez isolés | Rendre le portefeuille beaucoup plus lisible |
| Build-9 meta_minimal | Moyen+ | DTR, CRA, break-even, edge tracking | Moins gouverné que Build-9X | Lier aux hypothèses et diagnostics fins |
| Build-9X meta_learning | Très fort | Meilleure couche de gouvernance et revue | Risque de saturation backlog si trop d'idées mal cadrées | Tout enrichissement doit passer ici |
| Build-10 monitoring/ui | Fort | Système opérable et supervisable | Root cause pas encore partout visible | Projeter raisons à tous les niveaux |
| Build-11/12/13 protocols | Très fort | Vraie machine de preuve et de promotion | Ne doit jamais devenir une zone d'expérimentation diffuse | Conserver la discipline de gates |
| Build-14 complete_enablers | Très fort | Réserve d'enrichissement transverse la plus riche | Peut stériliser si promu trop vite | Mesurer reader-level utility avant influence |
| Build-15 engine_c | Partiel prometteur | Breakout distinct théoriquement utile | Faux breakout, coût, duplication potentielle avec A | Replay/Shadow analytique avant toute promotion |
| Build-16 engine_d | Partiel prometteur | Mémoire de contexte source, seconde chance disciplinée | Risque de revenge trade et de rationalisation ex post | Durcir why_not_A / why_not_entry1 / why_now |
| Build-17 Complete surface | Partiel | UI et surface de supervision pensées | Pas de fermeture runtime isolée complète | Ne pas confondre surface Complete avec readiness Complete |

# 4. Angles morts structurants classés par criticité

| Criticité | Angle mort | Description | Pourquoi c’est dangereux | Correction recommandée |
| --- | --- | --- | --- | --- |
| P0 | Asymétrie de preuve | risk_backbone, scoring_backbone et une partie de portfolio/meta sont moins riches en lineage textuel que Build-9X/11/14. | Difficile de distinguer proprement alpha, coût, pénalité, rejet portefeuille et veto dur. | Finir Lot 1 complet; pousser les reason codes jusque dans meta_learning, replay/import, Pairs et Risk. |
| P0 | Delta canon -> code isolé | microstructure_engine, regime_engine, risk_contribution_monitor, effective_edge_diversity et live_complete ne sont pas toujours des packages top-level isolés. | Couplage caché, audit plus dur, onboarding stratégie plus ambigu. | Créer une cartographie source-of-truth composant -> fichier -> contrat -> projection monitoring. |
| P0 | Rétroaction exécution insuffisante | Les coûts, partial fills, adverse selection et fragilité d'exécution ne rétro-influencent pas encore assez scoring et meta_learning. | On garde des stratégies 'jolies sur replay' mais fragiles en vrai. | Traiter Lot 7 tôt; créer des diagnostics alpha fail vs execution fail. |
| P0 | C et D encore fragiles conceptuellement | C risque de dupliquer A en plus nerveux; D risque le revenge trade automatisé. | Activation Complete prématurée = destruction de CE et de lisibilité. | Ne promouvoir C/D qu'avec preuve de non-duplication et valeur marginale. |
| P0 | Portefeuille partiellement absorbé | Une partie des fonctions canoniques de contribution au risque et de diversité effective vit dans des projections/gates, pas dans des modules clairement isolés. | Le portefeuille peut devenir la zone la moins lisible du système. | Rendre visibles overlap moteurs, MRC, K_eff, clusters, refus relatifs. |
| P1 | Build-14 puissant mais potentiellement stérilisant | Les readers Build-14 sont riches et propres, mais peuvent devenir une couche de pénalisation excessive. | Inflation de prudence, baisse de fréquence utile, illusion d'intelligence. | Mesurer reader par reader: utile, neutre, nocif; limiter au mode READ_ONLY/SHADOW_ENABLED avant promotion. |
| P1 | Data quality pas assez branchée aux décisions | Fraîcheur, gaps, duplications et saturation file d'attente ne sont pas encore assez visibles dans scoring/risk/meta. | Des faux signaux peuvent survivre trop loin dans la chaîne. | Créer des penalties/risk facts explicitement liés aux dégradations data. |
| P1 | Meta minimal moins gouverné que Build-9X | DTR/CRA/BEE existent, mais la gouvernance hypothèse -> replay -> shadow est plus forte dans meta_learning. | Risque de supervision correcte mais apprentissage faible. | Faire de toute nouvelle stratégie un objet Build-9X complet. |
| P1 | Build-17 partiel | La surface Complete existe surtout via enablers, C, D et UI Complete; le runtime live_complete isolé n'est pas fermé. | Le projet peut se croire plus prêt à la Complete qu'il ne l'est. | Considérer Build-17 comme surface de préparation, pas comme fermeture runtime. |
| P1 | Dashboard encore trop centré 'Engine cards' | Les nouveaux reason codes existent mais ne remontent pas encore assez vers Pairs, Risk, Replay & Import. | L'équipe peut continuer à corriger à l'aveugle. | Étendre les projections monitoring multi-niveaux. |
| P2 | Kelly prudent encore plus canonique que réellement exposé | Le canon prévoit `kelly_guard_prudent`, mais sa surface code-first visible n'est pas aussi saillante que les autres guards. | Risque de sizing moins explicable que gross/loss/beta/cluster. | Isoler ou au minimum projeter explicitement la logique de sizing prudent. |
| P2 | Risque de backlog learning | Build-9X a déjà des seuils backlog (`1000`, `5000`) et des protections. | Trop d'hypothèses mal gouvernées peut saturer la chaîne de revue. | Introduire scoring de priorité hypothèse et captures minimales plus agressives. |

# 5. Ce qu’il faut faire maintenant — ordre réellement rentable


## Ordre recommandé
1. **Terminer Lot 1**  
   Finir l’explicabilité risk/scoring jusqu’à `meta_learning`, `Replay & Import`, `Pairs`, `Risk`, `portfolio`.

2. **Exploiter Build-14 reader par reader**  
   Mesurer :
   - utile
   - neutre
   - nocif  
   et fixer un statut :
   - `SHADOW_ENABLED`
   - `READ_ONLY`
   - `LIMITED_INFLUENCE`
   - `DORMANT`

3. **Reconnecter data + exécution au diagnostic**  
   Construire une vraie taxonomie :
   - alpha faux
   - coût > edge
   - stale/gaps
   - partial fill / fragilité
   - rejet portefeuille
   - cluster overcrowding

4. **Durcir A et B avant d’ouvrir davantage C et D**  
   A/B sont déjà votre moteur économique principal.
   Leur enrichissement gouverné rapportera plus qu’une promotion précipitée de C/D.

5. **Rendre le portefeuille enfin pleinement racontable**  
   C’est probablement la prochaine zone à fort rendement d’amélioration, car c’est là que de “bons signaux” deviennent un “mauvais portefeuille”.

6. **Ne traiter C et D qu’en logique de valeur marginale**  
   Toute question sur C ou D doit commencer par :
   - que font-ils que A/B ne font pas déjà ?
   - à quel coût ?
   - avec quel gain marginal de CE ?


# 6. Vingt stratégies de trading pour V5.3

## Règles de conception respectées


- **aucun moteur E/F/G** ;
- classification uniquement dans le canon V5.3 ;
- **spot only / no short / no leverage** ;
- chaque stratégie reste soumise à :
  - `risk_backbone`
  - `scoring_backbone`
  - `portfolio_minimal`
  - `meta_learning`
  - `protocols`
- première validation en `LOCAL_REPLAY`, jamais directement en live.


## Tableau maître des 20 stratégies

| ID | Stratégie | Classe | Profil | Priorité | Thèse économique | Readers / contexte | Angle mort majeur | Validation initiale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Premium Pullback Resume | A_variant | Light/Complete | P0 | Entrer long après un pullback propre dans une tendance déjà validée, quand la structure reste intacte et le coût demeure défendable. | market_toxicity, competition_monitor | Peut acheter un simple rebond technique dans une tendance déjà fatiguée. | LOCAL_REPLAY -> SHADOW Light sur BTC/ETH/BNB/SOL |
| A2 | Compression Release Trend | A_variant | Light/Complete | P0 | Capter les sorties de compression qui ne sont pas encore des breakouts 'nerveux' de type C, mais des relances propres de tendance. | order_book_imbalance, lob_deep_filter_vwa | Glisse facilement vers un faux breakout si la microstructure ment. | Replay comparatif A pur vs A enrichi par readers Build-14 |
| A3 | Leader Pair Trend Follow | A_variant | Light/Complete | P1 | Prioriser les paires leaders de classes A/B quand leur qualité data, leur coût et leur contexte concurrence/toxicité sont supérieurs au reste de l'univers. | competition_monitor, market_toxicity | Peut concentrer excessivement le portefeuille sur le facteur BTC. | Replay portefeuille avec contrôle beta/cluster |
| A4 | Regime-Confirmed Trend Persistence | A_variant | Light/Complete | P1 | Renforcer A seulement quand la persistance de régime est favorable, pour éviter les faux débuts de tendance. | hurst_regime_classifier | Peut sur-filtrer et retomber dans la stérilité V5.2. | Analyse de trade-off fréquence utile vs CE nette |
| A5 | Low-Toxicity Expansion Rider | A_variant | Light/Complete | P1 | N'autoriser les expansions agressives de A que si la toxicité marché et la fragilité d'exécution restent sous contrôle. | market_toxicity, execution_fragility | Peut rater des moves explosifs mais monétisables. | Replay + segmentation des échecs coût > edge |
| B1 | Range Edge Mean Reversion | B_variant | Light/Complete | P0 | Acheter les excès locaux en bas de range quand la structure ne montre pas de vraie cassure hostile. | hurst_regime_classifier | Devient un attrape-couteau si le range est déjà cassé. | Shadow Light sur SOL/XRP/ADA/LINK |
| B2 | VWAP/Microprice Reclaim Reversion | B_variant | Light/Complete | P1 | Entrer sur réversion seulement quand le prix réintègre une zone VWAP/microprice cohérente après excès. | lob_deep_filter_vwa, order_book_imbalance | Dépend fortement de la qualité LOB et du bruit microstructure. | Replay microstructure-fidelity sur paires les plus liquides |
| B3 | Liquidity Sweep Snapback | B_variant | Light/Complete | P1 | Exploiter un flush court de liquidité suivi d'un retour rapide dans le range local. | market_toxicity, execution_fragility | Le flush peut être le début d'une vraie continuation baissière. | Replay + classification near-miss dans meta_learning |
| B4 | Order-Book Exhaustion Reversion | B_variant | Light/Complete | P1 | Prendre une réversion quand l'imbalance carnet signale une exhaustion plutôt qu'une continuation. | order_book_imbalance, competition_monitor | Très sensible au spoofing et aux données L2 imparfaites. | Replay reader-level puis SHADOW_ENABLED seulement |
| B5 | Failed Breakout Fade | B_variant | Light/Complete | P0 | Fader une tentative de cassure avortée et jouer le retour à la moyenne locale plutôt que la continuation. | false_breakout_model, hurst_regime_classifier | La 'fausse cassure' peut n'être qu'une pause avant reprise explosive. | Replay A/B/C interactions + suivi coût réel prudent |
| C1 | Classic Compression Breakout | C_candidate | Complete only | P1 | Acheter la sortie de compression/range avec confirmation de poursuite encore exploitable. | false_breakout_model, lob_deep_filter_vwa | Le moteur le plus exposé aux faux breakouts et au coût. | LOCAL_REPLAY Complete puis SHADOW analytique uniquement |
| C2 | OBI-Confirmed Breakout Continuation | C_candidate | Complete only | P1 | Ne garder que les cassures où l'order-book imbalance et la profondeur confirment réellement la poursuite. | order_book_imbalance, lob_deep_filter_vwa, execution_fragility | Peut devenir trop sélectif et perdre sa fréquence marginale. | Test gain marginal vs C nu et vs A |
| C3 | Post-Breakout Pullback Continuation | C_candidate | Complete only | P1 | Entrer non pas sur la première bougie de cassure, mais sur le premier pullback valide post-breakout. | false_breakout_model, market_toxicity | Peut basculer conceptuellement dans A si mal borné. | Audit de non-duplication A/C obligatoire |
| C4 | Cross-Timeframe Range Escape | C_candidate | Complete only | P2 | Capturer les échappées de range alignées entre micro-structure et structure supérieure. | hurst_regime_classifier, competition_monitor | Complexité élevée et risque de sur-fit régime/timeframe. | Replay long historique + stress tests sur faux signaux |
| C5 | Crowding-Squeeze Breakout | C_candidate | Complete only | P2 | Jouer les breakouts où la compétition/crowding augmente mais reste encore monétisable avant saturation du move. | competition_monitor, market_toxicity | Peut acheter la fin du move si le crowding arrive trop tard. | Reader-by-reader evidence puis SHADOW_ENABLED uniquement |
| D1 | Missed Entry Second Chance | D_candidate | Complete only | P1 | Réengager un move initial valide quand l'entrée 1 a été manquée mais que la structure se reforme proprement. | hurst_regime_classifier | Très proche d'un simple retard d'A si la frontière est mal définie. | Analyse explicite why_not_A + valeur marginale de D |
| D2 | Execution-Failed Re-entry | D_candidate | Complete only | P1 | Réentrer seulement quand le premier échec provient surtout de l'exécution (fill raté, coût, timeout) et non d'un alpha faux. | execution_fragility | Peut réinsister dans un environnement structurellement mauvais. | Segmentation stricte alpha fail vs execution fail |
| D3 | Regime-Improvement Re-entry | D_candidate | Complete only | P2 | Réengager un signal initial dégradé si le régime s'améliore objectivement après une phase d'hésitation. | hurst_regime_classifier, competition_monitor | Risque de rationaliser ex post un mauvais trade abandonné. | Replay avec liens origin_context_id / origin_trade_id |
| D4 | False-Abandon Re-entry | D_candidate | Complete only | P2 | Réouvrir après une sortie ou un abandon prématuré alors que la structure de continuation demeure saine. | market_toxicity, false_breakout_model | Peut devenir un moteur émotionnel automatisé si les diagnostics sont pauvres. | Meta_learning obligatoire avec tag 'faux abandon' |
| D5 | Partial-Exit Continuation Re-entry | D_candidate | Complete only | P2 | Réengager partiellement après prise de profit initiale quand le marché reforme un setup encore rentable. | execution_fragility, competition_monitor | Augmente facilement la concentration thème/cluster. | Test portefeuille: cluster, beta BTC, contribution au risque |

## Détail de chaque stratégie


### A1 — Premium Pullback Resume

- **Classification** : `A_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P0
- **Thèse** : Entrer long après un pullback propre dans une tendance déjà validée, quand la structure reste intacte et le coût demeure défendable.
- **Modules principaux** : engine_a, scoring_backbone, risk_backbone, execution_backbone
- **Readers / enrichissements utiles** : market_toxicity, competition_monitor
- **Source d’edge recherchée** : Continuation haute conviction avec meilleur prix d'entrée que la cassure initiale.
- **Angle mort principal** : Peut acheter un simple rebond technique dans une tendance déjà fatiguée.
- **Premier chemin de validation** : LOCAL_REPLAY -> SHADOW Light sur BTC/ETH/BNB/SOL
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### A2 — Compression Release Trend

- **Classification** : `A_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P0
- **Thèse** : Capter les sorties de compression qui ne sont pas encore des breakouts 'nerveux' de type C, mais des relances propres de tendance.
- **Modules principaux** : engine_a, data_backbone, scoring_backbone
- **Readers / enrichissements utiles** : order_book_imbalance, lob_deep_filter_vwa
- **Source d’edge recherchée** : Accéder plus tôt au move que A classique tout en restant dans une logique premium.
- **Angle mort principal** : Glisse facilement vers un faux breakout si la microstructure ment.
- **Premier chemin de validation** : Replay comparatif A pur vs A enrichi par readers Build-14
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### A3 — Leader Pair Trend Follow

- **Classification** : `A_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : Prioriser les paires leaders de classes A/B quand leur qualité data, leur coût et leur contexte concurrence/toxicité sont supérieurs au reste de l'univers.
- **Modules principaux** : engine_a, portfolio_minimal, monitoring
- **Readers / enrichissements utiles** : competition_monitor, market_toxicity
- **Source d’edge recherchée** : Meilleure capital efficiency par sélection de leaders plutôt que dispersion naïve.
- **Angle mort principal** : Peut concentrer excessivement le portefeuille sur le facteur BTC.
- **Premier chemin de validation** : Replay portefeuille avec contrôle beta/cluster
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### A4 — Regime-Confirmed Trend Persistence

- **Classification** : `A_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : Renforcer A seulement quand la persistance de régime est favorable, pour éviter les faux débuts de tendance.
- **Modules principaux** : engine_a, scoring_backbone, meta_learning
- **Readers / enrichissements utiles** : hurst_regime_classifier
- **Source d’edge recherchée** : Moins de faux départs, meilleur filtrage des tendances bruitées.
- **Angle mort principal** : Peut sur-filtrer et retomber dans la stérilité V5.2.
- **Premier chemin de validation** : Analyse de trade-off fréquence utile vs CE nette
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### A5 — Low-Toxicity Expansion Rider

- **Classification** : `A_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : N'autoriser les expansions agressives de A que si la toxicité marché et la fragilité d'exécution restent sous contrôle.
- **Modules principaux** : engine_a, execution_backbone, complete_enablers
- **Readers / enrichissements utiles** : market_toxicity, execution_fragility
- **Source d’edge recherchée** : Réduit les entrées premium détruites par les coûts cachés.
- **Angle mort principal** : Peut rater des moves explosifs mais monétisables.
- **Premier chemin de validation** : Replay + segmentation des échecs coût > edge
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### B1 — Range Edge Mean Reversion

- **Classification** : `B_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P0
- **Thèse** : Acheter les excès locaux en bas de range quand la structure ne montre pas de vraie cassure hostile.
- **Modules principaux** : engine_b, scoring_backbone, risk_backbone
- **Readers / enrichissements utiles** : hurst_regime_classifier
- **Source d’edge recherchée** : Fréquence utile élevée sur marchés latéraux propres.
- **Angle mort principal** : Devient un attrape-couteau si le range est déjà cassé.
- **Premier chemin de validation** : Shadow Light sur SOL/XRP/ADA/LINK
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### B2 — VWAP/Microprice Reclaim Reversion

- **Classification** : `B_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : Entrer sur réversion seulement quand le prix réintègre une zone VWAP/microprice cohérente après excès.
- **Modules principaux** : engine_b, data_backbone, execution_backbone
- **Readers / enrichissements utiles** : lob_deep_filter_vwa, order_book_imbalance
- **Source d’edge recherchée** : Améliore la qualité des reversions courtes et réduit les signaux trop tôt.
- **Angle mort principal** : Dépend fortement de la qualité LOB et du bruit microstructure.
- **Premier chemin de validation** : Replay microstructure-fidelity sur paires les plus liquides
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### B3 — Liquidity Sweep Snapback

- **Classification** : `B_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : Exploiter un flush court de liquidité suivi d'un retour rapide dans le range local.
- **Modules principaux** : engine_b, execution_backbone, meta_minimal
- **Readers / enrichissements utiles** : market_toxicity, execution_fragility
- **Source d’edge recherchée** : Très bon rapport durée/rotation du capital quand le flush est exagéré.
- **Angle mort principal** : Le flush peut être le début d'une vraie continuation baissière.
- **Premier chemin de validation** : Replay + classification near-miss dans meta_learning
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### B4 — Order-Book Exhaustion Reversion

- **Classification** : `B_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P1
- **Thèse** : Prendre une réversion quand l'imbalance carnet signale une exhaustion plutôt qu'une continuation.
- **Modules principaux** : engine_b, complete_enablers, scoring_backbone
- **Readers / enrichissements utiles** : order_book_imbalance, competition_monitor
- **Source d’edge recherchée** : Ajoute une lecture fine de l'épuisement, utile sur paires leaders.
- **Angle mort principal** : Très sensible au spoofing et aux données L2 imparfaites.
- **Premier chemin de validation** : Replay reader-level puis SHADOW_ENABLED seulement
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### B5 — Failed Breakout Fade

- **Classification** : `B_variant`
- **Profil visé** : Light/Complete
- **Priorité** : P0
- **Thèse** : Fader une tentative de cassure avortée et jouer le retour à la moyenne locale plutôt que la continuation.
- **Modules principaux** : engine_b, complete_enablers, meta_learning
- **Readers / enrichissements utiles** : false_breakout_model, hurst_regime_classifier
- **Source d’edge recherchée** : Très compatible avec la philosophie B si le faux breakout est objectivé.
- **Angle mort principal** : La 'fausse cassure' peut n'être qu'une pause avant reprise explosive.
- **Premier chemin de validation** : Replay A/B/C interactions + suivi coût réel prudent
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### C1 — Classic Compression Breakout

- **Classification** : `C_candidate`
- **Profil visé** : Complete only
- **Priorité** : P1
- **Thèse** : Acheter la sortie de compression/range avec confirmation de poursuite encore exploitable.
- **Modules principaux** : engine_c, scoring_backbone, execution_backbone
- **Readers / enrichissements utiles** : false_breakout_model, lob_deep_filter_vwa
- **Source d’edge recherchée** : Fréquence additionnelle distincte de A sur expansions courtes.
- **Angle mort principal** : Le moteur le plus exposé aux faux breakouts et au coût.
- **Premier chemin de validation** : LOCAL_REPLAY Complete puis SHADOW analytique uniquement
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### C2 — OBI-Confirmed Breakout Continuation

- **Classification** : `C_candidate`
- **Profil visé** : Complete only
- **Priorité** : P1
- **Thèse** : Ne garder que les cassures où l'order-book imbalance et la profondeur confirment réellement la poursuite.
- **Modules principaux** : engine_c, complete_enablers, execution_backbone
- **Readers / enrichissements utiles** : order_book_imbalance, lob_deep_filter_vwa, execution_fragility
- **Source d’edge recherchée** : Réduit la duplication d'A en rendant C plus spécifique.
- **Angle mort principal** : Peut devenir trop sélectif et perdre sa fréquence marginale.
- **Premier chemin de validation** : Test gain marginal vs C nu et vs A
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### C3 — Post-Breakout Pullback Continuation

- **Classification** : `C_candidate`
- **Profil visé** : Complete only
- **Priorité** : P1
- **Thèse** : Entrer non pas sur la première bougie de cassure, mais sur le premier pullback valide post-breakout.
- **Modules principaux** : engine_c, risk_backbone, portfolio_minimal
- **Readers / enrichissements utiles** : false_breakout_model, market_toxicity
- **Source d’edge recherchée** : Meilleur coût d'entrée et meilleure lisibilité d'invalidation.
- **Angle mort principal** : Peut basculer conceptuellement dans A si mal borné.
- **Premier chemin de validation** : Audit de non-duplication A/C obligatoire
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### C4 — Cross-Timeframe Range Escape

- **Classification** : `C_candidate`
- **Profil visé** : Complete only
- **Priorité** : P2
- **Thèse** : Capturer les échappées de range alignées entre micro-structure et structure supérieure.
- **Modules principaux** : engine_c, data_backbone, scoring_backbone
- **Readers / enrichissements utiles** : hurst_regime_classifier, competition_monitor
- **Source d’edge recherchée** : Réduit les cassures locales qui n'ont pas de relais structurel.
- **Angle mort principal** : Complexité élevée et risque de sur-fit régime/timeframe.
- **Premier chemin de validation** : Replay long historique + stress tests sur faux signaux
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### C5 — Crowding-Squeeze Breakout

- **Classification** : `C_candidate`
- **Profil visé** : Complete only
- **Priorité** : P2
- **Thèse** : Jouer les breakouts où la compétition/crowding augmente mais reste encore monétisable avant saturation du move.
- **Modules principaux** : engine_c, complete_enablers, meta_learning
- **Readers / enrichissements utiles** : competition_monitor, market_toxicity
- **Source d’edge recherchée** : Cherche un edge de squeeze/crowding absent d'A.
- **Angle mort principal** : Peut acheter la fin du move si le crowding arrive trop tard.
- **Premier chemin de validation** : Reader-by-reader evidence puis SHADOW_ENABLED uniquement
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### D1 — Missed Entry Second Chance

- **Classification** : `D_candidate`
- **Profil visé** : Complete only
- **Priorité** : P1
- **Thèse** : Réengager un move initial valide quand l'entrée 1 a été manquée mais que la structure se reforme proprement.
- **Modules principaux** : engine_d, meta_learning, portfolio_minimal
- **Readers / enrichissements utiles** : hurst_regime_classifier
- **Source d’edge recherchée** : Monétise des cas où A avait raison trop tôt sans lancer un nouveau moteur autonome.
- **Angle mort principal** : Très proche d'un simple retard d'A si la frontière est mal définie.
- **Premier chemin de validation** : Analyse explicite why_not_A + valeur marginale de D
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### D2 — Execution-Failed Re-entry

- **Classification** : `D_candidate`
- **Profil visé** : Complete only
- **Priorité** : P1
- **Thèse** : Réentrer seulement quand le premier échec provient surtout de l'exécution (fill raté, coût, timeout) et non d'un alpha faux.
- **Modules principaux** : engine_d, execution_backbone, meta_learning
- **Readers / enrichissements utiles** : execution_fragility
- **Source d’edge recherchée** : Exploite la mémoire transactionnelle propre à V5.3.
- **Angle mort principal** : Peut réinsister dans un environnement structurellement mauvais.
- **Premier chemin de validation** : Segmentation stricte alpha fail vs execution fail
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### D3 — Regime-Improvement Re-entry

- **Classification** : `D_candidate`
- **Profil visé** : Complete only
- **Priorité** : P2
- **Thèse** : Réengager un signal initial dégradé si le régime s'améliore objectivement après une phase d'hésitation.
- **Modules principaux** : engine_d, scoring_backbone, meta_learning
- **Readers / enrichissements utiles** : hurst_regime_classifier, competition_monitor
- **Source d’edge recherchée** : Utile pour des moves qui passent de neutres à favorables sans nouveau point zéro.
- **Angle mort principal** : Risque de rationaliser ex post un mauvais trade abandonné.
- **Premier chemin de validation** : Replay avec liens origin_context_id / origin_trade_id
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### D4 — False-Abandon Re-entry

- **Classification** : `D_candidate`
- **Profil visé** : Complete only
- **Priorité** : P2
- **Thèse** : Réouvrir après une sortie ou un abandon prématuré alors que la structure de continuation demeure saine.
- **Modules principaux** : engine_d, meta_minimal, execution_backbone
- **Readers / enrichissements utiles** : market_toxicity, false_breakout_model
- **Source d’edge recherchée** : Répare des sorties trop prudentes sans surtrader.
- **Angle mort principal** : Peut devenir un moteur émotionnel automatisé si les diagnostics sont pauvres.
- **Premier chemin de validation** : Meta_learning obligatoire avec tag 'faux abandon'
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

### D5 — Partial-Exit Continuation Re-entry

- **Classification** : `D_candidate`
- **Profil visé** : Complete only
- **Priorité** : P2
- **Thèse** : Réengager partiellement après prise de profit initiale quand le marché reforme un setup encore rentable.
- **Modules principaux** : engine_d, portfolio_minimal, risk_backbone
- **Readers / enrichissements utiles** : execution_fragility, competition_monitor
- **Source d’edge recherchée** : Améliore l'utilisation du capital sur moves persistants sans forcer Tier 3.
- **Angle mort principal** : Augmente facilement la concentration thème/cluster.
- **Premier chemin de validation** : Test portefeuille: cluster, beta BTC, contribution au risque
- **Safeguards obligatoires** : passer par `meta_learning`, exporter un evidence bundle, contrôler coût réel prudent, cluster/BTC budget, et vérifier la non-duplication avec les autres moteurs.

# 7. Priorisation réelle des 20 stratégies


## Vague 1 — à travailler d’abord
- `A1 Premium Pullback Resume`
- `A2 Compression Release Trend`
- `B1 Range Edge Mean Reversion`
- `B5 Failed Breakout Fade`
- `A5 Low-Toxicity Expansion Rider`
- `B2 VWAP/Microprice Reclaim Reversion`

**Pourquoi :**  
Ce sont les meilleures idées pour améliorer la V5.3 **sans changer de profil** et sans dépendre de la fermeture Complete.

## Vague 2 — enrichissements A/B plus fins
- `A3 Leader Pair Trend Follow`
- `A4 Regime-Confirmed Trend Persistence`
- `B3 Liquidity Sweep Snapback`
- `B4 Order-Book Exhaustion Reversion`

**Pourquoi :**  
Elles exploitent mieux Build-14 et le feedback execution, mais exigent une meilleure causalité reader-level.

## Vague 3 — C candidats
- `C1`
- `C2`
- `C3`

**Pourquoi :**  
Ce sont les trois candidats C les plus défendables.
Ils doivent prouver :
- non-duplication avec A
- CE nette défendable
- faux breakout sous contrôle

`C4` et `C5` sont intéressants mais clairement **P2**.

## Vague 4 — D candidats
- `D1`
- `D2`

**Pourquoi :**  
Ce sont les seuls D qui ont une justification immédiatement intelligible :
- entrée manquée mais structure intacte
- échec d’exécution et non échec d’alpha

`D3`, `D4`, `D5` sont plus riches mais plus dangereux conceptuellement.


# 8. Matrice d’onboarding recommandée pour toute nouvelle stratégie

| Étape | Action | Exigence | Règle de refus |
| --- | --- | --- | --- |
| 1 | Classifier | A_variant / B_variant / C_candidate / D_candidate | Refuser tout code avant classification |
| 2 | Versionner | strategy_version, feature_set_version, formula_set_version, scoring_version, regime_version, risk_policy_version, cost_model_version | Aucune logique décisive non versionnée |
| 3 | Intégrer shared core | Pas de script local libre, pas de plugin VPS | Même logique locale et VPS |
| 4 | Tester en LOCAL_REPLAY | Evidence bundle, DTR, metrics, comparaison baseline | Pas de promotion implicite |
| 5 | Importer sur VPS | Import gouverné, projection UI/Meta/Monitoring | Import != exécution |
| 6 | Observer en SHADOW | Reader-level, engine-level, pair-level | Pas de live tant que preuve insuffisante |
| 7 | Décider promotion | Replay-only / Shadow-ready / Micro-live-ready / Live-light-ready | Promotion selon protocols seulement |

# 9. Go / No-Go final


## GO
- **GO** pour produire maintenant un backlog exécutable de **20 stratégies gouvernées**.
- **GO** pour démarrer immédiatement :
  - variantes A/B,
  - exploitation Build-14,
  - boucle data/execution -> diagnostics,
  - explicabilité complète risk/scoring.

## NO-GO
- **NO-GO** pour une promotion directe live des nouvelles stratégies.
- **NO-GO** pour tout moteur supplémentaire hors A/B/C/D.
- **NO-GO** pour toute ouverture Complete basée sur l’intuition que “la surface existe déjà”.
- **NO-GO** pour C/D tant que la valeur marginale n’est pas démontrée.

## Formulation la plus honnête
La V5.3 n’a pas un problème de manque d’idées.
Elle a un problème beaucoup plus subtil et plus important :

> **transformer les bonnes idées en stratégies causalement prouvées, non dupliquées, économiquement défendables, et opérables sans aveuglement.**

C’est exactement là que votre prochain travail doit se concentrer.
