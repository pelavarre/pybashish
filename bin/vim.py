#!/usr/bin/env python3

"""
usage: vim.py [-h] ...

read files, accept edits, write files

optional arguments:
  -h, --help  show this help message and exit

quirks:
  runs like 'vi.py' but then emulates Vim bugs more closely

how to get more help for Vim:
  python3 vim.py --help
"""

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
