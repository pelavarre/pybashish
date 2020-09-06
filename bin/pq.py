#!/usr/bin/env python3

"""
usage: pq.py [-h] [FILTER [FILTER ...]]

walk input to produce output

positional arguments:
  FILTER      filter coded as auto-correctable python

optional arguments:
  -h, --help  show this help message and exit
  -i FILE, --input-file FILE  file to read (default: clipboard)
  -o FILE, --output-file FILE  file to write (default: clipboard)

bugs:
  new

unsurprising bugs:
  does prompt once for stdin, when stdin chosen as file "-" or by no file args, unlike bash "cat"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  pq.py lower
  pq.py lstrip
  pq.py strip
  pq.py title
  pq.py upper
"""

# FIXME: pq.py with no args
# FIXME: pq.py -e json.loads -e json.dumps
# FIXME: option to sponge or not to sponge


import sys

import argdoc


def main():

    args = argdoc.parse_args()

    assert not hasattr(args, "input_files")
    assert not hasattr(args, "output_files")

    args.input_files = ["-"]
    args.output_files = ["/dev/stdout"]

    # Filter each file

    paths = args.input_files if args.input_files else ["-"]

    if "-" in paths:
        prompt_tty_stdin()

    for path in paths:
        openable = "/dev/stdin" if (path == "-") else path
        try:
            with open(openable, "rb") as incoming:
                pq_incoming(incoming, filters=args.filters)
        except FileNotFoundError as exc:
            stderr_print("pq.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


def pq_incoming(incoming, filters):

    funcs = list(eval("str." + _) for _ in filters)

    isatty = sys.stdin.isatty()

    while True:

        if isatty:
            sys.stdout.flush()

        line = incoming.readline().decode("utf-8", errors="replace")
        if not line:
            break

        text = line.splitlines()[0]
        for func in funcs:
            text = func(text)

        print(text)


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
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
