# ~/.python.py

"""
Python dot file in home dir

alias -- -p='( set -xe; python3 -i ~/.python.py )'
alias -- -p3="( set -xe; python3 -i ~/.python.py 'print(sys.version.split()[0])' )"
alias -- -p2="( set -xe; python2 -i ~/.python.py 'print(sys.version.split()[0])' )"
"""

import argparse
import datetime as dt
import math
import os
import pdb
import random
import re
import string
import subprocess
import sys

_ = pdb


_ = math
_ = random
_ = re
_ = string
_ = subprocess


try:
    import pathlib
except ImportError:
    pathlib = None


_ = os
_ = pathlib


# header

now = dt.datetime.now()


# body

try:
    raise Exception("sparkling chaos")
except Exception as _exc:
    exc = _exc

ns = argparse.Namespace()

parser = argparse.ArgumentParser()


# trailer

if sys.argv[1:]:
    exec(sys.argv[1])


# copied from:  git clone https://github.com/pelavarre/pybashish.git
