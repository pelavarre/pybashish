#!/usr/bin/env python3

r"""
usage: vi.py [-h] [FILE ...]

read files, accept zero or more edits, write files

positional arguments:
  FILE        a file to edit, such as '-' to mean stdin

optional arguments:
  -h, --help  show this help message and exit

quirks:
  defaults to read Stdin, and writes Stdout at ZZ (but not at ZQ)

keyboard tests:
  ZQ ZZ ⌃Zfg  => how to exit Vi Py
  ⌃C Up Down Right Left Space Delete Return  => natural enough
  0 ^ $ fx h l tx Fx Tx ; , |  => leap to column
  b e w B E W { }  => leap across small word, large word, paragraph
  j k G 1G H L M - + _ ⌃J ⌃N ⌃P  => leap to row, leap to line
  1234567890 Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y zb zt zz  => scroll rows
  ⌃L ⌃G  => toggle lag and say if lag is toggled
  \n \i \F \Esc  => toggle show line numbers, search case, search regex, show matches
  /... Delete ⌃U ⌃C Return  ?...   * # £ n N  => enter a search key, find later/ earlier
  Esc ⌃C Qvi⌃M 123Esc 123⌃C 3ZQ f⌃C 9^ G⌃F⌃F 1G⌃B G⌃F⌃E 1G⌃Y ; , n N  => eggs
  \F/$Return  => more eggs

examples:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py -  # demo ZQ, etc
  cat bin/vi.py |bin/vi.py - |grep import  # demo ZQ vs ZZ
"""
# we do define the arcane ⌃L to redraw, but we don't mention it in the help
# we also don't mention ⌃D ⌃U till they stop raising NotImplementedError


import argparse
import collections
import difflib
import inspect
import os
import pdb
import re
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

ED_2 = "\x1B[2J"  # Erase in Display (ED)  # 2 = Whole Screen
CUP_Y_X = "\x1B[{};{}H"  # Cursor Position (CUP)
CUP_1_1 = "\x1B[H"  # Cursor Position (CUP)  # (1, 1) = Upper Left

SGR_N = "\x1B[{}m"  # Select Graphic Rendition
SGR_7 = SGR_N.format(7)  # SGR > Reverse Video, Invert
SGR = "\x1B[m"  # SGR > Reset, Normal, All Attributes Off

CUP_Y_X_REGEX = r"^\x1B\[([0-9]+);([0-9]+)H$"

DECSC = ESC + "7"  # DEC Save Cursor
DECRC = ESC + "8"  # DEC Restore Cursor

_XTERM_ALT_ = "\x1B[?1049h"
_XTERM_MAIN_ = "\x1B[?1049l"

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

    args = parse_vi_argv(argv)

    # Visit each File

    editor = TerminalVi(files=args.files)

    returncode = None
    try:
        editor.run_terminal()
        assert False  # unreached
    except SystemExit as exc:
        returncode = exc.code

        if editor.log:
            stderr_print(editor.log)

        # TODO: log keystrokes interpreted before exit, or dropped by exit

    # Exit

    sys.exit(returncode)


def parse_vi_argv(argv):
    """Convert a Vi Sys ArgV to an Args Namespace, or print some Help and quit"""

    parser = compile_argdoc(epi="quirks")
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a file to edit, such as '-' to mean stdin",
    )

    exit_unless_doc_eq(parser)

    args = parser.parse_args(argv[1:])

    return args


#
# Edit some Scrolling Rows, backed by Lines of a File of Chars encoded as Bytes
#


VI_BLANK_SET = set(" \t")
VI_SYMBOLIC_SET = set(string.ascii_letters + string.digits + "_")  # aka r"[A-Za-z0-9_]"


