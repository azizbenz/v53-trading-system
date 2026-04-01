# V5.3 — BUILD-9X SPEC
## Meta Learning Governed Layer
### Extension méta post-Build-9
### Sans auto-modification live — prod-safe
### Référence documentaire active — première implémentation codée, non finale

---

## 0. Objet du document

Ce document définit une **extension méta post-Build-9** pour V5.3.

Cette extension **ne remplace pas** Build-9. Elle s’appuie sur lui.

Build-9 fournit déjà :
- la traçabilité causale des décisions via `dtr_core`
- la lecture de stérilisation via `cra_monitor`
- la visibilité break-even via `break_even_dashboard`
- le suivi prudent de l’edge via `edge_tracker_prudent_minimal`

La présente extension a une autre mission :

> transformer l’observabilité post-trade en **apprentissage gouverné**, sans jamais autoriser une réécriture directe de la logique live.

Le pipeline cible est :

> **trade → diagnostic → hypothèse → replay/backtest → shadow → validation → déploiement versionné**

Cette brique doit rester compatible avec l’architecture V5.3 unifiée local/VPS :
- une seule base de code
- un shared core identique
- des `runtime_mode` séparés
- aucun bypass vers Shadow / Micro-live / Live
- aucun fork local / VPS

## 0.1 Statut de référence

Ce document est la **référence documentaire active** de Build-9X.

Il ne doit pas être lu comme :

- la preuve que Build-9X est déjà complet ou prêt pour Build-11+
- la preuve qu’un runtime `LOCAL_REPLAY` complet est déjà opéré
- une autorisation à muter le live
- une autorisation à créer un nouveau profil métier

Lecture honnête de la base actuelle :

- une première implémentation codée de Build-9X existe désormais
- cette implémentation reste gouvernée, sans mutation live ni promotion implicite
- `LOCAL_REPLAY` et l’import d’artifact n’existent encore qu’en scaffolds minimaux codés

---

## 1. Position dans l’architecture

### 1.1 Position retenue

Cette brique doit être placée comme :

**Build-9X — Meta Learning Governed Layer**

Statut :
- extension **après Build-9**
- extension **subordonnée** au canon actuel
- **hors remplacement** de Build-10
- **hors remplacement** de Build-11/12/13
- **sans impact live direct**

### 1.2 Pourquoi cet emplacement

Cette brique dépend naturellement de :
- Build-8 pour la lecture portefeuille et arbitrages réels
- Build-9 pour la causalité, la stérilisation, le break-even et l’edge prudent
- Build-10 pour l’exposition visuelle et audit opérable

Elle ne doit pas être confondue avec :
- Build-10 : supervision/UI
- Build-11 : protocole de vérité shadow
- Build-14 : enablers Complete activés à 100% en Shadow, promotion live conditionnelle au verdict

### 1.3 Nature exacte

Build-9X est :
- une couche d’apprentissage gouverné
- une couche de diagnostic post-trade
- une couche de génération d’hypothèses
- une couche de préparation au replay
- une couche de mémoire d’erreurs et de quasi-succès

Build-9X n’est pas :
- un moteur autonome
- une IA libre
- un module RL live
- un système d’auto-tuning live
- un raccourci pour promouvoir une idée en production

---

## 2. Mission stratégique

Build-9X doit permettre au système de répondre proprement à cinq questions :

1. Quelle erreur structurelle, économique ou opérationnelle a été commise ?
2. Quel quasi-succès mérite une investigation au lieu d’être perdu dans le bruit ?
3. Quel filtre, seuil, pénalité, priorité ou discipline semble devoir être retesté ?
4. Quelle hypothèse concrète doit être envoyée en `LOCAL_REPLAY` ?
5. Quels apprentissages doivent être mémorisés sans contaminer la prod ?

---

## 3. Principes non négociables

### 3.1 Principe de non-auto-modification

Build-9X ne doit jamais :
- modifier un seuil live
- modifier un hard blocker live
- modifier une pénalité live
- modifier un score moteur live
- modifier les caps portefeuille live
- retuner le sizing live
- réécrire A/B/C/D
- activer une logique shadow/live nouvelle sans validation

### 3.2 Principe de gouvernance

Toute amélioration issue de Build-9X doit suivre cette chaîne :

1. diagnostic
2. hypothèse versionnée
3. candidate config
4. tests unitaires / contractuels
5. `LOCAL_REPLAY`
6. comparaison logique
7. éventuelle candidature Shadow
8. validation formelle
9. déploiement versionné

### 3.3 Principe d’identité logique

Le replay local n’est pas une autre stratégie ; c’est la même V5.3 exécutée en `LOCAL_REPLAY`.

Donc Build-9X peut :
- produire des propositions
- produire des artifacts
- produire des candidats de test

Mais ne peut pas :
- produire une logique locale parallèle
- produire un `BACKTEST_PROFILE`
- produire un `LOCAL_PROFILE`
- dériver vers une seconde V5.3 cachée

### 3.4 Principe de lecture d’abord

Comme les enablers prudents, cette brique doit être introduite par étapes :
- d’abord **lecture / analyse**
- ensuite **proposition / export**
- jamais **influence live immédiate**

---

## 4. Arborescence Python recommandée

```text
src/
└── meta_learning/
    ├── __init__.py
    ├── contracts/
    │   ├── __init__.py
    │   ├── enums.py
    │   ├── snapshots.py
    │   ├── trade_learning_input.py
    │   ├── diagnostic_result.py
    │   ├── learning_hypothesis.py
    │   ├── improvement_candidate.py
    │   ├── learning_checklist.py
    │   ├── learning_memory_record.py
    │   └── export_bundle.py
    ├── diagnostic/
    │   ├── __init__.py
    │   ├── post_trade_diagnostic_engine.py
    │   ├── root_cause_resolver.py
    │   ├── counterfactual_builder.py
    │   ├── economic_assessor.py
    │   └── evidence_extractor.py
    ├── classification/
    │   ├── __init__.py
    │   ├── mistake_classifier.py
    │   ├── near_miss_analyzer.py
    │   └── category_rules.py
    ├── reporting/
    │   ├── __init__.py
    │   ├── breakdown_report_builder.py
    │   ├── checklist_generator.py
    │   ├── markdown_renderer.py
    │   └── summary_renderer.py
    ├── registry/
    │   ├── __init__.py
    │   ├── hypothesis_registry.py
    │   ├── learning_memory_store.py
    │   ├── hypothesis_deduplicator.py
    │   └── review_queue.py
    ├── candidate/
    │   ├── __init__.py
    │   ├── improvement_candidate_builder.py
    │   ├── config_delta_builder.py
    │   ├── replay_bundle_builder.py
    │   └── comparison_protocol_builder.py
    ├── export/
    │   ├── __init__.py
    │   ├── learning_review_exporter.py
    │   ├── replay_handoff_exporter.py
    │   └── audit_packet_exporter.py
    ├── governance/
    │   ├── __init__.py
    │   ├── non_live_mutation_guard.py
    │   ├── profile_integrity_guard.py
    │   ├── runtime_mode_guard.py
    │   └── versioning_guard.py
    └── service/
        ├── __init__.py
        └── meta_learning_facade.py

tests/
└── meta_learning/
    ├── contracts/
    │   ├── test_enums.py
    │   ├── test_trade_learning_input.py
    │   ├── test_diagnostic_result.py
    │   ├── test_learning_hypothesis.py
    │   ├── test_improvement_candidate.py
    │   └── test_export_bundle.py
    ├── diagnostic/
    │   ├── test_post_trade_diagnostic_engine.py
    │   ├── test_root_cause_resolver.py
    │   ├── test_counterfactual_builder.py
    │   └── test_economic_assessor.py
    ├── classification/
    │   ├── test_mistake_classifier.py
    │   ├── test_near_miss_analyzer.py
    │   └── test_category_rules.py
    ├── reporting/
    │   ├── test_breakdown_report_builder.py
    │   ├── test_checklist_generator.py
    │   └── test_markdown_renderer.py
    ├── registry/
    │   ├── test_hypothesis_registry.py
    │   ├── test_learning_memory_store.py
    │   └── test_hypothesis_deduplicator.py
    ├── candidate/
    │   ├── test_improvement_candidate_builder.py
    │   ├── test_replay_bundle_builder.py
    │   └── test_comparison_protocol_builder.py
    ├── governance/
    │   ├── test_non_live_mutation_guard.py
    │   ├── test_profile_integrity_guard.py
    │   ├── test_runtime_mode_guard.py
    │   └── test_versioning_guard.py
    └── integration/
        ├── test_trade_to_diagnostic_flow.py
        ├── test_diagnostic_to_hypothesis_flow.py
        ├── test_hypothesis_to_replay_bundle_flow.py
        └── test_no_live_mutation_end_to_end.py
```

