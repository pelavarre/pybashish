#!/usr/bin/env python3

r"""
usage: read.py [-h] [-e] [-p PROMPT] [-r] [-s] [--splat [SPLAT]] [--lines]

read one line of standard input, and print it

optional arguments:
  -h, --help       show this help message and exit
  -e               let people edit input and history
  -p PROMPT        chars to print out before reading input (default: "? ")
  -r               don't delete pairs of \ and \n that end lines
  -s               just edit input, don't echo input
  --splat [SPLAT]  chars to echo in place of input (default: "*")
  --lines          keep on reading till EOF (such as Terminal Control+D)

quirks:
  prompts with "? ", unlike the "" of Bash "read" with no "-p PROMPT"
  prompts and echoes, even when Stdin is not Tty, unlike Bash
  lets people edit input and history, like Bash "read -e" (missing from Dash) or Zsh "vared"
  defines ↑ ↓ up/down history review to skip over blank lines, like Zsh
  undoes edits of input and history at Return or ⌃C, like Zsh
  keeps blank lines in history, like Bash for non-empty blank lines (unstable feature?)
  doesn't stuff the line into a Bash Environment Variable (unlike Dash requiring var)
  prints the received line as a Python Repr

examples:
  echo '⌃ ⌥ ⇧ ⌘ ← → ↓ ↑' | read.py  # Control Option Shift Command Arrows at Mac
  echo 'å é î ø ü' | read.py  # the accented vowels prominent in Mac ⌥ Option
  echo '⋮' | read.py  # more favorite characters of mine
  read.py
  read.py --lines
  read -e  # in Bash
  FOO=123; vared -e FOO  # in Zsh
"""

# FIXME: compare vs "script" runs of Bash show a ^D at EOF in their "typescript" file

# FIXME: read.py --file  # invite lots of paste, capture it to file

# FIXME: somehow bookmark permutations '⌘ ⇧⌘ ⇧ ⌥⇧ ⌥⇧⌘ ⌥⌘ ⌥ ⌃⌥ ⌃⌥⌘ ⌃⌥⇧⌘ ⌃⌥⇧ ⌃⇧ ⌃⇧⌘ ⌃⌘ ⌃'
# FIXME FIXME: bind an undo key such as ⌃_
# FIXME FIXME:  stop discarding history edits at ⌃N "_next_history"
# FIXME: add -t TIMEOUT in seconds


from __future__ import print_function

import contextlib
import os
import select
import sys
import termios
import tty

import argdoc


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

    args = _parse_read_argv(argv)

    if args.lines:  # do prompt for ⌃D EOF, even when Stdin is not Tty
        stderr_print("Press ⌃D EOF to quit")

    whole = ""
    while True:

        shline = None
        try:
            with GlassTeletype(
                editing=args.e, silencing=args.s, splatter=args.splatter
            ) as gt:
                shline = gt.readline(args.prompting)
        except KeyboardInterrupt:
            pass  # trust GlassTeletype to log KeyboardInterrupt well

        if shline:
            whole += shline

        continuation = "\\\n"
        if shline and whole.endswith(continuation) and not args.r:
            whole = whole[: -len(continuation)]
            continue

        print(repr(whole))
        whole = ""

        if shline == "":  # continue after ⌃C for "read.py --lines"
            break

        if not args.lines:
            break


def _parse_read_argv(argv):
    """Parse the command line"""

    args = argdoc.parse_args()

    # Default to no splatter, else Ascii splat "*" splatter, to show input length not choice

    splatter = None
    if args.splat is not False:
        splatter = "*" if (args.splat is None) else args.splat

    args.splatter = splatter

    # Fail fast if wrongly called to silence or splatter while not in control of echoing

    echoing = args.e or (not sys.stdin.isatty())
    if not echoing:
        # FIXME: learn to silence without -e when stdin is a tty
        if args.s or splatter:
            stderr_print("read.py: error: call for -es, not -s, when stdin is a tty")
            sys.exit(2)  # exit 2 from rejecting usage

    # Choose a prompt

    args.prompting = "? " if (args.prompt is None) else args.prompt

    return args


def readline(prompt):
    """Read one line of edited input, or raise KeyboardInterrupt"""

    with GlassTeletype() as gt:
        shline = gt.readline(prompt)

    return shline


class ShLineHistory:
    """Remember old lines of edited input"""

    shlines = list()  # FIXME: resume history from "~/.cache/pybashish/stdin.txt"


class TerminalShadow:
    """Keep up a copy of what the Terminal should look like"""

    def __init__(self):

        self.tty_echoes = list()
        self.tty_lines = list()

    def putch(self, chars):

        for ch in chars:
            stdin = ch.encode()
            if stdin not in C0_CONTROL_STDINS:
                self.tty_echoes.append(ch)
            elif stdin == b"\a":
                pass
            elif stdin == b"\b":
                self.tty_echoes = self.tty_echoes[:-1]
            elif stdin == b"\r":
                pass
            elif stdin == b"\n":
                line = "".join(self.tty_echoes)
                self.tty_lines.append(line)
                self.tty_echoes = list()
            else:
                assert stdin == ESC_STDIN
                self.tty_echoes.append(ch)


