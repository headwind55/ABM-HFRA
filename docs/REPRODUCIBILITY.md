# Reproducibility Notes

## One-Period Run

ABM-IRM is configured for one simulation period per run. Edit `data/Parameter_file.txt` before each run:

```text
Para Value
start_year 2015
simulation_years 5
```

Then run:

```bash
python Abm_Main_apply.py --seed 1 --task-id 0
```

The resulting end year is `start_year + simulation_years`. For example, `2015` and `5` produce a 2020 output.

## Suggested Historical Checks

The cleaned repository supports these start years with bundled prepared data:

| Start year | End year | Purpose |
| --- | --- | --- |
| 2000 | 2005 | historical validation-style run |
| 2010 | 2015 | calibration-style run |
| 2015 | 2020 | no-flood counterfactual application run |

Run one period at a time. If you need to keep outputs from multiple runs, copy or rename the relevant `runtime/output/Task_ID_<task-id>/` directory before reusing the same task ID.

## Random Seed

Use `--seed` to make stochastic components repeatable for the same software and input data state:

```bash
python Abm_Main_apply.py --seed 1 --task-id 0
```

The supplement reports robustness analysis based on repeated random seeds. This public release keeps the simulation pathway but does not include the full calibration/robustness batch scripts.

## Smoke Test

A lightweight import and input-presence check is provided:

```bash
python tests/smoke_imports.py
```

## Output Locations

Runtime files are intentionally separated from source/data files:

```text
runtime/logs/
runtime/output/
runtime/analysis/
runtime/mesh_check/
```

These folders contain `.gitkeep` placeholders, while generated logs and simulation outputs are ignored by Git.

## Known Non-Reproducible Pieces

The model run itself is reproducible once prepared input files exist. However, upstream data preparation is only documented, not fully automated, because it depends on GIS processing and external datasets whose licenses and formats may differ by source/provider.
