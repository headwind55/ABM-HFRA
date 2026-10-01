from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abm_irm.Abm_Class import FamilyMember, HouseHold
from abm_irm.Abm_insurance import disable_insurance, initialize_insurance, insurance_probability, update_insurance
from abm_irm.Abm_disaster_decision import prepare_annual_threat_perception


def test_pins01_annual_coverage_smoke():
    rng = np.random.default_rng(3)
    hh = HouseHold(1, 1, [FamilyMember(40, "F")], False)
    initialize_insurance([hh], 2020, rng, initial_population=True)
    assert hh.insurance_initialized
    assert hh.insurance_expire_year is None
    assert 0.0 <= hh.p_insurance <= 1.0
    assert hh.insurance_origin == "PIns01_initial_population"
    hh.tp = 1.0
    expected = insurance_probability(hh)
    counts = update_insurance([hh], 2021, rng)
    assert isinstance(hh.insured, bool)
    assert hh.insurance_expire_year is None
    assert hh.p_insurance == expected
    assert sum(counts[key] for key in ("joined", "retained", "lapsed", "remained_uninsured")) == 1
    assert hh.insurance_decision.endswith("PIns01")


def test_new_household_uses_pins01_not_fixed_probability():
    rng = np.random.default_rng(7)
    hh = HouseHold(2, 1, [FamilyMember(35, "M")], False)
    counts = update_insurance([hh], 2025, rng)
    assert counts["new_households"] == 1
    assert hh.insurance_origin == "PIns01_new_household"
    assert 0.0 <= hh.p_insurance <= 1.0
    assert hh.insurance_expire_year is None


def test_initial_tp_and_insurance_are_scenario_independent():
    """BASE and SSP branches must be identical before the flood is applied."""
    def make_households():
        return [
            HouseHold(1, 1, [FamilyMember(72, "F")], True),
            HouseHold(2, 2, [FamilyMember(40, "M"), FamilyMember(12, "F")], False),
            HouseHold(3, 3, [FamilyMember(35, "F")], False),
            HouseHold(4, 4, [FamilyMember(45, "F"), FamilyMember(47, "M")], False),
        ]

    baseline = make_households()
    flood_scenario = make_households()
    tp_seed = 202001
    insurance_seed = 209920

    prepare_annual_threat_perception(baseline, 2020, tp_seed)
    prepare_annual_threat_perception(flood_scenario, 2020, tp_seed)
    initialize_insurance(baseline, 2020, np.random.default_rng(insurance_seed), initial_population=True)
    initialize_insurance(flood_scenario, 2020, np.random.default_rng(insurance_seed), initial_population=True)

    for base_hh, ssp_hh in zip(baseline, flood_scenario):
        assert base_hh.tp == ssp_hh.tp
        assert base_hh.insurance_efficacy == ssp_hh.insurance_efficacy
        assert base_hh.insurance_affordability == ssp_hh.insurance_affordability
        assert base_hh.provider_trust == ssp_hh.provider_trust
        assert base_hh.p_insurance == ssp_hh.p_insurance
        assert base_hh.insured == ssp_hh.insured


def test_no_insurance_policy_forces_households_uninsured():
    hh = HouseHold(5, 1, [FamilyMember(40, "F")], False)
    initialize_insurance([hh], 2020, np.random.default_rng(11), initial_population=True)

    disable_insurance([hh], 2020)

    assert hh.insured is False
    assert hh.insurance_initialized is False
    assert hh.p_insurance == 0.0
    assert hh.insurance_decision == "disabled"
    assert hh.insurance_origin == "policy_scenario_no_insurance"
