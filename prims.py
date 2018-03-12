from collections import abc

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
    def __init__(self, literals, normal=True, check=True):
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

    @property
    def literals(self):
        return self._literals

    @property
    def taut(self):
        return self._taut

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

    def resolve(self, other_clause, lit):
        if lit in self._literals:
            assert -lit in other_clause._literals, "Expecting a valid resolution"
        else:
            assert lit in other_clause._literals, "Expecting a valid resolution"
            assert -lit in self._literals, "Expecting a valid resolution"
            lit = -lit

        sl = list(self._literals)
        sl.remove(lit)
        ol = list(other_clause._literals)
        ol.remove(-lit)
        return Clause(sl + ol)

    def register(self):
        for l in self._literals:
            l.add_clause(self)

    def deregister(self):
        for l in self._literals:
            l.remove_clause(self)

    def __str__(self):
        return ' '.join([str(l) for l in self._literals])

    def __repr__(self):
        return self.__str__()
