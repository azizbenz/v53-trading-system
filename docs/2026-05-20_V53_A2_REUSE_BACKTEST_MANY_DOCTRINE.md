# V5.3 Build Data Once, Backtest Many

Date: 2026-05-20

## Objet

Ce document fixe la cible d'exploitation suivante:

- `A1 -> A2` servent a construire un corpus de donnees gouverne
- `B1 -> B2` servent a lancer des backtests/replays sur ce corpus
- une fois `A2` stabilise, on ne doit plus rerunner `A1/A2` pour chaque backtest

L'objectif est:

- de payer le cout data une seule fois
- de figer la verite des donnees
- puis d'iterer vite sur les fenetres, policies et hypotheses de backtest

## Doctrine cible

### 1. Dataset build workflow

Le workflow `A1 -> A2` devient un workflow de fabrication de dataset.

Il produit un package gouverne reutilisable:

- `silver_index.json`
- `gold/`
- `gold_feature_manifest.json`
- `raw_source_manifest.json`
- `data_factory_manifest.json`
- `data_quality_report.json`
- manifests de provenance / parite / drift utiles au cockpit

Ce package doit etre traite comme un artefact versionne, pas comme un simple sous-produit jetable.

### 2. Backtest workflow

Le workflow `B1 -> B2` devient un workflow d'experimentation/replay.

Il doit consommer un `A2` deja valide via:

- `feature_store_root`
- `silver_index_path`
- `raw_source_manifest_path`
- la fenetre a tester
- les knobs de replay (`ML mode`, policy mode, sample cap, engines, pairs)

Le backtest ne doit pas reconstruire la data factory si la base canonique existe deja et est compatible.

## Ce que signifie "A2 stabilise"

On peut arreter de rerunner `A1/A2` pour chaque backtest seulement si les conditions suivantes sont vraies:

1. `A2` est temporellement sain sur les timeframes critiques
- pas de blocage `OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED`
- pas de blocage `OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED`

2. `A2` expose une provenance explicite
- `raw_source_manifest_path` non vide
- `raw_source_provenance_status` renseigne
- `raw_source_typing_status` remonte au top-level

3. `A2` porte ses limites doctrinales explicitement
- `CURRENT_METADATA_PROXY`
- `RAW_SOURCE_TYPE_INFERRED`
- `SINGLE_PAIR_RESEARCH_ONLY`
- autres blockers research-only visibles dans les manifests et le cockpit

4. `B1/B2` savent consommer `A2` sans perdre la lineage
- `raw_source_manifest_path` survive jusqu'aux `run_manifest.json`
- `candidate_replay_windows` exposent les chemins reels utilises
- les refs de phase restent stables et non ambigues

5. les couts runtime restent soutenables
- pas de duplication explosive des `orderbook_delta`
- partage des fenetres la ou il est causalement valide
- telemetry de performance fiable

Tant que ces conditions ne sont pas vraies, `A1/A2` reste un chantier actif et ne doit pas encore etre traite comme une base canonique reusable.

## Contrat minimal de reutilisation

Quand `A2` est juge stable, le contrat de reutilisation est:

1. Un dataset `A2` est identifie par son dossier workflow ou son manifest canonique.
2. Les futurs `B1/B2` prennent ce dataset en entree.
3. Changer une fenetre de backtest ne force pas un nouveau `A2`.
4. Changer une policy `B1/B2`, un `ML mode`, ou un echantillon de replay ne force pas un nouveau `A2`.
5. On ne regenere `A2` que si la verite data a change:
- nouvelles dates couvertes
- correction de bronze/silver/gold
- nouvelle provenance
- nouvelle schema policy
- nouvelle validation doctrinale

## Benefices attendus

Si cette cible est atteinte:

- les runs `B1/B2` deviennent beaucoup plus rapides
- les comparaisons `ML off` vs `ML on` deviennent propres
- les audits deviennent reproductibles
- on evite de melanger bugs data et bugs replay
- on peut tester plusieurs echantillons/fenetres sans repayer toute la chaine data

## Risques si on le fait trop tot

Il ne faut pas passer en mode `build once / backtest many` trop tot.

Sinon:

- on fige un dataset incomplet ou biaise
- on propage une mauvaise verite temporelle dans tous les backtests
- on gagne du temps de calcul mais on perd la validite scientifique

Le mode cible est donc:

- `A2` rare, mais seulement apres stabilisation reelle
- `B1/B2` frequents, rapides, et adosses a ce `A2`

## Decision pratique pour la suite

La feuille de route immediate est:

1. continuer l'audit data jusqu'a stabiliser `A2`
2. fermer les derniers angles morts de provenance / temporalite / duplication runtime
3. seulement ensuite officialiser un dataset `A2` reusable
4. puis passer a un regime:
- `dataset build once`
- `backtest many`

## Statut a date

Statut actuel:

- doctrine valide
- implementation pas encore completement eligible

Raison:

- le principe est juste
- mais les derniers audits montrent encore des blockers data/runtime qui empechent de declarer `A2` completement stable comme verite canonique
