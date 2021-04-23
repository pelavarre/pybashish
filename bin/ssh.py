#!/usr/bin/env python3

"""
usage: ssh.py [-h] [-- [WORD [WORD ...]]]

shell out to a host

positional arguments:
  WORD        an arg to pass on to "ssh"

optional arguments:
  -h, --help  show this help message and exit

dreams:
  list which options were supplied
  fold the relevant parts of ~/.ssh/config into the command line if missing
  loop to reconnect
  time how long the session
  caffeinate self
  don't flood the console with polling
  accept keystrokes to accelerate
  teach make to more ignore notes of this kind, like because all comments and blanks
  like allow docstring but reject code without a proper stub
  turn on the "-vvv" of "ssh -vvv" only AFTER the session is up, a la ~v

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""

# FIXME: better ArgDoc explanation when pos~ usage missing from pos~ arguments

# copied from:  git clone https://github.com/pelavarre/pybashish.git
