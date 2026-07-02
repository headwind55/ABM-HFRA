"""Command-line entry point for the cleaned ABM-IRM 5-year simulation."""

from __future__ import annotations
import argparse
import contextlib
import datetime as _dt
import hashlib
import random
import sys
import time
import numpy as np
import pandas as pd
from .config import read_sim_period
from .paths import data_path, output_path, runtime_path


def configure_seed(seed: int) -> None:
    """Seed Python and NumPy random number generators."""
    random.seed(seed)
    np.random.seed(seed)

@contextlib.contextmanager
def run_log(task_id: str, enabled: bool=True):
    """Redirect one run's console output to a timestamped runtime log."""
    if not enabled:
        yield None
        return
    timestamp = _dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = runtime_path('logs', f'ABM_run_TASK_ID{task_id}_{timestamp}.log')
    original_stdout, original_stderr = (sys.stdout, sys.stderr)
    with open(log_file, 'w', buffering=1, encoding='utf-8') as handle:
        sys.stdout = handle
        sys.stderr = handle
        try:
            yield log_file
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def arr_sig(name, a):
    """Print a compact signature for cohort arrays used by the run."""
    a = np.ascontiguousarray(a)
    h = hashlib.sha256(a.tobytes()).hexdigest()[:16]
    print(f'[COHORT_SIG] {name}: shape={a.shape} sum={a.sum()} min={a.min()} max={a.max()} sha={h}')


def snapshot(households, tag: str) -> None:
    """Print a compact population checksum for a simulation stage."""
    female = sum((1 for hh in households for p in hh.members if p.sex == 'F'))
    male = sum((1 for hh in households for p in hh.members if p.sex == 'M'))
    checksum = sum((p.age for hh in households for p in hh.members))
    print(tag, 'F', female, 'M', male, 'sumAge', checksum)


def run_simulation(seed: int, task_id: str):
    """Run one configured ABM-IRM simulation period."""
    from .Abm_cohort_initial_application import male_annual, female_annual
    from .Abm_count_update import age_update_cohort, age_update_object, count_population_by_age_and_sex, gender_assign, get_gender_ratio, get_max_hh_ids, old_house_update
    from .Abm_household_ass_gender import Assign_house, initial_live_year, live_year_update
    from .Abm_output import gender_num_output, micro_output
    from .Abm_pop_dynamics import annual_birth, annual_death, life_course, migration, new_household, new_marriage

    arr_sig('male_annual', male_annual)
    arr_sig('female_annual', female_annual)
    start_time_all = time.perf_counter()
    start_year, sim_year = read_sim_period()
    population = pd.read_table(data_path('Input', f'Population_input_{start_year}.txt'), delimiter=' ')
    census = pd.read_table(data_path('Comparison', f'Pop_sex_{start_year}.txt'), sep=' ')
    gender_ratio = get_gender_ratio(census)
    house = pd.read_table(data_path('Input', f'Mesh_ID_Age_1yr_{start_year}.txt'), delimiter=' ')
    house = pd.concat([house.iloc[:, 0:1], house.iloc[:, 3:5]], axis=1)
    households = []
    print('Start to assign popluation to meshes\n')
    for i in range(len(house)):
        household_mesh = Assign_house(population, house, house['Mesh_ID_abm'][i])
        households = households + household_mesh
        households = old_house_update(households)
    print('There are ', len(households), 'household')
    print('Population assignment finishes\n')
    print('After initiliaztion, there are', len(households), 'Household\n')
    print('Start to assign the remaining gender')
    households = gender_assign(population, gender_ratio, households)
    female, male = count_population_by_age_and_sex(households)
    output = pd.concat([female, male], axis=1)
    output.columns = ['Female', 'Male']
    output.to_csv(runtime_path('analysis', 'Initialization_condition_check', 'gender_ini.txt'), sep=' ', index=None)
    households = initial_live_year(households)
    micro_output('initial', house, households, output_path(f'Initial_{task_id}'))
    print('Start to calculate in-out migration net (total number)\n')
    for k in range(sim_year):
        start_time = time.perf_counter()
        year = start_year + int(k + 1)
        print('The year is: ', year, '\n')
        rng_demo = random.Random(seed * 100000 + year)
        households, female, male = annual_death(households, year, female, male, rng=rng_demo)
        print('   After dealth, there are', len(households), 'Household\n')
        snapshot(households, f'Y{year} after_death\n')
        households = age_update_object(households)
        female, male = age_update_cohort(female, male)
        households, female, male = annual_birth(households, year, female, male, rng=rng_demo)
        print('   After birth, there are', len(households), 'Household\n')
        snapshot(households, f'Y{year} after_birth\n')
        total_pop = sum(female['Num']) + sum(male['Num'])
        print('Start to excute marriage function')
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = new_marriage(households, max_hh_ids, total_pop)
        snapshot(households, f'Y{year} after_new_marriage\n')
        print('Start to excute independece function')
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = new_household(households, max_hh_ids)
        snapshot(households, f'Y{year} after_new_household\n')
        print('Start to excute life-course migration')
        max_hh_ids = get_max_hh_ids(households)
        households, max_hh_ids = life_course(households, max_hh_ids)
        snapshot(households, f'Y{year} after_life_course_migration\n')
        max_hh_ids = get_max_hh_ids(households)
        print('Start to excute migration function')
        migr_target = pd.DataFrame({'Female': female_annual[k], 'Male': male_annual[k]}).copy()
        migr_target.index = migr_target.index - sim_year + k + 1
        migr_target = migr_target[migr_target.index >= 0]
        print('TARGET', year, 'F_out:', int(migr_target['Female'].sum()), 'M_out:', int(migr_target['Male'].sum()), 'TOTAL:', int(migr_target[['Female', 'Male']].to_numpy().sum()))
        households, max_hh_ids = migration(households, migr_target, max_hh_ids, rng=rng_demo)
        snapshot(households, f'Y{year} after_migration\n')
        female, male = count_population_by_age_and_sex(households)
        households = old_house_update(households)
        households = live_year_update(households)
        households = [hh for hh in households if hh.members]
        total_cohort = female['Num'].sum() + male['Num'].sum()
        total_agents = sum((len(hh.members) for hh in households))
        if total_cohort != total_agents:
            print(f'YEAR {year}: MISMATCH! Cohort: {total_cohort}, Agents: {total_agents}')
        print('Time spend: ', time.perf_counter() - start_time)
    households = [hh for hh in households if hh.members]
    print('---------')
    print('Time spend all: ', time.perf_counter() - start_time_all)
    print(len(households))
    output_dir = output_path(f'Task_ID_{task_id}')
    micro_output(year, house, households, output_dir)
    gender_num_output(year, households, output_dir)
    return households


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description='Run the cleaned ABM-IRM simulation configured by data/Parameter_file.txt.')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible stochastic steps.')
    parser.add_argument('--task-id', default=None, help='Task ID used in runtime output/log folder names.')
    parser.add_argument('--no-log', action='store_true', help='Print to console instead of runtime/logs.')
    return parser


def main(argv: list[str] | None=None) -> None:
    """Parse command-line arguments and launch the simulation."""
    args = build_parser().parse_args(argv)
    seed = args.seed if args.seed is not None else 1
    task_id = args.task_id if args.task_id is not None else '0'
    configure_seed(seed)
    with run_log(task_id, enabled=not args.no_log) as log_file:
        print(f'[INFO] Using SEED = {seed}')
        print(f'[INFO] Task ID is = {task_id}')
        if log_file:
            print(f'[INFO] Log file = {log_file}')
        run_simulation(seed, task_id)
if __name__ == '__main__':
    main()
