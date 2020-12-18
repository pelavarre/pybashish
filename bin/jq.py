#!/usr/bin/env python3

# FIXME: discard this abandoned dead code in favour of:  hearme.py

"""
usage: jq.py [-h] [FILTER] [FILE [FILE ...]]

walk the json at standard input

positional arguments:
  FILTER      filter coded as jq
  FILE        a file of json, or lines of text (default: json at stdin)

optional arguments:
  -h, --help  show this help message and exit

quirks:
  does nothing except test python json.loads and json.dumps

unsurprising quirks:
  does prompt once for stdin, when stdin chosen as file "-" or by no file args, unlike bash "cat"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

see also:
  https://stedolan.github.io/jq/tutorial/
  https://stedolan.github.io/jq/manual/

early guesses:
  jq '.'  # Restyle the Json, after checking it for syntax errors
  jq '.[index]'  # Take value from list if present - a la Python [index:][:1]
  jq '. []'  # Take a value from each index of list
  jq '.[] .key'  # Take one column by name
  jq '.[] [.key1, .key2]'  # Take values, drop keys - like to List of Lists from List of Dicts
  jq ".[] | keys"  # Take keys, drop values, without making you type out all the values
  jq '.[] | {newkey1:.key1, newkey2:.key2}'  # Rename columns
  jq '.[] | [.key1, .key2] | @csv'  # Format List of Lists as Csv
  jq '.[] | keys'  # Take keys and sort them, drop values
  jq '.[] | .key1 + " " + .key2'  # Join the values in each Dict
  jq '.[] | .slot_digits | tonumber'  # Strip the quotes from a numeric column
  jq '.[] | [.key1, .key2] | @sh'  # Add another layer of quotes
  jq --raw-input . | jq .  # Add the first layer of quotes
  jq --raw-output '.[] | [.key1, .key2]'  # Drop a layer of keys and quotes

examples:
  echo '["aa", "cc", "bb"]' | jq .
  jq . <(echo '[12, 345, 6789]')
"""

# FIXME: refresh "def main" instantiation of usage: FILE [FILE ...]]

# guesses:
#
#   Null is to JQ as None is to Python
#   Array is to JQ as List is to Python
#   Object is to JQ as Dict is to Python
#

# capture my fresh 6/Sep cheat sheet in the examples
# tweet my cheat sheet with a link to GitHub
# emphasize respecting the order of dicts


import json
import sys

import argdoc


def main():
    args = argdoc.parse_args()

    # Fetch

    files = args.files if args.files else "-".split()
    for path in files:

        if path == "-":
            prompt_tty_stdin()
            chars = sys.stdin.read()
        else:
            with open(path) as incoming:
                chars = incoming.read()

        # Munge

        stdout = "\n"
        if chars:
            bits = json.loads(chars)
            stdout = json.dumps(bits) + "\n"

        # Store

        sys.stdout.write(stdout)


#
# Git-track some Python idioms here
#


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
