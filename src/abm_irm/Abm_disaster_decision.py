"""Disaster-decision module for annual ABM-IRM/HBM coupling.

The module applies flood-relocation decisions to existing households using
Tanaka's life-stage HBM outputs and household-level threat perception (TP).
For future projection, TP is a persistent household state: it is initialized
once for a household, decays through time, and receives a flood shock only when
that household is exposed in the current flood year.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .Abm_utility_normal import utility_migration_normal
from .Abm_Class import ensure_household_uid
from .Abm_loss import record_flood_loss
from .paths import data_path, output_path

LIFE_STAGE_GROUPS = ("Single", "Child_hh", "Elderly_hh", "Other_adult")
DISASTER_DATA_DIR = data_path("Disaster_decision")
HBM_RESULTS_DIR = DISASTER_DATA_DIR / "HBM_results"
TP_PARAMETER_DIR = DISASTER_DATA_DIR / "TP_parameter"
WATER_DEPTH_DIR = DISASTER_DATA_DIR / "Water_depth"


@dataclass(frozen=True)
class DisasterDecisionSummary:
    """Compact summary returned by the disaster-decision module."""

    candidate_households: int
    affected_households: int
    moved_households: int
    mean_move_probability: float


def _sigmoid(value):
    value = np.asarray(value, dtype=float)
    return 1.0 / (1.0 + np.exp(-value))


def _is_finite(value) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def damage_ratio(depth_m: float) -> dict[str, float]:
    """Return asset damage ratios and gross loss in 万円 (10,000 JPY)."""
    floor_height = 0.45
    depth_m = float(depth_m)

    if depth_m <= 0:
        return {"house_damage_ratio": 0.0, "content_damage_ratio": 0.0,
                "vehicle_damage_ratio": 0.0, "gross_loss": 0.0,
                "weight_damage_ratio": 0.0}
    if depth_m < floor_height:
        house_damage = 0.064
        content_damage = 0.037
    else:
        depth_above_floor = depth_m - floor_height
        if depth_above_floor < 0.5:
            house_damage = 0.235
            content_damage = 0.308
        elif depth_above_floor < 1:
            house_damage = 0.325
            content_damage = 0.533
        elif depth_above_floor < 2:
            house_damage = 0.499
            content_damage = 0.701
        elif depth_above_floor < 3:
            house_damage = 0.690
            content_damage = 0.948
        else:
            house_damage = 0.865
            content_damage = 0.977

    if depth_m < 0.3:
        vehicle_damage = 0.0
    elif depth_m < 0.5:
        vehicle_damage = 0.1
    elif depth_m < 0.7:
        vehicle_damage = 0.5
    else:
        vehicle_damage = 1.0

    gross_loss = (house_damage * 2418 + content_damage * 880 + vehicle_damage * 320)
    weight_damage_ratio = gross_loss/(2418+1200)

    return {
        "house_damage_ratio": house_damage,
        "content_damage_ratio": content_damage,
        "vehicle_damage_ratio": vehicle_damage,
        "gross_loss": gross_loss,
        "weight_damage_ratio": weight_damage_ratio
    }


def ensure_disaster_attributes(households):
    """Add disaster attributes to households created before this module existed."""
    defaults = {
        "tp": 0.0,
        "tp0": np.nan,
        "cp": 0.0,
        "sp": 0.0,
        "psy": 0.0,
        "pa": np.nan,
        "sc": np.nan,
        "experienced": 0,
        "tp_initialized": False,
        "tp_t0_year": np.nan,
        "tp_last_update_year": np.nan,
        "tp_start": np.nan,
        "tp_pre_flood": np.nan,
        "tp_post_flood": np.nan,
        "hbm_group": None,
        "p_move_disaster": 0.0,
        "disaster_move": False,
        "disaster_old_mesh": None,
        "disaster_new_mesh": None,
    }
    for household in households:
        for name, value in defaults.items():
            if not hasattr(household, name):
                setattr(household, name, value)
    return households


def hbm_group(household) -> str:
    """Return Tanaka life-stage group for one ABM household."""
    members = [member for member in getattr(household, "members", []) if getattr(member, "alive", True)]
    ages = [float(getattr(member, "age", np.nan)) for member in members]
    ages = [age for age in ages if np.isfinite(age)]

    if (ages and all(age >= 65 for age in ages)) or bool(getattr(household, "old_hh", False)):
        return "Elderly_hh"
    if any(age <= 19 for age in ages):
        return "Child_hh"
    if len(members) == 1:
        return "Single"
    return "Other_adult"


def mesh_depth_path(flood_year: int | None = None, scenario: str = "SSP126") -> Path:
    """Return the prepared mesh-depth file for one scenario/year."""
    scenario = scenario.upper()
    if flood_year is not None:
        annual_path = WATER_DEPTH_DIR / scenario / f"mesh_eff_depth_{scenario}_{int(flood_year)}.csv"
        if annual_path.exists():
            return annual_path
        if int(flood_year) != 2020:
            raise FileNotFoundError(
                f"Missing annual disaster mesh-depth file: {annual_path}. "
                "Add the model-ready annual water-depth file before running this scenario."
            )

    fallback_path = DISASTER_DATA_DIR / "mesh_eff_depth.csv"
    if fallback_path.exists():
        return fallback_path
    raise FileNotFoundError(f"Missing disaster mesh-depth file for {scenario} {flood_year}")


def load_damage_by_mesh(flood_year: int | None = None, scenario: str = "SSP126") -> dict[int, dict[str, float]]:
    """Load mesh flood depths and asset-specific damage estimates."""
    path = mesh_depth_path(flood_year=flood_year, scenario=scenario)
    data = pd.read_csv(path)
    required = {"mesh_id", "eff_wd"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    data = data.dropna(subset=["mesh_id", "eff_wd"]).copy()
    data["mesh_id"] = data["mesh_id"].astype(int)
    data["Damage"] = data["eff_wd"].map(
        lambda depth: {"flood_depth_m": float(depth), **damage_ratio(depth)}
    )
    return dict(zip(data["mesh_id"], data["Damage"]))


def load_non_inundated_destination_mesh_ids(flood_year: int, scenario: str = "SSP126") -> set[int]:
    """Return ABM mesh ids where the current scenario/year flood depth is zero."""
    path = mesh_depth_path(flood_year=flood_year, scenario=scenario)
    data = pd.read_csv(path)
    required = {"mesh_id", "eff_wd"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"{path} missing required columns: {sorted(missing)}")
    safe = data[data["eff_wd"].fillna(0.0) <= 0.0]["mesh_id"].astype(int)
    safe_mesh_ids = set(safe.tolist())
    if not safe_mesh_ids:
        raise ValueError(f"No non-inundated destination mesh is available in {path}")
    return safe_mesh_ids


def assign_damage_ratio(households, flood_year: int, scenario: str = "SSP126") -> tuple[list, int]:
    """Assign flood damage and financial loss from the pre-move mesh."""
    damage_by_mesh = load_damage_by_mesh(flood_year=flood_year, scenario=scenario)
    affected = 0
    for household in households:
        damage = damage_by_mesh.get(int(household.mesh_id))
        if damage is None:
            damage = {"flood_depth_m": 0.0, **damage_ratio(0.0)}
        household.psy = float(damage["weight_damage_ratio"])
        record_flood_loss(household, damage["flood_depth_m"], damage)
        if household.psy > 0:
            affected += 1
    print(f"[Disaster damage] {scenario} {flood_year}: affected households {affected} / {len(households)}")
    return households, affected


def load_profile_pool() -> pd.DataFrame:
    """Load questionnaire-derived life-stage psychological profile pool."""
    path = HBM_RESULTS_DIR / "HBM_lifestage_profile_pool.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing life-stage HBM profile pool: {path}")
    pool = pd.read_csv(path)
    required = ["group", "PA_z", "SC_z", "CP_mean", "SP_mean", "experienced", "T0_year"]
    missing = [name for name in required if name not in pool.columns]
    if missing:
        raise ValueError(f"{path} missing columns: {missing}")
    pool = pool.dropna(subset=required).copy()
    pool = pool[pool["group"].isin(LIFE_STAGE_GROUPS)].copy()
    if pool.empty:
        raise ValueError(f"{path} contains no usable profile rows")
    return pool


def build_profile_cache(profile_pool: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return life-stage group -> profile rows cache."""
    cache = {}
    for group in LIFE_STAGE_GROUPS:
        rows = profile_pool[profile_pool["group"] == group].reset_index(drop=True)
        if rows.empty:
            raise ValueError(f"No questionnaire profile rows for life-stage group: {group}")
        cache[group] = rows
    return cache


