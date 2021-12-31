#!/usr/bin/env python3

r"""
usage: _cspsh4.py [-h]

chat over programs written as "communicating sequential processes"

options:
  -h, --help  show this help message and exit

workflow:
  while :; do
    echo ... paused ...
    read
    (
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

# TODO: PyLint E1101: Instance of '...' has no '...' member (no-member)
# TODO: PyLint R0901: Too many ancestors (.../7) (too-many-ancestors)
# TODO: PyLint R0911: Too many return statements (.../6) (too-many-return-statements)
# TODO: PyLint R1710: ... all ... return an expr... (inconsistent-return-statements)


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

    parser = compile_argdoc(epi="workflow:")
    exit_unless_main_doc_eq(parser)
    _ = parser.parse_args(argv[1:])

    try_test_self_some()

    stderr_print("cspsh: + exit 0")


#
# Eval:  Split and knit and compile Csp Source
#


def eval_csp(csp):
    """Split and knit Cells of Source Chars of Csp"""

    splits = split_csp_source(csp)

    (opened, closed) = balance_csp_splits(splits)
    assert not closed, (closed, opened, csp)
    assert not opened, (closed, opened, csp)

    cell = knit_csp_splits(splits)

    compile_csp_cell(cell)

    return cell


#
# Split:  Split Csp Source into blank and nonblank, balanced and unbalanced, Splits
#
# aka yet another Lexxer, Scanner, Splitter, Tokenizer
#


BLANKS_REGEX = r"(?P<blanks>[ \t\n]+)"
COMMENT_REGEX = r"(?P<comment>#[^\n]*)"

MARK_REGEX = r"(?P<mark>[()*,:={|}αμ•→⟨⟩])"
NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
# NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"  # TODO: test Freak Splits often
FREAK_REGEX = r"(?P<freak>.)"

SPLITS_REGEX = r"|".join(
    [BLANKS_REGEX, COMMENT_REGEX, MARK_REGEX, NAME_REGEX, FREAK_REGEX]
)

OPENING_MARKS = "([{⟨"
CLOSING_MARKS = ")]}⟩"


def split_csp_source(source):
    """Split Csp Source into Csp Splits of kinds of fragments of Source Chars"""

    # Drop the "\r" out of each "\r\n"

    chars = "\n".join(source.splitlines()) + "\n"

    # Split the Csp Source Chars into Csp Blanks, Comments, Marks, Names, & Freaks

    matches = re.finditer(SPLITS_REGEX, string=chars)
    items = list(_to_item_from_groupdict_(_.groupdict()) for _ in matches)

    splits = list(CspSplit(key=k, value=v) for (k, v) in items)

    # Require no Source Chars dropped

    rejoined = "".join(str(_) for _ in splits)  # a la ._split_misfit_
    assert rejoined == chars

    # Announce the Freaks

    for split in splits:
        str_freak = split.format_as_freak_char()
        if str_freak:

            ch = str(split)
            if ch not in split_csp_source.freaks:
                split_csp_source.freaks.add(ch)

                stderr_print("cspsh: freak char {}".format(str_freak))

    # Succeed

    return splits


split_csp_source.freaks = set()  # TODO: one set per Source, not per Python Process


def _to_item_from_groupdict_(groupdict):
    """Pick the 1 Item of Value Is Not None out of an Re FindIter GroupDict"""

    items = list(_ for _ in groupdict.items() if _[-1] is not None)
    assert len(items) == 1, groupdict

    item = items[-1]
    return item


def balance_csp_splits(splits):
    """Open up paired marks, close them down, & say what's missing or extra"""

    opened = ""
    closed = ""
    next_closing_mark = None

    for split in splits:

        # Open up any opening mark

        for mark in OPENING_MARKS:
            if split.is_mark(mark):
                opened += mark
                pair_index = OPENING_MARKS.index(mark)
                next_closing_mark = CLOSING_MARKS[pair_index]

                break

        # Close down an open mark followed by its corresponding close mark

        for mark in CLOSING_MARKS:

            if split.is_mark(mark):
                if mark == next_closing_mark:
                    opened = opened[:-1]

                # List close marks given before a corresponding open mark

                else:
                    closed += mark

                break

    # Return ("", "") if balanced, else the extra open marks and extra close marks

    return (opened, closed)


