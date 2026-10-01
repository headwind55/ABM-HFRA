# Model overview

ABM-HFRA extends the ABM-IRM demographic and migration model with household
flood exposure, damage and loss, insurance take-up, and disaster relocation.

## Annual sequence

For each simulation year, the model:

1. updates demographic processes and ordinary life-course migration;
2. recalculates household life-stage groups;
3. reads annual mesh-level effective flood depth for the chosen SSP;
4. updates household threat perception and applies a flood shock to exposed
   households;
5. calculates household damage and loss;
6. applies insurance coverage and payout when insurance is enabled;
7. evaluates disaster relocation when relocation is enabled; and
8. writes population, household, decision, and loss outputs.

For a simulation beginning in 2020, the initial-year disaster stage is applied
using the 2020 water-depth input before the first subsequent annual demographic
step.

## Adaptation switches

`--policy-scenario` independently switches insurance take-up and disaster
relocation. Scenario 0 is therefore a no-adaptation counterfactual, not a
no-migration or no-flood simulation. Life-course migration, exposure, damage,
and loss calculation continue in scenario 0.

## Disaster destinations

Disaster-relocating households use the existing utility-based destination
choice mechanism. Candidate destinations are restricted to meshes with
effective water depth less than or equal to zero in the selected scenario and
year. This restriction applies to disaster relocation; ordinary life-course
migration follows its own destination-choice process.

## Flood loss and insurance

Gross loss is calculated from building, contents, and vehicle damage. The
current research insurance setting uses full recovery for a covered event.
Insurance status at the time of flooding determines payout; insurance taken up
after a flood applies to later events. See
`data/Disaster_decision/README.md` for units and detailed output fields.

## Input scenarios

- Demography: high-mortality/low-fertility, medium, and
  low-mortality/high-fertility cases
- Flood forcing: SSP126, SSP245, SSP370, and SSP585 annual inputs for 2020-2100
