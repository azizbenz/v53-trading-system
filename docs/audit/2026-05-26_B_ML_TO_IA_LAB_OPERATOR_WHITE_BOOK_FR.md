# White Book Operateur FR - B_ML vers IA Lab

Statut: `B_ML_TO_IA_LAB_OPERATOR_GUIDE_READY`

## 1. Objet

Ce document explique, en francais operateur, quoi faire **apres un run B_ML**:

1. comment verifier que B_ML a produit un dataset entrainable,
2. comment lancer ensuite l'IA Lab,
3. quelle methode est possible depuis le cockpit aujourd'hui,
4. quelle methode exige encore le CLI,
5. quoi verifier pour ne pas confondre:
   - B_ML,
   - IA Lab handoff,
   - backtest avec frozen ML.

Il est aligne sur le code courant de:

- [run_strategy_ladder_b_ml_label_factory.py](</E:/claude  v5.3/v53_trading_system/scripts/run_strategy_ladder_b_ml_label_factory.py>)
- [run_strategy_ladder_ml_lab_handoff.py](</E:/claude  v5.3/v53_trading_system/scripts/run_strategy_ladder_ml_lab_handoff.py>)
- [train_strategy_ladder_expected_edge_artifact.py](</E:/claude  v5.3/v53_trading_system/scripts/train_strategy_ladder_expected_edge_artifact.py>)
- [server.py](</E:/claude  v5.3/v53_trading_system/src/cockpit/server.py>)

## 2. Difference entre B_ML et IA Lab

Il faut separer clairement les 2 choses.

### B_ML

B_ML fabrique un dataset de training:

```text
A2 gold ex-ante features
-> B_ML sampler
-> labels post-decision
-> labels/b_ml_label_store.jsonl
-> rapports de fuite / eligibilite / fidelite
```

B_ML ne fait pas:

- de trading live,
- de trade force,
- de patch seuil,
- de truth expected-edge en production,
- de remplacement des engines A/B/C/D.

### IA Lab

IA Lab entraine ensuite un artifact ML expected-edge a partir:

- soit du rail legacy kline-only,
- soit d'un rail replay-grounded,
- soit d'un `label_store_dataset_path` deja construit.

Donc:

- **B_ML produit le dataset**
- **IA Lab entraine le modele**

## 3. Ce qu'il faut verifier apres B_ML

Un run B_ML n'est pas "bon" juste parce qu'il a fini.

Verifier au minimum:

- `labels/b_ml_label_store.jsonl`
- `labels/b_ml_label_summary.json`
- `labels/b_ml_target_policy_report.json`
- `reports/b_ml_training_dataset_audit.json`
- `reports/b_ml_training_row_eligibility_report.json`
- `reports/b_ml_feature_label_leakage_report.json`
- `reports/b_ml_final_verdict.json`

### Conditions minimales

Le dataset B_ML est entrainable si, au minimum:

- `training_allowed = true`
- `training_row_eligible_count > 0`
- `feature_leakage_count = 0`
- `target_policy_mismatch_count = 0`
- `train_eval_overlap_blocked = false`

### Verdict a lire

Les verdicts utiles sont:

- `BML_READY_GOVERNED`
- `BML_READY_RESEARCH`

Si le verdict final n'est ni l'un ni l'autre, ne pas lancer le training IA Lab comme si le dataset etait propre.

## 4. Deux manieres de lancer IA Lab apres B_ML

Il existe aujourd'hui **deux rails**.

### Rail A - Cockpit /lab actuel

C'est le rail UI officiellement expose aujourd'hui.

Il passe par:

- `POST /lab/strategy-ladder-ml-handoff`
- script [run_strategy_ladder_ml_lab_handoff.py](</E:/claude  v5.3/v53_trading_system/scripts/run_strategy_ladder_ml_lab_handoff.py>)

Ce rail expose dans le formulaire:

- `kline_root`
- `b2_run_root`
- `pair`
- `timeframe`
- `train_start`
- `train_end`
- `feature_names`

Mais **il n'expose pas encore directement** un champ:

