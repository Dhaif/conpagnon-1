"""
This module is designed to study the link between
functional connectivity and behaviour. The algorithm
named connectome predictive modelling is adapted from
[1].

.. [1] Using connectome-based predictive modeling to
predict individual behavior from brain connectivity, Shen et al.

author: Dhaif BEKHA.
# TODO: Break the code into small part !!!!
# TODO: Use GLM with both negative and positive values as predictor of behavioral variable
# TODO: When the predicted value is computed, add possibility to add other variable in the model
# TODO: Compute a network visualisation of the results with networkx for example
# TODO: Estimate model efficience with other metrics such as MSE, instead of simple correlation
# TODO: Estimate p-value of model power with permutations statistic
"""
from data_handling import atlas, data_management
from utils.folders_and_files_management import load_object
import numpy as np
from nilearn.connectome import sym_matrix_to_vec, vec_to_sym_matrix
from patsy import dmatrix
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
from sklearn.model_selection import LeaveOneOut
from pylearn_mulm import mulm
from sklearn import linear_model
from scipy import stats
from nilearn.plotting import plot_connectome
from data_handling import dictionary_operations
from connectivity_statistics.parametric_tests import partial_corr
import pandas as pd
import seaborn as sns


# Atlas set up
atlas_folder = 'D:\\atlas_AVCnn'
atlas_name = 'atlas4D_2.nii'
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
subjects_connectivity_matrices = load_object(
    full_path_to_object='D:\\text_output_11042018\\dictionary'
                        '\\raw_subjects_connectivity_matrices.pkl')
Z_subjects_connectivity_matrices = load_object(
    full_path_to_object='D:\\text_output_11042018\\dictionary'
                        '\\z_fisher_transform_subjects_connectivity_matrices.pkl')
# Load behavioral data file
regression_data_file = data_management.read_excel_file(
    excel_file_path='D:\\regression_data\\regression_data.xlsx',
    sheetname='cohort_functional_data')

# Type of subjects connectivity matrices
subjects_matrices = Z_subjects_connectivity_matrices

# Select a subset of patients
# Compute the connectivity matrices dictionnary with factor as keys.
group_by_factor_subjects_connectivity, population_df_by_factor, factor_keys, =\
    dictionary_operations.groupby_factor_connectivity_matrices(
        population_data_file='D:\\regression_data\\regression_data.xlsx',
        sheetname='cohort_functional_data',
        subjects_connectivity_matrices_dictionnary=subjects_matrices,
        groupes=['patients'], factors=['Lesion'], drop_subjects_list=['sub40_np130304'])

subjects_matrices = {}
subjects_matrices['patients'] = group_by_factor_subjects_connectivity['G']


# Fetch patients matrices, and one behavioral score
kind = 'tangent'
patients_subjects_ids = list(subjects_matrices['patients'].keys())
# Patients matrices stack
patients_connectivity_matrices = np.array([subjects_matrices['patients'][s][kind] for
                                           s in patients_subjects_ids])
# Set to zero the diagonal of each matrix
#for patient_matrix in range(patients_connectivity_matrices.shape[0]):
#    np.fill_diagonal(patients_connectivity_matrices[patient_matrix, :, :],
#                     np.ones(patients_connectivity_matrices[patient_matrix, :, :].shape[0]))

# Behavioral score
behavioral_scores = regression_data_file['language_score'].loc[patients_subjects_ids]
# Vectorized connectivity matrices of shape (n_samples, n_features)
vectorized_connectivity_matrices = sym_matrix_to_vec(patients_connectivity_matrices, discard_diagonal=True)

# Build confounding variable
confounding_variables = ['lesion_normalized', 'Sexe']
confounding_variables_data = regression_data_file[confounding_variables].loc[patients_subjects_ids]
# Encode the confounding variable in an array
confounding_variables_matrix = dmatrix(formula_like='+'.join(confounding_variables), data=confounding_variables_data,
                                       return_type='dataframe').drop(['Intercept'], axis=1)


# Features selection by leave one out cross validation scheme
# Clean behavioral data
drop_subject_in_data = ['sub40_np130304']
try:
    regression_data_file = regression_data_file.drop(drop_subject_in_data)
