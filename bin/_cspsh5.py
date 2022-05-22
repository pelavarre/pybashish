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


#
# Run once, from the Command Line
#


def main():
    """Run once, from the Command Line"""

    argv = sys.argv[1:]
    wt = WordTerminal(argv, prompt="csp> ")
    assert wt

    vm = CspShVirtualMachine()

    main.vm = vm
    main.wt = wt
    main.pycharnames = make_pycharnames()

    run_till_exit(wt)


def run_till_exit(wt):
    """Run till raise of KeyboardInterrupt or SystemExit"""

    while True:
        try:
            run_till_exception(wt)
        except KeyboardInterrupt:
            if wt.stdin:
                print()

            print("KeyboardInterrupt")
            if wt.stdin:

                continue

            raise

        except SystemExit:
            if wt.stdin:

                continue  # todo: stop hiding nonzero SystemExit payloads

            raise


def run_till_exception(wt):
    """Run till raise of Exception"""

    vm = main.vm
    wt = main.wt

    while True:

        word = wt.pullword()  # send prompt, and hang till reply
        if word is None:
            if not wt:

                vm.BYE()

        if word:
            try:
                vm_step(vm, word=word)
            except CspSh_Exception as exc:
                exc_type = type(exc)

                exc_module = exc_type.__module__
                exc_module_prefix = "{}.".format(exc_module)
                if exc_module != "__main__":
                    exc_module_prefix = ""

                if wt.stdin:
                    print("{}{}: {}".format(exc_module_prefix, exc_type.__name__, exc))

                    wt.drop_line_drop_argv()

                    continue

                raise


#
# Make sense of their words
#


def vm_step(vm, word):
    """Make sense of one word"""

    func_name = pyname(word)
    func = getattr(vm, func_name, DEFAULT_NONE)
    if not func:

        raise CspSh_NameError(
            "name {!r} is not defined in Vm as:  def {}".format(word, func_name)
        )

    func()


class CspShVirtualMachine:
    """Do stuff"""

    def BYE(self):
        """Stop talking and go away"""

        wt = main.wt

        wt.close_argv_else_stdin()
        print("BYE")

        sys.exit()  # raise SystemExit

    def SLEEP(self):
        """Stop running for a short while"""

        time.sleep(1)

    def dash_i(self):
        """Start a conversation later, after interpreting the Command Line"""

        wt = main.wt

        wt.stdin = sys.stdin

    dash = dash_i

    def dash_dash(self):
        """Undefine the '-' and '--' words, such as '-h' and '--help' and '-i'"""

        keys = dir(self)
        for key in keys:
            if (key == "dash") or key.startswith("dash_"):
                delattr(self, key)
            elif (key == "dash_dash") or key.startswith("dash_dash_"):
                delattr(self, key)

    def print_cspsh_help(self):
        """Print the Command Line Help Lines from the top of the Main Python Sourcefile"""

        print()

        doc = textwrap.dedent(__main__.__doc__)
        doc = doc.strip()
        print(doc)

        print()  # todo:  less verbose tracing of dash options:  -, -h, -i, --h, etc

    dash_h = print_cspsh_help  # '-h'
    dash_dash_h = print_cspsh_help  # '--h'
    dash_dash_he = print_cspsh_help  # '--he'
    dash_dash_hel = print_cspsh_help  # '--hel'
    dash_dash_help = print_cspsh_help  # '--help'


#
# Work with Chars
#


def pyname(word):
    """Convert enough Chars to make meaningful Words into Python Names"""

    pycharnames = main.pycharnames

    chars = list()
    for (i, ch) in enumerate(word):
        chname = pycharnames.get(ch, DEFAULT_NONE)

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
# Take Input Words from the Command Line, then Stdin, then Empty Words forever
#


class WordTerminal:
    """Take Input Words from the Command Line, then Stdin, then Empty Words forever"""

    def __init__(self, argv, prompt):

        self.argv = list(argv) if argv else None
        self.prompt = prompt

        self.stdin = None if argv else sys.stdin

        self.welcome = "\n" + "Press ⌃D EOF to quit"
        self.eoi = "^D"  # "^D" as Control+D in the sense of Linux End-Of-Input (EOI)
        self.line = None
        self.word = None

    def __bool__(self):
        """Truthy while Input Words incoming"""

        falsy = all((_ is None) for _ in (self.argv, self.stdin, self.line))
        truthy = not falsy

        return truthy

    def close_argv_else_stdin(self):
        """Stop taking from the Command Line, else stop taking from Stdin"""

        if not self.argv:
            self.stdin = None

        self.drop_line_drop_argv()

    def drop_line_drop_argv(self):
        """Drop the Next Words of the Line, and drop the rest of the Command Line too"""

        argv = self.argv
        prompt = self.prompt
        line = self.line

        bye_lines = list()
        if argv:
            bye_lines.extend(argv)
        if line and line.lstrip():
            bye_lines.append(line)

        if bye_lines:
            print(prompt, end="")
            print("... {} input lines dropped ..".format(len(bye_lines)))

        self.argv = None
        self.line = None

    def pullword(self):
        """Pull the next Word, else raise SystemExit"""

        line = self.line
        word = None

        # Pull the Next Line when needed

        if not line:
            line = self.readline()

        # Split the Next Word out of the Pulled Line

        if line is not None:
            line = self.line.lstrip()
            if not line:
                line = None
            elif line.startswith("#"):
                line = ""
            else:
                word = line.split()[0]
                line = line[len(word) :]

        # Remember success, and succeed

        self.line = line
        self.word = word

        return word

    def readline(self):
        """Read & echo the next Line, from the Command Line, else Stdin, else EOI"""

        argv = self.argv
        eoi = self.eoi
        prompt = self.prompt
        stdin = self.stdin
        welcome = self.welcome

        print(prompt, end="")

        # Take the Next Arg from the Command Line

        if argv:

            line = argv.pop(0)
            print(line)

        # Else take EOI from the Command Line

        elif stdin:
            if argv is not None:
                line = ""
                print(eoi)

                self.argv = None

                print(welcome)

            # Else take EOI from the Pipe at Stdin

            elif not stdin.isatty():
                line = stdin.readline()
                if not line:
                    print(eoi)

                    self.stdin = None

                # Else take the next Line from the Pipe at Stdin

                else:
                    echo = line[: -len("\n")] if line.endswith("\n") else line
                    print(echo)

            # Else take EOI or the Next Line from the Terminal at Stdin

            else:
                sys.stdout.flush()
                sys.stderr.flush()

                line = self.stdin.readline()  # todo: add Input Line Editor
                if not line:
                    print()  # close the line into which Terminal wrote EOI

                    self.stdin = None

        # Else take another copy of EOI from nowhere

        else:

            line = None
            print(eoi)

        # Remember success, and succeed

        self.line = line

        return line


#
# Raise exceptions
#


class CspSh_Exception(Exception):
    """Gather together the set of CspSh_Exception Classes"""


class CspSh_NameError(CspSh_Exception):
    """Cry foul when they speak a word you don't understand"""


#
# Run once if loaded as the Main Process, not as an Imported Module
#


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
