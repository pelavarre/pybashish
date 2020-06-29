#!/usr/bin/env python3

r"""
usage: bind.py [-h] [-p]

print what each keystroke means

optional arguments:
  -h, --help  show this help message and exit
  -p          yea, print it all, like i said already

examples:
  bind -p | grep '".e.[DCAB]"'  # Ansi Terminal arrows
  bind -p | grep -v ': self-insert$'  # Control codes

bugs:
  "bind" with no args is "bind -h", unlike Bash
"""

from __future__ import print_function

import argdoc

import read


def main():

    args = argdoc.parse_args()
    if not args.p:
        argdoc.parse_args("--help".split())

    gt = read.GlassTeletype()
    bots_by_stdin = gt._bots_by_stdin  # peek inside

    sortables = list()
    for (stdin, bot,) in bots_by_stdin.items():

        str_bot = bot.__name__
        str_bot = "self-insert" if (str_bot == "_insert_stdin") else str_bot
        str_bot = str_bot.strip("_")
        str_bot = str_bot.replace("_", "-")

        repr_stdin = bind_repr(stdin, gt=gt)

        sortable = (
            str_bot,
            repr_stdin,
        )

        sortables.append(sortable)

    for sortable in sorted(sortables):
        (str_bot, repr_stdin,) = sortable
        print("{}: {}".format(repr_stdin, str_bot))


def bind_repr(stdin, gt):
    """Format as the conventional Bash "bind -p" name of a keystroke"""

    c0_control_stdins = gt.c0_control_stdins
    basic_latin_stdins = gt.basic_latin_stdins

    # Spell Ansi Esc codes as:  r"\eXY"

    if len(stdin) == 3:

        c0 = stdin[0:][:1]
        c1 = stdin[1:][:1]
        c2 = stdin[2:][:1]

        esc = b"\x1b"

        if c0 == esc:
            if c1 in basic_latin_stdins:
                if c2 in basic_latin_stdins:

                    repr_stdin = r'"\e{}{}"'.format(c1.decode(), c2.decode())
                    return repr_stdin

    # Spell Basic Latin codes as their characters

    if len(stdin) == 1:

        if stdin in basic_latin_stdins:

            repr_stdin = r'"{}"'.format(stdin.decode())
            return repr_stdin

        # Spell C0 Control codes as:  r"\C-x"

        if stdin in c0_control_stdins:

            control = ord(stdin)  # one of C-@ C-A..C-Z C-[ C-\ C-] C-^ C-_ C-?
            latin = control ^ 0x40
            if ord("A") <= latin <= ord("Z"):  # C-a..C-z is how Emacs says C-A..C-Z
                latin = latin ^ 0x20

            repr_stdin = r'"\C-{}"'.format(chr(latin))
            return repr_stdin

    repr_stdin = repr(stdin)
    return repr_stdin


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
