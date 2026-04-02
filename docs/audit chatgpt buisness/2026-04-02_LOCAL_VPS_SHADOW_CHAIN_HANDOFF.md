# V5.3 Local VPS Shadow Chain Handoff
## Date
2026-04-02

## Objet
Ce document decrit la chaine de travail maintenant disponible pour le flux :

`local replay -> export fichiers -> import VPS -> shadow`

Il sert de memo operateur et de preuve de ce qui a ete implemente dans cette passe.

---

# 1. Principe retenu

Le backtest/replay se fait en local.

Les resultats sont exportes sous forme de fichiers gouvernes.

La VPS n'execute pas du code strategie arbitraire upload. Elle consomme :
- des artifacts
- des manifests
- des refs d'evidence
- des metadonnees de lineage

La meme base V5.3 est utilisee localement et sur VPS. La communication se fait par export/import de fichiers.

---

# 2. Ce qui existe maintenant

## 2.1 Export local

Le local produit :
- `review_export`
- `feature_bridge`
- `parity_diagnostics`
- `replay_metrics`
- `replay_dtr`
- `replay_run_manifest`
- sidecars de session et de guards

Scripts :
- [run_local_replay_export.py](../../scripts/run_local_replay_export.py)

Modules clefs :
- [artifact_exporter.py](../../src/local_replay_runtime/artifact_exporter.py)
- [replay_run_manifest.py](../../src/local_replay_runtime/replay_run_manifest.py)
- [replay_orchestrator.py](../../src/local_replay_runtime/replay_orchestrator.py)
- [runtime_evidence.py](../../src/local_replay_runtime/runtime_evidence.py)

## 2.2 Import VPS

L'import valide explicitement :
- presence des refs obligatoires
- coherence du manifest
- lineage / shared core
- prerequis de replay utile

Modules clefs :
- [contracts.py](../../src/backtest_artifact_import/contracts.py)
- [validators.py](../../src/backtest_artifact_import/validators.py)

## 2.3 Shadow

Le shadow produit et consomme :
- `runtime evidence`
- `shadow runtime evidence`
- verdict d'acceptation / refus

Modules clefs :
- [shadow_runtime.py](../../src/protocols/shadow_runtime.py)
- [shadow_runtime_evidence.py](../../src/protocols/shadow_runtime_evidence.py)
- [contracts.py](../../src/protocols/contracts.py)

## 2.4 Runner dedie

La chaine complete peut etre lancee par :
- [run_local_replay_shadow.py](../../scripts/run_local_replay_shadow.py)

## 2.5 Service VPS autonome

Le mode service VPS existe aussi maintenant :
- [run_shadow_vps_service.py](../../scripts/run_shadow_vps_service.py)

Il supporte :
- `--exports-root`
- `--raw-inputs-root`
- `--websocket-streams-root`
- `--live-websocket-config`

Le mode `live_websocket` natif s'appuie sur :
- [shadow_live_websocket.py](../../src/protocols/shadow_live_websocket.py)
- [shadow_websocket_ingest.py](../../src/protocols/shadow_websocket_ingest.py)
- le runtime Build-2 `websocket_gateway`

---

# 3. Capacites ajoutees

## 3.1 Session et chunks

Le replay local supporte :
- `chunk_count`
- `chunk_index`
- `run_all_chunks`
- `resume`
- reprise partielle des chunks manquants
- trace de session agregee

Modules :
- [replay_session_config.py](../../src/local_replay_runtime/replay_session_config.py)
- [replay_state_store.py](../../src/local_replay_runtime/replay_state_store.py)
- [replay_orchestrator.py](../../src/local_replay_runtime/replay_orchestrator.py)

## 3.2 Selection ciblee

Le replay local supporte aussi :
- `chunk-indices`
- `window-start-ms`
- `window-end-ms`

## 3.3 Guards

Des guards explicites existent pour :
- `performance_mode`
- `run_consistency`

Modules :
- [performance_mode_guard.py](../../src/local_replay_runtime/performance_mode_guard.py)
- [run_consistency_guard.py](../../src/local_replay_runtime/run_consistency_guard.py)

## 3.4 Sources de donnees