class CspSplit(collections.namedtuple("CspSplit", "key value".split())):
    """Carry a fragment of Csp Source Code"""

    def __str__(self):
        """Print as the fragment of source, but stay repr'ed as the whole Self"""

        str_self = str(self.value)
        return str_self

    def format_as_freak_char(self):
        """Say if this Split is a Mark of those Chars, or not"""

        if self.key != "freak":
            return

        ch = self.value
        assert len(ch) == 1, (len(ch), repr(ch))

        # Rep chars that print only as \u or \U escapes

        repr_ch = repr(ch)

        ascii_ch = ascii(ch)
        if ascii_ch == repr_ch:
            if ascii_ch.lower().startswith(r"'\u"):
                return ascii_ch
            if ascii_ch.startswith(r"'\x"):
                return ascii_ch

            assert 0x20 <= ord(ch) <= 0x7E, hex(ord(ch))
            uxxxx_ch = r"\x{:02x}".format(ord(ch))

            return "{} {}".format(uxxxx_ch, repr_ch)

        return "{} {}".format(ascii_ch, repr_ch)

        # such as Apostrophe:  \x27 "'"
        # such as Reverse Solidus:  \x5c '\\'
        # such as Greek Small Letter Mu:  \u03bc 'μ'
        # such as Emoji Smiling Face With Smiling Eyes:  '\U0001f60a' '😊'

    def is_yarn(self):
        """Say to knit this kind of Split, drop the other kinds"""

        key = self.key
        if key not in "blanks comment".split():
            assert key in "mark name freak".split(), key
            return True

    def is_mark(self, chars):
        """Say if this Split is a Mark of those Chars, or not"""

        if self.key == "mark":
            if self.value == chars:
                return True

    def peek_alphabet_name(self):
        """Return the Chars of the Name if it splits as a Csp Alphabet Name"""
        return self.peek_proc_name()

    def peek_arg_name(self):
        """Return the Chars of the Name if it splits as a Csp Arg Name"""

        if self.key == "name":
            name = self.value
            return name

    def peek_event_name(self):
        """Return the Chars of the Name if it splits as a Csp Proc Name"""

        if self.key == "name":
            name = self.value

            if name.upper() != name:  # could be upper
                if name == name.lower():  # is lower
                    return name

    def peek_proc_name(self):
        """Return the Chars of the Name if it splits as a Csp Event Name"""

        if self.key == "name":
            name = self.value

            if name.lower() != name:  # could be lower
                if name == name.upper():  # is upper
                    return name


#
# Knit:  Form an Abstract Syntax Tree (AST) Graph of Cells of Args and KwArgs
#
# aka yet another Parser, Yacc
#
#   Such as:
#
#       Add(1, Divide(dividend=2, divisor=3))  # 1 + 2/3
#


