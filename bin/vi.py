#!/usr/bin/env python3

r"""
usage: vi.py [-h] [FILE]

read files, accept zero or more edits, write files

positional arguments:
  FILE        a file to edit

optional arguments:
  -h, --help  show this help message and exit

quirks:
  defaults to read Stdin and write Stdout
  defines only the most basic keyboard input chords of Bash Less/ Vim
    ZQ ZZ  => how to exit Vi Py
    ⌃C ↑ ↓ → ← Space  => natural enough
    0 ^ $ fx h l tx Fx Tx ; , |  => leap to column
    j k G 1G H L M - + _ ⌃J ⌃M ⌃N ⌃P  => leap to row, leap to line
    1234567890  => repeat
    ⌃B ⌃E ⌃F ⌃Y  => scroll rows
    \n  => toggle line numbers on and off

examples:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py
"""
# we define ⌃L to redraw, yes, and don't mention it above, on purpose


import argparse
import difflib
import inspect
import os
import select
import sys
import termios
import traceback
import tty


# Name some Terminal Output magic

ESC = "\x1B"  # Escape
CSI = ESC + "["  # Control Sequence Introducer (CSI)
CUP_Y_X = CSI + "{};{}H"  # Cursor Position (CUP)
CUP_1_1 = CUP_Y_X.format(1, 1)  # Cursor Position (CUP)  # (1, 1) = Upper Left
ED_2 = CSI + "2J"  # Erase in Display (ED)  # 2 = Whole Screen

DECSC = ESC + "7"  # DEC Save Cursor
DECRC = ESC + "8"  # DEC Restore Cursor

_XTERM_ALT_ = CSI + "?1049h"
_XTERM_MAIN_ = CSI + "?1049l"

SMCUP = DECSC + _XTERM_ALT_  # Set-Mode Cursor-Positioning
RMCUP = ED_2 + _XTERM_MAIN_ + DECRC  # Reset-Mode Cursor-Positioning

_CURSES_INITSCR_ = SMCUP + ED_2 + CUP_1_1
_CURSES_ENDWIN_ = RMCUP


# Name some Terminal Input magic

C0_CONTROL_STDINS = set(chr(codepoint).encode() for codepoint in range(0x00, 0x20))
C0_CONTROL_STDINS.add(chr(0x7F).encode())
assert len(C0_CONTROL_STDINS) == 33 == (128 - 95) == ((0x20 - 0x00) + 1)

X40_CONTROL_MASK = 0x40

ORD_ESC = 0x1B
ESC_CHAR = chr(ORD_ESC)
ESC_STDIN = ESC_CHAR.encode()

BASIC_LATIN_STDINS = set(chr(codepoint).encode() for codepoint in range(0x20, 0x7F))
assert len(C0_CONTROL_STDINS | BASIC_LATIN_STDINS) == 128
assert len(BASIC_LATIN_STDINS) == 95 == (128 - 33) == (0x7F - 0x20)

X20_LOWER_MASK = 0x20
X20_UPPER_MASK = 0x20


#
# Run from the Command Line
#


def main(argv):
    """Run from the Command Line"""

    parse_vi_argv(argv)

    # Sponge up input

    inbytes = b""
    if not sys.stdin.isatty():
        with open("/dev/stdin", "rb") as reading:
            inbytes = reading.read()

    # Edit the input

    iobytearray = bytearray(inbytes)

    editor = TerminalEditor(iobytearray)
    try:
        editor.run_awhile()
    except SystemExit:
        if editor.log:
            stderr_print(editor.log)

    # Flush output

    os.write(sys.stdout.fileno(), iobytearray)
    sys.stdout.flush()


def parse_vi_argv(argv):
    """Convert a Vi Sys ArgV to an Args Namespace, or print some Help and quit"""

    parser = compile_argdoc(epi="quirks")
    parser.add_argument("file", metavar="FILE", nargs="?", help="a file to edit")

    exit_unless_doc_eq(parser)

    args = parser.parse_args(argv[1:])

    if args.file is not None:
        if args.file != "-":
            stderr_print(
                "vi.py: error: file '-' meaning '/dev/stdin' implemented, nothing else yet"
            )
            sys.exit(2)

    return args


