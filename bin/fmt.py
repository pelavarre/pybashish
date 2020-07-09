#!/usr/bin/env python3

"""
usage: fmt [-h] [-w WIDTH] [--ruler]

join words of paragraphs then resplit them into lines

optional arguments:
  -h, --help  show this help message and exit
  -w WIDTH    limit line width (default: less wide than "/dev/tty")
  --ruler     show a ruler to count off the columns (and discard all Stdin)

bugs:
  does prompt once for Stdin, unlike Bash "fmt"
  doesn't default to prefer 65 within max 75 in the way of Bash
  does count columns up from 1, not up from 0, same as Bash
  prints '_' skids in the ruler to mark only the tabsize=8 tab stops:  1, 9, 17, ...

examples:
  echo {0..99} | fmt  # split to fit inside Terminal
  echo {0..39} | fmt -w42  # split to fit inside width
  echo {0..39} | tr -d ' ' | fmt -w42  # no split at width
  echo su-per-ca-li-fra-gil-is-tic-ex-pi-a-li-doc-ious | fmt -w42  # no split at "-" dashes
  fmt.py --ruler -w72  # ends in column 72
"""

import os
import sys
import textwrap

import argdoc


def main():
    """Run from the command line"""

    args = argdoc.parse_args()

    width = calc_width(args.width)
    if args.ruler:
        print_ruler(width)
        return

    fmt_paragraphs_of_stdin(width)


def calc_width(args_width):
    '''Take an explicit line width, else fit inside of "/dev/tty"'''

    if args_width is not None:

        width = int(args_width)

    else:

        with open("/dev/tty") as tty:
            fdtty = tty.fileno()
            columns = os.get_terminal_size(fdtty).columns
        assert columns

        width = columns - 1

    assert width > 0

    return width


def print_ruler(width):
    """Print one char per column to help count them accurately, when monospaced"""

    dupes = (width + 10 - 1) // 10
    chars = dupes * "1234567890"  # one-based, not zero-based
    assert len(chars) >= width

    ruler = chars[:width]
    for tabstop in range(0, width, 8):
        ruler = ruler[:tabstop] + "_" + ruler[(tabstop + 1) :]

    assert len(ruler) == width
    print(ruler)


def fmt_paragraphs_of_stdin(width):
    """Join words of paragraphs from Stdin, and then resplit them into lines of Stdout"""

    para = list()
    dent = ""

    prompt_tty_stdin()
    for line in sys.stdin.readlines():  # FIXME: cope with streams larger than memory

        line_dent = str_splitdent(line)[0]
        if para and (line_dent != dent):
            print_one_paragraph(dent, para=para, width=width)
            para = list()
            dent = line_dent

        para.append(line.strip())

    print_one_paragraph(dent, para=para, width=width)


def print_one_paragraph(dent, para, width):
    """Join words of one paragraph, resplit them into lines, and print the lines"""

    if para:

        width_ = width - len(dent)
        assert (
            width_ >= 1
        )  # FIXME: think through dents about as large and larger than widths

        text = "\n".join(para)
        filled = textwrap.fill(
            text, width=width_, break_on_hyphens=False, break_long_words=False
        )
        for line in filled.splitlines():
            print((dent + line).rstrip())


def prompt_tty_stdin():  # deffed in many files
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


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
