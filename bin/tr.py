#!/usr/bin/env python3

r"""
usage: tr.py [-h] [-d] [--sort] [--unique-everseen] [CHARSET]

count lines and words and characters and bytes

positional arguments:
  CHARSET            set of characters

optional arguments:
  -h, --help         show this help message and exit
  -d, --delete       delete the characters
  --sort             sort the characters
  --unique-everseen  delete all duplicates of any char

quirks:
  chokes except when called for -d '[^ -~]\t\r\n'
  runs as "--unique-everseen --sort" when called with no args, unlike Mac and Linux "tr" choking

examples:
  cat $(git ls-files) | tr.py --unique-everseen -d '[^ -~]\t\r\n' && echo
  cat $(git ls-files) | tr.py --unique-everseen --sort -d 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' && echo
  cat $(git ls-files) | tr.py; echo
"""
# FIXME: get argdoc to require --delete, while usage is limited
# FIXME: add -s, --squeeze-repeats
# FIXME: add --c, -C, --complement
# FIXME: add -t, --truncate-set1
# FIXME: add the interpretation of charset's, or mix it with Python regex


import sys

import argdoc


def main(argv):

    tr_argv_tail = argv[1:] if argv[1:] else ["--unique-everseen", "--sort", ""]
    args = argdoc.parse_args(tr_argv_tail)

    args_charset = args.charset if args.charset else ""

    charset = None
    if args_charset == r"[^ -~]\t\r\n":
        codes = list(range(ord(" "), (ord("~") + 1)))
        codes.extend([ord("\t"), ord("\r"), ord("\n")])
        charset = "".join(chr(_) for _ in codes)
    elif not any(_ in args_charset for _ in r"\[]"):
        charset = args_charset

    if charset is None:
        stderr_print("usage: tr.py [-h] [-d] [--sort] [--unique-everseen] [CHARSET]")
        stderr_print("tr.py: error: not much usage implemented")  # FIXME: shlex.join
        sys.exit(2)  # exit 2 from rejecting usage

    stdins = sys.stdin.read()  # FIXME: "utf-8", errors="surrogateescape"
    takes = stdins
    if args.delete:
        takes = list(_ for _ in stdins if _ not in charset)
    uniques = str_unique_everseen(takes)

    stdouts = uniques
    if args.sort:  # sorted(str_unique_everseen.charset) could be faster
        stdouts = "".join(sorted(uniques))

    sys.stdout.write("".join(stdouts))


#
# Git-track some Python idioms here
#


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
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