def load_tp_parameters() -> dict[str, float]:
    """Load shared revised TP12 distribution/decay parameters."""
    path = TP_PARAMETER_DIR / "TP12_distribution_model_parameters.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing TP12 parameter file: {path}")
    params = pd.read_csv(path)
    if not {"parameter", "value"}.issubset(params.columns):
        raise ValueError(f"{path} must contain parameter,value columns")
    return dict(zip(params["parameter"], params["value"].astype(float)))


def _truncated_normal(rng, mean: float, sd: float, lower: float = 0.0, upper: float = 1.0) -> float:
    """Sample one value from a bounded normal distribution."""
    sd = max(float(sd), 1e-6)
    value = float(mean)
    for _ in range(100):
        value = float(rng.normal(float(mean), sd))
        if lower <= value <= upper:
            return value
    return float(np.clip(value, lower, upper))


def integral_mu_pa_sc(T1, T2, PA_z, SC_z, beta_PA, beta_SC, ratio, tau_inf, k):
    """Integral of the revised TP12 decay rate between two elapsed times."""
    if ratio <= 0 or ratio >= 1 or tau_inf <= 0 or k <= 0:
        return np.nan
    if T2 < T1:
        return 0.0

    delta_tau = ratio * tau_inf
    term2 = tau_inf * np.exp(k * T2) - delta_tau
    term1 = tau_inf * np.exp(k * T1) - delta_tau
    if term1 <= 0 or term2 <= 0:
        return np.nan

    decay_modifier = np.exp(float(beta_PA) * float(PA_z) + float(beta_SC) * float(SC_z))
    return float(decay_modifier * np.log(2) / (tau_inf * k) * (np.log(term2) - np.log(term1)))


