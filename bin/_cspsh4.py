#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

workflow:
  while :; do
    cd ~/Public/pybashish/bin && \
      echo| python3 -m pdb _cspsh4.py && \
      --black _cspsh4.py && --flake8 _cspsh4.py && python3 _cspsh4.py
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
import functools
import itertools
import os
import pdb
import re
import sys
import textwrap


def b():
    pdb.set_trace()


#
# Cover Python with a layer of Lisp
#

#
# Form an Abstract Syntax Tree (AST) graph of Cells of Args and KwArgs, such as:
#
#       Add(1, Divide(dividend=2, divisor=3))  # 1 + 2/3
#


DENT = 4 * " "


class Cell:
    """Collect and order the Args or KwArgs children of a Cell of an Ast"""

    def _bonds_(self):
        """Yield each Bond to a child Cell, in order"""
        bonds = tuple()
        return bonds

    def _choose_formats_(self, style, replies):
        """Choose a format for each bond"""

        # Default to drop the head and middle and tail

        head = "" if (style.head is None) else style.head
        middle = "" if (style.middle is None) else style.middle
        tail = "" if (style.tail is None) else style.tail

        # Default same as middle for first and last

        first = middle if (style.first is None) else style.first
        last = middle if (style.last is None) else style.last

        # Choose a style for each bond

        formats = list()
        formats.append(head)

        last_index = len(replies) - 1
        for (index, bond) in enumerate(replies):
            if index == 0:
                formats.append(first)  # say a single bond is more a first, less a last
            elif index == last_index:
                formats.append(last)
            else:
                formats.append(middle)

        formats.append(tail)

        # Succeed

        assert len(formats[1:][:-1]) == len(replies)
        return formats

    def _grok_(self, func):
        """Call a Func on this Cell, to make sense of the Replies from that Func"""
        replies = self._replies_(func)
        reply = func(self, replies=replies)
        return reply

    def _replies_(self, func):
        """Call a Func on the Cell down the Bond, for each Bond in order"""

        replies = list()
        for bond in self._bonds_():
            down = bond.down

            down_reply = down
            if hasattr(down, "_grok_"):
                down_reply = down._grok_(func)

            replies.append(down_reply)

        return replies


class Bond(collections.namedtuple("Bond", "up, key, down".split(", "))):
    """Point a parent Cell down to a child Cell, & back up again"""


STYLE_FIELDS = "head, first, middle, last, tail".split(", ")


class Style(
    collections.namedtuple(
        "Style", STYLE_FIELDS, defaults=(len(STYLE_FIELDS) * (None,))
    ),
):
    """Say how to format an Abstract Syntax Tree graph (AST) as Source Code"""


class KwArgsCell(Cell):
    """Collect and order the keyed KwArgs children of this Cell"""

    def _bonds_(self):
        """Yield each Bond to a child Cell, in order"""

        up = self
        for key in self._keys_():
            down = getattr(self, key)
            bond = Bond(up, key=key, down=down)
            yield bond

    def _keys_(self):
        keys = self._fields  # from collections.namedtuple
        return keys


class ArgsCell(Cell):
    """Collect and order the indexed Args children of this Cell"""

    def _bonds_(self):
        """Yield each child Cell in order"""

        up = self
        for key in self._keys_():  # rarely more than one key
            downs_list = getattr(self, key)
            for down in downs_list:
                bond = Bond(up, key=None, down=down)
                yield bond

    def _keys_(self):
        keys = self._fields  # from collections.namedtuple
        return keys


class SourceCell(Cell):
    """Format the Graph rooted by the Cell, as Source Chars of our Lisp on Python"""

    def _as_source_(cell, func, replies, style):
        """Format this Cell as Source Chars"""

        # Pull the Replies from the whole Graph, if not chosen

        if replies is None:
            py = cell._grok_(func=func)
            return py

        # Else knit the replies together

        bonds = cell._bonds_()

        cell_type_name = type(cell).__name__
        formats = cell._choose_formats_(style, replies=replies)

        assert len(replies) == len(replies)
        assert len(formats[1:][:-1]) == len(replies)

        chars = ""
        chars += formats[0].format(cell_type_name)

        for (bond, reply, reply_format) in zip(bonds, replies, formats[1:][:-1]):
            key = bond.key
            down = bond.down

            str_reply = str(reply)
            if isinstance(down, str):
                if func == format_as_python:  # TODO: inelegant
                    str_reply = '"{}"'.format(reply)

            if key is None:
                formatted = reply_format.format(str_reply)
            elif reply_format.count("{}") < 2:
                formatted = reply_format.format(str_reply)
            else:
                formatted = reply_format.format(key, str_reply)

            # Indent each Item or Value

            dented = formatted
            if "\n" in formatted:
                dented = "\n\t".join(formatted.splitlines()) + "\n"

            chars += dented

        chars += formats[-1].format()

        spaced_chars = chars.expandtabs(tabsize=len(DENT))
        return spaced_chars