---

## 5. Modules canoniques proposés

### 5.1 `post_trade_diagnostic_engine`
Mission :
- agréger les faits post-trade et post-no-trade
- reconstruire la chaîne causale utile
- préparer un diagnostic standardisé

### 5.2 `mistake_classifier`
Mission :
- classifier l’événement observé dans une taxonomie d’erreurs canoniques

### 5.3 `near_miss_analyzer`
Mission :
- détecter les trades refusés ou réduits qui auraient pu être valides
- distinguer faux regret et opportunité de calibration

### 5.4 `breakdown_report_builder`
Mission :
- écrire un rapport de breakdown structuré, lisible, comparatif et exportable

### 5.5 `checklist_generator`
Mission :
- produire une checklist post-trade ou post-incident
- séparer opératoire / recherche / validation

### 5.6 `hypothesis_registry`
Mission :
- stocker les hypothèses d’amélioration
- versionner leur origine, leur cible, leur état, leur verdict

### 5.7 `improvement_candidate_builder`
Mission :
- transformer une hypothèse en candidate testable en replay
- sans toucher la configuration live

### 5.8 `learning_memory_store`
Mission :
- conserver l’historique exploitable des diagnostics, hypothèses, verdicts et rejets

### 5.9 `learning_review_exporter`
Mission :
- exporter les paquets de revue humaine, audit, replay et gouvernance

---

## 6. États enums canoniques

### 6.1 `DecisionType`
```python
from enum import Enum

class DecisionType(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"
    REDUCED_TRADE = "REDUCED_TRADE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
```

### 6.2 `DiagnosticCategory`
```python
class DiagnosticCategory(str, Enum):
    FALSE_POSITIVE_SIGNAL = "FALSE_POSITIVE_SIGNAL"
    VALID_SIGNAL_BAD_EXECUTION = "VALID_SIGNAL_BAD_EXECUTION"
    VALID_SIGNAL_BLOCKED_CORRECTLY = "VALID_SIGNAL_BLOCKED_CORRECTLY"
    VALID_SIGNAL_BLOCKED_POSSIBLE_OVERFILTER = "VALID_SIGNAL_BLOCKED_POSSIBLE_OVERFILTER"
    SIZE_STERILIZED = "SIZE_STERILIZED"
    PORTFOLIO_ARBITRATION_LOSS = "PORTFOLIO_ARBITRATION_LOSS"
    RISK_BLOCK_JUSTIFIED = "RISK_BLOCK_JUSTIFIED"
    RISK_BLOCK_TOO_CONSERVATIVE_CANDIDATE = "RISK_BLOCK_TOO_CONSERVATIVE_CANDIDATE"
    DATA_OR_CONTEXT_FAILURE = "DATA_OR_CONTEXT_FAILURE"
    MONITORING_OR_OPERATOR_INTERVENTION = "MONITORING_OR_OPERATOR_INTERVENTION"
    UNCLASSIFIED_REQUIRES_REVIEW = "UNCLASSIFIED_REQUIRES_REVIEW"
```

### 6.3 `ActionabilityLevel`
```python
class ActionabilityLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
```

### 6.4 `HypothesisType`
```python
class HypothesisType(str, Enum):
    SOFT_PENALTY_RECALIBRATION = "SOFT_PENALTY_RECALIBRATION"
    CONTEXT_SCORE_RECALIBRATION = "CONTEXT_SCORE_RECALIBRATION"
    COST_MODEL_RECALIBRATION = "COST_MODEL_RECALIBRATION"
    STERILIZATION_THRESHOLD_REVIEW = "STERILIZATION_THRESHOLD_REVIEW"
    PORTFOLIO_ARBITRATION_REVIEW = "PORTFOLIO_ARBITRATION_REVIEW"
    SIZING_DISCIPLINE_REVIEW = "SIZING_DISCIPLINE_REVIEW"
    MONITORING_ALERT_REVIEW = "MONITORING_ALERT_REVIEW"
    DIAGNOSTIC_ENRICHMENT = "DIAGNOSTIC_ENRICHMENT"
    REPLAY_COMPARISON_GUARD = "REPLAY_COMPARISON_GUARD"
```

### 6.5 `HypothesisStatus`
```python
class HypothesisStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    REPLAY_APPROVED = "REPLAY_APPROVED"
    REPLAY_REJECTED = "REPLAY_REJECTED"
    SHADOW_CANDIDATE = "SHADOW_CANDIDATE"
    SHADOW_REJECTED = "SHADOW_REJECTED"
    DEPLOYED_VERSIONED = "DEPLOYED_VERSIONED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
```

### 6.6 `CandidateStatus`
```python
class CandidateStatus(str, Enum):
    PREPARED = "PREPARED"
    TESTS_PENDING = "TESTS_PENDING"
    READY_FOR_REPLAY = "READY_FOR_REPLAY"
    REPLAY_RUNNING = "REPLAY_RUNNING"
    REPLAY_FAILED = "REPLAY_FAILED"
    REPLAY_PASSED = "REPLAY_PASSED"
    READY_FOR_SHADOW_REVIEW = "READY_FOR_SHADOW_REVIEW"
    RETIRED = "RETIRED"
```

### 6.7 `DiagnosticStatus`
```python
class DiagnosticStatus(str, Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    ARCHIVED = "ARCHIVED"
    ESCALATED = "ESCALATED"
```

### 6.8 `ChecklistScope`
```python
class ChecklistScope(str, Enum):
    TRADE = "TRADE"
    PAIR = "PAIR"
    ENGINE = "ENGINE"
    PORTFOLIO = "PORTFOLIO"
    INCIDENT = "INCIDENT"
```

### 6.9 `ChecklistOwnerType`
```python
class ChecklistOwnerType(str, Enum):
    OPERATIONS = "OPERATIONS"
    RESEARCH = "RESEARCH"
    VALIDATION = "VALIDATION"
    RISK = "RISK"
    MIXED = "MIXED"
```

