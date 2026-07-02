"""Utility-based destination choice for intra-regional household migration."""

import random
import pandas as pd
import numpy as np
import statistics as ss
import os
import sys
import math
from .paths import data_path
from .config import read_sim_period
from .Abm_Class import HouseHold, FamilyMember

dist_table = pd.read_csv(data_path('Utility_location_choice', 'mesh_facility_distances.csv'))
dist_table = dist_table.set_index('MESH4_ID')
dist_table.index = dist_table.index.astype(int)
mesh_centroids = dist_table[['x', 'y']]
utility_para = pd.read_table(data_path('Parameter_file.txt'), sep='\\s+')
row = utility_para.set_index('Para')['Value']
a_y = float(row['a_y'])
a_ds = float(row['a_ds'])
a_dh = float(row['a_dh'])
a_dm = float(row['a_dm'])
a_dd = float(row['a_dd'])
a_dd_f = float(row['a_dd_f'])
a_dh_e = float(row['a_dh_e'])
N_mesh = int(row['N_mesh'])
N_mesh_in = int(row['N_mesh_in'])
mesh_pair = pd.read_table(data_path('Utility_location_choice', 'mesh_pair.txt'), sep=' ')
mesh_adm2 = pd.read_table(data_path('Utility_location_choice', 'adm2_mesh_id.txt'), sep=' ', dtype=float)


def mesh_candidate_selection(hh):
    """Sample candidate destination meshes inside and outside the current municipality."""
    mesh_num = mesh_pair[mesh_pair['abm'] == hh.mesh_id]['data'].iloc[0].astype(float)
    adm2_code = mesh_adm2.columns[mesh_adm2.isin([mesh_num]).any()][0]
    adm2_list = mesh_adm2[str(adm2_code)]
    mesh_same_adm2 = np.array(adm2_list)
    mesh_same_adm2 = mesh_same_adm2[~np.isnan(mesh_same_adm2)].astype(int)
    mesh_same_adm2 = np.delete(mesh_same_adm2, np.where(mesh_same_adm2 == mesh_num)).tolist()
    mesh_candidate_1 = random.sample(mesh_same_adm2, N_mesh_in)
    mesh_other_adm2 = mesh_adm2.drop(columns=[adm2_code])
    mesh_other_adm2 = np.ravel(np.array(mesh_other_adm2))
    mesh_other_adm2 = mesh_other_adm2[~np.isnan(mesh_other_adm2)].astype(int).tolist()
    mesh_candidate_2 = random.sample(mesh_other_adm2, N_mesh - N_mesh_in)
    mesh_can = mesh_candidate_1 + mesh_candidate_2
    return (len(mesh_candidate_1), mesh_can)


def distance_calculation(this_mesh, meshes):
    """Collect facility and mesh-distance values for candidate destinations."""
    this_mesh_code = mesh_pair.loc[mesh_pair['abm'] == this_mesh, 'data'].iloc[0]
    this_mesh_code = int(this_mesh_code)
    mesh_codes = np.asarray(meshes, dtype=int)
    sub = dist_table.loc[mesh_codes]
    d_ele = sub['d_to_ele_school_m'].to_numpy()
    d_mid = sub['d_to_mid_school_m'].to_numpy()
    d_hig = sub['d_to_hig_school_m'].to_numpy()
    d_hos = sub['d_to_hospit_m'].to_numpy()
    d_mar = sub['d_to_market_m'].to_numpy()
    this_x, this_y = mesh_centroids.loc[this_mesh_code, ['x', 'y']]
    cand_x = sub['x'].to_numpy()
    cand_y = sub['y'].to_numpy()
    d_mesh = np.sqrt((cand_x - this_x) ** 2 + (cand_y - this_y) ** 2)
    data = np.vstack([d_ele, d_mid, d_hig, d_hos, d_mar, d_mesh])
    all_distance = pd.DataFrame(data, index=[0, 1, 2, 3, 4, 5], columns=[str(code) for code in mesh_codes])
    return all_distance


def school_distance(household, distance_point):
    """Select the school-distance variable relevant to household child ages."""
    es_key = 0
    ms_key = 0
    hs_key = 0
    child = 0
    for person in household.members:
        if 6 < person.age <= 12:
            es_key = 1
            child = child + 1
        elif 12 < person.age <= 15:
            ms_key = 1
            child = child + 1
        elif 15 < person.age <= 18:
            hs_key = 1
            child = child + 1
    school_key = pd.Series([es_key, ms_key, hs_key], index=distance_point.index[:3], dtype=float)
    school_distance = distance_point.iloc[0:3, :].mul(school_key, axis=0)
    school_distance = pd.DataFrame(school_distance.sum(axis=0) / child).T
    distance_point = pd.concat([school_distance, distance_point.iloc[3:, :]], axis=0).reset_index(drop=True)
    distance_point.replace(0, np.nan, inplace=True)
    return distance_point


def utility_function(house, elements):
    """Evaluate destination utility for one household."""
    aa_y = a_y
    aa_ds, aa_dh, aa_dm, aa_dd = (a_ds, a_dh, a_dm, a_dd)
    aa_dd_f = a_dd_f
    aa_dh_e = a_dh_e
    if house.agri == True:
        aa_dd = aa_dd_f
    if house.old_hh == True:
        aa_dh = aa_dh_e
    ele = np.ravel(np.array(elements, float))
    Y = ele[0]
    if np.isnan(Y):
        term1 = 1.0
    else:
        Y = max(Y, 1.0)
        term1 = Y ** (-aa_y)
    if np.isnan(ele[1]):
        term2 = 1
    else:
        term2 = math.pow(ele[1], -aa_ds)
    if np.isnan(ele[2]):
        term3 = 1
    else:
        term3 = math.pow(ele[2], -aa_dh)
    if np.isnan(ele[3]):
        term4 = 1
    else:
        term4 = math.pow(ele[3], -aa_dm)
    if np.isnan(ele[4]):
        term5 = 1
    else:
        term5 = math.pow(ele[4], -aa_dd)
    u = term1 * term2 * term3 * term4 * term5
    return u


def utility_migration_normal(household):
    """Move a household to the candidate mesh with the highest utility."""
    num_same_adm2, mesh_candidate = mesh_candidate_selection(household)
    dis_one_mesh = distance_calculation(household.mesh_id, mesh_candidate)
    dis_one_mesh_cor = school_distance(household, dis_one_mesh)
    live_year_same = pd.DataFrame(np.repeat(np.nan, num_same_adm2))
    live_year_other = pd.DataFrame(np.repeat(household.live_year, N_mesh - num_same_adm2))
    'redesign the live_year to [0,0,0,0,1,1,1,1...],\n    which will be multiply to a_y, indicating the activiation'
    live_year = pd.concat([live_year_same, live_year_other], axis=0).reset_index(drop=True).T
    live_year.columns = dis_one_mesh_cor.columns
    final_value = pd.concat([live_year, dis_one_mesh_cor], axis=0)
    storage = []
    for i in range(len(final_value.T)):
        utility_point = utility_function(household, final_value.iloc[:, i:i + 1])
        storage.append(utility_point)
    storage = pd.DataFrame(storage).T
    storage.columns = final_value.columns
    final_value = pd.concat([final_value, storage], axis=0)
    v = np.nanargmax(np.ravel(np.array(final_value.iloc[-1:, :])))
    new_mesh_id = final_value.columns[v]
    new_id = mesh_pair[mesh_pair['data'].astype(str) == new_mesh_id]['abm'].values[0]
    household.mesh_id = new_id
    return household
