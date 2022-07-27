#!/usr/bin/env python3

r"""
usage: _shbutton.py [-h] [HINT ...]

auto-complete the hints, trace the completion, and run it

positional arguments:
  HINT        code to run

options:
  -h, --help  show this help message and exit

quirks:
  works inside the os copy-paste clipboard, aka pasteboard, via "pbpaste" and "pbcopy"

calculator buttons:
  % * ** + - /

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
  git checkout main  # unneeded if new clone
  export PATH="${PATH:+$PATH:}$PWD/bin"
  which _shbutton.py

install into mac zsh:
  alias -- '%'='_shbutton.py %'
  alias -- '*'='_shbutton.py "*"'
  alias -- '**'='_shbutton.py "**"'
  alias -- '+'='_shbutton.py +'
  alias -- ','='_shbutton.py ,'
  alias -- '-'='_shbutton.py -'
  alias -- '/'='_shbutton.py /'
  alias -- '0'='_shbutton.py clearstack'

install into mac bash:
  function / { _shbutton.py / "$@"; }
  mkdir dir/
  cd dir/
  echo '_shbutton.py '"'*'"' "$@"' >\*
  chmod +x \*

contrast with:
  bash -c 'echo $(( (0 + 12 - 3) / 4 * 5 ))'  # small integer arithmetic
  dc -e '2 k  0 12 + p 3 - p 4 / p 5 * p'  # minimal vocabulary arithmetic
  (echo 1 1; echo d p sx + lx r p; echo d p sx + lx r p; cat -) |dc  # Fibonacci

examples:

  , clearstack 1 1
  , swap over + p  # Forth Fibonacci in two slots
  , + lastx swap p  # Hp Fibonacci in two slots
  , y y + F  # Fibonacci in O(N) slots
  , 1.1 2.2 + p  # decimal fixed point, not binary floating point
  , 0.30 0.20 + p  # significant trailing zeroes
  , 70 k  1 7 / p  # as many digits as you need
  , 123e1 p

  echo '      a b c d e      ' |pbcopy
  , dedent F  # call "sed"
  , upper F  # call "tr"
  , .-1,.0,.-2,.1  # call "awk"
  pbpaste

  , c 8:00 0:12:01.123456 17:00 '13 17:00' 1h12m 6m 23h F

  , 0 \~ p 0x5a \~ p 0xff \& p 0XA \| p 1 15 \<\< p 1 \>\> p
  , '0 ~ p 0x5a ~ p 0xff & p 0XA | p 1 15 << p 1 >> p' eval

  0
  + 12
  - 3
  / 4
  * 5
  / 0.6 700
"""

# TODO: stash a stack of paste - like collect paste now as input of next command
# pbpaste >a; read SHLINE; <a pbcopy; source <(echo "$SHLINE")


# TODO: add word "ruler" a la fmt.py --ruler
# TODO: add word "keycaps" a la read.py -h
# TODO: fill out the abs and rel date-time-stamps at left of a line

# TODO: add words:  float format %
# TODO: accept leading "_" skid in place of leading "-" dash
# TODO: count (and blame) lines of input as shlines:1:...
# TODO: configure str_decimal str_int

# TODO: traces revs of the pasteboard into the "~/.pb_history/" dir, if that dir exists
# TODO: announce first file dropped into "~/.pb_history/pb.bin~"


import argparse
import collections
import datetime as dt
import decimal
import math
import pdb
import re
import shlex
import subprocess
import sys

import argdoc


ONE_DECIMAL = r"[-+]?[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?"

ONE_HEXADECIMAL = r"[-+]?0[Xx][0-9A-Fa-f]+"

ONE_INDEX = r"[.][-+]?[0-9]+"

SOME_INDICES = r"{}([,]{})+".format(ONE_INDEX, ONE_INDEX)

ONE_INTERVAL = (
    r"([0-9]+)" + r"([YZEPTGMKkmµunpfazy])?" + r"([hms])"  # \u00B5 micro-sign
)

SOME_INTERVALS = r"({})+".format(ONE_INTERVAL)

