#!/usr/bin/env python3

import argparse
from prims import Lit, Clause, Node
from collections import namedtuple, defaultdict
import bisect
import sys

litmap_name="litmap" # name of file that stores mapping between literals and literals x min_bnd x max_bnd
NUM_LITS = 10

animation = "|/-\\"

def normalize_score(N, l, mode='int'):
    if mode == 'int':
        assert N <= max(l)
        incr = float(max(l))/N
        boundaries = [None]*N
        for i in range(N):
            boundaries[i] = incr*(i+1)

        return [bisect.bisect_left(boundaries, li) for li in l]
    elif mode == 'float':
        assert N <= max(l)
        factor = float(max(l))/N
        return [li/factor for li in l]
    else:
        raise RuntimeError("Unknown option: {}".format(mode))

def processed_form(clause, litmap):
    '''
    Normalizes a clause using the litmap file produces with cnf
    '''
    newlits = [litmap[l].lit for l in clause._literals]
    # the smallest bound is the clauses' minimum
    min_bnd = min([litmap[l].min_bnd for l in clause._literals])
    # the largest bound is the clauses' maximum
    max_bnd = max([litmap[l].max_bnd for l in clause._literals])
    return Clause(newlits), (min_bnd, max_bnd)

def write_data(output, litmap, clauses, scores):
    output.write("@RELATION BMC\n\n")
    for l in range(NUM_LITS):
        output.write("@ATTRIBUTE lit{} NUMERIC\n".format(l))
    output.write("@ATTRIBUTE csize NUMERIC\n")
    output.write("@ATTRIBUTE min_bnd NUMERIC\n")
    output.write("@ATTRIBUTE max_bnd NUMERIC\n")
    output.write("@ATTRIBUTE score REAL\n\n")
    output.write("@DATA\n")
    for c in clauses:
        if c not in scores:
            # couldn't trace it to the empty clause but showed up in trace file anyway
            # use as a bad example
            scores[c] = 0

        if c == Clause([]):
            # it's the empty clause!
            # got a great score, but can't learn much from it :P
            continue

        score = scores[c]
        processed_clause, bounds = processed_form(c, litmap)
        min_bnd, max_bnd = bounds
        features = processed_clause.feature_form(NUM_LITS)
        features += [min_bnd, max_bnd]
        features = [str(f) for f in features]
        output.write(", ".join(features) + ", " + str(score) + "\n")

def read_litmap():
    litmap = {}
    litinfo = namedtuple("litinfo", "lit min_bnd max_bnd")
    with open(litmap_name) as f:
        lines = f.read()
        f.close()

    for line in lines.split("\n"):
        if len(line) < 2:
            continue
        in_lit, out_lit, min_bnd, max_bnd = line.split()
        li = litinfo(Lit(int(out_lit)), int(min_bnd), int(max_bnd))
        litmap[Lit(int(in_lit))] = li

        # kind of wasteful but adding negations as separate pair
        negli = litinfo(Lit(-int(out_lit)), int(min_bnd), int(max_bnd))
        litmap[-Lit(int(in_lit))] = negli

    return litmap

def read_trace(trace):
    marker = ' 0 '
    clausemap = {}
    # Not using clausecnt for now
    # clausecnt = defaultdict(int) # keeps track of times it appears in resolution proof
    learned_clauses = []
    emptyclausenode = None
    num_lits = 0

    tidx = 0
    lines = trace.split('\n')
    total_lines = float(len(lines))
    for line in lines:
        # update screen progress
        if tidx % 1000 == 0:
            sys.stdout.write("\r" + "%.1f%% processed "%(100*tidx/total_lines))
            sys.stdout.flush()
        tidx += 1
        # end screen progress

        if len(line.strip()) < 2:
            continue
        s1 = line.find(' ')
        _id = int(line[:s1])
        line = line[s1:]
        z1 = line.find(marker)
        z2 = line[z1+len(marker):].find(marker)
        rlits = line[:z1].split()
        resolvent = Clause([Lit(int(rl)) for rl in rlits])
        # clausecnt[resolvent] += 1
        if ' 0 0' not in line:
            parent_ids = [int(i) for i in line[z1+1:z2].split()]
            parent_ids = list(filter(lambda x: x != 0, parent_ids))
            node_parents = tuple([clausemap[i] for i in parent_ids])
            # for p in parents:
                # clausecnt[p] += 1
                # Removing for performance reasons
                # assert p in clause2node, "Expecting parents to have already been processed"

            learned_clauses.append(resolvent)

            # add resolvent if needed
            if _id not in clausemap:
                clausemap[_id] = Node(resolvent, node_parents, [])

            for n in node_parents:
                n.add_child(clausemap[_id])

            if resolvent == Clause([]):
                emptyclausenode = clausemap[_id]
        else:
            # this is a leaf
            if _id not in clausemap:
                clausemap[_id] = Node(resolvent, [], [])

    all_clauses = set(c.data for c in clausemap.values())

    assert emptyclausenode is not None

    # new line after progress update
    print("")
    return learned_clauses, all_clauses, emptyclausenode, {}