#
# Cover Lisp on Python with a second Layer of Python
#


class PythonCell(SourceCell):
    """Like a SourceCell, but specifically for Python"""

    def _as_python_(self, replies=None):
        """Format this Cell as Py Source Chars"""
        func = format_as_python
        py = self._as_source_(func, replies=replies, style=self._py_style_)
        return py


def format_as_python(cell, replies=None):
    """Format a Cell as Python Source Chars"""
    py = cell._as_python_(replies)
    return py


class InlinePythonCell(PythonCell, KwArgsCell):
    """Format this Cell as a fragment of a single Python Sourceline"""

    _py_style_ = Style(head="{}(", first="{}", middle=", {}", tail=")")


class KwArgsPythonCell(PythonCell, KwArgsCell):
    """Spill the KwArgs of a this Cell across some Python Sourcelines"""

    _py_style_ = Style(head="{}(\n", middle="\t{}={},\n", tail=")")


class ArgsPythonCell(PythonCell, ArgsCell):
    """Spill the Args of this Cell across some Python Sourcelines"""

    _py_style_ = Style(head="{}(\n", middle="\t{},\n", tail=")")


#
# Cover Lisp on Python with a Layer of Csp
#


class CspCell(SourceCell):
    """Like a SourceCell, but specifically for Csp"""

    def _as_csp_(self, replies=None):
        """Format this Cell as Csp Source Chars"""
        func = format_as_csp
        csp = self._as_source_(func, replies=replies, style=self._csp_style_)
        return csp

    def _compile_csp_cell_(self):
        """Complete a compile-time evaluation of this Csp Cell"""
        _ = self._replies_(func=compile_csp_cell)


def format_as_csp(cell, replies=None):
    """Format a Cell as Csp Source Chars"""
    py = cell._as_csp_(replies)
    return py


def compile_csp_cell(down, replies=None):
    """Complete a compile-time evaluation of a Csp Cell"""

    _ = replies

    if hasattr(down, "_compile_csp_cell_"):
        reply = down._compile_csp_cell_()
        return reply

    assert isinstance(down, str)


class InlineCspCell(CspCell, InlinePythonCell):
    """Format a Cell of KwArgs as Csp Source, and its Python inline"""


class KwArgsCspCell(CspCell, KwArgsPythonCell):
    """Format a Cell of KwArgs as Csp Source, and spill its Python over Sourcelines"""


class ArgsCspCell(CspCell, ArgsPythonCell):
    """Format a Cell of Args as Csp Source, and spill its Python over Sourcelines"""


#
# Voluminous legacy, soon abandoned
#


class AfterProc(
    KwArgsCspCell,
    collections.namedtuple("AfterProc", "before after".split()),
):
    """Run a Proc after an Event"""

    _csp_style_ = Style(first="{}", middle=" → {}")

    def _compile_csp_cell_(self):

        (before, after) = (self.before, self.after)

        if isinstance(after, EmptyMark):
            assert isinstance(before, OrderedEventTuple)
            ordered_event_tuple = before
            raise csp_hint_proc_over_event(ordered_event_tuple.events[-1])

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
                if chosen_event_or_event:
                    before = chosen_event_or_event

        if not before:
            return

        # Take one "→" "\u2192" Rightwards Arrow Mark

        shard = taker.peek_one_shard()

        if not shard.is_mark("→"):

            assert ordered_event_tuple  # TODO: inelegant
            after = EmptyMark()

        else:

            assert shard.is_mark("→")  # TODO:  Mark.take_one_from_(taker)
            taker.take_one_shard()

            # Take one Pocket Proc or Deffed Proc

            after = PocketProc.pocket_proc_from(taker)
            if not after:
                after = DeffedProc.deffed_proc_from(taker)

        assert after is not None

        # Succeed

        after_proc = AfterProc(before, after=after)
        return after_proc


class ArgotDef(
    KwArgsCspCell,
    collections.namedtuple("ArgotDef", "before after".split()),
):
    """Detail an Alphabet of Events after listing Names for the Alphabet"""

    _csp_style_ = Style(first="{}", middle=" = {}")

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


