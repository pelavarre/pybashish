# ~/.python.lazy.py

"""
Python dot file in home dir

alias -- -p='( set -xe; python3 -i ~/.python.lazy.py )'
alias -- -p3="( set -xe; python3 -i ~/.python.lazy.py 'print(sys.version.split()[0])' )"
alias -- -p2="( set -xe; python2 -i ~/.python.lazy.py 'print(sys.version.split()[0])' )"
"""

import math  # 'dir(math)' goes wrong at test of:  math = lazy_import.lazy_module("math")

import lazy_import


argparse = lazy_import.lazy_module("argparse")
collections = lazy_import.lazy_module("collections")
dt = lazy_import.lazy_module("datetime")
json = lazy_import.lazy_module("json")
_ = math
os = lazy_import.lazy_module("os")
pathlib = lazy_import.lazy_module("pathlib")
pdb = lazy_import.lazy_module("pdb")
random = lazy_import.lazy_module("random")
re = lazy_import.lazy_module("re")
string = lazy_import.lazy_module("string")
subprocess = lazy_import.lazy_module("subprocess")
sys = lazy_import.lazy_module("sys")

matplotlib = lazy_import.lazy_module("matplotlib")
np = lazy_import.lazy_module("numpy")
pd = lazy_import.lazy_module("pandas")


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
