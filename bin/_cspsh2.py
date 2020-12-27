#!/usr/bin/env python3

r"""
usage: cspsh.py [-h] [-f] [-i] [-q] [-v] [-c COMMAND]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help      show this help message and exit
  -f, --force     ask less questions, such as quit without prompting
  -i, --interact  ask more questions, such as prompt for more commands
  -q, --quiet     say less, such as launch without banner
  -v, --verbose   say more, such as the tracebacks for unhandled exceptions
  -c COMMAND      take the command as the only input, else as the first input before -i

demo input:
  tick → STOP
  tick → tick → STOP
  CLOCK = (tick → tock → CLOCK)
  CLOCK

examples:
  cspsh.py -h
  cspsh.py
  cspsh.py -c $'CLOCK = (tick → tock → CLOCK)\nCLOCK'
  (echo 'CLOCK = (tick → tock → CLOCK)'; echo CLOCK) | cspsh.py
  open http://www.usingcsp.com/cspbook.pdf  # 1985 CARHoare
"""

# FIXME: solve the noqa-C901's

# TODO: produce permutation iterators

# TODO: spill cuts in place of reconstructed source chars
# TODO: include original comments and empty lines in styled source
# TODO: add option to sponge Stdin when launched, a la Zsh


import argparse
import pdb
import re
import select
import sys
import textwrap

import argdoc


def b():
    pdb.set_trace()


#
# Work with a Bash command line
#


def main():

    # Parse args

    args = argdoc.parse_args()

    confidence = args.force - args.interact
    args_force = confidence if (confidence > 0) else 0
    args_interact = -confidence if (confidence < 0) else 0

    finesse = args.quiet - args.verbose
    args_quiet = finesse if (finesse > 0) else 0
    args_verbose = -finesse if (finesse < 0) else 0

    args_lines = list()
    if args.command is not None:
        args_lines = args.command.splitlines()
        if not args.command.strip():
            args_lines = [""]

    # Test, if not interacting

    if not args_interact:
        test_cspsh()

    if not args_lines:
        if args_force:
            return

    # Run

    run_cspsh(
        args_lines=args_lines,
        args_interact=args_interact,
        args_quiet=args_quiet,
        args_verbose=args_verbose,
    )


def run_cspsh(args_lines, args_interact, args_quiet, args_verbose):  # noqa C901
    """
    Run as a tty shell
    """

    isatty = sys.stdin.isatty()

    if not args_lines:
        if isatty and not args_quiet:
            stderr_print("Type some line of CSP, press Return to see it run")
            stderr_print("Such as:  coin → choc → coin → choc → STOP")
            stderr_print(r"Press ⌃D EOF or ⌃C SIGINT or ⌃\ SIGQUIT to quit")

    lines = list(args_lines)
    open_exc = None
    open_lines = list()

    while True:
        prompt = open_exc.prompt if open_exc else "? "

        if lines:

            line = lines.pop(0)
            # stderr_print("{}{}".format(prompt, line))

        else:

            stderr_print(prompt, end="")

            ahead = kbhit() if isatty else False

            raw_line = sys.stdin.readline()

            line = raw_line.rstrip()
            if ahead or not sys.stdin.isatty():
                stderr_print(line)

            if not raw_line:
                stderr_print()
                break

        open_lines.append(line)
        closed_line = "\n".join(open_lines)  # "\n" to close comments opened by "#"

        csp_commands = None
        open_exc = enclose_csp_line(closed_line)

        if not open_exc:
            open_lines = list()
            try:
                csp_commands = compile_csp_commands(chars=closed_line)
            except Exception as exc:
                exc_mention = exc.mention
                stderr_print(exc_mention)
                if not args_verbose:
                    stderr_print("{}: {}".format(type(exc).__name__, exc))
                    sys.exit(1)
                raise

        if csp_commands:
            formatted = csp_commands.format_as_csp()
            columns = 89 - len("? ")  # 89 as in Black ".py"
            spilled = spill_csp_words(formatted, columns=columns)
            for spilled_line in spilled.splitlines():
                stderr_print("+ {}".format(spilled_line).rstrip())

        if args_lines:
            if not lines:
                if not args_interact:
                    break

        line = None

    if open_exc:
        raise open_exc


