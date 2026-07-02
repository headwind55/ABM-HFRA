"""Cohort-based demographic projection used to estimate baseline migration."""

import random
import pandas as pd
import numpy as np
import statistics as ss
import math
import os
import sys
from .paths import data_path
from .config import read_sim_period
from .Abm_Class import HouseHold, FamilyMember

start_year, sim_year = read_sim_period()
death_ratio = pd.read_table(data_path('Birth_Death_Rate', 'Death_Rate_Age_2000-2020.txt'), sep=' ')
birth_ratio = pd.read_table(data_path('Birth_Death_Rate', 'Birth_Rate_Age_2000-2020.txt'), sep=' ')
male_ratio = pd.read_table(data_path('Birth_Death_Rate', 'Birth_Sex_ratio.txt'), sep=' ')


def age_update_cohort(female_fun, male_fun):
    """Age the cohort table by one simulation year."""
    for gender in (female_fun, male_fun):
        gender.index = gender.index + 1
    zero_age_female = pd.DataFrame({'Female': [0]}, index=[0])
    zero_age_male = pd.DataFrame({'Male': [0]}, index=[0])
    female_fun = pd.concat([zero_age_female, female_fun], axis=0)
    female_fun = female_fun.drop(index=101, errors='ignore')
    male_fun = pd.concat([zero_age_male, male_fun], axis=0)
    male_fun = male_fun.drop(index=101, errors='ignore')
    return (female_fun, male_fun)


def annual_death(this_year, female_sim, male_sim):
    """Apply cohort mortality rates for one year."""
    if this_year <= 2020:
        death_ratio_sex = death_ratio[death_ratio['Year'] == this_year]
    else:
        death_ratio_sex = death_ratio[death_ratio['Year'] == 2020]
    female_death_ratio = death_ratio_sex[['Female']]
    male_death_ratio = death_ratio_sex['Male']
    death_female_in_age = (female_sim.values.flatten() * female_death_ratio.T.values.flatten()).round().astype(int)
    death_male_in_age = (male_sim.values.flatten() * male_death_ratio.T.values.flatten()).round().astype(int)
    death_female_in_age = pd.DataFrame(death_female_in_age, index=np.arange(0, 101))
    death_male_in_age = pd.DataFrame(death_male_in_age, index=np.arange(0, 101))
    death_female_in_age.columns = ['Female']
    death_male_in_age.columns = ['Male']
    female_sim = female_sim - death_female_in_age
    male_sim = male_sim - death_male_in_age
    return (female_sim, male_sim)


def annual_birth(this_year, female_sim, male_sim):
    """Apply cohort fertility and birth sex-ratio rates for one year."""
    if this_year <= 2020:
        birth_ratio_year = birth_ratio[str(this_year)]
    else:
        this_year = 2020
        birth_ratio_year = birth_ratio[str(2020)]
    birth_ratio_year = 1.16 * birth_ratio_year[5:]
    birth_female_in_age = (female_sim.loc[20:49].values.flatten() * birth_ratio_year.T.values.flatten()).round().astype(int)
    birth_female_in_age = pd.DataFrame(birth_female_in_age, index=np.arange(20, 50))
    new_female = birth_female_in_age.sum(axis=0) * (1 - male_ratio[male_ratio['year'] == this_year]['male_ratio'].values[0])
    new_female = int(round(new_female.loc[0]))
    new_male = birth_female_in_age.sum(axis=0) - new_female
    new_male = int(new_male.loc[0])
    female_sim.loc[0, 'Female'] = new_female
    male_sim.loc[0, 'Male'] = new_male
    return (female_sim, male_sim)
input = pd.read_table(data_path('Comparison', 'Pop_sex_' + str(start_year) + '.txt'), sep=' ')
male = input.iloc[:, 1:2].copy()
female = input.iloc[:, 2:3].copy()
male.columns = ['Male']
female.columns = ['Female']
for i in range(sim_year):
    thisyear = start_year + i
    female, male = annual_death(thisyear, female, male)
    thisyear = thisyear + 1
    female, male = age_update_cohort(female, male)
    female, male = annual_birth(thisyear, female, male)
'read flow-net ratio (average) data'
flow_rate = pd.read_table(data_path('Migration', 'Migration_2010-2015.txt'), sep=' ')
male_diff = round(-male * flow_rate[['Male']]).astype(int)
female_diff = round(-female * flow_rate[['Female']]).astype(int)


def distribute(sim_year, array):
    """Spread a five-year net migration difference across annual age cohorts."""
    initial_df = pd.DataFrame()
    for i in range(len(array)):
        total = int(array[i])
        q, r = divmod(total, sim_year)
        annual_num = np.full(sim_year, q, dtype=int)
        if r:
            annual_num[:r] += 1
        annual_num_df = pd.DataFrame(np.array(annual_num))
        initial_df = pd.concat([initial_df, annual_num_df], axis=1)
    return initial_df
male_diff = np.ravel(np.array(male_diff))
female_diff = np.ravel(np.array(female_diff))
male_annual = distribute(sim_year, male_diff)
print(male_annual)
female_annual = distribute(sim_year, female_diff)
male_annual = np.array(-male_annual)
female_annual = np.array(-female_annual)
trial = male_annual[0][male_annual[0] < 0]