### 6.10 `PromotionState`
```python
class PromotionState(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    ELIGIBLE_FOR_LOCAL_REPLAY = "ELIGIBLE_FOR_LOCAL_REPLAY"
    READY_FOR_REPLAY_REVIEW = "READY_FOR_REPLAY_REVIEW"
    ELIGIBLE_FOR_SHADOW_REVIEW = "ELIGIBLE_FOR_SHADOW_REVIEW"
    REJECTED = "REJECTED"
    DEPLOYED = "DEPLOYED"
```

---

## 7. Contrats de données recommandés

> Les exemples ci-dessous montrent une version **Pydantic v2** recommandée pour les contrats externes.
> Une variante `dataclass(frozen=True)` peut être utilisée pour les objets internes purs, mais les frontières de module et exports doivent idéalement rester validés par Pydantic.

### 7.1 Snapshots de base

```python
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class BreakEvenSnapshot(BaseModel):
    break_even_bps: float = Field(..., description="Seuil break-even prudent en bps")
    expected_edge_bps: float = Field(..., description="Edge prudent estimé")
    edge_after_cost_bps: float = Field(..., description="Edge net après coûts prudents")


class EdgeSnapshot(BaseModel):
    gross_edge_bps: float
    net_edge_bps: float
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    sample_size_reference: Optional[str] = None


class CostSnapshot(BaseModel):
    spread_bps: float
    slippage_bps: float
    fees_bps: float
    total_cost_bps: float


class ExecutionSnapshot(BaseModel):
    order_id: Optional[str] = None
    fill_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    partial_fills: Optional[int] = Field(default=None, ge=0)
    ack_latency_ms: Optional[float] = Field(default=None, ge=0.0)
    completion_latency_ms: Optional[float] = Field(default=None, ge=0.0)
    reconciliation_ok: Optional[bool] = None


class PortfolioSnapshot(BaseModel):
    exposure_before: float
    exposure_after: float
    capital_at_risk: float
    active_engines_count: int = Field(..., ge=0)
    arbitration_reason: Optional[str] = None


class RiskSnapshot(BaseModel):
    hard_block_triggered: bool
    soft_penalty_score: float
    cluster_limit_hit: bool
    beta_limit_hit: bool
    concentration_limit_hit: bool
    risk_reason: Optional[str] = None


class DataHealthSnapshot(BaseModel):
    market_data_fresh: bool
    context_data_fresh: bool
    pair_health_ok: bool
    data_gap_detected: bool
    anomaly_flag: Optional[str] = None
```

### 7.2 `TradeLearningInput`

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TradeLearningInput(BaseModel):
    decision_id: str
    trade_id: Optional[str] = None
    pair: str
    engine_id: str
    runtime_mode: str
    profile_id: str
    decision_timestamp: datetime
    decision_type: DecisionType
    dtr_reference: str
    cra_reference: Optional[str] = None
    break_even_snapshot: BreakEvenSnapshot
    edge_snapshot: EdgeSnapshot
    expected_cost_snapshot: CostSnapshot
    realized_cost_snapshot: Optional[CostSnapshot] = None
    execution_snapshot: Optional[ExecutionSnapshot] = None
    portfolio_snapshot: PortfolioSnapshot
    risk_snapshot: RiskSnapshot
    data_health_snapshot: DataHealthSnapshot
    operator_context: Optional[str] = None
```

### 7.3 `DiagnosticEvidence`

```python
class DiagnosticEvidence(BaseModel):
    source: str
    reference: str
    observation: str
    weight: float = Field(..., ge=0.0, le=1.0)
```

### 7.4 `DiagnosticResult`

```python
from typing import List
from pydantic import BaseModel, Field


class DiagnosticResult(BaseModel):
    diagnostic_id: str
    status: DiagnosticStatus = DiagnosticStatus.OPEN
    primary_category: DiagnosticCategory
    secondary_categories: List[DiagnosticCategory] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    root_causes: List[str] = Field(default_factory=list)
    evidence: List[DiagnosticEvidence] = Field(default_factory=list)
    counterfactual_summary: str
    economic_assessment: str
    actionability_level: ActionabilityLevel
    human_review_required: bool
    created_at: datetime
```

### 7.5 `LearningHypothesis`

```python
class LearningHypothesis(BaseModel):
    hypothesis_id: str
    origin_diagnostic_id: str
    hypothesis_type: HypothesisType
    target_module: str
    target_parameter_family: str
    expected_effect: str
    risk_of_regression: str
    required_replay_scope: str
    shadow_candidate_allowed: bool = False
    status: HypothesisStatus = HypothesisStatus.DRAFT
    source_version: str
    contracts_version: str
    feature_schema_version: str
    formula_schema_version: str
    regime_logic_version: str
    cost_model_version: str
```

### 7.6 `ImprovementCandidate`

```python
class ImprovementCandidate(BaseModel):
    candidate_id: str
    hypothesis_id: str
    candidate_version: str
    config_delta_reference: str
    tests_required: list[str] = Field(default_factory=list)
    replay_bundle_reference: str
    comparison_protocol_reference: str
    promotion_state: PromotionState = PromotionState.NOT_ELIGIBLE
    status: CandidateStatus = CandidateStatus.PREPARED
    shared_core_hash: str
```

### 7.7 `LearningChecklistItem`

```python
class LearningChecklistItem(BaseModel):
    key: str
    label: str
    mandatory: bool = True
    completed: bool = False
    note: Optional[str] = None
```

### 7.8 `LearningChecklist`

```python
class LearningChecklist(BaseModel):
    checklist_id: str
    scope: ChecklistScope
    owner_type: ChecklistOwnerType
    severity: ActionabilityLevel
    items: list[LearningChecklistItem] = Field(default_factory=list)
    due_before_promotion: Optional[str] = None
```

### 7.9 `LearningMemoryRecord`

```python
class LearningMemoryRecord(BaseModel):
    record_id: str
    diagnostic_id: str
    hypothesis_id: Optional[str] = None
    candidate_id: Optional[str] = None
    verdict: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    archived: bool = False
```

### 7.10 `ReplayExportBundle`

```python
class ReplayExportBundle(BaseModel):
    bundle_id: str
    candidate_id: str
    shared_core_hash: str
    source_version: str
    contracts_version: str
    feature_schema_version: str
    formula_schema_version: str
    regime_logic_version: str
    cost_model_version: str
    tests_required: list[str] = Field(default_factory=list)
    replay_scope: str
    comparison_protocol: str
