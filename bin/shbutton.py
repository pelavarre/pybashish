#!/usr/bin/env python3

r"""
usage: shbutton.py [-h] [HINT [HINT ...]]

auto-complete the hints into a complete bash command line, trace it, and run it

positional arguments:
  HINT        code to run

optional arguments:
  -h, --help  show this help message and exit

quirks:
  works inside the os copy-paste clipboard, aka pasteboard, via "pbpaste" and "pbcopy"

calculator buttons:
  % * + , - / 0
  clst swap t x y z

download:
  git clone https://github.com/pelavarre/pybashish.git
  cd pybashish/
  git checkout pelavarre-patch-1
  export PATH="${PATH:+$PATH:}$PWD/bin"
  which shbutton.py

install into mac zsh:
  alias -- '%'='shbutton.py %'
  alias -- '*'='shbutton.py "*"'
  alias -- '+'='shbutton.py +'
  alias -- ','='shbutton.py ,'
  alias -- '-'='shbutton.py -'
  alias -- '/'='shbutton.py /'
  alias -- '0'='shbutton.py clear.clst'

install into mac bash:
  function / { shbutton.py / "$@"; }
  mkdir dir/
  cd dir/
  echo 'shbutton.py '"'*'"' "$@"' >\*
  chmod +x \*

complex examples:
  , clear.clst
  pbpaste
  , 0 12 + 3 - 4 / 5 \*
  , 5 4 3 12 0 forth.swap + swap - swap / swap \*
  , 11 22 33 44 t t t t

basic examples:
  0
  + 12
  - 3
  / 4
  * 5
"""

# TODO: announce first file dropped into "~/.pb_history/pb.bin~"
# TODO: traces revs of the pasteboard into the "~/.pb_history/" dir, if that dir exists
# TODO: count lines of input as args:1:...


import decimal
import pdb
import shlex
import subprocess
import sys

import argdoc


def b():
    pdb.set_trace()


def main(argv):
    """Run one split command line"""

    args = argdoc.parse_args()
    hints = args.hints

    pb_lines = resume_from_pb()

    pbc = PbCalculator(pb_lines)
    pbc.walk_argv(argv=([""] + hints))

    suspend_to_pb(pbc.pb_lines)


#
# Calculate, on demand
#


class PbCalculator:
    #

    def __init__(self, pb_lines):
        self.pb_lines = pb_lines
        self.walkers_by_name = self.init_walkers_by_name()

    def init_walkers_by_name(self):

        walkers_by_name = dict()

        walkers_by_name["*"] = self.on_asterisk
        walkers_by_name["+"] = self.on_plus_sign
        walkers_by_name[","] = self.on_comma
        walkers_by_name["-"] = self.on_hyphen_minus
        walkers_by_name["/"] = self.on_solidus

        walkers_by_name["clear.clst"] = self.clear_clst
        walkers_by_name["forth.swap"] = self.forth_swap
        walkers_by_name["x"] = self.we_pick_x
        walkers_by_name["y"] = self.we_pick_y
        walkers_by_name["z"] = self.we_pick_z
        walkers_by_name["t"] = self.we_pick_t

        precise_walker_items = sorted(walkers_by_name.items())
        for (precise, walker) in precise_walker_items:
            if "." in precise:
                if precise != ".":
                    loose = precise.split(".")[-1]
                    if loose not in walkers_by_name.keys():
                        walkers_by_name[loose] = walker

        return walkers_by_name

    def walk_argv(self, argv):

        # stderr_print(argv[1:])

        walkers_by_name = self.walkers_by_name

        shuffled_argv = [""] + argv[2:][:1] + argv[1:][:1] + argv[3:]
        # stderr_print("?", " ".join(shuffled_argv[1:]))

        for arg in shuffled_argv[1:]:

            try:
                if arg in walkers_by_name:
                    # stderr_print(arg)
                    walker = walkers_by_name[arg]
                    if walker == self.on_comma:
                        continue
                    else:
                        walker()
                        if walker == self.clear_clst:
                            continue
                else:
                    w = decimal.Decimal(arg)
                    self.we_push(w)
                    continue
            except Exception:
                stderr_print("shbutton: error: at {!r}".format(arg))
                raise

            if self.pb_lines:
                last = self.pb_lines[-1]
                if last is not None:
                    print(last)  # TODO: think over vs repr

    def clear_clst(self):
        self.pb_lines = list()

    def fill_decimal(self, depth):
        while len(self.pb_lines) < depth:
            self.pb_lines.append("0")

    def forth_swap(self):
        self.fill_decimal(2)
        y = self.pb_lines[-2]
        x = self.pb_lines[-1]
        self.pb_lines[-2] = x
        self.pb_lines[-1] = y

    def on_asterisk(self):
        self.fill_decimal(2)
        y = self.we_eval_y()
        x = self.we_eval_x()
        w = y * x
        self.we_pop(2)
        self.we_push(w)

    def on_comma(self):
        pass

    def on_hyphen_minus(self):
        self.fill_decimal(2)
        y = self.we_eval_y()
        x = self.we_eval_x()
        w = y - x
        self.we_pop(2)
        self.we_push(w)

    def on_plus_sign(self):
        self.fill_decimal(2)
        y = self.we_eval_y()
        x = self.we_eval_x()
        w = y + x
        self.we_pop(2)
        self.we_push(w)

    def on_solidus(self):
        self.fill_decimal(2)
        y = self.we_eval_y()
        x = self.we_eval_x()
        w = y / x
        self.we_pop(2)
        self.we_push(w)

    def we_eval_t(self):
        self.fill_decimal(4)
        t = decimal.Decimal(self.pb_lines[-4])
        return t

    def we_eval_x(self):
        self.fill_decimal(1)
        x = decimal.Decimal(self.pb_lines[-1])
        return x

    def we_eval_y(self):
        self.fill_decimal(2)
        y = decimal.Decimal(self.pb_lines[-2])
        return y

    def we_eval_z(self):
        self.fill_decimal(3)
        z = decimal.Decimal(self.pb_lines[-3])
        return z

    def we_pick_t(self):
        self.fill_decimal(4)
        self.pb_lines.append(self.pb_lines[-4])

    def we_pick_x(self):
        self.fill_decimal(1)
        self.pb_lines.append(self.pb_lines[-1])

    def we_pick_y(self):
        self.fill_decimal(2)
        self.pb_lines.append(self.pb_lines[-2])

    def we_pick_z(self):
        self.fill_decimal(3)
        self.pb_lines.append(self.pb_lines[-3])

    def we_pop(self, depth=1):
        for _ in range(depth):
            w = self.pb_lines.pop()
        return w

    def we_push(self, w):
        self.pb_lines.append(str(w))


