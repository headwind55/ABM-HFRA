"""Population counting and annual age/household status updates."""

import pandas as pd
import numpy as np
import sys
import os
import time
import random
from .paths import data_path
from .config import read_sim_period
from .Abm_Class import HouseHold, FamilyMember


def count_population_by_age_and_sex(Household):
    """
    Count number of males and females at each age in the Household list.
    Returns a DataFrame with columns: Age, Male, Female
    """
    ages_m = []
    ages_f = []
    for hh in Household:
        for m in hh.members:
            a = int(m.age)
            if m.sex == 'M':
                ages_m.append(a)
            elif m.sex == 'F':
                ages_f.append(a)
    male_counts = pd.Series(ages_m).value_counts()
    female_counts = pd.Series(ages_f).value_counts()
    age_range = np.arange(0, 101)
    male_out = male_counts.reindex(age_range, fill_value=0).astype(int)
    female_out = female_counts.reindex(age_range, fill_value=0).astype(int)
    male_df = pd.DataFrame({'Num': male_out.values}, index=age_range)
    female_df = pd.DataFrame({'Num': female_out.values}, index=age_range)
    return (female_df, male_df)


def age_update_cohort(female_fun, male_fun):
    """Age the female and male cohort tables by one year."""
    for gender in (female_fun, male_fun):
        gender.index = gender.index + 1
    zero_age = pd.DataFrame({'Num': [0]}, index=[0])
    female_fun = pd.concat([zero_age, female_fun], axis=0)
    female_fun = female_fun.drop(index=101, errors='ignore')
    male_fun = pd.concat([zero_age, male_fun], axis=0)
    male_fun = male_fun.drop(index=101, errors='ignore')
    return (female_fun, male_fun)


def age_update_object(household):
    """Age each individual member object by one year."""
    for hh in household:
        for member in hh.members:
            member.age_one_year()
    return household


def get_max_hh_ids(household_fun):
    """Return the maximum household ID currently used in each mesh."""
    mesh_pair_fun = pd.read_table(data_path('Utility_location_choice', 'mesh_pair.txt'), sep=' ')
    zero = pd.DataFrame({'hh_id': np.repeat(0, len(mesh_pair_fun))})
    zero = pd.concat([mesh_pair_fun.iloc[:, :1], zero], axis=1)
    hh_df = pd.DataFrame([{'mesh_id': hh.mesh_id, 'hh_id': hh.hh_id} for hh in household_fun])
    max_hh_ids_fun = hh_df.groupby('mesh_id')['hh_id'].max()
    max_hh_ids_fun = pd.DataFrame(max_hh_ids_fun)
    max_hh_ids_fun.index = max_hh_ids_fun.index - 1
    result = zero.add(max_hh_ids_fun, fill_value=0)
    result = np.ravel(np.array(result['hh_id'], int))
    return result


def old_house_update(household):
    """Update elderly-household status from the current member composition."""
    for hh in household:
        if all((person.age >= 65 for person in hh.members)):
            hh.old_hh = True
        else:
            hh.old_hh = False
    return household


def get_gender_ratio(data):
    """Calculate age-specific female/male ratios from observed census data."""
    data = data[['male', 'female']]
    ratio = data['male'] / data.sum(axis=1)
    return ratio


def gender_assign(input_fun, gender_ratio_fun, household):
    """Assign sex to members whose sex is not fixed during household initialization."""
    age_dis = input_fun['Age'].value_counts().sort_index()
    male_age_dis = round(age_dis * gender_ratio_fun[:100]).astype(int)
    female_age_dis = age_dis - male_age_dis
    male_age_dis = pd.DataFrame({'Num': male_age_dis})
    female_age_dis = pd.DataFrame({'Num': female_age_dis})
    male_age_dis.loc[100] = 0
    female_age_dis.loc[100] = 0
    sex = ['F', 'M']
    female_list = []
    male_list = []
    for hh in household:
        for person in hh.members:
            if person.sex == 'F':
                female_list.append(person.age)
            if person.sex == 'M':
                male_list.append(person.age)
    female_list = pd.Series([int(x) for x in female_list])
    male_list = pd.Series([int(x) for x in male_list])
    age_range = np.arange(0, 101)
    female_list = female_list.value_counts().reindex(age_range, fill_value=0).to_numpy()
    male_list = male_list.value_counts().reindex(age_range, fill_value=0).to_numpy()
    female_out = pd.DataFrame({'Num': female_list})
    male_out = pd.DataFrame({'Num': male_list})
    remain_female = female_age_dis - female_out
    remain_male = male_age_dis - male_out
    genders_remain = []
    for i in range(len(remain_female)):
        remain_age = ['M'] * remain_male['Num'][i].astype(int) + ['F'] * remain_female['Num'][i].astype(int)
        random.shuffle(remain_age)
        genders_remain.append(remain_age)
    for hh in household:
        for person in hh.members:
            if person.sex == None:
                person.sex = genders_remain[person.age][0]
                del genders_remain[person.age][0]
    print('There are ', sum(np.array(female_age_dis)), ' female in the begining')
    print('There are ', sum(np.array(male_age_dis)), ' male in the begining')
    return household
