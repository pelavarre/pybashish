#!/usr/bin/env python3

r"""
usage: read.py [-h] [--lines]

read one line of standard input, and print it

optional arguments:
  -h, --help  show this help message and exit
  --lines     keep on reading till EOF (such as Terminal Control+D)

bugs:
  prompts with "? ", unlike the "" of Bash "read" with no -p PROMPT
  prompts and echoes, even when Stdin not Terminal, unlike Bash
  lets people edit input, like Bash "read -e", unlike Zsh "read"
  prints the line as a Python Repr
  doesn't stuff the line into a Bash Environment Variable
  doesn't compress spaces between words down to one space
  doesn't read another line after a line ends with \ backslash
  doesn't delete \ backslashes
"""

from __future__ import print_function

import contextlib
import os
import select
import sys
import termios
import tty

import argdoc


def main():
    """Run from the command line"""

    args = argdoc.parse_args()

    prompt = "? "

    if args.lines:
        sys.stderr.write(
            "Press ⌃D EOF to quit\n"
        )  # prompt even when Stdin not Terminal
        sys.stderr.flush()

    while True:

        shline = None
        try:
            shline = readline(prompt)
        except KeyboardInterrupt:
            sys.stderr.write("⌃C\r\n")
            sys.stderr.flush()

        print(repr(shline))
        sys.stdout.flush()

        if shline == "":
            break

        if not args.lines:
            break


def readline(prompt):
    """Read one line of edited input"""

    if not sys.stdin.isatty():

        sys.stdout.write(prompt)
        sys.stdout.flush()

        shline = sys.stdin.readline()

        sys.stdout.write(shline.rstrip())
        sys.stdout.write("\n")
        sys.stdout.flush()

    else:

        with GlassTeletype() as gt:
            gt.putch(prompt)
            shline = gt.readline()

    return shline


class ShLineHistory:
    """Remember old lines of edited input"""

    shlines = list()  # FIXME: resume history from "~/.cache/pybashish/stdin.txt"


