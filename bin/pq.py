#!/usr/bin/env python3

"""
usage: pq.py [-h] [-i FILE] [-o FILE] [-q] [-v] [FILTER [FILTER ...]]

walk input to produce output

positional arguments:
  FILTER                filter coded as auto-correctable python

optional arguments:
  -h, --help            show this help message and exit
  -i FILE, --input-file FILE
                        file to read (default: clipboard)
  -o FILE, --output-file FILE
                        file to write (default: clipboard)
  -q, --quiet           say less (like not even output file name)
  -v, --verbose         say more (like clipboard content, like even input file names)

bugs:
  backs up clipboard to files in cwd named "clip~1~", "clip~2~", etc
  backs up clipboard unless "-i" and "-o" chosen and do not exist as dirs

unsurprising bugs:
  does prompt once for stdin, when stdin chosen as file "-" or by no file args, unlike bash "cat"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:

  pq.py len  # len of str of line
  pq.py lower  # str.lower
  pq.py lstrip  # str.lstrip
  pq.py strip  # str.strip
  pq.py title  # str.title
  pq.py upper  # str.upper

  pq.py words.3  # 3rd word else empty = "".join(line.split()[3:][:1])

  pq.py '*' len  # more explicit, same as:  pq.py len

  pq.py . len  # len of list of lines
  pq.py . join  # " ".join(lines)  # la bash ... | xargs
  pq.py . set Counter  # collections.Counter(set(lines))  # a la bash ... | uniq -c
  pq.py . set sorted  # sorted(set(lines))  # a la bash ... | uniq c
  pq.py . sorted  # sorted(lines)  # a la bash ... | sort

  pq.py .. len  # len of chars of file
  pq.py .. split  # chars.split()  # a la bash ... | xargs -n 1
  pq.py .. strip  # strip leading/ trailing lines of file, lstrip first, rstrip last
  pq.py .. textwrap.dedent  # lstrip the whitespace common to every line
  pq.py .. split join  # " ".join(chars.split())
  pq.py .. split join." "  # more explicit, same as: pq.py .. split join
  pq.py .. split join."/"  # "/".join(chars.split())

  pq.py ../.. len  # len of bytes of file
  pq.py ../.. len, .. len, .. split len, . len  # count bytes, chars, words, lines
  pq.py -b len, -c len, -w len, -l len  # same, but more mnemonic, less algebraic

  pq.py ../../.. read decode."latin_1"  # alt decoding of file (not utf_8")
  pq.py t.txt ../../.. .name os.path.realpath  # read from file, disclose the realpath of its name
  pq.py t.txt ../../.. os.stat  # dump the last-modified time, byte size, etc of a file

  pq.py dedent  # a la bash ... | sed -E 's,^ ? ? ? ?,,g'
  pq.py dent  # a la bash ... | sed 's,^,    ,'
  pq.py eval  # __builtins__.eval  # a la bash ... | sed 's,^,echo ' | bash

"""

# FIXME: add in the "expand.py" idea of plain text (vs nbsp etc)

# FIXME: --rip py  to produce the python that we're running, to invite copy-edit

# FIXME: figure out how to loop over .. splitlines.True like to repr each
# pq.py .. splitlines.True 'repr for' ?

# FIXME: pq.py len  # len of each line, of all lines, of all chars, of all splits
# FIXME: pq.py 'split [3]'

# FIXME: pq.py with no args
# FIXME: pq.py -e json.loads -e json.dumps
# FIXME: option to sponge or not to sponge
# FIXME: more than one input file, more than one output file

# FIXME: splits = "hello word world".split()
# FIXME: sum(splits)  # TypeError: unsupported operand type(s) for +: 'int' and 'str'
# FIXME: "".join(splits)   # 'hellowordworld'


import glob
import io
import os
import platform
import re
import subprocess
import sys

import argdoc


