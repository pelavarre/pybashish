#!/usr/bin/env python3

r"""
usage: ls.py [-h] [-1] [-C] [-l] [--headings] [-a] [--full-time] [-F]
             [--sort FIELD] [-S] [-X] [-f] [-t] [-v] [--ascending]
             [--descending] [-r]

list the files and dirs inside a dir

optional arguments:
  -h, --help      show this help message and exit
  -1              print as column: one filename per line
  -C              print as zig-zag: filenames across one line, and more if need be (default: True)
  -l              print as rows of permissions, links, owner, group, size, date/time-stamp, name
  --headings      print as rows (a la -l), but start with one row of column headings
  -a, --all       list more rows: add the names starting with a "." dot
  --full-time     list more details: add the %a weekday and %f microseconds into date/time-stamps
  -F, --classify  lits more details: mark names as "/*@" for dirs, "chmod +x", and "ln -s"
  --sort FIELD    choose sort field by name: ext, name, none, time, or size
  -S              sort by size descending (or -r ascending)
  -X              sort by ext ascending (or -r descending)
  -f              sort by none and imply --all (like classic -f, distinct from Linux -U)
  -t              sort by time descending (or -r ascending)
  -v              sort by version ascending (or -r descending) (such as 3.2.1 before 3.10)
  --ascending     sort ascending:  newest to oldest, largest to smallest, etc
  --descending    sort descending:  newest to oldest, largest to smallest, etc
  -r              reverse the default sorts by size ascending, time ascending, name descending, etc

bugs:
  chokes over contradictions in args of how to print as or how to sort (last option doesn't win)
  doesn't show owner and group
  doesn't show size for dirs, and doesn't show size for links
  lists --full-time as to the microsecond not to the nanosecond, and without timezone
  marks names as r"[*/@]" on request, but doesn't yet notice r"[%=|]"
  marks lines as r"[-dl]" on request, but doesn't yet notice r"[bcps]"
  accepts --all, --classify, and --full-time to mean -a, -F, and --full-time (beyond Mac options)
  defines --headings, --ascending, --descending, and --sort=name (beyond the classic options)
  sees files as hidden if and only if name starts with "."

examples:
  ls
  ls -1
  ls -l
  ls -C
  bin/ls.py -alFt | tac  # at Linux
  bin/ls.py -alFt | tail -r  # at Mac
"""
# FIXME: add timezone to conform to --full-time output of Linux
# FIXME: add nanoseconds to conform to --full-time output of Linux
# FIXME: closer match at "ls.py -C" to classic line splits of "ls -C"
# FIXME argdoc: somehow separate -h / -1-C-l--h / -a--fu-F / -f-r--a--d-t-S-X--s=F
# FIXME: add -R recursive walk
# FIXME: add glob args
# FIXME: -w COLUMNS, --width COLUMNS  as if a terminal so wide
# FIXME: "import column" "import fmt" (or vice versa) to reach "def spill_cells" etc

from __future__ import print_function

import argparse
import datetime as dt
import distutils.version
import os
import stat
import sys

import argdoc


def main():
    """Interpret a command line"""

    tty = sketch_tty(sys.stdout)
    args = argdoc.parse_args()
    correct_args(args, tty=tty)
    print_each_top_walk(tops=[os.curdir], args=args, tty=tty)


def sketch_tty(stdio):
    """Mark this Terminal apart from others"""

    fd = stdio.fileno()
    isatty = os.isatty(fd)

    try:
        columns = os.get_terminal_size().columns
    except OSError:  # such as OSError: [Errno 25] Inappropriate ioctl for device
        columns = None

    tty = argparse.Namespace(columns=columns, isatty=isatty)

    return tty


def correct_args(args, tty):
    """Auto-correct else reject contradictions among the command line args"""

    _decide_print_as_args(args, tty=tty)
    _decide_sort_field_args(args)
    _decide_sort_order_args(args)


