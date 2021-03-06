import importlib
from conpagnon.data_handling import data_architecture, dictionary_operations, atlas, data_management
from conpagnon.utils import folders_and_files_management
from conpagnon.computing import compute_connectivity_matrices as ccm
from sklearn import covariance
from conpagnon.machine_learning import classification
from conpagnon.connectivity_statistics import parametric_tests
from conpagnon.plotting import display
from matplotlib.backends import backend_pdf
import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import ceil
from conpagnon.connectivity_statistics import regression_analysis_model
from conpagnon.plotting.display import t_and_p_values_barplot
# Reload all module
importlib.reload(data_management)
importlib.reload(atlas)
importlib.reload(display)
importlib.reload(parametric_tests)
importlib.reload(ccm)
importlib.reload(folders_and_files_management)
importlib.reload(classification)
importlib.reload(data_architecture)
importlib.reload(dictionary_operations)

# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 16:37:22 2017

@author: Dhaif BEKHA(dhaif.bekha@cea.fr)

Analysis of AVCnn cohort : patients and controls.

"""

# Atlas set up
atlas_folder = '/media/db242421/db242421_data/ConPagnon_data/atlas/atlas_reference'
atlas_name = 'atlas4D_2.nii'
labels_text_file = '/media/db242421/db242421_data/ConPagnon_data/atlas/atlas_reference/atlas4D_2_labels.csv'
colors = ['navy', 'sienna', 'orange', 'orchid', 'indianred', 'olive',
          'goldenrod', 'turquoise', 'darkslategray', 'limegreen', 'black',
          'lightpink']
# Number of regions in each user defined networks
networks = [2, 10, 2, 6, 10, 2, 8, 6, 8, 8, 6, 4]
# Atlas path
# Read labels regions files
atlas_nodes, labels_regions, labels_colors, n_nodes = atlas.fetch_atlas(
    atlas_folder=atlas_folder,
    atlas_name=atlas_name,
    network_regions_number=networks,
    colors_labels=colors,
    labels=labels_text_file,
    normalize_colors=True)

# Groups name to include in the study
groupes = ['PAL', 'PNL', 'TDC']
# The root fmri data directory containing all the fmri files directories
root_fmri_data_directory = \
    '/media/db242421/db242421_data/ConPagnon_data/fmri_images'
# Check all functional files existence
folders_and_files_management.check_directories_existence(
    root_directory=root_fmri_data_directory,
    directories_list=groupes)

# File extension for individual atlases images, and corresponding
# text labels files.
individual_atlas_file_extension = '*.nii'
individual_atlas_labels_extension = '*.csv'

# Full path, including extension, to the text file containing
# all the subject identifiers.
subjects_ID_data_path = \
    '/media/db242421/db242421_data/ConPagnon_data/text_data/acm_patients_and_controls.txt'

# Full to the following directories: individual atlases images,
# individual text labels files, and individual confounds directories.
individual_atlases_directory = \
    '/media/db242421/db242421_data/ConPagnon_data/atlas/individual_atlases_V2'
individual_atlases_labels_directory = \
    '/media/db242421/db242421_data/ConPagnon_data/atlas/individual_atlases_labels_V2'
individual_confounds_directory = \
    '/media/db242421/db242421_data/ConPagnon_data/regressors'

# output csv directory
output_csv_directory_path = \
    '/media/db242421/db242421_data/ConPagnon_data/language_study_ANOVA_ACM_controls_new_figures'
output_csv_directory = data_management.create_directory(directory=output_csv_directory_path, erase_previous=True)

# Figure directory which can be useful for illustrating
output_figure_directory_path = os.path.join(output_csv_directory, 'figures')
output_figure_directory = data_management.create_directory(directory=output_figure_directory_path,
                                                           erase_previous=True)
# Cohort behavioral data
cohort_excel_file_path = '/media/db242421/db242421_data/ConPagnon_data/regression_data/regression_data.xlsx'
behavioral_data = data_management.read_excel_file(excel_file_path=cohort_excel_file_path,
                                                  sheetname='cohort_functional_data')

# Clean the behavioral data by keeping only the subjects in the study
subjects_list = open(subjects_ID_data_path).read().split()
behavioral_data = behavioral_data.loc[subjects_list]
# save a CSV file format for the behavioral data
behavioral_data.to_csv(os.path.join(output_csv_directory, 'behavioral_data.csv'))

# Set the type I error (alpha level), usually .05.
alpha = .05
# Set the contrast vector, use for the direction of the mean effect
contrast = [1.0, -1.0]

# Metrics list of interest, connectivity matrices will be
# computed according to this list
kinds = ['tangent', 'partial correlation', 'correlation']

# Fetch data in the case of individual atlases for each subjects.
organised_data_with_individual_atlas = data_architecture.fetch_data_with_individual_atlases(
    subjects_id_data_path=subjects_ID_data_path,
    root_fmri_data_directory=root_fmri_data_directory,
    groupes=groupes,
    individual_atlases_directory=individual_atlases_directory,
    individual_atlases_labels_directory=individual_atlases_labels_directory,
    individual_atlas_labels_extension=individual_atlas_labels_extension,
    individual_atlas_file_extension=individual_atlas_file_extension,
    individual_counfounds_directory=individual_confounds_directory)

# Nilearn cache directory
nilearn_cache_directory = '/media/db242421/db242421_data/ConPagnon/nilearn_cache'

# Repetition time between time points in the fmri acquisition, usually 2.4s or 2.5s
repetition_time = 2.5


# Computing time series for each subjects according to individual atlases for each subjects
start = time.time()
times_series_individual_atlases = ccm.time_series_extraction_with_individual_atlases(
    root_fmri_data_directory=root_fmri_data_directory,
    groupes=groupes,
    subjects_id_data_path=subjects_ID_data_path,
    group_data=organised_data_with_individual_atlas,
    repetition_time=repetition_time,
    nilearn_cache_directory=nilearn_cache_directory)
end = time.time()
total_extraction_ts = (end - start)/60.

# Compute connectivity matrices for multiple metrics
# Covariance estimator
covariance_estimator = covariance.LedoitWolf()

# Choose the time series dictionary
time_series_dict = times_series_individual_atlases

# Computing for each metric, and each subjects in each groups,
# the connectivity matrices using the computed time series.
subjects_connectivity_matrices = ccm.individual_connectivity_matrices(
    time_series_dictionary=time_series_dict,
    kinds=kinds, covariance_estimator=covariance_estimator,
    vectorize=False, z_fisher_transform=False)

# Computing for each metric, and each subjects in each groups,
# the fisher transform connectivity matrices using the computed time series.
Z_subjects_connectivity_matrices = ccm.individual_connectivity_matrices(
    time_series_dictionary=time_series_dict,
    kinds=kinds, covariance_estimator=covariance_estimator,
    vectorize=False, z_fisher_transform=True,
    discarding_diagonal=False)

# Computing for each metric, and each groups the mean connectivity matrices,
# from the z fisher transform matrices.
Z_mean_groups_connectivity_matrices = ccm.group_mean_connectivity(
    subjects_connectivity_matrices=Z_subjects_connectivity_matrices,
    kinds=kinds)

# Fitting a gaussian distribution mean connectivity matrices in each groups, after a Z fisher transform.
parameters_estimation = parametric_tests.mean_functional_connectivity_distribution_estimation(
                        mean_groups_connectivity_matrices=Z_mean_groups_connectivity_matrices)

# Plot of mean connectivity distribution in each group, with the gaussian fit in overlay
fitted_dist_color1, fitted_dist_color2, fitted_dist_color3 = 'blue', 'red', 'green'
raw_data_color1, raw_data_color2, raw_data_color3 = 'blue', 'red', 'green'
hist_color = ['blue', 'red', 'green']
fit_color = ['blue', 'red', 'green']
# Display results
with backend_pdf.PdfPages(os.path.join(output_figure_directory, 'overall_connectivity_distribution.pdf')) as pdf:
    for kind in kinds:
        plt.figure()
        for groupe in groupes:
            display.display_gaussian_connectivity_fit(
                vectorized_connectivity=parameters_estimation[groupe][kind]['vectorized connectivity'],
                estimate_mean=parameters_estimation[groupe][kind]['mean'],
                estimate_std=parameters_estimation[groupe][kind]['std'],
                raw_data_colors=hist_color[groupes.index(groupe)],
                fitted_distribution_color=fit_color[groupes.index(groupe)],
                title='Overall functional connectivity distribution  for {}'.format(kind),
                xtitle='Functional connectivity coefficient', ytitle='proportion of edges',
                legend_fitted='{} distribution'.format(groupe),
                legend_data=groupe, display_fit='no', ms=0.5, line_width=1)
        pdf.savefig()
        plt.show()
# Extract homotopic connectivity coefficients on connectivity matrices
# Homotopic roi couple position in the connectivity matrices.
homotopic_roi_indices = np.array([
    (1, 0), (2, 3), (4, 5), (6, 7), (8, 11), (9, 10), (13, 12), (14, 15), (16, 17), (18, 19), (20, 25),
    (21, 26), (22, 29), (23, 28), (24, 27), (30, 31), (32, 33), (35, 34), (36, 37), (38, 39), (44, 40),
    (41, 45), (42, 43), (46, 49), (47, 48), (50, 53), (53, 54), (54, 57), (55, 56), (58, 61), (59, 60),
    (62, 63), (64, 65), (66, 67), (68, 69), (70, 71)])

# Atlas excel information file
atlas_excel_file = '/media/db242421/db242421_data/atlas_AVCnn/atlas_version2.xlsx'
sheetname = 'complete_atlas'

atlas_information = pd.read_excel(atlas_excel_file, sheetname='complete_atlas')
# Indices of left and homotopic right regions indices
left_regions_indices = homotopic_roi_indices[:, 0]
right_regions_indices = homotopic_roi_indices[:, 1]
# number of regions in the left and right side, should be the same because
# it's homotopic regions only we are interested in
n_left_regions = len(left_regions_indices)
n_right_regions = len(right_regions_indices)
try:
    n_left_regions == n_right_regions
except ValueError:
    print('Number of regions in the left and the right side are not equal !')

# Extract from the Z fisher subject connectivity dictionary the connectivity coefficients of interest
homotopic_connectivity = ccm.subjects_mean_connectivity_(
    subjects_individual_matrices_dictionnary=Z_subjects_connectivity_matrices,
    connectivity_coefficient_position=homotopic_roi_indices, kinds=kinds,
    groupes=groupes)

# Compute mean and standard deviation assuming gaussian behavior
homotopic_distribution_parameters = dict.fromkeys(groupes)
for groupe in groupes:
    homotopic_distribution_parameters[groupe] = dict.fromkeys(kinds)
    for kind in kinds:
        # Stack the mean homotopic connectivity of each subject for the current group
        subjects_mean_homotopic_connectivity = np.array(
            [homotopic_connectivity[groupe][subject][kind]['mean connectivity']
             for subject in homotopic_connectivity[groupe].keys()])
        # Estimate the mean and std assuming a Gaussian behavior
        subjects_mean_homotopic_connectivity_, mean_homotopic_estimation, std_homotopic_estimation = \
            parametric_tests.functional_connectivity_distribution_estimation(subjects_mean_homotopic_connectivity)
        # Fill a dictionnary saving the results for each groups and kind
        homotopic_distribution_parameters[groupe][kind] = {
            'subjects mean homotopic connectivity': subjects_mean_homotopic_connectivity_,
            'homotopic distribution mean': mean_homotopic_estimation,
            'homotopic distribution standard deviation': std_homotopic_estimation}


with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                       'mean_homotopic_connectivity_distribution.pdf')) as pdf:
    for kind in kinds:
        plt.figure(constrained_layout=True)
        for groupe in groupes:
            group_connectivity = homotopic_distribution_parameters[groupe][kind][
                'subjects mean homotopic connectivity']
            group_mean = homotopic_distribution_parameters[groupe][kind][
                'homotopic distribution mean']
            group_std = homotopic_distribution_parameters[groupe][kind][
                'homotopic distribution standard deviation']
            display.display_gaussian_connectivity_fit(
                vectorized_connectivity=group_connectivity,
                estimate_mean=group_mean,
                estimate_std=group_std,
                raw_data_colors=hist_color[groupes.index(groupe)],
                fitted_distribution_color=fit_color[groupes.index(groupe)],
                title='Whole brain mean homotopic connectivity distribution for {}'.format(kind),
                xtitle='Functional connectivity coefficient', ytitle='Proportion of subjects',
                legend_fitted='{}  distribution'.format(groupe),
                legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
            plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                        linewidth=2)
        pdf.savefig()
        plt.show()
        plt.close()

# Left roi first, and right roi in second
new_roi_order = np.concatenate((left_regions_indices, right_regions_indices), axis=0)
new_labels_regions = [labels_regions[i] for i in new_roi_order]
new_labels_colors = labels_colors[new_roi_order, :]

# Compute whole brain mean connectivity for each subjects i.e  the mean of the flatten subjects
# connectivity matrices
whole_brain_mean_connectivity = ccm.mean_of_flatten_connectivity_matrices(
    subjects_individual_matrices_dictionary=Z_subjects_connectivity_matrices, groupes=groupes, kinds=kinds)

# Estimate mean and standard deviation of whole brain mean connectivity for each group and kinds
whole_brain_mean_connectivity_parameters = dict.fromkeys(groupes)
for groupe in groupes:
    whole_brain_mean_connectivity_parameters[groupe] = dict.fromkeys(kinds)
    for kind in kinds:
        # Stack the mean homotopic connectivity of each subject for the current group
        subjects_mean_whole_brain_connectivity = np.array(
            [whole_brain_mean_connectivity[groupe][subject][kind]['mean connectivity']
             for subject in whole_brain_mean_connectivity[groupe].keys()])
        # Estimate the mean and std assuming a Gaussian behavior
        subjects_mean_whole_brain_connectivity_, mean_estimation, std_estimation = \
            parametric_tests.functional_connectivity_distribution_estimation(subjects_mean_whole_brain_connectivity)
        # Fill a dictionnary saving the results for each groups and kind
        whole_brain_mean_connectivity_parameters[groupe][kind] = {
            'subjects mean whole brain connectivity': subjects_mean_whole_brain_connectivity_,
            'whole brain distribution mean': mean_estimation,
            'whole brain distribution standard deviation': std_estimation}

# Display results: whole brain mean connectivity
with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                       'whole_brain_mean_connectivity_distribution.pdf')) as pdf:
    for kind in kinds:
        plt.figure()
        for groupe in groupes:
            group_connectivity = whole_brain_mean_connectivity_parameters[groupe][kind][
                'subjects mean whole brain connectivity']
            group_mean = whole_brain_mean_connectivity_parameters[groupe][kind][
                'whole brain distribution mean']
            group_std = whole_brain_mean_connectivity_parameters[groupe][kind][
                'whole brain distribution standard deviation']
            display.display_gaussian_connectivity_fit(
                vectorized_connectivity=group_connectivity,
                estimate_mean=group_mean,
                estimate_std=group_std,
                raw_data_colors=hist_color[groupes.index(groupe)],
                fitted_distribution_color=fit_color[groupes.index(groupe)],
                title='Whole brain mean connectivity distribution for {}'.format(kind),
                xtitle='Functional connectivity coefficient', ytitle='Proportion of subjects',
                legend_fitted='{} distribution'.format(groupe),
                legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
            plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                        linewidth=2)
        pdf.savefig()
        plt.show()

# Group by roi matrix
with backend_pdf.PdfPages(os.path.join(output_figure_directory, 'mean_connectivity_matrices_2.pdf')) as pdf:
    for kind in kinds:
        for groupe in groupes:
            display.plot_matrix(
                matrix=Z_mean_groups_connectivity_matrices[groupe][kind][:, new_roi_order][new_roi_order],
                mpart='all', labels_colors=new_labels_colors, horizontal_labels=new_labels_regions,
                vertical_labels=new_labels_regions, title='mean ' + kind + ' ' + groupe, linewidths=0)
            pdf.savefig()
            plt.show()

with backend_pdf.PdfPages(os.path.join(output_figure_directory, 'mean_difference_connectivity_matrices_3.pdf')) as pdf:
    for kind in kinds:
        difference = Z_mean_groups_connectivity_matrices[groupes[0]][kind][:, new_roi_order][new_roi_order] - \
                     Z_mean_groups_connectivity_matrices[groupes[2]][kind][:, new_roi_order][new_roi_order]

        display.plot_matrix(matrix=difference,
                            mpart='all', labels_colors=new_labels_colors, horizontal_labels=new_labels_regions,
                            vertical_labels=new_labels_regions,
                            title=groupes[0] + '-' + groupes[2] + ' mean ' + kind + ' difference', linewidths=0)
        pdf.savefig()
        plt.show()

# Connectivity intra-network
intra_network_connectivity_dict, network_dict, network_labels_list, network_label_colors = \
    ccm.intra_network_functional_connectivity(
        subjects_individual_matrices_dictionnary=Z_subjects_connectivity_matrices,
        groupes=groupes, kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname=sheetname,
        roi_indices_column_name='atlas4D index',
        network_column_name='network',
        color_of_network_column='Color')

# Estimation of mean intra network connectivity mean and std 
intra_network_distribution_parameters = dict.fromkeys(network_labels_list)
for network in network_labels_list:
    intra_network_distribution_parameters[network] = dict.fromkeys(groupes)
    for groupe in groupes:
        intra_network_distribution_parameters[network][groupe] = dict.fromkeys(kinds)
        for kind in kinds:
            # Stack the mean homotopic connectivity of each subject for the current group
            subjects_mean_intra_network_connectivity = np.array(
                [intra_network_connectivity_dict[groupe][subject][kind][network]['network connectivity strength']
                 for subject in intra_network_connectivity_dict[groupe].keys()])
            # Estimate the mean and std assuming a Gaussian behavior
            subjects_mean_intra_network_connectivity_, mean_intra_estimation, std_intra_estimation = \
                parametric_tests.functional_connectivity_distribution_estimation(
                    subjects_mean_intra_network_connectivity)
            # Fill a dictionary saving the results for each groups and kind
            intra_network_distribution_parameters[network][groupe][kind] = {
                'subjects mean intra connectivity': subjects_mean_intra_network_connectivity_,
                'intra distribution mean': mean_intra_estimation,
                'intra distribution standard deviation': std_intra_estimation}

for kind in kinds:
    with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                           kind + '_intra_network_connectivity_distribution.pdf')) as pdf:

        for network in network_labels_list:
            plt.figure(constrained_layout=True)
            for groupe in groupes:
                group_connectivity = intra_network_distribution_parameters[network][groupe][kind][
                    'subjects mean intra connectivity']
                group_mean = intra_network_distribution_parameters[network][groupe][kind][
                    'intra distribution mean']
                group_std = intra_network_distribution_parameters[network][groupe][kind][
                    'intra distribution standard deviation']
                display.display_gaussian_connectivity_fit(
                    vectorized_connectivity=group_connectivity,
                    estimate_mean=group_mean,
                    estimate_std=group_std,
                    raw_data_colors=hist_color[groupes.index(groupe)],
                    fitted_distribution_color=fit_color[groupes.index(groupe)],
                    title='',
                    xtitle='Functional connectivity', ytitle='Proportion of subjects',
                    legend_fitted='{} distribution'.format(groupe),
                    legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
                plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                            linewidth=2)
                plt.title('Connectivity distribution for the {} network'.format(network))

            pdf.savefig()
            plt.show()


# We can compute the homotopic connectivity for each network, i.e a intra-network homotopic connectivity
homotopic_intra_network_connectivity_d = dict.fromkeys(network_labels_list)
for network in network_labels_list:
    # Pick the 4D index of the roi in the network
    network_roi_ind = network_dict[network]['dataframe']['atlas4D index']
    # Extract connectivity coefficient couple corresponding to homotopic regions in the network
    network_homotopic_couple_ind = np.array([couple for couple in homotopic_roi_indices if (couple[0] or couple[1])
                                             in network_roi_ind])
    # Compute homotopic connectivity dictionary for the current network
    network_homotopic_d = ccm.subjects_mean_connectivity_(
        subjects_individual_matrices_dictionnary=Z_subjects_connectivity_matrices,
        connectivity_coefficient_position=network_homotopic_couple_ind,
        kinds=kinds, groupes=groupes)
    homotopic_intra_network_connectivity_d[network] = network_homotopic_d

# Create a homotopic intra-network dictionary with the same structure as the overall intra network dictionary
homotopic_intranetwork_d = dict.fromkeys(groupes)
for groupe in groupes:
    homotopic_intranetwork_d[groupe] = dict.fromkeys(Z_subjects_connectivity_matrices[groupe].keys())
    for subject in Z_subjects_connectivity_matrices[groupe].keys():
        homotopic_intranetwork_d[groupe][subject] = dict.fromkeys(kinds)
        for kind in kinds:
            homotopic_intranetwork_d[groupe][subject][kind] = \
                dict.fromkeys(list(homotopic_intra_network_connectivity_d.keys()))
            for network in list(homotopic_intra_network_connectivity_d.keys()):
                homotopic_intranetwork_d[groupe][subject][kind][network] =\
                    {'network connectivity strength':
                     homotopic_intra_network_connectivity_d[network][groupe][subject][kind]['mean connectivity']}

# estimate mean and std for each network, for the display of the intra-network homotopic connectivity
network_homotopic_distribution_parameters = dict.fromkeys(network_labels_list)
for network in network_labels_list:
    network_homotopic_distribution_parameters[network] = dict.fromkeys(groupes)
    for groupe in groupes:
        network_homotopic_distribution_parameters[network][groupe] = dict.fromkeys(kinds)
        for kind in kinds:
            # Stack the mean homotopic connectivity of each subject for the current group
            subjects_mean_homotopic_connectivity = np.array(
                [homotopic_intra_network_connectivity_d[network][groupe][subject][kind]['mean connectivity']
                 for subject in homotopic_intra_network_connectivity_d[network][groupe].keys()])
            # Estimate the mean and std assuming a Gaussian behavior
            subjects_mean_homotopic_connectivity_, mean_homotopic_estimation, std_homotopic_estimation = \
                parametric_tests.functional_connectivity_distribution_estimation(
                    subjects_mean_homotopic_connectivity)
            # Fill a dictionary saving the results for each groups and kind
            network_homotopic_distribution_parameters[network][groupe][kind] = {
                'subjects mean homotopic connectivity': subjects_mean_homotopic_connectivity_,
                'homotopic distribution mean': mean_homotopic_estimation,
                'homotopic distribution standard deviation': std_homotopic_estimation}

# Display for each network the mean homotopic distribution for all group
# Gaussian fit of homotopic connectivity
for kind in kinds:
    with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                           kind + '_intra_network_homotopic_connectivity_distribution.pdf')) as pdf:

        for network in network_labels_list:
            plt.figure(constrained_layout=True)
            for groupe in groupes:
                group_connectivity = network_homotopic_distribution_parameters[network][groupe][kind][
                    'subjects mean homotopic connectivity']
                group_mean = network_homotopic_distribution_parameters[network][groupe][kind][
                    'homotopic distribution mean']
                group_std = network_homotopic_distribution_parameters[network][groupe][kind][
                    'homotopic distribution standard deviation']
                display.display_gaussian_connectivity_fit(
                    vectorized_connectivity=group_connectivity,
                    estimate_mean=group_mean,
                    estimate_std=group_std,
                    raw_data_colors=hist_color[groupes.index(groupe)],
                    fitted_distribution_color=fit_color[groupes.index(groupe)],
                    title='',
                    xtitle='Functional connectivity', ytitle='Proportion of subjects',
                    legend_fitted='{} distribution'.format(groupe),
                    legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
                plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                            linewidth=2)
                plt.title('Mean homotopic connectivity for the {} network'.format(network))

            pdf.savefig()
            plt.show()

# Save the whole brain intra-network connectivity
data_management.csv_from_intra_network_dictionary(subjects_dictionary=intra_network_connectivity_dict,
                                                  groupes=groupes, kinds=kinds,
                                                  network_labels_list=network_labels_list,
                                                  field_to_write='network connectivity strength',
                                                  output_directory=output_csv_directory,
                                                  csv_prefix='intra')

# Save the whole brain intra-network homotopic connectivity
data_management.csv_from_intra_network_dictionary(subjects_dictionary=homotopic_intranetwork_d,
                                                  groupes=groupes, kinds=kinds,
                                                  network_labels_list=network_labels_list,
                                                  field_to_write='network connectivity strength',
                                                  output_directory=output_csv_directory,
                                                  csv_prefix='intra_homotopic')
# Save the whole brain mean connectivity
for group in groupes:
    for kind in kinds:
        data_management.csv_from_dictionary(subjects_dictionary=whole_brain_mean_connectivity,
                                            groupes=groupes,
                                            kinds=kinds,
                                            field_to_write='mean connectivity',
                                            header=['subjects', 'mean_connectivity'],
                                            csv_filename='mean_connectivity.csv',
                                            output_directory=os.path.join(output_csv_directory, kind),
                                            delimiter=',')

# Save the whole brain homotopic connectivity
for group in groupes:
    for kind in kinds:
        data_management.csv_from_dictionary(subjects_dictionary=homotopic_connectivity,
                                            groupes=[group],
                                            kinds=[kind],
                                            field_to_write='mean connectivity',
                                            header=['subjects', 'mean_homotopic'],
                                            csv_filename='mean_homotopic.csv',
                                            output_directory=os.path.join(output_csv_directory, kind),
                                            delimiter=',')

# Overall and Within network, ipsilesional and contralesional connectivity differences
# Compute the connectivity matrices dictionary with factor as keys.
group_by_factor_subjects_connectivity, population_df_by_factor, factor_keys = \
    dictionary_operations.groupby_factor_connectivity_matrices(population_data_file=cohort_excel_file_path,
                                                               sheetname='cohort_functional_data',
                                                               subjects_connectivity_matrices_dictionnary=Z_subjects_connectivity_matrices,
                                                               groupes=['PAL', 'PNL'],
                                                               factors=['Lesion', 'langage_clinique'],
                                                               drop_subjects_list=None)

# Create ipsilesional and contralesional dictionary
ipsi_dict = {}
contra_dict = {}

# Fetch left and right connectivity for each group attribute keys
left_connectivity = ccm.extract_sub_connectivity_matrices(
    subjects_connectivity_matrices=group_by_factor_subjects_connectivity,
    kinds=kinds, regions_index=left_regions_indices)
right_connectivity = ccm.extract_sub_connectivity_matrices(
    subjects_connectivity_matrices=group_by_factor_subjects_connectivity,
    kinds=kinds, regions_index=right_regions_indices)

# Fill ipsi-lesional and contra-lesional dictionary
for attribute in factor_keys:
    subject_for_this_attribute = list(population_df_by_factor[attribute])
    ipsi_dict[attribute] = dict.fromkeys(subject_for_this_attribute)
    contra_dict[attribute] = dict.fromkeys(subject_for_this_attribute)
    for s in subject_for_this_attribute:
        if attribute[0] == 'D':
            # Fill the ipsi-lesional dictionary for a right lesion with the
            # right connectivity matrices for the current attribute
            ipsi_dict[attribute][s] = right_connectivity[attribute][s]
            # Fill the contra-lesional dictionary for a right lesion with the
            # left connectivity matrices for the current attribute
            contra_dict[attribute][s] = left_connectivity[attribute][s]
        elif attribute[0] == 'G':
            # Fill the ipsi-lesional dictionary for a left lesion with the
            # left connectivity matrices for the current attribute
            ipsi_dict[attribute][s] = left_connectivity[attribute][s]
            # Fill the contra-lesional dictionary for a left lesion with the
            # right connectivity matrices for the current attribute
            contra_dict[attribute][s] = right_connectivity[attribute][s]


# Construct a corresponding ipsilesional and contralesional dictionary for controls
n_left_tot = len(ipsi_dict[('G', 'A')]) + len(ipsi_dict[('G', 'N')])
n_right_tot = len(ipsi_dict[('D', 'A')]) + len(ipsi_dict[('D', 'N')])

# Compute the percentage of right lesion and left lesion
n_total_patients = n_left_tot + n_right_tot
percent_left_lesioned = n_left_tot/n_total_patients
percent_right_lesioned = n_right_tot/n_total_patients

# total number of controls
n_controls = len(Z_subjects_connectivity_matrices['TDC'].keys())
# Number of left and right impaired hemisphere to pick randomly in the controls group
n_left_hemisphere = ceil(percent_left_lesioned*n_controls)
n_right_hemisphere = n_controls - n_left_hemisphere

# Random pick of n_left_tot in proportion to the number of left lesion in controls group
n_left_ipsilesional_controls, n_left_ipsi_controls_ids = \
    dictionary_operations.random_draw_of_connectivity_matrices(
        subjects_connectivity_dictionary=Z_subjects_connectivity_matrices,
        groupe='TDC', n_matrices=int(n_left_hemisphere),
        extract_kwargs={'kinds': kinds, 'regions_index': left_regions_indices,
                        'discard_diagonal': False,
                        'vectorize': False})
# Now, pick the right hemisphere in the left-out pool of subjects
leftout_controls_id = \
    list(set(Z_subjects_connectivity_matrices['TDC'].keys())-set(n_left_ipsi_controls_ids))

n_right_ipsilesional_controls, n_right_ipsi_controls_ids = \
    dictionary_operations.random_draw_of_connectivity_matrices(
        subjects_connectivity_dictionary=Z_subjects_connectivity_matrices,
        groupe='TDC', n_matrices=int(n_right_hemisphere),
        extract_kwargs={'kinds': kinds, 'regions_index': right_regions_indices,
                        'discard_diagonal': False,
                        'vectorize': False},
        subjects_id_list=leftout_controls_id)

# Merge the right and left ipsilesional to have the 'ipsilesional' controls dictionary
ipsilesional_controls_dictionary = dictionary_operations.merge_dictionary(
    new_key='TDC',
    dict_list=[n_left_ipsilesional_controls['TDC'],
               n_right_ipsilesional_controls['TDC']])

# In the same, we have to generate, a "contralesional" dictionary for the
# controls group

# contralesional dictionary for left lesions, we fetch all RIGHT side roi this time
n_left_contralesional_controls, n_left_contra_controls_ids = \
    dictionary_operations.random_draw_of_connectivity_matrices(
        subjects_connectivity_dictionary=Z_subjects_connectivity_matrices,
        groupe='TDC', n_matrices=int(n_left_hemisphere),
        extract_kwargs={'kinds': kinds, 'regions_index': right_regions_indices,
                        'discard_diagonal': False,
                        'vectorize': False})

# In the left-out pool of subjects, we fetch the LEFT side rois, for the
# contralesional side of right lesion.
leftout_controls_id = \
    list(set(Z_subjects_connectivity_matrices['TDC'].keys())-set(n_left_contra_controls_ids))

n_right_contralesional_controls, n_right_contra_controls_ids = \
    dictionary_operations.random_draw_of_connectivity_matrices(
        subjects_connectivity_dictionary=Z_subjects_connectivity_matrices,
        groupe='TDC', n_matrices=int(n_right_hemisphere),
        extract_kwargs={'kinds': kinds, 'regions_index': left_regions_indices,
                        'discard_diagonal': False,
                        'vectorize': False}, subjects_id_list=leftout_controls_id)

# Merge the right and left ipsilesional to have the 'ipsilesional' controls dictionary
contralesional_controls_dictionary = dictionary_operations.merge_dictionary(
    new_key='TDC',
    dict_list=[n_left_contralesional_controls['TDC'],
               n_right_contralesional_controls['TDC']])

# Finally, we have to merge ipsilesional/contralesional dictionaries of the different group
# Merge the dictionary to build the overall contra and ipsi-lesional
# subjects connectivity matrices dictionary

# First, the two group of patients
ipsilesional_patients_connectivity_matrices = {
    'PAL': {**ipsi_dict[('G', 'A')], **ipsi_dict[('D', 'A')]},
    'PNL': {**ipsi_dict[('G', 'N')], **ipsi_dict[('D', 'N')]}
    }

contralesional_patients_connectivity_matrices = {
     'PNL': {**contra_dict[('G', 'N')], **contra_dict[('D', 'N')]},
     'PAL': {**contra_dict[('G', 'A')], **contra_dict[('D', 'A')]}
   }

# Merged overall patients and controls dictionaries
ipsilesional_subjects_connectivity_matrices = dictionary_operations.merge_dictionary(
    dict_list=[ipsilesional_controls_dictionary,
               ipsilesional_patients_connectivity_matrices]
)
contralesional_subjects_connectivity_matrices = dictionary_operations.merge_dictionary(
    dict_list=[contralesional_controls_dictionary,
               contralesional_patients_connectivity_matrices]
)

# Estimate mean and std of ipsilesional connectivity assuming gaussian behavior
# Compute of mean ipsilesional distribution
ipsilesional_mean_connectivity = ccm.mean_of_flatten_connectivity_matrices(
    subjects_individual_matrices_dictionary=ipsilesional_subjects_connectivity_matrices,
    groupes=groupes,
    kinds=kinds)
contralesional_mean_connectivity = ccm.mean_of_flatten_connectivity_matrices(
    subjects_individual_matrices_dictionary=contralesional_subjects_connectivity_matrices,
    groupes=groupes,
    kinds=kinds)

# Estimate mean and standard deviation of mean ipsilesional connectivity
ipsilesional_mean_connectivity_parameters = dict.fromkeys(groupes)
for groupe in groupes:
    ipsilesional_mean_connectivity_parameters[groupe] = dict.fromkeys(kinds)
    for kind in kinds:
        # Stack the mean homotopic connectivity of each subject for the current group
        subjects_mean_ipsi_connectivity = np.array(
            [ipsilesional_mean_connectivity[groupe][subject][kind]['mean connectivity']
             for subject in ipsilesional_mean_connectivity[groupe].keys()])
        # Estimate the mean and std assuming a Gaussian behavior
        subjects_mean_ipsi_connectivity_, mean_estimation, std_estimation = \
            parametric_tests.functional_connectivity_distribution_estimation(subjects_mean_ipsi_connectivity)
        # Fill a dictionary saving the results for each groups and kind
        ipsilesional_mean_connectivity_parameters[groupe][kind] = {
            'subjects mean ipsilesional connectivity': subjects_mean_ipsi_connectivity_,
            'ipsilesional distribution mean': mean_estimation,
            'ipsilesional distribution standard deviation': std_estimation}

# Plot the distribution of mean ipsilesional connectivity assuming gaussian
# behavior
with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                       'ipsilesional_mean_connectivity_distribution.pdf')) as pdf:
    for kind in kinds:
        plt.figure()
        for groupe in groupes:
            group_connectivity = ipsilesional_mean_connectivity_parameters[groupe][kind][
                'subjects mean ipsilesional connectivity']
            group_mean = ipsilesional_mean_connectivity_parameters[groupe][kind][
                'ipsilesional distribution mean']
            group_std = ipsilesional_mean_connectivity_parameters[groupe][kind][
                'ipsilesional distribution standard deviation']
            display.display_gaussian_connectivity_fit(
                vectorized_connectivity=group_connectivity,
                estimate_mean=group_mean,
                estimate_std=group_std,
                raw_data_colors=hist_color[groupes.index(groupe)],
                fitted_distribution_color=fit_color[groupes.index(groupe)],
                title='Ipsilesional mean connectivity distribution  for {}'.format(kind),
                xtitle='Functional connectivity coefficient', ytitle='Proportion of subjects',
                legend_fitted='{} distribution'.format(groupe),
                legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
            plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                        linewidth=2)
        pdf.savefig()
        plt.show()
        
# Estimate mean and standard deviation of mean contralesional connectivity
contralesional_mean_connectivity_parameters = dict.fromkeys(groupes)
for groupe in groupes:
    contralesional_mean_connectivity_parameters[groupe] = dict.fromkeys(kinds)
    for kind in kinds:
        # Stack the mean homotopic connectivity of each subject for the current group
        subjects_mean_contra_connectivity = np.array(
            [contralesional_mean_connectivity[groupe][subject][kind]['mean connectivity']
             for subject in contralesional_mean_connectivity[groupe].keys()])
        # Estimate the mean and std assuming a Gaussian behavior
        subjects_mean_contra_connectivity_, mean_estimation, std_estimation = \
            parametric_tests.functional_connectivity_distribution_estimation(subjects_mean_contra_connectivity)
        # Fill a dictionary saving the results for each groups and kind
        contralesional_mean_connectivity_parameters[groupe][kind] = {
            'subjects mean contralesional connectivity': subjects_mean_contra_connectivity_,
            'contralesional distribution mean': mean_estimation,
            'contralesional distribution standard deviation': std_estimation}

# Plot the distribution of mean ipsilesional connectivity assuming gaussian
# behavior
with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                       'contralesional_mean_connectivity_distribution.pdf')) as pdf:
    for kind in kinds:
        plt.figure()
        for groupe in groupes:
            group_connectivity = contralesional_mean_connectivity_parameters[groupe][kind][
                'subjects mean contralesional connectivity']
            group_mean = contralesional_mean_connectivity_parameters[groupe][kind][
                'contralesional distribution mean']
            group_std = contralesional_mean_connectivity_parameters[groupe][kind][
                'contralesional distribution standard deviation']
            display.display_gaussian_connectivity_fit(
                vectorized_connectivity=group_connectivity,
                estimate_mean=group_mean,
                estimate_std=group_std,
                raw_data_colors=hist_color[groupes.index(groupe)],
                fitted_distribution_color=fit_color[groupes.index(groupe)],
                title='Contralesional mean connectivity distribution for {}'.format(kind),
                xtitle='Functional connectivity coefficient', ytitle='Proportion of subjects',
                legend_fitted='{} distribution'.format(groupe),
                legend_data=groupe, display_fit='yes', ms=3.5, line_width=2)
            plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                        linewidth=2)
        pdf.savefig()
        plt.show()

# Compute the intra-network connectivity for the ipsilesional hemisphere in
# groups
ipsilesional_intra_network_connectivity_dict, \
    ipsi_network_dict, ipsi_network_labels_list, ipsi_network_label_colors = \
    ccm.intra_network_functional_connectivity(
        subjects_individual_matrices_dictionnary=ipsilesional_subjects_connectivity_matrices,
        groupes=groupes, kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname='Hemisphere_regions',
        roi_indices_column_name='index',
        network_column_name='network',
        color_of_network_column='Color')

# Estimate mean and standard deviation of ipsilesional intra network parameters
ipsi_intra_network_distribution_parameters = dict.fromkeys(network_labels_list)
for network in network_labels_list:
    if network not in ['Basal_Ganglia', 'Precuneus', 'Auditory']:
        ipsi_intra_network_distribution_parameters[network] = dict.fromkeys(groupes)
        for groupe in groupes:
            ipsi_intra_network_distribution_parameters[network][groupe] = dict.fromkeys(kinds)
            for kind in kinds:
                # Stack the mean homotopic connectivity of each subject for the current group
                subjects_mean_ipsi_intra_network_connectivity = np.array(
                    [ipsilesional_intra_network_connectivity_dict[groupe][subject][kind][network][
                         'network connectivity strength']
                     for subject in ipsilesional_intra_network_connectivity_dict[groupe].keys()])
                # Estimate the mean and std assuming a Gaussian behavior
                subjects_mean_ipsi_intra_network_connectivity_, mean_intra_estimation, std_intra_estimation = \
                    parametric_tests.functional_connectivity_distribution_estimation(
                        subjects_mean_ipsi_intra_network_connectivity)
                # Fill a dictionary saving the results for each groups and kind
                ipsi_intra_network_distribution_parameters[network][groupe][kind] = {
                    'subjects mean ipsi intra connectivity': subjects_mean_ipsi_intra_network_connectivity_,
                    'ipsi intra distribution mean': mean_intra_estimation,
                    'ipsi intra distribution standard deviation': std_intra_estimation}

for kind in kinds:
    with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                           kind + '_ipsi_intra_network_connectivity_distribution.pdf')) as pdf:

        for network in network_labels_list:
            if network not in ['Basal_Ganglia', 'Precuneus', 'Auditory']:
                plt.figure(constrained_layout=True)
                for groupe in groupes:
                    group_connectivity = ipsi_intra_network_distribution_parameters[network][groupe][kind][
                        'subjects mean ipsi intra connectivity']
                    group_mean = ipsi_intra_network_distribution_parameters[network][groupe][kind][
                        'ipsi intra distribution mean']
                    group_std =  ipsi_intra_network_distribution_parameters[network][groupe][kind][
                        'ipsi intra distribution standard deviation']
                    display.display_gaussian_connectivity_fit(
                        vectorized_connectivity=group_connectivity,
                        estimate_mean=group_mean,
                        estimate_std=group_std,
                        raw_data_colors=hist_color[groupes.index(groupe)],
                        fitted_distribution_color=fit_color[groupes.index(groupe)],
                        title='',
                        xtitle='Functional connectivity', ytitle='Proportions of subjects',
                        legend_fitted='{} distribution'.format(groupe),
                        legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
                    plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                                linewidth=2)
                    plt.title('Mean ipsilesional connectivity distribution for the {} network'.format(network))

                pdf.savefig()
                plt.show()

# Compute the intra-network connectivity for the contralesional hemisphere in
# groups
contralesional_intra_network_connectivity_dict, \
    contra_network_dict, contra_network_labels_list, contra_network_label_colors = \
    ccm.intra_network_functional_connectivity(
        subjects_individual_matrices_dictionnary=contralesional_subjects_connectivity_matrices,
        groupes=groupes, kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname='Hemisphere_regions',
        roi_indices_column_name='index',
        network_column_name='network',
        color_of_network_column='Color')

# Estimate mean and standard deviation of contralesional intra network parameters
contra_intra_network_distribution_parameters = dict.fromkeys(network_labels_list)
for network in network_labels_list:
    if network not in ['Basal_Ganglia', 'Precuneus', 'Auditory']:
        contra_intra_network_distribution_parameters[network] = dict.fromkeys(groupes)
        for groupe in groupes:
            contra_intra_network_distribution_parameters[network][groupe] = dict.fromkeys(kinds)
            for kind in kinds:
                # Stack the mean homotopic connectivity of each subject for the current group
                subjects_mean_contra_intra_network_connectivity = np.array(
                    [contralesional_intra_network_connectivity_dict[groupe][subject][kind][network][
                         'network connectivity strength']
                     for subject in contralesional_intra_network_connectivity_dict[groupe].keys()])
                # Estimate the mean and std assuming a Gaussian behavior
                subjects_mean_contra_intra_network_connectivity_, mean_intra_estimation, std_intra_estimation = \
                    parametric_tests.functional_connectivity_distribution_estimation(
                        subjects_mean_contra_intra_network_connectivity)
                # Fill a dictionary saving the results for each groups and kind
                contra_intra_network_distribution_parameters[network][groupe][kind] = {
                    'subjects mean contra intra connectivity': subjects_mean_contra_intra_network_connectivity_,
                    'contra intra distribution mean': mean_intra_estimation,
                    'contra intra distribution standard deviation': std_intra_estimation}

for kind in kinds:
    with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                           kind + '_contra_intra_network_connectivity_distribution.pdf')) as pdf:

        for network in network_labels_list:
            if network not in ['Basal_Ganglia', 'Precuneus', 'Auditory']:
                plt.figure(constrained_layout=True)
                for groupe in groupes:
                    group_connectivity = contra_intra_network_distribution_parameters[network][groupe][kind][
                        'subjects mean contra intra connectivity']
                    group_mean = contra_intra_network_distribution_parameters[network][groupe][kind][
                        'contra intra distribution mean']
                    group_std = contra_intra_network_distribution_parameters[network][groupe][kind][
                        'contra intra distribution standard deviation']
                    display.display_gaussian_connectivity_fit(
                        vectorized_connectivity=group_connectivity,
                        estimate_mean=group_mean,
                        estimate_std=group_std,
                        raw_data_colors=hist_color[groupes.index(groupe)],
                        fitted_distribution_color=fit_color[groupes.index(groupe)],
                        title='',
                        xtitle='Functional connectivity', ytitle='Proportion of subjects',
                        legend_fitted='{} distribution'.format(groupe),
                        legend_data=groupe, display_fit='yes', ms=3.5, line_width=2.5)
                    plt.axvline(x=group_mean, color=fit_color[groupes.index(groupe)],
                                linewidth=2)
                    plt.title('Mean contralesional connectivity distribution for the {} network'.format(network))

                pdf.savefig()
                plt.show()

# Save the ipsilesional intra-network connectivity for each groups and network
data_management.csv_from_intra_network_dictionary(subjects_dictionary=ipsilesional_intra_network_connectivity_dict,
                                                  groupes=groupes,
                                                  kinds=kinds,
                                                  network_labels_list=ipsi_network_labels_list,
                                                  field_to_write='network connectivity strength',
                                                  output_directory=output_csv_directory,
                                                  csv_prefix='ipsi_intra',
                                                  delimiter=',')

# Save the contra-lesional intra-network connectivity for each group and networks
data_management.csv_from_intra_network_dictionary(subjects_dictionary=contralesional_intra_network_connectivity_dict,
                                                  groupes=groupes,
                                                  kinds=kinds,
                                                  network_labels_list=contra_network_labels_list,
                                                  field_to_write='network connectivity strength',
                                                  output_directory=output_csv_directory,
                                                  csv_prefix='contra_intra',
                                                  delimiter=',')

# Save the overall mean ipsilesional connectivity for each group and kind
for group in groupes:
    for kind in kinds:
        data_management.csv_from_dictionary(subjects_dictionary=ipsilesional_mean_connectivity,
                                            groupes=[group],
                                            kinds=[kind],
                                            field_to_write='mean connectivity',
                                            header=['subjects', 'mean_ipsi'],
                                            csv_filename='mean_ipsilesional.csv',
                                            output_directory=os.path.join(output_csv_directory, kind),
                                            delimiter=',')

        # Save the overall mean contralesional connectivity for each group and kind
        data_management.csv_from_dictionary(subjects_dictionary=contralesional_mean_connectivity,
                                            groupes=[group],
                                            kinds=[kind],
                                            field_to_write='mean connectivity',
                                            header=['subjects', 'mean_contra'],
                                            csv_filename='mean_contralesional.csv',
                                            output_directory=os.path.join(output_csv_directory, kind),
                                            delimiter=',')

# Compute the inter-network connectivity for whole brain:
subjects_inter_network_connectivity_matrices, inter_network_labels = \
    ccm.inter_network_subjects_connectivity_matrices(
        subjects_individual_matrices_dictionnary=Z_subjects_connectivity_matrices,
        groupes=groupes, kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname=sheetname,
        network_column_name='network',
        roi_indices_column_name='atlas4D index')


# Compute ipsilesional inter-network connectivity
subjects_inter_network_ipsilesional_connectivity_matrices, ipsi_inter_network_labels = \
    ccm.inter_network_subjects_connectivity_matrices(
        subjects_individual_matrices_dictionnary=ipsilesional_subjects_connectivity_matrices,
        groupes=groupes,
        kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname='Hemisphere_regions', network_column_name='network',
        roi_indices_column_name='index')

# Compute contralesional inter-network connectivity
subjects_inter_network_contralesional_connectivity_matrices, contra_inter_network_labels = \
    ccm.inter_network_subjects_connectivity_matrices(
        subjects_individual_matrices_dictionnary=contralesional_subjects_connectivity_matrices,
        groupes=groupes,
        kinds=kinds,
        atlas_file=atlas_excel_file,
        sheetname='Hemisphere_regions',
        network_column_name='network',
        roi_indices_column_name='index')

# Now save the different dictionary for the current analysis
save_dict_path = os.path.join(output_csv_directory, 'dictionary')
dictionary_output_directory = data_management.create_directory(save_dict_path)
# Save the labels order for inter-network connectivity: whole brain, ipsi/contra-lesional
folders_and_files_management.save_object(object_to_save=inter_network_labels,
                                         saving_directory=dictionary_output_directory,
                                         filename='whole_brain_inter_networks_labels.pkl')

folders_and_files_management.save_object(object_to_save=ipsi_inter_network_labels,
                                         saving_directory=dictionary_output_directory,
                                         filename='ipsi_inter_networks_labels.pkl')

folders_and_files_management.save_object(object_to_save=contra_inter_network_labels,
                                         saving_directory=dictionary_output_directory,
                                         filename='contra_inter_networks_labels.pkl')

# Save the times series dictionary
folders_and_files_management.save_object(object_to_save=times_series_individual_atlases,
                                         saving_directory=dictionary_output_directory,
                                         filename='times_series_individual_atlases.pkl')
# Save the raw subjects matrices dictionary
folders_and_files_management.save_object(object_to_save=subjects_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='raw_subjects_connectivity_matrices.pkl')
# Save the Z-fisher transform matrices dictionary
folders_and_files_management.save_object(object_to_save=Z_subjects_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='z_fisher_transform_subjects_connectivity_matrices.pkl')
# Save the Z-fisher mean groups connectivity matrices
folders_and_files_management.save_object(object_to_save=Z_mean_groups_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='z_fisher_groups_mean_connectivity_matrices.pkl')
# Save the whole brain mean connectivity dictionary
folders_and_files_management.save_object(object_to_save=whole_brain_mean_connectivity,
                                         saving_directory=dictionary_output_directory,
                                         filename='whole_brain_mean_connectivity.pkl')
# Save the whole brain homotopic connectivity dictionary
folders_and_files_management.save_object(object_to_save=homotopic_connectivity,
                                         saving_directory=dictionary_output_directory,
                                         filename='whole_brain_mean_homotopic_connectivity.pkl')
# Save the intra-network mean homotopic dictionary
folders_and_files_management.save_object(object_to_save=homotopic_intranetwork_d,
                                         saving_directory=dictionary_output_directory,
                                         filename='intra_network_mean_homotopic_connectivity.pkl')
# Save the whole brain intra_network connectivity dictionary
folders_and_files_management.save_object(object_to_save=intra_network_connectivity_dict,
                                         saving_directory=dictionary_output_directory,
                                         filename='whole_brain_intra_network_connectivity.pkl')
# Save the ipsilesional intra-network connectivity dictionary
folders_and_files_management.save_object(object_to_save=ipsilesional_intra_network_connectivity_dict,
                                         saving_directory=dictionary_output_directory,
                                         filename='ipsilesional_intra_network_connectivity.pkl')
# Save the contralesional intra-network connectivity dictionary
folders_and_files_management.save_object(object_to_save=contralesional_intra_network_connectivity_dict,
                                         saving_directory=dictionary_output_directory,
                                         filename='contralesional_intra_network_connectivity.pkl')
# Save the whole-brain inter-network connectivity dictionary
folders_and_files_management.save_object(object_to_save=subjects_inter_network_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='subjects_inter_network_connectivity_matrices.pkl')
# Save the ipsilesional inter-network connectivity dictionary
folders_and_files_management.save_object(object_to_save=subjects_inter_network_ipsilesional_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='subjects_inter_network_ipsi_connectivity_matrices.pkl')
# Save the contralesional inter-network connectivity dictionary
folders_and_files_management.save_object(object_to_save=subjects_inter_network_contralesional_connectivity_matrices,
                                         saving_directory=dictionary_output_directory,
                                         filename='subjects_inter_network_contra_connectivity_matrices.pkl')

# Statistical analysis
kinds_to_model = ['correlation', 'partial correlation', 'tangent']
groups_in_models = groupes

# Fit three linear model for the three type of overall connections
models_to_build = ['mean_connectivity', 'mean_homotopic',
                   'mean_contralesional', 'mean_ipsilesional']

# variables in the model
variables_model = ['langage_clinique']

# formulation of the model
model_formula = 'langage_clinique'

model_network_list = ['DMN', 'Auditory', 'Executive',
                      'Language', 'Basal_Ganglia', 'MTL',
                      'Salience', 'Sensorimotor', 'Visuospatial',
                      'Primary_Visual', 'Precuneus', 'Secondary_Visual']

ipsi_contra_model_network_list = ['DMN', 'Executive',
                                  'Language',  'MTL',
                                  'Salience', 'Sensorimotor', 'Visuospatial',
                                  'Primary_Visual', 'Secondary_Visual']

correction_methods = ['fdr_bh', 'bonferroni']

# Put a column named subject in the behavioral dataframe
behavioral_dataframe = data_management.read_csv(os.path.join(output_csv_directory, 'behavioral_data.csv'))
behavioral_data = behavioral_dataframe.rename(columns={behavioral_dataframe.columns[0]: 'subjects'})
# Shift index to be the subjects identifiers
behavioral_data = data_management.shift_index_column(
    panda_dataframe=behavioral_data,
    columns_to_index=['subjects'])


# Perform a one way ANOVA with language status as variable
# Whole brain models
regression_analysis_model.one_way_anova(models=models_to_build,
                                        groups=groupes,
                                        behavioral_dataframe=behavioral_data,
                                        kinds=kinds,
                                        correction_method=correction_methods,
                                        root_analysis_directory=output_csv_directory,
                                        variables_in_model=variables_model,
                                        alpha=alpha)

# Network models: intra homotopic
regression_analysis_model.one_way_anova_network(root_analysis_directory=output_csv_directory,
                                                kinds=kinds,
                                                groups=groupes,
                                                networks_list=model_network_list,
                                                models=['intra_homotopic'],
                                                correction_method=correction_methods,
                                                variables_in_model=variables_model,
                                                alpha=alpha,
                                                behavioral_dataframe=behavioral_data)

# Network models: contra intra, ipsi intra, intra.
regression_analysis_model.one_way_anova_network(root_analysis_directory=output_csv_directory,
                                                kinds=kinds,
                                                groups=groupes,
                                                networks_list=ipsi_contra_model_network_list,
                                                models=['intra', 'contra_intra', 'ipsi_intra'],
                                                correction_method=correction_methods,
                                                variables_in_model=variables_model,
                                                alpha=alpha,
                                                behavioral_dataframe=behavioral_data)

# TODO: write a function to perform a one way ANOVA with internetwork matrices.
# Display of the results
# The whole brain measures: whole brain mean connectivity,  mean homotopic, mean ipsilesional,
# mean contralesional
output_csv_directory = '/media/db242421/db242421_data/ConPagnon_data/language_study_ANOVA_ACM_controls'
results_directory = os.path.join(output_csv_directory, 'regression_analysis')
output_figure_directory = os.path.join(output_csv_directory, 'figures')
model_to_plot = ['mean_connectivity', 'mean_homotopic', 'mean_ipsilesional', 'mean_contralesional']
network_model_to_plot = ['intra', 'contra_intra', 'ipsi_intra']
# network: ipsi, contra, intra
model_network_list_1 = ['DMN', 'Executive',
                      'Language',  'MTL',
                      'Salience', 'Sensorimotor', 'Visuospatial',
                      'Primary_Visual', 'Secondary_Visual']
# network: whole brain scores
model_network_list_2 = ['DMN', 'Auditory', 'Executive',
                         'Language', 'Basal_Ganglia', 'MTL',
                         'Salience', 'Sensorimotor', 'Visuospatial',
                         'Primary_Visual', 'Precuneus', 'Secondary_Visual']

model_network_list = model_network_list_1

# Colors of network in the order of model networks list
atlas_information_colors = atlas_information[['network', 'Color']]
atlas_information_colors.set_index('network', inplace=True)
network_colors = [np.array(atlas_information_colors.loc[network]['Color'])[0] for network in
                  model_network_list]

# Variable of interest
variables_of_interest = ['langage_clinique[T.C]', 'langage_clinique[T.N]']

# Correction method
correction_methods = ['fdr_bh', 'bonferroni']

# Global connectivity composite scores
for variable in variables_of_interest:
    for kind in kinds:
        # For each king, fetch t values, and corrected p values
        t_values = []
        corrected_p_values = []
        for model in model_to_plot:
            # Read parameters file
            model_result = data_management.read_csv(
                csv_file=os.path.join(results_directory, kind, model + '_parameters.csv'))
            # Fetch t values, and corrected p values for the current model
            variable_t_values = np.array(model_result.loc[model_result['variables'] == variable]['t'])[0]
            t_values.append(variable_t_values)
            variable_p_values = np.array(model_result.loc[model_result['variables'] == variable][
                                             'FDRcorrected_pvalues'])[0]
            corrected_p_values.append(variable_p_values)

        # Display the barplot for t and p values for each kind and variables
        with backend_pdf.PdfPages(os.path.join(output_figure_directory, kind + '_' + variable +
                                               '_wb_homo_ipsi_contra.pdf')) as pdf:

            t_and_p_values_barplot(t_values=t_values,
                                   p_values=corrected_p_values,
                                   alpha_level=alpha,
                                   xlabel_color=['black', 'black', 'black', 'black'],
                                   bar_labels=model_to_plot,
                                   t_xlabel='',
                                   t_ylabel='t scores',
                                   p_xlabel='',
                                   p_ylabel='FDR corrected p values',
                                   t_title='{} effect for \n {} - {} ({})'.format(
                                       variable,
                                       (groupes[2] if variable == 'langage_clinique[T.C]' else groupes[1]),
                                       groupes[0],
                                       kind),
                                   p_title='{} effect for \n {} - {} ({})'.format(
                                       variable,
                                       (groupes[2] if variable == 'langage_clinique[T.C]' else groupes[1]),
                                       groupes[0],
                                       kind),
                                   xlabel_size=2)
            pdf.savefig()
        # plt.show()

# Network composite scores measures
network_model = ['intra_homotopic']
model_network_list = model_network_list_2
for tt in network_model:
    for variable in variables_of_interest:
        for kind in kinds[0:1]:
            # For each kind, fetch t values, and corrected p values
            t_values = []
            corrected_p_values = []
            for network in model_network_list:
                # Read parameters file
                model_result = data_management.read_csv(
                    csv_file=os.path.join(results_directory, kind, network, tt + '_parameters.csv'))
                # Fetch t values, and corrected p values for the current model
                variable_t_values = np.array(model_result.loc[model_result['variables'] == variable]['t'])[0]
                t_values.append(variable_t_values)
                variable_p_values = np.array(model_result.loc[model_result['variables'] == variable][
                                                 'FDRcorrected_pvalues'])[0]
                corrected_p_values.append(variable_p_values)

            # Display the barplot for t and p values for each kind and variables
            with backend_pdf.PdfPages(os.path.join(output_figure_directory,
                                                   kind, variable + '_' + tt + '_pdf')) as pdf:
                t_and_p_values_barplot(t_values=t_values,
                                       p_values=corrected_p_values,
                                       alpha_level=alpha,
                                       xlabel_color=network_colors,
                                       bar_labels=model_network_list,
                                       t_xlabel='',
                                       t_ylabel='t scores',
                                       p_xlabel='',
                                       p_ylabel='FDR corrected p values',
                                       t_title='{} network : {} effect for \n {} - {}. ({})'.format(
                                           tt,
                                           variable,
                                           (groupes[2] if variable == 'langage_clinique[T.C]' else groupes[1]),
                                           groupes[0],
                                           kind),
                                       p_title='{} network : {} effect for \n {} - {}. ({})'.format(
                                           tt,
                                           variable,
                                           (groupes[2] if variable == 'langage_clinique[T.C]' else groupes[1]),
                                           groupes[0],
                                           kind),
                                       xlabel_size=2)
                pdf.savefig()


# One way anova:
# Number of post hoc comparison inside each model
n_post_hoc_comparison = 3
# Set contrast name, and number of contrast for post hoc analysis
contrasts_name = ['Controls-Impaired language',
                  'Non impaired language-Impaired language',
                  'Non impaired language-Controls']
n_contrast = len(contrasts_name)

# whole brain levels
# Fetch the results for the model (F test) and plot it.
for kind in kinds:
    # F test values for all modes
    f_test_values = []
    # Array to stack the p values for each f test and each model, for each method
    f_test_p_values = np.zeros((len(correction_methods), len(model_to_plot)))

    # Array to stack the p values for the
    # post hoc t test between all contrast for all model
    # for each method
    post_hoc_t_test_p_values = np.zeros((len(correction_methods), len(model_to_plot), n_post_hoc_comparison))

    # Post hoc p values
    post_hoc_t_values = []

    for model in model_to_plot:

        # F test parameters files
        f_test_parameters = data_management.read_csv(
            csv_file=os.path.join(results_directory, 'ANOVA', kind, model + '_f_test_parameters.csv')
        )
        # Post hoc t test parameters files
        post_hoc_parameters = data_management.read_csv(
            csv_file=os.path.join(results_directory, 'ANOVA', kind, model + '_post_hoc_parameters.csv')
        )

        f_value = f_test_parameters['F'].iloc[0]
        f_test_values.append(f_value)

        post_hoc_t_values.append(np.array(post_hoc_parameters['t']))
        for correction in correction_methods:
            f_test_p_values[correction_methods.index(correction), model_to_plot.index(model), ...] = \
                f_test_parameters[correction + '_p_value'].iloc[0]
            post_hoc_t_test_p_values[correction_methods.index(correction), model_to_plot.index(model), ...] = \
                np.array(post_hoc_parameters[correction + '_p_value'])

    # Save results in pdf files for the f test model
    with backend_pdf.PdfPages(os.path.join(output_figure_directory, kind,
                                           kind + '_whole_brain_models_f_test.pdf')) as pdf:
        for correction in correction_methods:
            # Plot f values for each model on the same plot
            t_and_p_values_barplot(t_values=f_test_values,
                                   p_values=f_test_p_values[correction_methods.index(correction), ...],
                                   alpha_level=alpha,
                                   xlabel_color=['black'] * len(model_to_plot),
                                   bar_labels=model_to_plot,
                                   t_xlabel='',
                                   t_ylabel='F values',
                                   p_xlabel='',
                                   p_ylabel=correction + ' corrected p values',
                                   t_title='One way ANOVA with language profile as factors, \n ({}, {})'.format(
                                       kind,
                                       correction + '_corrected'),
                                   p_title='One way ANOVA with language profile as factors, \n ({}, {})'.format(
                                       kind,
                                       correction + '_corrected'))
            pdf.savefig()
            plt.show()

    # Save results in pdf files for the post hoc t test: one file per
    # contrast
    for contrast in contrasts_name:
        with backend_pdf.PdfPages(os.path.join(output_figure_directory, kind,
                                                kind + '_' + contrast + '_whole_brain_model_t_values.pdf')) as pdf:
            for correction in correction_methods:
                # Plot f values for each model on the same plot
                t_and_p_values_barplot(t_values=np.array(post_hoc_t_values)[:, contrasts_name.index(contrast)],
                                       p_values=post_hoc_t_test_p_values[correction_methods.index(correction), :,
                                                                         contrasts_name.index(contrast)],
                                       alpha_level=alpha,
                                       xlabel_color=['black'] * len(model_to_plot),
                                       bar_labels=model_to_plot,
                                       t_xlabel='',
                                       t_ylabel='t values',
                                       p_xlabel='',
                                       p_ylabel=correction + ' corrected p values',
                                       t_title='One way ANOVA with language profile as factors, \n ({}, {}), '
                                               '\n {}'.format(kind, correction + '_corrected', contrast),
                                       p_title='One way ANOVA with language profile as factors, \n ({}, {}), '
                                               '\n {}'.format(kind, correction + '_corrected', contrast))
                pdf.savefig()
                plt.show()


# Plot at the network levels
for kind in kinds:
    for model in network_model_to_plot:
        # Post hoc p values for all network
        post_hoc_t_values = []
        # F test values for all network
        f_test_values = []
        # Array to stack the p values for each f test and each model, for each method
        f_test_p_values = np.zeros((len(correction_methods), len(model_network_list)))

        # Array to stack the p values for all post hoc t test
        # for all network, for all correction method
        post_hoc_t_test_p_values = np.zeros((len(correction_methods), len(model_network_list),
                                             n_post_hoc_comparison))
        for network in model_network_list:

            # F test parameters files
            f_test_parameters = data_management.read_csv(
                csv_file=os.path.join(results_directory, 'ANOVA', kind, network,
                                      model + '_f_test_parameters.csv')
            )
            # Post hoc t test parameters files
            post_hoc_parameters = data_management.read_csv(
                csv_file=os.path.join(results_directory, 'ANOVA', kind, network,
                                      model + '_post_hoc_parameters.csv')
            )

            f_value = f_test_parameters['F'].iloc[0]
            f_test_values.append(f_value)

            post_hoc_t_values.append(np.array(post_hoc_parameters['t']))

            for correction in correction_methods:
                f_test_p_values[correction_methods.index(correction), model_network_list.index(network), ...] = \
                    f_test_parameters[correction + '_p_value'].iloc[0]
                post_hoc_t_test_p_values[correction_methods.index(correction), model_network_list.index(network), ...] = \
                    np.array(post_hoc_parameters[correction + '_p_value'])

        # Now plot F value, post hoc t values
        with backend_pdf.PdfPages(os.path.join(output_figure_directory, kind,
                                               kind + '_' + model + '_f_test_all_network.pdf')) as pdf:
            for correction in correction_methods:
                # F test plot
                t_and_p_values_barplot(t_values=f_test_values,
                                       p_values=f_test_p_values[correction_methods.index(correction)],
                                       alpha_level=alpha,
                                       xlabel_color=network_colors,
                                       bar_labels=model_network_list,
                                       t_xlabel='',
                                       t_ylabel='F test values',
                                       p_xlabel='',
                                       p_ylabel=correction + ' corrected p values',
                                       p_title='Network level ({}) ANOVA with language profile as factors, '
                                               '\n ({}, {})'.format(model, kind, correction + '_corrected'),
                                       t_title='Network level ({}) ANOVA with language profile as factors, '
                                               '\n ({}, {})'.format(model, kind, correction + '_corrected'))
                pdf.savefig()
                plt.show()

        # Now, plot the post hoc t test results for all
        # possible contrast
        for contrast in contrasts_name:
            with backend_pdf.PdfPages(os.path.join(output_figure_directory, kind,
                                                   kind + '_' + contrast + '_' + model + '_t_values.pdf')) as pdf:
                for correction in correction_methods:
                    # Plot t values for the current contrast
                    t_and_p_values_barplot(t_values=np.array(post_hoc_t_values)[:, contrasts_name.index(contrast)],
                                           p_values=post_hoc_t_test_p_values[correction_methods.index(correction), :,
                                                                             contrasts_name.index(contrast)],
                                           alpha_level=alpha,
                                           xlabel_color=network_colors,
                                           bar_labels=model_network_list,
                                           t_xlabel='',
                                           t_ylabel='t values',
                                           p_xlabel='',
                                           p_ylabel=correction + '_corrected_p_values',
                                           t_title='Network level ({}) ANOVA with language profile as factors, '
                                                   '\n ({}, {}), '
                                                   '\n {}'.format(model, kind, correction + '_corrected', contrast),
                                           p_title='Network level ({}) ANOVA with language profile as factors, '
                                                   '\n ({}, {}), '
                                                   '\n {}'.format(model, kind, correction + '_corrected', contrast))
                    pdf.savefig()
                    plt.show()