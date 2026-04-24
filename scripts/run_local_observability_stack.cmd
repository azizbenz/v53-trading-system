@echo off
setlocal
cd /d "%~dp0.."
python ".\scripts\run_local_observability_stack.py" %*
endlocal
