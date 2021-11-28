#!/usr/bin/env python3

r"""
usage: vi.py [-h] [+PLUS] [--pwnme [BRANCH]] [--version] [FILE ...]

read files, accept zero edits, write files

positional arguments:
  FILE              a file to edit (default: '/dev/stdin')

optional arguments:
  -h, --help        show this help message and exit
  +PLUS             next Ex command to run, just after loading first File
  --pwnme [BRANCH]  update and run this Code, don't just run it
  --version         print a hash of this Code (its Md5Sum)

quirks:
  works as pipe filter, pipe source, or pipe drain, like the pipe drain:  ls |vi -

keyboard cheat sheet:
  ZQ ZZ ⌃Zfg  :q!⌃M :n!⌃M :w!⌃M :wq!⌃M  => how to quit Vi Py
  ⌃C Up Down Right Left Space Delete Return  => natural enough
  0 ^ $ fx tx Fx Tx ; , | h l  => leap to column
  b e w B E W { }  => leap across small word, large word, paragraph
  G 1G H L M - + _ ⌃J ⌃N ⌃P j k  => leap to row, leap to line
  1234567890 Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y zb zt zz 99zz  => scroll rows
  ⌃L 999⌃L ⌃G  => clear lag, inject lag, measure lag and show version
  \n \i \F Esc ⌃G  => toggle line numbers, search case/ regex, show hits
  /... Delete ⌃U ⌃C Return  ?...   * # £ n N  => start search, next, previous
  :g/... Delete ⌃U ⌃C Return :g?...  => give search key and print lines found
  a i rx o A I O R ⌃O Esc ⌃C  => enter/ suspend-resume/ exit insert/ replace

keyboard easter eggs:
  9^ G⌃F⌃F 1G⌃B G⌃F⌃E 1G⌃Y ; , n N 2G9k \n99zz
  Esc ⌃C 123Esc 123⌃C zZZQ /⌃G⌃CZQ 3ZQ f⌃C w*Esc w*⌃C w*123456n⌃C w*:g/⌃M⌃C g/⌃Z
  Qvi⌃My REsc R⌃Zfg \Fw*/Up \F/$Return 9⌃G :vi⌃M :n

pipe tests of ZQ vs ZZ:
  ls |bin/vi.py -
  cat bin/vi.py |bin/vi.py
  cat bin/vi.py |bin/vi.py |grep import

how to get Vi Py:
  R=pelavarre/pybashish/master/bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R
  python3 vi?py vi?py
  /egg

how to get Vi Py again:
  python3 vi?py --pwnme
"""

# Vi Py also takes the \u0008 ⌃H BS \b chord in place of the \u007F ⌃? DEL chord


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
import time
import traceback
import tty

subprocess_run = subprocess.run  # evade Linters who freak over "shell=True"


# Name some Terminal Output magic

ESC = "\x1B"  # Esc
CSI = ESC + "["  # Control Sequence Introducer (CSI)

ED_2 = "\x1B[2J"  # Erase in Display (ED)  # 2 = Whole Screen
CUP_Y_X = "\x1B[{};{}H"  # Cursor Position (CUP)
CUP_1_1 = "\x1B[H"  # Cursor Position (CUP)  # (1, 1) = Upper Left

DECSCUSR_N = "\x1B[{} q"  # Set Cursor Style
DECSCUSR = "\x1B[ q"  # Clear Cursor Style (but doc'ed poorly)

SGR_N = "\x1B[{}m"  # Select Graphic Rendition
SGR = "\x1B[m"  # SGR > Reset, Normal, All Attributes Off

DECSC = ESC + "7"  # DEC Save Cursor
DECRC = ESC + "8"  # DEC Restore Cursor

_XTERM_ALT_ = "\x1B[?1049h"  # show Alt Screen
_XTERM_MAIN_ = "\x1B[?1049l"  # show Main Screen

SMCUP = DECSC + _XTERM_ALT_  # Set-Mode Cursor-Positioning
RMCUP = ED_2 + _XTERM_MAIN_ + DECRC  # Reset-Mode Cursor-Positioning


# Configure some Terminal Output magic

_CURSES_INITSCR_ = SMCUP + ED_2 + CUP_1_1
_CURSES_ENDWIN_ = RMCUP

_EOL_ = "\n"  # TODO: sometimes "\r\n" Dos, sometimes "\r" Classic Mac

_LIT_OPEN_ = SGR_N.format(7)  # Reverse Video, Invert, overriden by default Cursor
_LIT_CLOSE_ = SGR

_VIEW_CURSOR_STYLE_ = DECSCUSR_N.format(2)  # Steady Block  # Mac Terminal default
_REPLACE_CURSOR_STYLE_ = DECSCUSR_N.format(4)  # Steady Underline
_INSERT_CURSOR_STYLE_ = DECSCUSR_N.format(6)  # Steady Bar


# Parse some Terminal Output magic


class TerminalOrder(argparse.Namespace):
    """Split Terminal Output into magic and literals"""

    TERMINAL_WRITE_REGEX = r"".join(
        [
            r"(\x1B\[",  # Control Sequence Introducer (CSI)
            r"(([0-9?]+)(;([0-9?]+))?)?",  # 0, 1, or 2 Decimal Int or Question Args
            r"([^A-Z_a-z]*[A-Z_a-z]))",  # any Chars, then Ascii Letter
            r"|",
            r"(\x1B.)",  # else one escaped Char
            r"|",
            r"(\r\n|[\x00-\x1F\x7F])",  # else one or a few C0_CONTROL Chars
            r"|",
            r"([^\x00-\x1F\x7F]+)",  # else literal Chars
        ]
    )

    def __init__(self, match):
        """Parse one whole Terminal Order, found as Re Match of TERMINAL_WRITE_REGEX"""

        self.match = match

        # Name Groups of the Match

        m = match
        self.chars = m.string[m.start() : m.end()]

        assert len(m.groups()) == 9

        self.literals = m.group(9)
        self.controls = m.group(8)
        self.escape_plus = m.group(7)
        self.csi_plus = m.group(1)

        groups = (self.literals, self.controls, self.escape_plus, self.csi_plus)
        assert sum(bool(_) for _ in groups) == 1, (self.chars, groups)
        assert self.chars in groups, (self.chars, groups)

        self.a = m.group(6)
        self.x = m.group(5)
        self.y = m.group(3)

        if not self.csi_plus:
            assert self.a is self.x is self.y is None, (self.chars, groups)
        else:
            assert self.a, (self.chars, groups)

        # Raise ValueError if CSI Order carries an X or Y that is not Decimal Int

        rep = repr(self.chars)

        self.int_x = None
        if self.x is not None:
            try:
                self.int_x = int(self.x)
            except ValueError:

                raise ValueError(rep)  # such as _XTERM_ALT_ or _XTERM_MAIN_

        self.int_y = None
        if self.y is not None:
            try:
                self.int_y = int(self.y)
            except ValueError:
                assert False, (self.chars, groups)

        # Raise ValueError if CSI Order started and not ended

        if self.escape_plus and self.escape_plus.endswith(CSI):  # "\x1B["
            assert self.escape_plus == CSI  # as per TERMINAL_WRITE_REGEX

            raise ValueError(rep)  # incomplete CSI TerminalOrder

        if self.controls and self.controls.endswith(ESC):  # "\x1B"

            raise ValueError(rep)  # incomplete CSI TerminalOrder


class TerminalWriter(argparse.Namespace):
    """Split a mix of C0_CONTROL and other Chars into complete TerminalOrder's"""

    def __init__(self, chars):

        regex = TerminalOrder.TERMINAL_WRITE_REGEX

        orders = list()
        for match in re.finditer(regex, string=chars):
            order = TerminalOrder(match)

            orders.append(order)

        self.orders = orders


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
        do_args_pwnme(branch=args.pwnme)
        assert False  # unreached

    if args.version:
        do_args_version()
        if not (args.files or args.plusses):

            sys.exit()

    # Visit each File

    vi = TerminalSkinVi(files=args.files, plusses=args.plusses)

    returncode = None
    try:

        vi.run_vi_terminal()  # like till SystemExit
        assert False  # unreached

    except OSError as exc:

        stderr_print("{}: {}".format(type(exc).__name__, exc))

        sys.exit(1)

    except SystemExit as exc:

        returncode = exc.code
        if vi.vi_traceback:
            stderr_print(vi.vi_traceback)

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
        "--plus",  # Vim "+"
        metavar="PLUS",
        dest="plusses",
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


def do_args_version():
    """Print a hash of this Code (its Md5Sum) and exit"""

    version = module_file_version_zero()
    str_hash = module_file_hash()
    str_short_hash = str_hash[:4]  # conveniently fewer nybbles  # good enough?

    print("Vi Py {} hash {} ({})".format(version, str_short_hash, str_hash))


def do_args_pwnme(branch):
    """Download fresh Code to run in place of this stale Code"""

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

    callpath = to_relpath
    callpath = callpath if (os.sep in callpath) else os.path.join(os.curdir, callpath)

    # Compose a Bash Script
    # to back up Self, replace Self, mark Self as executable, call new Self

    when = main.since
    stamp = when.strftime("%m%djqd%H%M%S")
    mv_shline = "mv -i {relpath} {relpath}~{stamp}~".format(
        relpath=from_relpath, stamp=stamp
    )

    curl_shline = "curl -sS --location {link} >{relpath}".format(
        link=link, relpath=to_relpath
    )

    chmod_shline = "chmod ugo+x {relpath}".format(relpath=to_relpath)

    vi_py_shline_0 = shlex_join([callpath, "--version"])

    shlines = [mv_shline, curl_shline, chmod_shline, vi_py_shline_0]

    # Compose one more Bash Line to call new Self with Args, if more Args were given

    argv = list()
    argv.append(callpath)
    for (index, arg) in enumerate(sys.argv):
        if index:
            if arg.startswith("--pwnme"):
                pass
            elif sys.argv[index - 1] == "--pwnme":
                pass
            else:
                argv.append(arg)

    if argv[1:]:
        vi_py_shline_1 = shlex_join(argv)
        shlines.append(vi_py_shline_1)

    # Run the Bash Script, and exit with its process exit status returncode

    do_args_version()  # print the Version From, before download & run of the new Self

    for shline in shlines:
        stderr_print("+ {}".format(shline))
        try:
            _ = subprocess_run(shline, shell=True, check=True)
        except subprocess.CalledProcessError as exc:
            stderr_print("+ exit {}".format(exc.returncode))

            sys.exit(exc.returncode)

    sys.exit()  # exit old Self, after calling new Self once or twice


#
# Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim
#


VI_BLANK_SET = set(" \t")
VI_SYMBOLIC_SET = set(string.ascii_letters + string.digits + "_")  # r"[A-Za-z0-9_]"


class TerminalFile(argparse.Namespace):
    """Hold a copy of the Bytes of a File awhile"""

    def __init__(self, path=None):
        """Fetch the File"""

        self.path = None  # Path to File
        self.iobytes = b""  # Bytes of File, else None
        self.iochars = ""  # Chars of File, else None
        self.ended_lines = list()  # Ended Lines of File
        self.touches = 0

        if path is not None:

            self.path = os.path.abspath(path)

            with open(path, "rb") as reading:
                self.iobytes = reading.read()

            self.iochars = self.iobytes.decode(errors="surrogateescape")

            self.ended_lines = self.iochars.splitlines(keepends=True)

        write_path = "/dev/stdout" if (path in (None, "/dev/stdin")) else path
        write_path = os.path.abspath(write_path)

        self.write_path = write_path

    def decode(self):
        """Re-decode the File after changes"""

        if not self.ended_lines:

            return ""

        self.iochars = "".join(self.ended_lines)
        self.iobytes = self.iochars.encode(errors="surrogateescape")

        return self.iochars

        # TODO: stop re-decode'ing while 'self.ended_lines' unchanged

    def encode(self):
        """Re-encode the File after changes"""

        if not self.ended_lines:

            return b""

        self.iochars = "".join(self.ended_lines)
        self.iobytes = self.iochars.encode(errors="surrogateescape")

        return self.iobytes

        # TODO: stop re-encode'ing while 'self.ended_lines' unchanged

    def flush(self):
        """Store the File"""

        write_path = self.write_path

        iobytes = self.encode()
        with open(write_path, "wb") as writing:
            writing.write(iobytes)

        self.touches = 0


class TerminalPin(collections.namedtuple("TerminalPin", "row, column".split(", "))):
    """Pair up a Row with a Column"""

    # TODO:  class TerminalPinVi - to slip and step in the way of Vi


class TerminalPinPlus(
    collections.namedtuple("TerminalPinPlus", "row, column, obj".split(", "))
):
    """Add one more Thing to pairing up a Row with a Column"""


