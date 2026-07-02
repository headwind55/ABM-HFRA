"""Runtime output writers for household and age-sex distribution results."""

import random
import pandas as pd
import numpy as np
import statistics as ss
import math
import os
import sys
from collections import defaultdict
from .paths import runtime_path
from .Abm_Class import HouseHold, FamilyMember


def mesh_extraction(year_fuc, x, household, process):
    """Extract households located in one mesh."""
    for hh in household:
        if hh.mesh_id == x:
            with open(runtime_path('mesh_check', str(year_fuc) + '_Mesh_' + str(x) + '_' + str(process) + '_.txt'), 'a', encoding='utf-8') as f:
                print('hosuehold: ', hh, file=f)


def build_mesh_index(household_f):
    """Index households by mesh for faster output assembly."""
    mesh_index = defaultdict(list)
    for hh in household_f:
        mesh_index[hh.mesh_id].append(hh)
    return mesh_index


def micro_output(this_year, house_fun, household, output_dir_fun):
    """Write household-level simulation output."""
    mesh_index = build_mesh_index(household)
    base_meshes = set(house_fun['Mesh_ID_abm'])
    occ_meshes = {hh.mesh_id for hh in household}
    mesh_list = sorted(base_meshes | occ_meshes)
    results = []
    for mesh in mesh_list:
        mesh_hhs = mesh_index.get(mesh, [])
        total_household = len(mesh_hhs)
        total_pop = 0
        child_pop = 0
        old_pop = 0
        elder = 0
        agr_house = 0
        for hh in mesh_hhs:
            total_pop += len(hh.members)
            if hh.old_hh == True:
                elder += 1
            if hh.agri == True:
                agr_house += 1
            for m in hh.members:
                if m.age <= 19 and m.age >= 5:
                    child_pop += 1
                if m.age >= 65:
                    old_pop += 1
        results.append([mesh, total_household, elder, total_pop, child_pop, old_pop, agr_house])
    initial = pd.DataFrame(results, columns=['Mesh_ID', 'Households', 'Elder_Households', 'Total_Population', 'Children', 'Older', 'Agri_Household'])
    print('In the output, total_population is: ', initial['Total_Population'].sum())
    filename = os.path.join(output_dir_fun, f'Pop_household_{this_year}_seed.txt')
    initial.to_csv(filename, sep=' ', index=None)
    total_direct = sum((len(hh.members) for hh in household))
    mesh_set = set(house_fun['Mesh_ID_abm'])
    missing_hhs = [hh for hh in household if hh.mesh_id not in mesh_set]
    print('total_direct:', total_direct)
    print('households in meshes not listed:', len(missing_hhs))
    print('people in missing meshes:', sum((len(hh.members) for hh in missing_hhs)))
    print('example missing mesh ids:', sorted({hh.mesh_id for hh in missing_hhs})[:10])


def gender_num_output(this_year, household, output_dir_fun):
    """Write age-sex distribution output."""
    female_collect = []
    male_collect = []
    female_collect, male_collect, unknown = ([], [], [])
    for hh in household:
        for person in hh.members:
            if person.sex == 'F':
                female_collect.append(person.age)
            elif person.sex == 'M':
                male_collect.append(person.age)
            else:
                unknown.append(person.age)
    if unknown:
        print('WARNING: found unknow sex value ...')
    female_collect = pd.Series([int(x) for x in female_collect])
    male_collect = pd.Series([int(x) for x in male_collect])
    age_range = np.arange(0, 102)
    female_collect = female_collect.value_counts().reindex(age_range, fill_value=0).to_numpy()
    male_collect = male_collect.value_counts().reindex(age_range, fill_value=0).to_numpy()
    female_collect = pd.DataFrame({'Female': female_collect})
    male_collect = pd.DataFrame({'Male': male_collect})
    print('Total female is: ', sum(female_collect['Female']))
    print('Total male is: ', sum(male_collect['Male']))
    gender_age_distribution = pd.concat([female_collect, male_collect], axis=1)
    gender_age_distribution = gender_age_distribution.iloc[:101, :]
    filename = os.path.join(output_dir_fun, f'Gender_age_dis_{this_year}.txt')
    gender_age_distribution.to_csv(filename, sep=' ', index=None)
