#!/usr/bin/env python3

r"""
usage: cat.py [-h] [-E] [-e] [-n] [-T] [-t] [-v] [FILE [FILE ...]]

copy each line of input bytes (or chars) to output (as if "cat"enating them slowly)

positional arguments:
  FILE                  a file to copy out (default: stdin)

optional arguments:
  -h, --help            show this help message and exit
  -E, --show-ends       print each "\n" lf as "$\n"
  -e                    call for -E and -v
  -n, --number          number each line of output
  -T, --show-tabs       show each "\t" tab as r"\t" backslash tee
  -t                    call for -T and -v
  -v, --show-nonprinting
                        convert all but \n and \t and printable ascii r"[ -~]" to \ escapes

quirks:
  shows \t as \t, not as classic ^I
  shows \n as \n, not as classic $
  does show all but printable ascii as nonprinting, unlike Mac "cat" at \u00A0 &nbsp; etc
  does stop copying at first ⌃D of stdin, even when last line not completed by "\n"
  does print hard b"\x09" tab after each line number, via "{:6}\t", same as bash "cat"
  doesn't yet accept 'cat.py -n=0' to mean count up from zero

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "cat -" and "cat"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's

examples:
  cat -  # copy out each line of input
  cat - >/dev/null  # echo and discard each line of input
  cat - |grep . |cat.py -etv  # collect and echo some input, then echo it escaped
  echo a b c |tr ' ' '\n' |bin/cat.py -  # pass stdin through to stdout
  (echo a; echo b; echo c) |cat -n |cat.py -etv  # show \t as \t and \n as \n
  pbpaste |cat.py -etv  # show nonprinting in paste buffer
  echo $'\x5A\xC2\xA0' |cat -tv  # Linux ok, but Mac shows &nbsp; Non-Break Space as space :-(
  echo $'\x5A\xC2\xA0' |cat.py -tv  # do show even &nbsp; Non-Break Space as nonprinting
"""
# FIXME: let cat -n=0 mean count up from zero
# FIXME: rewrite as Python 2 without contextlib.ContextDecorator


import contextlib
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])

    if args.e:
        args.show_ends = True
        args.show_nonprinting = True

    if args.t:
        args.show_tabs = True
        args.show_nonprinting = True

    paths = args.files if args.files else ["-"]

    # Catenate each binary (or text) file

    if "-" in paths:
        prompt_tty_stdin()

    for path in paths:
        readable = "/dev/stdin" if (path == "-") else path
        try:
            with open(readable, mode="rb") as incoming:
                cat_incoming(fd=incoming.fileno(), args=args)
        except FileNotFoundError as exc:
            stderr_print("cat.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


def cat_incoming(fd, args):
    """Copy out some form of each byte as it arrives"""

    ofd = sys.stdout.fileno()

    line_index = 0
    line_bytes = b""
    fd_byte = b"\n"

    while True:

        # Rep each byte

        length = 1
        fd_byte = os.read(fd, length)

        rep = cat_repr_byte(fd_byte, args)
        line_bytes += rep

        # Close the last line, if showing ends and last line open

        if args.show_ends:
            if line_bytes:
                if not fd_byte:
                    line_bytes += b"\n"

        # Write the line and open new line, if line

        if line_bytes:

            if (fd_byte == b"\n") or (not fd_byte):
                tag = "{:6}\t".format(1 + line_index)
                if args.number:
                    os.write(ofd, tag.encode())

                os.write(ofd, line_bytes)

                line_index += 1
                line_bytes = b""

        # Quit after the last byte

        if not fd_byte:

            break


def cat_repr_byte(fd_byte, args):
    """Choose how to show each byte in the line"""

    if fd_byte:

        if fd_byte == b"\n":
            rep = (br"\n" + b"\n") if args.show_ends else fd_byte
            return rep

        if fd_byte == b"\t":
            rep = br"\t" if args.show_tabs else fd_byte
            return rep

        if args.show_nonprinting:
            xx = ord(fd_byte)
            if not (ord(" ") <= xx <= ord("~")):
                rep_chars = r"\x{:02X}".format(xx)
                rep = rep_chars.encode()

                return rep

    return fd_byte


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
class BrokenPipeErrorSink(contextlib.ContextDecorator):
    """Cut unhandled BrokenPipeError down to sys.exit(1)

    Test with large Stdout cut sharply, such as:  find.py ~ |head

    More narrowly than:  signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)
    As per https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc, exc_traceback) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, flags=os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


if __name__ == "__main__":
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