class TerminalSkinVi:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim"""

    def __init__(self, files, plusses):

        self.vi_traceback = None  # capture Python Tracebacks

        self.plusses = plusses  # Ex commands to run after

        self.files = files  # files to edit
        self.files_index = None

        self.held_file = None

        self.editor = None

        self.slip_choice = None  # find Char in Row
        self.slip_after = None  # slip off by one Column after finding Char
        self.slip_redo = None  # find later Char
        self.slip_undo = None  # find earlier Char

        self.seeking_column = None  # leap to Column in next Row, True to leap beyond
        self.seeking_more = None  # remembering the Seeking Column into next Nudge

    #
    # Visit each of the Files
    #

    def do_might_next_vi_file(self):  # Vim :n\r
        """Halt if touches Not flushed, else visit the next (or first) File"""

        if self.might_keep_changes():

            return True

        self.do_next_vi_file()

    def do_next_vi_file(self):  # Vim :n!\r
        """Visit the next (or first) File"""

        editor = self.editor
        files_index = self.files_index
        files = self.files

        # Choose next File, else quit after last File

        if files_index is None:
            next_files_index = 0
            file_path = None if (not files) else files[next_files_index]
        elif files_index < (len(files) - 1):
            next_files_index = files_index + 1
            file_path = files[next_files_index]
        else:
            self.do_quit_vi()  # Vim doesn't calmly quit, Vim chokes over no next file
            assert False  # unreached

        self.files_index = next_files_index

        # Map more abstract File Path Aliases to more concrete File Paths

        path = file_path
        if file_path == "-":
            path = "/dev/stdin"
        elif file_path is None:
            if not sys.stdin.isatty():
                path = "/dev/stdin"

        # Visit the chosen File

        held_file = TerminalFile(path)

        editor._reinit_with_held_file_(held_file)

        self.held_file = held_file

    #
    # Layer thinly over TerminalEditor
    #

    def run_vi_terminal(self):
        """Enter Terminal Driver, then run Keyboard, then exit Terminal Driver"""

        plusses = self.plusses  # Vim starts with lines of '~/.vimrc'

        # Choose how to start up

        chords = b""
        chords += b":n\r"  # autoload the first file => do_next_vi_file

        if plusses:
            for plus in plusses:
                chars = ":" + plus + "\r"
                chords += chars.encode()

        chords += b":vi\r"  # go with XTerm Alt Screen & Keyboard  => do_resume_editor
        chords += b"\x03"  # welcome warmly with ETX, ⌃C, 3  => do_help_quit_vi

        # Form stack

        editor = TerminalEditor(chords=chords)
        self.editor = editor

        keyboard = TerminalKeyboardVi(vi=self)

        # Feed Keyboard into Screen, like till SystemExit

        try:
            editor.run_terminal_with_keyboard(keyboard)  # TerminalKeyboardVi
            assert False  # unreached
        finally:
            self.vi_traceback = editor.skin.traceback  # /⌃G⌃CZQ Egg

    def get_vi_arg0_chars(self):
        """Get the Chars of the Chords pressed to call this Func"""

        return self.editor.get_arg0_chars()

    def get_vi_arg1_int(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        return self.editor.get_arg1_int(default=default)

    def get_vi_arg2_chords(self):
        """Get the Bytes of the Suffix supplied after the Input Chords"""

        return self.editor.get_arg2_chords()

    def vi_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        self.editor.editor_print(*args)  # 'def vi_print' calling

    #
    # Layer thinly under the rest of TerminalSkinVi
    #

    def check_vi_index(self, truthy, **kwargs):
        """Fail fast, else proceed"""

        if not truthy:

            raise IndexError()

    def keep_up_vi_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        assert self.seeking_column is not None
        self.seeking_more = True

    #
    # Define Chords for pausing TerminalSkinVi
    #

    def do_say_more(self):  # Vim ⌃G
        """Reply once with more verbose details"""

        editor = self.editor
        held_file = self.held_file

        showing_lag = editor.showing_lag

        #

        if editor.finding_line:
            editor.finding_highlights = True
            editor.reply_with_finding()

        str_lag = None
        if showing_lag is not None:
            str_lag = "{}s lag".format(showing_lag)

        #

        joins = list()

        joins.append(repr(os.path.basename(self.held_file.path)))

        if str_lag:
            joins.append(str_lag)

        if held_file.touches:
            joins.append("{} bytes touched".format(held_file.touches))

        more_status = "  ".join(joins)
        editor.editor_print(more_status)  # such as "'bin/vi.py'  less lag"

        # Vim ⌃G doesn't turn Search highlights back on

        # TODO: 1⌃G to show Dir of File Path

    def do_vi_c0_control_esc(self):  # Vim Esc
        """Cancel Digits Prefix, else suggest ZZ to quit Vi Py"""

        editor = self.editor

        version = module_file_version_zero()

        count = self.get_vi_arg1_int(default=None)
        if count is not None:
            self.vi_print("Escaped Repeat Count")  # 123 Esc Egg, etc
        elif editor.finding_highlights:
            self.vi_print("Escaped Search")  # *Esc Egg
            editor.finding_highlights = None  # Vim leaves highlights up
        else:
            self.vi_print("Press ZZ to save changes and quit Vi Py", version)  # Esc Egg

        # Vim rings a Bell for each extra Esc

    def do_continue_vi(self):  # Vim Q v i Return  # Vim b"Qvi\r"  # not Ex mode
        """Accept Q v i Return, without ringing the Terminal bell"""

        editor = self.editor

        self.vi_ask("Would you like to play a game? (y/n)")

        try:
            chord = editor.take_editor_chord()
        except KeyboardInterrupt:
            chord = b"\x03"  # ETX, ⌃C, 3

        editor.skin.nudge.suffix = chord

        if chord in (b"y", b"Y"):
            self.vi_print("Ok, now try to quit Vi Py")  # Qvi⌃My Egg
        else:
            self.vi_print("Ok")  # Qvi⌃Mn Egg

    def vi_ask(self, *args):
        """Ask a question, but don't wait for its answer"""

        editor = self.editor

        message = " ".join(str(_) for _ in args)
        message += " "  # place the cursor after a Space after the Message
        self.vi_print(message)  # 'def vi_ask' calling

        vi_reply = self.format_vi_status(self.editor.skin.reply)
        ex = TerminalSkinEx(editor, vi_reply=vi_reply)
        ex.flush_ex_status()

    def do_vi_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        editor = self.editor

        editor.do_sig_tstp()

        if self.seeking_column is not None:
            self.keep_up_vi_column_seek()

    #
    # Define Chords for entering, pausing, and exiting TerminalSkinVi
    #

    def do_help_quit_vi(self):  # Vim ⌃C  # Vi Py Init
        """Suggest ZQ to quit Vi Py"""

        editor = self.editor
        assert editor.skin.arg1 is None  # ⌃C cancels before 'call_chords_func'

        version = module_file_version_zero()

        if editor.finding_highlights:
            self.vi_print("Cancelled Search")  # *⌃C Egg
            editor.finding_highlights = None  # Vim leaves highlights up
        else:
            self.vi_print("Press ZQ to save changes and quit Vi Py", version)  # ⌃C Egg

        # Vim rings a Bell for each extra ⌃C

    def do_might_flush_quit_vi(self):  # Vim :wq\r
        """Write the File, but halt if more Files"""

        if self.do_might_flush_vi():

            return True

        if self.do_might_quit_vi():

            return True

        assert False  # unreached

        # Vim :wq :wq quits despite more Files named than fetched
        # Vi Py :wq doesn't quit while more Files named than fetched, vs its :wq! does

    def do_flush_quit_vi(self):  # Vim ZZ  # Vim :wq!\r
        """Write the File and quit Vi"""

        editor = self.editor

        editor.skin.traceback = None

        self.do_flush_vi()
        self.do_quit_vi()

        # Vim :wq! quits when more Files named than fetched, Vim ZZ no, Vim ZZ ZZ yes
        # Vi Py :wq! and ZZ quit despite more Files named than fetched

    def do_might_flush_vi(self):  # Vim :w\r
        """Write the File but do not quit Vi"""

        self.do_flush_vi()

    def do_flush_vi(self):  # Vim :w!\r
        """Write the File"""

        editor = self.editor
        held_file = self.held_file

        painter = editor.painter

        if held_file.write_path == held_file.path:
            held_file.flush()
        else:
            exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
            painter.__exit__(*exc_info)
            try:
                held_file.flush()
                time.sleep(0.001)  # TODO: wout this, fails 1 of 10:  ls |vi.py |cat -n
            finally:
                painter.__enter__()

            # TODO: shuffle this code down into TerminalEditor

        self.vi_print(
            "wrote {} lines as {} bytes".format(
                len(held_file.ended_lines), len(held_file.iobytes)
            )
        )

        # TODO: Vim :w! vs Vim :w

    def do_might_quit_vi(self):  # Vim :q\r
        """Halt if Touches not Flushed or More Files, else quit Vi"""

        if self.might_keep_changes():

            return True

        if self.might_keep_files():

            return True

        self.do_quit_vi()
        assert False  # unreached

        # Vim :q :q quits despite more Files named than fetched
        # Vi Py :q doesn't quit while more Files named than fetched, vs its :q! does

    def might_keep_changes(self):

        """Return None if no Touches held, else say how to bypass and return True"""
        held_file = self.held_file

        alt = self.get_vi_arg0_chars().rstrip() + "!"  # FIXME: factor this out
        assert alt in (":n!", ":q!", ":wq!"), repr(alt)
        alt = alt.replace(":q!", "ZQ")
        alt = alt.replace(":wq!", "ZZ")

        if held_file:
            touches = held_file.touches
            if touches:
                self.vi_print("{} bytes touched - Do you mean {}".format(touches, alt))

                return True

    def might_keep_files(self):
        """Return None if no Files held, else say how to bypass and return True"""

        files = self.files
        files_index = self.files_index

        alt = self.get_vi_arg0_chars().rstrip() + "!"  # FIXME: factor this out
        assert alt in (":q!", ":wq!")
        alt = alt.replace(":q!", "ZQ")
        alt = alt.replace(":wq!", "ZZ")

        more_files = files[files_index:][1:]
        if more_files:
            self.vi_print("{} more files - Do you mean {}".format(len(more_files), alt))

            return True

    def do_quit_vi(self):  # Vim ZQ  # Vim :q!\r
        """Lose last changes and quit"""

        returncode = self.get_vi_arg1_int(default=None)

        sys.exit(returncode)  # Mac & Linux take only 'returncode & 0xFF'

    #
    # Define Chords to take a Word of this Line as the Search Key, and look for it
    #

    def do_find_ahead_vi_this(self):  # Vim *
        """Take a Search Key from this Line, and then look ahead for it"""

        editor = self.editor
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if self.slip_find_fetch_vi_this(slip=+1) is None:
                self.vi_print("Press * and # only when Not on a blank line")  # * Egg

                return

        # Try the Search

        if editor.find_ahead_and_reply():

            editor.continue_do_loop()

        # Vim echoes the * Search Key as Status, unless not found ahead on same screen
        # Vi Py echoes the * Search Key as Status, at /Up, at :g/Up, etc

    def do_find_behind_vi_this(self):  # Vim #  # Vim £
        """Take a Search Key from this Line, and then look behind for it"""

        editor = self.editor
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if self.slip_find_fetch_vi_this(slip=-1) is None:
                self.vi_print("Press # and £ and * only when Not on a blank line")
                # £, # Eggs

                return

        # Try the Search

        if editor.find_behind_and_reply():

            editor.continue_do_loop()

        # Vim echoes the # Search Key as Status, unless not found behind on same screen
        # Vi Py echoes the # Search Key as Status, at ?Up, at :g?Up, etc

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

        def in_vi_symbolic(ch):

            return ch in VI_SYMBOLIC_SET

        def not_in_vi_blank(ch):

            return ch not in VI_BLANK_SET

        # Take a Symbolic word, else a Non-Blank word

        behind = column
        for in_vi_word_func in (in_vi_symbolic, not_in_vi_blank):

            # Look behind to first Char of Word

            while behind:
                ch = editor.fetch_column_char(column=behind)
                if not in_vi_word_func(ch):

                    break

                behind -= 1

            # Look ahead to first Char of Word

            for start in range(behind, columns):
                ch = editor.fetch_column_char(column=start)
                if in_vi_word_func(ch):

                    # Slip ahead to Start of Word

                    editor.column = start

                    # Collect one or more Chars of Word

                    word = ""

                    for end in range(start, columns):
                        ch = editor.fetch_column_char(column=end)
                        if in_vi_word_func(ch):
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
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if self.find_read_vi_line(slip=+1) is None:

                return

        # Try the Search

        if editor.find_ahead_and_reply():  # TODO: extra far scroll <= zb H 23Up n

            editor.continue_do_loop()

        # Vim echoes the / Search Key as Status, unless not found ahead
        # Vi Py echoes the / Search Key as Status, at /Up, at :g/Up, etc

    def do_find_all_vi_line(self):  # Vim :g/   # Vim :g?  # Vi Py :g/, :g?, g/, g?
        """Across all the File, print each Line containing 1 or More Matches"""

        editor = self.editor
        editor.reply_with_finding()

        # Take Search Key as input, but leave Search Slip unchanged

        if self.find_read_vi_line(slip=0) is None:

            return

        # Print Matches

        stale_status = self.format_vi_status(editor.skin.reply) + editor.finding_line

        if editor.find_ahead_and_reply():

            iobytespans = editor.iobytespans
            assert iobytespans

            last_span = iobytespans[-1]
            pin = editor.span_to_pin_on_char(last_span)
            (editor.row, editor.column) = pin

            editor.print_some_found_spans(stale_status)

            self.vi_print(  # "{}/{} Found {} chars"  # :g/, :g?, g/, g? Eggs
                "{}/{} Found {} chars".format(
                    len(iobytespans),
                    len(iobytespans),
                    last_span.beyond - last_span.column,
                )
            )

        # Vim lands the cursor in the first non-blank column

        # Vim echoes the ? Search Key as Status, unless not found behind
        # Vi Py echoes the ? Search Key as Status, at ?Up, at :g?Up, etc

        # TODO: Vim :4g/ means search only line 4, not pick +-Nth match

    def do_find_behind_vi_line(self):  # Vim ?
        """Take a Search Key as input, and then look behind for it"""

        editor = self.editor
        editor.reply_with_finding()

        if not editor.skin.doing_done:
            if self.find_read_vi_line(slip=-1) is None:

                return

        if editor.find_behind_and_reply():  # TODO: extra far scroll # <= zt L 23Down N

            editor.continue_do_loop()

    def find_read_vi_line(self, slip):
        """Take a Search Key"""

        editor = self.editor

        assert editor.finding_line != ""  # may be None, but never Empty
        slip_ = slip if slip else editor.finding_slip

        # Ask for fresh Search Key

        finding_line = None
        finding_line = self.read_vi_line()

        # Cancel Search if accepting stale Search Key while no stale Search Key exists

        if not finding_line:

            if finding_line is None:
                self.vi_print("Search cancelled")  # /⌃C, ?⌃C Eggs

                return

            if not editor.finding_line:  # Vim Return
                self.vi_print("Press one of / ? * # to enter a Search Key")  # n Egg

                return

        # Take fresh Slip always, and take fresh Search Key if given

        editor.finding_slip = slip_

        if finding_line:
            editor.finding_line = finding_line

        # Pick out Matches

        assert editor.finding_line != ""
        editor.reopen_found_spans()

        return True

    def read_vi_line(self):
        """Take a Line of Input"""

        editor = self.editor

        vi_reply = self.format_vi_status(self.editor.skin.reply)
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

        editor.reply_with_finding()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press ? or # to enter a Search Key")  # N Egg

            return

        # Try the Search

        and_earlier_func = behind_and_reply if (slip >= 0) else ahead_and_reply
        if and_earlier_func():

            editor.continue_do_loop()

    def do_vi_find_later(self):  # Vim n
        """Leap to later Search Key Match"""

        editor = self.editor

        ahead_and_reply = editor.find_ahead_and_reply
        behind_and_reply = editor.find_behind_and_reply
        slip = editor.finding_slip

        editor.reply_with_finding()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press / or * to enter a Search Key")  # n Egg

            return

        # Try the Search

        and_later_func = ahead_and_reply if (slip >= 0) else behind_and_reply
        if and_later_func():

            editor.continue_do_loop()

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |  # Emacs goto-char
        """Leap to first Column, else to a chosen Column"""

        editor = self.editor

        max_column = editor.spot_max_column()
        column = min(max_column, self.get_vi_arg1_int() - 1)

        editor.column = column

    def do_slip_dent(self):  # Vim ^
        """Leap to just past the Indent, but first Step Down if Arg"""

        count = self.get_vi_arg1_int(default=None)
        if count is not None:
            self.vi_print("Do you mean {} _".format(count))  # 9^ Egg, etc

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

        assert editor.skin.arg1 is None  # require no Digits before Vi Py 0 runs here

        editor.column = 0

    def do_slip_left(self):  # Vim h, ← Left Arrow  # Emacs left-char, backward-char
        """Slip left one Column or more"""

        editor = self.editor

        self.check_vi_index(editor.column)

        left = min(editor.column, self.get_vi_arg1_int())
        editor.column -= left

    def do_slip_right(self):  # Vim l, → Right Arrow  #  emacs right-char, forward-char
        """Slip Right one Column or more"""

        editor = self.editor

        max_column = editor.spot_max_column()
        self.check_vi_index(editor.column < max_column)

        right = min(max_column - editor.column, self.get_vi_arg1_int())
        editor.column += right

    #
    # Step the Cursor across zero, one, or more Columns of the same Row
    #

    def do_slip_ahead(self):  # Vim Space
        """Slip right, then down"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        if self.slip_ahead_one():
            editor.continue_do_loop()

    def slip_ahead_one(self):
        """Slip right or down, and return 1, else return None at End of File"""

        editor = self.editor

        max_column = editor.spot_max_column()
        last_row = editor.spot_last_row()

        if editor.column < max_column:
            editor.column += 1

            return 1

        elif editor.row < last_row:
            editor.column = 0
            editor.row += 1

            return 1

        # Vim ⌃O Space skips over the column beyond end of line, unlike Vi Py's
        # Vim ⌃O Delete visits the column beyond end of line, same as Vi Py's

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_first_pin() < editor.spot_pin())

        if self.slip_behind_one():

            editor.continue_do_loop()

    def slip_behind_one(self):
        """Slip left or down, and return 1, else return None at Start of File"""

        editor = self.editor

        if editor.column:
            editor.column -= 1

            return -1

        elif editor.row:
            editor.row -= 1
            row_max_column = editor.spot_max_column(row=editor.row)
            editor.column = row_max_column

            return -1

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step(self):  # Vim G, 1G  # Emacs goto-line
        """Leap to last Row, else to a chosen Row"""

        editor = self.editor
        last_row = editor.spot_last_row()

        row = min(last_row, self.get_vi_arg1_int() - 1)
        row = last_row if (editor.skin.arg1 is None) else row

        editor.row = row
        self.slip_dent()

    def do_step_down_dent(self):  # Vim +, Return
        """Step down a Row or more, but land just past the Indent"""

        self.step_down_repeatedly()
        self.slip_dent()

    def step_down_repeatedly(self):
        """Step down one Row or more"""

        editor = self.editor
        last_row = editor.spot_last_row()

        self.check_vi_index(editor.row < last_row)
        down = min(last_row - editor.row, self.get_vi_arg1_int())

        editor.row += down

    def do_step_down_minus_dent(self):  # Vim _
        """Leap to just past the Indent, but first Step Down if Arg"""

        self.step_down_minus()
        self.slip_dent()

    def step_down_minus(self):
        """Step down zero or more Rows, not one or more Rows"""

        down = self.get_vi_arg1_int() - 1
        if down:
            self.editor.skin.arg1 -= 1  # mutate
            self.step_down_repeatedly()

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

        self.step_up_repeatedly()
        self.slip_dent()

    def step_up_repeatedly(self):
        """Step up one Row or more"""

        editor = self.editor
        self.check_vi_index(editor.row)
        up = min(editor.row, self.get_vi_arg1_int())

        editor.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_max_seek(self):  # Vim $  # Emacs move-end-of-line
        """Leap to the last Column in Row, and keep seeking last Columns"""

        editor = self.editor

        self.seeking_column = True

        self.step_down_minus()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def do_step_down_seek(self):  # Vim j, ⌃J, ⌃N, ↓ Down Arrow  # Emacs next-line
        """Step down one Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_down_repeatedly()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def do_step_up_seek(self):  # Vim k, ⌃P, ↑ Up Arrow  # Emacs previous-line
        """Step up a Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_up_repeatedly()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def seek_vi_column(self, column=True):
        """Begin seeking a Column, if not begun already"""

        editor = self.editor

        max_column = editor.spot_max_column()

        if self.seeking_column is True:
            sought_column = max_column
        else:
            sought_column = min(max_column, self.seeking_column)

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
            if not self.editor.skin.doing_done:
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
            if not self.editor.skin.doing_done:
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
            if not editor.skin.doing_done:
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
            if not editor.skin.doing_done:
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

        row_plus = self.get_vi_arg1_int(default=(editor.row + 1))
        row = row_plus - 1
        editor.row = row

        editor.top_row = row

    def do_scroll_till_middle(self):  # Vim zz  # not to be confused with Vim ZZ
        """Scroll up or down till Cursor Row lands in Middle Row of Screen"""

        editor = self.editor
        painter = editor.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows

        row_plus = self.get_vi_arg1_int(default=(editor.row + 1))
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

        row_plus = self.get_vi_arg1_int(default=(editor.row + 1))
        row = row_plus - 1
        editor.row = row

        up = scrolling_rows - 1
        top_row = (row - up) if (row >= up) else 0

        editor.top_row = top_row

    #
    # Search ahead for an Empty Line (while ignoring Blank Lines)
    #

    def do_paragraph_ahead(self):  # Vim }
        """Step down over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor

        if editor.skin.doing_done:
            if editor.spot_pin >= editor.spot_last_pin():

                raise IndexError()

        while not editor.count_columns_in_row():
            if editor.row >= editor.spot_last_row():
                break
            editor.row += 1
            editor.column = 0

        while editor.count_columns_in_row():
            if editor.row >= editor.spot_last_row():
                editor.column = editor.spot_last_column()  # end at last Pin, not max
                break
            editor.row += 1
            editor.column = 0

        editor.continue_do_loop()

    def do_paragraph_behind(self):  # Vim {
        """Step up over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor

        if editor.skin.doing_done:
            if not editor.row:

                raise IndexError()

        while not editor.count_columns_in_row():
            if not editor.row:
                break
            editor.row -= 1

        while editor.count_columns_in_row():
            if not editor.row:
                break
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

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_end_ahead(charsets)

        editor.continue_do_loop()

    def word_end_ahead(self, charsets):
        """Slip ahead to last Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        self.slip_ahead_one()

        # Slip ahead across Blanks and Empty Lines, between Words, up to End of File

        while not editor.charsets_find_column(charsets):
            if not self.slip_ahead_one():

                break

        # Slip ahead across Chars of Word in Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                row_last_column = editor.spot_last_column(row=editor.row)
                if editor.column == row_last_column:

                    return

                ahead = self.slip_ahead_one()
                assert ahead, (editor.column, editor.count_columns_in_row())

            behind = self.slip_behind_one()  # backtrack
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

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_start_ahead(charsets)

        editor.continue_do_loop()

    def word_start_ahead(self, charsets):
        """Slip ahead to first Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        here = editor.charsets_find_column(charsets)

        _ = self.slip_ahead_one()

        # Slip ahead across more Chars of Word in Line

        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    break

                if not self.slip_ahead_one():

                    break

        # Slip ahead across Blanks, but not across Empty Lines, nor End of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_ahead_one():

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

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_start_behind(charsets)

        editor.continue_do_loop()

    def word_start_behind(self, charsets):
        """Slip behind to first Char of this else next Word"""

        editor = self.editor

        # Slip behind at least once (unless at Start of File)

        _ = self.slip_behind_one()

        # Slip behind across Blanks, but not across Empty Lines, nor Start of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_behind_one():

                break

        # Slip behind across Chars of Word, except stop at Start of Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    return

                behind = self.slip_behind_one()
                assert behind, (editor.column, editor.count_columns_in_row())

            ahead = self.slip_ahead_one()  # backtrack
            assert ahead, (editor.column, editor.count_columns_in_row())

    #
    # Search ahead inside the Row for a single Char
    #

    def do_slip_index_choice(self):  # Vim fx
        """Find Char to right in Row, once or more"""

        choice = self.get_vi_arg2_chords()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

        # TODO: Vim f⎋ means escaped without Bell
        # TODO: Vim f⌃C means cancelled with Bell
        # TODO: Vim f⌃? means cancelled with Bell

        # TODO: Vim f⌃VX means go find a ⌃V char, not go find X

    def do_slip_index_minus_choice(self):  # Vim tx
        """Find Char to Right in row, once or more, but then slip left one Column"""

        choice = self.get_vi_arg2_chords()

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

        count = self.get_vi_arg1_int()

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

    def do_slip_rindex_choice(self):  # Vim Fx
        """Find Char to left in Row, once or more"""

        choice = self.get_vi_arg2_chords()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def do_slip_rindex_plus_choice(self):  # Vim Tx
        """Find Char to left in Row, once or more, but then slip right one Column"""

        choice = self.get_vi_arg2_chords()

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

        count = self.get_vi_arg1_int()

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

    def do_slip_redo(self):  # Vim ;
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

    def do_slip_undo(self):  # Vim ,
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

        self.seeking_more = None  # break loop of Vi Column Seek

    def exit_do_vi(self):
        """Run after each Vi Func chosen by Chords"""

        # Remember the last Seeking Column across Funcs that ask for it

        if not self.seeking_more:
            self.seeking_column = None

    def format_vi_status(self, reply):
        """Format a Status Line of Row:Column, Nudge, and Message"""

        # Format parts, a la Vim ':set showcmd' etc

        pin_chars = "{},{}".format(1 + self.editor.row, 1 + self.editor.column)

        flags_chars = str(reply.flags) if reply.flags else ""

        nudge_bytes = b"" if (reply.nudge is None) else reply.nudge.join_bytes()
        nudge_chars = format(repr_vi_nudge_bytes(nudge_bytes)) if nudge_bytes else ""

        message_chars = str(reply.message) if reply.message else ""

        bell_chars = "?" if reply.bell else ""

        # Join parts

        replies = (pin_chars, flags_chars, nudge_chars, message_chars, bell_chars)
        vi_status = "  ".join(_ for _ in replies if _)

        return vi_status

    def place_vi_cursor(self):
        """Place the Cursor"""

        editor = self.editor

        row = editor.row - editor.top_row
        column = editor.column

        return TerminalPin(row, column=column)

    #
    # Variations on Switch Keyboards
    #

    def do_slip_beyond_last_take_inserts(self):  # Vim A
        """Take Input Chords after the Last Char of this Line"""

        editor = self.editor
        columns = editor.count_columns_in_row()

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert beyond Last Column

        if not columns:
            editor.column = 0
        else:
            editor.column = columns

        self.take_inserts()

    def do_slip_dent_take_inserts(self):  # Vim I
        """Take Input Chords after the Dent of the Line"""

        editor = self.editor

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert beyond Dent

        self.slip_dent()

        self.take_inserts()

    def do_slip_first_split_take_inserts(self):  # Vim O
        """Insert an empty Line before this Line, and take Input Chords into it"""

        editor = self.editor

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert an empty Line before this Line, but land in front of it

        editor.column = 0
        editor.insert_one_line()  # insert an empty Line before Cursor Line
        self.held_file.touches += 1
        editor.row -= 1

        # Take Input Chords into the new empty Line

        self.take_inserts()

    def do_slip_take_inserts(self):  # Vim a
        """Take Input Chords after the Char Beneath the Cursor"""

        editor = self.editor

        column = editor.column
        columns = editor.count_columns_in_row()

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert beyond this Char

        if column <= columns:
            editor.column = column + 1

        self.take_inserts()

    def do_slip_last_split_take_inserts(self):  # Vim o
        """Insert an empty Line after this Line, and take Input Chords into it"""

        editor = self.editor
        ended_lines = editor.ended_lines

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert an empty Line after this Line, but land in front of it

        if ended_lines:
            editor.row += 1
        editor.column = 0

        editor.insert_one_line()  # insert an empty Line after Cursor Line
        self.held_file.touches += 1

        editor.row -= 1

        # Take Input Chords into the new empty Line

        self.take_inserts()

    def do_take_inserts(self):  # Vim i
        """Take many keyboard Input Chords as meaning insert Chars, till Esc"""

        editor = self.editor

        # Raise NotImplementedError: Repeat Count  # TODO: till coded

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Insert before the Char beneath the Cursor

        self.take_inserts()

    #
    # Switch Keyboards
    #

    def take_inserts(self):

        editor = self.editor

        # Take many keyboard Input Chords

        self.vi_print("Type chars to insert, press Esc when done")

        keyboard = TerminalKeyboardViInsert(vi=self)
        editor.touching_beyond = True
        try:
            editor.run_skin_with_keyboard(keyboard)  # TerminalKeyboardViInsert
            assert False  # unreached
        except SystemExit:
            editor.touching_beyond = None
            editor.skin.doing_traceback = editor.skin.traceback

        # Slip the Cursor back onto the last inserted Char

        if editor.column:
            editor.column -= 1

        # Count Rows or Columns inserted

        self.vi_print("{} inserted".format(editor.format_touch_count()))

    def do_take_replacements(self):  # Vim R
        """Take many keyboard Input Chords as meaning replace Chars, till Esc"""

        editor = self.editor

        if editor.skin.arg1:

            return  # return to raise NotImplementedError: Repeat Count

        # Take many keyboard Input Chords

        self.vi_print("Type chars to replace, press Esc when done")

        keyboard = TerminalKeyboardViReplace(vi=self)
        editor.touching_beyond = True
        try:
            editor.run_skin_with_keyboard(keyboard)  # TerminalKeyboardViReplace
            assert False  # unreached
        except SystemExit:
            editor.touching_beyond = None
            editor.skin.doing_traceback = editor.skin.traceback

        # Slip the Cursor back onto the last replaced Char

        if editor.column:
            editor.column -= 1

        # Count Rows or Columns replaced

        self.vi_print("{} replaced".format(editor.format_touch_count()))

    def do_run_one_nudge(self):  # Vim ⌃O after Vim A I O R a i o etc
        """Take one Terminal Nudge In, as if Not inserting or replacing Chars"""

        editor = self.editor

        assert not editor.skin.arg1

        # Suspend, run, resume

        keyboard = TerminalKeyboardVi(vi=self)
        keyboard.hello_line = "Give one command"
        keyboard.continue_do_func = editor.do_sys_exit

        try:
            editor.run_skin_with_keyboard(keyboard)  # TerminalKeyboardVi
            assert False  # unreached
        except SystemExit:
            editor.skin.doing_traceback = editor.skin.traceback  # TODO: test this Egg

        editor.skin.reply = keyboard.skin.reply  # TODO: ugly

    def do_insert_one_line(self):
        """Insert one Line"""

        editor = self.editor
        editor.insert_one_line()
        self.held_file.touches += 1
        self.vi_print("inserted line")

    def do_insert_one_char(self):
        """Insert one Char"""

        editor = self.editor

        chars = self.get_vi_arg0_chars()
        editor.insert_some_chars(chars)  # insert as inserting itself
        self.held_file.touches += 1
        self.vi_print("inserted char")

    def do_replace_with_choice(self):  # Vim r
        """Replace one char with Input Suffix Char"""

        editor = self.editor

        choice = self.get_vi_arg2_chords()
        editor.replace_some_chars(chars=choice)
        self.held_file.touches += 1
        self.vi_print("{} replaced".format(editor.format_touch_count()))

        editor.continue_do_loop()

    def do_replace_one_char(self):
        """Replace one char"""

        editor = self.editor

        chars = self.get_vi_arg0_chars()
        editor.replace_some_chars(chars)
        self.held_file.touches += 1
        self.vi_print("replaced char")


class TerminalKeyboard:
    """Map Keyboard Inputs to Code"""

    def __init__(self):

        self.cursor_style = None
        self.hello_line = None

        self.format_status_func = lambda: None
        self.place_cursor_func = lambda: None
        self.enter_do_func = lambda: None
        self.continue_do_func = lambda: None
        self.exit_do_func = lambda: None

        self.prefix_chords = b""
        self.more_prefix_chords = b""

        self.corrections_by_chords = dict()
        self.func_by_chords = dict()
        self.suffixes_by_chords = dict()

    def _init_correcting_many_chords(self, chords, corrections):
        """Map one sequence of keyboard Input Chords to another"""

        corrections_by_chords = self.corrections_by_chords

        self._init_func_by_many_chords(chords, func=None)
        corrections_by_chords[chords] = corrections

    def _init_suffix_func(self, chords, func):
        """Map a sequence of keyboard Input Chords that needs 1 Suffix Chord"""

        self._init_func_by_many_chords(chords, func=func, suffixes=1)

    def _init_func_by_many_chords(self, chords, func, suffixes=None):
        """Map a sequence of keyboard Input Chords"""

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

    def __init__(self, vi):

        super().__init__()

        self.vi = vi
        self.editor = vi.editor

        self.cursor_style = _VIEW_CURSOR_STYLE_

        self.format_status_func = vi.format_vi_status
        self.place_cursor_func = vi.place_vi_cursor
        self.enter_do_func = vi.enter_do_vi
        self.exit_do_func = vi.exit_do_vi

        self.prefix_chords = b"123456789"
        self.more_prefix_chords = b"1234567890"

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
        func_by_chords[b"\x08"] = vi.do_slip_behind  # BS, ⌃H, 8 \b
        # func_by_chords[b"\x09"] = vi.do_c0_control_tab  # TAB, ⌃I, 9 \t
        func_by_chords[b"\x0A"] = vi.do_step_down_seek  # LF, ⌃J, 10 \n
        # func_by_chords[b"\x0B"] = vi.do_c0_control_vt  # VT, ⌃K, 11 \v
        func_by_chords[b"\x0C"] = editor.do_redraw  # FF, ⌃L, 12 \f
        func_by_chords[b"\x0D"] = vi.do_step_down_dent  # CR, ⌃M, 13 \r
        func_by_chords[b"\x0E"] = vi.do_step_down_seek  # SO, ⌃N, 14
        # func_by_chords[b"\x0F"] = vi.do_c0_control_si  # SI, ⌃O, 15
        func_by_chords[b"\x10"] = vi.do_step_up_seek  # DLE, ⌃P, 16
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
        func_by_chords[b"$"] = vi.do_slip_max_seek
        # func_by_chords[b"%"]  # TODO: leap to match
        # func_by_chords[b"&"]  # TODO: & and && for repeating substitution
        # func_by_chords[b"'"]  # TODO: leap to pin
        # func_by_chords[b"("]  # TODO: sentence behind
        # func_by_chords[b")"]  # TODO: sentence ahead
        func_by_chords[b"*"] = vi.do_find_ahead_vi_this
        func_by_chords[b"+"] = vi.do_step_down_dent
        func_by_chords[b","] = vi.do_slip_undo
        func_by_chords[b"-"] = vi.do_step_up_dent
        func_by_chords[b"/"] = vi.do_find_ahead_vi_line

        func_by_chords[b"0"] = vi.do_slip_first

        self._init_correcting_many_chords(b":/", corrections=b"/")
        self._init_correcting_many_chords(b":?", corrections=b"?")

        self._init_func_by_many_chords(b":g?", func=vi.do_find_all_vi_line)
        self._init_func_by_many_chords(b":g/", func=vi.do_find_all_vi_line)
        self._init_func_by_many_chords(b":n\r", func=vi.do_might_next_vi_file)
        self._init_func_by_many_chords(b":n!\r", func=vi.do_next_vi_file)
        self._init_func_by_many_chords(b":q\r", func=vi.do_might_quit_vi)
        self._init_func_by_many_chords(b":q!\r", func=vi.do_quit_vi)
        self._init_func_by_many_chords(b":vi\r", func=editor.do_resume_editor)
        self._init_func_by_many_chords(b":w\r", func=vi.do_might_flush_vi)
        self._init_func_by_many_chords(b":w!\r", func=vi.do_flush_vi)
        self._init_func_by_many_chords(b":wq\r", func=vi.do_might_flush_quit_vi)
        self._init_func_by_many_chords(b":wq!\r", func=vi.do_flush_quit_vi)

        func_by_chords[b";"] = vi.do_slip_redo
        # func_by_chords[b"<"]  # TODO: dedent
        # func_by_chords[b"="]  # TODO: dent after
        # func_by_chords[b">"]  # TODO: indent
        func_by_chords[b"?"] = vi.do_find_behind_vi_line
        # func_by_chords[b"@"] = vi.do_replay_input

        func_by_chords[b"A"] = vi.do_slip_beyond_last_take_inserts
        func_by_chords[b"B"] = vi.do_big_word_start_behind
        # func_by_chords[b"C"] = vi.do_chop_open
        # func_by_chords[b"D"] = vi.do_chop
        func_by_chords[b"E"] = vi.do_big_word_end_ahead

        self._init_suffix_func(b"F", func=vi.do_slip_rindex_choice)

        func_by_chords[b"G"] = vi.do_step
        func_by_chords[b"H"] = vi.do_step_max_high
        func_by_chords[b"I"] = vi.do_slip_dent_take_inserts
        # func_by_chords[b"J"] = vi.do_slip_last_join_right
        # func_by_chords[b"K"] = vi.do_lookup
        func_by_chords[b"L"] = vi.do_step_max_low
        func_by_chords[b"M"] = vi.do_step_to_middle
        func_by_chords[b"N"] = vi.do_vi_find_earlier
        func_by_chords[b"O"] = vi.do_slip_first_split_take_inserts
        # func_by_chords[b"P"] = vi.do_paste_behind

        self._init_func_by_many_chords(b"Qvi\r", func=vi.do_continue_vi)

        func_by_chords[b"R"] = vi.do_take_replacements
        # func_by_chords[b"S"] = vi.do_slip_first_chop_open

        self._init_suffix_func(b"T", func=vi.do_slip_rindex_plus_choice)

        # func_by_chords[b"U"] = vi.do_row_undo
        # func_by_chords[b"V"] = vi.do_gloss_rows
        func_by_chords[b"W"] = vi.do_big_word_start_ahead
        # func_by_chords[b"X"] = vi.do_cut_behind
        # func_by_chords[b"Y"] = vi.do_copy_row

        self._init_correcting_many_chords(b"QZ", corrections=b"Z")
        # TODO: stop commandeering the personal QZ Chord Sequence

        self._init_func_by_many_chords(b"ZQ", func=vi.do_quit_vi)
        self._init_func_by_many_chords(b"ZZ", func=vi.do_flush_quit_vi)

        # func_by_chords[b"["]  # TODO: b"["

        self._init_func_by_many_chords(b"\\F", func=editor.do_set_invregex)
        self._init_func_by_many_chords(b"\\i", func=editor.do_set_invignorecase)
        self._init_func_by_many_chords(b"\\n", func=editor.do_set_invnumber)

        # TODO: stop commandeering the personal \Esc \F \i \n Chord Sequences

        # func_by_chords[b"]"]  # TODO: b"]"
        func_by_chords[b"^"] = vi.do_slip_dent
        func_by_chords[b"_"] = vi.do_step_down_minus_dent
        # func_by_chords[b"`"]  # TODO: close to b"'"

        func_by_chords[b"a"] = vi.do_slip_take_inserts
        func_by_chords[b"b"] = vi.do_lil_word_start_behind
        # func_by_chords[b"c"] = vi.do_chop_after_open
        # func_by_chords[b"d"] = vi.do_chop_after
        func_by_chords[b"e"] = vi.do_lil_word_end_ahead

        self._init_suffix_func(b"f", func=vi.do_slip_index_choice)

        self._init_correcting_many_chords(b"g/", corrections=b":g/")
        self._init_correcting_many_chords(b"g?", corrections=b":g?")
        # TODO: stop commandeering the personal g/ g? Chord Sequences

        # func_by_chords[b"g"]
        func_by_chords[b"h"] = vi.do_slip_left
        func_by_chords[b"i"] = vi.do_take_inserts
        func_by_chords[b"j"] = vi.do_step_down_seek
        func_by_chords[b"k"] = vi.do_step_up_seek
        func_by_chords[b"l"] = vi.do_slip_right

        # self._init_suffix_func(b"m", func=vi.do_drop_pin)

        func_by_chords[b"n"] = vi.do_vi_find_later
        func_by_chords[b"o"] = vi.do_slip_last_split_take_inserts

        # func_by_chords[b"p"] = vi.do_paste_ahead
        # func_by_chords[b"q"] = vi.do_record_input

        self._init_suffix_func(b"r", func=vi.do_replace_with_choice)

        # func_by_chords[b"s"] = vi.do_cut_behind_open

        self._init_suffix_func(b"t", func=vi.do_slip_index_minus_choice)

        # func_by_chords[b"u"] = vi.do_undo
        # func_by_chords[b"v"] = vi.do_gloss_chars
        func_by_chords[b"w"] = vi.do_lil_word_start_ahead
        # func_by_chords[b"x"] = vi.do_cut_ahead
        # func_by_chords[b"y"] = vi.do_copy_after

        self._init_func_by_many_chords(b"zb", func=vi.do_scroll_till_bottom)
        self._init_func_by_many_chords(b"zt", func=vi.do_scroll_till_top)
        self._init_func_by_many_chords(b"zz", func=vi.do_scroll_till_middle)

        func_by_chords[b"{"] = vi.do_paragraph_behind
        func_by_chords[b"|"] = vi.do_slip
        func_by_chords[b"}"] = vi.do_paragraph_ahead
        # func_by_chords[b"~"] = vi.do_flip_char_case

        # Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS

        self._init_correcting_many_chords("£".encode(), corrections=b"#")


#
# Insert Chars into the Line, or add Chars past its end, or add Lines before it
#


class TerminalKeyboardViInsert(TerminalKeyboard):
    """Map Keyboard Inputs to insert Characters"""

    def __init__(self, vi):

        super().__init__()

        self.cursor_style = _INSERT_CURSOR_STYLE_

        self.vi = vi
        self.editor = vi.editor

        self.hello_line = "Press Esc to quit, else type chars to insert"

        self.format_status_func = vi.format_vi_status
        self.place_cursor_func = vi.place_vi_cursor

        self._init_by_vi_insert_chords_()

    def _init_by_vi_insert_chords_(self):

        func_by_chords = self.func_by_chords
        editor = self.editor
        vi = self.vi

        # Define the C0_CONTROL_STDINS

        for chords in sorted(C0_CONTROL_STDINS):
            func_by_chords[chords] = editor.do_raise_name_error

        # Mutate the C0_CONTROL_STDINS definitions

        func_by_chords[b"\x03"] = editor.do_sys_exit  # ETX, ⌃C, 3
        func_by_chords[b"\x0D"] = vi.do_insert_one_line  # CR, ⌃M, 13 \r
        func_by_chords[b"\x0F"] = vi.do_run_one_nudge  # SI, ⌃O, 15
        func_by_chords[b"\x1A"] = editor.do_sig_tstp  # SUB, ⌃Z, 26
        func_by_chords[b"\x1B"] = editor.do_sys_exit  # ESC, ⌃[, 27

        # Define the BASIC_LATIN_STDINS

        for chords in BASIC_LATIN_STDINS:
            func_by_chords[chords] = vi.do_insert_one_char

        # Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS

        self._init_correcting_many_chords("£".encode(), corrections=b"#")


#
# Replace Chars in the Line, or add Chars past its end, or add Lines after it
#


class TerminalKeyboardViReplace(TerminalKeyboard):
    """Map Keyboard Inputs to replace Characters"""

    def __init__(self, vi):

        super().__init__()

        self.cursor_style = _REPLACE_CURSOR_STYLE_

        self.vi = vi
        self.editor = vi.editor

        self.hello_line = "Press Esc to quit, else type replacement chars" ""

        self.format_status_func = vi.format_vi_status
        self.place_cursor_func = vi.place_vi_cursor

        self._init_by_vi_replace_chords_()

    def _init_by_vi_replace_chords_(self):

        func_by_chords = self.func_by_chords
        editor = self.editor
        vi = self.vi

        # Define the C0_CONTROL_STDINS

        for chords in sorted(C0_CONTROL_STDINS):
            func_by_chords[chords] = editor.do_raise_name_error

        # Mutate the C0_CONTROL_STDINS definitions

        func_by_chords[b"\x03"] = editor.do_sys_exit  # ETX, ⌃C, 3
        func_by_chords[b"\x0D"] = vi.do_insert_one_line  # CR, ⌃M, 13 \r
        func_by_chords[b"\x0F"] = vi.do_run_one_nudge  # SI, ⌃O, 15
        func_by_chords[b"\x1A"] = editor.do_sig_tstp  # SUB, ⌃Z, 26
        func_by_chords[b"\x1B"] = editor.do_sys_exit  # ESC, ⌃[, 27

        # Define the BASIC_LATIN_STDINS

        for chords in BASIC_LATIN_STDINS:
            func_by_chords[chords] = vi.do_replace_one_char

        # Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS

        self._init_correcting_many_chords("£".encode(), corrections=b"#")


#
# Edit some Chars in the Bottom Lines of the Screen
#


class TerminalSkinEx:
    """Feed Keyboard into Line at Bottom of Screen of Scrolling Rows, a la Ex"""

    def __init__(self, editor, vi_reply):

        self.editor = editor
        self.vi_reply = vi_reply

        self.ex_line = None

    def read_ex_line(self):
        """Take an Input Line from beneath the Scrolling Rows"""

        editor = self.editor

        self.ex_line = ""

        keyboard = TerminalKeyboardEx(ex=self)
        try:
            editor.run_skin_with_keyboard(keyboard)  # TerminalKeyboardEx
            assert False  # unreached
        except SystemExit:
            line = self.ex_line

            editor.skin.doing_traceback = editor.skin.traceback

            return line

    def flush_ex_status(self):
        """Paint Status and Cursor now"""

        editor = self.editor

        keyboard = editor.skin.keyboard
        reply = editor.skin.reply

        editor.flush_editor(keyboard, reply=reply)  # for 'flush_ex_status'

    def format_ex_status(self, reply):
        """Keep up the Vi Reply while working the Ex Keyboard, but add the Input Line"""

        ex_line = self.ex_line
        vi_reply = self.vi_reply

        ex_reply = vi_reply + ex_line

        return ex_reply

    def place_ex_cursor(self):
        """Place the Cursor"""

        editor = self.editor
        painter = editor.painter

        ex_reply = self.format_ex_status(editor.skin.reply)

        row = painter.status_row
        column = len(ex_reply)

        return TerminalPin(row, column=column)

    def do_clear_chars(self):  # Vim Ex ⌃U
        """Undo all the Append Chars, if any Not undone already"""

        self.ex_line = ""

    def do_append_char(self):
        """Append the Chords to the Input Line"""

        editor = self.editor
        chars = editor.get_arg0_chars()

        if chars == "£":  # TODO: less personal choice
            self.ex_line += "#"  # a la Vim :abbrev £ #
        else:
            self.ex_line += chars

    def do_append_suffix(self):  # Vim Ex ⌃V
        """Append the Suffix Chord to the Input Line"""

        chars = self.editor.skin.arg2_chords

        raise NotImplementedError("⌃V", repr(chars))

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
        """Lose all input and quit"""

        self.ex_line = None

        sys.exit()

    def do_copy_down(self):  # Vim Ex ⌃P, ↑ Up Arrow
        """Recall last input line"""

        editor = self.editor
        ex_line = self.ex_line

        editor_finding_line = editor.finding_line
        if ex_line is not None:
            if editor_finding_line is not None:
                if editor_finding_line.startswith(ex_line):

                    self.ex_line = editor_finding_line

                    return

        raise ValueError("substring not found")


class TerminalKeyboardEx(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Ex"""

    def __init__(self, ex):

        super().__init__()

        self.cursor_style = _VIEW_CURSOR_STYLE_

        self.ex = ex
        self.editor = ex.editor

        self.format_status_func = ex.format_ex_status
        self.place_cursor_func = ex.place_ex_cursor

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
        func_by_chords[b"\x08"] = ex.do_undo_append_char  # BS, ⌃H, 8 \b
        func_by_chords[b"\x0D"] = editor.do_sys_exit  # CR, ⌃M, 13 \r
        func_by_chords[b"\x10"] = ex.do_copy_down  # DLE, ⌃P, 16
        func_by_chords[b"\x1A"] = editor.do_sig_tstp  # SUB, ⌃Z, 26
        func_by_chords[b"\x15"] = ex.do_clear_chars  # NAK, ⌃U, 21

        self._init_suffix_func(b"\x16", func=ex.do_append_suffix)  # SYN, ⌃V, 22

        func_by_chords[b"\x1B[A"] = ex.do_copy_down  # ↑ Up Arrow

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
    """Collect the parts of one Nudge In"""

    def __init__(self, prefix=None, chords=None, suffix=None, epilog=None):

        self.prefix = prefix  # such as Repeat Count Digits before Vi Chords
        self.chords = chords  # such as b"Qvi\r" Vi Chords
        self.suffix = suffix  # such as b"x" of b"fx" to Find Char "x" in Vi
        self.epilog = epilog  # such as b"⌃C" of b"f⌃C" to cancel b"f"

    def join_bytes(self):
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
    """Collect the parts of one Reply Out"""

    def __init__(self, flags=None, nudge=None, message=None, bell=None):

        self.flags = flags  # such as "-Fin" Grep-Like Search
        self.nudge = nudge  # keep up a trace of the last input that got us here
        self.message = message  # say more
        self.bell = bell  # ring bell

    # Jun/2018 Python 3.7 can say '._defaults=(None, None),'


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