```

---

## 8. Familles d’hypothèses autorisées

Build-9X peut proposer des hypothèses sur :
- seuils de pénalités soft
- calibration de score contextuel
- calibration de coût prudent
- conditions de stérilisation
- seuils d’arbitrage portefeuille
- discipline de réduction de taille
- hiérarchie de rejets relatifs
- ajustements de monitoring / alertes
- enrichissement de diagnostics / DTR
- garde-fous de comparaison replay vs shadow

Build-9X ne peut pas proposer directement :
- un nouveau moteur
- une suppression brutale du risk backbone
- un bypass des caps
- une logique RL live
- une logique POMDP live
- une promotion implicite Complete
- un changement non traçable du shared core

---

## 9. Politique d’influence

### 9.1 Étape 1 — Lecture seule
Autorisé :
- diagnostics
- rapports
- checklists
- registry
- exports
- dashboards de learning

Interdit :
- toute influence décisionnelle

### 9.2 Étape 2 — Préparation replay
Autorisé :
- candidates versionnées
- paquets de replay
- définitions de comparaison
- files d’attente d’hypothèses

Interdit :
- activation Shadow automatique
- mutation runtime

### 9.3 Étape 3 — Candidature gouvernée
Autorisé :
- marquage `ELIGIBLE_FOR_LOCAL_REPLAY`
- marquage `ELIGIBLE_FOR_SHADOW_REVIEW`

Interdit :
- promotion directe vers Shadow
- promotion directe vers Micro-live
- promotion directe vers Live

---

## 10. Outputs obligatoires

### 10.1 Breakdown report
Chaque diagnostic significatif doit pouvoir produire un rapport contenant :
- résumé du cas
- causalité principale
- coûts attendus vs réalisés
- lecture break-even
- lecture stérilisation
- lecture portefeuille
- lecture contrefactuelle
- enseignement principal
- checklist
- hypothèse éventuelle
- verdict

### 10.2 Checklist
Checklist séparée selon trois axes :
- `OPERATIONS`
- `RESEARCH`
- `VALIDATION`

### 10.3 Hypothesis record
Toute hypothèse doit être enregistrée avec :
- sa source
- sa justification
- son périmètre
- son état
- son verdict final

### 10.4 Replay bundle
Toute hypothèse recevable doit pouvoir générer :
- une candidate versionnée
- les tests requis
- le scope de replay
- le protocole de comparaison

---

## 11. Ordre précis d’implémentation

### Étape 1
`post_trade_diagnostic_engine`

Pourquoi :
- il faut d’abord standardiser les faits

### Étape 2
`mistake_classifier`

Pourquoi :
- la mémoire d’apprentissage dépend d’une taxonomie propre

### Étape 3
`breakdown_report_builder`

Pourquoi :
- les diagnostics doivent devenir lisibles et auditables

### Étape 4
`checklist_generator`

Pourquoi :
- un diagnostic utile doit créer une discipline d’action

### Étape 5
`hypothesis_registry`

Pourquoi :
- il faut mémoriser proprement ce qui mérite replay

### Étape 6
`improvement_candidate_builder`

Pourquoi :
- il faut transformer l’hypothèse en candidat testable sans toucher la prod

### Étape 7
`learning_memory_store`

Pourquoi :
- il faut capitaliser les diagnostics, rejets et validations

### Étape 8
`learning_review_exporter`

Pourquoi :
- il faut rendre la revue humaine et la gouvernance praticables

---

## 12. Plan de tests module par module

## 12.1 Contracts

### `contracts/enums.py`
Tests :
- vérifier que chaque enum expose uniquement les valeurs canoniques
- vérifier la stabilité des noms sérialisés
- refuser toute valeur inconnue

### `contracts/trade_learning_input.py`
Tests :
- accepter un trade complet valide
- accepter un no-trade valide sans `trade_id`
- refuser un `confidence_score` hors bornes dans les snapshots liés
- refuser un input sans `dtr_reference`
- refuser un input avec `decision_type` invalide

### `contracts/diagnostic_result.py`
Tests :
- créer un diagnostic minimal valide
- refuser un `confidence_score` > 1.0
- accepter plusieurs catégories secondaires
- vérifier présence du `counterfactual_summary`

### `contracts/learning_hypothesis.py`
Tests :
- créer une hypothèse versionnée valide
- refuser une hypothèse sans `target_module`
- refuser une hypothèse sans versioning minimal
- vérifier statut par défaut `DRAFT`

### `contracts/improvement_candidate.py`
Tests :
- créer un candidate valide
- refuser un candidate sans `shared_core_hash`
- vérifier `promotion_state` par défaut
- refuser bundle incomplet pour replay

### `contracts/export_bundle.py`
Tests :
- créer un bundle export complet
- refuser un bundle sans protocole de comparaison
- vérifier cohérence `candidate_id` / `bundle_id`

---

## 12.2 Diagnostic

### `diagnostic/post_trade_diagnostic_engine.py`
Tests :
- trade accepté profitable mais coûts élevés → diagnostic cohérent
- trade accepté avec exécution destructrice → catégorie exécution
- no-trade correctement bloqué → catégorie blocage justifié
- trade réduit à taille stérile → catégorie `SIZE_STERILIZED`
- donnée dégradée → catégorie `DATA_OR_CONTEXT_FAILURE`

### `diagnostic/root_cause_resolver.py`
Tests :
- hiérarchiser correctement cause primaire et causes secondaires
- ne pas confondre blocage risque et mauvais signal
- marquer `human_review_required` sur cas ambigu

### `diagnostic/counterfactual_builder.py`
Tests :
- produire un résumé contrefactuel lisible
- distinguer “si exécuté à taille pleine” de “si non exécuté”
- refuser contrefactuel vide

### `diagnostic/economic_assessor.py`
Tests :
- comparer coûts attendus vs réalisés
- identifier destruction économique malgré bon signal
- détecter mismatch edge / coût

### `diagnostic/evidence_extractor.py`
Tests :
- extraire références DTR / CRA / coût / exécution
- pondérer les évidences
- ignorer les références manquantes non critiques

---

## 12.3 Classification

### `classification/mistake_classifier.py`
Tests :
- classer faux signal
- classer bon signal / mauvaise exécution
- classer blocage justifié
- classer sur-filtrage candidat
- classer incident opérateur

### `classification/near_miss_analyzer.py`
Tests :
- repérer un trade refusé qui aurait dépassé break-even
- ne pas surclasser un simple hasard favorable
- exiger taille d’échantillon suffisante pour répétition

### `classification/category_rules.py`
Tests :
- priorité correcte des règles
- déterminisme à input identique
- absence de catégories contradictoires en primaire

---

## 12.4 Reporting

### `reporting/breakdown_report_builder.py`
Tests :
- rapport complet avec toutes sections
- rapport minimal pour no-trade
- inclusion correcte checklist + hypothèse
- format stable pour audit/export

### `reporting/checklist_generator.py`
Tests :
- générer checklist `OPERATIONS`
- générer checklist `RESEARCH`
- générer checklist `VALIDATION`
- ne pas créer de checklist vide sur cas actionnable

### `reporting/markdown_renderer.py`
Tests :
- rendu markdown déterministe
- titres et sections conformes
- sérialisation propre des items checklist

### `reporting/summary_renderer.py`
Tests :
- résumer un diagnostic sans perdre la catégorie primaire
- conserver verdict et niveau d’actionnabilité

---

## 12.5 Registry

### `registry/hypothesis_registry.py`
Tests :
- enregistrer une hypothèse
- mettre à jour son statut
- historiser les transitions
- refuser écrasement silencieux d’une hypothèse existante

### `registry/learning_memory_store.py`
Tests :
- enregistrer diagnostic + verdict
- archiver sans perte de traçabilité
- retrouver l’historique par `decision_id`, `diagnostic_id`, `hypothesis_id`

### `registry/hypothesis_deduplicator.py`
Tests :
- détecter hypothèses quasi identiques
- éviter doublons faibles
- ne pas fusionner deux hypothèses de modules distincts

### `registry/review_queue.py`
Tests :
- file d’attente des hypothèses `UNDER_REVIEW`
- priorisation des cas `CRITICAL`
- exclusion des hypothèses déjà rejetées définitivement

---

## 12.6 Candidate

### `candidate/improvement_candidate_builder.py`
Tests :
- transformer une hypothèse valide en candidate
- ajouter tests requis minimum
- refuser hypothèse sans versioning complet
- refuser candidate si target module interdit

### `candidate/config_delta_builder.py`
Tests :
- construire delta traçable sans toucher config active
- refuser changement de hard block live
- refuser changement de profil non autorisé

### `candidate/replay_bundle_builder.py`
Tests :
- produire bundle consommable par `LOCAL_REPLAY`
- inclure versions et protocoles
- refuser bundle incomplet

### `candidate/comparison_protocol_builder.py`
Tests :
- définir baseline vs candidate
- imposer métriques obligatoires
- inclure garde-fous de non-régression

---

## 12.7 Export

### `export/learning_review_exporter.py`
Tests :
- exporter un paquet revue humaine complet
- inclure diagnostic, hypothèse, checklist, verdict
- checksum ou identifiant stable recommandé

### `export/replay_handoff_exporter.py`
Tests :
- exporter bundle pour replay local
- inclure versions minimales
- refuser export si candidate non prêt

### `export/audit_packet_exporter.py`
Tests :
- produire packet audit lisible
- inclure historique et rejets
- format stable et diffable

---

## 12.8 Governance

### `governance/non_live_mutation_guard.py`
Tests :
- bloquer toute tentative de mutation live
- bloquer modification hard block
- bloquer écriture dans config active

### `governance/profile_integrity_guard.py`
Tests :
- refuser création d’un profil parallèle
- refuser `BACKTEST_PROFILE`
- refuser `LOCAL_PROFILE`

### `governance/runtime_mode_guard.py`
Tests :
- autoriser uniquement les runtime modes déjà canoniques
- refuser runtime mode ad hoc
- vérifier compatibilité replay/shadow/live

### `governance/versioning_guard.py`
Tests :
- exiger toutes les versions minimales
- refuser hash shared core absent
- refuser candidate non versionné

---

## 12.9 Intégration end-to-end

### `integration/test_trade_to_diagnostic_flow.py`
Tests :
- input trade → diagnostic complet
- input no-trade → diagnostic complet
- input trade stérilisé → diagnostic `SIZE_STERILIZED`

### `integration/test_diagnostic_to_hypothesis_flow.py`
Tests :
- diagnostic actionnable → hypothèse `DRAFT`
- diagnostic non actionnable → pas d’hypothèse forcée
- diagnostic ambigu → revue humaine obligatoire

### `integration/test_hypothesis_to_replay_bundle_flow.py`
Tests :
- hypothèse approuvée → candidate → replay bundle
- bundle inclut tous les identifiants de version
- protocole de comparaison présent

### `integration/test_no_live_mutation_end_to_end.py`
Tests :
- aucun chemin end-to-end n’altère la configuration active
- aucune hypothèse ne bascule directement en Shadow/Live
- aucune écriture ne crée une seconde V5.3 locale

---

## 13. Dépendances officielles

### 13.1 Dépendance obligatoire
- Build-9 complété et gelé

### 13.2 Dépendance fortement recommandée
- Build-10 complété pour exposition propre des faits

### 13.3 Dépendances aval
- `LOCAL_REPLAY` pour validation
- Build-11 pour éventuelle revue shadow
- Build-12/13 uniquement après protocole normal

---

## 14. Conditions de sortie

Build-9X est considéré propre si :
- chaque trade significatif ou no-trade significatif peut générer un diagnostic standardisé
- les principales familles d’erreurs sont classées
- un breakdown report est générable
- une checklist est générable
- une hypothèse versionnée peut être créée sans toucher la prod
- un candidate replay peut être exporté proprement
- aucune auto-modification live n’est possible
- aucun fork local/VPS n’est introduit
- les rejets et validations sont mémorisés proprement

---

## 15. Critères de refus

Refuser Build-9X si :
- la brique peut modifier la prod directement
- la taxonomie est floue ou décorative
- les rapports ne sont pas causaux
- les checklists ne débouchent sur aucune discipline réelle
- les hypothèses ne sont pas versionnées
- le replay bundle n’est pas traçable
- une logique locale parallèle apparaît
- la brique devient un moteur caché
- le système “apprend” mais sans protocole de validation

---

## 16. Dérives globales à ne pas faire

- confondre diagnostic et optimisation live
- appeler “learning” un simple log enrichi
- multiplier les hypothèses faibles sans tri
- utiliser le hindsight comme preuve
- sur-réagir à quelques trades isolés
- ignorer la taille d’échantillon
- ignorer les coûts prudents
- corriger un moteur au lieu de diagnostiquer la vraie cause
- créer un module prestige non gouvernable
- remplacer l’analyse par un score opaque

---

## 17. Table synthétique

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| `post_trade_diagnostic_engine` | 1 | P0 | faits standardisés | diagnostic exploitable |
| `mistake_classifier` | 2 | P0 | erreurs classées | taxonomie robuste |
| `breakdown_report_builder` | 3 | P0 | rapport causal | lecture humaine exploitable |
| `checklist_generator` | 4 | P0/P1 | discipline post-trade | actions structurées |
| `hypothesis_registry` | 5 | P0 | mémoire gouvernée | hypothèses traçables |
| `improvement_candidate_builder` | 6 | P0 | handoff replay propre | candidate versionné |
| `learning_memory_store` | 7 | P1 | capitalisation durable | mémoire de verdicts |
| `learning_review_exporter` | 8 | P1 | revue et audit fluides | paquet exportable |

---

## 18. Verdict final

Build-9X est la brique qui transforme la V5.3 d’un système **explicable** en système **capable d’apprendre proprement**, sans trahir sa discipline prod-safe.

Si Build-9X est bien fait :
- les erreurs deviennent exploitables
- les quasi-succès ne sont plus perdus
- les améliorations sont gouvernées
- le replay reçoit des candidats propres
- la comparaison local/shadow devient plus utile
- la mémoire du système devient cumulative sans devenir dangereuse

Si Build-9X est mal fait :
- il créera une pseudo-intelligence décorative
- il introduira du hindsight mal contrôlé
- il favorisera des mutations non validées
- il augmentera la complexité sans vérité
- il mettra en danger la parité logique V5.3

Donc :

> **Build-9X doit être traité comme une extension méta de gouvernance de l’apprentissage, et non comme un moteur d’auto-optimisation live.**


---

## 19. INTERNAL API AND EVENT CONTRACTS

### 19.1 Principe général

Build-9X doit exposer une **façade interne unique**.  
Aucun module amont ou aval ne doit manipuler directement les registres, candidats, bundles ou transitions d’état.

Façade canonique :

```python
class MetaLearningFacadeProtocol(Protocol):
    def ingest_learning_input(self, payload: TradeLearningInput) -> str: ...
    def create_diagnostic(self, decision_id: str) -> DiagnosticResult: ...
    def register_hypothesis(self, diagnostic_id: str) -> LearningHypothesis | None: ...
    def prepare_candidate(self, hypothesis_id: str) -> ImprovementCandidate: ...
    def export_replay_bundle(self, candidate_id: str) -> ReplayExportBundle: ...
    def mark_review_decision(self, review_id: str, decision: str, actor_id: str, reason: str) -> str: ...
    def get_diagnostic(self, diagnostic_id: str) -> DiagnosticResult: ...
    def list_hypotheses(self, status: HypothesisStatus | None = None) -> list[LearningHypothesis]: ...
    def get_candidate(self, candidate_id: str) -> ImprovementCandidate: ...
    def get_learning_history(self, entity_id: str) -> list[LearningMemoryRecord]: ...
