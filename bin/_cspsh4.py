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
    """Order the Args or KwArgs of a Call"""

    def _to_deep_csp_(self):
        """Format the entire Call Tree as Csp"""
        chars = self._to_deep_style_(styles=self._csp_styles_, func=to_deep_csp)
        return chars

    def _to_deep_py_(self):
        """Format the entire Call Tree as Python"""
        chars = self._to_deep_style_(styles=self._py_styles_, func=to_deep_py)
        return chars

    def _to_deep_style_(self, styles, func):
        """Format the entire Call Tree as Csp or as Python"""

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

        if False:
            if self_type_name == "ChoiceTuple":
                if func == to_deep_csp:
                    if len(zippeds) > 2:
                        pdb.set_trace()

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
    """Order the KwArgs of a Call like a Collections Named Tuple"""

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
    """Order the indexed Args of a Call like a Tuple"""

    _py_styles_ = ("{}(\n", "\t{},\n", ")")

    def _zip_(self):
        """Yield each (index, key, value) of the Tuple, always with None as the key"""

        key = None
        for (index, value) in enumerate(self):
            yield (index, key, value)


def to_deep_csp(obj):
    """Format the entire Call Tree as Csp"""

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
# Declare a Csp Lisp
#

NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[(),:={|}μ•→⟨⟩])"
BLANKS_REGEX = r"(?P<blanks>[ \t\n]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


class AfterProc(
    collections.namedtuple("AfterProc", "before after".split()), SomeKwArgs
):
    """Run a Process after an Event"""

    _csp_styles_ = ("", "{}", " → {}", "")

    def after_proc_from(taker):

        # Match one or more of an Event Name and a "→" "\u2192" Rightwards Arrow Mark

        before = OrderedEventTuple.ordered_event_tuple_from(taker)
        if not before:
            shards = taker.peek_more_shards(2)
            if shards[1].is_mark("→"):
                before = Event.event_from(taker)

        if not before:
            return

        # Take one "→" "\u2192" Rightwards Arrow Mark

        shard = taker.peek_one_shard()
        assert shard and shard.is_mark("→")  # TODO:  Mark.take_one_from_(taker)
        taker.take_one_shard()

        # Take one Pocket Proc or Deffed Proc

        after = PocketProc.pocket_proc_from(taker)
        if not after:
            after = DeffedProc.deffed_proc_from(taker)
        assert after

        # Succeed

        after_proc = AfterProc(before, after=after)
        return after_proc


class ChoiceTuple(tuple, SomeArgs):
    """Choose 1 of N Processes"""

    _csp_styles_ = ("", "{} | ", "{}", "")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped

    def choice_tuple_from(taker, after_proc):

        after_procs = list()
        after_procs.append(after_proc)

        while True:

            shard = taker.peek_one_shard()
            if not shard.is_mark("|"):
                break

            taker.take_one_shard()

            next_proc = AfterProc.after_proc_from(taker)
            if not next_proc:
                next_proc = PocketProc.pocket_proc_from(taker)
            assert next_proc
            after_procs.append(next_proc)

        if len(after_procs) <= 1:
            return

        choice_tuple = ChoiceTuple(*after_procs)
        return choice_tuple


class DeffedProc(collections.namedtuple("DeffedProc", "name".split()), OneKwArg):
    """Mention a Proc by Name"""

    _csp_styles_ = ("", "{}", "")

    def deffed_proc_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_proc_name():
            taker.take_one_shard()

            deffed_proc = DeffedProc(shard.value)
            return deffed_proc


class Event(OneKwArg, collections.namedtuple("Event", "name".split())):
    """Name a thing that happens"""

    _csp_styles_ = ("", "{}", "")

    def event_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_event_name():
            taker.take_one_shard()

            event = Event(shard.value)
            return event


class EmptyMark(OneKwArg, collections.namedtuple("EmptyMark", "".split())):
    """Name the empty string that ends, or is all of, the Csp source"""

    _csp_styles_ = ("", "")

    def empty_mark_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_mark(""):
            # taker.take_one_shard()  # nope, don't

            empty_mark = EmptyMark()
            assert not empty_mark

            return empty_mark


