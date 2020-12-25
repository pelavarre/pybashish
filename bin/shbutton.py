#!/usr/bin/env python3

"""
usage: shbutton.py [-h] [HINT [HINT ...]]

auto-complete the hints into a complete bash command line, trace it, and run it

positional arguments:
  HINT                  code to run

mac zsh usage:

  alias -- '0'='shbutton 0'
  alias -- '+'='shbutton +'
  alias -- '-'='shbutton -'
  alias -- '*'='shbutton "*"'
  alias -- '/'='shbutton /'

  function shbutton () {
      local v="$1"
      shift
      shbutton.py "$@" "$v"
  }

examples:

  0
  + 12
  / 34
  * 5
  / 6

"""

import decimal
import subprocess
import sys


def main(argv):
    #

    print("pbpaste")
    print(argv[1:])
    print("pbcopy")


if __name__ == "__main__":
    main(sys.argv)
