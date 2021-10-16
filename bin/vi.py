#!/usr/bin/env python3

r"""
usage: vi.py [-h] [FILE]

read files, accept zero or more edits, write files

positional arguments:
  FILE        a file to edit

optional arguments:
  -h, --help  show this help message and exit

quirks:
  doesn't implement most of Vim
  defaults to read Stdin and write Stdout

examples:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py
"""

import argparse
import difflib
import inspect
import os
import select
import sys
import termios
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
assert len(BASIC_LATIN_STDINS) == 95 == (128 - 33) == (0x7F - 0x20)

X20_LOWER_MASK = 0x20
X20_UPPER_MASK = 0x20


def main(argv):
    """Run from the command line"""

    parse_vi_argv(argv)

    # Sponge up input

    inbytes = b""
    if not sys.stdin.isatty():
        with open("/dev/stdin", "rb") as reading:
            inbytes = reading.read()

    # Edit the input

    iobytearray = bytearray(inbytes)

    editor = TerminalEditor(iobytearray)
    editor.run_awhile()

    # Flush output

    os.write(sys.stdout.fileno(), iobytearray)
    sys.stdout.flush()


def parse_vi_argv(argv):
    """Convert a Vi Sys ArgV to an Args Namespace, or print some Help and quit"""

    parser = compile_argdoc(epi="quirks")
    parser.add_argument("FILE", nargs="?", help="a file to edit")

    exit_unless_doc_eq(parser)

    args = parser.parse_args(argv[1:])

    return args


