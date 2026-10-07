"""Validate Jekyll output, then stage public static assets for the single Worker."""
import argparse
import json
from pathlib import Path
import shutil


def prepare(source: Path, destination: Path) -> None:
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("source and destination must be separate directories")
    if destination.exists():
        raise ValueError("destination must not already exist")
    for required in ("index.html", "api/latest.json", "s/index.html", "feed-zh.xml", "sitemap.xml", "llms.txt"):
        if not (source / required).is_file():
            raise ValueError(f"missing rendered public output: {required}")
    latest = json.loads((source / "api/latest.json").read_text())
    if not latest.get("date") or not isinstance(latest.get("items"), list) or not latest["items"]:
        raise ValueError("invalid or empty published latest edition")
    home = (source / "index.html").read_text()
    if f'data-latest-edition-date="{latest["date"]}"' not in home:
        raise ValueError("homepage does not match latest edition")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlinks are not allowed in edge assets")
        if any(part in {".git", ".env", ".dev.vars", "node_modules"} or
               part.startswith(".env.") or part.startswith(".dev.vars.") for part in path.relative_to(source).parts):
            raise ValueError("private files are not allowed in edge assets")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("_worker.js", "Gemfile", "Gemfile.lock", "CNAME"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.destination)