class ArgotName(
    KwArgsCspCell,
    collections.namedtuple("ArgotName", "deffed_proc".split()),
):
    """Pick an Alphabet of Events out of a Deffed Proc"""

    _csp_style_ = Style(first="α{}")

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


class ChoiceTuple(  # FIXME: TODO: don't name these classes 'class ~Tuple:'
    ArgsCspCell,
    collections.namedtuple("ChoiceTuple", "choices".split()),
):
    """Choose 1 of N Proc's"""

    _csp_style_ = Style(first="{}", middle=" | {}")

    def __new__(cls, *args):  # pull these 'def __new__' from ArgsCspCell somehow?
        return super().__new__(cls, args)

    def _compile_csp_cell_(self):

        # Visit each Choice

        for choice in self.choices:

            # Reject Event in place of Proc

            if isinstance(choice, Event):
                event = choice
                raise csp_hint_choice_after_proc_over_event(event)

            # Reject PocketProc in place of After Proc

            if isinstance(choice, PocketProc):
                pocket_proc = choice
                raise csp_hint_choice_after_proc_over_pocket_proc(pocket_proc)

        # Reject conflicting choices

        menu = self.event_menu()
        names = sorted(_.name for _ in menu.events)

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

    def event_menu(self):

        menu = OrderedEventTuple()
        for choice in self.choices:

            choice_menu = choice.event_menu()

            # menu += OrderedEventTuple(choice_menu)  # TODO: does this work?
            if not menu.events:
                menu = choice_menu
            else:
                menu = OrderedEventTuple(
                    *(tuple(menu.events) + tuple(choice_menu.events))
                )

        return menu

    @staticmethod
    def choice_tuple_from(taker, after_proc):

        choices = list()
        choices.append(after_proc)

        #

        while True:

            shard = taker.peek_one_shard()
            if not shard.is_mark("|"):
                break
            taker.take_one_shard()

            next_after_proc = AfterProc.after_proc_from(taker)

            next_choice = next_after_proc
            if not next_after_proc:
                event = Event.event_from(taker)
                next_choice = event
                if not event:
                    pocket_proc = PocketProc.pocket_proc_from(taker)
                    next_choice = pocket_proc
                    assert pocket_proc

            assert next_choice
            choices.append(next_choice)

        if not choices[1:]:
            return

        #

        choice_tuple = ChoiceTuple(*choices)
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
    KwArgsCspCell,
    collections.namedtuple("ChosenEvent", "event_name argot_name".split()),
):
    """Define a Name for an Event chosen from the Argot of a Proc"""

    _csp_style_ = Style(first="{}", last=":{}")

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


class DeffedProc(
    InlineCspCell,
    collections.namedtuple("DeffedProc", "name".split()),
):
    """Mention a Proc by Name"""

    _csp_style_ = Style(first="{}", middle=" → {}")

    @staticmethod
    def deffed_proc_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_proc_name():
            taker.take_one_shard()

            deffed_proc = DeffedProc(shard.value)
            return deffed_proc


class Event(
    InlineCspCell,
    collections.namedtuple("Event", "name".split()),
):
    """Name a thing that happens"""

    _csp_style_ = Style(middle="{}")

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


class EmptyMark(
    InlineCspCell,
    collections.namedtuple("EmptyMark", "".split()),
):
    """Name the empty string that ends, or is all of, the Csp source"""

    @staticmethod
    def empty_mark_from(taker):

        shard = taker.peek_one_shard()
        if shard.is_mark(""):
            # taker.take_one_shard()  # nope, don't

            empty_mark = EmptyMark()
            assert not empty_mark

            return empty_mark


class EventsProc(
    KwArgsCspCell,
    collections.namedtuple("EventsProc", "name alphabet body".split()),
):
    """Give a Name to a PocketProc choosing Events from an Alphabet"""

    _csp_style_ = Style(first="μ {}", middle=" : {}", last=" • {}")

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
    KwArgsCspCell,
    collections.namedtuple("LazyEventsProc", "name body".split()),
):
    """Give a Name to a PocketProc choosing Events without declaring its Alphabet"""

    _csp_style_ = Style(first="μ {}", last=" • {}")


class OrderedArgotNameTuple(
    ArgsCspCell,
    collections.namedtuple("OrderedArgotNameTuple", "argot_names".split()),
):
    """Order two or more Argot Names"""

    _csp_style_ = Style(first="{}", middle=" = {}")

    def __new__(cls, *args):
        return super().__new__(cls, args)


class OrderedEventTuple(
    ArgsCspCell,
    collections.namedtuple("OrderedEventTuple", "events".split()),
):
    """Order two or more Events"""

    _csp_style_ = Style(first="{}", middle=" → {}")

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def event_menu(self):

        if not self.events:
            return OrderedEventTuple()

        menu = self.events[0].event_menu()
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


