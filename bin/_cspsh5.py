#!/usr/bin/env python3

"""
usage: cspsh.py [-h] [-i] [WORD ...]

talk out Csp ideas with people, by way of a Prompt-Listen-Speak-Repeat (Plsr) loop

positional arguments
  WORD        a word of command, such as 'SLEEP', or 'BYE'

options
  -h, --help  print this help message and exit
  -i          breakpoint at exit

examples
  cspsh.py  # start chatting
  cspsh.py BYE  # do nothing but launch and quit
  cspsh.py SLEEP  # launch, wait a short while, and then quit
  cspsh.py -i SLEEP  # launch, wait a short while, and then chat
  echo SLEEP |cspsh.py -  # same as:  cspsh.py SLEEP
"""
# cspsh.py hello → world  # print ⟨hello, world, STOP⟩


import __main__
import sys
import textwrap
import time


DEFAULT_NONE = None

g = __main__  # choose where to collect global variables


#
# Run once
#


def main():
    """Run from the Command Line"""

    if not sys.argv[1:]:
        g.stdin = sys.stdin

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            if g.stdin:
                print()

            print("KeyboardInterrupt")
            if g.stdin:

                continue

            raise

        except SystemExit:
            if g.stdin:

                continue  # todo: stop hiding nonzero SystemExit payloads

            raise


def run_once():
    """Prompt, Listen, Speak, Repeat, ... till they say Bye"""

    while True:
        do_prompt()
        try:
            do_listen()
            if g.word:
                do_speak()
        except CspSh_Exception as exc:
            if g.stdin:
                exc_type = type(exc)
                exc_module = exc_type.__module__
                exc_module = "" if (exc_module == "__main__") else (exc_module + ".")
                print("{}{}: {}".format(exc_module, exc_type.__name__, exc))
                drop_bye_lines()

                continue

            raise


def do_dash_i():
    """Start a conversation later, after interpreting the Command Line"""

    g.stdin = sys.stdin


do_dash = do_dash_i


def do_dash_dash():
    """Undefine the '-' and '--' words, such as '-h' and '--help' and '-i'"""

    keys = dir(__main__)
    for key in keys:
        if (key == "do_dash") or key.startswith("do_dash_"):
            delattr(__main__, key)
        elif (key == "do_dash_dash") or key.startswith("do_dash_dash_"):
            delattr(__main__, key)


def print_cspsh_help():
    """Print the Command Line Help Lines from the top of the Main Python Sourcefile"""

    print()

    doc = textwrap.dedent(__main__.__doc__)
    doc = doc.strip()
    print(doc)

    print()  # todo:  less verbose tracing of dash options:  -, -h, -i, --h, etc


do_dash_h = print_cspsh_help  # '-h'
do_dash_dash_h = print_cspsh_help  # '--h'
do_dash_dash_he = print_cspsh_help  # '--he'
do_dash_dash_hel = print_cspsh_help  # '--hel'
do_dash_dash_help = print_cspsh_help  # '--help'


#
# Prompt, Listen, Speak, Repeat, ... till they say Bye
#


def do_bye():
    """Stop talking and go away"""

    drop_bye_lines()

    if g.chatting:
        g.stdin = None

    print("BYE")

    sys.exit()  # raise SystemExit


def drop_bye_lines():
    """Shrug off what else you've heard, but do mention you shrugging it off"""

    bye_lines = list(g.argv)
    if g.sourceline.lstrip():
        bye_lines.append(g.sourceline)
    if bye_lines:
        print("disregarding {} input lines".format(len(bye_lines)))

    g.argv.clear()
    g.sourceline = ""


def do_prompt():
    """Keep on inviting them to speak, till they do speak"""

    # When taking End-Of-Input from the Command Line

    if not g.argv:
        if not g.chatting:

            # Always echo it

            if sys.argv[1:]:
                print("csp> ", end="")
                print("EOI")

            # Default to quit now

            if not g.stdin:

                do_bye()

            # Else open up a chat

            if sys.argv[1:]:
                print()

            print("Press ⌃D EOF to quit")
            g.chatting = True

    # Prompt for the next Input Line

    if not g.sourceline:
        print("csp> ", end="")

        # Take the next Input Line, and echo it

        assert not g.sourceline, repr(g.sourceline)
        do_refill()
        assert g.sourceline


