#!/usr/bin/env python3

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import train_test_split
from sklearn import svm
from sklearn.neural_network import MLPClassifier
import proc_data as pd
from prims import Clause, Lit
import argparse

NUM_LITS = 10

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read Picosat log or tracecheck file for resolution proof data')
    parser.add_argument('input_file', metavar='<INPUT_FILE>', help='Picosat log file')
    parser.add_argument('--resproof', action="store_true", help='Parse tracecheck output resolution proof file')
    parser.add_argument('--trace', action="store_true", help='Parse SAT solvers trace file')

    args = parser.parse_args()
    input_file = args.input_file

    if args.resproof or args.trace:

        print("Reading litmap")
        litmap = pd.read_litmap()

        f = open(input_file)
        trace = f.read()
        f.close()

        print("Reading trace file")
        learned_clauses, clause2node, orig_clauses, emptyclausenode, clausecnt = pd.read_trace(trace)
        print("# Original Clauses = {}".format(len(orig_clauses)))
        print("# Learned Clauses = {}".format(len(orig_clauses)))

        # print("Generating binary labels")
        # labels = pd.binary_labels(orig_clauses, learned_clauses)
        print("Generating scores")
        scores = pd.score_clauses(emptyclausenode, orig_clauses, clausecnt)

        print("Processing data")
        # -1 because not using the empty clause which is in clause2node
        X_train = np.zeros((len(clause2node) - 1, NUM_LITS + 3))
        y_train = np.zeros(len(clause2node) - 1)
        idx = 0
        for c in clause2node:
            if c == Clause([]):
                # don't use the empty clause
                continue
            if c not in scores:
                # if wasn't used, then zero
                scores[c] = 0
            proc_clause, bounds = pd.processed_form(c, litmap)
            features = proc_clause.feature_form(NUM_LITS)
            features += list(bounds)
            X_train[idx, :] = np.array(features)
            y_train[idx] = scores[c]
            idx += 1

        # scale the data
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        # Later, use: scaler.transform(raw_instance)

        N = 10
        print("Normalizing scores to have {} values".format(N))
        y_train = pd.normalize_score(N, y_train)

        # X_train, X_test, y_train, y_test = train_test_split(
        #     X_train, y_train, test_size=0.33, random_state=42)

        print("Fitting a SVR")
        model = svm.SVR(kernel='rbf')

        # print("Fitting a MLP")
        # model = MLPClassifier(solver='lbfgs', alpha=1e-5,
        #                       hidden_layer_sizes=(5, 2), random_state=1)

        model.fit(X_train, y_train)

        print(y_train[5000:5020])
        print(X_train[5000:5020,:])

        # random features
        test = np.matrix([[1, -400, 525, 3000, 622, 0, 0, 0, 0, 0, 5, 2, 2], \
                          [-6292, -450, 5205, -6000, -622, 200, 540, -81, 56, 256, 14, 1, 2], \
                          [-14, -50, 1005, -60, 27640, 11234, 0, 0, 0, 0, 6, 0, 1], \
                          [-14, -50, 1005, -60, 27640, 11234, 200, 0, 0, 0, 7, 0, 1], \
                          [-14, -50, 1005, -60, 27640, 11234, 200, 45, 0, 0, 8, 0, 1], \
                          [-14, -50, 1005, -60, 27640, 11234, 200, 45, -500, 0, 9, 0, 1], \
                          [-14, -50, 1005, -60, 27640, 11234, 200, 45, -500, 2045, 15, 0, 1]])

        print(model.predict(scaler.transform(test)))

        print(model.predict(X_train[5000:5020, :]))
