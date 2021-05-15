#!/usr/bin/env python3

r"""
usage: bind.py [-h] [-p]

look at what each keystroke means

optional arguments:
  -h, --help  show this help message and exit
  -p          print what each keystroke means

quirks:
  floods the terminal when called with no args, same as zsh "bindkey", unlike bash "bind" no-op
  lies when "ssh" redefines "~?" or "stty" redefines ⌃S and ⌃W, etc
  prints "drop-next-char" as the binding for ⌃D, but ⌃D at flush left ends input
  prints "end-input" as the binding for empty "" input, unlike no mention in bash / zsh
  prints none as the encoding for "self-insert", unlike bash / zsh leaving much unicode unmentioned
  sorts by binding like bash, not by encoding like zsh
  prints just the bindings only for ansi ↑ ↓ arrows, till "read.py" grows to bind the → ← arrows

examples:
  bind -p |grep '".e[[][DCAB]"' |sort  # ansi ↑ ↓ → ← arrows in bash
  bindkey |grep '".[[][[][ABCD]"'  # ansi ↑ ↓ → ← arrows in zsh
  bind.py |grep '".e[[][DCAB]"' |sort  # ansi ↑ ↓ → ← arrows in pybashish
"""
# FIXME --mac       print what each means, but in Apple style
# FIXME --zsh       print what each means, but in Zsh "bindkey" style
# FIXME --vim       print what each means, but in Vim and "cat -etv" style
# FIXME offers "--mac" and "--vim", unlike Bash
# FIXME example: bind --mac  # ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑ ... Control Option Shift Command ...


from __future__ import print_function

import sys

import argdoc

import read


def main():

    _ = argdoc.parse_args()

    gt = read.GlassTeletype()
    bots_by_stdin = gt._bots_by_stdin  # peek inside

    sortables = list()
    for (stdin, bot) in bots_by_stdin.items():

        str_bot = bot.__name__
        str_bot = "self-insert" if (str_bot == "_insert_stdin") else str_bot
        str_bot = str_bot.strip("_")
        str_bot = str_bot.replace("_", "-")

        repr_stdin = bind_repr(stdin)

        sortable = (str_bot, repr_stdin)

        sortables.append(sortable)

    for sortable in sorted(sortables):  # FIXME: column -t the "bind -p" output
        (str_bot, repr_stdin) = sortable
        print("{:7} {}".format((repr_stdin + ":"), str_bot))


def bind_repr(stdin):
    """Format as the name of a keystroke"""

    # Spell the empty end-of-input, as input

    if stdin == b"":

        repr_stdin = '""'  # no precedent for "" in Bash / Zsh
        return repr_stdin

    # Spell C0 Control codes

    if stdin in read.C0_CONTROL_STDINS:

        ord_stdin = stdin[0]  # one of C-@ C-A..C-Z C-[ C-\ C-] C-^ C-_ C-?
        ord_latin = ord_stdin ^ read.X40_CONTROL_MASK
        if ord("A") <= ord_latin <= ord("Z"):  # C-a..C-z is how Emacs says C-A..C-Z
            ord_latin = ord_latin ^ read.X20_LOWER_MASK

        repr_stdin = r'"\C-{}"'.format(chr(ord_latin))
        return repr_stdin

    # Spell Ansi Esc keystrokes

    if stdin and len(stdin) == 3:

        b0 = stdin[0:][:1]
        b1 = stdin[1:][:1]
        b2 = stdin[2:][:1]

        if b0 == read.ESC_STDIN:
            if b1 in read.BASIC_LATIN_STDINS:
                if b2 in read.BASIC_LATIN_STDINS:

                    repr_stdin = r'"\e{}{}"'.format(b1.decode(), b2.decode())
                    return repr_stdin

    # Settle for Python Repr

    repr_stdin = repr(stdin)  # no precedent for "None" in Bash / Zsh
    return repr_stdin


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