def do_refill():
    """Take the next Input Line, and echo it"""

    # Take all the remaining Args, or one Arg, or End-Of-Input, from the Command Line

    if g.argv:

        popline = g.argv[0]
        if popline.lstrip().startswith("#"):
            argline = "  ".join(g.argv)
            g.argv.clear()
        else:
            argline = g.argv.pop(0)

        print(argline)
        g.sourceline = argline

        return

    # Else take one Input Line, or End-Of-Input, from Stdin

    sys.stdout.flush()
    sys.stderr.flush()

    iline = g.stdin.readline()  # todo: add Input Line Editor
    if g.stdin.isatty():
        if not iline:
            print()
    else:
        if not iline:
            print("EOI")
        elif iline.endswith("\n"):
            print(iline[: -len("\n")])
        else:
            print(iline)

    if not iline:
        g.stdin = None  # stop listening after first End-Of-Input

        do_bye()  # todo: stop hiding all unfetched Stdin

    g.sourceline = iline


def do_listen():
    """Wait for their words, then make sense of their words"""

    # Pull the next line

    sline = g.sourceline
    g.sourceline = ""

    line = sline.lstrip()

    # Pull just the next word, and pushback the rest of the line

    word = None
    if line and not line.startswith("#"):
        word = line.split()[0]
        g.sourceline = line[len(word) :]

    g.word = word


def do_speak():
    """Make sense of their words"""

    func_name = "do_" + pyname(g.word).lower()
    func = getattr(__main__, func_name, DEFAULT_NONE)
    if not func:

        raise CspSh_NameError(
            "name {!r} is not defined as:  def {}".format(g.word, func_name)
        )

    func()


def do_sleep():
    """Stop running for a short while"""

    time.sleep(1)


#
# Work with Chars
#


def pyname(word):
    """Convert enough Chars to make meaningful Words into Python Names"""

    chars = list()
    for (i, ch) in enumerate(word):
        chname = g.pycharnames.get(ch, DEFAULT_NONE)

        repl = ch
        if chname:
            repl = "{}".format(chname)
            if i < (len(word) - 1):
                repl = "{}_".format(chname)

        chars.append(repl)

    joined = "".join(chars)

    return joined


def make_pycharnames():
    """Choose CspSh Names for Chars that Python Names reject"""

    d = dict()

    d[" "] = "space"
    d["!"] = "bang"
    d['"'] = "quote"
    d["#"] = "hash"
    # d["$"]
    # d["%"]
    d["&"] = "amp"
    d["'"] = "tick"
    # d["("]
    # d[")"]
    d["*"] = "star"
    d["+"] = "plus"
    d[","] = "comma"
    d["-"] = "dash"
    d["."] = "dot"
    d["/"] = "slash"

    d[":"] = "colon"
    d[";"] = "semi"
    # d["<"]
    d["="] = "equals"
    # d[">"]
    d["?"] = "query"

    d["@"] = "at"

    # d["["]
    d["\\"] = "backslant"
    # d["]"]
    d["^"] = "hat"
    d["_"] = "skid"  # underscore

    d["`"] = "backtick"

    # d["{"]
    d["|"] = "bar"
    # d["}"]
    d["~"] = "tilde"

    return d

    # https://unicode.org/charts/PDF/U0000.pdf
    # http://www.catb.org/jargon/html/A/ASCII.html
    # https://www.dourish.com/goodies/jargon.html

    # http://www.forth.org/svfig/Win32Forth/DPANS94.txt
    # https://aplwiki.com/wiki/Unicode


#
# RaiseExceptions
#


class CspSh_Exception(Exception):
    """Gather together the set of CspSh_Exception Classes"""


class CspSh_NameError(CspSh_Exception):
    """Cry foul when they speak a word you don't understand"""


#
# Run once if loaded as the Main Process, not as an Imported Module
#


g.chatting = False  # True while taking Input from Stdin
g.argv = sys.argv[1:]  # Args to take from the Command Line
g.pycharnames = make_pycharnames()  # Names for Chars that Python Names reject
g.sourceline = ""  # Terminal Input Buffer, a la the Forth Word Source
g.stdin = None  # Alt Input Source after Command Line, if any


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
