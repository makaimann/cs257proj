from prims import Clause, Lit
import random
from proc_data import read_trace, read_litmap

def sample_resolvable_clause(clauses, max_iter=20):
    lits = set()
    clauses = set(clauses)
    i = 0
    while i < max_iter & len(lits) == 0:
        c = random.sample(clauses, 1)[0]
        neglits = [-l for l in c._literals]
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
        neglits = [-l for l in c._literals]
        lits = set(filter(lambda l: len(l._clauses) > 0, neglits))
        if len(lits) == 0:
            c, oc, lit = sample_resolvable_clause(clauses)
        else:
            lit = random.sample(lits, 1)[0]
            oc = random.sample(set(lit._clauses), 1)[0]

        new_clauses[idx] = c.resolve(oc, lit)

        idx += 1

    return set(new_clauses)


if __name__ == "__main__":

    with open("fifo_3.trace") as f:
        log = f.read()
        f.close()

    litmap = read_litmap()

    learned_clauses, clauses, orig_clauses, emptyclausenode, clausecnt = read_trace(log)

    new_clauses = generate_random_clauses(clauses, 1000)
