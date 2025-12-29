#!/usr/bin/env python3
"""
Sync a target JSON's nth dialog with the first dialog from popup.json.

Usage:
  python dialog_sync.py <target_json> <index>

Behavior:
  - Reads source dialogs from popup.json in the same directory (can be changed via --source).
  - Copies the first dialog (visitTemplates[0].dialogs[0]) from source.
  - Ensures the target has visitTemplates up to <index>; creates empty templates if needed.
  - Replaces the first dialog of visitTemplates[<index>]; if none exists, it is created.
  - Preserves any other fields (e.g., openApp) already present in that template.
  - Writes back pretty-printed JSON; errors are not silently ignored.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SOURCE = Path(__file__).with_name("popup.json")


class DialogSyncError(Exception):
    """Custom error for sync failures."""


def load_json(path: Path, create_default: bool = False) -> Dict[str, Any]:
    if not path.exists():
        if create_default:
            return {"resetCounter": True, "visitTemplates": []}
        raise DialogSyncError(f"File not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise DialogSyncError(f"Invalid JSON in {path}: {exc}") from exc


def get_source_dialog(source_path: Path) -> Dict[str, Any]:
    data = load_json(source_path)
    try:
        return data["visitTemplates"][0]["dialogs"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise DialogSyncError(
            f"Source {source_path} lacks visitTemplates[0].dialogs[0]"
        ) from exc


def ensure_template(data: Dict[str, Any], index: int) -> Dict[str, Any]:
    if index < 0:
        raise DialogSyncError("Index must be non-negative")

    visit_templates: List[Dict[str, Any]] = data.setdefault("visitTemplates", [])
    while len(visit_templates) <= index:
        visit_templates.append({"dialogs": []})
    template = visit_templates[index]
    if "dialogs" not in template or not isinstance(template["dialogs"], list):
        template["dialogs"] = []
    return template


def replace_first_dialog(
    target_data: Dict[str, Any], dialog: Dict[str, Any], index: int
) -> None:
    template = ensure_template(target_data, index)
    dialog_copy = copy.deepcopy(dialog)
    if template["dialogs"]:
        template["dialogs"][0] = dialog_copy
    else:
        template["dialogs"].append(dialog_copy)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        raise DialogSyncError(f"Failed to write {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync target JSON's nth dialog with the first dialog from popup.json."
    )
    parser.add_argument("target", type=Path, help="Target JSON file to update")
    parser.add_argument(
        "index", type=int, help="0-based visitTemplates index to replace"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Source JSON (default: popup.json in current directory)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source_dialog = get_source_dialog(args.source)
        target_data = load_json(args.target, create_default=True)
        replace_first_dialog(target_data, source_dialog, args.index)
        write_json(args.target, target_data)
    except DialogSyncError as exc:
        print(f"[error] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
