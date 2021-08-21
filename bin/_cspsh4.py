#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

optional arguments:
  -h, --help  show this help message and exit

workflow:
  while :; do
    echo ... paused ...
    read
    date; time (
      cd ~/Public/pybashish/bin && \
        echo| python3 -m pdb _cspsh4.py && \
        --black _cspsh4.py && --flake8 _cspsh4.py && python3 _cspsh4.py
    )
  done

examples:
  _cspsh4.py
"""

# code reviewed by people, and by Black and Flake8 bots
# table of contents in Vim at :/g^#


import __main__
import argparse
import collections
import difflib
import os
import pdb
import re
import sys
import textwrap


def b():
    pdb.set_trace()


#
# Main:  Run from the command line
#


def main(argv):
    """Run from the command line"""

    stderr_print("")
    stderr_print("")
    stderr_print("cspsh: hello")
    stderr_print("")

    parser = compile_argdoc(epi="workflow:")
    _ = parser.parse_args(argv[1:])

    try_test_self_some()

    stderr_print("cspsh: + exit 0")


#
# Eval:  Split and parse and compile Csp Source
#


def eval_csp(csp):
    """Split and structure Cells corresponding to Source Chars of Csp"""

    shards = split_csp(csp)

    (opened, closed) = balance_csp_shards(shards)
    assert not closed, (closed, opened, csp)
    assert not opened, (closed, opened, csp)

    cell = parse_csp(csp)  # TODO: stop rerunning 'split_csp' inside 'parse_csp'

    compile_csp_cell(cell)

    return cell


#
# Split:  Split Csp Source into blank and nonblank, balanced and unbalanced, Shards
#
# aka Scanner, Tokenizer, Lexxer
#


NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Z\\a-z_]*)"
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
    assert rejoined == chars  # TODO: welcome new chars not yet found in MARK_REGEX

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


class CspShard(collections.namedtuple("CspShard", "key value".split())):
    """Carry a fragment of Csp Source Code"""

    def is_mark(self, chars):
        if self.key == "mark":
            if self.value == chars:
                return True

    def peek_event_name(self):
        """Return the Chars of the Name if it lexxes as a Csp Proc Name"""
        if self.key == "name":
            name = self.value

            if name.upper() != name:  # could be upper
                if name == name.lower():  # is lower
                    return name

    def peek_proc_name(self):
        """Return the Chars of the Name if it lexxes as a Csp Event Name"""
        if self.key == "name":
            name = self.value

            if name.lower() != name:  # could be lower
                if name == name.upper():  # is upper
                    return name


#
# Parse:  Form an Abstract Syntax Tree (AST) Graph of Cells of Args and KwArgs
#
#   Such as:
#
#       Add(1, Divide(dividend=2, divisor=3))  # 1 + 2/3
#


def parse_csp(csp):
    """Parse the Source to form a Graph rooted by one Cell, & return that root Cell"""

    shards = split_csp(csp)
    tails = list(_ for _ in shards if _.key != "blanks")
    bot = ParserBot(tails)

    try:

        cell = bot.accept_one(Frag)

        if not cell:
            raise csp_bot_hint_csp_none(bot)
        if not bot.at_mark(""):
            raise csp_bot_hint_csp_more(bot, cell=cell)

    except Exception as exc:

        if False:
            # TODO: go invent more accurate strong Source Repair Hints
            # TODO: more logging for unexpected parser failure

            (fit, misfit) = bot._split_misfit_()
            alt_source = fit + misfit

            stderr_print("cspsh: exc: {}({!r})".format(type(exc).__name__, exc))
            stderr_print("cspsh: in:", alt_source)
            stderr_print("cspsh: fit:", fit)
            stderr_print("cspsh: misfit:", misfit)
            stderr_print("")

        raise

    # Succeed

    return cell


#
# Lisp Cells:  Cover Python with a layer of Lisp Cells of Cells
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
            if isinstance(down, str):  # TODO: 'isinstance' should be method
                if func == format_as_py:  # TODO: inelegant to override str for func
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


STYLE_FIELDS = "head, first, middle, last, tail".split(", ")


class Style(
    collections.namedtuple(
        "Style", STYLE_FIELDS, defaults=(len(STYLE_FIELDS) * (None,))
    ),
):
    """Say how to format an Abstract Syntax Tree Graph (AST) as Source Code"""


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


#
# Python Cells:  Cover Lisp on Python with a layer of Python Cells of Cells
#


class PythonCell(SourceCell):
    """Like a SourceCell, but specifically for Python"""

    def _as_python_(self, replies=None):
        """Format this Cell as Py Source Chars"""
        func = format_as_py
        py = self._as_source_(func, replies=replies, style=self._py_style_)
        return py


def format_as_py(cell, replies=None):
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
# Csp Cells:  Cover Lisp on Python with a layer of Csp Cells of Cells
#


class CspCell(SourceCell):
    """Like a SourceCell, but specifically for Csp"""

    _csp_style_ = Style(middle="{}")

    def __str__(self):
        csp = self._as_csp_()
        return csp

    def _as_csp_(self, replies=None):
        """Format this Cell as Csp Source Chars"""
        func = format_as_csp
        csp = self._as_source_(func, replies=replies, style=self._csp_style_)
        return csp

    def _compile_(self):
        """Complete a compile-time evaluation of this Csp Cell"""
        _ = self._replies_(func=compile_csp_cell)


def format_as_csp(cell, replies=None):
    """Format a Cell as Csp Source Chars"""
    py = cell._as_csp_(replies)
    return py


def compile_csp_cell(down, replies=None):
    """Complete a compile-time evaluation of a Csp Cell"""

    _ = replies

    if hasattr(down, "_compile_"):
        reply = down._compile_()
        return reply

    assert isinstance(down, str)  # TODO: 'isinstance' should be method


class InlineCspCell(CspCell, InlinePythonCell):
    """Format a Cell of KwArgs as Csp Source, and its Python inline"""


class KwArgsCspCell(CspCell, KwArgsPythonCell):
    """Format a Cell of KwArgs as Csp Source, and spill its Python over Sourcelines"""


class ArgsCspCell(CspCell, ArgsPythonCell):
    """Format a Cell of Args as Csp Source, and spill its Python over Sourcelines"""

    def __new__(cls, *args):
        return super().__new__(cls, args)


#
# ParserBot:  Help knit Split Cells into an Abstract Syntax Tree Graph of Kwargs & Args
#


class SourceRepairHint(Exception):
    """Suggest how to repair Source so it more lexxes, parses, & compiles"""


class ParserBot:
    """
    Walk once through Source Chars, as split, working as yet another Yacc

    Say "take" to mean require and consume
    Say "accept" to mean take if present, else return None
    Say "peek" to mean detect and return a copy, but do Not consume
    Say "at" to mean detect, but do Not consume

    Let the caller ask to backtrack indefinitely far,
    like after each failure to complete a partial match

    Work especially well with Source Chars
    as split by 'match.groupdict().items()' of 'import re',
    per reg-ex'es of r"(?P<...>...)+"
    """

    def __init__(self, tails):
        self.tails = list(tails)
        self.heads = list(self.tails)
        self.contexts = list()

    def __enter__(self):
        """Back up the Tails not yet matched"""

        context = list(self.tails)
        self.contexts.append(context)

    def __exit__(self, *exc_info):
        """Restore the Tails that were not yet matched at last Enter/ Commit"""

        context = self.contexts.pop()
        self.tails[::] = context

    def _checkpoint_(self):
        """Say to call Self to choose which Tails to Backup and Restore"""

        return self

    def _commit_(self):
        """Say these are the Tails that were matched at last Enter/ Commit"""

        _ = self.contexts.pop()
        self.__enter__()

    def _split_misfit_(self):
        """Split a format of the source taken from a format of what remains"""

        before = " ".join(_.value for _ in self.heads[: -len(self.tails)])
        after = " ".join(_.value for _ in self.tails).rstrip()

        fit = (before + " ") if (before and after) else before
        misfit = after

        return (fit, misfit)

    def accept_between(self, cls, head, sep, end, tail):
        """between = head [ item { sep item } ] [ end ] tail"""
        # becomes 'head { item sep } [ item ] tail' when sep = end

        assert head and sep and end and tail  # nothing else yet tested
        assert sep == end  # nothing else yet tested

        items = list()
        with self._checkpoint_():

            # Require Head

            if head and not self.accept_mark(head):
                return

            # Allow one Item, or multiple items separated by Sep

            no_items = list()
            some_items = self.accept_some(cls=cls, sep=sep)  # indefinite lookahead
            items = no_items if (some_items is None) else some_items

            # Allow End

            if end:
                _ = self.accept_mark(end)

            # Require Tail

            if tail and self.accept_mark(tail):

                # Succeed with a truthy or falsey list of Items

                self._commit_()
                return items

    def accept_mark(self, chars):
        """Accept a Mark, if present"""

        tail = self.peek_one_tail()
        if tail and tail.is_mark(chars):
            self.take_one_tail()
            return True

    def accept_one(self, cls):
        """Form and take Cls if present, else return None"""

        cell = cls._accept_one_(self)
        return cell

    def accept_some(self, cls, sep):
        """some = item { sep item }"""

        items = list()

        if item := self.accept_one(cls):
            items.append(item)

        while True:
            with self._checkpoint_():
                if sep and self.accept_mark(sep):
                    if item := self.accept_one(cls):  # indefinite lookahead

                        items.append(item)
                        self._commit_()
                        continue

            break

        return items

    def alt_source(self):
        """Return the Alt Source, being a style of Source that shows the splitting"""

        (fit, misfit) = self._split_misfit_()
        alt_source = fit + misfit
        return alt_source

    def at_one(self, cls):
        """Form Cls if present, else return None, but don't take it yet"""

        with self._checkpoint_():
            cell = cls._accept_one_(self)  # indefinite lookahead
            if cell:

                self._commit_()
                return cell

    def at_mark(self, chars):
        """Return truthy if Mark present, but don't take it yet"""

        tail = self.peek_one_tail()
        if tail and tail.is_mark(chars):
            return True

        if not tail and not chars:
            return True

    def fit(self):
        """Return an Alt Source copy of the parsed head or whole of the Source"""

        (fit, _) = self._split_misfit_()
        return fit

    def form_plural(self, cls, items):
        """Return the first and only item, else flatten then wrap in plural Cls"""

        if len(items) == 1:
            return items[0]

        return cls(*items)

    def misfit(self):
        """Return an Alt Source copy of the not-parsed tail or whole of the Source"""

        (_, misfit) = self._split_misfit_()
        return misfit

    def peek_one_tail(self):
        """Return the next Tail, else None"""

        tails = self.tails

        if tails:
            tail = tails[0]
            return tail

    def suggest(self, hint):
        """Form an Exception to repair Source so it more lexxes, parses, & compiles"""

        return SourceRepairHint(hint)

    def take_one_tail(self):
        """Consume the next Tail, else raise IndexError"""

        tails = self.tails

        tails[::] = tails[1:]