class EventsProc(
    collections.namedtuple("EventsProc", "name alphabet body".split()), SomeKwArgs
):
    """Give a Name to a PocketProc choosing Events from an Alphabet"""

    _csp_styles_ = ("", "μ {}", " : {}", " • {}", "")

    def events_proc_from(taker):

        shard = taker.peek_one_shard()  # Csp:  μ
        if not shard.is_mark("μ"):
            return
        taker.take_one_shard()

        shard = taker.peek_one_shard()  # such as Csp:  μ X
        assert shard
        assert shard.is_proc_name()
        taker.take_one_shard()
        name = shard.value

        alphabet = None  # TODO: lazily detail the Alphabet of EventsProc
        shard = taker.peek_one_shard()  # such as Csp:  μ X : { ... } •
        if shard.is_mark(":"):
            taker.take_one_shard()

            alphabet = UnorderedEventTuple.unordered_event_tuple_from(taker)
            assert alphabet

        shard = taker.peek_one_shard()  # such as Csp:  μ X ... •
        assert shard.is_mark("•")
        taker.take_one_shard()

        body = PocketProc.pocket_proc_from(taker)  # such as Csp:  μ X ... • ( ... )
        assert body

        if not alphabet:
            lazy_events_proc = LazyEventsProc(name, body=body)
            return lazy_events_proc

        events_proc = EventsProc(name, alphabet=alphabet, body=body)
        return events_proc


class LazyEventsProc(
    collections.namedtuple("LazyEventsProc", "name body".split()), SomeKwArgs
):
    """Give a Name to a PocketProc choosing Events without declaring its Alphabet"""

    _csp_styles_ = ("", "μ {}", " • {}", "")


class OrderedEventTuple(tuple, SomeArgs):
    """Order two or more Events"""

    _csp_styles_ = ("", "{} → ", "{}", "")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped

    def ordered_event_tuple_from(taker):

        # Require an Event Name and a "→" "\u2192" Rightwards Arrow Mark

        shards = taker.peek_more_shards(3)  # TODO: pad with "" marks?

        match = None
        if shards[0].is_event_name():
            if shards[1].is_mark("→"):
                if shards[2].is_event_name():
                    match = True

        if not match:
            return

        # Accept one or more pairs of "→" and Event Name

        event_list = list()
        event_list.append(Event(shards[0].value))
        taker.take_one_shard()

        while True:

            shards = taker.peek_more_shards(2)

            match = None
            if shards[0].is_mark("→"):
                if shards[1].is_event_name():
                    match = True

            if not match:
                break

            taker.take_some_shards(2)

            event_list.append(Event(shards[1].value))

        # Succeed

        event_tuple = OrderedEventTuple(*event_list)
        return event_tuple


class ProcDef(collections.namedtuple("ProcDef", "name body".split()), SomeKwArgs):
    """Give a Name to a Pocket Proc or an Event Proc"""

    _csp_styles_ = ("", "{}", " = {}", "")

    def proc_def_from(taker):

        shards = taker.peek_more_shards(2)
        if not shards[1].is_mark("="):
            return

        shard = taker.peek_one_shard()
        if not shard.is_proc_name():
            return
        taker.take_one_shard()
        name = shard.value

        taker.take_one_shard()  # the mark "→"

        body = PocketProc.pocket_proc_from(taker)
        if not body:
            body = EventsProc.events_proc_from(taker)
        assert body

        proc_def = ProcDef(name, body=body)
        return proc_def


class PocketProc(collections.namedtuple("PocketProc", "pocketed".split()), SomeKwArgs):
    """Contain one AfterProc or a Choice between AfterProc's"""

    _csp_styles_ = ("(", "{}", ")")

    def pocket_proc_from(taker):

        shard = taker.peek_one_shard()
        if not shard.is_mark("("):
            return
        taker.take_one_shard()

        after_proc = AfterProc.after_proc_from(taker)
        assert after_proc

        pocketed = after_proc
        choice_tuple = ChoiceTuple.choice_tuple_from(taker, after_proc=after_proc)
        if choice_tuple:
            pocketed = choice_tuple

        shard = taker.peek_one_shard()
        assert shard.is_mark(")")
        taker.take_one_shard()

        pocket = PocketProc(pocketed)
        return pocket


