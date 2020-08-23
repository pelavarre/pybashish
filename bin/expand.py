#!/usr/bin/env python3

r"""
usage: expand.py [-h] [--plain] [--repr] [--wiki] [FILE [FILE ...]]

replace tabs with spaces, replace cr with lf, strip leading and trailing empty lines

positional arguments:
  FILE        a file to copy out

optional arguments:
  -h, --help  show this help message and exit
  --plain     replace smart quotes, smart dashes, and such with plain us-ascii " ' -
  --repr      replace all but r"[\n\r\t]" and plain us-ascii with python \u escapes
  --wiki      escape as html p of code nbsp br (fit for insertion into atlassian wiki)

bugs:
  doesn't accurately catenate binary files, unlike classic bash "expand"
  does strip leading and trailing empty lines, unlike bash "expand"
  does convert classic mac CR "\r" end-of-line to linux LF "\n", unlike bash "expand"
  does always end the last line with linux LF "\n" end-of-line, unlike bash "expand"
  doesn't implement classic -t 9,17 tab list, nor -t 4 tab width, nor linux --tabs alias thereof
  doesn't implement linux -i, --initial for keeping tabs in line after first nonwhite
  doesn't implement mac unexpand -a for compressing files maximally by replacing spaces with tabs

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "expand"
  accepts only the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", like linux "expand -", unlike mac "expand -"

see also:
  https://unicode.org/charts/PDF/U0000.pdf
  https://unicode.org/charts/PDF/U0080.pdf
  https://unicode.org/charts/PDF/U2000.pdf

examples:
  expand.py -
  echo -n $'\xC0\x80' | expand.py | hexdump -C  # Linux preserves binary, Mac says 'illegal byte'
  echo -n $'t\tr\rn\n' | expand.py | cat -etv
  echo 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' | expand.py
  echo $'\xC2\xA0 « » “ ’ ” – — ′ ″ ‴ ' | expand.py --plain
  echo 'import sys$if sys.stdout.isatty():$    print("isatty")$' | tr '$' '\n' | expand.py --wiki

"""
# FIXME: rewrite as Python 2 without contextlib.ContextDecorator


import collections
import contextlib
import html
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])
    relpaths = args.files if args.files else ["-"]

    # Expand each file

    if "-" in relpaths:
        prompt_tty_stdin()

    for relpath in relpaths:
        if relpath == "-":
            expand_incoming(sys.stdin, args=args)
        else:
            try:
                with open(relpath, "rt") as incoming:
                    expand_incoming(incoming, args=args)
            except FileNotFoundError as exc:
                stderr_print("expand.py: error: {}: {}".format(type(exc).__name__, exc))
                sys.exit(1)


def expand_incoming(incoming, args):
    """Copy each non-empty line out as it arrives, but pass it through .expandtabs and .rstrip"""

    begun = False
    stripped = 0

    while True:

        line = incoming.readline()
        lines = line.splitlines()

        if not line:
            break

        for line in lines:

            expanded = line.expandtabs()
            if args.plain:
                expanded = dash_quote_as_ascii(expanded)
            if args.repr:
                expanded = code_points_as_unicode_escapes(expanded)
            if args.wiki:
                expanded = chars_as_wiki_html(expanded)
            expanded = expanded.rstrip()

            if not expanded:

                if begun:
                    stripped += 1

            else:

                if stripped:
                    print((stripped - 1) * "\n")
                    stripped = 0

                print(expanded)

                begun = True


def chars_as_wiki_html(chars):
    """Escape as html of code nbsp br in p (fit for insertion into atlassian wiki"""

    lines = list()
    lines.append("<p>")

    for line in chars.splitlines():

        untabbed = line.expandtabs(tabsize=8)
        escaped = html.escape(untabbed)
        markup = escaped.replace(" ", "&nbsp;")

        lines.append("<code>{}</code><br></br>".format(markup))

    lines.append("</p>")

    reps = "\n".join(lines)

    return reps


# deffed in many files  # missing from docs.python.org
def code_points_as_unicode_escapes(chars):
    r"""Replace all but r"[\n\r\t]" and plain us-ascii with python \uXXXX escapes"""

    reps = ""
    for ch in chars:
        if ord(" ") <= ord(ch) <= ord("~"):
            reps += ch
        elif ch in "\t\r\n":
            reps += ch
        elif ord(ch) <= 0xFFFF:
            rep = r"\u{:04X}".format(ord(ch))
            reps += rep
        else:
            assert False  # FIXME: cope with Unicode beyond \uFFFF (if it exists here?)

    return reps


# deffed in many files  # missing from docs.python.org
def dash_quote_as_ascii(chars):
    """Replace such as “ ’ ” – — ′ ″ ‴ with printable us-ascii"""

    reps_by_ch = collections.defaultdict(type(None))

    reps_by_ch["\u00A0"] = " "  # 00A0 no-break space  # &nbsp;
    reps_by_ch["«"] = '"'  # 00AB left-pointing double angle quotation mark
    reps_by_ch["»"] = '"'  # 00BB right-pointing double angle quotation mark

    reps_by_ch["\u200B"] = " "  # 200B zero width space
    reps_by_ch["–"] = "-"  # 2013 en dash
    reps_by_ch["—"] = "--"  # 2014 em dash
    reps_by_ch["\u2018"] = "'"  # 2018 left single quotation mark
    reps_by_ch["’"] = "'"  # 2019 right single quotation mark
    reps_by_ch["“"] = '"'  # 201C left double quotation mark
    reps_by_ch["”"] = '"'  # 201D right double quotation mark
    reps_by_ch["′"] = "'"  # 2032 prime
    reps_by_ch["″"] = "''"  # 2033 double prime
    reps_by_ch["‴"] = "'''"  # 2034 triple prime

    reps = ""
    for ch in chars:
        alt_rep = reps_by_ch[ch]
        if alt_rep:
            reps += alt_rep
        else:
            reps += ch

    return reps


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


# deffed in many files  # missing from docs.python.org
class BrokenPipeErrorSink(contextlib.ContextDecorator):
    """Cut unhandled BrokenPipeError down to sys.exit(1)

    Test with large Stdout cut sharply, such as:  find.py ~ | head

    More narrowly than:  signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)
    As per https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc, exc_traceback,) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


if __name__ == "__main__":
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
