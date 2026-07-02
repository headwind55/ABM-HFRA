"""Annual demographic dynamics for death, birth, household formation, and migration."""

from collections import Counter
import random
import sys

import numpy as np
import pandas as pd

from .Abm_Class import FamilyMember, HouseHold
from .Abm_count_update import count_population_by_age_and_sex
from .Abm_utility_normal import mesh_adm2, mesh_pair, utility_migration_normal
from .paths import data_path


MAX_AGE = 100
BIRTH_AGE_MIN = 20
BIRTH_AGE_MAX = 49
INDEPENDENCE_GROUPS = (
    (20, 25, 0.08, 0.12),
    (25, 30, 0.03, 0.06),
    (30, 35, 0.005, 0.015),
)
MARRIAGE_RATE = 0.0045
MARRIAGE_AGE_GROUPS = (
    (20, 25, 0.088),
    (25, 30, 0.321),
    (30, 35, 0.357),
    (35, 40, 0.168),
    (40, 45, 0.066),
)
LIFE_COURSE_MOVE_PROBABILITY = 0.02

death_ratio = pd.read_table(data_path("Birth_Death_Rate", "Death_Rate_Age_2000-2020.txt"), delimiter=" ")
birth_ratio = pd.read_table(data_path("Birth_Death_Rate", "Birth_Rate_Age_2000-2020.txt"), delimiter=" ")
male_ratio = pd.read_table(data_path("Birth_Death_Rate", "Birth_Sex_ratio.txt"), delimiter=" ")


def _rng(rng):
    return random if rng is None else rng


def _rate_year(year):
    return min(year, 2020)


def _members_by_age_and_sex(households, age):
    female = []
    male = []
    for household in households:
        for person in household.members:
            if person.age == age and person.sex == "F":
                female.append((household, person))
            elif person.age == age and person.sex == "M":
                male.append((household, person))
    return female, male


def _remove_people(victims):
    for household, person in victims:
        household.members = [member for member in household.members if member is not person]


def _planned_deaths(this_year, female_sim, male_sim):
    death_ratio_sex = death_ratio[death_ratio["Year"] == _rate_year(this_year)]
    female_death_ratio = death_ratio_sex[["Female"]]
    male_death_ratio = death_ratio_sex["Male"]

    planned_f = (female_sim.values.flatten() * female_death_ratio.T.values.flatten()).round().astype(int)
    planned_m = (male_sim.values.flatten() * male_death_ratio.T.values.flatten()).round().astype(int)
    planned_f = pd.Series(planned_f, index=np.arange(0, MAX_AGE + 1))
    planned_m = pd.Series(planned_m, index=np.arange(0, MAX_AGE + 1))
    return planned_f, planned_m


def annual_death(Household, this_year, female_sim, male_sim, rng=None):
    """Remove members according to annual age-sex mortality counts."""
    rng = _rng(rng)
    female_sim, male_sim = count_population_by_age_and_sex(Household)
    planned_f, planned_m = _planned_deaths(this_year, female_sim, male_sim)

    print("There are:", len(Household), "before deletion")

    for age in range(0, MAX_AGE + 1):
        target_female, target_male = _members_by_age_and_sex(Household, age)
        n_to_die_f = int(planned_f.get(age, 0))
        n_to_die_m = int(planned_m.get(age, 0))

        if n_to_die_f > len(target_female):
            print("n_to_die_female is larger...")
            sys.exit()
        if n_to_die_m > len(target_male):
            print("n_to_die_male is larger...")
            sys.exit()

        _remove_people(rng.sample(target_female, n_to_die_f))
        _remove_people(rng.sample(target_male, n_to_die_m))

    for household in Household:
        household.members = [person for person in household.members if person.age != MAX_AGE]

    female_sim, male_sim = count_population_by_age_and_sex(Household)
    return Household, female_sim, male_sim


def _birth_targets_by_age(Household, age):
    married = []
    single = []
    for household in Household:
        for person in household.members:
            if person.age == age and person.sex == "F":
                if person.marriage:
                    married.append((household, person))
                else:
                    single.append((household, person))
    return married, single