def enclose_csp_line(line):
    """
    Return None, if a close mark closes every open mark

    Raise Exception, if more close marks than open marks

    Defer an Exception and return it, if more open marks than close marks
    """

    cutter = CspCutter()
    cuts = cutter.give_chars_as_cuts(chars=line)

    open_cuts = list()
    close_cuts = list()

    for cut in cuts:
        if cut.chars == "(":
            open_cuts.append(cut)
        elif cut.chars == ")":
            close_cuts.append(cut)

    exc_cut = None
    if len(close_cuts) > len(open_cuts):

        goal = "close only open marks"
        want = ""
        got = "".join(_.chars for _ in close_cuts)

        exc_cut = close_cuts[0]
        prompt = None

    elif len(open_cuts) > len(close_cuts):

        goal = "close each open mark"
        want = "".join(_.chars for _ in open_cuts)
        got = ""

        exc_cut = open_cuts[0]
        prompt = "{}? ".format(want)

    if exc_cut:

        exc_mention = cutter.make_mention(exc_cut)

        exc = KwargsException(goal=goal, want=want, got=got)
        exc.mention = exc_mention
        exc.prompt = prompt

        if prompt:
            return exc

        raise exc


def compile_csp_commands(chars):
    """
    Make a CspTreeList out of a Csp source line
    """

    cutter = CspCutter()
    cuts = cutter.give_chars_as_cuts(chars)
    compile_csp_commands.cutter = cutter  # leak to debug

    taker = CutsTaker(cuts)

    csp_commands = CspTreeList()
    csp_command = None
    while taker.peek_more():
        try:
            csp_command = CspCommand.take_tree_from(taker, before=csp_command)
        except Exception as exc:
            cut = taker.peek_one_cut()
            exc_mention = cutter.make_mention(cut)
            exc.mention = exc_mention  # defines undeclared attribute
            raise
        csp_commands.append(csp_command)

    return csp_commands


#
# Define a Csp grammar
# in terms of a "parser" of "abstract syntax tree", a la "import ast"
#


class CspTree(argparse.Namespace):
    """
    Hold a tree of trees of cuts of source, akin to a dir of dirs of files
    """

    def __init__(self, **kwargs):  # ordered since Dec/2016 CPython 3.6
        argparse.Namespace.__init__(self, **kwargs)

        formatted = "".join(_.format_as_csp() for _ in kwargs.values() if _)
        self.formatted = formatted

    def format_as_csp(self):
        return self.formatted


class CspTreeList(argparse.Namespace):  # TODO: Merge CspTreeList into CspTree
    """
    Hold a list of trees of cuts of source, akin to a dir of files
    """

    def __init__(self, *trees):
        argparse.Namespace.__init__(self, trees=list(trees))

        self.formatted = "".join(_.format_as_csp() for _ in trees)

    def __bool__(self):  # in place of def __nonzero__ since 2008 Python 3.0

        truthy = bool(self.trees)
        return truthy

    def append(self, tree):

        trees = self.trees

        tree_typename = type(tree).__name__
        check(got=isinstance(tree, CspTree), tree_typename=tree_typename)

        trees.append(tree)
        self.formatted += tree.format_as_csp()

    def format_as_csp(self):
        return self.formatted


class CspCommand(CspTree):
    """
    command := define_process_name | process
    """

    def format_as_csp(self):
        formatted = self.formatted
        return formatted

    @staticmethod
    def take_tree_from(taker, before):

        cuts = taker.peek_cuts(2)
        if cuts[1] and cuts[1].chars == "=":
            define_process_name = CspDefineProcessName.take_tree_from(taker)
            tree = define_process_name
        else:
            process = CspProcess.take_tree_from(taker)
            tree = process

        command = CspCommand(tree=tree)
        return command


class CspDefineProcessName(CspTree):
    """
    define_process_name := process_name "=" process_body
    """

    @staticmethod
    def take_tree_from(taker):

        process_name = CspProcessName().take_tree_from(taker)
        mark = CspMark.take_tree_from_chars(taker, chars="=")
        process_body = CspProcessBody().take_tree_from(taker)

        define_process_name = CspDefineProcessName(
            process_name=process_name, mark=mark, process_body=process_body
        )
        return define_process_name