#
# Csp Atoms:  Define the Atoms of the Parse as Event or Proc or Mark
#


class Event(
    InlineCspCell,
    collections.namedtuple("Event", "name".split(", ")),
):
    """Accept one Event name, if present"""

    def _menu_(self):
        menu = (self,)
        return menu

    @classmethod
    def _accept_one_(cls, bot):

        tail = bot.peek_one_tail()
        if tail:
            name = tail.peek_event_name()
            if name is not None:
                bot.take_one_tail()

                return Event(name)


class Proc(
    InlineCspCell,
    collections.namedtuple("Proc", "name".split(", ")),
):
    """Accept one Proc name, if present"""

    @classmethod
    def _accept_one_(cls, bot):

        tail = bot.peek_one_tail()
        if tail:
            name = tail.peek_proc_name()
            if name is not None:
                bot.take_one_tail()

                return Proc(name)


#
# Csp Grammar Doc:  Code up our Grammar in a Backus Naur Form (BNF) of Event/ Proc/ Mark
#
# In this BNF,
#
#       ','         is a quotation of source
#       [ ... ]     is 0 or 1
#       { ... }     is 0 or more
#


_grammar_ = """

    transcript = '⟨' { event ',' } [ event ] '⟩'
    alphabet = '{' { event ',' } [ event ] '}'

    argot = 'α' proc
    argot_names = argot { '=' argot }
    argot_def = argot_names '=' alphabet
    argot_event =  event ':' argot

    step = argot_event | event
    prolog = step { '→' step }
    epilog = proc | pocket
    prong = prolog '→' epilog
    fork = prong { '|' prong }

    proc_def = proc '=' body
    body = proc | sharp_body | fuzzy_body | fork | pocket
    sharp_body = 'μ' proc ':' alphabet '•' pocket
    fuzzy_body = 'μ' proc '•' pocket

    pocketable = fork | body
    pocket = '(' pocketable ')'

    frag = transcript | alphabet | proc_def | argot_def | pocketable
    csp = frag ''

"""


