#!/usr/bin/env python3

from prims import Clause, Lit
import random
from proc_data import read_trace, read_litmap
import heapq
from collections import Sequence
import scipy
from scipy.sparse import lil_matrix, coo_matrix, csr_matrix, csc_matrix
from sklearn.externals import joblib
import proc_data as pd
import argparse
import os
import numpy as np
import learning


class priqueue:
    def __init__(self):
        self._l = []

    def push(self, clause):
        heapq.heappush(self._l, clause)

    def pop(self):
        item = heapq.heappop(self._l)
        return item

    def top(self, n):
        return heapq.nsmallest(n, self._l)

    def keep(self, pc):
        idx = int(len(self._l)*pc)
        self._l = self._l[:idx]

def sample_resolvable_clause(clauses, max_iter=50):
    lits = set()
    clauses = set(clauses)
    i = 0
    while i < max_iter & len(lits) == 0:
        c = random.sample(clauses, 1)[0]
        neglits = (-l for l in c._literals)
        lits = set(filter(lambda l: len(l._clauses) > 0, neglits))

    if len(lits) == 0:
        raise RuntimeError("Never sampled a resolvable clause")

    lit = random.sample(lits, 1)[0]
    other_clause = random.sample(set(lit._clauses), 1)[0]
    return c, other_clause, lit

def generate_random_clauses(clauses, num):
    for c in clauses:
        c.register()

    sampled_clauses = list(random.sample(set(clauses), num))

    new_clauses = [None]*num
    idx = 0

    while idx < num:
        c = sampled_clauses[idx]
        neglits = (-l for l in c._literals)
        lits = set(filter(lambda l: len(l._clauses) > 0, neglits))
        if len(lits) == 0:
            try:
                c, oc, lit = sample_resolvable_clause(clauses)
            except RuntimeError:
                print("Failed to sample any resolvable clauses. Continuing anyway.")
                num -= 1
                continue
        else:
            lit = random.sample(lits, 1)[0]
            oc = random.sample(set(lit._clauses), 1)[0]

        new_clauses[idx] = c.resolve(oc, lit)

        idx += 1

    new_clauses = filter(lambda x: x is not None, new_clauses)

    return set(new_clauses)


# def gen_clauses(model, clauses, num, num_lits, model_processor, BURN=1000):
#     literals = set(Lit(l) for l in range(1, num_lits+1))
#     cmap = {}
#     for c in clauses:
#         # get processed forms of clauses
#         proc_clause, bounds = processed_form(c)
#         cmap[proc_clause] = (c, bounds)

#     for pc in cmap:
#         # register all the processed forms
#         # only doing clause resolution on normal forms
#         # then scoring it for each bound
#         pc.register()

#     # BURN IN Phase for generating random clauses
#     # might need to change this so it's not resolving on so many clauses
#     # of the same literal
#     # alternatively could just sweep through the literals once and add
#     # all of it's resolvents
#     b_cl = 0
#     burn_clauses = priqueue()
#     for l in random.sample(literals, 2*BURN):
#         for c1, c2 in l.get_resolvable_clauses():
#             cr = c1.resolve(c2, l)
#             # max score over any time
#             max_score = max((model.predict(model_processor(c, bounds)) for c, bounds in cmap[cr]))
#             burn_clauses.push((max_score, cr))
#             b_cl += 1
#             if b_cl >= BURN:
#                 break

#     gen_clauses = priqueue()

#     # keep the top twenty percent from burn_clauses
#     for score, bc in burn_clauses.top(int(.2*BURN)):
#         bc.register()
#         gen_clauses.push((score, bc))

#     cache_scores = {}
#     num_clauses = 0
#     while num_clauses < num:
#         # loop over top 20 clauses and add their resolvents if scores increase
#         # for c in
#         pass

def gen_model_processor(litmap, num_lits, ohl=False):
    processed_form = pd.processed_form
    if ohl:
        def ohl_processor(clauses):
            if not isinstance(clauses, Sequence):
                clauses = [clauses]
            X = lil_matrix(len(clauses), num_lits + 2)
            idx = 0
            for c in clauses:
                proc_clause, bounds = processed_form(c, litmap)
                for l in proc_clause._literals:
                    i = l._i
                    if i < 0:
                        X[idx, -i] = -1
                    else:
                        X[idx, i] = 1

                X[idx, -2:] = np.array(list(bounds))
                idx += 1
            return X
        return ohl_processor
    else:
        def feat_form_processor(clauses):
            if not isinstance(clauses, Sequence):
                clauses = [clauses]
            X = np.zeros((len(clauses), learning.NUM_FEAT_LITS + 3))
            idx = 0
            for c in clauses:
                proc_clause, bounds = processed_form(c, litmap)
                features = proc_clause.feature_form(learning.NUM_FEAT_LITS)
                features += list(bounds)
                X[idx, :] = np.array(features)
                idx += 1
            return X
        return feat_form_processor


