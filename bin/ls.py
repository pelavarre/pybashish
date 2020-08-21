#!/usr/bin/env python3

r"""
usage: ls.py [-h] [-1] [-C] [-l] [--headings] [-d] [-a] [--full-time] [-F]
             [--sort FIELD] [-S] [-X] [-f] [-t] [-v] [--ascending]
             [--descending] [-r]
             [TOP [TOP ...]]

show the files and dirs inside a dir

positional arguments:
  TOP              the name of a dir or file to show

optional arguments:
  -h, --help       show this help message and exit
  -1               print as column: one filename per line
  -C               print as zig-zag: filenames across one line, and more if need be (default: True)
  -l               print as rows of permissions, links, owner, group, size, date/time-stamp, name
  --headings       print as rows (a la -l), but start with one row of column headings
  -d, --directory  list less rows: each top only as itself, omitting the dirs and files inside it
  -a, --all        list more rows: add the names starting with a "." dot
  --full-time      list more details: add the %a weekday and %f microseconds into date/time-stamps
  -F, --classify   list more details: mark names as "/*@" for dirs, "chmod +x", and "ln -s"
  --sort FIELD     choose sort field by name: ext, name, none, time, or size
  -S               sort by size descending (or -r ascending)
  -X               sort by ext ascending (or -r descending)
  -f               sort by none and imply --all (like classic -f, distinct from Linux -U)
  -t               sort by time descending (or -r ascending)
  -v               sort by version ascending (or -r descending) (such as 3.2.1 before 3.10)
  --ascending      sort ascending:  newest to oldest, largest to smallest, etc
  --descending     sort descending:  newest to oldest, largest to smallest, etc
  -r               reverse the default sorts by size ascending, time ascending, name descending, etc

bugs:
  doesn't show owner and group
  doesn't show size for dirs, nor for links
  lists --full-time as to the microsecond, not to the nanosecond, and without timezone
  marks names as r"[*/@]" on request, but misses out on r"[%=|]"
  marks lines as r"[-dl]" on request, but misses out on r"[bcps]"
  accepts --all, --classify, and --full-time to mean -a, -F, and --full-time (beyond Mac options)
  defines --headings, --ascending, --descending, and --sort=name (beyond Mac and Linux)
  falls back to "/dev/tty" for "ls -C" width when stdout is not a tty (beyond Mac and Linux)
  doesn't show dirs to pipe like to terminal, doesn't show one dir like one of more
  shows dirs in just one way, sorts by just one field, chokes when args call for more
  sees files as hidden if and only if name starts with ".", as if just for Mac and Linux

examples:
  ls
  ls -1
  ls -l
  ls -C
  ls -alFt | tac  # reverse sort without ls -r at Linux
  ls -alFt | tail -r  # reverse sort without ls -r at Mac
  bin/ls.py --headings
  COLUMNS=101 ls -C | tee as-wide-as-you-say.txt
  bin/ls.py -C | tee as-wide-as-tty.txt
"""
# FIXME: add -R recursive walk
# FIXME: closer match at "ls.py -C" to classic line splits of "ls -C"
# FIXME argdoc: somehow separate help lines for -1 -C -l --hea / -a --fu -F / --sort ...
# FIXME: "import column" "import fmt" (or vice versa) to reach "def spill_cells" etc

from __future__ import print_function

import datetime as dt
import distutils.version
import os
import stat
import sys

import argdoc


def main():
    """Interpret a command line"""

    stdout_isatty = sys.stdout.isatty()
    stdout_columns = guess_stdout_columns()
    # FIXME: port to "/dev/tty" outside of Mac and Linux

    args = argdoc.parse_args()
    correct_args(args, stdout_isatty=stdout_isatty, stdout_columns=stdout_columns)

    tops = args.tops if args.tops else [os.curdir]
    for index in range(len(tops)):
        print_one_top_walk(tops=tops, index=index, args=args)
        if args.directory:
            break