def knit_csp_splits(splits):
    """Form Cells of the Splits and knit them into a Graph at a Cell"""

    rejoined = "".join(str(_) for _ in splits)  # rejoin to help trigger breakpoints
    _ = rejoined

    tails = list(_ for _ in splits if _.is_yarn())
    bot = KnitterBot(tails)

    try:

        if not tails:
            raise need_some_source()

        cell = bot.accept_one(Csp)

        if not cell:
            raise need_knitter()

        if not bot.at_mark(""):
            raise need_more_source()

    except Exception as exc:

        if not main.want_str_exc:
            # TODO: go invent more accurate strong Source Repair Hints
            # TODO: more logging for unexpected failure to knit

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
        for index in range(len(replies)):
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

    def _as_source_(self, func, replies, style):
        """Format this Cell as Source Chars"""

        # Pull the Replies from the Graph, if none supplied
        # else form Source Chars out of the Replies

        if replies is None:
            py = self._grok_(func=func)
            return py

        # Study this Cell, its children, and the bonds between them

        bonds = list(self._bonds_())

        cell_type_name = type(self).__name__
        formats = self._choose_formats_(style, replies=replies)

        assert len(replies) == len(bonds)
        assert len(formats[1:][:-1]) == len(replies)

        # Begin by adding Source Chars from this Cell

        chars = ""
        chars += formats[0].format(cell_type_name)

        # Add Source Chars from each Reply, as styled by this Cell

        for (bond, reply, reply_format) in zip(bonds, replies, formats[1:][:-1]):
            key = bond.key
            down = bond.down

            str_reply = str(reply)
            if isinstance(down, str):  # TODO: 'isinstance' should be method
                if func is format_as_py:  # TODO: inelegant to override str for func
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

        # End by adding more Source Chars from this Cell

        chars += formats[-1].format()

        # Produce only Spaces and Line Breaks as Blanks, produce no Tabs as Blanks

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
# KnitterBot:  Knit Splits into an Abstract Syntax Tree Graph of Cells of Kwargs & Args
#


class SourceRepairHint(Exception):
    """Say how to repair Source Chars, when we cannot split, knit, or compile them"""


class KnitterBot:
    """
    Choose one Path to walk through the Splits of Source

    Try one Path, then another, till some Path matches all the Splits

    Say "take" to mean require and consume
    Say "accept" to mean take if present, else return None
    Say "peek" to mean detect and return a copy, but do Not consume
    Say "at" to mean detect, but do Not consume

    Let the caller ask to backtrack indefinitely far,
    such as back across all of the partial match, for each incomplete match

    Trust the 'def __str__' of each Split is its fragment of Source Chars
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
        """Style a couple of Alt Sources to show the splitting and knitting"""

        before = " ".join(str(_) for _ in self.heads[: -len(self.tails)])
        after = " ".join(str(_) for _ in self.tails).rstrip()

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

        cell = cls._accept_one_(self)  # TODO: 'accept_one' overloads '_accept_one_'
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
        """Return an Alt Source copy of the knitted Splits of the Source"""

        (fit, _) = self._split_misfit_()
        return fit

    def form_plural(self, cls, items):
        """Return the first and only item, else flatten then wrap in plural Cls"""

        if len(items) == 1:
            return items[0]

        return cls(*items)

    def misfit(self):
        """Return an Alt Source copy of the not-knitted Splits of the Source"""

        (_, misfit) = self._split_misfit_()
        return misfit

    def peek_one_tail(self):
        """Return the next Tail, else None"""

        tails = self.tails

        if tails:
            tail = tails[0]
            return tail

    def suggest(self, hint):
        """Form an Exception to say how to repair Source Chars"""

        return SourceRepairHint(hint)

    def take_one_tail(self):
        """Consume the next Tail, else raise IndexError"""

        tails = self.tails

        tails[::] = tails[1:]


#
# Csp Atoms:  Plan to knit Cells of Cells of atomic single Cells of single Splits
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


class ProcName(
    InlineCspCell,
    collections.namedtuple("ProcName", "name".split(", ")),
):
    """Accept one Proc name, if present"""  # split same as an Alphabet or Arg name

    @classmethod
    def _accept_one_(cls, bot):

        tail = bot.peek_one_tail()
        if tail:
            name = tail.peek_proc_name()
            if name is not None:
                bot.take_one_tail()

                return ProcName(name)


class Alphabet(
    InlineCspCell,
    collections.namedtuple("Alphabet", "name".split(", ")),
):
    """Accept one Alphabet name, if present"""  # split same as an Arg or Proc name

    @classmethod
    def _accept_one_(cls, bot):

        tail = bot.peek_one_tail()
        if tail:
            name = tail.peek_alphabet_name()
            if name is not None:
                bot.take_one_tail()

                return Alphabet(name)


class Arg(
    InlineCspCell,
    collections.namedtuple("Arg", "name".split(", ")),
):
    """Accept one Arg name, if present"""  # split same as an Alphabet or Proc name

    @classmethod
    def _accept_one_(cls, bot):

        tail = bot.peek_one_tail()
        if tail:
            name = tail.peek_arg_name()
            if name is not None:
                bot.take_one_tail()

                return Arg(name)


#
# Csp Knitter Doc:  Code up our Grammar in a Backus Naur Form (BNF) of atomic Cells
#
# In this BNF,
#
#       ','         is a quotation of source
#       [ ... ]     is 0 or 1
#       { ... }     is 0 or more
#


_grammar_ = r"""

    transcript = '⟨' { event ',' } [ event ] '⟩'
    event_set = '{' { event ',' } [ event ] '}'

    proc = proc_with_args | proc_with_one | proc_name
    proc_with_one = proc '*' arg
    proc_with_args = proc_name arg_list
    arg_list = '(' { arg ',' } [ arg ]

    argot = 'α' proc_body
    argot_names = argot { '=' argot }
    argot_def = argot_names '=' event_set

    world = event_set | argot | alphabet
    argot_event =  event ':' world

    step = argot_event | event
    prolog = step { '→' step }
    epilog = proc | pocket
    prong = prolog '→' epilog
    fork = prong { '|' prong }

    proc_def = proc '=' proc_body
    proc_body = sharp_body | fuzzy_body | fork | basic_body
    sharp_body = 'μ' proc ':' world '•' basic_body
    fuzzy_body = 'μ' proc '•' basic_body
    basic_body = proc | pocket

    pocketable = fork | proc_body
    pocket = '(' pocketable ')'

    term = transcript | event_set | proc_def | argot_def | pocketable | step | argot

    sentence = term { '=' term }
    csp = sentence