```

### 19.2 Commandes autorisées

| Commande | Effet | Synchrone / asynchrone | Interdit en live path ? |
|---|---|---|---|
| `ingest_learning_input` | enregistre le fait brut d’apprentissage | synchrone léger | non |
| `create_diagnostic` | lance le diagnostic standardisé | asynchrone recommandé | oui si lourd |
| `register_hypothesis` | crée une hypothèse gouvernée | asynchrone | oui |
| `prepare_candidate` | prépare un candidate versionné | asynchrone | oui |
| `export_replay_bundle` | produit le paquet replay | asynchrone | oui |
| `mark_review_decision` | enregistre une décision humaine | synchrone léger | non |

### 19.3 Requêtes autorisées

| Requête | Sortie |
|---|---|
| `get_diagnostic(diagnostic_id)` | diagnostic complet |
| `list_hypotheses(status=None)` | liste filtrée |
| `get_candidate(candidate_id)` | candidate complet |
| `get_learning_history(entity_id)` | historique de transitions et verdicts |
| `get_review_queue()` | file d’attente de revue |
| `get_learning_counters(run_id)` | compteurs et backlog |

### 19.4 Opérations explicitement interdites

Aucune API interne Build-9X ne doit permettre :

- `apply_live_config`
- `mutate_runtime`
- `promote_to_shadow`
- `promote_to_micro_live`
- `promote_to_live`
- `create_profile`
- `set_runtime_mode`
- `override_hard_block`
- `override_risk_caps`
- `bypass_candidate_validation`

### 19.5 Contrats d’événements internes

Les événements internes doivent être immuables, versionnés et sérialisables.

```python
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class LearningEvent(BaseModel):
    event_id: str
    event_type: str
    event_version: str = "1.0"
    emitted_at: datetime
    run_id: str
    session_id: Optional[str] = None
    decision_id: Optional[str] = None
    trade_id: Optional[str] = None
    diagnostic_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    candidate_id: Optional[str] = None
    replay_bundle_id: Optional[str] = None
    actor_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
