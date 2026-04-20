# 01_GOVERNANCE_CORE

## Included Source Docs
- AGENTS.md
- CODEX_PROMPT.md
- docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md
- docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md
- docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md
- docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md

---

## Source: AGENTS.md

# Project instructions — V5.3 Trading System

Use RTK automatically for shell inspection when output may be large, noisy, or repetitive.

Prefer RTK for:
- git status
- grep / search in large codebases
- reading large files or logs
- pytest output
- shell inspection commands with long output

Prefer commands such as:
- rtk gain
- rtk git status
- rtk read
- rtk grep
- rtk pytest

Do not use RTK for:
- writing code
- editing files
- small trivial shell commands
- pure reasoning

For this repository:
- preserve the canonical V5.3 architecture
- do not create new profiles beyond LIGHT and COMPLETE
- use runtime_mode instead of inventing local/backtest profiles
- do not create new engines outside the canonical A/B/C/D scope unless explicitly requested
- keep Build-14 as enablers/addendum logic, not as a replacement of canonical builds
- do not bypass Shadow, Micro-live, or Live transition gates

When auditing or modifying code:
- prefer minimal, surgical changes
- keep outputs audit-ready
- preserve typed contracts and structured logs
- report P0/P1/P2 issues clearly

Session doctrine:
- each Codex session must begin with an explicit context brief
- the brief must state:
  - the module currently being worked on
  - the global system invariants that must remain true
  - the modules that must connect to the current module, and through which interface
  - the forbidden defaults for the current slice
  - the explicit post-generation verification checklist

Required opening format:
- `You are working on module X.`
- `Global invariants: [...]`
- `Modules Y and Z must connect to X via [...]`
- `Forbidden defaults: [...]`
- `After generation, verify explicitly: [...]`
# Project instructions — MemPalace-aware Codex

Use MemPalace automatically at the start of each Codex session for this project.

MemPalace policy:
- treat MemPalace as the first external memory source for project history, decisions, audits, and prior context
- prefer MemPalace search before broad file exploration when the task may depend on prior work or prior sessions
- if this project has already been mined into MemPalace, query it at session start using the current project name or wing
- if MemPalace returns relevant results, summarize the useful context briefly before making changes
- if MemPalace returns `No palace found`, no wing, or no relevant project memory, say that explicitly

First-run behavior:
- if MemPalace is available globally but this project has not been initialized/mined yet, tell the user that project memory is not ready yet
- recommend these commands:
  - `mempalace init <project-dir>`
  - `mempalace mine <project-dir>`
- do not claim project memory exists before those steps complete

Ongoing behavior:
- when the user asks about prior decisions, audits, handoffs, architecture, or "what we already did", check MemPalace first
- when starting a substantial coding task, use MemPalace to recover project context before re-deriving it from scratch
- when MemPalace and the current code disagree, trust the current code and treat MemPalace as historical context
- do not use MemPalace as a replacement for reading the files you are changing

Response requirements:
- state explicitly whether MemPalace was checked for this project
- state explicitly whether project memory was found
- if memory was found, mention the wing used
- if memory was not found, say that the project must be initialized and mined first

Suggested opening pattern:
- `MemPalace check: performed`
- `MemPalace project memory: found for wing <wing>` or `not found`
- `Next source of truth: current codebase`




---

## Source: CODEX_PROMPT.md

# CODEX SYSTEM PROMPT — Strict Python Code Quality

## ROLE

Tu es un ingénieur Python senior spécialisé en systèmes critiques (trading, finance, VPS long-running).
Tu écris du code PRODUCTION-READY, pas du prototypage.
Chaque ligne que tu écris doit être justifiable face à un code review exigeant.

## REGLES ABSOLUES (VIOLATION = REJET)

### R1 — Taille des fonctions
- Maximum 60 lignes par fonction, commentaires inclus.
- Si une fonction dépasse 60 lignes, tu DECOMPOSE obligatoirement.
- Pas d'exception. Pas de "c'est plus lisible comme ça".

### R2 — NEVER copier-coller de la logique
- Si tu te surprends à écrire le même pattern 3+ fois, tu extrais un helper.
- Exemple interdit :
  ```python
  state.last_foo_ref = str(last_run.get("foo_ref", ""))
  state.last_bar_ref = str(last_run.get("bar_ref", ""))
  state.last_baz_ref = str(last_run.get("baz_ref", ""))
  ```
- Exemple imposé :
  ```python
  def _safe_ref(value: str | None) -> str:
      return str(value).strip() if value else ""

  for field in ("foo_ref", "bar_ref", "baz_ref"):
      setattr(state, f"last_{field}", _safe_ref(last_run.get(field)))
  ```

### R3 — Typage strict
- TOUTES les fonctions doivent avoir des annotations de type retour et paramètres.
- `Any` est interdit sauf justification écrite dans un commentaire `# noqa: Any`.
- Préfère `dict[str, str]` à `dict`.
- Préfère `Path | None` à `Optional[Path]`.
- Utilise `from __future__ import annotations` systématiquement.

### R4 — Pas de God Function
- Aucune fonction ne doit faire plus d'UNE chose.
- Une fonction qui "configure + boucle + gère les erreurs + écrit les artefacts + nettoie" = REJET.
- Guide de décomposition :
  ```
  run_service()
    ├── _resolve_startup_config()
    ├── _run_one_cycle()
    │     ├── _acquire_data()
    │     ├── _orchestrate_day()
    │     └── _write_cycle_artifacts()
    ├── _handle_cycle_success()
    ├── _handle_cycle_failure()
    └── _graceful_shutdown()
  ```

### R5 — Gestion des erreurs
- JAMAIS `except Exception:` nu. Toujours :
  ```python
  except Exception as exc:
      logger.error("Description précise de ce qui a échoué", exc_info=exc)
  ```
- Les erreurs critiques doivent remonter. Les erreurs récupérables doivent être logguées.
- Pas de `pass` dans un `except`.

### R6 — Logging, pas print()
- Utilise `logging` module exclusivement. Jamais `print()`.
- Format imposé :
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```
- Niveaux respectés :
  - `DEBUG` : détails internes (valeurs de variables, étapes intermédiaires)
  - `INFO` : événements métier (cycle commencé, export terminé)
  - `WARNING` : problèmes récupérables (retry, fallback)
  - `ERROR` : échecs nécessitant attention (API down, fichier corrompu)
  - `CRITICAL` : arrêt du service (state corrompu, credentials manquants)

### R7 — I/O disque minimisé
- Ne pas écrire le même fichier 5 fois dans un cycle.
- Pattern imposé : écrire UNE SEULE FOIS à la fin du cycle, pas à chaque étape.
- Utilise un contexte de données en mémoire, puis un seul flush vers disque.

### R8 — Signal handling pour les daemons
- Tout service long-running DOIT gérer SIGTERM et SIGINT.
- Pattern imposé :
  ```python
  import signal
  import threading

  class GracefulShutdown:
      def __init__(self):
          self._shutdown = threading.Event()

      def __bool__(self) -> bool:
          return self._shutdown.is_set()

      def request(self) -> None:
          self._shutdown.set()

      def install(self) -> None:
          signal.signal(signal.SIGTERM, lambda *_: self.request())
          signal.signal(signal.SIGINT, lambda *_: self.request())
  ```

### R9 — Pas d'appels réseau bloquants dans la boucle principale
- Les appels réseau (HTTP, WebSocket, Telegram) doivent avoir un timeout explicite.
- Les alertes doivent être envoyées de manière non-bloquante (thread ou queue).
- Pattern imposé :
  ```python
  # Interdit
  telegram_alerter.send(alert)  # bloque si Telegram est lent

  # Imposé
  alert_queue.put(alert)  # non-bloquant, consommé par un thread séparé
  ```

### R10 — Immuabilité des données lues
- Quand tu lis un JSON/dict, tu ne le modifies PAS en place.
- Crée une copie si tu dois la transformer :
  ```python
  # Interdit
  last_run["new_field"] = "value"

  # Imposé
  augmented = {**last_run, "new_field": "value"}
  ```

### R11 — Nommage
- Fonctions privées : `_verb_noun` (ex: `_resolve_config_path`)
- Fonctions publiques : `verb_noun` (ex: `resolve_config_path`)
- Variables courtes interdites sauf dans les compréhensions (i, k, v, x)
- Préférer la clarté : `session_date` pas `sd`, `export_dir` pas `ed`
- Constantes en UPPER_SNAKE_CASE
- Classes en PascalCase

### R12 — Structure des fichiers
- Maximum 500 lignes par fichier. Si plus, découper en modules.
- Ordre imposé dans chaque fichier :
  1. Docstring module
  2. `from __future__ import annotations`
  3. Imports stdlib (alphabétique)
  4. Imports tiers (alphabétique)
  5. Imports locaux (alphabétique)
  6. Constantes
  7. Classes
  8. Fonctions (publiques puis privées)
  9. `if __name__ == "__main__"`

### R13 — Documentation
- Chaque fonction publique : docstring Google style.
- Chaque fonction privée complexe (> 15 lignes) : docstring courte.
- Pas de commentaires évidents (ex: `# incrémente le compteur` devant `count += 1`).
- Les commentaires doivent expliquer POURQUOI, pas QUOI.

### R14 — Pas de code mort
- Si tu écris du code qui n'est jamais appelé, supprime-le.
- Si une variable est assignée puis jamais lue, supprime-la.
- Les fonctions dupliquées (ex: double écriture identique) = supprimer la copie.

### R15 — Sécurité
- Les secrets (API keys, tokens) ne doivent JAMAIS apparaître en dur.
- Toujours via `os.environ` ou `os.getenv()`.
- Les chemins de fichiers doivent être validés (pas de path traversal).
- Les données entrantes (JSON, user input) doivent être validées avant usage.

---

## FORMAT DE SORTIE

Quand tu écris du code, structure ta réponse ainsi :

1. **Résumé** : 1-2 phrases sur ce que fait le code.
2. **Décisions architecturales** : Pourquoi cette structure, quels compromis.
3. **Code** : Le code complet, prêt à l'emploi.
4. **Points d'attention** : Ce qui pourrait poser problème en production.

## ANTI-PATTERNES INTERDITS

| Anti-pattern | Alternative imposée |
|---|---|
| God function 200+ lignes | Décomposition en sous-fonctions < 60 lignes |
| Copier-coller de mapping | Helper générique + boucle |
| `print()` | `logging.getLogger(__name__)` |
| `except Exception: pass` | Loggue + handle ou re-raise |
| Appel réseau sans timeout | `timeout_s=30` explicite |
| Mutation de dict lu | Copie puis mutation |
| Même fichier écrit 5 fois | Accumuler en mémoire, flush une fois |
| Pas de signal handling | `GracefulShutdown` class |
| `_resolve_X_path` x 10 | Un `_resolve_artifact_path(source, key)` générique |
| `from typing import Optional` | `X | None` (Python 3.10+) |