class CspProcessBody(CspTree):
    """
    process_body := process_with_such | process
    """

    @staticmethod
    def take_tree_from(taker):

        cut = taker.peek_one_cut()
        if cut and (cut.chars == "μ"):
            process_with_such = CspProcessWithSuch().take_tree_from(taker)
            tree = process_with_such
        else:
            process = CspProcess().take_tree_from(taker)
            tree = process

        process_body = CspProcessBody(tree=tree)
        return process_body


class CspProcessWithSuch(CspTree):
    """
    process_with_such := "μ" process_name [ ":" alphabet ] "•" process
    """

    @staticmethod
    def take_tree_from(taker):

        process_mark = CspMark.take_tree_from_chars(taker, chars="μ", formatted="μ ")
        process_name = CspProcessName().take_tree_from(taker)

        cut = taker.peek_one_cut()
        with_mark = None
        alphabet = None
        if cut and (cut.chars == ":"):
            with_mark = CspMark.take_tree_from_chars(taker, chars=":")
            alphabet = CspAlphabet().take_tree_from(taker)

        such_that_mark = CspMark.take_tree_from_chars(taker, chars="•")

        process_with_such = CspProcessWithSuch(
            process_mark=process_mark,
            process_name=process_name,
            with_mark=with_mark,
            alphabet=alphabet,
            such_that_mark=such_that_mark,
        )
        return process_with_such


class CspAlphabet(CspTree):
    """
    alphabet := "{" { event_name "," } event_name [ "," ] "}"
    """

    @staticmethod
    def take_tree_from(taker):

        open_mark = CspMark.take_tree_from_chars(taker, chars="{", formatted="{")

        event_comma_list = CspTreeList()
        while True:

            cut = taker.peek_one_cut()
            if cut and (cut.chars == "}"):
                break

            event_name = CspEventName().take_tree_from(taker)
            event_comma_list.append(event_name)

            cut = taker.peek_one_cut()
            if cut and (cut.chars == ","):
                comma_mark = CspMark.take_tree_from_chars(
                    taker, chars=",", formatted=", "
                )
                event_comma_list.append(comma_mark)
            else:
                break

        close_mark = CspMark.take_tree_from_chars(taker, chars="}", formatted="}")

        alphabet = CspAlphabet(
            open_mark=open_mark,
            event_comma_list=event_comma_list,
            close_mark=close_mark,
        )
        return alphabet


class CspProcess(CspTree):
    """
    process := choice | process_tail
    """

    @staticmethod
    def take_tree_from(taker):

        cuts = taker.peek_cuts(2)
        if cuts[1] and cuts[1].chars == "→":
            choice = CspChoice.take_tree_from(taker)
            tree = choice
        else:
            process_tail = CspProcessTail().take_tree_from(taker)
            tree = process_tail

        process = CspProcess(tree=tree)
        return process


class CspChoice(CspTree):
    """
    choice := guarded_process { "|" guarded_process }
    """

    @staticmethod
    def take_tree_from(taker):

        process_choice_list = CspTreeList()
        guard_names = list()
        while True:

            cuts = taker.peek_cuts(2)
            if cuts[1] and cuts[1].chars == "→":
                guard_names.append(cuts[0].chars)

                # cutter = compile_csp_commands.cutter
                # stderr_print(cutter.make_mention(cuts[0]))
                # stderr_print(guard_names)

                check(
                    "no duped process guard event names",
                    want=len(guard_names),
                    got=len(set(guard_names)),
                    guard_names=guard_names,
                )

                guarded_process = CspGuardedProcess.take_tree_from(taker)
                process_choice_list.append(guarded_process)

            cuts = taker.peek_cuts(3)
            if cuts[0] and cuts[0].chars == "|":
                if cuts[2] and cuts[2].chars == "→":

                    choice_mark = CspMark.take_tree_from_chars(taker, chars="|")
                    process_choice_list.append(choice_mark)

                    continue

            break

        check(got=process_choice_list)

        choice = CspChoice(process_choice_list=process_choice_list)
        return choice


