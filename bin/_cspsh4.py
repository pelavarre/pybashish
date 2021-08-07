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


class ClassyTuple(tuple):
    """Work like a Tuple, but when Classname is Not "tuple", say so"""

    def __repr__(self):
        self_type_name = type(self).__name__
        repped = "{}{}".format(self_type_name, super().__repr__())
        return repped


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
# Declare a Csp Lisp Lexxer, in the way of Linux Lex
#
# Split the Csp Source into blank and nonblank Shards,
# and take the nonblank Shards as tokens into a Parser
#

NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[(),:={|}αμ•→⟨⟩])"
COMMENT_REGEX = r"(?P<comment>#[^\n]+)"
BLANKS_REGEX = r"(?P<blanks>[ \t\n]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, COMMENT_REGEX, BLANKS_REGEX])

OPENING_MARKS = "([{⟨"
CLOSING_MARKS = ")]}⟩"


#
# Declare a Csp Lisp Parser, in the way of Linux Yacc,
# but by Recursive Descent with Lots of Lookahead
#


class AfterProc(
    collections.namedtuple("AfterProc", "before after".split()), SomeKwArgs
):
    """Run a Proc after an Event"""

    _csp_styles_ = ("", "{}", " → {}", "")

    def event_menu(self):
        before = self.before
        menu = before.event_menu()
        return menu

    @staticmethod
    def after_proc_from(taker):

        # Take one or more of an Event Name and a "→" "\u2192" Rightwards Arrow Mark

        ordered_event_tuple = OrderedEventTuple.ordered_event_tuple_from(taker)

        before = ordered_event_tuple
        if not ordered_event_tuple:
            shards = taker.peek_more_shards(5)

            match = None
            if shards[1].is_mark("→"):
                match = True  # x → P
            elif shards[1].is_mark(":") and shards[4].is_mark("→"):
                match = True  # x : α P → P

            if match:
                chosen_event_or_event = ChosenEvent.chosen_event_or_event_from(taker)
                before = chosen_event_or_event

        if not before:
            return

        # Take one "→" "\u2192" Rightwards Arrow Mark

        shard = taker.peek_one_shard()

        if not shard.is_mark("→"):
            if ordered_event_tuple:
                raise csp_hint_proc_over_event(ordered_event_tuple[-1])

        assert shard.is_mark("→")  # TODO:  Mark.take_one_from_(taker)
        taker.take_one_shard()

        # Take one Pocket Proc or Deffed Proc

        after = PocketProc.pocket_proc_from(taker)
        if not after:
            after = DeffedProc.deffed_proc_from(taker)
        assert after

        # Succeed

        after_proc = AfterProc(before, after=after)
        return after_proc


class ArgotDef(collections.namedtuple("ArgotDef", "before after".split()), SomeKwArgs):
    """Detail an Alphabet of Events after listing Names for the Alphabet"""

    _csp_styles_ = ("", "{} = ", "{}", "")

    @staticmethod
    def argot_def_from(taker, argot_name):

        # Take one or more Argot Names, each marked by "α"

        argot_names = list()
        argot_names.append(argot_name)

        while True:

            shards = taker.peek_more_shards(2)

            if not shards[0].is_mark("="):
                break
            if not shards[1].is_mark("α"):
                break

            taker.take_one_shard()  # just the "=", not also the "α"

            next_argot_name = ArgotName.argot_name_from(taker)
            assert next_argot_name
            argot_names.append(next_argot_name)

        if argot_names[1:]:
            before = OrderedArgotNameTuple(*argot_names)
        else:
            before = argot_name

        # Take one "=" "\u003D" Equals Sign

        shard = taker.peek_one_shard()
        assert shard.is_mark("=")
        taker.take_one_shard()

        # Take one Alphabet

        after = UnorderedEventTuple.unordered_event_tuple_from(taker)

        argot_def = ArgotDef(before, after=after)
        return argot_def


