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
  ls |bin/vi.py -  # to quit, strike the two keyboard chords Z Q
"""

import argparse
import difflib
import inspect
import os
import select
import sys
import termios
import tty


# Name Terminal Output magic

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


# Name Terminal Input magic

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
    chars = iobytearray.decode(errors="surrogateescape")
    lines = chars.splitlines()

    with TerminalEditor() as editor:
        shadow = editor.shadow

        while not editor.quitting:

            shadow.redraw(lines, first=0)
            ch = editor.getch()

            if ch == b'G':
                shadow.cursor_row = len(lines[:-1])

                continue

            if ch == b'0':
                y = shadow.cursor_row
                x = len("  1 ")
                shadow.cursor_column = x

                continue

            if ch == b'$':
                y = shadow.cursor_row
                x = len("  1 ") + len(lines[y][:-1])
                shadow.cursor_column = x

                continue

            if ch == b'Z':

                shadow.redraw(lines, first=0)
                ch = editor.getch()

                if ch == b'Q':
                    editor.quitting = True

                    continue

            editor.tty.write("\a")
            editor.tty.flush()

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


class TerminalShadow:
    """Write through to the Terminal, but keep a copy"""

    def __init__(self, tty):

        self.tty = tty

        fd = tty.fileno()
        self.fdtty = fd

        tty_size = os.get_terminal_size(fd)
        self.rows = tty_size.lines
        self.columns = tty_size.columns

        self.status = ""

        self.cursor_row = 0
        self.cursor_column = len("  1 ")

    def redraw(self, lines, first):
        """Write over the Rows of Chars"""

        tty = self.tty
        rows = self.rows
        columns = self.columns
        str_status = str(self.status)

        # Choose chars to display

        visibles = lines[first:][:(rows - 1)]
        texts = list(visibles)

        for (index, text) in enumerate(texts):
            texts[index] = text[:columns]
        while len(texts) < (rows - 1):
            texts.append("~")
        if texts and (len(texts[-1]) >= columns):
            texts[-1] = texts[-1][:-1]  # TODO: test writes of Lower Right Corner

        for (index, text) in enumerate(texts[:len(visibles)]):
            texts[index] = "{:3} ".format(1 + index) + text

        # Display the chosen chars

        tty.write(CUP_1_1)
        for (index, text) in enumerate(texts):
            tty.write(text + "\n\r")

        tty.write(str_status.ljust(columns - 1))

        y = 1 + self.cursor_row
        x = 1 + self.cursor_column
        tty.write(CUP_Y_X.format(y, x))

        tty.flush()


class TerminalEditor:
    r"""
    Emulate a glass teletype at Stdio, such as the 1978 DEC VT100 Video Terminal

    Wrap "tty.setraw" to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc as themselves,
    not as SIGINT SIGINFO SIGQUIT etc

    Compare Bash "bind -p", Zsh "bindkey", Bash "stty -a", and Unicode-Org U0000.pdf
    """

    def __init__(self):

        self.tty = None
        self.fdtty = None
        self.with_termios = None

        self.shadow = None
        self.inputs = None

        self.quitting = None

    def __enter__(self):

        self.tty = sys.stderr

        self.tty.flush()

        if self.tty.isatty():

            self.fdtty = self.tty.fileno()
            self.with_termios = termios.tcgetattr(self.fdtty)
            tty.setraw(self.fdtty, when=termios.TCSADRAIN)  # not TCSAFLUSH

            self.tty.write(_CURSES_INITSCR_)
            self.tty.flush()

            self.shadow = TerminalShadow(tty=self.tty)

        return self

    def __exit__(self, *exc_info):

        (_, exc, _) = exc_info

        self.tty.flush()

        if self.with_termios:

            self.tty.write(_CURSES_ENDWIN_)
            self.tty.flush()

            when = termios.TCSADRAIN
            attributes = self.with_termios
            termios.tcsetattr(self.fdtty, when, attributes)

    def getch(self):
        """Block to fetch next char of paste, next keystroke, or empty end-of-input"""

        # Block to fetch next keystroke, if no paste already queued

        inputs = "" if (self.inputs is None) else self.inputs
        if not inputs:

            stdin = self._pull_stdin()

            if len(stdin) <= 1:

                return stdin

            inputs = stdin.decode()

        # Pick an Esc [ X sequence apart from more paste

        if len(inputs) >= 3:
            if inputs[:2] == (ESC_CHAR + "["):

                stdin = inputs[:3].encode()
                self.inputs = inputs[3:]

                return stdin

        # Fetch next char of paste
        # such as ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑  # Control Option Alt Shift Command, Left Right Down Up Arrows

        stdin = inputs[:1].encode()
        self.inputs = inputs[1:]

        return stdin

    def _pull_stdin(self):
        """Pull a burst of paste, else one slow single keystroke, else empty at Eof"""

        # Block to fetch one more byte (or fetch no bytes at end of input when Stdin is not Tty)

        stdin = os.read(self.tty.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while line not closed, if Stdin is or is not Tty
        # Trust no multibyte character encoding contains b"\r" or b"\n", as is true for UTF-8
        # (Solving the case of this trust violated will never be worthwhile?)

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

        if False:  # FIXME: configure logging
            with open("trace.txt", mode="a") as appending:
                appending.write("read._pull_stdin: {} {}\n".format(calls, repr(stdin)))

        return stdin

    def kbhit(self):
        """Wait till next key struck, or a burst of paste pasted"""

        rlist = [self.tty]
        wlist = list()
        xlist = list()
        timeout = 0
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_) = selected

        if rlist_ == rlist:
            return True

    def putch(self, chars):
        """Print one or more decoded Basic Latin character or decode C0 Control code"""

        for ch in chars:
            self.shadow.putch(ch)
            if self.with_termios:
                self.tty.write(ch)

        self.tty.flush()

    def _insert_chars(self, chars):
        """Add chars to the shline"""

        for ch in chars:

            stdin = ch.encode()
            caret_echo = "^{}".format(chr(stdin[0] ^ X40_CONTROL_MASK))
            echo = caret_echo if (stdin in C0_CONTROL_STDINS) else ch

            self.chars.append(ch)
            self.echoes.append(echo)

            self.putch(echo)

    def _calc_bots_by_stdin(self):
        """Enlist some bots to serve many kinds of keystrokes"""

        bots_by_stdin = dict()

        bots_by_stdin[None] = self._insert_stdin

        bots_by_stdin[b""] = self._end_input

        bots_by_stdin[b"\x03"] = self._raise_keyboard_interrupt  # ETX, aka ⌃C, aka 3
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

        bots_by_stdin[b"\x1B[A"] = self._previous_history  # ↑ Up Arrow
        bots_by_stdin[b"\x1B[B"] = self._next_history  # ↓ Down Arrow
        # bots_by_stdin[b"\x1B[C"] = self._forward_char  # ↑ Left Arrow
        # bots_by_stdin[b"\x1B[D"] = self._backward_char  # ↑ Right Arrow

        return bots_by_stdin

    def _join_shline(self):
        """Catenate the chars of the shline, on demand"""

        shline = "".join(self.chars)

        return shline

    def _drop_char(self, stdin):  # aka Stty "erase", aka Bind "backward-delete-char"
        """Undo just the last insert of one char, no matter how it echoed out"""

        if not self.echoes:
            return

        echo = self.echoes[-1]

        width = len(echo)
        backing = width * "\b"
        blanking = width * " "

        self.echoes = self.echoes[:-1]
        self.chars = self.chars[:-1]
        self.putch(f"{backing}{blanking}{backing}")

    def _drop_line(self, stdin):  # aka Stty "kill" many, aka Bind "unix-line-discard"
        """Undo all the inserts of chars since the start of line"""

        if not self.echoes:
            self._ring_bell(stdin)
            return

        while self.echoes:
            self._drop_char(stdin)

    def _drop_next_char(self, stdin):
        """End the input if line empty, else drop the next char, else ring bell"""

        if not self.chars:
            return self._end_input(stdin)

        pass  # FIXME: code up the ← Left Arrow, to make drop-next-char possible

        self._ring_bell(stdin)

    def _drop_word(self, stdin):  # aka Stty "werase" many, aka Bind "unix-word-rubout"
        """Undo all the inserts of chars since the start of the last word"""

        if not self.echoes:
            self._ring_bell(stdin)
            return

        while self.echoes and self.echoes[-1] == " ":
            self._drop_char(stdin)

        while self.echoes and self.echoes[-1] != " ":
            self._drop_char(stdin)

    def _end_input(self, stdin):
        """End the input and the shline"""

        if not self.echoes:
            self.putch("^D")  # FIXME: second of two "^D"

        self.putch("\r\n")

        quitting = ""  # not "\n" there
        return quitting

    def _end_line(self, stdin):
        """End the shline"""

        self.putch("\r\n")  # echo ending the shline

        quitting = "\n"
        return quitting

    def _insert_stdin(self, stdin):  # aka Bash "bind -p | grep self-insert"
        """Add the codepoint of the keystroke"""

        ch = stdin.decode()
        self._insert_chars(ch)

    def _log_stdin(self, stdin):
        """Disclose the encoding of a meaningless keystroke"""

        echoable = "".join("<{}>".format(codepoint) for codepoint in stdin)
        self.echoes.append(echoable)
        self.putch(echoable)

    def _next_history(self, stdin):
        """Step forward in time, but skip over blank lines, except at ends of history"""

        stepped = False
        while self.lines:

            new_shline = self.lines[-1]
            self.lines = self.lines[:-1]

            self._drop_line(stdin)
            self._insert_chars(new_shline)  # FIXME: insert only last next choice
            stepped = True

            if new_shline.strip():
                return

        if not stepped:
            self._ring_bell(stdin)

    def _quoted_insert(self, stdin):
        """Add any one keystroke to the shline"""

        next_stdin = self.getch()  # such as the b"\x1B[A" ↑ Up Arrow
        next_char = next_stdin.decode()
        self._insert_chars(next_char)

    def _raise_keyboard_interrupt(self, stdin):  # aka Stty "intr" SIGINT
        """Raise KeyboardInterrupt"""

        raise KeyboardInterrupt()  # FIXME: also SIGINFO, SIGUSR1, SIGSUSP, SIGQUIT

    def _reprint(self, stdin):
        """Restart the edit of this line"""

        self.putch("^R\r\n")  # strike this one out, open up another
        self.putch("".join(self.echoes))  # echo as if inserting each char of this line

    def _ring_bell(self, stdin):
        """Ring the Terminal bell"""

        self.putch("\a")


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
