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
  hides eggs at:  Esc ⌃C \n Qvi⌃M 123Esc 123⌃C f⌃C 9^ G⌃F⌃F G⌃F⌃E 1G⌃Y ; ,

demos:
  ZQ ZZ ⌃Zfg  => how to exit Vi Py
  ⌃C Up Down Right Left Space Delete Return  => natural enough
  0 ^ $ fx h l tx Fx Tx ; , |  => leap to column
  b e w B E W { }  => leap across small word, large word, paragraph
  j k G 1G H L M - + _ ⌃J ⌃N ⌃P  => leap to row, leap to line
  1234567890 Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y ⌃D ⌃U  => scroll rows
  \n  => toggle line numbers on and off
  ⌃L  => toggle more lag on and off

examples:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py -  # demo ZQ, etc
  cat bin/vi.py |bin/vi.py - |grep import  # demo ZQ vs ZZ
"""
# we do define the arcane ⌃L to redraw, but we don't mention it in the help
# we also don't mention ⌃D ⌃U till they stop raising NotImplementedError


import argparse
import difflib
import inspect
import os
import select
import signal
import string
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

        # TODO: log keystrokes interpreted before exit, or dropped by exit

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
    """Split up the Terminal Keyboard Chords of one Input"""

    def __init__(self, prefix=None, chords=None, suffix=None):

        self.prefix = prefix
        self.chords = chords
        self.suffix = suffix

    def append(self, chords):
        """Collect next Chord into Suffix, like after collecting Prefix and Chords"""

        suffix = b"" if (self.suffix is None) else self.suffix
        suffix += chords

        self.suffix = suffix

    def getch(self):
        """Echo input, in order"""

        echo = b""

        if self.prefix is not None:
            echo += self.prefix
        if self.chords is not None:
            echo += self.chords
        if self.suffix is not None:
            echo += self.suffix

        return echo


class TerminalReplyOut(argparse.Namespace):
    """Collect things to say on the side, apart from main Output, in reply to Input"""

    def __init__(self, nudge=None, message=None):

        self.nudge = nudge
        self.message = message

    # 'class TerminalReplyOut' could become an immutable 'collections.namedtuple'
    # because Jun/2018 Python 3.7 can say '._defaults=(None, None),'


class TerminalEditor:
    """Write through to the Terminal, but keep a copy"""

    def __init__(self, iobytearray):

        # Capture arg

        self.iobytearray = iobytearray  # send mutations back to caller

        chars = iobytearray.decode(errors="surrogateescape")
        lines = chars.splitlines(keepends=True)
        self.lines = lines  # edit a copy of a File of Encoded Chars

        # Layer over a Terminal I/O Stack

        self.log = None  # capture Python Tracebacks

        self.terminal = None  # place a Terminal I/O Stack below

        self.row = 0  # point the Screen Cursor to a Row of File
        self.column = 0  # point the Screen Cursor to a Column of File

        self.top_row = 0  # scroll through more Lines than fit on Screen
        self.injecting_more_lag = None  # inject more Lag or not
        self.showing_line_number = None  # show Line Numbers or not

        self.bots_by_chords = self._vim_bots_by_chords_()  # map Keyboard Inputs to Code

        self.nudge = TerminalNudgeIn()  # split the Chords of one Keyboard Input
        self.arg1 = None  # take the Prefix Bytes as an Int of Decimal Digits
        self.arg2 = None  # take the Suffix Bytes as one Encoded Char

        self.sending_bell = None  # ring Bell after writing some Prompt's
        self.reply = TerminalNudgeIn()  # declare an empty Nudge
        self.do_reopen_vi()  # start with a warmer welcome, not a cold empty Nudge

        # Define Keyboard Input to walk Vim-like State Machines inside this Editor

        self.doing_more = None  # take the Arg1 as a Count of Repetition's
        self.done = None  # count the Repetition's completed before now

        self.slip_choice = None  # find Char in Row
        self.slip_after = None  # slip off by one Column after finding Char
        self.slip_redo = None  # find later Char
        self.slip_undo = None  # find earlier Char

        self.seeking_more = None  # remembering the Seeking Column into next Nudge
        self.seeking_column = None  # leap to a Column after changing Row

        # TODO: less sourcelines inside "def __init__"

    #
    # Work closely with one TerminalDriver and one TerminalPainter
    #

    def run_awhile(self):
        """Prompt, take input, react, repeat till quit"""

        # Layer Terminal Editor > TerminalPainter > TerminalShadow > TerminalDriver

        stdio = sys.stderr
        with TerminalDriver(terminal=stdio) as driver:
            shadow = TerminalShadow(terminal=driver)
            terminal = TerminalPainter(terminal=shadow)
            self.terminal = terminal

            # Repeat till quit

            while True:  # loop till SystemExit

                # Scroll, prompt, take input, react

                self.scroll()
                self.prompt()

                try:

                    chord = terminal.getch()

                except KeyboardInterrupt:

                    if self.nudge != TerminalNudgeIn():
                        self.nudge.append(b"\x03")  # ETX, aka ⌃C, aka 3
                        self.send_reply_soon("Cancelled")  # 123⌃C Egg, f⌃C Egg, etc

                        self.nudge = TerminalNudgeIn()

                        continue

                    chord = b"\x03"  # ETX, aka ⌃C, aka 3

                bot = self.choose_bot(chord)
                if bot is not None:
                    self.call_bot(bot)  # reply to one whole Nudge

                    self.nudge = TerminalNudgeIn()  # consume the whole Nudge

    def scroll(self):
        """Scroll to place Cursor on Screen"""

        row = self.row
        terminal = self.terminal

        bottom_row = self.find_bottom_row()

        if row < self.top_row:
            self.top_row = row
        elif row > bottom_row:
            self.top_row = row - (terminal.scrolling_rows - 1)

    def prompt(self):
        """Write over the Rows of Chars on Screen"""

        # Pull from Self

        terminal = self.terminal

        lines = self.lines
        top_lines = lines[self.top_row :]
        str_reply = self.consume_reply()

        injecting_more_lag = self.injecting_more_lag
        sending_bell = self.sending_bell

        # Push into the Terminal

        terminal.top_line_number = 1 + self.top_row
        terminal.last_line_number = 1 + len(lines)
        terminal.showing_line_number = self.showing_line_number

        terminal.cursor_row = self.row - self.top_row
        terminal.cursor_column = self.column

        # Choose more or less Accuracy & Lag

        if injecting_more_lag or sending_bell:
            terminal._reopen_terminal_()

        terminal.write_screen(lines=top_lines, status=str_reply)

        if sending_bell:
            self.sending_bell = None
            terminal.write_bell()

        terminal.flush()

    def choose_bot(self, chord):
        """Accept one Keyboard Input into Prefix, into main Chords, or as Suffix"""

        prefix = self.nudge.prefix
        chords = self.nudge.chords

        bots_by_chords = self.bots_by_chords

        assert self.nudge.suffix is None, (chords, chord)  # one Chord only

        # Accept a Prefix of Digits

        if not chords:
            if (chord in b"123456789") or (prefix and (chord == b"0")):

                prefix_plus = chord if (prefix is None) else (prefix + chord)
                self.nudge.prefix = prefix_plus
                self.send_reply_soon()  # show Prefix a la Vim ':set showcmd'

                return None  # ask for more Prefix, else for main Chords

        self.arg1 = int(prefix) if prefix else None
        assert self.get_arg1() >= 1

        # Accept one or more Chords

        bots = bots_by_chords.get(chords)
        if not (bots and (len(bots) != 1)):

            chords_plus = chord if (chords is None) else (chords + chord)
            self.nudge.chords = chords_plus
            self.send_reply_soon()  # Chords of Vim ':set showcmd'

            default_bots = bots_by_chords[None]  # such as 'self.do_raise_name_error'

            bots_plus = bots_by_chords.get(chords_plus, default_bots)
            if bots_plus is None:

                return None  # ask for more Chords

            if bots_plus and (len(bots_plus) != 1):

                return None  # ask for Suffix

            self.arg2 = None

            # Call a Bot with or without Prefix, and without Suffix

            bot = bots_plus[-1]
            assert bot is not None, (chords, chord)

            return bot

        # Accept one last Chord as the Suffix

        suffix = chord
        self.nudge.suffix = suffix
        self.send_reply_soon()  # more than Vim ':set showcmd'

        self.arg2 = suffix.decode(errors="surrogateescape")

        # Call a Bot with Suffix, but with or without Prefix

        bot = bots[-1]
        assert bot is not None, (chords, chord)

        return bot

    def call_bot(self, bot):
        """Call the Bot once or more, in reply to one Terminal Nudge In"""

        # Default to stop remembering the last Seeking Column

        self.seeking_more = None

        # Start calling

        self.done = 0
        while True:
            self.doing_more = None

            try:

                bot()
                self.keep_cursor_on_file()
                self.log = None

            # Cancel calls on KeyboardInterrupt

            except KeyboardInterrupt:

                self.nudge.append(b"\x03")  # ETX, aka ⌃C, aka 3
                self.send_reply_soon("Interrupted")  # TODO: find this Egg
                self.log = None

                break

            # Stop calls on Exception

            except Exception as exc:

                name = type(exc).__name__
                str_exc = str(exc)
                message = "{}: {}".format(name, str_exc) if str_exc else name

                self.log = traceback.format_exc()

                self.send_reply_soon(message)  # Egg of NotImplementedError
                self.send_bell_soon()

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

        echo_bytes = b"" if (nudge is None) else nudge.getch()
        str_echo = repr_vi_bytes(echo_bytes) if echo_bytes else ""

        str_message = str(reply.message) if reply.message else ""

        #

        str_reply = "{},{}  {}  {}".format(
            row_number, column_number, str_echo, str_message
        ).rstrip()

        # Consume the Status, before returning a formatted copy of it

        self.reply = TerminalReplyOut()

        return str_reply

    def send_bell_soon(self):
        """Capture some Status now, to show with next Prompt"""

        self.sending_bell = True

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.arg1' times"""

        self.doing_more = True

    def continue_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        self.seeking_more = True

    #
    # Focus on one Line of a File of Lines
    #

    def find_column_in_charsets(self, charsets):
        """Return the Index of the first CharSet containing Column Char, else -1"""

        chars = self.get_column_char()  # may be empty
        chars = chars if chars else " "

        for (index, charset) in enumerate(charsets):
            if chars in charset:

                return index

        return -1

    def get_column_char(self):
        """Get the one Char at the Column in the Row beneath the Cursor"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]  # "flat is better than nested"
        chars = row_text[self.column :][:1]

        return chars  # 0 or 1 chars

    def get_row_text(self):
        """Get Chars of Columns in Row beneath Cursor"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]

        return row_text

    def count_columns_in_row(self):
        """Count Columns in Row beneath Cursor"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]  # "flat is better than nested"

        columns = len(row_text)

        return columns

    def count_rows_in_file(self):
        """Count Rows in Buffer of File"""

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

        terminal = self.terminal

        last_row = self.find_last_row()

        bottom_row = self.top_row + (terminal.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def find_last_row(self):
        """Find the last Row in File, else Row Zero when no Rows in File"""

        rows = len(self.lines)  # "flat is better than nested"

        last_row = (rows - 1) if rows else 0

        return last_row

    def find_last_column(self):
        """Find the last Column in Row, else Column Zero when no Columns in Row"""

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

    def keep_cursor_on_file(self):
        """Fail faster, like when some Bug shoves the Cursor off of Buffer of File"""

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
        self.check(before == after, before=before, after=after)

    def check(self, truthy, **kwargs):
        """Fail fast, perhaps with details, else proceed"""

        if not truthy:
            if kwargs:
                raise KwArgsException(**kwargs)
            else:
                raise IndexError()

    #
    # Define keys for entering, pausing, exiting Vi Py
    #

    def do_help_quit(self):  # Vim ⌃C
        """Suggest ZQ to quit Vi Py"""

        self.send_reply_soon("Press ZQ to lose changes and quit Vi Py")  # ⌃C Egg

    def do_c0_control_esc(self):  # Vim Esc
        """Cancel Digits Prefix, else suggest ZZ to quit Vi Py"""

        arg1 = self.arg1

        if arg1 is not None:
            self.send_reply_soon("Escaped")  # 123 Esc Egg, etc
        else:
            self.send_reply_soon("Press ZZ to save changes and quit Vi Py")  # Esc Egg
            self.send_bell_soon()

    def do_redraw(self):  # Vim ⌃L
        """Toggle betwene more and less Lag (vs Vim injects lots of Lag exactly once)"""

        injecting_more_lag = not self.injecting_more_lag
        self.injecting_more_lag = injecting_more_lag

        message = ":set _lag_" if injecting_more_lag else ":set no_lag_"
        self.send_reply_soon(message)

    def do_give_more_status(self):  # Vim ⌃G
        """Toggle betwene more and less Lag (vs Vim injects lots of Lag exactly once)"""

        injecting_more_lag = self.injecting_more_lag

        message = ":set _lag_" if injecting_more_lag else ":set no_lag_"
        self.send_reply_soon(message)

        # TODO: echo $(whoami)@$(hostname):$(pwd)/

    def do_reopen_vi(self):  # Vim Q v i Return  # not Ex Mode from last century
        """Accept Q v i Return without ringing the bell"""

        nudge = TerminalNudgeIn(chords=b"Qvi\x0D")  # CR, aka ⌃M, aka 13 \r
        message = "Would you like to play a game?"

        self.reply = TerminalReplyOut(nudge=nudge, message=message)

    def do_raise_name_error(self):  # such as Esc, such as 'ZB'
        """Reply to meaningless Keyboard Input"""

        raise NameError()

    def do_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        terminal = self.terminal

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        terminal.__exit__(*exc_info)
        os.kill(os.getpid(), signal.SIGTSTP)
        terminal.__enter__()

    def do_quit(self):  # Vim ZQ  # Emacs kill-emacs
        """Lose last changes and quit"""

        returncode = 1 if self.iobytearray else None
        returncode = self.get_arg1(default=returncode)

        self.iobytearray[::] = b""

        sys.exit(returncode)

    def do_save_and_quit(self):  # Vim ZZ  # Emacs save-buffers-kill-terminal
        """Save last changes and quit"""

        returncode = self.get_arg1(default=None)

        sys.exit(returncode)

    #
    # Flip switches
    #

    def do_set_invnumber(self):  # Vi Py \n
        """Toggle Line-in-File numbers in or out"""

        self.showing_line_number = not self.showing_line_number
        message = ":set number" if self.showing_line_number else ":set nonumber"
        self.send_reply_soon(message)  # \n Egg

        # TODO: stop commandeering the personal \ Chord Sequences

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |  # Emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        last_column = self.find_last_column()
        column = min(last_column, self.get_arg1() - 1)

        self.column = column

    def do_slip_dent(self):  # Vim ^
        """Leap to just past the Indent, but first Step Down if Arg"""

        if self.arg1:
            arg1 = self.get_arg1()
            self.send_reply_soon("Did you mean:  {} _".format(arg1))  # 9^ Egg, etc

        self.slip_dent()

    def slip_dent(self):
        """Leap to the Column after the Indent"""

        text = self.get_row_text()
        lstripped = text.lstrip()
        column = len(text) - len(lstripped)

        self.column = column

    def do_slip_first(self):  # Vim 0  # Emacs move-beginning-of-line
        """Leap to the first Column in Row"""

        assert self.arg1 is None  # Vi Py takes no Digits before the Chord 0

        self.column = 0

    def do_slip_left(self):  # Vim h, Left  # Emacs left-char, backward-char
        """Slip left one Column or more"""

        self.check(self.column)

        left = min(self.column, self.get_arg1())
        self.column -= left

    def do_slip_right(self):  # Vim l, Right  #  emacs right-char, forward-char
        """Slip Right one Column or more"""

        last_column = self.find_last_column()
        self.check(self.column < last_column)

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
            self.check((self.column < last_column) or (self.row < last_row))

        if self.column < last_column:
            self.column += 1

            self.continue_do_loop()

        elif self.row < last_row:
            self.column = 0
            self.row += 1

            self.continue_do_loop()

    def slip_ahead(self):

        last_column = self.find_last_column()
        last_row = self.find_last_row()

        if self.column < last_column:
            self.column += 1

            return 1

        elif self.row < last_row:
            self.column = 0
            self.row += 1

            return 1

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        if not self.done:
            self.check(self.row or self.column)

        if self.column:
            self.column -= 1

            self.continue_do_loop()

        elif self.row:
            self.row -= 1
            self.column = self.find_last_column()

            self.continue_do_loop()

    def slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        if self.column:
            self.column -= 1

            self.continue_do_loop()

            return -1

        elif self.row:
            self.row -= 1
            self.column = self.find_last_column()

            return -1

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # Vim G, 1G  # Emacs goto-line
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

        self.check(self.row < last_row)
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

        self.check(self.row)
        up = min(self.row, self.get_arg1())

        self.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_last_seek(self):  # Vim $  # Emacs move-end-of-line
        """Leap to the last Column in Row, and keep seeking last Columns"""

        self.seeking_column = True
        self.step_down_minus()
        self.column = self.find_last_column()

        self.continue_column_seek()

    def do_step_down_seek(self):  # Vim j, ⌃J, ⌃N, Down  # Emacs next-line
        """Step down one Row or more, but seek the current Column"""

        if self.seeking_column is None:
            self.seeking_column = self.column

        self.step_down()

        self.column = self.seek_column()
        self.continue_column_seek()

    def do_step_up_seek(self):  # Vim k, ⌃P, Up  # Emacs previous-line
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
        terminal = self.terminal

        assert terminal.scrolling_rows >= 2
        rows_per_screen = terminal.scrolling_rows - 2

        bottom_row = self.find_bottom_row()
        last_row = self.find_last_row()

        # Quit at last Row

        if top_row == last_row:
            if not self.done:
                self.send_reply_soon("Did you mean ⌃B")  # G⌃F⌃F Egg

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
        terminal = self.terminal

        last_row = self.find_last_row()

        # Quit at top Row

        if not top_row:

            return

        assert terminal.scrolling_rows >= 2
        rows_per_screen = terminal.scrolling_rows - 2

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
                self.send_reply_soon("Did you mean ⌃Y")  # G⌃F⌃E Egg

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
                self.send_reply_soon("Did you mean ⌃E")  # 1G⌃Y Egg

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

    def do_paragraph_ahead(self):  # Vim {
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

    def do_paragraph_behind(self):  # Vim }

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

        # TODO: Vim f⎋ means escaped without Bell
        # TODO: Vim f⌃C means cancelled with Bell
        # TODO: Vim f⌃? means cancelled with Bell

        # TODO: Vim f⌃Vx means go find a ⌃V char, not go find X

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
        text = self.get_row_text()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_arg1()

        # Index each

        column = self.column

        for _ in range(count):

            self.check(column < last_column)
            column += 1

            right = text[column:].index(choice)
            column += right

        # Option to slip back one column

        if after:
            self.check(column)
            column -= 1

        self.column = column

    #
    # Step across Chars of CharSets
    #

    def do_big_word_end_ahead(self):  # Vim E

        charsets = list()
        charsets.append(set(" \t"))
        self.word_end_ahead(charsets)
        self.continue_do_loop()

    def do_lil_word_end_ahead(self):  # Vim e

        charsets = list()
        charsets.append(set(" \t"))
        charsets.append(set(string.ascii_letters + string.digits + "_"))

        self.word_end_ahead(charsets)
        self.continue_do_loop()

    def word_end_ahead(self, charsets):

        self.slip_ahead()

        while not self.find_column_in_charsets(charsets):
            if not self.slip_ahead():

                break

        here = self.find_column_in_charsets(charsets)
        if here:

            beyond = None
            while self.find_column_in_charsets(charsets) == here:
                on_last_column = self.column == self.find_last_column()
                if not self.slip_ahead():
                    beyond = False

                    break

                beyond = True
                if on_last_column:

                    break

            if beyond:
                self.slip_behind()

    def do_big_word_start_ahead(self):  # Vim W

        charsets = list()
        charsets.append(set(" \t"))
        self.word_start_ahead(charsets)
        self.continue_do_loop()

    def do_lil_word_start_ahead(self):  # Vim w

        charsets = list()
        charsets.append(set(" \t"))
        charsets.append(set(string.ascii_letters + string.digits + "_"))
        self.word_start_ahead(charsets)
        self.continue_do_loop()

    def word_start_ahead(self, charsets):

        here = self.find_column_in_charsets(charsets)
        if here:

            while self.find_column_in_charsets(charsets) == here:
                on_last_column = self.column == self.find_last_column()
                if not self.slip_ahead():

                    break

                if on_last_column:

                    break

            if not self.column:

                return

        while not self.find_column_in_charsets(charsets):
            if not self.slip_ahead():

                break

    def do_big_word_start_behind(self):  # Vim B

        charsets = list()
        charsets.append(set(" \t"))
        self.word_start_behind(charsets)
        self.continue_do_loop()

        # TODO: add option for 'b e w' and 'B E W' to swap places

    def do_lil_word_start_behind(self):  # Vim b

        charsets = list()
        charsets.append(set(" \t"))
        charsets.append(set(string.ascii_letters + string.digits + "_"))
        self.word_start_behind(charsets)
        self.continue_do_loop()

    def word_start_behind(self, charsets):

        self.slip_behind()

        on_first_column = self.column == 0
        if not on_first_column:

            while not self.find_column_in_charsets(charsets):
                if not self.slip_behind():

                    break

            here = self.find_column_in_charsets(charsets)
            if here:

                beyond = None
                while self.find_column_in_charsets(charsets) == here:
                    on_first_column = self.column == 0
                    if not self.slip_behind():
                        beyond = False

                        break

                    beyond = True
                    if on_first_column:

                        break

                if beyond:
                    self.slip_ahead()

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
        text = self.get_row_text()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_arg1()

        # R-Index each

        column = self.column

        for _ in range(count):

            self.check(column)
            column -= 1

            column = text[: (column + 1)].rindex(choice)

        # Option to slip right one column

        if after:

            self.check(column < last_column)
            column += 1

        self.column = column

    #
    # Repeat search inside the Row for a single Char
    #

    def do_slip_choice_redo(self):  # Vim ;
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        if self.slip_choice is None:
            self.send_reply_soon("Did you mean:  fx;")  # ; Egg
            self.send_bell_soon()

            return

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

        if self.slip_choice is None:
            self.send_reply_soon("Did you mean:  Fx,")  # , Egg
            self.send_bell_soon()

            return

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
    # Map Keyboard Inputs to Code, for when feeling like Vim
    #

    def _vim_bots_by_chords_(self):
        """Map Keyboard Inputs to Code, for when feeling like Vim"""

        bots_by_chords = dict()

        bots_by_chords[None] = (self.do_raise_name_error,)

        # bots_by_chords[b"\x00"]  # NUL, aka ⌃@, aka 0
        # bots_by_chords[b"\x01"]  # SOH, aka ⌃A, aka 1
        bots_by_chords[b"\x02"] = (self.do_scroll_behind_much,)  # STX, aka ⌃B, aka 2
        bots_by_chords[b"\x03"] = (self.do_help_quit,)  # ETX, aka ⌃C, aka 3
        bots_by_chords[b"\x04"] = (self.do_scroll_ahead_some,)  # EOT, aka ⌃D, aka 4
        bots_by_chords[b"\x05"] = (self.do_scroll_ahead_one,)  # ENQ, aka ⌃E, aka 5
        bots_by_chords[b"\x06"] = (self.do_scroll_ahead_much,)  # ACK, aka ⌃F, aka 6
        bots_by_chords[b"\x07"] = (self.do_give_more_status,)  # BEL, aka ⌃G, aka 7 \a
        # bots_by_chords[b"\x08"]  # BS, aka ⌃H, aka 8 \b
        # bots_by_chords[b"\x09"]  # TAB, aka ⌃I, aka 9 \t
        bots_by_chords[b"\x0A"] = (self.do_step_down_seek,)  # LF, aka ⌃J, aka 10 \n
        # bots_by_chords[b"\x0B"]  # VT, aka ⌃K, aka 11 \v
        bots_by_chords[b"\x0C"] = (self.do_redraw,)  # FF, aka ⌃L, aka 12 \f
        bots_by_chords[b"\x0D"] = (self.do_step_down_dent,)  # CR, aka ⌃M, aka 13 \r
        bots_by_chords[b"\x0E"] = (self.do_step_down_seek,)  # SO, aka ⌃N, aka 14
        # bots_by_chords[b"\x0F"]  # SI, aka ⌃O, aka 15
        bots_by_chords[b"\x10"] = (self.do_step_up_seek,)  # DLE, aka ⌃P, aka 16
        # bots_by_chords[b"\x11"]  # DC1, aka XON, aka ⌃Q, aka 17
        # bots_by_chords[b"\x12"]  # DC2, aka ⌃R, aka 18
        # bots_by_chords[b"\x13"]  # DC3, aka XOFF, aka ⌃S, aka 19
        # bots_by_chords[b"\x14"]  # DC4, aka ⌃T, aka 20
        bots_by_chords[b"\x15"] = (self.do_scroll_behind_some,)  # NAK, aka ⌃U, aka 21
        # bots_by_chords[b"\x16"]  # SYN, aka ⌃V, aka 22
        # bots_by_chords[b"\x17"]  # ETB, aka ⌃W, aka 23
        # bots_by_chords[b"\x18"]  # CAN, aka ⌃X , aka 24
        bots_by_chords[b"\x19"] = (self.do_scroll_behind_one,)  # EM, aka ⌃Y, aka 25
        bots_by_chords[b"\x1A"] = (self.do_sig_tstp,)  # SUB, aka ⌃Z, aka 26

        bots_by_chords[b"\x1B"] = (self.do_c0_control_esc,)  # ESC, aka ⌃[, aka 27
        bots_by_chords[b"\x1B[A"] = (self.do_step_up_seek,)  # ↑ Up Arrow
        bots_by_chords[b"\x1B[B"] = (self.do_step_down_seek,)  # ↓ Down Arrow
        bots_by_chords[b"\x1B[C"] = (self.do_slip_right,)  # → Right Arrow
        bots_by_chords[b"\x1B[D"] = (self.do_slip_left,)  # ← Left Arrow

        # bots_by_chords[b"\x1C"] = (self.eval_readline,)   # FS, aka ⌃\, aka 28
        # bots_by_chords[b"\x1D"]  # GS, aka ⌃], aka 29
        # bots_by_chords[b"\x1E"]  # RS, aka ⌃^, aka 30  # try this after edit in: |vi -
        # bots_by_chords[b"\x1F"]  # US, aka ⌃_, aka 31

        bots_by_chords[b" "] = (self.do_slip_ahead,)
        # bots_by_chords[b"!"] = (self.do_pipe,)
        # bots_by_chords[b'"'] = (self.do_arg,)
        # bots_by_chords[b'#'] = (self.do_lil_word_find_behind,)
        bots_by_chords[b"$"] = (self.do_slip_last_seek,)
        # bots_by_chords[b"%"]  # TODO: leap to match
        # bots_by_chords[b"&"]  # TODO: & and && for repeating substitution
        # bots_by_chords[b"'"]  # TODO: leap to pin
        # bots_by_chords[b"("]  # TODO: sentence behind
        # bots_by_chords[b")"]  # TODO: sentence ahead
        # bots_by_chords[b'*'] = (self.do_lil_word_find_ahead,)
        bots_by_chords[b"+"] = (self.do_step_down_dent,)
        bots_by_chords[b","] = (self.do_slip_choice_undo,)
        bots_by_chords[b"-"] = (self.do_step_up_dent,)
        # bots_by_chords[b"/"] = (self.find_ahead_readline,)

        bots_by_chords[b"0"] = (self.do_slip_first,)

        # bots_by_chords[b":"]  # TODO: escape vi
        bots_by_chords[b";"] = (self.do_slip_choice_redo,)
        # bots_by_chords[b"<"]  # TODO: dedent
        # bots_by_chords[b"="]  # TODO: dent after
        # bots_by_chords[b">"]  # TODO: indent
        # bots_by_chords[b"?"] = (self.find_behind_readline,)
        # bots_by_chords[b"@"]  # TODO: play

        # bots_by_chords[b"A"] = (self.do_slip_last_right_open,)
        bots_by_chords[b"B"] = (self.do_big_word_start_behind,)
        # bots_by_chords[b"C"] = (self.do_chop_open,)
        # bots_by_chords[b"D"] = (self.do_chop,)
        bots_by_chords[b"E"] = (self.do_big_word_end_ahead,)
        bots_by_chords[b"F"] = (None, self.do_slip_rindex)
        bots_by_chords[b"G"] = (self.do_step,)
        bots_by_chords[b"H"] = (self.do_step_max_high,)
        # bots_by_chords[b"I"] = (self.do_slip_dent_open,)
        # bots_by_chords[b"J"] = (self.do_slip_last_join_right,)
        # bots_by_chords[b"K"] = (self.do_lookup,)
        bots_by_chords[b"L"] = (self.do_step_max_low,)
        bots_by_chords[b"M"] = (self.do_step_to_middle,)
        # bots_by_chords[b"N"] = (self.find_behind,)
        # bots_by_chords[b"O"] = (self.do_slip_first_open,)
        # bots_by_chords[b"P"] = (self.do_paste_behind,)

        bots_by_chords[b"Q"] = None
        bots_by_chords[b"Qv"] = None
        bots_by_chords[b"Qvi"] = None
        bots_by_chords[b"Qvi\x0D"] = (self.do_reopen_vi,)  # CR, aka ⌃M, aka 13 \r

        # bots_by_chords[b"R"] = (self.do_open_overwrite,)
        # bots_by_chords[b"S"] = (self.do_slip_first_chop_open,)
        bots_by_chords[b"T"] = (None, self.do_slip_rindex_plus)
        # bots_by_chords[b"U"] = (self.do_row_undo,)
        # bots_by_chords[b"V"] = (self.do_mark_rows,)
        bots_by_chords[b"W"] = (self.do_big_word_start_ahead,)
        # bots_by_chords[b"X"] = (self.do_cut_behind,)
        # bots_by_chords[b"Y"] = (self.do_copy_row,)

        bots_by_chords[b"Z"] = None
        bots_by_chords[b"ZQ"] = (self.do_quit,)
        bots_by_chords[b"ZZ"] = (self.do_save_and_quit,)

        # bots_by_chords[b"["]  # TODO

        bots_by_chords[b"\\"] = None
        bots_by_chords[b"\\n"] = (self.do_set_invnumber,)

        # bots_by_chords[b"]"]  # TODO
        bots_by_chords[b"^"] = (self.do_slip_dent,)
        bots_by_chords[b"_"] = (self.do_step_down_minus_dent,)
        # bots_by_chords[b"`"]  # TODO: same as '

        # bots_by_chords[b"a"] = (self.do_slip_right_open,)
        bots_by_chords[b"b"] = (self.do_lil_word_start_behind,)
        # bots_by_chords[b"c"] = (self.do_chop_after_open,)
        # bots_by_chords[b"d"] = (self.do_chop_after,)
        bots_by_chords[b"e"] = (self.do_lil_word_end_ahead,)
        bots_by_chords[b"f"] = (None, self.do_slip_index)
        # bots_by_chords[b"g"]
        bots_by_chords[b"h"] = (self.do_slip_left,)
        # bots_by_chords[b"i"] = (self.do_open,)
        bots_by_chords[b"j"] = (self.do_step_down_seek,)
        bots_by_chords[b"k"] = (self.do_step_up_seek,)
        bots_by_chords[b"l"] = (self.do_slip_right,)
        # bots_by_chords[b"m"] = (None, self.do_drop_pin)
        # bots_by_chords[b"n"] = (self.find_ahead,)
        # bots_by_chords[b"o"] = (self.do_slip_last_right_open,)
        # bots_by_chords[b"p"] = (self.do_paste_ahead,)
        # bots_by_chords[b"q"] = (self.do_record,)
        # bots_by_chords[b"r"] = (None, self.do_overwrite)
        # bots_by_chords[b"s"] = (self.do_cut_behind_open,)
        bots_by_chords[b"t"] = (None, self.do_slip_index_minus)
        # bots_by_chords[b"u"] = (self.do_undo,)
        # bots_by_chords[b"v"] = (self.do_mark_chars,)
        bots_by_chords[b"w"] = (self.do_lil_word_start_ahead,)
        # bots_by_chords[b"x"] = (self.do_cut_ahead,)
        # bots_by_chords[b"y"] = (self.do_copy_after,)

        bots_by_chords[b"z"] = None
        # bots_by_chords[b"zz"] = (self.do_scroll_to_center,)

        bots_by_chords[b"{"] = (self.do_paragraph_behind,)
        bots_by_chords[b"|"] = (self.do_slip,)
        bots_by_chords[b"}"] = (self.do_paragraph_ahead,)
        # bots_by_chords[b"~"] = (self.do_flip_case_overwrite,)

        bots_by_chords[b"\x7F"] = (self.do_slip_behind,)  # DEL, aka ⌃?, aka 127

        return bots_by_chords


class TerminalPainter:
    """Paint a Screen of Rows of Chars"""

    def __init__(self, terminal):

        self.terminal = terminal  # layer over a TerminalShadow

        self.rows = None  # count Rows on Screen
        self.columns = None  # count Columns per Row
        self.scrolling_rows = None  # divide the Screen into Scrolling Rows and Status

        self.cursor_row = 0  # point the Screen Cursor to a Row of File
        self.cursor_column = 0  # point the Screen Cursor to a Column of File

        self.top_line_number = 1  # number the Rows of the Screen down from first
        self.last_line_number = 1  # number all Rows as wide as the last
        self.showing_line_number = None  # start each Row with its Line Number, or don't

        self._reopen_terminal_()  # start sized to fit the initial Screen

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.terminal.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        self.terminal.__exit__()

    def _reopen_terminal_(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        terminal_size = terminal._reopen_terminal_()  # a la os.get_terminal_size(fd)
        assert terminal_size.lines >= 1
        assert terminal_size.columns >= 1

        self.rows = terminal_size.lines
        self.columns = terminal_size.columns

        self.scrolling_rows = terminal_size.lines - 1  # reserve last 1 line for Status

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

    def getch(self):
        """Block to return next Keyboard Input, else raise KeyboardInterrupt"""

        chord = self.terminal.getch()

        if chord == b"\x03":
            raise KeyboardInterrupt()

        return chord

    def format_as_line_number(self, index):
        """Format a Row Index on Screen as a Line Number of File"""

        if not self.showing_line_number:

            return ""

        last_line_number = "{:3} ".format(self.last_line_number)
        width = len(last_line_number)

        line_number = self.top_line_number + index
        formatted = "{:3} ".format(line_number).rjust(width)

        return formatted

    def write_screen(self, lines, status):
        """Write over the Rows of Chars on Screen"""

        terminal = self.terminal
        rows = self.rows
        columns = self.columns

        visibles = lines[: (rows - 1)]
        texts = list(_.splitlines()[0] for _ in visibles)

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

        terminal.write(ED_2)
        terminal.write(CUP_1_1)
        for (index, text) in enumerate(texts):
            if len(text) < columns:
                terminal.write(text + "\n\r")
            else:
                terminal.write(text)  # depend on automagic "\n\r" after Last Column

        # Show status, inside the last Row
        # but don't write over the Lower Right Char  # TODO: test vs autoscroll

        str_status = "" if (status is None) else str(status)
        terminal.write(str_status.ljust(columns - 1))

        # Place the cursor

        y = 1 + self.cursor_row
        x = 1 + len(str_line_number) + self.cursor_column
        terminal.write(CUP_Y_X.format(y, x))

    def write_bell(self):
        """Ring the bell"""

        self.terminal.write("\a")


class TerminalShadow:
    """Paint a Screen of Rows of Chars, but mostly write just the Diffs to reduce Lag"""

    def __init__(self, terminal):

        self.terminal = terminal

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.terminal.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        self.terminal.__exit__()

    def _reopen_terminal_(self):
        """Clear the Caches layered over this Terminal, here and below"""

        terminal = self.terminal

        fd = terminal.fileno()
        terminal_size = os.get_terminal_size(fd)

        # FIXME: pad with Spaces to grow cache of Rows of Chars
        # FIXME: chop Chars to shrink cache of Rows of Chars

        return terminal_size

        # TODO: emulate more of 'shutil.get_terminal_size'

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

    def getch(self):
        """Block till the keyboard input Digit or Chord"""

        return self.terminal.getch()

    def write(self, chars):
        """Compare with Chars at Cursor, write Diffs now, move Cursor soon"""

        if chars.startswith(CSI):

            if chars == ED_2:
                self.write_erase_in_display(chars)
            elif chars.endswith("H"):
                self.write_cursor_position(chars)
            else:
                raise NotImplementedError(repr(chars))

        else:

            lines = chars.splitlines(keepends=True)
            for line in lines:

                if CSI in line:
                    raise NotImplementedError(repr(line))
                if len(line.splitlines()) != 1:
                    raise NotImplementedError(repr(line))

                text = line.splitlines()[0]
                end = line[len(text) :]

                self.write_text(chars=text)
                self.write_end(chars=end)

    def write_erase_in_display(self, chars):
        """Write Spaces over Chars of Screen"""

        self.terminal.write(chars)

        # FIXME: fill with Spaces

    def write_cursor_position(self, chars):
        """Leap to chosen Row and Column of Screen"""

        self.terminal.write(chars)

        # FIXME: parse and shadow Position

    def write_text(self, chars):
        """Write Chars over this Row, and start next Row if this Row complete"""

        self.terminal.write(chars)

    def write_end(self, chars):
        """Move Cursor to start of next Row"""

        # FIXME: assert there is a next Row, without Scrolling

        self.terminal.write(chars)

    # TODO: Add API to write Scroll CSI in place of rewriting Screen to Scroll


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

    def __init__(self, terminal):

        self.terminal = terminal

        self.terminal_fileno = None
        self.with_termios = None
        self.inputs = None

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.terminal.flush()

        if self.terminal.isatty():

            terminal_fileno = self.terminal.fileno()
            self.with_termios = termios.tcgetattr(terminal_fileno)
            tty.setraw(terminal_fileno, when=termios.TCSADRAIN)  # not TCSAFLUSH

            self.terminal.write(_CURSES_INITSCR_)
            self.terminal.flush()

            self.terminal_fileno = terminal_fileno

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        _ = (exc_type, exc_value, traceback)

        self.terminal.flush()

        if self.with_termios:

            self.terminal.write(_CURSES_ENDWIN_)
            self.terminal.flush()

            when = termios.TCSADRAIN
            attributes = self.with_termios
            termios.tcsetattr(self.terminal_fileno, when, attributes)

    def fileno(self):
        """Authorize bypass of Terminal Driver"""

        return self.terminal.fileno()

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

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

        stdin = os.read(self.terminal.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while line not closed
        # Trust no multibyte char encoding contains b"\r" or b"\n" (as per UTF-8)

        calls = 1
        while stdin and (b"\r" not in stdin) and (b"\n" not in stdin):

            if self.with_termios:
                if not self.kbhit():
                    break

            more = os.read(self.terminal.fileno(), 1)
            if not more:
                assert not self.with_termios
                break

            stdin += more
            calls += 1

        assert calls <= len(stdin) if self.with_termios else (len(stdin) + 1)

        return stdin

    def kbhit(self):
        """Wait till next Keystroke, or next burst of Paste pasted"""

        rlist = [self.terminal]
        wlist = list()
        xlist = list()
        timeout = 0
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_) = selected

        if rlist_ == rlist:
            return True

    def write(self, chars):
        """Compare with Chars at Cursor, write Diffs now, move Cursor soon"""

        self.terminal.write(chars)


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