class ArgotName(collections.namedtuple("ArgotName", "deffed_proc".split()), SomeKwArgs):
    """Pick an Alphabet of Events out of a Deffed Proc"""

    _csp_styles_ = ("α", "{}", "")

    @staticmethod
    def argot_name_from(taker):

        shard = taker.peek_one_shard()
        if not shard.is_mark("α"):
            return
        taker.take_one_shard()

        deffed_proc = DeffedProc.deffed_proc_from(taker)
        assert deffed_proc

        argot_name = ArgotName(deffed_proc)
        return argot_name


class ChoiceTuple(ClassyTuple, SomeArgs):
    """Choose 1 of N Proc's"""

    _csp_styles_ = ("", "{} | ", "{}", "")

    def __new__(cls, *args):  # move these 'def __new__' into ClassyTuple somehow?
        return super().__new__(cls, args)

    def event_menu(self):

        menu = OrderedEventTuple()
        for choice in self:

            choice_menu = choice.event_menu()
            # menu += OrderedEventTuple(choice_menu)  # TODO: does this work?
            menu = OrderedEventTuple(*(tuple(menu) + tuple(choice_menu)))

        return menu

    @staticmethod
    def choice_tuple_from(taker, after_proc):

        after_procs = list()
        after_procs.append(after_proc)

        #

        while True:

            shard = taker.peek_one_shard()
            if not shard.is_mark("|"):
                break
            taker.take_one_shard()

            next_after_proc = AfterProc.after_proc_from(taker)

            if not next_after_proc:
                event = Event.event_from(taker)
                if event:
                    raise csp_hint_choice_after_proc_over_event(event)
                pocket_proc = PocketProc.pocket_proc_from(taker)
                if pocket_proc:
                    raise csp_hint_choice_after_proc_over_pocket_proc(pocket_proc)

            assert next_after_proc
            after_procs.append(next_after_proc)

        if not after_procs[1:]:
            return

        #

        choice_tuple = ChoiceTuple(*after_procs)
        menu = choice_tuple.event_menu()

        names = sorted(_.name for _ in menu)
        dupes = list(
            names[_]
            for _ in range(len(names))
            if (
                ((_ > 0) and (names[_ - 1] == names[_]))
                or ((_ < (len(names) - 1)) and (names[_] == names[_ + 1]))
            )
        )
        if dupes:
            raise csp_hint_choice_dupes(dupes)

        return choice_tuple

    @staticmethod
    def choice_tuple_or_after_proc_from(taker):

        after_proc = AfterProc.after_proc_from(taker)
        if after_proc:
            choice_tuple = ChoiceTuple.choice_tuple_from(taker, after_proc=after_proc)
            if choice_tuple:
                return choice_tuple
            return after_proc


class ChosenEvent(
    collections.namedtuple("ChosenEvent", "event_name argot_name".split()), SomeKwArgs
):
    """Define a Name for an Event chosen from the Argot of a Proc"""

    _csp_styles_ = ("", "{}", ":{}", "")

    @staticmethod
    def chosen_event_from(taker):

        shards = taker.peek_more_shards(2)
        if not shards[1].is_mark(":"):
            return

        shard = taker.peek_one_shard()
        if not shard.is_event_name():
            return
        taker.take_one_shard()
        event_name = shard.value

        taker.take_one_shard()  # the mark ":"

        argot_name = ArgotName.argot_name_from(taker)

        chosen_event = ChosenEvent(event_name, argot_name=argot_name)
        return chosen_event

    @staticmethod
    def chosen_event_or_event_from(taker):

        chosen_event = ChosenEvent.chosen_event_from(taker)
        if chosen_event:
            return chosen_event

        event = Event.event_from(taker)
        return event


