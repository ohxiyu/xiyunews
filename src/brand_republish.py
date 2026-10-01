"""Migrate self links in existing published JSON without AI or news changes."""
import argparse
import json
from pathlib import Path

from ._file_utils import _atomic_write_text

OLD_ORIGINS = ("https://bmt.news", "https://www.bmt.news")
NEW_ORIGIN = "https://xiyu.news"


def migrate(value):
    if isinstance(value, dict):
        return {key: migrate(item) for key, item in value.items()}
    if isinstance(value, list):
        return [migrate(item) for item in value]
    if isinstance(value, str):
        for origin in OLD_ORIGINS:
            if value == origin or value.startswith((origin + "/", origin + "?", origin + "#")):
                return NEW_ORIGIN + value[len(origin):]
    return value


def republish(root: Path):
    count = 0
    for prefix in ("api", "editions", "_data/archive"):
        for path in (root / prefix).rglob("*.json"):
            old = json.loads(path.read_text(encoding="utf-8"))
            new = migrate(old)
            if new != old:
                _atomic_write_text(path, json.dumps(new, ensure_ascii=False, indent=2) + "\n")
                count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(f"Migrated self links in {republish(args.root)} published JSON files; news and delivery state unchanged.")
