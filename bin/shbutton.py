#!/usr/bin/env python3

r"""
usage: shbutton.py [-h] [HINT [HINT ...]]

auto-complete the hints, trace the completion, and run it

positional arguments:
  HINT        code to run

optional arguments:
  -h, --help  show this help message and exit

quirks:
  works inside the os copy-paste clipboard, aka pasteboard, via "pbpaste" and "pbcopy"

calculator buttons:
  % * ** + , - /

words:
  c d F k p r x y z
  clearstack dedent dent drop dup eng int lastx lower lstrip
  over rot upper rstrip strip swap upper

see also:
  https://docs.python.org/3/library/decimal.html
  https://en.wikipedia.org/wiki/Concatenative_programming_language
  https://unicode.org/charts/PDF/U0000.pdf

download:
  git clone https://github.com/pelavarre/pybashish.git
  cd pybashish/
  git checkout pelavarre-patch-1
  export PATH="${PATH:+$PATH:}$PWD/bin"
  which shbutton.py

install into mac zsh:
  alias -- '%'='shbutton.py %'
  alias -- '*'='shbutton.py "*"'
  alias -- '**'='shbutton.py "**"'
  alias -- '+'='shbutton.py +'
  alias -- ','='shbutton.py ,'
  alias -- '-'='shbutton.py -'
  alias -- '/'='shbutton.py /'
  alias -- '0'='shbutton.py clearstack'

install into mac bash:
  function / { shbutton.py / "$@"; }
  mkdir dir/
  cd dir/
  echo 'shbutton.py '"'*'"' "$@"' >\*
  chmod +x \*

contrast with:
  bash -c 'echo $(( (0 + 12 - 3) / 4 * 5 ))'  # small integer arithmetic
  dc -e '2 k  0 12 + p 3 - p 4 / p 5 * p'  # minimal vocabulary arithmetic
  (echo 1 1; echo d p sx + lx r p; echo d p sx + lx r p; cat -) | dc  # Fibonacci

stack examples:
  , clearstack 1 1
  , swap over + p  # Forth Fibonacci in two slots
  , + lastx swap p  # Hp Fibonacci in two slots
  , y y + F  # Fibonacci in O(N) slots
  , 1.1 2.2 + p  # decimal fixed point, not binary floating point
  , 0.30 0.20 + p  # significant trailing zeroes
  , 70 k  1 7 / p  # as many digits as you need
  , 123e1 eng p

text examples:
  echo '      a b c d e      ' | pbcopy
  , dedent F  # call "sed"
  , upper F  # call "tr"
  , .-1,.0,.-2,.1  # call "awk"
  pbpaste

math examples:
  0
  + 12
  - 3
  / 4
  * 5
  / 0.6 700
"""

# TODO: learn date lists - print as abs and rel, sum rels

# TODO: infer "-- " before negative numbers
# TODO: accept leading "_" skid in place of leading "-" dash
# TODO: accept hex int literals and << >> & | ^ bitwise ops
# TODO: accept '%1.3f' %
# TODO: accept '{:1.3f}' format
# TODO: default notations other than Python decimal engineering notation

# TODO: traces revs of the pasteboard into the "~/.pb_history/" dir, if that dir exists
# TODO: announce first file dropped into "~/.pb_history/pb.bin~"
# TODO: count (and blame) lines of input as shlines:1:...


import decimal
import pdb
import re
import shlex
import subprocess
import sys

import argdoc


HINTS_BY_HINT = dict()
HINTS_BY_HINT["%"] = "* p".split()
HINTS_BY_HINT["*"] = "* p".split()
HINTS_BY_HINT["**"] = "** p".split()
HINTS_BY_HINT["+"] = "+ p".split()
HINTS_BY_HINT["-"] = "- p".split()
HINTS_BY_HINT["/"] = "/ p".split()


def b():
    pdb.set_trace()


def main(argv):
    """Run one split command line"""

    args = argdoc.parse_args()

    hints = args.hints
    if hints:
        hint = hints[0]
        if hint in HINTS_BY_HINT:
            hints = args.hints[1:] + HINTS_BY_HINT[hint]
            if len(hints) > 2:
                stderr_print(", " + " ".join(hints))

    pb_lines = resume_from_pb()
    pbvm = PbVirtualMachine(pb_lines)

    pbvm.walk_hints(hints)

    suspend_to_pb(pbvm.pb_lines)