class ProcDef(
    KwArgsCspCell,
    collections.namedtuple("ProcDef", "name body".split()),
):
    """Give a Name to a Pocket Proc or an Event Proc"""

    _csp_style_ = Style(first="{}", middle=" = {}")

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


class PocketProc(
    collections.namedtuple("PocketProc", "pocketed".split()), KwArgsCspCell
):
    """Contain one AfterProc or a Choice between AfterProc's"""

    _csp_style_ = Style(head="(", middle="{}", tail=")")

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


class TracedEventTuple(
    ArgsCspCell,
    collections.namedtuple("TracedEventTuple", "events".split()),
):  # TODO: combine with OrderedEventTuple
    """Order two or more Events"""

    _csp_style_ = Style(head="⟨", first="{}", middle=",{}", tail="⟩")  # "⟨⟩", not "()"

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


class UnorderedEventTuple(
    ArgsCspCell,
    collections.namedtuple("UnorderedEventTuple", "events".split()),
):
    """Collect zero or more Events together"""

    _csp_style_ = Style(head="{{", first="{}", middle=", {}", tail="}}")

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
# Split Csp Source into blank and nonblank, balanced and unbalanced, Shards
#


NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[(),:={|}αμ•→⟨⟩])"
COMMENT_REGEX = r"(?P<comment>#[^\n]+)"
BLANKS_REGEX = r"(?P<blanks>[ \t\n]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, COMMENT_REGEX, BLANKS_REGEX])

OPENING_MARKS = "([{⟨"
CLOSING_MARKS = ")]}⟩"


def split_csp(source):
    """Split Csp Source into blank and nonblank, balanced and unbalanced, Shards"""

    # Drop the "\r" out of each "\r\n"

    chars = "\n".join(source.splitlines()) + "\n"

    # Split the source into names, marks, comments, and blanks

    matches = re.finditer(SHARDS_REGEX, string=chars)
    items = list(_to_item_from_groupdict_(_.groupdict()) for _ in matches)
    shards = list(CspShard(*_) for _ in items)

    # Require no chars dropped

    rejoined = "".join(_.value for _ in shards)  # a la ._split_misfit_
    assert rejoined == chars  # TODO: cope more gracefully with new chars

    # Succeed

    return shards


def _to_item_from_groupdict_(groupdict):
    """Pick the 1 Item of Value Is Not None out of an Re FindIter GroupDict"""

    items = list(_ for _ in groupdict.items() if _[-1] is not None)
    assert len(items) == 1, groupdict

    item = items[-1]
    return item


def balance_csp_shards(shards):
    """Open up paired marks, close them down, & say what's missing or extra"""

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


#
# Join Shards of Csp Source into an Abstract Syntax Tree graph
#


def parser(func):
    pass


def _traceable_(func):
    """Call '_enter_' before, and call '_exit_' after"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self._enter_(func, *args, **kwargs)
        result = func(self, *args, **kwargs)
        self._exit_(func, result=result)
        return result

    return wrapper


class CellJoiner:
    """Join Shards of Source into an Abstract Syntax Tree graph"""

    def __init__(self, taker):
        self.taker = taker

        self.calls = list()
        self.givebacks = list()
        self.snapshots = list()

        self.top_call = None

    def _enter_(self, func, *args, **kwargs):
        """Snapshot at entry, before trying to match"""

        _ = args
        _ = kwargs

        taker = self.taker

        calls = self.calls
        givebacks = self.givebacks
        snapshots = self.snapshots

        call = list()
        call.append(func)
        calls.append(call)

        giveback = taker._snapshot_()
        givebacks.append(giveback)

        snapshot = None
        snapshots.append(snapshot)

    def _checkpoint_(self):
        """Snapshot while matching, before rolling back"""

        taker = self.taker
        snapshots = self.snapshots

        snapshots[-1] = taker._snapshot_()

    def _rollback_(self):
        """Rollback to last snapshot"""

        taker = self.taker
        snapshots = self.snapshots

        snapshot = snapshots[-1]
        taker._restore_(snapshot)

        snapshots[-1] = None

    def _exit_(self, func, result):
        """Succeed & add self as next arg of call, else restore entry & fail"""

        taker = self.taker

        calls = self.calls
        givebacks = self.givebacks
        snapshots = self.snapshots

        call = calls.pop()
        giveback = givebacks.pop()
        snapshot = snapshots.pop()

        assert snapshot is None  # else lacking some:  self._rollback_()

        if not result:

            taker._restore_(giveback)  # Restore entry & fail

        else:

            if calls:  # Serve as Arg of Caller
                calls[-1].append(call)
            else:  # Else serve as Top Call
                self.top_call = call


class CspCellJoiner(CellJoiner):
    """Join Shards of Csp Source into an Abstract Syntax Tree graph"""

    @_traceable_
    def _eof_(self):
        """Match end-of-source & return True, else don't"""

        taker = self.taker
        shard = taker.peek_one_shard()
        if shard.is_mark(""):
            return True

    @_traceable_
    def _name_(self):
        """Take a Name & return True, else don't"""

        taker = self.taker
        shard = taker.peek_one_shard()
        if shard.is_name():
            taker.take_one_shard()
            return True

    @_traceable_
    def _lowered_(self):
        """Return True if at a Name or Mark that can go upper and is lower"""
        taker = self.taker
        shard = taker.peek_one_shard()
        value = shard.value
        islower = (value != value.upper()) and (value == value.lower())
        return islower

    @_traceable_
    def _uppered_(self):
        """Return True if at a Name or Mark that can go lower and is upper"""
        taker = self.taker
        shard = taker.peek_one_shard()
        value = shard.value
        islower = (value != value.lower()) and (value == value.upper())
        return islower

    @_traceable_
    def _mark_(self, chars):
        """Take a Mark equal to the Chars & return True, else don't"""

        taker = self.taker
        shard = taker.peek_one_shard()
        if shard.is_mark(chars):
            taker.take_one_shard()
            return True