def _birth_counts(this_year, female_sim):
    birth_ratio_year = birth_ratio[str(_rate_year(this_year))]
    birth_ratio_year = 1.16 * birth_ratio_year[5:]
    birth_female_in_age = (
        female_sim.loc[BIRTH_AGE_MIN:BIRTH_AGE_MAX].values.flatten()
        * birth_ratio_year.T.values.flatten()
    ).round().astype(int)
    return pd.DataFrame(birth_female_in_age, index=np.arange(BIRTH_AGE_MIN, BIRTH_AGE_MAX + 1))


def _select_mothers(Household, birth_female_in_age, rng):
    mothers_by_age = {}
    total_birth_real = 0

    for age in range(BIRTH_AGE_MIN, BIRTH_AGE_MAX + 1):
        n_births = int(birth_female_in_age.iloc[:, 0].get(age, 0))
        married, single = _birth_targets_by_age(Household, age)

        if len(married) >= n_births:
            target_female = rng.sample(married, n_births)
        else:
            single_number = n_births - len(married)
            single_number = min(single_number, len(single))
            target_single = rng.sample(single, single_number)
            target_female = married + target_single

        mothers_by_age[age] = rng.sample(target_female, n_births)
        total_birth_real += n_births

    return mothers_by_age, total_birth_real


def _baby_sexes(this_year, total_birth_real, rng):
    male_ratio_value = float(male_ratio.loc[male_ratio["year"] == _rate_year(this_year), "male_ratio"].values[0])
    new_male = int(round(total_birth_real * male_ratio_value))
    new_female = total_birth_real - new_male
    babies_sex = np.concatenate([np.repeat("F", new_female), np.repeat("M", new_male)])
    rng.shuffle(babies_sex)
    return babies_sex


def annual_birth(Household, this_year, female_sim, male_sim, rng=None):
    """Add newborn members according to annual fertility and sex-ratio counts."""
    rng = _rng(rng)
    female_sim, male_sim = count_population_by_age_and_sex(Household)
    birth_female_in_age = _birth_counts(this_year, female_sim)
    mothers_by_age, total_birth_real = _select_mothers(Household, birth_female_in_age, rng)
    babies_sex = _baby_sexes(this_year, total_birth_real, rng)

    total_birth = 0
    for age in range(BIRTH_AGE_MIN, BIRTH_AGE_MAX + 1):
        for household, _person in mothers_by_age[age]:
            baby = FamilyMember(age=0, sex=babies_sex[total_birth])
            household.members.append(baby)
            total_birth += 1

    female_sim, male_sim = count_population_by_age_and_sex(Household)
    return Household, female_sim, male_sim


def _independence_candidates(Household):
    groups = []
    for min_age, max_age, _low, _high in INDEPENDENCE_GROUPS:
        group = []
        for household in Household:
            for person in household.members:
                if min_age <= person.age < max_age and person.marriage is False and len(household.members) >= 3:
                    group.append((household.mesh_id, household.live_year, person))
        groups.append(group)
    return groups


def _sample_independent_people(groups):
    for group in groups:
        random.shuffle(group)

    sampled_groups = []
    for group, (_min_age, _max_age, low, high) in zip(groups, INDEPENDENCE_GROUPS):
        value = random.uniform(low, high)
        sampled_groups.append(group[0:int(round(len(group) * value))])
    return sampled_groups


def _remove_independent_people(Household, selected_people):
    for mesh_id, _live_year, person in selected_people:
        for household in Household:
            if household.mesh_id == mesh_id and person in household.members:
                household.members.remove(person)
                break


def _create_independent_households(selected_people, max_hh_ids_pop):
    new_households = []
    for mesh_id, live_year, person in selected_people:
        new_household = HouseHold(
            mesh_id=mesh_id,
            hh_id=0,
            members=[person],
            old_hh=False,
            income=person.income,
            saving=person.saving,
            expenditure=person.expenditure,
            live_year=min(live_year, person.age),
        )
        new_household = utility_migration_normal(new_household)
        new_household.live_year = 0
        new_household.hh_id = max_hh_ids_pop[new_household.mesh_id - 1] + 1
        new_households.append(new_household)
        max_hh_ids_pop[new_household.mesh_id - 1] += 1
    return new_households, max_hh_ids_pop


