#!/usr/bin/env python3

r"""
usage: ls.py [-h] [-1] [-C] [-F] [-a] [-l] [-t]

list the files and dirs inside a dir

optional arguments:
  -h, --help      show this help message and exit
  -1              print one filename per line
  -C              print filenames into multiple columns (default: True)
  -F, --classify  mark names as "/*@" for dirs, "chmod +x", and "ln -s"
  -a, --all       show, don't drop, names starting with a "." dot
  -l              list more, such as also the date-time modified
  -t              sort by time descending

bugs:
  defaults to --fulltime inside any -l
  chokes over -1 -C -l contradictions
  marks names as "/*@" on request, but doesn't yet notice "=%|"
  marks lines as "dl-" on request, but doesn't yet notice "bcsp"
  doesn't show size for dirs, and doesn't show size for links
  sees files as hidden if and only if name starts with "."

examples:
  ls
  ls -1
  ls -l
  ls -C
  bin/ls.py -alFt | tac  # at Linux
  bin/ls.py -alFt | tail -r  # at Mac
"""
# FIXME FIXME: add --fulltime toggle, conform --fulltime output to Linux
# FIXME FIXME: add -rt
# FIXME: add -R
# FIXME: add glob args
# FIXME: -w COLUMNS, --width COLUMNS  as if a terminal so wide
# FIXME: "import column" "import fmt" (or vice versa) to reach "def spill_cells" etc

from __future__ import print_function

import argparse
import datetime as dt
import os
import stat
import sys

import argdoc


def main():

    tty = sketch_tty(sys.stdout)
    args = parse_main_args(tty)
    main.args = args
    run_main_tty_args(tty, args=args)


def sketch_tty(stdout):

    isatty = os.isatty(stdout.fileno())

    try:
        columns = os.get_terminal_size().columns
    except OSError:  # such as OSError: [Errno 25] Inappropriate ioctl for device
        columns = None

    space = argparse.Namespace(columns=columns, isatty=isatty)

    return space


def parse_main_args(tty):

    args = argdoc.parse_args()

    #

    dash_el = vars(args)["l"]
    dash_cee = vars(args)["C"]
    dash_one = vars(args)["1"]

    lc1 = "-"
    lc1 += "l" if dash_el else ""
    lc1 += "C" if dash_cee else ""
    lc1 += "1" if dash_one else ""

    if len(lc1) > 2:
        dash_opts = list(("-" + _) for _ in "lC1")
        stderr_print(
            "ls.py: error: choose one of {!r}, do not choose {!r}".format(
                dash_opts, lc1
            )
        )
        sys.exit(1)

    if len(lc1) < 2:
        if tty.isatty:
            dash_cee = True

    args.dash_el = dash_el
    args.dash_cee = dash_cee
    args.dash_one = dash_one

    #

    return args


def run_main_tty_args(tty, args):

    listed = os.listdir()  # FIXME: implement options to do no sorting
    if args.all:
        whats = sorted(listed + [os.curdir, os.pardir])
    else:
        whats = sorted(_ for _ in listed if not _.startswith("."))
        # hidden file names start with "." at Mac and Linux, where:  os.name == "posix"

    stats_by_what = dict()
    for what in whats:
        stats_by_what[what] = os.stat(what)

    marked_names_by_what = dict()
    for what in whats:
        stats = stats_by_what[what]
        marked_name = mark_name(what, stats=stats)
        marked_names_by_what[what] = marked_name

    if args.dash_one:
        run_dash_one(marked_names_by_what.values() if args.classify else whats)
    elif args.dash_el:
        run_dash_el(
            tty,
            stats_by_what=stats_by_what,
            marked_names_by_what=(marked_names_by_what if args.classify else None),
        )
    else:
        assert args.dash_cee
        run_dash_cee(
            tty, cells=(marked_names_by_what.values() if args.classify else whats)
        )


def mark_name(what, stats):

    isdir = os.path.isdir(what)
    stats_isdir = bool(stats.st_mode & stat.S_IFDIR)
    assert stats_isdir == isdir

    isx = bool(stats.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXGRP))

    islink = os.path.islink(what)

    mark = ""
    if isdir:
        mark = os.path.sep  # os.path.sep aka "/"
    elif isx:
        mark = "*"
    elif islink:
        mark = "@"

    marked_name = what + mark
    return marked_name


def run_dash_one(cells):

    for cell in cells:
        print(cell)


def run_dash_el(tty, stats_by_what, marked_names_by_what):

    nil = "."

    chmod_chars = "drwxrwxrwx"
    chmod_masks = [stat.S_IFDIR]
    chmod_masks.extend([stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR])
    chmod_masks.extend([stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP])
    chmod_masks.extend([stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH])
    assert len(chmod_chars) == len(chmod_masks)

    items = list(stats_by_what.items())
    if main.args.t:
        items.sort(key=lambda sw: (sw[1].st_mtime, sw,), reverse=True)

    rows = list()
    for (what, stats,) in items:

        chmods = ""
        for (char, mask,) in zip(chmod_chars, chmod_masks):
            chmods += char if (stats.st_mode & mask) else "-"

        links = nil
        owner = nil
        group = nil

        stamp = dt.datetime.fromtimestamp(stats.st_mtime)
        str_stamp = stamp.strftime("%a %Y-%m-%d %H:%M:%S.%f")

        size = nil
        if chmods.startswith("-"):
            size = stats.st_size

        name = marked_names_by_what[what] if marked_names_by_what else what

        row = (
            chmods,
            links,
            owner,
            group,
            size,
            str_stamp,
            name,
        )
        rows.append(row)

    if tty.isatty:
        print("total {}".format(nil))  # not a count of 512-byte data blocks

    justifieds = left_justify_cells_in_rows(rows)
    for justified in justifieds:
        print("  ".join(justified))


def left_justify_cells_in_rows(rows):
    """Pad each cell on the right till each column lines up vertically"""

    # Convert each cell to string

    strung_rows = list(list(str(cell) for cell in row) for row in rows)

    # Add empty cells till every row is as wide as the widest row
    # completed_rows = complete_rows(strung_rows, cell="")  # FIXME
    completed_rows = strung_rows

    # Measure max width per column

    widths = list(list(len(cell) for cell in row) for row in completed_rows)
    max_column_widths = list(max(column_widths) for column_widths in zip(*widths))

    # Align every cell of every row, to left of column or to right of column

    justified_rows = list()
    for row in completed_rows:

        justified_row = list()
        for (index, cell,) in enumerate(row):
            if index == 4:  # FIXME: inconceivable hack
                justified_cell = cell.rjust(max_column_widths[index])
            else:
                justified_cell = cell.ljust(max_column_widths[index])
            justified_row.append(justified_cell)

        justified_rows.append(justified_row)

    # Succeed

    return justified_rows


def run_dash_cee(tty, cells):

    columns_ = 89 if (tty.columns is None) else tty.columns

    sep = "  "
    rows = spill_cells(cells, columns=columns_, sep=sep)
    for row in rows:
        print(sep.join(row).rstrip())


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


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