class CspParser(CspCellJoiner):
    """Parse Shards of Csp Source per our Csp Grammar"""

    _grammar_ = """

        event = _lowered_ _name_
        event_set = '{' { event ',' } [ event ] '}'
        transcript = '⟨' { event ',' } [ event ] '⟩'

        proc = _uppered_ _name_

        argot = 'α' proc
        aliases = argot { '=' argot }
        argot_def = aliases '=' event_set
        argot_event =  event ':' argot

        step = argot_event | event
        prolog = step { '→' step }
        epilog = proc | pocket
        prong = prolog '→' epilog
        fork = prong { '|' prong }

        proc_def = proc '=' body
        body = proc | focused | blurred | fork | pocket
        focused = 'μ' proc ':' event_set '•' pocket
        blurred = 'μ' proc '•' pocket

        pocketable = fork | body
        pocket = '(' pocketable ')'

        frag = transcript | event_set | proc_def | argot_def | pocketable
        csp = frag _eof_

    """  # our grammar in a Backus-Naur Form (BNF)

    @_traceable_
    def event(self):
        """event = _lowered_ _name_"""
        return self._lowered_() and self._name_()

    @_traceable_
    def event_set(self):
        """event_set = '{' { event ',' } [ event ] '}'"""
        if self._mark_("{"):
            self._checkpoint_()
            while self.event() and self._mark_(","):
                self._checkpoint_()
            self._rollback_()
            self.event()
            return self._mark_("}")

    @_traceable_
    def transcript(self):
        """transcript = '⟨' { event ',' } [ event ] '⟩'"""
        if self._mark_("⟨"):
            self._checkpoint_()
            while self.event() and self._mark_(","):
                self._checkpoint_()
            self._rollback_()
            self.event()
            return self._mark_("⟩")

    #

    @_traceable_
    def proc(self):
        """proc = _uppered_ _name_"""
        return self._uppered_() and self._name_()

    #

    @_traceable_
    def argot(self):
        """argot = 'α' proc"""
        return self._mark_("α") and self.proc()

    @_traceable_
    def aliases(self):
        """aliases = argot { '=' argot }"""
        if self.argot():
            self._checkpoint_()
            while self._mark_("=") and self.argot():
                self._checkpoint_()
            self._rollback_()
            return True

    @_traceable_
    def argot_def(self):
        """argot_def = aliases '=' event_set"""
        return self.aliases() and self._mark_("=") and self.event_set()

    @_traceable_
    def argot_event(self):
        """argot_event =  event ':' argot"""
        return self.event() and self._mark_(":") and self.argot()

    #

    @_traceable_
    def step(self):
        """step = argot_event | event"""
        return self.argot_event() or self.event()

    @_traceable_
    def prolog(self):
        """prolog = step { '→' step }"""
        if self.step():
            self._checkpoint_()
            while self._mark_("→") and self.step():
                self._checkpoint_()
            self._rollback_()
            return True

    @_traceable_
    def epilog(self):
        """epilog = proc | pocket"""
        return self.proc() or self.pocket()

    @_traceable_
    def prong(self):
        """prong = prolog '→' epilog"""
        return self.prolog() and self._mark_("→") and self.epilog()

    @_traceable_
    def fork(self):
        """fork = prong { '|' prong }"""

        if self.prong():

            self._checkpoint_()
            while self._mark_("|") and self.prong():
                self._checkpoint_()
            self._rollback_()

            self._checkpoint_()
            if self._mark_("|") and (self.prolog() or self._mark_("(")):
                self._rollback_()
                self._checkpoint_()

                taker = self.taker
                (fit, misfit) = taker._split_misfit_()
                stderr_print("inside {!r}".format(fit + misfit))

                stderr_print("need '| x → P', got '{}'".format(misfit))

            self._rollback_()

            return True

        if self.prolog() and not self._mark_("→"):

            taker = self.taker
            (fit, misfit) = taker._split_misfit_()
            stderr_print("inside {!r}".format(fit + misfit))

            stderr_print("need '→ P', got '{}'".format(misfit))

    #

    @_traceable_
    def proc_def(self):
        """proc_def = proc '=' body"""
        return self.proc() and self._mark_("=") and self.body()

    @_traceable_
    def body(self):
        """body = proc | focused | blurred | fork | pocket"""
        return (
            self.proc()
            or self.focused()
            or self.blurred()
            or self.fork()
            or self.pocket()
        )

    @_traceable_
    def focused(self):
        """focused = 'μ' proc ':' event_set '•' pocket"""
        return (
            self._mark_("μ")
            and self.proc()
            and self._mark_(":")
            and self.event_set()
            and self._mark_("•")
            and self.pocket()
        )

    @_traceable_
    def blurred(self):
        """blurred = 'μ' proc '•' pocket"""
        return self._mark_("μ") and self.proc() and self._mark_("•") and self.pocket()

    #

    @_traceable_
    def pocketable(self):
        """pocketable = fork | body"""
        return self.fork() or self.body()

    @_traceable_
    def pocket(self):
        """pocket = '(' pocketable ')'"""
        return self._mark_("(") and self.pocketable() and self._mark_(")")

    @_traceable_
    def frag(self):
        """frag = transcript | event_set | proc_def | argot_def | pocketable"""
        return (
            self.transcript()
            or self.event_set()
            or self.proc_def()
            or self.argot_def()
            or self.pocketable()
        )

    @_traceable_
    def csp(self):
        """csp = frag _eof_"""

        if self.frag():
            if self._eof_():
                return True

            taker = self.taker
            (fit, misfit) = taker._split_misfit_()
            stderr_print("inside {!r}".format(fit + misfit))

            #

            self._checkpoint_()
            need_prolog = self._mark_("→") and self.epilog()
            self._rollback_()

            if need_prolog:

                stderr_print("need 'x →' got {!r}".format(fit.rstrip() + " →"))

                return

            #

            self._checkpoint_()
            need_fork = self._mark_("|") and self.frag()
            self._rollback_()

            if need_fork:
                stderr_print("need 'x → P| y → Q' got {!r}".format(fit + misfit))


