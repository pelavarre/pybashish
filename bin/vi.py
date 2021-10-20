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
    ZQ ZZ ⌃Zfg  => how to exit Vi Py
    ⌃C Up Down Right Left Space Delete Return  => natural enough
    0 ^ $ fx h l tx Fx Tx ; , |  => leap to column
    { }  => leap to paragraph
    j k G 1G H L M - + _ ⌃J ⌃N ⌃P  => leap to row, leap to line
    1234567890 Esc  => repeat, or don't
    ⌃F ⌃B ⌃E ⌃Y ⌃D ⌃U  => scroll rows
    \n  => toggle line numbers on and off

examples:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py
"""
# we do define the arcane ⌃L to redraw, but we don't mention it in the help
# we also don't mention ⌃D ⌃U till they stop raising NotImplementedError

# TODO:  b e w B E W { }  => leap to small word, large word, paragraph
# TODO:  splits words at r"[^ \t]+" and at r"[0-9A-Za-z_]+"


import argparse
import collections
import difflib
import inspect
import os
import select
import signal
import sys
import termios
import traceback
import tty


# Name some Terminal Output magic

ESC = "\x1B"  # Esc
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

    returncode = None
    try:
        editor.run_awhile()
    except SystemExit as exc:
        returncode = exc.code

        if editor.log:
            stderr_print(editor.log)

    # Flush output

    os.write(sys.stdout.fileno(), iobytearray)
    sys.stdout.flush()

    # Exit

    sys.exit(returncode)


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


#
# Edit a Buffer of Chars Fetched from a File
#


class TerminalNudgeIn(argparse.Namespace):
    """Collect keyboard input Chords"""

    def __init__(self, prefix=None, chords=None, suffix=None):

        self.prefix = prefix
        self.chords = chords
        self.suffix = suffix

    def format_echo_bytes(self):

        echo = b""

        if self.prefix is not None:
            echo += self.prefix
        if self.chords is not None:
            echo += self.chords
        if self.suffix is not None:
            echo += self.suffix

        return echo


TerminalReplyOut = collections.namedtuple(
    "TerminalReplyOut",
    "nudge, message".split(", "),
    defaults=(None, None),
)


class TerminalEditor:
    """Write through to the Terminal, but keep a copy"""

    def __init__(self, iobytearray):

        self.iobytearray = iobytearray
        self.log = None

        self.driver = None
        self.painter = None

        self.row = 0
        self.column = 0

        self.reply = TerminalReplyOut()

        chars = iobytearray.decode(errors="surrogateescape")
        lines = chars.splitlines(keepends=True)
        self.lines = lines
        self.top_row = 0
        self.set_number = None

        self.bot_by_chords = self._calc_bot_by_chords()
        self.more_by_chords = self._calc_more_by_chords()

        self.nudge = TerminalNudgeIn()
        self.arg1 = None
        self.arg2 = None

        self.doing_more = None
        self.done = None

        self.slip_choice = None
        self.slip_after = None
        self.slip_redo = None
        self.slip_undo = None
        # TODO: self.last_slip = instance of collections.namedtuple

        self.seeking_more = None
        self.seeking_column = None

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

                    if self.nudge != TerminalNudgeIn():
                        self.nudge.suffix += b"\x03"  # ETX, aka ⌃C, aka 3
                        self.send_reply_soon("cancelled")

                        self.nudge = TerminalNudgeIn()

                        continue

                    chord = b"\x03"  # ETX, aka ⌃C, aka 3

                bot = self.choose_bot(chord)
                if bot is not None:
                    self.call_bot(bot)

                    self.nudge = TerminalNudgeIn()

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

        # Pull from Self

        painter = self.painter

        lines = self.lines
        top_lines = lines[self.top_row :]

        str_reply = self.consume_reply()

        # Push into the Painter

        painter.top_line_number = 1 + self.top_row
        painter.bottom_line_number = 1 + len(lines)
        painter.set_number = self.set_number

        painter.cursor_row = self.row - self.top_row
        painter.cursor_column = self.column

        painter.paint_diffs(lines=top_lines, status=str_reply)

    def choose_bot(self, chord):
        """Join together zero or more Digits and then one or more other Chords"""

        prefix = self.nudge.prefix
        chords = self.nudge.chords
        suffix = self.nudge.suffix

        bot_by_chords = self.bot_by_chords
        more_by_chords = self.more_by_chords

        # Collect the Prefix

        if not chords:

            if (chord in b"123456789") or (prefix and (chord == b"0")):

                prefix_plus = chord if (prefix is None) else (prefix + chord)
                self.nudge.prefix = prefix_plus
                self.send_reply_soon()

                return None  # ask for Chords

        self.arg1 = int(prefix) if prefix else None
        assert self.get_arg1() >= 1

        # Collect the Chords

        if chords not in more_by_chords.keys():

            chords_plus = chord if (chords is None) else (chords + chord)
            self.nudge.chords = chords_plus
            self.send_reply_soon()

            if chords_plus in more_by_chords.keys():

                return None  # ask for Suffix

            self.arg2 = None

            # Call a Bot with 0 or 1 Args

            if chords_plus in bot_by_chords.keys():

                bot = bot_by_chords[chords_plus]

                return bot  # may be None, to ask for more Chords

            # Raise a NameError when no Bot found

            bot = bot_by_chords[None]  # commonly 'self.do_raise_name_error'

            return bot

        # Collect the Suffix

        assert suffix is None, (chords, chord, suffix)  # one Chord only
        self.nudge.suffix = chord
        self.send_reply_soon()

        self.arg2 = chord.decode(errors="surrogateescape")

        # Call a Bot with 2 Args

        bot = bot_by_chords[chords]
        assert bot is not None, (chords, chord)

        return bot

    def call_bot(self, bot):
        """Call the Bot once or more"""

        # Default to stop remembering the last Stepping Column

        self.seeking_more = None

        # Start calling

        self.done = 0
        while True:
            self.doing_more = None

            try:

                bot()
                self.clip_cursor_on_screen()
                self.log = None

            # Cancel calls on KeyboardInterrupt

            except KeyboardInterrupt:

                self.nudge.suffix += b"\x03"  # ETX, aka ⌃C, aka 3
                self.send_reply_soon("interrupted")
                self.log = None

                break

            # Stop calls on Exception

            except Exception as exc:

                name = type(exc).__name__
                str_exc = str(exc)
                message = "{}: {}".format(name, str_exc) if str_exc else name

                self.log = traceback.format_exc()

                self.send_reply_soon(message)
                self.painter.ring_bell_soon()

                break

            # Let the Bot take the Arg as a Count of Repetitions

            if self.doing_more:
                self.done += 1
                if self.done < self.get_arg1():

                    continue

            break

        # Help many Steps between Rows leave the choice of Column unmoved

        if not self.seeking_more:
            self.seeking_column = None

    def send_reply_soon(self, message=None):
        """Capture some Status now, to show with next Prompt"""

        nudge = self.nudge

        self.reply = TerminalReplyOut(nudge=nudge, message=message)

    def consume_reply(self):
        """Send Shout else Mention else Row, Column, Input, & Whisper"""

        reply = self.reply
        nudge = reply.nudge

        #

        row_number = 1 + self.row
        column_number = 1 + self.column

        echo_bytes = b"" if (nudge is None) else nudge.format_echo_bytes()
        str_echo = repr_vi_bytes(echo_bytes) if echo_bytes else ""

        str_message = str(reply.message) if reply.message else ""

        #

        str_reply = "{},{} {} {}".format(
            row_number, column_number, str_echo, str_message
        ).rstrip()

        # Consume the Status, before returning a formatted copy of it

        self.reply = TerminalReplyOut()

        return str_reply

    def pull_chord(self):
        """Block till the keyboard input Digit or Chord, else raise KeyboardInterrupt"""

        driver = self.driver

        chord = driver.getch()
        if chord == b"\x03":
            raise KeyboardInterrupt()

        return chord

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.arg1' times"""

        self.doing_more = True

    def continue_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        self.seeking_more = True

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
        self.require(before == after, before=before, after=after)

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

    def get_arg1(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        arg1 = self.arg1
        arg1 = default if (arg1 is None) else arg1

        return arg1

    def get_arg2(self, default=1):
        """Get the Bytes of the input Suffix past the input Chords"""

        arg2 = self.arg2
        assert arg2 is not None

        return arg2

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

    def require(self, truthy, **kwargs):
        """Fail fast, perhaps with details, else proceed"""

        if not truthy:
            if kwargs:
                raise KwArgsException(**kwargs)
            else:
                raise IndexError()

    #
    # Define keys for entering, pausing, exiting Vi Py
    #

    def do_c0_control_esc(self):  # Vim Esc
        """Cancel Digits Prefix"""

        arg1 = self.arg1
        painter = self.painter

        if arg1 is None:
            self.send_reply_soon("Esc pressed without Digits before it")
            painter.ring_bell_soon()

    def do_help_quit(self):  # Vim ⌃C
        """Say how to exit Vi Py"""

        self.send_reply_soon("Press ZQ to quit Vi Py without saving last changes")

    def do_raise_name_error(self):  # such as Esc, such as 'ZB'
        """Reply to a meaningless keyboard input Chord Sequence"""

        raise NameError()

    def do_repaint_soon(self):  # Vim ⌃L
        """Clear the screen and repaint every char, just before next Prompt"""

        painter = self.painter
        painter.repaint_soon()

    def do_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        driver = self.driver

        driver.__exit__(*ExcInfo())
        os.kill(os.getpid(), signal.SIGTSTP)
        driver.__enter__()

    def do_quit(self):  # Vim ZQ  # emacs kill-emacs
        """Lose last changes and quit"""

        returncode = 1 if self.iobytearray else None
        returncode = self.get_arg1(default=returncode)

        self.iobytearray[::] = b""

        sys.exit(returncode)

    def do_save_and_quit(self):  # Vim ZZ  # emacs save-buffers-kill-terminal
        """Save last changes and quit"""

        returncode = self.get_arg1(default=None)

        sys.exit(returncode)

    #
    # Flip switches
    #

    def do_set_invnumber(self):  # Vi Py \n
        """Toggle Line-in-File numbers in or out"""

        self.set_number = not self.set_number
        message = ":set number" if self.set_number else ":set nonumber"
        self.send_reply_soon(message)

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |  # emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        last_column = self.find_last_column()
        column = min(last_column, self.get_arg1() - 1)

        self.column = column

    def do_slip_dent(self):  # Vim ^
        """Leap to just past the Indent, but first Step Down if Arg"""

        if self.arg1:  # Vim squelches this
            self.send_reply_soon("Press {}_ to step down".format(self.arg1))

        self.slip_dent()

    def slip_dent(self):
        """Leap to the Column after the Indent"""

        text = self.copy_row()
        lstripped = text.lstrip()
        column = len(text) - len(lstripped)

        self.column = column

    def do_slip_first(self):  # Vim 0  # emacs move-beginning-of-line
        """Leap to the first Column in Row"""

        assert self.arg1 is None  # Vi Py takes no Digits before the Chord 0

        self.column = 0

    def do_slip_left(self):  # Vim h, Left  # emacs left-char, backward-char
        """Slip left one Column or more"""

        self.require(self.column)

        left = min(self.column, self.get_arg1())
        self.column -= left

    def do_slip_right(self):  # Vim l, Right  #  emacs right-char, forward-char
        """Slip Right one Column or more"""

        last_column = self.find_last_column()
        self.require(self.column < last_column)

        right = min(last_column - self.column, self.get_arg1())
        self.column += right

    #
    #
    #

    def do_slip_ahead(self):  # Vim Space
        """Slip right, then down"""

        last_column = self.find_last_column()
        last_row = self.find_last_row()

        if not self.done:
            self.require((self.column < last_column) or (self.row < last_row))

        if self.column < last_column:
            self.column += 1

            self.continue_do_loop()

        elif self.row < last_row:
            self.column = 0
            self.row += 1

            self.continue_do_loop()

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        if not self.done:
            self.require(self.row or self.column)

        if self.column:
            self.column -= 1

            self.continue_do_loop()

        elif self.row:
            self.row -= 1
            self.column = self.find_last_column()

            self.continue_do_loop()

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # Vim G, 1G  # emacs goto-line
        """Leap to last Row, else to a chosen Row"""

        last_row = self.find_last_row()

        row = min(last_row, self.get_arg1() - 1)
        row = last_row if (self.arg1 is None) else row

        self.row = row
        self.slip_dent()

    def do_step_down_dent(self):  # Vim +, Return
        """Step down a Row or more, but land just past the Indent"""

        self.step_down()
        self.slip_dent()

    def step_down(self):
        """Step down one Row or more"""

        last_row = self.find_last_row()

        self.require(self.row < last_row)
        down = min(last_row - self.row, self.get_arg1())

        self.row += down

    def do_step_down_minus_dent(self):  # Vim _
        """Leap to just past the Indent, but first Step Down if Arg"""

        self.step_down_minus()
        self.slip_dent()

    def step_down_minus(self):
        """Step down zero or more Rows, not one or more Rows"""

        down = self.get_arg1() - 1
        if down:
            self.arg1 -= 1  # mutate
            self.step_down()

    def do_step_max_low(self):  # Vim L
        """Leap to first Word of Bottom Row on Screen"""

        self.row = self.find_bottom_row()
        self.slip_dent()

    def do_step_max_high(self):  # Vim H
        """Leap to first Word of Top Row on Screen"""

        self.row = self.top_row
        self.slip_dent()

    def do_step_to_middle(self):  # Vim M
        """Leap to first Word of Middle Row on Screen"""

        self.row = self.find_middle_row()
        self.slip_dent()

    def do_step_up_dent(self):  # Vim -
        """Step up a Row or more, but land just past the Indent"""

        self.step_up()
        self.slip_dent()

    def step_up(self):
        """Step up one Row or more"""

        self.require(self.row)
        up = min(self.row, self.get_arg1())

        self.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_last_seek(self):  # Vim $  # emacs move-end-of-line
        """Leap to the last Column in Row, and keep seeking last Columns"""

        self.seeking_column = True
        self.step_down_minus()
        self.column = self.find_last_column()

        self.continue_column_seek()

    def do_step_down_seek(self):  # Vim j, ⌃J, ⌃N, Down  # emacs next-line
        """Step down one Row or more, but seek the current Column"""

        if self.seeking_column is None:
            self.seeking_column = self.column

        self.step_down()

        self.column = self.seek_column()
        self.continue_column_seek()

    def do_step_up_seek(self):  # Vim k, ⌃P, Up  # emacs previous-line
        """Step up a Row or more, but seek the current Column"""

        if self.seeking_column is None:
            self.seeking_column = self.column

        self.step_up()

        self.column = self.seek_column()
        self.continue_column_seek()

    def seek_column(self, column=True):
        """Begin seeking a Column, if not begun already"""

        last_column = self.find_last_column()

        if self.seeking_column is True:
            chosen_column = last_column
        else:
            chosen_column = min(last_column, self.seeking_column)

        return chosen_column

    #
    # Scroll to show more than one Screen of File
    #

    def do_scroll_ahead_some(self):  # Vim ⌃D
        """TODO: Scroll ahead some, just once or more"""

        raise NotImplementedError()

    def do_scroll_behind_some(self):  # Vim ⌃U
        """TODO: Scroll behind some, just once or more"""

        raise NotImplementedError()

    def scroll_ahead_some_once(self):
        """TODO: Scroll ahead some"""

        raise NotImplementedError()

    #
    # Scroll ahead or behind almost one Whole Screen of Rows
    #

    def do_scroll_ahead_much(self):  # Vim ⌃F
        """Scroll ahead much"""

        row = self.row
        top_row = self.top_row
        painter = self.painter

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        bottom_row = self.find_bottom_row()
        last_row = self.find_last_row()

        # Quit at last Row

        if top_row == last_row:
            if not self.done:
                self.send_reply_soon("at end of file")  # Vim squelches this

            return

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

        self.slip_dent()

        self.continue_do_loop()

    def do_scroll_behind_much(self):  # Vim ⌃B
        """Show the previous Screen of Rows"""

        row = self.row
        top_row = self.top_row
        painter = self.painter

        last_row = self.find_last_row()

        # Quit at top Row

        if not top_row:

            return

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

        self.slip_dent()

        self.continue_do_loop()

    #
    # Scroll ahead or behind one Row of Screen
    #

    def do_scroll_ahead_one(self):  # Vim ⌃E
        """Show the next Row of Screen"""

        row = self.row
        top_row = self.top_row

        last_row = self.find_last_row()

        # Quit at last Row

        if self.top_row == last_row:
            if not self.done:
                self.send_reply_soon("at end of file")  # Vim squelches this

            return

        # Scroll ahead one

        if top_row < last_row:
            top_row += 1
            if row < top_row:
                row = top_row

        self.top_row = top_row
        self.row = row

        self.slip_dent()

        self.continue_do_loop()

    def do_scroll_behind_one(self):  # Vim ⌃Y
        """Show the previous Row of Screen"""

        row = self.row
        top_row = self.top_row

        # Quit at top Row

        if not top_row:

            if not self.done:
                self.send_reply_soon("at start of file")  # Vim squelches this

            return

        # Scroll behind one

        if top_row:
            top_row -= 1

            self.top_row = top_row  # TODO: ugly mutate
            bottom_row = self.find_bottom_row()

            if row > bottom_row:
                row = bottom_row

        self.top_row = top_row
        self.row = row

        self.slip_dent()

        self.continue_do_loop()

    #
    # Search ahead for an empty line
    #

    def do_paragraph_ahead(self):
        """Step down over Empty Lines, then over Non-Empty Lines"""

        last_row = self.find_last_row()

        if self.done:
            if (self.row, self.column) == (last_row, self.find_last_column()):
                raise IndexError()

        while (self.row < last_row) and not self.find_last_column():
            self.row += 1
        while (self.row < last_row) and self.find_last_column():
            self.row += 1

        self.column = self.find_last_column()

        self.continue_do_loop()

    def do_paragraph_behind(self):

        if self.done:
            if (self.row, self.column) == (0, 0):
                raise IndexError()

        while self.row and not self.find_last_column():
            self.row -= 1
        while self.row and self.find_last_column():
            self.row -= 1

        self.column = 0

        self.continue_do_loop()

    #
    # Search ahead inside the Row for a single Char
    #

    def do_slip_index(self):  # Vim fx
        """Find Char to right in Row, once or more"""

        choice = self.get_arg2()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

        # TODO: Vi says f⎋ means f⌃C interrupted, not go find the ⎋ Esc Char
        # TODO: Vi says f⌃V means go find the ⌃V char, not prefix of f⌃V⎋
        # TODO: Vi says f⌃? means fail

    def do_slip_index_minus(self):  # Vim tx
        """Find Char to Right in row, once or more, but then slip left one Column"""

        choice = self.get_arg2()

        self.slip_choice = choice
        self.slip_after = -1
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index(self):
        """Find Char to Right in row, once or more"""

        last_column = self.find_last_column()
        text = self.copy_row()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_arg1()

        # Index each

        column = self.column

        for _ in range(count):

            self.require(column < last_column)
            column += 1

            right = text[column:].index(choice)
            column += right

        # Option to slip back one column

        if after:
            self.require(column)
            column -= 1

        self.column = column

    #
    # Search behind inside the Row for a single Char
    #

    def do_slip_rindex(self):  # Vim Fx
        """Find Char to left in Row, once or more"""

        choice = self.get_arg2()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def do_slip_rindex_plus(self):  # Vim Tx
        """Find Char to left in Row, once or more, but then slip right one Column"""

        choice = self.get_arg2()

        self.slip_choice = choice
        self.slip_after = +1
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex(self):
        """Find Char to left in Row, once or more"""

        last_column = self.find_last_column()
        text = self.copy_row()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_arg1()

        # R-Index each

        column = self.column

        for _ in range(count):

            self.require(column)
            column -= 1

            column = text[: (column + 1)].rindex(choice)

        # Option to slip right one column

        if after:

            self.require(column < last_column)
            column += 1

        self.column = column

    #
    # Repeat search inside the Row for a single Char
    #

    def do_slip_choice_redo(self):  # Vim ;
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

    def do_slip_choice_undo(self):  # Vim ,
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
    # Bind sequences of keyboard input Chords to Code
    #

    def _calc_bot_by_chords(self):
        """Define lots of keyboard input Chord Sequences"""

        bot_by_chords = dict()

        bot_by_chords[None] = self.do_raise_name_error

        bot_by_chords[b"\x02"] = self.do_scroll_behind_much  # STX, aka ⌃B, aka 2
        bot_by_chords[b"\x03"] = self.do_help_quit  # ETX, aka ⌃C, aka 3
        bot_by_chords[b"\x04"] = self.do_scroll_ahead_some  # EOT, aka ⌃D, aka 4
        bot_by_chords[b"\x05"] = self.do_scroll_ahead_one  # ENQ, aka ⌃E, aka 5
        bot_by_chords[b"\x06"] = self.do_scroll_ahead_much  # ACK, aka ⌃F, aka 6
        # BEL, aka ⌃F, aka 7 \a
        bot_by_chords[b"\x0A"] = self.do_step_down_seek  # LF, aka ⌃J, aka 10 \n
        # VT, aka ⌃K, aka 11 \v
        bot_by_chords[b"\x0C"] = self.do_repaint_soon  # FF, aka ⌃L, aka 12 \f
        bot_by_chords[b"\x0D"] = self.do_step_down_dent  # CR, aka ⌃M, aka 13 \r
        bot_by_chords[b"\x0E"] = self.do_step_down_seek  # SO, aka ⌃N, aka 14
        bot_by_chords[b"\x10"] = self.do_step_up_seek  # DLE, aka ⌃P, aka 16
        bot_by_chords[b"\x15"] = self.do_scroll_behind_some  # NAK, aka ⌃U, aka 15
        bot_by_chords[b"\x19"] = self.do_scroll_behind_one  # EM, aka ⌃Y, aka 25
        bot_by_chords[b"\x1A"] = self.do_sig_tstp  # SUB, aka ⌃Z, aka 26
        bot_by_chords[b"\x1B"] = self.do_c0_control_esc  # ESC, aka ⌃[, aka 27

        bot_by_chords[b"\x1B[A"] = self.do_step_up_seek  # ↑ Up Arrow
        bot_by_chords[b"\x1B[B"] = self.do_step_down_seek  # ↓ Down Arrow
        bot_by_chords[b"\x1B[C"] = self.do_slip_right  # → Right Arrow
        bot_by_chords[b"\x1B[D"] = self.do_slip_left  # ← Left Arrow

        bot_by_chords[b" "] = self.do_slip_ahead
        bot_by_chords[b"$"] = self.do_slip_last_seek
        bot_by_chords[b"+"] = self.do_step_down_dent
        bot_by_chords[b","] = self.do_slip_choice_undo
        bot_by_chords[b"-"] = self.do_step_up_dent

        bot_by_chords[b"0"] = self.do_slip_first

        bot_by_chords[b";"] = self.do_slip_choice_redo

        bot_by_chords[b"F"] = self.do_slip_rindex
        bot_by_chords[b"G"] = self.do_step
        bot_by_chords[b"H"] = self.do_step_max_high
        bot_by_chords[b"M"] = self.do_step_to_middle
        bot_by_chords[b"L"] = self.do_step_max_low
        bot_by_chords[b"T"] = self.do_slip_rindex_plus

        bot_by_chords[b"Z"] = None
        bot_by_chords[b"ZQ"] = self.do_quit
        bot_by_chords[b"ZZ"] = self.do_save_and_quit

        bot_by_chords[b"^"] = self.do_slip_dent
        bot_by_chords[b"_"] = self.do_step_down_minus_dent

        bot_by_chords[b"f"] = self.do_slip_index
        bot_by_chords[b"j"] = self.do_step_down_seek
        bot_by_chords[b"k"] = self.do_step_up_seek
        bot_by_chords[b"h"] = self.do_slip_left
        bot_by_chords[b"l"] = self.do_slip_right
        bot_by_chords[b"t"] = self.do_slip_index_minus

        bot_by_chords[b"z"] = None
        # bot_by_chords[b"zz"] = self.do_scroll_to_center

        bot_by_chords[b"{"] = self.do_paragraph_behind
        bot_by_chords[b"|"] = self.do_slip
        bot_by_chords[b"}"] = self.do_paragraph_ahead

        bot_by_chords[b"\\"] = None
        bot_by_chords[b"\\n"] = self.do_set_invnumber
        # TODO: stop occupying the personal \ Chord Sequences

        bot_by_chords[b"\x7F"] = self.do_slip_behind  # DEL, aka ⌃?, aka 127

        return bot_by_chords

    def _calc_more_by_chords(self):
        """Ask for more keyboard input Chord Sequences after choosing Code to run"""

        more_by_chords = dict()

        more_by_chords[b"F"] = 1
        more_by_chords[b"T"] = 1
        more_by_chords[b"f"] = 1
        more_by_chords[b"t"] = 1

        return more_by_chords


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

        self.write_soon = None

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

        self.write_soon = "\a"

    def paint_diffs(self, lines, status):
        """Write over the Rows of Chars on Screen"""

        tty = self.tty
        rows = self.rows
        columns = self.columns

        visibles = lines[: (rows - 1)]
        texts = list(_.splitlines()[0] for _ in visibles)

        write_soon = self.write_soon
        self.write_soon = None

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

        if write_soon:
            tty.write(write_soon)

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

        _ = exc_info

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
            # rep += " ⇥"  # ⇥ \u21E5 Rightward Arrows to Bar
            rep += " Tab"
        elif xx == 13:
            # rep += " ⏎"  # ⏎ \u23CE Return Symbol
            rep += " Return"
        elif xx == 27:
            # rep += " ⎋"  # ⎋ \u238B Broken Circle With Northwest Arrow
            rep += " Esc"
        elif xx == 127:
            # rep += " ⌫"  # ⌫ \u232B Erase To The Left
            rep += " Delete"
        elif chr_xx == " ":
            # rep += " ␢"  # ␢ \u2422 Blank Symbol
            # rep += " ␣"  # ␣ \u2423 Open Box
            rep += " Space"

        elif chr_xx.encode() in C0_CONTROL_STDINS:  # xx in 0x00..0x1F,0x7F
            rep += " ⌃" + chr(xx ^ 0x40)

        elif (chr_xx in "0123456789") and rep and (rep[-1] in "0123456789"):
            rep += chr_xx  # no Space between Digits in Prefix or Chords or Suffix

        else:
            rep += " " + chr_xx

    rep = rep.replace("Esc [ A", "Up")  # aka ↑ \u2191 Upwards Arrow
    rep = rep.replace("Esc [ B", "Down")  # aka ↓ \u2193 Downwards Arrow
    rep = rep.replace("Esc [ C", "Right")  # aka → \u2192 Rightwards Arrow
    rep = rep.replace("Esc [ D", "Left")  # aka ← \u2190 Leftwards Arrows

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

ExcInfo = collections.namedtuple(
    "ExcInfo", "type, value, traceback".split(", "), defaults=(None, None, None)
)


# deffed in many files  # missing from docs.python.org
class KwArgsException(Exception):
    """Raise a string of Key-Value Pairs"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __str__(self):
        kwargs = self.kwargs
        str_exc = ", ".join("{}={!r}".format(k, v) for (k, v) in kwargs.items())
        return str_exc


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
