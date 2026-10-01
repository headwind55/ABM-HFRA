"""Command-line entry point for the cleaned ABM-IRM simulation."""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import os
import random
import sys
import time

import numpy as np
import pandas as pd

from .config import read_sim_period
from .paths import data_path, output_path, runtime_path


POLICY_SCENARIOS = {
    "0": (False, False),  # Do nothing
    "1": (True, False),   # Insurance only
    "2": (False, True),   # Relocation only
    "3": (True, True),    # Insurance and relocation
}


def configure_seed(seed: int) -> None:
    """Seed Python and NumPy random number generators."""
    random.seed(seed)
    np.random.seed(seed)


@contextlib.contextmanager
def run_log(task_id: str, enabled: bool = True):
    """Redirect one run's console output to a timestamped runtime log."""
    if not enabled:
        yield None
        return
    timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = runtime_path("logs", f"ABM_run_TASK_ID{task_id}_{timestamp}.log")
    original_stdout, original_stderr = (sys.stdout, sys.stderr)
    with open(log_file, "w", buffering=1, encoding="utf-8") as handle:
        sys.stdout = handle
        sys.stderr = handle
        try:
            yield log_file
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def arr_sig(name, a) -> None:
    """Print a compact signature for cohort arrays used by the run."""
    a = np.ascontiguousarray(a)
    h = hashlib.sha256(a.tobytes()).hexdigest()[:16]
    print(f"[COHORT_SIG] {name}: shape={a.shape} sum={a.sum()} min={a.min()} max={a.max()} sha={h}")


def snapshot(households, tag: str) -> None:
    """Print a compact population checksum for a simulation stage."""
    female = sum(1 for hh in households for person in hh.members if person.sex == "F")
    male = sum(1 for hh in households for person in hh.members if person.sex == "M")
    checksum = sum(person.age for hh in households for person in hh.members)
    print(tag, "F", female, "M", male, "sumAge", checksum)


