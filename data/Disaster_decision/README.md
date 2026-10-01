# Disaster-decision input data

This folder contains runtime inputs for the ABM-IRM disaster-decision module.

## Active future-projection workflow

- `Water_depth/SSP126/mesh_eff_depth_SSP126_<year>.csv`: annual projected effective water depth by ABM mesh for 2020-2100. The disaster module reads the file matching the current simulation year and converts `eff_wd` into household damage ratio.
- `HBM_results/HBM_lifestage_profile_pool.csv`: questionnaire-derived PA, SC, CP, SP, disaster experience, and T0-year profiles sampled once for each household when TP is first initialized.
- `HBM_results/HBM_lifestage_migration_coefficients.csv`: posterior mean coefficients from Tanaka's recommended life-stage varying-intercept migration model.
- `TP_parameter/TP12_distribution_model_parameters.csv`: shared revised TP12 initial distribution, annual decay, and flood-shock parameters.

## TP and household grouping logic

Household life-stage group is recalculated at every annual disaster-decision stage from the current household members. This lets a household become `Child_hh`, `Elderly_hh`, `Single`, or `Other_adult` as births, deaths, aging, and household transitions occur.

TP is persistent. A household samples PA/SC/CP/SP, experience, T0 year, and TP0 only once. In later years, TP decays from the previous update year. If the household is exposed to flood water in the current year, the flood shock is added to the decayed pre-flood TP.

## Projected water depth

Model-ready annual files are bundled under `Water_depth/<SSP>/` for SSP126,
SSP245, SSP370, and SSP585. Each scenario covers 2020-2100. The legacy
`mesh_eff_depth.csv` is retained only as a fallback for a single 2020 event;
future-projection runs should use the annual scenario files.

## Household flood-loss outputs

Each annual `runtime/output/Task_ID_<task>/Household_TP_<year>_seed.txt` now
contains building, contents, vehicle and total GUL, insurance payout and OOP.
`Loss_Mesh_ID` is the household's mesh at flood impact (before any relocation),
while `Mesh_ID` is its location when the annual record is written. Loss fields
are reset to zero in no-flood years. `Insured_At_Flood` is captured before the
post-flood annual insurance redraw, so insurance bought after a flood does not
pay for that event.

The current asset values are 2418 (building), 880 (contents), and 320 (vehicle),
as in the existing damage calculation. All three are in **万円** (10,000 JPY),
so 2418 means 24.18 million JPY. GUL, payout and OOP are also recorded in
万円; multiply by 10,000 to convert an output value to JPY.
The selected research assumption, `full_all_assets_v1`, pays ALL building,
contents and vehicle damage when `Insured_At_Flood=True`: payout equals GUL
and OOP is exactly zero. Without insurance, payout is zero and OOP equals
GUL. There are no deductibles, exclusions or payout limits under this rule.
This is an explicit research scenario rather than a calibrated Japanese
insurance contract. The existing `housevalue` field is not used because it
is not currently populated with an independently verified property valuation.

Each run also saves `Loss_summary_zone.csv`, `Loss_summary_municipality.csv`,
`Loss_summary_region.csv`, and `Loss_metadata.json`. The summaries contain
annual GUL, payouts, OOP and asset-specific GUL, plus accumulated GUL, payouts
and OOP. `Cumulative_*` includes 2020; `Projection_Cumulative_*` starts at
zero in 2020 and sums the 80 projection years 2021-2100. All money columns
end in `_manen`. Values are undiscounted and use constant asset values, with
no inflation, depreciation or persistent unrepaired damage. Every year's
damage calculation uses fully restored assets at the current household mesh.

Household records are retained for audit, while geographic summary files are
provided for analysis. Losses remain assigned to their impact location even
if the household moves later. PIns_01 timing is unchanged: post-flood coverage
draws apply to subsequent floods; newly created households are initialized at
the annual insurance-update stage after the flood.
