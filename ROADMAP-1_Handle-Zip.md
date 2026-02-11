# Roadmap for current issue Handle Zip File

## Problem // Basic Solution
---
- NEU is having problems transferring the files in their normal directory format - we are temporarily allowing them to push a zip to dest
- We need to identify when a zip is in the ne-dump directory and then unzip this first (waiting until success with error checking)
- Then we proceed with the rest of the pipeline
  
## ROADMAP
1. Locate ne-dump path and integrate zip handling (source only)

- [ ] Update code/transfer/main.py to resolve ne_dump_path = BASE_PATH / "ne-dump" in the transfer flow.
- [ ] Add a CLI flag (e.g., --handle-zip) with help text and ENV fallback mirroring existing ENV_* patterns.

2. Detect zip vs. existing structure safely

- [ ] In code/transfer/main.py, when --handle-zip is set:
    - [ ] Scan ne_dump_path for .zip files.
    - [ ] Allow other non-directory files (metadata) to exist.
    - [ ] If any directory is present under ne_dump_path, abort with a clear error to avoid overwriting expected structure.
    - [ ] If no zip files are found, log and continue the normal pipeline (no failure).

3. Single-zip rule and error handling

- [ ] If more than one .zip is found, abort with a clear error (mention the filenames).
- [ ] If exactly one .zip exists, proceed to unzip into ne_dump_path.
- [ ] On any unzip failure, abort and report (no partial continuation).

4. Dry-run tree preview

- [ ] When --dry-run is set, do not unzip.
- [ ] Instead, produce a “tree-like” preview of the expected post-unzip layout inside ne_dump_path (e.g., list zip contents and show how they’d be placed).
- [ ] Ensure output is logged via the module logger, not print.

5. Unzip implementation

- [ ] Use Python’s zipfile (no external tool constraint).
- [ ] Extract into ne_dump_path.
- [ ] Keep the zip file in place after extraction.

6. Logging and user feedback

- [ ] Log the zip detection decision, errors, and extraction steps via logger.
- [ ] Ensure error messages include the absolute path to ne_dump_path and the zip filename.

7. CLI documentation

- [ ] Update README.md to document the new --handle-zip flag, behavior, and dry-run output notes.
- [ ] Mention that build outputs are not edited; source changes live under code/.