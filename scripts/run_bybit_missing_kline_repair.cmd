@echo off
setlocal
cd /d "%~dp0.."
python -u ".\scripts\run_bybit_kline_recollection.py" --timeframes 1m,10m --kline-root "L:\klines" --orderbook-root "J:\.zip\bybit_v53_data\orderbook" --require-orderbook --report-root ".\tmp_bybit_missing_kline_repair" %*
endlocal
