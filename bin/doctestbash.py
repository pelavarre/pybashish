#!/usr/bin/env python3

"""
usage: doctestbash.py [-h] [-b] [-q] [-v] [FILE [FILE ...]]

test if bash behaves as the transcripts say it should

positional arguments:
  FILE                  folders or files of '.typescript' files (default: cwd)

optional arguments:
  -h, --help            show this help message and exit
  -b, --rip-bash-paste  copy the bash input lines out of the transcript, but don't run them
  -q, --quiet           say less
  -v, --verbose         say more

quirks:
  always tests only the files at "tests/"
  only finds "tests/pybashish.typescript" when searching "tests/"
  prints the actual output, even when matching it to "..." (unlike classic doctest)
  allows blank lines in output to mean blank lines (unlike classic doctest)

examples:
  mkdir -p tests/
  cp -ip doctestbash.py tests/pybashish.typescript && ./doctestbash.py $PWD

see also:  python "import doctest"
"""

# FIXME: defer failing the test till after all its output prints
# FIXME: work up how to take all their changes from the code

# FIXME: let '>' prompts of Bash continue '$' prompts of Bash
# FIXME: learn the '<<-EOF' here docs, but accept blanks as tabs
# FIXME: walk for exts
# FIXME: rip Bash paste distinguished only by repeated prompt ending in '$' or '#'
# FIXME: rip Python '>>>' paste, and Makefile paste, and Zsh '%' paste, not just Bash paste

# FIXME: think harder when no files chosen


import argparse
import doctest
import os
import subprocess
import sys

import argdoc


def main(argv):
    """Run from the Command Line"""

    # Parse args

    args = argdoc.parse_args()
    args.vq = (args.verbose if args.verbose else 0) - (args.quiet if args.quiet else 0)

    main.args = args

    # Require one or more args

    if not args.files:
        stderr_print(
            "doctestbash.py: error: the following arguments are required: FILE"
        )
        sys.exit(2)

    # Work each arg in order

    for args_file in args.files:
        if not os.path.isdir(args_file):
            _run_typescript_file(args, path=args_file)
        else:
            for (root, _, hits) in os.walk(args_file):
                for hit in hits:
                    path = os.path.join(root, hit)
                    if os.path.splitext(path)[-1] == ".typescript":
                        _run_typescript_file(args, path=path)


def _run_typescript_file(args, path):
    """Run with one TypeScript File"""

    with open(path) as incoming:
        passes = _run_bash_test_doc(incoming, path=path)
        if not args.rip_bash_paste:
            stderr_print("doctestbash.py: {} tests passed at:  {}".format(passes, path))

    _show_doctest_result()  # end with a demo of the Python DocTest precedent


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


def _run_bash_test_doc(incoming, path):
    """Run each test of a Bash Test Doc"""

    passes = 0

    line = incoming.readline()
    while line:

        # Take one more test, else break
        # FIXME: collections.namedtuple for (line_, dent, shline, doc_lines, wants)

        (line_, dent, shline, doc_lines, wants) = take_one_test(incoming, line)

        line = line_  # FIXME: don't so much hack up a stream with one line of lookahead

        if shline is None:
            assert wants is None
            break

        if main.args.rip_bash_paste:
            print(shline)
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

        require_test_passed(path, passes=passes, gots=gots, dent=dent, wants=wants)

        # Count passed tests

        passes += 1

    return passes


#
# Define some Python idioms
#


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

    return (dent, tail)


def take_one_test(incoming, line):
    """Take one test from the incoming stream: comments, one input line, outputs"""

    prompt = "$ "

    shline = None
    doc_lines = None
    wants = None

    # Take comments

    text = None

    while line:

        (dent, text) = str_splitdent(line.rstrip())
        vv_print(dent + text)

        if not text.startswith(prompt) and text != prompt.strip():
            line = incoming.readline()
            continue

        break

    if not line:

        return (line, dent, shline, doc_lines, wants)

    # Take input

    shline = text[len(prompt) :]
    line = incoming.readline()

    # Take output

    doc_lines = list()

    while line:
        (dent_, text_) = str_splitdent(line.rstrip())

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

    return (line, dent, shline, doc_lines, wants)


