from collections import abc
import copy

class Clause:
    def __init__(self, literals, normal=True, check=True):
        if not isinstance(literals, abc.Iterable):
            raise RuntimeError("Expecting iterable of literals")

        # normal form for literals
        if normal:
            self._literals = sorted(set([int(l) for l in literals]))
        else:
            self._literals = literals

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

    def can_resolve(self, other_clause):
        return len(self.shared_lits(other_clause))

    def resolution_lits(self, other_clause):
        return self._literals & (-other_clause)._literals

    def resolve(self, other_clause, lit):
        if lit in self._literals:
            assert -lit in other_clause, "Expecting a valid resolution"
        else:
            assert lit in other_clause, "Expecting a valid resolution"
            assert -lit in self._literals, "Expecting a valid resolution"
            lit = -lit

        sl = copy.copy(self._literals)
        sl.remove(lit)
        ol = copy.copy(other_clause._literals)
        ol.remove(-lit)
        return Clause(sl + ol)
