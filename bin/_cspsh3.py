#!/usr/bin/env python3

r"""
usage: _cspsh3.py [-h] [-c COMMAND]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit
  -c COMMAND  take the command as the only input, else as the first input before -i

examples:
  _cspsh3.py
  _cspsh3.py -c'VMCT = µ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))'
  _cspsh3.py -c'coin → (choc → X | toffee → X)'
"""


import argparse
import collections
import inspect
import pdb
import re

import argdoc


DEFAULT_CSP_CHARS = (
    "VMCT = µ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))"
)


def b():
    pdb.set_trace()


def parse_csp_chars(csp_chars):  # noqa: C901
    # note: Flake8 miscounts a grammar of 15 "def", "while", "if" as "too complex"

    # accept mutations of a copy of the chars

    mutable = argparse.Namespace(chars=csp_chars)

    # collect the matches

    arg_lists_by_depth = collections.defaultdict(list)

    # to parse the grammar, mutually recursively descend the call stack

    def command():
        ok = definition() or process()
        return collect(ok)

    def definition():
        ok = is_before("=")
        ok = ok and process_name() and mark("=") and process_body()
        return collect(ok)

    def process_body():
        ok = process_with_such() or process()
        return collect(ok)

    def process_with_such():
        ok = mark("µ") and process_name()
        _ = ok and mark(":") and alphabet()
        ok = ok and mark("•") and process()
        return collect(ok)

    def alphabet():
        ok = mark("{")
        while event_name():
            if not mark(","):
                break
        ok = ok and mark("}")
        return collect(ok)

    def process():
        ok = choice() or process_tail()
        return collect(ok)

    def choice():
        ok = guarded_process()
        while ok and mark("|") and guarded_process():
            pass
        return collect(ok)

    def guarded_process():
        ok = event_name() and mark("→")
        while ok and is_before("→"):
            _ = event_name() and mark("→")
        ok = ok and process_tail()
        return collect(ok)

    def process_tail():
        ok = anonymous_process() or process_name()
        return collect(ok)

    def anonymous_process():
        ok = mark("(") and process() and mark(")")
        return collect(ok)

    # lex the matches

    def mark(want):
        ok = marking(want)
        return collect(ok)

    def marking(want):
        if mutable.chars.startswith(want):

            # arg = repr(mutable.chars[: len(want)])
            arg = mutable.chars[: len(want)]
            mutable.chars = mutable.chars[len(want) :]

            arg_lists_by_depth[call_depth()].append(arg)
            return True

    def process_name():
        ok = match(r"^_*[A-Z]+[0-9.A-Za-z_]*")
        return collect(ok)

    def event_name():
        ok = match(r"^_*[a-z]+[0-9.A-Za-z_]*")
        return collect(ok)

    def match(regex):
        match = re.match(regex, string=mutable.chars)
        if match:

            # arg = repr(mutable.chars[: match.end()])
            arg = mutable.chars[: match.end()]
            mutable.chars = mutable.chars[match.end() :]

            arg_lists_by_depth[call_depth()].append(arg)
            return True

    # define the abbreviations spoken above

    def call_depth():

        f = inspect.currentframe()

        depth = 0
        while f.f_back:
            depth += 1
            f = f.f_back

        return depth

    def collect(ok):

        f = inspect.currentframe()
        f = f.f_back
        co_name = f.f_code.co_name

        depth_here = call_depth()

        values = list()
        for depth in list(arg_lists_by_depth.keys()):
            assert depth <= depth_here
            if depth == depth_here:
                values = arg_lists_by_depth[depth]
                del arg_lists_by_depth[depth]

        if not ok:
            return

        lstrip()

        depth_above = depth_here - 1
        # arg_above = dict([(co_name, values)])
        arg_above = [co_name] + values
        # arg_above = "{}({})".format(co_name, ", ".join(values))
        # print(ok, depth_here, arg_above, file=sys.stderr)

        arg_lists_by_depth[depth_above].append(arg_above)

        return ok

    def collect_top_arg():

        depths = list(arg_lists_by_depth.keys())
        assert len(depths) == 1
        top_depth = depths[-1]

        top_args = arg_lists_by_depth[top_depth]
        assert len(top_args) == 1
        top_arg = top_args[-1]

        return top_arg

    def is_before(want):

        regex = r"^ *_*[A-Za-z]+[0-9.A-Za-z_]* *{}".format(want)
        match = re.match(regex, string=mutable.chars)

        return match

    def lstrip():

        while mutable.chars.startswith(" "):
            mutable.chars = mutable.chars[len(" ") :]

    print()

    print(csp_chars)
    print()

    lstrip()
    command()
    top_arg = collect_top_arg()

    # with open("p.py", "w") as outgoing:
    #     outgoing.write(str(top_arg))

    def print_list(dent, values):
        if (len(values) == 2) and not isinstance(values[-1], list):
            print("{}{}".format(dent, values))
        else:
            print("{}[{!r},".format(dent, values[0]))
            inner_dent = dent + "    "
            for value in values[1:]:
                value_list = value
                print_list(inner_dent, value_list)
            print("{}]".format(dent))

    print_list("", top_arg)

    print()


args = argdoc.parse_args()
csp_chars = args.command if args.command else DEFAULT_CSP_CHARS
parse_csp_chars(csp_chars)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
