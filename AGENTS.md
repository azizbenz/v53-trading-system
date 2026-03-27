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
