#!/usr/bin/env python3

r"""
usage: vi.py [-h] [+PLUS] [--pwnme [BRANCH]] [--version] [FILE ...]

read files, accept zero or more edits, write files

positional arguments:
  FILE              a file to edit (default: '/dev/stdin')

optional arguments:
  -h, --help        show this help message and exit
  +PLUS             next Ex command to run, just after loading first File
  --pwnme [BRANCH]  update and run this Code, don't just run it
  --version         print a hash of this Code (its Md5Sum)

quirks:
  |vi.py works like |vi -

keyboard tests:
  ZQ :q!⌃M :q⌃M :n!⌃M :n⌃M :w!⌃M :w⌃M ZZ :wq!⌃M :wq⌃M ⌃Zfg  => how to quit Vi Py
  ⌃C Up Down Right Left Space Delete Return  => natural enough
  0 ^ $ fx h l tx Fx Tx ; , |  => leap to column
  b e w B E W { }  => leap across small word, large word, paragraph
  j k G 1G H L M - + _ ⌃J ⌃N ⌃P  => leap to row, leap to line
  1234567890 Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y zb zt zz 99zz  => scroll rows
  ⌃L ⌃G  => toggle lag, say if lag is toggled, show version
  \n \i \F \Esc  => toggle show line numbers, search case, search regex, show matches
  /... Delete ⌃U ⌃C Return  ?...   * # £ n N  => enter a search key, find later/ earlier
  :g/... Delete ⌃U ⌃C Return  => enter a search key and print every line found
  Esc ⌃C 123Esc 123⌃C zZ /⌃G 3ZQ f⌃C 9^ G⌃F⌃F 1G⌃B G⌃F⌃E 1G⌃Y ; , n N  => Easter eggs
  \n99zz \F/$Return 9⌃G Qvi⌃My Qvi⌃Mn :n  => more Easter eggs

pipe tests:
  ls |bin/vi.py -  # press ZQ to quit Vi Py without saving last changes
  cat bin/vi.py |bin/vi.py -  # demo multiple screens of chars
  cat bin/vi.py |bin/vi.py - |grep import  # demo ZQ vs ZZ

how to get Vi Py:
  cd ~/Desktop/
  R=pelavarre/pybashish/master && F=bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R/$F
  ls -alF -drt vi.py

how to get Vi Py again:
  python3 vi.py +q --pwnme

simplest demo:
  python3 vi.py vi.py
  /egg
"""


import argparse
import collections
import datetime as dt
import difflib
import hashlib
import inspect
import os
import pdb
import re
import select
import shlex
import signal
import string
import subprocess
import sys
import termios
import traceback
import tty

subprocess_run = subprocess.run  # evade Linters who freak over "shell=True"


# Name some Terminal Output magic

ESC = "\x1B"  # Esc
CSI = ESC + "["  # Control Sequence Introducer (CSI)

ED_2 = "\x1B[2J"  # Erase in Display (ED)  # 2 = Whole Screen
CUP_Y_X = "\x1B[{};{}H"  # Cursor Position (CUP)
CUP_1_1 = "\x1B[H"  # Cursor Position (CUP)  # (1, 1) = Upper Left

SGR_N = "\x1B[{}m"  # Select Graphic Rendition
SGR_7 = SGR_N.format(7)  # SGR > Reverse Video, Invert
SGR = "\x1B[m"  # SGR > Reset, Normal, All Attributes Off

DECSC = ESC + "7"  # DEC Save Cursor
DECRC = ESC + "8"  # DEC Restore Cursor

_XTERM_ALT_ = "\x1B[?1049h"
_XTERM_MAIN_ = "\x1B[?1049l"

SMCUP = DECSC + _XTERM_ALT_  # Set-Mode Cursor-Positioning
RMCUP = ED_2 + _XTERM_MAIN_ + DECRC  # Reset-Mode Cursor-Positioning

_CURSES_INITSCR_ = SMCUP + ED_2 + CUP_1_1
_CURSES_ENDWIN_ = RMCUP


# Specify how to split Terminal Output into magic and literals

TERMINAL_WRITE_REGEX = r"".join(
    [
        r"(\x1B\[",  # Control Sequence Introducer (CSI)
        r"(([0-9?]+)(;([0-9?]+))?)?",  # 0, 1, or 2 Decimal Int or Question Args
        r"([A-Z_a-z]))",  # one Ascii Letter or Skid mark
        r"|",
        r"(\x1B.)",  # else one escaped Char
        r"|",
        r"(\r\n|[\x00-\x1F\x7F])",  # else one or a few C0_CONTROL Chars
        r"|",
        r"([^\x00-\x1F\x7F]+)",  # else literal Chars
    ]
)


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

    main.since = dt.datetime.now()

    args = parse_vi_argv(argv)
    if args.pwnme is not False:
        pwnme(branch=args.pwnme)
    if args.version:
        print_version_and_exit()

    # Visit each File

    skin = TerminalSkinVi(files=args.files, ex_commands=args.ex_commands)

    returncode = None
    try:
        skin.run_editor()  # till SystemExit
        assert False  # unreached
    except SystemExit as exc:
        returncode = exc.code

        if (not returncode) and skin.file_written:

            iobytearray = skin.editor.iobytearray
            os.write(sys.stdout.fileno(), iobytearray)
            sys.stdout.flush()

        if skin.log:
            stderr_print(skin.log)

        # TODO: log keystrokes interpreted before exit, or dropped by exit

    # Exit

    sys.exit(returncode)


def parse_vi_argv(argv):
    """Convert a Vi Sys ArgV to an Args Namespace, or print some Help and quit"""

    parser = compile_argdoc(epi="quirks", drop_help=True)

    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a file to edit (default: '/dev/stdin')",
    )

    parser.add_argument(
        "-h", "--help", action="count", help="show this help message and exit"
    )

    parser.add_argument(
        "--plus",  # Vim Cli "+"
        metavar="PLUS",
        dest="ex_commands",
        action="append",  # 'man vim' says <= 10 commands
        help="next Ex command to run, just after loading first File",
    )

    parser.add_argument(
        "--pwnme",  # Vim doesn't do software-update-in-place
        metavar="BRANCH",
        nargs="?",
        default=False,
        help="update and run this Code, don't just run it",
    )

    parser.add_argument(
        "--version",
        action="count",
        help="print a hash of this Code (its Md5Sum)",
    )

    exit_unless_doc_eq(parser)

    argv_tail = list()
    for arg in argv[1:]:
        if not arg.startswith("+"):
            argv_tail.append(arg)
        else:
            argv_tail.append("--plus=" + arg[len(":")])

    args = parser.parse_args(argv_tail)
    if args.help:
        sys.stdout.write(parser_format_help(parser))
        sys.exit()

    return args


def print_version_and_exit():
    """Print a hash of this Code (its Md5Sum) and exit"""

    version = module_file_version_zero()
    str_hash = module_file_hash()
    str_short_hash = str_hash[:4]  # conveniently fewer nybbles  # good enough?

    print("Vi Py {} hash {} ({})".format(version, str_short_hash, str_hash))

    sys.exit()


def pwnme(branch):
    """Download fresh Code to run in place of this stale Code"""

    sys_argv = sys.argv

    # Find present Self

    path = module_file_path()
    from_relpath = os.path.relpath(path)

    # Find future Self  # TODO: rename to branch "main" from branch "master"

    assert branch in (None, "master", "pelavarre-patch-1"), branch
    branch_ = "master" if (branch is None) else branch

    link = (
        "https://raw.githubusercontent.com/" "pelavarre/pybashish/{}/" "bin/vi.py"
    ).format(branch_)

    to_relpath = from_relpath

    # Compose a Bash Script

    when = main.since
    stamp = when.strftime("%m%djqd%H%M%S")
    mv_shline = "mv -i {relpath} {relpath}~{stamp}~".format(
        relpath=from_relpath, stamp=stamp
    )

    curl_shline = "curl -sS --location {link} >{relpath}".format(
        link=link, relpath=to_relpath
    )

    chmod_shline = "chmod ugo+x {relpath}".format(relpath=to_relpath)

    argv = list()
    argv.append("./" + to_relpath)
    for arg in sys_argv[1:]:
        if not arg.startswith("--pwnme"):
            argv.append(arg)

    vi_py_shline = shlex_join(argv)

    shlines = (mv_shline, curl_shline, chmod_shline, vi_py_shline)

    # Run the Bash Script, and exit with its process exit status returncode

    for shline in shlines:
        stderr_print("+ {}".format(shline))
        try:
            _ = subprocess_run(shline, shell=True, check=True)
        except subprocess.CalledProcessError as exc:
            stderr_print("+ exit {}".format(exc.returncode))
            sys.exit(exc.returncode)

    sys.exit()


#
# Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim
#


VI_BLANK_SET = set(" \t")
VI_SYMBOLIC_SET = set(string.ascii_letters + string.digits + "_")  # r"[A-Za-z0-9_]"