"""
# TODO: keep our Csp Knitter Doc synched with the Docstrins of Csp Knitter Code


#
# Csp Knitter Code:  Code up our Grammar on top of KnitterBot
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


class EventSet(
    ArgsCspCell,
    collections.namedtuple("EventSet", "events".split(", ")),
):
    """event_set = '{' { event ',' } [ event ] '}'"""

    _csp_style_ = Style(head="{{", first="{}", middle=", {}", tail="}}")

    def _compile_(self):
        events = self.events

        csp_source_repair_hint = need_distinct(
            "event names", items=list(_.name for _ in events)
        )
        if csp_source_repair_hint:
            raise csp_source_repair_hint

    @classmethod
    def _accept_one_(cls, bot):
        events = bot.accept_between(Event, head="{", sep=",", end=",", tail="}")
        if events is not None:
            return EventSet(*events)


# Csp Procs without Args, with explicit 0 Args, with 1 Arg, with more Args #


class Proc(ArgsCspCell, collections.namedtuple("Proc", list())):
    """proc = proc_with_args | proc_with_one | proc_name"""

    @classmethod
    def _accept_one_(cls, bot):
        if proc_with_args := bot.accept_one(ProcWithArgs):
            return proc_with_args
        if proc_with_one := bot.accept_one(ProcWithOne):
            return proc_with_one
        if proc_name := bot.accept_one(ProcName):
            return proc_name


class ProcWithOne(
    ArgsCspCell,
    collections.namedtuple("ProcWithOne", "atoms".split(", ")),
):
    r"""proc_with_one = proc '*' arg"""

    _csp_style_ = Style(first="{}", middle=r"*{}")

    @classmethod
    def _accept_one_(cls, bot):

        with bot._checkpoint_():
            if proc_name := bot.accept_one(ProcName):
                if bot.accept_mark("*"):
                    if arg := bot.accept_one(Arg):

                        atoms = list()
                        atoms.append(proc_name)
                        atoms.append(arg)

                        bot._commit_()
                        return ProcWithOne(*atoms)


class ProcWithArgs(
    ArgsCspCell,
    collections.namedtuple("ProcWithOne", "atoms".split(", ")),
):
    """proc_with_args = proc_name arg_list"""

    _csp_style_ = Style(first="{}(", middle="{}, ", last="{}", tail=")")

    @classmethod
    def _accept_one_(cls, bot):

        with bot._checkpoint_():
            if proc_name := bot.accept_one(ProcName):
                if arg_list := bot.accept_one(ArgList):

                    atoms = list()
                    atoms.append(proc_name)
                    atoms.extend(arg_list.args)

                    bot._commit_()
                    return ProcWithArgs(*atoms)


class ArgList(
    ArgsCspCell,
    collections.namedtuple("ArgList", "args".split(", ")),
):
    """arg_list = '(' { arg ',' } [ arg ]"""

    @classmethod
    def _accept_one_(cls, bot):
        args = bot.accept_between(Arg, head="(", sep=",", end=",", tail=")")
        if args is not None:
            return ArgList(*args)


# name the event_set of a process #


class Argot(
    KwArgsCspCell,
    collections.namedtuple("Argot", "proc_body".split(", ")),
):

    """argot = 'α' proc_body"""

    _csp_style_ = Style(first="α{}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("α"):
                if proc_body := bot.accept_one(ProcBody):

                    bot._commit_()
                    return Argot(proc_body)

    # "α" "\u03B1" Greek Small Letter Alpha


class ArgotNames(
    ArgsCspCell,
    collections.namedtuple("ArgotNames", "argots".split(", ")),
):
    """argot_names = argot { '=' argot }"""

    _csp_style_ = Style(first="{}", middle=" = {}")

    def _compile_(self):
        argots = self.argots

        csp_source_repair_hint = need_distinct(
            "argot names", items=list(_.proc_body.name for _ in argots)
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
    collections.namedtuple("ArgotDef", "argot_names, event_set".split(", ")),
):
    """argot_def = argot_names '=' event_set"""

    _csp_style_ = Style(first="{}", last=" = {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if argot_names := bot.accept_one(ArgotNames):
                if bot.accept_mark("="):
                    if event_set := bot.accept_one(EventSet):

                        bot._commit_()
                        return ArgotDef(argot_names, event_set=event_set)


class World(
    KwArgsCspCell,
    collections.namedtuple("World", list()),
):
    """world = event_set | argot | alphabet"""

    @classmethod
    def _accept_one_(cls, bot):
        if event_set := bot.accept_one(EventSet):
            return event_set
        if argot := bot.accept_one(Argot):
            return argot
        if alphabet := bot.accept_one(Alphabet):
            return alphabet


class ArgotEvent(
    KwArgsCspCell,
    collections.namedtuple("ArgotEvent", "event, world".split(", ")),
):
    """argot_event =  event ':' world"""

    _csp_style_ = Style(first="{}", last=":{}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if event := bot.accept_one(Event):
                if bot.accept_mark(":"):
                    if world := bot.accept_one(World):

                        bot._commit_()
                        return ArgotEvent(event, world=world)


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
        if event := bot.accept_one(Event):
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
        if pocket := bot.accept_one(Pocket):
            return pocket


class Prong(  # Csp:  prefixes then process
    KwArgsCspCell,
    collections.namedtuple("Prong", "prolog, epilog".split(", ")),
):
    """prong = prolog '→' epilog"""

    _csp_style_ = Style(first="{}", last=" → {}")

    def _compile_(self):
        pass  # TODO:  event_set of prolog must be in event_set of epilog

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

        csp_source_repair_hint = need_distinct(
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


# define a proc of pocket over event_set #


class ProcDef(
    KwArgsCspCell,
    collections.namedtuple("ProcDef", "proc, proc_body".split(", ")),
):
    """proc_def = proc '=' proc_body"""

    _csp_style_ = Style(first="{}", last=" = {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if proc := bot.accept_one(Proc):
                if bot.accept_mark("="):
                    if proc_body := bot.accept_one(ProcBody):

                        bot._commit_()
                        return ProcDef(proc, proc_body=proc_body)


class ProcBody(KwArgsCspCell, collections.namedtuple("ProcBody", list())):
    """proc_body = sharp_body | fuzzy_body | fork | basic_body"""

    @classmethod
    def _accept_one_(cls, bot):
        if sharp_body := bot.accept_one(SharpBody):
            return sharp_body
        if fuzzy_body := bot.accept_one(FuzzyBody):
            return fuzzy_body
        if fork := bot.accept_one(Fork):
            return fork
        if basic_body := bot.accept_one(BasicBody):
            return basic_body


class SharpBody(
    KwArgsCspCell,
    collections.namedtuple("SharpBody", "proc, world, basic_body".split(", ")),
):
    """sharp_body = 'μ' proc ':' world '•' basic_body"""

    _csp_style_ = Style(first="μ {}", middle=" : {}", last=" • {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("μ"):
                if proc := bot.accept_one(Proc):
                    if bot.accept_mark(":"):
                        if world := bot.accept_one(World):
                            if bot.accept_mark("•"):
                                if basic_body := bot.accept_one(BasicBody):

                                    bot._commit_()
                                    return SharpBody(
                                        proc, world=world, basic_body=basic_body
                                    )


class FuzzyBody(
    KwArgsCspCell,
    collections.namedtuple("FuzzyBody", "proc, basic_body".split(", ")),
):
    """fuzzy_body = 'μ' proc '•' basic_body"""

    _csp_style_ = Style(first="μ {}", last=" • {}")

    @classmethod
    def _accept_one_(cls, bot):
        with bot._checkpoint_():

            if bot.accept_mark("μ"):
                if proc := bot.accept_one(Proc):
                    if bot.accept_mark("•"):
                        if basic_body := bot.accept_one(BasicBody):

                            bot._commit_()
                            return FuzzyBody(proc, basic_body=basic_body)


class BasicBody(
    KwArgsCspCell,
    collections.namedtuple("BasicBody", list()),
):
    """basic_body = proc | pocket"""

    @classmethod
    def _accept_one_(cls, bot):
        if proc := bot.accept_one(Proc):
            return proc
        if pocket := bot.accept_one(Pocket):
            return pocket


# say what process work is pocketable #


class Pocketable(
    KwArgsCspCell,
    collections.namedtuple("Pocketable", list()),
):
    """pocketable = fork | proc_body"""

    @classmethod
    def _accept_one_(cls, bot):
        if fork := bot.accept_one(Fork):
            return fork
        if proc_body := bot.accept_one(ProcBody):
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


class Term(
    KwArgsCspCell,
    collections.namedtuple("Term", list()),
):
    """term = transcript | event_set | proc_def | argot_def | pocketable | step | argot"""

    @classmethod
    def _accept_one_(cls, bot):
        if transcript := bot.accept_one(Transcript):
            return transcript
        if event_set := bot.accept_one(EventSet):
            return event_set
        if proc_def := bot.accept_one(ProcDef):
            return proc_def
        if argot_def := bot.accept_one(ArgotDef):
            return argot_def
        if pocketable := bot.accept_one(Pocketable):
            return pocketable
        if step := bot.accept_one(Step):
            return step
        if argot := bot.accept_one(Argot):
            return argot


class Sentence(
    ArgsCspCell,
    collections.namedtuple("Sentence", "terms".split(", ")),
):
    """sentence = term { '=' term }"""

    _csp_style_ = Style(first="{}", middle=" = {}")

    @classmethod
    def _accept_one_(cls, bot):

        terms = bot.accept_some(Term, sep="=")
        if terms:
            sentence_or_term = bot.form_plural(Sentence, items=terms)

            return sentence_or_term


Csp = Sentence  # as if class Csp: ... same as Sentence ...


#
# Did You Mean:  Form Source Repair Hints to raise
#


def need_distinct(kind, items):

    dupes = duplicates(sorted(items))
    if dupes:
        str_dupes = " ".join(dupes)  # TODO: '" ".join' goes wrong if " " in any item
        hint = "need distinct {}, got: {}".format(kind, str_dupes)
        return SourceRepairHint(hint)


def need_knitter():
    return SourceRepairHint("need a stronger knitter")


def need_more_source():
    return SourceRepairHint("need more source to knit")


def need_some_source():
    return SourceRepairHint("need some source")


#
# Extra Pythonic:  Run on top of a layer of general-purpose Python idioms
#


# deffed in many files  # missing from docs.python.org
def compile_argdoc(epi):
    """Construct the 'argparse.ArgumentParser' with Epilog but without Arguments yet"""

    doc = __main__.__doc__
    prog = doc.strip().splitlines()[0].split()[1]
    description = list(_ for _ in doc.strip().splitlines() if _)[1]
    epilog_at = doc.index(epi)
    epilog = doc[epilog_at:]  # pylint: disable=unsubscriptable-object

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=True,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

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
        # different in each copy-edit

        sys.exit(1)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def stderr_print_diff(**kwargs):
    """Return the Diff of the Lines given, but print it first when not empty"""

    (fromfile, tofile) = kwargs.keys()
    a_lines = kwargs[fromfile].splitlines()
    b_lines = kwargs[tofile].splitlines()

    diff_lines = list(
        difflib.unified_diff(
            a=a_lines,
            b=b_lines,
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

    for test in tests:

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

        cell_of_py = eval(py)  # pylint: disable=eval-used
        _trace_(dict(got_cell_of_py=bool(cell_of_py)))

        py_of_cell = format_as_py(cell_of_py)
        _trace_(dict(py_of_cell=py_of_cell))
        assert py_of_cell == py

        csp_of_cell = format_as_csp(cell_of_py)
        _trace_(dict(csp_of_cell=csp_of_cell))
        assert csp_of_cell == csp

        main.want_str_exc = str_exc
        cell_of_csp = eval_csp(csp)
        _trace_(dict(cell_of_csp=cell_of_csp))
        assert cell_of_csp == cell_of_py

    # Then switch up to test lots of brief Csp in place of a few verbose Python
    # and include raising Exception's

    else:

        try:

            main.want_str_exc = str_exc
            cell_of_csp = eval_csp(csp)
            _trace_(dict(cell_of_csp=bool(cell_of_csp)))
            assert not str_exc

        except SourceRepairHint as srh:

            str_srh = str(srh)
            _trace_(dict(str_srh=str_srh))
            assert str_srh == str_exc, (str_srh, str_exc)

            return

        except Exception:
            stderr_print("cspsh: Exception in Csp: {}".format(csp))

            raise

        py_of_cell = format_as_py(cell_of_csp)
        _trace_(dict(py_of_cell=py_of_cell))

        csp_of_cell = format_as_csp(cell_of_csp)
        _trace_(dict(csp_of_cell=csp_of_cell))
        assert csp_of_cell == csp

        cell_of_py = eval(py_of_cell)  # pylint: disable=eval-used
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
    for csp_line in csp_lines:

        # Join Csp lines til all ( [ { ⟨ marks closed by ) ] } ⟩ marks

        csp_laters.append(csp_line)
        csp_joined = "\n".join(csp_laters)

        splits = split_csp_source(csp_joined)
        (opened, closed) = balance_csp_splits(splits)
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
            ProcName("X")
            """
        ).strip()
    )

    # An EventSet collects Events

    csps.append("{coin, choc, toffee}")

    pys.append(
        textwrap.dedent(
            """
            EventSet(
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
                epilog=ProcName("X"),
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
                    epilog=ProcName("X"),
                ),
                Prong(
                    prolog=Event("toffee"),
                    epilog=ProcName("X"),
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
                            epilog=ProcName("X"),
                        ),
                        Prong(
                            prolog=Event("toffee"),
                            epilog=ProcName("X"),
                        ),
                    ),
                ),
            )
        """
        ).strip()
    )

    # Stepping through Events of an EventSet defines a Proc

    csps.append("VMCT = μ X : {coin, choc, toffee} • (coin → (choc → X | toffee → X))")

    pys.append(
        textwrap.dedent(
            """
            ProcDef(
                proc=ProcName("VMCT"),
                proc_body=SharpBody(
                    proc=ProcName("X"),
                    world=EventSet(
                        Event("coin"),
                        Event("choc"),
                        Event("toffee"),
                    ),
                    basic_body=Pocket(
                        pocketable=Prong(
                            prolog=Event("coin"),
                            epilog=Pocket(
                                pocketable=Fork(
                                    Prong(
                                        prolog=Event("choc"),
                                        epilog=ProcName("X"),
                                    ),
                                    Prong(
                                        prolog=Event("toffee"),
                                        epilog=ProcName("X"),
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

    A = B = C = {x, y, z}  # sets of events, variables denoting events

    X   # variables denoting processes
    Y

    αVMS = {coin, choc}
    αVMC = {in1p, in2p, small, large, out1p}


    # 1.1.1 Prefix, p.3

    (x → P)  # 'x then P'
    α(x → P) = αP  # provided x ∈ αP
    # x ∈ αP  # not till we knit set ops

    coin → STOP  # 1.1.1 X1  # Pdf speaks STOP↓αVMS as subscript
    (coin → (choc → (coin → (choc → STOP))))  # 1.1.1 X2

    αCTR = {up, right}
    CTR = (right → up → right → right → STOP)  # 1.1.1 X3

    P → Q  # no, need more source to knit
    x → y  # no, need more source to knit

    x → (y → STOP)


    # 1.1.2 Recursion, p.4

    αCLOCK = {tick}

    (tick → CLOCK)
    CLOCK = (tick → CLOCK)
    CLOCK = (tick → (tick → CLOCK))
    CLOCK = (tick → (tick → (tick → CLOCK)))  # tick → tick → tick → ... unbounded

    X = X
    F(X)
    X = F(X)
    μ X : A • F(X)
    μ X : A • F(X) = μ Y : A • F(Y)

    CLOCK = μ X : {tick} • (tick → X)  # 1.1.2 X1

    VMS = (coin → (choc → VMS))  # 1.1.2a X2
    VMS = μ X : {coin, choc} • (coin → (choc → X))  # 1.1.2b X2

    αCH5A = {in5p, out2p, out1p}
    CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3

    αCH5B = αCH5A
    αCH5B = {in5p, out2p, out1p}
    CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4


    # 1.1.3 Choice, p.7

    (x → P | y → Q)
    α(x → P | y → Q) = αP   # provided {x, y} ⊆ αP and αP = αQ
    # {x, y} ⊆ αP  # not till we knit set ops
    αP = αQ

    (up → STOP | right → right → up → STOP)  # 1.1.3 X1

    CH5C = in5p → (  # 1.1.3 X2
        out1p → out1p → out1p → out2p → CH5C
        | out2p → out1p → out2p → CH5A
    )
    # Pdf doesn't break sourcelines in Black style

    VMCT = μ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3

    VMC = (  # 1.1.3 X4
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

    P | Q  # no, need more source to knit
    (x → P | x → Q)  # no, need distinct guard names, got: x x
    (x → P | (y → Q | z → R))  # no, need a stronger knitter

    (x → P | y → Q | z → R)

    (x → P | y)  # no, need a stronger knitter
    (x → P) | (y → Q)  # no, need more source to knit
    (x → P) | y → Q  # no, need more source to knit

    A
    x:A

    (x:B → P(x))
    (x:B → P(x)) = (y:B → P(u))

    x:αP
    x:αRUN*A

    αRUN*A
    αRUN*A = A
    x:A → RUN*A
    RUN*A = (x:A → RUN*A)  # 1.1.3 X8

    (x:{e} → P(x)) = (e → P(e))

    (a → P | b → Q) = (x:B → R(x))
    B = {a, b}
    # (a → P | x:C → Q)  # not till we calc menu of x:C
    # R(x) = if x = a then P else Q  # not till we knit if-then-else

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

*               subscript                   RUN*A  # RUN sub A

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
