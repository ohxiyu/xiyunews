"""Apply identical source templates to an immutable publication in CI and production."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil

REQUIRED_DIRECTORIES = ("_layouts", "_includes", "assets")
OPTIONAL_DIRECTORIES = ("_sass",)
REQUIRED_FILES = ("_config.yml", "index.md", "threads.html", "history.html")


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
    for name in (*REQUIRED_DIRECTORIES, *OPTIONAL_DIRECTORIES):
        if (source / name).is_dir():
            shutil.copytree(source / name, destination / name, dirs_exist_ok=True)
    for name in REQUIRED_FILES:
        shutil.copy2(source / name, destination / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    overlay(args.source, args.destination)
    print("Prepared core templates; existing publication evidence preserved")