except:
    pass

# Initialize leave one out object
leave_one_out_generator = LeaveOneOut()

# Selection connectivity threshold
significance_selection_threshold = 0.01

# Initialization of behavior prediction vector
behavior_prediction_positive_edges = np.zeros(len(patients_subjects_ids))
behavior_prediction_negative_edges = np.zeros(len(patients_subjects_ids))

# Choose method to relate connectivity to behavior (predictor selection)
selection_predictor_method = 'linear_model'

patients_design_matrix = dmatrix(formula_like='language_score+Sexe+lesion_normalized',
                                 data=regression_data_file,
                                 NA_action='drop',
                                 return_type='dataframe').loc[patients_subjects_ids]

from scipy.stats import t

def predictors_selection_linear_model(training_connectivity_matrices, training_set_design_matrix,
                                      behavior_column_name, significance_selection_threshold=.01):
    """Relate each edges of subjects connectivity matrices in the training set
    with a behavioral scores using a linear model


    """
    # Reorder the design matrix, put the behavioral variable
    # to the last position
    columns_name_design_matrix = list(training_set_design_matrix.columns)
    behavioral_variable_position = columns_name_design_matrix.index(behavior_column_name)
    if behavioral_variable_position != 1:
        # Move the colmumn name corresponding to the behavioral variable of interest
        # to the 1 index of the list
        columns_name_design_matrix.insert(1, columns_name_design_matrix.pop(behavioral_variable_position))
        # Reorder the design matrix
        training_set_design_matrix = training_set_design_matrix[columns_name_design_matrix]
    else:
        training_set_design_matrix = training_set_design_matrix

    # Fit a linear model with MUOLS
    training_set_model = mulm.MUOLS(training_connectivity_matrices, np.array(training_set_design_matrix))
    contrasts = np.identity(training_set_design_matrix.shape[1])
    t_value, p_value, df = training_set_model.fit().t_test(contrasts, pval=True, two_tailed=True)

    # Fetch the t and p vector corresponding to the behavior of interest
    t_behavior = t_value[1, :]
    p_behavior = p_value[1, :]

    # For each edges convert the t statistic of the linear model in correlation
    # coefficient value
    R_mat = np.sign(t_behavior)*np.sqrt(t_behavior**2/(df[1] + t_behavior**2))
    P_mat = t.sf(np.abs(t_behavior), df[1])

    # Positive and Negative correlation indices, under the selection threshold
    negative_edges_indices = np.nonzero((R_mat < 0) & (P_mat < significance_selection_threshold))
    positives_edges_indices = np.nonzero((R_mat > 0) & (P_mat < significance_selection_threshold))

    # Fill the corresponding indices with 1 if indices exist, zero elsewhere
    negative_edges_mask[negative_edges_indices] = 1
    positive_edges_mask[positives_edges_indices] = 1

    # Get the sum off all edges in the mask
    negative_edges_summary_values = np.zeros(training_connectivity_matrices.shape[0])
    positive_edges_summary_values = np.zeros(training_connectivity_matrices.shape[0])

    for i in range(training_connectivity_matrices.shape[0]):
        negative_edges_summary_values[i] = np.sum(np.multiply(negative_edges_mask,
                                                              training_connectivity_matrices[i, ...]))
        positive_edges_summary_values[i] = np.sum(np.multiply(positive_edges_mask,
                                                              training_connectivity_matrices[i, ...]))

    return training_set_design_matrix, t_behavior, p_behavior, R_mat, P_mat





