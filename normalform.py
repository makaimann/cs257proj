#!/usr/bin/env python3

import re

timestr = '_AT(?P<T>\d+)'

def normal_form(name):
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
    return fstr%tuple(ntimes), max_time

if __name__ == "__main__":
    n1 = "wrPtr__AT0"
    n2 = "rdPtr__AT1"
    n3 = "(= wrPtr__AT21 (+ wrPtr__AT20 #b0001))"
    n4 = "(and (not clk__AT4) clk__AT5 (not clk__AT6) clk__AT7)"

    for n in [n1, n2, n3, n4]:
        print(n, normal_form(n))