class TerminalEditor:
    """Write through to the Terminal, but keep a copy"""

    def __init__(self, iobytearray):

        self.iobytearray = iobytearray
        self.log = None

        self.driver = None
        self.painter = None

        self.row = 0
        self.column = 0

        self.status_tag = None
        self.status_chords = None
        self.status_digits = None
        self.status_whisper = None
        self.status_shout = None
        # FIXME: self.status = instance of collections.namedtuple

        chars = iobytearray.decode(errors="surrogateescape")
        lines = chars.splitlines(keepends=True)
        self.lines = lines
        self.top_row = 0
        self.set_number = None

        self.bots_by_stdin = self._calc_bots_by_stdin()

        self.digits = b""
        self.arg = None

        self.chords = b""
        self.chording_more = None

        self.slip_choice = None
        self.slip_after = None
        self.slip_redo = None
        self.slip_undo = None
        # FIXME: self.last_slip = instance of collections.namedtuple

        self.stepping_column = None
        self.stepping_more = None
        # FIXME: self.last_step = instance of collections.namedtuple

    #
    # Work closely with one TerminalDriver and one TerminalPainter
    #

    def run_awhile(self):
        """Prompt, take input, react, repeat till quit"""

        # Repeat till quit

        tty = sys.stderr
        with TerminalDriver(tty) as driver:
            self.driver = driver
            self.painter = TerminalPainter(tty)

            while True:  # loop till SystemExit

                # Scroll, prompt, take input, react

                self.scroll()
                self.prompt()

                try:

                    chord = self.pull_chord()

                except KeyboardInterrupt:

                    chord = b"\x03"  # ETX, aka ⌃C, aka 3

                    if self.digits or self.chords:
                        self.chords += chord
                        self.send_status_soon(tag="cancelled")

                        self.digits = b""
                        self.chords = b""

                        continue

                self.react(chord)

    def scroll(self):
        """Scroll to place Cursor on Screen"""

        row = self.row
        painter = self.painter

        bottom_row = self.find_bottom_row()

        if row < self.top_row:
            self.top_row = row
        elif row > bottom_row:
            self.top_row = row - (painter.scrolling_rows - 1)

    def prompt(self):
        """Write over the Rows of Chars on Screen"""

        painter = self.painter

        lines = self.lines
        top_lines = lines[self.top_row :]

        status = self.consume_status()

        painter.top_line_number = 1 + self.top_row
        painter.bottom_line_number = 1 + len(lines)
        painter.set_number = self.set_number

        painter.cursor_row = self.row - self.top_row
        painter.cursor_column = self.column

        painter.paint_diffs(lines=top_lines, status=status)

    def react(self, chord):
        """Interpret sequences of keyboard input chords"""

        painter = self.painter
        bots_by_stdin = self.bots_by_stdin

        # Accept decimal digits as a prefix before any Chords

        if not self.chords:
            if (chord in b"123456789") or (self.digits and (chord == b"0")):
                self.digits += chord
                self.send_status_soon(tag=None)

                return

        digits = self.digits

        # Append the keyboard input Chord

        self.chords += chord

        chords = self.chords
        self.send_status_soon(tag=None)  # a la Vim :set showcmd

        # Else find, call, and consume the Chord

        self.arg = int(digits) if digits else None

        if chords in bots_by_stdin.keys():
            bot = bots_by_stdin[chords]
        else:
            self.send_status_soon("meaningless")
            bot = self.do_ring_bell

        self.chording_more = None
        self.stepping_more = None

        try:

            bot()
            self.clip_cursor_on_screen()
            if not self.chording_more:
                self.log = None

        except KeyboardInterrupt:

            self.chords += b"\x03"  # ETX, aka ⌃C, aka 3
            self.send_status_soon("interrupted")
            self.log = None

        except Exception as exc:

            type_exc_name = type(exc).__name__
            str_exc = str(exc)
            detailed_status = "{}: {}".format(type_exc_name, str_exc)
            status = detailed_status if str_exc else type_exc_name

            self.send_status_soon(status)
            painter.ring_bell_soon()

            self.log = traceback.format_exc()

        self.digits = b""
        if not self.chording_more:
            self.chords = b""
        if not self.stepping_more:
            self.stepping_column = None

    def send_status_soon(self, tag):
        """Capture some Status now, to show with next Prompt"""

        self.status_tag = tag

        self.status_digits = self.digits
        self.status_chords = self.chords

    def consume_status(self):
        """Mention Row, Column, Tag, Digits, and Chords"""

        tag = self.status_tag
        digits = self.status_digits
        chords = self.status_chords
        whisper = self.status_whisper
        shout = self.status_shout

        #

        row_number = 1 + self.row
        column_number = 1 + self.column

        digits_chords = b""
        if digits:
            digits_chords += digits
        if chords:
            digits_chords += chords

        echo = repr_vi_bytes(digits_chords) if digits_chords else ""

        str_tag = str(tag) if tag else ""

        #

        status = "{},{} {} {}".format(row_number, column_number, echo, str_tag).rstrip()
        if whisper:
            status = str(whisper)
        if shout:
            status = str(shout)

        #

        self.status_tag = None
        self.status_chords = None
        self.status_digits = None
        self.status_whisper = None
        self.status_shout = None

        return status

    def pull_chord(self):
        """Block till the keyboard input Digit or Chord, else raise KeyboardInterrupt"""

        driver = self.driver

        chord = driver.getch()
        if chord == b"\x03":
            raise KeyboardInterrupt()

        return chord

    def chord_more_now(self):
        """Add another keyboard input chord, but now, not soon"""

        self.scroll()
        self.prompt()

        chord = self.pull_chord()
        self.chords += chord
        self.status = self.send_status_soon(tag=None)

        choice = chord.decode(errors="surrogateescape")

        return choice

    def chord_more_soon(self):
        """Ask for another keyboard input Chord, after the next Prompt"""

        self.chording_more = True

    def break_do_loop(self):
        """Silently deny the keyboardist's demand for more repetition"""

        self.arg = None  # mutate  # FIXME: loop if Not break'ened

    #
    # Define keys for entering, pausing, exiting Vi Py
    #

    # TODO: shuffle these into place far below

    def do_help_quit(self):
        """Say how to exit Vi Py"""

        self.send_status_soon("Press ZQ to quit Vi Py without saving last changes")

        self.break_do_loop()

    def do_repaint_soon(self):
        """Clear the screen and repaint every char, just before next Prompt"""

        painter = self.painter
        painter.repaint_soon()

        self.break_do_loop()

    def do_ring_bell(self):
        """Reject unwanted input"""

        painter = self.painter
        painter.ring_bell_soon()

        self.break_do_loop()

    def do_sig_stop(self):

        raise NotImplementedError()

    def do_quit(self):  # emacs kill-emacs
        """Lose last changes and quit"""

        returncode = 1 if self.iobytearray else 0
        self.iobytearray[::] = b""

        sys.exit(returncode)

    def do_save_and_quit(self):  # emacs save-buffers-kill-terminal
        """Save last changes and quit"""

        sys.exit()

    #
    # Flip switches
    #

    def do_set_invnumber(self):
        """Toggle Line-in-File numbers in or out"""

        self.set_number = not self.set_number
        self.status_shout = ":set number" if self.set_number else ":set nonumber"

        self.break_do_loop()

    #
    # Focus on one Line of a File of Lines
    #

    def clip_cursor_on_screen(self):
        """Fail faster, like when a bug moves the Cursor out of the File"""

        row = self.row
        column = self.column

        rows = self.count_rows_in_file()
        columns = self.count_columns_in_row()

        # Keep the choice of Row and Column non-negative and in File

        before = (row, column)

        if not ((0 <= row < rows) or (row == rows == 0)):
            row = 0
        if not ((0 <= column < columns) or (column == columns == 0)):
            column = 0

        self.row = row
        self.column = column

        # After fixing it, assert we never got it wrong

        after = (row, column)
        assert before == after, (before, after)

    def copy_row(self):
        """Get chars of columns in row"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]

        return row_text

    def count_columns_in_row(self):
        """Count columns in row"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]  # "flat is better than nested"

        columns = len(row_text)

        return columns

    def count_rows_in_file(self):
        """Count rows in file"""

        rows = len(self.lines)

        return rows

    def find_bottom_row(self):
        """Find the Bottom Row on Screen, as if enough Rows to fill Screen"""

        painter = self.painter

        last_row = self.find_last_row()

        bottom_row = self.top_row + (painter.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def find_last_row(self):
        """Find the Last Row in File, else Row Zero when no Rows in File"""

        rows = len(self.lines)  # "flat is better than nested"

        last_row = (rows - 1) if rows else 0

        return last_row

    def find_last_column(self):
        """Find the Last Column in Row, else Column Zero when no Columns in Row"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]  # "flat is better than nested"

        columns = len(row_text)
        last_column = (columns - 1) if columns else 0

        return last_column

    def find_middle_row(self):
        """Find the Middle Row on Screen, of the Rows that carry Lines of File"""

        top_row = self.top_row
        bottom_row = self.find_bottom_row()
        rows_on_screen = bottom_row - top_row + 1

        middle = (rows_on_screen + 1) // 2  # match +1 bias in Vi's 'find_middle_row'
        middle_row = top_row + middle

        return middle_row

    #
    # Define keys for entering, pausing, exiting Vi Py
    #

    # TODO: move do_help_quit, do_repaint_soon, do_ring_bell, etc here

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        arg = self.arg
        last_column = self.find_last_column()

        column = 0 if (arg is None) else (arg - 1)
        column = min(column, last_column)

        self.column = column

    #

    def do_slip_choice_redo(self):
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        after = self.slip_after
        if not after:

            self.slip_redo()

        else:

            last_column = self.find_last_column()

            with_column = self.column
            try:

                if after < 0:
                    assert self.column < last_column
                    self.column += 1
                elif after > 0:
                    assert self.column
                    self.column -= 1

                self.slip_redo()

                assert self.column != with_column

            except Exception:
                self.column = with_column

                raise

    def do_slip_choice_undo(self):
        """Undo the last 'slip_index' or 'slip_rindex' once or more"""

        after = self.slip_after
        if not after:

            self.slip_undo()

        else:

            last_column = self.find_last_column()

            with_column = self.column
            try:

                if after < 0:
                    assert self.column
                    self.column -= 1
                elif after > 0:
                    assert self.column < last_column
                    self.column += 1

                self.slip_undo()

                assert self.column != with_column

            except Exception:
                self.column = with_column

                raise

    #

    def do_slip_dent(self):
        """Leap to the Column after the Indent"""
        # silently ignore Arg

        text = self.copy_row()
        lstripped = text.lstrip()
        column = len(text) - len(lstripped)

        self.column = column

    def do_slip_first(self):  # emacs move-beginning-of-line
        """Leap to the first Column in Row"""

        assert not self.arg

        self.column = 0

    #

    def do_slip_index_chord(self):
        """Find Char to right in Row, once or more"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def do_slip_index_chord_minus(self):
        """Find Char to Right in row, once or more, but then slip left one Column"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = -1
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index(self):
        """Find Char to Right in row, once or more"""

        arg = self.arg
        last_column = self.find_last_column()
        text = self.copy_row()

        choice = self.slip_choice
        after = self.slip_after

        count = 1 if (arg is None) else arg

        # Index each

        column = self.column

        for _ in range(count):

            assert column < last_column
            column += 1

            right = text[column:].index(choice)
            column += right

        # Option to slip back one column

        if after:
            assert column
            column -= 1

        self.column = column

    #

    def do_slip_ahead(self):
        """Slip right, then down"""

        arg = self.arg

        last_column = self.find_last_column()
        last_row = self.find_last_row()
        assert (self.column < last_column) or (self.row < last_row)

        ahead = 1 if (arg is None) else arg
        for _ in range(ahead):

            if self.column < self.find_last_column():
                self.column += 1
            elif self.row < self.find_last_row():
                self.column = 0
                self.row += 1
            else:
                break

    def do_slip_behind(self):
        """Slip left, then up"""

        arg = self.arg

        assert self.row or self.column

        behind = 1 if (arg is None) else arg
        for _ in range(behind):

            if self.column:
                self.column -= 1
            elif self.row:
                self.row -= 1
                self.column = self.find_last_column()
            else:
                break

    def do_slip_last(self):  # emacs move-end-of-line, but to last, not beyond end
        """Leap to the last Column in Row"""
        # FIXME: Vim says '$' should mean choose last col again in next row
        # FIXME: Vim says N'$' should mean (N-1)'j' '$'

        last_column = self.find_last_column()

        self.column = last_column

    def do_slip_left(self):  # emacs left-char, backward-char
        """Slip left one Column or more"""

        arg = self.arg

        assert self.column  # FIXME: raise IndexError for such constraints

        left = 1 if (arg is None) else arg
        left = min(left, self.column)

        self.column -= left

    def do_slip_right(self):  # emacs right-char, forward-char
        """Slip Right one Column or more"""

        arg = self.arg
        last_column = self.find_last_column()

        assert self.column < last_column

        right = 1 if (arg is None) else arg
        right = min(right, last_column - self.column)

        self.column += right

    #

    def do_slip_rindex_chord(self):
        """Find Char to left in Row, once or more"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def do_slip_rindex_chord_plus(self):
        """Find Char to left in Row, once or more, but then slip right one Column"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = +1
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex(self):
        """Find Char to left in Row, once or more"""

        arg = self.arg
        last_column = self.find_last_column()
        text = self.copy_row()

        choice = self.slip_choice
        after = self.slip_after

        count = 1 if (arg is None) else arg

        # R-Index each

        column = self.column

        for _ in range(count):

            assert column
            column -= 1

            column = text[: (column + 1)].rindex(choice)

        # Option to slip right one column

        if after:

            assert column < last_column
            column += 1

        self.column = column

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # emacs goto-line
        """Leap to last Row, else to a chosen Row"""

        arg = self.arg
        last_row = self.find_last_row()

        row = last_row if (arg is None) else (arg - 1)
        row = min(row, last_row)

        self.row = row
        self.step_clip_column()

    def do_step_down(self):  # emacs next-line
        """Step down a Row or more"""

        arg = self.arg
        last_row = self.find_last_row()

        assert self.row < last_row

        down = 1 if (arg is None) else arg
        down = min(down, last_row - self.row)

        self.row += down
        self.step_clip_column()

    def do_step_down_dent(self):
        """Step down a Row or more, but land just past the Indent"""

        self.do_step_down()
        self.do_slip_dent()

    def do_step_down_minus_dent(self):

        if self.arg and (self.arg > 1):
            self.arg -= 1  # mutate
            self.do_step_down()

        self.do_slip_dent()

    def do_step_max_low(self):
        """Leap to first Word of Bottom Row on Screen"""

        self.row = self.find_bottom_row()
        self.do_slip_dent()

    def do_step_max_high(self):
        """Leap to first Word of Top Row on Screen"""

        self.row = self.top_row
        self.do_slip_dent()

    def do_step_to_middle(self):
        """Leap to first Word of Middle Row on Screen"""

        self.row = self.find_middle_row()
        self.do_slip_dent()

    def do_step_up(self):  # emacs previous-line
        """Step up a Row or more"""

        arg = self.arg

        assert self.row

        up = 1 if (arg is None) else arg
        up = min(up, self.row)

        self.row -= up
        self.step_clip_column()

    def do_step_up_dent(self):
        """Step up a Row or more, but land just past the Indent"""

        self.do_step_up()
        self.do_slip_dent()

    def step_clip_column(self):
        """Restore Column when lost only by Stepping from Row to Row"""

        column = self.column
        last_column = self.find_last_column()

        self.stepping_more = True
        if not self.stepping_column:
            self.stepping_column = column

        stepping_column = self.stepping_column
        if stepping_column is not None:
            clipped_column = min(self.stepping_column, last_column)
        else:
            clipped_column = min(column, last_column)

        self.column = clipped_column

    #
    # Scroll to show more than one Screen of File
    #

    def do_half_screen_down(self):
        """FIXME"""

        raise NotImplementedError()

        if self.arg:
            self.do_screen_row_down()
        else:
            self.half_screen_down_once()

    def do_half_screen_up(self):
        """FIXME"""

        raise NotImplementedError()

        arg = self.arg
        reps = 1 if (arg is None) else arg

        for _ in range(reps):
            self.half_screen_up_once()

    def half_screen_down_once(self):
        """FIXME"""

        row = self.row
        top_row = self.top_row
        painter = self.painter

        last_row = self.find_last_row()

        old_cursor_row = row - top_row
        rows_per_half_screen = painter.scrolling_rows // 2

        # Choose new Top Row

        top_row += rows_per_half_screen
        top_row = min(top_row, last_row)

        self.top_row = top_row

        # Choose new Row and Column

        row = top_row + old_cursor_row
        if row > last_row:
            row = last_row

        self.row = row

        self.do_slip_dent()

    #

    # FIXME: def do scroll_ahead_lots, scroll_ahead_one, scroll_ahead_some
    # FIXME: def do scroll_behind_lots, scroll_behind_one, scroll_behind_some
    def do_screen_down(self):
        """Show some later Screen of Rows"""

        arg = self.arg
        reps = 1 if (arg is None) else arg

        for _ in range(reps):
            self.screen_down_once()

    def do_screen_up(self):
        """Show some earlier Screen of Rows"""
        # FIXME: diffs from Vim in case of G ⌃F ⌃B

        arg = self.arg
        reps = 1 if (arg is None) else arg

        for _ in range(reps):
            self.screen_up_once()

    def screen_down_once(self):
        """Show the next Screen of Rows"""

        row = self.row
        top_row = self.top_row
        painter = self.painter

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        bottom_row = self.find_bottom_row()
        last_row = self.find_last_row()

        # Step one Up if in Bottom Row already

        if (row == bottom_row) and (row != last_row):
            if row:
                row -= 1

        # Choose new Top Row

        if row == last_row:
            top_row = last_row
        else:
            top_row += rows_per_screen
            top_row = min(top_row, last_row)

        self.top_row = top_row

        # Choose new Row and Column

        if row < top_row:
            row = top_row

        self.row = row

        self.do_slip_dent()

    def screen_up_once(self):
        """Show the previous Screen of Rows"""

        row = self.row
        top_row = self.top_row
        painter = self.painter

        last_row = self.find_last_row()

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        # Step one Down if in Top Row already

        if row == top_row:
            if top_row < last_row:
                row += 1

        # Choose new Top Row

        if rows_per_screen >= top_row:
            top_row = 0
        else:
            top_row -= rows_per_screen

        self.top_row = top_row

        # Choose new Row and Column

        bottom_row = self.find_bottom_row()
        if row > bottom_row:
            self.row = bottom_row

        self.do_slip_dent()

    #

    def do_screen_row_down(self):
        """Show some later Rows of Screen"""

        last_row = self.find_last_row()
        if self.top_row == last_row:
            self.send_status_soon("scrolled to end of file")  # Vim squelches this

        arg = self.arg
        reps = 1 if (arg is None) else arg

        for _ in range(reps):
            self.screen_row_down_one()

    def do_screen_row_up(self):
        """Show some earlier Rows of Screen"""

        if not self.top_row:
            self.send_status_soon("scrolled to start of file")  # Vim squelches this

        arg = self.arg
        reps = 1 if (arg is None) else arg

        for _ in range(reps):
            self.screen_row_up_one()

    def screen_row_down_one(self):
        """Show the next Row of Screen"""

        row = self.row
        top_row = self.top_row

        last_row = self.find_last_row()

        if top_row < last_row:
            top_row += 1
            if row < top_row:
                row = top_row

        self.top_row = top_row
        self.row = row

    def screen_row_up_one(self):
        """Show the previous Row of Screen"""

        row = self.row
        top_row = self.top_row

        if top_row:
            top_row -= 1

            self.top_row = top_row  # TODO: ugly
            bottom_row = self.find_bottom_row()

            if row > bottom_row:
                row = bottom_row

        self.top_row = top_row
        self.row = row

    #
    # Bind sequences of keyboard input Chords to Code
    #

    def _calc_bots_by_stdin(self):
        """Enlist some bots to serve many kinds of keystrokes"""

        bots_by_stdin = dict()

        bots_by_stdin[b"\x02"] = self.do_screen_up  # STX, aka ⌃B, aka 2
        bots_by_stdin[b"\x03"] = self.do_help_quit  # ETX, aka ⌃C, aka 3
        bots_by_stdin[b"\x04"] = self.do_half_screen_down  # EOT, aka ⌃D, aka 4
        bots_by_stdin[b"\x05"] = self.do_screen_row_down  # ENQ, aka ⌃E, aka 5
        bots_by_stdin[b"\x06"] = self.do_screen_down  # ACK, aka ⌃F, aka 6
        # BEL, aka ⌃F, aka 7 \a
        bots_by_stdin[b"\x0A"] = self.do_step_down  # LF, aka ⌃J, aka 10 \n
        # VT, aka ⌃K, aka 11 \v
        bots_by_stdin[b"\x0C"] = self.do_repaint_soon  # FF, aka ⌃L, aka 12 \f
        bots_by_stdin[b"\x0D"] = self.do_step_down_dent  # CR, aka ⌃M, aka 13 \r
        bots_by_stdin[b"\x0E"] = self.do_step_down  # SO, aka ⌃N, aka 14
        bots_by_stdin[b"\x10"] = self.do_step_up  # DLE, aka ⌃P, aka 16
        bots_by_stdin[b"\x15"] = self.do_half_screen_up  # NAK, aka ⌃U, aka 15
        bots_by_stdin[b"\x19"] = self.do_screen_row_up  # EM, aka ⌃Y, aka 25

        bots_by_stdin[b"\x1B[A"] = self.do_step_up  # ↑ Up Arrow
        bots_by_stdin[b"\x1B[B"] = self.do_step_down  # ↓ Down Arrow
        bots_by_stdin[b"\x1B[C"] = self.do_slip_right  # → Right Arrow
        bots_by_stdin[b"\x1B[D"] = self.do_slip_left  # ← Left Arrow

        bots_by_stdin[b" "] = self.do_slip_ahead
        bots_by_stdin[b"$"] = self.do_slip_last
        bots_by_stdin[b"+"] = self.do_step_down_dent
        bots_by_stdin[b","] = self.do_slip_choice_undo
        bots_by_stdin[b"-"] = self.do_step_up_dent

        bots_by_stdin[b"0"] = self.do_slip_first

        bots_by_stdin[b";"] = self.do_slip_choice_redo

        bots_by_stdin[b"F"] = self.do_slip_rindex_chord
        bots_by_stdin[b"G"] = self.do_step
        bots_by_stdin[b"H"] = self.do_step_max_high
        bots_by_stdin[b"M"] = self.do_step_to_middle
        bots_by_stdin[b"L"] = self.do_step_max_low
        bots_by_stdin[b"T"] = self.do_slip_rindex_chord_plus

        bots_by_stdin[b"Z"] = self.chord_more_soon
        bots_by_stdin[b"ZQ"] = self.do_quit
        bots_by_stdin[b"ZZ"] = self.do_save_and_quit

        bots_by_stdin[b"^"] = self.do_slip_dent
        bots_by_stdin[b"_"] = self.do_step_down_minus_dent

        bots_by_stdin[b"f"] = self.do_slip_index_chord
        bots_by_stdin[b"j"] = self.do_step_down
        bots_by_stdin[b"k"] = self.do_step_up
        bots_by_stdin[b"h"] = self.do_slip_left
        bots_by_stdin[b"l"] = self.do_slip_right
        bots_by_stdin[b"t"] = self.do_slip_index_chord_minus

        bots_by_stdin[b"z"] = self.chord_more_soon
        # bots_by_stdin[b"zz"] = self.do_scroll_to_center

        bots_by_stdin[b"|"] = self.do_slip

        bots_by_stdin[b"\\"] = self.chord_more_soon
        bots_by_stdin[b"\\n"] = self.do_set_invnumber
        # TODO: stop occupying the \ Chord Sequences

        bots_by_stdin[b"\x7F"] = self.do_slip_behind  # DEL, aka ⌃?, aka 127

        return bots_by_stdin


class TerminalPainter:
    """Paint a Screen of Rows of Chars"""

    def __init__(self, tty):

        self.tty = tty

        fd = tty.fileno()
        self.fdtty = fd

        tty_size = os.get_terminal_size(fd)
        assert tty_size.lines
        assert tty_size.columns

        self.rows = tty_size.lines
        self.scrolling_rows = tty_size.lines - 1  # reserve last 1 line for Status
        self.columns = tty_size.columns

        self.top_line_number = 1
        self.bottom_line_number = 1
        self.set_number = None

        self.cursor_row = 0
        self.cursor_column = 0

        self.soon = None

    def format_as_line_number(self, index):
        """Format a Row Index on Screen as a Line Number of File"""

        if not self.set_number:

            return ""

        last_line_number = "{:3} ".format(self.bottom_line_number)
        width = len(last_line_number)

        line_number = self.top_line_number + index
        formatted = "{:3} ".format(line_number).rjust(width)

        return formatted

    def repaint_soon(self):
        """Repaint all the Chars when next asked to just paint Diffs"""

        pass  # no work to do here, till we change 'def repaint' to

    def ring_bell_soon(self):
        """Ring the bell after next painting Diffs"""

        self.soon = "\a"

    def paint_diffs(self, lines, status):
        """Write over the Rows of Chars on Screen"""

        tty = self.tty
        rows = self.rows
        columns = self.columns

        visibles = lines[: (rows - 1)]
        texts = list(_.splitlines()[0] for _ in visibles)

        soon = self.soon
        self.soon = None

        # Format chars to display

        for (index, text) in enumerate(texts):
            texts[index] = text
        while len(texts) < (rows - 1):
            texts.append("~")

        str_line_number = self.format_as_line_number(1)
        for (index, text) in enumerate(texts[: len(visibles)]):
            str_line_number = self.format_as_line_number(index)
            numbered_and_chopped = (str_line_number + text)[:columns]
            texts[index] = numbered_and_chopped

        # Write the formatted chars

        tty.write(ED_2)
        tty.write(CUP_1_1)
        for (index, text) in enumerate(texts):
            if len(text) < columns:
                tty.write(text + "\n\r")
            else:
                tty.write(text)  # depend on automagic "\n\r" after last tty column

        # Show status, inside the last Row
        # but don't write over the Lower Right Char  # TODO: test vs autoscroll

        str_status = "" if (status is None) else str(status)
        tty.write(str_status.ljust(columns - 1))

        # Place the cursor

        y = 1 + self.cursor_row
        x = 1 + len(str_line_number) + self.cursor_column
        tty.write(CUP_Y_X.format(y, x))

        # Ring the bell on demand

        if soon:
            tty.write(soon)

        # Flush it all now

        tty.flush()


class TerminalDriver:
    r"""
    Emulate a glass teletype at Stdio, such as the 1978 DEC VT100 Video Terminal

    Apply Terminal Input Magic to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc as themselves,
    not as SIGINT SIGINFO SIGQUIT etc

    Apply Terminal Output Magic to write the XTerm Alt Screen without Scrollback,
    in place of the XTerm Main Screen with Scrollback

    Compare Bash 'bind -p', Zsh 'bindkey', Bash 'stty -a', and Unicode-Org U0000.pdf

    Compare Bash 'vim' and 'less -FIXR'
    """

    def __init__(self, tty):

        self.tty = tty

        self.fdtty = None
        self.with_termios = None
        self.inputs = None

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.tty.flush()

        if self.tty.isatty():

            self.fdtty = self.tty.fileno()
            self.with_termios = termios.tcgetattr(self.fdtty)
            tty.setraw(self.fdtty, when=termios.TCSADRAIN)  # not TCSAFLUSH

            self.tty.write(_CURSES_INITSCR_)
            self.tty.flush()

        return self

    def __exit__(self, *exc_info):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        (_, exc, _) = exc_info

        self.tty.flush()

        if self.with_termios:

            self.tty.write(_CURSES_ENDWIN_)
            self.tty.flush()

            when = termios.TCSADRAIN
            attributes = self.with_termios
            termios.tcsetattr(self.fdtty, when, attributes)

    def getch(self):
        """Block to fetch next Char of Paste, next Keystroke, or empty Eof"""

        # Block to fetch next Keystroke, if no Paste already queued

        inputs = "" if (self.inputs is None) else self.inputs
        if not inputs:

            stdin = self._pull_stdin()

            if len(stdin) <= 1:

                return stdin

            inputs = stdin.decode(errors="surrogateescape")

        # Pick a CSI Esc [ sequence apart from more Paste

        if len(inputs) >= 3:
            if inputs[:2] == (ESC_CHAR + "["):

                stdin = inputs[:3].encode()
                self.inputs = inputs[3:]

                return stdin

        # Fetch next whole Char of Paste, such as
        # ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑  # Control Option Alt Shift Command, Left Right Down Up Arrows

        stdin = inputs[:1].encode()
        self.inputs = inputs[1:]

        return stdin

    def _pull_stdin(self):
        """Pull a burst of Paste, else one slow single Keystroke, else empty at Eof"""

        # Block to fetch one more byte
        # (or fetch no bytes at end of input when Stdin is not Tty)

        stdin = os.read(self.tty.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while line not closed
        # Trust no multibyte char encoding contains b"\r" or b"\n" (as per UTF-8)

        calls = 1
        while stdin and (b"\r" not in stdin) and (b"\n" not in stdin):

            if self.with_termios:
                if not self.kbhit():
                    break

            more = os.read(self.tty.fileno(), 1)
            if not more:
                assert not self.with_termios
                break

            stdin += more
            calls += 1

        assert calls <= len(stdin) if self.with_termios else (len(stdin) + 1)

        return stdin

    def kbhit(self):
        """Wait till next Keystroke, or next burst of Paste pasted"""

        rlist = [self.tty]
        wlist = list()
        xlist = list()
        timeout = 0
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_) = selected

        if rlist_ == rlist:
            return True


def repr_vi_bytes(xxs):
    """Echo keyboard input without asking people to memorise b'\a\b\t\n\v\f\r'"""

    rep = ""
    for xx in xxs:
        chr_xx = chr(xx)

        if xx == 9:
            rep += " Tab"
        elif xx == 13:
            rep += " Return"
        elif xx == 27:
            rep += " Escape"
        elif xx == 127:
            rep += " Delete"
        elif chr_xx == " ":
            rep += " Space"
        elif chr_xx.encode() in C0_CONTROL_STDINS:  # xx in 0x00..0x1F,0x7F
            rep += " ⌃" + chr(xx ^ 0x40)
        elif (chr_xx in "0123456789") and rep and (rep[-1] in "0123456789"):
            rep += chr_xx
        else:
            rep += " " + chr_xx

    _ = 0x0C  # Black Python style enforces Uppercase Hex in this sourceline

    rep = rep.replace("Escape [ A", "Up")
    rep = rep.replace("Escape [ B", "Down")
    rep = rep.replace("Escape [ C", "Right")
    rep = rep.replace("Escape [ D", "Left")

    rep = rep.strip()

    return rep  # such as '⌃L' at FF, aka ⌃L, aka 12, aka '\f'


#
# List the Vim idioms active while testing Vi Py for compatibility with Vim
#

_VIMRC_ = r"""

" ~/.vimrc


" Lay out Spaces and Tabs

:set softtabstop=4 shiftwidth=4 expandtab
autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab

:set background=light


" Configure Vim

:syntax on

:set ignorecase
:set nowrap

:set hlsearch

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:set ruler  " not inferred from :set ttyfast at Mac
:set showcmd  " not inferred from :set ttyfast at Linux or Mac


" Add keys (without redefining keys)
" n-nore-map = map Normal (non insert) Mode and don't recurse through other remaps

" \ Esc => cancel the :set hlsearch highlighting of all search hits on screen
:nnoremap <Bslash><esc> :noh<return>

" \ e => reload, if no changes not-saved
:nnoremap <Bslash>e :e<return>

" \ i => toggle ignoring case in searches, but depends on :set nosmartcase
:nnoremap <Bslash>i :set invignorecase<return>

" \ m => mouse moves cursor
" \ M => mouse selects zigzags of chars to copy-paste
:nnoremap <Bslash>m :set mouse=a<return>
:nnoremap <Bslash>M :set mouse=<return>

" \ n => toggle line numbers
:nnoremap <Bslash>n :set invnumber<return>

" \ w => delete the trailing whitespace from each line (not yet from file)
:nnoremap <Bslash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

" £ => insert # instead, because Shift+3 at UK/US Keyboards
:abbrev £ #

" copied from:  git clone https://github.com/pelavarre/pybashish.git


"""


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def compile_argdoc(epi, drop_help=None):
    """Construct the 'argparse.ArgumentParser' with Epilog but without Arguments"""

    f = inspect.currentframe()
    module = inspect.getmodule(f.f_back)
    module_doc = module.__doc__

    prog = module_doc.strip().splitlines()[0].split()[1]

    description = list(
        _ for _ in module_doc.strip().splitlines() if _ and not _.startswith(" ")
    )[1]

    epilog_at = module_doc.index(epi)
    epilog = module_doc[epilog_at:]

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=not drop_help,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    return parser


# deffed in many files  # missing from docs.python.org
def exit_unless_doc_eq(parser):
    """Exit nonzero, unless __main__.__doc__ equals "parser.format_help()" """

    f = inspect.currentframe()
    module = inspect.getmodule(f.f_back)
    module_doc = module.__doc__
    module_file = f.f_back.f_code.co_filename  # more available than 'module.__file__'

    # Fetch the two docs

    got_doc = module_doc.strip()

    with_columns = os.getenv("COLUMNS")
    os.environ["COLUMNS"] = str(89)  # Black promotes 89 columns per line
    try:
        want_doc = parser.format_help()
    finally:
        if with_columns is None:
            os.environ.pop("COLUMNS")
        else:
            os.environ["COLUMNS"] = with_columns

    # Ignore Line-Break's jittering across Python Versions

    (alt_got, alt_want) = (got_doc, want_doc)
    if sys.version_info[:3] < (3, 9, 6):
        alt_got = join_first_paragraph(got_doc)
        alt_want = join_first_paragraph(want_doc)

    # Count differences

    got_file = module_file
    got_file = os.path.split(got_file)[-1]
    got_file = "./{} --help".format(got_file)

    want_file = "argparse.ArgumentParser(..."

    diff_lines = list(
        difflib.unified_diff(
            a=alt_got.splitlines(),
            b=alt_want.splitlines(),
            fromfile=got_file,
            tofile=want_file,
        )
    )

    # Exit if differences, but print them first

    if diff_lines:

        lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
        stderr_print("\n".join(lines))

        sys.exit(1)  # trust caller to log SystemExit exceptions well


# deffed in many files
def join_first_paragraph(doc):
    """Join by single spaces all the leading lines up to the first empty line"""

    index = (doc + "\n\n").index("\n\n")
    lines = doc[:index].splitlines()
    chars = " ".join(_.strip() for _ in lines)
    alt = chars + doc[index:]

    return alt


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
