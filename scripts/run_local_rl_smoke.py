#!/usr/bin/env python
"""Local smoke test for the RL/self-evolution export pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_training_data import main


if __name__ == "__main__":
    main()
