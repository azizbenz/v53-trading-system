# Secrets Manager

Bounded sealed-secrets slice for `T2 / P0-4`.

## Scope

- seals plaintext YAML/JSON/text files into a typed JSON envelope
- uses Windows DPAPI with a required external `master.key` file as additional entropy
- keeps plaintext out of runtime logs and typed repr surfaces

## Current backend

- implemented now: `windows_dpapi_user`
- not implemented yet: `age`, `sops`, Linux VPS backend

This is an honest bounded step, not a fake cross-platform crypto claim.

## Workflow

1. generate a master key once:

```powershell
python -m secrets_manager gen-key "$HOME/.config/v53/master.key"
```

2. seal a plaintext file:

```powershell
python -m secrets_manager seal config/api.yml --key-path "$HOME/.config/v53/master.key"
```

3. optionally delete the plaintext immediately:

```powershell
python -m secrets_manager seal config/api.yml --key-path "$HOME/.config/v53/master.key" --delete-source
```

4. runtime loader:

```python
from secrets_manager import load

payload = load("config/api.yml.sealed.json", key_path="~/.config/v53/master.key")
```

## Invariants

- no secret value should be logged or serialized in clear text
- the master key file is never stored in the repo
- this slice does not claim Linux/VPS readiness yet
