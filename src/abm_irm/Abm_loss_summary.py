"""Annual and accumulated flood losses by exposure municipality and zone."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from .Abm_loss import LOSS_POLICY
from .paths import data_path


MONEY_FIELDS = {
    "GUL": "gul", "Payout": "insurance_payout", "OOP": "oop",
    "Building_GUL": "building_gul", "Contents_GUL": "contents_gul",
    "Vehicle_GUL": "vehicle_gul",
}


def load_loss_geography() -> pd.DataFrame:
    """Match internal ABM mesh IDs to the existing municipal and zone maps."""
    folder = data_path("Utility_location_choice")
    pair = pd.read_csv(folder / "mesh_pair.txt", sep=r"\s+")
    adm = pd.read_csv(folder / "adm2_mesh_pair.txt", sep=r"\s+")
    zone = pd.read_csv(folder / "Zone_mesh_pair.txt", sep=r"\s+")
    result = pair.merge(adm, left_on="data", right_on="Mesh_ID", how="left", validate="one_to_one")
    result = result.merge(zone, on="Mesh_ID", how="left", validate="one_to_one")
    if result[["adm2", "zone"]].isna().any().any():
        raise ValueError("A simulation mesh has no municipality or zone")
    result = result[["abm", "adm2", "zone"]].astype(int)
    result.columns = ["Mesh_ID", "Municipality", "Zone"]
    if set(result.Zone) != {1, 2, 3}:
        raise ValueError("Expected exactly zones 1, 2 and 3")
    # Check the consolidated zone table against the zone files used in plots.
    for number in (1, 2, 3):
        codes = pd.read_csv(folder / f"zone_{number}_mesh_id.txt", sep=r"\s+").iloc[:, 0]
        expected = set(pair.loc[pair.data.isin(codes), "abm"].astype(int))
        actual = set(result.loc[result.Zone == number, "Mesh_ID"])
        if actual != expected:
            raise ValueError(f"Inconsistent definitions for Zone {number}")
    return result


class LossSummaryWriter:
    """Keep small per-run totals; save a complete, atomic table after each year."""

    def __init__(self, output_dir, seed, scenario, start_year, demographic_case,
                 geography=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = int(seed)
        self.scenario = scenario
        self.start_year = int(start_year)
        self.last_year = None
        self.geography = load_loss_geography() if geography is None else geography
        self.rows = {"zone": [], "municipality": [], "region": []}
        self.accumulated = {}
        metadata = {
            "policy": LOSS_POLICY, "seed": seed, "scenario": scenario,
            "demographic_case": demographic_case, "monetary_unit": "manen",
            "JPY_per_unit": 10000, "start_year": start_year,
            "coverage": "insured at impact: all three assets paid in full; uninsured: no payout",
            "location": "mesh at flood impact before disaster relocation",
            "cumulative": f"includes {start_year}; projection cumulative excludes {start_year}",
            "valuation": "constant asset values, undiscounted, no inflation; annual damage uses fully restored assets",
        }
        (self.output_dir / "Loss_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8")

    def write_year(self, year, households):
        expected = self.start_year if self.last_year is None else self.last_year + 1
        if year != expected:
            raise ValueError(f"Loss summary expected year {expected}, got {year}")
        records = []
        for hh in households:
            gul, payout, oop = float(hh.gul), float(hh.insurance_payout), float(hh.oop)
            if not all(map(math.isfinite, (gul, payout, oop))) or min(gul, payout, oop) < 0:
                raise ValueError("Non-finite or negative household loss")
            if not math.isclose(gul, payout + oop, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("Household GUL does not equal payout plus OOP")
            if bool(hh.insured_at_flood) and oop != 0.0:
                raise ValueError("Full-coverage insured household has nonzero OOP")
            if not bool(hh.insured_at_flood) and payout != 0.0:
                raise ValueError("Uninsured household received a payout")
            records.append({
                "Mesh_ID": int(hh.loss_mesh_id), "Households": 1,
                "Affected_Households": int(gul > 0),
                "Affected_Insured_Households": int(gul > 0 and hh.insured_at_flood),
                **{name: float(getattr(hh, attr)) for name, attr in MONEY_FIELDS.items()},
            })
        columns = ["Mesh_ID", "Households", "Affected_Households",
                   "Affected_Insured_Households", *MONEY_FIELDS]
        frame = pd.DataFrame(records, columns=columns).merge(
            self.geography, on="Mesh_ID", how="left", validate="many_to_one")
        if frame[["Municipality", "Zone"]].isna().any().any():
            raise ValueError("Household loss mesh is absent from the geographic mapping")
        measures = columns[1:]
        for level, group_col in (("zone", "Zone"), ("municipality", "Municipality"),
                                 ("region", None)):
            if group_col:
                ids = sorted(self.geography[group_col].unique())
                totals = frame.groupby(group_col)[measures].sum().reindex(ids, fill_value=0)
            else:
                totals = pd.DataFrame([frame[measures].sum()], index=[0])
            for area, values in totals.iterrows():
                row = {"Year": int(year), "Seed": self.seed, "Scenario": self.scenario,
                       "Area_ID": int(area), "Unit": "manen"}
                for name in ("Households", "Affected_Households", "Affected_Insured_Households"):
                    row[name] = int(values[name])
                for name in MONEY_FIELDS:
                    row[f"Annual_{name}_manen"] = float(values[name])
                for name in ("GUL", "Payout", "OOP"):
                    for projection in (False, True):
                        key = (level, int(area), name, projection)
                        increment = float(values[name]) if not projection or year > self.start_year else 0.0
                        self.accumulated[key] = self.accumulated.get(key, 0.0) + increment
                        prefix = "Projection_Cumulative" if projection else "Cumulative"
                        row[f"{prefix}_{name}_manen"] = self.accumulated[key]
                self.rows[level].append(row)
            destination = self.output_dir / f"Loss_summary_{level}.csv"
            temporary = destination.with_suffix(".tmp")
            pd.DataFrame(self.rows[level]).to_csv(temporary, index=False)
            temporary.replace(destination)
        self.last_year = year
