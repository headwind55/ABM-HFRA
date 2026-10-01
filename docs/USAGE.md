# Usage guide

## Single simulation

Run commands from the repository root. A reproducible run should specify a
seed, task ID, policy scenario, demographic case, and flood scenario:

```bash
python Abm_Main_apply.py \
  --seed 1 \
  --task-id MED_P0_SSP126_seed01 \
  --demographic-case Medium_case \
  --policy-scenario 0 \
  --disaster-year 2020 \
  --disaster-scenario SSP126
```

The four policy scenarios are:

- `0`: neither insurance take-up nor disaster relocation
- `1`: insurance take-up only
- `2`: disaster relocation only
- `3`: both insurance take-up and disaster relocation

Flood exposure and loss calculation remain active in all four cases. Normal
life-course migration also remains active when disaster relocation is off.

## Important command options

| Option | Meaning |
| --- | --- |
| `--seed` | Random seed for stochastic processes |
| `--task-id` | Unique name used for output and log directories |
| `--demographic-case` | Demographic input folder under `data/Birth_Death_Rate/` |
| `--policy-scenario` | Adaptation scenario `0`, `1`, `2`, or `3` |
| `--disaster-year` | First year of the flood module |
| `--disaster-scenario` | `SSP126`, `SSP245`, `SSP370`, or `SSP585` |
| `--disaster-single-event` | Apply the disaster module only in the first disaster year |
| `--no-log` | Print to the console instead of writing the standard run log |

Use the built-in help for the complete current list:

```bash
python Abm_Main_apply.py --help
```

## Simulation period

Edit `data/Parameter_file.txt` to change `start_year` and `simulation_years`.
The distributed annual flood inputs cover 2020-2100, so a flood projection run
must stay within that range.

## Outputs

Each run creates a task directory below `runtime/output/`. Output files include
population and household records, flood-decision summaries, household loss
records, geographic loss summaries, and loss metadata. Monetary loss columns
ending in `_manen` are expressed in 10,000 JPY.

`Cumulative_*` fields include the initial year. `Projection_Cumulative_*`
fields use the initial year as a zero baseline and accumulate subsequent
projection years.

## Policy-1 ensemble

The supplied ensemble launcher runs insurance-only scenario 1 for 10 seeds and
four SSPs (40 simulations):

```bash
python scripts/run_PIns01_MED_seed_ensemble_1.py
```

The launcher uses at most five concurrent workers. Change `max_workers` in the
script to match the CPU, memory, and scheduler policy of the target system.

## Tests

Install the development requirements and run:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```