def main(argv):

    tail_pq_argv = argv[1:] if argv[1:] else "-v".split()
    args = argdoc.parse_args(tail_pq_argv)

    main.args = args

    verbose = main.args.verbose if main.args.verbose else 0
    quiet = main.args.quiet if main.args.quiet else 0
    main.args.verbosely = verbose - quiet

    # Decide to work with clipboard or not

    inpath = None
    outpath = None
    clippath = None

    if args.input_file is None:
        clippath = name_clippath()
        inpath = clippath
    elif os.path.isdir(args.input_file):
        clippath = name_clippath(cwd=args.input_file)
        inpath = clippath
    else:
        outpath = args.output_file

    if args.output_file is None:
        clippath = name_clippath()
        outpath = clippath
    elif os.path.isdir(args.output_file):
        clippath = name_clippath(cwd=args.input_file)
        outpath = clippath
    else:
        outpath = args.output_file

    # Default to capture clipboard before work

    if clippath:
        shline = "pbpaste >{}".format(os_path_briefpath(clippath))
        check_and_log_shell(shline)

    # Apply filters

    apply_filters(outpath, inpath=inpath, filters=args.filters)

    # Default to update clipboard from file

    if clippath:
        shline = "pbcopy <{}".format(os_path_briefpath(clippath))
        check_and_log_shell(shline)


def check_and_log_shell(shline):
    """Call through to check_shell_stdout, but first log the shline if --verbose"""

    if not (main.args.verbosely >= 2):

        _ = check_shell_stdout(shline)

    else:

        stderr_print("+")
        stderr_print("+ {}".format(shline))
        _ = check_shell_stdout(shline)
        stderr_print("+")