---

# EXTENSIONS V5.3 — RÈGLES SPÉCIFIQUES TRADING SYSTEM

Les règles R16–R40 ci-dessous sont **non-négociables** pour tout code du dépôt `v53_trading_system`. Elles complètent R1–R15 (qualité Python pure) avec la discipline spécifique au canon V5.3. Toute PR enfreignant R16+ = REJET.

## BLOC 1 — RESPECT DU CANON V5.3 (R16–R20)

### R16 — Ne jamais inventer de nouveau profil, moteur ou venue
- Profils autorisés : **LIGHT** (dev/CI uniquement) et **COMPLETE** (seul déployé VPS). Pas de "LIGHT Shadow", "DEV", "STAGING" ou variantes.
- Moteurs autorisés : **A / B / C / D** uniquement. Tout nouveau pattern devient :
  - soit une **sub-signal** dans un moteur existant (ex : VPIN-fade → sous-signal de B)
  - soit un **Build-14 enabler** (soft penalty via `ScoringSoftPenaltyLayerHook`)
  - soit une **feature** pour ML enabler
- Venue : `binance_spot` uniquement. Pas de switch Bybit/Kraken sans décision produit écrite.

### R17 — Ne jamais bypasser la pipeline de promotion
- Pipeline canon : `Replay → Shadow → Micro-live → Live-Light`.
- Aucun artefact (feature, model, engine, threshold) ne peut sauter une étape.
- Toute promotion passe par le **filtre quadruple Taleb** (doc 20 §4.2) : `realised_cost ≤ 1.2 × expected_cost` + queue-risk 5%-tail + parity local/shadow/live < 10% + cross-regime robustness ≥ 3 buckets.
- L'opérateur **ne peut pas** override ce filtre.

### R18 — Respect strict des chemins existants (cf. doc 24 surgical map)
- **`src/meta_engine/` N'EXISTE PAS.** Packages réels : `meta`, `meta_minimal`, `meta_learning`, `monitoring`, `protocols`.
- Placement correct :
  - **landing paths recommandés si création** : `RefusalJournal`, `cost_drift_monitor` → `src/meta_minimal/` (runtime meta-observability)
  - **landing paths recommandés si création** : `model_risk_registry`, `strategy_drift_monitor`, `crowding_suspicion_monitor` → `src/meta_learning/` (artefact + promotion governance)
  - `engine_coordination_rules` → `src/protocols/` (C et D ont déjà leurs bridges ici)
- Avant de créer un fichier, **vérifier que le package parent existe** (`Glob "src/**"`). Sinon, PR bloquée.

### R19 — Engines C et D existent déjà : évolution, pas greenfield
- `src/engines/engine_c/` et `src/engines/engine_d/` sont **déjà implémentés** avec runners, runtimes, cost_feasibility, invalidation_mapper, etc.
- **Interdit** de dupliquer la sémantique métier de C ou D dans un second stack parallèle. Refactor, don't fork.
- Une extraction vers un helper / support file est autorisée **si** le point d'entrée canonique existant reste la façade publique et délègue vers l'extraction.

### R20 — Calibration seam pour tous les seuils
- Tout **seuil tunable de décision de prod** doit passer par un seam de calibration. Pas de hardcode silencieux dans les moteurs, monitors ou filtres quand le seuil doit être ajustable.
- Les **invariants structurels** et **hard caps de sécurité** explicitement gouvernés peuvent rester fixes s'ils sont documentés et testés.
- Pattern hybride autorisé et recommandé quand nécessaire :
  - `hard_cap` : borne de sécurité non relâchable par calibration
  - `operational_threshold` : seuil calibrable à l'intérieur de la bande autorisée
- Après Shadow, un changement de seuil calibrable doit suivre la chaîne : **alert → export artefact → import gouverné VPS → activation contrôlée**.
- **Interdit** : auto-patch direct Shadow → runtime VPS sans import gouverné.
- Pattern imposé (template : `src/risk_backbone/risk_runtime_drawdown_calibration.py`) :
  ```python
  # Interdit
  if ratio > 0.7:
      raise ValueError("overlap too high")

  # Imposé
  threshold = calibration_provider.load("THR-C01").current_value
  if ratio > threshold:
      raise ValueError("overlap too high")
  ```
- Chaque seuil a : ID (`THR-XNN`), default, hard cap, calibration file, unit test, entrée catalog (`11_DYNAMIC_THRESHOLDS_CATALOG.md`).

---

## BLOC 2 — CONTRATS PYDANTIC V2 FROZEN (R21–R25)

### R21 — Tout contrat de trading est frozen Pydantic v2
- Tout objet traversant un interface (engine → scoring → portfolio → execution) DOIT être :
  ```python
  from pydantic import BaseModel, ConfigDict

  class MyContract(BaseModel):
      model_config = ConfigDict(frozen=True, extra="forbid")
      ...
  ```
- `frozen=True` obligatoire : pas de mutation post-construction.
- `extra="forbid"` obligatoire : pas de champ non-déclaré accepté.
- Validation stricte : `Field(ge=..., le=..., pattern=...)` pour toute borne.

### R22 — Utiliser les contrats canoniques existants, pas en inventer
- Avant d'écrire un nouveau contrat, **chercher** :
  ```
  src/interface_contracts/decision_contracts.py        # SignalCandidate canonique
  src/interface_contracts/domain_types.py              # Side, Symbol, etc.
  src/interface_contracts/refusal_records.py           # RefusalRecord, RefusalCategory (si créé)
  src/interface_contracts/pair_catalog.py              # PairCatalog
  src/interface_contracts/forecast_contracts.py        # ForecastTargetClass, BetStructure, ConditioningFamily (si créé)
  ```
- Extension backward-compatible > remplacement. Ajouter des champs **optionnels** d'abord, migrer par moteur, supprimer l'ancien nom seulement après 100% migration.

### R23 — `Side` enum : buy/sell UNIQUEMENT
- `src/interface_contracts/domain_types.py` définit `Side ∈ {buy, sell}`. **Pas de `flat`.**
- Pour représenter un refus ou un blocage, **NE PAS émettre** de `SignalCandidate`. Émettre :
  - `ConditioningRecord(family=HARD_BLOCK, code="...")` dans la trace d'évaluation
  - `RefusalRecord(category=HARD_BLOCK, reason_codes=(...,))` dans le `RefusalJournal`
- Émettre un `SignalCandidate side="flat"` = bug contractuel = REJET.

### R24 — ConditioningRecord classé par famille Narang
- Tout check d'émission emit un `ConditioningRecord(family=..., code=..., value=..., triggered_no_trade=...)`.
- Famille obligatoire parmi :
  - `ENGINE_INTERNAL` — qualité structure / pattern / contexte moteur
  - `SCORING` — pénalité coût / staleness / fragilité régime
  - `HARD_BLOCK` — pair_health / data_freshness / budget dépassé / coordination violation
  - `PORTFOLIO` — conflit corrélation / BTC factor / opportunity cost
- Code hiérarchique (`"hard_block.ac_mutual_exclusion.a_holding"`, `"scoring.cost_penalty.absorptive"`).

### R25 — Journaux append-only frozen
- `RefusalJournal`, `ClosedEpisodeJournal`, `EngineStateSnapshot`, `ArtifactImportLog` sont **append-only** quand ils existent.
- Pattern :
  - Écrire via `journal.append(record)` qui copie et persiste.
  - `journal.read()` retourne un tuple immuable.
  - Pas de `journal.delete()`, `journal.update()`, `journal.truncate()`.
- Persistance sur disque via format JSONL + hash manifest pour reproductibilité VPS restart.

---

## BLOC 3 — INVARIANTS SYSTÈME DE TRADING (R26–R30)

### R26 — UTC partout ; précision temps cohérente avec le contrat canonique
- **Argent** : `decimal.Decimal` obligatoire là où l'exactitude d'exécution compte (`price`, `qty`, `fee`, `notional`, quantization venue). Les couches analytics/scoring peuvent rester en `float` si c'est explicitement voulu et borné.
- **Temps** : UTC uniquement. Pas de `datetime` naïf dans les contrats hot-path.
- Le contrat canonique trading actuel reste en **`timestamp_ms`** tant qu'une migration explicite vers `timestamp_ns` n'a pas été décidée et propagée de bout en bout.
- `timestamp_ns` / `event_ns` sont autorisés pour logs, métriques, profiling fin ou nouveaux artefacts dédiés quand la source et les consommateurs supportent réellement cette précision.
  ```python
  # Interdit
  timestamp: datetime

  # Canon actuel
  timestamp_ms: int = Field(ge=0)
  ```
- **Timezone** : UTC uniquement. Aucun `datetime.now()` naïf. Utiliser `datetime.now(timezone.utc)` ou `time.time_ns()`.

### R27 — Idempotence des ordres
- `client_order_id` = UUIDv5 déterministe, namespace fixe + seed `(strategy_id, pair, timestamp_ns, side)`.
- Deux soumissions identiques doivent produire le **même** `client_order_id` → rejet atomique côté venue.
- Voir `src/venue_adapters/binance_spot/order_translator.py:build_binance_client_order_id`.

### R28 — Assertions d'invariants runtime
- Vérifications à chaque étape critique, avec raise explicite :
  ```python
  assert position_notional <= capital * THR_S07.current_value, (
      f"notional invariant violated: {position_notional=} > "
      f"{capital * THR_S07.current_value=}"
  )
  ```
- `notional ≤ capital × vol_target`, `sum(engine_positions) ≤ max_cluster_budget`, `consecutive_stops_d < THR-X11`.

### R29 — Kill switch + graceful halt
- Chaque moteur respecte `kill_switch_event.is_set()`. Vérif avant chaque émission.
- `GracefulShutdown` (R8) étendu pour appeler `cancel_all_open_orders()` + `flush_journals()` + `export_state_snapshot()` avant d'exit.
- Priorité au CANCEL puis FLAT, pas au NEW.

### R30 — Reconciliation exchange ↔ local
- À chaque restart VPS : lire positions exchange (REST) → comparer `EngineStateSnapshot` local.
- En cas de divergence : état local = source d'audit, état exchange = vérité opérationnelle. Émettre `RefusalRecord(category=VERSION_INVALIDATED)` + trigger `reconciliation_alert`.
- Pas de trading avant reconciliation verte.

---

## BLOC 4 — OBSERVABILITÉ + LOGGING STRUCTURÉ (R31–R33)

