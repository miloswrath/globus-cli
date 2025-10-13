"""Transfer actigraphy CSVs into a BIDS-like layout.

File structure of the ne-dump on LSS::

    BASE_PATH/ne-dump/Actigraphy/<subject_id>_actigraphy/v<#>/<subject_id> (<date of recording>)RAW.csv

where `<#>` is one of `0`, `3`, or `5`, there is a literal space between
`<subject_id>` and the parenthesised date, and the version directory maps to a
session:

- `v0` → `ses-1`
- `v3` → `ses-2`
- `v5` → `ses-3`

The desired output is in a BIDS-inspired structure::

    BASE_PATH/act-int-test/sub-<subject_id>/accel/ses-<session_id>/sub-<subject_id>_ses-<session_id>_accel.csv

This module provides a helper that copies each actigraphy CSV into the target
layout using glob pattern matching. `BASE_PATH` is expected to be supplied via
environment variable when no explicit path is provided.
"""

from __future__ import annotations

import os
import shutil
import sys
import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

VERSION_TO_SESSION = {"v0": "1", "v3": "2", "v5": "3"}


def copy_actigraphy_to_bids(
    base_path: Optional[Path] = None, *, dry_run: bool = False
) -> List[Tuple[Path, Path]]:
    """Copy the actigraphy CSVs into a BIDS-compliant directory structure.

    Parameters
    ----------
    base_path:
        Optional base directory. If omitted, the value of the `BASE_PATH`
        environment variable is used.
    dry_run:
        When True, simulate the copy without creating directories or writing
        files. The returned list still contains the source and intended
        destination paths.

    Returns
    -------
    list[tuple[pathlib.Path, pathlib.Path]]
        A list of `(source, destination)` pairs for the files that were copied.

    Raises
    ------
    EnvironmentError
        If `BASE_PATH` is not provided via argument or environment.
    FileNotFoundError
        If the expected source directory does not exist.
    """

    if base_path is None:
        raw_base = os.environ.get("BASE_PATH")
        if not raw_base:
            raise EnvironmentError(
                "BASE_PATH environment variable must be set or base_path provided."
            )
        base_path = Path(raw_base)

    base_path = Path(base_path).expanduser().resolve()
    source_root = base_path / "ne-dump" / "Actigraph"
    destination_root = base_path / "act-int-test"

    if not source_root.is_dir():
        raise FileNotFoundError(f"Actigraphy source directory not found: {source_root}")

    copied: List[Tuple[Path, Path]] = []

    for subject_dir in sorted(source_root.glob("*_Actigraphy")):
        if not subject_dir.is_dir():
            continue

        subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
        if not subject_id:
            continue

        for version_dir in sorted(subject_dir.iterdir()):
            if not version_dir.is_dir():
                continue

            session_id = VERSION_TO_SESSION.get(version_dir.name)
            if session_id is None:
                continue

            for csv_file in version_dir.glob("*RAW.csv"):
                if not csv_file.is_file():
                    continue

                destination_dir = (
                    destination_root / f"sub-{subject_id}" / "accel" / f"ses-{session_id}"
                )
                destination_file = (
                    destination_dir / f"sub-{subject_id}_ses-{session_id}_accel.csv"
                )

                if not dry_run:
                    destination_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(csv_file, destination_file)

                copied.append((csv_file, destination_file))

    return copied


def iter_transferred_files(
    *, base_path: Optional[Path] = None, dry_run: bool = False
) -> Iterable[Tuple[Path, Path]]:
    """Convenience generator yielding the results of `copy_actigraphy_to_bids`."""
    for result in copy_actigraphy_to_bids(base_path=base_path, dry_run=dry_run):
        yield result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copy actigraphy CSVs into the BIDS-like directory structure."
    )
    parser.add_argument(
        "--base-path",
        help="Root directory that contains ne-dump/Actigraphy (defaults to BASE_PATH).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the files that would be copied without modifying the filesystem.",
    )
    args = parser.parse_args()

    kwargs = {"dry_run": args.dry_run}
    if args.base_path:
        kwargs["base_path"] = Path(args.base_path)

    try:
        for source, destination in iter_transferred_files(**kwargs):
            action = "Would copy" if args.dry_run else "Copied"
            print(f"{action} {source} -> {destination}")
    except Exception as exc:  # pragma: no cover - convenience for CLI usage
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
