"""Apply identical source templates to an immutable publication in CI and production."""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
import shutil

REQUIRED_DIRECTORIES = ("_layouts", "_includes", "assets")
OPTIONAL_DIRECTORIES = ("_sass",)
REQUIRED_FILES = ("_config.yml", "_headers", "index.md", "threads.html", "feed.xml")
RETIRED_SOURCES = ("about", "about.html", "history", "history.html", "en", "events", "entity", "threads", "weekly", "s", "admin",
                   "developers", "developer", "sources", "entity.html", "weekly.html",
                   "feed-en.xml", "feed-zh.xml", "openapi.json", "llms.txt", "llms-full.txt",
                   "manifest.webmanifest", "offline.html", "pwa-version.json", "_worker.js")


def overlay(source: Path, destination: Path) -> None:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir() or not destination.is_dir():
        raise ValueError("source and published snapshot must exist")
    if source == destination or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("source and published snapshot must be separate directories")
    # Validate every input before changing the snapshot. _sass is optional in
    # this repository; missing required templates must still fail the build.
    for name in REQUIRED_DIRECTORIES:
        if not (source / name).is_dir():
            raise ValueError(f"missing required template directory: {name}")
    for name in REQUIRED_FILES:
        if not (source / name).is_file():
            raise ValueError(f"missing required source page: {name}")
    for name in OPTIONAL_DIRECTORIES:
        if (source / name).exists() and not (source / name).is_dir():
            raise ValueError(f"optional template path must be a directory: {name}")
    for name in RETIRED_SOURCES:
        target = destination / name
        if target.is_dir(): shutil.rmtree(target)
        elif target.exists(): target.unlink()
    for name in (*REQUIRED_DIRECTORIES, *OPTIONAL_DIRECTORIES):
        if (source / name).is_dir():
            if (destination / name).exists(): shutil.rmtree(destination / name)
            shutil.copytree(source / name, destination / name)
    for name in REQUIRED_FILES:
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, destination / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--latest-only", action="store_true")
    args = parser.parse_args()
    overlay(args.source, args.destination)
    if args.latest_only:
        latest = json.loads((args.destination / "api/latest.json").read_text())
        day = date.fromisoformat(latest["date"]).isoformat()
        current = args.destination / "_posts" / f"{day}-summary-zh.md"
        if day != latest["date"] or not current.is_file():
            raise ValueError("missing current edition in publication snapshot")
        for post in current.parent.glob("*.md"):
            if post != current:
                post.unlink()
    print("Prepared core templates; existing publication evidence preserved")