def calculate_tp_at_year(tp0, PA_z, SC_z, T0_year, target_year, tp_par):
    """Calculate TP at a target year from the sampled T0 value."""
    elapsed = max(float(target_year) - float(T0_year), 0.0)
    integral = integral_mu_pa_sc(
        0.0,
        elapsed,
        PA_z=float(PA_z),
        SC_z=float(SC_z),
        beta_PA=float(tp_par["beta_PA"]),
        beta_SC=float(tp_par["beta_SC"]),
        ratio=float(tp_par["ratio"]),
        tau_inf=float(tp_par["tau_inf"]),
        k=float(tp_par["k"]),
    )
    if not np.isfinite(integral):
        return np.nan
    return float(np.clip(float(tp0) * np.exp(-integral), 0.0, 1.0))


def decay_tp_between_years(household, target_year: int, tp_par: dict[str, float]) -> float:
    """Decay the household's stored TP from its last update year to target year."""
    if not _is_finite(getattr(household, "tp", np.nan)):
        return 0.0
    if not _is_finite(getattr(household, "tp_t0_year", np.nan)):
        return float(np.clip(float(household.tp), 0.0, 1.0))

    last_year = getattr(household, "tp_last_update_year", np.nan)
    if not _is_finite(last_year):
        last_year = target_year
    t0_year = float(household.tp_t0_year)
    T1 = max(float(last_year) - t0_year, 0.0)
    T2 = max(float(target_year) - t0_year, 0.0)
    integral = integral_mu_pa_sc(
        T1,
        T2,
        PA_z=float(household.pa),
        SC_z=float(household.sc),
        beta_PA=float(tp_par["beta_PA"]),
        beta_SC=float(tp_par["beta_SC"]),
        ratio=float(tp_par["ratio"]),
        tau_inf=float(tp_par["tau_inf"]),
        k=float(tp_par["k"]),
    )
    if not np.isfinite(integral):
        return float(np.clip(float(household.tp), 0.0, 1.0))
    return float(np.clip(float(household.tp) * np.exp(-integral), 0.0, 1.0))


def initialize_household_tp(household, profile_cache, rng, current_year: int, tp_par: dict[str, float]) -> None:
    """Sample psychological profile values and initialize TP once for a household."""
    profiles = profile_cache[household.hbm_group]
    profile = profiles.iloc[int(rng.integers(0, len(profiles)))]

    household.pa = float(profile["PA_z"])
    household.sc = float(profile["SC_z"])
    household.cp = float(profile["CP_mean"])
    household.sp = float(profile["SP_mean"])
    household.experienced = int(round(float(profile["experienced"])))
    household.tp_t0_year = float(profile["T0_year"])

    if household.experienced == 1:
        household.tp0 = _truncated_normal(rng, tp_par["mu0_exp"], tp_par["sd0_exp"])
    else:
        household.tp0 = _truncated_normal(rng, tp_par["mu0_noexp"], tp_par["sd0_noexp"])

    tp_start = calculate_tp_at_year(
        household.tp0,
        household.pa,
        household.sc,
        household.tp_t0_year,
        current_year,
        tp_par,
    )
    if not np.isfinite(tp_start):
        tp_start = float(household.tp0)

    household.tp_start = float(tp_start)
    household.tp = float(tp_start)
    household.tp_last_update_year = float(current_year)
    household.tp_initialized = True


