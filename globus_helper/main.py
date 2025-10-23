"""Helper utilities for orchestrating Globus CLI transfers.

The `GlobusSync` class defined in this module keeps the imperative shell logic
for `globus transfer` in one place so that cron jobs or ad hoc bash scripts can
delegate the heavy lifting to Python. Configuration comes from either explicit
arguments, environment variables, or a combination of both, which keeps the
shell wrapper minimal and easier to audit.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Mapping, Optional, Sequence

import click

from .logging_config import setup_logging
from .transfer.main import copy_actigraphy_to_bids

ENV_SOURCE_ENDPOINT = "GLOBUS_SOURCE_ENDPOINT"
ENV_DEST_ENDPOINT = "GLOBUS_DEST_ENDPOINT"
ENV_SOURCE_PATH = "GLOBUS_SOURCE_PATH"
ENV_DEST_PATH = "GLOBUS_DEST_PATH"
ENV_LABEL = "GLOBUS_LABEL"
ENV_SYNC_LEVEL = "GLOBUS_SYNC_LEVEL"
ENV_NOTIFY = "GLOBUS_NOTIFY"
ENV_PRESERVE_MTIME = "GLOBUS_PRESERVE_MTIME"
ENV_DRY_RUN = "GLOBUS_DRY_RUN"
ENV_EXTRA_FLAGS = "GLOBUS_EXTRA_FLAGS"
ENV_CLI = "GLOBUS_CLI"

ENV_VAR_MAP = {
    "source_endpoint": ENV_SOURCE_ENDPOINT,
    "destination_endpoint": ENV_DEST_ENDPOINT,
    "destination_path": ENV_DEST_PATH,
    "source_path": ENV_SOURCE_PATH,
    "label": ENV_LABEL,
    "sync_level": ENV_SYNC_LEVEL,
    "notify": ENV_NOTIFY,
    "preserve_mtime": ENV_PRESERVE_MTIME,
    "dry_run": ENV_DRY_RUN,
}

setup_logging()
logger = logging.getLogger(__name__)


def _str_to_bool(value: Optional[str], *, default: bool) -> bool:
    """Convert a string environment variable into a boolean flag."""
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class GlobusSync:
    """Build and execute a `globus transfer` command.

    Parameters
    ----------
    source_endpoint:
        The Globus endpoint ID or alias that should act as the source.
        Typically sourced from the environment variable
        `GLOBUS_SOURCE_ENDPOINT`.
    destination_endpoint:
        The Globus endpoint ID or alias that should receive the files.
        Typically sourced from `GLOBUS_DEST_ENDPOINT`.
    destination_path:
        Absolute path on the destination endpoint where data should land.
    source_path:
        Path on the source endpoint to transfer. Defaults to `/`.
    label:
        Friendly label shown in the Globus dashboard and e-mail
        notifications.
    sync_level:
        Value passed to `--sync-level` (default: `mtime`).
    notify:
        Value passed to `--notify`. Set to `"off"` to suppress e-mails.
    preserve_mtime:
        Include `--preserve-mtime` when True.
    dry_run:
        Include `--dry-run` when True, useful for rehearsals.
    extra_flags:
        Additional flags appended verbatim to the command after the standard
        options. Each individual flag should be a separate list item.
    globus_command:
        Path or alias for the Globus CLI binary. Defaults to `globus`.
    """

    def __init__(
        self,
        source_endpoint: str,
        destination_endpoint: str,
        destination_path: str,
        *,
        source_path: str = "/",
        label: str = "NEU to UI sync",
        sync_level: str = "mtime",
        notify: str = "on",
        preserve_mtime: bool = True,
        dry_run: bool = False,
        extra_flags: Optional[Sequence[str]] = None,
        globus_command: str = "globus",
    ) -> None:
        if not source_endpoint:
            raise ValueError("source_endpoint must be provided")
        if not destination_endpoint:
            raise ValueError("destination_endpoint must be provided")
        if not destination_path:
            raise ValueError("destination_path must be provided")

        if not destination_path.startswith("/"):
            raise ValueError("destination_path must be absolute (start with '/')")
        if not source_path:
            raise ValueError("source_path must be provided")

        self.source_endpoint = source_endpoint
        self.destination_endpoint = destination_endpoint
        self.destination_path = destination_path
        self.source_path = source_path
        self.label = label
        self.sync_level = sync_level
        self.notify = notify
        self.preserve_mtime = preserve_mtime
        self.dry_run = dry_run
        self.extra_flags = list(extra_flags) if extra_flags else []
        self.globus_command = globus_command

    @classmethod
    def from_env(
        cls,
        *,
        env: Optional[Mapping[str, str]] = None,
        **overrides,
    ) -> "GlobusSync":
        """Create an instance, falling back to well-named environment variables.

        Parameters
        ----------
        env:
            Optional environment mapping. Defaults to `os.environ`.
        overrides:
            Keyword arguments that override environment values. Any key must
            match a parameter accepted by :meth:`__init__`.
        """

        env_mapping = env or os.environ

        params = {
            "source_endpoint": overrides.pop(
                "source_endpoint", env_mapping.get(ENV_SOURCE_ENDPOINT)
            ),
            "destination_endpoint": overrides.pop(
                "destination_endpoint", env_mapping.get(ENV_DEST_ENDPOINT)
            ),
            "destination_path": overrides.pop(
                "destination_path", env_mapping.get(ENV_DEST_PATH)
            ),
            "source_path": overrides.pop(
                "source_path", env_mapping.get(ENV_SOURCE_PATH, "/")
            ),
            "label": overrides.pop("label", env_mapping.get(ENV_LABEL, "NEU to UI sync")),
            "sync_level": overrides.pop(
                "sync_level", env_mapping.get(ENV_SYNC_LEVEL, "mtime")
            ),
            "notify": overrides.pop("notify", env_mapping.get(ENV_NOTIFY, "on")),
            "preserve_mtime": overrides.pop(
                "preserve_mtime",
                _str_to_bool(env_mapping.get(ENV_PRESERVE_MTIME), default=True),
            ),
            "dry_run": overrides.pop(
                "dry_run", _str_to_bool(env_mapping.get(ENV_DRY_RUN), default=False)
            ),
            "globus_command": overrides.pop(
                "globus_command", env_mapping.get(ENV_CLI, "globus")
            ),
        }

        extra_flags = overrides.pop("extra_flags", None)
        if extra_flags is None:
            raw_flags = env_mapping.get(ENV_EXTRA_FLAGS)
            params["extra_flags"] = shlex.split(raw_flags) if raw_flags else None
        else:
            params["extra_flags"] = list(extra_flags)

        if overrides:
            unexpected = ", ".join(sorted(overrides))
            raise TypeError(f"Unknown override(s): {unexpected}")

        missing = [
            key
            for key in ("source_endpoint", "destination_endpoint", "destination_path")
            if not params[key]
        ]
        if missing:
            detail = ", ".join(
                f"{key} (set via {ENV_VAR_MAP[key]})" for key in missing
            )
            raise ValueError(f"Missing required Globus configuration: {detail}")

        return cls(**params)

    def build_transfer_command(self) -> List[str]:
        """Return the `globus transfer` command as a list of arguments."""
        command = [
            self.globus_command,
            "transfer",
            "--recursive",
            "--sync-level",
            self.sync_level,
            "--label",
            self.label,
        ]
        if self.notify:
            command.extend(["--notify", self.notify])
        if self.preserve_mtime:
            command.append("--preserve-mtime")
        if self.dry_run:
            command.append("--dry-run")

        command.extend(self.extra_flags)
        command.append(f"{self.source_endpoint}:{self.source_path}")
        command.append(f"{self.destination_endpoint}:{self.destination_path}")

        logger.debug("Constructed globus command arguments: %s", command)
        return command

    def command_as_string(self) -> str:
        """Return a shell-ready representation of the transfer command."""
        return " ".join(shlex.quote(part) for part in self.build_transfer_command())

    def run(
        self,
        *,
        capture_output: bool = False,
        text: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Execute the transfer command via :func:`subprocess.run`."""
        command = self.build_transfer_command()
        logger.debug("Executing globus command: %s", command)
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
        )


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """Command-line helpers for Globus sync and actigraphy transfers."""