def read_dimacs(dimacs):
    dimacs = dimacs.split("\n")
    header = dimacs[0].split()
    num_lits = int(header[2])
    num_clauses = int(header[3])
    clauses = set()
    for line in dimacs[1:]:
        if len(line) > 2:
            lits = line.split()[:-1]
            clauses.add(Clause([Lit(int(l)) for l in lits]))

    return num_lits, num_clauses, clauses

def score_clauses(root, unused_clauses, clausecnt):
    if len(clausecnt) != 0:
        raise NotImplementedError("Not using clausecnt. Need to add that functionality if needed")

    scores = {}
    scores[root.data] = 0
    node_list = list(root.parents)

    min_score = 0

    # for progress animation
    tidx = 0
    aidx = 0

    for n in node_list:
        # progress animation
        if tidx % 10000 == 0:
            sys.stdout.write("\r" + animation[aidx % len(animation)])
            sys.stdout.flush()
            aidx += 1
        tidx += 1
        # end progress animation

        processed_children = list(filter(lambda x: x.data in scores, n.children))
        assert len(processed_children) > 0, "Should have at least one processed child"

        s = max([scores[c.data] for c in processed_children]) - 1
        scores[n.data] = s

        if s < min_score:
            min_score = s

        # only add parents that haven't already been processed
        # the maximum score is kept (which is the first one received)
        node_list += list(filter(lambda x: x.data not in scores, n.parents))

    assert len(scores) > 1000, "Just checking that scores is reasonably sized"
    bias = -min_score

    print("\nDepth of proof is {}".format(bias))

    # adjust the scores to be positive
    for k, v in scores.items():
        # progress animation
        if tidx % 1000 == 0:
            sys.stdout.write("\r" + animation[aidx % len(animation)])
            sys.stdout.flush()
            aidx += 1
        tidx += 1
        # end progress animation

        # add the bias to make positive and the number of times it appears in the proof
        # hoping that clauses used more often are more useful
        # scores[k] = v + bias + clausecnt[k]
        scores[k] = v + bias

    # give all the original clauses a score of 0
    # this might overwrite a previous score
    for c in unused_clauses:
        # progress animation
        if tidx % 1000 == 0:
            sys.stdout.write("\r" + animation[aidx % len(animation)])
            sys.stdout.flush()
            aidx += 1
        tidx += 1
        # end progress animation
        scores[c] = 0

    return scores

def binary_labels(unused_clauses, learned_clauses):
    labels = {}
    for c in unused_clauses:
        labels[c] = 0
    for c in learned_clauses:
        labels[c] = 1
    return labels

# deprecating
# def read_picolog(log):
#     reason = namedtuple("reason", "lit level clause")
#     corig = "c original "
#     cassig = "c assign "
#     cassig_at = " at level "
#     cassig_by = " by "
#     cconfl = "c conflict "
#     clearn = "c learned "
#     clvl = "c new level "
#     cbt  = "c back to level "
#     end_clause = " 0\n" # assuming at end of line
#     clauses = []
#     reasons = []
#     learned_clauses = []
#     lit2lvl = {}

#     conflict = None # only process one conflict at a time
#     tconfl = 0

#     dl = 0
#     llidx = 0 # last level idx
#     idxmap = {0: 0} # need to keep track of previous llidx's

#     matchlearned = 0
#     matchorig = 0
#     numconflicts = 0
#     derived_empty = False

