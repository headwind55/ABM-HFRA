from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abm_irm.Abm_Main_apply import POLICY_SCENARIOS, build_parser


def test_four_policy_scenarios_are_independent_switch_combinations():
    assert POLICY_SCENARIOS == {
        "0": (False, False),
        "1": (True, False),
        "2": (False, True),
        "3": (True, True),
    }


def test_policy_scenario_cli_accepts_all_four_choices():
    parser = build_parser()
    for name in POLICY_SCENARIOS:
        assert parser.parse_args(["--policy-scenario", name]).policy_scenario == name
