from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abm_irm.Abm_Class import FamilyMember, HouseHold
from abm_irm.config import read_sim_period
from abm_irm.paths import data_path


def test_basic_objects_and_paths():
    hh = HouseHold(mesh_id=1, hh_id=1, members=[FamilyMember(age=40, sex="F")], old_hh=False)
    assert hh.get_family_size() == 1
    start_year, sim_years = read_sim_period()
    assert start_year in {2000, 2010, 2015}
    assert sim_years > 0
    assert data_path("Input", f"Population_input_{start_year}.txt").exists()
    assert data_path("Input", f"Mesh_ID_Age_1yr_{start_year}.txt").exists()


if __name__ == "__main__":
    test_basic_objects_and_paths()
    print("smoke_imports passed")
