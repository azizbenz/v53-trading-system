# Note doctrinale — Stage naming vs Profile naming

**Date** : 2026-04-21
**Auteur Opus** : arbitrage doctrinal session 2026-04-21
**Statut** : canon — référence pour toute future question sur les noms `Light` / `Complete` dans V5.3
**Origine** : arbitrage B (`2026-04-21_manifest_registry_stage_naming_restore.md`) — sur-interprétation du memory 2026-04-19 "no LIGHT profile" ayant conduit au renommage unilatéral des stages Build-12/13/17 dans `build_order_registry.py`

---

## Règle de doctrine (à garder en mémoire)

Dans V5.3 il existe **deux axes orthogonaux** qui utilisent tous deux les mots `Light` et `Complete`. Confondre les deux produit des mutations incorrectes.

### Axe 1 — Profils de déploiement (règle "no LIGHT profile")

| Profil | Usage autorisé | Usage interdit |
|---|---|---|
| **LIGHT** | dev loop, CI smoke, bootstrap local uniquement | aucun déploiement Shadow / Micro-live / Live |
| **COMPLETE** | seul profil déployé sur VPS (Shadow → Micro-live → Live) | — |

**Règle** (CLAUDE.md 2026-04-14 + memory `feedback_no_light_profile_doctrine.md` 2026-04-19) :

> Il n'y a **ni** LIGHT Shadow, **ni** LIGHT Live, **ni** LIGHT deployment.
> LIGHT est un outil développeur, pas un stage de déploiement.
> Shadow-through-Live run COMPLETE avec tous les layers activés (A+B+C+D, full risk stack, full meta, SignalCandidate enrichi, RefusalJournal, model_risk_registry, etc.).

Portée : artefacts `config/profile_*.yaml`, branches CI, conteneurs build, tags release, feature flags.

### Axe 2 — Paliers de rampe capital (noms de stages canoniques)

Les **paliers `Live-Light` et `Live-Complete` NE SONT PAS des profils**. Ce sont des étapes de la phase Live dans la table des gates V5.3, conditionnées par des tiers de capital et des enablers.

| Palier | Tier capital | Enablers requis | Rôle |
|---|---|---|---|
| **Shadow** | 0 | none | validation sans capital |
| **Micro-live** | T3+ / T4+ (selon engine) | engine-specific gates | première exécution réelle ultra-prudente |
| **Live-Light** | T3+ | kill-switch + governance + replay | première rampe live restreinte |
| **Live-Complete** | T4+ | enablers C + enablers D + UI operator | rampe élargie post-enablers |

Portée : noms de stages dans `build_order_registry`, specs Build-17, gates table, table de promotion capital, seams `live_light_runtime.py` / `LiveLightInput` / `LiveLightDecision` / `LiveLightRunSummary`.

**Ces noms sont gelés** et référencés dans 13+ sources doctrinales primaires (cf. spec `2026-04-21_manifest_registry_stage_naming_restore.md` §"Docs Governants").

---

## Arbitrage (pour référence future)

| Question | Réponse |
|---|---|
| Peut-on supprimer `Live-Light` du registry au nom de "no LIGHT profile" ? | **NON** — c'est un palier canonique, pas un profil |
| Peut-on renommer `UI Complete + Live-Complete` en "Live Extension" au nom de "no COMPLETE profile" ? | **NON** — "UI Complete + Live-Complete" est le titre littéral du spec Build-17 dédié |
| Peut-on laisser Build-12 = "Micro-live Light" ? | **NON** — doctrine dit toujours juste `"Micro-live"` sans suffixe (drift local du test) |
| Peut-on créer un profil "Live-Light" ? | **NON** — les paliers ne sont pas des profils ; seuls LIGHT et COMPLETE profils existent |
| Faut-il conserver `live_light_runtime.py` malgré la règle no-LIGHT-profile ? | **OUI** — le fichier est le seam runtime du palier Build-13, pas un artefact de profil |

---

## Nomenclature canonique (référence fixe)

```
Stages V5.3 :
  Build-11 : Shadow Runtime
  Build-12 : Micro-live
  Build-13 : Live-Light
  Build-14 : Governed Enablers
  Build-15 : Engine C
  Build-16 : Engine D
  Build-17 : UI Complete + Live-Complete

Profils V5.3 :
  LIGHT     (dev + CI only, jamais déployé)
  COMPLETE  (seul profil déployé, Shadow → Micro-live → Live)

Paliers Live (après Micro-live) :
  Live-Light     (T3+, enablers core)
  Live-Complete  (T4+, enablers C + D + UI)
```

---

## Anti-dérive — checklist avant tout renommage Light/Complete

Avant de renommer un symbole contenant `Light` ou `Complete`, vérifier **à la fois** :

1. Est-ce un **profil de déploiement** (artefact CI/config/build) ? → règle no-LIGHT-profile s'applique
2. Est-ce un **palier de rampe capital** ou un **stage de build** ? → règle no-LIGHT-profile NE s'applique PAS
3. Le symbole apparaît-il dans docs 20, 21, 22, whitebook, master, gates table, specs Build-17 ? → ne pas toucher sans arbitrage doctrinal
4. Le symbole est-il utilisé dans `src/protocols/` comme seam runtime ? → ne pas toucher

Si un doute subsiste : ouvrir un arbitrage Opus avant modification.

---

## Références

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` L11 — pipeline `Replay → Shadow → Micro-live → Live-Light`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` L240-242 — "Live-Light (T3+)"
- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` L364 — "Live-Light (T4+)"
- `docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` L2 — "UI Complete + Live-Complete Protocol"
- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md` L1492 — "Build-17 — UI Complete + Live-Complete"
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` L639 — 4 paliers "Shadow | Micro-live | Live-Light | Live-Complete"
- `docs/whitebook/V5_3_WHITE_BOOK_PART_1_DOCTRINE_ARCHITECTURE_AND_BUILD_STATE.md` L394 — "validation Live-Complete"
- CLAUDE.md §"Profile discipline (revised 2026-04-14)" — règle no-LIGHT-profile
- Memory `feedback_no_light_profile_doctrine.md` 2026-04-19 — portée profils uniquement
- Spec arbitrage B `2026-04-21_manifest_registry_stage_naming_restore.md` — fix registry
