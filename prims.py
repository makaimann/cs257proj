from collections import abc
import itertools

class Lit(object):
    litmap = dict()
    def __new__(cls, i):
        if i in Lit.litmap:
            return Lit.litmap[i]
        else:
            newcls = super(Lit, cls).__new__(cls)
            newcls._clauses = set()
            Lit.litmap[i] = newcls
            return newcls

    def __init__(self, i):
        self._i = i

    def add_clause(self, c):
        self._clauses.add(c)

    def remove_clause(self, c):
        if c in self._clauses:
            self._clauses.remove(c)

    def get_resolvable_clauses(self):
        return itertools.product(self._clauses, (-self)._clauses)

    def absl(self):
        return Lit(abs(self._i))

    def __hash__(self):
        return self._i.__hash__()

    def __eq__(self, other):
        return self._i == other._i

    def __ne__(self, other):
        return self._i != other._i

    def __neg__(self):
        return Lit(-self._i)

    def __lt__(self, other):
        return self._i < other._i

    def __le__(self, other):
        return self._i <= other._i

    def __gt__(self, other):
        return self._i > other._i

    def __ge__(self, other):
        return self._i >= other._i

    def __str__(self):
        return str(self._i)

    def __repr__(self):
        return str(self._i)

class Clause:
    def __init__(self, literals, normal=True, check=False):
        if not isinstance(literals, abc.Iterable):
            raise RuntimeError("Expecting iterable of literals")

        # normal form for literals
        # remove duplicates and sort
        if normal:
            self._literals = tuple(sorted(set(literals)))
        else:
            self._literals = tuple(literals)

        self._taut = False

        if check:
            for l in self._literals:
                if -l in self._literals:
                    self._taut = True

        self._score = None

    @property
    def literals(self):
        return self._literals

    @property
    def taut(self):
        return self._taut

    @property
    def score(self):
        return self._score

    def add_score(self, score):
        self._score = score

    def __lt__(self, other):
        # using in a min-heap
        # but we actually want max, so reverse the order
        return self._score > other._score

    def __neg__(self):
        '''
        Negates all the literals in the clause.
        Note: This does NOT negate the *clause*, it negates each of
              the literals.
        '''
        return Clause([-l for l in reversed(self._literals)], normal=False, check=False)

    def __hash__(self):
        return self._literals.__hash__()

    def __eq__(self, other):
        return self._literals == other._literals

    def __ne__(self, other):
        return self._literals != other._literals

    def can_resolve(self, other_clause):
        return len(self.resolution_lits(other_clause)) > 0

    def resolution_lits(self, other_clause):
        return set(self._literals) & set((-other_clause)._literals)

    def resolve(self, other_clause, lit, check=False):
        if lit in self._literals:
            assert -lit in other_clause._literals, "Expecting a valid resolution"
        else:
            assert lit in other_clause._literals, "Expecting a valid resolution"
            assert -lit in self._literals, "Expecting a valid resolution, {}: {} - {}".format(lit, other_clause, self,)
            lit = -lit

        sl = list(self._literals)
        sl.remove(lit)
        ol = list(other_clause._literals)
        ol.remove(-lit)
        return Clause(sl + ol, check=check)

    def get_resol_clauses(self):
        neglits = (-l for l in self._literals)
        for nl in neglits:
            for c in nl._clauses:
                yield c, -nl

    def register(self):
        for l in self._literals:
            l.add_clause(self)

    def deregister(self):
        for l in self._literals:
            l.remove_clause(self)

    def feature_form(self, num_lits):
        '''
        Transform to data representation.
        As a feature, this gives <num_lits> of the literals in the clause
        If the clause has less literals than <num_lits> fill the extra slots with zeros
        And it appends the size of the (original) clause
        '''
        features = None
        literals = list([l._i for l in self._literals])
        mid = int(num_lits/2)
        if len(literals) < num_lits:
            features = literals
            features += [0]*(num_lits - len(literals))
        else:
            # don't want to bias towards just negative values (because literals are always sorted)
            # Thus take from the beginning and end
            if num_lits%2 == 0:
                features = literals[:mid] + literals[-mid:]
            else:
                features = literals[:mid+1] + literals[-mid:]

        features.append(len(self._literals))

        assert features is not None
        assert len(features) == num_lits + 1

        return features

    def __str__(self):
        if len(self._literals) == 0:
            return "phi"
        else:
            return ' '.join([str(l) for l in self._literals])

    def __repr__(self):
        return self.__str__()


class Node:
    '''
    Represents a node in the resolution refutation DAG
    '''
    def __init__(self, data, parents, children):
        self._data = data

        if len(parents) > 0:
            for p in parents:
                assert isinstance(p, Node)
            self._parents = parents

        if len(children) > 0:
            assert isinstance(child, Node)

        self._parents = parents
        self._children = children

    @property
    def parents(self):
        return self._parents

    @property
    def children(self):
        return self._children

    @property
    def data(self):
        return self._data

    def add_child(self, c):
        self._children.append(c)

    def __repr__(self):
        return "<Node: data={}, parents={}, children={}>".format(self._data,
                                                                 [p.data for p in self._parents],
                                                                 [c.data for c in self._children])
