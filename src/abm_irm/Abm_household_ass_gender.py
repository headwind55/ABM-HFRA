"""Initial household reconstruction and demographic attribute assignment."""

import random

import numpy as np
import pandas as pd

from .Abm_Class import FamilyMember, HouseHold
from .config import read_sim_period
from .paths import data_path


AGE_CHILD_MAX = 19
AGE_ADULT_MIN = 20
AGE_ELDER_MIN = 65
COUPLE_AGE_GAP = 3
AGE_GAP_PAIRING_THRESHOLD = 100

year, _sim_years = read_sim_period()
farmer_ratio = pd.read_table(data_path("Input", f"Mesh_ID_FARFOR_{year}.txt"), sep=" ")
farmer_ratio["Mesh_ID1"] = farmer_ratio["Mesh_ID1"] + 1
farmer_ratio["Ratio"] = farmer_ratio["IND_AGRFOR"] // 2


def gender_assign(household):
    """Assign one male and one female to two-person households."""
    sexes = ["M", "F"]
    random.shuffle(sexes)
    for person, sex in zip(household.members, sexes):
        person.sex = sex

    if len(household.members) == 2:
        for person in household.members:
            person.marriage = True

    return household


def elder_houses(x_house: int, y_elder: int):
    """Return two-person, one-person, and residual elderly household counts."""
    if y_elder <= 2 * x_house:
        tpp_house = y_elder - x_house
        opp_house = x_house - tpp_house
        remain_old = 0
    else:
        tpp_house = x_house
        opp_house = 0
        remain_old = y_elder - 2 * x_house

    return tpp_house, opp_house, remain_old


def non_elder_house(x_house: int, y_middle: int):
    """Return two-person, one-person, and residual non-elderly household counts."""
    if y_middle <= 2 * x_house:
        tpp_house = y_middle - x_house
        opp_house = x_house - tpp_house
        remain_middle = 0
    else:
        tpp_house = x_house
        opp_house = 0
        remain_middle = y_middle - 2 * x_house

    return tpp_house, opp_house, remain_middle


def Assign_remain_to_non(non_old_house, Opp_non_old, youngs, remain_mid, remain_old):
    """Allocate children and residual adults/elders into non-elderly households."""
    tpp_non_old_number = len(non_old_house) - Opp_non_old
    max_assign = min(tpp_non_old_number, len(youngs))

    if max_assign == 0:
        remain_young = youngs
    else:
        for i in range(max_assign):
            non_old_house[-Opp_non_old - (i + 1)].add_member(youngs[-(i + 1)])
        remain_young = youngs[:-max_assign]

    remain_people = remain_young + remain_mid + remain_old
    random.shuffle(remain_people)

    for person in remain_people:
        random.shuffle(non_old_house)
        for household in non_old_house:
            if household.add_member(person):
                break

    return non_old_house


def Pairing_function(man_group, woman_group):
    """Pair candidate adults by the configured age-gap rule."""
    fail = []
    success = []

    for man in man_group:
        possible = [person for person in woman_group if person.age == man.age - COUPLE_AGE_GAP]
        if not possible:
            fail.append(man)
            continue

        woman = random.choice(possible)
        woman_group.remove(woman)
        success.append([man, woman])

    remaining = fail + woman_group
    return success, remaining


def _household_targets(house_fun, mesh_id):
    house_info = house_fun[house_fun["Mesh_ID_abm"] == mesh_id]
    house_info = np.ravel(np.array(house_info))
    return house_info[1], house_info[2]


def _member_pools(input_fun, mesh_id):
    mesh_demo = input_fun[input_fun["Mesh_ID"] == mesh_id]
    people = [FamilyMember(row["Age"]) for _, row in mesh_demo.iterrows()]

    elders = [person for person in people if person.age >= AGE_ELDER_MIN]
    elders = elders[::-1]
    middles = [person for person in people if AGE_ADULT_MIN <= person.age < AGE_ELDER_MIN]
    youngs = [person for person in people if person.age <= AGE_CHILD_MAX]
    return elders, middles, youngs


def _new_household(mesh_id, hh_id, members, old_hh):
    household = HouseHold(mesh_id=mesh_id, hh_id=hh_id, members=members, old_hh=old_hh)
    return gender_assign(household)


def _build_elder_households(mesh_id, elders, old_house_count, hh_count):
    tpp_house, opp_house, _remain_old = elder_houses(old_house_count, len(elders))
    elder_index = 0
    households = []

    for _ in range(tpp_house):
        households.append(_new_household(mesh_id, hh_count + 1, elders[elder_index:elder_index + 2], True))
        elder_index += 2
        hh_count += 1

    for _ in range(opp_house):
        households.append(_new_household(mesh_id, hh_count + 1, elders[elder_index:elder_index + 1], True))
        elder_index += 1
        hh_count += 1

    return households, elders[elder_index:], hh_count


