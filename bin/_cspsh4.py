#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

workflow:
  cd ~/Public/pybashish/bin && --black _cspsh4.py && --flake8 _cspsh4.py && python3 -i _cspsh4.py

examples:
  _cspsh4.py
"""

# FIXME:
#
# 2 # write def to_csp(self)
# 3 # write def from_csp(str) factories
# 4 # collapse to line that fits
#

# code reviewed by people, and by Black and Flake8 bots


import __main__
import argparse
import collections
import difflib
import os
import sys
import textwrap


#
# Think in Lisp, while coding in Python
#


DENT = 4 * " "


class CspTree:
    def _to_deep_py_(self, depth):

        pys = list()
        pys.append(type(self).__name__ + "(")

        for field in self._fields:
            tree = getattr(self, field)
            if not hasattr(tree, "_to_deep_py_"):
                pys.append(DENT + field + '="{}",'.format(tree))
            else:
                pys.append(DENT + field + "=" + tree._to_deep_py_(depth + 1) + ",")

        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)

        return py

        # .format(... tree ...) goes wrong over quotes, line breaks, etc


class CspLeaf(CspTree):
    def _to_deep_py_(self, depth):

        assert len(self._fields) == 1, self._fields

        field = self._fields[-1]
        tree = getattr(self, field)
        py = '{}("{}")'.format(type(self).__name__, tree)

        return py

        # .format(... tree ...) goes wrong over quotes, line breaks, etc


class CspList(CspTree):
    def _to_deep_py_(self, depth):

        pys = list()
        pys.append(type(self).__name__ + "(")

        for item in self:
            pys.append(DENT + item._to_deep_py_(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


def to_deep_py(csp_tree):
    py = csp_tree._to_deep_py_(0)
    return py


#
# Declare a CSP Lisp
#


class AfterProc(collections.namedtuple("AfterProc", "before after".split()), CspTree):
    pass


class EventsProc(
    collections.namedtuple("EventsProc", "name events body".split()), CspTree
):
    pass


class ChoiceTuple(tuple, CspList):
    def __new__(cls, *args):
        return super().__new__(cls, args)


class Event(CspLeaf, collections.namedtuple("Event", "name".split())):
    pass


class EventPair(collections.namedtuple("EventPair", "head tail".split())):
    pass


class EventTuple(tuple, CspList):
    def __new__(cls, *args):
        return super().__new__(cls, args)


class ProcDef(collections.namedtuple("ProcDef", "name body".split()), CspTree):
    pass


class DeffedProc(collections.namedtuple("DeffedProc", "name".split()), CspLeaf):
    pass


#
# Run from the command line
#


def main(argv):
    """Run from the command line"""

    parser = compile_argdoc(epi="workflow:")
    _ = parser.parse_args(argv[1:])

    try_to_deep_py()

    stderr_print("+ exit 0")


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
        stderr_print("\n".join(lines))

        stderr_print("error: update main argdoc to match help, or vice versa")

        sys.exit(1)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


#
# Self test
#


def try_to_deep_py():
    """Translate to source lines of nests of Python calls, from Csp Tree"""

    # coin  # an event exists

    want0 = textwrap.dedent(
        """
        Event("coin")
        """
    ).strip()

    # {coin, choc, toffee}  # an alphabet collects one event after another

    want1 = textwrap.dedent(
        """
        EventTuple(
            Event("coin"),
            Event("choc"),
            Event("toffee"),
        )
        """
    ).strip()

    # choc → X  # event guards process

    want11 = textwrap.dedent(
        """
        AfterProc(
            before=Event("choc"),
            after=DeffedProc("X"),
        )
        """
    ).strip()

    # coin → (choc → X | toffee → X)  # events guard processes

    want2 = textwrap.dedent(
        """
        AfterProc(
            before=Event("coin"),
            after=ChoiceTuple(
                AfterProc(
                    before=Event("choc"),
                    after=DeffedProc("X"),
                ),
                AfterProc(
                    before=Event("toffee"),
                    after=DeffedProc("X"),
                ),
            ),
        )
        """
    ).strip()

    # VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))

    want3 = textwrap.dedent(
        """
        ProcDef(
            name="VMCT",
            body=EventsProc(
                name="X",
                events=EventTuple(
                    Event("coin"),
                    Event("choc"),
                    Event("toffee"),
                ),
                body=AfterProc(
                    before=Event("coin"),
                    after=ChoiceTuple(
                        AfterProc(
                            before=Event("choc"),
                            after=DeffedProc("X"),
                        ),
                        AfterProc(
                            before=Event("toffee"),
                            after=DeffedProc("X"),
                        ),
                    ),
                ),
            ),
        )
        """
    ).strip()

    wants = (want0, want1, want11, want2, want3)
    for want in wants:
        csp_tree = eval(want)
        py = to_deep_py(csp_tree)

        if False:
            stderr_print()
            stderr_print(py)

        assert not stderr_print_diff(input=want, output=py)


def stderr_print_diff(**kwargs):
    """Retun the Diff of the Lines given, but print it first when not empty"""

    (fromfile, tofile) = kwargs.keys()
    a = kwargs[fromfile].splitlines()
    b = kwargs[tofile].splitlines()

    diff_lines = list(
        difflib.unified_diff(
            a=a,
            b=b,
            fromfile=fromfile,
            tofile=tofile,
        )
    )

    if diff_lines:
        stderr_print("\n".join(diff_lines))

    return diff_lines


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
