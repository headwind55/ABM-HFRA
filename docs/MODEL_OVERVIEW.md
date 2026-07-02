# Model Overview

ABM-IRM stands for **Agent-based model for intra-regional migration**. It simulates household-level demographic change and residential relocation over a five-year period. The model was designed to support counterfactual demographic analysis: given a start-year population and calibrated relocation assumptions, it estimates the population and household distribution that would be expected at the end year under baseline no-flood conditions.

## Main Use Case

The model was developed for the Kuma River basin, Japan, where it supports comparison between simulated no-flood population distributions and observed census data after the 2020 flood. This comparison helps separate disaster-related displacement signals from ordinary demographic trends such as aging, birth, death, and background migration.

## Spatial Unit

The active model uses 500 m mesh units. Household agents live in mesh cells, and output can be aggregated to municipalities, flood-impact zones, or other user-defined regions if suitable grouping tables are prepared.

## Agent Types

The model represents two linked agent types:

- **Member agents**: individual people with age, gender, and marital status.
- **Household agents**: decision-making units with mesh ID, household ID, household type, agroforestry status, residential duration, and a list of member agents.

## Modules

### Household Dynamics Module (HDM)

The HDM updates demographic and household states. It includes:

- aging of individuals;
- death and birth events using cohort-related rate tables;
- inter-regional net inflow and outflow represented by age/sex migration patterns;
- marriage, independence, and life-course migration events;
- household formation and removal.

The initial household population is reconstructed from mesh-level census constraints. Elderly households and non-elderly households are assigned first, then remaining children, working-age adults, and surplus elderly members are allocated to existing households while preserving census-derived mesh totals.

### Intra-regional Migration Module (IRM)

The IRM evaluates potential residential destinations when a household receives a relocation chance from a life event. The location-choice mechanism uses a utility-based function with:

- residential duration and relocation distance, reflecting place attachment and moving effort;
- school accessibility;
- hospital accessibility;
- market accessibility;
- household-type-specific parameter adjustments, such as stronger distance constraints for agroforestry households and stronger hospital-accessibility weighting for elderly households.

For each relocation opportunity, the model samples candidate meshes from inside and outside the current municipality, evaluates utility, and assigns the household to the highest-utility candidate when relocation improves the household state.

## Current Release Scope

This cleaned release includes the baseline five-year ABM-IRM workflow. It does not include:

- active disaster-decision making;
- insurance assignment;
- calibration grid-search utilities;
- temporary intermediate pickle files;
- generated outputs or logs.

## Evaluation Indicators

The paper and supplement evaluate the model with six demographic indicators:

| Code | Description |
| --- | --- |
| HH | Number of households |
| TP | Total population |
| EP | Population of elderly people, older than 65 years |
| CP | Population of children, 5-19 years |
| AHH | Number of agroforestry households |
| EHH | Number of elderly households |

Calibration used 2010-2015, validation used 2000-2005, and application used 2015-2020 as the no-flood counterfactual period.

## Transferability

The source code can be reused for another region, but the model is not plug-and-play without rebuilding the prepared data tables. A new study region requires compatible mesh-level population data, household constraints, age/sex distributions, migration estimates, utility-location inputs, and facility-distance tables.
