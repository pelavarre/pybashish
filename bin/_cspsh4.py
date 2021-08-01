#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

workflow:
  while :; do
    date
    cd ~/Public/pybashish/bin && \
      --black _cspsh4.py && --flake8 _cspsh4.py && python3 _cspsh4.py
    echo 'press Control+D (EOF) to continue'
    read
  done

examples:
  _cspsh4.py
"""

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


class Call:
    """Collect the Args or KwArgs of a Call"""

    def _to_deep_csp_(self):
        """Format the entire Call Tree as CSP"""
        chars = self._to_deep_style_(styles=self._csp_styles_, func=to_deep_csp)
        return chars

    def _to_deep_py_(self):
        """Format the entire Call Tree as Python"""
        chars = self._to_deep_style_(styles=self._py_styles_, func=to_deep_py)
        return chars

    def _to_deep_style_(self, styles, func):
        """Format the entire Call Tree as CSP or as Python"""

        assert len(styles) >= 3, repr(styles)

        self_type_name = type(self).__name__

        # Open up, visit each Item or Value, and close out

        chars = ""

        if "{}" not in styles[0]:  # 1st
            chars += styles[0].format()
        else:
            chars += styles[0].format(self_type_name)

        zippeds = list(self._zip_())
        zipped_styles = styles[1:][:-1]

        for zipped in zippeds:
            (index, key, value) = zipped

            # Choose a style for the zipped Item or Value

            zipped_style_index = -1  # end with the last zipped style
            if len(zipped_styles) > 1:
                if index < (len(zippeds) - 1):
                    zipped_style_index = index  # step through the styles
                    if index >= (len(zipped_styles) - 1):
                        zipped_style_index = -2  # but don't step past the 2nd to last

            style = zipped_styles[zipped_style_index]

            # Apply the chosen style

            count = style.count("{}")
            assert count in (1, 2), (count, self_type_name)

            func_value = func(value)

            if (count == 1) or (key is None):
                styled = style.format(func_value)
            else:
                styled = style.format(key, func_value)

            # Indent each Item or Value

            dented = styled
            if "\n" in styled:
                dented = "\n\t".join(styled.splitlines()) + "\n"

            chars += dented

        chars += styles[-1].format()  # Last

        # Convert Tabs to Spaces

        spaced_chars = chars.replace("\t", DENT)
        return spaced_chars


class SomeKwArgs(Call):
    """Collect the KwArgs of a Call like a Collections Named Tuple"""

    _py_styles_ = ("{}(\n", "\t{}={},\n", ")")

    def _zip_(self):
        """Yield each (index, key, value) of the Named Tuple in order"""

        for (index, key) in enumerate(self._fields):  # from collections.namedtuple
            value = getattr(self, key)
            yield (index, key, value)


class OneKwArg(SomeKwArgs):
    """Like SomeKwArgs, but styled differently"""

    _py_styles_ = ("{}(", "{}", ")")


class SomeArgs(Call):
    """Collect the indexed Args of a Call like a Tuple"""

    _py_styles_ = ("{}(\n", "\t{},\n", ")")

    def _zip_(self):
        """Yield each (index, key, value) of the Tuple, always with None as the key"""

        key = None
        for (index, value) in enumerate(self):
            yield (index, key, value)


def to_deep_csp(obj):
    """Format the entire Call Tree as CSP"""

    if hasattr(obj, "_to_deep_csp_"):
        chars = obj._to_deep_csp_()
    else:
        assert isinstance(obj, str), type(obj)
        chars = "{}".format(obj)  # TODO: too easily goes wrong

    return chars


def to_deep_py(obj, depth=0):
    """Format the entire Call Tree as Python"""

    if hasattr(obj, "_to_deep_py_"):
        chars = obj._to_deep_py_()
    else:
        assert isinstance(obj, str), type(obj)
        chars = '"{}"'.format(obj)  # TODO: too easily goes wrong

    return chars


#
# Declare a CSP Lisp
#

NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[(),:={|}μ•→⟨⟩])"
BLANKS_REGEX = r"(?P<blanks>[ \t\n]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


class AfterProc(
    collections.namedtuple("AfterProc", "before after".split()), SomeKwArgs
):

    _csp_styles_ = ("", "{}", " → {}", "")

    def accept_one_from(taker):
        """Accept zero or more Events as an EventTuple"""

        shards = taker.peek_more_shards()
        if not shards[1:]:
            return

        if not shards[1].is_mark("→"):
            return

        before = Event.accept_one_from(taker)
        if not before:
            return

        taker.take_one_shard()  # the mark "→"

        after = Pocket.accept_one_from(taker)
        if not after:
            after = DeffedProc.accept_one_from(taker)
        assert after

        after_proc = AfterProc(before, after=after)
        return after_proc


class ChoiceTuple(tuple, SomeArgs):

    _csp_styles_ = ("", "{}", " | {}", "")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped

    def accept_one_from(taker, after_proc):
        """Accept two or more After Procs as a Choice Tuple"""

        after_procs = list()
        after_procs.append(after_proc)

        while True:

            shard = taker.peek_one_shard()
            if not shard:
                break
            if not shard.is_mark("|"):
                break

            taker.take_one_shard()

            next_after_proc = AfterProc.accept_one_from(taker)
            assert next_after_proc
            after_procs.append(next_after_proc)

        if len(after_procs) <= 1:
            return

        choice_tuple = ChoiceTuple(*after_procs)
        return choice_tuple


class DeffedProc(collections.namedtuple("DeffedProc", "name".split()), OneKwArg):

    _csp_styles_ = ("", "{}", "")

    def accept_one_from(taker):
        """Accept a proc name as an Deffed Proc"""

        shard = taker.peek_one_shard()
        if shard.is_proc_name():

            taker.take_one_shard()
            deffed_proc = DeffedProc(shard.value)
            return deffed_proc


class Event(OneKwArg, collections.namedtuple("Event", "name".split())):

    _csp_styles_ = ("", "{}", "")

    def accept_one_from(taker):
        """Accept an event name as an Event"""

        shard = taker.peek_one_shard()
        if shard.is_event_name():

            taker.take_one_shard()
            event = Event(shard.value)
            return event


class EventTuple(tuple, SomeArgs):

    _csp_styles_ = ("{{", "{}, ", "{}", "}}")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped

    def accept_one_from(taker):
        """Accept zero or more Events as an Event Tuple"""

        events = list()

        shards = taker.peek_more_shards()
        len_shards = 0
        if len_shards >= len(shards):
            return

        shard = shards[len_shards]
        len_shards += 1
        if not shard.is_mark("{"):
            return

        event_list = list()
        while True:

            shard = shards[len_shards]
            if not shard.is_event_name():
                break

            len_shards += 1
            if len_shards >= len(shards):
                break

            event_list.append(Event(shard.value))

            shard = shards[len_shards]
            if not shard.is_mark(","):
                break

            len_shards += 1
            if len_shards >= len(shards):
                break

        shard = shards[len_shards]
        if not shard.is_mark("}"):
            return

        len_shards += 1
        taker.take_some_shards(len_shards)

        events = EventTuple(*event_list)
        return events


class EventsProc(
    collections.namedtuple("EventsProc", "name events body".split()), SomeKwArgs
):

    _csp_styles_ = ("", "μ {}", " : {}", " • {}", "")


class Pocket(collections.namedtuple("Pocket", "pocketed".split()), SomeKwArgs):

    _csp_styles_ = ("(", "{}", ")")

    def accept_one_from(taker):
        """Accept an AfterProc between parentheses"""

        shard = taker.peek_one_shard()
        if not shard.is_mark("("):
            return
        taker.take_one_shard()

        after_proc = AfterProc.accept_one_from(taker)
        assert after_proc

        pocketed = after_proc
        choice_tuple = ChoiceTuple.accept_one_from(taker, after_proc=after_proc)
        if choice_tuple:
            pocketed = choice_tuple

        shard = taker.peek_one_shard()
        assert shard.is_mark(")")
        taker.take_one_shard()

        pocket = Pocket(pocketed)
        return pocket


class ProcDef(collections.namedtuple("ProcDef", "name body".split()), SomeKwArgs):

    _csp_styles_ = ("", "{}", " = {}", "")


#
# Parse CSP source lines
#


def eval_csp_calls(source):
    """Parse an entire Call Tree of CSP"""

    # drop the "\r" out of each "\r\n"

    nix_chars = "\n".join(source.splitlines()) + "\n"

    # split the source into names, marks, and blanks

    matches = re.finditer(SHARDS_REGEX, string=nix_chars)
    shards = list(CspShard(_.groupdict()) for _ in matches)
    words = list(_ for _ in shards if _.key != "blanks")

    shards_taker = ShardsTaker()
    shards_taker.give_shards(words)

    csp_taker = CspTaker(shards_taker)
    call = csp_taker.accept_one()
    csp_taker.take_eof()

    return call

    # TODO: delete this

    _ = """

        coin
        {coin, choc, toffee}
        choc → X
        choc → X | toffee → X
        coin → (choc → X | toffee → X)

        VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))

    """


class CspTaker:
    """
    Walk once thru source chars, as split, working as yet another Yacc
    """

    def __init__(self, taker):
        self.taker = taker

    def accept_one(self):

        after_proc = self.accept_after_proc()
        if after_proc:
            choice_tuple = self.accept_choice_tuple(after_proc)
            if choice_tuple:
                return choice_tuple
            return after_proc

        event = self.accept_event()
        if event:
            return event

        events = self.accept_event_tuple()
        if events:
            return events

    def accept_after_proc(self):
        taker = self.taker
        after_proc = AfterProc.accept_one_from(taker)
        return after_proc

    def accept_choice_tuple(self, after_proc):
        taker = self.taker
        choice_tuple = ChoiceTuple.accept_one_from(taker, after_proc=after_proc)
        return choice_tuple

    def accept_deffed_proc(self):
        taker = self.taker
        deffed_proc = DeffedProc.accept_one_from(taker)
        return deffed_proc

    def accept_event(self):
        taker = self.taker
        event = Event.accept_one_from(taker)
        return event

    def accept_event_tuple(self):
        taker = self.taker
        event_tuple = EventTuple.accept_one_from(taker)
        return event_tuple

    def take_eof(self):
        taker = self.taker
        taker.take_beyond_shards()


class CspShard(collections.namedtuple("Event", "key value".split())):
    def __new__(cls, groupdict):

        key = None
        value = None

        for (item_key, item_value) in groupdict.items():
            if item_value is not None:
                assert key is None, groupdict
                assert value is None, groupdict

                key = item_key
                value = item_value

        assert key is not None, groupdict

        return super().__new__(cls, key=key, value=value)

    def is_event_name(self):
        if self.key == "name":
            if self.value == self.value.lower():
                return True

    def is_proc_name(self):
        if self.key == "name":
            if self.value == self.value.upper():
                return True

    def is_mark(self, mark):
        if self.key == "mark":
            if self.value == mark:
                return True

    def strip(self):
        stripped = self.value.strip()
        return stripped


#
# Sketch the wound, in wounded CSP source
#


def depth_opened(source):
    """List marks opened but not closed"""

    OPEN_MARKS = "{[("
    open_regex = r"[{}]".format(re.escape(OPEN_MARKS))  # r"[\{\[\("
    assert OPEN_MARKS == "".join(list(re.findall(open_regex, OPEN_MARKS)))

    CLOSE_MARKS = ")]}"
    close_regex = r"[{}]".format(re.escape(CLOSE_MARKS))  # r"[\)\]\}]"
    assert CLOSE_MARKS == "".join(list(re.findall(close_regex, CLOSE_MARKS)))

    marks = OPEN_MARKS + CLOSE_MARKS
    regex = r"[{}]".format(re.escape(OPEN_MARKS))  # r"[\{\[\("r"\)\]\}]"
    assert marks == "".join(list(re.findall(close_regex, CLOSE_MARKS)))

    opening = ""
    closing = ""
    for mark in re.findall(regex, string=marks):
        assert len(mark) == 1, repr(mark)

        if mark in OPEN_MARKS:
            opening += mark
        elif mark == opening[-1:]:
            opening = opening[:-1]
        else:
            closing += mark

    return (closing, opening)


#
# Run from the command line
#


def main(argv):
    """Run from the command line"""

    parser = compile_argdoc(epi="workflow:")
    _ = parser.parse_args(argv[1:])

    try_to_deep_style()

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
        lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
        stderr_print("\n".join(lines))

    return diff_lines


# deffed in many files  # missing from docs.python.org
class ShardsTaker(argparse.Namespace):
    """
    Walk once thru source chars, as split, working as yet another Lexxer

    Define "take" to mean require and consume
    Define "peek" to mean look ahead into the shards followed by infinitely many None's
    Define "accept" to mean take if present, else quietly don't bother
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_shards(self, shards):
        """Give shards, such as from r"(?P<...>...)+" via 'match.groupdict().items()'"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Take one shard, and drop it, don't return it"""

        self.shards = self.shards[1:]

    def take_some_shards(self, count):
        """Take the next few shards, and drop them, don't return them"""

        self.shards = self.shards[count:]

    def peek_one_shard(self):
        """Return the next shard, but without consuming it"""

        if self.shards:  # infinitely many None's past the last shard

            return self.shards[0]

    def peek_some_shards(self, count):
        """Return the next few shards, without consuming them"""

        nones = count * [None]
        some = (self.shards[:count] + nones)[:count]

        return some

    def peek_equal_shards(self, hopes):
        """Return the next few shards, but only if they equal our hopes"""

        some = self.peek_some_shards(len(hopes))
        if some == list(hopes):

            return True

    def take_beyond_shards(self):
        """Do nothing if all shards consumed, else raise mystic IndexError"""

        count = len(self.shards)
        if count:

            assert not self.shards, self.shards  # TODO: assert else raise
            raise IndexError("{} remaining shards".format(count))

    def peek_more(self):
        """Return True if more shards remain"""

        more = bool(self.shards)  # see also:  self.peek_more_shards

        return more

    def peek_more_shards(self):
        """List zero or more remaining shards"""

        more_shards = list(self.shards)  # see also:  self.peek_more

        return more_shards

    def accept_blank_shards(self):
        """Drop zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():

                break

            self.take_one_shard()

    def peek_upto_blank_shard(self):
        """List zero or more non-blank shards found here"""

        shards = list()
        for shard in self.shards:
            if not shard.strip():

                break

            shards.append(shard)

        return shards


#
# Self test
#


def try_to_deep_style():
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
            after=Pocket(
                pocketed=ChoiceTuple(
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
                body=Pocket(
                    pocketed=AfterProc(
                        before=Event("coin"),
                        after=Pocket(
                            pocketed=ChoiceTuple(
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

        # test parse as Py

        py_evalled = eval(py_want)

        # test print as Py

        py_got = to_deep_py(py_evalled)

        assert not stderr_print_diff(input=py_want, output=py_got)

        # test print as Csp

        csp_got = to_deep_csp(py_evalled)

        assert csp_got == csp_want, dict(csp_got=csp_got, csp_want=csp_want)

        # test parse as Csp

        if index > 4:
            continue

        csp_evalled = eval_csp_calls(csp_want)

        if csp_evalled != py_evalled:
            stderr_print("csp_evalled", csp_evalled)
            stderr_print("py_evalled", py_evalled)
            pdb.set_trace()

        assert csp_evalled == py_evalled, dict(
            want_deep_py=py_want,
            got_deep_py=to_deep_py(csp_evalled),
        )

        stderr_print("passed", csp_want)


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