def new_household(Household, max_hh_ids_pop):
    """Create independent households from young adult members."""
    sampled_groups = _sample_independent_people(_independence_candidates(Household))
    selected_people = sampled_groups[0] + sampled_groups[1] + sampled_groups[2]
    _remove_independent_people(Household, selected_people)
    new_households, max_hh_ids_pop = _create_independent_households(selected_people, max_hh_ids_pop)
    Household = Household + new_households
    Household.sort(key=lambda household: (household.mesh_id, household.hh_id))
    return Household, max_hh_ids_pop


def get_male_candidate(female, single_pool_male_sim):
    """Find a male marriage candidate for a selected female member."""
    candidates_sim = []
    for household_m, male in single_pool_male_sim:
        if female.age <= male.age <= female.age + 7:
            candidates_sim.append((household_m, male))
    return candidates_sim


def _single_pools(Household):
    single_pool_female = []
    single_pool_male = []
    for household in Household:
        for person in household.members:
            if 20 <= person.age < 45 and person.marriage is False:
                if person.sex == "F":
                    single_pool_female.append((household, person))
                else:
                    single_pool_male.append((household, person))
    return single_pool_female, single_pool_male


def _marriage_groups(single_pool_female, marriage_num):
    groups = [[] for _ in MARRIAGE_AGE_GROUPS]
    marr_num = [int(round(ratio * marriage_num)) for _min_age, _max_age, ratio in MARRIAGE_AGE_GROUPS]

    for household, person in single_pool_female:
        for index, (min_age, max_age, _ratio) in enumerate(MARRIAGE_AGE_GROUPS):
            if min_age <= person.age < max_age:
                groups[index].append((household, person))
                break

    return groups, marr_num


def _create_married_household(household_f, female_person, household_m, male_person, max_hh_ids_pop):
    tmp_mesh_id = random.choice([household_m.mesh_id, household_f.mesh_id])
    if tmp_mesh_id == household_m.mesh_id:
        tmp_liveyear = min(male_person.age, household_m.live_year)
    else:
        tmp_liveyear = min(female_person.age, household_f.live_year)

    new_household = HouseHold(
        mesh_id=tmp_mesh_id,
        hh_id=0,
        members=[female_person, male_person],
        old_hh=household_m.old_hh,
        income=female_person.income + male_person.income,
        saving=female_person.saving + male_person.saving,
        expenditure=female_person.expenditure + male_person.expenditure,
        live_year=tmp_liveyear,
    )
    new_household = utility_migration_normal(new_household)
    new_household.live_year = 0
    new_household.hh_id = max_hh_ids_pop[new_household.mesh_id - 1] + 1
    max_hh_ids_pop[household_m.mesh_id - 1] += 1
    return new_household, max_hh_ids_pop


def new_marriage(Household, max_hh_ids_pop, total_sum):
    """Form married couples and update household membership."""
    marriage_num = int(round(MARRIAGE_RATE * total_sum))
    print("marriage number is", marriage_num)

    single_pool_female, single_pool_male = _single_pools(Household)
    print("Ther are ", len(single_pool_female), "single female and ", len(single_pool_male), " single male")

    female_groups, marriage_targets = _marriage_groups(single_pool_female, marriage_num)

    for group, target_count in zip(female_groups, marriage_targets):
        random.shuffle(group)
        for household_f, female_person in group[0:target_count]:
            candidates = get_male_candidate(female_person, single_pool_male)
            if not candidates:
                continue

            household_m, male_person = random.choice(candidates)
            female_person.marriage = True
            male_person.marriage = True
            single_pool_male.remove((household_m, male_person))

            if random.random() < 0.6:
                new_household, max_hh_ids_pop = _create_married_household(
                    household_f, female_person, household_m, male_person, max_hh_ids_pop
                )
                Household.append(new_household)
                household_m.members = [member for member in household_m.members if member is not male_person]
            else:
                household_m.members.append(female_person)

            household_f.members = [member for member in household_f.members if member is not female_person]

    return Household, max_hh_ids_pop