class DeffedProc(collections.namedtuple("DeffedProc", "name".split()), OneKwArg):
    """Mention a Proc by Name"""

    _csp_styles_ = ("", "{}", "")

    @staticmethod
    def deffed_proc_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_proc_name():
            taker.take_one_shard()

            deffed_proc = DeffedProc(shard.value)
            return deffed_proc


class Event(OneKwArg, collections.namedtuple("Event", "name".split())):
    """Name a thing that happens"""

    _csp_styles_ = ("", "{}", "")

    @staticmethod
    def event_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_event_name():
            taker.take_one_shard()

            event = Event(shard.value)
            return event

    def event_menu(self):
        menu = OrderedEventTuple(self)
        return menu


class EmptyMark(OneKwArg, collections.namedtuple("EmptyMark", "".split())):
    """Name the empty string that ends, or is all of, the Csp source"""

    _csp_styles_ = ("", "")

    @staticmethod
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

    @staticmethod
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


class OrderedArgotNameTuple(ClassyTuple, SomeArgs):
    """Order two or more Argot Names"""

    _csp_styles_ = ("", "{} = ", "{}", "")

    def __new__(cls, *args):
        return super().__new__(cls, args)


class OrderedEventTuple(ClassyTuple, SomeArgs):
    """Order two or more Events"""

    _csp_styles_ = ("", "{} → ", "{}", "")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def event_menu(self):

        if not self:
            return OrderedEventTuple()

        menu = self[0].event_menu()
        return menu

    @staticmethod
    def ordered_event_tuple_from(taker):

        # Require one "→" "\u2192" Rightwards Arrow Mark in between two Event Names

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

    @staticmethod
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
            if not body:
                body = ChoiceTuple.choice_tuple_or_after_proc_from(taker)
        assert body

        proc_def = ProcDef(name, body=body)
        return proc_def


class PocketProc(collections.namedtuple("PocketProc", "pocketed".split()), SomeKwArgs):
    """Contain one AfterProc or a Choice between AfterProc's"""

    _csp_styles_ = ("(", "{}", ")")

    def event_menu(self):
        pocketed = self.pocketed
        menu = pocketed.event_menu()
        return menu

    @staticmethod
    def pocket_proc_from(taker):

        shard = taker.peek_one_shard()
        if not shard.is_mark("("):
            return
        taker.take_one_shard()

        pocketed = ChoiceTuple.choice_tuple_or_after_proc_from(taker)

        shard = taker.peek_one_shard()
        assert shard.is_mark(")")
        taker.take_one_shard()

        pocket = PocketProc(pocketed)
        return pocket


class TracedEventTuple(ClassyTuple, SomeArgs):  # TODO: combine with OrderedEventTuple
    """Order two or more Events"""

    _csp_styles_ = ("⟨", "{},", "{}", "⟩")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    @staticmethod
    def traced_event_tuple_from(taker):

        # Open up with mark "⟨"

        shard = taker.peek_one_shard()
        if not shard.is_mark("⟨"):
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

        # TODO: Accept extra "," mark before close mark "⟩"

        # Require close down with mark "⟩"

        shard = taker.peek_one_shard()
        assert shard
        assert shard.is_mark("⟩")
        taker.take_one_shard()

        # Succeed

        event_tuple = TracedEventTuple(*event_list)
        return event_tuple


class UnorderedEventTuple(ClassyTuple, SomeArgs):
    """Collect zero or more Events together"""

    _csp_styles_ = ("{{", "{}, ", "{}", "}}")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    @staticmethod
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

        # TODO: Accept extra "," mark before close mark "}"

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
    """Split and structure calls corresponding to Source Chars of Csp"""

    shards = split_csp(source)

    (opened, closed) = balance_csp_shards(shards)
    assert not closed, (closed, opened, source)
    assert not opened, (closed, opened, source)

    call = parse_csp_calls(source)  # TODO: stop repeating work of "split_csp"

    return call  # may be falsey because empty, but is not None


