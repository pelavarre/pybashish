#!/usr/bin/env python3

"""
usage: bash.py [-h] [-i]

chat with people: prompt, then listen, then speak, and repeat

optional arguments:
  -h, --help      show this help message and exit
  -i, --interact  ask more questions

bugs:
  returns exit status 0 after printing usage, if called with no arguments
  returns exit status 127, not 258, for ⌃D EOF pressed while ' or "" input quote open
  changes exit status after next line of input, no matter if input is blank
  defines "--interact" to expand on "-i", whereas "bash" doesn't bother
  leaves most of "bash" unimplemented

examples:
  bash.py  # chat till "exit", or ⌃D EOF pressed to quit, or ssh drops, etc
"""

# FIXME: add --color=never|always|auto
# FIXME: mark history with returncode, absolute start/stop time, copies of out/err, ...

from __future__ import print_function

import os
import platform
import shlex
import subprocess
import sys

import argdoc

import pwd_  # FIXME: packaging

import read


FILE_DIR = os.path.split(os.path.realpath(__file__))[0]  # sample before 1st "os.chdir"


def main(argv):

    args = argdoc.parse_args()
    if not args.interact:
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("bash.py: error: choose --interact")
        sys.exit(2)  # exit 2 from rejecting usage

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

        prompt = calc_ps1()

        try:
            shline = read.readline(prompt)
        except KeyboardInterrupt:
            continue

        # Exit at end-of-file
        # Exit with same subprocess.CompletedProcess.returncode=1 as Bash exit at EOF

        if not shline:
            sys.exit(1)

        # Compile and execute the line

        returncode = compile_and_run_shline(shline)

        main.returncode = returncode

        if returncode:  # trace nonzero a la Zsh "print_exit_value"
            stderr_print("bash.py: warning:  exit {}".format(returncode))
            # FIXME: think into trace "shline" of nonzero "returncode", a la Zsh


def compile_and_run_shline(shline):

    argv = _parse_shline(shline)
    how = _compile_shline(shline, argv=argv)
    returncode = how(argv)

    return returncode


#
#
#


def builtin_cd(argv):
    """Inject a change of working dir"""

    ran = builtin_via_py("cd.py", argv)
    returncode = ran.returncode

    changing_dir = True

    if (not ran.stdout) or len(ran.stdout.splitlines()) != 1:
        changing_dir = False
        if ran.stdout:
            os.write(sys.stdout.fileno(), ran.stdout)

    if ran.stderr:
        sys.stdout.flush()
        os.write(sys.stderr.fileno(), ran.stderr)
        sys.stderr.flush()

    if ran.returncode:
        changing_dir = False

    if changing_dir:

        stdouts = ran.stdout.decode()
        stdouts = stdouts.splitlines()

        assert len(stdouts) == 1
        realpath = stdouts[0]

        returncode = os_chdir_path(path=realpath)

    return returncode


def os_chdir_path(path):
    """Change the working dir of this process"""

    # Sample cwd

    try:
        before_cwd = os.getcwd()
    except FileNotFoundError:
        before_cwd = None

    if before_cwd is not None:
        before_realpath = os.path.realpath(before_cwd)
        os.environ[
            "OLDPWD"
        ] = before_realpath  # unneeded, unless this raises an exception

    # Change cwd and resample cwd

    try:
        os.chdir(path)
        after_cwd = os.getcwd()
    except FileNotFoundError as exc:
        stderr_print("cd.py: error: {}: {}".format(type(exc).__name__, exc))
        return 1

    after_realpath = os.path.realpath(after_cwd)
    os.environ["PWD"] = after_realpath

    ran = builtin_via_py("pwd_.py")
    returncode = ran.returncode

    if ran.stdout:
        os.write(sys.stdout.fileno(), ran.stdout)

    if ran.stderr:
        sys.stdout.flush()
        os.write(sys.stderr.fileno(), ran.stderr)
        sys.stderr.flush()

    return returncode


def builtin_cd_back(argv):
    cd_argv = ["cd", "-"] + argv[1:]
    returncode = builtin_cd(cd_argv)
    return returncode


