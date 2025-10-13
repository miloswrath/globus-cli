# Repository Guidelines

## Project Structure & Module Organization
The Python package lives in `code/`, with `code/main.py` assembling Globus CLI transfers and `code/transfer/main.py` shaping actigraphy outputs into the BIDS-inspired layout. Shared logging helpers are in `code/logging_config.py`, while Bash entry points land in `code/sh/` for cron or interactive use. Add new utilities beside these modules, and stage automated checks in a future `tests/` directory at the repo root. Environment scaffolding for contributors is defined in `flake.nix`, so keep Nix adjustments isolated there.

## Build, Test, and Development Commands
Enter the curated toolchain with `nix develop` (or `direnv allow` if you prefer auto-loading). Run the primary sync helper using `python -m code.main`, or inspect the generated command safely through `python -m code.main --show-command`. Exercise the actigraphy pipeline via `BASE_PATH=/path/to/share python -m code.transfer.main --dry-run` before copying real files. When you are ready to execute a transfer, drop the `--dry-run` flag and confirm the Globus CLI is authenticated for the current user.

## Dependency Management
Install runtime dependencies with either `uv pip install -r requirements.txt` or `pip install -r requirements.txt`. For contributor tooling, add `-r requirements-dev.txt` to pull in pytest. Package metadata also lives in `pyproject.toml`, so `uv pip install .` or `pip install -e .` remains valid when you need editable installs.

## Coding Style & Naming Conventions
Match the existing PEP 8 layout: four-space indents, 100-character soft limits, and double-quoted strings for user-facing text. Keep modules typed (see the `typing` imports) and prefer `pathlib.Path` for filesystem work. Use module-level `logger = logging.getLogger(__name__)` instead of bare `print`. When extending CLI surfaces, provide argparse help text and environment-variable fallbacks mirroring the established `ENV_*` constants.

## Testing Guidelines
There is no automated suite yet, so favour pure functions and dry-run paths that are easy to exercise. Place new tests under `tests/` using `pytest`, mocking subprocess calls from `GlobusSync` and filesystem writes in `code.transfer.main`. Run the suite with `pytest` (optionally `pytest -k globus` for focused checks), and record the command in your pull request. For manual verification, rely on `--show-command` and `--dry-run` to avoid triggering irreversible transfers.

## Commit & Pull Request Guidelines
Follow the imperative, one-line style already in history (`Add Globus sync helper and actigraphy transfer tooling`). Include concise bodies when rationale or roll-back steps help reviewers. Open pull requests with a summary, configuration notes (e.g., which `GLOBUS_*` or `BASE_PATH` values you used), and screenshots or command transcripts when behaviour changed. List any remaining risks, such as untested transfer scenarios, so maintainers can plan follow-up work.