#
# Csp Grammar Code:  Code up our Grammar on top of ParserBot
#


# aggregate events #


class Transcript(
    ArgsCspCell,
    collections.namedtuple("Transcript", "events".split(", ")),
):
    """transcript = '⟨' { event ',' } [ event ] '⟩'"""

    _csp_style_ = Style(head="⟨", first="{}", middle=", {}", tail="⟩")  # "⟨⟩", not "()"

    @classmethod
    def _accept_one_(cls, bot):
        events = bot.accept_between(Event, head="⟨", sep=",", end=",", tail="⟩")
        if events is not None:
            return Transcript(*events)

    # "⟨" "\u27E8" Mathematical Left Angle Bracket
    # "⟩" "\u28E9" Mathematical Right Angle Bracket


class Alphabet(
    ArgsCspCell,
    collections.namedtuple("Alphabet", "events".split(", ")),
):
    """alphabet = '{' { event ',' } [ event ] '}'"""

    _csp_style_ = Style(head="{{", first="{}", middle=", {}", tail="}}")

    def _compile_(self):
        events = self.events

        csp_source_repair_hint = csp_bot_hint_uniq(
            "event names", items=list(_.name for _ in events)
        )
        if csp_source_repair_hint:
            raise csp_source_repair_hint

    @classmethod
    def _accept_one_(cls, bot):
        events = bot.accept_between(Event, head="{", sep=",", end=",", tail="}")
        if events is not None:
            return Alphabet(*events)


# name the alphabet of a process #


