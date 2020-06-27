#!/usr/bin/env python3

r"""
usage: ls.py [-h] [-1] [-C]

print some filenames

optional arguments:
  -h, --help  show this help message and exit
  -1          print one filename per line
  -C          print filenames into multiple columns
"""
# FIXME:  -w COLUMNS, --width COLUMNS  as if a terminal so wide
# FIXME: count -1 -C to resolve contradictions

from __future__ import print_function

import os
import sys

import argdoc


def main():

    #

    stdout_isatty = os.isatty(sys.stdout.fileno())

    try:
        columns = os.get_terminal_size().columns
    except OSError:  # such as OSError: [Errno 25] Inappropriate ioctl for device
        columns = None

    #

    args = argdoc.parse_args()

    args.dash_one = vars(args)["1"]
    if args.dash_one is None:
        if stdout_isatty:
            args.dash_one = True

    #

    whats = sorted(w for w in os.listdir() if not os_stat_hidden(w))

    #

    if args.dash_one:

        for what in whats:
            print(what)

        return

    #

    columns_ = 89 if (columns is None) else columns

    sep = "  "
    rows = spill_cells(whats, columns=columns_, sep=sep)
    for row in rows:
        print(sep.join(row).rstrip())

    # FIXME: implement ls -alF -rt, etc
    # FIXME: implement glob args
    # FIXME: timestamp to like the second in an ls -l


def os_stat_hidden(what):

    hidden = what.startswith(".")  # correct at Mac and Linux, where os.name == "posix"
    return hidden


def spill_cells(cells, columns, sep):  # FIXME  # noqa C901

    cell_strs = list(str(c) for c in cells)

    no_floors = list()
    if not cell_strs:
        return no_floors

    floors = None  # FIXME: review spill_cells closely, now that it mostly works
    widths = None  # FIXME: offer tabulation with 1 to N "\t" in place of 1 to N " "

    for width in reversed(range(1, len(cell_strs) + 1)):
        height = (len(cell_strs) + width - 1) // width
        assert (width * height) >= len(cell_strs)

        shafts = list()
        for shaft_index in range(width):
            shaft = cell_strs[(shaft_index * height) :][:height]
            shafts.append(shaft)

        floors = list()
        for floor_index in range(height):
            floor = list()
            for shaft in shafts:
                if floor_index < len(shaft):
                    str_cell = shaft[floor_index]
                    floor.append(str_cell)
            floors.append(floor)

        widths = len(floors[0]) * [
            0
        ]  # FIXME: stop requiring first row to be 1 of the longest
        for floor in floors:
            for (shaft_index, str_cell,) in enumerate(floor):
                widths[shaft_index] = max(widths[shaft_index], len(str_cell))

        sep = "  "
        if (sum(widths) + (len(sep) * (len(widths) - 1))) < columns:
            break

        if width == 1:
            break

    rows = list()
    for floor in floors:
        row = list()
        for (shaft_index, str_cell,) in enumerate(floor):
            padded_str_cell = str_cell.ljust(widths[shaft_index])
            row.append(padded_str_cell)
        rows.append(row)

    return rows


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
