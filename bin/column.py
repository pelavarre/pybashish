#!/usr/bin/env python3

r"""
usage: column.py [-h] [-t]

align words of lines into columns

optional arguments:
  -h, --help  show this help message and exit
  -t          print words, but separate columns by two spaces

bugs:
  aligns cells to the right when two-thirds or more contain decimal digits
  doesn't offer to run without arguments a la mac and linux
  doesn't offer the "-csx" of mac, nor the "-censtx" of linux

bugs:
  does prompt once for stdin, when stdin chosen as file "-" or by no file args, unlike bash "cat"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  echo 'su per ca $ li fra gil $ is tic ex $ pi a li $ doc ious' | tr '$' '\n' | column -t
  echo '27 735 43 $ 51 785 640 $ 23 391 62 $ 14 6 19 $ 002 8809' | tr '$' '\n' | column -t
  echo 'su per ca $ 51 785 640 $ 23 391 62 $ 14 6 19 $ 002 8809' | tr '$' '\n' | column -t
"""


import collections
import random
import re
import sys

import argdoc


def main():
    """Run from the command line"""

    args = argdoc.parse_args()

    if not args.t:
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("column.py: error: no arguments not implemented")
        sys.exit(2)  # exit 2 from rejecting usage

    # Fetch all of Stdin

    prompt_tty_stdin()
    lines = sys.stdin.readlines()

    # Divide each line into words

    split_lines = list(_.split() for _ in lines)

    # Discard empty lines

    rows = list(row for row in split_lines if row)

    # Justify the cells in each column

    justified_rows = justify_cells_in_rows(complete_rows(rows, cell=""))
    for justified_row in justified_rows:
        print("  ".join(justified_row).rstrip())


def complete_rows(rows, cell):
    """Add cells till every row is as wide as the widest row"""

    if not rows:
        return list(rows)

    max_row_width = max(len(row) for row in rows)

    completed_rows = list()
    for row in rows:
        completed_row = row + ((max_row_width - len(row)) * [""])
        completed_rows.append(completed_row)

    return completed_rows


def justify_cells_in_rows(rows):
    """Justify the cells in each column, when given a rectangular list of rows of cells"""

    # Convert each cell to string

    strung_rows = list(list(str(cell) for cell in row) for row in rows)

    # Call on each cell to vote for left or right alignment

    left = collections.defaultdict(int)
    right = collections.defaultdict(int)
    for row in strung_rows:
        for (index, cell,) in enumerate(row):
            if re.search(
                r"[0-9]", string=cell
            ):  # vote right once if one or more decimal digits
                right[index] += 1
            else:
                left[index] += 1  # vote left once if zero decimal digits

    # Add empty cells till every row is as wide as the widest row

    completed_rows = complete_rows(strung_rows, cell="")

    # Measure max width per column

    widths = list(list(len(cell) for cell in row) for row in completed_rows)
    max_column_widths = list(max(column_widths) for column_widths in zip(*widths))

    # Align every cell of every row, to left of column or to right of column

    justified_rows = list()
    for row in completed_rows:

        justified_row = list()
        for (index, cell,) in enumerate(row):

            voters = left[index] + right[index]
            if right[index] >= ((2 * voters) / 3):  # require 2/3's vote to go right
                justified_cell = cell.rjust(max_column_widths[index])
            else:
                justified_cell = cell.ljust(max_column_widths[index])

            justified_row.append(justified_cell)

        justified_rows.append(justified_row)

    # Succeed

    return justified_rows


def pick_some_digits():
    """Generate some digits to work with, as an example"""

    shuffler = random.Random()
    shuffler.seed("19890604")  # 1989_Tiananmen_Square_protests

    plenty = len("supercalifragilisticexpialidocious")
    digits_list = list(_ for _ in ("0123456789" * plenty)[:plenty])
    shuffler.shuffle(digits_list)

    digits = "".join(digits_list)

    return digits  # '2773543517856402339162146190028809' in my Mar/2019 Python 3.7.3


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