class Argot(
    KwArgsCspCell,
    collections.namedtuple("Argot", "proc".split(", ")),
):

    """argot = 'α' proc"""

    _csp_style_ = Style(first="α{}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("α"):
                if proc := bot.accept_one(Proc):

                    bot._commit_()
                    return Argot(proc)

    # "α" "\u03B1" Greek Small Letter Alpha


class ArgotNames(
    ArgsCspCell,
    collections.namedtuple("ArgotNames", "argots".split(", ")),
):
    """argot_names = argot { '=' argot }"""

    _csp_style_ = Style(first="{}", middle=" = {}")

    def _compile_(self):
        argots = self.argots

        csp_source_repair_hint = csp_bot_hint_uniq(
            "argot names", items=list(_.proc.name for _ in argots)
        )
        if csp_source_repair_hint:
            raise csp_source_repair_hint

    @classmethod
    def _accept_one_(cls, bot):
        argots = bot.accept_some(Argot, sep="=")
        if argots:
            cell = bot.form_plural(ArgotNames, items=argots)
            return cell


class ArgotDef(
    KwArgsCspCell,
    collections.namedtuple("ArgotDef", "argot_names, alphabet".split(", ")),
):
    """argot_def = argot_names '=' alphabet"""

    _csp_style_ = Style(first="{}", last=" = {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if argot_names := bot.accept_one(ArgotNames):
                if bot.accept_mark("="):
                    if alphabet := bot.accept_one(Alphabet):

                        bot._commit_()
                        return ArgotDef(argot_names, alphabet=alphabet)


class ArgotEvent(
    KwArgsCspCell,
    collections.namedtuple("ArgotEvent", "event, argot".split(", ")),
):
    """argot_event =  event ':' argot"""

    _csp_style_ = Style(first="{}", last=":{}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if event := bot.accept_one(Event):
                if bot.accept_mark(":"):
                    if argot := bot.accept_one(Argot):

                        bot._commit_()
                        return ArgotEvent(event, argot=argot)


# sketch a fork of prongs of prolog and epilog of steps #


class Step(
    KwArgsCspCell,
    collections.namedtuple("Step", list()),
):
    """step = argot_event | event"""

    @classmethod
    def _accept_one_(cls, bot):
        if argot_event := bot.accept_one(ArgotEvent):
            return argot_event
        elif event := bot.accept_one(Event):
            return event


class Prolog(
    ArgsCspCell,
    collections.namedtuple("Prolog", "steps".split(", ")),
):
    """prolog = step { '→' step }"""

    _csp_style_ = Style(first="{}", middle=" → {}")

    def _menu_(self):
        steps = self.steps
        menu = (steps[0],)
        return menu

    @classmethod
    def _accept_one_(cls, bot):
        steps = bot.accept_some(Step, sep="→")
        if steps:
            cell = bot.form_plural(Prolog, items=steps)
            return cell

    # "→" "\u2192" Rightwards Arrow


class Epilog(
    KwArgsCspCell,
    collections.namedtuple("Epilog", list()),
):
    """epilog = proc | pocket"""

    @classmethod
    def _accept_one_(cls, bot):
        if proc := bot.accept_one(Proc):
            return proc
        elif pocket := bot.accept_one(Pocket):
            return pocket


class Prong(  # Csp:  prefixes then process
    KwArgsCspCell,
    collections.namedtuple("Prong", "prolog, epilog".split(", ")),
):
    """prong = prolog '→' epilog"""

    _csp_style_ = Style(first="{}", last=" → {}")

    def _compile_(self):
        pass  # TODO:  alphabet of prolog must be in alphabet of epilog

    def _menu_(self):
        prolog = self.prolog
        menu = prolog._menu_()
        return menu

    @classmethod
    def _accept_one_(cls, bot):

        with bot._checkpoint_():

            if prolog := bot.accept_one(Prolog):
                if bot.accept_mark("→"):
                    if epilog := bot.accept_one(Epilog):

                        bot._commit_()
                        return Prong(prolog, epilog=epilog)

    # "→" "\u2192" Rightwards Arrow


class Fork(
    ArgsCspCell,
    collections.namedtuple("Fork", "prongs".split(", ")),
):
    """fork = prong { '|' prong }"""

    _csp_style_ = Style(first="{}", middle=" | {}")

    def _compile_(self):
        menu = self._menu_()

        csp_source_repair_hint = csp_bot_hint_uniq(
            "guard names", items=list(_.name for _ in menu)
        )
        if csp_source_repair_hint:
            raise csp_source_repair_hint

    def _menu_(self):
        events = list()
        for prong in self.prongs:
            events.extend(prong._menu_())
        menu = tuple(events)
        return menu

    @classmethod
    def _accept_one_(cls, bot):

        prongs = bot.accept_some(Prong, sep="|")
        if prongs:
            fork_or_prong = bot.form_plural(Fork, items=prongs)

            return fork_or_prong

    # "→" "\u2192" Rightwards Arrow


# define a proc of pocket over alphabet #


class ProcDef(
    KwArgsCspCell,
    collections.namedtuple("ProcDef", "proc, proc_body".split(", ")),
):
    """proc_def = proc '=' body"""

    _csp_style_ = Style(first="{}", last=" = {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if proc := bot.accept_one(Proc):
                if bot.accept_mark("="):
                    if proc_body := bot.accept_one(ProcBody):

                        bot._commit_()
                        return ProcDef(proc, proc_body=proc_body)


class ProcBody(
    KwArgsCspCell,
    collections.namedtuple("ProcBody", "body".split(", ")),
):
    """proc_body = proc | sharp_body | fuzzy_body | fork | pocket"""

    @classmethod
    def _accept_one_(cls, bot):
        if proc := bot.accept_one(Proc):
            return proc
        elif sharp_body := bot.accept_one(SharpBody):
            return sharp_body
        elif fuzzy_body := bot.accept_one(FuzzyBody):
            return fuzzy_body
        elif fork := bot.accept_one(Fork):
            return fork
        elif pocket := bot.accept_one(Pocket):
            return pocket


class SharpBody(
    KwArgsCspCell,
    collections.namedtuple("SharpBody", "proc, alphabet, pocket".split(", ")),
):
    """sharp_body = 'μ' proc ':' alphabet '•' pocket"""

    _csp_style_ = Style(first="μ {}", middle=" : {}", last=" • {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("μ"):
                if proc := bot.accept_one(Proc):
                    if bot.accept_mark(":"):
                        if alphabet := bot.accept_one(Alphabet):
                            if bot.accept_mark("•"):
                                if pocket := bot.accept_one(Pocket):

                                    bot._commit_()
                                    return SharpBody(
                                        proc, alphabet=alphabet, pocket=pocket
                                    )


class FuzzyBody(
    KwArgsCspCell,
    collections.namedtuple("FuzzyBody", "proc, pocket".split(", ")),
):
    """fuzzy_body = 'μ' proc '•' pocket"""

    _csp_style_ = Style(first="μ {}", last=" • {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("μ"):
                if proc := bot.accept_one(Proc):
                    if bot.accept_mark("•"):
                        if pocket := bot.accept_one(Pocket):

                            bot._commit_()
                            return FuzzyBody(proc, pocket=pocket)


# say what process work is pocketable #


class Pocketable(
    KwArgsCspCell,
    collections.namedtuple("Pocketable", list()),
):
    """pocketable = fork | body"""

    @classmethod
    def _accept_one_(cls, bot):
        if fork := bot.accept_one(Fork):
            return fork
        elif proc_body := bot.accept_one(ProcBody):
            return proc_body


class Pocket(
    KwArgsCspCell,
    collections.namedtuple("Pocket", "pocketable".split(", ")),
):
    """pocket = '(' pocketable ')'"""

    _csp_style_ = Style(head="(", middle="{}", tail=")")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("("):
                if pocketable := bot.accept_one(Pocketable):
                    if bot.accept_mark(")"):

                        bot._commit_()
                        return Pocket(pocketable)


# accept any of many fragments of Csp source #


class Frag(
    KwArgsCspCell,
    collections.namedtuple("Frag", list()),
):
    """frag = transcript | alphabet | proc_def | argot_def | pocketable"""

    @classmethod
    def _accept_one_(cls, bot):
        if transcript := bot.accept_one(Transcript):
            return transcript
        elif alphabet := bot.accept_one(Alphabet):
            return alphabet
        elif proc_def := bot.accept_one(ProcDef):
            return proc_def
        elif argot_def := bot.accept_one(ArgotDef):
            return argot_def
        elif pocketable := bot.accept_one(Pocketable):
            return pocketable


#
# Did You Mean:  Form Source Repair Hints to raise
#


def csp_bot_hint_csp_none(bot):
    _ = bot
    raise SourceRepairHint("need hint from some smarter parser")


def csp_bot_hint_csp_more(bot, cell):
    _ = bot
    _ = cell
    raise SourceRepairHint("need hint for less source")


def csp_bot_hint_uniq(kind, items):

    dupes = duplicates(sorted(items))
    if dupes:
        str_dupes = " ".join(dupes)  # TODO: '" ".join' goes wrong if " " in any item
        hint = "need distinct {}, got: {}".format(kind, str_dupes)
        raise SourceRepairHint(hint)


#
# Extra Pythonic:  Run on top of a layer of general-purpose Python idioms
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
def duplicates(items):
    """Keep the items that show up more than once in a row, drop the rest"""

    dupes = list(
        items[_]
        for _ in range(len(items))
        if (
            ((_ > 0) and (items[_ - 1] == items[_]))
            or ((_ < (len(items) - 1)) and (items[_] == items[_ + 1]))
        )
    )

    return dupes


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


# deffed in many files  # partly missing from docs.python.org
def unique_everseen(items):  # TODO: mmm not tested much here lately
    """Remove each duplicate, but keep the first occurrence, in order"""

    item_set = set()

    uniques = list()
    for item in items:
        if item not in item_set:
            item_set.add(item)
            uniques.append(item)

    return uniques


#
# Try Self Test
#

TRACES = list()


def try_test_self_some():
    """Try Self Test"""

    tests = collect_tests()

    for (index, test) in enumerate(tests):

        TRACES[::] = list()
        try:
            try_test_self_one(test)
        except AssertionError:
            for trace in TRACES:
                stderr_print(trace)
            raise


def try_test_self_one(test):
    """Pass test, else raise AssertionError"""

    def _trace_(kwargs):
        space = argparse.Namespace(**kwargs)
        TRACES.append(space)

    (csp, py, str_exc) = test
    _trace_(dict(csp=csp, py=py, str_exc=str_exc))

    # Bootstrap on Csp paired with Python, and without raising Exception's

    if py:
        assert str_exc is None

        cell_of_py = eval(py)
        _trace_(dict(got_cell_of_py=bool(cell_of_py)))

        py_of_cell = format_as_py(cell_of_py)
        _trace_(dict(py_of_cell=py_of_cell))
        assert py_of_cell == py

        csp_of_cell = format_as_csp(cell_of_py)
        _trace_(dict(csp_of_cell=csp_of_cell))
        assert csp_of_cell == csp

        cell_of_csp = eval_csp(csp)
        _trace_(dict(cell_of_csp=cell_of_csp))
        assert cell_of_csp == cell_of_py

    # Then switch up to test lots of brief Csp in place of a few verbose Python
    # and include raising Exception's

    else:

        try:
            cell_of_csp = eval_csp(csp)
            _trace_(dict(cell_of_csp=bool(cell_of_csp)))
            assert not str_exc
        except SourceRepairHint as srh:
            str_srh = str(srh)
            _trace_(dict(str_srh=str_srh))
            assert str_srh == str_exc, (str_srh, str_exc)

            return

        py_of_cell = format_as_py(cell_of_csp)
        _trace_(dict(py_of_cell=py_of_cell))

        csp_of_cell = format_as_csp(cell_of_csp)
        _trace_(dict(csp_of_cell=csp_of_cell))
        assert csp_of_cell == csp

        cell_of_py = eval(py_of_cell)
        _trace_(dict(got_cell_of_py=bool(cell_of_py)))
        assert cell_of_py == cell_of_csp


def collect_tests():
    """Collect the tests as Csp alone, or as Csp paired with Python"""

    # Collect tests of Csp paired with Lisp on Python

    (csps, pys) = choose_csps_pys_pairs()

    assert len(csps) == len(pys)
    str_excs = len(csps) * [None]

    # Collect tests of Csp without git-tracked Lisp on Python
    # TODO: include comments and blanks in the tests

    chars = CHAPTER_1
    chars += CHAPTER_2
    chars = textwrap.dedent(chars).strip()

    csp_chars = "\n".join(_.partition("#")[0] for _ in chars.splitlines())
    csp_lines = (_.strip() for _ in csp_chars.splitlines() if _.strip())

    # Visit each line of Csp that has no Python

    csp_laters = list()
    for (index, csp_line) in enumerate(csp_lines):

        # Join Csp lines til all ( [ { ⟨ marks closed by ) ] } ⟩ marks

        csp_laters.append(csp_line)
        csp_joined = "\n".join(csp_laters)

        shards = split_csp(csp_joined)
        (opened, closed) = balance_csp_shards(shards)
        assert not closed, (closed, opened, csp_line)

        if opened:
            continue

        csp_laters = list()

        # Collapse the Csp Test into a single line
        # TODO: include the line-break's in test

        csp = csp_joined
        csp = csp.replace("(\n", "(")  # TODO: grossly inelegant
        csp = csp.replace("\n)", ")")  # TODO: grossly inelegant
        csp = csp.replace("\n", " ")
        csp = csp.replace("\t", " ")

        # Admit we have no Py

        py = None

        # Pick 0 or 1 raised Exception's out of the test source
        # TODO: keep separate the same test when given duplicates

        tail_chars = chars[chars.index(csp_line) :]
        tail_line = tail_chars.splitlines()[0]
        tail_comment = tail_line.partition("#")[-1].strip()

        str_exc = None
        if tail_comment.startswith("no, "):
            str_exc = tail_comment[len("no, ") :]

        # Collect the test

        csps.append(csp)
        pys.append(py)
        str_excs.append(str_exc)

    # Require no lines of Csp leftover

    assert not csp_laters

    return zip(csps, pys, str_excs)


def choose_csps_pys_pairs():
    """Put a few fragments of Py Source, and their Csp Source, under test"""

    csps = list()
    pys = list()

    # A Proc exists

    csps.append("X")

    pys.append(
        textwrap.dedent(
            """
        Proc("X")
        """
        ).strip()
    )

    # An Alphabet collects Events

    csps.append("{coin, choc, toffee}")

    pys.append(
        textwrap.dedent(
            """
        Alphabet(
            Event("coin"),
            Event("choc"),
            Event("toffee"),
        )
        """
        ).strip()
    )

    # An Event Guards a Proc

    csps.append("choc → X")

    pys.append(
        textwrap.dedent(
            """
        Prong(
            prolog=Event("choc"),
            epilog=Proc("X"),
        )
        """
        ).strip()
    )

    # Events guard Proc's

    csps.append("choc → X | toffee → X")

    pys.append(
        textwrap.dedent(
            """
        Fork(
            Prong(
                prolog=Event("choc"),
                epilog=Proc("X"),
            ),
            Prong(
                prolog=Event("toffee"),
                epilog=Proc("X"),
            ),
        )
        """
        ).strip()
    )

    # An Event guards a Pocket

    csps.append("coin → (choc → X | toffee → X)")

    pys.append(
        textwrap.dedent(
            """
        Prong(
            prolog=Event("coin"),
            epilog=Pocket(
                pocketable=Fork(
                    Prong(
                        prolog=Event("choc"),
                        epilog=Proc("X"),
                    ),
                    Prong(
                        prolog=Event("toffee"),
                        epilog=Proc("X"),
                    ),
                ),
            ),
        )
        """
        ).strip()
    )

    # Stepping through Events of an Alphabet defines a Proc

    csps.append("VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))")

    pys.append(
        textwrap.dedent(
            """
        ProcDef(
            proc=Proc("VMCT"),
            proc_body=SharpBody(
                proc=Proc("X"),
                alphabet=Alphabet(
                    Event("coin"),
                    Event("choc"),
                    Event("toffee"),
                ),
                pocket=Pocket(
                    pocketable=Prong(
                        prolog=Event("coin"),
                        epilog=Pocket(
                            pocketable=Fork(
                                Prong(
                                    prolog=Event("choc"),
                                    epilog=Proc("X"),
                                ),
                                Prong(
                                    prolog=Event("toffee"),
                                    epilog=Proc("X"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
        """
        ).strip()
    )

    # Return the chosen fragments

    return (csps, pys)


CHAPTER_1 = r"""

    #
    # Chapter 1:  Processes
    #


    # 1.1 Introduction, p.1

    {coin, choc, in2p, out1p}
    {a, b, c, d, e}

    VMS
    VMC

    P   # arbitrary processes in laws
    Q
    R

    # A = B = C = {x,y,z}  # sets of events, variables denoting events

    X   # variables denoting processes
    Y

    αVMS = {coin, choc}
    αVMC = {in1p, in2p, small, large, out1p}


    # 1.1.1 Prefix, p.3

    (x → P)  # 'x then P'
    # α(x → P) = αP  provided x ∈ αP

    coin → STOP  # 1.1.1 X1  # Pdf speaks STOP↓αVMS as subscript
    (coin → (choc → (coin → (choc → STOP))))  # 1.1.1 X2

    αCTR = {up, right}
    CTR = (right → up → right → right → STOP)  # 1.1.1 X3

    P → Q  # no, need hint for less source
    x → y  # no, need hint from some smarter parser

    x → (y → STOP)


    # 1.1.2 Recursion, p.4

    αCLOCK = {tick}

    (tick → CLOCK)
    CLOCK = (tick → CLOCK)
    CLOCK = (tick → (tick → CLOCK))
    CLOCK = (tick → (tick → (tick → CLOCK)))  # tick → tick → tick → ... unbounded

    # X = X
    # X = F(X)
    # μ X : A • F(X)
    # μ X : A • F(X) = μ Y : A • F(Y)

    CLOCK = μ X : {tick} • (tick → X)  # 1.1.2 X1

    VMS = (coin → (choc → VMS))  # 1.1.2a X2
    VMS = μ X : {coin, choc} • (coin → (choc → X))  # 1.1.2b X2

    αCH5A = {in5p, out2p, out1p}
    CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3

    # αCH5B = αCH5A  # TODO
    αCH5B = {in5p, out2p, out1p}
    CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4


    # 1.1.3 Choice, p.7

    (x → P | y → Q)
    # α(x → P | y → Q) = αP provided {x, y} ⊆ αP and αP = αQ

    (up → STOP | right → right → up → STOP)  # 1.1.3 X1

    # 1.1.3 X2     # Pdf doesn't split sourcelines in Black style
    CH5C = in5p → (
        out1p → out1p → out1p → out2p → CH5C
        | out2p → out1p → out2p → CH5A
    )

    VMCT = μ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3

    VMC = (     # 1.1.3 X4
        in2p → (
            large → VMC
            | small → out1p → VMC
        ) | in1p → (
            small → VMC
            | in1p → (
                large → VMC
                | in1p → STOP
            )
        )
    )

    VMCRED = μ X • (coin → choc → X | choc → coin → X)  # 1.1.3 X5

    VMS2 = (coin → VMCRED)  # 1.1.3 X6

    COPYBIT = μ X • (  # 1.1.3 X7
        in.0 → out.0 → X
        | in.1 → out.1 → X
    )

    P | Q  # no, need hint for less source
    (x → P | x → Q)  # no, need distinct guard names, got: x x
    (x → P | (y → Q | z → R))  # no, need hint from some smarter parser

    (x → P | y → Q | z → R)

    (x → P | y)  # no, need hint from some smarter parser
    (x → P) | (y → Q)  # no, need hint for less source
    (x → P) | y → Q  # no, need hint for less source

    # (x:B → P(x))
    # (x:B → P(x)) = (y:B → P(u))

    # αRUN\A = A
    # RUN\A = (x:α → RUN\A)       # 1.1.3 X8

    # (x:{e} → P(x)) = (e → P(e))

    # (a → P | b → Q ) = (x : B → R(x))
    # B = {a,b}
    # R(x) = if x = a then P else Q


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

    ⟨coin, choc, coin, choc⟩  # 1.5 X1

    ⟨coin, choc, coin⟩  # 1.5 X2

    ⟨⟩  # 1.5 X3

    ⟨⟩  # 1.5 X4.1
    ⟨in2p⟩  # 1.5 X4.2.1
    ⟨in1p⟩  # 1.5 X4.2.2
    ⟨in2p, large⟩  # 1.5 X4.3.1
    ⟨in2p, small⟩  # 1.5 X4.3.2
    ⟨in1p, in1p⟩  # 1.5 X4.3.3
    ⟨in1p, small⟩  # 1.5 X4.3.4

    ⟨in1p, in1p, in1p⟩  # 1.5 X5.1
    ⟨in1p, in1p, in1p, x⟩  # 1.5 X5.2


    # 1.6 Operations on traces

"""

CHAPTER_2 = r"""
    # TODO:  Tests beyond Csp Chapter 1
"""


GLOSSARY_BEYOND_CSP = r"""

Notation
..............  Meaing
..............  ..........................  Example
..............  ..........................  ............

#               separate source & comment

\               subscript                   RUN\A  # RUN sub A

"""


GLOSSARY_OF_LOGIC = r"""

Notation
..............  Meaing
..............  ..........................  Example
..............  ..........................  ............

=               equals                      x = x

≠               is distinct from            x ≠ x + 1

∎               end of an example or proof

P ∧ Q           P and Q (both true)         x ≤ x + 1  ∧  x ≠ x + 1

P ∨ Q           P or Q (one or both true)   x ≤ y  ∨  y ≤ x

¬ P             not P (P is not true)       ¬ 3 ≥ 5

P ⇒ Q           if P then Q                 x < y  ⇒  x ≤ y

P ≡             P if and only if Q          x < y  ≡  y > x

∃ x • P         there exists an x           ∃ x • x > y
                such that P

∀ x • P         for all x, yes P            ∀ x • x < x + 1

∃ x : A • P     there exists an x
                in set A such that P

∀ x : A • P     for all x in set A, yes P

# Pdf doesn't choose the '∎' end-of-example/proof character for us
# Pdf lacks the two "yes " here
# Pdf doesn't add spaces to show nesting, such as '∨  y ≤ x' far above

"""


# TODO:  GLOSSARY_OF_SETS
# TODO:  GLOSSARY_OF_FUNCTIONS
# TODO:  GLOSSARY_OF_TRACES
# TODO:  GLOSSARY_OF_SPECIAL_EVENTS

GLOSSARY_OF_PROCESSES = """

Section
......  Notation
..................          Meaning

1.1     αP                  the alphabet of process P

1.1.1   a → P               a then P

1.1.3   (a → P | b → Q)     a then P choice b then Q (provided a ≠ b)

1.1.3   (x:A → P(x))        (choice of) x from A then P(x)

1.1.2   μ X : A • F(X)      the process X with alphabet A
                            such that X = F(X)

1.8     P / s               P after (engaging in events of trace) s

1.10.1  P sat S             (process) P satisfies (specification) S
1.10.1  tr                  an arbitrary trace of the specified process

# Pdf doesn't squeeze spaces to show close association, such as 'αP' and '(x:A'

# TODO: fill out the rest of GLOSSARY_OF_PROCESSES

"""

# TODO:  GLOSSARY_OF_ALGEBRA
# TODO:  GLOSSARY_OF_GRAPHS


#
# To do
#

# TODO:  review grammar & grammar class names vs CspBook Pdf

# TODO:  code up cogent '.format_as_trace' representations of infinities
# TODO:  write the Csp code for me, when I give you the trace and edit the trace
# TODO:  exit into interactive Repl

# TODO:  Slackji :: transliteration of Unicode Org names of the Csp Unicode symbols
# TODO:  Ascii transliteration of Csp Unicode

# TODO:  search the source lines for 'TODO' marks


#
# Launch from command line
#


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
