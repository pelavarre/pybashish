#!/usr/bin/env python3

r"""
usage:  doubler.py

duplicates every copy of self

quirks:  looks only for r"^doubler.py(~|~[0-9]+~)?$"
"""

import os
import re
import shutil


NAME = os.path.split(__file__)[-1]
regex = r"^{name}(~|~[0-9]+~)?$".format(name=NAME)


name_by_index = dict()

for name in os.listdir():
    match = re.match(regex, string=name)
    if match:
        str_index = match.group(1)

        index = 0
        if str_index is not None:
            index = 1
            if str_index != "~":
                assert str_index.startswith("~"), repr(str_index)
                assert str_index.endswith("~"), repr(str_index)
                index = int(str_index[len("~") :][: -len("~")])

        print("+ {}:{}".format(index, name))

        assert index not in name_by_index.keys()
        name_by_index[index] = name

assert name_by_index.values(), (regex, name)
last_prior_index = max(name_by_index.keys())

index = last_prior_index + 1
for name in sorted(name_by_index.values()):

    next_name = "{name}~".format(name=name)
    if index > 1:
        next_name = "{name}~{index}~".format(name=NAME, index=index)

    print("+ cp -ip {} {}".format(NAME, next_name))

    assert not os.path.exists(next_name), next_name
    shutil.copy2(NAME, dst=next_name)

    index += 1
