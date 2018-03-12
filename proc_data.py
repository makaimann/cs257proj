#!/usr/bin/env python3

import argparse
from prims import Lit, Clause
from collections import namedtuple

def read_proof(log):
    for line in log.split("\n"):
        if line[-3:] == "0 0":
            pass
        # TODO finish this function

def read_picolog(log):
    reason = namedtuple("reason", "lit level clause")
    corig = "c original "
    cassig = "c assign "
    cassig_at = " at level "
    cassig_by = " by "
    cconfl = "c conflict "
    clearn = "c learned "
    end_clause = " 0\n" # assuming at end of line
    clauses = []
    reasons = []
    learned_clauses = []

    conflict = None # only process one conflict at a time
    tconfl = 0

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
        elif cconfl in line:
            cstr = line[line.find(cconfl)+len(cconfl):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            conflict = Clause(literals)
            tconfl = 2
        elif clearn in line and tconfl == 1:
            cstr = line[line.find(clearn)+len(clearn):line.find(end_clause)]
            literals = [Lit(int(i)) for i in cstr.split()]
            lc = Clause(literals)
            genclause = conflict

            trail = []
            for r in reversed(reasons):
                if not genclause.can_resolve(r.clause):
                    continue

                genclause = genclause.resolve(r.clause, r.lit)
                # don't need to score empty clause
                if genclause != Clause([]):
                    trail.append(genclause)
                if genclause == lc:
                    break

            learned_clauses += trail

        if tconfl > 0:
            tconfl -= 1

    return clauses, learned_clauses


parser = argparse.ArgumentParser(description='Read Picosat log file for resolution proof data')
parser.add_argument('input_file', metavar='<INPUT_FILE>', help='Picosat log file')

args = parser.parse_args()

input_file = args.input_file

log = None
with open(input_file) as f:
    log = f.read()
    f.close()

assert log is not None

clauses, learned_clauses = read_picolog(log)

print("clauses", clauses)
print("learned_clauses", learned_clauses)