#
# Split and parse and compile Csp Source
#


class CspHint(Exception):
    """Suggest how to repair some Csp Source so it lexxes, parses, and compiles"""


def eval_csp_cell(source):
    """Split and structure Cells corresponding to Source Chars of Csp"""

    shards = split_csp(source)

    (opened, closed) = balance_csp_shards(shards)
    assert not closed, (closed, opened, source)
    assert not opened, (closed, opened, source)

    cell = parse_csp_cell(source)  # TODO: stop repeating the work of "split_csp"

    compile_csp_cell(cell)

    return cell


def parse_csp_cell(source):
    """Parse the Source to form a Graph rooted by one Cell, & return that root Cell"""

    shards = split_csp(source)

    # Pad the end of Source with empty Marks

    leading_shards = list(_ for _ in shards if _.key != "blanks")

    lookahead = 5
    empty_shard = CspShard("mark", value="")
    trailing_shards = lookahead * [empty_shard]

    shards = leading_shards + trailing_shards

    # Start up one Parser

    shard_taker = CspShardTaker(shards, lookahead=lookahead)
    csp_taker = LegacyCspTaker(shard_taker)

    # TODO: keep this, cut legacy
    taker2 = CspShardTaker(shards, lookahead=lookahead)
    parser2 = CspParser(taker2)
    ok = parser2.csp()
    if not ok:
        stderr_print("not grammar parsing")  # : ", source)
        stderr_print("")

    # Convert Csp to Call Graph

    try:

        # b()
        cell = csp_taker.accept_one_cell()  # might be a first EmptyMark

        assert cell is not None

        empty_mark = csp_taker.accept_empty_mark()
        assert empty_mark is not None

    except CspHint:

        raise

    except Exception:

        stderr_print("cspsh: failing in 'parse_csp_cell' of :", repr(source))

        heads = shards[: -len(shard_taker.tails)]
        rejoined_heads = " ".join(_.value for _ in heads)
        rejoined_tails = " ".join(_.value for _ in shard_taker.tails)

        stderr_print("cspsh: failing after taking:", rejoined_heads)
        stderr_print("cspsh: failing before taking:", rejoined_tails)

        raise

    # Succeed

    return cell


