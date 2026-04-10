# Project instructions — MemPalace-aware Claude

Use MemPalace automatically at the start of each Claude session for this project.

MemPalace policy:
- treat MemPalace as the first external memory source for project history, prior decisions, audits, and continuity context
- prefer MemPalace lookup before broad repo exploration when the task may depend on earlier work
- if this project has already been mined into MemPalace, query it at session start using the project name or the matching wing
- if MemPalace returns relevant results, summarize the useful context briefly before making changes
- if MemPalace returns no palace, no wing, or no relevant project memory, say that explicitly

First-run behavior:
- if MemPalace is available globally but this project has not been initialized and mined yet, say that project memory is not ready yet
- recommend these commands:
  - `mempalace init <project-dir>`
  - `mempalace mine <project-dir>`
- do not claim project memory exists before those steps complete

Ongoing behavior:
- when asked about prior architecture choices, audits, handoffs, historical decisions, or earlier sessions, check MemPalace first
- when starting a substantial coding or audit task, recover project context from MemPalace before re-deriving it from scratch
- when MemPalace and the current code disagree, treat the current codebase as the source of truth and MemPalace as historical context
- do not use MemPalace as a replacement for reading the files you are about to edit

Response requirements:
- state explicitly whether MemPalace was checked for this project
- state explicitly whether project memory was found
- if memory was found, mention the wing used
- if memory was not found, say that the project must be initialized and mined first

Suggested opening pattern:
- `MemPalace check: performed`
- `MemPalace project memory: found for wing <wing>` or `not found`
- `Next source of truth: current codebase`
