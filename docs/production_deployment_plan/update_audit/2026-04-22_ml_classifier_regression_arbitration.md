## 2026-04-22 — ML classifier vs regression arbitration

### Scope
- `src/calibration_methods/ml_trainer.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/interface_contracts/ml_backtest_training_contracts.py`
- `src/local_replay_runtime/ml_backtest_projection.py`
- `docs/production_deployment_plan/V5_3_CODEX_ML_ENABLER_MD1.md`
- `docs/production_deployment_plan/V5_3_CODEX_ML_ENABLER_SPEC_FULL_V2.md`
- `docs/production_deployment_plan/V5_3_CODEX_ML_ENABLER_CANON_SCIENTIFIQUE_V1.md`

### Question
Le modèle canonique doit-il être un `classifier` ou une `regression` pour la V1 prod-safe du ML enabler ?

### Evidence reviewed
- Les MD ML demandent un **LightGBM classifier** et définissent `ml_confidence` comme une probabilité de follow-through favorable.
- Le code actuel entraîne un LightGBM avec `objective = "regression"` sur une cible continue `target_return_fraction`.
- Le runtime consomme ensuite la prédiction comme un `ml_confidence` borné à `[0,1]`, avec neutralité à `0.5`.
- Le dataset repo-truth actuel est structuré autour de `projected_net_return_bps` / `realized_net_return_bps`, pas autour d'un label binaire déjà fermé avec horizon et marge canonique.

### Hard conclusion
Le repo ne permet **pas encore** de canoniser honnêtement `classifier` ou `regression` comme vérité finale V1.

### What is already scientifically rejectable
La chaîne actuelle suivante n'est **pas** une sémantique finale prod-safe :

`target continu net-return -> LightGBM regression -> clipping [0,1] -> ml_confidence`

Raison :
- une sortie de régression continue n'est pas une probabilité par construction
- la neutralité runtime à `0.5` n'est pas démontrée par le training actuel
- le clipping masque l'erreur de sémantique au lieu de la résoudre

### Safe verdict
- `classifier`: **not yet closed**
  - acceptable seulement si le label binaire, l'horizon et la marge nette sont figés mathématiquement
- `regression`: **not yet closed**
  - acceptable seulement si le runtime renonce au vocabulaire probabiliste ou ajoute une calibration explicite et testée

### Operational rule from this arbitration
Tant que ce point n'est pas fermé :
- le trainer ML reste doctrinalement **provisoire**
- le ML enabler reste **additif et non promouvable** comme couche de confiance canonique
- la promotion doit rester fail-closed

### Next safe decision slice
Trancher l'une des deux voies suivantes :

1. **Voie classifier**
- définir le label binaire canonique
- définir l'horizon canonique par moteur ou par slice
- définir la marge nette canonique
- recoder le trainer et les tests autour d'une vraie probabilité

2. **Voie regression**
- assumer explicitement une cible de retour net
- renommer la sortie runtime pour qu'elle ne prétende plus être une probabilité
- ou insérer une calibration explicite et auditée entre sortie modèle et `ml_confidence`

### Status
- Final verdict: `UNKNOWN_FINAL_FORMALISM`
- Unsafe shortcut rejected: `REGRESSION_CLIPPED_AS_CONFIDENCE`