class TerminalSkinVi:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim"""

    def __init__(self, files, ex_commands):

        self.files = files  # files to edit
        self.ex_commands = ex_commands  # Ex commands to run after

        self.file_index = None
        self.file_path = None
        self.file_written = None

        self.log = None  # capture Python Tracebacks

        self.editor = None

        self.slip_choice = None  # find Char in Row
        self.slip_after = None  # slip off by one Column after finding Char
        self.slip_redo = None  # find later Char
        self.slip_undo = None  # find earlier Char

        self.seeking_more = None  # remembering the Seeking Column into next Nudge
        self.seeking_column = None  # leap to a Column after changing Row

    #
    # Visit each of the Files
    #

    def do_might_next_vi_file(self):  # Vim :n\r
        """Halt if Dev Stdin held, else visit the next (or first) File"""

        file_path = self.file_path
        iobytearray = self.editor.iobytearray

        if file_path == "/dev/stdin":
            if iobytearray:
                n = str(len(iobytearray))
                self.vi_print(n + " chars at Dev Stdin - Do you mean :n!")

                return

        self.do_next_vi_file()

        return True

    def do_next_vi_file(self):  # Vim :n!\r
        """Visit the next (or first) File"""

        file_index = self.file_index
        file_path = self.file_path
        files = self.files

        iobytearray = None
        if hasattr(self.editor, "iobytearray"):
            iobytearray = self.editor.iobytearray

        # Loudly fail to flush, rather than losing the held Chars

        if file_path == "/dev/stdin":
            if iobytearray:
                raise NotImplementedError(
                    "Dev Stdin :n! - Do you mean ZZ, :wq, ZQ, or :q!"
                )

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

        self.reopen_vi_path(path)

    def reopen_vi_path(self, path):
        """Visit a chosen File"""

        self.file_path = path

        editor = self.editor

        # Fetch Bytes of File

        iobytes = b""
        if path is not None:

            if sys.stdin.isatty():
                if path == "/dev/stdin":
                    stderr_print("Press ⌃D EOF to quit giving input")

            with open(path, "rb") as reading:
                iobytes = reading.read()

        iobytearray = bytearray(iobytes)

        # Swap in a new File of Lines

        editor._init_iobytearray_etc_(iobytearray)

    #
    # Layer thinly over TerminalEditor
    #

    def run_editor(self):
        """Enter Terminal Driver, then run Keyboard, then exit Terminal Driver"""

        ex_commands = self.ex_commands  # Vim starts with lines of '~/.vimrc

        # Choose how to start up

        chords = b""

        chords += b":n\r"  # autoload the first file => do_next_vi_file

        if ex_commands:
            for ex_command in ex_commands:
                chars = ":" + ex_command + "\r"
                chords += chars.encode()

        chords += b"\x03"  # welcome warmly with ETX, ⌃C, 3 => do_help_quit_vi

        # Form stack

        editor = TerminalEditor(chords=chords)
        keyboard = TerminalKeyboardVi(terminal_vi=self, editor=editor)
        self.editor = editor

        # Feed Keyboard into Screen, till SystemExit

        try:

            editor.run_terminal(keyboard)  # till SystemExit
            assert False  # unreached

        finally:

            self.log = editor.traceback

            if editor.iobytearray:
                if not self.file_written:

                    stderr_print(  # "vi.py: quit without write, ...
                        "vi.py: quit without write, "
                        "like because ZQ, or :q!, or didn't read Stdin"
                    )

    def get_vi_arg1(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        return self.editor.get_arg1(default=default)

    def get_vi_arg2(self):
        """Get the Bytes of the input Suffix past the input Chords"""

        return self.editor.get_arg2()

    def vi_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        self.editor.editor_print(*args)

    #
    # Layer thinly under the rest of TerminalSkinVi
    #

    def check_vi_index(self, truthy, **kwargs):
        """Fail fast, else proceed"""

        if not truthy:
            raise IndexError()

    def continue_vi_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        self.seeking_more = True

    #
    # Define Chords for pausing TerminalSkinVi
    #

    def do_say_more(self):  # Vim ⌃G
        """Reply once with more verbose details"""

        editor = self.editor

        if editor.finding_highlights:
            editor.flag_reply_with_find()

        joins = list()
        joins.append(repr(self.file_path))
        joins.append("more lag" if editor.injecting_lag else "less lag")

        editor.editor_print("  ".join(joins))  # such as "'bin/vi.py'  less lag"

        # TODO: echo $(whoami)@$(hostname):$(pwd)/

    def do_vi_c0_control_esc(self):  # Vim Esc
        """Cancel Digits Prefix, else suggest ZZ to quit Vi Py"""

        version = module_file_version_zero()

        arg1 = self.get_vi_arg1(default=None)
        if arg1 is not None:
            self.vi_print("Escaped")  # 123 Esc Egg, etc
        else:
            self.vi_print("Press ZZ to save changes and quit Vi Py", version)
            # Esc Egg  # Vim rings a Bell for each extra Esc

    def do_continue_vi(self):  # Vim Q v i Return  # Vim b"Qvi\r"  # not Ex mode
        """Accept Q v i Return, without ringing the Terminal bell"""

        editor = self.editor

        self.vi_ask("Would you like to play a game? (y/n)")

        try:
            chord = editor.terminal_getch()
        except KeyboardInterrupt:
            chord = b"\x03"  # ETX, ⌃C, 3

        editor.nudge.suffix = chord

        if chord in (b"y", b"Y"):
            self.vi_print("Ok, now try to quit Vi Py")
        else:
            self.vi_print("Ok")

    def vi_ask(self, *args):
        """Ask a question, but don't wait for its answer"""

        editor = self.editor

        message = " ".join(str(_) for _ in args)
        message += " "  # place the cursor after a Space after the Message
        self.vi_print(message)  # 'def vi_ask' asking a question

        vi_reply = self.format_vi_reply()
        ex = TerminalSkinEx(editor, vi_reply=vi_reply)

        with_paint_cursor_func = editor.keyboard.paint_cursor_func
        editor.keyboard.paint_cursor_func = ex.paint_ex_cursor
        try:
            editor.prompt_for_chords()
        finally:
            editor.keyboard.paint_cursor_func = with_paint_cursor_func

    def do_vi_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        editor = self.editor

        editor.do_sig_tstp()

        if self.seeking_column is not None:
            self.continue_vi_column_seek()

    #
    # Define Chords for entering, pausing, and exiting TerminalSkinVi
    #

    def do_flush_quit_vi(self):  # Vim ZZ  # Vim :wq!\r
        """Save last changes and quit"""

        if self.file_path == "/dev/stdin":
            self.file_written = True

        returncode = self.get_vi_arg1(default=None)
        sys.exit(returncode)  # Mac & Linux take only 'returncode & 0xFF'

    def do_help_quit_vi(self):  # Vim ⌃C  # Vi Py Init
        """Suggest ZQ to quit Vi Py"""

        editor = self.editor
        if editor.finding_highlights:
            editor.flag_reply_with_find()

        version = module_file_version_zero()
        self.vi_print("Press ZQ to lose changes and quit Vi Py", version)
        # ⌃C Egg  # Vim rings a Bell for each extra ⌃C

    def do_might_flush_quit_vi(self):  # Vim :wq\r
        """Halt if more files, else try might quit"""

        file_index = self.file_index
        files = self.files

        more_files = files[file_index:][1:]
        if more_files:
            self.vi_print("{} more files - Do you mean :wq!".format(len(more_files)))
            # Vim raises this IndexError only once, til next ':w' write

            return

        self.do_flush_quit_vi()
        assert False  # unreached

    def do_might_flush_vi(self):  # Vim :w\r
        """Halt if difficult to write, else write"""

        file_path = self.file_path
        iobytearray = self.editor.iobytearray

        if file_path == "/dev/stdin":
            if iobytearray:
                n = str(len(iobytearray))
                self.vi_print(n + " chars at Dev Stdin - Do you mean :w!")

                return

        return True

    def do_flush_vi(self):  # Vim :w!\r
        """Mutate the File"""

        file_path = self.file_path
        iobytearray = self.editor.iobytearray

        if file_path == "/dev/stdin":
            if iobytearray:
                raise NotImplementedError(
                    "Dev Stdin :w! - Do you mean ZZ, :wq, ZQ, or :q!"
                )

    def do_might_quit_vi(self):  # Vim :q\r
        """Halt if more Files, else quit"""

        file_index = self.file_index
        file_path = self.file_path
        files = self.files
        iobytearray = self.editor.iobytearray

        if file_path == "/dev/stdin":
            if iobytearray:
                n = str(len(iobytearray))  # TODO: "{:_}".format(122213) in later Python
                self.vi_print(n + " chars at Dev Stdin - Do you mean ZZ, :q!, ZQ")

                return

        more_files = files[file_index:][1:]
        if more_files:
            self.vi_print("{} more files - Do you mean :n".format(len(more_files)))
            # Vim raises this IndexError only once, til next ':w' write

            return

        self.do_quit_vi()
        assert False  # unreached

    def do_quit_vi(self):  # Vim ZQ  # Vim :q!\r
        """Lose last changes and quit"""

        file_path = self.file_path
        iobytearray = self.editor.iobytearray

        returncode = None
        if file_path == "/dev/stdin":
            if iobytearray:
                returncode = 1
        returncode = self.get_vi_arg1(default=returncode)

        sys.exit(returncode)  # Mac & Linux take only 'returncode & 0xFF'

    #
    # Define Chords to take a Word of this Line as the Search Key, and look for it
    #

    def do_find_ahead_vi_this(self):  # Vim *
        """Take a Search Key from this Line, and then look ahead for it"""

        editor = self.editor
        editor.flag_reply_with_find()

        # Take up a new Search Key

        if not editor.doing_done:
            if self.slip_find_fetch_vi_this(slip=+1) is None:
                self.vi_print("Press * and # only when Not on a blank line")

                return

        # Try the Search

        if editor.find_ahead_and_reply():

            editor.continue_do_loop()

    def do_find_behind_vi_this(self):  # Vim #  # Vim £
        """Take a Search Key from this Line, and then look behind for it"""

        editor = self.editor
        editor.flag_reply_with_find()

        # Take up a new Search Key

        if not editor.doing_done:
            if self.slip_find_fetch_vi_this(slip=-1) is None:
                self.vi_print("Press # and £ and * only when Not on a blank line")

                return

        # Try the Search

        if editor.find_behind_and_reply():

            editor.continue_do_loop()

    def slip_find_fetch_vi_this(self, slip):
        """Take a Word from this Line and return Truthy, else don't"""

        editor = self.editor

        # Take this Word

        word = self.slip_fetch_vi_word_here()
        if word is not None:
            assert word != ""

            # Make this Word into a Search Key for Words

            search_key = word  # partial Words and whole Words
            if word and editor.finding_regex:
                search_key = r"\b" + re.escape(search_key) + r"\b"  # whole Words only

            # Search for the Key

            editor.finding_line = search_key
            editor.finding_slip = slip

            assert editor.finding_line != ""
            editor.reopen_found_spans()

            # Pass back Word found, but with no mention of more Match'es found or not

            return word

    def slip_fetch_vi_word_here(self):
        """Slip to start Symbolic word, else Non-Blank word, in Line and return it"""

        # Setup

        editor = self.editor

        column = editor.column
        columns = editor.count_columns_in_row()

        def is_vi_symbolic(ch):
            return ch in VI_SYMBOLIC_SET

        def is_not_vi_blank(ch):
            return ch not in VI_BLANK_SET

        # Take a Symbolic word, else a Non-Blank word

        behind = column
        for func in (is_vi_symbolic, is_not_vi_blank):

            # Look behind to first Char of Word

            while behind:
                ch = editor.fetch_column_char(column=behind)
                if not func(ch):

                    break

                behind -= 1

            # Look ahead to first Char of Word

            for start in range(behind, columns):
                ch = editor.fetch_column_char(column=start)
                if func(ch):

                    # Slip ahead to Start of Word

                    editor.column = start

                    # Collect one or more Chars of Word

                    word = ""

                    for end in range(start, columns):
                        ch = editor.fetch_column_char(column=end)
                        if func(ch):
                            word += ch
                        else:

                            break

                    assert word

                    return word

    #
    # Define Chords to take a Search Key as additional Input, and look for it
    #

    def do_find_ahead_vi_line(self):  # Vim /
        """Take a Search Key as input, and then look ahead for it"""

        editor = self.editor
        editor.flag_reply_with_find()

        # Take up a new Search Key

        if not editor.doing_done:
            if self.find_read_vi_line(slip=+1) is None:

                return

        # Try the Search

        if editor.find_ahead_and_reply():  # TODO: extra far scroll <= zb H 23Up n

            editor.continue_do_loop()

    def do_find_all_vi_line(self):  # Vim :g/  # Vi Py :g/, g/
        """Across all the File, print each Line containing 1 or More Matches"""

        editor = self.editor

        editor.flag_reply_with_find()

        # Take Search Key as input

        if self.find_read_vi_line(slip=+1) is None:

            return

        # Print Matches

        before_status = self.format_vi_reply() + editor.finding_line

        if editor.find_ahead_and_reply():

            iobytespans = editor.iobytespans
            last_span = iobytespans[-1]

            editor.print_some_found_spans(before_status)
            self.vi_print(  # "{}/{} Found {} chars"
                "{}/{} Found {} chars".format(
                    len(iobytespans),
                    len(iobytespans),
                    last_span.beyond - last_span.column,
                )
            )

        # TODO: Vim :4g/ means search only line 4, not pick +-Nth match

    def do_find_behind_vi_line(self):  # Vim ?
        """Take a Search Key as input, and then look behind for it"""

        editor = self.editor
        editor.flag_reply_with_find()

        if not editor.doing_done:
            if self.find_read_vi_line(slip=-1) is None:

                return

        if editor.find_behind_and_reply():  # TODO: extra far scroll # <= zt L 23Down N

            editor.continue_do_loop()

    def find_read_vi_line(self, slip):
        """Take a Search Key"""

        editor = self.editor

        assert editor.finding_line != ""

        # Ask for fresh Search Key

        finding_line = None
        try:
            finding_line = self.read_vi_line()
        except Exception:

            raise

        # Cancel Search if accepting stale Search Key while no stale Search Key exists

        if not finding_line:

            if finding_line is None:
                self.vi_print("Search cancelled")  # Vim ⌃C

                return

            if not editor.finding_line:
                self.vi_print("Press ? or / to enter a Search Key")  # Vim ⌃C

                return

        # Take fresh Slip always, and take fresh Search Key if given

        editor.finding_slip = slip
        if finding_line:
            editor.finding_line = finding_line

        # Pick out Matches

        assert editor.finding_line != ""
        editor.reopen_found_spans()

        return True

    def read_vi_line(self):
        """Take a Line of Input"""

        editor = self.editor

        vi_reply = self.format_vi_reply()
        ex = TerminalSkinEx(editor, vi_reply=vi_reply)

        line = ex.read_ex_line()

        return line

    #
    # Define Chords to search again for the same old Search Key
    #

    def do_vi_find_earlier(self):  # Vim N
        """Leap to earlier Search Key Match"""

        editor = self.editor

        ahead_and_reply = editor.find_ahead_and_reply
        behind_and_reply = editor.find_behind_and_reply
        slip = editor.finding_slip

        editor.flag_reply_with_find()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press ? to enter a Search Key")

            return

        # Try the Search

        func = behind_and_reply if (slip >= 0) else ahead_and_reply
        if func():

            editor.continue_do_loop()

    def do_vi_find_later(self):  # Vim n
        """Leap to later Search Key Match"""

        editor = self.editor

        ahead_and_reply = editor.find_ahead_and_reply
        behind_and_reply = editor.find_behind_and_reply
        slip = editor.finding_slip

        editor.flag_reply_with_find()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press / to enter a Search Key")

            return

        # Try the Search

        func = ahead_and_reply if (slip >= 0) else behind_and_reply
        if func():

            editor.continue_do_loop()

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |  # Emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        editor = self.editor

        last_column = editor.spot_last_column()
        column = min(last_column, self.get_vi_arg1() - 1)

        editor.column = column

    def do_slip_dent(self):  # Vim ^
        """Leap to just past the Indent, but first Step Down if Arg"""

        arg1 = self.get_vi_arg1(default=None)
        if arg1 is not None:
            self.vi_print("Do you mean {} _".format(arg1))  # 9^ Egg, etc

        self.slip_dent()

    def slip_dent(self):
        """Leap to the Column after the Indent"""

        editor = self.editor

        line = editor.fetch_row_line()
        lstripped = line.lstrip()
        column = len(line) - len(lstripped)

        editor.column = column

    def do_slip_first(self):  # Vim 0  # Emacs move-beginning-of-line
        """Leap to the first Column in Row"""

        editor = self.editor

        assert editor.arg1 is None  # require no Digits before Vi Py 0 runs here

        editor.column = 0

    def do_slip_left(self):  # Vim h, Left  # Emacs left-char, backward-char
        """Slip left one Column or more"""

        editor = self.editor

        self.check_vi_index(editor.column)

        left = min(editor.column, self.get_vi_arg1())
        editor.column -= left

    def do_slip_right(self):  # Vim l, Right  #  emacs right-char, forward-char
        """Slip Right one Column or more"""

        editor = self.editor

        last_column = editor.spot_last_column()
        self.check_vi_index(editor.column < last_column)

        right = min(last_column - editor.column, self.get_vi_arg1())
        editor.column += right

    #
    # Step the Cursor across zero, one, or more Columns of the same Row
    #

    def do_slip_ahead(self):  # Vim Space
        """Slip right, then down"""

        editor = self.editor
        last_column = editor.spot_last_column()
        last_row = editor.spot_last_row()

        if not editor.doing_done:
            self.check_vi_index(
                (editor.column < last_column) or (editor.row < last_row)
            )

        if editor.column < last_column:
            editor.column += 1

            editor.continue_do_loop()

        elif editor.row < last_row:
            editor.column = 0
            editor.row += 1

            editor.continue_do_loop()

    def slip_ahead(self):
        """Slip right or down, and return 1, else return None at End of File"""

        editor = self.editor
        last_column = editor.spot_last_column()
        last_row = editor.spot_last_row()

        if editor.column < last_column:
            editor.column += 1

            return 1

        elif editor.row < last_row:
            editor.column = 0
            editor.row += 1

            return 1

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        editor = self.editor

        if not editor.doing_done:
            self.check_vi_index(editor.row or editor.column)

        if editor.column:
            editor.column -= 1

            editor.continue_do_loop()

        elif editor.row:
            editor.row -= 1
            row_last_column = editor.spot_last_column(row=editor.row)
            editor.column = row_last_column

            editor.continue_do_loop()

    def slip_behind(self):
        """Slip left or down, and return 1, else return None at Start of File"""

        editor = self.editor

        if editor.column:
            editor.column -= 1

            editor.continue_do_loop()

            return -1

        elif editor.row:
            editor.row -= 1
            row_last_column = editor.spot_last_column(row=editor.row)
            editor.column = row_last_column

            return -1

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # Vim G, 1G  # Emacs goto-line
        """Leap to last Row, else to a chosen Row"""

        editor = self.editor
        last_row = editor.spot_last_row()

        row = min(last_row, self.get_vi_arg1() - 1)
        row = last_row if (editor.arg1 is None) else row

        editor.row = row
        self.slip_dent()

    def do_step_down_dent(self):  # Vim +, Return
        """Step down a Row or more, but land just past the Indent"""

        self.step_down()
        self.slip_dent()

    def step_down(self):
        """Step down one Row or more"""

        editor = self.editor
        last_row = editor.spot_last_row()

        self.check_vi_index(editor.row < last_row)
        down = min(last_row - editor.row, self.get_vi_arg1())

        editor.row += down

    def do_step_down_minus_dent(self):  # Vim _
        """Leap to just past the Indent, but first Step Down if Arg"""

        self.step_down_minus()
        self.slip_dent()

    def step_down_minus(self):
        """Step down zero or more Rows, not one or more Rows"""

        down = self.get_vi_arg1() - 1
        if down:
            self.editor.arg1 -= 1  # mutate
            self.step_down()

    def do_step_max_low(self):  # Vim L
        """Leap to first Word of Bottom Row on Screen"""

        editor = self.editor
        editor.row = editor.spot_bottom_row()
        self.slip_dent()

    def do_step_max_high(self):  # Vim H
        """Leap to first Word of Top Row on Screen"""

        editor = self.editor
        editor.row = editor.top_row
        self.slip_dent()

    def do_step_to_middle(self):  # Vim M
        """Leap to first Word of Middle Row on Screen"""

        editor = self.editor
        editor.row = editor.spot_middle_row()
        self.slip_dent()

    def do_step_up_dent(self):  # Vim -
        """Step up a Row or more, but land just past the Indent"""

        self.step_up()
        self.slip_dent()

    def step_up(self):
        """Step up one Row or more"""

        editor = self.editor
        self.check_vi_index(editor.row)
        up = min(editor.row, self.get_vi_arg1())

        editor.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_last_seek(self):  # Vim $  # Emacs move-end-of-line
        """Leap to the last Column in Row, and keep seeking last Columns"""

        editor = self.editor

        self.seeking_column = True
        self.step_down_minus()
        row_last_column = editor.spot_last_column(row=editor.row)
        editor.column = row_last_column

        self.continue_vi_column_seek()

    def do_step_down_seek(self):  # Vim j, ⌃J, ⌃N, Down  # Emacs next-line
        """Step down one Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_down()

        editor.column = self.seek_vi_column()
        self.continue_vi_column_seek()

    def do_step_up_seek(self):  # Vim k, ⌃P, Up  # Emacs previous-line
        """Step up a Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_up()

        editor.column = self.seek_vi_column()
        self.continue_vi_column_seek()

    def seek_vi_column(self, column=True):
        """Begin seeking a Column, if not begun already"""

        editor = self.editor
        last_column = editor.spot_last_column()

        if self.seeking_column is True:
            sought_column = last_column
        else:
            sought_column = min(last_column, self.seeking_column)

        return sought_column

    #
    # Scroll ahead or behind almost one Whole Screen of Rows
    #

    def do_scroll_ahead_much(self):  # Vim ⌃F
        """Scroll ahead much"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row
        editor = self.editor
        painter = editor.painter

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        bottom_row = editor.spot_bottom_row()
        last_row = editor.spot_last_row()

        # Quit at last Row

        if top_row == last_row:
            if not self.editor.doing_done:
                self.vi_print("Do you mean ⌃B")  # G⌃F⌃F Egg

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

        editor.top_row = top_row

        # Choose new Row and Column

        if row < top_row:
            row = top_row

        editor.row = row

        self.slip_dent()

        editor.continue_do_loop()

    def do_scroll_behind_much(self):  # Vim ⌃B
        """Show the previous Screen of Rows"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row
        editor = self.editor
        painter = editor.painter

        last_row = editor.spot_last_row()

        # Quit at top Row

        if not top_row:
            if not self.editor.doing_done:
                self.vi_print("Do you mean ⌃F")  # 1G⌃B Egg

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

        editor.top_row = top_row

        # Choose new Row and Column

        bottom_row = editor.spot_bottom_row()
        if row > bottom_row:
            editor.row = bottom_row

        self.slip_dent()

        editor.continue_do_loop()

    #
    # Scroll ahead or behind one Row of Screen
    #

    def do_scroll_ahead_one(self):  # Vim ⌃E
        """Show the next Row of Screen"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row

        editor = self.editor
        last_row = editor.spot_last_row()

        # Quit at last Row

        if editor.top_row == last_row:
            if not editor.doing_done:
                self.vi_print("Do you mean ⌃Y")  # G⌃F⌃E Egg

            return

        # Scroll ahead one

        if top_row < last_row:
            top_row += 1
            if row < top_row:
                row = top_row

        editor.top_row = top_row  # always different Top Row

        editor.row = row  # same or different Row
        self.slip_dent()  # same or different Column

        editor.continue_do_loop()

    def do_scroll_behind_one(self):  # Vim ⌃Y
        """Show the previous Row of Screen"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row

        # Quit at top Row

        if not top_row:
            if not editor.doing_done:
                self.vi_print("Do you mean ⌃E")  # 1G⌃Y Egg

            return

        # Scroll behind one

        if top_row:
            top_row -= 1

            bottom_row = editor.spot_bottom_row(top_row)
            if row > bottom_row:
                row = bottom_row

        editor.top_row = top_row  # always different Top Row

        editor.row = row  # same or different Row
        self.slip_dent()  # same or different Column

        editor.continue_do_loop()

    #
    # Scroll to move Cursor on Screen
    #

    def do_scroll_till_top(self):  # Vim zt
        """Scroll up or down till Cursor Row lands in Top Row of Screen"""

        editor = self.editor

        row_plus = self.get_vi_arg1(editor.row + 1)
        row = row_plus - 1
        editor.row = row

        editor.top_row = row

    def do_scroll_till_middle(self):  # Vim zz  # not to be confused with Vim ZZ
        """Scroll up or down till Cursor Row lands in Middle Row of Screen"""

        editor = self.editor
        painter = editor.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows

        row_plus = self.get_vi_arg1(editor.row + 1)
        row = row_plus - 1
        editor.row = row

        up = scrolling_rows // 2
        top_row = (row - up) if (row >= up) else 0

        editor.top_row = top_row

    def do_scroll_till_bottom(self):  # Vim zb
        """Scroll up or down till Cursor Row lands in Bottom Row of Screen"""

        editor = self.editor
        painter = editor.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows

        row_plus = self.get_vi_arg1(editor.row + 1)
        row = row_plus - 1
        editor.row = row

        up = scrolling_rows - 1
        top_row = (row - up) if (row >= up) else 0

        editor.top_row = top_row

    #
    # Search ahead for an Empty Line (while ignoring Blank Lines)
    #

    def do_paragraph_ahead(self):  # Vim {
        """Step down over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor
        last_row = editor.spot_last_row()

        if editor.doing_done:
            if (editor.row, editor.column) == (last_row, editor.spot_last_column()):
                raise IndexError()

        while (editor.row < last_row) and not editor.spot_last_column(row=editor.row):
            editor.row += 1
        while (editor.row < last_row) and editor.spot_last_column(row=editor.row):
            editor.row += 1

        editor.column = editor.spot_last_column(row=editor.row)

        editor.continue_do_loop()

    def do_paragraph_behind(self):  # Vim }
        """Step up over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor

        if editor.doing_done:
            if (editor.row, editor.column) == (0, 0):
                raise IndexError()

        while editor.row and not editor.spot_last_column(row=editor.row):
            editor.row -= 1
        while editor.row and editor.spot_last_column(row=editor.row):
            editor.row -= 1

        editor.column = 0

        editor.continue_do_loop()

    #
    # Step across "Big" Words between Blanks, and "Lil" Words of Symbolic/Not Chars
    #

    def do_big_word_end_ahead(self):  # Vim E
        """Slip ahead to last Char of this else next Big Word"""

        self.do_word_end_ahead(VI_BLANK_SET)

    def do_lil_word_end_ahead(self):  # Vim e
        """Slip ahead to last Char of this else next Lil Word"""

        self.do_word_end_ahead(VI_BLANK_SET, VI_SYMBOLIC_SET)

    def do_word_end_ahead(self, *charsets):
        """Slip ahead to last Char of this else next Word"""

        editor = self.editor

        if not editor.doing_done:
            self.check_vi_index(editor.may_slip_ahead())

        self.word_end_ahead(charsets)

        editor.continue_do_loop()

    def word_end_ahead(self, charsets):
        """Slip ahead to last Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        self.slip_ahead()

        # Slip ahead across Blanks and Empty Lines, between Words, up to End of File

        while not editor.charsets_find_column(charsets):
            if not self.slip_ahead():

                break

        # Slip ahead across Chars of Word in Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                row_last_column = editor.spot_last_column(row=editor.row)
                if editor.column == row_last_column:

                    return

                ahead = self.slip_ahead()
                assert ahead, (editor.column, editor.count_columns_in_row())

            behind = self.slip_behind()  # backtrack
            assert behind, (editor.column, editor.count_columns_in_row())

    def do_big_word_start_ahead(self):  # Vim W  # inverse of Vim B
        """Slip ahead to first Char of next Big Word"""

        self.do_word_start_ahead(VI_BLANK_SET)

    def do_lil_word_start_ahead(self):  # Vim w  # inverse of Vim b
        """Slip ahead to first Char of next Lil Word"""

        self.do_word_start_ahead(VI_BLANK_SET, VI_SYMBOLIC_SET)

    def do_word_start_ahead(self, *charsets):
        """Slip ahead to first Char of next Word"""

        editor = self.editor

        if not editor.doing_done:
            self.check_vi_index(editor.may_slip_ahead())

        self.word_start_ahead(charsets)

        editor.continue_do_loop()

    def word_start_ahead(self, charsets):
        """Slip ahead to first Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        here = editor.charsets_find_column(charsets)

        _ = self.slip_ahead()

        # Slip ahead across more Chars of Word in Line

        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    break

                if not self.slip_ahead():

                    break

        # Slip ahead across Blanks, but not across Empty Lines, nor End of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_ahead():

                break

    def do_big_word_start_behind(self):  # Vim B  # inverse of Vim W
        """Slip behind to first Char of Big Word"""

        self.do_word_start_behind(VI_BLANK_SET)

        # TODO: add option for '._' between words, or only '.' between words
        # TODO: add option for 'b e w' and 'B E W' to swap places

    def do_lil_word_start_behind(self):  # Vim b  # inverse of Vim b
        """Slip behind first Char of Lil Word"""

        self.do_word_start_behind(VI_BLANK_SET, VI_SYMBOLIC_SET)

    def do_word_start_behind(self, *charsets):
        """Slip behind to first Char of Word"""

        editor = self.editor

        if not editor.doing_done:
            self.check_vi_index(editor.may_slip_behind())

        self.word_start_behind(charsets)

        editor.continue_do_loop()

    def word_start_behind(self, charsets):
        """Slip behind to first Char of this else next Word"""

        editor = self.editor

        # Slip behind at least once (unless at Start of File)

        _ = self.slip_behind()

        # Slip behind across Blanks, but not across Empty Lines, nor Start of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_behind():

                break

        # Slip behind across Chars of Word, except stop at Start of Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    return

                behind = self.slip_behind()
                assert behind, (editor.column, editor.count_columns_in_row())

            ahead = self.slip_ahead()  # backtrack
            assert ahead, (editor.column, editor.count_columns_in_row())

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

        # TODO: Vim f⌃VX means go find a ⌃V char, not go find X

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

        editor = self.editor

        last_column = editor.spot_last_column()
        line = editor.fetch_row_line()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_vi_arg1()

        # Index each

        column = editor.column

        for _ in range(count):

            self.check_vi_index(column < last_column)
            column += 1

            try:
                right = line[column:].index(choice)
            except ValueError:
                raise ValueError("substring {!r} not found ahead".format(choice))
            column += right

        # Option to slip back one column

        if after:
            self.check_vi_index(column)
            column -= 1

        editor.column = column

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

        editor = self.editor

        last_column = editor.spot_last_column()
        line = editor.fetch_row_line()

        choice = self.slip_choice
        after = self.slip_after

        count = self.get_vi_arg1()

        # R-Index each

        column = editor.column

        for _ in range(count):

            self.check_vi_index(column)
            column -= 1

            try:
                column = line[: (column + 1)].rindex(choice)
            except ValueError:
                raise ValueError("substring {!r} not found behind".format(choice))

        # Option to slip right one column

        if after:

            self.check_vi_index(column < last_column)
            column += 1

        editor.column = column

    #
    # Repeat search inside the Row for a single Char
    #

    def do_slip_choice_redo(self):  # Vim ;
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        editor = self.editor

        if self.slip_choice is None:
            self.vi_print("Do you mean fx;")  # ; Egg

            return

        after = self.slip_after
        if not after:

            self.slip_redo()

        else:

            row_last_column = editor.spot_last_column(row=editor.row)

            with_column = editor.column
            try:

                if after < 0:
                    assert editor.column < row_last_column
                    editor.column += 1
                elif after > 0:
                    assert editor.column
                    editor.column -= 1

                self.slip_redo()

                assert editor.column != with_column

            except Exception:
                editor.column = with_column

                raise

    def do_slip_choice_undo(self):  # Vim ,
        """Undo the last 'slip_index' or 'slip_rindex' once or more"""

        editor = self.editor

        if self.slip_choice is None:
            self.vi_print("Do you mean Fx,")  # , Egg

            return

        after = self.slip_after
        if not after:

            self.slip_undo()

        else:

            row_last_column = editor.spot_last_column(row=editor.row)

            with_column = editor.column
            try:

                if after < 0:
                    assert editor.column
                    editor.column -= 1
                elif after > 0:
                    assert editor.column < row_last_column
                    editor.column += 1

                self.slip_undo()

                assert editor.column != with_column

            except Exception:
                editor.column = with_column

                raise

    #
    # Map Keyboard Inputs to Code, for when feeling like Vi
    #

    def enter_do_vi(self):
        """Run before each Vi Func chosen by Chords"""

        # Default to stop remembering the last Seeking Column

        self.seeking_more = None

    def exit_do_vi(self):
        """Run after each Vi Func chosen by Chords"""

        # Remember the last Seeking Column across Funcs that ask for it

        if not self.seeking_more:
            self.seeking_column = None

    def format_vi_reply(self):
        """Format a Status Line of Row:Column, Nudge, and Message"""

        editor = self.editor
        reply = editor.reply
        nudge = reply.nudge

        # Format parts, a la Vim ':set showcmd' etc

        str_pin = "{},{}".format(1 + self.editor.row, 1 + self.editor.column)

        str_flags = str(reply.flags) if reply.flags else ""

        echo_bytes = b"" if (nudge is None) else nudge.join_echo_bytes()
        str_echo = format(repr_vi_bytes(echo_bytes)) if echo_bytes else ""

        str_message = str(reply.message) if reply.message else ""

        # Join parts

        replies = (str_pin, str_flags, str_echo, str_message)
        vi_reply = "  ".join(_ for _ in replies if _)

        return vi_reply

    def paint_vi_cursor(self):
        """Place the Screen Cursor"""

        editor = self.editor
        painter = editor.painter
        terminal = painter

        terminal.row = editor.row - editor.top_row
        terminal.column = editor.column


