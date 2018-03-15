#!/usr/bin/env python3

import re

timestr = '_AT(?P<T>\d+)'

def normal_form(name):
    # need to remove BVSKOLEM's number
    min_time = 1000000
    max_time = 0
    for t in re.finditer(timestr, name):
        time = int(t.groupdict()['T'])
        if time < min_time:
            min_time = time
        if time > max_time:
            max_time = time

    # normalize times to have zero be the minimum
    ntimes = list()
    for t in re.finditer(timestr, name):
        ntimes.append(int(t.groupdict()['T']) - min_time)

    fstr = re.sub(timestr, '_AT%d', name)
    fstr = re.sub('BVSKOLEM\$\$_\d+', 'BVSKOLEM$$_norm', fstr)
    return fstr%tuple(ntimes), (min_time, max_time)

if __name__ == "__main__":
    n1 = "wrPtr__AT0"
    n2 = "rdPtr__AT1"
    n3 = "(= wrPtr__AT21 (+ wrPtr__AT20 #b0001))"
    n4 = "(and (not clk__AT4) clk__AT5 (not clk__AT6) clk__AT7)"
    n5 = "(= (BITVECTOR_BITOF [1] mpt.__DOLLAR__lt__DOLLAR__data_integrity_scoreboard__DOT__sv__COLON__42__DOLLAR__203.extendA.out_AT0) (BITVECTOR_BITOF [1] BVSKOLEM$$_29)))"

    for n in [n1, n2, n3, n4, n5]:
        print(n, normal_form(n))