class UnorderedEventTuple(tuple, SomeArgs):
    """Collect zero or more Events together"""

    _csp_styles_ = ("{{", "{}, ", "{}", "}}")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped

    def unordered_event_tuple_from(taker):

        # Open up with mark "{"

        shard = taker.peek_one_shard()
        if not shard.is_mark("{"):
            return
        taker.take_one_shard()

        # Accept zero or more pairs of Event Name and ","

        event_list = list()

        while True:

            shards = taker.peek_more_shards(2)

            match = None
            if shards[0].is_event_name():
                if shards[1].is_mark(","):
                    match = True

            if not match:
                break

            taker.take_some_shards(2)

            event_list.append(Event(shards[0].value))

        # Accept one or zero final Event Name's

        shard = taker.peek_one_shard()
        assert shard
        if shard.is_event_name():
            taker.take_one_shard()

            event_list.append(Event(shard.value))

        # Require close down with mark "}"

        shard = taker.peek_one_shard()
        assert shard
        assert shard.is_mark("}")
        taker.take_one_shard()

        # Succeed

        event_tuple = UnorderedEventTuple(*event_list)
        return event_tuple


#
# Parse Csp source lines
#


def eval_csp_calls(source):
    """Parse an entire Call Tree of Csp"""

    if False:  # TODO: --verbose
        stderr_print("cspsh: testing Csp:", source)

    # Drop the "\r" out of each "\r\n"

    nix_chars = "\n".join(source.splitlines()) + "\n"

    # Drop the comments

    chars = "\n".join(_.partition("#")[0] for _ in nix_chars.splitlines())

    # Split the source into names, marks, and blanks

    matches = re.finditer(SHARDS_REGEX, string=chars)
    items = list(_to_item_from_groupdict_(_.groupdict()) for _ in matches)
    split_shards = list(CspShard(*_) for _ in items)

    leading_shards = list(_ for _ in split_shards if _.key != "blanks")

    max_lookahead = 3
    empty_shard = CspShard("mark", value="")
    trailing_shards = max_lookahead * [empty_shard]

    shards = leading_shards + trailing_shards

    shards_taker = ShardsTaker()
    shards_taker.give_shards(shards)

    csp_taker = CspTaker(shards_taker)
    if False:  # TODO: --verbose
        stderr_print("cspsh: testing shards:", shards_taker.shards)

    try:
        call = csp_taker.accept_one_call()  # might be a first EmptyMark
        empty_mark = csp_taker.accept_empty_mark()
        assert empty_mark is not None
    except Exception:
        stderr_print("cspsh: failing before consuming:", shards_taker.shards)
        raise

    return call


def _to_item_from_groupdict_(groupdict):
    """Pick the 1 Item of Value Is Not None out of an Re FindIter GroupDict"""

    items = list(_ for _ in groupdict.items() if _[-1] is not None)
    assert len(items) == 1, groupdict

    item = items[-1]
    return item


class CspTaker:
    """
    Walk once through source chars, as split, working as yet another Yacc
    """

    def __init__(self, taker):
        self.taker = taker

    def accept_one_call(self):

        call = self.accept_empty_mark()

        call = call or self.accept_choice_tuple_or_after_proc()  # Csp:  ... → ... |

        call = call or self.accept_proc_def()  # Csp:  ... =

        call = call or self.accept_event_tuple()  # Csp:  { ...
        call = call or self.accept_event()  # Csp:  <lowercase_name>
        call = call or self.accept_deffed_proc()  # Csp:  <uppercase_name>

        call = call or self.accept_pocket_proc()  # Csp:  ( ...

        return call

    def accept_empty_mark(self):  # end of source file
        taker = self.taker
        empty_mark = EmptyMark.empty_mark_from(taker)
        return empty_mark

    def accept_proc_def(self):  # such as Csp:  VMCT = μ X : { ... } • ( ... )
        taker = self.taker
        proc_def = ProcDef.proc_def_from(taker)
        return proc_def

    def accept_choice_tuple_or_after_proc(self):  # (parse these with less backtracking)
        after_proc = self.accept_after_proc()
        if after_proc:
            choice_tuple = self.accept_choice_tuple(after_proc)
            if choice_tuple:
                return choice_tuple
            return after_proc

    def accept_after_proc(self):  # such as:  choc → X
        taker = self.taker
        after_proc = AfterProc.after_proc_from(taker)
        return after_proc

    def accept_choice_tuple(self, after_proc):  # such as Csp:  choc → X | toffee → X
        taker = self.taker
        choice_tuple = ChoiceTuple.choice_tuple_from(taker, after_proc=after_proc)
        return choice_tuple

    def accept_event_tuple(self):  # such as Csp:  {coin, choc, toffee}
        taker = self.taker
        event_tuple = UnorderedEventTuple.unordered_event_tuple_from(taker)
        return event_tuple

    def accept_event(self):  # such as Csp:  coin
        taker = self.taker
        event = Event.event_from(taker)
        return event

    def accept_deffed_proc(self):  # such as Csp:  X
        taker = self.taker
        deffed_proc = DeffedProc.deffed_proc_from(taker)
        return deffed_proc

    def accept_pocket_proc(self):  # such as Csp:  ( ... )
        taker = self.taker
        pocket_proc = PocketProc.pocket_proc_from(taker)
        return pocket_proc


