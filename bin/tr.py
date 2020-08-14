#!/usr/bin/env python3

r"""
usage: tr.py [-h] [-d] [--sort] [--unique-everseen] CHARSET

count lines and words and characters and bytes

positional arguments:
  CHARSET            set of characters

optional arguments:
  -h, --help         show this help message and exit
  -d, --delete       delete the characters
  --sort             sort the characters
  --unique-everseen  delete all duplicates of any char

bugs:
  chokes except when called for -d '[^ -~]\t\r\n'

examples:
  cat $(git ls-files) | tr.py --unique-everseen -d '[^ -~]\t\r\n' && echo
  cat $(git ls-files) | tr.py --unique-everseen --sort -d '⌃⌥⇧⌘←→↓↑💥💔😊😢😠åéîøü' && echo
"""
# FIXME: get argdoc to require --delete, while usage is limited
# FIXME: add -s, --squeeze-repeats
# FIXME: add --c, -C, --complement
# FIXME: add -t, --truncate-set1
# FIXME: add the interpretation of charset's, or mix it with Python regex

import sys

import argdoc


def main():
    args = argdoc.parse_args()

    charset = None
    if args.charset == r"[^ -~]\t\r\n":
        codes = list(range(ord(" "), (ord("~") + 1)))
        codes.extend([ord("\t"), ord("\r"), ord("\n")])
        charset = "".join(chr(_) for _ in codes)
    elif args.charset == "⌃⌥⇧⌘←→↓↑💥💔😊😢😠åéîøü":
        charset = args.charset

    if (not args.delete) or (not charset):
        stderr_print(r"usage: tr.py -d '[^ -~]\t\r\n'")
        stderr_print("tr.py: error: unrecognized arguments")  # FIXME: shlex.join
        sys.exit(2)  # exit 2 from rejecting usage

    stdins = sys.stdin.read()  # FIXME: "utf-8", errors="surrogateescape"
    takes = list(_ for _ in stdins if _ not in charset)
    uniques = str_unique_everseen(takes)

    stdouts = uniques
    if args.sort:
        stdouts = "".join(sorted(uniques))

    sys.stdout.write("".join(stdouts))


# deffed in many files  # missing from docs.python.org
def str_unique_everseen(chars):
    """Delete all duplicates of any char"""

    charset = set()
    uniques = ""

    for char in chars:
        if char not in charset:
            charset.add(char)
            uniques += char

    return uniques


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
