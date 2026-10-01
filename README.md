# ABM-HFRA

ABM-HFRA is an application of ABM-IRM for household flood-risk analysis in the
Kawabe Dam study area. It simulates demographic change, life-course migration,
annual flood exposure and damage, insurance take-up, and disaster-induced
relocation from 2020 to 2100.

The release supports four independently controlled adaptation scenarios:

| Scenario | Insurance take-up | Disaster relocation |
| --- | --- | --- |
| `0` | Off | Off |
| `1` | On | Off |
| `2` | Off | On |
| `3` | On | On |

Scenario 0 disables the two adaptation modules; flood exposure, damage, loss,
and normal life-course migration remain active.

## Authors

- Shi Feng, Disaster Prevention Research Institute, Kyoto University
- Tomohiro Tanaka, Disaster Prevention Research Institute, Kyoto University

See [AUTHORS.md](AUTHORS.md) for repository authorship notes.

## Requirements

- Python 3.10 or later
- Dependencies listed in `requirements.txt`

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Quick start

Run from the repository root:

```bash
python Abm_Main_apply.py --seed 1 --task-id example --policy-scenario 0 --disaster-scenario SSP126
```

Change `--policy-scenario` to `1`, `2`, or `3` for the other adaptation
combinations. Available flood scenarios are `SSP126`, `SSP245`, `SSP370`, and
`SSP585`. Results and logs are written below `runtime/` and are excluded from
version control.

The simulation period is controlled by `data/Parameter_file.txt`. The bundled
release is configured for 2020-2100 (`start_year = 2020`,
`simulation_years = 80`).

## Model behavior

- Annual flood depth is read for the selected SSP and simulation year.
- Household damage and gross loss are calculated even in policy scenario 0.
- Insurance payout is available only to insured households meeting the active
  coverage conditions.
- Disaster relocation is distinct from ordinary life-course migration.
- Disaster movers choose among non-inundated destination meshes for the
  current flood year.

See [docs/USAGE.md](docs/USAGE.md) for command options, outputs, ensemble runs,
and testing. See [docs/MODEL_OVERVIEW.md](docs/MODEL_OVERVIEW.md) for the annual
model sequence and the interpretation of the adaptation scenarios.

## Repository layout

```text
data/       Model-ready input data
docs/       User and model documentation
scripts/    Batch and ensemble launchers
src/        ABM-HFRA Python source
tests/      Automated tests
runtime/    Generated outputs and logs (not committed)
```

## Citation and license

Source code and documentation are released under the [MIT License](LICENSE).
Prepared input data may be governed by their original data-source terms; see
[DATA_LICENSE.md](DATA_LICENSE.md). Citation metadata are provided in
[CITATION.cff](CITATION.cff), and author information is in
[AUTHORS.md](AUTHORS.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