#
# Calculate, on demand
#


class PbVirtualMachine:
    "Work on one pasteboard"

    def __init__(self, pb_lines):
        self.hp_last_line = pb_lines[-1] if pb_lines else None
        self.pb_lines = pb_lines
        self.workers_by_name = self.init_workers_by_name()

    def init_workers_by_name(self):
        """Name the workers"""

        workers_by_name = dict()

        workers_by_name["%"] = self.on_percent_sign
        workers_by_name["*"] = self.on_asterisk
        workers_by_name["**"] = self.py_pow
        workers_by_name["+"] = self.on_plus_sign
        workers_by_name[","] = self.on_comma
        workers_by_name["-"] = self.on_hyphen_minus
        workers_by_name["/"] = self.on_solidus

        workers_by_name["dc.c"] = self.dc_clearstack  # ... --
        workers_by_name["dc.d"] = self.dc_dup  # x -- x x
        workers_by_name["dc.F"] = self.dc_cat
        workers_by_name["dc.k"] = self.dc_precision_put
        workers_by_name["dc.p"] = self.dc_dup_print
        workers_by_name["dc.r"] = self.dc_reverse_y_x  # y x -- x y  # aka swap

        workers_by_name["gforth.clearstack"] = self.gforth_clearstack  # ... --

        workers_by_name["forth.drop"] = self.forth_drop  # x --
        workers_by_name["forth.dup"] = self.forth_dup  # x -- x x
        workers_by_name["forth.over"] = self.forth_over  # y x -- y x y
        workers_by_name["forth.rot"] = self.forth_rot  # z y x -- y x z
        workers_by_name["forth.swap"] = self.forth_swap  # y x -- x y

        workers_by_name["hp.clst"] = self.hp_clst  # ... --
        workers_by_name["hp.lastx"] = self.hp_lastx
        workers_by_name["hp.x"] = self.hp_x  # x -- x x
        workers_by_name["hp.y"] = self.hp_y  # y x -- y x y
        workers_by_name["hp.z"] = self.hp_z  # z y x -- z y x z  # aka rot-without-pop-z

        #       workers_by_name["py.math.e"] = self.py_math_e e  # TODO: add these
        #       workers_by_name["py.math.pi"] = self.py_math_pi π
        workers_by_name["py.eng"] = self.py_eng
        workers_by_name["py.int"] = self.py_int

        workers_by_name["sed.py.dedent"] = self.sed_py_dedent
        workers_by_name["sed.py.dent"] = self.sed_py_dent
        workers_by_name["sed.py.lstrip"] = self.sed_py_lstrip
        workers_by_name["sed.py.rstrip"] = self.sed_py_rstrip
        workers_by_name["sed.py.strip"] = self.sed_py_strip

        workers_by_name["tr.py.lower"] = self.tr_py_lower
        workers_by_name["tr.py.upper"] = self.tr_py_upper

        precise_worker_items = sorted(workers_by_name.items())
        for (precise, worker) in precise_worker_items:
            if "." in precise:
                if precise != ".":
                    loose = precise.split(".")[-1]
                    if loose not in workers_by_name.keys():
                        workers_by_name[loose] = worker
        # TODO: drop the collisions

        return workers_by_name

    def walk_hints(self, hints):
        """Interpret each hint in turn"""

        workers_by_name = self.workers_by_name

        for hint in hints:

            try:
                if hint in workers_by_name:
                    worker = workers_by_name[hint]
                    worker()
                elif re.match(r"^([.][-+]?[0-9]+)([,][.][-+]?[0-9]+)*", string=hint):
                    self.awk_column_picker(hint)
                else:
                    w = decimal.Decimal(hint)
                    self.push_one_decimal(w)
            except Exception:
                stderr_print("shbutton: error: at {!r}".format(hint))
                raise

    def awk_column_picker(self, hint):
        """Call Awk to reorder or dupe columns, while dropping the rest"""

        fetches = list()
        for str_index in hint.split(","):
            check(got=str_index.startswith("."), str_index=str_index)

            index = int(str_index[len(".") :])
            if index < 0:
                if index == -1:
                    fetch = "$NF"
                else:
                    fetch = "$(NF-{})".format(-1 - index)
            else:
                fetch = "${}".format(1 + index)

            fetches.append(fetch)

        awk = ", ".join(fetches)
        self.pipe_through("awk '//{print " + awk + "}'")

    def dc_cat(self):
        """Print a copy of all lines in order (not reversed like Dc "f")"""

        # self.pipe_through("tee /dev/stderr")
        for line in self.pb_lines:
            stderr_print(line)

    def dc_dup(self):  # x -- x x
        """Repeat the last line"""

        self.pb_lines.append(self.pb_lines[-1])

    def dc_dup_print(self):
        """Print a copy of the last line"""

        line = self.pb_lines[-1]  # a la Bash:  pbpaste | tail -1
        print(line)

    def dc_clearstack(self):  # ... --
        """Drop all the lines"""

        self.pb_lines = list()

    def dc_precision_put(self):
        """Reconfigure how many decimal digits to work with"""

        (x,) = self.pop_some_decimals(1)

        int_x = int(x)
        check(want=int_x, got=x)

        decimal.getcontext().prec = int_x

    def dc_reverse_y_x(self):  # y x -- x y
        """Rewrite the end as Q P in place of P Q"""

        y = self.pb_lines[-2]
        x = self.pb_lines[-1]
        self.pb_lines[-2] = x
        self.pb_lines[-1] = y

    def forth_drop(self):
        """Lose the last line"""

        _ = self.pb_lines.pop()

    def forth_dup(self):  # x -- x x
        """Repeat the last line"""

        self.pb_lines.append(self.pb_lines[-1])

    def forth_over(self):  # y x -- y x y
        """End with a copy of the second-to-last line"""

        self.pb_lines.append(self.pb_lines[-2])

    def forth_rot(self):  # z y x -- y x z
        """Rewrite the end as Q R P in place of P Q R"""

        z = self.pb_lines[-3]
        y = self.pb_lines[-2]
        x = self.pb_lines[-1]
        self.pb_lines[-3] = y
        self.pb_lines[-2] = x
        self.pb_lines[-1] = z

    def forth_swap(self):  # y x -- x y
        """Rewrite the end as Q P in place of P Q"""

        y = self.pb_lines[-2]
        x = self.pb_lines[-1]
        self.pb_lines[-2] = x
        self.pb_lines[-1] = y

    def gforth_clearstack(self):  # ... --
        """Drop all the lines"""

        self.pb_lines = list()

    def hp_clst(self):  # ... --
        """Drop all the lines"""

        self.pb_lines = list()

    def hp_lastx(self):
        """Recall the line that was the last involved in arithmetic"""

        self.pb_lines.append(self.hp_last_line)

    def hp_x(self):  # x -- x
        """Repeat the last line"""

        self.pb_lines.append(self.pb_lines[-1])

    def hp_y(self):  # y x -- y x y
        """End with a copy of the second-to-last line"""

        self.pb_lines.append(self.pb_lines[-2])

    def hp_z(self):  # z y x -- z y x z
        """End with a copy of the third-to-last line"""

        self.pb_lines.append(self.pb_lines[-3])

    def on_asterisk(self):
        """Multiply the last two lines"""

        (y, x) = self.pop_some_decimals(2)
        w = y * x
        self.push_one_decimal(w)

    def on_comma(self):
        """Gracefully do nothing"""

    def on_hyphen_minus(self):
        """Subtract the last two lines"""

        (y, x) = self.pop_some_decimals(2)
        w = y - x
        self.push_one_decimal(w)

    def on_percent_sign(self):
        """Divide the last two lines, keep the remainder, drop the quotient"""

        (y, x) = self.pop_some_decimals(2)
        w = y % x
        self.push_one_decimal(w)

    def on_plus_sign(self):
        """Add the last two lines"""

        (y, x) = self.pop_some_decimals(2)
        w = y + x
        self.push_one_decimal(w)

    def on_solidus(self):
        """Divide the last two lines, keep the quotient, drop the remainder"""

        (y, x) = self.pop_some_decimals(2)
        w = y / x
        self.push_one_decimal(w)

    def pipe_through(self, shline):
        """Pass all the lines through a Shell Pipe"""

        pb_chars = strip_right_above_below("\n".join(self.pb_lines))
        shinput = pb_chars.encode()

        stderr_print("+", shline)
        argv = shlex.split(shline)
        ran = subprocess.run(
            argv,
            shell=False,
            input=shinput,
            stdout=subprocess.PIPE,
            stderr=None,  # let my people trace their work
            check=True,
        )
        check(want=0, got=ran.returncode)

        pb_chars_plus = ran.stdout.decode(errors="surrogateescape")
        pb_chars = strip_right_above_below(pb_chars_plus)
        pb_lines = pb_chars.splitlines()

        self.pb_lines = pb_lines

    def decimal_or_exit(self, chars):
        try:
            arg = decimal.Decimal(chars)
        except Exception:
            shards = chars.split()
            starter = "{} ...".format(" ".join(shards[:2]))
            handwave = chars if (len(shards) < 3) else starter
            stderr_print(
                "shbutton.py: error: want decimal digits, got {!r}".format(handwave)
            )
            sys.exit(1)
        return arg

    def pop_some_decimals(self, depth=1):
        """Take one or more of the trailing lines as decimals"""

        check(got=(depth > 0), depth=depth)

        decimals = list()
        for _ in range(depth):
            line = self.pb_lines.pop() if self.pb_lines else "0"
            w = self.decimal_or_exit(line)
            decimals.insert(0, w)

        check(want=depth, got=len(decimals))
        self.hp_last_line = str(decimals[-1])

        return decimals

    def push_one_decimal(self, w):
        """Add one decimal as the trailing line"""

        self.pb_lines.append(str(w))

    def py_eng(self):
        """Replace the last line with its decimal value in engineering notation"""

        (x,) = self.pop_some_decimals(1)
        w = x.to_eng_string()
        self.push_one_decimal(w)

    def py_int(self):
        """Replace the last line with its int floor"""

        (x,) = self.pop_some_decimals(1)
        w = int(x)
        self.push_one_decimal(w)

    def py_pow(self):
        """Replace the last two lines with the second to last raised to the first"""

        (y, x) = self.pop_some_decimals(2)
        w = y ** x
        self.push_one_decimal(w)

    def sed_py_dedent(self):
        """Strip four spaces or none from the left of each line"""

        # self.pipe_through("""awk '//{sub("^    ", ""); print}'""")
        self.pipe_through("sed 's,^    ,,'")

    def sed_py_dent(self):
        """Insert four spaces at the left of each line"""

        # self.pipe_through("""awk '//{sub("^", "    "); print}'""")
        self.pipe_through("sed 's,^,    ,'")

    def sed_py_lstrip(self):
        """Drop the leading spaces from the left of each line"""

        # self.pipe_through("""awk '//{sub("^  *", ""); print}'""")
        self.pipe_through("sed 's,^ *,,'")

    def sed_py_rstrip(self):
        """Drop the trailing spaces from the right of each line"""

        stderr_print("shbutton.py: warning: shbuttons rstrip by default")
        # self.pipe_through("""awk '//{sub("  *$", ""); print}'""")
        self.pipe_through("sed 's, *$,,'")

    def sed_py_strip(self):
        """Drop the leading and trailing spaces from the left and right of each line"""

        stderr_print("shbutton.py: warning: shbutton lstrip is strip")
        # self.pipe_through("""awk '//{sub("^  *", "");sub("^  *", ""); print}'""")
        self.pipe_through("sed -E 's,^ *| *$,,g'")

    def tr_py_lower(self):
        """Lowercase every character of every line"""

        self.pipe_through("tr '[:upper:]' '[:lower:]'")

    def tr_py_upper(self):
        """Uppercase every character of every line"""

        self.pipe_through("tr '[:lower:]' '[:upper:]'")


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
    shinput = pb_chars.encode()

    argv = shlex.split("pbcopy")

    ran = subprocess.run(  # call for Stdin, without Stdout/err, with ReturnCode Zero
        argv,
        shell=False,
        input=shinput,
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

    lines_plus = chars.splitlines()

    lines = list(_.rstrip() for _ in lines_plus)

    while lines and not lines[0]:
        lines = lines[1:]
    while lines and not lines[-1]:
        lines = lines[:-1]

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
