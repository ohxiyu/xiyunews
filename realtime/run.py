#!/usr/bin/env python3
import os
from pathlib import Path

from src.platform.app import main

if __name__ == "__main__":
    release = Path(__file__).resolve().with_name("release.sha")
    if release.is_file():
        os.environ["SOURCE_COMMIT"] = release.read_text().strip()
    main()
