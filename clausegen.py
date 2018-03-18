from prims import Clause, Lit
import random
from proc_data import read_trace, read_litmap
import heapq

class priqueue:
    def __init__():
        self._l = []

    def push(self, item):
        heapq.heappush(self._l, (-item[0], item[1]))

    def pop(self):
        item = heapq.heappop(self._l)
        return (-item[0], item[1])

    def top(self, n):
        res = heapq.nsmallest(n, self._l)
        return [(-it[0], it[1]) for it in res]

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


def gen_clauses(model, clauses, num, num_lits, model_processor, BURN=1000):
    literals = set(Lit(l) for l in range(1, num_lits+1))
    cmap = {}
    for c in clauses:
        # get processed forms of clauses
        proc_clause, bounds = processed_form(c)
        cmap[proc_clause] = (c, bounds)

    for pc in cmap:
        # register all the processed forms
        # only doing clause resolution on normal forms
        # then scoring it for each bound
        pc.register()

    # BURN IN Phase for generating random clauses
    # might need to change this so it's not resolving on so many clauses
    # of the same literal
    # alternatively could just sweep through the literals once and add
    # all of it's resolvents
    b_cl = 0
    burn_clauses = priqueue()
    for l in random.sample(literals, 2*BURN):
        for c1, c2 in l.get_resolvable_clauses():
            cr = c1.resolve(c2, l)
            # max score over any time
            max_score = max((model.predict(model_processor(c, bounds)) for c, bounds in cmap[cr]))
            burn_clauses.push((max_score, cr))
            b_cl += 1
            if b_cl >= BURN:
                break

    gen_clauses = priqueue()

    # keep the top twenty percent from burn_clauses
    for score, bc in burn_clauses.top(int(.2*BURN)):
        bc.register()
        gen_clauses.push((score, bc))

    cache_scores = {}
    num_clauses = 0
    while num_clauses < num:
        # loop over top 20 clauses and add their resolvents if scores increase
        # for c in
        pass


if __name__ == "__main__":

    with open("fifo_3.trace") as f:
        log = f.read()
        f.close()

    litmap = read_litmap()

    learned_clauses, clauses, orig_clauses, emptyclausenode, clausecnt = read_trace(log)

    new_clauses = generate_random_clauses(clauses, 1000)
