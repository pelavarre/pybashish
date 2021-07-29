#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

workflow:
  cd ~/Public/pybashish/bin && \
    --black _cspsh4.py && --flake8 _cspsh4.py && python3 -i _cspsh4.py

examples:
  _cspsh4.py
"""

# FIXME:
#
# 3 # write def eval_csp(str) factories
# 4 # collapse to line that fits
#

# code reviewed by people, and by Black and Flake8 bots


import __main__
import argparse
import collections
import difflib
import itertools
import os
import pdb
import re
import sys
import textwrap

_ = pdb


#
# Think in Lisp, while coding in Python
#


DENT = 4 * " "


class CspTree:
    def _to_deep_csp_(self, depth):

        csps = list()

        mark_field_pairs = itertools.zip_longest(self._marks_, self._fields)
        for (mark, field) in mark_field_pairs:
            tree = getattr(self, field)
            if not hasattr(tree, "_to_deep_py_"):
                csp_item = str(tree)
            else:
                csp_item = tree._to_deep_csp_(depth + 1)

            csps.append(DENT + mark + csp_item)

        dent = depth * DENT
        csp = ("\n" + dent).join(csps)
        return csp

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

        # goes wrong when field value type is not in (CspTree, str)
        # goes wrong over quotes, line breaks, etc in field values


class CspLeaf(CspTree):
    def _to_deep_csp_(self, depth):

        assert len(self._fields) == 1, self._fields

        field = self._fields[-1]
        tree = getattr(self, field)
        csp = tree

        return csp

    def _to_deep_py_(self, depth):

        assert len(self._fields) == 1, self._fields

        field = self._fields[-1]
        tree = getattr(self, field)
        py = '{}("{}")'.format(type(self).__name__, tree)

        return py

        # goes wrong over quotes, line breaks, etc in field value


class CspTuple(CspTree):
    def _to_deep_csp_(self, depth):

        csps = list()
        csps.append(self._open_mark_)

        for (index, item) in enumerate(self):
            csp_item = item._to_deep_csp_(depth + 1)
            csp_item = _csp_unwrap_(csp_item)

            if not index:
                csps.append(DENT + csp_item + self._comma_mark_)
            else:
                csps.append(DENT + self._op_mark_ + csp_item + self._comma_mark_)

        csps.append(self._close_mark_)

        dent = depth * DENT
        csp = ("\n" + dent).join(csps)
        return csp

    def _to_deep_py_(self, depth):

        if hasattr(self, "_py_style_"):

            styles = self._py_style_.splitlines(keepends=True)
            assert len(styles) >= 3, repr(styles)

            self_name = type(self).__name__

            chars = ""

            if "{}" not in styles[0]:
                chars += to_deep_py(styles[0])
            else:
                chars += styles[0].format(to_deep_py(self_name, depth=(depth + 1)))

            for (index, item) in enumerate(self):
                if not index:
                    chars += styles[1].format(to_deep_py(item, depth=(depth + 1)))
                else:
                    chars += styles[-2].format(to_deep_py(item, depth=(depth + 1)))

            chars += styles[-1].format()

            dent = depth * "\t"
            dented_chars = ("\n" + dent).join(chars.splitlines())
            spaced_chars = dented_chars.replace("\t", DENT)

            return spaced_chars

        pys = list()
        pys.append(type(self).__name__ + "(")

        for item in self:
            pys.append(DENT + item._to_deep_py_(depth + 1) + ",")
        pys.append(")")

        dent = depth * DENT
        py = ("\n" + dent).join(pys)
        return py


class CspPair(CspTree):
    def _to_deep_csp_(self, depth):

        assert len(self._fields) == 2, self._fields

        csps = list()
        csps.append(self._open_mark_)

        for (index, field) in enumerate(self._fields):
            tree = getattr(self, field)
            if not index:
                csps.append(DENT + tree._to_deep_csp_(depth + 1))
            else:
                csps.append(DENT + self._op_mark_ + " " + tree._to_deep_csp_(depth + 1))

        csps.append(self._close_mark_)

        dent = depth * DENT
        csp = ("\n" + dent).join(csps)

        return csp


def to_deep_csp(csp_tree):
    csp = csp_tree._to_deep_csp_(0)
    return csp


def to_deep_py(obj, depth=0):
    if hasattr(obj, "_to_deep_py_"):
        chars = obj._to_deep_py_(depth)
    else:
        chars = str(obj)
    return chars


def _csp_unwrap_(csp_got):
    if csp_got.startswith("(") and csp_got.endswith(")"):
        csp_got = csp_got[len("(") :][: -len(")")]
    csp_got = csp_got.strip()
    return csp_got


#
# Declare a CSP Lisp
#


class AfterProc(collections.namedtuple("AfterProc", "before after".split()), CspPair):
    _open_mark_ = "("
    _op_mark_ = "→"
    _close_mark_ = ")"


class EventsProc(
    collections.namedtuple("EventsProc", "name events body".split()), CspTree
):
    _marks_ = ("μ ", " : ", " • ")


class ChoiceTuple(tuple, CspTuple):

    _open_mark_ = "("
    _op_mark_ = "| "
    _comma_mark_ = ""
    _close_mark_ = ")"

    def __new__(cls, *args):
        return super().__new__(cls, args)


class Event(CspLeaf, collections.namedtuple("Event", "name".split())):
    pass


class EventTuple(tuple, CspTuple):

    # TODO: _csp_style_ = "{{\n" "\t{},\n" "}}\n"
    _py_style_ = "{}(\n" "\t{},\n" ")\n"

    _open_mark_ = "{"
    _op_mark_ = ""
    _comma_mark_ = ","
    _close_mark_ = "}"

    def __new__(cls, *args):
        return super().__new__(cls, args)


class ProcDef(collections.namedtuple("ProcDef", "name body".split()), CspTree):
    _marks_ = ("", " = ")


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
    """Format and log like "print", except flush Stdout & write and flush Stderr"""

    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def stderr_print_diff(**kwargs):
    """Return the Diff of the Lines given, but print it first when not empty"""

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

    # choc → X | toffee → X  # events guard processes

    want20 = textwrap.dedent(
        """
        ChoiceTuple(
            AfterProc(
                before=Event("choc"),
                after=DeffedProc("X"),
            ),
            AfterProc(
                before=Event("toffee"),
                after=DeffedProc("X"),
            ),
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

    # choose

    py_wants = (want0, want1, want11, want20, want2, want3)

    csp_wants = (
        textwrap.dedent(
            """
            coin
            {coin, choc, toffee}
            choc → X
            choc → X | toffee → X
            coin → (choc → X | toffee → X)
            VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))
            """
        )
        .strip()
        .splitlines()
    )

    # test

    tupled_wants = itertools.zip_longest(py_wants, csp_wants)
    for (index, tupled_want) in enumerate(tupled_wants):
        (py_want, csp_want) = tupled_want

        csp_tree = eval(py_want)

        # test print as Py

        py_got = to_deep_py(csp_tree)

        assert not stderr_print_diff(input=py_want, output=py_got)

        # test print as Csp

        csp_got = to_deep_csp(csp_tree)

        if False:  # compile time option to review line broken format
            print()
            print(csp_got)  # intelligible, but not yet great

        if True:
            csp_got = re.sub(r" +", repl=" ", string=csp_got)
            csp_got = csp_got.replace("\n", "")
            csp_got = csp_got.replace("( ", "(")
            csp_got = csp_got.replace("{ ", "{")
            csp_got = csp_got.replace(",}", "}")
            csp_got = csp_got.replace(", }", "}")
            csp_got = csp_got.replace(" )", ")")
            csp_got = csp_got.strip()
            csp_got = _csp_unwrap_(csp_got)

        assert csp_got == csp_want, dict(csp_got=csp_got, csp_want=csp_want)


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
