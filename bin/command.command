#!/usr/bin/env python3

r"""
==== Usage

Download this file into a macOS Finder

Drag some files, and also this file, into a new folder

Try double-clicking this file, to see what it says and does

It will destroy/ recreate a subfolder named "__copies__"

It will copy the small text files in the folder with it into the new subfolder

It will mess with the copies as it makes copies

a )

In the "__copies__/expand/" subfolder, you'll see plain quotes and dashes, not special

b )

In the "__copies__/expand--repr/" subfolder, you'll see all the special chars called out
by number, such as the number \u005C Backslash of

    https://unicode.org/charts/PDF/U0000.pdf

c )

In the "__copies__/cp/" subfolder, you'll see copies of the originals

d )

Tell us what you think?


==== Troubleshooting

1 )

They may say

    The file "command.command" could
    not be executed because you do not have
    appropriate access privileges

    To view or change access privileges, ...

The workaround for that one is

    Finder > Go Utilities > Terminal

        cat command.command >command2.command

        chmod +x ../command2.command

"""


import collections
import difflib
import os
import shutil
import sys


FILE = os.path.splitext(os.path.split(__file__)[-1])[0]

FileVisit = collections.namedtuple(
    "FileVisit", "filename, file_bytes, file_chars".split(", ")
)


def main():
    """Run inside macOS when double-clicked"""

    stderr_print.separate_once = True

    # Focus on the folder enclosing this ".command" file

    file_dir = os.path.abspath(os.path.split(__file__)[0])
    os.chdir(file_dir)

    # Log where here is

    prefix = os.path.abspath(os.environ["HOME"])

    home_file_dir = file_dir
    if file_dir.startswith(prefix):
        beyond_prefix = len(prefix)
        home_file_dir = "~" + file_dir[beyond_prefix:]

    stderr_print("{}: Working at {}/".format(FILE, home_file_dir))

    # Recklessly destroy all past work, without backup

    where = "__copies__"

    stderr_print("{}: Destroying {}/".format(FILE, where))
    if os.path.exists(where):
        shutil.rmtree(where)

    stderr_print("{}: Creating {}/".format(FILE, where))
    os.makedirs(where)

    # Visit every file and dir in this folder, and fetch every small text file

    stderr_print.separate_once = True

    visits = list()

    for filename in os.listdir():
        main.filename = filename

        # Read the bytes of a small text file, else continue

        file_bytes = file_read_bytes(filename)

        if file_bytes is None:
            continue

        # Read the chars from the bytes, else continue

        try:
            file_chars = file_bytes.decode()
        except UnicodeDecodeError:
            file_chars = None

        if file_chars is None:
            continue

        visit = FileVisit(filename, file_bytes=file_bytes, file_chars=file_chars)
        visits.append(visit)

    # Export all formats

    file_export_formats(visits)


def bytes_expand_to_chars(file_bytes):
    r"""Replace all but Ascii chars with \u or \U escapes, but replace escapes too"""

    changes = 0

    # Replace all but Ascii chars with \u or \U escapes

    lines = list()
    for line_bytes in file_bytes.splitlines(keepends=True):

        # Pick the chars of the line apart from its end

        line_chars = line_bytes.decode()
        if line_chars.endswith("\n"):
            line_chars = line_chars[: -len("\n")]

        # Expand the escapes

        assert "\u005C" == "\\"
        assert "\u0055" == "U"
        assert "\u0075" == "u"

        picked_chars = line_chars
        picked_chars = picked_chars.replace(r"\u", "\u005C\u0075")
        picked_chars = picked_chars.replace(r"\U", "\u005C\u0055")

        # Expand the chars

        line = chars_expand_repr(picked_chars)
        if line != line_chars:
            changes += 1

        lines.append(line)

    changed_chars = "\n".join(lines) + "\n"

    # Log change

    if changes:
        stderr_print(
            "{}: Expand Repr tweaked {} lines of:  {}".format(
                FILE, changes, main.filename
            )
        )

    return changed_chars


def bytes_export_unchanged(bashline, filename, want):
    """Export bytes unchanged"""

    path = path_from_bashline(bashline, filename=filename)

    path_dir = os.path.split(path)[0]
    if not os.path.isdir(path_dir):
        os.makedirs(path_dir)

    with open(path, mode="wb") as outgoing:
        outgoing.write(want)


def chars_expand(chars):
    """Replace frequently troublesome special chars with plainer chars"""

    changes = 0

    # Expand each line

    changed_lines = list()
    for line in chars.splitlines():
        changed_line = line_expand(line).rstrip()
        if changed_line != line:
            changes += 1
        changed_lines.append(changed_line)

    # Strip empty lines, when leading and when trailing

    while changed_lines and not changed_lines[0]:
        changed_lines = changed_lines[1:]
        changes += 1

    while changed_lines and not changed_lines[-1]:
        changed_lines = changed_lines[:-1]
        changes += 1

    # End each line and end the chars

    changed_chars = "\n".join(changed_lines) + "\n"

    # Log change

    if chars != changed_chars:  # zero lines when only changing whitespace
        stderr_print(
            "{}: Expand tweaked {} lines of:  {}".format(FILE, changes, main.filename)
        )

    return changed_chars