def split_csp(source):
    """Split Csp Source into blank and nonblank, balanced and unbalanced, Shards"""

    # Drop the "\r" out of each "\r\n"

    chars = "\n".join(source.splitlines()) + "\n"

    # Split the source into names, marks, comments, and blanks

    matches = re.finditer(SHARDS_REGEX, string=chars)
    items = list(_to_item_from_groupdict_(_.groupdict()) for _ in matches)
    shards = list(CspShard(*_) for _ in items)

    # Require no chars dropped

    rejoined = "".join(_.value for _ in shards)
    assert rejoined == chars  # TODO: cope more gracefully with new chars

    # Succeed

    return shards


def balance_csp_shards(shards):
    """Open up paired marks, close them down, and say what's missing"""

    opened = ""
    closed = ""
    next_closing_mark = None

    for shard in shards:

        # Open up any opening mark

        for mark in OPENING_MARKS:
            if shard.is_mark(mark):
                opened += mark
                pair_index = OPENING_MARKS.index(mark)
                next_closing_mark = CLOSING_MARKS[pair_index]

                break

        # Close down an open mark followed by its corresponding close mark

        for mark in CLOSING_MARKS:

            if shard.is_mark(mark):
                if mark == next_closing_mark:
                    opened = opened[:-1]

                # List close marks given before a corresponding open mark

                else:
                    closed += mark

                break

    # Return ("", "") if balanced, else the extra open marks and extra close marks

    return (opened, closed)


def parse_csp_calls(source):
    """Parse an entire Call Tree of Csp"""

    shards = split_csp(source)

    # Pad the end of source with empty marks

    leading_shards = list(_ for _ in shards if _.key != "blanks")

    lookahead = 5
    empty_shard = CspShard("mark", value="")
    trailing_shards = lookahead * [empty_shard]

    shards = leading_shards + trailing_shards

    # Start up one parser

    shards_taker = ShardsTaker(lookahead)
    shards_taker.give_shards(shards)

    csp_taker = CspTaker(shards_taker)

    # Convert Csp to Call Tree

    try:

        call = csp_taker.accept_one_call()  # might be a first EmptyMark

        assert call is not None

        empty_mark = csp_taker.accept_empty_mark()
        assert empty_mark is not None

    except CspHint:

        raise

    except Exception:

        stderr_print("cspsh: failing in 'parse_csp_calls' of :", repr(source))

        heads = shards[: -len(shards_taker.shards)]
        rejoined_heads = " ".join(_.value for _ in heads)
        rejoined_tails = " ".join(_.value for _ in shards_taker.shards)

        stderr_print("cspsh: failing after taking:", rejoined_heads)
        stderr_print("cspsh: failing before taking:", rejoined_tails)

        raise

    # Succeed

    return call  # may be falsey because empty, but is not None


def _to_item_from_groupdict_(groupdict):
    """Pick the 1 Item of Value Is Not None out of an Re FindIter GroupDict"""

    items = list(_ for _ in groupdict.items() if _[-1] is not None)
    assert len(items) == 1, groupdict

    item = items[-1]
    return item


class CspHint(Exception):  # TODO: say more here, maybe do more here too?
    pass