class CspShard(collections.namedtuple("CspShard", "key value".split())):
    """
    Carry a fragment of Csp Source Code
    """

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
# Sketch the wound, in wounded Csp source
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

    stderr_print("")
    stderr_print("cspsh: hello")

    parser = compile_argdoc(epi="workflow:")
    _ = parser.parse_args(argv[1:])

    try_py_then_csp()
    try_csp_then_py()

    stderr_print("cspsh: + exit 0")


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

        stderr_print("error: cspsh: update main argdoc to match help, or vice versa")

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
    Walk once through source chars, as split, working as yet another Lexxer

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

    def peek_more_shards(self, limit):
        """List zero or more remaining shards"""

        more_shards = list(self.shards)  # see also:  self.peek_more
        more_shards = more_shards[:limit]

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


def bootstrap_py_csp_fragments():
    """Put a few fragments of Py Source, and their Csp Source, under test"""

    # Csp Python of Csp:  coin  # an event exists

    want0 = textwrap.dedent(
        """
        Event("coin")
        """
    ).strip()

    # Csp Python of Csp:  {coin, choc, toffee}  # an alphabet collects events

    want1 = textwrap.dedent(
        """
        UnorderedEventTuple(
            Event("coin"),
            Event("choc"),
            Event("toffee"),
        )
        """
    ).strip()

    # Csp Python of Csp:  choc → X  # event guards process

    want11 = textwrap.dedent(
        """
        AfterProc(
            before=Event("choc"),
            after=DeffedProc("X"),
        )
        """
    ).strip()

    # Csp Python of Csp:  choc → X | toffee → X  # events guard processes

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

    # Csp Python of Csp:  coin → (choc → X | toffee → X)  # events guard processes

    want2 = textwrap.dedent(
        """
        AfterProc(
            before=Event("coin"),
            after=PocketProc(
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

    # Csp Python of Csp:  VMCT = μ X : {...} • (coin → (choc → X | toffee → X))

    want3 = textwrap.dedent(
        """
        ProcDef(
            name="VMCT",
            body=EventsProc(
                name="X",
                alphabet=UnorderedEventTuple(
                    Event("coin"),
                    Event("choc"),
                    Event("toffee"),
                ),
                body=PocketProc(
                    pocketed=AfterProc(
                        before=Event("coin"),
                        after=PocketProc(
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

    # Same lines of Csp as above

    CSP_WANTS = textwrap.dedent(
        """
        coin
        {coin, choc, toffee}
        choc → X
        choc → X | toffee → X
        coin → (choc → X | toffee → X)
        VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))
        """
    )

    # Return the fragments chosen

    py_wants = (want0, want1, want11, want20, want2, want3)
    csp_wants = CSP_WANTS.strip().splitlines()
    return (py_wants, csp_wants)


def try_py_then_csp():
    """Translate from Py Source to Calls to Py Source, to Csp Source, to Csp Calls"""

    (py_wants, csp_wants) = bootstrap_py_csp_fragments()

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

        if csp_got != csp_want:
            stderr_print("cspsh: want Csp::  {!r}".format(csp_want))
            stderr_print("cspsh: got Csp:::  {!r}".format(csp_got))
            assert False

        # test parse as Csp

        csp_evalled = eval_csp_calls(csp_want)

        if csp_evalled != py_evalled:
            stderr_print("cspsh: csp_evalled", csp_evalled)
            stderr_print("cspsh: py_evalled", py_evalled)

        assert csp_evalled == py_evalled, argparse.Namespace(
            want_deep_py=py_want,
            got_deep_py=to_deep_py(csp_evalled),
        )


def try_csp_then_py():
    """Translate from Csp Source to Calls to Py Source, to Py Calls, to Csp Source"""

    chars = OUR_BOOTSTRAP
    chars += CHAPTER_1

    csp_chars = textwrap.dedent(chars).strip()
    csp_chars = "\n".join(_.partition("#")[0] for _ in csp_chars.splitlines())
    csp_wants = (_.strip() for _ in csp_chars.splitlines() if _.strip())

    for csp_want in csp_wants:
        py_got = None
        try:
            csp_evalled = eval_csp_calls(csp_want)
            py_got = to_deep_py(csp_evalled)
            py_evalled = eval(py_got)
            csp_got = to_deep_csp(py_evalled)
            if csp_got != csp_want:
                stderr_print("cspsh: want Csp::  {!r}".format(csp_want))
                stderr_print("cspsh: got Csp:::  {!r}".format(csp_got))
                assert False
        except Exception:
            stderr_print("cspsh: failing at test of Csp:  {}".format(csp_want))
            stderr_print("cspsh: failing with Python of:  {}".format(py_got))
            raise


OUR_BOOTSTRAP = """

    coin
    {coin, choc, toffee}
    choc → X
    choc → X | toffee → X
    coin → (choc → X | toffee → X)
    VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))

"""

CHAPTER_1 = """

    #
    # Chapter 1:  Processes
    #


    # 1.1 Introduction, p.1


    # 1.1.1 Prefix, p.3

    STOP
    coin → STOP  # 1.1.1 X1
    coin → choc → coin → choc → STOP  # 1.1.1 X2

    CTR = (right → up → right → right → STOP)  # 1.1.1 X3

    # x → y  # no, name 'y' is not upper case process name 'Y'
    # P → Q  # no, name 'P' is not lower case event name 'p'

    x → (y → STOP)


    # 1.1.2 Recursion, p.4

    CLOCK = (tick → CLOCK)
    CLOCK = (tick → tick → tick → CLOCK)
    CLOCK = μ X : {tick} • (tick → X)  # 1.1.2 X1

    VMS = (coin → (choc → VMS))  # 1.1.2 X2

    CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
    CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4


    # 1.1.3 Choice, p.7

    (up → STOP | right → right → up → STOP)  # 1.1.3 X1

    # CH5C = in5p → (  # 1.1.3 X2
    #     out1p → out1p → out1p → out2p → CH5C |
    #     out2p → out1p → out2p → CH5C)

    (x → P | y → Q)

    VMCT = μ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3

    # VMC = (in2p → (large → VMC |  # 1.1.3 X4
    #                small → out1p → VMC) |
    #        in1p → (small → VMC |
    #                in1p → (large → VMC |
    #                        in1p → STOP)))

    VMCRED = μ X • (coin → choc → X | choc → coin → X)  # 1.1.3 X5

    VMS2 = (coin → VMCRED)  # 1.1.3 X6

    # COPYBIT = μ X • (in.0 → out.0 → X |  # 1.1.3 X7
    #                  in.1 → out.1 → X)

    (x → P | y → Q | z → R)
    # (x → P | x → Q)  # no, choices not distinct: ['x', 'x']
    # (x → P | y)  # no, '| y)' is not '| y → P'
    # (x → P) | (y → Q)  # no, '|' is not an operator on processes
    (x → P | (y → Q | z → R))

    # RUN-A = (x:A → RUN-A)  # 1.1.3 X8


    # 1.1.4 Mutual recursion, p.11

    # αDD = αO = αL = {setorange, setlemon, orange, lemon}

    DD = (setorange → O | setlemon → L)  # 1.1.4 X1
    O = (orange → O | setlemon → L | setorange → O)
    L = (lemon → L | setorange → O | setlemon → L)

    CT0 = (up → CT1 | around → CT0)  # 1.1.4 X2
    CT1 = (up → CT2 | down → CT0)
    CT2 = (up → CT3 | down → CT1)

    CT0 = (around → CT0 | up → CT1)  # 1.1.4 X2  # Variation B
    CT1 = (down → CT0 | up → CT2)
    CT2 = (down → CT1 | up → CT3)

"""


#
# To do
#

# TODO:  parse alphabet grammar:  α RUN-A x:A
# TODO:  parse trace grammar:  ⟨ ... ⟩
# TODO:  parse multi-line grammar
# TODO:  emit Csp Source Repair Hints

# TODO:  review grammar & grammar class names vs CspBook Pdf

# TODO:  Slackji :: transliteration of Unicode Org names of the Csp Unicode symbols
# TODO:  Ascii transliteration of Csp Unicode


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
