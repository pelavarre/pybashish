#!/usr/bin/env python3

r"""
usage: grep.py [--help] [-h] [PATTERN [PATTERN ...]]

search a curated Terminal input history for a paragraph or line of input to repeat now

positional arguments:
  PATTERN            search key, in the syntax of a Python regular expression

optional arguments:
  --help             show this help message and exit
  -h, --no-filename  just print the hits, not the filenames they came from (default: True)

usage as a ~/.bashrc (or ~/.zshrc) history-recall extension:
  alias -- '~'=source_grep_py  # execute hit
  alias -- '~~'=grep.py  # print hit
  alias -- '~!'="vim '+\$' ~/.local/share/g.grep"  # add hits

  function source_grep_py () {
    local sourceable=$(mktemp)
    grep.py "$@" >"$sourceable"
    local xs="$?"
    if [ "$xs" = "0" ]; then
      local usage=''
      cat "$sourceable" | head -1 | grep '^usage: ' | read usage
      if [ ! "$usage" ]; then
        cat "$sourceable" | sed 's,^,+ ,' 1>&2
        source "$sourceable"
        xs="$?"
        rm "$sourceable"
        return "$xs"
      fi
    fi
    cat "$sourceable" 1>&2
    rm "$sourceable"
  }

bugs in the syntax:
  welcomes only more patterns, makes you push if you want more dirs or more files

bugs in the defaults:
  creates (and seeds) the ~/.local/share/g.grep if it doesn't exist
  searches ~/.local/share/g.grep when no files chosen, not the classic /dev/stdin
  searches every line of input, not just the text lines, a la classic -a aka --text
  takes first word of first line of input as defining how to begin an end-of-line comment
  picks out paragraphs split by blank lines, a la classic -z, not only the classic single lines
  prints just what's found, not also the classic -H filename, nor the classic --color=isatty
  picks out the last paragraph when no patterns chosen
  requires every pattern in any order, not just the one or more patterns of classic -e p1 -e p2 ...
  understands patterns as python "import re" defines them, not as classic grep -G/-E/-P defines them
  understands patterns as case-insensitive, unless given in mixed or upper case, a la Emacs

other bugs:
  doesn't implement most of classic grep
  splits lines like python does, not like classic grep does
  spends whole milliseconds to fetch hits, when classic grep would spend just microseconds
  strips the patterns that start the hit from the hit, but fails if they do
  fails if not precisely one hit found, vs classic grep failing if not one or more hits found

examples:
  ~~  # print the last paragraph found
  ~  # execute the last paragraph found, as if you typed it onto the bash prompt
  ~ apple key  # remind us of Apple's conventional ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑ ordering of shift keys
  ~~ gs  # print the one line hit most by "gs", not every line hit by "gs"
  ~ gs  # execute the one line found by:  ~~ gs
  ~ ruler  # count off the first hundred columns of a Terminal
  ~ vim  # print a Vim cheatsheet, a la Emacs, PbPaste, Screen, TMux, etc
  ~ quit vim  # remind us how to quit Vim
  ~ vim quit  # same hit, just found by another order
  # example ignore case, example respect case
  # example duplicate patterns must show up more than once
"""
# FIXME: call it one hit when only one hit has more copies of some or of all the patterns
# FIXME: match trailing N patterns to 1 or more "..." as args, not just to themselves

import os
import re
import sys

import argdoc


def main():  # FIXME  # noqa C901
    # FIXME: divide into defs

    args = argdoc.parse_args()

    # Make dir, if need be

    dir_ = "~/.local/share".replace("~", os.environ["HOME"])
    if not os.path.isdir(dir_):
        stderr_print("+ mkdir {}".format(dir_))
        os.makedirs(dir_)

    # Make file, if need be

    whats = [os.path.join(dir_, "g.grep")]

    what0 = whats[0]
    if not os.path.exists(what0):

        file_dir = os.path.split(os.path.realpath(__file__))[0]
        what = os.path.join(file_dir, "dot-local-share-g.grep")
        with open(what) as incoming:
            chars = incoming.read()

        with open(what0, "w") as outgoing:
            outgoing.write(chars)

    # Visit each file

    patterns = args.patterns

    file_hits = list()
    separating_hits = None
    last_file_body_para = None

    for what in whats:

        # Read the file

        with open(what) as incoming:
            chars = incoming.read()
        lines = chars.splitlines()

        # Pick out the first word

        file_word_0 = None
        if lines:
            words = lines[0].split()
            if words:
                file_word_0 = words[0]

        # Collect the paragraphs

        paras = list()
        para = list()
        for line in lines:
            if line.strip():
                para.append(line)
            else:
                paras.append(para)
                para = list()
        if para:
            paras.append(para)

        # Search each line for all patterns in any order

        for para in paras:

            para_comments = list()
            para_hits = list()

            for line in para:

                if line.lstrip().startswith(file_word_0):
                    para_comments.append(line)
                else:
                    last_file_body_para = para

                searches = list()
                for pattern in patterns:

                    flags = re.IGNORECASE if (pattern == pattern.casefold()) else 0
                    search = re.search(pattern, string=line, flags=flags)

                    if search:
                        searches.append(search)
                    else:
                        break

                if searches:
                    if len(searches) == len(patterns):
                        para_hits.append(line)

            # Hit each matching line
            # except hit a whole paragraph of comments if hitting more than one of its lines
            # and hit a whole paragraph of comments and not-comment's if hitting any of its lines

            if para_hits:
                if not para_comments:
                    file_hits.extend([_] for _ in para_hits)
                elif para_comments == para:
                    if len(para_hits) == 1:
                        file_hits.extend([_] for _ in para_hits)
                    else:
                        file_hits.append(para)
                else:
                    assert 0 < len(para_comments) < len(para)
                    file_hits.append(para)
                    separating_hits = True

    # Take the last paragraph with bodies buried in it, if no patterns

    if not patterns:
        assert not file_hits
        if last_file_body_para:
            file_hits.append(last_file_body_para)

    # Print one paragraph of lines hit, else a paragraph per hit

    exit_status = None

    if len(file_hits) != 1:
        exit_status = exit_status if exit_status else 2

    for hit in file_hits:
        hit_lines = hit

        if separating_hits:
            print()

        dedents = list()
        for line in hit_lines:
            line = line.strip()
            assert line

            if line.startswith(file_word_0):
                tail = line[len(file_word_0) :].lstrip()
                if not tail:
                    dedents.append(tail)
                else:
                    cuts = list()
                    for pattern in patterns:
                        if tail.casefold().startswith(
                            pattern.casefold()
                        ):  # FIXME: nope match each pattern precisely as above
                            cuts.append(pattern)
                            tail = tail[len(pattern) :].lstrip()
                    if len(cuts) == len(
                        patterns
                    ):  # FIXME: nope, agree to cut the same partial from all
                        dedents.append(tail)

        dedenting = None
        if len(dedents) == len(hit_lines):
            if (len(file_hits) == 1) or (len(hit_lines) > 1):
                dedenting = True

        if not dedenting:
            print("\n".join(hit_lines))
        else:
            print("\n".join(dedents))
            exit_status = exit_status if exit_status else 1

    if separating_hits:
        print()

    # Pass only when precisely one hit found, and not dedented

    sys.exit(exit_status)


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
