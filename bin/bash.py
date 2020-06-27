#!/usr/bin/env python3

"""
usage: bash.py [-h]

optional arguments:
  -h, --help      show this help message and exit
"""

from __future__ import print_function

import contextlib
import os
import platform
import shlex
import subprocess
import sys

import argdoc

import pwd_ as pybashish_pwd  # FIXME: group these into one package

import read as pybashish_read


def main(argv):

    argdoc.parse_args()

    # Print banner

    stderr_print()
    stderr_print("Pybashish 0.x.y for Linux and Mac OS Terminals")
    stderr_print('Type "help" and press Return for more information.')
    stderr_print('Type "exit" and press Return to quit, or press ⌃D EOF to quit')
    stderr_print()

    # Serve till exit

    main.returncode = None
    while True:

        # Pull one line of input

        with pybashish_read.GlassTeletype() as gt:

            ps1 = calc_ps1()
            gt.putch(ps1)

            try:
                shline = gt.readline()
            except KeyboardInterrupt:
                gt.putch("⌃C\r\n")
                continue

        # Exit at end-of-file

        if not shline:
            sys.exit(
                1
            )  # same subprocess.CompletedProcess.returncode=1 as Bash exit at EOF

        # Compile and execute the line

        how = compile_shline(shline)
        returncode = how(shlex.split(shline))
        main.returncode = returncode


def builtin_exit(argv):
    sys.exit()


def compile_shline(shline):

    words = shline.split()

    # Execute an empty verb

    if not words:

        def how(argv):
            return 0

        return how

    # Execute a built-in verb

    verb = words[0]
    if verb in BUILTINS.keys():
        how = BUILTINS[verb]
        return how

    # Execute an outside verb

    how = _compile_run_py(verb)
    return how


def _compile_run_py(verb):

    # Plan escape to a sub-shell

    if verb.startswith(":!"):

        def how(argv):
            ran = subprocess.run([verb[len(":1") :]] + argv[1:])
            return ran.returncode

        return how

    # Plan to decline to call a relpath

    if ("/" in verb) or ("." in verb):

        if os.path.exists(verb):
            how = _compile_log_error(
                "bash.py: {}: No such file or directory in bash path".format(verb)
            )
            return how

        how = _compile_log_error("bash.py: {}: No such file or directory".format(verb))
        return how

    # Map verb to Py file

    file_dir = os.path.split(os.path.realpath(__file__))[0]

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

    how = _compile_log_error("bash.py: {}: command not found".format(verb))
    return how


def _compile_log_error(message):
    def how(argv):
        return log_error(message)

    return how


def log_error(message):
    stderr_print(message)
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
    where = pybashish_pwd.os_path_homepath(os.getcwd())

    nocolor = "\x1b[00m"
    green = "\x1b[00;32m"  # Demo ANSI TTY escape codes without "01;" bolding
    blue = "\x1b[00;34m"

    ps1 = f"{green}{user}@{hostname}{nocolor}:{blue}{where}{nocolor}{mark} \r\n({env}) {mark} "
    return ps1


def stderr_print(*args):
    print(*args, file=sys.stderr)


class BrokenPipeHandler(contextlib.ContextDecorator):
    """Silence any unhandled BrokenPipeError down to nothing but sys.exit(1)

    Yes, this is try-except-pass, but it is significantly more narrow than:
        signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)

    See https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):

        return self

    def __exit__(self, *exc_info):

        (exc_type, exc_value, exc_traceback,) = exc_info
        if isinstance(exc_value, BrokenPipeError):
            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())
            # FIXME: add test to reliably and quickly demo needing to "dup2" the "stdout.fileno"
            sys.exit(1)


BUILTINS = {k: _compile_run_py(k) for k in "".split()}  # FIXME: empty
BUILTINS["exit"] = builtin_exit
# FIXME: implement BUILTINS["cd"]
# FIXME: implement BUILTINS["bind"] for "bind -p"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
