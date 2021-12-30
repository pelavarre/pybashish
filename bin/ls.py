#!/usr/bin/env python3

r"""
usage: ls.py [-h] [-1] [-C] [-l] [--headings] [-d] [-a] [--full-time] [-F]
             [--sort FIELD] [-S] [-X] [-f] [-t] [-v] [--ascending] [--descending] [-r]
             [TOP ...]

show the files and dirs inside a dir

positional arguments:
  TOP              the name of a dir or file to show

optional arguments:
  -h, --help       show this help message and exit
  -1               print as one column: one filename per line
  -C               print by filling multiple columns (default: True)
  -l               print as rows of perms, links, owner, group, size, date/time, name
  --headings       print as rows (a la -l), but start with one row of column headings
  -d, --directory  list less: each top as itself, omitting dirs and files inside
  -a, --all        list more: add the dirs and files whose names start with a "." dot
  --full-time      detail more: add the %a weekday and %f microseconds
  -F, --classify   detail more: mark names as "/*@" for dirs, "chmod +x", and "ln -s"
  --sort FIELD     choose sort field by name: ext, name, none, time, or size
  -S               sort by size descend (or -r ascend)
  -X               sort by ext ascend (or -r descend)
  -f               sort --all by none (like classic -f, distinct from Linux -U)
  -t               sort by time descend (or -r ascend)
  -v               sort by version ascend (or -r descend) (such as 3.2.1 before 3.10)
  --ascending      sort ascending:  newest to oldest, largest to smallest, etc
  --descending     sort descending:  newest to oldest, largest to smallest, etc
  -r               reverse defaults: name desc, size asc, ext desc, time asc, etc

temporary quirks:
  doesn't sort the files before the dirs when given both files and dirs as tops
  shows first failure to list a top and quit, not all failures vs successes

quirks:
  doesn't show owner and group
  doesn't show size for dirs, nor for links
  lists --full-time as to the microsecond, not to the nanosecond, and without timezone
  marks names as r"[*/@]" on request, but misses out on r"[%=|]"
  marks lines as r"[-dl]" on request, but misses out on r"[bcps]"
  accepts --all, --classify, and --full-time to mean -a, -F, and --full-time (beyond Mac options)
  defines --headings, --ascending, --descending, and --sort=name (beyond Mac and Linux)
  doesn't show dirs to pipe like to terminal, doesn't show one dir like one of more
  shows dirs in just one way, sorts by just one field, chokes when args call for more
  guesses -C terminal width from "COLUMNS", else sys.stdout, else "/dev/tty", else guesses 80
  slams a deleted dir as a "stale file handle", like later Linux, unlike Mac and older Linux
  sees files as hidden if and only if name starts with ".", as if just for Mac and Linux

examples:
  ls
  ls -1
  ls -l
  ls -C
  ls -alFt |tac  # reverse sort without ls -r at Linux
  ls -alFt |tail -r  # reverse sort without ls -r at Mac
  ls.py --headings
  COLUMNS=101 ls.py -C |tee as-wide-as-you-say.txt
  ls.py -C |tee as-wide-as-tty.txt
  (mkdir foo && cd foo/ && echo hi>x && rm -fr ../foo/ && ls.py .)
"""
# FIXME: add Linux -U like classic -f but without implying -a

# FIXME: -ll print header line "Mode Links Owner Group Bytes m d H:M Name\n"
# FIXME: -lll print blank line, header line, blank line, data lines, blank trailer line

# FIXME: add the --color that's missing at Mac
# FIXME: tell us about sym links that don't resolve
# FIXME FIXME:  -x               print by filling multiple rows
# FIXME: add -R recursive walk
# FIXME: closer match at "ls.py -C" to classic line splits of "ls -C"
# FIXME argdoc: somehow separate help lines for -1 -C -l --hea / -a --fu -F / --sort ...
# FIXME: share "def spill_cells" etc with "import column", "import fmt, etc
# FIXME: fix the "temporary" doesn't sort the files before the dirs when given both
# FIXME: shows only first failure to list a top and quit, should show all failures and successes


