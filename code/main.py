"""Helper utilities for orchestrating Globus CLI transfers.

The `GlobusSync` class defined in this module keeps the imperative shell logic
for `globus transfer` in one place so that cron jobs or ad hoc bash scripts can
delegate the heavy lifting to Python. Configuration comes from either explicit
arguments, environment variables, or a combination of both, which keeps the
shell wrapper minimal and easier to audit.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from typing import List, Mapping, Optional, Sequence

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
        return subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point that can be hooked directly from Bash."""
    parser = argparse.ArgumentParser(
        description="Execute a Globus transfer using the local Globus CLI."
    )
    parser.add_argument("--source-endpoint", help="Override GLOBUS_SOURCE_ENDPOINT.")
    parser.add_argument("--dest-endpoint", help="Override GLOBUS_DEST_ENDPOINT.")
    parser.add_argument("--source-path", help="Override GLOBUS_SOURCE_PATH.")
    parser.add_argument("--dest-path", help="Override GLOBUS_DEST_PATH.")
    parser.add_argument("--label", help="Override GLOBUS_LABEL.")
    parser.add_argument(
        "--sync-level",
        choices=["exists", "size", "mtime", "checksum"],
        help="Override GLOBUS_SYNC_LEVEL.",
    )
    parser.add_argument("--notify", help="Override GLOBUS_NOTIFY.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force --dry-run regardless of environment configuration.",
    )
    parser.add_argument(
        "--globus-command",
        help="Path or alias to the Globus CLI executable.",
    )
    parser.add_argument(
        "--extra-flag",
        dest="extra_flags",
        action="append",
        default=None,
        help="Additional flag to append to the globus command. Can be used multiple times.",
    )
    parser.set_defaults(preserve_mtime=None)
    preserve_group = parser.add_mutually_exclusive_group()
    preserve_group.add_argument(
        "--preserve-mtime",
        dest="preserve_mtime",
        action="store_true",
        help="Explicitly enable --preserve-mtime.",
    )
    preserve_group.add_argument(
        "--no-preserve-mtime",
        dest="preserve_mtime",
        action="store_false",
        help="Explicitly disable --preserve-mtime.",
    )
    parser.add_argument(
        "--show-command",
        action="store_true",
        help="Print the assembled command instead of executing it.",
    )

    args = parser.parse_args(argv)

    overrides = {}
    if args.source_endpoint:
        overrides["source_endpoint"] = args.source_endpoint
    if args.dest_endpoint:
        overrides["destination_endpoint"] = args.dest_endpoint
    if args.source_path:
        overrides["source_path"] = args.source_path
    if args.dest_path:
        overrides["destination_path"] = args.dest_path
    if args.label:
        overrides["label"] = args.label
    if args.sync_level:
        overrides["sync_level"] = args.sync_level
    if args.notify:
        overrides["notify"] = args.notify
    if args.dry_run:
        overrides["dry_run"] = True
    if args.globus_command:
        overrides["globus_command"] = args.globus_command
    if args.extra_flags is not None:
        overrides["extra_flags"] = args.extra_flags
    if args.preserve_mtime is not None:
        overrides["preserve_mtime"] = args.preserve_mtime

    sync = GlobusSync.from_env(**overrides)

    if args.show_command:
        print(sync.command_as_string())
        return 0

    try:
        sync.run()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(
            f"Globus transfer failed with exit code {exc.returncode}.\n"
        )
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