```

### 19.6 Catalogue minimal d’événements

| Event type | Déclencheur | Payload minimal |
|---|---|---|
| `learning_input_ingested` | input accepté | pair, engine_id, decision_type |
| `diagnostic_created` | diagnostic produit | primary_category, confidence_score |
| `diagnostic_escalated` | revue humaine obligatoire | reason, actionability_level |
| `hypothesis_created` | hypothèse créée | hypothesis_type, target_module |
| `hypothesis_deduplicated` | hypothèse fusionnée / rejetée comme doublon | duplicate_of |
| `hypothesis_rejected` | revue défavorable | rejection_reason |
| `candidate_prepared` | candidate validé | candidate_version, target_module |
| `replay_bundle_exported` | bundle produit | bundle_id, replay_scope |
| `promotion_state_changed` | changement de promotion_state | previous_state, new_state |
| `live_mutation_blocked` | tentative interdite | blocked_action, guard_name |
| `learning_store_degraded` | stockage/logging/backpressure dégradé | failure_mode, queue_depth |

### 19.7 Règle de compatibilité

Tout nouveau champ ajouté à un contrat d’événement doit être :
- optionnel au premier déploiement,
- versionné,
- accompagné d’un test de rétrocompatibilité,
- documenté dans le changelog canonique.

---

## 20. OBSERVABILITY IDS AND LOGGING POLICY

### 20.1 Chaîne d’identifiants obligatoire

Tout le flux Build-9X doit être corrélé par les identifiants suivants :

- `run_id`
- `session_id`
- `decision_id`
- `trade_id`
- `dtr_id`
- `cra_id`
- `diagnostic_id`
- `hypothesis_id`
- `candidate_id`
- `replay_bundle_id`
- `review_id`
- `change_ticket_id`

Aucun diagnostic, log critique, export replay ou décision de revue ne doit exister sans au moins :
- `run_id`
- `decision_id` ou `diagnostic_id`
- `event_id`

### 20.2 Règles de génération d’IDs

- IDs stables, non réutilisés, globalement uniques
- pas d’IDs dépendants d’un ordre mémoire local
- pas d’IDs incrémentaux non namespacés
- préfixes recommandés :
  - `diag_`
  - `hyp_`
  - `cand_`
  - `rpb_`
  - `rev_`
  - `evt_`

### 20.3 Niveaux de logs canoniques

- `DEBUG` : détails de développement, désactivables hors local
- `INFO` : transition métier normale
- `WARNING` : comportement inattendu mais récupérable
- `ERROR` : échec partiel nécessitant revue
- `CRITICAL` : défaillance mettant en cause la traçabilité ou la gouvernance

### 20.4 Taxonomie minimale des logs Build-9X

| Log key | Level par défaut | Obligation |
|---|---|---|
| `learning.input.accepted` | INFO | obligatoire |
| `learning.input.rejected` | WARNING | obligatoire |
| `learning.diagnostic.created` | INFO | obligatoire |
| `learning.diagnostic.failed` | ERROR | obligatoire |
| `learning.diagnostic.escalated` | WARNING | obligatoire |
| `learning.hypothesis.created` | INFO | obligatoire |
| `learning.hypothesis.duplicate` | INFO | obligatoire |
| `learning.hypothesis.rejected` | INFO | obligatoire |
| `learning.candidate.prepared` | INFO | obligatoire |
| `learning.bundle.exported` | INFO | obligatoire |
| `learning.governance.live_mutation_blocked` | CRITICAL | obligatoire |
| `learning.storage.backpressure` | WARNING | obligatoire |
| `learning.storage.loss_detected` | ERROR | obligatoire |
| `learning.review.decision_recorded` | INFO | obligatoire |

### 20.5 Champs obligatoires de chaque log structuré

```python
class StructuredLearningLog(BaseModel):
    timestamp: datetime
    level: str
    logger_name: str
    message_key: str
    run_id: str
    session_id: str | None = None
    decision_id: str | None = None
    trade_id: str | None = None
    diagnostic_id: str | None = None
    hypothesis_id: str | None = None
    candidate_id: str | None = None
    review_id: str | None = None
    event_id: str | None = None
    runtime_mode: str
    profile_id: str
    module_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