def assign_psychological_inputs(households, profile_cache, rng, current_year: int):
    """Update life-stage group and persistent TP for the current disaster year."""
    tp_par = load_tp_parameters()

    for household in households:
        household.hbm_group = hbm_group(household)
        needs_initialization = not bool(getattr(household, "tp_initialized", False))
        needs_initialization = needs_initialization or not _is_finite(getattr(household, "pa", np.nan))
        needs_initialization = needs_initialization or not _is_finite(getattr(household, "sc", np.nan))
        if needs_initialization:
            initialize_household_tp(household, profile_cache, rng, current_year, tp_par)

        household.tp_pre_flood = decay_tp_between_years(household, current_year, tp_par)
        shock_mean = float(tp_par["eta"]) * float(household.psy)
        shock_sd = float(tp_par["shock_sd"]) * np.sqrt(max(float(household.psy), 0.0))
        shock = max(0.0, float(rng.normal(shock_mean, shock_sd))) if household.psy > 0 else 0.0
        household.tp_post_flood = float(np.clip(household.tp_pre_flood + shock, 0.0, 1.0))
        household.tp = household.tp_post_flood
        household.tp_last_update_year = float(current_year)

    return households


def prepare_annual_threat_perception(households, current_year: int, random_state: int):
    """Initialize or decay TP before any scenario-specific flood shock.

    Calling this stage for baseline and flood scenarios with the same seed gives
    matching pre-flood psychological states.  A subsequent disaster decision
    may then add a scenario-specific shock without changing the initialization.
    """
    households = ensure_disaster_attributes(households)
    profile_cache = build_profile_cache(load_profile_pool())
    tp_par = load_tp_parameters()
    rng = np.random.default_rng(random_state)

    for household in households:
        household.hbm_group = hbm_group(household)
        needs_initialization = not bool(getattr(household, "tp_initialized", False))
        needs_initialization = needs_initialization or not _is_finite(getattr(household, "pa", np.nan))
        needs_initialization = needs_initialization or not _is_finite(getattr(household, "sc", np.nan))
        if needs_initialization:
            initialize_household_tp(household, profile_cache, rng, current_year, tp_par)
        else:
            household.tp = decay_tp_between_years(household, current_year, tp_par)
            household.tp_last_update_year = float(current_year)

        # These values describe the common no-flood state for this year.  The
        # disaster stage overwrites tp_post_flood only when a shock is applied.
        household.tp_pre_flood = float(household.tp)
        household.tp_post_flood = float(household.tp)

    return households