def correct_args(args, stdout_isatty, stdout_columns):
    """Auto-correct else reject contradictions among the command line args"""

    print_as = _decide_print_as_args(args)

    args._print_as = print_as
    if not print_as:
        if stdout_isatty:
            args._print_as = "zigzag"
        else:
            args._print_as = "column"

    args._zigzag_columns = None
    if args._print_as == "zigzag":
        args._zigzag_columns = stdout_columns

    args._print_total_row = None
    if args._print_as == "rows":
        if stdout_isatty:
            args._print_total_row = True

    args._sort_by = _decide_sort_field_args(args)
    args._sort_order = _decide_sort_order_args(args)


def _decide_print_as_args(args):
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
            "ls.py: error: choose just one of {!r}, not the style contradiction {!r}".format(
                " ".join(ballot), " ".join(vote_args)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    args_print_as = None
    if votes:
        if vote_one:
            args_print_as = "column"
        elif vote_cee:
            args_print_as = "zigzag"
        else:
            args_print_as = "rows"

    return args_print_as


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
            "ls.py: error: choose just one of {!r}, not the sort contradiction {!r}".format(
                " ".join(ballot), " ".join(votes)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    # Expand abbreviations

    sortables = (
        "extension name none size time version".split()
    )  # allow "extension", not just Python "ext"

    args_sort_by = "name"
    if args.S:
        args_sort_by = "size"
    elif args.X:
        args_sort_by = "extension"
    elif args.f:
        args_sort_by = "none"  # distinct from Python str(None)
    elif args.t:
        args_sort_by = "time"
    elif args.v:
        args_sort_by = "version"
    elif args.sort:
        fields = list(_ for _ in sortables if _.startswith(args.sort))
        if len(fields) == 1:
            args_sort_by = fields[-1]
        else:

            # Reject unknown field names

            stderr_print(
                "ls.py: error: choose just one of {!r}, not the field contradiction {!r}".format(
                    " ".join(ballot), " ".join(votes)
                )
            )
            sys.exit(2)  # exit 2 from rejecting usage

    assert args_sort_by in sortables

    return args_sort_by


def _decide_sort_order_args(args):
    """Auto-correct else reject contradictions among which sort order to print as"""

    by = args._sort_by

    vote_ascending = "--ascending" if args.ascending else ""
    vote_descending = "--descending" if args.descending else ""
    vote_reverse = "-r" if args.r else ""

    votes = (vote_ascending, vote_descending, vote_reverse)
    votes = tuple(_ for _ in votes if _)

    if len(votes) > 1:
        ballot = "-r --ascending --descending".split()
        stderr_print(
            "ls.py: error: choose just one of {!r}, not the order contradiction {!r}".format(
                " ".join(ballot), " ".join(votes)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    if by == "none":
        default_sort_order = None
    elif by in "size time".split():
        default_sort_order = "ascending" if args.r else "descending"
    else:
        assert by in "extension name none version".split()
        default_sort_order = "descending" if args.r else "ascending"

    args_sort_order = default_sort_order
    if args.ascending:
        assert not args.descending
        args_sort_order = "ascending"
    elif args.descending:
        assert not args.ascending
        args_sort_order = "descending"

    return args_sort_order


def print_one_top_walk(tops, index, args):
    """Print files and dirs found, as zigzag, column, or rows"""

    # Trace the top and separate by blank line, if more than one top

    if not args.directory:
        print_as_plural_if_plural(tops, index)

    # Find dirs and files inside this one top dir
    # FIXME: conform to Linux listing CurDir and ParDir in other places, unlike Mac Bash

    top = tops[index]
    if args.directory:
        listed = list(tops)
    else:
        listed = [os.curdir, os.pardir] + os.listdir(top)

    names = listed
    if not args.all:
        names = list(_ for _ in names if not _.startswith("."))
        # hidden file names start with "." at Mac and Linux, per:  os.name == "posix"

    # Collect stats for each

    stats_by_name = dict()
    for name in names:
        wherewhat = name if args.directory else os.path.join(top, name)
        stats_by_name[name] = os.stat(wherewhat)

    # Mark each with r"[*/@]" for executable-not-dir, dir, or symbolic link

    names_by_name = {_: _ for _ in names}

    markeds_by_name = dict()
    for name in names:
        wherewhat = name if args.directory else os.path.join(top, name)
        rep = mark_name(name=name, wherewhat=wherewhat, stats=stats_by_name[name])
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
        print_as_zigzag(reps, stdout_columns=args._zigzag_columns)
    else:
        assert args._print_as == "rows"
        print_as_rows(
            tops,
            index=index,
            args=args,
            items=items,
            reps_by_name=reps_by_name,
            now_year=now.year,
        )


def mark_name(name, wherewhat, stats):
    """Mark name with r"[*/@]" for executable-not-dir, dir, or symbolic link, else no mark"""

    isdir = os.path.isdir(wherewhat)
    stats_isdir = bool(stats.st_mode & stat.S_IFDIR)
    assert stats_isdir == isdir

    isx = bool(stats.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXGRP))

    islink = os.path.islink(wherewhat)

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
    py_sort_reverse = True if (order == "descending") else False

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
            key=lambda sw: looser_comparable_version(sw[0]), reverse=py_sort_reverse,
        )
    else:
        assert False

    return items


# deffed in many files  # missing from docs.python.org
def looser_comparable_version(vstring):
    """Workaround TypeError in LooseVersion comparisons between int and str"""

    diffables = list()

    words = distutils.version.LooseVersion(vstring).version

    ints = list()
    strs = list()
    for word in words:
        if isinstance(word, int):
            if strs:
                diffables.extend([ints, strs])
                strs = list()
            ints.append(word)
        elif (
            type(word).__mro__[-2] is str.__mro__[-2]
        ):  # aka Python 3 isinstance(_, str)
            if ints:
                diffables.extend([ints, strs])
                ints = list()
            strs.append(word)
        else:
            assert False

    if ints or strs:
        diffables.extend([ints, strs])

    return diffables


def print_as_plural_if_plural(tops, index):
    """Trace the top and separate by blank line, if more than one top"""

    top = tops[index]
    if len(tops) > 1:
        if 0 < index < len(tops):
            print()
        print("{}:".format(top))


def print_as_column(cells):
    """Print as one column of names, marked or not"""

    for cell in cells:
        print(cell)


def print_as_zigzag(cells, stdout_columns):
    """Print as lines of words"""

    sep = "  "
    rows = spill_cells(cells, columns=stdout_columns, sep=sep)
    for row in rows:
        print(sep.join(row).rstrip())


def print_as_rows(tops, index, args, items, reps_by_name, now_year):
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
        if index == 0:
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
            if stamp.year == now_year:
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

    if args._print_total_row:
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

        if len(row):
            justified_row[-1] = row[-1]  # no padding past right column

        justified_rows.append(justified_row)

    # Succeed

    return justified_rows


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
def guess_stdout_columns(*hints):
    """
    Run all the searches offered, accept the first result found if any, else assert False

    Default to search:  "COLUMNS", sys.stdout, "/dev/tty", 80

    To fail fast, call for all the guesses always, but still just return the first that works
    """

    chosen_hints = hints if hints else ("COLUMNS", sys.stdout, "/dev/tty", 80,)

    terminal_widths = list()
    for hint in chosen_hints:

        terminal_width = guess_stdout_columns_os(hint)
        if terminal_width is not None:
            _ = guess_stdout_columns_os_environ_int(hint)
        else:
            terminal_width = guess_stdout_columns_os_environ_int(hint)

        if terminal_width is not None:
            terminal_widths.append(terminal_width)

    if terminal_widths:
        terminal_width = terminal_widths[0]

        return terminal_width

    assert False


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
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
