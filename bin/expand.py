#!/usr/bin/env python3

r"""
usage: expand.py [-h] [--csv] [--repr] [--keep-tabs] [--wiki] [FILE [FILE ...]]

replace tabs with spaces, replace cr with lf, strip leading and trailing empty lines

positional arguments:
  FILE         a file to copy out (default: stdin)

optional arguments:
  -h, --help   show this help message and exit
  --csv        convert to a ".csv" table
  --repr       replace all but r"[\n\r\t]" and plain ascii with python \u escapes
  --keep-tabs  don't replace tabs, smart quotes, smart dashes, and such with plain ascii " - etc
  --wiki       escape as html p of code nbsp br (fit for insertion into atlassian wiki)

quirks:
  defaults to replace tabs, smart quotes, dashes, etc: not just tabs, but not also emoji
  doesn't accurately catenate binary files, unlike classic bash "expand"
  does strip leading and trailing empty lines, unlike bash "expand"
  does convert classic mac CR "\r" end-of-line to linux LF "\n", unlike bash "expand"
  does always end the last line with linux LF "\n" end-of-line, unlike bash "expand"
  does print eight-nybble \U code points as four lowercase nybbles then four uppercase
  doesn't implement classic -t 9,17 tab list, nor -t 4 tab width, nor linux --tabs alias thereof
  doesn't implement linux -i, --initial for keeping tabs in line after first nonwhite
  doesn't implement mac unexpand -a for compressing files maximally by replacing spaces with tabs

unsurprising quirks:
  does prompt once for stdin, like bash "grep -R", unlike bash "expand"
  accepts only the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", like linux "expand -", unlike mac "expand -"

see also:
  https://unicode.org/charts/PDF/U0000.pdf
  https://unicode.org/charts/PDF/U0080.pdf
  https://unicode.org/charts/PDF/U2000.pdf

examples:
  expand.py -
  echo -n $'\xC0\x80' | expand | hexdump  # Linux happy, but Mac says 'illegal byte sequence'
  echo -n $'\xC0\x80' | expand.py | hexdump.py  # x EF BF BD = uFFFD = Unicode Replacement chars
  echo -n $'t\tr\rn\n' | expand.py | cat.py -etv
  echo 'åéîøü←↑→↓⇧⋮⌃⌘⌥💔💥😊😠😢' | expand.py  # no change
  echo 'åéîøü←↑→↓⇧⋮⌃⌘⌥💔💥😊😠😢' | expand.py --repr  # such as "\u22EE" for "⋮" vertical ellipsis
  echo -n $'\xC2\xA0 « » “ ’ ” – — ′ ″ ‴ ' | expand.py | hexdump.py --chars  # common 'smart' chars
  echo 'import sys$if sys.stdout.isatty():$    print("isatty")$' | tr '$' '\n' | expand.py --wiki
"""

# note: the five chars "💔💥😊😠😢" are ": broken_heart : boom : blush : angry : cry :" in Slack 2020

# FIXME: option to sponge or not to sponge
# FIXME: think into the redundancy between incremental and sponging solutions to "def striplines()"
# FIXME: learn more of how much the sponging slows and stresses hosts


import collections
import contextlib
import html
import os
import sys

import argdoc


def passme():
    pass