def life_course(household, max_hh_ids_pop):
    """Apply ordinary life-course relocation opportunities."""
    for hh in household:
        if not hh.members:
            continue

        max_age = max(person.age for person in hh.members)
        if 30 <= max_age <= 79 and random.random() < LIFE_COURSE_MOVE_PROBABILITY:
            pre_mesh = hh.mesh_id
            hh = utility_migration_normal(hh)
            hh.live_year = 0
            hh.hh_id = max_hh_ids_pop[hh.mesh_id - 1] + 1
            max_hh_ids_pop[hh.mesh_id - 1] += 1

    return household, max_hh_ids_pop


def _has_positive_migration(migration_frame):
    return (migration_frame > 0).any().any()


def _household_removal_needs(household, migration_frame):
    needed = Counter()
    for member in household.members:
        column = "Female" if member.sex == "F" else "Male"
        needed[(member.age, column)] += 1

    for (age, column), count in needed.items():
        if age not in migration_frame.index or migration_frame.loc[age, column] < count:
            return False, None
    return True, needed


def _remove_exact_person(age, sex, need, household_f):
    removed = 0
    for household in household_f:
        if removed >= need:
            break
        member_index = 0
        while member_index < len(household.members) and removed < need:
            member = household.members[member_index]
            if member.age == age and member.sex == sex:
                del household.members[member_index]
                removed += 1
            else:
                member_index += 1
    return removed


def migrate_out(migr_f, household_f, rng=None):
    """Remove net out-migrants using household-first then person-level matching."""
    household_f = [household for household in household_f if household.members]
    household_f.sort(key=lambda household: (household.mesh_id, household.hh_id))
    migr_f = migr_f.clip(lower=0).copy()

    print("number of migrate out should be: ", migr_f.to_numpy().sum(axis=0))
    print("Total_number of migrate out should be: ", migr_f.to_numpy().sum())

    f_count = 0
    m_count = 0
    changed = True

    while changed and _has_positive_migration(migr_f) and household_f:
        changed = False
        for household in list(household_f):
            ok, needed = _household_removal_needs(household, migr_f)
            if not ok:
                continue

            for (age, column), count in needed.items():
                migr_f.loc[age, column] -= count
            for member in household.members:
                if member.sex == "M":
                    m_count += 1
                if member.sex == "F":
                    f_count += 1
            household_f.remove(household)
            changed = True

    if _has_positive_migration(migr_f) and household_f:
        for age in migr_f.index:
            for column in migr_f.columns:
                need = int(migr_f.loc[age, column])
                if need <= 0:
                    continue
                sex = "F" if column == "Female" else "M"
                removed = _remove_exact_person(age, sex, need, household_f)
                migr_f.loc[age, column] -= removed
                if sex == "M":
                    m_count += removed
                if sex == "F":
                    f_count += removed

    print("------------------")
    print("Migrate out female: ", f_count)
    print("Migrate out male: ", m_count)
    print("------------------")

    household_f = [household for household in household_f if household.members]
    residual = migr_f.clip(lower=0)
    print("residual: ", residual.sum(0))
    res_total = int(residual.to_numpy().sum())
    if res_total > 0:
        print("!!! migrate_out residual not removed (not enough candidates):", res_total)

    return household_f


def mesh_weight_fun(household_f):
    """Build mesh sampling weights for in-migration placement."""
    mesh_pair_fun = mesh_pair.copy()
    mesh_adm2_fun = mesh_adm2.copy()
    mesh_adm2_abm = mesh_adm2.copy()
    mesh_counts = Counter(household.mesh_id for household in household_f)

    total = mesh_pair_fun.copy()
    total["household"] = total["abm"].map(mesh_counts).fillna(0).astype(int)

    for i in range(len(total)):
        mesh_adm2_fun.replace(total.iloc[i]["data"], total.iloc[i]["household"], inplace=True)
        mesh_adm2_abm.replace(total.iloc[i]["data"], total.iloc[i]["abm"], inplace=True)

    mesh_weight_by_adm2 = {}
    for adm2_name in mesh_adm2.columns:
        mesh_list = mesh_adm2_abm[adm2_name].dropna().astype(int).tolist()
        hh_list = mesh_adm2_fun[adm2_name].dropna().astype(int).tolist()
        mesh_weight_by_adm2[adm2_name] = [list(item) for item in zip(mesh_list, hh_list)]

    total_hh = {key: sum(value[1] for value in mesh_values) for key, mesh_values in mesh_weight_by_adm2.items()}
    total_sum = sum(total_hh.values())
    total_hh_w = {key: value / total_sum for key, value in total_hh.items()}
    return list(total_hh_w.keys()), list(total_hh_w.values()), mesh_weight_by_adm2


