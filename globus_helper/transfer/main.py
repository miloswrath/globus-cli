"""Transfer actigraphy CSVs into a BIDS-like layout.

File structure of the ne-dump on LSS (two layouts are supported)::

    # legacy layout (no dump folders)
    BASE_PATH/ne-dump/Actigraphy/<subject_id>_actigraphy/v<#>/<subject_id> (<date of recording>)RAW.csv

    # current layout with dumps A1–A4
    BASE_PATH/ne-dump/Actigraphy/A#/ <subject_id>_actigraphy/v<#>/<subject_id> (<date of recording>)RAW.csv

In the legacy layout, the version directory (`v0`, `v3`, `v5`) determines the
session number. In the dump-aware layout, the dump directory (`A1`–`A4`)
determines the session number while version directories are ignored for session
assignment.

The desired output is in a BIDS-inspired structure::

    BASE_PATH/act-int-test/sub-<subject_id>/accel/ses-<session_id>/sub-<subject_id>_ses-<session_id>_accel.csv

This module provides a helper that copies each actigraphy CSV into the target
layout using glob pattern matching. `BASE_PATH` is expected to be supplied via
environment variable when no explicit path is provided.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:
    from ..logging_config import setup_logging
except ImportError:  # pragma: no cover - allows running as a script
    from logging_config import setup_logging  # type: ignore

setup_logging()
logger = logging.getLogger(__name__)

VERSION_TO_SESSION = {"V0": "1", "V3": "2", "V5": "3"}
DUMP_TO_SESSION = {"A1": "1", "A2": "2", "A3": "3", "A4": "4"}


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
            logger.error("BASE_PATH environment variable is not set")
            raise EnvironmentError(
                "BASE_PATH environment variable must be set or base_path provided."
            )
        base_path = Path(raw_base)

    base_path = Path(base_path).expanduser().resolve()
    logger.debug("Resolved base path: %s (dry_run=%s)", base_path, dry_run)

    source_root = base_path / "ne-dump" / "Actigraph"
    destination_root = base_path / "act-int-test"

    logger.debug("Scanning source root: %s", source_root)

    if not source_root.is_dir():
        logger.error("Actigraphy source directory not found at %s", source_root)
        raise FileNotFoundError(f"Actigraphy source directory not found: {source_root}")

    copied: List[Tuple[Path, Path]] = []

    dump_dirs = [
        dump_dir
        for dump_dir in sorted(source_root.iterdir())
        if dump_dir.is_dir() and dump_dir.name in DUMP_TO_SESSION
    ]

    def _copy_csv(
        *, subject_id: str, session_id: str, csv_file: Path
    ) -> None:
        destination_dir = destination_root / f"sub-{subject_id}" / "accel" / f"ses-{session_id}"
        destination_file = destination_dir / f"sub-{subject_id}_ses-{session_id}_accel.csv"

        if not dry_run:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(csv_file, destination_file)

        logger.debug(
            "%s %s -> %s",
            "Would copy" if dry_run else "Copying",
            csv_file,
            destination_file,
        )
        copied.append((csv_file, destination_file))

    if dump_dirs:
        logger.debug("Detected dump-aware layout with %d dump directory(ies)", len(dump_dirs))
        for dump_dir in dump_dirs:
            session_id = DUMP_TO_SESSION[dump_dir.name]
            for subject_dir in sorted(dump_dir.glob("*_Actigraphy")):
                if not subject_dir.is_dir():
                    continue

                subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
                if not subject_id:
                    logger.debug(
                        "Skipping subject directory %s due to missing subject_id", subject_dir
                    )
                    continue

                logger.debug(
                    "Processing subject %s in %s (session=%s)", subject_id, subject_dir, session_id
                )

                for version_dir in sorted(subject_dir.iterdir()):
                    if not version_dir.is_dir():
                        continue

                    for csv_file in version_dir.glob("*RAW.csv"):
                        if csv_file.is_file():
                            _copy_csv(subject_id=subject_id, session_id=session_id, csv_file=csv_file)
    else:
        logger.debug("Detected legacy layout (no dump directories present)")
        for subject_dir in sorted(source_root.glob("*_Actigraphy")):
            if not subject_dir.is_dir():
                continue

            subject_id = subject_dir.name.split("_Actigraphy", 1)[0].strip()
            if not subject_id:
                logger.debug("Skipping subject directory %s due to missing subject_id", subject_dir)
                continue

            logger.debug("Processing subject %s in %s", subject_id, subject_dir)

            for version_dir in sorted(subject_dir.iterdir()):
                if not version_dir.is_dir():
                    continue

                session_id = VERSION_TO_SESSION.get(version_dir.name)
                if session_id is None:
                    logger.debug(
                        "Skipping version directory %s; no session mapping available",
                        version_dir,
                    )
                    continue

                for csv_file in version_dir.glob("*RAW.csv"):
                    if csv_file.is_file():
                        _copy_csv(
                            subject_id=subject_id, session_id=session_id, csv_file=csv_file
                        )

    logger.info("Identified %d file(s) for transfer (dry_run=%s)", len(copied), dry_run)
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
        logger.info("Transfer simulation complete (dry_run=%s)", args.dry_run)
    except Exception as exc:  # pragma: no cover - convenience for CLI usage
        logger.exception("Transfer operation failed")
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)