def main(argv):

    args = argdoc.parse_args(argv[1:])

    passme.sponging = False
    passme.print_lines = list()
    if args.csv:
        passme.sponging = True

    # Expand each file

    paths = args.files if args.files else ["-"]

    if "-" in paths:
        prompt_tty_stdin()

    for path in paths:
        readable = "/dev/stdin" if (path == "-") else path
        try:
            with open(readable, "rb") as incoming:
                expand_incoming(incoming, args=args)
        except FileNotFoundError as exc:
            stderr_print("expand.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


def expand_incoming(incoming, args):
    """Copy each non-empty line out as it arrives, but transform it first"""

    passme.wiki_begun = False

    begun = False
    stripped = 0

    while True:

        line = incoming.readline().decode("utf-8", errors="replace")
        # \uFFFD Replacement Character, in place of raising UnicodeDecodeError
        # per https://unicode.org/charts/PDF/UFFF0.pdf

        lines = line.splitlines()

        if not line:
            break

        for line in lines:
            expanded = expand_line(line, args=args)
            if not expanded:
                if begun:
                    stripped += 1
            else:

                if stripped:
                    asif_print((stripped - 1) * "\n")
                    stripped = 0

                asif_print(expanded)

                begun = True

    if passme.wiki_begun:
        asif_print("</p>")

    printed = "\n".join(passme.print_lines) + "\n"
    stripped = striplines(printed)
    assert printed == stripped

    if args.csv:
        exit_csv(passme.print_lines)


def expand_line(line, args):
    """Transform one line"""

    expanded = line

    if not args.keep_tabs:
        expanded = line.expandtabs()
        if not (args.repr or args.wiki):
            expanded = dash_quote_as_ascii(expanded)

    if args.repr:
        expanded = code_points_as_unicode_escapes(expanded)

    if args.wiki:
        expanded = chars_as_wiki_html(expanded)

    expanded = expanded.rstrip()

    if expanded:
        if args.wiki:
            if not passme.wiki_begun:
                passme.wiki_begun = True
                asif_print("<p>")

    return expanded


def chars_as_wiki_html(chars):
    """Escape as html of code nbsp br in p (fit for insertion into atlassian wiki"""

    lines = list()

    for line in chars.splitlines():

        untabbed = line.expandtabs(tabsize=8)
        escaped = html.escape(untabbed)
        markup = escaped.replace(" ", "&nbsp;")

        lines.append("<code>{}</code><br></br>".format(markup))

    reps = "\n".join(lines)

    return reps


def asif_print(*args):
    """Print, or just collect, lines of output"""

    line = " ".join(str(_) for _ in args)
    passme.print_lines.append(line)

    if not passme.sponging:
        print(line)


def exit_csv(lines):
    """Convert to Csv from PSql today, and maybe to Csv from messier sources tomorrow"""

    for (index, line,) in enumerate(lines):

        bars = list(_ for (_, ch,) in enumerate(line) if ch == "|")
        if index == 0:
            bars0 = bars
        elif bars != bars0:
            plusses = list(_ for (_, ch,) in enumerate(line) if ch == "+")
            if index == 1:
                assert plusses == bars0
            elif (not line) and (index == (len(lines) - 1)):
                pass  # FIXME: not relevant when "expand.py" has stripped trailing lines
            else:  # FIXME: limit to one trailer not more
                trailer = "({} rows)".format((index + 1) - 3)
                assert line == trailer

        else:

            assert "," not in line
            cells = list(_.strip() for _ in line.split("|"))
            _ = cells

    print(len(lines))  # FIXME: finish implementing "--csv"


#
# Git-track some Python idioms here
#


#
# Copy-paste some "def"s from elsewhere
#
# deffed in many files  # missing from docs.python.org
def code_points_as_unicode_escapes(chars):
    r"""Replace all but r"[\n\r\t]" and plain Ascii with \uXXXX and \uxxxxXXXX escapes"""

    reps = ""
    for ch in chars:
        if ord(" ") <= ord(ch) <= ord("~"):
            reps += ch
        elif ch in "\t\r\n":
            reps += ch
        elif ord(ch) <= 0xFFFF:
            rep = r"\u{:04X}".format(ord(ch))
            reps += rep
        elif ord(ch) <= 0xFFFFFFFF:
            nybbles = "{:08X}".format(ord(ch))
            assert len(nybbles) == 8
            rep = r"\u{}{}".format(nybbles[:4].lower(), nybbles[4:].upper())
            reps += rep
        else:  # FIXME: cope with Unicode beyond \uffffFFFF (if it exists here?)
            assert False

    return reps


# deffed in many files  # missing from docs.python.org
def dash_quote_as_ascii(chars):
    """Replace such as “ ’ ” – — ′ ″ ‴ with printable Ascii"""

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
def striplines(chars):
    """Strip leading blank lines, trailing blank lines, and trailing blank spaces from every line"""

    lines = chars.splitlines()
    lines = list(_.rstrip() for _ in lines)
    while lines and not lines[0]:
        lines = lines[1:]
    while lines and not lines[-1]:
        lines = lines[:-1]

    stripped = "\n".join(lines) + "\n"
    return stripped


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


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
