#!/usr/bin/env python3

r"""
usage: fmt.py [-h] [-w WIDTH] [--ruler]

join lines of the same indentation, and split at width or before it

optional arguments:
  -h, --help  show this help message and exit
  -w WIDTH    width to split at or before (default: don't print into last column of terminal)
  --ruler     show a ruler to count off the columns

bugs:
  buffers whole paragraphs, not just lines, but takes each blank line as its own paragraph
  joins and splits all lines, not just lines that don't begin with an nroff "." dot
  defaults to fit inside terminal width, not to the prefer 65 within max 75 of bash "fmt"
  guesses -w terminal width from "COLUMNS", else sys.stdout, else "/dev/tty", else guesses 80
  prints '_' skids onto the ruler to mark the tabsize=8 tab stops:  1, 9, 17, ...

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "fmt"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", like linux "fmt -", unlike mac "fmt -"

examples:
  echo 'a b  c  d e f g  h i j   k  l m' | fmt.py -9  # keep blanks except at joins and splits
  echo '  a b c$  d e f$  g$$h' | tr '$' '\n' | fmt.py -9  # group by common indents
  echo '   a b c' | fmt.py -1  # forward indentation wider than wanted, if present
  :
  echo $(seq 0 99) | fmt.py  # split to fit inside Terminal
  echo $(seq 0 39) | fmt.py -42  # split to fit inside width
  echo $(seq 0 39) | tr -d ' ' | fmt.py -42  # no split at width
  echo su-per-ca-li-fra-gil-is-tic-ex-pi-a-li-doc-ious | fmt.py -42  # no split at "-" dashes
  :
  fmt.py --ruler -w72  # ends in column 72
  : # 5678_0123456_8901234_6789012_4567890 2345678_0123456_8901234_6789012  # the 72-column ruler
"""


import os
import re
import sys
import textwrap

import argdoc


def main(argv):
    """Run from the command line"""

    stdout_columns = guess_stdout_columns()

    # Parse the command line

    fmt_argv_tail = list(argv[1:])
    for (index, arg,) in enumerate(fmt_argv_tail):
        if re.match(r"^[-][0-9]+$", string=arg):
            fmt_argv_tail[index] = "-w{}".format(-int(arg))

    args = argdoc.parse_args(fmt_argv_tail)
    width = (stdout_columns - 1) if (args.width is None) else int(args.width)

    # Option to print the ruler and discard Stdin

    if args.ruler:
        print_ruler(width)
        return

    # Else join and split Stdin

    fmt_paragraphs_of_stdin(width)


def print_ruler(width):
    """Print one monospaced char per column to help number the columns accurately"""

    dupes = (width + 10 - 1) // 10
    chars = dupes * "1234567890"  # one-based, not zero-based
    assert len(chars) >= width

    ruler = chars[:width]
    for tabstop in range(0, width, 8):
        ruler = ruler[:tabstop] + "_" + ruler[(tabstop + 1) :]
    for halfscreen in range(40, width, 40):
        ruler = ruler[:halfscreen] + " " + ruler[(halfscreen + 1) :]

    assert len(ruler) == width

    print(ruler.rstrip())


def fmt_paragraphs_of_stdin(width):
    """Join lines of the same indentation, and split at width or before it"""

    column = width + 1
    prompt_tty_stdin("Joining words, resplitting before column {}".format(column))

    para = list()
    para_dent = None

    while True:
        line = sys.stdin.readline()
        if not line:
            if para:
                fmt_one_paragraph(para_dent, para=para, width=width)
            break

        (str_dent, text,) = str_splitdent(line)

        rstripped = text.rstrip()
        dent = str_dent if rstripped else None

        if (dent != para_dent) or (not rstripped):
            if para:
                fmt_one_paragraph(para_dent, para=para, width=width)
                para = list()
            para_dent = dent

        if rstripped:
            para.append(rstripped)
        else:
            print()


def fmt_one_paragraph(dent, para, width):
    """Join words of one paragraph, resplit them into fewest wide lines, and print the lines"""

    assert dent is not None
    assert all(_ for _ in para)

    text = "\n".join(para)

    fill_width = (width - len(dent)) if (len(dent) < width) else 1
    chars = textwrap.fill(
        text, width=fill_width, break_on_hyphens=False, break_long_words=False
    )
    lines = chars.splitlines()

    assert lines

    for line in chars.splitlines():
        print((dent + line).rstrip())


# deffed in many files  # missing from docs.python.org
def guess_stdout_columns(*hints):
    """
    Run all the searches offered, accept the first result found if any, else return None

    Default to search:  "COLUMNS", sys.stdout, "/dev/tty", 80

    To fail fast, call for all the guesses always, while still returning only the first that works
    """

    chosen_hints = hints if hints else ("COLUMNS", sys.stdout, "/dev/tty", 80,)

    terminal_widths = list()
    for hint in chosen_hints:

        terminal_width = guess_stdout_columns_os(hint)
        if terminal_width is None:
            terminal_width = guess_stdout_columns_os_environ_int(hint)
        else:
            _ = guess_stdout_columns_os_environ_int(hint)

        if terminal_width is not None:
            terminal_widths.append(terminal_width)

    if terminal_widths:
        terminal_width = terminal_widths[0]

        return terminal_width


# deffed in many files  # missing from docs.python.org
def guess_stdout_columns_os(hint):
    """Try "os.get_terminal_size", and slap back "shutil.get_terminal_size" pushing (80, 24,)"""

    showing = None
    fd = None
    if hasattr(hint, "fileno"):
        streaming = hint
        fd = streaming.fileno()
    elif hasattr(hint, "startswith"):
        if hint.startswith(os.sep):
            devname = hint
            showing = open(devname)
            fd = showing.fileno()

    terminal_width = None
    if fd is not None:
        try:
            terminal_size = os.get_terminal_size(fd)
            terminal_width = terminal_size.columns
        except OSError:  # such as OSError: [Errno 25] Inappropriate ioctl for device
            pass

    if showing:
        showing.close()

    return terminal_width


# deffed in many files  # missing from docs.python.org
def guess_stdout_columns_os_environ_int(hint):
    """Pull digits from "os.environ" via the hint as key, else from the hint itself"""

    digits = hint
    if hasattr(hint, "startswith"):
        envname = hint
        try:
            digits = os.environ[envname]
        except KeyError:  # such as KeyError: 'COLUMN'
            pass

    try:
        terminal_width = int(digits)
    except TypeError:  # such as TypeError: must be ... not 'list'
        terminal_width = None
    except ValueError:  # such as ValueError: invalid literal ... with base 10
        terminal_width = None

    return terminal_width


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin(message=None):
    if sys.stdin.isatty():
        if message is not None:
            stderr_print(message)
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def str_splitdent(line):
    """Split apart the indentation of a line, from the remainder of the line"""

    lstripped = line.lstrip()
    len_dent = len(line) - len(lstripped)

    tail = lstripped
    if not lstripped:  # see no chars, not all chars, as the indentation of a blank line
        tail = line
        len_dent = 0

    dent = len_dent * " "

    return (
        dent,
        tail,
    )


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