@cli.command("sync")
@click.option("--source-endpoint", help=f"Override {ENV_SOURCE_ENDPOINT}.")
@click.option("--dest-endpoint", help=f"Override {ENV_DEST_ENDPOINT}.")
@click.option("--source-path", help=f"Override {ENV_SOURCE_PATH}.")
@click.option("--dest-path", help=f"Override {ENV_DEST_PATH}.")
@click.option("--label", help=f"Override {ENV_LABEL}.")
@click.option(
    "--sync-level",
    type=click.Choice(["exists", "size", "mtime", "checksum"]),
    help=f"Override {ENV_SYNC_LEVEL}.",
)
@click.option("--notify", help=f"Override {ENV_NOTIFY}.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Force --dry-run regardless of environment configuration.",
)
@click.option(
    "--globus-command",
    help="Path or alias to the Globus CLI executable.",
)
@click.option(
    "--extra-flag",
    "extra_flags",
    multiple=True,
    help="Additional flag to append to the globus command. Can be used multiple times.",
)
@click.option(
    "--preserve-mtime",
    "preserve_mtime_flag",
    flag_value=True,
    default=None,
    help="Explicitly enable --preserve-mtime.",
)
@click.option(
    "--no-preserve-mtime",
    "preserve_mtime_flag",
    flag_value=False,
    help="Explicitly disable --preserve-mtime.",
)
@click.option(
    "--show-command",
    is_flag=True,
    help="Print the assembled command instead of executing it.",
)
def sync_command(
    *,
    source_endpoint: Optional[str],
    dest_endpoint: Optional[str],
    source_path: Optional[str],
    dest_path: Optional[str],
    label: Optional[str],
    sync_level: Optional[str],
    notify: Optional[str],
    dry_run: bool,
    globus_command: Optional[str],
    extra_flags: Sequence[str],
    preserve_mtime_flag: Optional[bool],
    show_command: bool,
) -> None:
    """Execute a Globus transfer using the local Globus CLI."""
    overrides = {}
    if source_endpoint:
        overrides["source_endpoint"] = source_endpoint
    if dest_endpoint:
        overrides["destination_endpoint"] = dest_endpoint
    if source_path:
        overrides["source_path"] = source_path
    if dest_path:
        overrides["destination_path"] = dest_path
    if label:
        overrides["label"] = label
    if sync_level:
        overrides["sync_level"] = sync_level
    if notify:
        overrides["notify"] = notify
    if dry_run:
        overrides["dry_run"] = True
    if globus_command:
        overrides["globus_command"] = globus_command
    if extra_flags:
        overrides["extra_flags"] = list(extra_flags)
    if preserve_mtime_flag is not None:
        overrides["preserve_mtime"] = preserve_mtime_flag

    logger.debug("CLI overrides: %s", overrides)

    try:
        sync = GlobusSync.from_env(**overrides)
    except Exception as exc:  # noqa: BLE001 - handled for CLI feedback
        logger.exception("Failed to initialise GlobusSync from CLI inputs")
        raise click.ClickException(str(exc)) from exc

    if show_command:
        command_str = sync.command_as_string()
        logger.info("Dry-run assembled command: %s", command_str)
        click.echo(command_str)
        return

    try:
        sync.run()
    except subprocess.CalledProcessError as exc:
        logger.exception("Globus transfer failed")
        raise click.ClickException(
            f"Globus transfer failed with exit code {exc.returncode}."
        ) from exc

    logger.info("Globus transfer completed successfully")