def run_one_shline(shline):
    """Shell out"""

    run = subprocess_run(
        shline,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert not run.stderr  # because stderr=subprocess.STDOUT
    assert run.returncode is not None

    gots = run.stdout.decode().strip().replace("\r\n", "\n").splitlines()
    if run.returncode:
        gots.append("+ exit {}".format(run.returncode))

    return gots


def require_test_passed(path, passes, gots, dent, wants):
    """Raise exception, unless actual output roughly equals expected output"""

    # Print each line we want, while we get it
    # Round up what we got with as many trailing blank lines as we want

    max_len = max(len(wants), len(gots))
    min_len = min(len(wants), len(gots))
    empties = (max_len - min_len) * [""]

    eq = True
    tail_wants = list(wants)
    tail_gots = list(gots)

    for (want, got) in zip(wants + empties, gots + empties):

        if got != want:
            if not equal_as_unordered_str_namespace(want, got=got):
                if not equal_but_for_ellipses(got, want=want):
                    eq = False

                    break

        vv_print(dent + got)

        tail_wants = tail_wants[1:]
        tail_gots = tail_gots[1:]

    if eq:

        return

    vv_print()
    vv_print()

    vv_print("wants ......: {}".format(repr(tail_wants)))
    vv_print("but gots ...: {}".format(repr(tail_gots)))
    vv_print()
    vv_print()

    vv_print("want .......: {}".format(want))
    vv_print("but got ....: {}".format(got))
    diff_mask = "".join(("^" if (_[0] != _[-1]) else ".") for _ in zip(want, got))
    vv_print("diff mask ..: {}".format(diff_mask))
    vv_print()
    vv_print()

    ellipsis = "..."
    if ellipsis in want:

        vv_print("want splits ......: {}".format(want.split(ellipsis)))
        vv_print("but got splits ...: {}".format(got.split(ellipsis)))
        vv_print()
        vv_print()

    reasons = list()
    reasons.append("unexpected output after {} tests:".format(passes))
    if main.args.vq < len("vv"):
        reasons.append("try again with -vv")
    reasons.append("fix the code, else the test:  vim {}".format(path))  # or both

    for reason in reasons:
        stderr_print("doctestbash.py: error: {}".format(reason))

    sys.exit(1)


def equal_as_unordered_str_namespace(want, got):
    """
    Reformat a printed Namespace to match the wanted key order

    FIXME As a workaround for the change in CPython behavior at:
        argparse should preserve argument ordering in Namespace
        https://bugs.python.org/issue39058
    """

    # Give up if not a match for prints of "argparse.Namespace" instances

    if not want.startswith("Namespace("):

        return

    if not got.startswith("Namespace("):

        return

    # Eval both, and substitute the "want" for the "got" only when they're equal

    eval_want = eval("argparse." + want)
    eval_got = eval("argparse." + got)

    if str(sorted(vars(eval_want).items())) == str(sorted(vars(eval_got).items())):
        # ok ignore key order, but don't accept False == 0, nor True == 1

        return True


def equal_but_for_ellipses(got, want):
    """Compare two strings, but match "..." to zero or more characters"""

    ellipsis = "..."

    # Cut trailing whitespace from the comparisons

    given = got.rstrip()
    musts = want.rstrip().split(ellipsis)

    # Require each fragment between "..." ellipses, in order

    for must in musts:

        must_at = given.find(must)
        if must_at < 0:
            return False

        given = given[must_at:][len(must) :]

    # Match endswith "..." ellipsis to all remaining text

    if len(musts) > 1:
        if not musts[-1]:
            given = ""

    # Fail if some text unmatched

    if given:

        return False

    # Succeed here, if no failures above

    return True


def vv_print(*args):
    if main.args.vq >= 2:
        stderr_print(*args)


#
# Call on Python
#


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


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
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
