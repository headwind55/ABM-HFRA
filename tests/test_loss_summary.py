from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from abm_irm.Abm_Class import FamilyMember, HouseHold
from abm_irm.Abm_disaster_decision import damage_ratio
from abm_irm.Abm_loss import record_flood_loss, reset_annual_losses
from abm_irm.Abm_loss_summary import LossSummaryWriter, load_loss_geography


class LossSummaryTests(unittest.TestCase):
    def test_exposure_location_zero_areas_and_cumulative_accounting(self):
        geography = pd.DataFrame({"Mesh_ID": [1, 2, 3],
                                  "Municipality": [10, 20, 20], "Zone": [1, 2, 3]})
        insured = HouseHold(1, 1, [FamilyMember(40, "F")], False)
        uninsured = HouseHold(2, 1, [FamilyMember(40, "M")], False)
        insured.insured = True
        households = [insured, uninsured]
        for hh in households:
            record_flood_loss(hh, 0.6, damage_ratio(0.6))
        insured.mesh_id = 3  # Damage remains allocated to zone 1 / municipality 10.
        one_loss = insured.gul
        with TemporaryDirectory() as folder:
            writer = LossSummaryWriter(folder, 1, "SSP126", 2020, "Medium_case", geography)
            writer.write_year(2020, households)
            reset_annual_losses(households)
            writer.write_year(2021, households)
            record_flood_loss(uninsured, 1.0, damage_ratio(1.0))
            later_loss = uninsured.gul
            writer.write_year(2022, households)
            zone = pd.read_csv(Path(folder) / "Loss_summary_zone.csv")
            mun = pd.read_csv(Path(folder) / "Loss_summary_municipality.csv")
            region = pd.read_csv(Path(folder) / "Loss_summary_region.csv")
        self.assertEqual(len(zone), 9)
        first = zone[zone.Year == 2020].set_index("Area_ID")
        self.assertAlmostEqual(first.loc[1, "Annual_GUL_manen"], one_loss)
        self.assertEqual(first.loc[1, "Annual_OOP_manen"], 0)
        self.assertAlmostEqual(first.loc[2, "Annual_OOP_manen"], one_loss)
        self.assertEqual(first.loc[3, "Annual_GUL_manen"], 0)
        self.assertEqual(region.loc[region.Year == 2021, "Annual_GUL_manen"].iloc[0], 0)
        last = region[region.Year == 2022].iloc[0]
        self.assertAlmostEqual(last.Cumulative_GUL_manen, 2 * one_loss + later_loss)
        self.assertAlmostEqual(last.Cumulative_OOP_manen, one_loss + later_loss)
        self.assertAlmostEqual(last.Projection_Cumulative_GUL_manen, later_loss)
        self.assertAlmostEqual(last.Projection_Cumulative_OOP_manen, later_loss)
        for table in (zone, mun):
            pd.testing.assert_series_equal(
                table.groupby("Year").Annual_GUL_manen.sum(),
                region.set_index("Year").Annual_GUL_manen, check_names=False)

    def test_real_maps_cover_all_three_zones_and_municipalities(self):
        geography = load_loss_geography()
        self.assertEqual(len(geography), 2225)
        self.assertEqual(geography.Municipality.nunique(), 11)
        self.assertEqual(set(geography.Zone), {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