def load_hbm_coefficients() -> dict[str, dict[str, float]]:
    """Load life-stage migration coefficients from Tanaka's recommended HBM."""
    path = HBM_RESULTS_DIR / "HBM_lifestage_migration_coefficients.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing life-stage HBM coefficient file: {path}")
    data = pd.read_csv(path)
    required = {"group", "intercept", "tp", "cp", "sp"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    coeffs = {}
    for group in LIFE_STAGE_GROUPS:
        match = data[data["group"] == group]
        if match.empty:
            raise ValueError(f"Missing coefficients for life-stage group {group} in {path}")
        row = match.iloc[0]
        coeffs[group] = {
            "intercept": float(row["intercept"]),
            "tp": float(row["tp"]),
            "cp": float(row["cp"]),
            "sp": float(row["sp"]),
        }
    return coeffs


def predict_move_probability(households: Iterable, coeffs: dict[str, dict[str, float]]) -> np.ndarray:
    """Predict disaster relocation probability for households."""
    linear = []
    for household in households:
        co = coeffs[household.hbm_group]
        linear.append(
            co["intercept"]
            + co["tp"] * float(household.tp)
            + co["cp"] * float(household.cp)
            + co["sp"] * float(household.sp)
        )
    return _sigmoid(np.asarray(linear, dtype=float))


def reset_event_state(households) -> None:
    """Clear per-event disaster outcomes while keeping persistent TP attributes."""
    for household in households:
        household.p_move_disaster = 0.0
        household.disaster_move = False
        household.disaster_old_mesh = household.mesh_id
        household.disaster_new_mesh = household.mesh_id


def write_disaster_summary(
    task_id: str,
    flood_year: int,
    scenario: str,
    candidate_households,
    summary: DisasterDecisionSummary,
) -> None:
    """Write compact disaster movement outputs without bulky candidate-level traces."""
    output_dir = output_path(f"Task_ID_{task_id}")
    move_rows = []
    for household in candidate_households:
        ensure_household_uid(household)
        moved_between_meshes = household.disaster_old_mesh != household.disaster_new_mesh
        if not bool(household.disaster_move) and not moved_between_meshes:
            continue
        move_rows.append({
            "scenario": scenario,
            "flood_year": flood_year,
            "household_uid": household.household_uid,
            "hh_id": household.hh_id,
            "mesh_before": household.disaster_old_mesh,
            "mesh_after": household.disaster_new_mesh,
            "life_stage": household.hbm_group,
            "damage_ratio": household.psy,
            "tp_pre_flood": household.tp_pre_flood,
            "tp_post_flood": household.tp_post_flood,
            "tp": household.tp,
            "p_move_disaster": household.p_move_disaster,
            "disaster_move": int(household.disaster_move),
            "members": len(household.members),
        })

    trace_columns = [
        "scenario", "flood_year", "household_uid", "hh_id", "mesh_before", "mesh_after",
        "life_stage", "damage_ratio", "tp_pre_flood", "tp_post_flood", "tp",
        "p_move_disaster", "disaster_move", "members",
    ]
    prefix = f"Disaster_movement_trace_{scenario}_{flood_year}_seed"
    pd.DataFrame(move_rows, columns=trace_columns).to_csv(output_dir / f"{prefix}.csv", index=False)
    pd.DataFrame([{"scenario": scenario, "flood_year": flood_year, **summary.__dict__}]).to_csv(
        output_dir / f"Disaster_decision_summary_{scenario}_{flood_year}_seed.csv",
        index=False,
    )


def disaster_decision(
    households,
    task_id: str = "0",
    random_state: int = 42,
    only_damaged: bool = True,
    do_destination_choice: bool = True,
    abm_start_year: int = 2020,
    flood_year: int = 2020,
    scenario: str = "SSP126",
    enable_relocation: bool = True,
):
    """Apply flood impacts and optionally the disaster-relocation decision."""
    del abm_start_year
    scenario = scenario.upper()
    print(f"[Disaster decision] start {scenario} {flood_year}")
    rng = np.random.default_rng(random_state)

    households = ensure_disaster_attributes(households)
    reset_event_state(households)
    households, affected_households = assign_damage_ratio(households, flood_year=flood_year, scenario=scenario)
    profile_pool = load_profile_pool()
    profile_cache = build_profile_cache(profile_pool)
    households = assign_psychological_inputs(
        households,
        profile_cache=profile_cache,
        rng=rng,
        current_year=flood_year,
    )

    if only_damaged:
        candidates = [
            household for household in households
            if getattr(household, "exist", True)
            and len(getattr(household, "members", [])) > 0
            and float(getattr(household, "psy", 0.0)) > 0.0
        ]
    else:
        candidates = [
            household for household in households
            if getattr(household, "exist", True)
            and len(getattr(household, "members", [])) > 0
        ]

    print(f"[Disaster decision] candidate households: {len(candidates)}")
    if not enable_relocation:
        summary = DisasterDecisionSummary(len(candidates), affected_households, 0, 0.0)
        print("[Disaster decision] relocation disabled by policy scenario")
        write_disaster_summary(task_id, flood_year, scenario, [], summary)
        return households, summary

    if not candidates:
        summary = DisasterDecisionSummary(0, affected_households, 0, 0.0)
        write_disaster_summary(task_id, flood_year, scenario, [], summary)
        return households, summary

    coeffs = load_hbm_coefficients()
    probabilities = predict_move_probability(candidates, coeffs)
    move_flags = rng.random(len(candidates)) < probabilities

    safe_destination_mesh_ids = (
        load_non_inundated_destination_mesh_ids(flood_year=flood_year, scenario=scenario)
        if do_destination_choice
        else None
    )

    moved = 0
    for household, probability, move_flag in zip(candidates, probabilities, move_flags):
        household.p_move_disaster = float(probability)
        household.disaster_old_mesh = household.mesh_id
        household.disaster_move = bool(move_flag)
        if household.disaster_move:
            moved += 1
            if do_destination_choice:
                utility_migration_normal(household, allowed_mesh_ids=safe_destination_mesh_ids)
        household.disaster_new_mesh = household.mesh_id

    summary = DisasterDecisionSummary(
        candidate_households=len(candidates),
        affected_households=affected_households,
        moved_households=moved,
        mean_move_probability=float(np.mean(probabilities)),
    )
    print(f"[Disaster decision] movers: {moved} / {len(candidates)}")
    print(f"[Disaster decision] mean move probability: {summary.mean_move_probability:.4f}")
    write_disaster_summary(task_id, flood_year, scenario, candidates, summary)
    return households, summary


Disaster_decision = disaster_decision



