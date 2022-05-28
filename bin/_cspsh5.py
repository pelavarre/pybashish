#!/usr/bin/env python3

"""
usage: cspsh.py [-h] [-i] [WORD ...]

talk out Csp ideas with people, by way of a Prompt-Listen-Speak-Repeat (Plsr) loop

positional arguments
  WORD        a word of command, such as 'SLEEP', or 'BYE'

options
  -h, --help  print this help message and exit
  -i          turn up verbosity, and breakpoint at exit

see also
  http://www.usingcsp.com/cspbook.pdf by CARHoare, May/2015

messy examples
  alias cspsh.py=bin/_cspsh5.py  # edit your Sh Path's as you please
  cspsh.py BYE  # launch then quit
  cspsh.py SLEEP  # launch, then wait, then quit
  cspsh.py -i SLEEP  # launch, then wait, then chat
  echo SLEEP |cspsh.py -  # same as:  cspsh.py SLEEP

error examples
  cspsh.py curtailed
  cspsh.py events without ops

simple examples
  cspsh.py  # start chatting
  cspsh.py hello → world → STOP  # print ⟨hello, world, STOP⟩
  cspsh.py hello → world → STOP -i  # work awhile, then turn up verbosity, then chat
"""


import __main__
import re
import sys
import textwrap
import time


CSP_EVENT_REGEX = r"^[a-z]+$"
CSP_PROC_REGEX = r"^[A-Z]+$"

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

        # Raise one exception or another

        try:

            run_till_exception(wt)

        # Intercept Control+C SigInt KeyboardInterrupt's

        except KeyboardInterrupt:
            if wt.stdin:
                print()

            print("KeyboardInterrupt")
            if wt.stdin:

                continue

            raise

        # Intercept SystemExit's

        except SystemExit:
            if wt.stdin:

                continue  # todo: stop hiding nonzero SystemExit payloads

            raise


def run_till_exception(wt):
    """Run till raise of Exception"""

    vm = main.vm
    wt = main.wt

    while True:

        # Pull the Next Word and make sense of it

        try:

            word = wt.pullword()  # send prompt, and hang till reply
            if word is None:
                if not wt:
                    vm.end_push()

                    vm.bye_push()

                continue

            vm.word_push(word)

        # Else complain, and try again, else quit

        except CspSyntaxError as exc:

            exc_type = type(exc)

            exc_module = exc_type.__module__
            exc_module_prefix = "{}.".format(exc_module)
            if exc_module != "__main__":
                exc_module_prefix = ""

            print("{}{}: {}".format(exc_module_prefix, exc_type.__name__, exc))
            wt.drop_line_drop_argv()

            sys.exit(1)


#
# Make sense of their words, one at a time
#


