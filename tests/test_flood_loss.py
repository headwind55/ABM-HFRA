from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abm_irm.Abm_Class import FamilyMember, HouseHold
from abm_irm.Abm_disaster_decision import assign_damage_ratio, damage_ratio
from abm_irm.Abm_loss import record_flood_loss, reset_annual_losses
from abm_irm.Abm_output import household_tp_output


def household(insured=False):
    hh = HouseHold(12, 1, [FamilyMember(40, "F")], False)
    hh.insured = insured
    return hh


class FloodLossTests(unittest.TestCase):
    def test_insured_loss_and_pre_move_location(self):
        hh = household(insured=True)
        damage = damage_ratio(0.6)
        record_flood_loss(hh, 0.6, damage)
        self.assertAlmostEqual(hh.gul, damage["gross_loss"])
        self.assertAlmostEqual(hh.building_payout, hh.building_gul)
        self.assertAlmostEqual(hh.contents_payout, hh.contents_gul)
        self.assertAlmostEqual(hh.vehicle_payout, hh.vehicle_gul)
        self.assertEqual(hh.oop, 0.0)
        self.assertEqual(hh.insurance_payout, hh.gul)
        hh.mesh_id = 99
        hh.insured = False
        self.assertTrue(hh.insured_at_flood)
        self.assertEqual(hh.loss_mesh_id, 12)

    def test_uninsured_loss_and_annual_reset(self):
        hh = household()
        damage = damage_ratio(1.0)
        record_flood_loss(hh, 1.0, damage)
        self.assertEqual(hh.insurance_payout, 0.0)
        self.assertAlmostEqual(hh.oop, hh.gul)
        hh.insured = True
        record_flood_loss(hh, 1.0, damage)
        self.assertEqual(hh.oop, 0.0)
        self.assertEqual(hh.insurance_payout, hh.gul)
        reset_annual_losses([hh])
        self.assertEqual((hh.gul, hh.insurance_payout, hh.oop), (0.0, 0.0, 0.0))

    def test_assignment_and_household_output(self):
        hh = household(insured=True)
        damage = {"flood_depth_m": 0.6, **damage_ratio(0.6)}
        with patch("abm_irm.Abm_disaster_decision.load_damage_by_mesh",
                   return_value={12: damage}):
            households, affected = assign_damage_ratio([hh], 2020, "SSP126")
        self.assertEqual(households, [hh])
        self.assertEqual(affected, 1)
        self.assertAlmostEqual(hh.psy, damage["weight_damage_ratio"])
        with TemporaryDirectory() as directory:
            household_tp_output(2020, [hh], directory)
            row = pd.read_csv(Path(directory) / "Household_TP_2020_seed.txt", sep=r"\s+").iloc[0]
        self.assertAlmostEqual(row["GUL"], hh.gul)
        self.assertAlmostEqual(row["OOP"], hh.oop)
        self.assertEqual(row["Loss_Mesh_ID"], 12)
        self.assertTrue(bool(row["Insured_At_Flood"]))


if __name__ == "__main__":
    unittest.main()