@cli.command("transfer")
@click.option(
    "--base-path",
    type=click.Path(file_okay=False, path_type=Path),
    help="Root containing both ne-dump/ and act-int-test/. Defaults to BASE_PATH env var.",
)
@click.option(
    "--dry-run/--apply",
    default=True,
    show_default=True,
    help="Preview files without copying by default; pass --apply to perform the copy.",
)
def transfer_command(
    *,
    base_path: Optional[Path],
    dry_run: bool,
) -> None:
    """Copy actigraphy CSVs into the BIDS-like layout."""
    kwargs = {"dry_run": dry_run}
    if base_path is not None:
        kwargs["base_path"] = base_path

    try:
        copied = copy_actigraphy_to_bids(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surfaced to CLI users
        logger.exception("Actigraphy transfer failed")
        raise click.ClickException(str(exc)) from exc

    action = "Would copy" if dry_run else "Copied"
    for source, destination in copied:
        click.echo(f"{action} {source} -> {destination}")

    logger.info("Actigraphy transfer complete (dry_run=%s)", dry_run)


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Program entry point compatible with console scripts."""
    args_list = list(argv) if argv is not None else None
    cli.main(args=args_list, prog_name="globus-helper", standalone_mode=False)


if __name__ == "__main__":  # pragma: no cover - convenience for module invocation
    try:
        main(sys.argv[1:])
    except click.ClickException as exc:
        click.echo(str(exc), err=True)
        sys.exit(exc.exit_code)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level guard
        logger.exception("Unhandled exception in globus-helper CLI")
        click.echo(f"Unhandled error: {exc}", err=True)
        sys.exit(1)
