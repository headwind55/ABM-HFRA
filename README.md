# ABM-IRM

ABM-IRM is a cleaned Python implementation of the **Agent-based model for intra-regional migration** used to simulate household-level demographic redistribution in the Kuma River basin, Japan. The model was prepared for research on counterfactual demographic simulation: it reconstructs how population and households would have evolved under a no-flood condition, then supports comparison with observed census outcomes.

This public version focuses on the five-year baseline simulation workflow. Disaster-decision making, insurance assignment, calibration scratch scripts, temporary pickle handoffs, duplicate data copies, and generated output files were removed from the repository.

## Scientific Context

The model accompanies a manuscript on detecting flood-induced displacement by counterfactual demographic simulation in a high-resolution agent-based approach. In the paper, ABM-IRM is used to construct a no-flood demographic baseline for the 2020 Kuma River flood by combining:

- a household dynamics module (HDM) for aging, birth, death, inter-regional net migration, household formation, and household dissolution;
- an intra-regional migration module (IRM) for household relocation within the basin using a utility-based location-choice function;
- mesh-level demographic inputs at 500 m resolution;
- local amenity accessibility data for schools, hospitals, and markets.

The repository is intended to make the model structure, required inputs, and reproducible five-year run workflow transparent. Some preprocessing inputs are derived from licensed or externally maintained spatial/statistical datasets, so this repository should be treated as a model release plus prepared example data, not a universal turnkey data-preparation pipeline.

## Authors

- Shi Feng, Disaster Prevention Research Institute, Kyoto University
- Tomohiro Tanaka, Disaster Prevention Research Institute, Kyoto University

See [AUTHORS.md](AUTHORS.md) for repository authorship notes.

## Project Structure

```text
ABM-IRM/
|-- Abm_Main_apply.py              # root launcher
|-- data/
|   |-- Parameter_file.txt         # start year, simulation period, utility parameters
|   |-- Birth_Death_Rate/          # birth, death, and birth-sex-ratio tables
|   |-- Comparison/                # observed female/male age distributions
|   |-- Input/                     # population, mesh-age, and FAR/FOR input tables
|   |-- Migration/                 # estimated/observed migration net-flow tables
|   `-- Utility_location_choice/   # mesh-pair, adm2, and facility-distance tables
|-- docs/                          # model, data, reproducibility, and release notes
|-- runtime/                       # generated logs, outputs, checks; ignored by Git
|-- src/abm_irm/                   # model source code
`-- tests/                         # lightweight smoke test
```

## Configure One Simulation

Each run uses exactly one five-year simulation period, configured in `data/Parameter_file.txt`:

```text
Para Value
start_year 2015
simulation_years 5
a_y 0.1
...
```

To run `2000 -> 2005`, edit the first two rows:

```text
start_year 2000
simulation_years 5
```

Do not put multiple start years in this file. Run one period, archive or inspect the output, then edit `Parameter_file.txt` for another period.

## Installation

Use Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

For editable development:

```bash
pip install -e .
```

## Run

From the project root:

```bash
python Abm_Main_apply.py --seed 1 --task-id 0
```

By default, console output is written to `runtime/logs/`. To print directly to the terminal:

```bash
python Abm_Main_apply.py --seed 1 --task-id 0 --no-log
```

## Outputs

Generated files are written under `runtime/`:

- `runtime/output/Initial_<task-id>/Pop_household_initial_seed.txt`
- `runtime/output/Task_ID_<task-id>/Pop_household_<end-year>_seed.txt`
- `runtime/output/Task_ID_<task-id>/Gender_age_dis_<end-year>.txt`
- `runtime/analysis/Initialization_condition_check/gender_ini.txt`
- `runtime/logs/ABM_run_TASK_ID<task-id>_<timestamp>.log`

Runtime files are excluded from Git by `.gitignore`.

## Required Input Data

See [data/README.md](data/README.md) for the exact file list and [docs/DATA_PREPARATION.md](docs/DATA_PREPARATION.md) for the preprocessing logic. The bundled cleaned data currently support `2000`, `2010`, and `2015` as simulation start years.

## Documentation

- [docs/MODEL_OVERVIEW.md](docs/MODEL_OVERVIEW.md): model purpose, modules, and assumptions
- [docs/DATA_PREPARATION.md](docs/DATA_PREPARATION.md): input-data requirements and preprocessing workflow
- [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md): commands for one-period runs and basic checks
- [docs/GITHUB_RELEASE_CHECKLIST.md](docs/GITHUB_RELEASE_CHECKLIST.md): items to resolve before public release

## Important Limitations

- The model currently represents a no-flood baseline workflow; the disaster-decision module is not active in this release.
- The active release does not include an insurance module.
- Some preprocessing steps depend on external geospatial/statistical data sources and GIS operations that are not fully automated in this repository.
- The model is calibrated for the Kuma River basin context; transfer to another region requires rebuilding the mesh-level demographic, migration, and amenity-distance inputs.

## Analysis Scripts

This first public release contains the core ABM-IRM simulation model and prepared input-data structure. Post-processing and analysis scripts are not included yet; they will be selected, cleaned, and added in a later release.

## License

ABM-IRM source code and repository documentation are released under the [MIT License](LICENSE).

Prepared input data may be subject to the terms of their original statistical and geospatial data sources. See [DATA_LICENSE.md](DATA_LICENSE.md) before making the repository public or redistributing the bundled data.

## Citation

If you use this repository, cite the repository metadata in [CITATION.cff](CITATION.cff). When the related paper is accepted or assigned a DOI, update `CITATION.cff` with the final article citation.
