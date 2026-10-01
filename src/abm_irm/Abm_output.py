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
from .Abm_Class import HouseHold, FamilyMember, ensure_household_uid


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


def household_life_stage_group(household):
    """Return the household life-stage group used by the HBM disaster module."""
    members = [member for member in getattr(household, "members", []) if getattr(member, "alive", True)]
    ages = [float(getattr(member, "age", np.nan)) for member in members]
    ages = [age for age in ages if np.isfinite(age)]

    if (ages and all(age >= 65 for age in ages)) or bool(getattr(household, "old_hh", False)):
        return "Elderly_hh"
    if any(age <= 19 for age in ages):
        return "Child_hh"
    if len(members) == 1:
        return "Single"
    return "Other_adult"


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
        single_house = 0
        children_house = 0
        other_house = 0
        agr_house = 0
        for hh in mesh_hhs:
            total_pop += len(hh.members)
            life_stage = household_life_stage_group(hh)
            if life_stage == "Elderly_hh":
                elder += 1
            elif life_stage == "Single":
                single_house += 1
            elif life_stage == "Child_hh":
                children_house += 1
            elif life_stage == "Other_adult":
                other_house += 1
            if hh.agri == True:
                agr_house += 1
            for m in hh.members:
                if m.age <= 19 and m.age >= 5:
                    child_pop += 1
                if m.age >= 65:
                    old_pop += 1
        results.append([
            mesh,
            total_household,
            elder,
            single_house,
            children_house,
            other_house,
            total_pop,
            child_pop,
            old_pop,
            #agr_house,
        ])
    initial = pd.DataFrame(
        results,
        columns=[
            'Mesh_ID',
            'Households',
            'Elder_Households',
            'Single_Person_Households',
            'Children_Households',
            'Other_Households',
            'Total_Population',
            'Children',
            'Older',
            #'Agri_Household',
        ],
    )
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


def household_tp_output(this_year, household, output_dir_fun):
    """Write household TP, insurance, and annual GUL/payout/OOP in 万円."""
    results = []

    for hh in household:
        results.append([
            this_year,
            ensure_household_uid(hh),
            hh.mesh_id,
            hh.hh_id,
            household_life_stage_group(hh),
            getattr(hh, "tp", np.nan),
            bool(getattr(hh, "insured", False)),
            (np.nan if getattr(hh, "insurance_expire_year", None) is None
             else hh.insurance_expire_year),
            getattr(hh, "insurance_efficacy", np.nan),
            getattr(hh, "insurance_affordability", np.nan),
            getattr(hh, "provider_trust", np.nan),
            getattr(hh, "p_insurance", np.nan),
            getattr(hh, "insurance_decision", "not_evaluated"),
            getattr(hh, "insurance_origin", "unknown"),
            getattr(hh, "loss_mesh_id", hh.mesh_id),
            getattr(hh, "flood_depth_m", 0.0),
            bool(getattr(hh, "insured_at_flood", False)),
            getattr(hh, "building_damage_ratio", 0.0),
            getattr(hh, "contents_damage_ratio", 0.0),
            getattr(hh, "vehicle_damage_ratio", 0.0),
            getattr(hh, "building_gul", 0.0),
            getattr(hh, "contents_gul", 0.0),
            getattr(hh, "vehicle_gul", 0.0),
            getattr(hh, "gul", 0.0),
            getattr(hh, "building_payout", 0.0),
            getattr(hh, "contents_payout", 0.0),
            getattr(hh, "vehicle_payout", 0.0),
            getattr(hh, "insurance_payout", 0.0),
            getattr(hh, "building_oop", 0.0),
            getattr(hh, "contents_oop", 0.0),
            getattr(hh, "vehicle_oop", 0.0),
            getattr(hh, "oop", 0.0),
        ])

    output = pd.DataFrame(
        results,
        columns=[
            'Year',
            'household_uid',
            'Mesh_ID',
            'hh_id',
            'Household_Type',
            'TP',
            'Insured',
            'Insurance_Expire_Year',
            'Insurance_Efficacy',
            'Insurance_Affordability',
            'Provider_Trust',
            'Insurance_Decision_Probability',
            'Insurance_Decision',
            'Insurance_Origin',
            'Loss_Mesh_ID',
            'Flood_Depth_m',
            'Insured_At_Flood',
            'Building_Damage_Ratio',
            'Contents_Damage_Ratio',
            'Vehicle_Damage_Ratio',
            'Building_GUL',
            'Contents_GUL',
            'Vehicle_GUL',
            'GUL',
            'Building_Payout',
            'Contents_Payout',
            'Vehicle_Payout',
            'Insurance_Payout',
            'Building_OOP',
            'Contents_OOP',
            'Vehicle_OOP',
            'OOP',
        ],
    )
    output = output.sort_values(['household_uid', 'Year'])
    filename = os.path.join(output_dir_fun, f'Household_TP_{this_year}_seed.txt')
    output.to_csv(filename, sep=' ', index=None, na_rep='nan')


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
