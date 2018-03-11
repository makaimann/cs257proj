#!/usr/bin/env python3

import argparse
from normalform import normal_form

# FUNCTIONS

def _fix_literal(lit):
    assert isinstance(lit, str)
    # weird -0 notation
    if lit == '-0':
        return -1

    lit = int(lit)
    if lit >= 0:
        lit += 1
    else:
        lit -= 1

    return lit


def read_trans(trans):

    newlit = "newLiteral("
    point = " => "
    newclause = "clause: "

    node2literal = {}
    normnode2literal = {}
    literal2node = {}
    clauses = []
    for line in trans.split("\n"):
        if "BITVECTOR_EAGER_ATOM" in line:
            line = line.replace("(BITVECTOR_EAGER_ATOM ", "")
            idx = line.rfind(")")
            # remove extra parenthesis
            line = line[:idx] + line[idx+1:]

        if newlit in line and point in line:
            node = line[line.find(newlit)+len(newlit):line.find(point)]
            lit = line[line.find(point)+len(point):]
            norm_node, unroll = normal_form(node)
            lit = _fix_literal(lit)
            node2literal[node] = lit
            if norm_node not in normnode2literal:
                # Note: This might not be the first literal for that signal, but it will at least be consistent
                # In the future, consider ensuring it's the first one
                normnode2literal[norm_node] = lit
            literal2node[lit] = {"norm_node": norm_node,
                                 "node": node,
                                 "unroll": unroll}

        elif newclause in line:
            clause = line[line.find(newclause)+len(newclause):]
            clause = clause.replace(";", "0")
            clause = clause.replace("~", '-')
            clauses.append(' '.join(clause.split()) + " 0")

    numlits = len(node2literal)
    numclauses = len(clauses)

    return node2literal, normnode2literal, literal2node

def read_clauses(trans):
    addclause = "Add clause clause: "

    numlits = 0
    for line in trans.split("\n"):
        if addclause not in line:
            continue
        clause = line[line.find(addclause)+len(addclause):]
        clause = clause.replace(";", "")
        clause = clause.replace("~", "-")
        proc_clause = list()

        for l in clause.split():
            lit = _fix_literal(l)
            if abs(lit) > numlits:
                numlits = abs(lit)
            proc_clause.append(lit)

        clauses.append(' '.join(str(c) for c in proc_clause) + " 0")

    numclauses = len(clauses)

    return numlits, numclauses, clauses

def read_proof(trans):
    for line in trans.split("\n"):
        if line[-3:] == "0 0":
            pass
        # TODO finish this function
# END FUNCTIONS

parser = argparse.ArgumentParser(description='Read CNF from CVC4 Output')
parser.add_argument('input_file', metavar='<INPUT_FILE>', help='The file to read containing CVC4 -d cnf-trans or --bitblast=eager -d sat::minisat (eager bitblasting is vital)')
parser.add_argument('output_file', metavar='<OUTPUT_FILE>', help='The file to write DIMACs to', default="out.dimacs")
parser.add_argument('--cnf-trans', action='store_true', dest="cnf_trans", help='Read CVC4 cnf-trans output')

args = parser.parse_args()

input_file = args.input_file
output_file = args.output_file
cnf_trans = args.cnf_trans

with open(input_file) as f:
    trans = f.read()
    f.close()

if cnf_trans:

    _, normnode2literal, _ = read_trans(trans)

    with open(output_file, "w") as f:
        for n, l in normnode2literal.items():
            f.write(n + ": " + str(l))
            f.write("\n")

        f.close()

else:
    numlits, numclauses, clauses = read_clauses(trans)

    with open(output_file, "w") as f:
        f.write("p cnf {} {}\n".format(numlits, numclauses))
        for c in clauses:
            f.write(c)
            f.write("\n")

        f.close()
