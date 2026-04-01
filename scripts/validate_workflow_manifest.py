#!/usr/bin/env python3
"""
Validate canonical n8n workflow manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    workflows_root = root / "n8n_workflows"
    manifest_path = workflows_root / "canonical_manifest.json"

    if not manifest_path.exists():
        print("ERROR: Missing manifest file n8n_workflows/canonical_manifest.json")
        return 1

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    workflows = data.get("workflows", [])
    expected_count = int(data.get("workflow_count", 0))

    if expected_count != len(workflows):
        print(
            f"ERROR: Manifest workflow_count mismatch "
            f"(declared={expected_count}, actual={len(workflows)})"
        )
        return 1

    seen = set()
    for item in workflows:
        path = item.get("path")
        expected_hash = item.get("sha256")
        if not path or not expected_hash:
            print(f"ERROR: Invalid manifest entry: {item}")
            return 1
        if path in seen:
            print(f"ERROR: Duplicate path in manifest: {path}")
            return 1
        seen.add(path)

        workflow_file = workflows_root / path
        if not workflow_file.exists():
            print(f"ERROR: Manifest path does not exist: {path}")
            return 1
        actual_hash = sha256_of(workflow_file)
        if actual_hash != expected_hash:
            print(
                f"ERROR: Hash mismatch for {path}\n"
                f"  expected: {expected_hash}\n"
                f"  actual:   {actual_hash}"
            )
            return 1

    active_files = {
        p.relative_to(workflows_root).as_posix()
        for p in workflows_root.rglob("*.json")
        if "archive" not in p.parts and p.name != "canonical_manifest.json"
    }
    manifest_files = {item["path"] for item in workflows}
    missing_in_manifest = sorted(active_files - manifest_files)
    missing_on_disk = sorted(manifest_files - active_files)

    if missing_in_manifest:
        print("ERROR: Active workflow files missing from manifest:")
        for path in missing_in_manifest:
            print(f"  - {path}")
        return 1
    if missing_on_disk:
        print("ERROR: Manifest entries not found on disk:")
        for path in missing_on_disk:
            print(f"  - {path}")
        return 1

    print(f"Manifest validation passed ({len(workflows)} workflows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