class TerminalKeyboard:
    """Map Keyboard Inputs to Code"""

    def _init_correcting_many_chords(self, chords, corrections):
        """Map one sequence of keyboard input Chords to another"""

        corrections_by_chords = self.corrections_by_chords

        self._init_func_by_many_vi_chords(chords, func=None)
        corrections_by_chords[chords] = corrections

    def _init_suffix_func(self, chords, func):
        """Map a sequence of keyboard input Chords that needs 1 Suffix Chord"""

        self._init_func_by_many_vi_chords(chords, func=func, suffixes=1)

    def _init_func_by_many_vi_chords(self, chords, func, suffixes=None):
        """Map a sequence of keyboard input Chords"""

        func_by_chords = self.func_by_chords
        suffixes_by_chords = self.suffixes_by_chords

        # Ask for more Chords while holding some, but not all, of these Chords

        for some in range(1, len(chords)):
            some_chords = chords[:some]

            if some_chords not in func_by_chords.keys():
                func_by_chords[some_chords] = None
            else:
                assert func_by_chords[some_chords] is None, chords

        # Call this Func after collecting all these Chords

        func_by_chords[chords] = func  # may be init, may be mutate

        # Except first ask for 1 Suffix Chord, if wanted

        if suffixes:
            assert suffixes, chords
            suffixes_by_chords[chords] = suffixes


