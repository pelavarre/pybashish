# ~/.python.py

"""
Python dot file in home dir

alias -- -p='( set -xe; python3 -i ~/.python.py )'
alias -- -p3="( set -xe; python3 -i ~/.python.py 'print(sys.version.split()[0])' )"
alias -- -p2="( set -xe; python2 -i ~/.python.py 'print(sys.version.split()[0])' )"
"""

import datetime as dt
import os
import sys

try:
    import pathlib
except ImportError:
    pathlib = None


_ = os
_ = pathlib


if sys.argv[1:]:
    exec(sys.argv[1])


now = dt.datetime.now()

try:
    raise Exception("sparkling chaos")
except Exception as _exc:
    exc = _exc


# copied from:  git clone https://github.com/pelavarre/pybashish.git
