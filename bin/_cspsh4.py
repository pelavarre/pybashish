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


DENT = 4 * " "


class AfterProc(collections.namedtuple("AfterProc", "before after".split())):
    def to_py(self, depth):
        pys = list()
        pys.append("AfterProc(")
        pys.append(DENT + "before=" + self.before.to_py(depth + 1) + ",")
        pys.append(DENT + "after=" + self.after.to_py(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class EventsProc(collections.namedtuple("EventsProc", "name events body".split())):
    def to_py(self, depth):
        pys = list()
        pys.append("EventsProc(")
        pys.append(DENT + 'name="{}",'.format(self.name))
        pys.append(DENT + "events=" + self.events.to_py(depth + 1) + ",")
        pys.append(DENT + "body=" + self.body.to_py(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class ChoiceTuple(tuple):
    def __new__(cls, *args):
        return super().__new__(cls, args)

    def to_py(self, depth):
        pys = list()
        pys.append("ChoiceTuple(")
        for event in self:
            pys.append(DENT + event.to_py(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class Event(collections.namedtuple("Event", "name".split())):
    def to_py(self, depth):
        py = 'Event("{}")'.format(self.name)  # wrong over quotes or line breaks
        return py


class EventPair(collections.namedtuple("EventPair", "head tail".split())):
    pass


class EventTuple(tuple):
    def __new__(cls, *args):
        return super().__new__(cls, args)

    def to_py(self, depth):
        pys = list()
        pys.append("EventTuple(")
        for event in self:
            pys.append(DENT + event.to_py(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class Proc(collections.namedtuple("Proc", "name body".split())):
    def to_py(self, depth):
        pys = list()
        pys.append("Proc(")
        pys.append(DENT + 'name="{}",'.format(self.name))
        pys.append(DENT + "body=" + self.body.to_py(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class StoredProc(collections.namedtuple("StoredProc", "name".split())):
    def to_py(self, depth):
        py = 'StoredProc("{}")'.format(self.name)  # wrong over quotes or line breaks
        return py


def to_py(csp):  # TODO: declare type(csp) as layer over collections.namedtuple
    py = csp.to_py(0)
    return py


#
# Run from the command line
#


def main(argv):
    """Run from the command line"""

    parser = compile_argdoc(epi="examples:")
    _ = parser.parse_args(argv[1:])

    try_csp_py()

    print("+ exit 0")


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


#
# Self test
#


def try_csp_py():
    """VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))"""

    vmct = Proc(
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
                        after=StoredProc("X"),
                    ),
                    AfterProc(
                        before=Event("toffee"),
                        after=StoredProc("X"),
                    ),
                ),
            ),
        ),
    )

    _ = vmct

    csp1 = Event("coin")
    py = to_py(csp1)
    assert py == 'Event("coin")', repr(py)

    csp2 = EventTuple(
        Event("coin"),
        Event("choc"),
        Event("toffee"),
    )
    py = to_py(csp2)
    want = 'EventTuple(\n Event("coin"),\n Event("choc"),\n Event("toffee"),\n)'
    assert py == want.replace(" ", DENT), repr(py)

    csp3 = AfterProc(
        before=Event("coin"),
        after=ChoiceTuple(
            AfterProc(before=Event("choc"), after=StoredProc("X")),
            AfterProc(before=Event("toffee"), after=StoredProc("X")),
        ),
    )
    py = to_py(csp3)
    want = textwrap.dedent(  # FIXME: read this from this source file
        """
        AfterProc(
            before=Event("coin"),
            after=ChoiceTuple(
                AfterProc(
                    before=Event("choc"),
                    after=StoredProc("X"),
                ),
                AfterProc(
                    before=Event("toffee"),
                    after=StoredProc("X"),
                ),
            ),
        )
        """
    ).strip()
    assert py == want, (repr(want), repr(py))

    want = textwrap.dedent(  # FIXME: read this from this source file
        """
        Proc(
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
                            after=StoredProc("X"),
                        ),
                        AfterProc(
                            before=Event("toffee"),
                            after=StoredProc("X"),
                        ),
                    ),
                ),
            ),
        )
        """
    ).strip()

    got = to_py(vmct)

    diff_lines = list(
        difflib.unified_diff(
            a=want.splitlines(),
            b=got.splitlines(),
            fromfile="input",
            tofile="output",
        )
    )

    assert not diff_lines, print("\n".join(diff_lines)) or len(diff_lines)
    # FIXME: stderr_print


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