Le replay local peut maintenant partir :
- d'un dataset normalise
- d'un batch snapshots / events historiques

Modules :
- [historical_data_gateway.py](../../src/local_replay_runtime/historical_data_gateway.py)
- [historical_snapshot_loader.py](../../src/local_replay_runtime/historical_snapshot_loader.py)
- [replay_event_router.py](../../src/local_replay_runtime/replay_event_router.py)
- [replay_clock.py](../../src/local_replay_runtime/replay_clock.py)
- [shadow_execution_simulator.py](../../src/local_replay_runtime/shadow_execution_simulator.py)

---

# 4. Commandes operateur

## 4.1 Export local simple

```powershell
cd "E:\claude  v5.3\v53_trading_system"
python scripts/run_local_replay_export.py --output-dir build\local_replay_export_real --dataset-path <ton_dataset.json> --strategy-id <strategy_id> --strategy-version <version> --lineage-version <lineage>
```

## 4.2 Export local multi-chunks

```powershell
cd "E:\claude  v5.3\v53_trading_system"
python scripts/run_local_replay_export.py --output-dir build\local_replay_real --dataset-path <ton_dataset.json> --strategy-id <strategy_id> --strategy-version <version> --lineage-version <lineage> --chunk-count 8 --run-all-chunks
```

## 4.3 Resume multi-chunks

```powershell
cd "E:\claude  v5.3\v53_trading_system"
python scripts/run_local_replay_export.py --output-dir build\local_replay_real --run-id <meme_run_id> --strategy-id <strategy_id> --strategy-version <version> --lineage-version <lineage> --dataset-path <ton_dataset.json> --chunk-count 8 --run-all-chunks --resume
```

## 4.4 Import VPS + shadow

```powershell
cd "E:\claude  v5.3\v53_trading_system"
python scripts/run_local_replay_shadow.py --output-dir build\local_replay_shadow_real --export-dir build\local_replay_real
```

## 4.5 Service VPS live_websocket natif

```powershell
cd "E:\claude  v5.3\v53_trading_system"
python scripts/run_shadow_vps_service.py --service-dir build\shadow_vps_service --orchestrator-output-dir build\shadow_vps_orchestrator --shadow-output-dir build\shadow_session --live-websocket-config build\shadow_live_websocket_config.json --live-captures-root build\shadow_live_captures --auto-exports-root build\shadow_auto_exports
```

---

# 5. Fichiers produits importants

Selon le mode, la chaine peut produire :
- `replay_run_manifest.json`
- `review_export.md`
- `feature_bridge.json`
- `parity_diagnostics.json`
- `replay_metrics.json`
- `replay_dtr.jsonl`
- `performance_mode_guard.json`
- `run_consistency_guard.json`
- `replay_chunk_session.json`
- `local_replay_shadow.import_summary.json`
- `local_replay_shadow.local_replay_evidence.json`
- `local_replay_shadow.shadow_runtime_evidence.json`
- `local_replay_shadow.shadow_summary.json`

---

# 6. Statut honnete

Ce que la chaine sait faire aujourd'hui :
- produire un export local gouverne
- materialiser un manifest de run
- verifier les refs obligatoires
- faire un import VPS gouverne
- produire une evidence `LOCAL_REPLAY`
- produire une evidence `SHADOW`
- rendre un verdict shadow sur un run gouverne
- faire tourner un service VPS autonome avec capture `live_websocket` native codee

Verdict :
- `OPERATIONAL FOR GOVERNED REPLAY / SHADOW CHAIN`

Ce que la chaine n'implique pas encore automatiquement :
- que tous les builds Shadow aval soient clos `ALIGNED`
- qu'on ait deja une equivalence prod totale pour tous les cas operateur
- que le mode `live_websocket` ait deja ete smoke contre le vrai reseau exchange dans cet environnement

---

# 7. Point important a conserver

Le sens exact du flux est :
- on teste et exporte localement
- on importe les fichiers sur la VPS
- on continue la gouvernance en `SHADOW`

On ne pousse pas un code strategie arbitraire vers la VPS comme plugin libre.
On pousse un resultat gouverne, versionne, trace et verifiable.