class CspGuardedProcess(CspTree):
    """
    guarded_process := event_name "→" { event_name "→" } process_tail
    """

    @staticmethod
    def take_tree_from(taker):

        event_then_list = CspTreeList()
        while True:

            event_name = CspEventName().take_tree_from(taker)
            then_mark = CspMark.take_tree_from_chars(taker, chars="→")

            event_then_list.append(event_name)
            event_then_list.append(then_mark)

            cuts = taker.peek_cuts(2)
            if cuts[1] and cuts[1].chars == "→":
                continue

            break

        check(got=event_then_list)

        process_tail = CspProcessTail().take_tree_from(taker)

        guarded_process = CspGuardedProcess(
            event_then_list=event_then_list, process_tail=process_tail
        )
        return guarded_process


class CspProcessTail(CspTree):
    """
    process_tail := anonymous_process | process_name
    """

    @staticmethod
    def take_tree_from(taker):

        cut = taker.peek_one_cut()
        if cut and cut.chars == "(":
            anonymous_process = CspAnonymousProcess().take_tree_from(taker)
            tree = anonymous_process
        else:
            process_name = CspProcessName().take_tree_from(taker)
            tree = process_name

        process_tail = CspProcessTail(tree=tree)
        return process_tail


class CspAnonymousProcess(CspTree):
    """
    anonymous_process := "(" process ")"
    """

    @staticmethod
    def take_tree_from(taker):

        open_mark = CspMark.take_tree_from_chars(taker, chars="(", formatted="(")
        process = CspProcess().take_tree_from(taker)
        close_mark = CspMark.take_tree_from_chars(taker, chars=")", formatted=")")

        anonymous_process = CspAnonymousProcess(
            open_mark=open_mark, process=process, close_mark=close_mark
        )
        return anonymous_process


class CspProcessName(CspTree):
    """
    process_name := ... upper name ...
    """

    @staticmethod
    def take_tree_from(taker):

        cut = taker.peek_one_cut()

        got = cut.chars
        want = got.upper()
        check("uppercase process name", want=want, got=got)

        name = CspName.take_tree_from(taker)
        process_name = CspProcessName(name=name)
        return process_name


class CspEventName(CspTree):
    """
    event_name := ... lower name ...
    """

    @staticmethod
    def take_tree_from(taker):

        cut = taker.peek_one_cut()

        got = cut.chars
        want = got.lower()
        check("lowercase event name", want=want, got=got)

        name = CspName.take_tree_from(taker)
        event_name = CspEventName(name=name)
        return event_name


class CspLeaf(CspTree):
    """
    Hold a single cut
    """

    def __init__(self, cut, formatted):
        self.cut = cut
        self.formatted = formatted

    @classmethod
    def take_tree_from_cut(cls, taker, formatted):

        cut = taker.peek_one_cut()

        taker.take_one_cut()

        leaf = cls(cut=cut, formatted=formatted)
        return leaf

    @classmethod
    def take_tree_from_kind(cls, taker, kind):

        cut = taker.peek_one_cut()

        check(want=kind, got=cut.kind)

        leaf = cls.take_tree_from_cut(taker, formatted=cut.chars)
        return leaf

    @classmethod
    def take_tree_from_mark_chars(cls, taker, chars, formatted=None):

        cut = taker.peek_one_cut()

        check(want="mark", got=cut.kind)
        check(want=chars, got=cut.chars)

        as_formatted = " {} ".format(chars) if (formatted is None) else formatted
        leaf = cls.take_tree_from_cut(taker, formatted=as_formatted)

        return leaf


class CspName(CspLeaf):
    """
    Hold a single name
    """

    @staticmethod
    def take_tree_from(taker):

        name = CspName.take_tree_from_kind(taker, kind="name")
        return name


class CspMark(CspLeaf):
    """
    Hold a single mark
    """

    @staticmethod
    def take_tree_from_chars(taker, chars, formatted=None):

        mark = CspMark.take_tree_from_mark_chars(
            taker, chars=chars, formatted=formatted
        )
        return mark


#
# Define a Csp syntax
# in terms of a "lexxer"
# accepting the chars r"[.0-9A-Za-z_]" in names
#