for train_index, test_index in leave_one_out_generator.split(vectorized_connectivity_matrices):
    print('Train on {}'.format([patients_subjects_ids[i] for i in train_index]))
    print('Test on {}'.format([patients_subjects_ids[i] for i in test_index]))
    # For each iteration, split the patients matrices array in train and
    # test set using leave one out cross validation
    patients_train_set, leave_one_out_patients = \
        vectorized_connectivity_matrices[train_index], vectorized_connectivity_matrices[test_index]

    training_set_behavioral_score = behavioral_scores[train_index]
    test_subject_behavioral_score = behavioral_scores[test_index]

    training_set_confounding_variables = np.array(confounding_variables_matrix)[train_index]

    if selection_predictor_method == 'linear_model':

        # Perform linear regression for feature selection controlling for confounding
        # effect
        # Fetch the corresponding design matrix for the current training set
        training_set_design_matrix = patients_design_matrix.iloc[train_index]
        # Fit a linear model with muols
        training_set_model = mulm.MUOLS(patients_train_set, np.array(training_set_design_matrix))
        contrasts = np.identity(training_set_design_matrix.shape[1])
        t_value, p_value, df = training_set_model.fit().t_test(contrasts, pval=True, two_tailed=True)

        # TODO: convert t statistic to partial r-value !!!

        # By default, the behavior of interest is assume to be
        # the first variable in the model
        t_behavior = t_value[2, :]
        p_behavior = p_value[2, :]

        # Separate edge who correlates positively and negatively to the behavior of interest
        # Positive and negative mask initialisation
        negative_edges_mask = np.zeros(patients_train_set.shape[1])
        positive_edges_mask = np.zeros(patients_train_set.shape[1])

        # Positive and Negative correlation indices, under the selection threshold
        negative_edges_indices = np.nonzero((t_behavior < 0) & (p_behavior < significance_selection_threshold))
        positives_edges_indices = np.nonzero((t_behavior > 0) & (p_behavior < significance_selection_threshold))

        # Fill the corresponding indices with 1 if indices exist, zero elsewhere
        negative_edges_mask[negative_edges_indices] = 1
        positive_edges_mask[positives_edges_indices] = 1

        # Get the sum off all edges in the mask
        negative_edges_summary_values = np.zeros(patients_train_set.shape[0])
        positive_edges_summary_values = np.zeros(patients_train_set.shape[0])

        for i in range(patients_train_set.shape[0]):
            negative_edges_summary_values[i] = np.sum(np.multiply(negative_edges_mask, patients_train_set[i, ...]))
            positive_edges_summary_values[i] = np.sum(np.multiply(positive_edges_mask, patients_train_set[i, ...]))

    elif selection_predictor_method == 'correlation':
        # Matrix which will contain the correlation of each edge to behavior, and the corresponding
        # p values
        R_mat = np.zeros(patients_train_set.shape[1])
        P_mat = np.zeros(patients_train_set.shape[1])
        # Positive and negative mask initialisation
        negative_edges_mask = np.zeros(patients_train_set.shape[1])
        positive_edges_mask = np.zeros(patients_train_set.shape[1])

        for i in range(patients_train_set.shape[1]):
            # Simple correlation between each edges and behavior
            R_mat[i], P_mat[i] = stats.pearsonr(x=patients_train_set[:, i],
                                                y=training_set_behavioral_score)

        # Positive and Negative correlation indices, under the selection threshold
        negative_edges_indices = np.nonzero((R_mat < 0) & (P_mat < significance_selection_threshold))
        positives_edges_indices = np.nonzero((R_mat > 0) & (P_mat < significance_selection_threshold))

        # Fill the corresponding indices with 1 if indices exist, zero elsewhere
        negative_edges_mask[negative_edges_indices] = 1
        positive_edges_mask[positives_edges_indices] = 1

        # Get the sum off all edges in the mask
        negative_edges_summary_values = np.zeros(patients_train_set.shape[0])
        positive_edges_summary_values = np.zeros(patients_train_set.shape[0])

        for i in range(patients_train_set.shape[0]):
            negative_edges_summary_values[i] = np.sum(np.multiply(negative_edges_mask, patients_train_set[i, ...]))
            positive_edges_summary_values[i] = np.sum(np.multiply(positive_edges_mask, patients_train_set[i, ...]))

    elif selection_predictor_method == 'partial correlation':
        # Matrix which will contain the correlation of each edge to behavior, and the corresponding
        # p values
        R_mat = np.zeros(patients_train_set.shape[1])
        P_mat = np.zeros(patients_train_set.shape[1])

        # Positive and negative mask initialisation
        negative_edges_mask = np.zeros(patients_train_set.shape[1])
        positive_edges_mask = np.zeros(patients_train_set.shape[1])

        # Construct temporary array to contain the connectivity, behavior and
        # other variable to regress
        for i in range(patients_train_set.shape[1]):
            R_, P_ = partial_corr(np.c_[patients_train_set[:, i], training_set_behavioral_score,
                                  training_set_confounding_variables])
            R_mat[i] = R_[0, 1]
            P_mat[i] = P_[0, 1]

        # Positive and Negative correlation indices, under the selection threshold
        negative_edges_indices = np.nonzero((R_mat < 0) & (P_mat < significance_selection_threshold))
        positives_edges_indices = np.nonzero((R_mat > 0) & (P_mat < significance_selection_threshold))

        # Fill the corresponding indices with 1 if indices exist, zero elsewhere
        negative_edges_mask[negative_edges_indices] = 1
        positive_edges_mask[positives_edges_indices] = 1

        # Get the sum off all edges in the mask
        negative_edges_summary_values = np.zeros(patients_train_set.shape[0])
        positive_edges_summary_values = np.zeros(patients_train_set.shape[0])

        for i in range(patients_train_set.shape[0]):
            negative_edges_summary_values[i] = np.sum(np.multiply(negative_edges_mask, patients_train_set[i, ...]))
            positive_edges_summary_values[i] = np.sum(np.multiply(positive_edges_mask, patients_train_set[i, ...]))

    else:
        raise ValueError('Selection method not understood')

    # Reshape the matrices to get indices of regions for plotting purpose
    negatives_edges_matrix = vec_to_sym_matrix(vec=negative_edges_mask,
                                               diagonal=np.zeros(n_nodes))
    positive_edges_matrix = vec_to_sym_matrix(vec=positive_edges_mask,
                                              diagonal=np.zeros(n_nodes))

    # Fit a linear model on the training set, for negative and positive edges summary values
    design_matrix_negative_edges = sm.add_constant(negative_edges_summary_values)
    # design_matrix_negative_edges = np.c_[design_matrix_negative_edges, np.array(training_set_extra_variables)]

    design_matrix_positive_edges = sm.add_constant(positive_edges_summary_values)
    # design_matrix_positive_edges = np.c_[design_matrix_positive_edges, np.array(training_set_extra_variables)]

    # Fit positive edges model
    positive_edges_model = sm.OLS(training_set_behavioral_score, design_matrix_positive_edges)
    positive_edge_model_fit = positive_edges_model.fit()

    # Fit negative edges model
    negative_edges_model = sm.OLS(training_set_behavioral_score, design_matrix_negative_edges)
    negative_edge_model_fit = negative_edges_model.fit()

    # Test the positive edges model on the left out subject
    test_subject_positive_edges_summary = np.sum(np.multiply(leave_one_out_patients[0, :], positive_edges_mask))
    test_subject_negative_edges_summary = np.sum(np.multiply(leave_one_out_patients[0, :], negative_edges_mask))

    # Fit the model of on the left out subject
    behavior_prediction_negative_edges[test_index] = \
        negative_edge_model_fit.params[1]*test_subject_negative_edges_summary + \
        negative_edge_model_fit.params[0]

    behavior_prediction_positive_edges[test_index] = \
        positive_edge_model_fit.params[1]*test_subject_positive_edges_summary + positive_edge_model_fit.params[0]