```

### 20.6 Politique de sampling et déduplication

- jamais de sampling sur :
  - `live_mutation_blocked`
  - `diagnostic_failed`
  - `storage.loss_detected`
  - `review_decision_recorded`
- déduplication autorisée seulement pour les logs répétitifs non critiques
- toute déduplication doit incrémenter un compteur de suppression
- la déduplication ne doit jamais casser la reconstitution causale

### 20.7 Politique de confidentialité / sécurité

Il est interdit de logguer en clair :
- secrets
- credentials
- clés API
- contenu brut de config active sensible
- payloads PII éventuels si un opérateur est référencé

Les logs doivent rester suffisants pour audit sans divulgation inutile.

### 20.8 Invariants d’observabilité

Refuser le merge si :
- un diagnostic significatif ne laisse pas de trace log structurée,
- un `candidate_prepared` n’est pas corrélé à un `hypothesis_id`,
- une décision de revue n’est pas attribuable à un `actor_id`,
- une perte de logs ne déclenche ni compteur ni alerte.

---

## 21. UI DASHBOARD PROJECTIONS

### 21.1 Principe

Build-9X ne crée pas un nouveau monde UI parallèle.  
Il se projette dans les écrans déjà canoniques de la V5.3.

### 21.2 Écran Meta / DTR / Phantom Trades

Ajouter les widgets suivants :

- `Recent Diagnostics`
- `Top Diagnostic Categories`
- `Near-Miss Candidates`
- `Overfilter Candidates`
- `Hypotheses Opened`
- `Hypotheses Rejected`
- `Replay Eligibility Queue`
- `Learning Backlog Depth`
- `Blocked Live Mutations`
- `Review SLA Status`

Colonnes minimales d’une table diagnostics :
- `diagnostic_id`
- `decision_id`
- `pair`
- `engine_id`
- `primary_category`
- `confidence_score`
- `actionability_level`
- `human_review_required`
- `status`
- `created_at`

### 21.3 Écran Logs & Événements

Ajouts obligatoires :
- filtre par `diagnostic_id`
- filtre par `hypothesis_id`
- filtre par `candidate_id`
- filtre par `review_id`
- vue des événements `learning.*`
- compteur `loss_detected`
- compteur `live_mutation_blocked`

### 21.4 Écran Administration contrôlée

Actions autorisées :
- approuver une hypothèse pour replay review
- rejeter une hypothèse
- ouvrir le replay bundle exporté
- consulter la piste d’audit complète
- escalader à revue humaine

Actions interdites :
- pousser vers Shadow
- pousser vers Live
- modifier la config active
- éditer silencieusement un diagnostic ou une hypothèse validée

Toute action opérateur doit journaliser :
- `actor_id`
- `timestamp`
- `reason`
- `review_id`
- `change_ticket_id` si applicable

### 21.5 KPIs dashboard minimaux

- `diagnostics_created_total`
- `diagnostics_escalated_total`
- `hypotheses_created_total`
- `hypotheses_duplicate_total`
- `hypotheses_rejected_total`
- `candidates_prepared_total`
- `replay_bundles_exported_total`
- `live_mutation_blocked_total`
- `learning_backlog_depth`
- `review_latency_p50/p95`
- `learning_store_error_rate`

### 21.6 États visuels obligatoires

Chaque entité affichée doit exposer un statut visuel stable :
- `OPEN`
- `UNDER_REVIEW`
- `READY_FOR_REPLAY`
- `REPLAY_RUNNING`
- `REJECTED`
- `ARCHIVED`

### 21.7 UX de recherche

L’UI doit permettre une recherche directe par :
- `decision_id`
- `trade_id`
- `diagnostic_id`
- `hypothesis_id`
- `candidate_id`
- `bundle_id`

Sans cela, la brique learning n’est pas opérable en production.

---

## 22. RESOURCE BUDGETS AND PERFORMANCE GATES

### 22.1 Principe cardinal

Build-9X ne doit jamais allonger matériellement le chemin critique de décision live.  
Le live path ne doit produire qu’un événement/snapshot minimal et retourner.

### 22.2 Architecture d’exécution imposée

- émission inline ultra-légère d’un `TradeLearningInput` ou équivalent
- file asynchrone bornée
- traitement diagnostic hors chemin critique
- export/replay/checklist/hypothesis hors chemin critique
- comportement de dégradation explicite si backlog saturé

### 22.3 Budgets par défaut — profil LIGHT

En l’absence de valeur plus stricte imposée par le master :

- overhead inline p95 : **<= 1 ms**
- overhead inline p99 : **<= 2 ms**
- allocations mémoire inline : **bornées et sans croissance non bornée**
- surcoût CPU steady-state Build-9X : **<= 10 % d’un cœur logique** en Light
- RSS additionnelle steady-state Build-9X : **<= 256 MB**
- backlog queue normal : **0 à 1 000 éléments**
- seuil d’alerte backlog : **> 1 000**
- seuil de protection : **> 5 000**
- export bundle : asynchrone uniquement
- rendu markdown/rapports lourds : asynchrone uniquement

### 22.4 Budgets par défaut — mode LOCAL_REPLAY

`LOCAL_REPLAY` peut consommer davantage, mais :

- ne doit pas modifier les décisions métier,
- ne doit pas casser la parité logique,
- doit exposer son propre budget CPU/RAM/I/O,
- doit signaler toute réduction d’observabilité utilisée pour performance.

Budgets recommandés :
- batching autorisé,
- compression logs autorisée,
- rendu rapport bulk autorisé,
- mais aucune approximation sur la logique de diagnostic primaire.

### 22.5 Politique de backpressure

Si la file Build-9X dépasse le seuil de protection :
1. continuer le trading sans blocage,
2. dégrader Build-9X en mode `capture_minimale`,
3. émettre `learning.storage.backpressure`,
4. compter les éléments non traités,
5. interdire toute promotion/revue basée sur données incomplètes.

### 22.6 Merge gates performance obligatoires

Refuser le merge si l’implémentation Build-9X :
- ajoute un appel bloquant sur le chemin live,
- augmente le p95 de décision au-delà du budget,
- introduit une croissance mémoire non bornée,
- perd des logs sans compteur de perte,
- ne distingue pas normal / alert / protection backlog,
- nécessite un thread unique fragile sans recovery.

### 22.7 Budget I/O et stockage

- pas d’écriture synchrone lourde sur le live path
- rotation de fichiers ou stockage segmenté obligatoire
- bundles exportés checksumés
- pas de scan disque complet sur hot path
- pas de lecture massive pour construire un diagnostic unitaire

### 22.8 Métriques de capacité minimales

- `learning_queue_depth`
- `learning_queue_oldest_age_ms`
- `learning_worker_cpu_pct`
- `learning_worker_rss_mb`
- `learning_write_latency_ms`
- `learning_export_failures_total`
- `learning_log_loss_total`

---

## 23. PERSISTENCE, RETENTION, AND LIFECYCLE GOVERNANCE

### 23.1 Modèle de persistance

Build-9X doit utiliser un modèle **append-only** pour les transitions d’état critiques :
- création de diagnostic
- changement de statut diagnostic
- création d’hypothèse
- changement de statut hypothèse
- création de candidate
- export replay
- décision de revue
- archivage

### 23.2 Entités persistées

À minima :
- `diagnostic_records`
- `hypothesis_records`
- `candidate_records`
- `review_records`
- `learning_events`
- `export_bundle_records`
- `learning_memory_records`

### 23.3 Invariants de persistance

- pas d’écrasement silencieux
- toute transition d’état historisée
- horodatage obligatoire
- acteur obligatoire pour toute revue humaine
- hash/checksum pour tout bundle exporté
- possibilité de relecture par `entity_id`

### 23.4 Politique de rétention minimale

En l’absence de règle supérieure imposée par la solution :

- diagnostics et hypothèses : conserver **>= 180 jours**
- transitions de review et promotions : conserver **>= 365 jours**
- bundles exportés : conserver au moins tant qu’une revue ou replay associé reste ouvert
- logs structurés critiques : conserver selon politique monitoring centrale, sans être inférieure à la période de review active

### 23.5 Archivage

Un diagnostic ou une hypothèse peut être archivé seulement si :
- aucun replay actif associé,
- aucune revue ouverte,
- aucune promotion pendante,
- le verdict final est enregistré.

### 23.6 Intégrité et diffabilité

Les exports doivent être :
- diffables,
- checksumés,
- versionnés,
- re-générables à partir des enregistrements sources,
- comparables entre local et VPS.

### 23.7 Machine à états canonique

#### Diagnostic
`OPEN -> REVIEWED -> ARCHIVED`
`OPEN -> ESCALATED -> REVIEWED -> ARCHIVED`

#### Hypothesis
`DRAFT -> UNDER_REVIEW -> REPLAY_APPROVED -> SHADOW_CANDIDATE`
`DRAFT -> UNDER_REVIEW -> REPLAY_REJECTED -> CLOSED_NO_ACTION`
`SHADOW_CANDIDATE -> SHADOW_REJECTED -> CLOSED_NO_ACTION`
`SHADOW_CANDIDATE -> DEPLOYED_VERSIONED`

#### Candidate
`PREPARED -> TESTS_PENDING -> READY_FOR_REPLAY -> REPLAY_RUNNING`
`REPLAY_RUNNING -> REPLAY_FAILED -> RETIRED`
`REPLAY_RUNNING -> REPLAY_PASSED -> READY_FOR_SHADOW_REVIEW`

### 23.8 Transitions interdites

- `DRAFT -> DEPLOYED_VERSIONED`
- `PREPARED -> DEPLOYED`
- `REPLAY_FAILED -> READY_FOR_SHADOW_REVIEW`
- `ARCHIVED -> OPEN` sans record de réouverture explicite
- toute transition non historisée

---

## 24. STATISTICAL GOVERNANCE AND PROMOTION VALIDITY

### 24.1 Principe

Build-9X ne doit pas transformer le hindsight en vérité.  
Toute hypothèse doit être qualifiée selon sa force probante.

### 24.2 Niveaux de force probante

- `ANECDOTAL`
- `WEAK_PATTERN`
- `REPEATABLE_PATTERN`
- `ROBUST_CANDIDATE`

### 24.3 Règles minimales

- un diagnostic issu d’un seul trade peut créer un diagnostic,
  mais pas une promotion forte automatique ;
- une hypothèse issue d’un seul cas doit être marquée au mieux `ANECDOTAL` ;
- une hypothèse de recalibration doit indiquer :
  - périmètre,
  - taille d’échantillon,
  - moteur,
  - paire ou groupe de paires,
  - régime concerné,
  - horizon temporel,
  - expected vs realized.

### 24.4 Exigences avant `REPLAY_APPROVED`

Toute hypothèse candidate au replay doit fournir :
- justification causale,
- échantillon utilisé,
- segmentation utilisée,
- risque de régression,
- métriques de comparaison prévues,
- critères explicites de rejet.

### 24.5 Critères de rejet statistique

Refuser une hypothèse si :
- elle repose uniquement sur un résultat isolé sans contexte,
- elle n’indique pas l’échantillon,
- elle mélange plusieurs moteurs sans justification,
- elle mélange plusieurs régimes sans justification,
- elle ne distingue pas coût prudent attendu et réalisé,
- elle ne propose aucun protocole de comparaison.

### 24.6 Near-miss governance

Les `near_miss` ne doivent jamais être interprétés comme gains ratés par défaut.  
Ils doivent être séparés en :
- `near_miss_noise`
- `near_miss_candidate`
- `near_miss_repeatable_candidate`

### 24.7 Promotion governance

Aucune hypothèse ne doit pouvoir atteindre `SHADOW_CANDIDATE` sans :
- replay bundle complet,
- protocole de comparaison,
- review humaine ou revue gouvernée équivalente,
- versions complètes,
- absence de régression critique identifiée.

---

## 25. DOC FREEZE AMENDMENTS REQUIRED IN THE SOLUTION

### 25.1 Amendements à apporter au build plan

Ajouter explicitement :

> **Build-9X — Meta Learning Governed Layer**  
> Extension officielle post-Build-9.  
> Dépend de Build-9. S’appuie fortement sur Build-10 pour exposition.  
> Produit diagnostics, hypothèses, checklists et replay bundles, sans auto-modification live.

### 25.2 Amendements à apporter au master canonique / unique

Ajouter les invariants suivants :
- Build-9X n’est pas un moteur,
- Build-9X ne modifie jamais la prod,
- Build-9X ne crée ni profil ni runtime mode,
- Build-9X ne peut promouvoir qu’à travers le pipeline gouverné,
- Build-9X appartient au shared core logique,
- son exécution lourde reste asynchrone et non bloquante.

### 25.3 Amendements à apporter à la table UI

Ajouter dans les écrans existants :
- widgets diagnostics,
- widgets hypotheses,
- recherche par IDs learning,
- actions de review gouvernée,
- compteurs de backpressure / log loss / live mutation blocked.

### 25.4 Amendements à apporter aux merge gates

Ajouter des gates spécifiques :
- `NO_LIVE_MUTATION_PATH`
- `END_TO_END_ID_CORRELATION`
- `STRUCTURED_LEARNING_LOGS_PRESENT`
- `LEARNING_BACKPRESSURE_HANDLED`
- `RESOURCE_BUDGETS_RESPECTED`
- `STATISTICAL_GOVERNANCE_PRESENT`

---

## 26. FREEZE CHECKLIST

Build-9X peut être considéré **freeze-ready** seulement si :

- la façade API interne est figée,
- la chaîne d’IDs est figée,
- les logs structurés et événements sont figés,
- les écrans UI impactés sont figés,
- les budgets de ressources et merge gates sont figés,
- la persistance append-only est figée,
- les transitions d’état sont figées,
- la gouvernance statistique est figée,
- les docs mères ont reçu leurs amendements,
- les tests de non-mutation live et de corrélation end-to-end passent.

### 26.1 Ce qui restait manquant avant cette V2

- contrats d’API interne
- politique d’IDs de bout en bout
- taxonomie de logs learning
- projections dashboard précises
- budgets CPU/RAM/I/O/latence
- persistance/rétention/lifecycle
- gouvernance statistique
- amendements explicites aux docs mères

### 26.2 Ce qui reste encore hors périmètre

Cette spec ne remplace toujours pas :
- les paramètres exacts du backtest engine,
- les détails Shadow/Micro-live/Live,
- la politique globale de stockage de toute la solution,
- les choix d’infrastructure physique.

---

## 27. VERDICT FREEZE-READY

Après ajout des sections 19 à 26, Build-9X n’est plus seulement une bonne idée métier.  
Il devient une brique **gelable** côté documentation, parce que :

- sa place dans la hiérarchie V5.3 est claire,
- son API interne est bornée,
- sa corrélation IDs/logs est audit-able,
- son exposition UI est définie,
- ses budgets ressources sont bornés,
- sa persistance et son lifecycle sont explicites,
- sa gouvernance statistique limite le faux apprentissage,
- ses amendements documentaires sont identifiés.

Donc :

> **La V2 de Build-9X peut servir de base de freeze documentaire, sous réserve d’inscrire ses amendements dans le master, le build plan, la table UI et les merge gates de la solution.**
