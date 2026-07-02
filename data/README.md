# Data Inputs

ABM-IRM expects model inputs under this `data/` directory. The model-ready files in this folder are prepared inputs for the cleaned five-year simulation workflow. For preprocessing background, see [../docs/DATA_PREPARATION.md](../docs/DATA_PREPARATION.md).

## Parameter File

`Parameter_file.txt` contains both run-period settings and utility parameters. It must have two columns: `Para` and `Value`.

Required run-period rows:

- `start_year`: simulation start year, currently one of `2000`, `2010`, or `2015`
- `simulation_years`: number of years to simulate, commonly `5`

The same file also stores utility parameters used by location-choice routines: `a_y`, `a_ds`, `a_dh`, `a_dm`, `a_dd`, `a_dd_f`, `a_dh_e`, `N_mesh`, and `N_mesh_in`.

## Input

`Input/Population_input_<year>.txt`
: Individual population records for the start year. Required columns include `Mesh_ID`, `ID`, and `Age`.

`Input/Mesh_ID_Age_1yr_<year>.txt`
: Mesh-level household and one-year age distribution table for the start year.

`Input/Mesh_ID_FARFOR_<year>.txt`
: Mesh-level agroforestry/farmer household information used during household assignment.


`Input/Mesh_ID_Age_1yr_2020.txt`, if present, is retained as an end-year/reference mesh-age table. It is not a supported simulation start year unless matching `Population_input_2020`, `Mesh_ID_FARFOR_2020`, and comparison files are also prepared.

## Observed Demography

`Comparison/Pop_sex_<year>.txt`
: Observed female/male age distribution used for initialization and cohort migration calculations.

## Birth and Death Rates

`Birth_Death_Rate/Birth_Rate_Age_2000-2020.txt`
: Age-specific birth-rate table.

`Birth_Death_Rate/Death_Rate_Age_2000-2020.txt`
: Age-specific death-rate table.

`Birth_Death_Rate/Birth_Sex_ratio.txt`
: Birth sex-ratio table.

## Migration

`Migration/Migration.txt`
: Estimated net-flow rate table retained for reference and alternative migration settings.

`Migration/Migration_2010-2015.txt`
: Migration-flow table used by the active cohort migration calculation.

## Utility Location Choice

`Utility_location_choice/mesh_pair.txt`
: Mapping between ABM mesh IDs and national mesh IDs.

`Utility_location_choice/adm2_mesh_id.txt`
: Administrative-region mesh grouping table.

`Utility_location_choice/mesh_facility_distances.csv`
: Precomputed mesh-to-facility distance table. This file depends on upstream spatial preprocessing of school, hospital, and market locations.

## Supported Start Years

The bundled cleaned data currently support `2000`, `2010`, and `2015`. To add another start year, add matching `Population_input`, `Mesh_ID_Age_1yr`, `Mesh_ID_FARFOR`, and `Comparison/Pop_sex` files, then confirm migration and rate tables cover the simulation period.
