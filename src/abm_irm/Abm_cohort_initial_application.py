"""Cohort helpers for building age-sex migration targets."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import read_sim_period
from .paths import data_path

SCENARIO = "Medium_case"
MAX_AGE = 100
BIRTH_AGE_MIN = 20
BIRTH_AGE_MAX = 49
MIGRATION_BLOCK_YEARS = 5
FUTURE_MALE_BIRTH_RATIO = 0.513

start_year, sim_year = read_sim_period()

male_death_ratio = pd.read_csv(
    data_path("Birth_Death_Rate", SCENARIO, "Kumamoto_male_2020_2100_medium_mortality.csv")
)
female_death_ratio = pd.read_csv(
    data_path("Birth_Death_Rate", SCENARIO, "Kumamoto_female_2020_2100_medium_mortality.csv")
)
birth_ratio = pd.read_csv(
    data_path("Birth_Death_Rate", SCENARIO, "Fertility_medium_2020-2100.csv")
)
flow_rate = pd.read_table(data_path("Migration", "Migration.txt"), sep=r"\s+")


def _rate_year(year: int) -> int:
    """Clamp requested future demographic rates to the available table range."""
    year_columns = [int(column) for column in male_death_ratio.columns if str(column).isdigit()]
    return min(max(int(year), min(year_columns)), max(year_columns))


def _empty_cohort(column: str) -> pd.DataFrame:
    return pd.DataFrame({column: np.zeros(MAX_AGE + 1, dtype=int)}, index=np.arange(MAX_AGE + 1))


def _cohort_from_series(series: pd.Series, column: str) -> pd.DataFrame:
    cohort = _empty_cohort(column)
    values = pd.to_numeric(series, errors="coerce").fillna(0)
    values.index = pd.to_numeric(values.index, errors="coerce")
    values = values[values.index.notna()]
    values.index = values.index.astype(int)
    cohort.loc[cohort.index.intersection(values.index), column] = values.reindex(cohort.index, fill_value=0).astype(int)
    return cohort


def _cohort_from_frame(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return a 0-100 age-indexed single-sex cohort table."""
    candidates = [column, column.lower(), "Num"]
    if "Age" in frame.columns:
        frame = frame.set_index("Age")
    for candidate in candidates:
        if candidate in frame.columns:
            return _cohort_from_series(frame[candidate], column)
    raise ValueError(f"Cannot find a {column!r} cohort column in {list(frame.columns)}")