# TODO: move this above 'class Call'?
class CspTaker:
    """
    Walk once through source chars, as split, working as yet another Yacc
    """

    def __init__(self, taker):
        self.taker = taker

    def accept_one_call(self):

        #

        call = self.accept_empty_mark()

        call = call or self.accept_choice_tuple_or_after_proc()  # Csp:  ... → ... |

        call = call or self.accept_proc_def()  # Csp:  ... =

        call = call or self.accept_argot_name_or_def()  # Csp:  α ...
        call = call or self.accept_chosen_event_or_event()  # Csp:  <lowercase_name>
        call = call or self.accept_deffed_proc()  # Csp:  <uppercase_name>

        call = call or self.accept_pocket_proc()  # Csp:  ( ...

        if not call:  # TODO: matched empty tuples are falsey, but should they be?
            assert call is None

        if call is None:
            call = self.accept_event_tuple()  # Csp:  { ...
        if call is None:
            call = self.accept_traced_event_tuple()  # Csp:  ⟨ ...

        #

        empty_mark = self.accept_empty_mark()
        if empty_mark is None:

            if isinstance(call, DeffedProc):  # TODO: more polymorphic than "isinstance"
                deffed_proc = call
                if self.peek_is_mark("→"):
                    raise csp_hint_event_over_deffed_proc(deffed_proc)

            if isinstance(call, PocketProc):
                if self.peek_is_mark("|"):
                    taker = self.taker
                    taker.take_one_shard()
                    next_pocket_proc = self.accept_pocket_proc()
                    if next_pocket_proc:
                        raise csp_hint_choice_after_proc_over_pocket_proc(
                            next_pocket_proc
                        )
                    assert next_pocket_proc  # unreliable

        # TODO: add tests that cause 'call = None' here

        return call  # may be falsey because empty, but is not None

    def accept_after_proc(self):  # such as Csp:  choc → X
        taker = self.taker
        after_proc = AfterProc.after_proc_from(taker)
        return after_proc

    def accept_argot_name_or_def(self):  # such as Csp:  αF = {orange, lemon}
        taker = self.taker
        argot_name = ArgotName.argot_name_from(taker)
        if argot_name:
            argot_def = ArgotDef.argot_def_from(taker, argot_name)
            if argot_def:
                return argot_def
            return argot_name

    def accept_choice_tuple(self, after_proc):  # such as Csp:  choc → X | toffee → X
        taker = self.taker
        choice_tuple = ChoiceTuple.choice_tuple_from(taker, after_proc=after_proc)
        return choice_tuple

    def accept_choice_tuple_or_after_proc(self):
        taker = self.taker
        choice_tuple_or_after_proc = ChoiceTuple.choice_tuple_or_after_proc_from(taker)
        return choice_tuple_or_after_proc

    def accept_chosen_event_or_event(self):  # such as Csp 'x:A' or 'coin'
        taker = self.taker
        event = ChosenEvent.chosen_event_or_event_from(taker)
        return event

    def accept_deffed_proc(self):  # such as Csp:  X
        taker = self.taker
        deffed_proc = DeffedProc.deffed_proc_from(taker)
        return deffed_proc

    def accept_empty_mark(self):  # end of source file
        taker = self.taker
        empty_mark = EmptyMark.empty_mark_from(taker)
        return empty_mark

    def accept_event_tuple(self):  # such as Csp:  {coin, choc, toffee}
        taker = self.taker
        event_tuple = UnorderedEventTuple.unordered_event_tuple_from(taker)
        return event_tuple

    def accept_proc_def(self):  # such as Csp:  VMCT = μ X : { ... } • ( ... )
        taker = self.taker
        proc_def = ProcDef.proc_def_from(taker)
        return proc_def

    def accept_pocket_proc(self):  # such as Csp:  ( ... )
        taker = self.taker
        pocket_proc = PocketProc.pocket_proc_from(taker)
        return pocket_proc

    def accept_traced_event_tuple(self):  # such as Csp: ⟨ ... ⟩
        taker = self.taker
        traced_event_tuple = TracedEventTuple.traced_event_tuple_from(taker)

        if False:
            if traced_event_tuple is not None:
                if not traced_event_tuple:
                    pdb.set_trace()

        return traced_event_tuple

    def peek_is_mark(self, mark):
        taker = self.taker
        shard = taker.peek_one_shard()
        if shard.is_mark(mark):
            return shard


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


def csp_hint_choice_after_proc_over_event(event):
    """Reject Event Without Proc in place of After Proc of Choice"""

    hint = "no, '| {}' event is not '| {} → P' guarded process".format(
        event.name, event.name
    )

    raise CspHint(hint)


