#!/usr/bin/env python3

# FIXME: discard this abandoned dead code in favour of:  hearme.py

"""
usage: pq.py [-h] [-b] [-c] [-i] [-l] [-p] [-t] [-w] [DOT [DOT ...]]

produce output from input by way of read, reread, reshape, zip, for, if, and/or pipe

positional arguments:
  DOT             a name or mark speaking output in terms of input

optional arguments:
  -h, --help      show this help message and exit
  -b, --bytes     read as bytes, aka dash -
  -c, --chars     read as chars, aka dotdot ..
  -i, --interact  take more dots to run from stdin
  -l, --lines     read as lines, aka dot .
  -p, --pipe      replace input with output to start again, aka colon :
  -t, --table     read as lines of words, aka plus +
  -w, --words     read as words, aka skid _

quirks:
  reads input from os clipboard by calling mac bash "pbpaste"
  replaces clipboard with output by calling mac bash "pbcopy"
  defaults to take more dots to run from stdin, when called with no args

dots:
  -t -l -w -c -b for zip if rip repr eval exec help
  dent dedent  ljust center rjust
  split join  set reversed sorted  encode decode  ascii expand
  lower upper title  lstrip strip rstrip
  len int  range  bin hex oct str
  commonprefix unique_everseen Counter
  csv html json tarfile
  expand hexdump uniq.c

examples of files of lines of words of chars of bytes, sketched as bash:
  pq.py -  # cat -
  pq.py enumerate.start  # cat -n
  pq.py enumerate  # cat -n=0
  pq.py reversed  # linux tac, mac tail -r
  pq.py sorted  # sort
  pq.py set sorted  # sort | uniq
  pq.py sorted.reverse  # sort -r
  pq.py set uniq.c reversed  # sort | uniq -c | sort -nr
  pq.py :10  # head
  pq.py :5, '"..."', -5:,  # bash -c 'tee >(head -5) >(echo ...) >(tail -5) >/dev/null'
  pq.py _ join  # x$args
  pq.py _  # xargs -n 1
  pq.py -lwc len : join  # wc -lwc
  pq.py 'hello pq world'  # echo 'hello pq world'
  pq.py "hey y'all"  # echo "hey y'all"
  pq.py .keepends for repr  # cat -etv
  pq.py .. set sorted join  # tr.py  # list chars in file
  pq.py - latin1 set sorted join  # list bytes in file

examples of words of chars in lines, sketched as bash:
  pq.py for if  # grep .
  pq.py for .4:  # cut -c5-
  pq.py for '$ ' +  # cat -etv
  pq.py for if enumerate  # cat -b
  pq.py + for join  # single spaces between words
  pq.py + for :3  # awk '{print $1, $2, $3}'
  pq.py + for -1:  # awk '{print $NF}'
  pq.py + for .3,.2 for upper  # awk '{print toupper($4), toupper($3)}'
  pq.py for for '" ".join'  # sed 's,.,. ,g'  # insert spaces to separate chars
  pq.py + for for +  # delete the spaces between chars in each line

more examples
  pq.py - rip  # print the python compiled, without running it
  pq.py +  # column -t  # print as rows of columns
  pq.py + csv  # parse as lines of words, print as csv
"""

# FIXME: work with files and dirs too

import os
import re
import shlex
import sys


NAME_REGEX = r"[A-Za-z_][A-Za-z_0-9]*"
INT_REGEX = r"[-+]?[0-9]+"
OPTS_REGEX = r"[-][A-Za-z_0-9]+"
MARK_REGEX = r"."

DOT_REGEX = r"|".join([NAME_REGEX, INT_REGEX, OPTS_REGEX, MARK_REGEX])


def main(argv):

    dots = _split_some_argv(argv[1:])

    if opt_in_argv_tail(argv[1:], concise="-h", mnemonic="--help"):
        print_help()
        sys.exit(0)  # exit zero from printing help

    pq_py = os.path.relpath(argv[0])
    shline = shlex_quote_argv([pq_py] + dots)

    _ = shline
    # sys.stderr.write("pq.py: testing usage: {}\n".format(shline))

    sys.stderr.write("dots = {}\n".format(dots))


def _repr_one_arg(arg):
    """Compromise with the damage done by shlex.split"""

    # Eval each twice-quoted arg  # like bash '"..."' means the three chars "..."

    if arg and arg[0] in ("'", '"'):

        dot = arg
        dots = [dot]

        return dots

    # Take blanks and such as quoted  # like bash "hey y'all" means its own 9 chars

    try:
        argv = shlex.split(arg)
    except ValueError:
        argv = list()

    if len(argv) != 1:

        dot = arg
        dots = [dot]

        return dots

    # Split anything else into a list of names, ints, opts, and marks

    dots = re.findall(DOT_REGEX, string=arg)  # just split, no eval
    if ":" in dots:

        # Take any ":" colon as "[start:stop:step]", not as the next -p Pipe
        # but avoid dragging trailing or leading "," commas into it

        core = arg.strip(" ,")
        core_at = arg.index(core)
        core_upto = core_at + len(core)

        if (core != ":") and not core.startswith("["):

            corrected = arg[:core_at] + "[" + core + "] " + arg[core_upto:]
            dots = re.findall(DOT_REGEX, string=corrected)

            return dots

    return dots


def _split_some_argv(argv):
    """Take each arg as a next fragment of source code"""

    dots = list()
    for arg in argv:
        if arg.lstrip().startswith("#"):
            break

        more_dots = _repr_one_arg(arg)
        assert more_dots

        dots.extend(more_dots)

    return dots


def opt_in_argv_tail(argv_tail, concise, mnemonic):
    """Say if an optional argument is plainly present"""

    # Give me a concise "-" dash opt, or a "--" double-dash opt, or both

    assert concise or mnemonic
    if concise:
        assert concise.startswith("-") and not concise.startswith("--")
    if mnemonic:
        assert mnemonic.startswith("--") and not mnemonic.startswith("---")

    # Detect the plain use of the concise or mnemonic opts
    # Drop the ambiguities silently, like see "-xh" always as "-x '-h'" never as "-x -h"

    for arg in argv_tail:

        if mnemonic.startswith(arg) and (arg > "--"):
            return True

        if arg.startswith(concise) and not arg.startswith("--"):
            return True


#
# Git-track some Python idioms here
#


# deffed in many files  # missing from docs.python.org
def print_help():
    """Print the lines of the argdoc at top of file, much like ArgumentParser would"""

    module = sys.modules[__name__]
    doc = module.__doc__.strip()
    print(doc)


# deffed in many files  # missing from docs.python.org
def shlex_quote_argv(argv):
    """Reconstruct what this input line could have been, in Bash"""

    shline = " ".join(shlex_quote_briefly(_) for _ in argv)

    return shline


# deffed in many files  # missing from docs.python.org
def shlex_quote_briefly(arg):
    """Abbreviate down to less than three quote marks, if possible"""

    rep = shlex.quote(arg)  # such as 'hey y'"'"'all'

    for q in ("'", '"'):

        alt_rep = "{}{}{}".format(q, arg, q)  # such as "hey y'all"

        try:
            alt_argv = shlex.split(alt_rep)
        except ValueError:
            continue

        if len(alt_argv) == 1:
            if alt_argv[0] == arg:
                if len(alt_rep) < len(rep):

                    return alt_rep

    return rep


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