class CspShVirtualMachine:
    """Trace events"""

    def __init__(self):

        self.func_by_proc = self.make_func_by_proc()
        self.event_names = set()
        self.proc_names = set("STOP".split())

        self.trace = None
        self.word = None

        self.wants = "event_name proc_name end".split()

    def add_event_name(self):
        event_name = self.word
        if event_name not in self.event_names:
            if main.wt.stdin:
                print("cspsh.py: defining event name:  {}".format(event_name))
            self.event_names.add(event_name)

    def add_proc_name(self):
        proc_name = self.word
        if proc_name not in self.proc_names:
            if main.wt.stdin:
                print("cspsh.py: defining proc name:  {}".format(proc_name))
            self.proc_names.add(proc_name)

    def word_push(self, word):
        """Obey one Word Of Command"""

        self.word = word
        func = self.func_from_word(word)

        func()

    def end_push(self):
        """Close the conversation"""

        self.word = ""
        self.take_as("end")

    def func_from_word(self, word):
        """Choose the Func to call"""

        # Call 1 BuiltIn Function

        func_name = word
        func = self.func_by_proc.get(func_name, DEFAULT_NONE)
        if not func:

            # Or compile 1 Csp Source Word

            if re.match(CSP_EVENT_REGEX, string=word):
                func = self.do_event_name
            elif re.match(CSP_PROC_REGEX, string=word):
                func = self.do_proc_name
            elif word == "→":  # "\N{Rightwards Arrow}" "\u2192"
                func = self.do_and_then

            # Or reject this Csp Source Line

            else:

                self.take_as("unknown_word")

        return func

    def take_as(self, got):
        """Raise an Exception unless you're ready to take this Word"""

        wants = self.wants
        word = self.word

        if got not in wants:  # the unknown grammar
            want = "|".join(wants)

            str_want = 'want Csp "{}"'.format(want)
            if not wants[1:]:
                if want.startswith("'"):
                    str_want = "want Csp {}".format(want)

            str_got = 'got "{}" {!r}'.format(got, word)
            if got.startswith("'"):
                str_got = "got {}".format(got)

            self.trace = None  # todo def a method to cancel partial code
            self.wants = "event_name proc_name end".split()

            raise CspSyntaxError("{}, {}".format(str_want, str_got))

    def do_event_name(self):
        """Do an event"""

        self.take_as("event_name")
        self.add_event_name()

        if not self.trace:
            self.trace = list()
        self.trace.append(self.word)

        self.wants = "'→'".split()  # "\N{Rightwards Arrow}" "\u2192"

    def do_and_then(self):

        self.take_as("'→'")  # "\N{Rightwards Arrow}" "\u2192

        self.wants = "event_name proc_name".split()

    def do_proc_name(self):
        """Do a process"""

        self.take_as("proc_name")
        self.add_proc_name()

        #

        if not self.trace:
            self.trace = list()
        self.trace.append(self.word)

        trace = self.trace
        print("⟨{}⟩".format(", ".join(trace)))  # U+27E8, U+27E9 Angle Brackets

        self.trace = None

        #

        self.wants = "event_name proc_name end".split()

    #
    # Define the BuiltIn Processes
    #

    def make_func_by_proc(self):
        """Define the BuiltIn Processes"""

        d = dict()

        d["BYE"] = self.bye_push
        d["SLEEP"] = self.sleep_push
        d["STOP"] = self.do_proc_name

        d["-"] = self.dash_i  # take CspSh '-' as short for CspSh '-i'
        d["--"] = self.dash_dash
        d["--h"] = self.print_cspsh_help
        d["--he"] = self.print_cspsh_help
        d["--hel"] = self.print_cspsh_help
        d["--help"] = self.print_cspsh_help
        d["-h"] = self.print_cspsh_help
        d["-i"] = self.dash_i

        return d

    def bye_push(self):
        """Stop talking and go away"""

        self.word = "BYE"

        wt = main.wt

        verbose = wt.stdin
        wt.close_argv_else_stdin()
        if verbose:
            print("BYE")

        sys.exit()  # raise SystemExit

    def sleep_push(self):
        """Stop running for a short while"""

        self.word = "SLEEP"

        time.sleep(1)

    #
    # Define Command Line Options
    #

    def dash_i(self):
        """Start a conversation later, after interpreting the Command Line"""

        wt = main.wt

        stdin = wt.stdin
        wt.stdin = sys.stdin

        if not stdin:
            wt.print(wt.prompt, end="")
            wt.print(self.word)

    def dash_dash(self):
        """Undefine the '-' and '--' words, such as '-h' and '--help' and '-i'"""

        func_by_proc = self.func_by_proc

        keys = list(func_by_proc.keys())
        for key in keys:
            if key.startswith("-"):
                del func_by_proc[key]

    def print_cspsh_help(self):
        """Print the Command Line Help Lines from the top of the Main Python Sourcefile"""

        doc = textwrap.dedent(__main__.__doc__)
        doc = doc.strip()
        print(doc)


#
# Work with Chars
#


def pyname(word):  # todo:  put this to work, or delete it
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

    # FIXME: change WordTerminal, while Truthy, to return Empty String '', not None

    def __init__(self, argv, prompt):

        self.argv = list(argv) if argv else list()
        self.prompt = prompt

        self.stdin = None if argv else sys.stdin

        self.welcome = "Press ⌃D EOF to quit"
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
            self.print(prompt, end="")
            self.print("... {} input lines dropped ..".format(len(bye_lines)))

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

        # Take the Next Arg from the Command Line

        if argv:
            self.print(prompt, end="")

            line = argv.pop(0)
            self.print(line)

        # Else take EOI before Stdin from the Command Line

        elif stdin:
            if argv is not None:
                line = ""

                # do not:  if stdin.isatty():
                # do not:      print(prompt, end="")
                # do not:      print(eoi)

                self.argv = None

                if stdin.isatty():
                    if sys.argv[1:]:
                        print(self.prompt)  # print twice
                        print(self.prompt)
                    print(welcome)

            # Else take EOI from the Pipe at Stdin

            elif not stdin.isatty():
                line = stdin.readline()
                if not line:
                    # do not:  self.print(eoi)

                    self.stdin = None

                # Else take the next Line from the Pipe at Stdin

                else:
                    print(prompt, end="")
                    echo = line[: -len("\n")] if line.endswith("\n") else line
                    print(echo)

            # Else take EOI or the Next Line from the Terminal at Stdin

            else:
                print(prompt, end="")
                sys.stdout.flush()
                sys.stderr.flush()

                line = self.stdin.readline()  # todo: add Input Line Editor
                if not line:
                    print()  # close the line into which Terminal wrote EOI

                    self.stdin = None

        # Else take EOI from the Command Line without Stdin

        else:
            line = None

            self.print(prompt, end="")
            self.print(eoi)

            self.argv = None

        # Remember success, and succeed

        self.line = line

        return line

    def print(self, *args, **kwargs):
        """Print only while Stdin conversation in progress"""

        if self.stdin:
            print(*args, **kwargs)


#
# Raise exceptions
#


class CspSyntaxError(Exception):
    """Cry foul when they speak a word or a grammar that you don't understand"""


#
# Run once if loaded as the Main Process, not as an Imported Module
#


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
