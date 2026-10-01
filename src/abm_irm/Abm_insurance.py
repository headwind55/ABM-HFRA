"""Annual household flood-insurance coverage using Tanaka's PIns_01 model.

Stable insurance perceptions are sampled jointly from questionnaire records.
PIns_01 is then evaluated for every household each year; its Bernoulli outcome
is the household's insurance-coverage state for that year.
"""

from __future__ import annotations

from functools import lru_cache
import math

import numpy as np
import pandas as pd

from .paths import data_path


INSURANCE_DIR = data_path("Insurance")
MODEL = "PIns_01"
TERMS = ("Intercept", "TP_use", "insurance_efficacy", "insurance_affordability", "provider_trust")


def _group(hh) -> str:
    members = [m for m in getattr(hh, "members", []) if getattr(m, "alive", True)]
    ages = [float(m.age) for m in members if np.isfinite(float(m.age))]
    if (ages and all(a >= 65 for a in ages)) or bool(getattr(hh, "old_hh", False)):
        return "G1_elderly_only"
    if any(a <= 19 for a in ages):
        return "G2_with_children"
    if len(members) == 1:
        return "G3_single_nonelderly"
    return "G4_other"


@lru_cache(maxsize=1)
def _profiles() -> dict[str, pd.DataFrame]:
    df = pd.read_csv(INSURANCE_DIR / "PIns_01_questionnaire_profiles.csv")
    needed = ["household_group", "insurance_efficacy", "insurance_affordability", "provider_trust"]
    df = df.dropna(subset=needed).copy()
    for col in needed[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=needed)
    return {key: group.reset_index(drop=True) for key, group in df.groupby("household_group")}


@lru_cache(maxsize=2)
def _coefficients(model: str) -> dict[str, dict[str, float]]:
    filename = f"{model}_household_group_coefficients.csv"
    frame = pd.read_csv(INSURANCE_DIR / filename)
    frame = frame[frame["term"].isin(TERMS)]
    result = {}
    for group, rows in frame.groupby("household_group"):
        result[group] = dict(zip(rows["term"], rows["Estimate"].astype(float)))
    return result


def _sample_profile(hh, rng: np.random.Generator) -> pd.Series:
    pools = _profiles()
    pool = pools.get(_group(hh), pools["G4_other"])
    return pool.iloc[int(rng.integers(0, len(pool)))]


def _ensure_attributes(hh) -> None:
    defaults = {
        "insured": False, "insurance_expire_year": None,
        "insurance_initialized": False, "insurance_efficacy": None,
        "insurance_affordability": None, "provider_trust": None,
        "p_insurance": None, "insurance_decision": "not_evaluated",
        "insurance_origin": None,
    }
    for name, value in defaults.items():
        if not hasattr(hh, name):
            setattr(hh, name, value)


def disable_insurance(households, year: int) -> None:
    """Force the no-insurance policy state for every current household."""
    for hh in households:
        _ensure_attributes(hh)
        hh.insured = False
        hh.insurance_expire_year = None
        hh.insurance_initialized = False
        hh.insurance_efficacy = None
        hh.insurance_affordability = None
        hh.provider_trust = None
        hh.p_insurance = 0.0
        hh.insurance_decision = "disabled"
        hh.insurance_origin = "policy_scenario_no_insurance"
    print(f"[Insurance {year}] disabled; insured=0/{len(households)}")


def initialize_insurance(households, year: int, rng: np.random.Generator,
                         initial_population: bool = False):
    """Initialize unseen households and draw current coverage with PIns_01."""
    initialized = 0
    for hh in households:
        _ensure_attributes(hh)
        if hh.insurance_initialized:
            continue
        profile = _sample_profile(hh, rng)
        hh.insurance_efficacy = float(profile["insurance_efficacy"])
        hh.insurance_affordability = float(profile["insurance_affordability"])
        hh.provider_trust = float(profile["provider_trust"])
        hh.insurance_initialized = True
        hh.p_insurance = insurance_probability(hh)
        hh.insured = bool(rng.random() < hh.p_insurance)
        hh.insurance_expire_year = None
        if initial_population:
            hh.insurance_origin = "PIns01_initial_population"
            hh.insurance_decision = "initially_insured_PIns01" if hh.insured else "initially_uninsured_PIns01"
        else:
            hh.insurance_origin = "PIns01_new_household"
            hh.insurance_decision = "new_household_insured_PIns01" if hh.insured else "new_household_uninsured_PIns01"
        initialized += 1
    return initialized


def insurance_probability(hh, model: str = MODEL) -> float:
    """Return the posterior-mean PIns_01 current-coverage probability."""
    group = _group(hh)
    co = _coefficients(model)[group]
    tp = float(np.clip(getattr(hh, "tp", 0.0), 0.0, 1.0))
    eta = (co["Intercept"] + co["TP_use"] * tp
           + co["insurance_efficacy"] * float(hh.insurance_efficacy)
           + co["insurance_affordability"] * float(hh.insurance_affordability)
           + co["provider_trust"] * float(hh.provider_trust))
    return 1.0 / (1.0 + math.exp(-float(np.clip(eta, -35.0, 35.0))))


def update_insurance(households, year: int, rng: np.random.Generator):
    """Redraw annual coverage for every household using PIns_01."""
    existing = {id(hh) for hh in households if bool(getattr(hh, "insurance_initialized", False))}
    initialize_insurance(households, year, rng, initial_population=False)
    counts = {
        "new_households": 0, "new_households_insured": 0,
        "joined": 0, "retained": 0, "lapsed": 0, "remained_uninsured": 0,
    }
    for hh in households:
        if id(hh) not in existing:
            counts["new_households"] += 1
            counts["new_households_insured"] += int(hh.insured)
            continue
        was_insured = bool(hh.insured)
        probability = insurance_probability(hh)
        hh.p_insurance = probability
        hh.insured = bool(rng.random() < probability)
        hh.insurance_expire_year = None
        hh.insurance_origin = "PIns01_annual"
        if not was_insured and hh.insured:
            hh.insurance_decision = "joined_PIns01"
            counts["joined"] += 1
        elif was_insured and hh.insured:
            hh.insurance_decision = "retained_PIns01"
            counts["retained"] += 1
        elif was_insured and not hh.insured:
            hh.insurance_decision = "lapsed_PIns01"
            counts["lapsed"] += 1
        else:
            hh.insurance_decision = "remained_uninsured_PIns01"
            counts["remained_uninsured"] += 1
    print(f"[Insurance {year}] {counts}; insured={sum(bool(h.insured) for h in households)}/{len(households)}")
    return counts
