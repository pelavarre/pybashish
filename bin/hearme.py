#!/usr/bin/env python3

"""
usage: hearme.py [-h] [-p] [-f] [-i] [-q] [-v] [HINT [HINT ...]]

auto-complete the hints into a complete bash command line, trace it, and run it

positional arguments:
  HINT            code to run

optional arguments:
  -h, --help      show this help message and exit
  -p, --pipe      read stdin and write stdout, not the os copy-paste clipboard
  -f, --force     ask less
  -i, --interact  ask more
  -q, --quiet     say less
  -v, --verbose   say more

quirks:

  defines punctuation marks as in the J Programming Language
    https://www.jsoftware.com/help/learning/contents.htm

examples:

  hearme.py -h  # show this help message and exit

  hearme.py -p upper  # awk '{print toupper($0)}'
  hearme.py upper  # pbpaste | awk '{print toupper($0)}' | pbcopy
  hearme.py -i upper  # ask permission before running it
  hearme.py -ii upper  # just show it, don't run it
  hearme.py -q upper  # just run it, don't show it

  hearme.py -p lstrip  # awk '{sub("^  *", ""); print}'
  hearme.py -p rstrip  # awk '{sub("  *$", ""); print}'
  hearme.py -p strip  # awk '{sub("^  *", ""); sub("  *$", ""); print}'

  hearme.py -p .2  # awk '{print $3}'  # like py words[2]
  hearme.py -p _.1  # awk '{print $NF}'  # like py words[-1]
  hearme.py -p _.5  # awk '{print $(NF-4)}'  # like py words[-5]

  hearme.py -p '.1 +/'  # awk '{v1 += $2} END{print v1}'  # sum
  hearme.py -p '.3 +/ % #'  # awk '{v3 += $4} END{print v1 / NR}'  # average

"""

# FIXME: back up copies of the clipboard to "~/.hearme/pb/{pb,pb~,pb~2~,pb~3~,...}"

# FIXME: Makefile: rewrite "hearme.py" for distribution without "argdoc.py"
# FIXME: ArgDoc: explain better when usage is mnemonic opt but must be concise opt


import argparse
import re
import subprocess
import sys

import argdoc


def main(argv):  # FIXME FIXME  # noqa C901
    """Run a command line"""

    args = argdoc.parse_args()

    #

    awk = argparse.Namespace()

    awk.lines = list()
    awk.prints = list()
    awk.end_prints = list()

    #

    for hint in args.hints:
        try:
            add_awk_hint(awk, hint=hint)
        except Exception:
            sys.stderr.write("error: hearme.py: meaningless hint {!r}\n".format(hint))
            sys.exit(1)

    #

    shline = ""
    if not args.pipe:
        shline = "pbpaste | "

    #

    awk_lines = awk.lines
    if awk.prints or not awk.lines:
        awk_print_line = "print " + ", ".join(awk.prints)
        awk_lines = awk.lines + [awk_print_line.rstrip()]

    shline += "awk '"
    shline += "//{"
    shline += "; ".join(awk_lines)
    shline += "}"
    if awk.end_prints:
        shline += " END{"
        shline += "print " + ", ".join(awk.end_prints)
        shline += "}"
    shline += "'"

    #

    if not args.pipe:
        shline += "| pbcopy"

    #

    if args.interact > 1:
        if not args.quiet:
            sys.stderr.write("+ # {}\n".format(shline))
        sys.exit()

    #

    if not args.quiet:
        sys.stderr.write("+ {}\n".format(shline))

    #

    if args.interact:
        sys.stderr.write("Press Return to continue, else Control+C to quit\n")
        try:
            sys.stdin.readline()
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            sys.exit(1)

    #

    ran = subprocess.run(shline, shell=True)
    sys.exit(ran.returncode)


def add_awk_hint(awk, hint):  # FIXME FIXME  # noqa C901

    #

    if not hint:
        return

    #

    shards = hint.split()
    shard0 = shards[0]

    awk_value = None
    j_index = None

    if shard0 == "lower":
        awk_value = "tolower($0)"
        awk.prints.append(awk_value)
    elif shard0 == "lstrip":
        awk_line = """ sub("^  *", "") """.strip()
        awk.lines.append(awk_line)
    elif shard0 == "strip":
        awk_line = """ sub("^  *", ""); sub("  *$", "") """.strip()
        awk.lines.append(awk_line)
    elif shard0 == "rstrip":
        awk_line = """ sub("  *$", "") """.strip()
        awk.lines.append(awk_line)
    elif shard0 == "upper":
        awk_value = "toupper($0)"
        awk.prints.append(awk_value)
    else:

        match = re.match(r"^(_?)[.]([0-9]+)$", string=shard0)
        if not match:
            raise TypeError()
        else:
            j_index = int(match.group(2))

            if not match.group(1):
                awk_value = "${}".format(1 + j_index)
            elif j_index == 0:
                awk_value = "$0"
            else:
                awk_value = "$(NF + 1 - {})".format(j_index)

            if len(shards) == 1:
                awk.prints.append(awk_value)
            else:

                awk_line = "v{} += {}".format(j_index, awk_value)  # same sum
                if shards[1:] == "+/".split():
                    awk_end_print = "v{}".format(j_index)
                elif shards[1:] == "+/ % #".split():
                    awk_end_print = "v{} / NR".format(j_index)
                else:
                    raise TypeError()

                awk.lines.append(awk_line)
                awk.end_prints.append(awk_end_print)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


"""
FIXME: A grammar of HearMe Hints

FIXME: produce ".py" or ".c", not always only ".awk"
"""


# copied from:  git clone https://github.com/pelavarre/pybashish.git
