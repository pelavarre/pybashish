#!/usr/bin/env python3

"""
usage: bash.py [-h]

chat with people: prompt, then listen, then speak, and repeat

optional arguments:
  -h, --help  show this help message and exit

bugs:
  returns exit status 127, not 258, for ⌃D EOF pressed while ' or "" input quote open
  zeroes exit status after next line of input, no matter if input is blank
  lots more bugs not yet reported, please help us out

examples:
  bash.py  # chat till "exit", or ⌃D EOF pressed to quit, or Ssh drops, etc
"""
# FIXME: add --color=never|always|auto

from __future__ import print_function

import os
import platform
import shlex
import subprocess
import sys

import argdoc

import pwd_  # FIXME: packaging

import read


def main(argv):

    argdoc.parse_args()

    # Print banner

    stderr_print()
    stderr_print("Pybashish 0.x.y for Linux and Mac OS Terminals")
    stderr_print('Type "help" and press Return for more information.')
    stderr_print('Type "exit" and press Return to quit, or press ⌃D EOF to quit')
    stderr_print()
    sys.stderr.flush()

    # Serve till exit

    main.returncode = None
    while True:

        # Pull one line of input

        prompt = calc_ps1()

        try:
            shline = read.readline(prompt)
        except KeyboardInterrupt:
            sys.stderr.write("⌃C\r\n")
            sys.stderr.flush()
            continue

        # Exit at end-of-file
        # Exit with same subprocess.CompletedProcess.returncode=1 as Bash exit at EOF

        if not shline:
            sys.exit(1)

        # Compile and execute the line

        argv = _parse_shline(shline)
        how = _compile_shline(shline, argv=argv)
        returncode = how(argv)

        main.returncode = returncode

        if returncode:  # trace nonzero a la Zsh "print_exit_value"
            stderr_print("bash.py: warning:  exit {}".format(returncode))
            # FIXME: think into trace "shline" of nonzero "returncode", a la Zsh


def builtin_pass(argv):  # FIXME FIXME FIXME: build in "-h" and "--help" without a verb
    pass  # FIXME: stop zeroing last exit status "$?" at each blank input line


def builtin_exit(argv):
    """Inject a choice of process returncode"""

    file_dir = _calc_file_dir()
    wherewhat = os.path.join(file_dir, "exit.py")

    ran = subprocess.run(
        [wherewhat] + argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    os.write(sys.stdout.fileno(), ran.stdout)
    assert ran.returncode is not None
    assert not ran.stderr  # because stderr=subprocess.STDOUT

    returncode = ran.returncode
    if not ran.stdout:
        sys.exit(returncode)

    return returncode


def builtin_history(argv):
    """
    usage: history [-h]

    review command line input history

    optional arguments:
      -h, --help  show this help message and exit

    examples:
      history
    """

    doc = builtin_history.__doc__
    try:
        _ = argdoc.parse_args(args=argv[1:], doc=doc)
    except SystemExit as exc:
        returncode = exc.code
        return returncode

    shlines = read.ShLineHistory.shlines  # couple less tightly  # add date/time-stamp's
    for (index, shline,) in enumerate(shlines):
        lineno = 1 + index
        print("{:5d}  {}".format(lineno, shline))


def _parse_shline(shline):
    """Split a line of input into an argv list of words"""

    split_argv = None
    try:
        split_argv = shlex.split(shline)
    except ValueError as exc:
        stderr_print("bash.py: warning: {}: {}".format(type(exc).__name__, exc))

    argv = None
    if split_argv is not None:
        argv = list(split_argv)
        for (index, arg,) in enumerate(split_argv):
            if arg.startswith("#"):
                argv = split_argv[:index]  # drop "#..." hash comment till end of shline
                break

    return argv


def _compile_shline(shline, argv):
    """Return a callable to interpret argv"""

    # Fail fast if no input line parsed

    if argv is None:

        how = _compile_log_error()

        return how

    # Plan to call a built-in verb

    verb = argv[0] if argv else ":"  # take ":" as no-op, a la Bash ":" or Dos "rem"
    if verb in BUILTINS.keys():

        how = BUILTINS[verb]

        return how

    # Plan escape to a sub-shell

    if shline.startswith(":!"):

        escaped_shline = shline[len(":!") :].lstrip()
        argv_ = shlex.split(escaped_shline)

        def how(argv):
            ran = subprocess.run(argv_)
            return ran.returncode

        return how

    # Plan to decline to call any explicit relpath

    verb = argv[0]
    if ("/" in verb) or ("." in verb):

        if os.path.exists(verb):
            how = _compile_log_error(
                "bash.py: warning: {}: No such file or directory in bash path".format(
                    verb
                )
            )
            return how

        how = _compile_log_error(
            "bash.py: warning: {}: No such file or directory".format(verb)
        )
        return how

    # Map plain verb to Py file

    file_dir = _calc_file_dir()

    what = f"{verb}_.py"
    wherewhat = os.path.join(file_dir, what)
    if not os.path.exists(wherewhat):
        what = f"{verb}.py"
        wherewhat = os.path.join(file_dir, what)

    # Plan to call a Py file that exists

    if os.path.exists(wherewhat):

        def how(argv):
            ran = subprocess.run([wherewhat] + argv[1:])
            return ran.returncode

        return how

    # Plan to rejecy a verb that maps to a Py file that doesn't exist

    how = _compile_log_error("bash.py: warning: {}: command not found".format(verb))
    return how


def _calc_file_dir():
    file_dir = os.path.split(os.path.realpath(__file__))[0]
    return file_dir


def _compile_log_error(message=None):
    def how(argv):
        return log_error(message)

    return how


def log_error(message):
    if message is not None:
        stderr_print(message)
        sys.stderr.flush()
    return 127


def calc_ps1():
    "Calculate what kind of prompt to print next"

    # Usually return a short prompt

    env = "pybashish"
    mark = "$" if os.getuid() else "#"

    if hasattr(calc_ps1, "user"):
        ps1 = f"({env}) {mark} "
        return ps1

    # But first calculate a long prompt

    ran = subprocess.run(shlex.split("id -un"), stdout=subprocess.PIPE)
    user = ran.stdout.decode().rstrip()
    calc_ps1.user = user

    user = calc_ps1.user
    hostname = platform.node()
    where = pwd_.os_path_homepath(os.getcwd())

    assert read.ESC_CHAR == "\x1B"

    nocolor = "\x1B[00m"
    green = "\x1B[00;32m"  # Demo ANSI TTY escape codes without "01;" bolding
    blue = "\x1B[00;34m"

    ps1 = f"{green}{user}@{hostname}{nocolor}:{blue}{where}{nocolor}{mark} \r\n({env}) {mark} "
    return ps1


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


BUILTINS = dict()
BUILTINS[":"] = builtin_pass
BUILTINS["exit"] = builtin_exit
BUILTINS["history"] = builtin_history
# FIXME FIXME: implement BUILTINS["cd"]


if __name__ == "__main__":
    main(sys.argv)


# See also
#
# POSIX.1-2017
# https://pubs.opengroup.org/onlinepubs/9699919799/
# https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html
# https://pubs.opengroup.org/onlinepubs/9699919799/utilities/read.html
#


# copied from:  git clone https://github.com/pelavarre/pybashish.git