#
#
#


class LegacyCspTaker:
    """Walk once through source chars, as split, working as yet another Yacc"""

    def __init__(self, taker):
        self.taker = taker

    def accept_one_cell(self):

        cell = self.accept_empty_mark()

        cell = cell or self.accept_choice_tuple_or_after_proc()  # Csp:  ... → ... |

        cell = cell or self.accept_proc_def()  # Csp:  ... =

        cell = cell or self.accept_argot_name_or_def()  # Csp:  α ...
        cell = cell or self.accept_chosen_event_or_event()  # Csp:  x  # Csp:  x:αP
        cell = cell or self.accept_deffed_proc()  # Csp:  P

        cell = cell or self.accept_pocket_proc()  # Csp:  ( ...

        if not cell:  # TODO: matched empty tuples are falsey, but should they be?
            assert cell is None

        if cell is None:
            cell = self.accept_event_tuple()  # Csp:  { ...
        if cell is None:
            cell = self.accept_traced_event_tuple()  # Csp:  ⟨ ...

        #

        empty_mark = self.accept_empty_mark()
        if empty_mark is None:

            if isinstance(cell, DeffedProc):  # TODO: more polymorphic than "isinstance"
                deffed_proc = cell
                if self.peek_is_mark("→"):
                    raise csp_hint_event_over_deffed_proc(deffed_proc)

            if isinstance(cell, PocketProc):
                if self.peek_is_mark("|"):
                    taker = self.taker
                    taker.take_one_shard()
                    next_pocket_proc = self.accept_pocket_proc()
                    if next_pocket_proc:
                        raise csp_hint_choice_after_proc_over_pocket_proc(
                            next_pocket_proc
                        )
                    assert next_pocket_proc  # unreliable

        # TODO: add tests that cause 'cell = None' here

        return cell

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
    """Carry a fragment of Csp Source Code"""

    def is_event_name(self):  # TODO: delete legacy
        if self.key == "name":
            if self.value == self.value.lower():
                return True

    def is_proc_name(self):  # TODO: delete legacy
        if self.key == "name":
            if self.value == self.value.upper():
                return True

    def is_name(self):
        if self.key == "name":
            return True

    def is_mark(self, mark):
        if self.key == "mark":
            if self.value == mark:
                return True


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

    event = menu.events[0]
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
# Run from the command line
#


def main(argv):
    """Run from the command line"""

    stderr_print("")
    stderr_print("")
    stderr_print("cspsh: hello")
    stderr_print("")

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
class ShardTaker(argparse.Namespace):
    """
    Walk once through Source Chars, as split, working as yet another Lexxer

    Define "take" to mean require and consume
    Define "peek" to mean look ahead into the shards followed by infinitely many None's
    Define "accept" to mean take if present, else quietly don't bother

    Work well with Source Chars
    as split by 'match.groupdict().items()' of 'import re',
    per reg-ex'es of r"(?P<...>...)+"
    """

    # TODO: delete the methods we're not testing here

    def __init__(self, shards, lookahead):
        self.lookahead = int(lookahead)
        self.heads = list(shards)
        self.tails = list(shards)

    def _snapshot_(self):
        """Take a snapshot of shards remaining"""
        snapshot = list(self.tails)
        return snapshot

    def _restore_(self, snapshot):
        """Restore a snapshot of shards remaining"""
        self.tails = snapshot

    def take_one_shard(self):
        """Take one shard, and drop it, don't return it"""

        self.tails = self.tails[1:]

    def take_some_shards(self, count):
        """Take the next few shards, and drop them, don't return them"""

        self.tails = self.tails[count:]

    def peek_one_shard(self):
        """Return the next shard, but without consuming it"""

        if self.tails:  # infinitely many None's past the last shard

            return self.tails[0]

    def peek_some_shards(self, count):
        """Return the next few shards, without consuming them"""

        nones = count * [None]
        some = (self.tails[:count] + nones)[:count]

        return some

    def peek_equal_shards(self, hopes):
        """Return the next few shards, but only if they equal our hopes"""

        some = self.peek_some_shards(len(hopes))
        if some == list(hopes):

            return True

    def take_beyond_shards(self):
        """Do nothing if all shards consumed, else raise mystic IndexError"""

        count = len(self.tails)
        if count:

            assert not self.tails, self.tails  # TODO: assert else raise
            raise IndexError("{} remaining shards".format(count))

    def peek_more(self):
        """Return True if more shards remain"""

        more = bool(self.tails)  # see also:  self.peek_more_shards

        return more

    def peek_more_shards(self, limit):
        """List zero or more remaining shards"""

        assert limit <= self.lookahead

        more_shards = list(self.tails)  # see also:  self.peek_more
        more_shards = more_shards[:limit]

        return more_shards