#     for line in log.split("\n"):
#         if corig in line:
#             cstr = line[line.find(corig)+len(corig):line.find(end_clause)]
#             literals = [Lit(int(i)) for i in cstr.split()]
#             clauses.append(Clause(literals))
#         elif cassig in line and cassig_by in line:
#             lit = Lit(int(line[line.find(cassig)+len(cassig):line.find(cassig_at)]))
#             level = int(line[line.find(cassig_at)+len(cassig_at):line.find(cassig_by)])
#             cstr = line[line.find(cassig_by)+len(cassig_by):line.find(end_clause)]
#             literals = [Lit(int(i)) for i in cstr.split()]
#             reasons.append(reason(lit, level, Clause(literals)))
#             lit2lvl[lit] = level
#             lit2lvl[-lit] = level
#         elif cconfl in line:
#             cstr = line[line.find(cconfl)+len(cconfl):line.find(end_clause)]
#             literals = [Lit(int(i)) for i in cstr.split()]
#             conflict = Clause(literals)
#             tconfl = 2
#             numconflicts += 1
#         elif clearn in line and tconfl == 1:
#             cstr = line[line.find(clearn)+len(clearn):line.find(end_clause)]
#             literals = [Lit(int(i)) for i in cstr.split()]
#             lc = Clause(literals)
#             genclause = conflict

#             trail = []
#             resolved_lits = []
#             for r in reversed(reasons):

#                 rlits = genclause.resolution_lits(r.clause)
#                 if r.lit not in rlits and -r.lit not in rlits:
#                     continue

#                 genclause = genclause.resolve(r.clause, r.lit)
#                 # don't need to score empty clause
#                 if genclause != Clause([]):
#                     trail.append(genclause)
#                     resolved_lits.append(r.lit)
#                 else:
#                     derived_empty = True
#                 if genclause == lc:
#                     matchlearned += 1
#                     break
#                 if genclause in clauses:
#                     matchorig += 1
#                     break
#                 # if len(list(filter(lambda l: False if l not in lit2lvl else lit2lvl[l] == dl, genclause._literals))) == 1:
#                 #     print("breaking because last literal at dl = {}".format(dl))
#                 #     break

#             # debugging
#             # print("lc", lc)
#             # print("genclause", genclause)
#             # if Clause([Lit(-522), Lit(-544)]) == lc:
#             #     for i in reversed(range(len(trail))):
#             #         print("l", resolved_lits[i], "t", trail[i])
#             # end debugging

#             learned_clauses += trail
#         elif clvl in line:
#             idxmap[dl] = len(reasons)
#             dl += 1
#             assert dl == int(line[line.find(clvl)+len(clvl):]), "dl: {}, {}".format(dl, line)
#         elif cbt in line:
#             dl = int(line[line.find(cbt)+len(cbt):])
#             if dl < 0:
#                 break

#             reasons = reasons[:idxmap[dl]]
#             assert all([r.level <= dl for r in reasons]), "dl: {}\n{}".format(dl, reasons)

#         if tconfl > 0:
#             tconfl -= 1

#     # pack stats
#     stats = {"matchlearned": matchlearned,
#              "matchorig": matchorig,
#              "numconflicts": numconflicts,
#              "derived_empty": derived_empty
#             }

#     return clauses, learned_clauses, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read Picosat log or tracecheck file for resolution proof data')
    parser.add_argument('input_file', metavar='<INPUT_FILE>', help='Picosat log file')
    parser.add_argument('--resproof', action="store_true", help='Parse tracecheck output resolution proof file')
    parser.add_argument('--trace', action="store_true", help='Parse SAT solvers trace file')

    args = parser.parse_args()

    input_file = args.input_file

    log = None
    with open(input_file) as f:
        log = f.read()
        f.close()

    assert log is not None

    if args.resproof or args.trace:
        litmap = read_litmap()

        learned_clauses, clauses, emptyclausenode, clausecnt = read_trace(log)

        # if args.resproof:
        #     # Check for valid resolution proof
        #     for n in clauses.values():
        #         if len(n.parents) > 0:
        #             assert len(n.parents) == 2
        #             p1, p2 = n.parents
        #             assert p1.data.can_resolve(p2.data), "Expecting to be able to resolve parents but have {}, {}".format(p1.data, p2.data)

        # score each of the clauses
        scores = score_clauses(emptyclausenode, orig_clauses, clausecnt)

        with open("data.arff", "w") as output_file:
            write_data(output_file, litmap, clauses, scores)

    else:
        clauses, learned_clauses, stats = read_picolog(log)

        print("# clauses", len(clauses))
        print("# learned_clauses", len(learned_clauses))
        for n, s in stats.items():
            print(n, s)