def chars_expand_repr(chars):
    r"""
    Replace all but Ascii chars with \u or \U escapes

    Trust caller to replace escapes too
    """

    escaped = ""
    for ch in chars:
        if " " <= ch <= "~":
            escaped = escaped + ch
        elif ord(ch) <= 0xFFFF:
            escaped = escaped + r"\u{:04X}".format(ord(ch))
        else:
            escaped = escaped + r"\U{:08X}".format(ord(ch))

    return escaped


def chars_export(bashline, filename, want, got):
    """Export chars if changed"""

    if want == got:
        stderr_print("{}: No changes saved by:  {} {}".format(FILE, bashline, filename))
    else:

        path = path_from_bashline(bashline, filename=filename)

        path_dir = os.path.split(path)[0]
        if not os.path.isdir(path_dir):
            os.makedirs(path_dir)

        with open(path, mode="wt") as outgoing:
            outgoing.write(got)

        diff_export(bashline, filename=filename, want=want, got=got)


def diff_export(bashline, filename, want, got):
    """Export diff of lines"""

    diff_lines = difflib.unified_diff(
        a=got.splitlines(), b=want.splitlines(), fromfile=filename, tofile=filename
    )

    diff_chars = "\n".join(diff_lines) + "\n"

    diff_path = path_from_bashline(bashline, filename=os.path.join("diffs", filename))
    diff_path = diff_path.replace(".", "-") + ".diff"

    diff_dir = os.path.split(diff_path)[0]
    if not os.path.isdir(diff_dir):
        os.makedirs(diff_dir)

    with open(diff_path, mode="wt") as outgoing:
        outgoing.write(diff_chars)


def file_export_formats(visits):

    # Save the originals

    stderr_print.separate_once = True

    for visit in visits:
        main.filename = visit.filename

        cp_bytes = visit.file_bytes
        bytes_export_unchanged("cp.py", filename=visit.filename, want=cp_bytes)

    # Replace frequently troublesome special chars with plainer chars

    stderr_print.separate_once = True

    for visit in visits:
        main.filename = visit.filename

        expand_chars = chars_expand(visit.file_chars)
        chars_export(
            "expand.py",
            filename=visit.filename,
            want=expand_chars,
            got=visit.file_chars,
        )

    # Replace all but Ascii chars with \u or \U escapes, but replace escapes too

    stderr_print.separate_once = True

    for visit in visits:
        main.filename = visit.filename

        expand_repr_chars = bytes_expand_to_chars(visit.file_bytes)

        chars_export(
            "expand.py --repr",
            filename=visit.filename,
            want=expand_repr_chars,
            got=visit.file_chars,
        )

    # Give a quiet visible sign of work complete

    stderr_print.separate_once = True


def file_read_bytes(filename):
    """Read bytes from a file that feels like a small text file, else return None"""

    # Log file skipped because is more dir like

    if not os.path.isfile(filename):
        stderr_print("{}: Not working on {}, because not a file".format(FILE, filename))
        return None

    # Log file skipped because is large

    stats = os.stat(filename)
    if stats.st_size >= 1_000_000:
        stderr_print(
            "{}: Not working on {}, because too many bytes ({:_}) inside".format(
                FILE, filename, stats.st_size
            )
        )
        return None

    # Else read bytes of file

    with open(filename, "rb") as incoming:
        file_bytes = incoming.read()

    return file_bytes


def line_expand(line):
    """Replace frequently troublesome special chars with plainer chars"""

    changed = line

    changed = changed.replace("\u00A0", " ")  # u00A0 no-break space  # &nbsp;
    changed = changed.replace("«", '"')  # u00AB left-pointing double angle q~ mark
    changed = changed.replace("»", '"')  # u00BB right-pointing double angle q~ mark
    changed = changed.replace("\u200B", " ")  # u200B zero width space
    changed = changed.replace("–", "-")  # u2013 en dash
    changed = changed.replace("—", "--")  # u2014 em dash
    changed = changed.replace("\u2018", "'")  # u2018 left single quotation mark
    changed = changed.replace("’", "'")  # u2019 right single quotation mark
    changed = changed.replace("“", '"')  # u201C left double quotation mark
    changed = changed.replace("”", '"')  # u201D right double quotation mark
    changed = changed.replace("′", "'")  # u2032 prime
    changed = changed.replace("″", "''")  # u2033 double prime
    changed = changed.replace("‴", "'''")  # u2034 triple prime

    return changed


def path_from_bashline(bashline, filename):
    """Pick a Path from a Bashline applied to a Filename"""

    path = bashline
    path = path.replace(".py", "-py")
    path = path.replace(" ", "")

    path = os.path.join("__copies__", path, filename)

    return path


def stderr_print(*args):

    if stderr_print.separate_once:
        stderr_print.separate_once = False
        sys.stderr.write("\n")

    str_args = " ".join(str(_) for _ in args)
    sys.stderr.write("{}\n".format(str_args))

    sys.stderr.flush()


main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
