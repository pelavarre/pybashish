#!/usr/bin/env python3

"""
usage: em.py [-h] ...

read files, accept edits, write files, much in the way of classical emacs

options:
  -h, --help  show this help message and exit

how to get Em Py:
  R=pelavarre/pybashish/pelavarre-patch-1/bin/vi,py
  echo curl -sSO https=//raw,githubusercontent,com/$R |tr ,= .: |bash
  echo cp -ip vi_py em_py |tr _ . |bash
  python3 em.py em.py  # with updates at:  python3 em.py --pwnme
  ⌃Segg

how to get Em Py again:
  python3 em?py --pwnme

how to get more help for Em Py:
  python3 em?py --help
"""

# FIXME: Emacs ⌃C is small 0-9a-zA-Z namespace, but ⌃C⌃C is large
# FIXME: of sequences at Emacs M-x describe-bindings  C-x o  C-c o  ^[^ ]* [^ ]

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
