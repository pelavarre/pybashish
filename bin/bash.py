#!/usr/bin/env python3

"""
usage: bash.py [-h]

optional arguments:
  -h, --help  show this help message and exit
"""

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
            sys.stdout.write("⌃C\r\n")
            sys.stdout.flush()
            continue

        # Exit at end-of-file

        if not shline:
            sys.exit(
                1
            )  # same subprocess.CompletedProcess.returncode=1 as Bash exit at EOF

        # Compile and execute the line

        argv = shlex.split(shline)
        how = _compile_shline(shline, argv=argv)

        returncode = how(argv)
        main.returncode = returncode


def builtin_pass(argv):
    pass


def builtin_exit(argv):
    sys.exit()


def _compile_shline(shline, argv):

    # Plan to call a built-in verb

    verb = argv[0] if argv else ""
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
                "bash.py: {}: No such file or directory in bash path".format(verb)
            )
            return how

        how = _compile_log_error("bash.py: {}: No such file or directory".format(verb))
        return how

    # Map plain verb to Py file

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
    where = pwd_.os_path_homepath(os.getcwd())

    nocolor = "\x1b[00m"
    green = "\x1b[00;32m"  # Demo ANSI TTY escape codes without "01;" bolding
    blue = "\x1b[00;34m"

    ps1 = f"{green}{user}@{hostname}{nocolor}:{blue}{where}{nocolor}{mark} \r\n({env}) {mark} "
    return ps1


def stderr_print(*args):
    print(*args, file=sys.stderr)


BUILTINS = dict()
BUILTINS[""] = builtin_pass
BUILTINS["exit"] = builtin_exit
# FIXME: implement BUILTINS["cd"]


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
