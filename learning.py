#!/usr/bin/env python3

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn import svm
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.feature_selection import VarianceThreshold
from sklearn.externals import joblib
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
import scipy
from scipy.sparse import lil_matrix, coo_matrix, csr_matrix, csc_matrix
import proc_data as pd
from prims import Clause, Lit
import argparse

NUM_FEAT_LITS = 10

def calculate_error(yp, yt):
    assert len(yp) == len(yt)
    N = float(len(yp))
    return np.sum(np.abs(yp - yt))/N

def calculate_misclassified(yp, yt):
    assert len(yp) == len(yt)
    N = len(yp)
    return (np.sum(yp != yt)/N)*100

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read Picosat log or tracecheck file for resolution proof data')
    parser.add_argument('input_file', metavar='<INPUT_FILE>', help='Proof or trace file')
    parser.add_argument('dimacs_file', metavar='<DIMACS_FILE>', help='DIMACS file to read original clauses')
    parser.add_argument('model_file', metavar='<MODEL_FILE>', help='Name of file to write model to')
    parser.add_argument('algo', metavar='<ML ALGO>', help='Which ML algorithm to use. <SVC, SVR, KNR, MLPC, MLPR, GP, LR, ABC, RFC>.\nNote: Does not set hyper parameters')
    parser.add_argument('--ohl', action='store_true', help='Use one-hot literals as features')

    args = parser.parse_args()
    input_file = args.input_file
    dimacs_file = args.dimacs_file
    model_filename = args.model_file
    algo = args.algo

    assert algo in {'SVC', 'SVR', 'KNR', 'MLPC', 'MLPR', 'GP', 'LR', 'ABC', 'RFC'}

    print("Reading litmap")
    litmap, bound = pd.read_litmap()

    f2 = open(dimacs_file)
    dimacs = f2.read()
    f2.close()

    print("Reading dimacs file")
    num_lits, num_clauses, orig_clauses = pd.read_dimacs(dimacs)

    f = open(input_file)
    trace = f.read()
    f.close()

    print("Reading trace file")
    learned_clauses, clauses, emptyclausenode, clausecnt = pd.read_trace(trace)
    print("# Original Clauses = {}".format(len(orig_clauses)))
    print("# Learned Clauses = {}".format(len(learned_clauses)))

    unused_clauses = orig_clauses - set(learned_clauses)

    # print("Generating binary labels")
    # scores = pd.binary_labels(orig_clauses, learned_clauses)
    print("Generating scores")
    scores = pd.score_clauses(emptyclausenode, unused_clauses, clausecnt)

    # NRC = 3000
    # print("Generating {} random clauses and giving low scores".format(NRC))
    # new_clauses = generate_random_clauses(clauses, NRC)
    # new_clauses = new_clauses - set(learned_clauses) - set(orig_clauses)
    # print("Retaining {} of the generated clauses".format(len(new_clauses)))
    # for nc in new_clauses:
    #     scores[nc] = 0

    training_clauses = clauses.union(unused_clauses)

    if args.ohl:
        print("Processing data with one-hot literal encoding")
        X = lil_matrix((len(training_clauses) - 1, num_lits + 2))
        y = np.zeros(len(training_clauses) - 1)
        idx = 0
        for c in training_clauses:
            if c == Clause([]):
                # don't use the empty clause
                continue
            if c not in scores:
                # if not used, score := 0
                scores[c] = 0
            proc_clause, bounds = pd.processed_form(c, litmap)
            for l in proc_clause._literals:
                i = l._i
                if i < 0:
                    X[idx, -i] = -1
                else:
                    X[idx, i] = 1
            X[idx, -2:] = np.array(list(bounds))
            y[idx] = scores[c]
            idx += 1
            X = X.tocsr()
    else:
        print("Processing data with NUM_FEAT_LITS={}".format(NUM_FEAT_LITS))
        # -1 because not using the empty clause which is in clauses
        X = np.zeros((len(training_clauses) - 1, NUM_FEAT_LITS + 3))
        y = np.zeros(len(training_clauses) - 1)
        idx = 0
        for c in training_clauses:
            if c == Clause([]):
                # don't use the empty clause
                continue
            if c not in scores:
                # if wasn't used, then zero
                scores[c] = 0
            proc_clause, bounds = pd.processed_form(c, litmap)
            features = proc_clause.feature_form(NUM_FEAT_LITS)
            features += list(bounds)
            X[idx, :] = np.array(features)
            y[idx] = scores[c]
            idx += 1

        # sel = VarianceThreshold(threshold=(.8 * (1 - .8)))
        # X = sel.fit_transform(X)
        # Later, use: sel.transform(raw_instance)

        # scale the data
        scaler = StandardScaler()
        # X = scaler.fit_transform(X)
        # Later, use: scaler.transform(raw_instance)

    N = 8
    print("Normalizing scores to have {} values".format(N))
    y = pd.normalize_score(N, y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.10, random_state=42)

    if algo == 'SVC':
        print("Fitting a SVC")
        model = svm.SVC(kernel='rbf', gamma='scale', C=2.0)
    elif algo == 'SVR':
        print("Fitting a SVR")
        model = svm.SVR(kernel='rbf', gamma='scale', C=2.0)
    elif algo == 'KNR':
        print("Fitting a KNR")
        model = KNeighborsRegressor(n_neighbors=10)
    elif algo == 'MLPC':
        print("Fitting a MLP Classifier")
        model = MLPClassifier(solver='sgd', alpha=1e-5,
                              hidden_layer_sizes=(15, 15, 10, 10, 5, 2), random_state=1)
    elif algo == 'MLPR':
        print("Fitting a MLPR")
        model = MLPRegressor(solver='sgd', alpha=1e-5,
                             hidden_layer_sizes=(15, 15, 10, 10, 5, 2), random_state=1)
    elif algo == 'GP':
        print("Fitting a GP")
        model = GaussianProcessRegressor()
    elif algo == 'LR':
        print("Fitting a LogisticRegressor")
        model = LogisticRegression(C=1e5)
    elif algo == 'ABC':
        print("Fitting Ada Boost Classifier")
        model = AdaBoostClassifier(n_estimators=200)
    elif algo == 'RFC':
        print('Fitting RandomForestclassifier')
        model = RandomForestClassifier(n_estimators=100)
    else:
        raise RuntimeError('Unhandled algo={}'.format(algo))

    model.fit(X_train, y_train)
    joblib.dump(model, model_filename)

    # yp = model.predict(scaler.transform(X_test))
    yp = model.predict(X_test)

    if algo in {'SVC', 'MLPC', 'LR', 'ABC', 'RFC'}:
        print("Classification Error = {}%".format(calculate_misclassified(yp, y_test)))
    else:
        print("Error = {}".format(calculate_error(yp, y_test)))

    print("len(yp)", len(yp))
    print("len(y_test)", len(y_test))

    # for i in range(len(yp)):
    #     print(yp[i], y_test[i])
    # print(y_train[5000:5020])
    # print(X_train[5000:5020,:])

    # # random features
    # test = np.matrix([[1, -400, 525, 3000, 622, 0, 0, 0, 0, 0, 5, 2, 2], \
    #                   [-6292, -450, 5205, -6000, -622, 200, 540, -81, 56, 256, 14, 1, 2], \
    #                   [-14, -50, 1005, -60, 27640, 11234, 0, 0, 0, 0, 6, 0, 1], \
    #                   [-14, -50, 1005, -60, 27640, 11234, 200, 0, 0, 0, 7, 0, 1], \
    #                   [-14, -50, 1005, -60, 27640, 11234, 200, 45, 0, 0, 8, 0, 1], \
    #                   [-14, -50, 1005, -60, 27640, 11234, 200, 45, -500, 0, 9, 0, 1], \
    #                   [-14, -50, 1005, -60, 27640, 11234, 200, 45, -500, 2045, 15, 0, 1]])

    # print(model.predict(scaler.transform(test)))

    # print(model.predict(X_train[5000:5020, :]))
