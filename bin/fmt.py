#!/usr/bin/env python3

"""
usage: fmt [-h] [-w WIDTH] [--ruler]

join words of paragraphs then resplit them into lines

optional arguments:
  -h, --help  show this help message and exit
  -w WIDTH    limit line width (default: less wide than "/dev/tty")
  --ruler     show a ruler to count off the columns (and discard all Stdin)

bugs:
  doesn't default to prefer 65 within max 75 in the way of Bash
  does count columns up from 1, not up from 0, same as Bash

examples:
  echo {0..99} | fmt  # split to fit inside Terminal
  echo {0..39} | fmt -w42  # split to fit inside width
  echo {0..39} | tr -d ' ' | fmt -w42  # no split at width
  echo su-per-ca-li-fra-gil-is-tic-ex-pi-a-li-doc-ious | fmt.py -w42  # no split at "-" dashes
  fmt --ruler -w73  # ends in column 72
"""

import os
import sys

import argdoc


def main():
    args = argdoc.parse_args()

    #

    if args.width is not None:

        width = int(args.width)

    else:

        with open("/dev/tty") as tty:
            fdtty = tty.fileno()
            columns = os.get_terminal_size(fdtty).columns
        assert columns

        width = columns - 1

    assert width > 0

    #

    if args.ruler:

        dupes = (width + 10 - 1) // 10
        chars = dupes * "1234567890"  # one-based, not zero-based
        assert len(chars) >= width

        ruler = chars[:width]
        for tabstop in range(0, width, 8):
            ruler = ruler[:tabstop] + "_" + ruler[(tabstop + 1) :]

        assert len(ruler) == width
        print(ruler)

        return

    #

    para = list()
    dent = ""
    line = "\n"

    while line:
        line = sys.stdin.readline()  # "" at end-of-input

        line_dent = str_splitdent(line)[0]
        if (not para) or (line_dent == dent):
            para.append(line)
        else:
            text = "\n".join(para)
            textwrap.fill(
                text, width=width, break_on_hyphens=False, break_long_words=False
            )
            print(text)


"""

    print(args)

12345678_0123456_8901234_6789012_4567890_2345678_0123456_8901234_6789012_4567890_2345678_0123456789_
        x       x       x       x       x       x       x       x       x       x       x       x
x       x       x       x       x       x
"""


def str_splitdent(line):  # deffed by "doctestbash.py", "fmt.py
    """Split apart the indentation of a line, from the remainder of the line"""

    len_dent = len(line) - len(line.lstrip())
    dent = len_dent * " "

    tail = line[len(dent) :]

    return (
        dent,
        tail,
    )


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
