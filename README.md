## Globus Sync Helper

This project keeps the Globus CLI invocation logic in `code/main.py` so we can call it from cron jobs or ad-hoc shell scripts without duplicating options.

### Requirements
- Python 3.9+
- Globus CLI installed and authenticated for the user executing transfers

### Configuration
Populate these environment variables before running the helper:
- `GLOBUS_SOURCE_ENDPOINT`
- `GLOBUS_DEST_ENDPOINT`
- `GLOBUS_SOURCE_PATH` (defaults to `/` if unset)
- `GLOBUS_DEST_PATH`
- `GLOBUS_LABEL` (defaults to `NEU to UI sync`)
- `GLOBUS_SYNC_LEVEL` (defaults to `mtime`)
- `GLOBUS_NOTIFY` (`on`, `off`, or `failed`; defaults to `on`)
- `GLOBUS_PRESERVE_MTIME` (`true`/`false`; defaults to `true`)
- `GLOBUS_DRY_RUN` (`true`/`false`; defaults to `false`)
- `GLOBUS_EXTRA_FLAGS` (optional string of additional CLI flags)
- `GLOBUS_CLI` (override the `globus` executable path)

### Quick Start
Run the Python entry point directly:

```bash
python -m code.main
```

To confirm the generated command without executing it:

```bash
python -m code.main --show-command
```

Override individual arguments via flags as needed:

```bash
python -m code.main \
  --dest-path "/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump" \
  --dry-run
```

### Using From Bash
Wrap the helper in your script (e.g., `code/sh/sync.sh`) and delegate the actual transfer to Python:

```bash
#!/usr/bin/env bash
set -euo pipefail

export GLOBUS_SOURCE_ENDPOINT="686bbc3e-08f7-46cf-95f8-7539e6fee972"
export GLOBUS_DEST_ENDPOINT="39dd0982-d784-11e6-9cd4-22000a1e3b52"
export GLOBUS_DEST_PATH="/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump"

python -m code.main
```

Replace the endpoint IDs and destination path as required, and add optional overrides (such as `--dry-run`) to the final command when testing.

## Actigraphy Transfer

`code/transfer/main.py` converts the raw actigraphy dump into the BIDS-like layout expected by downstream tooling.

### Configuration
- Set `BASE_PATH` to the common root that contains both `ne-dump/Actigraphy` and the target `act-int-test` directory. The script will create the required BIDS folders as needed.

### Usage
Run the helper directly to copy files and echo each source/destination pair:

```bash
BASE_PATH=/path/to/share python -m code.transfer.main
```

Add `--dry-run` to verify the mapping without writing files, or `--base-path` to override `BASE_PATH`:

```bash
python -m code.transfer.main --base-path /path/to/share --dry-run
```

You can also import and call `copy_actigraphy_to_bids()` from another script to get the list of copied `(source, destination)` paths for logging or testing.