# TODO: Shuffle this up after substituting Composition for Inheritance
class CspShardTaker(ShardTaker):
    """
    Walk once through Source Chars, as split into CspShard's, working as a Lexxer
    """

    def _split_misfit_(self):
        """Split a format of the source taken from a format of what remains"""

        before = " ".join(_.value for _ in self.heads[: -len(self.tails)])
        after = " ".join(_.value for _ in self.tails).rstrip()

        fit = (before + " ") if after else before
        misfit = after

        # TODO: mmm ugly drop of lookahead padding

        return (fit, misfit)


#
# Self test
#


def bootstrap_py_csp_fragments():
    """Put a few fragments of Py Source, and their Csp Source, under test"""

    # Csp Python of Csp:  coin  # an event exists

    want0 = textwrap.dedent(
        """
        DeffedProc("X")
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
        X
        {coin, choc, toffee}
        choc → X
        choc → X | toffee → X
        coin → (choc → X | toffee → X)
        VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))
        """
    ).strip()

    assert textwrap.dedent(OUR_BOOTSTRAP).strip() == CSP_WANTS

    # Return the fragments chosen

    py_wants = (want0, want1, want11, want20, want2, want3)
    csp_wants = CSP_WANTS.splitlines()
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

        py_got = py_evalled._as_python_()

        assert not stderr_print_diff(input=py_want, output=py_got)

        # test print as Csp

        csp_got = format_as_csp(py_evalled)
        if csp_got != csp_want:
            stderr_print("cspsh: want Csp::  {!r}".format(csp_want))
            stderr_print("cspsh: got Csp:::  {!r}".format(csp_got))
            assert False

        # test parse as Csp

        csp_evalled = eval_csp_cell(csp_want)

        if csp_evalled != py_evalled:
            stderr_print("cspsh: csp_evalled", csp_evalled)
            stderr_print("cspsh: py_evalled", py_evalled)

        assert csp_evalled == py_evalled, argparse.Namespace(
            want_py=py_want,
            got_py=format_as_python(csp_evalled),
        )


def try_csp_then_py():
    """Translate from Csp Source to Calls to Py Source, to Py Calls, to Csp Source"""

    # Collect input lines

    chars = OUR_BOOTSTRAP
    chars += CHAPTER_1
    chars = textwrap.dedent(chars).strip()

    if False:
        chars = "x → y"

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

            csp_evalled = eval_csp_cell(csp_joined)
            assert not want_str_exc, (want_str_exc, None)

            py_got = format_as_python(csp_evalled)

            alt_py_got = csp_evalled._as_python_()
            assert py_got == alt_py_got, (print(py_got), print(alt_py_got))

            py_evalled = eval(py_got)

            csp_got = format_as_csp(py_evalled)
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

        if False:
            if "x:αP" in csp_joined:
                pdb.set_trace()
                pass

    # Require no input lines leftover

    assert not csp_laters


OUR_BOOTSTRAP = """

    X
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
    # (x → P) | y → Q  # no
    (x → P | (y → Q | z → R))  # no, '| (y' process choice is not '| y' event choice

    x:αP → STOP
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

# TODO:  emit a graph from the Bnf parser
# TODO:  format the Bnf graph as Csp
# TODO:  format the Bnf graph as Python
# TODO:  pull Csp repair hints from the Bnf parser
# TODO:  delete the legacy parser

# TODO:  exit into interactive Repl
# TODO:  review grammar & grammar class names vs CspBook Pdf
# TODO:  code more methods, less branches on 'if isinstance('

# TODO:  Slackji :: transliteration of Unicode Org names of the Csp Unicode symbols
# TODO:  Ascii transliteration of Csp Unicode


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