class GlassTeletype(contextlib.ContextDecorator):
    r"""Emulate a glass teletype at Stdio, such as the 1978 DEC VT100 Video Terminal

    Wrap "tty.setraw" to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc as themselves,
    not as SIGINT SIGINFO SIGQUIT etc

    Compare Bash "bind -p", Zsh "bindkey", Bash "stty -a", and Unicode-Org U0000.pdf
    """

    def __init__(self, editing=None, silencing=None, splatter=None):

        self.editing = True if (editing is None) else editing
        self.silencing = silencing
        self.splatter = splatter

        self.inputs = ""  # buffer input to process later

        self.chars = list()  # insert chars into a shline
        self.echoes = list()  # echo chars of a shline
        self.lines = list()  # keep lines of history

        self._bots_by_stdin = self._calc_bots_by_stdin()

        self.shadow = TerminalShadow()

        self.fdin = None
        self.with_termios = None

    def __enter__(self):

        sys.stdout.flush()
        sys.stderr.flush()

        if self.editing and sys.stdin.isatty():

            self.fdin = sys.stdin.fileno()
            self.with_termios = termios.tcgetattr(self.fdin)

            when = termios.TCSADRAIN  # not termios.TCSAFLUSH
            tty.setraw(self.fdin, when)

        return self

    def __exit__(self, *exc_info):

        (_, exc, _) = exc_info

        sys.stdout.flush()
        sys.stderr.flush()

        if isinstance(exc, KeyboardInterrupt):
            if self.with_termios:
                sys.stderr.write("⌃C\r\n")
            else:
                sys.stderr.write("\n")

        if self.with_termios:

            when = termios.TCSADRAIN
            attributes = self.with_termios
            termios.tcsetattr(self.fdin, when, attributes)

        self.fdin = None
        self.with_termios = None

    def readline(self, prompt):
        """Pull the next line of input, but let people edit the shline as it comes"""

        # Open the line with flushes and the prompt

        self._open_line(prompt)

        # Block to fetch next char of paste, next keystroke, or empty end-of-input

        quitting = None
        while quitting is None:

            stdin = self.getch()
            assert stdin or not self.with_termios

            # Deal with these bytes as Control, else Data, else Log

            bot = self._bots_by_stdin.get(stdin)
            if bot is None:
                bot = self._insert_stdin
                if stdin in C0_CONTROL_STDINS:
                    bot = self._log_stdin

            # Close the line at _end_input, _end_line, etc.

            quitting = bot(stdin)

        # Close the line with input echoes, "\r", and/or "\n", as needed

        self._close_line(quitting)

        # Keep this line of history

        shline = self._join_shline()
        ShLineHistory.shlines.append(shline)

        # End the line with "\n", unless ended by _end_input

        result = shline + quitting
        return result

    def _open_line(self, prompt):
        """Open the line with flushes and the prompt"""

        if self.with_termios:
            self.putch(prompt)  # FIXME: think into write "with_termios" to "stderr"

        if self.silencing or not self.with_termios:
            sys.stderr.write(prompt)
            sys.stderr.flush()

    def _close_line(self, quitting):
        """Close the line with input echoes, "\r", and/or "\n", as needed"""

        # Close the prompt if Stdin is Tty, or if all input echoes silenced

        if self.with_termios:

            if self.silencing:
                if not quitting:
                    sys.stderr.write("^D")  # FIXME: first of two "^D"
                sys.stderr.write("\r\n")
                sys.stderr.flush()

        else:

            if sys.stdin.isatty():
                if not quitting:  # if no input echoed
                    stderr_print()
            elif self.silencing:
                stderr_print()
            else:

                # Echo the input now, not earlier, if Stdin is not Tty and echoes not silenced

                for echo in self.shadow.tty_lines:  # may include Ansi color codes
                    stderr_print(echo)

    def getch(self):
        """Block to fetch next char of paste, next keystroke, or empty end-of-input"""

        # Block to fetch next keystroke, if no paste already queued

        inputs = self.inputs
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

        stdin = os.read(sys.stdin.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while line not closed, if Stdin is or is not Tty
        # Trust no multibyte character encoding contains b"\r" or b"\n", as is true for UTF-8
        # (Solving the case of this trust violated will never be worthwhile?)

        calls = 1
        while stdin and (b"\r" not in stdin) and (b"\n" not in stdin):

            if self.with_termios:
                if not self.kbhit():
                    break

            more = os.read(sys.stdin.fileno(), 1)
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

        rlist = [sys.stdin]
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
            if self.with_termios and not self.silencing:
                sys.stderr.write(ch)

        sys.stderr.flush()

    def _insert_chars(self, chars):
        """Add chars to the shline"""

        for ch in chars:

            stdin = ch.encode()
            caret_echo = "^{}".format(chr(stdin[0] ^ X40_CONTROL_MASK))
            echo = caret_echo if (stdin in C0_CONTROL_STDINS) else ch

            self.chars.append(ch)
            self.echoes.append(echo)
            if self.splatter:
                splatter = len(echo) * self.splatter
                self.putch(splatter[: len(echo)])
            else:
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

    def _previous_history(self, stdin):
        """Step backwards in time, but skip over blank lines, except at ends of history"""
        # FIXME: stop warping cursor to Eol, here and in _next_history
        # FIXME: step back to match left-of-cursor only, a la Bash history-search-backward/forward

        stepped = False
        while len(self.lines) < len(ShLineHistory.shlines):

            index = len(ShLineHistory.shlines) - len(self.lines)
            if not any(_.strip() for _ in ShLineHistory.shlines[:index]):
                break

            shline = self._join_shline()
            self.lines.append(shline)

            old_shline = ShLineHistory.shlines[-len(self.lines)]

            self._drop_line(stdin)
            self._insert_chars(old_shline)  # FIXME: insert only last previous choice
            stepped = True

            if old_shline.strip():
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
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
