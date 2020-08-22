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

popular bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "fmt"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", like linux "fmt -", unlike mac "fmt -"

examples:
  echo 'a b  c  d e f g  h i j   k  l m' | fmt.py -w9  # keep blanks except at joins and splits
  echo '  a b c$  d e f$  g$$h' | tr '$' '\n' | fmt -w9  # group by common indents
  echo $(seq 0 99) | fmt.py  # split to fit inside Terminal
  echo $(seq 0 39) | fmt.py -w42  # split to fit inside width
  echo $(seq 0 39) | tr -d ' ' | fmt.py -w42  # no split at width
  echo su-per-ca-li-fra-gil-is-tic-ex-pi-a-li-doc-ious | fmt.py -w42  # no split at "-" dashes
  fmt.py --ruler -w72  # ends in column 72
  : # 5678_0123456_8901234_6789012_4567890 2345678_0123456_8901234_6789012  # the 72-column ruler
"""


import os
import sys
import textwrap

import argdoc


def main():
    """Run from the command line"""

    stdout_columns = guess_stdout_columns()

    args = argdoc.parse_args()
    width = (stdout_columns - 1) if (args.width is None) else int(args.width)

    if args.ruler:
        print_ruler(width)
        return

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
    """Join words of paragraphs from Stdin, and then resplit them into lines of Stdout"""

    prompt_tty_stdin()

    para = list()
    para_dent = None

    while True:
        line = sys.stdin.readline()
        if not line:
            if para:
                fmt_one_paragraph((para_dent * " "), para=para, width=width)
            break

        text = line.lstrip()
        line_dent = (len(line) - len(text)) if text else 0

        if (not text) or (line_dent != para_dent):
            if para:
                fmt_one_paragraph((para_dent * " "), para=para, width=width)
                para = list()
            para_dent = line_dent

        if not text:
            print()
        else:
            para.append(line.strip())


def fmt_one_paragraph(dent, para, width):
    """Join words of one paragraph, resplit them into lines, and print the lines"""

    width = (width - len(dent)) if (width > len(dent)) else 1

    text = "\n".join(para)

    filled = textwrap.fill(
        text, width=width, break_on_hyphens=False, break_long_words=False
    )

    for line in filled.splitlines():
        print((dent + line).rstrip())


# deffed in many files  # missing from docs.python.org
def guess_stdout_columns(*hints):
    """
    Run all the searches offered, accept the first result found if any, else return None

    Default to search:  "COLUMNS", sys.stdout, "/dev/tty", 80

    To fail fast, call for all the guesses always, while still returning only the first that works
    """

    chosen_hints = hints if hints else ("COLUMNS", sys.stdout, "/dev/tty", 80,)
    # FIXME: port to "/dev/tty" outside of Mac and Linux

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
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