# Compare prediction and true behavioral score
R_predict_negative_model, P_predict_negative_model = \
    stats.pearsonr(x=behavior_prediction_negative_edges,
                   y=np.array(behavioral_scores))

R_predict_positive_model,  P_predict_positive_model = \
    stats.pearsonr(x=np.array(behavioral_scores),
                   y=behavior_prediction_positive_edges)

# Plot relationship between predicted and true value by the model
# Add predicted score for negative and positive edges model
behavioral_scores_both_model = pd.DataFrame(data={'true_behavioral_score':np.array(behavioral_scores) ,
                                                  'predicted_positive_model_scores': behavior_prediction_positive_edges,
                                                  'predicted_negative_model_scores': behavior_prediction_negative_edges,
                                                  'language profil': regression_data_file['langage_clinique']},

                                            index=behavioral_scores.index)
plt.figure()
g = sns.lmplot(x='true_behavioral_score', y='predicted_positive_model_scores', data=behavioral_scores_both_model,
               fit_reg=False, hue='language profil', legend_out=True, legend=True)
sns.regplot(x='true_behavioral_score', y='predicted_positive_model_scores', data=behavioral_scores_both_model,
            scatter=False, ax=g.axes[0, 0], line_kws={'color': 'firebrick'})
plt.title('Predicted behavioral score versus true behavioral score \n in the positive edges model \n'
          'r = {}, p = {}'.format(R_predict_positive_model, P_predict_positive_model))
