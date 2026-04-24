
# V5.3 — PLAN MAÎTRE CODEX — ML ENABLER EN 2 PARTIES

## 0. But de ce découpage

Ce plan découpe la spécification ML en **deux MD détaillés** pour maximiser la concentration, éviter les oublis, et permettre un audit fin après chaque retour Codex.

- **MD1** = doctrine, architecture, contrats, données, label, features V1 exactes, artefacts, fusion, promotion gate.
- **MD2** = features V2 + research-only, tests, garde-fous, ordre d’implémentation, checklist d’audit, preuves à exiger, deferred propre.

Ce plan maître existe pour que Codex ne traite pas MD1 et MD2 comme deux textes séparés sans colonne vertébrale commune.

---

## 1. Lecture obligatoire

Codex doit lire dans cet ordre :

1. **Ce plan maître**
2. **MD1 — doctrine + architecture + features V1**
3. **MD2 — tests + V2 + gouvernance + audit**
4. Puis seulement le code réel du repo sur les seams cités

Aucune implémentation ne doit commencer avant lecture complète des 3 fichiers.

---

## 2. Mission exacte

Implémenter un **LightGBM tabulaire local-only** servant de **ML confidence enabler** pour V5.3.

Le ML :
- n’est **pas** un moteur autonome,
- ne remplace **jamais** A/B/C/D,
- ne fixe **jamais** le side,
- ne s’entraîne **jamais** sur VPS,
- agit uniquement comme **modulation bornée du score** d’un candidat déjà émis par les moteurs canoniques.

---

## 3. Doctrine non négociable à garder en tête

1. **Une seule solution complète** — pas de fork Local/VPS.
2. **Local IA Lab -> artefact signé -> VPS** reste la topologie canonique.
3. **VPS never trains**.
4. **A/B/C/D restent souverains**.
5. **Le ML est un enabler additif**, jamais un moteur roi.
6. **Aucune modification** des ancres quant gelées :
   - `src/calibration_methods/psr.py`
   - `src/calibration_methods/dsr.py`
   - `src/calibration_methods/pot_gpd.py`
   - `src/calibration_methods/energy_distance.py`
7. **Pas de 1990s TA** comme pilier du modèle.
8. **Pas de nouveau package top-level** de type `src/local_ai_lab/`.
9. **Pas de bypass** des gates Shadow / Micro-live / Live.
10. **Pas d’hallucination de formule** : si une feature n’est pas mathématiquement fermée, elle reste en `DEFERRED` ou `RESEARCH_ONLY`.

---

## 4. Répartition MD1 / MD2

### MD1 couvre obligatoirement

- Objectif et périmètre
- Repo seams existants à réutiliser
- Fichiers à créer / modifier
- Contrats de données
- Définition du label
- Définition du dataset builder
- Features V1 exactes
- Artefact ML
- Promotion gate
- Fusion score
- Drift / model risk minimum

### MD2 couvre obligatoirement

- Features V2 exactes
- Features `RESEARCH_ONLY` / `DEFERRED`
- Tests unitaires
- Tests anti-leakage
- Tests promotion gate
- Tests drift
- Garde-fous d’engineering
- Ordre d’implémentation
- Critères d’acceptation
- Preuves / commandes à rendre
- Checklist d’audit commune

---

## 5. Plan pour ne rien oublier

Codex doit traiter explicitement chacun des points ci-dessous et cocher mentalement chaque item avant de conclure.

### A. Doctrine / architecture
- [ ] ML local-only
- [ ] VPS artifact-only
- [ ] aucune autorité souveraine du ML
- [ ] aucune modification des ancres quant
- [ ] aucune invention d’un 5e moteur

### B. Seams repo à réutiliser
- [ ] `forecast_contracts.py`
- [ ] `strategy_identity.py`
- [ ] `break_even_filter.py`
- [ ] `cost_drift_monitor/`
- [ ] `model_risk_registry/`
- [ ] `strategy_drift_monitor/`
- [ ] `data_backbone/microstructure/*`
- [ ] `backtest_artifact_import/`

### C. Données et labels
- [ ] règle anti-leakage
- [ ] alignement temporel
- [ ] définition explicite du label
- [ ] gestion des NaN / trous / forward-fill interdits ou bornés
- [ ] séparation train / validation / OOS

### D. Features
- [ ] chaque feature a une formule complète
- [ ] chaque variable est définie
- [ ] chaque source de donnée est définie
- [ ] chaque fenêtre est définie
- [ ] chaque règle d’alignement est définie
- [ ] chaque clipping / epsilon est défini
- [ ] ADX n’est pas un pilier
- [ ] aucune feature floue n’est codée sans fermeture math

### E. Modèle
- [ ] famille = LightGBM uniquement
- [ ] entraînement déterministe
- [ ] walk-forward borné
- [ ] Optuna borné
- [ ] artefact versionné
- [ ] hash / feature hash / seed

### F. Runtime / scoring
- [ ] formule de fusion exacte
- [ ] alpha configurable
- [ ] alpha hard cap <= 0.5
- [ ] side inchangé
- [ ] si artefact manquant -> dégradation gracieuse

### G. Gouvernance / prod-safe
- [ ] promotion gate fail-closed
- [ ] coût réel / coût attendu
- [ ] drift monitor
- [ ] refusal / observabilité si nécessaire
- [ ] aucune mutation live autonome
- [ ] aucune promotion au PnL seul

### H. Tests
- [ ] tests unitaires par module
- [ ] tests anti-leakage
- [ ] tests de stabilité du trainer
- [ ] tests artefact round-trip
- [ ] tests promotion gate
- [ ] tests fusion
- [ ] tests drift
- [ ] DAG PASS
- [ ] engineering_guardrails `new_violations=0`

---

## 6. Politique de décision sur les features

- **V1** = doit être codé maintenant ; formule complètement fermée.
- **V2** = codable ensuite ; utile mais secondaire.
- **RESEARCH_ONLY** = intéressante mais non autorisée au runtime tant que la formule / source / calibration n’est pas fermée.
- **DEFERRED** = explicitement reportée ; Codex ne doit pas improviser.

---

## 7. Règle de vérité

Si MD1/MD2 contredisent le repo réel :
- le **code réel** gagne comme vérité opérationnelle,
- mais Codex doit **remonter la contradiction** au lieu de résoudre silencieusement.

---

## 8. Livrables attendus de Codex

1. Code
2. Tests
3. Liste des fichiers créés / modifiés
4. Formules réellement implémentées
5. Résultats de proof commands
6. Deferred / Not Done
7. Risques / Questions ouvertes
8. Verdict final : `COMPLETE`, `PARTIAL`, ou `BLOCKED`

---

## 9. Interdits absolus

- pas de deep learning
- pas de torch
- pas de RL
- pas de XGBoost/CatBoost parallèle
- pas de stratégie ou engine autonome ML
- pas de side piloté par le modèle
- pas de retrain VPS
- pas de seuil ou formule inventés “par intuition”
- pas de modification des fichiers quant gelés
- pas de god files > 700L
- pas de doc rewrite large

---

## 10. Utilisation pratique

- Donner **MD1** à Codex pour la première session d’implémentation.
- Utiliser **MD2** comme garde-fou et checklist de clôture.
- Auditer chaque retour avec la checklist de MD2.

Fin du plan maître.