LINESEP = r"(?P<linesep>#.*)"  # Csp doesn't define '#' comments, but we do
NAME = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK = r"(?P<mark>[(),:={|}μ•→⟨⟩])"
GAP = r"(?P<gap>[ ])"  # TODO: expand tabs, strip chars, strip lines, at input
GOOF = r"(?P<goof>.)"  # doesn't match r"[\r\n]"

SPILL = r" [^.0-9A-Za-z_]"  # mark or goof preceded by space
STARTSWITH_DEF = r"^[.0-9A-Za-z_]+ [=][^.0-9A-Za-z_]*"  # name "=" marks|goofs
ENDSLIKE_CLOSING = r"[^.0-9A-Za-z_ ]+$"  # marks goofs gaps ending the line

CSP = r"|".join([LINESEP, NAME, MARK, GAP, GOOF])


class CspCutter(argparse.Namespace):
    """
    Cut source chars into lines, and cut source lines into words

    Number the lines, and point back to where cut from
    """

    def __init__(self, chars=None):

        self.chars = ""
        self.line_cuts_list = list()

        if chars is not None:
            self.give_chars_as_cuts(chars)

    def give_chars_as_cuts(self, chars):
        """Add source lines of chars"""

        given_cuts = list()
        for given_line in chars.splitlines():

            raw_cuts = list()
            for match in re.finditer(CSP, string=given_line):
                for item in match.groupdict().items():
                    (kind, chars) = item
                    if chars:
                        cut = CspCut(chars, kind=kind)
                        raw_cuts.append(cut)

                        if False:
                            stderr_print(cut)

            if raw_cuts and raw_cuts[-1].kind == "linesep":
                pass
            else:
                linesep_cut = CspCut("", kind="linesep")  # here, not elsewhere
                raw_cuts.append(linesep_cut)

            spliced_line = "".join(_.chars for _ in raw_cuts)
            check("no cuts dropped", want=given_line, got=spliced_line)

            drop_kinds = "gap linesep".split()
            line_cuts = list(_ for _ in raw_cuts if _.kind not in drop_kinds)

            self.line_cuts_list.append(raw_cuts)
            given_cuts.extend(line_cuts)

        if False:
            for cut in given_cuts:
                stderr_print(self.make_mention(cut))

        return given_cuts

    def make_mention(self, cut):
        """Format the line containing the cut and a "... ^" arrow pointing to the cut"""

        found = self.find_row_column_line0_line1(cut)
        if found:
            (column, row, line0, line1) = found

            mention = "{}\n{}".format(line0, line1)
            return mention

    def find_row_column_line0_line1(self, cut):
        """Print the sourceline containing the cut and a pointer to it"""

        for (row, line_cuts) in enumerate(self.line_cuts_list):  # O(N)

            tag = "{}:".format((1 + row))
            spliced_line = "".join(_.chars for _ in line_cuts)
            line0 = "{}{}".format(tag, spliced_line)

            dots = len(tag) * "."
            dots0 = dots
            for line_cut in line_cuts:

                if cut is line_cut:

                    len_arrows = max(1, len(cut.chars))
                    line1 = dots[:-1] + " " + (len_arrows * "^")

                    column = len(dots) - len(dots0)  # TODO: untested
                    return (column, row, line0, line1)

                dots += len(line_cut.chars) * "."


class CspCut(argparse.Namespace):
    """
    Carry a fragment of source, without losing track of where it came from
    """

    def __init__(self, chars, kind):

        self.chars = chars
        self.kind = kind


