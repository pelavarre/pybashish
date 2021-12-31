#!/usr/bin/env python3

"""
usage: emacs.py [-h] ...

read files, accept edits, write files, in the way of classical emacs

options:
  -h, --help  show this help message and exit

quirks:
  runs like 'em.py' but then emulates Emacs bugs more closely

how to get Emacs Py:
  R=pelavarre/pybashish/master/bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R
  echo cp -ip vi_py emacs_py |tr _ . ||bash
  python3 emacs?py emacs?py
  ⌃Segg

how to get Emacs Py again:
  python3 emacs?py --pwnme

how to get more help for Emacs Py:
  python3 emacs?py --help
"""

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
