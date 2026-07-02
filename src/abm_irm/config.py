"""Simulation and utility-parameter configuration for ABM-IRM."""

from __future__ import annotations
import pandas as pd
from .paths import data_path


def read_parameter_file() -> pd.Series:
    """Return values from data/Parameter_file.txt indexed by parameter name."""
    params = pd.read_table(data_path('Parameter_file.txt'), sep='\\s+')
    if not {'Para', 'Value'}.issubset(params.columns):
        raise ValueError("data/Parameter_file.txt must contain 'Para' and 'Value' columns")
    return params.set_index('Para')['Value']


def read_sim_period() -> tuple[int, int]:
    """Return (start_year, simulation_years) from data/Parameter_file.txt."""
    params = read_parameter_file()
    missing = [name for name in ('start_year', 'simulation_years') if name not in params.index]
    if missing:
        raise ValueError(f'data/Parameter_file.txt is missing required parameter(s): {missing}')
    return (int(float(params['start_year'])), int(float(params['simulation_years'])))