def apply_filters(outpath, inpath, filters):
    """Run filters against input to produce output"""

    paths = [inpath]

    if "-" in paths:
        prompt_tty_stdin()

    outlines = list()
    for path in paths:
        readable = "/dev/stdin" if (path == "-") else path

        outlines = list()
        try:
            with open(readable, "rb") as incoming:
                more_outlines = pq_incoming(outpath, incoming=incoming, filters=filters)
                outlines.extend(more_outlines)
        except FileNotFoundError as exc:
            stderr_print("pq.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)

    outchars = "\n".join(outlines) + "\n"
    outbytes = outchars.encode()

    if main.args.verbosely >= 0:
        stderr_print("pq.py: writing:  less -FRX {}".format(outpath))

    with open(outpath, "wb") as outgoing:  # FIXME: flush output to tty sooner
        outgoing.write(outbytes)


def pq_incoming(outpath, incoming, filters):
    """Apply each filter, if any"""

    funcs = autocorrect_py_filters(filters)

    if main.args.verbosely >= 2:
        readable = os_path_briefpath(incoming.name)
        stderr_print("pq.py: reading from:  less -FRX {}".format(readable))

    _ = incoming.isatty()  # FIXME: flush output, before blocking for tty input

    outlines = list()
    len_ins = 0
    len_outs = 0

    while True:

        closed_line = incoming.readline().decode("utf-8", errors="replace")
        if not closed_line:
            break

        len_ins += 1

        line = closed_line.splitlines()[0]
        for func in funcs:
            line = func(line)

        if main.args.verbosely >= 1:
            stderr_print(line)

        outlines.append(line)

        len_outs += 1

    if main.args.verbosely >= 2:
        if len_outs == len_ins:
            stderr_print("pq.py: writing {} lines".format(len_outs))
        else:
            stderr_print(
                "pq.py: read {} lines and writing {} lines".format(len_ins, len_outs)
            )

    return outlines


def name_clippath(cwd=None):
    """Coin a name for the next edited copy of the cut/ copy/ paste clipboard"""

    gotcwd = os.getcwd() if (cwd is None) else cwd

    finds = glob.glob("{}/clip~*~".format(gotcwd))
    filenames = list(os.path.split(_)[-1] for _ in finds)
    clips = list(_ for _ in filenames if re.match(r"^clip[~][0-9]+~$", string=_))
    versions = list(int(_.split("~")[-2]) for _ in clips)
    last = max(versions) if versions else 0

    version = last + 1
    clippath = os.path.join(gotcwd, "clip~{}~".format(version))  # as in Emacs

    return clippath


#
#
#


def autocorrect_py_filters(filters):
    """Convert Py filter names to Py functions"""

    modules = [__builtins__, str]

    funcs = list()
    for filter_ in filters:
        func = None

        for module in modules:
            vars_module = vars(module)
            if filter_ in vars_module.keys():

                assert func is None
                func = vars_module[filter_]

                if func is str.join:
                    func = str_join

        if func is None:
            if filter_ == "dent":
                func = str_dent
            elif filter_ == "dedent":
                func = str_dedent

        funcs.append(func)

    funcs.append(str)

    return funcs


def str_dedent(line):
    """Call str.join, but give it its default separator of one " " space"""

    dedented = line

    len_dent = len(line.rstrip()) - len(line.strip())
    dent = len_dent * " "

    dedented = line
    if line.startswith(dent):  # true when all the indentation is " "
        len_dedent = min(len(dent), 4)
        if len_dedent:
            dedented = line[len_dedent:]

    return dedented


def str_dent(line):
    """Call str.join, but give it its default separator of one " " space"""

    dented = "    " + line
    return dented


def str_join(iterable):
    """Call str.join, but give it its default separator of one " " space"""

    joined = " ".join(iterable)
    return joined


#
# Git-track some Python idioms here
#

# deffed in many files  # missing from docs.python.org
def check_shell_stdout(shline, exit_statuses=(0,)):
    """Call silently, else trace and raise non-empty stderr or non-zero exit status"""

    # Call shell to run silently

    ran = subprocess.run(
        shline,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )

    # Raise CalledProcessError if non-empty Stderr or non-zero Exit Status

    if ran.stderr or ran.returncode:

        # First trace shell-like prompts and the input

        ps1 = platform.node() + os.pathsep + os.getcwd() + os.sep + "# "

        sys.stdout.flush()
        sys.stderr.write(ps1.rstrip() + "\n")
        sys.stderr.write("+ " + shline + "\n")
        sys.stderr.flush()

        # Next trace all of Stdout, and then all of Stderr

        try:
            stdout_fd = sys.stdout.fileno()
            stderr_fd = sys.stderr.fileno()
        except io.UnsupportedOperation:
            stdout_fd = None
            stderr_fd = None

        if stdout_fd and stderr_fd:  # often true, but false inside Jupyter IPython 3

            os.write(stdout_fd, ran.stdout)
            sys.stdout.flush()

            os.write(stderr_fd, ran.stderr)
            sys.stderr.flush()

        else:

            ipyout = ran.stdout.decode()
            sys.stdout.write(ipyout)
            sys.stdout.flush()

            ipyerr = ran.stderr.decode()
            sys.stderr.write(ipyerr)
            sys.stderr.flush()

        sys.stderr.write("+ exit {}\n".format(ran.returncode))
        sys.stderr.flush()

        raise subprocess.CalledProcessError(
            returncode=ran.returncode,
            cmd=ran.args,  # legacy cruft spells "shline" as "args" or as "cmd"
            output=ran.stdout,  # legacy cruft spells "stdout" as "output"
            stderr=ran.stderr,
        )

    return ran.stdout


# deffed in many files  # missing from docs.python.org
def os_path_briefpath(path):
    """Return the relpath with dir if shorter, else return abspath"""

    abspath = os.path.abspath(path)  # trust caller chose os.path.realpath or not

    relpath = os.path.relpath(path)
    relpath = relpath if (os.sep in relpath) else os.path.join(os.curdir, relpath)

    if len(relpath) < len(abspath):
        return relpath

    return abspath


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