class TerminalEditor:
    """Write through to the Terminal, but keep a copy"""

    def __init__(self, iobytearray):

        self.iobytearray = iobytearray

        self.quitting = None

        self.row = 0
        self.column = 0
        self.status = None
        self.shout = None

        chars = iobytearray.decode(errors="surrogateescape")
        lines = chars.splitlines(keepends=True)
        self.lines = lines
        self.top_row = 0
        self.set_number = None

        self.bots_by_stdin = self._calc_bots_by_stdin()
        self.digits = b""
        self.arg = None
        self.chords = b""

        self.slip_choice = None
        self.slip_after = None
        self.slip_redo = None
        self.slip_undo = None

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

            while not self.quitting:

                # Scroll, prompt, take input, react

                self.scroll()
                self.prompt()

                try:

                    chord = self.pull_chord()

                except KeyboardInterrupt:

                    chord = b"\x03"  # ETX, aka ⌃C, aka 3

                    if self.digits or self.chords:
                        self.chords += chord
                        self.status = self.format_echo(tag="cancelled")

                        self.digits = b""
                        self.chords = b""

                        continue

                self.react(chord)

    def scroll(self):
        """Scroll to place Cursor on Screen"""

        painter = self.painter
        row = self.row

        bottom_row = self.find_bottom_row()

        # Scroll to place Cursor on Screen

        if row < self.top_row:
            self.top_row = row
        else:
            if row > bottom_row:
                self.top_row = row - (painter.rows - 1) + 1

    def prompt(self):
        """Write over the Rows of Chars on Screen"""

        painter = self.painter

        # Tell Painter to repaint

        lines = self.lines
        top_lines = lines[self.top_row :]

        status = self.shout if self.shout else self.status

        self.status = None
        self.shout = None

        painter.top_line_number = 1 + self.top_row
        painter.bottom_line_number = 1 + len(lines)
        painter.set_number = self.set_number

        painter.cursor_row = self.row - self.top_row
        painter.cursor_column = self.column

        painter.repaint(lines=top_lines, status=status)

    def react(self, chord):
        """Interpret sequences of keyboard input chords"""

        bots_by_stdin = self.bots_by_stdin

        # Accept decimal digits as a prefix before any Chords

        if not self.chords:
            if (chord in b"123456789") or (self.digits and (chord == b"0")):
                self.digits += chord
                self.status = self.digits.decode()

                return

        digits = self.digits

        # Append the keyboard input Chord

        self.chords += chord

        chords = self.chords
        self.status = self.format_echo(tag=None)

        # Else find, call, and consume the Chord

        self.arg = int(digits) if digits else None
        self.chording_more = None

        if chords in bots_by_stdin.keys():
            bot = bots_by_stdin[chords]
        else:
            self.status = self.format_echo("meaningless")
            bot = self.ring_bell

        try:
            bot()
        except KeyboardInterrupt:
            self.chords += b"\x03"  # ETX, aka ⌃C, aka 3
            self.status = self.format_echo("cancelled as")
        except Exception as exc:
            self.status = self.format_echo(type(exc).__name__ + " in")
            self.ring_bell()

        self.digits = b""
        if not self.chording_more:
            self.chords = b""

    def format_echo(self, tag):
        """Echo keyboard input Digits and Chords"""

        digits = self.digits
        chords = self.chords

        status = repr(digits + chords)
        if tag:
            status = "{} {}".format(tag, status)

        return status

    def pull_chord(self):
        """Block till the keyboard input Digit or Chord, else raise KeyboardInterrupt"""

        driver = self.driver

        chord = driver.getch()
        if chord == b"\x03":
            raise KeyboardInterrupt()

        return chord

    def chord_more_now(self):
        """Repaint now and add another keyboard input chord now"""

        self.scroll()
        self.prompt()

        chord = self.pull_chord()
        self.chords += chord
        self.status = self.format_echo(tag=None)

        choice = chord.decode(errors="surrogateescape")

        return choice

    def chord_more_soon(self):
        """Add another keyboard input chord, after next Repaint"""

        self.chording_more = True

    def ring_bell(self):
        """Reject unwanted input"""

        painter = self.painter
        painter.ring_bell_soon()

    def help_quit(self):
        """Say how to exit Vi Py"""

        self.status = "Press ZQ to quit Vi Py without saving last changes" ""

    def quit(self):  # emacs kill-emacs
        """Lose last changes and quit"""

        self.iobytearray[::] = b""
        self.quitting = True

    def save_and_quit(self):  # emacs save-buffers-kill-terminal
        """Save last changes and quit"""

        self.quitting = True

    #
    # Flip switches
    #

    def set_invnumber(self):
        """Toggle Line-in-File numbers in or out"""

        self.set_number = not self.set_number
        self.status = ":set number" if self.set_number else ":set nonumber"

    #
    # Focus on one Line of a File of Lines
    #

    def count_columns_in_row(self):
        """Count columns in row"""

        line = self.lines[self.row]
        text = line.splitlines()[0]
        columns = len(text)

        return columns

    def count_rows_in_file(self):
        """Count rows in file"""

        rows = len(self.lines)

        return rows

    def find_bottom_row(self):
        """Find the Bottom Row on Screen"""

        painter = self.painter
        bottom_row = self.top_row + (painter.rows - 1) - 1

        return bottom_row

    def copy_row(self):
        """Get chars of columns in row"""

        line = self.lines[self.row]
        text = line.splitlines()[0]

        return text

    #
    # Say to "slip" is to place the Cursor in a Column of the Row
    #

    def slip(self):  # emacs goto-char
        """Go to first column, else to a chosen column"""

        arg = self.arg
        columns = self.count_columns_in_row()

        column = 0 if (arg is None) else (arg - 1)
        column = min(column, columns - 1)

        self.column = column

    def slip_choice_redo(self):
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        after = self.slip_after
        if not after:

            self.slip_redo()

        else:

            columns = self.count_columns_in_row()

            with_column = self.column
            try:

                if after < 0:
                    assert self.column < (columns - 1)
                    self.column += 1
                elif after > 0:
                    assert self.column
                    self.column -= 1

                self.slip_redo()

                assert self.column != with_column

            except Exception:
                self.column = with_column

                raise

    def slip_choice_undo(self):
        """Undo the last 'slip_index' or 'slip_rindex' once or more"""

        after = self.slip_after
        if not after:

            self.slip_undo()

        else:

            columns = self.count_columns_in_row()

            with_column = self.column
            try:

                if after < 0:
                    assert self.column
                    self.column -= 1
                elif after > 0:
                    assert self.column < (columns - 1)
                    self.column += 1

                self.slip_undo()

                assert self.column != with_column

            except Exception:
                self.column = with_column

                raise

    def slip_dent_plus(self):
        """Go to the column after the indent"""
        # silently ignore Arg

        text = self.copy_row()
        lstripped = text.lstrip()
        column = len(text) - len(lstripped)

        self.column = column

    def slip_first(self):  # emacs move-beginning-of-line
        """Leap to the first column in row"""

        assert not self.arg

        self.column = 0

    def slip_index_chord(self):
        """Find char to right in row, once or more"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index_chord_minus(self):
        """Find char to right in row, once or more, but then slip back one column"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = -1
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index(self):

        arg = self.arg
        columns = self.count_columns_in_row()
        text = self.copy_row()

        choice = self.slip_choice
        after = self.slip_after

        count = 1 if (arg is None) else arg

        # Index each

        column = self.column

        for _ in range(count):

            assert column < (columns - 1)
            column += 1

            right = text[column:].index(choice)
            column += right

        # Option to slip back one column

        if after:
            assert column
            column -= 1

        self.column = column

    def slip_last(self):  # emacs move-end-of-line, but to last, not beyond end
        """Leap to the last column in row"""
        # Vim says N'$' should mean (N-1)'j' '$'

        columns = self.count_columns_in_row()
        self.column = (columns - 1) if columns else 0  # goes beyond when line is empty

    def slip_left(self):  # emacs left-char, backward-char
        """Go left a column or more"""

        arg = self.arg

        assert self.column

        left = 1 if (arg is None) else arg
        left = min(left, self.column)

        self.column -= left

    def slip_more(self):
        """Go right, then down"""

        arg = self.arg

        columns = self.count_columns_in_row()
        rows = self.count_rows_in_file()
        assert (self.column < (columns - 1)) or (self.row < (rows - 1))

        ahead = 1 if (arg is None) else arg
        for _ in range(ahead):

            if self.column < (self.count_columns_in_row() - 1):
                self.column += 1
            elif self.row < (self.count_rows_in_file() - 1):
                self.column = 0
                self.row += 1
            else:
                break

    def slip_right(self):  # emacs right-char, forward-char
        """Go right a column or more"""

        arg = self.arg
        columns = self.count_columns_in_row()

        assert self.column < (columns - 1)

        right = 1 if (arg is None) else arg
        right = min(right, columns - 1 - self.column)

        self.column += right

    def slip_rindex_chord(self):
        """Find char to left in row, once or more"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex_chord_plus(self):
        """Find char to left in row, once or more, but then slip right one column"""

        choice = self.chord_more_now()

        self.slip_choice = choice
        self.slip_after = +1
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex(self):
        """Find char to left in row, once or more"""

        arg = self.arg
        columns = self.count_columns_in_row()
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

            assert column < (columns - 1)
            column += 1

        self.column = column

    def slip_rindex_plus(self):
        """Find char to left in row, once or more, but then also go column right once"""

        columns = self.count_columns_in_row()

        self.slip_rindex()

        assert self.column < (columns - 1)
        self.column += 1

    #
    # Say to "step" is to place the Cursor in a Line of the File
    #

    def step(self):  # emacs goto-line
        """Go to last row, else to a chosen row"""

        arg = self.arg
        rows = self.count_rows_in_file()

        row = (rows - 1) if (arg is None) else (arg - 1)
        row = min(row, rows - 1)

        self.row = row

    def step_down(self):  # emacs next-line
        """Go down a row or more"""

        arg = self.arg
        rows = self.count_rows_in_file()

        assert self.row < (rows - 1)

        down = 1 if (arg is None) else arg
        down = min(down, rows - 1 - self.row)

        self.row += down

    def step_up(self):  # emacs previous-line
        """Go up a row or more"""

        arg = self.arg

        assert self.row

        up = 1 if (arg is None) else arg
        up = min(up, self.row)

        self.row -= up

    #
    # Bind sequences of keyboard input Chords to Code
    #

    def _calc_bots_by_stdin(self):
        """Enlist some bots to serve many kinds of keystrokes"""

        bots_by_stdin = dict()

        bots_by_stdin[b"\x03"] = self.help_quit  # ETX, aka ⌃C, aka 3
        # bots_by_stdin[b"\x0C"] = self.repaint_every_char  # FF, aka ⌃L, aka 12

        bots_by_stdin[b"\x1B[A"] = self.step_up  # ↑ Up Arrow
        bots_by_stdin[b"\x1B[B"] = self.step_down  # ↓ Down Arrow
        bots_by_stdin[b"\x1B[C"] = self.slip_right  # → Right Arrow
        bots_by_stdin[b"\x1B[D"] = self.slip_left  # ← Left Arrow

        bots_by_stdin[b" "] = self.slip_more
        bots_by_stdin[b"$"] = self.slip_last
        bots_by_stdin[b","] = self.slip_choice_undo

        bots_by_stdin[b"0"] = self.slip_first

        bots_by_stdin[b";"] = self.slip_choice_redo

        bots_by_stdin[b"F"] = self.slip_rindex_chord
        bots_by_stdin[b"G"] = self.step
        bots_by_stdin[b"T"] = self.slip_rindex_chord_plus

        bots_by_stdin[b"^"] = self.slip_dent_plus

        bots_by_stdin[b"f"] = self.slip_index_chord
        bots_by_stdin[b"j"] = self.step_down
        bots_by_stdin[b"k"] = self.step_up
        bots_by_stdin[b"h"] = self.slip_left
        bots_by_stdin[b"l"] = self.slip_right
        bots_by_stdin[b"t"] = self.slip_index_chord_minus

        bots_by_stdin[b"|"] = self.slip

        bots_by_stdin[b"Z"] = self.chord_more_soon
        bots_by_stdin[b"ZQ"] = self.quit
        bots_by_stdin[b"ZZ"] = self.save_and_quit

        # TODO: stop occupying the \ Chord Sequences

        bots_by_stdin[b"\\"] = self.chord_more_soon
        bots_by_stdin[b"\\n"] = self.set_invnumber

        return bots_by_stdin

    def _scratch_space_for_sourcelines_coming_back_soon(self):

        _ = r"""

        bots_by_stdin[b"\x04"] = self._drop_next_char  # EOT, aka ⌃D, aka 4
        bots_by_stdin[b"\x07"] = self._ring_bell  # BEL, aka ⌃G, aka 7
        bots_by_stdin[b"\x08"] = self._drop_char  # BS, aka ⌃H, aka 8
        bots_by_stdin[b"\x0A"] = self._end_line  # LF, aka ⌃J, aka 10
        # FF, aka ⌃L, aka 12
        bots_by_stdin[b"\x0D"] = self._end_line  # CR, aka ⌃M, aka 13
        bots_by_stdin[b"\x0E"] = self._next_history  # SO, aka ⌃N, aka 14
        bots_by_stdin[b"\x10"] = self._previous_history  # DLE, aka ⌃P, aka 16
        # XON, aka ⌃Q, aka 17
        bots_by_stdin[b"\x12"] = self._reprint  # DC2, aka ⌃R, aka 18
        # XOFF, aka ⌃S, aka 19
        bots_by_stdin[b"\x15"] = self._drop_line  # NAK, aka ⌃U, aka 21
        bots_by_stdin[b"\x16"] = self._quoted_insert  # ACK, aka ⌃V, aka 22
        bots_by_stdin[b"\x17"] = self._drop_word  # ETB, aka ⌃W, aka 23

        bots_by_stdin[b"\x7F"] = self._drop_char  # DEL, classically aka ⌃?, aka 127
        # SUB, aka ⌃Z, aka 26
        # FS, aka ⌃\, aka 28

        """


class TerminalPainter:
    """Paint a Screen of Rows of Chars"""

    def __init__(self, tty):

        self.tty = tty

        fd = tty.fileno()
        self.fdtty = fd

        tty_size = os.get_terminal_size(fd)
        self.rows = tty_size.lines
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

    def ring_bell_soon(self):
        """Ring the bell at end of next Repaint"""

        self.soon = "\a"

    def repaint(self, lines, status):
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
            texts[index] = text[:columns]
        while len(texts) < (rows - 1):
            texts.append("~")
        if texts and (len(texts[-1]) >= columns):
            texts[-1] = texts[-1][:-1]  # TODO: test writes of Lower Right Corner

        for (index, text) in enumerate(texts[: len(visibles)]):
            str_line_number = self.format_as_line_number(index)
            texts[index] = str_line_number + text

        # Write the formatted chars

        tty.write(ED_2)
        tty.write(CUP_1_1)
        for (index, text) in enumerate(texts):
            tty.write(text + "\n\r")

        # Show status

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

            inputs = stdin.decode()

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