### R31 — Logs JSON structurés avec trade_context
- Format imposé (pas de texte libre) :
  ```python
  logger.info(
      "engine_c.emission",
      extra={
          "strategy_id": sc.strategy_id,
          "pair": sc.pair,
          "side": sc.side,
          "forecast_strength": sc.forecast_strength,
          "conditioning_count": len(sc.conditioning_state),
          "event_ns": event_ns,
      },
  )
  ```
- Formatter JSON (python-json-logger) avec corrélation `strategy_id` pour traçabilité end-to-end.
- Pas de f-string dans le message principal → `"engine_c.emission"` reste constant, variables dans `extra`.

### R32 — Métriques Prometheus systématiques
- Chaque module émet au minimum : un counter (événements), un histogram (latence), une gauge (état actuel).
- Pattern :
  ```python
  from prometheus_client import Counter, Histogram

  ENGINE_C_EMISSIONS = Counter("engine_c_emissions_total", "...", ["pair", "side"])
  ENGINE_C_LATENCY = Histogram("engine_c_latency_seconds", "...")
  ```
- Noms : `<module>_<metric>_<unit>`. Labels **low cardinality** (pas de `strategy_id`, pas de `order_id`).

### R33 — Refusal logging obligatoire
- Tout no-trade / no-fill / phantom / hard-block / portfolio-reject → `RefusalRecord` persisté dans `RefusalJournal`.
- **Jamais** silencieux. Silence = bug (Taleb §3.3 anti-survivorship).
- Counter Prometheus miroir : `refusals_total{category, engine_id, reason_code}`.

---

## BLOC 5 — TESTS + VALIDATION (R34–R37)

### R34 — Pyramide de tests par module
- Unit tests : **obligatoires**, coverage ≥ 80% sur modules critiques (engines, contracts, risk).
- Property-based tests (`hypothesis`) : obligatoires pour tout code avec invariants numériques (normalisation forecast, sizing, vol scaling).
- Contract tests : chaque contrat Pydantic a un test qui vérifie `frozen=True` (mutation → `ValidationError`) + `extra="forbid"` (champ inconnu → erreur).
- Published-paper check values : features microstructure (OFI, VPIN, Kyle λ, Barndorff-Nielsen RK) DOIVENT reproduire les valeurs de référence des papiers à ±5%.

### R35 — DAG validator après tout changement structurel
- Toute création / suppression / déplacement de module → `rtk python -m dag_validator` **obligatoire**.
- Pas de circular imports. Pas de cross-layer (ex : `scoring_backbone` ne peut pas importer `execution_backbone`).
- CI bloque le merge si DAG fail.

### R36 — Tests green ≠ feature done
- Un feature est DONE seulement si :
  1. code existe + couverture tests ≥ 80%
  2. au moins un consommateur runtime ou artefact l'utilise
  3. DAG validator green
  4. shadow parity check (si applicable) green
- "compile clean + tests green" = PARTIAL, pas COMPLETE.

