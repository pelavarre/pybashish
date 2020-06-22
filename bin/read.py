#!/usr/bin/env python3

import contextlib
import os
import select
import sys
import termios
import tty


class ShLineHistory:

    shlines = list()  # FIXME: resume history from "~/.cache/pybashish/stdin.txt"


class GlassTeletype(contextlib.ContextDecorator):
    r"""Emulate a glass teletype, such as the 1978 DEC VT100 video terminal

    Wrap "tty.setraw" to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc, not as SIGINT SIGINFO SIGQUIT etc

    Compare Bash "bind -p" and "stty -a"
    Compare Unicode-Org U0000.pdf
    """

    def __init__(self):

        self.bots_by_stdin = self._index_bots_by_stdin()

    def __enter__(self):

        self.fdin = sys.stdin.fileno()
        self.with_termios = termios.tcgetattr(self.fdin)

        when = termios.TCSADRAIN  # not termios.TCSAFLUSH
        tty.setraw(self.fdin, when)

        return self

    def __exit__(self, *exc):

        when = termios.TCSADRAIN
        attributes = self.with_termios
        termios.tcsetattr(self.fdin, when, attributes)

    def getch(self):

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
                appending.write("{} {}\n".format(calls, repr(stdin)))

        return stdin

    def kbhit(self):

        rlist = [sys.stdin]
        wlist = list()
        xlist = list()
        timeout = 0
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, wlist_, xlist_,) = selected

        if rlist_ == rlist:
            return True

    def putch(self, chars):

        for ch in chars:
            sys.stdout.write(ch)
            sys.stdout.flush()

    def readline(self):

        self.shline = ""
        self.echoes = list()

        self.pushes = list()

        self.quitting = None
        while self.quitting is None:

            stdin = self.getch()

            bot = self.bots_by_stdin.get(stdin, self._log_stdin)
            bot(stdin)

        shline = self.shline
        ShLineHistory.shlines.append(shline)

        result = shline + self.quitting
        return result

    def _index_bots_by_stdin(self):

        bots_by_stdin = dict()

        bots_by_stdin[b"\x03"] = self._raise_keyboard_interrupt  # ETX, aka ⌃C, aka 3
        bots_by_stdin[b"\x04"] = self._end_file  # EOT, aka ⌃D, aka 4
        bots_by_stdin[b"\x07"] = self._ring_bell  # BEL, aka ⌃G, aka 7
        bots_by_stdin[b"\x08"] = self._erase_one  # BS, aka ⌃H, aka 8
        bots_by_stdin[b"\x0a"] = self._end_line  # LF, aka ⌃J, aka 10
        bots_by_stdin[b"\x0d"] = self._end_line  # CR, aka ⌃M, aka 13
        bots_by_stdin[b"\x0e"] = self._next_history  # SO, aka ⌃N, aka 14
        bots_by_stdin[b"\x10"] = self._previous_history  # DLE, aka ⌃P, aka 16
        bots_by_stdin[b"\x12"] = self._reprint  # DC2, aka ⌃R, aka 18
        bots_by_stdin[b"\x15"] = self._unix_line_discard  # NAK, aka ⌃U, aka 21
        bots_by_stdin[b"\x7f"] = self._erase_one  # DEL, classically aka ⌃?, aka 127

        bots_by_stdin[b"\x1b[A"] = self._previous_history  # Up Arrow
        bots_by_stdin[b"\x1b[B"] = self._next_history  # Down Arrow

        for codepoint in range(
            ord(" "), ord("~") + 1
        ):  # "\u0020" .. "\u007e" "us-ascii" plain text in U0000.pdf
            stdin = chr(codepoint).encode()
            bots_by_stdin[stdin] = self._take_stdin

        return bots_by_stdin

    def _end_file(self, stdin):

        if self.shline:
            self._ring_bell(stdin)
            return

        self.putch("\r\n")
        self.quitting = ""

    def _end_line(self, stdin):

        self.putch("\r\n")
        self.quitting = "\n"

    def _erase_one(self, stdin):

        if not self.echoes:
            return

        echo = self.echoes[-1]
        width = len(self.echoes[-1])
        self.echoes = self.echoes[:-1]

        if len(echo) == 1:
            assert ord(" ") <= ord(echo) <= ord("~")
            self.shline = self.shline[:-1]

        backing = width * "\b"
        blanking = width * " "
        self.putch(f"{backing}{blanking}{backing}")

    def _log_stdin(self, stdin):

        #

        pasteables = set(codepoint for codepoint in range(ord(" "), ord("~") + 1))
        # pasteables.add(ord("\t"))  # implement _complete and _dynamic_complete_history
        pasteables.add(ord("\n"))
        pasteables.add(ord("\r"))

        if all((codepoint in pasteables) for codepoint in stdin):
            for codepoint in stdin:
                stdin_ = chr(codepoint).encode()
                bot = self.bots_by_stdin.get(stdin_, self._log_stdin)
                assert bot != self._log_stdin
                bot(stdin_)
                if self.quitting:  # FIXME: redundant
                    break
            return

        #

        echoable = "".join("<{}>".format(codepoint) for codepoint in stdin)
        self.echoes.append(echoable)
        self.putch(echoable)

    def _next_history(self, stdin):

        while self.pushes:

            shline = self.pushes[-1]
            self.pushes = self.pushes[:-1]

            self._unix_line_discard(stdin)
            if shline:
                self._take_chars(shline)
                break

    def _previous_history(self, stdin):

        while len(self.pushes) < len(ShLineHistory.shlines):

            self.pushes.append(self.shline)
            shline = ShLineHistory.shlines[-len(self.pushes)]

            self._unix_line_discard(stdin)
            if shline:
                self._take_chars(shline)
                break

    def _raise_keyboard_interrupt(self, stdin):  # aka stty "intr" SIGINT

        raise KeyboardInterrupt()  # FIXME: also SIGINFO, SIGUSR1, SIGSUSP, SIGQUIT

    def _reprint(self, stdin):

        self.putch("^R\r\n")
        self.putch("".join(self.echoes))

    def _ring_bell(self, stdin):

        self.putch("\a")

    def _take_chars(self, chars):

        for ch in chars:
            self.shline += ch
            self.echoes.append(ch)
            self.putch(ch)

    def _take_stdin(self, stdin):

        ch = stdin.decode()
        self._take_chars(ch)

    def _unix_line_discard(self, stdin):  # aka stty "kill" many

        while self.echoes:
            self._erase_one(stdin)


def main():

    with GlassTeletype() as gt:
        line = gt.readline()

    print(repr(line))


if __name__ == "__main__":
    main()


# pulled from:  git clone git@github.com:pelavarre/pybashish.git