def _decide_print_as_args(args, tty):
    """Auto-correct else reject contradictions among which style to print finds as"""

    vote_cee = "-C" if args.C else ""
    vote_el = "-l" if args.l else ""
    vote_one = "-1" if vars(args)["1"] else ""
    vote_full_time = "--full-time" if args.full_time else ""
    vote_headings = "--headings" if args.headings else ""

    vote_args = (
        vote_cee,
        vote_el,
        vote_one,
        vote_full_time,
        vote_headings,
    )

    votes = (
        vote_cee,
        vote_el,
        vote_one or vote_full_time or vote_headings,
    )
    votes = tuple(_ for _ in votes if _)

    if len(votes) > 1:
        ballot = (
            "-1 -l -C --headings".split()
        )  # -1 simple, -l messy, -C classic, else --headings
        stderr_print(
            "ls.py: error: choose just one of {!r}, not the contradiction {!r}".format(
                " ".join(ballot), " ".join(vote_args)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    if not votes:
        if tty.isatty:
            vote_cee = True
        else:
            vote_one = True

    if vote_one:
        args._print_as = "column"
    elif vote_cee:
        args._print_as = "zigzag"
    else:
        args._print_as = "rows"


def _decide_sort_field_args(args):
    """Auto-correct else reject contradictions among which sort column to sort"""

    # Reject contradictions
    # FIXME: sort by multiple columns

    vote_ext = "-X" if args.X else ""
    vote_none = "-f" if args.f else ""
    vote_size = "-S" if args.S else ""
    vote_sort = "--sort={}".format(args.sort) if args.sort else ""
    vote_time = "-t" if args.t else ""
    vote_version = "-v" if args.v else ""

    votes = (
        vote_ext,
        vote_none,
        vote_size,
        vote_sort,
        vote_time,
        vote_version,
    )
    votes = tuple(_ for _ in votes if _)

    ballot = "-X -S -f -t --sort=ext|name|none|size|sort|time|version".split()
    if len(votes) > 1:
        stderr_print(
            "ls.py: error: choose just one of {!r}, not the contradiction {!r}".format(
                " ".join(ballot), " ".join(votes)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    # Expand abbreviations

    sortables = (
        "extension name none size time version".split()
    )  # allow "extension", not just Python "ext"

    args._sort_by = "name"
    if args.S:
        args._sort_by = "size"
    elif args.X:
        args._sort_by = "extension"
    elif args.f:
        args._sort_by = "none"  # distinct from Python str(None)
    elif args.t:
        args._sort_by = "time"
    elif args.v:
        args._sort_by = "version"
    elif args.sort:
        fields = list(_.startswith(args.sort) for _ in sortables)
        if len(fields) == 1:
            args._sort_by = fields[-1]
        else:

            # Reject unknown field names

            stderr_print(
                "ls.py: error: choose just one of {!r}, not the contradiction {!r}".format(
                    " ".join(ballot), " ".join(votes)
                )
            )
            sys.exit(2)  # exit 2 from rejecting usage

    assert args._sort_by in sortables


def _decide_sort_order_args(args):
    """Auto-correct else reject contradictions among which sort order to print as"""

    by = args._sort_by

    vote_ascending = "--ascending" if args.ascending else ""
    vote_descending = "--descending" if args.ascending else ""
    vote_reverse = "-r" if args.r else ""

    votes = (vote_ascending, vote_descending, vote_reverse)
    votes = tuple(_ for _ in votes if _)

    if len(votes) > 1:
        ballot = "-r --ascending --descending".split()
        stderr_print(
            "ls.py: error: choose just one of {!r}, not the contradiction {!r}".format(
                " ".join(ballot), " ".join(votes)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    if by == "none":
        args._sort_order = None
    elif by in "size time".split():
        args._sort_order = "ascending" if args.r else "descending"
    else:
        assert by in "extension name none version".split()
        args._sort_order = "descending" if args.r else "ascending"


def print_each_top_walk(tops, args, tty):
    """Print files and dirs found, as zigzag, column, or rows"""

    # Choose files and dirs

    assert len(tops) == 1
    top0 = tops[0]

    listed = [os.curdir, os.pardir] + os.listdir(top0)
    # FIXME: conform to Linux listing CurDir and ParDir in other places, unlike Mac Bash

    names = listed
    if not args.all:
        names = list(_ for _ in names if not _.startswith("."))
        # hidden file names start with "." at Mac and Linux, where:  os.name == "posix"

    # Collect stats for each

    stats_by_name = dict()
    for name in names:
        stats_by_name[name] = os.stat(name)

    # Mark each with r"[*/@]" for executable-not-dir, dir, or symbolic link

    names_by_name = {_: _ for _ in names}

    markeds_by_name = dict()
    for name in names:
        rep = mark_name(name, stats=stats_by_name[name])
        markeds_by_name[name] = rep

    reps_by_name = markeds_by_name if args.classify else names_by_name

    # Sort finds

    items = stats_items_sorted(stats_by_name, by=args._sort_by, order=args._sort_order)
    reps = list(reps_by_name[_[0]] for _ in items)

    # Print as one column of cells, as one zigzag of cells, or as one or more rows of columns

    now = dt.datetime.now()

    if args._print_as == "column":
        print_as_column(reps)
    elif args._print_as == "zigzag":
        print_as_zigzag(reps, tty=tty)
    else:
        assert args._print_as == "rows"
        print_as_rows(items, reps_by_name=reps_by_name, args=args, tty=tty, now=now)


def mark_name(name, stats):
    """Mark name with r"[*/@]" for executable-not-dir, dir, or symbolic link, else no mark"""

    isdir = os.path.isdir(name)
    stats_isdir = bool(stats.st_mode & stat.S_IFDIR)
    assert stats_isdir == isdir

    isx = bool(stats.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXGRP))

    islink = os.path.islink(name)

    mark = ""
    if isdir:
        mark = os.path.sep  # os.path.sep aka "/"
    elif isx:
        mark = "*"
    elif islink:
        mark = "@"

    rep = name + mark
    return rep


def stats_items_sorted(stats_by_name, by, order):
    """Return list of (key, value,) but sorted as requested"""

    items = list(stats_by_name.items())

    if by == "none":
        return items

    assert order in "ascending descending".split()
    py_sort_reverse = order == "descending"

    items.sort(key=lambda sw: sw[0])
    if by == "extension":
        items.sort(key=lambda sw: os.path.splitext(sw[0])[-1], reverse=py_sort_reverse)
    elif by == "name":  # sort by "name" here meaning sort by name+ext
        items.sort(key=lambda sw: sw[0], reverse=py_sort_reverse)
    elif by == "size":
        items.sort(key=lambda sw: sw[-1].st_size, reverse=py_sort_reverse)
    elif by == "time":
        items.sort(key=lambda sw: sw[-1].st_mtime, reverse=py_sort_reverse)
    elif by == "version":
        items.sort(
            key=lambda sw: distutils.version.LooseVersion(sw[0]),
            reverse=py_sort_reverse,
        )
    else:
        assert False

    return items


def print_as_column(cells):
    """Print as one column of names, marked or not"""

    for cell in cells:
        print(cell)


def print_as_rows(items, reps_by_name, args, tty, now):
    """Print as many rows of columns"""

    # Choose how to print None

    str_none = "."

    # Style chmod permissions

    chmod_chars = "drwxrwxrwx"
    chmod_masks = [stat.S_IFDIR]
    chmod_masks.extend([stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR])
    chmod_masks.extend([stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP])
    chmod_masks.extend([stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH])
    assert len(chmod_chars) == len(chmod_masks)

    # Form rows

    rows = list()

    if args.headings:  # chmod-perm's, links, owner, group, size, date/time-stamp, name
        row = "chmods links owner group size stamp name".split()
        rows.append(row)

    for (name, stats,) in items:

        chmods = ""
        for (char, mask,) in zip(chmod_chars, chmod_masks):
            chmods += char if (stats.st_mode & mask) else "-"

        links = str_none
        owner = str_none
        group = str_none

        stamp = dt.datetime.fromtimestamp(stats.st_mtime)
        if args.full_time:
            str_stamp = stamp.strftime("%a %Y-%m-%d %H:%M:%S.%f")
        else:  # FIXME: emulate the original over-packing date/time-stamp heuristics more closely
            if stamp.year == now.year:
                str_stamp = stamp.strftime("%b {:2d} %H:%M".format(stamp.day))
            else:
                str_stamp = stamp.strftime("%b {:2d}  %Y".format(stamp.day))

        size = str_none
        if chmods.startswith("-"):
            size = stats.st_size

        rep = reps_by_name[name]

        row = (chmods, links, owner, group, size, str_stamp, rep)
        rows.append(row)

    # Print rows

    if tty.isatty:
        print("total {}".format(str_none))  # not a count of 512-byte data blocks

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


def print_as_zigzag(cells, tty):

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

        # FIXME: stop requiring first row to be 1 of the longest
        widths = len(floors[0]) * [0]
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


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