from __future__ import print_function

import argparse
import collections
import datetime as dt
import os
import stat
import subprocess
import sys

import argdoc

import pkg_resources  # in 2021, actually more native than "import distutils"


def main():
    """Interpret a command line"""

    stdout_isatty = sys.stdout.isatty()
    stdout_columns = sys_stdout_guess_tty_columns()

    args = argdoc.parse_args()
    correct_args(args, stdout_isatty=stdout_isatty, stdout_columns=stdout_columns)

    tops = args.tops if args.tops else [os.curdir]
    for index in range(len(tops)):
        print_one_top_walk(tops=tops, index=index, args=args)
        if args.directory:
            break


def correct_args(args, stdout_isatty, stdout_columns):
    """Auto-correct else reject contradictions among the command line args"""

    args.stdout_columns = stdout_columns

    print_as = _decide_print_as_args(args)

    args._print_as = print_as
    if not print_as:
        if stdout_isatty:
            args._print_as = "columns_of_names"
        else:
            args._print_as = "lines_of_names"

    args._print_total_row = None
    if args._print_as == "rows_of_detail":
        if stdout_isatty:  # FIXME: make --total=yes easy to add when not isatty
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
        vote_cee,  # -C => "columns_of_names"
        vote_el,  # -l => "rows_of_detail"
        vote_one,  # -1 => "lines_of_names"
        vote_full_time,  # implies -l "rows_of_detail"
        vote_headings,  # implies -l "rows_of_detail"
    )

    votes = (vote_cee, vote_el or vote_full_time or vote_headings, vote_one)
    votes = tuple(_ for _ in votes if _)

    if len(votes) > 1:
        ballot = (
            "-C -l -1 --full-time --headings".split()
        )  # -1 simple, -l messy, -C classic, else --headings
        stderr_print(
            "ls.py: error: "
            "choose just one of {!r}, not the style contradiction {!r}".format(
                " ".join(ballot), " ".join(vote_args)
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    args_print_as = None
    if votes:
        if vote_one:
            args_print_as = "lines_of_names"
        elif vote_cee:
            args_print_as = "columns_of_names"
        else:
            args_print_as = "rows_of_detail"

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

    (top, names, args_directory) = _plan_one_top_walk(tops, index=index, args=args)

    _run_one_top_walk(
        tops,
        index=index,
        top=top,
        names=names,
        args=args,
        args_directory=args_directory,
    )


def _plan_one_top_walk(tops, index, args):
    """Plan to run differently, as per -a and -d or not, as per top is dir or not"""

    # Pick apart dirs and files
    # FIXME: think well into mixing dirs and files, relpaths and abspaths, deleted and not

    args_directory = args.directory  # FIXME: better variable name than args_directory
    if args.directory:

        top = None
        listed = list(tops)

        names = listed
        if not args.all:
            names = list(_ for _ in names if not os.path.split(_)[-1].startswith("."))
            # hidden file names start with "." at Mac and Linux, per:  os.name == "posix"

    elif not os.path.isdir(tops[index]):

        args_directory = True
        top = None
        listed = [tops[index]]

        names = listed

    else:

        top = tops[index]

        listed = list()
        listed.append(os.curdir)
        listed.append(os.pardir)
        os_listdir_top = os.listdir(top)
        listed.extend(os_listdir_top)

        if os_path_isdir_deleted(
            top
        ):  # should be False, and unneeded, when not os_listdir_top
            stderr_print(
                "ls.py: warning: cannot access {!r}: stale file handle {}".format(
                    top, "of deleted dir"
                )
            )
            sys.exit(2)  # classic exit status 2 for a deleted dir

        names = listed
        if not args.all:
            names = list(_ for _ in names if not os.path.split(_)[-1].startswith("."))
            # hidden file names start with "." at Mac and Linux, per:  os.name == "posix"

    return (
        top,
        names,
        args_directory,
    )


def _run_one_top_walk(tops, index, top, names, args, args_directory):
    """Print files and dirs found, as lines of names, as a matrix of names, or as rows of detail"""

    # Trace the top and separate by blank line, if more than one top

    if not args_directory:
        print_as_plural_if_plural(tops, index)
    elif not args.directory:
        if len(tops) > 1:
            print()  # FIXME: sort the files before dirs when both tops

    # Find dirs and files inside this one top dir
    # FIXME: conform to Linux listing CurDir and ParDir in other places, unlike Mac Bash

    # Collect stats for each

    stats_by_name = dict()
    for name in names:
        wherewhat = name if args_directory else os.path.join(top, name)
        try:
            stats = os.stat(wherewhat)
        except FileNotFoundError as exc:
            stderr_print("ls.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)  # FIXME: defer the FileNotFoundError's to list the rest
        stats_by_name[name] = stats

    # Mark each with r"[*/@]" for executable-not-dir, dir, or symbolic link

    names_by_name = {_: _ for _ in names}

    markeds_by_name = dict()
    for name in names:
        wherewhat = name if args_directory else os.path.join(top, name)
        rep = mark_name(name=name, wherewhat=wherewhat, stats=stats_by_name[name])
        markeds_by_name[name] = rep

    reps_by_name = markeds_by_name if args.classify else names_by_name

    # Sort finds

    items = stats_items_sorted(stats_by_name, by=args._sort_by, order=args._sort_order)
    reps = list(reps_by_name[_[0]] for _ in items)

    # Print as one name per line, as columns or rows of names, or as rows of details

    now = dt.datetime.now()

    if args._print_as == "lines_of_names":
        print_as_lines_of_names(reps)
    elif args._print_as == "columns_of_names":
        print_as_matrix_of_names(reps, stdout_columns=args.stdout_columns)
    else:
        assert args._print_as == "rows_of_detail"
        print_as_rows_of_detail(
            tops,
            index=index,
            args=args,
            items=items,
            reps_by_name=reps_by_name,
            now_year=now.year,
            args_directory=args_directory,
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
    """Return list of (key, value) but sorted as requested"""

    items = list(stats_by_name.items())

    if by == "none":
        return items

    assert order in "ascending descending".split()
    reverse = True if (order == "descending") else False

    items.sort(key=lambda sw: sw[0])
    if by == "extension":
        items.sort(key=lambda sw: os.path.splitext(sw[0])[-1], reverse=reverse)
    elif by == "name":  # sort by "name" here meaning sort by name+ext
        items.sort(key=lambda sw: sw[0], reverse=reverse)
    elif by == "size":
        items.sort(key=lambda sw: sw[-1].st_size, reverse=reverse)
    elif by == "time":
        items.sort(key=lambda sw: sw[-1].st_mtime, reverse=reverse)
    elif by == "version":
        items.sort(key=lambda sw: looser_comparable_version(sw[0]), reverse=reverse)
    else:
        assert False

    return items


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def looser_comparable_version(vstring):
    """Workaround TypeError in LooseVersion comparisons between int and str"""
    # diffable = distutils.version.LooseVersion(vstring).version
    diffable = pkg_resources.parse_version(vstring)
    return diffable


def print_as_plural_if_plural(tops, index):
    """Trace the top and separate by blank line, if more than one top"""

    top = tops[index]
    if len(tops) > 1:
        if 0 < index < len(tops):
            print()
        print("{}:".format(top))


def print_as_lines_of_names(cells):
    """Print as one column of names, marked or not"""

    for cell in cells:
        print(cell)


def print_as_matrix_of_names(cells, stdout_columns):
    """Print as columns or rows of words"""

    sep = "  "
    rows = spill_cells(cells, columns=stdout_columns, sep=sep)
    for row in rows:
        print(sep.join(row).rstrip())


def print_as_rows_of_detail(
    tops, index, args, items, reps_by_name, now_year, args_directory
):
    """Print as rows of details, for one name per line"""

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

    for (name, stats) in items:

        chmods = ""
        for (char, mask) in zip(chmod_chars, chmod_masks):
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

    print_the_formed_rows(
        rows, str_none=str_none, args=args, args_directory=args_directory
    )


def print_the_formed_rows(rows, str_none, args, args_directory):

    # Print rows

    if args._print_total_row:
        if args_directory and not args.directory:
            pass
        else:
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
        for (index, cell) in enumerate(row):
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


def spill_cells(cells, columns, sep):  # FIXME FIXME FIXME  # noqa C901

    #

    cell_strs = list(str(c) for c in cells)

    no_floors = list()
    if not cell_strs:
        return no_floors

    #

    floors = None  # FIXME: review spill_cells closely, now that it mostly works
    widths = None  # FIXME: offer tabulation with 1 to N "\t" in place of 1 to N " "

    for width in reversed(range(1, len(cell_strs) + 1)):
        height = (len(cell_strs) + width - 1) // width
        assert (width * height) >= len(cell_strs)

        # Fill each shaft in order, let the last shaft stop short
        # FIXME: Option to fill each floor in order, let the last floor stop short

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

        # Count out the width of each shaft

        widths = collections.defaultdict(int)
        for floor in floors:
            for (shaft_index, str_cell) in enumerate(floor):
                widths[shaft_index] = max(widths[shaft_index], len(str_cell))

        # Take the first matrix that fits, else the last matrix tried
        # FIXME: Print it to see if it fits

        sep = "  "
        if (sum(widths.values()) + (len(sep) * (width - 1))) < columns:
            break

        if width == 1:
            break

    # Print the matrix

    rows = list()
    for floor in floors:
        row = list()
        for (shaft_index, str_cell) in enumerate(floor):
            padded_str_cell = str_cell.ljust(widths[shaft_index])
            row.append(padded_str_cell)
        rows.append(row)

    return rows


# deffed in many files  # missing from docs.python.org
def sys_stdout_guess_tty_columns(*hints):
    """
    Run all the searches offered, accept the first result found if any, else return None

    Default to search:  "COLUMNS", sys.stdout, "/dev/tty", 80

    To fail fast, call for all the guesses always, while still returning only the first that works
    """

    chosen_hints = hints if hints else ("COLUMNS", sys.stdout, "/dev/tty", 80)
    # FIXME: port to "/dev/tty" outside of Mac and Linux

    terminal_widths = list()
    for hint in chosen_hints:

        terminal_width = sys_stdout_guess_tty_columns_os(hint)
        if terminal_width is None:
            terminal_width = sys_stdout_guess_tty_columns_os_environ_int(hint)
        else:
            _ = sys_stdout_guess_tty_columns_os_environ_int(hint)

        if terminal_width is not None:
            terminal_widths.append(terminal_width)

    if terminal_widths:
        terminal_width = terminal_widths[0]

        return terminal_width


# deffed in many files  # missing from docs.python.org
def sys_stdout_guess_tty_columns_os(hint):
    """Try "os.get_terminal_size", and slap back "shutil.get_terminal_size" pushing (80, 24)"""

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
def sys_stdout_guess_tty_columns_os_environ_int(hint):
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
def os_path_isdir_deleted(top):  # FIXME: solve this without calling:  bash /dev/null
    """Mark a deleted dir apart from undeleted dirs, even if working inside of it"""

    run = subprocess_run(
        "bash /dev/null".split(),
        cwd=top,
        stdin=subprocess.PIPE,  # FIXME FIXME: how often should .run.stdin be PIPE?
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if run.stdout or run.stderr or run.returncode:
        return True


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(*args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to say:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(*args, **kwargs)

        return run

    # Emulate the library roughly, because often good enough

    args_ = args[0] if args else kwargs["args"]
    kwargs_ = dict(**kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    if ("input" in kwargs) and ("stdin" in kwargs):
        raise ValueError("stdin and input arguments may not both be used.")

    if "input" in kwargs:
        raise NotImplementedError("subprocess.run.input")

    sub = subprocess.Popen(*args, **kwargs_)
    (stdout, stderr) = sub.communicate()
    returncode = sub.poll()

    run = argparse.Namespace(
        args=args_, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
