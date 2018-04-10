"""
This module is designed to study the link between
functional connectivity and behaviour. The algorithm
named connectome predictive modelling is adapted from
[1].

.. [1] Using connectome-based predictive modeling to
predict individual behavior from brain connectivity, Shen et al.
"""
from data_handling import atlas, data_management
from utils.folders_and_files_management import load_object
import numpy as np
from connectivity_statistics.parametric_tests import design_matrix_builder
from nilearn.connectome import sym_matrix_to_vec
from patsy import dmatrix
# Atlas set up
atlas_folder = 'D:\\atlas_AVCnn'
atlas_name ='atlas4D_2.nii'
monAtlas = atlas.Atlas(path=atlas_folder,
                       name=atlas_name)
# Atlas path
atlas_path = monAtlas.fetch_atlas()
# Read labels regions files
labels_text_file = 'D:\\atlas_AVCnn\\atlas4D_2_labels.csv'
labels_regions = monAtlas.GetLabels(labels_text_file)
# User defined colors for labels ROIs regions
colors = ['navy', 'sienna', 'orange', 'orchid', 'indianred', 'olive',
          'goldenrod', 'turquoise', 'darkslategray', 'limegreen', 'black',
          'lightpink']
# Number of regions in each user defined networks
networks = [2, 10, 2, 6, 10, 2, 8, 6, 8, 8, 6, 4]
# Transformation of string colors list to an RGB color array,
# all colors ranging between 0 and 1.
labels_colors = (1./255)*monAtlas.UserLabelsColors(networks=networks,
                                                   colors=colors)
# Fetch nodes coordinates
atlas_nodes = monAtlas.GetCenterOfMass()
# Fetch number of nodes in the parcellation
n_nodes = monAtlas.GetRegionNumbers()

# Load raw and Z-fisher transform matrix
subjects_connectivity_matrices = load_object(full_path_to_object='D:\\ConPagnon_data\\raw_subjects_matrices.pkl')
Z_subjects_connectivity_matrices = load_object(full_path_to_object='D:\\ConPagnon_data\\Z_subjects_matrices.pkl')

# Load behavioral data file
regression_data_file = data_management.read_excel_file(excel_file_path='D:\\regression_data\\regression_data.xlsx',
                                                       sheetname='patients_data')

# Fetch patients matrices, and one behavioral score
kind = 'correlation'
patients_subjects_ids = list(subjects_connectivity_matrices['patients'].keys())
# Patients matrices stack
patients_connectivity_matrices = np.array([subjects_connectivity_matrices['patients'][s][kind] for
                                           s in patients_subjects_ids])
# Behavioral score
behavioral_scores = regression_data_file['uni_deno'].loc[patients_subjects_ids]
# Vectorized connectivity matrices of shape (n_samples, n_features)
vectorized_connectivity_matrices = sym_matrix_to_vec(patients_connectivity_matrices, discard_diagonal=True)

# Features selection by leave one out cross validation scheme
from sklearn.model_selection import LeaveOneOut
from pylearn_mulm import mulm

# Clean behavioral data
drop_subject_in_data = ['sub40_np130304']
regression_data_file = regression_data_file.drop(drop_subject_in_data)
# Initialize leave one out object
leave_one_out_generator = LeaveOneOut()
for train_index, test_index in leave_one_out_generator.split(vectorized_connectivity_matrices):
    # For each iteration, split the patients matrices array in train and
    # test set using leave one out cross validation
    patients_train_set, leave_one_out_patients = \
        vectorized_connectivity_matrices[train_index], vectorized_connectivity_matrices[test_index]
    # Perform linear regression for feature selection controlling for confounding
    # effect
    patients_design_matrix = dmatrix(formula_like='Sexe+uni_deno', data=regression_data_file,
                                     NA_action='drop', return_type='dataframe')
    # Fetch the corresponding design matrix for the current training set
    training_set_design_matrix = patients_design_matrix.iloc[train_index]
    # Fit a linear model with muols
    training_set_model = mulm.MUOLS(patients_train_set, np.array(training_set_design_matrix))
    contrasts = np.identity(training_set_design_matrix.shape[1])
    t_value, p_value, df = training_set_model.fit().t_test(contrasts, pval=True, two_tailed=True)
