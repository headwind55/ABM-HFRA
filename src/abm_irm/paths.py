"""Project path helpers for ABM-IRM."""

from __future__ import annotations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
RUNTIME_DIR = PROJECT_ROOT / 'runtime'


def data_path(*parts: str) -> Path:
    """Return an absolute path below the data directory."""
    return DATA_DIR.joinpath(*parts)


def runtime_path(*parts: str) -> Path:
    """Return an absolute runtime path, creating folders as needed."""
    path = RUNTIME_DIR.joinpath(*parts)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def output_path(*parts: str) -> Path:
    """Return an absolute path below runtime/output."""
    return runtime_path('output', *parts)