class GlassTeletype(contextlib.ContextDecorator):
    r"""Emulate a glass teletype, such as the 1978 DEC VT100 video terminal

    Wrap "tty.setraw" to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc, not as SIGINT SIGINFO SIGQUIT etc

    Compare Bash "bind -p" and "stty -a"
    Compare Unicode-Org U0000.pdf
    """

    def __init__(self):

        self.c0_control_stdins = b"".join(self._calc_c0_controls_stdins())
        self.basic_latin_stdins = b"".join(self._calc_basic_latin_stdins())
        self._bots_by_stdin = self._calc_bots_by_stdin()

    def __enter__(self):

        self.fdin = sys.stdin.fileno()
        self.with_termios = termios.tcgetattr(self.fdin)

        when = termios.TCSADRAIN  # not termios.TCSAFLUSH
        tty.setraw(self.fdin, when)

        return self

    def __exit__(self, *exc_info):

        when = termios.TCSADRAIN
        attributes = self.with_termios
        termios.tcsetattr(self.fdin, when, attributes)

    def getch(self):
        """Pull the next slow single keystroke, or a burst of paste"""

        stdin = os.read(sys.stdin.fileno(), 1)
        calls = 1

        while (b"\r" not in stdin) and (b"\n" not in stdin):
            if not self.kbhit():
                break

            more = os.read(sys.stdin.fileno(), 1)
            stdin += more
            calls += 1

        assert calls <= len(stdin)

        if False:  # FIXME: configure logging
            with open("trace.txt", "a") as appending:
                appending.write("read.getch: {} {}\n".format(calls, repr(stdin)))

        return stdin

    def kbhit(self):
        """Wait till next key struck, or a burst of paste pasted"""

        rlist = [sys.stdin]
        wlist = list()
        xlist = list()
        timeout = 0
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_,) = selected

        if rlist_ == rlist:
            return True

    def putch(self, chars):
        """Print one or more decoded Basic Latin character or decode C0 Control code"""

        for ch in chars:
            sys.stdout.write(ch)
            sys.stdout.flush()

    def readline(self):
        """Pull the next line of input, but let people edit the line as it comes"""

        self.shline = ""
        self.echoes = list()

        self.pushes = list()

        quitting = None
        while quitting is None:

            stdin = self.getch()

            bot = self._bots_by_stdin.get(stdin)
            if bot is None:
                bot = self._log_stdin
                if self._can_paste_stdin(stdin):
                    bot = self._do_paste_stdin

            quitting = bot(stdin)

        shline = self.shline
        ShLineHistory.shlines.append(shline)

        result = shline + quitting
        return result

    def _insert_chars(self, chars):
        """Add chars to the line"""

        for ch in chars:
            self.shline += ch
            self.echoes.append(ch)
            self.putch(ch)

    def _calc_c0_controls_stdins(self):
        """List the U0000.pdf C0 Control codepoints, encoded as bytes"""

        for codepoint in range(
            0, 0x20
        ):  # first thirty-two of the C0 Control codepoints
            yield chr(codepoint).encode()

        codepoint = 0x7F  # last of the thirty-three C0 Control codepoints
        yield chr(codepoint).encode()

    def _calc_basic_latin_stdins(self):
        """List the U0000.pdf Basic Latin codepoints, encoded as bytes"""

        for codepoint in range(0x20, 0x7F):  # ninety-five Basic Latin codepoints
            yield chr(codepoint).encode()

    def _calc_bots_by_stdin(self):
        """Enlist some bots to serve many kinds of keystrokes"""

        bots_by_stdin = dict()

        bots_by_stdin[b"\x03"] = self._raise_keyboard_interrupt  # ETX, aka ⌃C, aka 3
        bots_by_stdin[b"\x04"] = self._end_file  # EOT, aka ⌃D, aka 4
        bots_by_stdin[b"\x07"] = self._ring_bell  # BEL, aka ⌃G, aka 7
        bots_by_stdin[b"\x08"] = self._drop_char  # BS, aka ⌃H, aka 8
        bots_by_stdin[b"\x0a"] = self._end_line  # LF, aka ⌃J, aka 10
        bots_by_stdin[b"\x0d"] = self._end_line  # CR, aka ⌃M, aka 13
        bots_by_stdin[b"\x0e"] = self._next_history  # SO, aka ⌃N, aka 14
        bots_by_stdin[b"\x10"] = self._previous_history  # DLE, aka ⌃P, aka 16
        bots_by_stdin[b"\x12"] = self._reprint  # DC2, aka ⌃R, aka 18
        bots_by_stdin[b"\x15"] = self._drop_line  # NAK, aka ⌃U, aka 21
        bots_by_stdin[b"\x7f"] = self._drop_char  # DEL, classically aka ⌃?, aka 127

        for stdin in bots_by_stdin.keys():
            assert len(stdin) == 1
            assert stdin in self.c0_control_stdins

        for codepoint in self.basic_latin_stdins:
            stdin = chr(codepoint).encode()
            bots_by_stdin[stdin] = self._insert_stdin

        bots_by_stdin[b"\x1b[A"] = self._previous_history  # ↑ Up Arrow
        bots_by_stdin[b"\x1b[B"] = self._next_history  # ↓ Down Arrow
        # bots_by_stdin[b"\x1b[C"] = self._forward_char  # ↑ Left Arrow
        # bots_by_stdin[b"\x1b[D"] = self._backward_char  # ↑ Right Arrow

        return bots_by_stdin

    def _can_paste_stdin(self, stdin):
        """Say when picking paste apart one char at a time works well enough for now"""

        ord_esc = 0x1B

        if len(stdin) == 3:  # do not paste the Esc [ DCAB arrow keys, etc
            if stdin[0] == ord_esc:
                return False

        return True

    def _do_paste_stdin(self, stdin):
        """Pick paste apart one char at a time"""

        assert self._can_paste_stdin(stdin)

        # Pull out each char of paste

        quitting = None
        for ch in stdin.decode():
            ch_ = ch.encode()

            # Insert everything except C0 Control characters

            if ch_ not in self.c0_control_stdins:
                self._insert_chars(ch)

            # Execute, or log & drop, each C0 Control character

            else:
                bot = self._log_stdin
                bot = self._bots_by_stdin.get(ch_, bot)
                quitting = bot(ch_)

            if quitting:
                break

        return quitting

    def _drop_char(self, stdin):  # aka Stty "erase", aka Bind "backward-delete-char"
        """Undo the last "_insert_stdin", even if it inserted no chars"""

        if not self.echoes:
            return

        echo = self.echoes[-1]
        width = len(self.echoes[-1])
        self.echoes = self.echoes[:-1]

        if len(echo) == 1:
            assert echo.encode() in self.basic_latin_stdins
            self.shline = self.shline[:-1]

        backing = width * "\b"
        blanking = width * " "
        self.putch(f"{backing}{blanking}{backing}")

    def _drop_line(self, stdin):  # aka Stty "kill" many, aka Bind "unix-line-discard"
        """Undo all the "_insert_stdin" since the start of line"""

        while self.echoes:
            self._drop_char(stdin)

    def _end_file(self, stdin):
        """End the file before starting the next line, else ring the bell"""

        if self.shline:
            self._ring_bell(stdin)
            return

        self.putch("\r\n")  # echo ending the file, same as ending a line

        quitting = ""
        return quitting

    def _end_line(self, stdin):
        """End the line"""

        self.putch("\r\n")  # echo ending the line

        quitting = "\n"
        return quitting

    def _log_stdin(self, stdin):
        """Disclose the encoding of a meaningless keystroke"""

        echoable = "".join("<{}>".format(codepoint) for codepoint in stdin)
        self.echoes.append(echoable)
        self.putch(echoable)

    def _next_history(self, stdin):
        """Step forward in time"""

        while self.pushes:

            shline = self.pushes[-1]
            self.pushes = self.pushes[:-1]

            self._drop_line(stdin)
            if shline:
                self._insert_chars(shline)
                break

    def _previous_history(self, stdin):
        """Step backwards in time"""

        while len(self.pushes) < len(ShLineHistory.shlines):

            self.pushes.append(self.shline)
            shline = ShLineHistory.shlines[-len(self.pushes)]

            self._drop_line(stdin)
            if shline:
                self._insert_chars(shline)
                break

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

    def _insert_stdin(self, stdin):  # aka Bash "bind -p | grep self-insert"
        """Add the codepoint of the keystroke"""

        assert (
            len(stdin) == 1
        )  # no tests yet of keys other than the ninety-five Basic Latin chars
        assert stdin in self.basic_latin_stdins

        ch = stdin.decode()
        self._insert_chars(ch)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
