#!/usr/bin/env python3

import os
import platform
import shlex
import subprocess
import sys

import pwd
import read


def main():

    stderr_print()
    stderr_print("Pybashish 0.x.y for Linux and Mac OS Terminals")
    stderr_print('Type "help" and press Return for more information.')
    stderr_print('Type "exit" and press Return to quit, or press ⌃D EOF to quit')
    stderr_print()

    main.returncode = 0
    while True:

        with read.GlassTeletype() as gt:

            ps1 = calc_ps1()
            gt.putch(ps1)

            try:
                shline = gt.readline()
            except KeyboardInterrupt:
                gt.putch("⌃C\r\n")
                continue

        if not shline:
            break

        how = compile_shline(shline)
        returncode = how(shlex.split(shline))
        main.returncode = returncode


def compile_shline(shline):

    words = shline.split()

    if not words:

        def how(argv):
            return 0

        return how

    verb = words[0]
    if verb in BUILTINS.keys():
        how = BUILTINS[verb]
        return how

    how = compile_run_py(verb)
    return how


def compile_run_py(verb):

    if verb.startswith(":!"):

        def how(argv):
            ran = subprocess.run([verb[len(":1") :]] + argv[1:])
            return ran.returncode

        return how

    if ("/" in verb) or ("." in verb):

        if os.path.exists(verb):
            how = compile_error(
                "bash.py: {}: No such file or directory in bash path".format(verb)
            )
            return how

        how = compile_error("bash.py: {}: No such file or directory".format(verb))
        return how

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    what = f"{verb}.py"
    wherewhat = os.path.join(file_dir, what)

    if os.path.exists(wherewhat):

        def how(argv):
            ran = subprocess.run([wherewhat] + argv[1:])
            return ran.returncode

        return how

    how = compile_error("bash.py: {}: command not found".format(verb))
    return how


def compile_error(errline):
    def how(argv):
        return return_loud_error(errline)

    return how


def return_loud_error(errline):
    stderr_print(errline)
    return 127


def builtin_exit(argv):
    sys.exit()


def prompt(gt):

    mark = "$" if os.getuid() else "#"
    gt.putch(mark + " ")
    gt.putch(calc_ps1())


def calc_ps1():

    env = "pybashish"
    mark = "$" if os.getuid() else "#"

    if hasattr(calc_ps1, "user"):
        ps1 = f"({env}) {mark} "
        return ps1

    ran = subprocess.run(shlex.split("id -un"), stdout=subprocess.PIPE)
    user = ran.stdout.decode().rstrip()
    calc_ps1.user = user

    user = calc_ps1.user
    hostname = platform.node()
    where = os_path_homepath(os.getcwd())

    nocolor = "\x1b[00m"
    green = "\x1b[00;32m"  # ANSI TTY escape codes
    blue = "\x1b[00;34m"

    ps1 = f"{green}{user}@{hostname}{nocolor}:{blue}{where}{nocolor}{mark} \r\n({env}) {mark} "
    return ps1


def os_path_homepath(path):

    home = os.path.realpath(os.environ["HOME"])
    homepath = path
    if (path == home) or path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


def stderr_print(*args):
    print(*args, file=sys.stderr)


BUILTINS = {k: compile_run_py(k) for k in "".split()}  # FIXME: empty
BUILTINS["exit"] = builtin_exit
# FIXME: implement BUILTINS["cd"]
# FIXME: implement BUILTINS["bind"] for "bind -p"


if __name__ == "__main__":
    main()
