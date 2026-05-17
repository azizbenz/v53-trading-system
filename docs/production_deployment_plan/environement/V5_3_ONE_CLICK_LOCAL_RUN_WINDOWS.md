# V5.3 One-Click Local Run - Windows

## Commande unique

Depuis la racine du repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-V53LocalSolution.ps1
```

Ce wrapper unique enchaine:
- chargement des credentials Binance depuis `.env`
- lancement de la campagne Shadow gouvernee
- bootstrap de la stack locale Prometheus + Grafana
- lancement du serveur cockpit local
- ouverture du cockpit local comme surface principale

## Fichier exact pour l'API Binance

Le fichier local ou mettre l'API Binance est:

```text
E:\claude  v5.3\v53_trading_system\.env
```

Contenu minimal:

```dotenv
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

Regles:
- `.env` reste local et non tracke
- le launcher convertit ces valeurs en variables d'environnement canoniques
- aucun secret ne doit etre stocke dans `build\...` ni dans les JSON gouvernes

## Mode public sans credentials

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-V53LocalSolution.ps1 -PublicOnly
```

Dans ce cas:
- la campagne Shadow reste sur le rail public market-data
- aucun user-data stream authentifie n'est active

## Prerequis Grafana local

Le wrapper sait reutiliser:
- une stack deja en ecoute sur `127.0.0.1:3000` et `127.0.0.1:9090`

Sinon il sait demarrer la stack locale si les executables sont resolvables:
- `prometheus.exe`
- `grafana-server.exe`

Si besoin, passer les chemins explicites:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Run-V53LocalSolution.ps1 `
  -PrometheusExe "C:\Program Files\Prometheus\prometheus.exe" `
  -GrafanaServerExe "C:\Program Files\GrafanaLabs\grafana\bin\grafana-server.exe" `
  -GrafanaHome "C:\Program Files\GrafanaLabs\grafana"
```

## Surface principale apres lancement

La page d'atterrissage attendue est maintenant le cockpit:

```text
http://127.0.0.1:8080/
```

Depuis cette surface unique, la navigation expose:
- Trading
- Shadow
- VPS
- IA Lab
- Backtest
- Observability
- Logs

Grafana et Prometheus restent accessibles depuis la barre laterale du cockpit.

## Artefacts produits

- `build\run_v53_local_solution\launch.summary.json`
- `build\build11_live_websocket_campaign\service\shadow_vps_service_observability.prom`
- `.local_observability_stack\local_observability_stack.summary.json` si la stack locale utilise sa sortie par defaut

Le summary unifie contient aussi:
- `cockpit_url`
- `cockpit_log_path`
- `cockpit_pid`

## Doctrine

- aucun nouveau stage ou profile
- aucun bypass de Shadow
- aucun secret en clair dans les artefacts gouvernes
- le cockpit est la surface operateur par defaut
- Grafana et Prometheus restent des surfaces d'observabilite secondaires