#
# Work with the os copy-paste clipboard (aka pasteboard)
#


def resume_from_pb():
    """To get going again, read text lines from the pasteboard"""

    pb_chars_plus = subprocess_run_check_stdout_chars("pbpaste")
    pb_chars = strip_right_above_below(pb_chars_plus)
    pb_lines = pb_chars.splitlines()

    return pb_lines


def suspend_to_pb(pb_lines):
    """Just before taking a break, write text lines to the pasteboard"""

    pb_chars = strip_right_above_below("\n".join(pb_lines))
    pb_bytes = pb_chars.encode()

    argv = shlex.split("pbcopy")

    ran = subprocess.run(  # call for Stdin, without Stdout/err, with ReturnCode Zero
        argv,
        shell=False,
        input=pb_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    check(want=0, got=ran.returncode)
    check(want=b"", got=ran.stdout)
    check(want=b"", got=ran.stderr)


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
# TODO: push changes back out to other copies of KwargsException at CheckException
class KwargsException(Exception):
    """Raise the values of some vars"""

    def __init__(self, **kwargs):  # ordered since Dec/2016 CPython 3.6
        self.items = kwargs.items()

    def __str__(self):
        sketch = ", ".join("{}={!r}".format(*_) for _ in self.items)
        sketch = "({})".format(sketch)
        return sketch


# deffed in many files  # missing from docs.python.org
def check(goal=None, want=True, got=None, **kwargs):
    """Raise the values of vars most likely to explain our next failure well"""

    if isinstance(want, bool):
        happy = want is bool(got)
    else:
        happy = want == got

    if not happy:
        if goal:
            raise KwargsException(goal=goal, want=want, got=got, **kwargs)
        else:
            raise KwargsException(want=want, got=got, **kwargs)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def strip_right_above_below(chars):
    """Drop leading and trailing blank lines, and drop trailing spaces in each line"""

    lines_plus = chars.strip().splitlines()

    lines = list(_.rstrip() for _ in lines_plus)

    chars = ""
    if lines:
        chars = "\n".join(lines) + "\n"

    return chars


# deffed in many files  # missing from docs.python.org
def subprocess_run_check_stdout_chars(args):
    """Call for Stdout, without Stderr, with ReturnCode Zero"""

    argv = shlex.split(args)

    ran = subprocess.run(
        argv,
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    check(want=0, got=ran.returncode)
    check(want=b"", got=ran.stderr)

    fetched = ran.stdout.decode(errors="surrogateescape")

    return fetched


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