```text
label_store_dataset_path
```

Donc:

- oui, le backend de training sait consommer un label store B_ML,
- non, le cockpit IA Lab standard ne propose pas encore ce champ en UI.

### Rail B - CLI direct sur le label store B_ML

C'est le rail le plus direct si tu veux entrainer **exactement sur la sortie B_ML**.

Il passe par:

- [train_strategy_ladder_expected_edge_artifact.py](</E:/claude  v5.3/v53_trading_system/scripts/train_strategy_ladder_expected_edge_artifact.py>)

Ce script expose:

- `--label-store-dataset-path`

Donc c'est lui qui permet aujourd'hui de dire explicitement:

```text
entraine le modele a partir de labels/b_ml_label_store.jsonl
```

## 5. Reponse courte a la question operateur

### "Apres B_ML, comment on lance IA Lab ?"

La reponse exacte est:

1. **si tu veux rester 100% cockpit UI**, tu vas dans la page **IA Lab** et tu lances le handoff ML standard;
2. **si tu veux reutiliser explicitement le dataset B_ML produit**, aujourd'hui le chemin explicite est le **CLI** avec `--label-store-dataset-path`.

Autrement dit:

- **Cockpit IA Lab actuel**: oui
- **Cockpit IA Lab direct sur `b_ml_label_store.jsonl`**: pas encore
- **CLI direct sur `b_ml_label_store.jsonl`**: oui

## 6. Flow recommande

### Cas 1 - Tu veux un flow cockpit simple

Utilise ce flow:

```text
1. A1 preview
2. A2 data factory
3. B1 si tu veux des candidats natifs
4. B_ML label factory
5. verifier que B_ML est training-ready
6. aller sur /lab
7. lancer Strategy Ladder ML handoff
8. recuperer l'artifact frozen
9. revenir sur /backtest avec ML_MODE_OVERLAY_FROZEN
```

Limite:

- ce rail cockpit ne "pointe" pas explicitement le champ `label_store_dataset_path`.

### Cas 2 - Tu veux entrainer exactement sur la sortie B_ML

Utilise ce flow:

```text
1. A1
2. A2
3. B_ML
4. verifier training_allowed=true
5. lancer train_strategy_ladder_expected_edge_artifact.py
   avec --label-store-dataset-path labels/b_ml_label_store.jsonl
6. recuperer l'artifact
7. backtest avec ML_MODE_OVERLAY_FROZEN
```

Avantage:

- train explicitement cale sur le dataset B_ML.

## 7. Procedure cockpit apres B_ML

### Etape 1 - Finir B_ML

Depuis la page `/backtest`:

- choisir la phase `B_ML Training Label Factory`
- lancer
- attendre la fin
- ouvrir le dossier:

```text
<workflow_root>/phase_b_ml_training_label_factory
```

### Etape 2 - Verifier que le dataset est valable

Verifier:

- `labels/b_ml_label_store.jsonl` existe
- `reports/b_ml_training_dataset_audit.json` existe
- `training_allowed = true`
- `final_verdict in {BML_READY_GOVERNED, BML_READY_RESEARCH}`

### Etape 3 - Aller sur IA Lab

Depuis la page `/lab`:

- renseigner `kline_root`
- renseigner `b2_run_root` si features non-legacy
- renseigner `pair`
- renseigner `timeframe`
- choisir les features
- lancer `Strategy Ladder ML handoff`

### Etape 4 - Recuperer l'artifact

Verifier dans le run IA Lab:

- `strategy_ladder_ml_lab_handoff_report.json`
- `strategy_ladder_backtest_ml_input.json`
- `strategy_ladder_expected_edge_ml_model_bundle.json`
- `strategy_ladder_expected_edge_ml_model_bundle.summary.json`

### Etape 5 - Retour backtest

Depuis `/backtest`:

- `ML_MODE_OVERLAY_FROZEN`
- fournir le run root IA Lab ou l'artifact frozen
- lancer ensuite B1/B2 replay selon le besoin

## 8. Procedure CLI directe apres B_ML

Exemple conceptuel:

```powershell
python scripts/train_strategy_ladder_expected_edge_artifact.py `
  --artifact-id strategy_ladder_expected_edge.bml.direct `
  --label-store-dataset-path L:\output backtest\runs\<workflow>\phase_b_ml_training_label_factory\labels\b_ml_label_store.jsonl `
  --output-dir K:\v5.3 backtest\output2\ml_handoffstrategy\runs\bml_direct_train `
  --pair BTCUSDT `
  --timeframe 1m `
  --train-start 2025-07-10 `
  --train-end 2025-07-11 `
  --feature-names close_return,high_low_range,volume,spread_bps,slippage_bps,book_depth_levels,vpin,cumulative_ofi,realized_vol_current
```

Notes:

- `--label-store-dataset-path` est le point cle.
- `--b2-run-root` n'est pas obligatoire si tu fournis deja un label store B_ML valide.
- il faut conserver la coherence pair / timeframe / dates / features.

## 9. Ce que le cockpit fait aujourd'hui, et ce qu'il ne fait pas encore

| Sujet | Etat actuel |
|---|---|
| Lancer B_ML depuis `/backtest` | Oui |
| Voir les outputs B_ML | Oui |
| Lancer IA Lab depuis `/lab` | Oui |
| Bloquer les features non-legacy sans replay grounding | Oui |
| Utiliser directement `label_store_dataset_path` depuis le formulaire IA Lab | Non |
| Entrainer en CLI direct sur `b_ml_label_store.jsonl` | Oui |

## 10. Quand utiliser B2 run root, et quand utiliser le label store B_ML

### Utiliser `b2_run_root`

Utilise `b2_run_root` si:

- tu travailles avec le rail cockpit IA Lab actuel,
- tu veux un training replay-grounded standard,
- tu veux laisser le handoff construire son propre chemin de training gouverne.

### Utiliser `label_store_dataset_path`

Utilise `label_store_dataset_path` si:

- tu veux entrainer explicitement sur le dataset B_ML deja produit,
- tu veux un controle plus strict de la source de rows,
- tu acceptes de passer par le CLI.

## 11. Checklist operateur courte

### Avant B_ML

- A2 pret
- gold present
- silver index present
- pair/timeframe/date window corrects

### Avant IA Lab

- B_ML `training_allowed=true`
- `training_row_eligible_count > 0`
- pas de fuite feature/label
- features choisies coherentes avec le dataset

### Avant backtest frozen ML

- artifact genere
- hash present
- summary present
- handoff report present
- mode `ML_MODE_OVERLAY_FROZEN`

## 12. Decision operateur recommandee

Si ta question est:

```text
"J'ai fini B_ML. Quelle est la bonne suite ?"
```

La reponse recommandee est:

- si tu veux aller vite en UI: **B_ML -> /lab -> ML handoff -> artifact frozen -> /backtest**
- si tu veux etre strictement cale sur la sortie B_ML: **B_ML -> CLI `train_strategy_ladder_expected_edge_artifact.py --label-store-dataset-path ...` -> artifact frozen -> /backtest**

## 13. Fichiers de reference

- [2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK_FR.md](</E:/claude  v5.3/v53_trading_system/docs/audit/2026-05-24_IA_LAB_ML_TRAINING_AND_BACKTEST_WHITE_BOOK_FR.md>)
- [B_ML_OPERATOR_WHITEBOOK.md](</E:/claude  v5.3/v53_trading_system/docs/audit/B_ML_OPERATOR_WHITEBOOK.md>)
- [run_strategy_ladder_b_ml_label_factory.py](</E:/claude  v5.3/v53_trading_system/scripts/run_strategy_ladder_b_ml_label_factory.py>)
- [run_strategy_ladder_ml_lab_handoff.py](</E:/claude  v5.3/v53_trading_system/scripts/run_strategy_ladder_ml_lab_handoff.py>)
- [train_strategy_ladder_expected_edge_artifact.py](</E:/claude  v5.3/v53_trading_system/scripts/train_strategy_ladder_expected_edge_artifact.py>)
