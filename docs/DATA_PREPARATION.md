# Data Preparation Guide

ABM-IRM depends on several prepared tables. Some of these files are directly derived from public statistical sources, while others require spatial preprocessing. This document explains what the repository expects and how the original application prepared the data.

## Repository Input Folders

```text
data/
|-- Parameter_file.txt
|-- Birth_Death_Rate/
|-- Comparison/
|-- Input/
|-- Migration/
`-- Utility_location_choice/
```

The exact file names expected by the current code are listed in [data/README.md](../data/README.md).

## Core Data Requirements

### Mesh-Level Population and Household Inputs

Files such as `Input/Population_input_2015.txt`, `Input/Mesh_ID_Age_1yr_2015.txt`, and `Input/Mesh_ID_FARFOR_2015.txt` define the start-year population, age structure, household constraints, and agroforestry household information.

In the original application, county-level census data were downscaled to 500 m meshes using night-time population data as a residential mask/reference. This avoided assigning people to non-residential mountainous or forested areas. The workflow was:

1. collect county-level census data with household and 5-year age-group information;
2. collect 500 m night-time population data, using year 2005 as the spatial redistribution reference;
3. intersect county polygons with 500 m mesh geometries;
4. distribute county-level population into residential mesh cells according to night-time population weights;
5. convert/downscale age groups to one-year age classes using municipal-level age-by-sex census data;
6. export the model-ready `Population_input`, `Mesh_ID_Age_1yr`, and `Mesh_ID_FARFOR` files.

### Observed Demographic Comparison Files

`Comparison/Pop_sex_<year>.txt` files contain observed age-by-sex distributions. They are used for initialization checks and cohort migration calculations.

### Birth and Death Rate Tables

`Birth_Death_Rate/` stores fertility, mortality, and birth sex-ratio tables used by the household dynamics module.

### Migration Tables

`Migration/Migration.txt` is retained as the estimated net-flow rate table. `Migration/Migration_2010-2015.txt` is used by the active cohort migration calculation in this cleaned release.

The research workflow estimated inter-regional net migration with cohort-based projection. Population was projected forward with aging, birth, and death processes, and the difference between projected and observed census population was interpreted as net migration. Average net migration ratios across historical five-year periods were used as baseline no-flood migration tendencies.

### Utility Location Choice Inputs

`Utility_location_choice/mesh_facility_distances.csv` is a precomputed mesh-to-facility distance table. It requires geospatial locations for:

- schools;
- hospitals;
- markets, including supermarkets, drug stores, and convenience stores depending on source availability.

In the paper workflow, school and hospital locations came from GSI datasets, while market data were compiled from OpenStreetMap and BODIK. Preparing this file for another region requires GIS processing to calculate distances from candidate residential meshes to the nearest relevant amenities.

`Utility_location_choice/mesh_pair.txt` maps model mesh IDs to national mesh IDs. `Utility_location_choice/adm2_mesh_id.txt` stores administrative-region mesh groupings used by the location-choice routines.

## Original Data Sources Mentioned in the Manuscript/Supplement

| Data type | Dataset | Source | Years used |
| --- | --- | --- | --- |
| Geospatial | County-level census with 5-year age groups | ESRI Japan | 2000, 2005, 2010, 2015, 2020 |
| Geospatial | Night-time census / mesh-level population | ESRI Japan | 2005 |
| Geospatial | Land use | GSI / MLIT National Land Numerical Information | 2016 |
| Geospatial | School locations | GSI / MLIT National Land Numerical Information | 2023 |
| Geospatial | Hospital locations | GSI / MLIT National Land Numerical Information | 2020 |
| Geospatial | Market locations | OpenStreetMap and BODIK | 2025 |
| Statistical | Municipal one-year age/sex census | e-Stat | 2000, 2005, 2010, 2015, 2020 |
| Statistical | Fertility and mortality rates | IPSS | Application dependent |

Check licensing and redistribution conditions for each source before publishing derived data.

## Reusing ABM-IRM in Another Region

To apply ABM-IRM elsewhere, prepare at minimum:

- start-year individual/member population records by mesh;
- mesh-level household counts and age distributions;
- observed age-by-sex comparison tables;
- birth, death, and birth-sex-ratio tables;
- estimated net migration rates or a replacement migration table;
- mesh-pair and administrative grouping files;
- mesh-to-school, mesh-to-hospital, and mesh-to-market distance tables;
- calibrated utility parameters in `Parameter_file.txt`.

The current repository does not automate all upstream GIS preprocessing. For a public GitHub release, it is better to state this explicitly than to imply that users can reproduce all data files from raw sources with one command.