ONE_MOMENT_FORMATS = (
    r"%Y-%m-%d %H:%M:%S",
    r"%Y-%m-%d %H:%M",
    r"%Y-%m-%d %H",
    r"%y-%m-%d %H:%M:%S",
    r"%y-%m-%d %H:%M",
    r"%y-%m-%d %H",
    r"%m-%d %H:%M:%S",
    r"%m-%d %H:%M",
    r"%m-%d %H",
    r"%d %H:%M:%S",
    r"%d %H:%M",
    r"%d %H",
    r"%H:%M",
    r"%H:%M:%S",
)

ONE_MOMENT = (
    r"|".join(ONE_MOMENT_FORMATS)
    .replace(r" ", r"[ T]")  # ISO 8601 accepts only "T" not also " " space
    .replace(r"%H", r"([0-9][0-9]?)")
    .replace(r"%M", r"([0-9][0-9]?)")
    .replace(r"%S", r"([0-9][0-9]?([.][0-9]+)?)")
    .replace(r"%Y", r"([0-9][0-9][0-9][0-9])")
    .replace(r"%d", r"([0-9][0-9]?)")
    .replace(r"%m", r"([0-9][0-9]?)")
    .replace(r"%y", r"([0-9][0-9])")
)

ONE_HINT_REGEX = (
    r"^("
    + r"(?P<decimal>{})".format(ONE_DECIMAL)
    + r"|"
    + r"(?P<hexadecimal>{})".format(ONE_HEXADECIMAL)
    + r"|"
    + r"(?P<indices>{})".format(SOME_INDICES)
    + r"|"
    + r"(?P<interval>{})".format(SOME_INTERVALS)
    + r"|"
    + r"(?P<moment>{})".format(ONE_MOMENT)
    + r")$"
)


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

    argv_tail = list()
    for (index, arg) in enumerate(argv):
        if index:

            if arg == "--":  # accept negated numbers as not dash options
                argv_tail.extend(argv[index:])
                break

            if re.match(r"^[-]?[0-9]", string=arg):
                argv_tail.append("--")
                argv_tail.extend(argv[index:])
                break

            argv_tail.append(arg)

    # if argv_tail != argv[1:]:
    #     stderr_print("+ , {}".format(shlex.join(argv_tail)))

    args = argdoc.parse_args(argv_tail)

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
        self.era = dt.datetime.now()
        self.hp_last_line = None
        self.multipliers_by_code = self.init_multipliers_by_code()
        self.pb_lines = pb_lines
        self.workers_by_name = self.init_workers_by_name()
        self.workers_by_syntax = self.init_workers_by_syntax()

    def init_multipliers_by_code(self):

        multipliers_by_code = dict()

        for (index, code) in enumerate(".kMGTPEZY"):
            if code != ".":
                multipliers_by_code[code] = 10 ** (3 * index)

        for (index, code) in enumerate(".munpfazy"):
            if code != ".":
                multipliers_by_code[code] = 10 ** (-3 * index)

        multipliers_by_code["K"] = 10**3
        multipliers_by_code["µ"] = 10**-6  # \u00B5 micro-sign

        return multipliers_by_code

    def init_workers_by_name(self):
        """Name the workers who work the "pb_lines" stack"""

        workers_by_name = dict()

        workers_by_name["%"] = self.on_percent_sign
        workers_by_name["*"] = self.on_asterisk
        workers_by_name["**"] = self.py_pow
        workers_by_name["+"] = self.on_plus_sign
        workers_by_name[","] = self.on_comma
        workers_by_name["-"] = self.on_hyphen_minus
        workers_by_name["/"] = self.on_solidus

        workers_by_name["&"] = self.on_ampersand
        workers_by_name["<<"] = self.py_left_shift
        workers_by_name[">>"] = self.py_right_shift
        workers_by_name["^"] = self.on_circumflex_accent
        workers_by_name["|"] = self.on_vertical_line
        workers_by_name["^"] = self.on_circumflex_accent
        workers_by_name["~"] = self.on_tilde

        workers_by_name["bash.eval"] = self.bash_eval

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

        workers_by_name["py.math.e"] = self.py_math_e
        workers_by_name["py.math.pi"] = self.py_math_pi
        workers_by_name["py.math.π"] = self.py_math_pi
        workers_by_name["py.hex"] = self.py_hex
        workers_by_name["py.int"] = self.py_int

        workers_by_name["sed.py.dedent"] = self.sed_py_dedent
        workers_by_name["sed.py.dent"] = self.sed_py_dent
        workers_by_name["sed.py.lstrip"] = self.sed_py_lstrip
        workers_by_name["sed.py.rstrip"] = self.sed_py_rstrip
        workers_by_name["sed.py.strip"] = self.sed_py_strip

        workers_by_name["tr.py.lower"] = self.tr_py_lower
        workers_by_name["tr.py.upper"] = self.tr_py_upper

        workers_by_loose = collections.defaultdict(list)
        precise_worker_items = sorted(workers_by_name.items())
        for (precise, worker) in precise_worker_items:
            if "." in precise:
                if precise != ".":
                    loose = precise.split(".")[-1]
                    workers_by_loose[loose].append(worker)

        for (loose, workers) in sorted(workers_by_loose.items()):
            if len(workers) == 1:
                worker = workers[-1]
                if loose in workers_by_name.keys():
                    del workers_by_name[loose]
                    assert False  # untested in the early days
                else:
                    workers_by_name[loose] = worker

        return workers_by_name

    def init_workers_by_syntax(self):
        """Name the workers who parse hints"""

        workers_by_syntax = dict()

        workers_by_syntax["decimal"] = self.work_decimal_hint
        workers_by_syntax["hexadecimal"] = self.work_hexadecimal_hint
        workers_by_syntax["interval"] = self.work_interval_hint
        workers_by_syntax["indices"] = self.work_indices_hint
        workers_by_syntax["moment"] = self.work_moment_hint
        workers_by_syntax["str"] = self.work_str_hint

        return workers_by_syntax

    def bash_eval(self):
        """Eval the last line as if it were the arguments of a command line"""

        line = self.pb_lines.pop()
        argv = shlex.split(line)
        self.walk_hints(hints=argv)  # argv[:], not argv[1:]

    def walk_hints(self, hints):
        """Interpret each hint in turn"""

        for hint in hints:
            worker = self.find_worker(hint)
            try:
                worker()
            except Exception:
                # TODO: trace last few of self.pb_lines
                stderr_print("_shbutton.py: error: at {!r}".format(hint))
                raise

    def find_worker(self, hint):
        """Interpret one hint"""

        self.hint = hint

        workers_by_syntax = self.workers_by_syntax
        workers_by_name = self.workers_by_name

        key = None
        match = re.match(ONE_HINT_REGEX, string=hint)
        if match:
            keys = list(k for (k, v) in match.groupdict().items() if v)
            if keys:
                check(want=1, got=len(keys), keys=keys)
                key = keys[-1]

        worker = None
        if key:
            worker = workers_by_syntax[key]
        elif hint in workers_by_name.keys():
            worker = workers_by_name[hint]
        else:
            worker = workers_by_syntax["str"]

        return worker

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

        line = self.pb_lines[-1]  # a la Bash:  pbpaste |tail -1
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

    def eval_decimal(self, chars):
        """Convert to decimal.Decimal from str, else from str of int, else exit"""

        try:
            arg = decimal.Decimal(chars)
        except Exception:
            try:
                base_0 = 0
                arg = decimal.Decimal(int(chars, base_0))
            except Exception:
                shards = chars.split()
                starter = "{} ...".format(" ".join(shards[:2]))
                handwave = chars if (len(shards) < 3) else starter
                stderr_print(
                    "_shbutton.py: error: want decimal, got {!r}".format(handwave)
                )
                sys.exit(1)

        return arg

    def eval_int(self, chars):
        """Convert to int from str, else exit"""

        try:
            base_0 = 0
            arg = int(chars, base_0)
        except Exception:
            stderr_print("_shbutton.py: error: want int, got {!r}".format(chars))
            sys.exit(1)

        return arg

    def eval_interval_hint(self, hint):
        """Convert to dt.timedelta from str, else raise exception"""

        multipliers_by_code = self.multipliers_by_code
        codes = sorted(multipliers_by_code.keys())

        regex = (
            r"(?P<digits>[0-9]+)"
            + r"(?P<multiplier>[{}])?".format("".join(codes))
            + r"(?P<unit>[hms])"
        )

        matches = list(re.finditer(regex, string=hint))
        check(got=matches)

        interval = dt.timedelta()
        for match in matches:
            parts = match.groupdict()

            digits = parts["digits"]
            multiplicand = int(digits)

            multiplier_code = parts["multiplier"]
            multiplier = 1
            if multiplier_code in codes:
                multiplier = multipliers_by_code[multiplier_code]

            multiplied = multiplier * multiplicand

            unit = parts["unit"]
            if unit == "h":
                interval += dt.timedelta(hours=multiplied)
            elif unit == "m":
                interval += dt.timedelta(minutes=multiplied)
            else:
                check(want="s", got=unit)
                interval += dt.timedelta(seconds=multiplied)

        return interval

    def eval_moment_hint(self, era, hint):
        """Expand an abbreviated moment into the year-month-day hour of now"""

        (moment_, format_) = self._find_moment_format(hint)
        moment = self._pin_moment(era, moment_=moment_, format_=format_, hint=hint)

        return moment

    def _find_moment_format(self, hint):
        """Convert the hint to a partial moment of a particular format"""

        chars = hint
        if "." in hint:
            check(want=1, got=hint.count("."))
            chars = hint.split(".")[0]

        formats = list()
        moments = list()
        for format_ in ONE_MOMENT_FORMATS:
            try:
                moment_ = dt.datetime.strptime(chars, format_)
            except Exception:
                continue
            formats.append(format_)
            moments.append(moment_)

        check(want=1, got=len(moments), moments=moments)
        format_ = formats[-1]
        moment_ = moments[-1]

        return (moment_, format_)

    def _pin_moment(self, era, moment_, format_, hint):
        """Fit the partial moment to the year-month-day hour of now"""

        moment = era.replace(microsecond=0)
        parts = format_.replace("-", " ").replace(":", "  ").split()
        for part in parts:
            if part == "%Y":
                moment = moment.replace(year=moment_.year)
            elif part == "%y":
                moment = moment.replace(year=moment_.year)
            elif part == "%m":
                moment = moment.replace(month=moment_.month)
            elif part == "%d":
                moment = moment.replace(day=moment_.day)
            elif part == "%H":
                moment = moment.replace(hour=moment_.hour, minute=0, second=0)
            elif part == "%M":
                moment = moment.replace(minute=moment_.minute, second=0)
            elif part == "%S":
                moment = moment.replace(second=moment_.second)

        if "." in hint:
            check(got=("%S" in parts))
            digits = hint.split(".")[-1]
            check(got=(len(digits) <= 6), digits=digits)
            digits_plus = digits + "000" + "000"
            microsecond = int(digits_plus[:6])
            moment = moment.replace(microsecond=microsecond)

        return moment

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

    def on_ampersand(self):
        """Replace the last two lines, seen as hex ints, by and'ing their bits"""

        (y, x) = self.pop_some_ints(2)
        w = y & x
        self.push_one_hexadecimal(w)

    def on_asterisk(self):
        """Multiply the last two lines, seen as decimals"""

        (y, x) = self.pop_some_decimals(2)
        w = y * x
        self.push_one_decimal(w)

    def on_circumflex_accent(self):
        """Replace the last two lines, seen as hex ints, by xor'ing their bits"""

        (y, x) = self.pop_some_ints(2)
        w = y ^ x
        self.push_one_hexadecimal(w)

    def on_tilde(self):
        """Replace the last line, seen as a hex int, by flip its bits"""

        (x,) = self.pop_some_ints(1)
        w = ~x
        self.push_one_hexadecimal(w)

    def on_vertical_line(self):
        """Replace the last two lines, seen as hex ints, by or'ing their bits"""

        (y, x) = self.pop_some_ints(2)
        w = y | x
        self.push_one_hexadecimal(w)

    def on_comma(self):
        """Gracefully do nothing"""

    def on_hyphen_minus(self):
        """Subtract the last two lines, seen as decimals"""

        (y, x) = self.pop_some_decimals(2)
        w = y - x
        self.push_one_decimal(w)

    def on_percent_sign(self):
        """Divide the last two lines, keep the remainder, drop the quotient"""

        (y, x) = self.pop_some_decimals(2)
        w = y % x
        self.push_one_decimal(w)

    def on_plus_sign(self):
        """Add the last two lines, seen as decimals"""

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
        shinput_bytes = pb_chars.encode()

        stderr_print("+", shline)
        argv = shlex.split(shline)
        ran = subprocess_run(
            argv,
            shell=False,
            input=shinput_bytes,
            stdout=subprocess.PIPE,
            stderr=None,  # let my people trace their work
            check=True,
        )
        check(want=0, got=ran.returncode)

        pb_chars_plus = ran.stdout.decode(errors="surrogateescape")
        pb_chars = strip_right_above_below(pb_chars_plus)
        pb_lines = pb_chars.splitlines()

        self.pb_lines = pb_lines

    def pop_some_decimals(self, depth=1):
        """Take one or more of the trailing lines as decimals"""

        check(got=(depth > 0), depth=depth)

        decimals = list()
        for _ in range(depth):
            line = self.pb_lines.pop() if self.pb_lines else "0"
            w = self.eval_decimal(line)
            decimals.insert(0, w)

        check(want=depth, got=len(decimals))
        self.hp_last_line = self.str_decimal(decimals[-1])

        return decimals

    def pop_some_ints(self, depth=1):
        """Take one or more of the trailing lines as ints"""

        check(got=(depth > 0), depth=depth)

        ints = list()
        for _ in range(depth):
            line = self.pb_lines.pop() if self.pb_lines else "0"
            w = self.eval_int(line)
            ints.insert(0, w)

        check(want=depth, got=len(ints))
        self.hp_last_line = self.str_int(ints[-1])

        return ints

    def push_one_decimal(self, w):
        """Add one decimal as the trailing line"""

        self.pb_lines.append(self.str_decimal(w))

    def push_one_hexadecimal(self, w):
        """Add one hexadecimal as the trailing line"""

        self.pb_lines.append(self.str_int(w))

    def py_hex(self):
        """Replace the last line with the hex of its int floor"""

        self.py_int()
        self.pb_lines[-1] = hex(int(self.pb_lines[-1]))

    def py_int(self):
        """Replace the last line with its int floor"""

        try:
            (x,) = self.pop_some_ints(1)
        except Exception:
            (x,) = self.pop_some_decimals(1)

        (x,) = self.pop_some_decimals(1)
        w = int(x)
        self.push_one_decimal(w)

    def py_left_shift(self):
        """Replace the last two lines, seen as hex ints, by shifting y left by x"""

        (y, x) = self.pop_some_ints(2)
        w = y << x
        self.push_one_hexadecimal(w)

    def py_math_e(self):
        """Add an approximate copy of Euler's number"""

        w = math.e
        self.push_one_decimal(w)

    def py_math_pi(self):
        """Add an approximate copy of Pi"""

        w = math.pi
        self.push_one_decimal(w)

    def py_pow(self):
        """Replace the last two lines with the second to last raised to the first"""

        (y, x) = self.pop_some_decimals(2)
        w = y**x
        self.push_one_decimal(w)

    def py_right_shift(self):
        """Replace the last two lines, seen as hex ints, by shifting y right by x"""

        (y, x) = self.pop_some_ints(2)
        w = y >> x
        self.push_one_hexadecimal(w)

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

        stderr_print("_shbutton.py: warning: shbuttons rstrip by default")
        # self.pipe_through("""awk '//{sub("  *$", ""); print}'""")
        self.pipe_through("sed 's, *$,,'")

    def sed_py_strip(self):
        """Drop the leading and trailing spaces from the left and right of each line"""

        stderr_print("_shbutton.py: warning: shbutton lstrip is strip")
        # self.pipe_through("""awk '//{sub("^  *", "");sub("^  *", ""); print}'""")
        self.pipe_through("sed -E 's,^ *| *$,,g'")

    def str_decimal(self, w):
        """Format a decimal to stack it"""

        chars = w.to_eng_string()
        return chars

    def str_int(self, w):
        """Format an int to stack it"""

        chars = hex(w).upper().replace("X", "x")
        return chars

    def tr_py_lower(self):
        """Lowercase every character of every line"""

        self.pipe_through("tr '[:upper:]' '[:lower:]'")

    def tr_py_upper(self):
        """Uppercase every character of every line"""

        self.pipe_through("tr '[:lower:]' '[:upper:]'")

    def work_decimal_hint(self):
        """Push one decimal.Decimal arg"""

        hint = self.hint
        w = self.eval_decimal(chars=hint)
        self.push_one_decimal(w)

    def work_hexadecimal_hint(self):
        """Push one hexadecimal int arg"""

        hint = self.hint
        w = self.eval_int(chars=hint)
        self.pb_lines.append(self.str_int(w))

    def work_interval_hint(self):
        """Push one dt.timedelta arg"""

        hint = self.hint
        interval = self.eval_interval_hint(hint)
        self.pb_lines.append(str(interval))

    def work_indices_hint(self):
        """Call Awk to reorder or dupe columns, while dropping the rest"""

        hint = self.hint

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

    def work_moment_hint(self):

        era = self.era
        hint = self.hint
        moment = self.eval_moment_hint(era, hint)
        self.pb_lines.append(str(moment))

    def work_str_hint(self):
        """Push one str arg"""

        str_hint = self.hint
        self.pb_lines.append(str_hint)


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
    shinput_bytes = pb_chars.encode()

    argv = shlex.split("pbcopy")

    ran = subprocess_run(  # call for Stdin, without Stdout/err, with ReturnCode Zero
        argv,
        shell=False,
        input=shinput_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    check(want=0, got=ran.returncode)
    check(want=b"", got=ran.stdout)
    check(want=b"", got=ran.stderr)


#
# Define some Python idioms
# TODO: push changes back out to other copies
#


# deffed in many files  # missing from docs.python.org
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

        raise KwargsException(want=want, got=got, **kwargs)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


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


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to encode empty Stdin as:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(args, **kwargs)  # pylint: disable=subprocess-run-check

        return run

    # Convert KwArgs to Python 2

    kwargs2 = dict(kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    for kw in "encoding errors text universal_newlines".split():
        if kw in kwargs:
            raise NotImplementedError("keyword {}".format(kw))

    for kw in "check input".split():
        if kw in kwargs:
            del kwargs2[kw]  # drop now, catch later

    input2 = None
    if "input" in kwargs:
        input2 = kwargs["input"]

        if "stdin" in kwargs:
            raise ValueError("stdin and input arguments may not both be used.")

        assert "stdin" not in kwargs2
        kwargs2["stdin"] = subprocess.PIPE

    # Emulate the library roughly, because often good enough

    sub = subprocess.Popen(args, **kwargs2)  # pylint: disable=consider-using-with
    (stdout, stderr) = sub.communicate(input=input2)
    returncode = sub.poll()

    if "check" in kwargs:
        if returncode != 0:

            raise subprocess.CalledProcessError(
                returncode=returncode, cmd=args, output=stdout
            )

    # Succeed

    run = argparse.Namespace(
        args=args, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


# deffed in many files  # missing from docs.python.org
def subprocess_run_check_stdout_chars(args):
    """Call for Stdout, without Stderr, with ReturnCode Zero"""

    argv = shlex.split(args)

    ran = subprocess_run(
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


# FIXME: alias "+" to grow a "~/.python.py" history to rerun at each reentry
# feeling lucky enough to kill wrong history when it becomes wrong


# copied from:  git clone https://github.com/pelavarre/pybashish.git
