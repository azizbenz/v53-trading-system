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