def spill_csp_words(chars, columns):  # noqa C901
    """
    Replace " " spaces with "\n" line separators
    """

    # Place the margins

    dent = "    "
    head_width = columns - 1
    tail_width = head_width - len(dent)

    check(got=(tail_width > 0), columns=columns, dent=dent)
    check(got=(head_width > 0), columns=columns, dent=dent)  # passes always

    # Work the chars till all chars placed in a line

    lines = list()
    while chars:

        width = tail_width if lines else head_width
        chopped = chars[:width]

        # Take the linesep that is

        linesep_at = len(chopped)

        linesep_was_at = chopped.find("\n")
        if linesep_was_at >= 0:

            linesep_at = linesep_was_at

        # Don't break lines that fit
        # Except do break trailing lines that end with marks and goofs

        elif not chars[width:]:

            endslike_closing = re.search(ENDSLIKE_CLOSING, string=chopped)
            if endslike_closing:
                linesep_spillers_at = endslike_closing.start()
                if lines and (linesep_spillers_at != 0):

                    linesep_at = linesep_spillers_at

        # Break lines that don't fit before last mark or goof

        else:

            spills = list(re.finditer(SPILL, string=chopped))
            if spills:
                last_spill_at = spills[-1].start()

                linesep_at = last_spill_at

                # Except break leading lines that say "=" after gaps marks goofs

                if not lines:
                    startswith_def = re.match(STARTSWITH_DEF, string=chopped)
                    if startswith_def:
                        linesep_at = startswith_def.end()

            # Break lines without mark or goof that don't fit before last space

            else:
                last_wordsep_at = chopped.rfind(" ")
                if last_wordsep_at >= 0:

                    linesep_at = last_wordsep_at

        # Break the line in two at the chosen spot

        line = chars[:linesep_at]
        chars = chars[linesep_at:].lstrip()

        # Dent all lines but the first
        # Except also don't the last if it holds nothing but marks and goofs

        line_dent = ""
        if lines:
            line_dent = dent
            if not chars:
                line_spillers_at = re.search(ENDSLIKE_CLOSING, string=line).start()
                if line_spillers_at == 0:
                    line_dent = ""

        # Collect the line

        lines.append(line_dent + line)

    # Succeed

    spilled = "\n".join(lines)
    return spilled


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
# TODO: push changes back out to other copies of CutsTaker at ShardsTaker
class CutsTaker(argparse.Namespace):
    """
    Walk through cuts of source, supplied incrementally

    Define "take" to mean consume, else raise Exception
    Define "peek" to mean look ahead if present, else into an infinite stream of None's
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, cuts=None):
        self.cuts = list()
        if cuts is not None:
            self.give_cuts(cuts)

    def give_cuts(self, cuts):
        """Add cuts"""

        self.cuts.extend(cuts)

    def take_one_cut(self):
        """Consume the next cut, without returning it"""

        self.cuts = self.cuts[1:]

    def take_cuts(self, count):
        """Take a number of cuts, without returning them"""

        self.cuts = self.cuts[count:]

    def peek_one_cut(self):
        """Return the next cut and don't consume it, or return None"""

        if self.cuts:
            return self.cuts[0]

    def peek_cuts(self, count):
        """Return the next few cuts, don't consume them, and pad with None's"""

        nones = count * [None]
        some = (self.cuts[:count] + nones)[:count]

        return some

    def peek_equal_cuts(self, hopes):
        """Return the next few cuts, if they are the cuts you're looking for"""

        some = self.peek_cuts(len(hopes))
        if some == list(hopes):
            return True

    def take_beyond_cuts(self):
        """Do nothing if all cuts consumed, else raise Exception"""

        assert not self.peek_more()

    def peek_more(self):
        """Return True while cuts remain"""

        more = bool(self.cuts)
        return more

    def count_more_cuts(self):
        """Count the remaining cuts"""

        return len(self.cuts)

    def accept_falsy_cuts(self):
        """Consume the falsy cuts here, if any"""

        while self.peek_more():
            cut = self.peek_one_cut()
            if cut.strip():
                break
            self.take_one_cut()

    def count_truthy_cuts(self):
        """Count the truthy cuts here"""

        cuts = list()
        for cut in self.cuts:
            if not cut.strip():
                break
            cuts.append(cut)

        len_truthy_cuts = len(cuts)
        return len_truthy_cuts


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
# TODO: push changes back out to other copies of def.check, and into #LikeMyCode
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
# TODO: push changes back out to other copies of def.kbhit
def kbhit():
    """Wait till next key struck, or a burst of paste pasted"""

    rlist = [sys.stdin]
    wlist = list()
    xlist = list()
    timeout = 0
    selected = select.select(rlist, wlist, xlist, timeout)
    (rlist_, wlist_, xlist_) = selected

    if rlist_ == rlist:
        return True


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def verbose_print(*args, **kwargs):
    sys.stdout.flush()
    if main.args.verbose:
        print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