plt.show()

# Plot for negative model
plt.figure()
g = sns.lmplot(x='true_behavioral_score', y='predicted_negative_model_scores', data=behavioral_scores_both_model,
               fit_reg=False, hue='language profil', legend_out=True, legend=True)
sns.regplot(x='true_behavioral_score', y='predicted_negative_model_scores', data=behavioral_scores_both_model,
            scatter=False, ax=g.axes[0, 0], line_kws={'color': 'b'})
plt.title('Predicted behavioral score versus true behavioral score \n in the negative edges model \n'
          'r = {}, p = {}'.format(R_predict_negative_model, P_predict_negative_model))
plt.show()



from plotting import display
save_plot_directory = '/media/db242421/db242421_data/ConPagnon_data/CPM'
# Plot the negative and positive edges on a glass brain
with PdfPages(os.path.join(save_plot_directory, kind + '_LG_LesionSize_CPM_correlation_selelection_of_predictor.pdf')) \
        as pdf:
    # Plot regression line for both model

    # Plot for positive model
    plt.figure()
    g = sns.lmplot(x='true_behavioral_score', y='predicted_positive_model_scores', data=behavioral_scores_both_model,
                   fit_reg=False, hue='language profil', legend_out=True, legend=True)
    sns.regplot(x='true_behavioral_score', y='predicted_positive_model_scores', data=behavioral_scores_both_model,
                scatter=False, ax=g.axes[0, 0], line_kws={'color': 'firebrick'})
    plt.title('Predicted behavioral score versus true behavioral score \n in the positive edges model \n'
              'r = {}, p = {}'.format(R_predict_positive_model, P_predict_positive_model))
    pdf.savefig(bbox_inches='tight')
    plt.show()

    # Plot for negative model
    plt.figure()
    g = sns.lmplot(x='true_behavioral_score', y='predicted_negative_model_scores', data=behavioral_scores_both_model,
                   fit_reg=False, hue='language profil', legend_out=True, legend=True)
    sns.regplot(x='true_behavioral_score', y='predicted_negative_model_scores', data=behavioral_scores_both_model,
                scatter=False, ax=g.axes[0, 0], line_kws={'color': 'b'})
    plt.title('Predicted behavioral score versus true behavioral score \n in the negative edges model \n'
              'r = {}, p = {}'.format(R_predict_negative_model, P_predict_negative_model))
    pdf.savefig(bbox_inches='tight')
    plt.show()


    # plot glass brain for selected positive edges
    plt.figure()
    plot_connectome(adjacency_matrix=positive_edges_matrix, node_coords=atlas_nodes, node_color=labels_colors,
                    edge_cmap='Reds', title='Edges with positive correlation to language score')
    pdf.savefig(bbox_inches='tight')
    plt.show()

    # plot glass brain for selected negative edges
    plt.figure()
    plot_connectome(adjacency_matrix=negatives_edges_matrix, node_coords=atlas_nodes, node_color=labels_colors,
                    edge_cmap='Blues', title='Edges with negative correlation to language score')
    pdf.savefig(bbox_inches='tight')
    plt.show()

    # plot positive model matrix
    plt.figure()
    display.plot_matrix(matrix=positive_edges_matrix, labels_colors=labels_colors, mpart='all',
                        colormap='Reds', horizontal_labels=labels_regions, vertical_labels=labels_regions,
                        title='Edges with positive correlation to behavior', linecolor='black')
    pdf.savefig(bbox_inches='tight')
    plt.show()

    # plot negative model matrix
    plt.figure()
    display.plot_matrix(matrix=negatives_edges_matrix, labels_colors=labels_colors, mpart='all',
                        colormap='Blues', horizontal_labels=labels_regions, vertical_labels=labels_regions,
                        title='Edges with negative correlation to behavior', linecolor='black')
    pdf.savefig(bbox_inches='tight')
    plt.show()


    # For the positive edges model
    positive_edges_position = np.where(np.tril(positive_edges_matrix) == 1)
    number_of_couple_region = len(positive_edges_position[0])
    for n_couple in range(number_of_couple_region):
        # list of connectivity coefficient of the current couple accross patients
        rois_couple_connectivity = []
        for n_patient in range(patients_connectivity_matrices.shape[0]):
            rois_couple_connectivity.append(patients_connectivity_matrices[n_patient,
                                            positive_edges_position[0][n_couple],
                                            positive_edges_position[1][n_couple]])

        rois_couple_connectivity = np.array(rois_couple_connectivity)
        # Construct a pandas dataframe to plot with seaborn
        couple_connectivity_dataframe = pd.DataFrame(
            data={'{} - {}'.format(labels_regions[positive_edges_position[0][n_couple]],
                                   labels_regions[positive_edges_position[1][n_couple]]): rois_couple_connectivity,
                  'true behavioral score': np.array(behavioral_scores),
                  'language profil': regression_data_file['langage_clinique']
                  }, index=behavioral_scores.index)
        plt.figure()
        g = sns.lmplot(x='true behavioral score',
                       y='{} - {}'.format(labels_regions[positive_edges_position[0][n_couple]],
                                   labels_regions[positive_edges_position[1][n_couple]]),
                       data=couple_connectivity_dataframe,
                       fit_reg=False, hue='language profil', legend_out=True, legend=True)
        sns.regplot(x='true behavioral score',
                    y='{} - {}'.format(labels_regions[positive_edges_position[0][n_couple]],
                                   labels_regions[positive_edges_position[1][n_couple]]),
                    data=couple_connectivity_dataframe,
                    scatter=False, ax=g.axes[0, 0], line_kws={'color': 'firebrick'})
        pdf.savefig()
        plt.show()

    # For the negative edges model
    negative_edges_position = np.where(np.tril(negatives_edges_matrix) == 1)
    number_of_couple_region = len(negative_edges_position[0])
    for n_couple in range(number_of_couple_region):
        # list of connectivity coefficient of the current couple accross patients
        rois_couple_connectivity = []
        for n_patient in range(patients_connectivity_matrices.shape[0]):
            rois_couple_connectivity.append(patients_connectivity_matrices[n_patient,
                                                                           negative_edges_position[0][n_couple],
                                                                           negative_edges_position[1][n_couple]])

        rois_couple_connectivity = np.array(rois_couple_connectivity)
        # Construct a pandas dataframe to plot with seaborn
        couple_connectivity_dataframe = pd.DataFrame(
            data={'{} - {}'.format(labels_regions[negative_edges_position[0][n_couple]],
                                   labels_regions[negative_edges_position[1][n_couple]]): rois_couple_connectivity,
                  'true behavioral score': np.array(behavioral_scores),
                  'language profil': regression_data_file['langage_clinique']
                  }, index=behavioral_scores.index)
        plt.figure()
        g = sns.lmplot(x='true behavioral score',
                       y='{} - {}'.format(labels_regions[negative_edges_position[0][n_couple]],
                                          labels_regions[negative_edges_position[1][n_couple]]),
                       data=couple_connectivity_dataframe,
                       fit_reg=False, hue='language profil', legend_out=True, legend=True)
        sns.regplot(x='true behavioral score',
                    y='{} - {}'.format(labels_regions[negative_edges_position[0][n_couple]],
                                       labels_regions[negative_edges_position[1][n_couple]]),
                    data=couple_connectivity_dataframe,
                    scatter=False, ax=g.axes[0, 0], line_kws={'color': 'b'})
        pdf.savefig()
        plt.show()