def load_start_cohort(year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load observed age-sex population for the initial projection year."""
    source = pd.read_table(data_path("Comparison", f"Pop_sex_{year}.txt"), sep=r"\s+")
    if "Age" not in source.columns and len(source.columns) >= 3:
        source = source.rename(columns={source.columns[0]: "Age"})
    female = _cohort_from_frame(source, "Female")
    male = _cohort_from_frame(source, "Male")
    return female, male


def age_update_cohort(female_fun: pd.DataFrame, male_fun: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Age the cohort table by one simulation year."""
    female_next = female_fun.copy()
    male_next = male_fun.copy()
    female_next.index = female_next.index + 1
    male_next.index = male_next.index + 1
    female_next = pd.concat([pd.DataFrame({"Female": [0]}, index=[0]), female_next], axis=0)
    male_next = pd.concat([pd.DataFrame({"Male": [0]}, index=[0]), male_next], axis=0)
    return (
        female_next.reindex(np.arange(MAX_AGE + 1), fill_value=0).astype(int),
        male_next.reindex(np.arange(MAX_AGE + 1), fill_value=0).astype(int),
    )


def annual_death(this_year: int, female_sim: pd.DataFrame, male_sim: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply future age-sex mortality rates for one cohort year."""
    rate_year = str(_rate_year(this_year))
    female_rates = female_death_ratio.set_index("Age")[rate_year].reindex(np.arange(MAX_AGE + 1), fill_value=0)
    male_rates = male_death_ratio.set_index("Age")[rate_year].reindex(np.arange(MAX_AGE + 1), fill_value=0)
    female_deaths = (female_sim["Female"].to_numpy() * female_rates.to_numpy()).round().astype(int)
    male_deaths = (male_sim["Male"].to_numpy() * male_rates.to_numpy()).round().astype(int)
    female_next = female_sim.copy()
    male_next = male_sim.copy()
    female_next["Female"] = np.maximum(female_next["Female"].to_numpy() - female_deaths, 0)
    male_next["Male"] = np.maximum(male_next["Male"].to_numpy() - male_deaths, 0)
    return female_next.astype(int), male_next.astype(int)


def annual_birth(this_year: int, female_sim: pd.DataFrame, male_sim: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply future fertility rates and fixed newborn sex ratio for one cohort year."""
    rate_year = str(_rate_year(this_year))
    fertility = birth_ratio.set_index("Age")[rate_year].reindex(np.arange(BIRTH_AGE_MIN, BIRTH_AGE_MAX + 1), fill_value=0)
    fertile_female = female_sim.loc[BIRTH_AGE_MIN:BIRTH_AGE_MAX, "Female"].to_numpy()
    total_births = int(round((fertile_female * fertility.to_numpy()).sum()))
    new_male = int(round(total_births * FUTURE_MALE_BIRTH_RATIO))
    new_female = total_births - new_male
    female_sim = female_sim.copy()
    male_sim = male_sim.copy()
    female_sim.loc[0, "Female"] = new_female
    male_sim.loc[0, "Male"] = new_male
    return female_sim.astype(int), male_sim.astype(int)


def project_cohort(period_start_year: int,
                   female_start: pd.DataFrame,
                   male_start: pd.DataFrame,
                   period_years: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Project a cohort forward without applying migration."""
    female = _cohort_from_frame(female_start, "Female")
    male = _cohort_from_frame(male_start, "Male")
    for offset in range(period_years):
        female, male = annual_death(period_start_year + offset, female, male)
        female, male = age_update_cohort(female, male)
        female, male = annual_birth(period_start_year + offset + 1, female, male)
    return female, male


def distribute(period_years: int, array: np.ndarray) -> pd.DataFrame:
    """Spread a period total across annual age cohorts using integer totals."""
    annual_columns = []
    for total in np.asarray(array, dtype=int):
        q, r = divmod(int(total), period_years)
        annual_num = np.full(period_years, q, dtype=int)
        if r:
            annual_num[:r] += 1
        annual_columns.append(annual_num)
    return pd.DataFrame(np.column_stack(annual_columns))


def _shift_final_age_targets(final_age_targets: np.ndarray,
                             year_offset: int,
                             period_years: int) -> np.ndarray:
    """Convert final-period age targets to the age people have in a given year."""
    current_age_targets = np.zeros(MAX_AGE + 1, dtype=int)
    for final_age, target in enumerate(np.asarray(final_age_targets, dtype=int)):
        current_age = final_age - period_years + year_offset + 1
        if 0 <= current_age <= MAX_AGE:
            current_age_targets[current_age] += int(target)
    return current_age_targets


def build_annual_migration_targets(female_start: pd.DataFrame,
                                   male_start: pd.DataFrame,
                                   period_start_year: int,
                                   period_years: int = MIGRATION_BLOCK_YEARS) -> tuple[np.ndarray, np.ndarray]:
    """Build annual migration targets for one continuous 5-year projection block.

    Positive values mean out-migration and negative values mean in-migration,
    matching the convention used by Abm_pop_dynamics.migration().
    """
    female_end, male_end = project_cohort(period_start_year, female_start, male_start, period_years)
    rate = flow_rate.reindex(np.arange(MAX_AGE + 1)).fillna(0)
    male_diff = np.ravel(np.array(round(-male_end[["Male"]] * rate[["Male"]]).astype(int)))
    female_diff = np.ravel(np.array(round(-female_end[["Female"]] * rate[["Female"]]).astype(int)))
    male_by_final_age = -distribute(period_years, male_diff).to_numpy()
    female_by_final_age = -distribute(period_years, female_diff).to_numpy()
    male_targets = np.vstack([
        _shift_final_age_targets(male_by_final_age[offset], offset, period_years)
        for offset in range(period_years)
    ])
    female_targets = np.vstack([
        _shift_final_age_targets(female_by_final_age[offset], offset, period_years)
        for offset in range(period_years)
    ])
    return female_targets, male_targets


female_initial, male_initial = load_start_cohort(start_year)
female_annual, male_annual = build_annual_migration_targets(
    female_initial,
    male_initial,
    start_year,
    min(sim_year, MIGRATION_BLOCK_YEARS),
)
