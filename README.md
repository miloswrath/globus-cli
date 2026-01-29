# Globus Sync Helper

Globus Sync Helper packages our Globus transfer automation and actigraphy reshaping utilities behind a single Click-powered CLI (`globus-helper`). The tool builds repeatable Globus CLI commands, records dry-run output for auditing, and reshapes actigraphy exports into the BIDS-inspired layout used downstream.

## Prerequisites

- Python 3.9+
- Globus CLI installed and authenticated for the account running transfers

> REQUIRED SCOPES
> - manage_collection
> - set_gcs_attributes

### Install and Configure the Globus CLI

1. Install the Globus CLI (choose one):
   ```bash
   pipx install globus-cli
   # or
   pip install --user globus-cli
   ```
2. Log in so the CLI can submit transfers on your behalf:
   ```bash
   globus login
   ```
3. (Optional) Verify credentials:
   ```bash
   globus session show
   ```

Official documentation provides platform-specific guidance and troubleshooting: https://docs.globus.org/cli/

## Installation

Install dependencies and register the console script either with uv or pip.

```bash
# uv (creates .venv by default)
uv pip install --editable .

# pip (activate your virtualenv first)
pip install --editable .
```

To install only runtime dependencies without editable mode, use `uv pip install -r requirements.txt` or `pip install -r requirements.txt`. Developers can add `-r requirements-dev.txt` for pytest.

## Configuration

Populate these environment variables before running Globus transfers:

- `GLOBUS_SOURCE_ENDPOINT`
- `GLOBUS_DEST_ENDPOINT`
- `GLOBUS_SOURCE_PATH` (defaults to `/`)
- `GLOBUS_DEST_PATH`
- `GLOBUS_LABEL` (defaults to `NEU to UI sync`)
- `GLOBUS_SYNC_LEVEL` (defaults to `mtime`)
- `GLOBUS_NOTIFY` (`on`, `off`, or `failed`; defaults to `on`)
- `GLOBUS_PRESERVE_MTIME` (`true`/`false`; defaults to `true`)
- `GLOBUS_DRY_RUN` (`true`/`false`; defaults to `false`)
- `GLOBUS_EXTRA_FLAGS` (optional string of additional CLI flags)
- `GLOBUS_CLI` (override the `globus` executable path)

For the actigraphy workflow, supply `BASE_PATH` pointing at the shared storage root containing both `ne-dump/` and the desired `act-int-test/` directory.

## Usage

### Step 1: Inspect the Planned Globus Transfer

```bash
globus-helper sync --show-command
```

Override settings at the command line when needed:

```bash
globus-helper sync \
  --dest-path "/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump" \
  --dry-run
```

### Step 2: Execute the Transfer

Once satisfied with the dry run, drop `--dry-run` to launch the Globus task:

```bash
globus-helper sync
```

Failures return a non-zero exit code and bubble up the Globus CLI output for troubleshooting.

### Step 3: Reshape Actigraphy Files

Use the same CLI to mirror the actigraphy reshaping workflow. Dry-run mode previews the mappings:

```bash
BASE_PATH=/path/to/share globus-helper transfer --dry-run
```

Remove `--dry-run` (or pass `--apply`) to copy files into the BIDS-like layout:

```bash
BASE_PATH=/path/to/share globus-helper transfer --apply
```

The command prints each `(source -> destination)` pair so you can capture logs or perform manual verification.

## Automating From Bash

Wrap the CLI in scripts or cron jobs. Example sync script:

```bash
#!/usr/bin/env bash
set -euo pipefail

export GLOBUS_SOURCE_ENDPOINT="686bbc3e-08f7-46cf-95f8-7539e6fee972"
export GLOBUS_DEST_ENDPOINT="39dd0982-d784-11e6-9cd4-22000a1e3b52"
export GLOBUS_DEST_PATH="/Shared/vosslabhpc/Projects/BOOST/InterventionStudy/3-experiment/data/ne-dump"

globus-helper sync --show-command  # Optional rehearsal
globus-helper sync
```

Adjust endpoints, source/destination paths, or additional flags to match the dataset you are moving. Because `globus-helper` reads environment variables, scripts stay concise and shareable across environments.

## Further Reading

- Globus CLI reference: https://docs.globus.org/cli/
- Actigraphy transfer implementation: `code/transfer/main.py`
- Logging configuration: `code/logging_config.py`
