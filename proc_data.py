#!/usr/bin/env python3

import argparse
from prims import Lit, Clause, Node
from collections import namedtuple, defaultdict

def read_tracecheck(resproof):
    marker = ' 0 '
    clausemap = {}
    clausecnt = defaultdict(int) # keeps track of times it appears in resolution proof
    learned_clauses = []
    clause2node = {}
    emptyclausenode = None
    for line in resproof.split('\n'):
        if len(line.strip()) < 2:
            continue
        s1 = line.find(' ')
        _id = int(line[:s1])
        line = line[s1:]
        z1 = line.find(marker)
        z2 = line[z1+len(marker):].find(marker)
        rlits = line[:z1].split()
        resolvent = Clause([Lit(int(rl)) for rl in rlits])
        clausemap[_id] = resolvent
        clausecnt[resolvent] += 1
        if ' 0 0' not in line:
            parent_ids = [int(i) for i in line[z1+1:z2].split()]
            parent_ids = list(filter(lambda x: x != 0, parent_ids))
            parents = tuple([clausemap[i] for i in parent_ids])
            for p in parents:
                clausecnt[p] += 1
                assert p in clause2node, "Expecting parents to have already been processed"

            node_parents = tuple([clause2node[p] for p in parents])
            learned_clauses.append(resolvent)

            # add resolvent if needed
            if resolvent not in clause2node:
                clause2node[resolvent] = Node(resolvent, node_parents, None)

            for n in node_parents:
                n.add_child(clause2node[resolvent])

            if resolvent == Clause([]):
                emptyclausenode = clause2node[resolvent]
        else:
            # this is a leaf
            clause2node[resolvent] = Node(resolvent, None, None)

    assert emptyclausenode is not None
    return learned_clauses, clause2node, emptyclausenode

def read_picolog(log):
    reason = namedtuple("reason", "lit level clause")
    corig = "c original "
    cassig = "c assign "
    cassig_at = " at level "
    cassig_by = " by "
    cconfl = "c conflict "
    clearn = "c learned "
    clvl = "c new level "
    cbt  = "c back to level "
    end_clause = " 0\n" # assuming at end of line
    clauses = []
    reasons = []
    learned_clauses = []
    lit2lvl = {}

    conflict = None # only process one conflict at a time
    tconfl = 0

    dl = 0
    llidx = 0 # last level idx
    idxmap = {0: 0} # need to keep track of previous llidx's

    matchlearned = 0
    matchorig = 0
    numconflicts = 0
    derived_empty = False

    for line in log.split("\n"):
        if corig in line:
            cstr = line[line.find(corig)+len(corig):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            clauses.append(Clause(literals))
        elif cassig in line and cassig_by in line:
            lit = Lit(int(line[line.find(cassig)+len(cassig):line.find(cassig_at)]))
            level = int(line[line.find(cassig_at)+len(cassig_at):line.find(cassig_by)])
            cstr = line[line.find(cassig_by)+len(cassig_by):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            reasons.append(reason(lit, level, Clause(literals)))
            lit2lvl[lit] = level
            lit2lvl[-lit] = level
        elif cconfl in line:
            cstr = line[line.find(cconfl)+len(cconfl):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            conflict = Clause(literals)
            tconfl = 2
            numconflicts += 1
        elif clearn in line and tconfl == 1:
            cstr = line[line.find(clearn)+len(clearn):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            lc = Clause(literals)
            genclause = conflict

            trail = []
            resolved_lits = []
            for r in reversed(reasons):

                rlits = genclause.resolution_lits(r.clause)
                if r.lit not in rlits and -r.lit not in rlits:
                    continue

                genclause = genclause.resolve(r.clause, r.lit)
                # don't need to score empty clause
                if genclause != Clause([]):
                    trail.append(genclause)
                    resolved_lits.append(r.lit)
                else:
                    derived_empty = True
                if genclause == lc:
                    matchlearned += 1
                    break
                if genclause in clauses:
                    matchorig += 1
                    break
                # if len(list(filter(lambda l: False if l not in lit2lvl else lit2lvl[l] == dl, genclause._literals))) == 1:
                #     print("breaking because last literal at dl = {}".format(dl))
                #     break

            # debugging
            # print("lc", lc)
            # print("genclause", genclause)
            # if Clause([Lit(-522), Lit(-544)]) == lc:
            #     for i in reversed(range(len(trail))):
            #         print("l", resolved_lits[i], "t", trail[i])
            # end debugging

            learned_clauses += trail
        elif clvl in line:
            idxmap[dl] = len(reasons)
            dl += 1
            assert dl == int(line[line.find(clvl)+len(clvl):]), "dl: {}, {}".format(dl, line)
        elif cbt in line:
            dl = int(line[line.find(cbt)+len(cbt):])
            if dl < 0:
                break

            reasons = reasons[:idxmap[dl]]
            assert all([r.level <= dl for r in reasons]), "dl: {}\n{}".format(dl, reasons)

        if tconfl > 0:
            tconfl -= 1

    # pack stats
    stats = {"matchlearned": matchlearned,
             "matchorig": matchorig,
             "numconflicts": numconflicts,
             "derived_empty": derived_empty
            }

    return clauses, learned_clauses, stats


parser = argparse.ArgumentParser(description='Read Picosat log or tracecheck file for resolution proof data')
parser.add_argument('input_file', metavar='<INPUT_FILE>', help='Picosat log file')
parser.add_argument('--tracecheck', action="store_true", help='Parse tracecheck file')

args = parser.parse_args()

input_file = args.input_file

log = None
with open(input_file) as f:
    log = f.read()
    f.close()

assert log is not None

if args.tracecheck:
    learned_clauses, clause2node, emptyclausenode = read_tracecheck(log)
    for n in clause2node.values():
        if n.parents is not None:
            assert len(n.parents) == 2
            p1, p2 = n.parents
            assert p1.data.can_resolve(p2.data), "Expecting to be able to resolve parents but have {}, {}".format(p1.data, p2.data)
else:
    clauses, learned_clauses, stats = read_picolog(log)

    print("# clauses", len(clauses))
    print("# learned_clauses", len(learned_clauses))
    for n, s in stats.items():
        print(n, s)