#
# Define some tests
#


def test_cspsh():  # noqa C901
    """Return to pass, or raise exception to fail"""

    lines = TEST_LINES

    tests = list()
    for line in lines:

        continuation = False
        if tests and line:
            endslike_closing = re.search(ENDSLIKE_CLOSING, string=line)
            if line.startswith(" "):
                continuation = True
            elif endslike_closing and (endslike_closing.start() == 0):
                continuation = True

        if continuation:
            tests[-1] = "{}\n{}".format(tests[-1], line)
        else:
            tests.append(line)

    for test in tests:
        goal = "testing:  {!r}".format(test)

        want_str_exc = None
        hash_exc_at = test.find("# Exception")
        if hash_exc_at >= 0:
            want_str_exc = test[(hash_exc_at + len("# ")) :]

        try:

            _ = compile_csp_commands(chars=test)
            if want_str_exc:
                check(goal, want=want_str_exc, got=None)

        except Exception as exc:

            str_exc = "{}: {}".format(type(exc).__name__, str(exc))
            if (want_str_exc is None) or (want_str_exc not in str_exc):
                check(goal, want=want_str_exc, got=str_exc)


BASIC_TEST_CHARS = """

    #
    # examples from the help lines
    #


    tick → STOP
    tick → tick → STOP
    CLOCK = (tick → tock → CLOCK)
    CLOCK


    #
    # more examples from us
    #


    HER.WALTZ = (
        her.right.back → her.left.hook.back → her.right.close
        → her.left.forward → her.right.hook.forward → her.left.close
        → HER.WALTZ
    )
    HIS.WALTZ = (
        his.left.forward → his.right.hook.forward → his.left.close
        → his.right.back → his.left.hook.back → his.right.close
        → HIS.WALTZ
    )
    HER.WALTZ
    HIS.WALTZ

    CLOCK = μ X : {tick, tock} • (tick → tock → X)
    CLOCK

"""

