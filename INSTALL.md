# INSTALL — prérequis avant lancement (PC dev + VPS)

Ce qu'il faut installer **avant** de lancer la solution V5.3, sur un poste de
développement (PC Windows) **ou** la VPS (Linux). À jour 2026-06-03.

> ⚠️ Le `pyproject.toml` a longtemps sous-déclaré ses dépendances : `pyarrow`,
> `orjson` et `httpx` étaient **importés par le runtime mais absents** de la liste
> (un `pip install .` neuf ne tournait pas). C'est corrigé — ce doc est la
> référence opérationnelle.

---

## 1. Python

- **Version requise** : `>= 3.12` (testé en CI/dev sur **3.14**).
- Vérifier : `python --version`.

## 2. Dépendances runtime

`pip install .` installe tout. Mais selon le **chemin exécuté**, le minimum diffère :

### 2a. CORE — requis pour TOUT run, y compris backtest (A2/B1/B2)

| Paquet | Rôle | Floor |
|---|---|---|
| `pydantic` | contrats typés (modèles, manifestes) | `>=2.0,<3.0` |
| `pyarrow` | cœur colonnaire in-RAM (fenêtres/features, parquet, ipc) — **import dur** | `>=14.0` |
| `orjson` | parser JSON C — parse trades A2 **~2.2× plus rapide** (hotspot) ; fallback stdlib si absent | `>=3.9` |
| `pyyaml` | calibration / config YAML | `>=6.0` |

> **Sans `pyarrow` rien ne démarre** (import au chargement). `orjson` a un fallback
> gracieux (correct mais ~2× plus lent) — recommandé pour la perf A2. Un poste de
> **backtest pur** peut tourner avec ces 4 seulement.

### 2b. LIVE — requis en plus pour Shadow / Micro-live / Live (VPS)

| Paquet | Rôle | Floor |
|---|---|---|
| `keyring` | secrets (tokens, clés) — jamais en clair | `>=25.0,<26.0` |
| `websocket-client` | ingestion live (gateway WS) | `>=1.8,<2.0` |
| `httpx` | REST (bootstrap snapshot, API venue) | `>=0.27` |

> La **VPS** (Shadow→Live) a besoin de CORE **+** LIVE. Le backtest seul n'importe
> pas ces 3 au chargement (chemins live/secrets uniquement).

## 3. Dépendances optionnelles

| Groupe | Paquet | Quand |
|---|---|---|
| `ml` | `lightgbm>=4.6,<5.0` | uniquement pour l'entraînement / l'edge model ML (Build-14). Pas requis pour Replay/Shadow sans ML. |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy` | tests + lint + typecheck (dev/CI seulement). |

## 4. Outils système (optionnels, dev seulement)

- **poppler / `pdftoppm`** : seulement pour lire des PDF via l'outil de dev (analyse de docs).
  - PC Windows : `choco install poppler` (ou binaire poppler dans le PATH).
  - VPS Debian/Ubuntu : `sudo apt-get install -y poppler-utils`.
  - **Non requis** pour exécuter la solution de trading.

---

## 5. Installation — PC (Windows)

```powershell
# depuis la racine du repo (E:\claude  v5.3\v53_trading_system)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .            # runtime
pip install -e ".[dev]"     # + tests/lint (optionnel)
pip install -e ".[ml]"      # + LightGBM (optionnel, ML)
```

## 6. Installation — VPS (Linux Debian/Ubuntu)

```bash
sudo apt-get update && sudo apt-get install -y python3-venv build-essential
cd /chemin/vers/v53_trading_system
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .            # runtime (pyarrow + orjson incluent des wheels Linux)
pip install -e ".[ml]"      # optionnel ML
```

> `pyarrow` et `orjson` fournissent des wheels binaires pour Windows et Linux
> x86_64 → pas de compilation nécessaire dans les cas normaux.

---

## 7. Vérification (smoke test, avant tout run)

```bash
python - <<'PY'
import sys, importlib
print("python", sys.version.split()[0])
core = ["pydantic", "pyarrow", "orjson", "yaml"]
live = ["keyring", "websocket", "httpx"]
missing = [m for m in core if importlib.util.find_spec(m) is None]
assert not missing, f"CORE manquant: {missing} -> pip install ."
import pyarrow, orjson
print("pyarrow", pyarrow.__version__, "| orjson", orjson.__version__)
print("LIVE present:", [m for m in live if importlib.util.find_spec(m)])
sys.path.insert(0, "src")
from local_replay_runtime.strategy_ladder_arrow_window import load_silver_table  # noqa
from local_replay_runtime.strategy_ladder_economic_provenance import _fast_json_loads
print("orjson actif:", _fast_json_loads is orjson.loads)
print("OK — CORE runtime satisfait (backtest). Pour la VPS: ajouter LIVE.")
PY
```

Sortie attendue : versions + `OK — CORE runtime satisfait`. Si `orjson actif: False`
→ fallback stdlib (corriger via `pip install orjson` pour la perf). Sur la VPS,
`LIVE present` doit lister `keyring`, `websocket`, `httpx`.

---

## 8. Versions testées (référence)

| | Version |
|---|---|
| Python | 3.14.3 |
| pyarrow | 23.0.1 |
| orjson | 3.11.8 |
| pydantic | 2.x |