def _mesh_weights(mesh_in_adm2):
    hh_values = [value[1] for value in mesh_in_adm2]
    hh_total = sum(hh_values)
    if hh_total == 0:
        return [1.0 / len(mesh_in_adm2)] * len(mesh_in_adm2)
    return [value[1] / hh_total for value in mesh_in_adm2]


def _create_in_migrant_household(age_f, sex_f, new_mesh, hh_ids, old_hh=False):
    new_hh_id = hh_ids[new_mesh - 1] + 1
    household = HouseHold(
        mesh_id=new_mesh,
        hh_id=new_hh_id,
        members=[FamilyMember(age=age_f, sex=sex_f, marriage=False)],
        old_hh=old_hh,
        income=0,
        saving=0,
        expenditure=0,
        live_year=0,
    )
    hh_ids[new_mesh - 1] += 1
    return household, hh_ids


def migrate_in(age_f, num_f, sex_f, household_f, hh_ids,
               adm2_pool_f, adm2_weight_f, mesh_weight_by_adm2_f,
               rng=None):
    """Create or place net in-migrants into the study region."""
    rng = _rng(rng)
    target_adm2 = rng.choices(adm2_pool_f, weights=adm2_weight_f, k=-num_f)
    new_hh_list = []

    for adm2 in target_adm2:
        mesh_in_adm2 = mesh_weight_by_adm2_f[str(adm2)]
        new_mesh = rng.choices(mesh_in_adm2, weights=_mesh_weights(mesh_in_adm2), k=1)[0][0]

        if 19 < age_f < 45:
            household, hh_ids = _create_in_migrant_household(age_f, sex_f, new_mesh, hh_ids, old_hh=False)
            new_hh_list.append(household)
            continue

        hh_pool = [household for household in household_f if household.mesh_id == new_mesh]
        if not hh_pool:
            household, hh_ids = _create_in_migrant_household(age_f, sex_f, new_mesh, hh_ids, old_hh=age_f >= 65)
            new_hh_list.append(household)
        else:
            rng.choice(hh_pool).add_member(FamilyMember(age=age_f, sex=sex_f, marriage=False))

    household_f.extend(new_hh_list)
    return household_f, hh_ids


def migration(household, migr_target_fun, max_hh_ids_fun, rng=None):
    """Apply net migration for one simulation year."""
    rng = _rng(rng)
    gender = ["Male", "Female"]
    gender_abm = ["M", "F"]

    household = migrate_out(migr_target_fun, household, rng=rng)
    adm2_pool, adm2_weight, mesh_weight_by_adm2 = mesh_weight_fun(household)

    f_count_in = 0
    m_count_in = 0

    for i in range(2):
        target = migr_target_fun[[gender[i]]]
        ta_neg = target[(target < 0).any(axis=1)].reset_index()
        ta_neg = np.array(ta_neg)
        total_in = int(np.abs(ta_neg[:, 1]).sum())
        print("--------")
        print("migrate in people number is: ", total_in)

        for j in range(len(ta_neg)):
            age = int(ta_neg[j][0])
            num_in = int(abs(ta_neg[j][1]))

            if gender[i] == "Male":
                m_count_in += num_in
            else:
                f_count_in += num_in

            household, max_hh_ids_fun = migrate_in(
                age,
                ta_neg[j][1],
                gender_abm[i],
                household,
                max_hh_ids_fun,
                adm2_pool,
                adm2_weight,
                mesh_weight_by_adm2,
                rng=rng,
            )

    print("--------------")
    print("Migrate_in female is: ", f_count_in)
    print("Migrate_in male is: ", m_count_in)
    print("--------------\n")
    return household, max_hh_ids_fun