CHAPTER_1_TEST_CHARS = """

    #
    # Chapter 1:  Processes
    #


    # 1.1.1 Prefix

    coin → STOP  # 1.1.1 X1
    coin → choc → coin → choc → STOP  # 1.1.1 X2

    CTR = (right → up → right → right → STOP)  # 1.1.1 X3
    CTR
    x → y  # Exception: (goal='uppercase process name', want='Y', got='y')
    P → Q  # Exception: (goal='lowercase event name', want='p', got='P')
    x → (y → STOP)


    # 1.1.2 Recursion

    CLOCK = (tick → CLOCK)
    CLOCK

    CLOCK = (tick → tick → tick → CLOCK)
    CLOCK

    CLOCK = μ X : {tick} • (tick → X)  # 1.1.2 X1
    CLOCK

    VMS = (coin → (choc → VMS))  # 1.1.2 X2
    VMS

    CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
    CH5A

    CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4
    CH5B


    # 1.1.3 Choice

    (up → STOP | right → right → up → STOP)  # 1.1.3 X1

    CH5C = in5p → (  # 1.1.3 X2
        out1p → out1p → out1p → out2p → CH5C
        | out2p → out1p → out2p → CH5C
    )
    CH5C

    (x → P | y → Q)

    VMCT = μ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3
    VMCT

    VMC = (  # 1.1.3 X4
        in2p → (large → VMC
                | small → out1p → VMC)
        | in1p → (small → VMC
                  | in1p → (large → VMC
                            | in1p → STOP
    )))
    VMC

    VMCRED = μ X • (coin → choc → X | choc → coin → X)  # 1.1.3 X5
    VMCRED

    VMS2 = (coin → VMCRED)  # 1.1.3 X6
    VMS2

    COPYBIT = μ X • (in.0 → out.0 → X  # 1.1.3 X7
                     | in.1 → out.1 → X)
    COPYBIT

    (x → P | y → Q | z → R)
    (x → P | x → Q)  # Exception: (goal='no duped process guard event names'
    (x → P | y)  # Exception: (want=')', got='|')
    (x → P) | (y → Q)  # Exception: (want='name', got='mark')
    (x → P | (y → Q | z → R))  # Exception: (want=')', got='|')

    # RUN-A = (x:A → RUN-A)  # 1.1.3 X8


    # 1.1.4 Mutual recursion

    # αDD = αO = αL = {setorange, setlemon, orange, lemon}

    DD = (setorange → O | setlemon → L)  # 1.1.4 X1
    O = (orange → O | setlemon → L | setorange → O)
    L = (lemon → L | setorange → O | setlemon → L)

    DD

    CT0 = (up → CT1 | around → CT0)  # 1.1.4 X2
    CT1 = (up → CT2 | down → CT0)
    CT2 = (up → CT3 | down → CT1)

    CT0

    CT0 = (around → CT0 | up → CT1)  # 1.1.4 X2  # Variation B
    CT1 = (down → CT0 | up → CT2)
    CT2 = (down → CT1 | up → CT3)

    CT0

    # CT[n+1] = (up → CT[n+2] | down → CT[n])


    # 1.2 Pictures


    # 1.3 Laws

    # (x → P | y → Q) = (y → Q | x → P)  # but our traces of these are inequal
    (x → P | y → Q)
    (y → Q | x → P)

    # (x → P) ≠ STOP
    (x → P)
    STOP

    # L1    (x:A → P(x)) = (y:B → Q(y))  ≡  (A = B  ∧  ∀ x:A • P(x)=Q(x))
    # L1A   STOP ≠ (d → P)
    # L1B   (c → P) ≠ (d → Q)
    # L1C   (c → P | d → Q) = (d → Q | c → P)
    # L1D   (c → P) = (c → Q)  ≡  P = Q

    # (coin → choc → coin → choc → STOP) ≠ (coin → STOP)  # 1.3 X1

    # μ X • (coin → (choc → X | toffee → X ))  =  # 1.3 X2
    #   μ X • (coin → (toffee → X | choc → X ))

    # L2    (Y = F(Y))  ≡  (Y = μ X • F(X))  # <= TODO: what is this??
    # L2A   μ X • F(X) = F(μ X • F(X))  # <= TODO: a la L2

    VM1 = (coin → VM2)
    VM2 = (choc → VM1)

    VM1
    VM2
    VMS

    # L3    if (∀ i:S • (Xi = F(i, X )  ∧  Yi = F(i, Y))) then X = Y  # <= TODO: a la L2


    # 1.4  Implementation of processes

    # Bleep, Label, Choice2, Menu, Interact, Cons, Car


    # 1.5 Traces

    # first 4 events of VMS  # 1.5 X1
    # first 3 events of VMS  # 1.5 X2
    # first 0 events of any process, even STOP  # 1.5 X3
    # all traces of <= 2 events at VMC  # 1.5 X4
    # ⟨in1p, in1p, in1p⟩ ends the only trace it begins, because it STOP's  # 1.5 X5


    # 1.6 Operations on traces

    # 1.6.1 Catenation  # TODO: math unicode that doesn't paste
    # 1.6.2 Restriction
    # 1.6.3 Head and tail
    # 1.6.4 Star
    # 1.6.5 Ordering
    # 1.6.6 Length

    # 1.7 Implementation of traces

    # 1.8 Traces of a process
    # 1.8.1 Laws [of traces]
    # 1.8.2 Implementation

    # 1.8.3 After

    # 1.9 More operations on traces
    # 1.9.1 Change of symbol
    # 1.9.2 Catenation [continued from 1.6.1]
    # 1.9.3 Interleaving
    # 1.9.4 Subscription
    # 1.9.5 Reversal
    # 1.9.6 Selection
    # 1.9.7 Composition

    # 1.10 Specifications
    # 1.10.1 Satisfaction
    # 1.10.2 Proofs

"""

CHAPTER_2_TEST_CHARS = """

    #
    # Chapter 2:  Concurrency
    #

"""

TEST_LINES = (
    textwrap.dedent(BASIC_TEST_CHARS + CHAPTER_1_TEST_CHARS + CHAPTER_2_TEST_CHARS)
    .strip()
    .splitlines()
)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
