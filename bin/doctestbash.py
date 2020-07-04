#!/usr/bin/env python3

r"""
usage: doctestbash.py [-h] [-b] [-q] [-v] [FILE [FILE ...]]

Test if Bash behaves as the transcripts say it should

positional arguments:
  FILE                  Folders or files of '.typescript' files

optional arguments:
  -h, --help            show this help message and exit
  -b, --rip-bash-paste  copy the Bash input lines out of the transcript, but don't run them
  -q, --quiet           say less
  -v, --verbose         say more

examples:
  cp doctestbash.py doctestbash.doctestbash && ./doctestbash.py $PWD

notes:
  compare Python "import doctest"
"""
# FIXME: walk for exts
# FIXME FIXME: rip Bash paste distinguished only by repeated prompt ending in '$' or '#'
# FIXME FIXME: rip Python paste, not just Bash paste
# FIXME: rip Makefile paste, not just Bash paste

import doctest
import os
import subprocess
import sys

import argdoc


def main(argv):

    # Parse args

    args = argdoc.parse_args()
    args.vq = (args.verbose if args.verbose else 0) - (args.quiet if args.quiet else 0)
    main.args = args

    assert not args.files

    # Test the one well known file

    file_dir = os.path.split(__file__)[0]
    tests_dir = os.path.join(file_dir, os.pardir, "tests")
    args_file = os.path.join(tests_dir, "pybashish.typescript")
    args_file = os.path.relpath(args_file)

    with open(args_file) as incoming:
        passes = _run_bash_test_doc(incoming, args_file=args_file)

    # Declare success

    if not args.rip_bash_paste:
        stderr_print("doctestbash.py: {} tests passed".format(passes))

    # Call one Python Doc Test, just to help people reviewing the code find that precedent

    _show_doctest_result()


def _show_doctest_result(want="2.718"):
    """Show a Python Doc Test passing, for comparison with these Bash Doc Tests"""

    f = """
    >>> import math
    >>> math.e
    {}...
    >>>
    """.format(
        want
    )

    globs = dict()

    doctest.run_docstring_examples(f, globs, optionflags=doctest.ELLIPSIS)


def _run_bash_test_doc(incoming, args_file):
    """Run each test of a Bash Test Doc"""

    passes = 0

    line = incoming.readline()
    while line:

        # Take one more test, else break

        (line_, dent, shline, doc_lines, wants,) = take_one_test(
            incoming, line
        )  # FIXME: collections.namedtuple

        line = line_  # FIXME: don't so much hack up a stream with one line of lookahead

        if shline is None:
            assert wants is None
            break

        if main.args.rip_bash_paste:
            print(shline)
            sys.stdout.flush()
            if shline:
                passes += 1
            continue

        if not shline:
            separators = list(doc_lines)
            while separators and not separators[-1]:
                vv_print()
                separators = separators[:-1]
            continue

        if main.args.vq == len("v"):
            stderr_print(passes)
            stderr_print("+ {}".format(shline))

        # Test input

        gots = run_one_shline(shline)

        # Require correct output

        require_test_passed(args_file, passes=passes, gots=gots, dent=dent, wants=wants)

        # Count passed tests

        passes += 1

    return passes


def split_dent(line):
    """Split apart the indentation of a line, from the remainder of the line"""

    text = line.rstrip()
    len_dent = len(text) - len(text.lstrip())
    dent = len_dent * " "

    remainder = line[len(dent) :]

    return (
        dent,
        remainder,
    )


def take_one_test(incoming, line):
    """Take one test from the incoming stream: comments, one input line, outputs"""

    prompt = "$ "

    shline = None
    doc_lines = None
    wants = None

    # Take comments

    text = None

    while line:

        (dent, text,) = split_dent(line.rstrip())
        vv_print(dent + text)

        if not text.startswith(prompt) and text != prompt.strip():
            line = incoming.readline()
            continue

        break

    if not line:

        return (
            line,
            dent,
            shline,
            doc_lines,
            wants,
        )

    # Take input

    shline = text[len(prompt) :]
    line = incoming.readline()

    # Take output

    doc_lines = list()

    while line:
        (dent_, text_,) = split_dent(line.rstrip())

        wanted = False
        if not text_:
            wanted = (
                True  # let transcripts contain blank lines, unlike "import doctest"
            )
        if dent_.startswith(dent):
            if dent_ != dent:
                wanted = True
            elif not text_.startswith(prompt) and text_ != prompt.strip():
                wanted = True

        if not wanted:
            break

        doc_lines.append(text_.rstrip())
        line = incoming.readline()

    wants = "\n".join(doc_lines).strip().splitlines()

    return (
        line,
        dent,
        shline,
        doc_lines,
        wants,
    )


def run_one_shline(shline):

    ran = subprocess.run(
        shline, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    assert (
        not ran.stderr
    )  # because Stderr all folded into Stdout by "subprocess.STDOUT"

    gots = ran.stdout.decode().strip().replace("\r\n", "\n").splitlines()
    if ran.returncode:
        gots.append("+ exit {}".format(ran.returncode))

    return gots


def require_test_passed(args_file, passes, gots, dent, wants):
    """Raise exception, unless actual output roughly equals expected output"""

    max_len = max(len(wants), len(gots))
    min_len = min(len(wants), len(gots))
    empties = (max_len - min_len) * [""]

    for (want, got,) in zip(wants + empties, gots + empties):
        if got != want:

            try:
                assert equal_but_for_ellipses(got, want)
            except AssertionError:

                vv_print()
                vv_print()

                vv_print("wants ......: {}".format(repr(wants)))
                vv_print()
                vv_print("but gots ...: {}".format(repr(gots)))
                vv_print()
                vv_print()

                vv_print("want ......: {}".format(want))
                vv_print("but got ...: {}".format(got))
                vv_print()
                vv_print()

                ellipsis = "..."
                if ellipsis in want:

                    vv_print("want splits ......: {}".format(want.split(ellipsis)))
                    vv_print("but got ..........: {}".format(repr(got)))
                    vv_print()
                    vv_print()

                reasons = list()
                reasons.append("unexpected output after {} tests:".format(passes))
                if main.args.vq < len("vv"):
                    reasons.append("try again with -vv")
                reasons.append(
                    "fix the code, and/or fix the test at:  vim {}".format(args_file)
                )

                for reason in reasons:
                    stderr_print("doctestbash.py: error: {}".format(reason))

                sys.exit(1)

        vv_print(dent + got)


def equal_but_for_ellipses(got, want):
    """Compare two strings, but match "..." to zero or more characters"""

    ellipsis = "..."

    given = got.rstrip()
    musts = want.rstrip().split(ellipsis)

    for must in musts:
        assert must in given
        must_at = given.index(must)
        given = given[must_at:][len(must) :]

    assert not given  # FIXME: incomplete equal_but_for_ellipses

    return True


def vv_print(*args):
    if main.args.vq >= 2:
        stderr_print(*args)


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
