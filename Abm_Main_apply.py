"""Backward-compatible launcher for the cleaned ABM-IRM simulation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from abm_irm.Abm_Main_apply import main


if __name__ == "__main__":
    main()
