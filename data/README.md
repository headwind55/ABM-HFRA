# Data inputs

This directory contains the model-ready data distributed with ABM-HFRA.

## Main groups

- `Input/`: initial population, household, and mesh attributes
- `Comparison/`: observed age-sex population tables used during initialization
- `Birth_Death_Rate/`: fertility and mortality assumptions by demographic case
- `Migration/`: migration inputs
- `Utility_location_choice/`: mesh crosswalks, loss-summary geography, and
  destination-choice attributes
- `Insurance/`: insurance model parameters
- `Disaster_decision/`: threat-perception, flood-depth, and damage inputs

## Parameter file

`Parameter_file.txt` controls the simulation window and utility parameters. It
must contain the columns `Para` and `Value`. The release setting is:

```text
start_year 2020
simulation_years 80
```

This represents 2020-2100, including the initial year. The annual flood inputs
under `Disaster_decision/Water_depth/` cover the same period for SSP126,
SSP245, SSP370, and SSP585.

Do not rename input columns or folders without updating the corresponding path
and loader code in `src/abm_irm/`.