def csp_hint_choice_after_proc_over_pocket_proc(pocket_proc):
    """Reject Pocket Proc in place of After Proc of Choice"""

    menu = pocket_proc.event_menu()
    assert menu  # hmm, may be unreliable

    event = menu[0]
    hint = "no, '| ({}' process choice is not '| {}' event choice".format(
        event.name, event.name
    )

    raise CspHint(hint)


def csp_hint_choice_dupes(dupes):
    """Reject conflicting Events of Choice"""

    str_dupes = ", ".join(["..."] + dupes + ["..."])
    hint = "no, choices not distinct: {{ {} }}".format(str_dupes)

    raise CspHint(hint)


def csp_hint_event_over_deffed_proc(deffed_proc):
    """Reject Deffed Proc in place of Event"""

    proc_name = deffed_proc.name
    event_name = proc_name.lower()

    got_event = "name {!r}".format(proc_name)
    want_event = "lower case event name {!r}".format(event_name)
    hint = "no, {} is not {}".format(got_event, want_event)

    raise CspHint(hint)


def csp_hint_proc_over_event(event):
    """Reject Event in place of Deffed Proc"""

    event_name = event.name
    proc_name = event.name.upper()

    got_proc = "name {!r}".format(event_name)
    want_proc = "upper case process name {!r}".format(proc_name)
    hint = "no, {} is not {}".format(got_proc, want_proc)

    raise CspHint(hint)


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

    def __init__(self, lookahead):
        self.lookahead = int(lookahead)
        self.shards = list()  # the shards being peeked, taken, and accepted

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

        assert limit <= self.lookahead

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

    # Csp Python of Csp:  choc → X  # event guards proc

    want11 = textwrap.dedent(
        """
        AfterProc(
            before=Event("choc"),
            after=DeffedProc("X"),
        )
        """
    ).strip()

    # Csp Python of Csp:  choc → X | toffee → X  # events guard proc's

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

    # Csp Python of Csp:  coin → (choc → X | toffee → X)  # events guard proc's

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

    # Collect input lines

    chars = OUR_BOOTSTRAP
    chars += CHAPTER_1
    chars = textwrap.dedent(chars).strip()

    csp_chars = "\n".join(_.partition("#")[0] for _ in chars.splitlines())
    csp_lines = (_.strip() for _ in csp_chars.splitlines() if _.strip())
    # TODO: teach the comments and blanks to survive the parse

    # Visit each input line

    csp_laters = list()
    for csp_line in csp_lines:

        # Join input lines til all ( [ { ⟨ marks closed by ) ] } ⟩ marks

        csp_laters.append(csp_line)
        csp_joined = "\n".join(csp_laters)

        shards = split_csp(csp_joined)
        (opened, closed) = balance_csp_shards(shards)
        assert not closed, (closed, opened, csp_line)

        if opened:
            continue

        csp_laters = list()

        # Pick 0 or 1 raised Exception's out of the test source

        tail_chars = chars[chars.index(csp_line) :]
        tail_line = tail_chars.splitlines()[0]
        tail_comment = tail_line.partition("#")[-1]
        want_str_exc = None
        if tail_comment.startswith(" no, "):
            want_str_exc = tail_comment[len("#") :].strip()

        # Test a closed fragment of Csp source

        py_got = None

        try:

            csp_want = csp_joined
            csp_want = csp_want.replace("(\n", "(")  # TODO: grossly inelegant
            csp_want = csp_want.replace("\n", " ")
            csp_want = csp_want.replace("\t", " ")

            csp_evalled = eval_csp_calls(csp_joined)
            assert not want_str_exc, want_str_exc

            py_got = to_deep_py(csp_evalled)

            py_evalled = eval(py_got)

            csp_got = to_deep_csp(py_evalled)
            if csp_got != csp_want:
                stderr_print("cspsh: want Csp::  {!r}".format(csp_want))
                stderr_print("cspsh: got Csp:::  {!r}".format(csp_got))
                assert False

        except CspHint as exc:

            got_str_exc = str(exc)

            assert got_str_exc == want_str_exc, (want_str_exc, got_str_exc)

        except Exception:

            stderr_print("cspsh: failing at test of Csp:  {}".format(csp_want))
            stderr_print("cspsh: failing to raise:  {}".format(want_str_exc))
            stderr_print("cspsh: failing with Python of:  {}".format(py_got))

            raise

    # Require no input lines leftover

    assert not csp_laters


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

    x → y  # no, name 'y' is not upper case process name 'Y'
    P → Q  # no, name 'P' is not lower case event name 'p'

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

    CH5C = in5p → (  # 1.1.3 X2
        out1p → out1p → out1p → out2p → CH5C |
        out2p → out1p → out2p → CH5C)

    (x → P | y → Q)

    VMCT = μ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3

    VMC = (in2p → (large → VMC |  # 1.1.3 X4
                   small → out1p → VMC) |
           in1p → (small → VMC |
                   in1p → (large → VMC |
                           in1p → STOP)))

    VMCRED = μ X • (coin → choc → X | choc → coin → X)  # 1.1.3 X5

    VMS2 = (coin → VMCRED)  # 1.1.3 X6

    COPYBIT = μ X • (in.0 → out.0 → X |  # 1.1.3 X7
                     in.1 → out.1 → X)

    (x → P | y → Q | z → R)
    (x → P | x → Q)  # no, choices not distinct: { ..., x, x, ... }
    (x → P | y)  # no, '| y' event is not '| y → P' guarded process
    (x → P) | (y → Q)  # no, '| (y' process choice is not '| y' event choice
    (x → P | (y → Q | z → R))  # no, '| (y' process choice is not '| y' event choice

    αRUNNER = {coin, choc, toffee}
    RUNNER = (x:αRUNNER → RUNNER)  # 1.1.3 X8


    # 1.1.4 Mutual recursion, p.11

    αDD = αO = αL = {setorange, setlemon, orange, lemon}

    DD = (setorange → O | setlemon → L)  # 1.1.4 X1
    O = (orange → O | setlemon → L | setorange → O)
    L = (lemon → L | setorange → O | setlemon → L)

    CT0 = (up → CT1 | around → CT0)  # 1.1.4 X2
    CT1 = (up → CT2 | down → CT0)
    CT2 = (up → CT3 | down → CT1)

    CT0 = (around → CT0 | up → CT1)  # 1.1.4 X2  # Variation B
    CT1 = (down → CT0 | up → CT2)
    CT2 = (down → CT1 | up → CT3)


    # 1.2 Pictures


    # 1.3 Laws


    # 1.4 Implementation of processes


    # 1.5 Traces

    ⟨coin,choc,coin,choc⟩  # 1.5 X1

    ⟨coin,choc,coin⟩  # 1.5 X2

    ⟨⟩  # 1.5 X3

    ⟨⟩  # 1.5 X4.1
    ⟨in2p⟩  # 1.5 X4.2.1
    ⟨in1p⟩  # 1.5 X4.2.2
    ⟨in2p,large⟩  # 1.5 X4.3.1
    ⟨in2p,small⟩  # 1.5 X4.3.2
    ⟨in1p,in1p⟩  # 1.5 X4.3.3
    ⟨in1p,small⟩  # 1.5 X4.3.4

    ⟨in1p,in1p,in1p⟩  # 1.5 X5.1
    ⟨in1p,in1p,in1p,x⟩  # 1.5 X5.2


    # 1.6 Operations on traces

"""


#
# To do
#

# TODO:  defer type checks of Csp Source Repair Hints till after parse

# TODO:  review grammar & grammar class names vs CspBook Pdf

# TODO:  Slackji :: transliteration of Unicode Org names of the Csp Unicode symbols
# TODO:  Ascii transliteration of Csp Unicode


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