def gen_resolvents(model, clauses, bound, model_processor, num, litmap, BURN_ITERS=100):
    processed_form = pd.processed_form
    clause_cache_r = {}
    literals = set()
    gen_clauses = priqueue()

    for c in clauses:
        proc_clause, bounds = processed_form(c, litmap)
        if bounds[0] >= bound - 2:
            # clause_cache[c] = model_processor(proc_clause, *bounds)
            clause_cache_r[proc_clause, bounds[0], bounds[1]] = c
            # all original clauses should have 0 score
            c.add_score(0)
            gen_clauses.push(c)
            c.register()
            for l in c._literals:
                literals.add(l.absl())

    rlits = random.sample(literals, BURN_ITERS)
    burn_clauses = []
    feats = []
    for rl in rlits:
        for c1, c2 in rl.get_resolvable_clauses():
            cr = c1.resolve(c2, rl, check=True)
            if not cr.taut:
                cr.register()
                burn_clauses.append(cr)
                feats.append(cr)

    gen_scores = model.predict(model_processor(feats))
    for gs, cr in zip(gen_scores, burn_clauses):
        cr.add_score(gs)
        gen_clauses.push(cr)

    del burn_clauses

    print("Maximum score from burn_clauses was {}".format(max(gen_scores)))

    n = 0
    while n < num:
        for c in gen_clauses.top(30):
            s = c.score
            c2scores = []
            feats = []
            for c2, l in c.get_resol_clauses():
                cr = c.resolve(c2, l, check=True)
                if not cr.taut:
                    c2scores.append(c2.score)
                    feats.append(cr)
            gen_scores = model.predict(model_processor(feats))
            for c2s, gs, cr in zip(c2scores, gen_scores, feats):
                max_prev = max(s, c2s)
                if gs >= max_prev:
                    cr.add_score(gs)
                    gen_clauses.push(cr)
                    n += 1
    return gen_clauses


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Generate and score clauses')
    parser.add_argument('model_file', metavar='<MODEL_FILE>', help='Pickled model file')
    parser.add_argument('dimacs_file', metavar='<DIMACS_FILE>', help='DIMACS file to read original clauses')
    parser.add_argument('output_file', metavar='<OUTPUT_FILE>', help='Where to write new clauses')
    parser.add_argument('--ohl', action='store_true', help='Use one-hot literals as features')

    args = parser.parse_args()
    model_file = args.model_file
    dimacs_file = args.dimacs_file
    output_file = args.output_file
    ohl = args.ohl

    print("Load model")
    model = joblib.load(model_file)

    print("Reading litmap")
    litmap, bound = pd.read_litmap()

    f2 = open(dimacs_file)
    dimacs = f2.read()
    f2.close()

    print("Reading dimacs file")
    num_lits, num_clauses, orig_clauses = pd.read_dimacs(dimacs)

    mp = gen_model_processor(litmap, num_lits, ohl=ohl)

    NUM = 20000
    gen_clauses = gen_resolvents(model, orig_clauses, bound, mp, NUM, litmap, BURN_ITERS=1000)

    pc = 0.1
    new_clauses = gen_clauses.top(int(pc*NUM))
    num_new_clauses = len(new_clauses)

    print("Writing top {}% ({}) clauses to file".format(100*pc, num_new_clauses))
    max_score = 0
    min_score = 100000

    with open(output_file, 'w') as of:
        dlines = dimacs.split("\n")
        header = dlines[0].split()
        header[-1] = str(int(header[-1]) + num_new_clauses)
        of.write(" ".join(header) + "\n")

        for line in dlines[1:]:
            of.write(line + str("\n"))

        # write top {pc}%
        for c in new_clauses:
            if c.score > max_score:
                max_score = c.score
            if c.score < min_score:
                min_score = c.score
            of.write(str(c) + " 0\n")
        of.close()

    print("Max added clause score = {}".format(max_score))
    print("Min added clause score = {}".format(min_score))