def builtin_cd_up(argv):
    cd_argv = ["cd", ".."] + argv[1:]
    returncode = builtin_cd(cd_argv)
    return returncode


def builtin_exit(argv):
    """Inject a choice of process returncode"""

    ran = builtin_via_py("exit.py", argv)

    if ran.stdout:
        os.write(sys.stdout.fileno(), ran.stdout)

    if ran.stderr:
        sys.stdout.flush()
        os.write(sys.stderr.fileno(), ran.stderr)
        sys.stderr.flush()

    assert ran.returncode is not None
    if (not ran.stdout) and (not ran.stderr):
        sys.exit(ran.returncode)

    return ran.returncode


def builtin_via_py(what_py, argv=None):

    wherewhat = os.path.join(FILE_DIR, what_py)
    wherewhat_argv = [wherewhat] + argv[1:]

    ran = subprocess.run(wherewhat_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return ran


def builtin_help(argv):
    compile_and_run_shline("help")


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


def builtin_pass(argv):  # think more about  $ : --help
    pass  # FIXME: stop zeroing last exit status "$?" at each blank input line


#
#
#


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

        how = _compile_return_error()  # hope crash in _parse_shline printed a message

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

        how = _compile_explicit_relpath(verb)

        return how

    # Map one plain verb to each Py file

    wherewhat = _calc_wherewhat(verb)

    # Plan to call a Py file that exists

    if os.path.exists(wherewhat):

        def how(argv):
            try:
                ran = subprocess.run([wherewhat] + argv[1:])
            except PermissionError as exc:
                stderr_print("bash.py: error: {}: {}".format(type(exc).__name__, exc))
                ran.returncode = 126  # exit 126 from executable permission error
            return ran.returncode

        return how

    # Plan to reject a verb that maps to a Py file that doesn't exist

    how = _compile_log_error("bash.py: warning: {}: command not found".format(verb))

    return how


def _compile_explicit_relpath(verb):
    """Decline to map any explicit relpath to verb"""

    assert ("/" in verb) or ("." in verb)

    if os.path.exists(verb):
        how = _compile_log_error(
            "bash.py: warning: {}: No such file or directory in bash path".format(verb)
        )

        return how

    how = _compile_log_error(
        "bash.py: warning: {}: No such file or directory".format(verb)
    )

    return how


def _calc_wherewhat(verb):
    """Map verb to file"""

    what = f"{verb}_.py"
    wherewhat = os.path.join(FILE_DIR, what)
    if not os.path.exists(wherewhat):
        if not verb.endswith("_"):
            what = f"{verb}.py"
            wherewhat = os.path.join(FILE_DIR, what)

    return wherewhat


def _compile_log_error(message):
    """Plan to log an error message and return nonzero"""

    def how(argv):
        return _log_error(message)

    return how


def _compile_return_error():
    """Plan to to return nonzero, as if error message already logged"""

    def how(argv):
        return 127

    return how


def _log_error(message):
    """Log an error message and return nonzero"""

    assert message
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
    #
    # FIXME: Noise to Stderr at "platform.node()" in such tests as:  mkdir foo/ && cd foo/ && rm -fr ../foo/
    #
    #   Linux => sh: 0: getcwd() failed: No such file or directory"
    #   Mac => shell-init: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
    #

    gotcwd = os.environ["PWD"]
    try:
        gotcwd = os.getcwd()
    except FileNotFoundError:
        pass

    where = pwd_.os_path_homepath(gotcwd)

    assert read.ESC_CHAR == "\x1B"

    nocolor = "\x1B[00m"
    green = "\x1B[00;32m"  # Demo ANSI TTY escape codes without "01;" bolding
    blue = "\x1B[00;34m"

    ps1 = f"{green}{user}@{hostname}{nocolor}:{blue}{where}{nocolor}{mark} \r\n({env}) {mark} "

    return ps1


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


BUILTINS = {
    "-": builtin_cd_back,
    "--h": builtin_help,
    "--he": builtin_help,
    "--hel": builtin_help,
    "--help": builtin_help,
    "-h": builtin_help,
    "..": builtin_cd_up,
    ":": builtin_pass,
    "cd": builtin_cd,
    "exit": builtin_exit,
    "history": builtin_history,
}


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