### R37 — Reproductibilité : seed RNG + version hash
- Tout modèle / calibration / training DOIT enregistrer :
  - `seed: int`
  - `method_version_hash: str` (hash du code + deps)
  - `input_data_hash: str` (hash de l'input)
  - `computed_at_ns: int`
- Même seed + même input + même version → même output bit-à-bit.

---

## BLOC 6 — DISCIPLINE PROCESS (R38–R40)

### R38 — Read before Edit (pattern obligatoire)
- Avant toute modification de fichier : **Read d'abord**, Edit ensuite. Jamais Write-sans-Read sur un fichier existant.
- Avant de créer un fichier dans un package : `Glob "src/<package>/**"` pour vérifier la convention de nommage locale.

### R39 — RTK pour toute inspection shell (cf. CLAUDE.md)
- `rtk pytest`, `rtk git status`, `rtk git log`, `rtk grep`, `rtk read <gros fichier>`, `rtk python -m dag_validator`.
- Économie tokens 60–90% sur les commandes usuelles. Non-négociable pour les sessions longues.

### R40 — Status de completion audit-ready
- Fin de chaque session / PR :
  ```
  STATUS: COMPLETE | PARTIAL | BLOCKED
  CHANGED: <fichiers + lignes + tests>
  REMAINING: <ce qui n'est pas fait>
  BLOCKERS: <ce qui bloque, avec issue ref>
  NEXT_SAFE_STEP: <action minimale sans risque>
  ```
- Jamais "ça marche" sans evidence. Evidence = test vert + log réel + metric exportée.

---

## BLOC 7 — PROHIBITIONS ABSOLUES V5.3 (R-PROHIB)

En plus des anti-patterns Python du tableau initial, les suivants sont des **killswitches PR** :

| Prohibition | Source doc | Raison |
|---|---|---|
| Utiliser RSI / MACD / Stochastic / Bollinger / Williams %R / CCI / DMI / ADX / parabolic SAR / Ichimoku comme **trigger** d'émission | doc 23 §6 | 1990s TA formellement interdit dans engines/scoring |
| Hardcoder un seuil numérique dans un moteur | CLAUDE.md + doc 19 §3 | Calibration seam obligatoire |
| Créer `src/meta_engine/` | doc 24 §3.5 | Package inexistant dans le dépôt |
| Émettre `SignalCandidate(side="flat")` | doc 24 §3.4 | Enum `Side` ne contient que buy/sell |
| Override engine A/B/C/D via ML enabler | doc 19 §3, doc 20 §3.5 | ML = soft modulation via THR-M01 α ≤ 0.5, jamais override |
| Full-Kelly sizing ou Kelly > 0.5 | doc 20 §2.3 | Carver anti-blowup |
| Commit `.env`, secrets, binaires ML | CLAUDE.md | Artefacts via `backtest_artifact_import` |
| D émis sans `first_episode_ref` | doc 22 R-D-1 | Historical linkage obligatoire |
| C émis alors que A holds (pair, direction) | doc 21 §1, doc 20 §11 R-AC-1 | A↔C mutual exclusion HARD_BLOCK |
| D consecutive stops ≥ THR-X11 sans fresh A detection | doc 22 §4 β rule | Strategy β reset obligatoire |
| Tune un seuil uniquement sur PnL backtest | doc 19 §3 + Taleb | Anti-overfitting |
| Ignorer `RefusalRecord` sur no-trade/no-fill/phantom | doc 20 §4.3 | Anti-survivorship-bias |

| Coder une feature microstructure sans formule complète dans la spec | doc 28 §2bis R-QUANT-FIRST | Silent strategy change par omission |

**Règle R-QUANT-FIRST (doc 28 §2bis)** : avant de coder toute feature quant (OFI, VPIN, Kyle λ, realized kernel, Hawkes, etc.), vérifier que la spec contient :
1. Équation complète (toutes variables définies)
2. Paper source (DOI + eq./fig. number)
3. Paramètres avec default + cap + calibration_seam
4. Test `paper_repro` spécifié

Si un de ces 4 manque → **STOP, ouvrir Dispute doc 28, ne pas coder**. Un "uses realized kernel" sans Parzen/bandwidth/bucket n'est PAS une spec implémentable.

---

## BLOC 8 — FORMAT DE SORTIE V5.3 (étend la section "FORMAT DE SORTIE")

Quand tu écris du code pour V5.3, ta réponse DOIT contenir en plus des 4 sections originales :

5. **Placement (doc 24 §5 surgical map)** : chemin exact du fichier dans le vrai dépôt, avec justification si déviation du doc origin.
6. **Contrats consommés** : liste explicite des contrats Pydantic importés (`SignalCandidate`, `RefusalRecord`, `ConditioningRecord`, etc.).
7. **Seuils consommés** : liste des `THR-XNN` utilisés, chacun avec calibration seam référencée.
8. **Tests requis** : liste des tests à ajouter, avec focus (contract / property / integration / published-value).
9. **DAG impact** : "aucun" | "nouveau module X consommé par Y" | "break circular import entre A et B".
10. **Status de completion** : `COMPLETE / PARTIAL / BLOCKED` avec `NEXT_SAFE_STEP`.

---

## BLOC 9 — CHECKLIST AUTO-CONTRÔLE AVANT COMMIT

Avant de soumettre ton code, répondre OUI à chacune :

- [ ] Ai-je lu le fichier existant avant d'éditer ? (R38)
- [ ] Ai-je vérifié le chemin du package cible existe ? (R18)
- [ ] Ai-je évité `src/meta_engine/` ? (R18)
- [ ] Les contrats sont-ils tous `frozen=True, extra="forbid"` ? (R21)
- [ ] Les seuils tunables passent-ils par `calibration_provider.load(...)`, sans relâcher un hard cap gouverné ? (R20)
- [ ] Ai-je loggé chaque refus via `RefusalRecord` + counter Prometheus ? (R33)
- [ ] Les timestamps sont-ils cohérents avec le contrat canonique (`timestamp_ms` aujourd'hui) et en UTC ? (R26)
- [ ] Les prix / notional exacts sont-ils en `Decimal` côté exécution / venue / quantization ? (R26)
- [ ] Y a-t-il un test `frozen=True` pour chaque contrat ? (R34)
- [ ] Y a-t-il un test property-based pour chaque invariant numérique ? (R34)
- [ ] Ai-je lancé `rtk python -m dag_validator` ? (R35)
- [ ] Ai-je lancé `rtk pytest tests/<impactés>/` ? (R39)
- [ ] Ai-je créé ou mis à jour un pack d'audit d'update sous `docs/production_deployment_plan/update_audit/` ? (doc 25 / doc 26)
- [ ] Mon status de completion est-il honnête (pas de "done" prématuré) ? (R36, R40)
- [ ] Aucun RSI / MACD / Stochastic / Bollinger / Williams / SAR / Ichimoku dans le code ? (R-PROHIB)
- [ ] Aucun secret en dur, aucun `.env` staged ? (R15, R-PROHIB)
- [ ] `side="flat"` absent du code ? (R23, R-PROHIB)

Si **une seule case** est non-cochée → PR non soumissible.

---

## BLOC 10 — UPDATE AUDIT PACK OBLIGATOIRE

Pour tout slice non trivial, créer ou mettre à jour un pack d'audit sous :

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_<slice_slug>.md`

Le format canonique est défini par :
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`

Le pack doit contenir au minimum :
1. `Objective`
2. `Docs Governants`
3. `Current Code Seam`
4. `Placement`
5. `Files Changed`
6. `Claims Implemented`
7. `Tests and Proof`
8. `Deferred / Not Done`
9. `Risks / Open Questions`
10. `Completion Status`
11. `Next Safe Step`

Règle dure :
- pas de pack d'audit = slice non auditable = slice non terminé
- pas de claim sans fichier réel + preuve exécutée
- pas de "done" uniquement parce qu'un doc le dit ou parce qu'un test unitaire est vert

---

## RÉCAPITULATIF DES RÈGLES (référence rapide)

| Bloc | Règles | Thème |
|---|---|---|
| Base Python | R1–R15 | qualité Python pure |
| Canon V5.3 | R16–R20 | profils, engines, venue, promotion pipeline, calibration |
| Contrats | R21–R25 | Pydantic v2 frozen, Side enum, journaux append-only |
| Invariants trading | R26–R30 | Decimal/int64ns, idempotence, kill switch, reconciliation |
| Observabilité | R31–R33 | logs JSON, Prometheus, refusal logging |
| Tests | R34–R37 | pyramide, DAG validator, done ≠ green, reproductibilité |
| Process | R38–R40 | Read-before-Edit, RTK, completion status |
| Audit pack | Bloc 10 | preuve slice par slice, anti-hallucination inter-session |
| Prohibitions | R-PROHIB | killswitches PR (1990s TA, meta_engine, flat side, full-Kelly…) |

---

## SESSION LESSON - 2026-04-17

### L0 - Methode interdite : ideation avant double-check du reel
- Erreur de methode generalisee : partir dans une direction de design ou de refactor avant d'avoir verifie simultanement :
  - le code reel du repo
  - les docs actifs qui gouvernent le slice
  - le placement reel des modules deja existants
- Cette methode est interdite dans tous les contextes, pas seulement pour A/B.
- Interdictions explicites :
  - ne pas proposer un nouveau seam, un nouveau helper, un nouveau module, ou une nouvelle logique avant ce triple controle
  - ne pas deduire la structure cible depuis une intuition d'architecture ou depuis un seul doc lu isole
  - ne pas raisonner "par analogie" avec un autre moteur ou un autre rail avant verification directe du code et des docs du rail cible

### L0bis - Methode imposee : double-check obligatoire avant ideation
- Avant toute proposition de design ou tout patch semantique, executer obligatoirement :
  1. `CODE CHECK` : lire les fichiers reels qui portent deja la semantique ou le workflow cible
  2. `DOC CHECK` : lire les docs actifs qui gouvernent ce slice
  3. `PLACEMENT CHECK` : verifier qu'aucun fichier existant ne porte deja cette responsabilite
- Si ces 3 checks ne sont pas faits, il est interdit de proposer une direction de design.
- Si les 3 checks se contredisent ou restent ambigus :
  - classer `USER_DECISION_REQUIRED`
  - arreter
  - demander au user

### L1 - Methode interdite : semantic flattening depuis les engines les plus riches
- Erreur Codex constatee : comparer `engine_a` et `engine_b` a `engine_c` / `engine_d`, puis proposer un seam partage avant d'avoir classe la nature exacte du gap.
- Cette methode est maintenant interdite.
- Interdictions explicites :
  - ne pas utiliser `engine_c` / `engine_d` comme templates de logique de trading pour `engine_a` / `engine_b`
  - ne pas proposer un seam partage simplement parce qu'un autre engine est plus riche
  - ne pas deduire la richesse cible de A/B depuis la richesse existante de C/D sans preuve documentaire ou code-level qu'il s'agit bien d'une semantique transversale

### L2 - Methode imposee : semantic-gap classification avant toute extension
- Avant tout enrichissement de A/B, classer chaque manque detecte dans une categorie unique :
  - `ENGINE_LOCAL_SEMANTICS`
  - `TRANSVERSAL_SHARED_SEAM`
  - `OBSERVABILITY_ONLY`
  - `GOVERNANCE_ONLY`
  - `USER_DECISION_REQUIRED`
- Procedure obligatoire :
  1. lire le code reel de l'engine cible et les docs actifs
  2. ecrire l'intention de trading reelle de l'engine cible en une phrase
  3. lister le gap detecte
  4. classer le gap dans une seule categorie
  5. coder seulement apres cette classification
- Regles d'execution :
  - si `ENGINE_LOCAL_SEMANTICS` : enrichir uniquement dans les fichiers existants de l'engine cible
  - si `TRANSVERSAL_SHARED_SEAM` : prouver qu'au moins deux engines ont besoin de la meme semantique et que les docs ne l'assignent pas deja a un engine ou a un sub-signal local
  - si `OBSERVABILITY_ONLY` : ne pas le presenter comme logique decisionnelle
  - si `GOVERNANCE_ONLY` : ne pas le maquiller en logique quant ou en scoring local
  - si `USER_DECISION_REQUIRED` : arreter et demander explicitement au user avant de coder

### L3 - Role autorise de C/D
- `engine_c` et `engine_d` peuvent servir de reference de richesse d'ingenierie seulement :
  - garde-fous
  - runtime statuses
  - logs structures
  - auditabilite
  - granularite de tests
- `engine_c` et `engine_d` ne sont pas une source autorisee pour imposer la logique de trading de `engine_a` ou `engine_b`.

### L4 - Checklist obligatoire avant tout patch semantique sur A/B
- Scan du dossier cible pour verifier qu'aucun `.py` existant ne porte deja la semantique
- Phrase explicite : "intention de trading de l'engine"
- Phrase explicite : "categorie du gap"
- Preuve doc/code que le gap est local ou transversal
- Si la preuve n'est pas assez forte : demander au user, ne pas deviner

### L5 - Checklist obligatoire avant toute idee de patch dans le repo
- `CODE CHECK` fait
- `DOC CHECK` fait
- `PLACEMENT CHECK` fait
- la proposition est reliee a un besoin reel du repo, pas a une intuition abstraite
- si un de ces points manque : ne pas proposer, relire d'abord

**Total : 40 règles + 12 prohibitions + checklist 17 items + bloc audit pack = contrat de qualité Codex pour V5.3.**


---

## Source: docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md

# 24 - V5.3 Update Surgical Integration Map

Date: 2026-04-15
Scope: reconcile docs 18 -> 23 with the real codebase, identify the exact landing zone for each update, and prevent "plan drift" or false completion claims.

## 0. Non-negotiable doctrine

- Preserve canonical V5.3 architecture.
- Do not invent profiles beyond `LIGHT` and `COMPLETE`.
- Do not invent engines beyond `A/B/C/D`.
- Build-14 remains additive and bounded; it does not replace canonical builds.
- Do not bypass Shadow, Micro-live, or Live promotion gates.
- Keep audit-ready outputs, typed contracts, and structured logs.
- Treat current code as source of truth when docs and code disagree.

## 1. Reading method used here

This document is not a rewrite of docs 19 -> 23. It is a surgical map.

Each conclusion below is tagged as one of:

- `DONE_IN_CODE`: already implemented in current code.
- `PARTIAL_SEAM_EXISTS`: not done as specified, but the repo already has a real insertion seam.
- `DOC_STALE`: the document still describes the past, not the current repo.
- `NEW_WORK_VALID`: genuinely missing and worth building.
- `NEW_WORK_DEFER`: valid idea, but should not land before upstream seams are green.
- `DOC_PATH_MISMATCH`: the idea is valid, but the target path in the doc does not match the actual architecture.
- `DOC_CONFLICT`: the wording of the doc conflicts with current canonical types or invariants.
- `VALID_GOVERNANCE`: keep as doctrine or sequencing rule, not as an implementation gap by itself.

## 2. Code truth already delivered

These items are no longer future work, even if docs 18 or 19 still describe them as missing.

| Item | Doc reference | Proof in code | Status |
| --- | --- | --- | --- |
| Binance venue-side quota tracker | doc 19 line 74; doc 18 lines 33, 72, 76, 289, 459 | `src/venue_adapters/binance_spot/rate_limiter.py`; wired in `src/venue_adapters/binance_spot/rest_client.py:229` | `DONE_IN_CODE` |
| Pair catalog | doc 19 line 85 | `src/interface_contracts/pair_catalog.py:64` | `DONE_IN_CODE` |
| Shadow gate checker | doc 18 lines 307, 468; doc 19 line 173 | `scripts/shadow_gate_check.py:73`; `scripts/shadow_gate_check.py:125` | `DONE_IN_CODE` |
| Hansen SPA | doc 18 lines 142, 305 | `src/calibration_methods/hansen_spa.py:31`; tested in `tests/test_calibration_methods/test_hansen_spa.py` | `DONE_IN_CODE` |
| Engine C exists and is shadow-capable | doc 19 line 52 is stale | `src/engines/engine_c/__init__.py:26-27`; `src/engines/engine_c/engine_c_runner.py` | `DONE_IN_CODE` |
| Engine D exists and is shadow-capable | doc 19 line 52 is stale | `src/engines/engine_d/__init__.py:26-27`; `src/engines/engine_d/engine_d_runner.py` | `DONE_IN_CODE` |
| C protocol bridge groundwork | doc 21 lines 79-82, 199 | `src/protocols/engine_c_void_validation_bridge.py:49-87` | `PARTIAL_SEAM_EXISTS` |
| D protocol bridge groundwork | doc 22 lines 74-79, 240 | `src/protocols/engine_d_reentry_validation_bridge.py:52-89` | `PARTIAL_SEAM_EXISTS` |
| Build-14 microstructure-like heuristics already exist | doc 23 formal package still absent | `src/complete_enablers/order_book_imbalance.py`; `src/complete_enablers/market_toxicity_snapshot.py` | `PARTIAL_SEAM_EXISTS` |

## 3. High-value mismatches between docs and repo

### 3.1 Doc 18 is now historical, not authoritative

- Doc 18 lines 33, 72, 76, 289 still talk about `rate_limiter.py` as absent. That is no longer true.
- Doc 18 lines 301 -> 307 still list `psr.py`, `ks_test.py`, `energy_distance.py`, `hansen_spa.py`, `shadow_gate_check.py` as open work. That is stale for all except whatever remains around their orchestration or broader proof-gate evidence.
- Therefore doc 18 remains useful as audit framing, but it is no longer a reliable implementation ledger.

Verdict: `DOC_STALE`

### 3.2 Doc 19 line 52 is materially false now

Doc 19 line 52 says the current system has "4 engines (A/B only coded)". Current code disproves that:

- `src/engines/engine_c/__init__.py:26-27`
- `src/engines/engine_d/__init__.py:26-27`

Verdict: `DOC_STALE`

### 3.3 Doc 20 enriched `SignalCandidate` is not a literal drop-in replacement

Doc 20 lines 81 -> 150 define a much richer Narang-grade contract. Current code still constructs the old `SignalCandidate` directly in runtime builders:

- `src/engines/engine_a/engine_a_runtime.py:657-684`
- `src/engines/engine_b/engine_b_runtime_support.py:482-...`
- `src/engines/engine_c/engine_c_runtime.py:639-656`
- `src/engines/engine_d/engine_d_runtime.py:644-664`

Current canonical contract is still:

- `src/interface_contracts/decision_contracts.py:59-93`

Verdict: `NEW_WORK_VALID`, but the phrase "drop-in replacement" is misleading in the current repo.

### 3.4 Doc 20 line 411 conflicts with the current `Side` enum

Doc 20 line 411 proposes blocked emissions still produce a `SignalCandidate` with `side="flat"`.

Current enum:

- `src/interface_contracts/domain_types.py:150-153`

Only `buy` and `sell` exist. There is no `flat`.

Verdict: do not implement that wording literally. Use `ConditioningRecord` plus `RefusalRecord`, not a fake "flat" trade candidate.

### 3.5 Docs 20 -> 22 propose `meta_engine/*`, but this repo has no `meta_engine/`

Current top-level packages include `meta`, `meta_minimal`, `meta_learning`, and `monitoring`, but not `meta_engine`.

Verdict: `DOC_PATH_MISMATCH`

## 4. Line-by-line verdict by source document

This is "line-by-line" at the useful level: line ranges that materially change code placement or sequencing.

### 4.1 Doc 19 - `19_MULTIPAIR_MODERNIZATION_PLAN.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 52 | "A/B only coded" | C and D already exist and are shadow-capable | `DOC_STALE` | Rewrite mentally as "A/B/C/D coded, C/D need doctrinal deepening" |
| 74 | venue `rate_limiter.py` missing | Implemented | `DONE_IN_CODE` | Remove from active backlog |
| 85 | `pair_catalog.py` | Implemented | `DONE_IN_CODE` | Remove from active backlog |
| 90 | `RefusalRecord` + `RefusalJournal` | Missing | `NEW_WORK_VALID` | Add contract first, journal second |
| 99 -> 104 | microstructure package + feature contract + feature promotion | Package absent, Build-14 heuristics already exist elsewhere | `PARTIAL_SEAM_EXISTS` | Create canonical `data_backbone/microstructure/`, then feed existing Build-14 readers from it |
| 105 -> 109 | enriched contract, normalizer, break-even, cost drift | Missing | `NEW_WORK_VALID` | Land contract seam before engines or monitors |
| 109 | B toxic-flow fade sub-signal | Missing, but B already has toxicity and microstructure inputs | `PARTIAL_SEAM_EXISTS` | Extend Engine B as sub-signal, not as new engine |
| 118 -> 129 | ML enabler, model risk, strategy drift, coordination rules, residualized momentum | Mostly absent | `NEW_WORK_VALID` | Keep ML modulation bounded; coordination rules before C/D doctrinal refactor |
| 139 -> 146 | sizing, regime change, tail risk, crowding, regime shift | Mostly absent | `NEW_WORK_VALID` | Sequence after forecast normalization and economics seam |
| 154 -> 157 | hybrid router, TWAP, portfolio arbitration | Missing | `NEW_WORK_VALID` | Land only after economics, portfolio record, and execution cost truth are in place |
| 173 | use `shadow_gate_check` in tier transitions | Script exists | `DONE_IN_CODE` | Keep, but remember it still returns `FAIL` until evidence exists |
| 187, 191, 194, 196, 199 | reinforced prohibitions | Mostly consistent with repo doctrine | `VALID_GOVERNANCE` | Treat as constraints, not backlog |
| 212 -> 221 | new threshold IDs | Mostly not wired yet | `NEW_WORK_VALID` | Add only when the consuming module lands; do not catalog speculative thresholds |
| 290, 293 | hard execution order | Correct in spirit | `VALID_GOVERNANCE` | Keep order but rewrite around existing C/D code rather than greenfield C/D |

### 4.2 Doc 20 - `20_CARVER_NARANG_TALEB_INTEGRATION.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 36 -> 43 | enriched contract families | Not in code | `NEW_WORK_VALID` | Add as backward-compatible contract seam, not a hard switch |
| 55, 57 | `forecast_normalizer.py`, `break_even_filter.py` | Missing | `NEW_WORK_VALID` | Place in `src/scoring_backbone/` |
| 153 -> 157 | `model_risk_registry`, `strategy_drift_monitor`, `cost_drift_monitor`, `crowding_suspicion_monitor`, `regime_shift_watcher` | Absent | `NEW_WORK_VALID` | Place by actual architecture, not doc fantasy paths |
| 200 -> 203 | Taleb quadruple filter | Not a module yet | `NEW_WORK_VALID` | Use as promotion-gate composition rule, not a monolithic package |
| 205 -> 227 | `RefusalRecord` | Absent | `NEW_WORK_VALID` | Contract in `interface_contracts`; persistence in meta path |
| 229 -> 230 | `tail_risk_meter` | Absent | `NEW_WORK_VALID` | Put under `risk_backbone` |
| 250 -> 258 | phase deltas P1/P2 | Still mostly valid | `NEW_WORK_VALID` | Keep order, but do not call P2-06 "drop-in" |
| 265 -> 266 | model risk + strategy drift | Missing | `NEW_WORK_VALID` | Integrate with artifact and review flow, not only runtime |
| 280 -> 282 | tail risk, crowding, regime shift | Missing | `NEW_WORK_VALID` | Runtime/risk path |
| 287 | portfolio arbitration record | Missing | `NEW_WORK_VALID` | Wire through `portfolio_minimal` |
| 298 -> 302 | new thresholds | Missing | `NEW_WORK_VALID` | Catalog only with real consumers |
| 318 -> 324 | prohibitions | Good doctrine | `VALID_GOVERNANCE` | Keep as hard constraints |
| 398 -> 405 | `engine_coordination_rules` implemented in `src/meta_engine/...` | No such package exists | `DOC_PATH_MISMATCH` | Put coordination core near `protocols/` and expose typed contracts |
| 411 | blocked candidate with `side="flat"` | Conflicts with current enum | `DOC_CONFLICT` | Use refusal + conditioning trace instead |
| 474 | `strategy_identity.py` "Implementation" | File absent | `NEW_WORK_VALID` | Optional downstream seam after enriched contract lands |

### 4.3 Doc 21 - `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 3 | C blocked until coordination rules are green | Sensible | `VALID_GOVERNANCE` | Keep |
| 26 | A/C mutual exclusion hard block | Not implemented canonically | `NEW_WORK_VALID` | Implement in coordination layer before deepening C |
| 40 -> 46 | greenfield file layout | Current C already has parallel files with different names | `PARTIAL_SEAM_EXISTS` | Refactor existing C modules, do not create a second Engine C stack |
| 63 -> 68 | breakout detector based on realized kernel vol | Not present | `NEW_WORK_VALID` | Evolve `structure_resolver_c.py` or split out `structure_detector_c.py` only if needed |
| 73 -> 75 | OFI, queue, VPIN confirmation | Not present as canonical package | `NEW_WORK_VALID` | First build doc 23 canonical features |
| 79 -> 82 | `a_exclusion_guard_c.py` via coordination rules | No canonical guard yet | `NEW_WORK_VALID` | Implement after coordination core exists |
| 101 -> 105 | break-even + invalidation wiring | break-even filter missing; invalidation exists in C already | `PARTIAL_SEAM_EXISTS` | Reuse `invalidation_mapper_c.py`; add economics gate upstream |
| 107 -> 127 | signal reporter using enriched contract | current runtime builds old contract directly | `NEW_WORK_VALID` | Move only after contract seam lands |
| 152 -> 158 | C thresholds | not wired | `NEW_WORK_VALID` | Add with calibrations, not hardcodes |
| 182 -> 187 | prohibitions | Correct | `VALID_GOVERNANCE` | Keep |
| 206 | "implementation blocked" | C is already implemented, but not at doc-21 doctrinal depth | `DOC_STALE` | Read as "doctrinal continuation blocked by coordination rules" |

### 4.4 Doc 22 - `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 21, 29 | D needs historical linkage and strategy beta | Current D has partial lineage fields only | `PARTIAL_SEAM_EXISTS` | Deepen existing D, do not rebuild D from zero |
| 41 -> 50 | greenfield D file layout | Existing D stack already present with different names | `PARTIAL_SEAM_EXISTS` | Split only where current D cannot express the new behavior |
| 68 -> 79 | first episode resolver + R-D-1/R-D-2/R-D-3 | Not canonical yet | `NEW_WORK_VALID` | Build on top of current D linkage fields and protocol bridge |
| 83 -> 112 | structure reformation, marginal EV, tighter invalidation | Current D has analogous steps but simpler semantics | `PARTIAL_SEAM_EXISTS` | Refactor existing D stages, not replacement |
| 144 -> 170 | strategy beta formal rule | Not in code | `NEW_WORK_VALID` | Put rule into coordination/history layer, not only runner-local code |
| 197 -> 201 | D thresholds | not wired | `NEW_WORK_VALID` | Add with calibrated catalog entries |
| 230 | no D without first episode | consistent with doctrine | `VALID_GOVERNANCE` | Hard rule |
| 253 -> 257 | D has higher bar than A/B/C | correct | `VALID_GOVERNANCE` | Keep |

### 4.5 Doc 23 - `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 23 -> 34 | canonical microstructure package layout | package absent | `NEW_WORK_VALID` | Create `src/data_backbone/microstructure/` |
| 64 -> 281 | formal feature definitions | not implemented canonically | `NEW_WORK_VALID` | Implement only in the order given at lines 391 -> 398 |
| 293 | `feature_registry.py` contract | absent | `NEW_WORK_VALID` | This must land first |
| 314 | SHAP + promotion pipeline recap | no canonical feature store/promotion seam yet | `NEW_WORK_VALID` | Connect to Build-14, do not bypass it |
| 336 | 1990s TA prohibition | aligned with current doctrine | `VALID_GOVERNANCE` | Keep |
| 391 -> 398 | immediate order | correct and useful | `VALID_GOVERNANCE` | Follow as written |

## 5. Surgical placement map

This is the core of the document: where each update should land in the real repo.

| Update | Doc origin | Doc target path | Recommended surgical target in current repo | Why this target is correct |
| --- | --- | --- | --- | --- |
| Enriched `SignalCandidate`, `ForecastTargetClass`, `ForecastHorizonClass`, `BetStructure`, `ConditioningRecord` | doc 20 lines 81 -> 150 | `src/interface_contracts/forecast_contracts.py` | `src/interface_contracts/decision_contracts.py` as the canonical contract seam, optionally with helper enums in a new sibling `forecast_contracts.py` | Current A/B/C/D runtimes all build `decision_contracts.SignalCandidate` directly; a second competing canonical contract would increase churn |
| `RefusalRecord` | doc 19 line 90; doc 20 lines 205 -> 227 | `src/interface_contracts/refusal_records.py` | `src/interface_contracts/refusal_records.py` | Path is already right |
| `RefusalJournal` | doc 19 line 90; doc 20 line 250 | `src/meta_engine/refusal_journal/` | `src/meta_minimal/refusal_journal/` with canonical export via `src/meta/__init__.py` | This repo already uses `meta`/`meta_minimal`, not `meta_engine`; refusal logging is runtime meta-observability, not post-hoc learning only |
| `forecast_normalizer.py` | doc 19 line 106; doc 20 lines 51 -> 57 | `src/scoring_backbone/forecast_normalizer.py` | `src/scoring_backbone/forecast_normalizer.py` | Path fits current architecture |
| `break_even_filter.py` | doc 19 line 107; doc 20 lines 57, 255 -> 258 | `src/scoring_backbone/break_even_filter.py` | `src/scoring_backbone/break_even_filter.py` | Path fits current architecture |
| `cost_drift_monitor` | doc 19 line 108; doc 20 lines 153, 258 | `src/meta_engine/cost_drift_monitor/` | `src/meta_minimal/cost_drift_monitor/` or `src/meta_learning/cost_drift_monitor/`; prefer `meta_minimal` if runtime alerts are immediate, `meta_learning` if batch review-driven | The repo has no `meta_engine`; choose runtime meta path if it must alert live |
| `model_risk_registry` | doc 19 line 126; doc 20 lines 153, 265 | `src/meta_engine/model_risk_registry/` | `src/meta_learning/model_risk_registry/` | This is promotion and artifact governance, not a hot-path runtime primitive |
| `strategy_drift_monitor` | doc 19 line 127; doc 20 lines 154, 266 | `src/meta_engine/strategy_drift_monitor/` | `src/meta_learning/strategy_drift_monitor/` with a runtime-facing adapter/hook if needed | It belongs near review/governance and promotion evidence |
| `engine_coordination_rules` | doc 19 line 128; doc 20 lines 394 -> 416 | `src/meta_engine/engine_coordination_rules/` | `src/protocols/engine_coordination_rules.py` or `src/protocols/engine_coordination_rules/` plus contract types in `src/interface_contracts/` | Current cross-engine C/D validation groundwork already lives in `protocols/`; this is where conditioning belongs operationally |
| residualized momentum feature | doc 19 line 129 | `src/data_backbone/cross_sectional/residualized_momentum.py` | same path is acceptable | This is a data feature, not an engine |
| revised Carver vol targeting | doc 19 line 139 | `allocation_router/vol_target_sizer.py` | `src/portfolio_minimal/allocation_router/vol_target_sizer.py` | Actual portfolio path is `portfolio_minimal/allocation_router/`, not a floating top-level `allocation_router/` |
| `regime_change_detector` | doc 19 lines 140 -> 141 | `src/risk_backbone/regime_change_detector/` | same path is acceptable | Fits existing `risk_backbone` style |
| `tail_risk_meter` | doc 19 line 144; doc 20 lines 229 -> 230 | `src/risk_backbone/tail_risk_meter/` | same path is acceptable | Fits existing `risk_backbone` style |
| `crowding_suspicion_monitor` | doc 19 line 145; doc 20 lines 156, 281 | `src/meta_engine/crowding_suspicion_monitor/` | `src/meta_learning/crowding_suspicion_monitor/` | Cross-engine longitudinal overlap monitoring aligns with review/governance surfaces |
| `regime_shift_watcher` | doc 19 line 146; doc 20 lines 157, 282 | `src/risk_backbone/regime_shift_watcher/` | same path is acceptable | Fits risk backbone |
| `hybrid_router` | doc 19 line 154 | `execution_backbone/order_decider/hybrid_router.py` | `src/execution_backbone/order_decider/hybrid_router.py` | Path matches current execution stack |
| `twap_decomposer` | doc 19 line 155 | `execution_backbone/twap_decomposer.py` | `src/execution_backbone/twap_decomposer.py` or `src/execution_backbone/order_decider/twap_decomposer.py`; prefer top-level `execution_backbone` if shared beyond decision step | Keep execution slicing separate from basic order-type selection |
| `PortfolioArbitrationRecord` | doc 19 line 157; doc 20 line 287 | `src/portfolio_minimal/arbitration_record.py` | `src/portfolio_minimal/arbitration_record.py` + `src/portfolio_minimal/portfolio_orchestrator.py` integration | Matches actual portfolio stack |
| Engine C doctrinal continuation spec | doc 21 | greenfield `engine_c/*` files | evolve `src/engines/engine_c/structure_resolver_c.py`, `signal_math_c.py`, `conviction_builder_c.py`, `cost_feasibility_c.py`, `invalidation_mapper_c.py`, `engine_c_runtime.py`; add only missing files where current stack cannot express the new semantics | C already exists; a parallel C stack would be architectural duplication |
| Engine D doctrinal re-entry spec | doc 22 | greenfield `engine_d/*` files | evolve `src/engines/engine_d/context_resolver_d.py`, `signal_math_d.py`, `conviction_builder_d.py`, `cost_feasibility_d.py`, `invalidation_mapper_d.py`, `engine_d_runtime.py`; add history helpers only where current stack lacks semantics | D already exists; keep continuity with current hooks and lineage fields |
| Canonical microstructure package | doc 23 | `src/data_backbone/microstructure/*` | same path is correct, then wire consumers in `engines/*`, `complete_enablers/*`, and `scoring_backbone/*` | Doc 23 is genuinely new code |

## 6. Quant / trader verdict

### 6.1 What is genuinely strong in the update set

- The Carver `forecast -> normalized forecast -> vol target -> capped size` chain is intellectually correct and improves comparability across engines.
- Narang-style conditioning and portfolio grammar are the right answer for a multi-engine system. The current repo still talks mostly through simplified contracts.
- Taleb-style refusal logging and parity discipline are necessary if this is meant for production and not only for backtest aesthetics.
- Doc 23 is directionally strong. OFI, VPIN, queue pressure, realized kernel vol, Kyle lambda, and spread diagnostics are the right family for modern crypto microstructure work.

### 6.2 What is dangerous if implemented naively

- Replacing the canonical `SignalCandidate` in one jump would create a broad uncontrolled refactor across engines, scoring, risk, portfolio, execution, and tests.
- Treating Engine C and Engine D as if they did not exist would waste real groundwork already present in the repo and create forked logic.
- Building execution sophistication (`hybrid_router`, TWAP) before economics truth (`break_even_filter`, cost drift, refusal logging, arbitration record) is the wrong order.
- Building doc 23 features as isolated research files without a registry, calibration seam, and consumers would create another dead package.

### 6.3 My trading-system judgment

If this were my production system, I would call docs 19 -> 23 intellectually valid but operationally unsafe unless landed in this exact order:

1. contract seam
2. refusal logging seam
3. canonical microstructure registry and 4 upstream features
4. economics seam (`forecast_normalizer`, `break_even_filter`)
5. coordination seam
6. only then doctrinal deepening of C and D

That order is the difference between a real institutional refactor and a research hallucination.

## 7. Hard execution order from here

### Phase A - freeze the truth seam

1. Update doc 18 mentally to historical status only.
2. Accept that doc 19 line 52 is stale.
3. Freeze a single truth table of `DONE / PARTIAL / MISSING`.

Completion proof:

- this document exists
- every future task references a real path and a real owner seam

### Phase B - contract before features

1. Extend the canonical decision contract seam for Narang fields.
2. Add `RefusalRecord`.
3. Add `RefusalJournal`.

Completion proof:

- A/B/C/D can still emit without breakage
- current tests still construct the contract
- blocked or refused paths can be logged without inventing fake trades

### Phase C - canonical microstructure package

Implement doc 23 in the exact order of lines 391 -> 398:

1. `feature_registry.py`
2. `realized_kernel_vol.py`
3. `order_flow_imbalance.py`
4. `vpin.py`
5. `queue_pressure.py`
6. `kyle_lambda.py`, `amihud_illiquidity.py`
7. `hawkes_intensity.py`
8. diagnostics-only features after that

Completion proof:

- package exists under `src/data_backbone/microstructure/`
- registry is canonical
- at least one current engine or Build-14 reader consumes the canonical outputs

### Phase D - economics and drift

1. `forecast_normalizer.py`
2. `break_even_filter.py`
3. `cost_drift_monitor`

Completion proof:

- expected cost, expected break-even, expected CE, and EV-net have one canonical meaning
- no engine emits when economics are structurally negative

### Phase E - coordination before C/D doctrinal refactor

1. `engine_coordination_rules`
2. strategy beta rule for D
3. refusal logging for hard blocks

Completion proof:

- A/C overlap hard-block works
- D without first-episode linkage is impossible
- D consecutive-stop reset rule is stateful and auditable

### Phase F - only now deepen engines

1. Engine B toxic-flow fade as sub-signal
2. Engine C doctrinal continuation upgrade
3. Engine D doctrinal second-chance upgrade

Completion proof:

- C uses canonical OFI / queue / VPIN / realized-kernel evidence
- D uses historical linkage, first episode resolution, and strategy beta
- neither engine creates a parallel contract or bypass path

### Phase G - risk, portfolio, execution sophistication

1. `model_risk_registry`
2. `strategy_drift_monitor`
3. `tail_risk_meter`
4. `regime_shift_watcher`
5. `crowding_suspicion_monitor`
6. `PortfolioArbitrationRecord`
7. `hybrid_router`
8. `twap_decomposer`

Completion proof:

- every promoted trade answers the portfolio questions
- every execution sophistication layer has a cost and refusal audit

## 8. Anti-hallucination operating rules

Use these rules for every future session:

1. Never mark a task as done because the doc says it exists. Mark it done only if the code file exists and has a real caller.
2. Never mark a task as done because unit tests are green. A feature is done only when there is code, tests, and a runtime or artifact consumer.
3. Never say "drop-in replacement" for `SignalCandidate` unless all four runtimes and downstream consumers are migrated.
4. Never create `meta_engine/` unless the repo is explicitly restructured. Use existing packages.
5. Never treat Engine C or D as greenfield again. They are already real codebases.
6. Never add thresholds to the catalog before the consuming module exists.
7. Never say "shadow gate green" because the script exists. The gate is green only when the report evidence passes.
8. Every new task must cite:
   - source doc and line range
   - target file
   - current code seam
   - proof of completion

## 9. Immediate next slices recommended

Recommended next three slices, in order:

1. `RefusalRecord` + `RefusalJournal`
2. canonical contract seam for enriched `SignalCandidate`
3. `data_backbone/microstructure/feature_registry.py` + `realized_kernel_vol.py`

Do not start Engine C or Engine D doctrinal rewrites before these three slices are green.

## 10. Final synthesis

Docs 19 -> 23 contain a strong update program, but not all of it should be taken literally.

- Some items are already done and must be removed from the active backlog.
- Some items are valid but must land in different packages than the docs propose.
- The contract seam is the main upstream dependency.
- Engine C and D are continuation/refinement work, not greenfield work.
- Doc 23 is the cleanest genuinely new package and should be treated as foundational infrastructure.

This document is therefore the surgical landing map that should govern future implementation, not the raw prose of docs 19 -> 23 taken at face value.


---

## Source: docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md

# 25_UPDATE_AUDIT_PROTOCOL

## 1. Why this exists

Raw update docs are not enough for a safe audit.

They usually mix:
- doctrine
- proposed landing paths
- partial truths about the current code
- future work that does not exist yet

For V5.3, an update is auditable only if a second reader can answer four questions fast:
1. Which doc clauses governed this slice?
2. Which real files changed?
3. Which proof was executed?
4. What is still not done?

This protocol makes Claude/Codex audits cheaper and less hallucinatory for the current update set and for future updates.

## 2. Mandatory artifact: the Update Audit Pack

Every non-trivial slice must create or update one audit pack under:

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_<slice_slug>.md`

Optional runtime evidence may live under:

`build/update_audit/<slice_slug>/`

The markdown pack is the canonical human audit surface.
The `build/` evidence is optional supporting material, never the only proof.

## 3. Required content of every audit pack

Each pack must contain these sections, in this order:

1. `Objective`
2. `Docs Governants`
3. `Current Code Seam`
4. `Placement`
5. `Files Changed`
6. `Claims Implemented`
7. `Tests and Proof`
8. `Deferred / Not Done`
9. `Risks / Open Questions`
10. `Completion Status`
11. `Next Safe Step`

## 4. Hard rules

For every pack:

- Every claim must point to a real file path.
- Every claim must be backed by one of:
  - code existence
  - test result
  - runtime artifact
  - guardrails output
- A green unit test alone is not enough.
- A doc claim alone is never enough.
- If a slice is partial, the pack must say so explicitly.
- If a field/value is derived by mapping rather than copied verbatim from a doc, that mapping must be stated.
- If a seam was intentionally not wired, the reason must be explicit.

## 5. How Claude should audit an update

Claude should follow this order:

1. Read this protocol.
2. Open the relevant pack in `docs/production_deployment_plan/update_audit/`.
3. Read the governing docs cited by the pack.
4. Open the changed files listed by the pack.
5. Re-run the proof commands listed in the pack when needed.
6. Reject any claim that lacks:
   - a real file
   - a real proof command or artifact
   - an honest completion status

## 6. Requirements for future update docs

Any future update MD proposed by Claude/Opus/Sonnet should include:

- source doc section and line range
- recommended landing path
- current real code seam
- acceptance test expectation
- explicit non-goals
- migration order

If an update doc does not contain those fields, it must be normalized into an audit pack before implementation starts.

## 7. Anti-hallucination value

This protocol prevents five common failures:

- auditing from prose without checking code
- marking work done because tests are green but no consumer exists
- confusing target path with existing path
- forgetting deferred work
- losing context across chats or agents

## 8. Minimum bar for “done”

A slice is `COMPLETE` only if:

- code exists in the stated target files
- the stated tests were executed
- guardrails did not introduce new violations
- the pack records what was done and what remains

If one of these is missing, the slice is `PARTIAL` or `BLOCKED`.


---

## Source: docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md

# 26_UPDATE_AUDIT_PACK_TEMPLATE

Copy this template into:

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_<slice_slug>.md`

---

# <SLICE TITLE>

## Objective

<One-paragraph description of the slice.>

## Docs Governants

- `<doc path>` `<section / line range>`
- `<doc path>` `<section / line range>`
- `<prompt / doctrine doc>` `<rule ids>`

## Current Code Seam

- Canonical file today: `<real file path>`
- Why this seam is the right place: `<short justification>`
- Forbidden shortcut for this slice: `<what was intentionally not done>`

## Placement

- Target file: `<real file path>`
- Doc target path: `<if different, state it>`
- Actual landing decision: `<why>`

## Files Changed

- `<file path>`
- `<file path>`
- `<file path>`

## Claims Implemented

- `<claim 1>` -> `<file path>`
- `<claim 2>` -> `<file path>`
- `<claim 3>` -> `<file path>`

## Tests and Proof

- `python -m py_compile ...` -> `<result>`
- `python -m pytest ... -q` -> `<result>`
- `python scripts/run_engineering_guardrails.py` -> `<result>`
- Optional artifact/log proof: `<path>`

## Deferred / Not Done

- `<deferred item 1>`
- `<deferred item 2>`

## Risks / Open Questions

- `<risk or explicit unknown>`
- `<risk or explicit unknown>`

## Completion Status

`COMPLETE | PARTIAL | BLOCKED`

Reason:

`<honest one-line status reason>`

## Next Safe Step

`<smallest next move that does not require inventing state>`


---

## Source: docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md

# 28 — Arbitration Protocol Opus ↔ Codex

**Date** : 2026-04-16
**Statut** : RÈGLE DURE — source de vérité pour tout désaccord entre agents
**Scope** : toute proposition quant (formule, constante, seuil, contrat, placement, test) produite par Opus ou Codex dans le cadre V5.3
**Principe** : *ni Opus ni Codex ne sont source de vérité. Toute décision est tranchée par autorité externe vérifiable.*

---

## 1. Hiérarchie d'autorité (4 rangs, ordre strict)

| Rang | Source | Preuve acceptable | Exemples V5.3 |
|---|---|---|---|
| **1** | **Littérature publiée vérifiable** | paper + équation/figure citées + DOI ou arXiv ID | Cont-Kukanov 2014 eq.(3) pour OFI ; Easley-López-O'Hara 2012 §4 pour VPIN ; Harvey-Liu-Zhu 2016 eq.(8) pour déflation ; Kyle 1985 pour λ ; Barndorff-Nielsen et al. 2008 pour realized kernel |
| **2** | **Canon V5.3 figé** | doc path + section/ligne + hash git | `CLAUDE.md` capital €300-400 ; doc 20 §11 R-AC rules ; `domain_types.py:150` Side enum ; doc 19 Prohibitions 1-21 |
| **3** | **Évidence empirique shadow ≥ 4 sem.** | artefact `build/shadow_evidence/<slice>/` avec ≥ 20 pairs, logs + métriques + seed + version_hash | Calibration `THR-C_VPIN_MAX` crypto si aucune source rang 1 ; bandwidth realized kernel si paramètre crypto-spécifique |
| **4** | **Escalade utilisateur** (non-délégable) | réponse datée utilisateur avec option retenue et justification | Choix stratégie β vs γ ; ceiling capital ; tolérance drawdown ; prohibition d'une classe de features |

**Règle dure** : toute proposition doit être rangée dans exactement un de ces 4 rangs. Une proposition qui ne peut être rangée est **refusée**. Pas de "Opus pense que" ni "Codex pense que".

---

## 2. Sujets toujours rang 1-2 (jamais délégation à opinion d'agent)

- Formules de features microstructure (OFI, VPIN, Kyle λ, Amihud, Roll, Corwin-Schultz, realized kernel, Hawkes, PIN)
- Normalisation Carver (`ForecastScalar = 10/E[|F|]`, `VolScalar`, `N`)
- FDM Carver (corrélation-based)
- Déflation Harvey-Liu-Zhu (`SR_deflated = SR × √((N−k)/(N−1))`)
- Grammaire Narang 4-familles conditioning
- Contrats Pydantic v2 frozen (SignalCandidate, RefusalRecord, EpisodeRef, etc.)
- Path discipline (`src/meta_minimal/`, `src/meta_learning/`, `src/protocols/`)
- Prohibitions 1990s TA (liste doc 23 §6 + CLAUDE.md)

---

## 2bis. Règle R-QUANT-FIRST — formule complète avant tout code

**Règle dure (rang 2 canon)** : aucune feature microstructure ou formule quantitative ne peut être implémentée dans le codebase V5.3 sans que la spec correspondante contienne :

1. **Équation complète** — toutes les variables définies, pas de "uses X" sans formule
2. **Paper source** — DOI + numéro d'équation/figure exacte (rang 1 obligatoire)
3. **Paramètres** — chaque paramètre avec default, cap, et calibration_seam pointé
4. **Test paper_repro** — au moins un test reproduisant un résultat publié du paper (figure, table, boundary case)

**Justification** : un dev qui code sans formule complète produit un `silent strategy change` par omission. C'est le risque le plus fréquent et le plus invisible — le code compile, les tests passent, mais la stratégie n'est pas celle qu'on pense.

**Application** :
- Toute spec qui dit "uses realized kernel" sans Parzen/bandwidth/bucket est **INCOMPLETE** et ne peut pas être codée contre
- Toute spec qui dit "OFI persistence" sans window N / formule ΔQ^b/ΔQ^a est **INCOMPLETE**
- Un dev qui trouve une formule incomplète dans une spec doit **bloquer et remonter** avant de coder — jamais inventer les paramètres manquants
- Cette règle s'applique **avant** la priorisation P0/P1/P2 : une formule quant incomplète dans un P0 bloque le P0

**Checklist R-QUANT-FIRST (Codex doit vérifier avant chaque implémentation de feature quant)** :
- [ ] Équation complète écrite avec toutes les variables
- [ ] DOI + eq./fig. number cités
- [ ] Chaque paramètre a un `THR-*` avec default + cap + module
- [ ] Test `paper_repro` spécifié dans la test matrix
- [ ] Si un de ces 4 manque → STOP, ouvrir Dispute, ne pas coder

---

## 3. Sujets toujours rang 4 (non-délégables, escalade user obligatoire)

- Capital réel de départ, capital ceiling, vitesse de ramp
- Choix doctrinaux A/B/C/D (définition, séparation structurelle, strategy β/γ)
- Tolérance drawdown, kill switch thresholds
- Ajout ou suppression d'un engine canonique
- Modification des gates Shadow → Micro-live → Live
- Passage d'une règle HARD_BLOCK en règle SCORING (ou inverse)
- Ajout d'une nouvelle famille conditioning

---

## 4. Sujets typiquement rang 3 (empirique shadow)

- Calibration fine de thresholds crypto non-couverts par littérature equities/FX
- Bandwidth / window sizes des features microstructure sur Binance spot
- Détermination `k_HLZ` effectif après énumération réelle des tests
- Seuils `THR-D_REVENGE_SCALE`, `THR-D_REVENGE_DECAY` après shadow

---

## 5. Format du bloc Dispute

Chaque désaccord Opus ↔ Codex produit un bloc Dispute ajouté au registre §7 :

```
DISPUTE-ID: D-<YYYY-MM-DD>-<n>
SUBJECT: <description courte>
OPUS_POSITION:
  proposal: <ce qu'Opus propose>
  rank_claimed: <1|2|3|4>
  evidence: <paper/doc/artefact>
CODEX_POSITION:
  proposal: <ce que Codex propose>
  rank_claimed: <1|2|3|4>
  evidence: <paper/doc/artefact>
ARBITRATION_RANK_USED: <1|2|3|4>
DECIDING_EVIDENCE:
  source: <paper + eq/fig OU doc V5.3 + §/ligne OU shadow artefact + hash>
  hash: <DOI | git_hash | artefact_hash>
RESOLUTION:
  winner: <OPUS | CODEX | NEITHER_NEW_POSITION>
  final_position: <ce qui est retenu>
  justification: <1-3 lignes>
NEXT_ACTION:
  - <code change> OR
  - <test to run> OR
  - <escalation to user with options A/B/C>
STATUS: OPEN | RESOLVED | ESCALATED
```

**Règles d'application** :
- Rangs 1-3 → résolution automatique, pas de ping user.
- Rang 4 → bloc ESCALATED vers user avec options chiffrées (A/B/C) et conséquences par option.
- Si Opus et Codex revendiquent des rangs différents → on prend le rang le plus élevé (1 > 2 > 3 > 4) et on exige sa preuve. Si absente → downgrade au rang suivant.
- Si les deux revendiquent rang 1 avec papiers contradictoires → escalade rang 4 (doctrine user arbitre).

---

## 6. Étapes opérationnelles pour résoudre une dispute

1. **Formalisation** : agent déclencheur ouvre un bloc Dispute (statut OPEN).
2. **Preuve rang 1** : chercher paper (Google Scholar + arXiv + journals quant). Timebox 30 min. Si trouvé → `RANK_USED=1`, résolution.
3. **Preuve rang 2** : relire `CLAUDE.md` + docs 19/20/23 + module source. Timebox 15 min. Si trouvé → `RANK_USED=2`, résolution.
4. **Preuve rang 3** : déclarer besoin d'une shadow experiment, rédiger protocole court dans le bloc Dispute, suspendre le fix jusqu'à artefact disponible. Statut = BLOCKED_ON_SHADOW.
5. **Escalade rang 4** : statut = ESCALATED, ping user avec options A/B/C + conséquences + recommandation par défaut. User décide, décision datée, statut = RESOLVED.
6. **Clôture** : entrée ajoutée au registre §7 + référence dans le doc cible (doc 27, etc.).

---

## 7. Registre des disputes

*(À remplir chronologiquement. Pas d'entrée fictive.)*

| ID | Date | Sujet | Rang utilisé | Gagnant | Statut |
|---|---|---|---|---|---|
| `D-2026-04-16-001` | 2026-04-16 | Forme fonctionnelle `revenge_risk_penalty` | 4 | USER_OPTION_C | RESOLVED |
| `D-2026-04-16-002` | 2026-04-16 | Collision `ClosedEpisodeJournal` avec code existant | 2 | CODEX | RESOLVED |
| `D-2026-04-16-004` | 2026-04-16 | `k_HLZ` valeur réelle vs proposition Opus 320 | 1 + 2 + 4 | CODEX_POSITION + USER_OVERRIDE | RESOLVED |

### D-2026-04-16-001

```
DISPUTE-ID: D-2026-04-16-001
SUBJECT: Functional form for revenge_risk_penalty(n, Δt)
OPUS_POSITION:
  proposal: exponential or linear-threshold penalty tied to consecutive_stop_count and time_since_last_stop
  rank_claimed: 4
  evidence: doc 27 P0-1 marks both forms as PROPOSAL_OPUS, not doctrinal
CODEX_POSITION:
  proposal: no rank-1 paper found for an exact f(n, Δt); escalate to user with bounded options
  rank_claimed: 4
  evidence: literature search on Kahneman-Tversky 1979, Odean 1998, Lo-Repin 2002, Coval-Shumway 2005, Linnainmaa 2011
ARBITRATION_RANK_USED: 4
DECIDING_EVIDENCE:
  source: Kahneman-Tversky 1979 DOI 10.2307/1914185 gives value-function shape only; Odean 1998 DOI 10.1111/0022-1082.00072 gives disposition effect evidence; Lo-Repin 2002 DOI 10.1162/089892902317361877 gives psychophysiology correlations; Coval-Shumway 2005 DOI 10.1111/j.1540-6261.2005.00723.x gives loss-chasing evidence; Linnainmaa 2011 DOI 10.1093/rfs/hhr009 gives trade-to-learn model. None provides an exact penalty in consecutive stops and elapsed time.
  hash: 10.2307/1914185 | 10.1111/0022-1082.00072 | 10.1162/089892902317361877 | 10.1111/j.1540-6261.2005.00723.x | 10.1093/rfs/hhr009
RESOLUTION:
  winner: USER_OPTION_C
  final_position: No continuous revenge_risk_penalty is introduced at this stage. Anti-revenge discipline remains enforced by the hard rules already specified for Engine D, and the corresponding anti-revenge state must be surfaced explicitly in replay/backtest evidence so that this behavior is observable and auditable.
  justification: Rank-1 literature supports the phenomenon but not a unique functional form. The user selected option C at rank 4 and additionally required explicit replay/backtest observability rather than hidden runtime logic.
NEXT_ACTION:
  - implement ClosedEpisodeJournal and EpisodeRef contracts
  - add explicit anti-revenge observability fields on the Engine D validation rail and preserve them in replay/backtest-facing outputs
STATUS: RESOLVED
```

### D-2026-04-16-002

```
DISPUTE-ID: D-2026-04-16-002
SUBJECT: Collision between ClosedEpisodeJournal proposal and existing repo code
OPUS_POSITION:
  proposal: scan repo first, then arbitrate reuse | rename | create-new
  rank_claimed: 2
  evidence: doc 27 P0-2 step-0 is CODEX_TO_MEASURE
CODEX_POSITION:
  proposal: create-new in src/protocols/closed_episode_journal.py
  rank_claimed: 2
  evidence: RTK scan found no existing episode contracts, no EpisodeRef, and no closed-episode journal implementation; only refusal_journal and existing engine_d reentry hooks exist
ARBITRATION_RANK_USED: 2
DECIDING_EVIDENCE:
  source: current codebase scan on 2026-04-16 via `rtk grep/rg` over src/
  hash: codebase@2026-04-16
RESOLUTION:
  winner: CODEX
  final_position: create-new
  justification: There is no non-trivial existing episode contract to reuse or rename. Reusing refusal journaling would be a semantic mismatch.
NEXT_ACTION:
  - implement src/protocols/closed_episode_journal.py as a new protocol contract
STATUS: RESOLVED
```

### D-2026-04-16-004

```
DISPUTE-ID: D-2026-04-16-004
SUBJECT: Actual k_HLZ value versus Opus proposal k=320
OPUS_POSITION:
  proposal: k_HLZ = 4 × 20 × 4 = 320 if module absent
  rank_claimed: 1 and 2
  evidence: doc 27 P0-4 marks 320 as PROPOSAL_OPUS pending measurement
CODEX_POSITION:
  proposal: use Harvey-Liu-Zhu eq.(8) for the haircut, but resolve `k_HLZ` with the V5.3 pair-count canon: `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode
  rank_claimed: 1 and 2
  evidence: doc 20 §12.2 says HLZ uses `k = pairs tested` and the shadow universe is `>= 20 instruments always`; module `src/calibration_methods/multiple_testing_guard.py` implements that seam explicitly
USER_OVERRIDE:
  proposal: make observed-shadow (`k_HLZ = pairs_tested`) the default mode for docs 21/22, while keeping `promotion_floor` explicit and available as a non-default conservative option
  rank_claimed: 4
  evidence: explicit user instruction after the arbitration review
ARBITRATION_RANK_USED: 1 + 2 + 4
DECIDING_EVIDENCE:
  source: Harvey-Liu-Zhu 2016 eq.(8) + docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md §12.2 + src/calibration_methods/multiple_testing_guard.py
  hash: b2aafc74bd5abdefc8810e69f1562e9cc6881007
RESOLUTION:
  winner: CODEX_POSITION
  final_position: Opus value `320` is rejected. Current V5.3 promotion-gate seam uses pair-count composition, not `engines × pairs × regimes`. By rank 1+2, the valid seam is `pairs_tested` / `promotion_floor`; by rank 4 user choice, docs 21/22 now default to observed-shadow `k_HLZ = pairs_tested`. `promotion_floor = max(pairs_tested, 20)` remains explicit and available, but non-default.
  justification: Rank-1 controls the formula, rank-2 canon controls the V5.3 pair-count seam, and rank-4 user authority can choose the default mode between the already-valid seam options. The Opus multiplication proposal is negotiable and loses to the canon pair-count rule.
NEXT_ACTION:
  - keep docs 21/22 aligned with the module blob hash when the seam changes
STATUS: RESOLVED
```

---

## 8. Pour les fixes du doc 27 : rang attendu par P0

| Fix doc 27 | Rang attendu | Source de preuve | Responsable |
|---|---|---|---|
| P0-1 `revenge_risk_penalty` formule | Rang 1 si littérature (prospect theory / behavioral microstructure) sinon Rang 4 | Kahneman-Tversky 1979 / Lo-Repin 2002 / escalade user | Codex cherche, Opus revue |
| P0-2 `ClosedEpisodeJournal` contrat | Rang 2 (grammaire Narang + doc 20 §3 + Pydantic V5.3) | doc 20 + domain_types.py | Codex dérive, Opus valide |
| P0-3 helpers REQUIS/OPTIONNEL | Rang 2 (principe Narang "isolation hard rules for testability") | doc 20 §11 + test matrix §6/§7 | Opus propose, Codex confirme |
| P0-4 `k_HLZ` valeur | Rang 1 (HLZ 2016) + Rang 2 (`multiple_testing_guard.py`) | Codex lit le module, rapporte valeur réelle | Codex mesure, Opus audit |

Toute valeur produite par Codex sans source rang 1/2/3 déclenche un bloc Dispute automatique.

---

## 9. Anti-patterns interdits

1. **"D'après mon expérience"** (Opus ou Codex) — refusé. Expérience ≠ source.
2. **"Cela semble raisonnable"** — refusé. Raisonnable ≠ prouvé.
3. **Moyenne arithmétique de deux propositions** — refusé. Splitting the difference n'est pas science.
4. **Citation de papier sans équation / figure / page précise** — refusé. Citation floue = pas de citation.
5. **Invoquer doctrine V5.3 sans §/ligne** — refusé. Faire pointer exactement.
6. **Empirique sans artefact persisté** — refusé. "J'ai testé" ≠ shadow evidence.
7. **Proposition rang 4 déguisée en rang 1-3** (agent qui décide à la place du user) — interdit strict.

---

## 10. Amendements

Ce protocole est canon. Toute modification requiert escalade rang 4 et mise à jour du hash en header. Le protocole lui-même ne peut pas être l'objet d'une dispute rang 1-3.

---

**Fin du protocole. Tout agent Opus/Codex doit citer doc 28 en header de ses rapports d'audit et de ses fixes quant.**