class TerminalKeyboardVi(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Vi"""

    def __init__(self, terminal_vi, editor):

        vi = terminal_vi

        self.vi = vi
        self.editor = editor
        assert vi.editor in (None, editor), (vi, vi.editor, editor)

        self.format_reply_func = vi.format_vi_reply
        self.paint_cursor_func = vi.paint_vi_cursor
        self.enter_do_func = vi.enter_do_vi
        self.do_func = editor.do_raise_name_error
        self.exit_do_func = vi.exit_do_vi

        self.corrections_by_chords = dict()
        self.func_by_chords = dict()
        self.suffixes_by_chords = dict()

        self._init_by_vi_chords_()

    def _init_by_vi_chords_(self):

        editor = self.editor
        func_by_chords = self.func_by_chords
        vi = self.vi

        # Define the C0_CONTROL_STDINS

        # func_by_chords[b"\x00"] = vi.do_c0_control_nul  # NUL, ⌃@, 0
        # func_by_chords[b"\x01"] = vi.do_c0_control_soh  # SOH, ⌃A, 1
        func_by_chords[b"\x02"] = vi.do_scroll_behind_much  # STX, ⌃B, 2
        func_by_chords[b"\x03"] = vi.do_help_quit_vi  # ETX, ⌃C, 3
        # func_by_chords[b"\x04"] = vi.do_scroll_ahead_some  # EOT, ⌃D, 4
        func_by_chords[b"\x05"] = vi.do_scroll_ahead_one  # ENQ, ⌃E, 5
        func_by_chords[b"\x06"] = vi.do_scroll_ahead_much  # ACK, ⌃F, 6
        func_by_chords[b"\x07"] = vi.do_say_more  # BEL, ⌃G, 7 \a
        # func_by_chords[b"\x08"] = vi.do_c0_control_bs  # BS, ⌃H, 8 \b
        # func_by_chords[b"\x09"] = vi.do_c0_control_tab  # TAB, ⌃I, 9 \t
        func_by_chords[b"\x0A"] = vi.do_step_down_seek  # LF, ⌃J, 10 \n
        # func_by_chords[b"\x0B"] = vi.do_c0_control_vt  # VT, ⌃K, 11 \v
        func_by_chords[b"\x0C"] = editor.do_redraw  # FF, ⌃L, 12 \f
        func_by_chords[b"\x0D"] = vi.do_step_down_dent  # CR, ⌃M, 13 \r
        func_by_chords[b"\x0E"] = vi.do_step_down_seek  # SO, ⌃N, 14
        # func_by_chords[b"\x0F"] = vi.do_c0_control_si  # SI, ⌃O, 15
        func_by_chords[b"\x10"] = vi.do_step_up_seek  # dle, ⌃P, 16
        # func_by_chords[b"\x11"] = vi.do_c0_control_dc1  # DC1, XON, ⌃Q, 17
        # func_by_chords[b"\x12"] = vi.do_c0_control_dc2  # DC2, ⌃R, 18
        # func_by_chords[b"\x13"] = vi.do_c0_control_dc3  # DC3, XOFF, ⌃S, 19
        # func_by_chords[b"\x14"] = vi.do_c0_control_dc4  # DC4, ⌃T, 20
        # func_by_chords[b"\x15"] = vi.do_scroll_behind_some  # NAK, ⌃U, 21
        # func_by_chords[b"\x16"] = vi.do_c0_control_syn  # SYN, ⌃V, 22
        # func_by_chords[b"\x17"] = vi.do_c0_control_etb  # ETB, ⌃W, 23
        # func_by_chords[b"\x18"] = vi.do_c0_control_can  # CAN, ⌃X , 24
        func_by_chords[b"\x19"] = vi.do_scroll_behind_one  # EM, ⌃Y, 25
        func_by_chords[b"\x1A"] = vi.do_vi_sig_tstp  # SUB, ⌃Z, 26

        func_by_chords[b"\x1B"] = vi.do_vi_c0_control_esc  # ESC, ⌃[, 27
        func_by_chords[b"\x1B[A"] = vi.do_step_up_seek  # ↑ Up Arrow
        func_by_chords[b"\x1B[B"] = vi.do_step_down_seek  # ↓ Down Arrow
        func_by_chords[b"\x1B[C"] = vi.do_slip_right  # → Right Arrow
        func_by_chords[b"\x1B[D"] = vi.do_slip_left  # ← Left Arrow

        # func_by_chords[b"\x1C"] = vi.do_eval_vi_line   # FS, ⌃\, 28
        # func_by_chords[b"\x1D"] = vi.do_c0_control_gs  # GS, ⌃], 29
        # func_by_chords[b"\x1E"] = vi.do_c0_control_rs  # RS, ⌃^, 30
        # func_by_chords[b"\x1F"] = vi.do_c0_control_us  # US, ⌃_, 31

        func_by_chords[b"\x7F"] = vi.do_slip_behind  # DEL, ⌃?, 127

        # Define the BASIC_LATIN_STDINS

        func_by_chords[b" "] = vi.do_slip_ahead
        # func_by_chords[b"!"] = vi.do_pipe
        # func_by_chords[b'"'] = vi.do_arg
        func_by_chords[b"#"] = vi.do_find_behind_vi_this
        func_by_chords[b"$"] = vi.do_slip_last_seek
        # func_by_chords[b"%"]  # TODO: leap to match
        # func_by_chords[b"&"]  # TODO: & and && for repeating substitution
        # func_by_chords[b"'"]  # TODO: leap to pin
        # func_by_chords[b"("]  # TODO: sentence behind
        # func_by_chords[b")"]  # TODO: sentence ahead
        func_by_chords[b"*"] = vi.do_find_ahead_vi_this
        func_by_chords[b"+"] = vi.do_step_down_dent
        func_by_chords[b","] = vi.do_slip_choice_undo
        func_by_chords[b"-"] = vi.do_step_up_dent
        func_by_chords[b"/"] = vi.do_find_ahead_vi_line

        func_by_chords[b"0"] = vi.do_slip_first
        func_by_chords[b"1234567890"] = None  # TODO: say this more elegantly

        self._init_correcting_many_chords(b":/", corrections=b"/")
        self._init_correcting_many_chords(b":?", corrections=b"?")

        self._init_func_by_many_vi_chords(b":g/", func=vi.do_find_all_vi_line)
        self._init_func_by_many_vi_chords(b":n\r", func=vi.do_might_next_vi_file)
        self._init_func_by_many_vi_chords(b":n!\r", func=vi.do_next_vi_file)
        self._init_func_by_many_vi_chords(b":noh\r", func=editor.do_set_invhlsearch)
        self._init_func_by_many_vi_chords(b":q\r", func=vi.do_might_quit_vi)
        self._init_func_by_many_vi_chords(b":q!\r", func=vi.do_quit_vi)
        self._init_func_by_many_vi_chords(b":w\r", func=vi.do_might_flush_vi)
        self._init_func_by_many_vi_chords(b":w!\r", func=vi.do_flush_vi)
        self._init_func_by_many_vi_chords(b":wq\r", func=vi.do_might_flush_quit_vi)
        self._init_func_by_many_vi_chords(b":wq!\r", func=vi.do_flush_quit_vi)

        func_by_chords[b";"] = vi.do_slip_choice_redo
        # func_by_chords[b"<"]  # TODO: dedent
        # func_by_chords[b"="]  # TODO: dent after
        # func_by_chords[b">"]  # TODO: indent
        func_by_chords[b"?"] = vi.do_find_behind_vi_line
        # func_by_chords[b"@"] = vi.do_replay_input

        # func_by_chords[b"A"] = vi.do_slip_last_right_open
        func_by_chords[b"B"] = vi.do_big_word_start_behind
        # func_by_chords[b"C"] = vi.do_chop_open
        # func_by_chords[b"D"] = vi.do_chop
        func_by_chords[b"E"] = vi.do_big_word_end_ahead

        self._init_suffix_func(b"F", func=vi.do_slip_rindex)

        func_by_chords[b"G"] = vi.do_step
        func_by_chords[b"H"] = vi.do_step_max_high
        # func_by_chords[b"I"] = vi.do_slip_dent_open
        # func_by_chords[b"J"] = vi.do_slip_last_join_right
        # func_by_chords[b"K"] = vi.do_lookup
        func_by_chords[b"L"] = vi.do_step_max_low
        func_by_chords[b"M"] = vi.do_step_to_middle
        func_by_chords[b"N"] = vi.do_vi_find_earlier
        # func_by_chords[b"O"] = vi.do_slip_first_open
        # func_by_chords[b"P"] = vi.do_paste_behind

        self._init_func_by_many_vi_chords(b"Qvi\r", func=vi.do_continue_vi)

        # func_by_chords[b"R"] = vi.do_open_overwrite
        # func_by_chords[b"S"] = vi.do_slip_first_chop_open

        self._init_suffix_func(b"T", func=vi.do_slip_rindex_plus)

        # func_by_chords[b"U"] = vi.do_row_undo
        # func_by_chords[b"V"] = vi.do_gloss_rows
        func_by_chords[b"W"] = vi.do_big_word_start_ahead
        # func_by_chords[b"X"] = vi.do_cut_behind
        # func_by_chords[b"Y"] = vi.do_copy_row

        self._init_correcting_many_chords(b"QZ", corrections=b"Z")
        # TODO: stop commandeering the personal QZ Chord Sequence

        self._init_func_by_many_vi_chords(b"ZQ", func=vi.do_quit_vi)
        self._init_func_by_many_vi_chords(b"ZZ", func=vi.do_flush_quit_vi)

        # func_by_chords[b"["]  # TODO: b"["

        self._init_func_by_many_vi_chords(b"\\\x1B", func=editor.do_set_invhlsearch)
        self._init_func_by_many_vi_chords(b"\\F", func=editor.do_set_invregex)
        self._init_func_by_many_vi_chords(b"\\i", func=editor.do_set_invignorecase)
        self._init_func_by_many_vi_chords(b"\\n", func=editor.do_set_invnumber)

        # TODO: stop commandeering the personal \Esc \F \i \n Chord Sequences

        # func_by_chords[b"]"]  # TODO: b"]"
        func_by_chords[b"^"] = vi.do_slip_dent
        func_by_chords[b"_"] = vi.do_step_down_minus_dent
        # func_by_chords[b"`"]  # TODO: close to b"'"

        # func_by_chords[b"a"] = vi.do_slip_right_open
        func_by_chords[b"b"] = vi.do_lil_word_start_behind
        # func_by_chords[b"c"] = vi.do_chop_after_open
        # func_by_chords[b"d"] = vi.do_chop_after
        func_by_chords[b"e"] = vi.do_lil_word_end_ahead

        self._init_suffix_func(b"f", func=vi.do_slip_index)

        self._init_correcting_many_chords(b"g/", corrections=b":g/")
        # TODO: stop commandeering the personal g/ Chord Sequence

        # func_by_chords[b"g"]
        func_by_chords[b"h"] = vi.do_slip_left
        # func_by_chords[b"i"] = vi.do_open
        func_by_chords[b"j"] = vi.do_step_down_seek
        func_by_chords[b"k"] = vi.do_step_up_seek
        func_by_chords[b"l"] = vi.do_slip_right

        # self._init_suffix_func(b"m", func=vi.do_drop_pin)

        func_by_chords[b"n"] = vi.do_vi_find_later
        # func_by_chords[b"o"] = vi.do_slip_last_right_open
        # func_by_chords[b"p"] = vi.do_paste_ahead
        # func_by_chords[b"q"] = vi.do_record_input

        # self._init_suffix_func(b"r", func=vi.do_overwrite_char)

        # func_by_chords[b"s"] = vi.do_cut_behind_open

        self._init_suffix_func(b"t", func=vi.do_slip_index_minus)

        # func_by_chords[b"u"] = vi.do_undo
        # func_by_chords[b"v"] = vi.do_gloss_chars
        func_by_chords[b"w"] = vi.do_lil_word_start_ahead
        # func_by_chords[b"x"] = vi.do_cut_ahead
        # func_by_chords[b"y"] = vi.do_copy_after

        self._init_func_by_many_vi_chords(b"zb", func=vi.do_scroll_till_bottom)
        self._init_func_by_many_vi_chords(b"zt", func=vi.do_scroll_till_top)
        self._init_func_by_many_vi_chords(b"zz", func=vi.do_scroll_till_middle)

        func_by_chords[b"{"] = vi.do_paragraph_behind
        func_by_chords[b"|"] = vi.do_slip
        func_by_chords[b"}"] = vi.do_paragraph_ahead
        # func_by_chords[b"~"] = vi.do_flip_case_overwrite

        # Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS

        func_by_chords["£".encode()] = vi.do_find_behind_vi_this  # \u00A3 GBP


#
# Edit some Chars in the Bottom Lines of the Screen
#


class TerminalSkinEx:
    """Feed Keyboard into Line at Bottom of Screen of Scrolling Rows, a la Ex"""

    def __init__(self, editor, vi_reply):

        self.editor = editor
        self.vi_reply = vi_reply
        self.ex_line = ""

    def format_ex_reply(self):
        """Keep up the Vi Reply while working the Ex Keyboard, but add the Input Line"""

        vi_reply = self.vi_reply
        ex_line = self.ex_line

        ex_reply = vi_reply + ex_line

        return ex_reply

    def paint_ex_cursor(self):
        """Place the Screen Cursor"""

        editor = self.editor
        painter = editor.painter
        terminal = painter

        ex_reply = self.format_ex_reply()

        terminal.row = painter.status_row
        terminal.column = len(ex_reply)

    def read_ex_line(self):
        """Take an Input Line from beneath the Scrolling Rows"""

        self.ex_line = ""

        try:
            self.run_ex_keyboard()
            assert False  # unreached
        except SystemExit:
            pass

        line = self.ex_line

        return line

    def run_ex_keyboard(self):
        """Edit an Input Line beneath the Scrolling Rows"""

        editor = self.editor

        keyboard = TerminalKeyboardEx(terminal_ex=self, editor=editor)
        editor.run_keyboard(keyboard)
        assert False  # unreached

    def do_clear_chars(self):  # Vim Ex ⌃U
        """Undo all the Append Chars, if any Not undone already"""

        self.ex_line = ""

    def do_append_char(self):
        """Append the Chords to the Input Line"""

        editor = self.editor
        chords = editor.get_arg0()

        chars = chords.decode(errors="surrogateescape")

        if chars == "£":  # TODO: less personal choice
            self.ex_line += "#"  # a la Vim :abbrev £ #
        else:
            self.ex_line += chars

    def do_append_suffix(self):  # Vim Ex ⌃V
        """Append the Suffix Chord to the Input Line"""

        chars = self.editor.arg2

        raise NotImplementedError(repr(chars))

        self.ex_line += chars

    def do_undo_append_char(self):
        """Undo the last Append Char, else Quit Ex"""

        ex_line = self.ex_line
        if ex_line:
            self.ex_line = ex_line[:-1]
        else:
            self.ex_line = None

            sys.exit()

    def do_quit_ex(self):  # Vim Ex ⌃C

        self.ex_line = None

        sys.exit()


class TerminalKeyboardEx(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Ex"""

    def __init__(self, terminal_ex, editor):

        ex = terminal_ex

        self.ex = ex
        self.editor = editor
        assert ex.editor in (None, editor), (ex, ex.editor, editor)

        self.format_reply_func = ex.format_ex_reply
        self.paint_cursor_func = ex.paint_ex_cursor
        self.enter_do_func = lambda: None
        self.do_func = editor.do_raise_name_error
        self.exit_do_func = lambda: None

        self.corrections_by_chords = dict()
        self.func_by_chords = dict()
        self.suffixes_by_chords = dict()

        self._init_by_ex_chords_()

    def _init_by_ex_chords_(self):

        ex = self.ex
        func_by_chords = self.func_by_chords
        editor = self.editor

        # Define the C0_CONTROL_STDINS

        for chords in sorted(C0_CONTROL_STDINS):
            func_by_chords[chords] = editor.do_raise_name_error

        # Mutate the C0_CONTROL_STDINS definitions

        func_by_chords[b"\x03"] = ex.do_quit_ex  # ETX, ⌃C, 3
        func_by_chords[b"\x0D"] = editor.do_sys_exit  # CR, ⌃M, 13 \r
        func_by_chords[b"\x15"] = ex.do_clear_chars  # NAK, ⌃U, 21

        self._init_suffix_func(b"\x16", func=ex.do_append_suffix)  # SYN, ⌃V, 22

        func_by_chords[b"\x7F"] = ex.do_undo_append_char  # DEL, ⌃?, 127

        # Define the BASIC_LATIN_STDINS

        for chords in BASIC_LATIN_STDINS:
            func_by_chords[chords] = ex.do_append_char

        # Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS

        func_by_chords["£".encode()] = ex.do_append_char

        # TODO: input Search Keys containing more than BASIC_LATIN_STDINS and #

        # TODO: define Esc to replace live Regex punctuation with calmer r"."


#
# Define the Editors above in terms of Inputs, Outputs, & Selections of Chars
#


class TerminalNudgeIn(argparse.Namespace):
    """Take the Keyboard Chords of one Input"""

    def __init__(self, prefix=None, chords=None, suffix=None, epilog=None):

        self.prefix = prefix  # such as Repeat Count Digits before Vi Chords
        self.chords = chords  # such as b"Qvi\r" Vi Chords
        self.suffix = suffix  # such as b"x" of b"fx" to Find Char "x" in Vi
        self.epilog = epilog  # such as b"⌃C" of b"f⌃C" to cancel b"f"

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

    def __init__(self, flags=None, nudge=None, message=None):

        self.flags = flags  # such as "-Fin" Grep-Like Search
        self.nudge = nudge  # keep up a trace of the last input that got us here
        self.message = message  # say more

    # Jun/2018 Python 3.7 can say '._defaults=(None, None),'


class TerminalPin(collections.namedtuple("TerminalPin", "row, column".split(", "))):
    """Pair up a choice of Row and a choice of Column"""


class TerminalSpan(
    collections.namedtuple("TerminalSpan", "row, column, beyond".split(", "))
):
    """Pick out the Columns of Rows covered by a Match of Chars"""

    # TODO:  class TerminalPinVi - to slip and step in the way of Vi

    @staticmethod
    def find_spans(matches):
        """Quickly calculate the Row and Column of each of a List of Spans"""

        if not matches:

            return list()

        # Split the Lines apart

        some_match = matches[-1]

        chars = some_match.string
        ended_lines = chars.splitlines(keepends=True)

        # Search each Line for the next Match

        spanned_lines = list()
        spanned_chars = ""

        spans = list()
        for match in matches:
            assert match.string is some_match.string

            start = match.start()
            while start > len(spanned_chars):
                ended_line = ended_lines[len(spanned_lines)]

                spanned_lines.append(ended_line)
                spanned_chars += ended_line

            # Find the Row of the Match, in or beyond the Spanned Lines

            row = 0
            line_at = 0
            if spanned_lines:

                row = len(spanned_lines) - 1
                spanned_line = spanned_lines[-1]
                line_at = len(spanned_chars) - len(spanned_line)

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
            if last_span.row >= len(ended_lines):

                del spans[-1]

        return spans


class TerminalEditor:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars"""

    editor_skin_stack = list()

    def __init__(self, chords):

        self.chords_ahead = list(chords)

        #

        self.traceback = None  # capture Python Tracebacks

        self.painter = None  # layer over a Terminal I/O Stack
        self.shadow = None
        self.driver = None
        self.stdio = None

        self.showing_line_number = None  # show Line Numbers or not
        self.injecting_lag = None  # inject extra Lag or not

        self.finding_case = None  # ignore Upper/Lower Case in Searching or not
        self.finding_line = None  # remember the Search Key
        self.finding_regex = None  # search as Regex or search as Chars
        self.finding_slip = 0  # remember to Search again ahead or again behind
        self.finding_highlights = None  # highlight all spans on screen or no spans

        # TODO: self.~_ = mutable namespace ~ for self.finding_, argv_, doing_, etc

        #

        self.keyboard = None  # map Keyboard Inputs to Code

        self.nudge = TerminalNudgeIn()  # split the Chords of one Keyboard Input
        self.arg0 = None  # take all the Chords as Chars in a Row
        self.arg1 = None  # take the Prefix Bytes as an Int of Decimal Digits
        self.arg2 = None  # take the Suffix Bytes as one Encoded Char

        self.sending_bell = None  # ring the Terminal Bell as part of some Prompt's
        self.reply = TerminalReplyOut()  # declare an Empty Reply

        self.doing_less = None  # reject the Arg1 when not explicitly accepted
        self.doing_more = None  # take the Arg1 as a Count of Repetition's
        self.doing_done = None  # count the Repetition's completed before now

        self.flagging_more = None  # keep up some Flags in the Reply to a Nudge

        #

        self._init_iobytearray_etc_(iobytearray=b"")

    def _init_iobytearray_etc_(self, iobytearray):
        """Swap in a new File of Lines"""

        self.iobytearray = iobytearray

        chars = iobytearray.decode(errors="surrogateescape")
        ended_lines = chars.splitlines(keepends=True)
        self.ended_lines = ended_lines  # Ended Lines of Chars decoded from Bytes

        self.row = 0  # point the Screen Cursor to a Row of File
        self.column = 0  # point the Screen Cursor to a Column of File

        self.top_row = 0  # scroll through more Lines than fit on Screen

        self.iobytespans = list()  # cache the spans in file
        self.reopen_found_spans()

    #
    # Stack Skin's with Keyboard's on top of a Terminal I/O Stack
    #

    def run_terminal(self, keyboard):
        """Stack Skin's with Keyboard's on top of a Terminal I/O Stack"""

        stdio = sys.stderr
        with TerminalDriver(terminal=stdio) as driver:
            shadow = TerminalShadow(terminal=driver)
            painter = TerminalPainter(terminal=shadow)

            self.painter = painter
            self.shadow = shadow
            self.driver = driver
            self.stdio = stdio

            self.run_keyboard(keyboard)  # till SystemExit

    def run_keyboard(self, keyboard):
        """Read keyboard Input, eval it, print replies, till SystemExit"""

        self._enter_skin_()
        try:
            self._try_run_keyboard_(keyboard)
        finally:
            self._exit_skin_(*sys.exc_info())

    def _enter_skin_(self):
        """Push an Editor Skin to make room for a new Editor Skin"""

        editor_skin = (
            self.keyboard,
            self.nudge,
            self.arg0,
            self.arg1,
            self.arg2,
            self.sending_bell,
            self.reply,
            self.doing_less,
            self.doing_more,
            self.doing_done,
            self.flagging_more,
        )

        TerminalEditor.editor_skin_stack.append(editor_skin)

    def _exit_skin_(self, exc_type, exc_value, traceback):
        """Pop back an old Editor Skin"""

        _ = (exc_type, exc_value, traceback)

        editor_skin = TerminalEditor.editor_skin_stack.pop()

        (
            self.keyboard,
            self.nudge,
            self.arg0,
            self.arg1,
            self.arg2,
            self.sending_bell,
            self.reply,
            self.doing_less,
            self.doing_more,
            self.doing_done,
            self.flagging_more,
        ) = editor_skin

    def _try_run_keyboard_(self, keyboard):
        """Prompt, take input, react, repeat till quit"""

        self.keyboard = keyboard

        # Repeat till SystemExit raised

        self.nudge = TerminalNudgeIn()

        while True:

            # Scroll and prompt

            self.scroll_cursor_into_screen()

            self.prompt_for_chords()

            self.flagging_more = None
            self.reply = TerminalReplyOut()
            self.sending_bell = None

            # Take one Chord in, or next Chord, or cancel Chords to start again

            try:
                chord = self.terminal_getch()
            except KeyboardInterrupt:
                chord = b"\x03"  # ETX, ⌃C, 3

                if self.nudge != TerminalNudgeIn():  # if not meaning 'do_help_quit_vi'
                    self.nudge.epilog = chord
                    self.editor_print("Cancelled")  # 123⌃C Egg, f⌃C Egg, etc

                    self.nudge = TerminalNudgeIn()

                    continue

            func = self.choose_func(chord)
            if func is None:

                continue

            # Reply

            keyboard.enter_do_func()
            try:
                self.call_func(func)  # reply to one whole Nudge
            finally:
                keyboard.exit_do_func()

            self.nudge = TerminalNudgeIn()  # consume the whole Nudge

    def scroll_cursor_into_screen(self):
        """Scroll to place Cursor on Screen"""

        row = self.row
        painter = self.painter
        top_row = self.top_row

        half_screen = painter.scrolling_rows // 2
        last_row = self.spot_last_row()
        screen_minus = painter.scrolling_rows - 1

        # Keep the choice of Top Row on File

        top = top_row
        if not (0 <= top_row < len(self.ended_lines)):
            top = 0

        # Scroll behind to get Cursor on Screen, if need be

        if row < top:
            if (top - row) <= half_screen:
                top = row
            elif row < half_screen:
                top = row
            else:
                top = row - half_screen  # a la 'do_scroll_till_middle' Vim zz

        # Scroll ahead to get Cursor on Screen, if need be

        bottom = self.spot_bottom_row(top_row=top)
        if row > bottom:
            if (row - bottom) <= half_screen:
                top = row - screen_minus
            elif (last_row - row) < half_screen:
                top = last_row - screen_minus
            else:
                top = row - half_screen  # a la 'do_scroll_till_middle' Vim zz

        # After fixing the choice, assert the Top Row always was on File

        self.top_row = top

        if top_row:
            if not (0 <= top_row < len(self.ended_lines)):
                raise KwArgsException(before=top_row, after=self.top_row)

    def prompt_for_chords(self):
        """Write over the Rows of Chars on Screen"""

        # 1st: Rewrite whole Screen slowly to override bugs in TerminalShadow

        if not self.injecting_lag:
            # time.sleep(0.3)  # compile-time option for a different kind of lag

            if self.sending_bell:  # in reply to Bell signalling trouble
                self.painter._reopen_terminal_()

        # 2nd: Call back

        status = self.keyboard.format_reply_func()
        self.keyboard.paint_cursor_func()

        # 3rd: Walk through the steps of writing Screen, Cursor, and Bell

        ended_lines = self.ended_lines
        painter = self.painter
        sending_bell = self.sending_bell

        terminal = painter

        # Consume

        # Form

        screen_lines = ended_lines[self.top_row :][: painter.scrolling_rows]
        screen_spans = self.spot_spans_on_screen()

        # Write Screen, Cursor, and Bell

        painter.top_line_number = 1 + self.top_row
        painter.last_line_number = 1 + len(ended_lines)
        painter.painting_line_number = self.showing_line_number

        painter.write_screen(
            ended_lines=screen_lines, spans=screen_spans, status=status
        )

        if sending_bell:
            painter.write_bell()

        # Flush Screen, Cursor, and Bell

        terminal.flush()

    def spot_spans_on_screen(self):
        """Say where to highlight each Match of the Search Key on Screen"""

        if not self.finding_highlights:

            return list()

        iobytespans = self.iobytespans
        top_row = self.top_row
        bottom_row = self.spot_bottom_row()

        screen_spans = list()
        for span in iobytespans:
            if top_row <= span.row <= bottom_row:

                screen_span_row = span.row - top_row
                screen_span = TerminalSpan(
                    screen_span_row, column=span.column, beyond=span.beyond
                )
                screen_spans.append(screen_span)

        return screen_spans

    def choose_func(self, chord):
        """Accept one Keyboard Input into Prefix, into main Chords, or as Suffix"""

        prefix = self.nudge.prefix
        chords = self.nudge.chords
        keyboard = self.keyboard

        corrections_by_chords = keyboard.corrections_by_chords
        func_by_chords = keyboard.func_by_chords

        assert self.nudge.suffix is None, (chords, chord)  # one Chord only

        # Take more decimal Digits, while nothing but decimal Digits given

        if b"1234567890" in func_by_chords.keys():
            if not chords:
                if (chord in b"123456789") or (prefix and (chord == b"0")):

                    prefix_plus = chord if (prefix is None) else (prefix + chord)
                    self.nudge.prefix = prefix_plus
                    self.editor_print()  # echo Prefix

                    # Ask for more Prefix, else for main Chords

                    return None  # ask for more Prefix, or for other Chords

        self.arg1 = int(prefix) if prefix else None
        assert self.get_arg1() >= 1

        # If not taking a Suffix now

        chords_plus = chord if (chords is None) else (chords + chord)

        func = func_by_chords.get(chords)
        if not (func and (chords in keyboard.suffixes_by_chords)):
            self.nudge.chords = chords_plus
            self.editor_print()  # echo Prefix + Chords

            self.arg0 = chords_plus

            # If need more Chords

            default = keyboard.do_func
            func_plus = func_by_chords.get(chords_plus, default)
            if (not func_plus) or (chords_plus in keyboard.suffixes_by_chords):

                # Option to auto-correct the Chords

                if chords_plus in corrections_by_chords.keys():
                    self.nudge.chords = b""
                    corrections = corrections_by_chords[chords_plus]
                    self.chords_ahead = list(corrections) + self.chords_ahead
                    self.editor_print("Corrected")

                # Ask for more Chords, or for Suffix

                return None

            self.arg2 = None

            # Call a Func with or without Prefix, and without Suffix

            assert chords_plus not in corrections_by_chords.keys(), (chords, chord)
            assert func_plus is not None, (chords, chord)

            return func_plus

        assert self.arg0 == chords, (chords, chord, self.arg0)

        # Call a Func chosen by Chords plus Suffix

        suffix = chord
        self.nudge.suffix = suffix
        self.editor_print()  # echo Prefix + Chords + Suffix

        self.arg2 = suffix.decode(errors="surrogateescape")

        # Call a Func with Suffix, but with or without Prefix

        assert chords not in corrections_by_chords.keys()
        assert func is not None, (chords, chord)

        return func

    def call_func(self, func):
        """Call the Func once or more, in reply to one Terminal Nudge In"""

        # Start calling

        self.doing_done = 0
        while True:
            self.doing_less = True
            self.doing_more = None

            try:

                func()
                self.keep_cursor_on_file()
                self.traceback = None

                if self.doing_less:
                    arg1 = self.get_arg1(default=None)
                    if arg1 is not None:
                        raise NotImplementedError("Repeat Count {}".format(arg1))

            # Stop calls on Exception

            except Exception as exc:  # Egg of NotImplementedError, etc

                name = type(exc).__name__
                str_exc = str(exc)

                line = "{}: {}".format(name, str_exc) if str_exc else name
                self.editor_print(line)  # "{exc_type}: {str_exc}"
                self.send_bell()

                self.traceback = traceback.format_exc()
                # file_print(self.traceback)  # compile-time option to log every Exc

                break

            # Let the Func take the Arg as a Count of Repetitions, but don't force it

            if self.doing_more:
                self.doing_done += 1
                if self.doing_done < self.get_arg1():

                    continue

            break

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
        arg1_ = default if (arg1 is None) else arg1

        self.doing_less = False

        return arg1_

    def get_arg2(self):
        """Get the Bytes of the input Suffix past the input Chords"""

        arg2 = self.arg2
        assert arg2 is not None

        return arg2

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.arg1' times"""

        self.doing_less = False
        self.doing_more = True

    #
    # Send and tweak replies
    #

    def editor_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        flagging_more = self.flagging_more
        flags = flagging_more if flagging_more else None

        nudge = self.nudge

        message = " ".join(str(_) for _ in args)

        self.reply = TerminalReplyOut(flags=flags, nudge=nudge, message=message)

    def flag_reply_with_find(self):
        """Add the Find Flags into the last Reply, before showing it"""

        flags = self.format_find_flags()
        self.reply.flags = flags
        self.flagging_more = flags

    def format_find_flags(self):
        """Show Search Flags a la Bash Grep Switches"""

        flags = ""
        if not self.finding_regex:
            flags += "F"
        if not self.finding_case:
            flags += "i"
        if self.showing_line_number:
            flags += "n"

        str_flags = "-{}".format(flags) if flags else ""

        return str_flags

    def send_bell(self):
        """Ring the Terminal Bell as part of the next Prompt"""

        self.sending_bell = True

    def terminal_print(self, *args, end="\r\n"):
        """Scroll up and write Line"""

        line = " ".join(str(_) for _ in args)
        self.driver.write(line + end)

    def terminal_getch(self):
        """Block till next keyboard input Chord"""

        chords_ahead = self.chords_ahead
        terminal = self.painter

        if not chords_ahead:
            chord = terminal.getch()  # may raise KeyboardInterrupt
        else:
            ord_chord = chords_ahead.pop(0)  # may be b"\x03" ETX, ⌃C, 3
            chord = chr(ord_chord).encode()

        return chord

    #
    # Focus on one Line of a File of Lines
    #

    def charsets_find_column(self, charsets, default=" "):
        """Return the Index of the first CharSet containing Column Char, else -1"""

        chars = self.fetch_column_char(default=default)

        for (index, charset) in enumerate(charsets):
            if chars in charset:

                return index

        return -1

    def count_columns_in_row(self):
        """Count Columns in Row beneath Cursor"""

        ended_lines = self.ended_lines
        row = self.row

        if row >= len(ended_lines):
            raise IndexError(row)

        ended_line = ended_lines[row]
        line = ended_line.splitlines()[0]

        columns = len(line)

        return columns

    def count_rows_in_file(self):
        """Count Rows in Buffer of File"""

        rows = len(self.ended_lines)

        return rows

    def fetch_column_char(self, column=None, default=" "):
        """Get the one Char at the Column in the Row beneath the Cursor"""

        column_ = self.column if (column is None) else column

        ended_line = self.ended_lines[self.row]
        line = ended_line.splitlines()[0]

        ch = line[column_] if (column_ < len(line)) else default

        return ch

    def fetch_row_line(self, row=None):
        """Get Chars of Columns in Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_line = self.ended_lines[row_]
        line = ended_line.splitlines()[0]

        return line

    def may_slip_ahead(self):
        """Return None at End of File, else return 1"""

        last_row = self.spot_last_row()
        last_column = self.spot_last_column()

        if (self.row, self.column) != (last_row, last_column):
            return 1

    def may_slip_behind(self):
        """Return None at Start of File, else return 1"""

        if (self.row, self.column) != (0, 0):
            return 1

    def spot_bottom_row(self, top_row=None):
        """Find the Bottom Row of File on Screen"""

        top_row_ = self.top_row if (top_row is None) else top_row
        painter = self.painter

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        bottom_row = top_row_ + (painter.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def spot_last_row(self):
        """Find the last Row in File, else Row Zero when no Rows in File"""

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        return last_row

    def spot_last_column(self, row=None):
        """Find the last Column in Row, else Column Zero when no Columns in Row"""

        row_ = self.row if (row is None) else row
        ended_lines = self.ended_lines

        if row_ >= len(ended_lines):
            raise IndexError(row)

        ended_line = ended_lines[row_]
        line = ended_line.splitlines()[0]

        columns = len(line)
        last_column = (columns - 1) if columns else 0

        return last_column

    def spot_middle_row(self):
        """Find the Middle Row on Screen, of the Rows that carry Lines of File"""

        top_row = self.top_row
        bottom_row = self.spot_bottom_row()
        rows_on_screen = bottom_row - top_row + 1

        middle = (rows_on_screen + 1) // 2  # match +1 bias in Vi's 'spot_middle_row'
        middle_row = top_row + middle

        return middle_row

    #
    # Define Chords common to many TerminalEditor's
    #

    def do_raise_name_error(self):  # Vim Zz  # Vim zZ  # etc
        """Reply to meaningless Keyboard Input"""

        echo_bytes = self.nudge.join_echo_bytes()  # similar or same as 'self.arg0'

        escapes = ""
        for xx in echo_bytes:
            escapes += r"\x{:02X}".format(xx)

        arg = "b'{}'".format(escapes)
        raise NameError(arg)

    def do_redraw(self):  # Vim ⌃L
        """Toggle between more and less Lag (vs Vim injects lots of Lag exactly once)"""

        painter = self.painter

        injecting_lag = not self.injecting_lag
        if injecting_lag:
            painter.terminal = self.driver
        else:
            painter.terminal = self.shadow
            painter._reopen_terminal_()

        self.injecting_lag = injecting_lag

        if injecting_lag:
            self.editor_print(":set _lag_")
        else:
            self.editor_print(":set no_lag_")

    def do_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        terminal = self.painter

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()'
        terminal.__exit__(*exc_info)
        os.kill(os.getpid(), signal.SIGTSTP)
        terminal.__enter__()

    def do_sys_exit(self):  # Ex Return
        """Stop taking more Keyboard Input"""

        sys.exit()

    #
    # Find Spans of Chars
    #

    def do_set_invhlsearch(self):  # \Esc Egg
        """Highlight Matches or not, but without rerunning Search"""

        self.finding_highlights = not self.finding_highlights

        if self.finding_highlights:
            self.flag_reply_with_find()
            self.editor_print(":set hlsearch")
        else:
            self.editor_print(":nohlsearch")

        # Vim lacks ':invhlsearch' and lacks ':hlsearch'
        # Vi Py \Esc means ':invhlsearch' not just the ':noh' .. ':nohlsearch'

    def do_set_invignorecase(self):  # \i Egg
        """Search Upper/Lower Case or not"""

        self.finding_case = not self.finding_case

        self.reopen_found_spans()

        if self.finding_case:
            self.editor_print(":set noignorecase")
        else:
            self.editor_print(":set ignorecase")

    def do_set_invnumber(self):  # \n Egg
        """Show Line Numbers or not, but without rerunning Search"""

        self.showing_line_number = not self.showing_line_number

        if self.showing_line_number:
            self.editor_print(":set number")
        else:
            self.editor_print(":set nonumber")

    def do_set_invregex(self):  # \F Egg
        """Search as Regex or search as Chars"""

        self.finding_regex = not self.finding_regex

        self.reopen_found_spans()

        if self.finding_regex:
            self.editor_print(":set regex")  # kin to Vim default
        else:
            self.editor_print(":set noregex")  # doesn't exist in Vim

    def reopen_found_spans(self):
        """Find Chars in File"""

        iobytearray = self.iobytearray
        iobytespans = self.iobytespans

        # Cancel the old Spans

        iobytespans.clear()

        # Find the New Spans

        self.finding_highlights = None
        if self.finding_line is not None:
            self.finding_highlights = True

            pattern = self.finding_line
            if not self.finding_regex:
                pattern = re.escape(pattern)

            flags = 0
            flags |= re.MULTILINE
            if not self.finding_case:
                flags |= re.IGNORECASE

            chars = iobytearray.decode(errors="surrogateescape")
            matches = list(re.finditer(pattern, string=chars, flags=flags))
            iobytespans[::] = TerminalSpan.find_spans(matches)

            if matches:  # as many Spans as Matches, except for such as r"$" in "abc\n"
                assert iobytespans
                assert len(iobytespans) in (len(matches), len(matches) - 1)

    def print_some_found_spans(self, before_status):
        """Print as many of the Found Spans as fit on screen"""
        # Vim prints more through a Less-like Paginator

        iobytespans = self.iobytespans
        painter = self.painter

        terminal = painter

        last_line_number = 1 + len(self.ended_lines)
        str_last_line_number = "{:3} ".format(last_line_number)
        last_width = len(str_last_line_number)

        # Scroll up the Status Line

        self.terminal_print("")

        # Visit each Span

        printed_row = None
        assert self.iobytespans
        for span in self.iobytespans:

            (found_row, found_column, _) = span

            line_number = 1 + found_row
            str_line_number = ""  # TODO: merge with 'format_as_line_number'
            if self.showing_line_number:
                str_line_number = "{:3} ".format(line_number).rjust(last_width)

            line = self.fetch_row_line(row=found_row)

            # Print each Line of Spans only once

            if found_row != printed_row:
                printed_row = found_row

                self.terminal_print(str_line_number + line)  # may wrap multiple rows

        (self.row, self.column) = (found_row, found_column)

        # Track experimental Code for echoing Search

        if False:  # FIXME: this only works when :g/ finds a screen or more of hits

            self.driver.write(CUP_1_1)
            self.driver.write(before_status.ljust(painter.columns))

            y = 1 + self.painter.status_row
            x = 1
            self.driver.write(CUP_Y_X.format(y, x))

        # Prompt for next keyboard input Chord, and block till it arrives

        self.editor_print(  # "{}/{} Press Return to continue . . .
            "{}/{} Press Return to continue . . .".format(
                len(iobytespans), len(iobytespans)
            )
        )
        after_status = self.keyboard.format_reply_func()

        self.terminal_print(after_status, end=" ")
        self.driver.flush()
        _ = self.terminal_getch()

        terminal._reopen_terminal_()

        # TODO: highlight Matches in :g/ Lines

    def find_ahead_and_reply(self):
        """Find the Search Key ahead, else after start, else fail silently"""

        spans = self.iobytespans
        row = self.row
        column = self.column

        # Find none

        if not spans:
            self.editor_print("No chars found: not ahead and not after start")

            return

        self.finding_highlights = True

        # Find one or more, ahead, else after start

        here0 = (row, column)
        here1 = (-1, -1)  # before start
        heres = (here0, here1)

        how0 = "{}/{}  Found {} chars ahead"
        how1 = "{}/{}  Found {} chars, not ahead, found instead after start"
        hows = (how0, how1)

        for (here, how) in zip(heres, hows):
            for (index, span) in enumerate(spans):
                len_chars = span.beyond - span.column
                there = self.spot_row_column_near_span(span)

                if here < there:

                    how_ = how
                    if there == here0:
                        how_ = "{}/{}  Found {} chars, here and only here"

                    self.editor_print(  # "{}/{}  Found ...
                        how_.format(1 + index, len(spans), len_chars)
                    )

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def find_behind_and_reply(self):
        """Find the Search Key loudly: behind, else before end, else not"""

        spans = self.iobytespans
        row = self.row
        column = self.column

        # Find none

        if not spans:
            self.editor_print("No chars found: not behind and not before end")

            return

        self.finding_highlights = True

        # Find one or more, behind, else before end

        here0 = (row, column)
        here1 = (self.spot_last_row() + 1, 0)  # after end
        heres = (here0, here1)

        how0 = "{}/{}  Found {} chars behind"
        how1 = "{}/{}  Found {} chars, not behind, found instead before end"
        hows = (how0, how1)

        for (here, how) in zip(heres, hows):
            for (index, span) in enumerate(reversed(spans)):
                len_chars = span.beyond - span.column
                there = self.spot_row_column_near_span(span)

                if there < here:

                    how_ = how
                    if there == here0:
                        how_ = "{}/{}  Found {} chars, here and only here"

                    self.editor_print(  # "{}/{}  Found ...
                        how_.format(1 + index, len(spans), len_chars)
                    )

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def spot_row_column_near_span(self, span):
        """Find the Row:Column in File nearest to a Span"""

        try:

            there_row = span.row
            there_last_column = self.spot_last_column(row=there_row)
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

        self.top_line_number = 1  # number the Scrolling Rows down from First of Screen
        self.last_line_number = 1  # number all Rows as wide as the Last Row of File
        self.painting_line_number = None  # number the Scrolling Rows visibly, or not

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

        if chord == b"\x03":  # ETX, ⌃C, 3
            raise KeyboardInterrupt()

        return chord

    def write_screen(self, ended_lines, spans, status):
        """Write over the Rows of Chars on Screen"""

        terminal = self.terminal

        column = self.column
        columns = self.columns
        left_column = self.spot_left_column()
        row = self.row
        scrolling_rows = self.scrolling_rows

        # Fill the Screen with Lines of "~" past the last Line of File

        lines = list(_.splitlines()[0] for _ in ended_lines)

        while len(lines) < scrolling_rows:
            lines.append("~")

        assert len(lines) == scrolling_rows, (len(lines), scrolling_rows)

        # Number the Scrolling Lines of the Screen

        for (index, line) in enumerate(lines):
            str_line_number = self.format_as_line_number(index)
            numbered_and_chopped = (str_line_number + line)[:columns]
            lines[index] = numbered_and_chopped

        # Write the formatted chars

        terminal.write(ED_2)
        terminal.write(CUP_1_1)

        for (index, line) in enumerate(lines):
            (styled, line_plus) = self.style_line(index, line=line, spans=spans)
            if len(line_plus) < columns:
                terminal.write(styled + "\r\n")
            else:
                terminal.write(styled)  # depend on automagic "\r\n" after Last Column

        # Show status, inside the last Row
        # but don't write over the Lower Right Char  # TODO: test vs xterm autoscroll

        str_status = "" if (status is None) else str(status)
        status_columns = columns - 1
        status_line = str_status[:status_columns].ljust(status_columns)
        terminal.write(status_line)

        # Place the cursor

        cursor_left_column = left_column if (row < scrolling_rows) else 0

        y = 1 + row
        x = 1 + cursor_left_column + column
        terminal.write(CUP_Y_X.format(y, x))

    def write_bell(self):
        """Ring the Terminal bell"""

        self.terminal.write("\a")

    def spot_left_column(self):
        """Find the leftmost Column occupied by the Chars of the Scrolling Lines"""

        formatted = self.format_as_line_number(row=1)
        left_column = len(formatted)

        return left_column

    def format_as_line_number(self, row):
        """Format a Row Index on Screen as a Line Number of File"""

        if not self.painting_line_number:

            return ""

        str_last_line_number = "{:3} ".format(self.last_line_number)
        last_width = len(str_last_line_number)

        line_number = self.top_line_number + row
        formatted = "{:3} ".format(line_number).rjust(last_width)

        return formatted

    def style_line(self, row, line, spans):
        """Inject SGR_7 and SGR to style the Chars of a Row"""

        # Work only inside this Row

        (row_spans, line_plus) = self.spread_spans(row, line=line, spans=spans)

        # Add one Empty Span beyond the end, to place all Chars between Spans

        beyond = len(line_plus)
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

                fragment = line_plus[visited : span.column]

                styled += SGR if lit else ""
                styled += fragment

                lit = False
                visited = span.column

            # Write the Chars of this Span, as SGR_7

            if span.column < span.beyond:

                fragment = line_plus[span.column : span.beyond]

                styled += "" if lit else SGR_7
                styled += fragment

                lit = True
                visited = span.beyond

        # Add a last SGR to close the last SGR_7, if need be

        styled += SGR if lit else ""

        return (styled, line_plus)

    def spread_spans(self, row, line, spans):
        """Spread each Empty Span to cover one more Column beyond it"""

        columns = self.columns
        left_column = self.spot_left_column()

        assert len(line) <= columns, (len(line), columns)

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

        # Add one Space to grow the Line, when Span runs past End of Line

        len_line = len(line) if (not row_spans) else max(_.beyond for _ in row_spans)

        assert len_line <= columns, (len_line, columns)

        line_plus = line
        if len_line > len(line):

            line_plus = line + " "
            assert len_line == len(line_plus), (row, len_line, len(line_plus))

        # Succeed

        return (row_spans, line_plus)


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

        blank_line = columns * " "
        bottom_row = rows - 1

        # Write the rows

        terminal.write(CUP_1_1)

        assert len(held_lines) == rows, (len(held_lines), rows)
        for (row, held_line) in enumerate(held_lines):
            flushed_line = flushed_lines[row]

            if flushed_line != held_line:  # write Rows who changed since last Flush
                if row < bottom_row:

                    self._terminal_write_cup(row, column=0)
                    terminal.write(blank_line)

                    self._terminal_write_cup(row, column=0)
                    terminal.write(held_line.rstrip())

                else:

                    self._terminal_write_cup(row, column=0)
                    terminal.write(blank_line[:-1])

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

        columns = self.columns
        held_lines = self.held_lines
        row = self.row
        rows = self.rows

        # Forward the Chars unchanged

        held_line = held_lines[row]
        assert held_line is None, held_line

        held_lines[row] = chars

        # Move the Shadow Cursor

        escapist = TerminalEscapist(rows, columns=columns)
        if (self.row, self.column) != (None, None):
            escapist.write(CUP_Y_X.format(1 + self.row, 1 + self.column))
        # FIXME: write all writes to one TerminalEscapist

        escapist.write(chars)
        (self.row, self.column) = escapist.pin

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

        # Interpret the CUP_Y_X or CUP_1_1 Escape Sequence

        escapist = TerminalEscapist(rows, columns=columns)
        escapist.write(chars)
        (to_row, to_column) = escapist.pin

        # Move the Shadow Cursor

        self.row = to_row
        self.column = to_column

    # TODO: Add API to write Scroll CSI in place of rewriting Screen to Scroll
    # TODO: Reduce writes to Chars needed, smaller than whole Lines needed


class TerminalEscapist:
    """Interpret writes of Chars including C0_CONTROL Chars, like a Terminal does"""

    ALT_TERMINAL_WRITE_REGEX = r"".join(
        [
            r"(\x1B\[",  # Control Sequence Introducer (CSI)
            r"(([0-9?]+)(;([0-9?]+))?)?",  # 0, 1, or 2 Decimal Int or Question Args
            r"([A-Z_a-z]))",  # one Ascii Letter or Skid mark
            r"|",
            r"(\x1B.)",  # else one escaped Char
            r"|",
            r"(\r\n|[\x00-\x1F\x7F])",  # else one or a few C0_CONTROL Chars
            r"|",
            r"([^\x00-\x1F\x7F]+)",  # else literal Chars
        ]
    )

    assert ALT_TERMINAL_WRITE_REGEX == TERMINAL_WRITE_REGEX

    def __init__(self, rows, columns):

        self.rows = rows
        self.columns = columns

        self.row = None
        self.column = None

    @property
    def pin(self):
        """Say where the Cursor is"""

        pin_ = TerminalPin(self.row, column=self.column)

        return pin_

    def write(self, chars):
        """Write a mix of C0_CONTROL Chars and other Chars"""

        row = self.row  # mutable
        column = self.column  # mutable

        for match in re.finditer(TERMINAL_WRITE_REGEX, string=chars):
            (row, column) = self.find_cursor_after(match)

        self.row = row
        self.column = column

    def find_cursor_after(self, match):
        """Say where writing one Match of TERMINAL_WRITE_REGEX moves the Cursor"""

        rows = self.rows
        columns = self.columns

        # Default to keep the Cursor unmoved

        row = self.row  # mutable
        column = self.column  # mutable

        # Name Groups of the Match

        m = match
        order = m.string[m.start() : m.end()]

        literals = m.group(9)
        controls = m.group(8)
        escape = m.group(7)
        csi = m.group(1)

        groups = (literals, controls, escape, csi)
        assert sum(bool(_) for _ in groups) == 1, (order, groups)

        a = m.group(6)
        x = m.group(5)
        y = m.group(3)

        assert bool(a or x or y) == bool(csi), (order, groups)

        # Write Literals over Columns, slipping the Cursor right and down

        if literals:
            column += len(literals)
            row += column // columns  # 'row == rows' after writing last Column
            column = column % columns

        # Interpret C0_CONTROL Chars

        elif controls == "\a":
            pass
        elif controls == "\r\n":
            row += 1
            column = 0

        # Interpret CSI Escape Sequences

        elif csi == ED_2:
            row = None
            column = None
        elif csi == CUP_1_1:
            row = 0
            column = 0
        elif a == CUP_Y_X[-1]:
            row = int(y) - 1  # raise TypeError/ ValueError for bad/missing Arg
            column = int(x) - 1  # again, may raise TypeError/ ValueError

        elif csi == SGR_7:
            pass
        elif csi == SGR:
            pass

        # Reject meaningless Orders

        else:
            raise NotImplementedError(repr(order))

        assert 0 <= row < rows, (order,)
        assert 0 <= column < columns, (order,)

        # Succeed

        return (row, column)


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

        # Block to fetch one more Byte
        # (or fetch no Bytes at end of input when Stdin is not Tty)

        stdin = os.read(self.terminal.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while Line not closed
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

    rep = rep.replace("Esc [ A", "Up")  # ↑ \u2191 Upwards Arrow
    rep = rep.replace("Esc [ B", "Down")  # ↓ \u2193 Downwards Arrow
    rep = rep.replace("Esc [ C", "Right")  # → \u2192 Rightwards Arrow
    rep = rep.replace("Esc [ D", "Left")  # ← \u2190 Leftwards Arrows

    rep = rep.strip()

    return rep  # such as '⌃L' at FF, ⌃L, 12, '\f'


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

    # Find the Doc of caller, even when not Main, and when:  __main__ is None

    f = inspect.currentframe()
    module = inspect.getmodule(f.f_back)
    module_doc = module.__doc__

    # Pick the ArgParse Prog, Description, & Epilog out of the Main Arg Doc

    prog = module_doc.strip().splitlines()[0].split()[1]

    headlines = list(
        _ for _ in module_doc.strip().splitlines() if _ and not _.startswith(" ")
    )
    description = headlines[1]

    epilog_at = module_doc.index(epi)
    epilog = module_doc[epilog_at:]

    # Start forming the ArgParse Parser

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
    """Exit nonzero, unless __main__.__doc__ equals 'parser.format_help()'"""

    # Find the Doc and File of caller, even when not Main, and when:  __main__ is None

    f = inspect.currentframe()
    module = inspect.getmodule(f.f_back)

    module_doc = module.__doc__
    module_file = f.f_back.f_code.co_filename  # more available than 'module.__file__'

    # Fetch the two docs

    with_columns = os.getenv("COLUMNS")
    os.environ["COLUMNS"] = str(89)  # Black promotes 89 columns per line
    try:
        parser_doc = parser_format_help(parser)
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

    if diff_lines:  # TODO: ugly contingent '.rstrip()'

        lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
        stderr_print("\n".join(lines))

        sys.exit(1)  # trust caller to log SystemExit exceptions well


# deffed in many files  # missing from docs.python.org
def module_file_hash():
    """Hash the Bytes of this SourceFile"""

    abs_module_file = os.path.abspath(module_file_path())
    with open(abs_module_file, "rb") as reading:
        file_bytes = reading.read()

    hasher = hashlib.md5()
    hasher.update(file_bytes)
    hash_bytes = hasher.digest()

    str_hash = hash_bytes.hex()
    str_hash = str_hash.upper()  # such as 32 nybbles 'D41D8CD98F00B204E9800998ECF8427E'

    return str_hash


# deffed in many files  # missing from docs.python.org
def module_file_path():
    """Find the Doc of caller, even when not Main, and when:  __main__ is None"""

    f = inspect.currentframe()
    module_file = f.f_back.f_code.co_filename  # more available than 'module.__file__'

    return module_file


# deffed in many files  # missing from docs.python.org
def module_file_version_zero():
    """Pick a conveniently small, reasonably distinct, decimal Version Number"""

    str_hash = module_file_hash()

    major = 0
    minor = int(str_hash[0], 0x10)  # 0..15
    micro = int(str_hash[1:][:2], 0x10)  # 0..255

    version = "{}.{}.{}".format(major, minor, micro)

    return version


# deffed in many files  # missing from docs.python.org
def parser_format_help(parser):
    """Patch around Python ArgParse misreading declarations of "+" optional args"""

    doc = parser.format_help()

    doc = doc.replace(" [--plus PLUS]", " [+PLUS]")
    doc = doc.replace(
        "  --plus PLUS  ",
        "  +PLUS        ",
    )

    return doc


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


# deffed in many files  # missing from Python till Oct/2019 Python 3.8
def shlex_join(argv):
    """Undo shlex.split"""

    # Trust the library, if available

    if hasattr(shlex, "join"):
        shline = shlex.join(argv)
        return shline

    # Emulate the library roughly, because often good enough

    shline = " ".join(shlex_quote(_) for _ in argv)
    return shline


# deffed in many files  # missing from Python till Oct/2019 Python 3.8
def shlex_quote(arg):
    """Mark up with quote marks and backslashes , but only as needed"""

    # Trust the library, if available

    if hasattr(shlex, "quote"):
        quoted = shlex.quote(arg)
        return quoted

    # Emulate the library roughly, because often good enough

    mostly_harmless = set(
        "%+,-./"  # not: !"#$&'()*
        + string.digits
        + ":=@"  # not ;<>?
        + string.ascii_uppercase
        + "_"  # not [\]^
        + string.ascii_lowercase
        + ""  # not {|}~
    )

    likely_harmful = set(arg) - set(mostly_harmless)
    if likely_harmful:
        quoted = repr(arg)  # as if the Py rules agree with Sh rules
        return quoted

    return arg


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):  # later Python 3 accepts ', **kwargs' here
    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


#
# Track ideas of future work
#


# TODO: search the Sourcelines above here a la :g/FIXME
# TODO: search the Sourcelines above here a la :g/TODO\|FIXME

# -- bugs --


# FIXME: Vim :g/ :g? affirms or flips direction, doesn't force ahead/behind
# FIXME: somehow need two ⌃L after each Terminal Window Resize?  \ n \ n doesn't work?
# FIXME: ( workaround is quit and relaunch, or press enough pairs of ⌃L )


# -- future inventions --


# TODO: QR to draw with a Logo Turtle till QR,
# TODO: infinite Spaces per Row, rstrip at exit, moving relative not absolute
# TODO: 1234567890 Up Down Left Right, initially headed Up with |
# TODO: | - =| =- to draw a rectangle, |=-=|=- to draw a square
# TODO: [ ] for macro repetition
# TODO: escape to complete unabbreviated Logo:  Repeat 4 [ Forward 10 Right 90 ]
# TODO: escape to complete abbreviated Logo:  Rep 4 [ Fd 10 Rt 90 ]
# TODO: contrast with default Emacs Picture Modes |-/\+ ...


# TODO: stop passing through Controls from the File
# TODO: accept b"\t" as a form of b" "
# TODO: solve /⌃V⌃IReturn
# TODO: solve:  echo -n abc |vi -
# TODO: show the first ~ past the end differently when No End for Last Line
# TODO: revive the last Match of r"$" out there


# TODO: radically simplified undo:  3u to rollback 3 keystrokes
# TODO: radically simplified undo:  u to explain radically simplified undo


# -- future improvements --

# TODO: record and replay tests of:  cat bin/vi.py |vi.py - bin/vi.py

# TODO: do echo the Search Key, and better than Vim does
# TODO:   Vim echoes / ? keys till you press Return
# TODO:   Vim echoes / ? keys if you come back and / Up or ? Up
# TODO:   Vim echoes * keys only when found ahead, # keys only when found behind
# TODO:   Vim never echoes n N :g/ keys
# TODO:   Vi Py today discloses :g/ Search Keys when less than 1 Screen of Matches

# TODO: name errors for undefined keys inside Ex of / ? etc

# TODO: :0 ... :9 to work as 0..9 but then G after Prefix
# TODO: accept more chords and DEL and ⌃U after : till \r
# TODO: accept :123\r, but suggest 123G etc
# TODO: accept :noh\r and :set ignorecase and so on, but suggest \Esc \i etc
_ = """
ex tests:
  ls |bin/vi.py +3 -  # start on chosen line
  ls |bin/vi.py +/Makefile -  # start on found line
"""


# -- future features --

# TODO: ⌃I ⌃O walk the Jump List of ' ` G / ? n N % ( ) [[ ]] { } L M H :s :tag :n etc
# TODO: despite Doc, to match Vim, include in the Jump List the * # forms of / ?

# TODO: mm '' `` pins
# TODO: qqq @q  => record input, replay input

# TODO: save/load to/from local Os CopyPaste Buffer, like via Mac pbpaste/pbcopy

# TODO: toggled :set wrap, :set nowrap
# TODO: ⌃D ⌃U scrolling
# TODO: ⌃V o  => rectangular: opposite


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
