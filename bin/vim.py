#!/usr/bin/env python3

"""
usage: vim.py [-h] ...

read files, accept edits, write files, in the way of classical vim

options:
  -h, --help  show this help message and exit

quirks:
  runs like 'vi.py' but then emulates Vim bugs more closely

how to get Vim Py:
  R=pelavarre/pybashish/master/bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R
  echo cp -ip vi_py vim_py |tr _ . ||bash
  python3 vim?py vim?py
  /egg

how to get Vim Py again:
  python3 vim?py --pwnme

how to get more help for Vim Py:
  python3 vim?py --help
"""

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