class TerminalVi:
    """Feed Keyboard into Screen of File of Lines of chars, a la Vi"""

    def __init__(self, files):

        self.files = files  # read zero or more files
        self.file_index = None
        self.reading_path = None

        self.log = None  # capture Python Tracebacks

        self.slip_choice = None  # find Char in Row
        self.slip_after = None  # slip off by one Column after finding Char
        self.slip_redo = None  # find later Char
        self.slip_undo = None  # find earlier Char

        self.seeking_more = None  # remembering the Seeking Column into next Nudge
        self.seeking_column = None  # leap to a Column after changing Row

    def run_terminal(self):
        """Enter Terminal Driver, then run Keyboard, then exit Terminal Driver"""

        runner = TerminalRunner()
        self.runner = runner

        self.do_next_vi_file()
        self.do_help_quit_vi()  # start with a warmer welcome, not a cold empty Nudge

        bots_by_chords = self._vi_bots_by_chords_()
        try:
            runner.run_terminal(bots_by_chords)
            assert False  # unreached
        finally:
            self.log = runner.traceback

    def do_next_vi_file(self):
        """Visit the next File, else the first File"""

        files = self.files
        file_index = self.file_index

        # Explicitly reject the traditional Vim Count argument

        arg1 = self.get_vi_arg1(default=None)
        if arg1 is not None:
            raise NotImplementedError

        # Close this File

        if self.reading_path is not None:
            self.do_might_flush_vi()

        # Choose next File, else quit after last File

        if file_index is None:
            next_file_index = 0
            next_file = None if (not files) else files[next_file_index]
        elif file_index < (len(files) - 1):
            next_file_index = file_index + 1
            next_file = files[next_file_index]
        else:
            self.do_quit_vi()  # Vim chokes here, because no next File
            assert False  # unreached

        self.file_index = next_file_index

        # Visit the chosen File

        path = next_file
        if next_file == "-":
            path = "/dev/stdin"
        elif next_file is None:
            if not sys.stdin.isatty():
                path = "/dev/stdin"

        self.reopen_path(path)

    def reopen_path(self, path):
        """Visit a chosen File"""

        self.reading_path = path

        runner = self.runner

        # Fetch Bytes of File

        iobytes = b""
        if path is not None:

            if sys.stdin.isatty():
                if path == "/dev/stdin":
                    stderr_print("Press ⌃D EOF to quit giving input")

            with open(path, "rb") as reading:
                iobytes = reading.read()

        iobytearray = bytearray(iobytes)

        # Start editing Lines of Columns, given a File of Bytes

        runner.reopen_iobytearray(iobytearray)

    #
    # Layer thinly over TerminalRunner
    #

    def get_vi_arg1(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        return self.runner.get_arg1(default=default)

    def get_vi_arg2(self):
        """Get the Bytes of the input Suffix past the input Chords"""

        return self.runner.get_arg2()

    def send_vi_reply(self, message):
        """Capture some Status now, to show with next Prompt"""

        self.runner.send_reply(message)

    def send_vi_bell(self):
        """Capture some Status now, to show with next Prompt"""

        self.runner.send_bell()

    #
    # Layer thinly under the rest of TerminalVi
    #

    def check_index(self, truthy, **kwargs):
        """Fail fast, else proceed"""

        if not truthy:
            raise IndexError()

    def continue_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        self.seeking_more = True

    #
    # Define keys for pausing TerminalVi
    #

    def do_raise_vi_name_error(self):  # such as Esc, such as ZB
        """Reply to meaningless Keyboard Input"""

        self.runner.raise_chords_as_name_error()

    def do_c0_control_esc(self):  # Vim Esc
        """Cancel Digits Prefix, else suggest ZZ to quit Vi Py"""

        arg1 = self.get_vi_arg1(default=None)
        if arg1 is not None:
            self.send_vi_reply("Escaped")  # 123 Esc Egg, etc
        else:
            self.send_vi_reply("Press ZZ to save changes and quit Vi Py")  # Esc Egg
            # Vim rings a Bell for each extra Esc

    def do_continue_vi(self):  # Vim Q v i Return  # not Ex Mode from last century
        """Accept Q v i Return, without ringing the Terminal bell"""

        runner = self.runner

        nudge = TerminalNudgeIn(chords=b"Qvi\r")
        message = "Would you like to play a game?"

        runner.reply = TerminalReplyOut(nudge=nudge, message=message)

    def do_vi_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        runner = self.runner

        runner.do_sig_tstp()

        if self.seeking_column is not None:
            self.continue_column_seek()

    #
    # Define keys for entering, pausing, and exiting TerminalVi
    #

    def do_flush_quit_vi(self):  # Vim ZZ  # Vim :wq!\r
        """Save last changes and quit"""

        self.do_flush_vi()

        returncode = self.get_vi_arg1(default=None)
        sys.exit(returncode)  # Mac & Linux take only 'returncode & 0xFF'

    def do_flush_vi(self):  # Vim :w!\r

        runner = self.runner
        iobytearray = runner.iobytearray
        os.write(sys.stdout.fileno(), iobytearray)
        sys.stdout.flush()

    def do_help_quit_vi(self):  # Vim ⌃C  # Vi Py Init
        """Suggest ZQ to quit Vi Py"""

        self.send_vi_reply("Press ZQ to lose changes and quit Vi Py")  # ⌃C Egg
        # Vim rings a Bell for each extra ⌃C

    def do_might_flush_quit_vi(self):  # Vim :wq\r
        """Halt if more files, else quit"""

        self.do_might_flush_vi()
        self.do_might_quit_vi()

    def do_might_flush_vi(self):  # Vim :w\r

        self.do_flush_vi()

    def do_might_quit_vi(self):  # Vim :q\r
        """Halt if more files, else quit"""

        file_index = self.file_index
        files = self.files

        more_files = files[file_index:][1:]
        if more_files:
            raise IndexError("{} more files".format(len(more_files)))
            # Vim raises this IndexError only once, til next ':w' write

        self.do_quit_vi()

    def do_quit_vi(self):  # Vim ZQ  # Vim :q!\r
        """Lose last changes and quit"""

        runner = self.runner
        iobytearray = runner.iobytearray

        returncode = 1 if iobytearray else None
        returncode = self.get_vi_arg1(default=returncode)

        sys.exit(returncode)  # Mac & Linux take only 'returncode & 0xFF'

    #
    # Define keys for entering Search Keys and leaping to the matching Span
    #

    def do_find_ahead_this(self):  # Vim *
        """Take a Search Key from this Line, and then look ahead for it"""

        runner = self.runner

        if self.get_find_vi_this(slip=+1) is None:
            self.send_vi_reply("Press * and # only when Not on a blank line")
        else:
            runner.highlighting_matches = True
            if runner.find_ahead():

                runner.continue_do_loop()

    def do_find_behind_this(self):  # Vim #
        """Take a Search Key from this Line, and then look behind for it"""

        runner = self.runner

        if self.get_find_vi_this(slip=-1) is None:
            self.send_vi_reply("Press # and * only when Not on a blank line")
        else:
            runner.highlighting_matches = True
            if runner.find_behind():

                runner.continue_do_loop()

    def do_find_ahead_vi_line(self):  # Vim /
        """Take a Search Key as input, and then look ahead for it"""

        runner = self.runner

        if self.read_find_vi_line(slip=+1):
            runner.highlighting_matches = True
            if runner.find_ahead():  # TODO: scroll ahead when far  # <= zb H 23Up n

                runner.continue_do_loop()

    def do_find_behind_vi_line(self):  # Vim ?
        """Take a Search Key as input, and then look behind for it"""

        runner = self.runner

        if self.read_find_vi_line(slip=-1):
            runner.highlighting_matches = True
            if runner.find_behind():  # TODO: scroll behind when far  # <= zt L 23Down N

                runner.continue_do_loop()

    def do_find_earlier(self):  # Vim N
        """Leap to earlier Search Key Match"""

        runner = self.runner

        if runner.finding_line is None:
            self.send_vi_reply("Press ? to enter a Search Key")
        elif runner.finding_slip >= 0:
            runner.highlighting_matches = True
            if runner.find_behind():

                runner.continue_do_loop()
        else:
            runner.highlighting_matches = True
            if runner.find_ahead():

                runner.continue_do_loop()

    def do_find_later(self):  # Vim n
        """Leap to later Search Key Match"""

        runner = self.runner

        if runner.finding_line is None:
            self.send_vi_reply("Press / to enter a Search Key")
        elif runner.finding_slip >= 0:
            runner.highlighting_matches = True
            if runner.find_ahead():

                runner.continue_do_loop()
        else:
            runner.highlighting_matches = True
            if runner.find_behind():

                runner.continue_do_loop()

    def get_find_vi_this(self, slip):
        """Take a Search Key from this Line and return Truthy, else don't"""

        runner = self.runner

        search_key = self.get_vi_this()
        if search_key is not None:

            runner.finding_line = search_key
            runner.finding_slip = slip

            assert runner.finding_line != ""
            runner.reopen_finding_spans()

            return search_key

    def get_vi_this(self):
        """Take a Symbolic word, else a Non-Blank word, from the rest of this Line"""

        runner = self.runner

        column = runner.column
        columns = runner.count_columns_in_row()

        def is_vi_symbolic(ch):
            return ch in VI_SYMBOLIC_SET

        def is_not_vi_blank(ch):
            return ch not in VI_BLANK_SET

        search_key = None

        for func in (is_vi_symbolic, is_not_vi_blank):
            for start in range(column, columns):
                ch = runner.get_column_char(column=start)
                if func(ch):

                    search_key = ""

                    for stepper in range(start, columns):
                        ch = runner.get_column_char(column=stepper)
                        if func(ch):
                            search_key += ch
                        else:

                            break

                    return search_key

    def read_find_vi_line(self, slip):
        """Take a Search Key"""

        runner = self.runner

        assert runner.finding_line != ""

        finding_line = None
        with_finding_line = runner.finding_line
        with_finding_slip = runner.finding_slip
        runner.finding_slip = slip
        try:
            finding_line = self.read_vi_line()
            if finding_line:
                runner.finding_line = finding_line
        except Exception:
            runner.finding_line = with_finding_line
            runner.finding_slip = with_finding_slip
            raise

        if not finding_line:
            if (not runner.finding_line) or (finding_line is None):
                runner.finding_slip = with_finding_slip
                self.send_vi_reply("Search cancelled")  # Vim ⌃C

                return

        assert runner.finding_line != ""
        runner.reopen_finding_spans()

        return True

    def read_vi_line(self):
        """Take a Line of Input"""

        runner = self.runner
        runner.nudge = TerminalNudgeIn()

        ex = TerminalEx(runner)
        line = ex.read_ex_line()

        return line

    #
    # Flip switches
    # TODO: somehow soon stop commandeering the personal \ or Q Chord Sequences
    #

    def do_invhlsearch(self):  # Vi Py \Esc
        """Toggle highlighting matches"""

        runner = self.runner

        runner.highlighting_matches = not runner.highlighting_matches
        message = ":set hlsearch" if runner.highlighting_matches else ":nohlsearch"
        self.send_vi_reply(message)  # \Esc Egg

        # Vim lacks ':invhlsearch' and lacks ':hlsearch'
        # Vi Py stretches Vim ':noh' to mean ':invhlsearch', not just ':nohlsearch'

    def do_set_invignorecase(self):  # Vi Py \i
        """Search Upper/Lower Case or not"""

        runner = self.runner

        runner.finding_case = not runner.finding_case
        runner.reopen_finding_spans()

        message = ":set noignorecase" if runner.finding_case else ":set ignorecase"
        self.send_vi_reply(message)  # \i Egg

    def do_set_invnumber(self):  # Vi Py \n
        """Show Line Numbers or not"""

        runner = self.runner

        runner.showing_line_number = not runner.showing_line_number

        message = ":set number" if runner.showing_line_number else ":set nonumber"
        self.send_vi_reply(message)  # \n Egg

    def do_set_invregex(self):  # Vi Py \F
        """Search as Regex or search as Chars"""

        runner = self.runner

        runner.finding_regex = not runner.finding_regex
        runner.reopen_finding_spans()

        message = ":set regex" if runner.finding_regex else ":set noregex"
        self.send_vi_reply(message)  # \F Egg  # but Vim never gives you 'noregex'

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |  # Emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        runner = self.runner

        last_column = runner.find_last_column()
        column = min(last_column, self.get_vi_arg1() - 1)

        runner.column = column

    def do_slip_dent(self):  # Vim ^
        """Leap to just past the Indent, but first Step Down if Arg"""

        arg1 = self.get_vi_arg1(default=None)
        if arg1 is not None:
            self.send_vi_reply("Did you mean:  {} _".format(arg1))  # 9^ Egg, etc

        self.slip_dent()

    def slip_dent(self):
        """Leap to the Column after the Indent"""

        runner = self.runner

        text = runner.get_row_text()
        lstripped = text.lstrip()
        column = len(text) - len(lstripped)

        runner.column = column

    def do_slip_first(self):  # Vim 0  # Emacs move-beginning-of-line
        """Leap to the first Column in Row"""

        runner = self.runner

        assert runner.arg1 is None  # Vi Py takes no Digits before the Chord 0

        runner.column = 0

    def do_slip_left(self):  # Vim h, Left  # Emacs left-char, backward-char
        """Slip left one Column or more"""

        runner = self.runner

        self.check_index(runner.column)

        left = min(runner.column, self.get_vi_arg1())
        runner.column -= left

    def do_slip_right(self):  # Vim l, Right  #  emacs right-char, forward-char
        """Slip Right one Column or more"""

        runner = self.runner

        last_column = runner.find_last_column()
        self.check_index(runner.column < last_column)

        right = min(last_column - runner.column, self.get_vi_arg1())
        runner.column += right

    #
    # Step the Cursor across zero, one, or more Columns of the same Row
    #

    def do_slip_ahead(self):  # Vim Space
        """Slip right, then down"""

        runner = self.runner
        last_column = runner.find_last_column()
        last_row = runner.find_last_row()

        if not runner.doing_done:
            self.check_index((runner.column < last_column) or (runner.row < last_row))

        if runner.column < last_column:
            runner.column += 1

            runner.continue_do_loop()

        elif runner.row < last_row:
            runner.column = 0
            runner.row += 1

            runner.continue_do_loop()

    def slip_ahead(self):

        runner = self.runner
        last_column = runner.find_last_column()
        last_row = runner.find_last_row()

        if runner.column < last_column:
            runner.column += 1

            return 1

        elif runner.row < last_row:
            runner.column = 0
            runner.row += 1

            return 1

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        runner = self.runner

        if not runner.doing_done:
            self.check_index(runner.row or runner.column)

        if runner.column:
            runner.column -= 1

            runner.continue_do_loop()

        elif runner.row:
            runner.row -= 1
            row_last_column = runner.find_last_column(row=runner.row)
            runner.column = row_last_column

            runner.continue_do_loop()

    def slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        runner = self.runner

        if runner.column:
            runner.column -= 1

            runner.continue_do_loop()

            return -1

        elif runner.row:
            runner.row -= 1
            row_last_column = runner.find_last_column(row=runner.row)
            runner.column = row_last_column

            return -1

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # Vim G, 1G  # Emacs goto-line
        """Leap to last Row, else to a chosen Row"""

        runner = self.runner
        last_row = runner.find_last_row()

        row = min(last_row, self.get_vi_arg1() - 1)
        row = last_row if (runner.arg1 is None) else row

        runner.row = row
        self.slip_dent()

    def do_step_down_dent(self):  # Vim +, Return
        """Step down a Row or more, but land just past the Indent"""

        self.step_down()
        self.slip_dent()

    def step_down(self):
        """Step down one Row or more"""

        runner = self.runner
        last_row = runner.find_last_row()

        self.check_index(runner.row < last_row)
        down = min(last_row - runner.row, self.get_vi_arg1())

        runner.row += down

    def do_step_down_minus_dent(self):  # Vim _
        """Leap to just past the Indent, but first Step Down if Arg"""

        self.step_down_minus()
        self.slip_dent()

    def step_down_minus(self):
        """Step down zero or more Rows, not one or more Rows"""

        down = self.get_vi_arg1() - 1
        if down:
            self.runner.arg1 -= 1  # mutate
            self.step_down()

    def do_step_max_low(self):  # Vim L
        """Leap to first Word of Bottom Row on Screen"""

        runner = self.runner
        runner.row = runner.find_bottom_row()
        self.slip_dent()

    def do_step_max_high(self):  # Vim H
        """Leap to first Word of Top Row on Screen"""

        runner = self.runner
        runner.row = runner.top_row
        self.slip_dent()

    def do_step_to_middle(self):  # Vim M
        """Leap to first Word of Middle Row on Screen"""

        runner = self.runner
        runner.row = runner.find_middle_row()
        self.slip_dent()

    def do_step_up_dent(self):  # Vim -
        """Step up a Row or more, but land just past the Indent"""

        self.step_up()
        self.slip_dent()

    def step_up(self):
        """Step up one Row or more"""

        runner = self.runner
        self.check_index(runner.row)
        up = min(runner.row, self.get_vi_arg1())

        runner.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_last_seek(self):  # Vim $  # Emacs move-end-of-line
        """Leap to the last Column in Row, and keep seeking last Columns"""

        runner = self.runner

        self.seeking_column = True
        self.step_down_minus()
        row_last_column = runner.find_last_column(row=runner.row)
        runner.column = row_last_column

        self.continue_column_seek()

    def do_step_down_seek(self):  # Vim j, ⌃J, ⌃N, Down  # Emacs next-line
        """Step down one Row or more, but seek the current Column"""

        runner = self.runner

        if self.seeking_column is None:
            self.seeking_column = runner.column

        self.step_down()

        runner.column = self.seek_column()
        self.continue_column_seek()

    def do_step_up_seek(self):  # Vim k, ⌃P, Up  # Emacs previous-line
        """Step up a Row or more, but seek the current Column"""

        runner = self.runner

        if self.seeking_column is None:
            self.seeking_column = runner.column

        self.step_up()

        runner.column = self.seek_column()
        self.continue_column_seek()

    def seek_column(self, column=True):
        """Begin seeking a Column, if not begun already"""

        runner = self.runner
        last_column = runner.find_last_column()

        if self.seeking_column is True:
            sought_column = last_column
        else:
            sought_column = min(last_column, self.seeking_column)

        return sought_column

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

        runner = self.runner

        row = runner.row
        top_row = runner.top_row
        runner = self.runner
        painter = runner.painter

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        bottom_row = runner.find_bottom_row()
        last_row = runner.find_last_row()

        # Quit at last Row

        if top_row == last_row:
            if not self.runner.doing_done:
                self.send_vi_reply("Did you mean ⌃B")  # G⌃F⌃F Egg

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

        runner.top_row = top_row

        # Choose new Row and Column

        if row < top_row:
            row = top_row

        runner.row = row

        self.slip_dent()

        runner.continue_do_loop()

    def do_scroll_behind_much(self):  # Vim ⌃B
        """Show the previous Screen of Rows"""

        runner = self.runner

        row = runner.row
        top_row = runner.top_row
        runner = self.runner
        painter = runner.painter

        last_row = runner.find_last_row()

        # Quit at top Row

        if not top_row:
            if not self.runner.doing_done:
                self.send_vi_reply("Did you mean ⌃F")  # 1G⌃B Egg

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

        runner.top_row = top_row

        # Choose new Row and Column

        bottom_row = runner.find_bottom_row()
        if row > bottom_row:
            runner.row = bottom_row

        self.slip_dent()

        runner.continue_do_loop()

    #
    # Scroll ahead or behind one Row of Screen
    #

    def do_scroll_ahead_one(self):  # Vim ⌃E
        """Show the next Row of Screen"""

        runner = self.runner

        row = runner.row
        top_row = runner.top_row

        runner = self.runner
        last_row = runner.find_last_row()

        # Quit at last Row

        if runner.top_row == last_row:
            if not runner.doing_done:
                self.send_vi_reply("Did you mean ⌃Y")  # G⌃F⌃E Egg

            return

        # Scroll ahead one

        if top_row < last_row:
            top_row += 1
            if row < top_row:
                row = top_row

        runner.top_row = top_row
        runner.row = row

        self.slip_dent()

        runner.continue_do_loop()

    def do_scroll_behind_one(self):  # Vim ⌃Y
        """Show the previous Row of Screen"""

        runner = self.runner

        row = runner.row
        top_row = runner.top_row

        # Quit at top Row

        if not top_row:

            if not runner.doing_done:
                self.send_vi_reply("Did you mean ⌃E")  # 1G⌃Y Egg

            return

        # Scroll behind one

        if top_row:
            top_row -= 1

            runner.top_row = top_row  # TODO: ugly mutate
            bottom_row = runner.find_bottom_row()

            if row > bottom_row:
                row = bottom_row

        runner.top_row = top_row
        runner.row = row

        self.slip_dent()

        runner.continue_do_loop()

    #
    # Scroll to move Cursor on Screen
    #

    def do_scroll_till_top(self):  # Vim zt
        """Scroll up or down till Cursor Row lands in Top Row of Screen"""

        runner = self.runner
        row = self.get_vi_arg1(runner.row)

        runner.top_row = row

    def do_scroll_till_middle(self):  # Vim zz  # not to be confused with Vim ZZ
        """Scroll up or down till Cursor Row lands in Middle Row of Screen"""

        runner = self.runner
        painter = runner.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows

        row = self.get_vi_arg1(runner.row)

        up = scrolling_rows // 2
        top_row = (row - up) if (row >= up) else 0

        runner.top_row = top_row

    def do_scroll_till_bottom(self):  # Vim zb
        """Scroll up or down till Cursor Row lands in Bottom Row of Screen"""

        runner = self.runner
        painter = runner.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows

        row = self.get_vi_arg1(runner.row)

        up = scrolling_rows - 1
        top_row = (row - up) if (row >= up) else 0

        runner.top_row = top_row

    #
    # Search ahead for an empty line
    #

    def do_paragraph_ahead(self):  # Vim {
        """Step down over Empty Lines, then over Non-Empty Lines"""

        runner = self.runner
        last_row = runner.find_last_row()

        if runner.doing_done:
            if (runner.row, runner.column) == (last_row, runner.find_last_column()):
                raise IndexError()

        while (runner.row < last_row) and not runner.find_last_column(row=runner.row):
            runner.row += 1
        while (runner.row < last_row) and runner.find_last_column(row=runner.row):
            runner.row += 1

        runner.column = runner.find_last_column(row=runner.row)

        runner.continue_do_loop()

    def do_paragraph_behind(self):  # Vim }

        runner = self.runner

        if runner.doing_done:
            if (runner.row, runner.column) == (0, 0):
                raise IndexError()

        while runner.row and not runner.find_last_column(row=runner.row):
            runner.row -= 1
        while runner.row and runner.find_last_column(row=runner.row):
            runner.row -= 1

        runner.column = 0

        runner.continue_do_loop()

    #
    # Step across Chars of CharSets
    #

    def do_big_word_end_ahead(self):  # Vim E

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        self.word_end_ahead(charsets)

        runner.continue_do_loop()

    def do_lil_word_end_ahead(self):  # Vim e

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        charsets.append(VI_SYMBOLIC_SET)

        self.word_end_ahead(charsets)

        runner.continue_do_loop()

    def word_end_ahead(self, charsets):

        runner = self.runner

        self.slip_ahead()

        while not runner.find_column_in_charsets(charsets):
            if not self.slip_ahead():

                break

        here = runner.find_column_in_charsets(charsets)
        if here:

            beyond = None
            while runner.find_column_in_charsets(charsets) == here:
                row_last_column = runner.find_last_column(row=runner.row)
                on_last_column = runner.column == row_last_column
                if not self.slip_ahead():
                    beyond = False

                    break

                beyond = True
                if on_last_column:

                    break

            if beyond:
                self.slip_behind()

    def do_big_word_start_ahead(self):  # Vim W

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        self.word_start_ahead(charsets)

        runner.continue_do_loop()

    def do_lil_word_start_ahead(self):  # Vim w

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        charsets.append(VI_SYMBOLIC_SET)
        self.word_start_ahead(charsets)

        runner.continue_do_loop()

    def word_start_ahead(self, charsets):

        runner = self.runner

        here = runner.find_column_in_charsets(charsets)
        if here:

            while runner.find_column_in_charsets(charsets) == here:
                row_last_column = runner.find_last_column(row=runner.row)
                on_last_column = runner.column == row_last_column
                if not self.slip_ahead():

                    break

                if on_last_column:

                    break

            if not runner.column:

                return

        while not runner.find_column_in_charsets(charsets):
            if not self.slip_ahead():

                break

    def do_big_word_start_behind(self):  # Vim B

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        self.word_start_behind(charsets)

        runner.continue_do_loop()

        # TODO: add option for 'b e w' and 'B E W' to swap places

    def do_lil_word_start_behind(self):  # Vim b

        runner = self.runner

        charsets = list()
        charsets.append(VI_BLANK_SET)
        charsets.append(VI_SYMBOLIC_SET)
        self.word_start_behind(charsets)

        runner.continue_do_loop()

    def word_start_behind(self, charsets):

        runner = self.runner

        self.slip_behind()

        on_first_column = runner.column == 0
        if not on_first_column:

            while not runner.find_column_in_charsets(charsets):
                if not self.slip_behind():

                    break

            here = runner.find_column_in_charsets(charsets)
            if here:

                beyond = None
                while runner.find_column_in_charsets(charsets) == here:
                    on_first_column = runner.column == 0
                    if not self.slip_behind():
                        beyond = False

                        break

                    beyond = True
                    if on_first_column:

                        break

                if beyond:
                    self.slip_ahead()

    #
    # Search ahead inside the Row for a single Char
    #

    def do_slip_index(self):  # Vim fx
        """Find Char to right in Row, once or more"""

        choice = self.get_vi_arg2()

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

        choice = self.get_vi_arg2()

        self.slip_choice = choice
        self.slip_after = -1
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index(self):
        """Find Char to Right in row, once or more"""

        runner = self.runner

        last_column = runner.find_last_column()
        text = runner.get_row_text()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_vi_arg1()

        # Index each

        column = runner.column

        for _ in range(count):

            self.check_index(column < last_column)
            column += 1

            try:
                right = text[column:].index(choice)
            except ValueError:
                raise ValueError("substring {!r} not found ahead".format(choice))
            column += right

        # Option to slip back one column

        if after:
            self.check_index(column)
            column -= 1

        runner.column = column

    #
    # Search behind inside the Row for a single Char
    #

    def do_slip_rindex(self):  # Vim Fx
        """Find Char to left in Row, once or more"""

        choice = self.get_vi_arg2()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def do_slip_rindex_plus(self):  # Vim Tx
        """Find Char to left in Row, once or more, but then slip right one Column"""

        choice = self.get_vi_arg2()

        self.slip_choice = choice
        self.slip_after = +1
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex(self):
        """Find Char to left in Row, once or more"""

        runner = self.runner

        last_column = runner.find_last_column()
        text = runner.get_row_text()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_vi_arg1()

        # R-Index each

        column = runner.column

        for _ in range(count):

            self.check_index(column)
            column -= 1

            try:
                column = text[: (column + 1)].rindex(choice)
            except ValueError:
                raise ValueError("substring {!r} not found behind".format(choice))

        # Option to slip right one column

        if after:

            self.check_index(column < last_column)
            column += 1

        runner.column = column

    #
    # Repeat search inside the Row for a single Char
    #

    def do_slip_choice_redo(self):  # Vim ;
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        runner = self.runner

        if self.slip_choice is None:
            self.send_vi_reply("Did you mean:  fx;")  # ; Egg
            self.send_vi_bell()

            return

        after = self.slip_after
        if not after:

            self.slip_redo()

        else:

            row_last_column = runner.find_last_column(row=runner.row)

            with_column = runner.column
            try:

                if after < 0:
                    assert runner.column < row_last_column
                    runner.column += 1
                elif after > 0:
                    assert runner.column
                    runner.column -= 1

                self.slip_redo()

                assert runner.column != with_column

            except Exception:
                runner.column = with_column

                raise

    def do_slip_choice_undo(self):  # Vim ,
        """Undo the last 'slip_index' or 'slip_rindex' once or more"""

        runner = self.runner

        if self.slip_choice is None:
            self.send_vi_reply("Did you mean:  Fx,")  # , Egg
            self.send_vi_bell()

            return

        after = self.slip_after
        if not after:

            self.slip_undo()

        else:

            row_last_column = runner.find_last_column(row=runner.row)

            with_column = runner.column
            try:

                if after < 0:
                    assert runner.column
                    runner.column -= 1
                elif after > 0:
                    assert runner.column < row_last_column
                    runner.column += 1

                self.slip_undo()

                assert runner.column != with_column

            except Exception:
                runner.column = with_column

                raise

    #
    # Map Keyboard Inputs to Code, for when feeling like Vi
    #

    def run_before_do_vi(self):
        """Run before each Vi Bot chosen by Chords"""

        # Default to stop remembering the last Seeking Column

        self.seeking_more = None

    def run_after_do_vi(self):
        """Run after each Vi Bot chosen by Chords"""

        # Remember the last Seeking Column across Bots that ask for it

        if not self.seeking_more:
            self.seeking_column = None

    def run_before_vi_prompt(self):
        """Run before Vi Prompt written"""

        runner = self.runner

        painter = runner.painter
        terminal = painter

        # Place the Screen Cursor

        terminal.row = runner.row - runner.top_row
        terminal.column = runner.column

        # Choose the Status to surface

        str_reply = runner.format_vi_reply()
        runner.reply = TerminalReplyOut()

        return str_reply

    def _vi_bots_by_chords_(self):
        """Map Keyboard Inputs to Code, for when feeling like Vi"""

        runner = self.runner

        bots_by_chords = dict()

        bots_by_chords[None] = (self.do_raise_vi_name_error,)

        bots_by_chords[False] = (self.run_before_do_vi,)
        bots_by_chords[True] = (self.run_after_do_vi,)
        bots_by_chords[""] = (self.run_before_vi_prompt,)
        # TODO: ok yes callbacks, but less of kluge than wild types for keys

        # bots_by_chords[b"\x00"]  # NUL, aka ⌃@, aka 0
        # bots_by_chords[b"\x01"]  # SOH, aka ⌃A, aka 1
        bots_by_chords[b"\x02"] = (self.do_scroll_behind_much,)  # STX, aka ⌃B, aka 2
        bots_by_chords[b"\x03"] = (self.do_help_quit_vi,)  # ETX, aka ⌃C, aka 3
        bots_by_chords[b"\x04"] = (self.do_scroll_ahead_some,)  # EOT, aka ⌃D, aka 4
        bots_by_chords[b"\x05"] = (self.do_scroll_ahead_one,)  # ENQ, aka ⌃E, aka 5
        bots_by_chords[b"\x06"] = (self.do_scroll_ahead_much,)  # ACK, aka ⌃F, aka 6
        bots_by_chords[b"\x07"] = (runner.do_give_more_status,)  # BEL, aka ⌃G, aka 7 \a
        # bots_by_chords[b"\x08"]  # BS, aka ⌃H, aka 8 \b
        # bots_by_chords[b"\x09"]  # TAB, aka ⌃I, aka 9 \t
        bots_by_chords[b"\x0A"] = (self.do_step_down_seek,)  # LF, aka ⌃J, aka 10 \n
        # bots_by_chords[b"\x0B"]  # VT, aka ⌃K, aka 11 \v
        bots_by_chords[b"\x0C"] = (runner.do_redraw,)  # FF, aka ⌃L, aka 12 \f
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
        bots_by_chords[b"\x1A"] = (self.do_vi_sig_tstp,)  # SUB, aka ⌃Z, aka 26

        bots_by_chords[b"\x1B"] = (self.do_c0_control_esc,)  # ESC, aka ⌃[, aka 27
        bots_by_chords[b"\x1B[A"] = (self.do_step_up_seek,)  # ↑ Up Arrow
        bots_by_chords[b"\x1B[B"] = (self.do_step_down_seek,)  # ↓ Down Arrow
        bots_by_chords[b"\x1B[C"] = (self.do_slip_right,)  # → Right Arrow
        bots_by_chords[b"\x1B[D"] = (self.do_slip_left,)  # ← Left Arrow

        # bots_by_chords[b"\x1C"] = (self.do_eval_vi_line,)   # FS, aka ⌃\, aka 28
        # bots_by_chords[b"\x1D"]  # GS, aka ⌃], aka 29
        # bots_by_chords[b"\x1E"]  # RS, aka ⌃^, aka 30  # try this after edit in: |vi -
        # bots_by_chords[b"\x1F"]  # US, aka ⌃_, aka 31

        bots_by_chords[b" "] = (self.do_slip_ahead,)
        # bots_by_chords[b"!"] = (self.do_pipe,)
        # bots_by_chords[b'"'] = (self.do_arg,)
        bots_by_chords[b"#"] = (self.do_find_behind_this,)
        bots_by_chords[b"$"] = (self.do_slip_last_seek,)
        # bots_by_chords[b"%"]  # TODO: leap to match
        # bots_by_chords[b"&"]  # TODO: & and && for repeating substitution
        # bots_by_chords[b"'"]  # TODO: leap to pin
        # bots_by_chords[b"("]  # TODO: sentence behind
        # bots_by_chords[b")"]  # TODO: sentence ahead
        bots_by_chords[b"*"] = (self.do_find_ahead_this,)
        bots_by_chords[b"+"] = (self.do_step_down_dent,)
        bots_by_chords[b","] = (self.do_slip_choice_undo,)
        bots_by_chords[b"-"] = (self.do_step_up_dent,)
        bots_by_chords[b"/"] = (self.do_find_ahead_vi_line,)

        bots_by_chords[b"0"] = (self.do_slip_first,)
        bots_by_chords[b"1234567890"] = None

        bots_by_chords[b":"] = None

        bots_by_chords[b":n"] = None
        bots_by_chords[b":n\r"] = (self.do_next_vi_file,)

        bots_by_chords[b":no"] = None
        bots_by_chords[b":noh"] = None
        bots_by_chords[b":noh\r"] = (self.do_invhlsearch,)

        bots_by_chords[b":q"] = None
        bots_by_chords[b":q\r"] = (self.do_might_quit_vi,)

        bots_by_chords[b":q!"] = None
        bots_by_chords[b":q!\r"] = (self.do_quit_vi,)

        bots_by_chords[b":w"] = None
        bots_by_chords[b":w\r"] = (self.do_might_flush_vi,)

        bots_by_chords[b":w!\r"] = (self.do_flush_vi,)

        bots_by_chords[b":wq"] = None
        bots_by_chords[b":wq\r"] = (self.do_might_flush_quit_vi,)

        bots_by_chords[b":wq!"] = None
        bots_by_chords[b":wq!\r"] = (self.do_flush_quit_vi,)

        bots_by_chords[b";"] = (self.do_slip_choice_redo,)
        # bots_by_chords[b"<"]  # TODO: dedent
        # bots_by_chords[b"="]  # TODO: dent after
        # bots_by_chords[b">"]  # TODO: indent
        bots_by_chords[b"?"] = (self.do_find_behind_vi_line,)
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
        bots_by_chords[b"N"] = (self.do_find_earlier,)
        # bots_by_chords[b"O"] = (self.do_slip_first_open,)
        # bots_by_chords[b"P"] = (self.do_paste_behind,)

        bots_by_chords[b"Q"] = None
        bots_by_chords[b"Qv"] = None
        bots_by_chords[b"Qvi"] = None
        bots_by_chords[b"Qvi\r"] = (self.do_continue_vi,)

        # bots_by_chords[b"R"] = (self.do_open_overwrite,)
        # bots_by_chords[b"S"] = (self.do_slip_first_chop_open,)
        bots_by_chords[b"T"] = (None, self.do_slip_rindex_plus)
        # bots_by_chords[b"U"] = (self.do_row_undo,)
        # bots_by_chords[b"V"] = (self.do_mark_rows,)
        bots_by_chords[b"W"] = (self.do_big_word_start_ahead,)
        # bots_by_chords[b"X"] = (self.do_cut_behind,)
        # bots_by_chords[b"Y"] = (self.do_copy_row,)

        bots_by_chords[b"Z"] = None
        bots_by_chords[b"ZQ"] = (self.do_quit_vi,)
        bots_by_chords[b"ZZ"] = (self.do_flush_quit_vi,)

        # bots_by_chords[b"["]  # TODO

        bots_by_chords[b"\\"] = None
        bots_by_chords[b"\\\x1B"] = (self.do_invhlsearch,)
        bots_by_chords[b"\\F"] = (self.do_set_invregex,)
        bots_by_chords[b"\\i"] = (self.do_set_invignorecase,)
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
        bots_by_chords[b"n"] = (self.do_find_later,)
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
        bots_by_chords[b"zb"] = (self.do_scroll_till_bottom,)
        bots_by_chords[b"zt"] = (self.do_scroll_till_top,)
        bots_by_chords[b"zz"] = (self.do_scroll_till_middle,)

        bots_by_chords[b"{"] = (self.do_paragraph_behind,)
        bots_by_chords[b"|"] = (self.do_slip,)
        bots_by_chords[b"}"] = (self.do_paragraph_ahead,)
        # bots_by_chords[b"~"] = (self.do_flip_case_overwrite,)

        bots_by_chords[b"\x7F"] = (self.do_slip_behind,)  # DEL, aka ⌃?, aka 127

        bots_by_chords["£".encode()] = (self.do_find_behind_this,)  # \u00A3 Pound Sign

        return bots_by_chords


#
# Edit some Chars in the Bottom Lines of the Screen
#


class TerminalEx:
    """Feed Keyboard into Line at Bottom of Screen of Scrolling Rows, a la Ex"""

    def __init__(self, runner):

        self.runner = runner

        self.ex_head = None
        self.ex_line = None

        self.ex_flags = ""

    def format_ex_reply(self):

        ex_head = self.ex_head
        ex_flags = self.ex_flags
        ex_line = self.ex_line

        word0 = ex_head.split()[0]
        dashed_ex_flags = "-" + ex_flags
        repl = word0 + "  " + dashed_ex_flags

        ex_head_repl = ex_head
        if ex_flags:
            count = 1
            ex_head_repl = ex_head.replace(word0, repl, count)

        str_reply = ex_head_repl + ex_line

        return str_reply

    def read_ex_line(self):
        """Take an Input Line from beneath the Scrolling Rows"""

        try:
            self.run_ex_keyboard()
            assert False  # unreached
        except SystemExit:
            pass

        line = self.ex_line

        return line

    def run_ex_keyboard(self):
        """Edit an Input Line beneath the Scrolling Rows"""

        runner = self.runner

        ex_flags = ""
        if not runner.finding_regex:
            ex_flags += "F"
        if not runner.finding_case:
            ex_flags += "i"
        if runner.showing_line_number:
            ex_flags += "n"
        self.ex_flags = ex_flags

        self.ex_head = runner.format_vi_reply()
        self.ex_line = ""

        bots_by_chords = self._ex_bots_by_chords_()
        runner.run_keyboard(bots_by_chords)
        assert False  # unreached

    def do_clear_chars(self):  # Vim Ex ⌃U
        """Undo all the Append Chars, if any Not undone already"""

        self.ex_line = ""

    def do_append_char(self):
        """Append the Chords to the Input Line"""

        runner = self.runner
        chords = runner.get_arg0()

        chars = chords.decode(errors="surrogateescape")

        if chars == "£":  # TODO: less personal choice
            self.ex_line += "#"  # a la Vim :abbrev £ #
        else:
            self.ex_line += chars

    def do_append_suffix(self):  # Vim Ex ⌃V
        """Append the Suffix Chord to the Input Line"""

        raise NotImplementedError()

        chars = self.runner.arg2

        self.ex_line += chars

    def do_undo_append_char(self):
        """Undo the last Append Char, else Quit Ex"""

        ex_line = self.ex_line
        if ex_line:
            self.ex_line = ex_line[:-1]
        else:
            self.ex_line = None

            sys.exit()

    def do_raise_ex_name_error(self):  # such as ⌃D
        """Reply to meaningless Keyboard Input"""

        self.runner.raise_chords_as_name_error()

    def do_quit_ex(self):  # Vim Ex ⌃C

        self.ex_line = None

        sys.exit()

    def do_save_and_quit_ex(self):  # Vim Ex ⌃M
        """Place the Screen Cursor, like while prompting for more Chords"""

        sys.exit()

    def run_before_ex_prompt(self):
        """Place the Screen Cursor, like while prompting for more Chords"""

        runner = self.runner

        painter = runner.painter
        terminal = painter

        # Place the Screen Cursor

        str_reply = self.format_ex_reply()

        terminal.row = painter.status_row
        terminal.column = len(str_reply)

        # Replace the Status

        return str_reply

    def _ex_bots_by_chords_(self):

        bots_by_chords = dict()

        bots_by_chords[None] = (self.do_raise_ex_name_error,)
        bots_by_chords[""] = (self.run_before_ex_prompt,)

        for chords in sorted(C0_CONTROL_STDINS):
            bots_by_chords[chords] = (self.do_raise_ex_name_error,)

        bots_by_chords[b"\x03"] = (self.do_quit_ex,)  # ETX, aka ⌃C, aka 3
        bots_by_chords[b"\x0D"] = (self.do_save_and_quit_ex,)  # CR, aka ⌃M, aka 13 \r
        bots_by_chords[b"\x15"] = (self.do_clear_chars,)  # NAK, aka ⌃U, aka 21
        bots_by_chords[b"\x16"] = (None, self.do_append_suffix)  # SYN, aka ⌃V, aka 22

        for xx in range(0x80):
            chords = chr(xx).encode()
            if chords not in C0_CONTROL_STDINS:
                bots_by_chords[chords] = (self.do_append_char,)

        bots_by_chords["£".encode()] = (self.do_append_char,)

        bots_by_chords[b"\x7F"] = (self.do_undo_append_char,)  # DEL, aka ⌃?, aka 127

        # TODO: define Esc to replace live Regex punctuation with calmer r"."
        # TODO: search for more than US Ascii

        return bots_by_chords


#
# Define the Editors above in terms of Inputs, Outputs, & Selections of Chars
#


class TerminalNudgeIn(argparse.Namespace):
    """Take the Keyboard Chords of one Input"""

    def __init__(self, prefix=None, chords=None, suffix=None, epilog=None):

        self.prefix = prefix
        self.chords = chords
        self.suffix = suffix
        self.epilog = epilog

    def add_epilog(self, epilog):
        """Add more Chords to echo, Chords that came later"""

        assert self.epilog is None
        self.epilog = epilog

    def join_echo_bytes(self):
        """Echo all the Chords of this one Input, in order"""

        echo = b""

        if self.prefix is not None:
            echo += self.prefix
        if self.chords is not None:
            echo += self.chords
        if self.suffix is not None:
            echo += self.suffix
        if self.epilog is not None:
            echo += self.epilog

        return echo


class TerminalReplyOut(argparse.Namespace):
    """Give the parts of a Reply to Input, apart from the main Output"""

    def __init__(self, nudge=None, message=None):

        self.nudge = nudge
        self.message = message

    # 'class TerminalReplyOut' could become an immutable 'collections.namedtuple'
    # because Jun/2018 Python 3.7 can say '._defaults=(None, None),'


class TerminalSpan(
    collections.namedtuple("TerminalSpan", "row, column, beyond".split(", "))
):
    """Pick out the Columns of Rows covered by a Match of Chars"""

    @staticmethod
    def find_spans(matches):
        """Quickly calculate the Row and Column of each of a List of Spans"""

        if not matches:

            return list()

        # Split the Lines apart

        some_match = matches[-1]

        chars = some_match.string
        lines = chars.splitlines(keepends=True)

        # Search each Line for the next Match

        spanned_lines = list()
        spanned_chars = ""

        spans = list()
        for match in matches:
            assert match.string is some_match.string

            start = match.start()
            while start > len(spanned_chars):
                line = lines[len(spanned_lines)]

                spanned_lines.append(line)
                spanned_chars += line

            # Find the Row of the Match, in or beyond the Spanned Lines

            row = 0
            line_at = 0
            if spanned_lines:
                row = len(spanned_lines) - 1
                line_at = len(spanned_chars) - len(spanned_lines[-1])
                if start == len(spanned_chars):
                    row = len(spanned_lines)
                    line_at = len(spanned_chars)

            # Find the Column of the Match

            column = start - line_at
            beyond = column + (match.end() - match.start())

            # Collect this Span

            span = TerminalSpan(row, column=column, beyond=beyond)
            spans.append(span)

        # Silently drop the extra Match past the last Line,
        # to duck out of the case of an extra Match past the End of the last Line
        # as per: list(re.finditer(r"$", string="a\n\nz\n", flags=re.MULTILINE))

        if spans:

            last_span = spans[-1]
            if last_span.row >= len(lines):

                del spans[-1]

        return spans


class TerminalRunner:
    """Loop on Keyboard Chords, not whole Lines, but then do read-eval-print"""

    def __init__(self):

        self.painter = None  # layer over a Terminal I/O Stack
        self.shadow = None
        self.driver = None
        self.stdio = None

        self.showing_line_number = None  # show Line Numbers or not
        self.injecting_lag = None  # inject extra Lag or not

        self.bots_by_chords = None  # map Keyboard Inputs to Code

        self.finding_case = None  # ignore Upper/Lower Case in Searching or not
        self.finding_line = None  # remember the Search Key
        self.finding_regex = None  # search as Regex or search as Chars
        self.finding_slip = 0  # remember to Search again ahead or again behind
        self.highlighting_matches = None  # highlight all spans on screen or no spans

        self.nudge = TerminalNudgeIn()  # split the Chords of one Keyboard Input
        self.arg0 = None  # take all the Chords as Chars in a Row
        self.arg1 = None  # take the Prefix Bytes as an Int of Decimal Digits
        self.arg2 = None  # take the Suffix Bytes as one Encoded Char

        self.sending_bell = None  # ring the Terminal Bell as part of some Prompt's
        self.reply = TerminalReplyOut()  # declare an empty Reply

        self.doing_more = None  # take the Arg1 as a Count of Repetition's
        self.doing_done = None  # count the Repetition's completed before now

    def reopen_iobytearray(self, iobytearray):
        "Start editing Lines of Columns, given a File of Bytes" ""

        self.iobytearray = iobytearray

        chars = iobytearray.decode(errors="surrogateescape")
        lines = chars.splitlines(keepends=True)
        self.lines = lines  # view a copy of a File of Chars encoded as Bytes

        self.traceback = None  # capture Python Tracebacks

        self.row = 0  # point the Screen Cursor to a Row of File
        self.column = 0  # point the Screen Cursor to a Column of File

        self.top_row = 0  # scroll through more Lines than fit on Screen

        self.finding_spans = list()  # cache the spans in file
        self.reopen_finding_spans()

    def run_terminal(self, bots_by_chords):
        """Enter Terminal Driver, then run Keyboard, then exit Terminal Driver"""

        stdio = sys.stderr
        with TerminalDriver(terminal=stdio) as driver:
            shadow = TerminalShadow(terminal=driver)
            painter = TerminalPainter(terminal=shadow)

            self.painter = painter
            self.shadow = shadow
            self.driver = driver
            self.stdio = stdio

            self.run_keyboard(bots_by_chords)  # till SystemExit

    def run_keyboard(self, bots_by_chords):
        """Prompt, take input, react, repeat till quit"""

        terminal = self.painter

        # Repeat till SystemExit raised

        while True:

            # Choose keyboard

            self.bots_by_chords = bots_by_chords

            # Scroll and prompt

            self.scroll_cursor_into_screen()

            self.prompt_for_chords()

            # Take one Chord in, or next Chord, or cancel Chords to start again

            try:
                chord = terminal.getch()
            except KeyboardInterrupt:
                chord = b"\x03"  # ETX, aka ⌃C, aka 3

                if self.nudge != TerminalNudgeIn():
                    self.nudge.add_epilog(epilog=chord)
                    self.send_reply("Cancelled")  # 123⌃C Egg, f⌃C Egg, etc

                    self.nudge = TerminalNudgeIn()

                    continue

            bot = self.choose_bot(chord)
            if bot is None:

                continue

            # Reply

            if False in bots_by_chords.keys():
                before_bots = bots_by_chords[False]  # callback to Client
                assert len(before_bots) == 1, (before_bots,)
                before_bots[-1]()

            self.call_bot(bot)  # reply to one whole Nudge

            if True in bots_by_chords.keys():
                after_bots = bots_by_chords[True]  # callback to Client
                assert len(after_bots) == 1, (after_bots,)
                after_bots[-1]()

            self.nudge = TerminalNudgeIn()  # consume the whole Nudge

    def scroll_cursor_into_screen(self):
        """Scroll to place Cursor on Screen"""

        row = self.row
        painter = self.painter
        top_row = self.top_row

        # Keep the choice of Top Row on File

        if not (0 <= top_row < len(self.lines)):
            self.top_row = 0

        # Scroll behind to get Cursor on Screen, if need be

        if row < self.top_row:
            self.top_row = row

        # Scroll ahead to get Cursor on Screen, if need be

        bottom_row = self.find_bottom_row()
        if row > bottom_row:
            self.top_row = row - (painter.scrolling_rows - 1)

        # After fixing the choice, assert the Top Row always was on File

        if not (0 <= top_row < len(self.lines)):
            raise KwArgsException(before=top_row, after=self.top_row)

    def prompt_for_chords(self):
        """Write over the Rows of Chars on Screen"""

        painter = self.painter
        terminal = painter

        # Call back to Client

        run_before_prompt = self.bots_by_chords[""][-1]  # TODO: cope with len != 1?
        str_reply = run_before_prompt()

        # Pull from Self

        lines = self.lines
        screen_lines = lines[self.top_row :][: painter.scrolling_rows]
        screen_spans = self.find_spans_on_screen()

        injecting_lag = self.injecting_lag
        sending_bell = self.sending_bell

        # Push into the Terminal

        painter.top_line_number = 1 + self.top_row
        painter.last_line_number = 1 + len(lines)
        painter.showing_line_number = self.showing_line_number

        # Choose more or less Accuracy & Lag

        if not injecting_lag:
            if sending_bell:
                # time.sleep(0.3)  # delaying Output demos a different kind of lag
                terminal._reopen_terminal_()

        painter.write_screen(status=str_reply, lines=screen_lines, spans=screen_spans)

        if sending_bell:
            self.sending_bell = None
            painter.write_bell()

        terminal.flush()

    def find_spans_on_screen(self):
        """Mark some Chars on Screen as more equal than others"""

        if not self.highlighting_matches:

            return list()

        finding_spans = self.finding_spans
        top_row = self.top_row
        bottom_row = self.find_bottom_row()

        screen_spans = list()
        for span in finding_spans:
            if top_row <= span.row <= bottom_row:

                screen_span_row = span.row - top_row
                screen_span = TerminalSpan(
                    screen_span_row, column=span.column, beyond=span.beyond
                )
                screen_spans.append(screen_span)

        return screen_spans

    def choose_bot(self, chord):
        """Accept one Keyboard Input into Prefix, into main Chords, or as Suffix"""

        prefix = self.nudge.prefix
        chords = self.nudge.chords

        bots_by_chords = self.bots_by_chords

        assert self.nudge.suffix is None, (chords, chord)  # one Chord only

        # Accept a Prefix of Digits

        if b"1234567890" in bots_by_chords.keys():
            if not chords:
                if (chord in b"123456789") or (prefix and (chord == b"0")):

                    prefix_plus = chord if (prefix is None) else (prefix + chord)
                    self.nudge.prefix = prefix_plus
                    self.send_reply(message=None)

                    return None  # ask for more Prefix, else for main Chords

        self.arg1 = int(prefix) if prefix else None
        assert self.get_arg1() >= 1

        # Accept one or more Chords

        bots = bots_by_chords.get(chords)
        if not (bots and (len(bots) != 1)):

            chords_plus = chord if (chords is None) else (chords + chord)
            self.nudge.chords = chords_plus
            self.send_reply(message=None)

            default_bots = bots_by_chords[None]  # such as 'self.do_raise_'

            self.arg0 = chords_plus
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

        assert self.arg0 == chords, (chords, chord, self.arg0)

        # Accept one last Chord as the Suffix

        suffix = chord
        self.nudge.suffix = suffix
        self.send_reply(message=None)

        self.arg2 = suffix.decode(errors="surrogateescape")

        # Call a Bot with Suffix, but with or without Prefix

        bot = bots[-1]
        assert bot is not None, (chords, chord)

        return bot

    def call_bot(self, bot):
        """Call the Bot once or more, in reply to one Terminal Nudge In"""

        # Start calling

        self.doing_done = 0
        while True:
            self.doing_more = None

            try:

                bot()
                self.keep_cursor_on_file()
                self.traceback = None

            # Stop calls on Exception

            except Exception as exc:

                name = type(exc).__name__
                str_exc = str(exc)
                message = "{}: {}".format(name, str_exc) if str_exc else name

                self.traceback = traceback.format_exc()

                self.send_reply(message)  # Egg of NotImplementedError
                self.send_bell()

                break

            # Let the Bot take the Arg as a Count of Repetitions

            if self.doing_more:
                self.doing_done += 1
                if self.doing_done < self.get_arg1():

                    continue

            break

    def raise_chords_as_name_error(self):
        """Reply to meaningless Keyboard Input"""

        echo_bytes = self.nudge.join_echo_bytes()  # similar or same as 'self.arg0'

        escapes = ""
        for xx in echo_bytes:
            escapes += r"\x{:02X}".format(xx)

        arg = "b'{}'".format(escapes)
        raise NameError(arg)

    def send_reply(self, message):
        """Capture some Status now, to show with next Prompt"""

        nudge = self.nudge

        self.reply = TerminalReplyOut(nudge=nudge, message=message)

    def format_vi_reply(self):  # TODO: move this to TerminalVi from TerminalRunner
        """Show Row, Column, Nudge, & Message"""

        reply = self.reply
        nudge = reply.nudge

        # Format parts, a la Vim ':set showcmd' etc

        row_number = 1 + self.row
        column_number = 1 + self.column

        echo_bytes = b"" if (nudge is None) else nudge.join_echo_bytes()
        str_echo = repr_vi_bytes(echo_bytes) if echo_bytes else ""

        str_message = str(reply.message) if reply.message else ""

        # Join parts

        str_reply = "{},{}  {}  {}".format(
            row_number, column_number, str_echo, str_message
        ).rstrip()

        return str_reply

    def send_bell(self):
        """Ring the Terminal Bell as part of the next Prompt"""

        self.sending_bell = True

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.arg1' times"""

        self.doing_more = True

    #
    # Take the Args as given, or substitute a Default Arg Value
    #

    def get_arg0(self):
        """Get the Bytes of the input Chords"""

        arg0 = self.arg0
        assert arg0 is not None

        return arg0

    def get_arg1(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        arg1 = self.arg1
        arg1 = default if (arg1 is None) else arg1

        return arg1

    def get_arg2(self):
        """Get the Bytes of the input Suffix past the input Chords"""

        arg2 = self.arg2
        assert arg2 is not None

        return arg2

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

    def get_column_char(self, column=None):
        """Get the one Char at the Column in the Row beneath the Cursor"""

        chosen_column = self.column if (column is None) else column

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]
        chars = row_text[chosen_column:][:1]

        return chars  # 0 or 1 chars

    def get_row_text(self):
        """Get Chars of Columns in Row beneath Cursor"""

        row_line = self.lines[self.row]
        row_text = row_line.splitlines()[0]

        return row_text

    def count_columns_in_row(self):
        """Count Columns in Row beneath Cursor"""

        lines = self.lines
        row = self.row

        if row >= len(lines):
            raise IndexError(row)

        row_line = lines[row]
        row_text = row_line.splitlines()[0]

        columns = len(row_text)

        return columns

    def count_rows_in_file(self):
        """Count Rows in Buffer of File"""

        rows = len(self.lines)

        return rows

    def find_bottom_row(self):
        """Find the Bottom Row of File on Screen"""

        painter = self.painter

        rows = len(self.lines)
        last_row = (rows - 1) if rows else 0

        bottom_row = self.top_row + (painter.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def find_last_row(self):
        """Find the last Row in File, else Row Zero when no Rows in File"""

        rows = len(self.lines)
        last_row = (rows - 1) if rows else 0

        return last_row

    def find_last_column(self, row=None):
        """Find the last Column in Row, else Column Zero when no Columns in Row"""

        chosen_row = self.row if (row is None) else row
        lines = self.lines

        if chosen_row >= len(lines):
            raise IndexError(row)

        row_line = lines[chosen_row]
        row_text = row_line.splitlines()[0]

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
        columns = 0 if (not rows) else self.count_columns_in_row()

        # Keep the choice of Row and Column on File

        before = (row, column)

        if not ((0 <= row < rows) or (row == rows == 0)):
            row = 0
        if not ((0 <= column < columns) or (column == columns == 0)):
            column = 0

        self.row = row
        self.column = column

        # After fixing the choice, assert the Row and Column always were on File

        after = (row, column)
        if before != after:
            raise KwArgsException(before=before, after=after)

    #
    # Define keys for entering, pausing, and exiting TerminalRunner
    #

    def do_redraw(self):  # Vim ⌃L
        """Toggle betwene more and less Lag (vs Vim injects lots of Lag exactly once)"""

        painter = self.painter

        injecting_lag = not self.injecting_lag
        if injecting_lag:
            painter.terminal = self.driver
        else:
            painter.terminal = self.shadow
            painter._reopen_terminal_()

        self.injecting_lag = injecting_lag

        message = ":set _lag_" if injecting_lag else ":set no_lag_"
        self.send_reply(message)

    def do_give_more_status(self):  # Vim ⌃G
        """Toggle betwene more and less Lag (vs Vim injects lots of Lag exactly once)"""

        injecting_lag = self.injecting_lag

        message = ":set _lag_" if injecting_lag else ":set no_lag_"
        self.send_reply(message)

        # TODO: echo $(whoami)@$(hostname):$(pwd)/

    def do_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        terminal = self.painter

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        terminal.__exit__(*exc_info)
        os.kill(os.getpid(), signal.SIGTSTP)
        terminal.__enter__()

    #
    # Find Spans of Chars
    #

    def reopen_finding_spans(self):
        """Find Chars in File"""

        iobytearray = self.iobytearray
        finding_spans = self.finding_spans

        # Cancel the old Spans

        finding_spans.clear()

        # Find the New Spans

        if self.finding_line is not None:

            pattern = self.finding_line
            if not self.finding_regex:
                pattern = re.escape(pattern)

            flags = 0
            flags |= re.MULTILINE
            if not self.finding_case:
                flags |= re.IGNORECASE

            chars = iobytearray.decode(errors="surrogateescape")
            matches = list(re.finditer(pattern, string=chars, flags=flags))
            finding_spans[::] = TerminalSpan.find_spans(matches)

            if matches:  # as many Spans as Matches, except for such as r"$" in "abc\n"
                assert finding_spans
                assert len(finding_spans) in (len(matches), len(matches) - 1)

    def find_ahead(self):
        """Find the Search Key ahead, else after start, else fail"""

        spans = self.finding_spans
        row = self.row
        column = self.column

        if not spans:

            self.send_reply("No chars found: not ahead and not behind")

            return False

        else:

            here0 = (row, column)
            here1 = (-1, -1)  # before start
            heres = (here0, here1)

            message0 = "Found {} chars ahead"
            message1 = "Found {} chars, not ahead, found instead after start"
            messages = (message0, message1)

            for (here, message) in zip(heres, messages):
                for span in spans:
                    len_chars = span.beyond - span.column
                    there = self.find_row_column_near_span(span)

                    if here < there:
                        self.send_reply(message.format(len_chars))

                        (self.row, self.column) = there

                        return True

            assert False, spans  # unreached

    def find_behind(self):
        """Find the Search Key behind, else above bottom, else fail"""

        spans = self.finding_spans
        row = self.row
        column = self.column

        if not spans:

            self.send_reply("No chars found: not behind and not ahead")

            return False

        else:

            here0 = (row, column)
            here1 = (self.find_last_row() + 1, 0)  # after end
            heres = (here0, here1)

            message0 = "Found {} chars behind"
            message1 = "Found {} chars, not behind, found instead before end"
            messages = (message0, message1)

            for (here, message) in zip(heres, messages):
                for span in reversed(spans):
                    len_chars = span.beyond - span.column
                    there = self.find_row_column_near_span(span)

                    if there < here:
                        self.send_reply(message.format(len_chars))

                        (self.row, self.column) = there

                        return True

            assert False, spans  # unreached

    def find_row_column_near_span(self, span):
        """Find the Row:Column in File nearest to a Span"""

        try:

            there_row = span.row
            there_last_column = self.find_last_column(row=there_row)
            there_column = min(there_last_column, span.column)
            there = (there_row, there_column)

        except IndexError:

            raise IndexError(span)

        return there


#
# Stack the I/O of a Terminal
# as TerminalPainter > TerminalShadow > TerminalDriver
#


class TerminalPainter:
    """Paint a Screen of Rows of Chars"""

    def __init__(self, terminal):

        self.terminal = terminal  # layer over a TerminalShadow

        self.rows = None  # count Rows on Screen
        self.columns = None  # count Columns per Row
        self.scrolling_rows = None  # divide the Screen into Scrolling Rows and Status

        self.row = 0  # point the Screen Cursor to a Row of File
        self.column = 0  # point the Screen Cursor to a Column of File

        self.top_line_number = 1  # number the Rows of the Screen down from first
        self.last_line_number = 1  # number all Rows as wide as the last
        self.showing_line_number = None  # start each Row with its Line Number, or don't

        self._reopen_terminal_()  # start sized to fit the initial Screen

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.terminal.__enter__()
        self._reopen_terminal_()

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        self.terminal.__exit__(exc_type, exc_value, traceback)  # positional args

    def pdb_set_trace(self):
        """Visit Pdb, if Stdin is Tty, else raise 'bdb.BdbQuit'"""

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        self.__exit__(*exc_info)
        pdb.set_trace()
        self.__enter__()

    def _reopen_terminal_(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        terminal_size = terminal._reopen_terminal_()  # a la os.get_terminal_size(fd)

        (columns, rows) = (terminal_size.columns, terminal_size.lines)
        assert rows >= 1
        assert columns >= 1
        self.rows = rows
        self.columns = columns

        self.scrolling_rows = rows - 1  # reserve last 1 line for Status
        self.status_row = self.scrolling_rows

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

    def getch(self):
        """Block to return next Keyboard Input, else raise KeyboardInterrupt"""

        chord = self.terminal.getch()

        if chord == b"\x03":
            raise KeyboardInterrupt()

        return chord

    def write_screen(self, status, lines, spans):
        """Write over the Rows of Chars on Screen"""

        terminal = self.terminal

        columns = self.columns
        left_column = self.find_left_column()
        scrolling_rows = self.scrolling_rows

        # Format chars to display

        texts = list(_.splitlines()[0] for _ in lines)

        for (row, text) in enumerate(texts):
            texts[row] = text
        while len(texts) < scrolling_rows:
            texts.append("~")

        assert len(texts) == scrolling_rows, (len(texts), scrolling_rows)

        for (row, text) in enumerate(texts):
            str_line_number = self.format_as_line_number(row)
            numbered_and_chopped = (str_line_number + text)[:columns]
            if row < len(lines):
                texts[row] = numbered_and_chopped

        # Write the formatted chars

        terminal.write(ED_2)
        terminal.write(CUP_1_1)

        for (row, text) in enumerate(texts):
            (styled, text_plus) = self.style_text(row, text=text, spans=spans)
            if len(text_plus) < columns:
                terminal.write(styled + "\r\n")
            else:
                terminal.write(styled)  # depend on automagic "\r\n" after Last Column

        # Show status, inside the last Row
        # but don't write over the Lower Right Char  # TODO: test vs xterm autoscroll

        str_status = "" if (status is None) else str(status)
        status_columns = columns - 1
        status_row_text = str_status[:status_columns].ljust(status_columns)
        terminal.write(status_row_text)

        # Place the cursor

        y = 1 + self.row
        x = 1 + left_column + self.column
        terminal.write(CUP_Y_X.format(y, x))

    def write_bell(self):
        """Ring the Terminal bell"""

        self.terminal.write("\a")

    def find_left_column(self):
        """Find the leftmost Column occupied by Scrolling Text"""

        formatted = self.format_as_line_number(row=1)
        left_column = len(formatted)

        return left_column

    def format_as_line_number(self, row):
        """Format a Row Index on Screen as a Line Number of File"""

        if not self.showing_line_number:

            return ""

        last_line_number = "{:3} ".format(self.last_line_number)
        last_width = len(last_line_number)

        line_number = self.top_line_number + row
        formatted = "{:3} ".format(line_number).rjust(last_width)

        return formatted

    def style_text(self, row, text, spans):
        """Inject SGR_7 and SGR to style the Text of a Row"""

        # Work only inside this Row

        (row_spans, text_plus) = self.spread_spans(row, text=text, spans=spans)

        # Add one empty Span beyond the end, to place all Chars between Spans

        beyond = len(text_plus)
        empty_beyond_span = TerminalSpan(row, column=beyond, beyond=beyond)

        row_spans_plus = list(row_spans)
        row_spans_plus.append(empty_beyond_span)

        # Visit the Chars between each pair of Spans, and the Chars of the Spans

        visited = 0
        lit = False

        styled = ""
        for span in row_spans_plus:

            # Write the Chars before this Span, as default SGR

            if visited < span.column:

                fragment = text_plus[visited : span.column]

                styled += SGR if lit else ""
                styled += fragment

                lit = False
                visited = span.column

            # Write the Chars of this Span, as SGR_7

            if span.column < span.beyond:

                fragment = text_plus[span.column : span.beyond]

                styled += "" if lit else SGR_7
                styled += fragment

                lit = True
                visited = span.beyond

        # Add a last SGR to close the last SGR_7, if need be

        styled += SGR if lit else ""

        return (styled, text_plus)

    def spread_spans(self, row, text, spans):
        """Spread each Empty Span to cover one more Column beyond it"""

        columns = self.columns
        left_column = self.find_left_column()

        assert len(text) <= columns, (len(text), columns)

        # Look only at the Columns on Screen of This Row

        row_spans = list()
        for span in spans:

            if span.row == row:
                column = left_column + span.column
                if column < columns:
                    beyond = min(columns, left_column + span.beyond)

                    row_span = TerminalSpan(row, column=column, beyond=beyond)
                    row_spans.append(row_span)

        # Visit each Empty Span

        for (index, span) in enumerate(row_spans):

            column = left_column + span.column
            beyond = left_column + span.beyond

            assert span.column <= span.beyond <= columns, (span, columns)

            if span.column == span.beyond:

                # Don't spread off Screen

                if span.column == columns:

                    continue

                # Don't spread into the next Span

                next_spans = row_spans[(index + 1) :]
                if next_spans:
                    next_span = next_spans[0]
                    if next_span.column == span.column:

                        continue

                # Else do spread to cover one Column

                column_plus = span.column + 1
                spread_span = TerminalSpan(row, column=span.column, beyond=column_plus)

                row_spans[index] = spread_span

        # Add one Space to spread the text beneath the Spans, if need be

        len_text = len(text) if (not row_spans) else max(_.beyond for _ in row_spans)

        assert len_text <= columns, (len_text, columns)

        text_plus = text
        if len_text > len(text):

            text_plus = text + " "
            assert len_text == len(text_plus), (row, len_text, len(text_plus))

        # Succeed

        return (row_spans, text_plus)


class TerminalShadow:
    """Simulate a Terminal, to mostly write just the Diffs, to reduce Lag"""

    def __init__(self, terminal):

        self.terminal = terminal

        self.rows = None
        self.columns = None

        self.held_lines = list()
        self.ringing_bell = None
        self.row = None
        self.column = None

        self.flushed_lines = list()

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        self.terminal.__enter__()
        self._reopen_terminal_()

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        self.terminal.__exit__(exc_type, exc_value, traceback)  # positional args

    def _reopen_terminal_(self):
        """Clear the Caches layered over this Terminal, here and below"""

        # Update the Ask here

        terminal = self.terminal

        held_lines = self.held_lines
        flushed_lines = self.flushed_lines

        fd = terminal.fileno()
        terminal_size = os.get_terminal_size(fd)

        (columns, rows) = (terminal_size.columns, terminal_size.lines)
        assert rows >= 1
        assert columns >= 1
        self.rows = rows
        self.columns = columns

        # Clear the Caches here

        held_lines[::] = rows * [None]
        self.ringing_bell = None
        self.row = None
        self.column = None

        flushed_lines[::] = rows * [None]

        # Clear the Caches below

        terminal.write(ED_2)
        terminal.write(CUP_1_1)
        terminal.flush()

        return terminal_size

        # TODO: deal with $LINES, $COLUMNS, fallback,
        # TODO: like 'shutil.get_terminal_size' would

    def flush(self):
        """Stop waiting for more Writes from above"""

        columns = self.columns
        flushed_lines = self.flushed_lines
        held_lines = self.held_lines
        rows = self.rows
        terminal = self.terminal

        blank_text = columns * " "
        bottom_row = rows - 1

        # Write the rows

        terminal.write(CUP_1_1)

        assert len(held_lines) == rows, (len(held_lines), rows)
        for (row, held_line) in enumerate(held_lines):
            flushed_line = flushed_lines[row]

            if flushed_line != held_line:  # write Rows who changed since last Flush
                if row < bottom_row:

                    self._terminal_write_cup(row, column=0)
                    terminal.write(blank_text)

                    self._terminal_write_cup(row, column=0)
                    terminal.write(held_line.rstrip())

                else:

                    self._terminal_write_cup(row, column=0)
                    terminal.write(blank_text[:-1])

                    self._terminal_write_cup(row, column=0)
                    terminal.write(held_line.rstrip())

                flushed_lines[row] = held_line

        held_lines[::] = list()

        # Place the cursor

        self._terminal_write_cup(self.row, column=self.column)

        # Ring the bell

        if self.ringing_bell:
            terminal.write("\a")

        self.ringing_bell = None

        # Flush the writes

        terminal.flush()

        # TODO: maybe complexify to reduce latency:  Erase Row, CUP_Y, etc

    def _terminal_write_cup(self, row, column):
        """Position the Terminal Cursor, but without telling the Shadow"""

        terminal = self.terminal

        y = 1 + row
        x = 1 + column
        terminal.write(CUP_Y_X.format(y, x))

    def getch(self):
        """Block till the keyboard input Digit or Chord"""

        return self.terminal.getch()

    def write(self, chars):
        """Compare with Chars at Cursor, write Diffs now, move Cursor soon"""

        if chars == "\a":
            self.shadow_control_bell()
        elif chars.count(CSI) >= 2:
            self.shadow_opaque_chars_as_line(chars)
        elif chars.startswith(CSI):
            self.shadow_csi_chars(chars)
        else:
            self.shadow_opaque_chars_as_line(chars)

    def shadow_control_bell(self):
        """Ring the Terminal Bell at next Flush"""

        self.ringing_bell = True

    def shadow_opaque_chars_as_line(self, chars):
        """Write Opaque Chars over Screen, & shadow Cursor as if one Line written"""

        held_lines = self.held_lines
        row = self.row

        held_line = held_lines[row]
        assert held_line is None, held_line

        held_lines[row] = chars

        if row < (self.rows - 1):
            self.row += 1
            self.column = 0

        # FIXME: interpret Chars enough to affirm one Line written

    def shadow_csi_chars(self, chars):
        """Interpret CSI Escape Sequences"""

        if chars == ED_2:
            self.shadow_csi_clear_screen()
        elif chars.endswith("H"):
            self.shadow_csi_cursor_position(chars)
        else:
            raise NotImplementedError(repr(chars))

    def shadow_csi_clear_screen(self):
        """Write Spaces over Chars of Screen"""

        held_lines = self.held_lines
        rows = self.rows

        held_lines[::] = rows * [None]

    def shadow_csi_cursor_position(self, chars):
        """Leap to chosen Row and Column of Screen"""

        columns = self.columns
        rows = self.rows

        # Pick Y and X out of this CUP_Y_X

        (y, x) = (1, 1)
        if chars != CUP_1_1:

            match = re.match(CUP_Y_X_REGEX, string=chars)
            if not match:
                raise NotImplementedError(repr(chars))

            y = int(match.group(1))
            x = int(match.group(2))

        # Require simple

        if not ((y >= 1) and (x >= 1)):
            raise NotImplementedError(y, x)

        # Move the Shadow Cursor

        self.row = min(rows - 1, y - 1)
        self.column = min(columns - 1, x - 1)

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
    for ch in xxs.decode(errors="surrogateescape"):
        ord_ch = ord(ch)

        if ord_ch == 9:
            # rep += " ⇥"  # ⇥ \u21E5 Rightward Arrows to Bar
            rep += " Tab"
        elif ord_ch == 13:
            # rep += " ⏎"  # ⏎ \u23CE Return Symbol
            rep += " Return"
        elif ord_ch == 27:
            # rep += " ⎋"  # ⎋ \u238B Broken Circle With Northwest Arrow
            rep += " Esc"
        elif ord_ch == 127:
            # rep += " ⌫"  # ⌫ \u232B Erase To The Left
            rep += " Delete"
        elif ch == " ":
            # rep += " ␢"  # ␢ \u2422 Blank Symbol
            # rep += " ␣"  # ␣ \u2423 Open Box
            rep += " Space"

        elif ch.encode() in C0_CONTROL_STDINS:  # ord_ch in 0x00..0x1F,0x7F
            rep += " ⌃" + chr(ord_ch ^ 0x40)

        elif (ch in "0123456789") and rep and (rep[-1] in "0123456789"):
            rep += ch  # no Space between Digits in Prefix or Chords or Suffix

        else:
            rep += " " + ch

    rep = rep.replace("Esc [ A", "Up")  # aka ↑ \u2191 Upwards Arrow
    rep = rep.replace("Esc [ B", "Down")  # aka ↓ \u2193 Downwards Arrow
    rep = rep.replace("Esc [ C", "Right")  # aka → \u2192 Rightwards Arrow
    rep = rep.replace("Esc [ D", "Left")  # aka ← \u2190 Leftwards Arrows

    rep = rep.strip()

    return rep  # such as '⌃L' at FF, aka ⌃L, aka 12, aka '\f'


#
# Track how to configure Vim to feel like Vi Py
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

" \ Delay  => gracefully do nothing
:nnoremap <Bslash> :<return>

" \ Esc  => cancel the :set hlsearch highlighting of all search hits on screen
:nnoremap <Bslash><esc> :noh<return>

" \ e  => reload, if no changes not-saved
:nnoremap <Bslash>e :e<return>

" \ i  => toggle ignoring case in searches, but depends on :set nosmartcase
:nnoremap <Bslash>i :set invignorecase<return>

" \ m  => mouse moves cursor
" \ M  => mouse selects zigzags of chars to copy-paste
:nnoremap <Bslash>m :set mouse=a<return>
:nnoremap <Bslash>M :set mouse=<return>

" \ n  => toggle line numbers
:nnoremap <Bslash>n :set invnumber<return>

" \ w  => delete the trailing whitespace from each line (not yet from file)
:nnoremap <Bslash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

" £  => insert # instead, because Shift+3 at UK/US Keyboards
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

    headlines = list(
        _ for _ in module_doc.strip().splitlines() if _ and not _.startswith(" ")
    )
    description = headlines[1]

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

    with_columns = os.getenv("COLUMNS")
    os.environ["COLUMNS"] = str(89)  # Black promotes 89 columns per line
    try:
        parser_doc = parser.format_help()
    finally:
        if with_columns is None:
            os.environ.pop("COLUMNS")
        else:
            os.environ["COLUMNS"] = with_columns

    # Cut the worthless jitter we wish away

    alt_module_doc = module_doc.strip()
    alt_parser_doc = parser_doc

    if sys.version_info[:3] < (3, 9, 6):

        alt_module_doc = join_first_paragraph(alt_module_doc)
        alt_parser_doc = join_first_paragraph(alt_parser_doc)

        if "[FILE ...]" in module_doc:
            alt_parser_doc = alt_parser_doc.replace("[FILE [FILE ...]]", "[FILE ...]")
            # older Python needed this accomodation, such as Feb/2015 Python 3.4.3

    # Count significant differences

    alt_module_file = module_file
    alt_module_file = os.path.split(alt_module_file)[-1]
    alt_module_file = "./{} --help".format(alt_module_file)

    alt_parser_file = "argparse.ArgumentParser(..."

    diff_lines = list(
        difflib.unified_diff(
            a=alt_module_doc.splitlines(),
            b=alt_parser_doc.splitlines(),
            fromfile=alt_module_file,
            tofile=alt_parser_file,
        )
    )

    # Exit if significant differences, but print them first

    if diff_lines:

        lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
        stderr_print("\n".join(lines))

        sys.exit(1)  # trust caller to log SystemExit exceptions well


# deffed in many files  # missing from docs.python.org
def file_print(*args):  # later Python 3 accepts ', **kwargs' here
    """Save out the Str of an Object as a File"""

    with open("f.file", "a") as printing:
        print(*args, file=printing)


# deffed in many files
def join_first_paragraph(doc):
    """Join by single spaces all the leading lines up to the first empty line"""

    index = (doc + "\n\n").index("\n\n")
    lines = doc[:index].splitlines()
    chars = " ".join(_.strip() for _ in lines)
    alt = chars + doc[index:]

    return alt


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):  # later Python 3 accepts ', **kwargs' here
    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# TODO: hunt out the Fixme's

# TODO: :g/patternReturn  => preview lines found

# TODO: ⌃I ⌃O walk the Jump List of ' ` G / ? n N % ( ) [[ ]] { } L M H :s :tag :n etc
# TODO: despite Doc, to match Vim, include in the Jump List the * # forms of / ?

# TODO: mm '' `` marks
# TODO: qqq @q  => record, replay
# TODO: ⌃D ⌃U scrolling

# TODO: QR to draw with a Logo Turtle till QR,
# TODO: infinite Spaces per Row, rstrip at exit, moving relative not absolute
# TODO: 1234567890 Up Down Left Right, initially headed Up with |
# TODO: | - =| =- to draw a rectangle, |=-=|=- to draw a square
# TODO: [ ] for macro repetition

# TODO: stop passing through Controls from the File
# TODO: accept b"\t" as a form of b" "
# TODO: solve /⌃V⌃IReturn
# TODO: solve:  echo -n abc |vi -
# TODO: show the first ~ past the end differently when No End for Last Line
# TODO: revive the last Match of r"$" out there

# TODO: ⌃V o  => rectangular: opposite


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