def run_simulation(seed: int, task_id: str, enable_disaster: bool = True, disaster_year: int = 2020,
                   disaster_only_damaged: bool = True, disaster_destination_choice: bool = True,
                   disaster_scenario: str = "SSP370", disaster_single_event: bool = False,
                   demographic_case: str = "Medium_case", enable_insurance: bool = True,
                   enable_relocation: bool | None = None):
    """Run one configured continuous ABM-IRM simulation."""
    if enable_relocation is None:
        enable_relocation = enable_disaster
    demographic_case = demographic_case or "Medium_case"
    os.environ["ABM_IRM_DEMOGRAPHIC_CASE"] = demographic_case
    from .Abm_cohort_initial_application import MIGRATION_BLOCK_YEARS, build_annual_migration_targets
    from .Abm_count_update import (
        age_update_cohort,
        age_update_object,
        count_population_by_age_and_sex,
        gender_assign,
        get_gender_ratio,
        get_max_hh_ids,
        old_house_update,
    )
    from .Abm_household_ass_gender import Assign_house, initial_live_year, live_year_update
    from .Abm_output import gender_num_output, household_tp_output, micro_output
    from .Abm_insurance import disable_insurance, initialize_insurance, update_insurance
    from .Abm_loss import reset_annual_losses
    from .Abm_loss_summary import LossSummaryWriter
    from .Abm_disaster_decision import prepare_annual_threat_perception
    from .Abm_pop_dynamics import annual_birth, annual_death, life_course, migration, new_household, new_marriage
    if enable_disaster:
        from .Abm_disaster_decision import disaster_decision

    start_time_all = time.perf_counter()
    start_year, sim_year = read_sim_period()
    population = pd.read_table(data_path("Input", f"Population_input_{start_year}.txt"), delimiter=" ")
    census = pd.read_table(data_path("Comparison", f"Pop_sex_{start_year}.txt"), sep=" ")
    gender_ratio = get_gender_ratio(census)
    house = pd.read_table(data_path("Input", f"Mesh_ID_Age_1yr_{start_year}.txt"), delimiter=" ")
    house = pd.concat([house.iloc[:, 0:1], house.iloc[:, 3:5]], axis=1)
    households = []

    print("Start to assign popluation to meshes\n")
    for i in range(len(house)):
        household_mesh = Assign_house(population, house, house["Mesh_ID_abm"][i])
        households = households + household_mesh
        households = old_house_update(households)

    print("There are ", len(households), "household")
    print("Population assignment finishes\n")
    print("After initiliaztion, there are", len(households), "Household\n")
    print("Start to assign the remaining gender")
    households = gender_assign(population, gender_ratio, households)
    female, male = count_population_by_age_and_sex(households)
    output = pd.concat([female, male], axis=1)
    output.columns = ["Female", "Male"]
    output.to_csv(
        runtime_path(
            "analysis", "Initialization_condition_check",
            f"gender_ini_{task_id}_seed{seed:02d}.txt",
        ),
        sep=" ", index=None,
    )
    households = initial_live_year(households)
    #micro_output("initial", house, households, output_path(f"Initial_{task_id}"))

    output_dir = output_path(f"Task_ID_{task_id}")
    loss_summary = LossSummaryWriter(output_dir, seed,
                                    disaster_scenario if enable_disaster else "BASE",
                                    start_year, demographic_case)
    female_block_targets = None
    male_block_targets = None
    block_start_year = None

    disaster_applied_years = []

    # Establish a common pre-flood psychological and insurance state.  For a
    # given seed this stage is identical in BASE and every SSP scenario.
    tp_random_state = seed * 100000 + start_year
    households = prepare_annual_threat_perception(households, start_year, tp_random_state)
    insurance_rng = np.random.default_rng(seed * 100000 + start_year + 7919)
    if enable_insurance:
        initialize_insurance(households, start_year, insurance_rng, initial_population=True)
    else:
        disable_insurance(households, start_year)
    reset_annual_losses(households)

    apply_initial_disaster = enable_disaster and start_year >= disaster_year
    apply_initial_disaster = apply_initial_disaster and (not disaster_single_event or start_year == disaster_year)
    if apply_initial_disaster:
        households, disaster_summary = disaster_decision(
            households,
            task_id=task_id,
            random_state=seed * 100000 + start_year,
            only_damaged=disaster_only_damaged,
            do_destination_choice=disaster_destination_choice,
            abm_start_year=start_year,
            flood_year=start_year,
            scenario=disaster_scenario,
            enable_relocation=enable_relocation,
        )
        disaster_applied_years.append(start_year)
        snapshot(households, f"Y{start_year} after_initial_disaster_decision\n")

    household_tp_output(start_year, households, output_dir)
    micro_output(start_year, house, households, output_dir)
    loss_summary.write_year(start_year, households)

    print("Start to calculate in-out migration net (total number)\n")
    for k in range(sim_year):
        if k % MIGRATION_BLOCK_YEARS == 0:
            block_start_year = start_year + k
            block_years = min(MIGRATION_BLOCK_YEARS, sim_year - k)
            female_block_targets, male_block_targets = build_annual_migration_targets(
                female,
                male,
                block_start_year,
                block_years,
            )
            arr_sig(f"female_migration_targets_{block_start_year}_{block_start_year + block_years}", female_block_targets)
            arr_sig(f"male_migration_targets_{block_start_year}_{block_start_year + block_years}", male_block_targets)

        start_time = time.perf_counter()
        year = start_year + int(k + 1)
        block_offset = k - (block_start_year - start_year)
        print("The year is: ", year, "\n")
        rng_demo = random.Random(seed * 100000 + year)

        households, female, male = annual_death(households, year, female, male, rng=rng_demo)
        print("   After dealth, there are", len(households), "Household\n")
        snapshot(households, f"Y{year} after_death\n")

        households = age_update_object(households)
        female, male = age_update_cohort(female, male)
        households, female, male = annual_birth(households, year, female, male, rng=rng_demo)
        print("   After birth, there are", len(households), "Household\n")
        snapshot(households, f"Y{year} after_birth\n")

        total_pop = sum(female["Num"]) + sum(male["Num"])
        print("Start to excute marriage function")
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = new_marriage(households, max_hh_ids, total_pop)
        snapshot(households, f"Y{year} after_new_marriage\n")

        print("Start to excute independece function")
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = new_household(households, max_hh_ids)
        snapshot(households, f"Y{year} after_new_household\n")

        print("Start to excute life-course migration")
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = life_course(households, max_hh_ids)
        snapshot(households, f"Y{year} after_life_course_migration\n")

        max_hh_ids = get_max_hh_ids(households)
        print("Start to excute migration function")
        migr_target = pd.DataFrame({
            "Female": female_block_targets[block_offset],
            "Male": male_block_targets[block_offset],
        })
        print(
            "TARGET",
            year,
            "F_out:",
            int(migr_target["Female"].sum()),
            "M_out:",
            int(migr_target["Male"].sum()),
            "TOTAL:",
            int(migr_target[["Female", "Male"]].to_numpy().sum()),
        )
        households, max_hh_ids = migration(households, migr_target, max_hh_ids, rng=rng_demo)
        snapshot(households, f"Y{year} after_migration\n")

        female, male = count_population_by_age_and_sex(households)
        households = old_house_update(households)
        households = live_year_update(households)
        households = [hh for hh in households if hh.members]
        total_cohort = female["Num"].sum() + male["Num"].sum()
        total_agents = sum(len(hh.members) for hh in households)
        if total_cohort != total_agents:
            print(f"YEAR {year}: MISMATCH! Cohort: {total_cohort}, Agents: {total_agents}")

        # TP evolves in every scenario, including BASE.  Flood scenarios add
        # their shock only after this common annual no-flood update.
        tp_random_state = seed * 100000 + year
        households = prepare_annual_threat_perception(households, year, tp_random_state)
        reset_annual_losses(households)
        if not enable_insurance:
            disable_insurance(households, year)

        should_apply_disaster = enable_disaster and year >= disaster_year
        if should_apply_disaster and (not disaster_single_event or year == disaster_year):
            households, disaster_summary = disaster_decision(
                households,
                task_id=task_id,
                random_state=seed * 100000 + year,
                only_damaged=disaster_only_damaged,
                do_destination_choice=disaster_destination_choice,
                abm_start_year=start_year,
                flood_year=year,
                scenario=disaster_scenario,
                enable_relocation=enable_relocation,
            )
            disaster_applied_years.append(year)
            snapshot(households, f"Y{year} after_disaster_decision\n")

        # Insurance is evaluated after the annual TP/flood update. PIns_01
        # redraws current coverage for every household each year, including
        # newly formed households, using the same posterior-mean equation.
        if enable_insurance:
            insurance_rng = np.random.default_rng(seed * 100000 + year + 7919)
            update_insurance(households, year, insurance_rng)

        # Annual output is needed to trace Zone 1/2 inter-migration without hiding moves inside 5-year gaps.
        micro_output(year, house, households, output_dir)
        #gender_num_output(year, households, output_dir) ! Feng 20260725
        household_tp_output(year, households, output_dir)
        loss_summary.write_year(year, households)

        print("Time spend: ", time.perf_counter() - start_time)

    households = [hh for hh in households if hh.members]
    print("---------")
    print("Time spend all: ", time.perf_counter() - start_time_all)
    print(len(households))
    if enable_disaster and not disaster_applied_years:
        print(f"[Disaster decision] not applied; disaster_year={disaster_year} is outside this simulation period.")
    return households


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Run ABM-IRM using data/Parameter_file.txt.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible stochastic steps.")
    parser.add_argument("--task-id", default=None, help="Task ID used in runtime output/log folder names.")
    parser.add_argument("--demographic-case", default="Medium_case", help="Folder under data/Birth_Death_Rate used for fertility and mortality rates.")
    parser.add_argument("--no-log", action="store_true", help="Print to console instead of runtime/logs.")
    parser.add_argument("--enable-disaster", action="store_true", help="Apply the annual flood disaster-decision module from --disaster-year onward.")
    parser.add_argument("--disaster-year", type=int, default=2020, help="First simulation year when the flood disaster-decision module is applied.")
    parser.add_argument("--disaster-scenario", default="SSP370", help="Water-depth scenario folder/name used by the disaster module.")
    parser.add_argument("--disaster-single-event", action="store_true", help="Apply disaster decision only in --disaster-year instead of every year afterward.")
    parser.add_argument("--disaster-all-households", action="store_true", help="Evaluate disaster decisions for all households, not only damaged households.")
    parser.add_argument("--disaster-no-destination-choice", action="store_true", help="Mark disaster movers without relocating them through utility destination choice.")
    parser.add_argument(
        "--policy-scenario",
        choices=tuple(POLICY_SCENARIOS),
        default=None,
        help=("Adaptation scenario: 0=do nothing, 1=insurance only, "
              "2=relocation only, 3=both. "
              "Selecting one also enables flood impact processing."),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse command-line arguments and launch the simulation."""
    args = build_parser().parse_args(argv)
    seed = args.seed if args.seed is not None else 1
    task_id = args.task_id if args.task_id is not None else "0"
    if args.policy_scenario is None:
        enable_disaster = args.enable_disaster
        enable_insurance = True
        enable_relocation = args.enable_disaster
        policy_scenario = "legacy"
    else:
        enable_disaster = True
        enable_insurance, enable_relocation = POLICY_SCENARIOS[args.policy_scenario]
        policy_scenario = args.policy_scenario
    configure_seed(seed)
    with run_log(task_id, enabled=not args.no_log) as log_file:
        print(f"[INFO] Using SEED = {seed}")
        print(f"[INFO] Task ID is = {task_id}")
        print(f"[INFO] Demographic case = {args.demographic_case}")
        print(f"[INFO] Policy scenario = {policy_scenario}")
        print(f"[INFO] Insurance enabled = {enable_insurance}")
        print(f"[INFO] Disaster relocation enabled = {enable_relocation}")
        if log_file:
            print(f"[INFO] Log file = {log_file}")
        run_simulation(
            seed,
            task_id,
            enable_disaster=enable_disaster,
            disaster_year=args.disaster_year,
            disaster_only_damaged=not args.disaster_all_households,
            disaster_destination_choice=not args.disaster_no_destination_choice,
            disaster_scenario=args.disaster_scenario,
            disaster_single_event=args.disaster_single_event,
            demographic_case=args.demographic_case,
            enable_insurance=enable_insurance,
            enable_relocation=enable_relocation,
        )


if __name__ == "__main__":
    main()