def _build_non_elder_households(mesh_id, middles, non_old_house_count, hh_count):
    tpp_house, opp_house, _remain_mid = non_elder_house(non_old_house_count, len(middles))

    if len(middles) > AGE_GAP_PAIRING_THRESHOLD:
        return _build_age_gap_households(mesh_id, middles, tpp_house, opp_house, hh_count)

    return _build_sequential_non_elder_households(mesh_id, middles, tpp_house, opp_house, hh_count)


def _build_age_gap_households(mesh_id, middles, tpp_house, opp_house, hh_count):
    households = []
    non_old_count = 0
    middles_copy = middles.copy()
    random.shuffle(middles_copy)

    male_group = middles_copy[:tpp_house]
    female_group = middles_copy[tpp_house:]
    couples, remaining_people = Pairing_function(male_group, female_group)

    for couple in couples:
        households.append(_new_household(mesh_id, hh_count + 1, couple, False))
        hh_count += 1
        non_old_count += 2

    remaining_people.sort(key=lambda person: person.age, reverse=True)
    fail_pair_num = tpp_house - len(couples)

    for _ in range(fail_pair_num):
        selected_members = remaining_people[0:2]
        remaining_people = remaining_people[2:]
        households.append(_new_household(mesh_id, hh_count + 1, selected_members, False))
        hh_count += 1
        non_old_count += 2

    for _ in range(opp_house):
        selected_member = remaining_people[0:1]
        remaining_people = remaining_people[1:]
        households.append(_new_household(mesh_id, hh_count + 1, selected_member, False))
        hh_count += 1
        non_old_count += 1

    return households, remaining_people, hh_count


def _build_sequential_non_elder_households(mesh_id, middles, tpp_house, opp_house, hh_count):
    households = []
    non_old_count = 0

    for _ in range(tpp_house):
        selected_members = middles[non_old_count:non_old_count + 2]
        households.append(_new_household(mesh_id, hh_count + 1, selected_members, False))
        non_old_count += 2
        hh_count += 1

    for _ in range(opp_house):
        selected_member = middles[non_old_count:non_old_count + 1]
        households.append(_new_household(mesh_id, hh_count + 1, selected_member, False))
        non_old_count += 1
        hh_count += 1

    return households, middles[non_old_count:], hh_count


def _assign_farmer_households(households, mesh_id):
    farmer_num = farmer_ratio[farmer_ratio["Mesh_ID1"] == mesh_id]["Ratio"].values[0]
    farmer_num = min(farmer_num, len(households))

    random.shuffle(households)
    for i in range(farmer_num):
        households[i].agri = True

    households.sort(key=lambda household: household.hh_id)
    return households


def Assign_house(input_fun, house_fun, mesh_id):
    """Build all household agents for one mesh from population and household tables."""
    old_house_count, non_old_house_count = _household_targets(house_fun, mesh_id)
    elders, middles, youngs = _member_pools(input_fun, mesh_id)

    hh_count = 0
    elder_households, remain_old_member, hh_count = _build_elder_households(
        mesh_id, elders, old_house_count, hh_count
    )

    non_elder_households, remain_mid_member, hh_count = _build_non_elder_households(
        mesh_id, middles, non_old_house_count, hh_count
    )

    _, opp_house_mid, _ = non_elder_house(non_old_house_count, len(middles))
    non_elder_households = Assign_remain_to_non(
        non_elder_households, opp_house_mid, youngs, remain_mid_member, remain_old_member
    )

    households = non_elder_households + elder_households
    households = _assign_farmer_households(households, mesh_id)
    return [household for household in households if household.members]


age_y = 20
age_o = 65
r_ratio = 0.5


def gen_int(range):
    """Generate a random integer within a closed interval."""
    low, high = range
    return random.randint(low, high)


def initial_live_year(household):
    """Assign initial residential duration to households."""
    for hh in household:
        ages = [member.age for member in hh.members if member.age is not None]
        oldest_age = max(ages, default=None)

        if oldest_age - age_y > 0:
            hh.live_year = gen_int((1, oldest_age - age_y + 1))
        else:
            hh.live_year = 1

        if hh.mesh_id == 799:
            print(hh)

    return household


def live_year_update(household):
    """Increase residential duration for households that remain in place."""
    for hh in household:
        hh.liveyear_update()
    return household
