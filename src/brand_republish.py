"""Migrate published JSON/XML self links without AI or news changes."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

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
    xml_paths = [root / "sitemap.xml", *(root / "feeds").rglob("*.xml")]
    for path in xml_paths:
        if not path.is_file():
            continue
        document = ET.fromstring(path.read_text(encoding="utf-8"))
        changed = False
        for node in document.iter():
            if node.tag.rsplit("}", 1)[-1] in {"loc", "link", "id", "guid"} and node.text:
                value = migrate(node.text)
                if value != node.text:
                    node.text = value
                    changed = True
            if "href" in node.attrib:
                value = migrate(node.attrib["href"])
                if value != node.attrib["href"]:
                    node.attrib["href"] = value
                    changed = True
        # Only channel-level metadata, never third-party entry headlines.
        namespace = document.tag.split("}", 1)[0][1:] if document.tag.startswith("{") else ""
        title = document.find(f"{{{namespace}}}title" if namespace else "channel/title")
        if title is not None and title.text and (
            title.text == "BMTNews" or title.text.startswith("BMTNews · ")
        ):
            title.text = "xiyu.news" + title.text[len("BMTNews"):]
            changed = True
        if changed:
            if namespace:
                ET.register_namespace("", namespace)
            _atomic_write_text(path, '<?xml version="1.0" encoding="utf-8"?>\n' +
                               ET.tostring(document, encoding="unicode") + "\n")
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(f"Migrated self links in {republish(args.root)} published JSON/XML files; news and delivery state unchanged.")