class TerminalSkin:
    """Form a Skin out of keyboard Input Chords and an Output Reply"""

    def __init__(self, chords=()):

        self.keyboard = None  # map Keyboard Inputs to Code

        self.chord_ints_ahead = list(chords)  # defer keyboard Input Chords

        self.traceback = None  # capture Python Tracebacks

        self.nudge = TerminalNudgeIn()  # split the Chords of one Keyboard Input
        self.arg0_chords = None  # take all the Chords as Chars in a Row
        self.arg1 = None  # take the Prefix Bytes as an Int of Decimal Digits
        self.arg2_chords = None  # take the Suffix Bytes as one Encoded Char

        self.reply = TerminalReplyOut()  # declare an Empty Reply

        self.doing_less = None  # reject the Arg1 when not explicitly accepted
        self.doing_more = None  # take the Arg1 as a Count of Repetition's
        self.doing_done = None  # count the Repetition's completed before now
        self.doing_traceback = None  # retain a Python Traceback till after more Chords


class TerminalEditor:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars"""

    def __init__(self, chords):

        self.skin = TerminalSkin(chords)

        self.stdio = sys.stderr  # layer over a Terminal I/O Stack
        self.driver = TerminalDriver(stdio=self.stdio)
        self.shadow = TerminalShadow(terminal=self.driver)
        self.painter = TerminalPainter(terminal=self.shadow)

        self.terminal_size = None  # detect changes in Terminal Column:Lines

        self.showing_line_number = None  # show Line Numbers or not
        self.showing_lag = None  # inject None or 0s or more Lag

        self.touching_beyond = None  # slip the Cursor past Last Char in Line, or not
        self.touching_pins = list()  # collect a TerminalPinPlus per edit

        self.finding_case = None  # ignore Upper/Lower Case in Searching or not
        self.finding_line = None  # remember the Search Key
        self.finding_regex = None  # search as Regex or search as Chars
        self.finding_slip = 0  # remember to Search again ahead or again behind
        self.finding_highlights = None  # show Searching as Highlights, or don't

        self._reinit_with_held_file_(TerminalFile())

        # TODO: mutable namespaces for self.finding_, argv_, doing_, etc

    def _reinit_with_held_file_(self, held_file):
        """Swap in a new File of Lines"""

        self.held_file = held_file
        self.ended_lines = held_file.ended_lines

        self.row = 0  # point the Cursor to a Row of File
        self.column = 0  # point the Cursor to a Column of File

        self.top_row = 0  # scroll through more Lines than fit on Screen

        self.iobytespans = list()  # cache the spans in file
        self.reopen_found_spans()

    #
    # Stack Skin's with Keyboard's on top of a Terminal I/O Stack
    #

    def _reopen_terminal_(self):
        """Clear the Caches of this Terminal, here and below, if cacheing here"""

        showing_lag = self.showing_lag
        painter = self.painter

        if not painter.rows:
            return

        if showing_lag is not None:
            self.driver.lag = showing_lag
            painter.terminal = self.driver
        else:
            self.driver.lag = None
            painter.terminal = self.shadow

        size = painter._reopen_terminal_()
        self.terminal_size = size

        return size

    def _keep_busy_(self, reply):
        """Work while waiting for input"""

        keyboard = self.skin.keyboard

        if self.terminal_size is not None:
            if self.driver.get_terminal_size() != self.terminal_size:

                self._reopen_terminal_()  # for resize
                self.flush_editor(keyboard, reply=reply)  # for resize

    def run_terminal_with_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        assert self.showing_lag is None

        # self.painter.__enter__()  # no, enter lazily, via 'do_resume_editor'
        try:
            self.run_skin_with_keyboard(keyboard)  # like till SystemExit
        finally:
            self.painter.__exit__(*sys.exc_info())

    def run_skin_with_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        painter = self.painter
        skin = self.skin

        chords = skin.chord_ints_ahead  # TODO: works, but clashes types
        cursor_style = skin.keyboard.cursor_style if skin.keyboard else None
        hello_line = skin.keyboard.hello_line if skin.keyboard else None

        self.skin = TerminalSkin(chords)

        if skin.keyboard:
            if cursor_style != keyboard.cursor_style:
                painter.terminal_write(keyboard.cursor_style)

        try:
            if keyboard.hello_line:
                self.editor_print(keyboard.hello_line)
            self.run_keyboard(keyboard)  # like till SystemExit
        finally:
            skin.traceback = self.skin.traceback

            if skin.keyboard:
                if cursor_style != keyboard.cursor_style:
                    painter.terminal_write(cursor_style)

            if hello_line:
                self.editor_print(hello_line)

            keyboard.skin = self.skin  # TODO: ugly

            self.skin = skin

    def run_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        self.skin.keyboard = keyboard

        # Repeat like till SystemExit raised

        while True:

            # Scroll and prompt

            if self.painter.rows:
                self.scroll_cursor_into_screen()
                self.flush_editor(keyboard, reply=self.skin.reply)  # for 'run_keyboard'
                self.skin.reply.bell = False  # ring the Bell at most once per ask

            # Take one Chord in, or next Chord, or cancel Chords to start again

            try:
                chord = self.take_editor_chord()
            except KeyboardInterrupt:
                chord = b"\x03"  # ETX, ⌃C, 3

            chords_func = self.choose_chords_func(chord)
            if chords_func is None:

                continue

            # Reply

            keyboard.enter_do_func()
            try:

                self.call_chords_func(chords_func)  # reply to one whole Nudge
                keyboard.continue_do_func()

            except KeyboardInterrupt:  # Egg of *123456n⌃C, etc

                self.editor_print("Interrupted")
                self.reply_with_bell()
                # self.skin.chord_ints_ahead = list()

                self.skin.traceback = traceback.format_exc()

                keyboard.continue_do_func()

            except Exception as exc:  # Egg of NotImplementedError, etc

                name = type(exc).__name__
                str_exc = str(exc)
                line = "{}: {}".format(name, str_exc) if str_exc else name

                self.editor_print(line)  # "{exc_type}: {str_exc}"
                self.reply_with_bell()
                # self.skin.chord_ints_ahead = list()

                self.skin.traceback = traceback.format_exc()
                if not self.painter.rows:

                    raise

                keyboard.continue_do_func()

            finally:
                keyboard.exit_do_func()

            self.skin.nudge = TerminalNudgeIn()  # consume the whole Nudge

            # Vim replies with Bell more often

        # TODO: shuffle away 'run_keyboard', 'choose_chords_func', 'call_chords_func'

    def do_resume_editor(self):
        """Set up XTerm Alt Screen & Keyboard, till 'self.painter.__exit__'"""

        self.painter.__enter__()
        self._reopen_terminal_()

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

    def flush_editor(self, keyboard, reply):
        """Paint Screen, Cursor, and Bell now"""

        ended_lines = self.ended_lines
        painter = self.painter

        # 1st: Option to rewrite whole Screen slowly

        if (self.showing_lag is None) and reply.bell:
            self._reopen_terminal_()  # for bell

        # 2nd: Call back to format Status and place Cursor

        status = keyboard.format_status_func(reply)
        cursor = keyboard.place_cursor_func()

        # Paint Screen, Cursor, and Bell

        painter.top_line_number = 1 + self.top_row
        painter.last_line_number = 1 + len(ended_lines)
        painter.painting_line_number = self.showing_line_number

        screen_lines = ended_lines[self.top_row :][: painter.scrolling_rows]
        screen_spans = self.spot_spans_on_screen()

        painter.paint_screen(
            ended_lines=screen_lines,
            spans=screen_spans,
            status=status,
            cursor=cursor,
            bell=reply.bell,
        )

        # Flush Screen, Cursor, and Bell

        painter.flush_painter()

    def spot_spans_on_screen(self):
        """Spot where to highlight each Match of the Search Key on Screen"""

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

    def choose_chords_func(self, chord):
        """Accept one Keyboard Input into Prefix, into main Chords, or as Suffix"""

        chord_ints_ahead = self.skin.chord_ints_ahead
        chords = self.skin.nudge.chords
        keyboard = self.skin.keyboard
        prefix = self.skin.nudge.prefix

        prefix_chords = keyboard.prefix_chords
        more_prefix_chords = keyboard.more_prefix_chords
        corrections_by_chords = keyboard.corrections_by_chords
        func_by_chords = keyboard.func_by_chords

        assert self.skin.nudge.suffix is None, (chords, chord)  # one Chord only

        # Take more decimal Digits, while nothing but decimal Digits given

        if not chords:
            if (chord in prefix_chords) or (prefix and chord in more_prefix_chords):

                prefix_plus = chord if (prefix is None) else (prefix + chord)
                self.skin.nudge.prefix = prefix_plus
                self.editor_print()  # echo Prefix

                # Ask for more Prefix, else for main Chords

                return None  # ask for more Prefix, or for other Chords

        self.skin.arg1 = int(prefix) if prefix else None
        assert self.get_arg1_int() >= 1

        # At KeyboardInterrupt, cancel these keyboard Input Chords and start over

        chords_plus = chord if (chords is None) else (chords + chord)

        if prefix or chords:
            if chord == b"\x03":  # ETX, ⌃C, 3
                self.skin.nudge.chords = chords_plus
                self.editor_print("Cancelled input")  # 123⌃C Egg, f⌃C Egg, etc

                return lambda: self.get_arg1_int()

        # If not taking a Suffix now

        chords_func = func_by_chords.get(chords)
        if not (chords_func and (chords in keyboard.suffixes_by_chords)):
            self.skin.nudge.chords = chords_plus
            self.editor_print()  # echo Prefix + Chords

            self.skin.arg0_chords = chords_plus

            # If need more Chords

            default_func = self.do_raise_name_error

            chords_plus_func = func_by_chords.get(chords_plus, default_func)
            if (not chords_plus_func) or (chords_plus in keyboard.suffixes_by_chords):

                # Option to auto-correct the Chords

                if chords_plus in corrections_by_chords.keys():
                    self.skin.nudge.chords = b""
                    corrected_chords = corrections_by_chords[chords_plus]
                    corrected_ints = list(corrected_chords)
                    chord_ints_ahead[:] = corrected_ints + chord_ints_ahead
                    self.editor_print("Corrected")

                # Ask for more Chords, or for Suffix

                return None

            self.skin.arg2_chords = None

            # Call a Func with or without Prefix, and without Suffix

            assert chords_plus not in corrections_by_chords.keys(), (chords, chord)
            assert chords_plus_func is not None, (chords, chord)

            return chords_plus_func

        assert self.skin.arg0_chords == chords, (chords, chord, self.skin.arg0_chords)

        # Call a Func chosen by Chords plus Suffix

        suffix = chord
        self.skin.nudge.suffix = suffix
        self.editor_print()  # echo Prefix + Chords + Suffix

        self.skin.arg2_chords = suffix.decode(errors="surrogateescape")

        # Call a Func with Suffix, but with or without Prefix

        assert chords not in corrections_by_chords.keys()
        assert chords_func is not None, (chords, chord)

        return chords_func

    def call_chords_func(self, chords_func):
        """Call the Func once or more, in reply to one Terminal Nudge In"""

        # Setup before first calling the Func

        self.skin.doing_done = 0
        self.skin.doing_less = True

        if not self.touching_beyond:
            self.touching_pins[:] = list()

        # Call the Func once or more

        while True:
            self.skin.doing_more = None

            # Call the Func, for the first time or again
            # Forget any Python Traceback older than the Func after the Func exits

            try:

                try:
                    chords_func()
                    pin = self.spot_pin()
                finally:
                    self.keep_cursor_on_file()

            except Exception:  # do Not finally catch SystemExit, KeyboardInterrupt
                self.skin.traceback = self.skin.doing_traceback
                self.skin.doing_traceback = None

                raise

            self.skin.traceback = self.skin.doing_traceback
            self.skin.doing_traceback = None

            # Raise an Exception when the Func has gone egregiously wrong

            self.raise_blame_for_chords_func(pin)

            # Let the Func take the Arg as a Count of Repetitions, but don't force it

            if self.skin.doing_more:
                self.skin.doing_done += 1
                if self.skin.doing_done < self.get_arg1_int():

                    _ = self.peek_editor_chord()  # raise KeyboardInterrupt at ⌃C

                    continue

            break

    def raise_blame_for_chords_func(self, pin):
        """Raise an Exception when the Func has gone egregiously wrong"""

        # Blame the Func when Cursor slips off File

        if self.spot_pin() != pin:

            raise KwArgsException(before=tuple(pin), after=tuple(self.spot_pin()))

        # Blame the Func when Repeat Count given but Not taken

        if self.skin.doing_less:
            arg1 = self.get_arg1_int(default=None)
            if arg1 is not None:

                raise NotImplementedError("Repeat Count {}".format(arg1))

    def keep_cursor_on_file(self):
        """Fail faster, like when some Bug shoves the Cursor off of Buffer of File"""

        row = self.row
        rows = self.count_rows_in_file()
        if not rows:
            row = 0
        elif row < 0:
            row = 0
        elif row >= rows:
            row = rows - 1

        column = self.column
        max_column = self.spot_max_column(row=row)
        if column < 0:
            column = 0
        elif column > max_column:
            column = max_column

        self.row = row
        self.column = column

    #
    # Take the Args as given, or substitute a Default Arg Value
    #

    def get_arg0_chars(self):
        """Get the Bytes of the Input Chords"""

        chords = self.skin.arg0_chords
        assert chords is not None

        chars = chords.decode(errors="surrogateescape")

        return chars

    def get_arg1_int(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        took = self.skin.arg1
        took_int = default if (took is None) else took

        self.skin.doing_less = False

        return took_int

    def get_arg2_chords(self):
        """Get the Bytes of the Suffix supplied after the Input Chords"""

        chords = self.skin.arg2_chords
        assert chords is not None

        return chords

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.skin.arg1' times"""

        assert self.skin.doing_more is None, self.skin.doing_more

        self.skin.doing_less = False
        self.skin.doing_more = True

    #
    # Keep hold of the one Reply to send out, & take input keyboard Chords in
    #

    def editor_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        message = " ".join(str(_) for _ in args)
        self.skin.reply.message = message

    def reply_with_finding(self):
        """Show Search Flags a la Bash Grep Switches"""

        letters = ""
        if not self.finding_regex:
            letters += "F"
        if not self.finding_case:
            letters += "i"
        if self.showing_line_number:
            letters += "n"

        flags = "-{}".format(letters) if letters else ""

        self.skin.reply.flags = flags

    def reply_with_nudge(self):
        """Capture the Nudge In to echo, as part of the next Reply Out"""

        self.skin.reply.nudge = self.skin.nudge

    def reply_with_bell(self):
        """Ring the Terminal Bell as part of the next Prompt"""

        self.skin.reply.bell = True

    def peek_editor_chord(self):
        """Reveal the next keyboard input Chord, or raise KeyboardInterrupt at ⌃"""

        chord_ints_ahead = self.skin.chord_ints_ahead
        painter = self.painter

        # Return a copy of the first deferred Chord

        if chord_ints_ahead:

            chord_int = chord_ints_ahead[0]  # copy, do Not consume
            chord = chr(chord_int).encode()

            if chord == b"\x03":  # ETX, ⌃C, 3

                raise KeyboardInterrupt()

            return chord

        # Give up now, if no input available

        if not self.driver.kbhit(timeout=0):

            return None

        # Consume the Chord and raise KeyboardInterrupt, if it is ETX, ⌃C, 3

        if self.showing_lag is None:
            self._keep_busy_(reply=self.skin.reply)  # give 1 Time Slice for this Chord

        chord = painter.take_painter_chord()
        if chord == b"\x03":  # ETX, ⌃C, 3

            raise KeyboardInterrupt()

        # Else defer this first keyboard input Chord for later, but return a copy now

        chord_int = ord(chord)
        chord_ints_ahead.insert(0, chord_int)

        return chord

    def take_editor_chord(self):
        """Block Self till next keyboard input Chord, or raise KeyboardInterrupt"""

        chord_ints_ahead = self.skin.chord_ints_ahead
        painter = self.painter

        # Consume the Reply

        reply_stale_chord = self.skin.reply

        self.skin.reply = TerminalReplyOut()
        self.reply_with_nudge()

        # Consume one deferred Chord and return it

        if chord_ints_ahead:

            chord_int = chord_ints_ahead.pop(0)  # consume, do Not copy
            chord = chr(chord_int).encode()

            if chord == b"\x03":  # ETX, ⌃C, 3

                raise KeyboardInterrupt()

            return chord

        # Block to take and return the next keyboard input Chord,
        # except do give >=1 Time Slices per Chord

        if self.showing_lag is None:
            while True:
                self._keep_busy_(reply=reply_stale_chord)
                if self.driver.kbhit(timeout=0.250):
                    break

        chord = painter.take_painter_chord()

        if chord == b"\x03":  # ETX, ⌃C, 3

            raise KeyboardInterrupt()

        return chord

    #
    # Focus on one Line of a File of Lines
    #

    def charsets_find_column(self, charsets):
        """Return the Index of the first CharSet containing Column Char, else -1"""

        chars = self.fetch_column_char(default=" ")

        for (index, charset) in enumerate(charsets):
            if chars in charset:

                return index

        return -1

    def count_columns_in_row(self, row=None):
        """Count Columns in Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_lines = self.ended_lines
        if not ended_lines:

            return 0

        if row_ >= len(ended_lines):

            raise IndexError(row)

        ended_line = ended_lines[row_]
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

        ended_line = self.ended_lines[row_] if self.ended_lines else _EOL_
        line = ended_line.splitlines()[0]

        return line

    def fetch_row_line_end(self, row=None):
        """Get the Line Ending of the Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_line = self.ended_lines[row_] if self.ended_lines else _EOL_
        line = ended_line.splitlines()[0]
        line_end = ended_line[len(line) :]

        return line_end

    def spot_bottom_row(self, top_row=None):
        """Spot the Bottom Row of File on Screen"""

        top_row_ = self.top_row if (top_row is None) else top_row
        painter = self.painter

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        bottom_row = top_row_ + (painter.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def spot_first_pin(self):
        """Spot the First Char of File, else as if it were a File of 1 Char"""

        first_pin = TerminalPin(0, column=0)

        return first_pin

    def spot_pin(self):
        """Spot the Char of File beneath the Cursor of File"""

        pin = TerminalPin(self.row, column=self.column)

        return pin

    def spot_pin_plus(self, obj):
        """Spot the Char of File beneath the Cursor of File"""

        pin_plus = TerminalPinPlus(self.row, column=self.column, obj=obj)

        return pin_plus

    def spot_last_pin(self):
        """Spot the last Char of File, else as if it were a File of 1 Char"""

        last_row = self.spot_last_row()
        last_column = self.spot_last_column()
        last_pin = TerminalPin(last_row, column=last_column)

        return last_pin

    def spot_last_row(self):
        """Find the last Row in File, else as if it were a File of 1 Char"""

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        return last_row

    def spot_max_column(self, row=None):
        """Spot the last Column in Row, else one beyond while inserting/ replacing"""

        if self.touching_beyond:
            max_column = self.count_columns_in_row(row=row)
        else:
            max_column = self.spot_last_column(row=row)

        return max_column

    def spot_last_column(self, row=None):
        """Find the last Column in Row, else as if it were a File of 1 Char"""

        row_ = self.row if (row is None) else row

        ended_lines = self.ended_lines
        if not ended_lines:

            return 0

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

        nudge = self.skin.nudge

        nudge_bytes = nudge.join_bytes()  # often same as 'self.skin.arg0_chords'

        nudge_escapes = ""
        for nudge_byte_int in nudge_bytes:
            nudge_escapes += r"\x{:02X}".format(nudge_byte_int)

        arg = "b'{}'".format(nudge_escapes)

        raise NameError(arg)

    def do_redraw(self):  # Vim ⌃L
        """Toggle between more and less Lag (vs Vim injects lots of Lag exactly once)"""

        lag_plus = self.get_arg1_int(default=None)
        lag = None if (lag_plus is None) else ((lag_plus - 1) / 1e6)
        lag = 0 if (lag == 0) else lag  # echo 0 as '0', not as '0.0'

        self.showing_lag = lag

        if lag is None:
            self.editor_print(":set no_lag_")
        else:
            self.editor_print(":set _lag_={}".format(lag))

        self._reopen_terminal_()  # for redraw

    def do_sig_tstp(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        painter = self.painter

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        painter.__exit__(*exc_info)
        os.kill(os.getpid(), signal.SIGTSTP)
        painter.__enter__()

    def do_sys_exit(self):  # Ex Return
        """Stop taking more Keyboard Input"""

        sys.exit()

    #
    # Find Spans of Chars
    #

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

        iobytespans = self.iobytespans

        iochars = self.held_file.decode()

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

            matches = list(re.finditer(pattern, string=iochars, flags=flags))
            iobytespans[::] = TerminalSpan.find_spans(matches)

            if matches:  # as many Spans as Matches, except for such as r"$" in "abc\n"
                assert iobytespans
                assert len(iobytespans) in (len(matches), len(matches) - 1)

    def print_some_found_spans(self, stale_status):
        """Print as many of the Found Spans as fit on screen"""

        ended_lines = self.ended_lines
        iobytespans = self.iobytespans
        keyboard = self.skin.keyboard
        painter = self.painter
        reply = self.skin.reply
        shadow = self.shadow
        showing_line_number = self.showing_line_number

        assert iobytespans

        last_line_number = 1 + len(ended_lines)
        str_last_line_number = "{:3} ".format(last_line_number)
        last_width = len(str_last_line_number)

        # Scroll up the Status Line

        painter.terminal_print()  # could reprint 'stale_status'

        # Visit each Span

        printed_row = None
        for span in iobytespans:

            (found_row, found_column, _) = span

            line_number = 1 + found_row
            str_line_number = ""  # TODO: merge with 'format_as_line_number'
            if showing_line_number:
                str_line_number = "{:3} ".format(line_number).rjust(last_width)

            line = self.fetch_row_line(row=found_row)

            # Print each Line of Spans only once

            if found_row != printed_row:
                printed_row = found_row

                painter.terminal_print(str_line_number + line)  # may wrap rows

        # Recover the Status Line destroyed by scrolling inside of 'terminal_print'

        if painter.terminal == shadow:
            if shadow.scroll > painter.scrolling_rows:
                assert shadow.row == painter.status_row
                assert shadow.column == 0

                painter.terminal_write_scrolled_status(
                    shadow.spot_pin(), status=stale_status
                )

        # Prompt for next keyboard input Chord, and block till it arrives

        self.editor_print(  # "{}/{} Press Return or ⌃C to continue . . .
            "{}/{} Press Return or ⌃C to continue . . .".format(
                len(iobytespans), len(iobytespans)
            )
        )

        fresh_status = keyboard.format_status_func(reply)

        painter.terminal_print(fresh_status, end=" ")
        self.driver.flush()

        try:
            _ = self.take_editor_chord()
        except KeyboardInterrupt:
            pass  # take ⌃C as Return here

        self._reopen_terminal_()  # after 'painter.terminal_print'

        # TODO: highlight Matches in :g/ Lines
        # TODO: Vim prints more through a Less-like Paginator

    def find_ahead_and_reply(self):
        """Find the Search Key ahead, else after start, else fail silently"""

        rep_line = self.format_finding_line()
        spans = self.iobytespans

        # Find none

        if not spans:
            self.editor_print("No chars found as:  {}".format(rep_line))

            return

        # Find one or more, ahead, else after start

        self.finding_highlights = True

        here0 = self.spot_pin()
        here1 = TerminalPin(row=-1, column=-1)  # before any Pin of File
        heres = (here0, here1)

        how0 = "{}/{}  Found {} chars ahead as:  {}"
        how1 = "{}/{}  Found {} chars after start, none found ahead, as:  {}"
        hows = (how0, how1)

        for (here, how) in zip(heres, hows):
            for (index, span) in enumerate(spans):
                len_chars = span.beyond - span.column
                there = self.span_to_pin_on_char(span)

                if here < there:

                    how_ = how
                    if there == here0:
                        how_ = "{}/{}  Found {} chars, only here, as {}"

                    self.editor_print(  # "{}/{}  Found ...
                        how_.format(1 + index, len(spans), len_chars, rep_line)
                    )

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def find_behind_and_reply(self):
        """Find the Search Key loudly: behind, else before end, else not"""

        rep_line = self.format_finding_line()
        rows = self.count_rows_in_file()
        spans = self.iobytespans

        # Find none

        if not spans:
            self.editor_print("No chars found as: {}".format(rep_line))

            return

        # Find one or more, behind, else before end

        self.finding_highlights = True

        here0 = self.spot_pin()
        here1 = TerminalPin(row=rows, column=0)  # after any Pin of File
        heres = (here0, here1)

        how0 = "{}/{}  Found {} chars behind as:  {}"
        how1 = "{}/{}  Found {} chars before end, none found behind, as:  {}"
        hows = (how0, how1)

        for (here, how) in zip(heres, hows):
            for (reverse_index, span) in enumerate(reversed(spans)):
                index = len(spans) - 1 - reverse_index
                len_chars = span.beyond - span.column
                there = self.span_to_pin_on_char(span)

                if there < here:

                    how_ = how
                    if there == here0:
                        how_ = "{}/{}  Found {} chars, only here, as:  {}"

                    self.editor_print(  # "{}/{}  Found ...
                        how_.format(1 + index, len(spans), len_chars, rep_line)
                    )

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def format_finding_line(self):
        """Echo the Search Key"""

        line = self.finding_line

        if self.finding_regex:
            rep_line = "r'{}'".format(line)
        elif self.finding_case:
            rep_line = repr(line)
        else:
            rep_line = line

        return rep_line

    def span_to_pin_on_char(self, span):
        """Find the Row:Column in Chars of File nearest to a Span"""

        there_row = span.row

        row_last_column = self.spot_last_column(row=there_row)
        there_column = min(row_last_column, span.column)

        there = TerminalPin(row=there_row, column=there_column)

        return there

    #
    # Replace Lines, replace Chars, insert Lines, insert Chars
    #

    def replace_some_chars(self, chars):
        """Replace some Chars inside a Line, or an empty Line"""

        ended_lines = self.ended_lines
        column = self.column
        row = self.row

        columns = self.count_columns_in_row()
        column_plus = column + 1

        # Fall back to insert the Fresh Char, if there is no Stale Char to delete

        if column >= columns:

            self.insert_some_chars(chars=chars)  # insert as fallen back from replacing

        # Delete one Char to insert one Char

        else:

            (head, _, ended_tail) = self.split_row_line_for_chars(chars)
            ended_lines[row] = head + chars + ended_tail[1:]

            self.column = column_plus

    def insert_some_chars(self, chars):
        """Insert some Chars inside a Line"""

        assert chars.splitlines()[0] == chars

        ended_lines = self.ended_lines
        column = self.column
        row = self.row

        (head, ended_head, ended_tail) = self.split_row_line_for_chars(chars)
        if not ended_lines:
            ended_lines[:] = [""]
        ended_lines[row] = head + chars + ended_tail

        self.column = column + 1

    def insert_one_line(self):
        """Insert an empty Line, and land the Cursor in it"""

        ended_lines = self.ended_lines
        row = self.row
        row_plus = row + 1

        (head, ended_head, ended_tail) = self.split_row_line_for_chars(chars=None)
        ended_lines[row] = ended_head
        ended_lines.insert(row_plus, ended_tail)

        self.row = row_plus
        self.column = 0

    def split_row_line_for_chars(self, chars):
        """Split this Line to insert or replace Char or Line, and remember where"""

        row = self.row
        column = self.column

        pin_plus = self.spot_pin_plus(chars)
        self.touching_pins.append(pin_plus)

        ended_line = self.ended_lines[row] if self.ended_lines else _EOL_
        columns = len(ended_line.splitlines()[0])
        line_end = ended_line[columns:]

        (head, ended_tail) = (ended_line[:column], ended_line[column:])
        ended_head = head + line_end

        return (head, ended_head, ended_tail)

    def format_touch_count(self):
        """Describe the list of Touched Pins"""

        pins = self.touching_pins

        if not pins:
            rep = "0 chars"
        else:

            line_pins = list(_ for _ in pins if _.obj is None)
            char_pins = list(_ for _ in pins if _.obj is not None)

            assert line_pins or char_pins

            if not line_pins:
                rep = "{} chars".format(len(pins))
            elif not char_pins:
                rep = "{} lines".format(len(pins))
            else:
                char_rows = len(set(_.row for _ in char_pins))
                if char_rows == 1:
                    rep = "{} chars in 1 line".format(len(char_pins))
                else:
                    rep = "{} chars across {} lines".format(len(char_pins), char_rows)

        return rep


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

        self.top_line_number = 1  # number the Scrolling Rows down from First of Screen
        self.last_line_number = 1  # number all Rows as wide as the Last Row of File
        self.painting_line_number = None  # number the Scrolling Rows visibly, or not

        # TODO: all = None in TerminalPainter.__init__

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        if self.rows is None:
            self.terminal.__enter__()
            self._reopen_terminal_()

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        if self.rows is not None:
            self.rows = None
            self.columns = None  # TODO: think into how much TerminalPainter to wipe

            self.terminal.__exit__(exc_type, exc_value, traceback)  # positional args

    def _reopen_terminal_(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        size = terminal._reopen_terminal_()  # a la os._reopen_terminal_(fd)

        (columns, rows) = (size.columns, size.lines)
        assert rows
        assert columns
        self.rows = rows
        self.columns = columns

        self.scrolling_rows = rows - 1  # reserve last 1 line for Status
        self.status_row = self.scrolling_rows

        return size

    def pdb_set_trace(self):
        """Visit Pdb, if Stdin is Tty, else raise 'bdb.BdbQuit'"""

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        self.__exit__(*exc_info)
        pdb.set_trace()
        self.__enter__()

    def flush_painter(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

    def take_painter_chord(self):
        """Block till TerminalDriver 'kbhit', to return next Keyboard Input"""

        chord = self.terminal.getch()

        return chord

    def terminal_print(self, *args, end="\r\n"):
        """Bypass the cache here:  Write line, slip to next, and scroll up if need be"""

        line = " ".join(str(_) for _ in args)
        self.terminal_write(line + end)

    def terminal_write(self, chars):
        """Bypass the cache here:  Write the Chars immediately, precisely as given"""

        self.terminal.write(chars)

    def terminal_write_scrolled_status(self, pin, status):
        """Repaint a copy of the Status Line, as if scrolled to top of Screen"""

        erased_line = self.columns * " "

        self.terminal_write(CUP_1_1)
        self.terminal_write(erased_line)

        self.terminal_write(CUP_1_1)
        self.terminal_write(status[: (self.columns - 1)])

        y = 1 + pin.row
        x = 1 + pin.column
        self.terminal_write(CUP_Y_X.format(y, x))

    def paint_screen(self, ended_lines, spans, status, cursor, bell):
        """Write over the Rows of Chars on Screen"""

        (row, column) = self.spot_nearby_cursor(cursor.row, column=cursor.column)

        columns = self.columns
        scrolling_rows = self.scrolling_rows
        terminal = self.terminal

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
            (styled, line_plus) = self.style_line(
                index, line=line, cursor=cursor, spans=spans
            )
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

        y = 1 + row
        x = 1 + column
        terminal.write(CUP_Y_X.format(y, x))

        # Ring the bell

        if bell:
            terminal.write("\a")

    def spot_nearby_cursor(self, row, column):
        """Choose a Row:Column to stand for a Row:Column on or off Screen"""

        columns = self.columns
        scrolling_rows = self.scrolling_rows
        rows = self.rows

        assert rows
        assert columns

        found_row = min(rows - 1, row)

        left_column = self.spot_left_column() if (row < scrolling_rows) else 0
        found_column = min(columns - 1, left_column + column)

        return (found_row, found_column)

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

    def style_line(self, row, line, cursor, spans):
        """Inject kinds of SGR so as to style the Chars of a Row"""

        # Work only inside this Row

        (spans0, line_plus) = self.spread_spans(row, line=line, spans=spans)

        # Add a one Char Span at the Cursor

        spans1 = list(spans0)
        if False:
            if row == cursor.row:
                cursor_span = TerminalSpan(
                    row=cursor.row, column=cursor.column, beyond=(cursor.column + 1)
                )
                spans1.append(cursor_span)
                spans1.sort()

        # Add one Empty Span beyond the end

        beyond = len(line_plus)
        empty_beyond_span = TerminalSpan(row, column=beyond, beyond=beyond)

        spans2 = list(spans1)
        spans2.append(empty_beyond_span)

        # Visit the Chars between each pair of Spans, and the Chars of the Spans

        visited = 0
        opened = False

        styled = ""
        for span in spans2:

            # Write the Chars before this Span, as Highlight never opened or as closed

            if visited < span.column:

                fragment = line_plus[visited : span.column]

                styled += _LIT_CLOSE_ if opened else ""
                styled += fragment

                opened = False
                visited = span.column

            # Write the Chars of this Span, as Highlight opened

            if span.column < span.beyond:

                fragment = line_plus[span.column : span.beyond]

                styled += "" if opened else _LIT_OPEN_
                styled += fragment

                opened = True
                visited = span.beyond

        # Close the last opened Highlight, if it exists

        styled += _LIT_CLOSE_ if opened else ""

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

        self.rows = None  # count Rows on Screen
        self.columns = None  # count Columns per Row

        self.row = None  # place the Cursor in a Row of Screen, at Flush
        self.column = None  # place the Cursor in a Column of Screen, at Flush
        self.enter_cursor_style_chars = None  # change the Cursor Shape, at Enter
        self.exit_cursor_style_chars = None  # change the Cursor Shape, at Exit
        self.writing_bell_chars = None  # ring the Bell, at next Flush

        self.flushed_lines = list()  # don't rewrite Lines unchanged since last Flush
        self.held_lines = list()  # collect the Lines to rewrite at next Flush

        self.scroll = None  # count Terminal Lines scrolled by Writes

        # TODO: all = None in TerminalShadow.__init__

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        enter_cursor_style_chars = self.enter_cursor_style_chars
        rows = self.rows
        terminal = self.terminal

        if rows is None:

            terminal.__enter__()
            self._reopen_terminal_()

            if enter_cursor_style_chars:
                terminal.write(enter_cursor_style_chars)

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        exit_cursor_style_chars = self.exit_cursor_style_chars
        rows = self.rows
        terminal = self.terminal

        if rows is not None:

            if exit_cursor_style_chars:
                terminal.write(exit_cursor_style_chars)

            self.rows = None
            self.columns = None  # TODO: think into how much TerminalShadow to wipe

            terminal.__exit__(exc_type, exc_value, traceback)  # positional args

    def _reopen_terminal_(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        # Count Rows x Columns below

        size = terminal._reopen_terminal_()
        (columns, rows) = (size.columns, size.lines)

        # Size this Terminal to match the Terminal Below

        assert rows >= 1
        assert columns >= 1
        self.rows = rows
        self.columns = columns

        # Clear the Terminal Caches below

        terminal.write(ED_2)
        terminal.write(CUP_1_1)
        terminal.flush()

        # Clear the Terminal Cache here

        self.flushed_lines[::] = rows * [None]
        self.writing_bell_chars = None

        self.write(ED_2)
        self.write(CUP_1_1)

        self.scroll = 0

        return size

        # TODO: ugly to have enter_cursor_style_chars/ exit_cursor_style_chars endure?

        # TODO: deal with $LINES, $COLUMNS, and fallback,
        # TODO: like 'shutil.get_terminal_size' would

    def spot_pin(self):
        """Point to the Cursor on Screen"""

        pin = TerminalPin(self.row, column=self.column)

        return pin

    def flush(self):
        """Stop waiting for more Writes from above"""

        columns = self.columns
        enter_cursor_style_chars = self.enter_cursor_style_chars
        exit_cursor_style_chars = self.exit_cursor_style_chars
        flushed_lines = self.flushed_lines
        held_lines = self.held_lines
        rows = self.rows
        terminal = self.terminal
        writing_bell_chars = self.writing_bell_chars

        erased_line = columns * " "
        bottom_row = rows - 1

        # Visit each row, top down

        assert len(held_lines) == rows, (len(held_lines), rows)  # flush after ED_2

        terminal.write(CUP_1_1)

        for (row, held_line) in enumerate(held_lines):
            flushable_line = "\r\n" if (held_line is None) else held_line

            # If row written differently

            flushed_line = flushed_lines[row]
            if flushed_line != flushable_line:
                if row < bottom_row:

                    # Write a Scrolling Row above the Bottom Row

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(erased_line)

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(flushable_line.rstrip())

                else:

                    # Write the Bottom Row, but without closing it
                    # and without writing its Last Column

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(erased_line[:-1])

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(flushable_line.rstrip())

                # Remember this Write, as if all Columns written

                flushed_lines[row] = flushable_line

        # Clear the Terminal Cache of Lines to write

        held_lines[::] = list()

        # Place the Terminal Cursor, and sometimes change the Cursor's Shape

        self.terminal_write_cursor_order(self.row, column=self.column)

        if enter_cursor_style_chars and not exit_cursor_style_chars:
            self.exit_cursor_style_chars = DECSCUSR

            terminal.write(enter_cursor_style_chars)

        # Ring the Terminal Bell below

        if writing_bell_chars:
            self.writing_bell_chars = None

            terminal.write(writing_bell_chars)

        # Flush the Terminal Writes below

        terminal.flush()

    def terminal_write_cursor_order(self, row, column):
        """Position the Terminal Cursor below, without telling this Shadow"""

        terminal = self.terminal

        y = 1 + row
        x = 1 + column
        terminal.write(CUP_Y_X.format(y, x))

    def getch(self):
        """Block till next keyboard input Chord"""

        chord = self.terminal.getch()

        return chord

    def write(self, chars):
        """Write into the Shadow now, write the Terminal Below at next Flush"""

        held_lines = self.held_lines
        column = self.column
        columns = self.columns
        rows = self.rows
        terminal = self.terminal

        row_ = self.row

        # Flush through the Write of anything but ED_2 after Flush before ED_2
        # TODO: Shadow Literals written after ED_2 to Flush at GetCh

        writer = TerminalWriter(chars)
        orders = writer.orders

        writing_ed_2 = False
        if len(orders) == 1:
            order = orders[-1]
            if order.csi_plus == ED_2:
                writing_ed_2 = True

        if not held_lines and not writing_ed_2:
            terminal.write(chars)
            terminal.flush()

        # Hold the Write of one or more Literals from Erase Display to Flush

        if held_lines:

            if column == columns:

                (row_, column_) = self.find_step_ahead()
                self.write_cursor_order(row=row_, column=column_)

            if any(_.literals for _ in orders):

                assert len(held_lines) == rows, (len(held_lines), row_)
                assert row_ < len(held_lines), (row_, chars)

                held_line = held_lines[row_]
                assert held_line is None, (row_, held_line, chars)

                held_lines[row_] = chars

        # Write the Orders into the Shadow Cursor

        self.write_some_orders(orders)

    def write_some_orders(self, orders):
        """Write the Orders into the Shadow Cursor"""

        columns = self.columns

        for order in orders:

            # Accept CR LF beyond the last Column, but nothing else

            if self.column == columns:
                self.write_beyond_row_order()
                if order.controls == "\r\n":

                    continue

            # Write whichever kind of order

            if order.csi_plus:
                self.write_csi_plus_order(order)
            elif order.escape_plus:
                self.write_escape_plus_order(order)
            elif order.controls:
                self.write_controls_order(order)
            elif order.literals:
                self.write_literals_order(order)
            else:
                assert False, order  # unreached

    def write_beyond_row_order(self):
        """Wrap into next Row, to accept Write past Last Column"""

        (row, column) = self.find_step_ahead()

        self.write_cursor_order(row, column=column)

    def write_csi_plus_order(self, order):
        """Write one CSI Order into the Shadow Cursor"""

        held_lines = self.held_lines
        rows = self.rows

        if order.csi_plus == ED_2:
            held_lines[::] = rows * [None]
            self.write_cursor_order(row=None, column=None)

        elif order.csi_plus == CUP_1_1:
            self.write_cursor_order(row=0, column=0)

        elif order.a == CUP_Y_X[-1] == "H":  # may move the Cursor past Last Column
            self.write_cursor_order(row=(order.int_y - 1), column=(order.int_x - 1))

        elif order.a == SGR_N[-1] == "m":

            if order.x is None:
                if order.int_y in (None, 7):

                    return  # TODO: learn to shadow SGR_N, more than its Cursor movement

            raise NotImplementedError(order)

        elif order.a == DECSCUSR_N[-2:] == " q":

            if order.x is None:
                if order.int_y in (2, 4, 6):

                    self.enter_cursor_style_chars = DECSCUSR_N.format(order.int_y)
                    self.exit_cursor_style_chars = None  # till after writing DECSCUSR_N

                    return

            raise NotImplementedError(order)

        else:

            raise NotImplementedError(order)

    def write_escape_plus_order(self, order):
        """Write one Escape Order into the Shadow Cursor"""

        raise NotImplementedError(order)

    def write_controls_order(self, order):
        """Write one Controls Order into the Shadow Cursor"""

        row = self.row

        if order.controls == "\a":
            self.writing_bell_chars = "\a"

        elif order.controls == "\r":
            self.write_cursor_order(row, column=0)

        elif order.controls == "\r\n":  # "\r\n" past last Column don't come here
            self.write_beyond_row_order()

        else:

            raise NotImplementedError(order)

    def write_literals_order(self, order):
        """Write one Literals Order into the Shadow Cursor"""

        (row, column) = self.find_slip_ahead(slips=len(order.literals))

        self.write_cursor_order(row, column=column)

    def write_cursor_order(self, row, column):
        """Place the Shadow Cursor, but never out of bounds"""

        columns = self.columns
        rows = self.rows

        # Assert Row:Column on Screen, or just past the Last Column of a Row

        if row is not None:
            assert 0 <= row < rows, (row, rows)

        if column is not None:
            assert 0 <= column <= columns, (column, columns)

        # Move the Shadow Cursor

        self.row = row
        self.column = column

    def find_slip_ahead(self, slips):
        """Scroll up the Rows when given an Order before or up to the Lower Right"""

        rows = self.rows
        columns = self.columns

        # Scroll as needed to slip ahead,
        # but accept landing one Column past the Lower Right

        row_ = self.row
        column_ = self.column

        column_ += slips

        while column_ > columns:
            column_ -= columns
            if row_ < (rows - 1):
                row_ += 1
            else:
                self.scroll += 1

        return (row_, column_)

    def find_step_ahead(self):
        """Scroll up the Rows when given an Order past the Lower Right"""

        rows = self.rows

        column_ = self.column
        row_ = self.row

        column_ = 0
        if row_ < rows - 1:
            row_ += 1
        else:
            self.scroll += 1

        return (row_, column_)

    # TODO: Add API to write Scroll CSI in place of rewriting Screen to Scroll
    # TODO: Reduce writes to Chars needed, smaller than whole Lines needed


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

    def __init__(self, stdio):

        self.stdio = stdio

        self.fd = self.stdio.fileno()
        self.with_termios = None
        self.inputs = None

        self.lag = None

    def __enter__(self):
        """Switch Screen to XTerm Alt Screen and take single Chords from Keyboard"""

        fd = self.fd

        self.stdio.flush()

        if self.stdio.isatty():

            self.with_termios = termios.tcgetattr(fd)
            tty.setraw(fd, when=termios.TCSADRAIN)  # not TCSAFLUSH

            self.stdio.write(_CURSES_INITSCR_)
            self.stdio.flush()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        _ = (exc_type, exc_value, traceback)

        self.stdio.flush()

        attributes = self.with_termios
        if attributes:
            self.with_termios = None

            self.stdio.write(_CURSES_ENDWIN_)
            self.stdio.flush()

            fd = self.fd
            when = termios.TCSADRAIN
            termios.tcsetattr(fd, when, attributes)

    def _reopen_terminal_(self):
        """Do nothing much, when running TerminalDriver in place of TerminalShadow"""

        size = os.get_terminal_size(self.fd)

        return size

        # TODO: resolve the clash between no 'flush' here while named as 'reopen'

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.stdio.flush()

    def get_terminal_size(self):
        """Get a (Columns, Lines) Terminal Size, a la 'os.get_terminal_size'"""

        size = os.get_terminal_size(self.fd)

        return size

    def kbhit(self, timeout):
        """Wait till next Keystroke, or next burst of Paste pasted"""

        if self.inputs:

            return True

        rlist = [self.stdio]
        wlist = list()
        xlist = list()
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_) = selected

        if rlist_ == rlist:

            return True

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

        stdin = os.read(self.stdio.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while Line not closed
        # Trust no multibyte char encoding contains b"\r" or b"\n" (as per UTF-8)

        calls = 1
        while stdin and (b"\r" not in stdin) and (b"\n" not in stdin):

            if self.with_termios:
                if not self.kbhit(timeout=0):
                    break

            more = os.read(self.stdio.fileno(), 1)
            if not more:
                assert not self.with_termios
                break

            stdin += more
            calls += 1

        assert calls <= len(stdin) if self.with_termios else (len(stdin) + 1)

        return stdin

    def write(self, chars):
        """Compare with Chars at Cursor, write Diffs now, move Cursor soon"""

        self.stdio.write(chars)

        if self.lag:
            time.sleep(self.lag)


def repr_vi_nudge_bytes(iobytes):
    """Echo keyboard input without asking people to memorise b'\a\b\t\n\v\f\r'"""

    rep = ""
    for iobyte_int in iobytes:
        ch = chr(iobyte_int)
        iobyte = ch.encode()

        if iobyte_int == 9:
            # rep += " ⇥"  # ⇥ \u21E5 Rightward Arrows to Bar
            rep += " Tab"
        elif iobyte_int == 13:
            # rep += " ⏎"  # ⏎ \u23CE Return Symbol
            rep += " Return"
        elif iobyte_int == 27:
            # rep += " ⎋"  # ⎋ \u238B Broken Circle With Northwest Arrow
            # rep += " Escape"
            rep += " Esc"
        elif iobyte_int == 127:
            # rep += " ⌫"  # ⌫ \u232B Erase To The Left
            rep += " Delete"

        elif ch == " ":
            # rep += " ␢"  # ␢ \u2422 Blank Symbol
            # rep += " ␣"  # ␣ \u2423 Open Box
            rep += " Space"

        elif iobyte in C0_CONTROL_STDINS:  # iobyte_int in 0x00..0x1F,0x7F
            rep += " ⌃" + chr(iobyte_int ^ 0x40)

        elif rep and (rep[-1] in "0123456789") and (ch in "0123456789"):
            rep += ch  # no Space between Digits in Prefix or Chords or Suffix

        else:  # default to echo each Chord as one Space and one Glyph
            rep += " " + ch

    rep = rep.replace("Esc [ A", "Up")  # ↑ \u2191 Upwards Arrow
    rep = rep.replace("Esc [ B", "Down")  # ↓ \u2193 Downwards Arrow
    rep = rep.replace("Esc [ C", "Right")  # → \u2192 Rightwards Arrow
    rep = rep.replace("Esc [ D", "Left")  # ← \u2190 Leftwards Arrows

    rep = rep.strip()

    return rep  # such as '⌃L' at FF, ⌃L, 12, '\f'


#
# Track how to configure Vim to feel like Vi Py,
# especially after backing up or removing your history at:  -rw------- ~/.viminfo
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


# Cite some Terminal Doc's and Git-track experience of Terminal Output magic
#
#       https://en.wikipedia.org/wiki/ANSI_escape_code
#           SGR (Select Graphic Rendition) parameters
#
#               "m"     Reset, Normal
#               "1m"    Bold, Increased Intensity
#               "2m"    Faint, Decreased Intensity, Dim  <-- Replace
#               "3m"    Italic
#               "4m"    Underline
#               "5m"    Slow Blink
#               "6m"    Rapid Blink  # ignored by Mac Terminal
#               "7m"    Reverse Video, Invert  # overriden by default Cursor
#               "8m"    Conceal, Hide
#               "9m"    Crossed-out, Strike  # ignored by Mac Terminal
#
#       https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
#           CSI Pm m  Character Attributes (SGR)
#           CSI Ps SP q  Set Cursor Style (DECSCUSR), VT520
#
#               " q"    Reset, Normal (but doc'ed poorly)
#               "1 q"   Blinking Block (like after Screen still for 2s)
#               "2 q"   Steady Block (same as default of Mac Terminal)
#               "3 q"   Blinking Underline
#               "4 q"   Steady Underline
#               "5 q"   Blinking Bar
#               "6 q"   Steady Bar
#


#
# Track ideas of future work
#


# TODO: search the Sourcelines above here a la :g/FIXME
# TODO: search the Sourcelines above here a la :g/TODO\|FIXME


# -- bugs --

# FIXME:  vim.py --pwnme should quit like --version does
# FIXME:  vim.py --pwnme/--version +vi should be the way to stay open

# TODO:  find more bugs


# -- future inventions --


# TODO: Delete after Replaces as undo Replaces, inside the R mode
# TODO: code Repeat Count for the a i o A I O variations of Insert
# TODO: cancel Insert Repeat Count if moved away while inserting


# TODO: ⌃O for Search Key input, not just Insert/ Replace input


# TODO: something akin to Vim :set cursorline, :set nocursorline
# TODO: Vim V V to highlight the Line at the Cursor
# TODO: Vim ⌃V for feeding into :!|pbcopy
# TODO: Vim ! default into :!|pbcopy


# TODO: QR to draw with a Logo Turtle till QR,
# TODO: infinite Spaces per Row, rstrip at exit, moving relative not absolute
# TODO: 1234567890 Up Down Left Right, initially headed Up with |
# TODO: | - =| =- to draw a rectangle, |=-=|=- to draw a square
# TODO: [ ] for macro repetition
# TODO: escape to complete unabbreviated Logo:  Repeat 4 [ Forward 10 Right 90 ]
# TODO: escape to complete abbreviated Logo:  Rep 4 [ Fd 10 Rt 90 ]
# TODO: contrast with default Emacs Picture Modes |-/\+ ...


# TODO: stop passing through Controls from the File
# TODO: test hard Tabs in File
# TODO: solve /⌃V⌃IReturn
# TODO: accept b"\t" Hard Tabs as a form of b" " Space
# TODO: show the first ~ past the end differently when No End for Last Line
# TODO: revive the last Match of r"$" out there
# TODO: show, delete, and insert the Eol of the last line
# TODO: test Eol encodings of b"\r\n" and b"\r", apart from b"\n" in File
# TODO: test chars outside  and far outside the basic "\u0000".."\u00FF" in File
# TODO: test SurrogateEscape's in File


# TODO: radically simplified undo:  3u to rollback 3 keystrokes
# TODO: radically simplified undo:  u to explain radically simplified undo


# TODO: save/load to/from local Os CopyPaste Buffer, like via Mac pbpaste/pbcopy


# -- future improvements --

# TODO: test inception of i⌃O inside R⌃O etc

# TODO: record and replay tests of:  cat bin/vi.py |vi.py - bin/vi.py

# TODO: recover :g/ Status when ⌃L has given us :set _lag_ of >1 Screen of Hits

# TODO: name errors for undefined keys inside Ex of / ? etc

# TODO: Vim \ n somehow doesn't disrupt the 'keep_up_vi_column_seek' of $


# -- future features --

# TODO: choose which Controls to allow through I mode
# TODO: choose which Controls to allow through R mode
# TODO: mix together TerminalKeyboardViInsert/ TerminalKeyboardViReplace

# TODO: ⌃I ⌃O walk the Jump List of ' ` G / ? n N % ( ) [[ ]] { } L M H :s :tag :n etc
# TODO: despite Doc, to match Vim, include in the Jump List the * # forms of / ?

# TODO: mm '' `` pins
# TODO: qqq @q  => record input, replay input

# TODO: :! for like :!echo $(whoami)@$(hostname):$(pwd)/
# TODO: accept more chords and DEL and ⌃U after : till \r
# TODO: accept :123\r, but suggest 123G etc
# TODO: accept :noh\r and :set ignorecase and so on, but suggest \i etc

# TODO: toggled :set wrap, :set nowrap
# TODO: ⌃D ⌃U scrolling
# TODO: ⌃V o  => rectangular: opposite

# TODO: code :r to try read files by name, pass and fail
# TODO: code :w to try write files by name, pass and fail

# TODO: ls |bin/vi.py +3 -  # start on chosen line
# TODO: ls |bin/vi.py +/Makefile -  # start on found line


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
