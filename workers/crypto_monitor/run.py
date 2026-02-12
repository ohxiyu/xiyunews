#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录和 src 目录到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.main import main

if __name__ == "__main__":
    main()
