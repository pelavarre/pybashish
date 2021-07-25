#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

examples:
  _cspsh4.py
"""

# FIXME:
#
# 1
# git commit code that doesn't crash
#
# 2
# derive Classes from Named Tuple
# write def to_py(self), one test at a time
# test from innermost expression, then more and more
# collapse to line that fits
# pass down the indent level to discover fits or not
#
# 3
# write def to_csp(self)
#
# 4
# write def from_csp(str) factories
#

# code reviewed by people, and by Black and Flake8 bots


import __main__
import argparse
import collections
import difflib
import os
import sys


Proc = collections.namedtuple("Proc", "name body".split())
AlphabetProc = collections.namedtuple("AlphabetProc", "name alphabet body".split())
Event = collections.namedtuple("Event", "name".split())
AfterProc = collections.namedtuple("AfterProc", "before after".split())
ChoiceProc = collections.namedtuple("ChoiceProc", "first last".split())
StoredProc = collections.namedtuple("StoredProc", "name".split())


#
# Run from the command line
#


def main(argv):
    """Run from the command line"""

    parser = compile_argdoc(epi="examples:")
    _ = parser.parse_args(argv[1:])

    try_csp_py()

    print("+ exit 0")


def try_csp_py():
    """VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))"""

    vmct = Proc(
        name="VMCT",
        body=AlphabetProc(
            name="X",
            alphabet={
                Event("coin"),
                Event("choc"),
                Event("toffee"),
            },
            body=AfterProc(
                before=Event("coin"),
                after=ChoiceProc(
                    AfterProc(before=Event("choc"), after=StoredProc("X")),
                    AfterProc(before=Event("toffee"), after=StoredProc("X")),
                ),
            ),
        ),
    )

    _ = vmct


#
# Run on top of a layer of general-purpose Python idioms
#


# deffed in many files  # missing from docs.python.org
def compile_argdoc(epi):
    """Declare how to parse the command line"""

    doc = __main__.__doc__
    prog = doc.strip().splitlines()[0].split()[1]
    description = list(_ for _ in doc.strip().splitlines() if _)[1]
    epilog_at = doc.index(epi)
    epilog = doc[epilog_at:]

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=True,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    exit_unless_main_doc_eq(parser)
    return parser


# deffed in many files  # missing from docs.python.org
def exit_unless_main_doc_eq(parser):
    """Exit nonzero, unless __main__.__doc__ equals "parser.format_help()" """

    file_filename = os.path.split(__file__)[-1]

    main_doc = __main__.__doc__.strip()
    parser_doc = parser.format_help()

    got = main_doc
    got_filename = "./{} --help".format(file_filename)
    want = parser_doc
    want_filename = "argparse.ArgumentParser(..."

    diff_lines = list(
        difflib.unified_diff(
            a=got.splitlines(),
            b=want.splitlines(),
            fromfile=got_filename,
            tofile=want_filename,
        )
    )

    if diff_lines:

        lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
        print("\n".join(lines))

        print("error: update main argdoc to match help, or vice versa")

        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
