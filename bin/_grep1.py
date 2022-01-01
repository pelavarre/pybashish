#!/usr/bin/env python3

r"""
usage: grep.py [--help] [-h] [-v] [PATTERN ...]

search a curated Terminal input history for a paragraph or line of input to repeat now

positional arguments:
  PATTERN            search key, in the syntax of a Python regular expression

options:
  --help             show this help message and exit
  -h, --no-filename  print the hits without filenames (default: True)
  -v, --verbose      think more out loud

usage as a ~/.bashrc (or ~/.zshrc) history-recall extension:
  alias -- '~'=search-me-while-feeling-lucky  # execute hit
  alias -- '~~'=grep.py  # print hit
  alias -- '~!'='vim +$ $(cat ~/.local/share/grep/hitfiles)'

  function search-me-while-feeling-lucky () {
    local sourceable=$(mktemp)
    grep.py "$@" >"$sourceable"
    local xs="$?"
    if [ "$xs" = "0" ]; then
      local usage=''
      cat "$sourceable" |head -1 |grep '^usage: ' |read usage
      if [ ! "$usage" ]; then
        cat "$sourceable" |sed 's,^,+ ,' 1>&2
        source "$sourceable"
        xs="$?"
        rm "$sourceable"
        return "$xs"
      fi
    fi
    cat "$sourceable" 1>&2
    rm "$sourceable"
  }

quirks in the syntax:
  welcomes only more patterns, makes you push if you want more dirs or more files

quirks in the defaults:
  creates (and seeds) the ~/.local/share/grep/files/ dir, if it doesn't exist
  searches ~/.local/share/grep/files/ dir when no files chosen, not the classic /dev/stdin
  searches the files and dirs in the dir, doesn't give the classic "is a directory" rejection
  searches every line of input, not just the text lines, a la classic -a aka --text
  takes first word of the first line of input as defining how to begin an end-of-line comment
  picks out paragraphs split by blank lines, a la classic -z, not only the classic single lines
  prints just what's found, not also the classic -H filename and --color=auto for stdout isatty
  picks out the entire last file, when no patterns chosen
  requires every pattern in any order, not just the one or more patterns of classic -e p1 -e p2 ...
  understands patterns as python "import re" defines them, not as classic grep -G/-E/-P defines them
  understands patterns as case-insensitive, unless given in mixed or upper case, a la Emacs

other quirks:
  doesn't implement most of classic grep
  splits lines like python does, not like classic grep does
  spends whole milliseconds to fetch hits, when classic grep would spend just microseconds
  strips the patterns that start the hit from the hit, but fails if they do
  fails if not precisely one hit found, vs classic grep failing if not one or more hits found

quirks in examples:
  cases of ~ gs, ~ ascii

examples:
  ~~  # print the first file searched
  ~  # source the first file searched, as if you pasted it into the bash prompt
  ~~ apple key  # remind us of Apple's conventional ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑ ordering of shift keys
  ~~ gs  # print the one line hit most by "gs", not every line hit by "gs"
  ~ gs  # execute the one line found by:  ~~ gs
  ~ ruler  # count off the first hundred columns of a Terminal
  ~ 0123  # print the printable ascii chars in code point order
  ~ ascii  # print the printable ascii chars in code point order
  ~ vim  # print a Vim cheatsheet, a la Emacs, PbPaste, Screen, TMux, etc
  ~ quit vim  # remind us how to quit Vim
  ~ vim quit  # same hit, just found by another order
"""

# FIXME: move off of "~" quasi-reserved at left of line by "ssh"

# FIXME: add a grep option to balance the () [] {} <<  >> found in hits, as context

#
# FIXME: call it one hit when only one hit has more copies of some or of all the patterns, eg, ~ gs
#
# FIXME: quit after like ten hits, but say how many hits were found vs shown
#
# FIXME: populate the cat ~/.local/share/grep/hitfiles with the files hit
# FIXME: example ignore case, example respect case
# FIXME: example duplicate patterns must show up more than once
# FIXME: match trailing N patterns to 1 or more "..." as args, not just to themselves
#
# FIXME: add --color=yes|no|auto for "grep.py" when isatty and not
# FIXME: add --color=unstable for flipping the defaults to where I like them
#

# FIXME: capture:  F=p.py && mv -i $F $F~$(date +'%m%dJQDH%M%S')~


import contextlib
import os
import re
import sys
import textwrap

import argdoc

BASH_EXT = ".bash"

GREP_DIR = ".local/share/grep"
FILES_DIR = os.path.join(GREP_DIR, "files")


def main(argv):
    """Interpret the command line"""

    # Parse the command line, per the top-of-file docstring

    args = argdoc.parse_args(argv[1:])
    args.verbose = args.verbose if args.verbose else 0

    main.args = args

    if args.no_filename:  # print help because "-h" is short for "--filename"
        argdoc.print_help()
        sys.exit(0)  # exit zero from printing help

    if main.args.verbose >= 2:
        stderr_print("grep.py: args={}".format(args))

    # Publish default files individually, apart from this source file

    file_dir = os.path.split(os.path.realpath(__file__))[0]

    source_files_dir = os.path.realpath(
        os.path.join(file_dir, "../{}".format(FILES_DIR))
    )
    if not os.path.exists(source_files_dir):
        stderr_print("grep.py: creating dir {}/".format(minpath(source_files_dir)))
        _export_many_files(FILES_CHARS, from_dir="files/", to_dir=source_files_dir)

    # Share default files out across this localhost, apart from this source file

    home_files_dir = "~/{}".format(FILES_DIR)

    main.home_files_dir = home_files_dir

    home_files_envpath = home_files_dir.replace("~", os.environ["HOME"])
    home_files_envpath = os.path.realpath(home_files_envpath)

    main.home_files_envpath = home_files_envpath

    if not os.path.exists(home_files_envpath):
        stderr_print("grep.py: creating dir {}/".format(minpath(home_files_dir)))
        _export_many_files(FILES_CHARS, from_dir="files/", to_dir=home_files_envpath)

    # Choose files to search

    top = home_files_envpath
    many_relpaths = list(os_walk_sorted_relfiles(top))
    few_relpaths = list(_ for _ in many_relpaths if "~" not in _)
    realpaths = list(os.path.realpath(os.path.join(top, _)) for _ in few_relpaths)

    # Fetch and tag lines

    (files_lines, chosen_lines) = _ext_files_readlines(BASH_EXT, files=realpaths)

    # Search through lines

    exit_status = grep_lines(args, lines=files_lines, chosen_lines=chosen_lines)
    verbose_print("grep.py: + exit {}".format(exit_status if exit_status else 0))

    sys.exit(exit_status)


def _export_many_files(tarrish_chars, from_dir, to_dir):
    """Export lines as files and dirs into a dir, a la Bash "tar xkf tarred.gz" """

    files_chars = textwrap.dedent(tarrish_chars).strip() + "\n\n\n"
    files_lines = files_chars.splitlines()

    what_key = from_dir.rstrip(os.sep) + os.sep

    # Visit each line

    lines = list()
    what = None
    was_stripped = None

    for line in files_lines:

        # Pick out filenames coded as # files/...: ...

        words = line.split()
        if words[1:]:
            if (words[0] == "#") and words[1].startswith(what_key):

                cut = line[(line.index("#") + len("#")) :]
                cut = cut.split(":")[0]
                cut = cut.strip()

                what = cut
                assert what.startswith(what_key)
                what = what[len(what_key) :]

        # Pick out files delimited by a pair of blank lines

        stripped = line.strip()
        if lines:

            if (not was_stripped) and (not stripped):

                assert what
                assert lines[-1].strip() == was_stripped == ""

                wherewhat = os.path.join(to_dir, what)

                file_word_0 = None
                ext = os.path.splitext(wherewhat)[-1]
                if not ext.endswith("sh"):  # such as .bash, .zsh
                    file_word_0 = _pick_export_lines_word_zero(lines)

                chars = _format_one_file(
                    wherewhat, lines=lines[:-1], file_word_0=file_word_0
                )
                _export_one_file(wherewhat, chars=chars)

                # Begin again to collect the next file

                lines = list()
                what = None

        # Collect lines

        if lines or line:
            lines.append(line)

        was_stripped = stripped

    assert not "\n".join(lines).strip()  # silently discard trailing blank lines


def _pick_export_lines_word_zero(lines):
    """Choose the first word of the first line past the "#" header as an end-of-line comment mark"""

    for line in lines:
        words = line.split()
        if words:
            word0 = words[0]
            if word0 != "#":

                return word0

    return None


def _format_one_file(wherewhat, lines, file_word_0):
    """Format one file for export"""

    _ = wherewhat

    writes = list(lines)

    # End each file with a mark of its own provenance

    writes.append("")
    writes.append(
        "# copied from:  git clone https://github.com/pelavarre/pybashish.git"
    )

    # Convert the comments

    if file_word_0:

        for (index, write) in enumerate(writes):
            if write:
                word0 = write.split()[0]
                if word0 != "#":
                    break

                writes[index] = file_word_0 + write[len("#") :]

        for (index, write) in reversed(list(enumerate(writes))):
            if write:
                word0 = write.split()[0]
                if word0 != "#":
                    break

                writes[index] = file_word_0 + write[len("#") :]

    chars = "\n".join(writes) + "\n"

    return chars


def _export_one_file(wherewhat, chars):
    """Export one file"""

    where = os.path.split(wherewhat)[0]
    if not os.path.isdir(where):
        os.makedirs(where)

    if os.path.exists(wherewhat):  # create, no replace, as in "tar xvkf"
        stderr_print("grep.py: {}: Cannot open: File exists".format(wherewhat))
    else:
        with open(wherewhat, mode="w") as outgoing:
            outgoing.write(chars)


def _ext_files_readlines(ext, files):
    """Collect the lines of some files, but if not .ext then preface with # {filename}:"""

    verbose_print(
        "grep.py: collecting, from the {}/ dir, the relpaths:  {}".format(
            main.home_files_dir,
            " ".join(os.path.relpath(_, start=main.home_files_envpath) for _ in files),
        )
    )

    chosen_lines = None

    files_lines = list()
    for file_ in files:

        (_, what) = os.path.split(file_)
        (_, ext_) = os.path.splitext(what)

        with open(file_) as incoming:  # FIXME: odds on errors="surrogateescape" someday
            chars = incoming.read()
        file_lines = chars.splitlines()

        prefix = "" if (ext_ == ext) else "# {what}: ".format(what=what)

        prefixed_lines = file_lines
        if prefix:
            prefixed_lines = list((prefix + _) for _ in file_lines)

        if not prefix:
            if chosen_lines is None:
                chosen_lines = prefixed_lines

        if files_lines:
            files_lines.append("")

        files_lines.extend(file_lines)

    return (files_lines, chosen_lines)


def grep_lines(args, lines, chosen_lines):  # FIXME FIXME  # noqa C901

    patterns = args.patterns

    file_hits = list()
    separating_hits = None

    # Define comments

    file_word_0 = None
    if lines:
        words = chosen_lines[0].split()
        if words:
            file_word_0 = words[0]

    # Split lines into paragraphs

    paras = split_paragraphs(lines)

    # Search each line for all patterns in any order

    for para in paras:

        para_comments = list()
        para_hits = list()

        for line in para:

            if line.lstrip().startswith(file_word_0):
                para_comments.append(line)

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
                verbose_print(
                    "grep.py: {} lines hit in para without comments".format(
                        len(para_hits)
                    )
                )
                file_hits.extend([_] for _ in para_hits)
            elif para_comments == para:
                verbose_print(
                    "grep.py: {} lines hit in para of comments".format(len(para_hits))
                )
                if len(para_hits) == 1:
                    file_hits.extend([_] for _ in para_hits)
                else:
                    file_hits.append(para)
            else:
                verbose_print(
                    "grep.py: {} lines hit in para of input and comments".format(
                        len(para_hits)
                    )
                )
                assert 0 < len(para_comments) < len(para)
                file_hits.append(para)
                separating_hits = True

    # Take the last paragraph with bodies buried in it, if no patterns

    default_hit_lines = list(_ for _ in chosen_lines if _.strip())
    default_hit_lines = list(
        _ for _ in default_hit_lines if not _.startswith(file_word_0)
    )

    if not patterns:
        assert not file_hits
        file_hits.append(default_hit_lines)

    # Print one paragraph of lines hit, else a paragraph per hit

    exit_status = None

    if len(file_hits) != 1:
        exit_status = exit_status if exit_status else 2

    for hit in file_hits:
        # print((20 * "-"), index, (20 * "-"))

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
            verbose_print("grep.py: hitting {} lines".format(len(hit_lines)))
            print("\n".join(hit_lines))
        else:
            verbose_print("grep.py: dedenting {} lines".format(len(dedents)))
            verbose_print("grep.py: hit {!r}".format(hit_lines))
            print("\n".join(dedents))
            exit_status = exit_status if exit_status else 1

    if separating_hits:
        print()

    # Suggest which file to edit next

    hitfiles = [os.path.join(FILES_DIR, "b.bash")]  # FIXME: less brittle

    hitfiles_file = os.path.join(os.environ["HOME"], GREP_DIR, "hitfiles")
    with open(hitfiles_file, "w") as outgoing:
        outgoing.write("\n".join(hitfiles))

    # Pass only when precisely one hit found, and not dedented

    return exit_status


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def min_path_formatter(exemplar):
    """Choose the def that abbreviates this path most sharply: abs, real, rel, or home"""

    formatters = (
        os.path.abspath,
        os.path.realpath,
        os.path.relpath,
        os_path_homepath,
    )

    formatter = formatters[0]
    for formatter_ in formatters[1:]:
        if len(formatter_(exemplar)) < len(formatter(exemplar)):
            formatter = formatter_

    return formatter


# deffed in many files  # missing from docs.python.org
def minpath(path):
    "Abbreviate this path most sharply: abs, real, rel, or home" ""

    formatter = min_path_formatter(path)
    min_path = formatter(path)

    return min_path


# deffed in many files  # missing from docs.python.org
def os_path_homepath(path):
    """Return the ~/... relpath of a file or dir inside the Home, else the realpath"""

    home = os.path.realpath(os.environ["HOME"])

    homepath = path
    if path == home:
        homepath = "~"
    elif path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


# deffed in many files  # missing from docs.python.org
def os_walk_sorted_relfiles(top):
    """Walk the files in a top dir and its dirs, in alphabetical order, returning their relpath's"""

    top_ = "." if (top is None) else top
    top_realpath = os.path.realpath(top_)

    walker = os.walk(top_realpath)
    for (where, wheres, whats) in walker:  # (dirpath, dirnames, filenames)

        wheres[:] = sorted(wheres)  # sort these now, yield them never

        for what in sorted(whats):
            wherewhat = os.path.join(where, what)

            realpath = os.path.realpath(wherewhat)
            relpath = os.path.relpath(realpath, start=top_realpath)
            yield relpath


# deffed in many files  # missing from docs.python.org
def lstrip_lines(lines):
    """Strip the blank lines that begin a list"""

    lstrips = list(lines)
    while lstrips and not lstrips[0].lstrip():
        lstrips = lstrips[1:]

    return lstrips


# deffed in many files  # missing from docs.python.org
def split_paragraphs(lines, keepends=False):
    """Split the lines into paragraphs"""

    paras = list()

    para = list()
    for line in lines:
        if line.strip():
            para.append(line)
        else:
            if keepends:
                para.append(line)
            if para or keepends:
                paras.append(para)
            para = list()
    if para:
        paras.append(para)

    return paras


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def verbose_print(*args):
    """Print the Args, but to Stderr, not to Stdout, but only when Main Arg Verbose"""

    sys.stdout.flush()
    if main.args.verbose:
        print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


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
        (_, exc, _) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, flags=os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


# FIXME: sort the files here by name
# FIXME: then cross-ref bash to mac, emacs to emacs, vim to vim, etc
# FIXME: declare these as docstrings of defs, for "diff -burp" to cite them
FILES_CHARS = r"""

    #
    # files/b.bash:  Bash
    #

    autopep8 --max-line-length 100 --in-place ...

    awk '{print ...}'

    bash --version

    cat /dev/null/child  # always fails, often outside the shell
    cd /dev/null  # always fails inside the shell

    cat - |grep . |grep .  # free-text glass-terminal till ⌃C

    cd -  # for toggling between two dirs

    diff -x .git -burp ... ...

    echo -n $'\e[8;'$(stty size |cut -d' ' -f1)';101t'  # 101 cols
    echo >/dev/full  # always fails

    export PS1='\$ '
    export PS1="$PS1"'\n\$ '

    find . -not \( -path './.git' -prune \)  # akin to:  git ls-files

    if false; then echo y; else echo n; fi
    if true; then echo y; else echo n; fi

    last |head

    ls *.csv |sed 's,[.]csv$,,' |xargs -I{} mv -i {}.csv {}.txt  # demo replace ext
    ls --full-time ...  # to the second, at Linux
    ls |LC_ALL=C sort |cat -n

    rename 's,[.]csv$,-csv.txt,' *.csv  # replace ext, at Perl Linux

    sed -e $'3i\\\n...' |tee >(head -3) >(tail -2) >/dev/null  # first two, ellipsis, last two
    sed -i~ 's,STALE,FRESH,' *.json  # global edit find search replace

    ssh -G ...
    ssh -vvv ...

    ssh-add -l

    stat ...

    tar kxf ...  # FIXME: test CACHEDIR.TAG
    tar zcf ... ...

    # !?memo  # feeling lucky enough to authorize find and run again


    #
    # files/mac.bash:  Bash of Mac Clipboard, indexed by Python of Str
    #

    cat - |grep . |tr -c '[ -~\n]' '@'  # substitute '@', when Mac 'cat -etv' doesn't

    curl -O -Ss ...  # Mac a la Linux wget
    gunzip -c ...  # Mac a la Linux zcat
    openssl dgst -md5 ...  # Mac a la Linux md5sum
    openssl dgst -sha1 ...  # Mac a la Linux sha1sum
    tail -r  # Mac a la Linux tac

    pbpaste |hexdump -C |pbcopy  # hexdump
    pbpaste |sed 's,^,    ,' |pbcopy  # indent
    pbpaste |sed 's,^    ,,' |pbcopy  # dedent undent
    pbpaste |tr '[A-Z]' '[a-z]' |pbcopy  # lower
    pbpaste |sed 's,^  *,,' |pbcopy  # lstrip
    pbpaste |cat <(tr '\n' ' ') <(echo) |pbcopy  # join
    pbpaste |cat -n |sort -nr |cut -f2- |pbcopy  # reverse
    pbpaste |sed 's,  *$,,' |pbcopy  # rstrip
    pbpaste |sort |pbcopy  # sort
    pbpaste |sed 's,  *, ,g' |tr ' ' '\n' |pbcopy  # split
    pbpaste |sed 's,^\(.*\)\([.][^.]*\)$,\1 \2,' |pbcopy  # splitext
    pbpaste |sed 's,^  *,,'  |sed 's,  *$,,' |pbcopy  # strip
    pbpaste |tr '[a-z]' '[A-Z]' |pbcopy  # upper
    pbpaste |sed 's,[^ -~],?,g' |pbcopy  # ascii errors replace with "\x3F" question mark
    pbpaste |sed 's,[^ -~],,g' |pbcopy  # ascii errors ignore

    pbpaste >p  # pb stash
    cat p |pbcopy  # pb stash pop

    uname


    #
    # files/c.bash:  The C Programming Language
    #

    gcc --version

    #
    (cat >c.c <<EOF
    main() {
        puts("Hello, World!");
    }
    EOF
    ) && gcc -w c.c && ./a.out
    #


    #
    # files/cpp.bash:  The C++ Programming Language
    #

    g++ version

    #
    (cat >c.cpp <<EOF
    #include <iostream>
    int main() {
            std::cout << "Hello, C++ World" << std::endl;
    }
    EOF
    ) && g++ -Wall -Wpedantic c.cpp && ./a.out
    # TODO: evaluate g++ -Weverything -Werror -w c.c
    #


    #
    # files/emacs.bash:  Emacs
    #

    emacs --version
    emacs -nw --no-splash --eval '(menu-bar-mode -1)'  # free-text glass-terminal
    emacs -nw ~/.emacs

    #
    # emacs  ⌃G  => cancel
    # emacs  ⌃Q ⌃J  => literal input, literal newline
    #
    # emacs  ⌃A ⌃B ⌃E ⌃F ⌥M ⌥GTab  => move column
    # emacs  ⌥B ⌥F ⌥A ⌥E  => move small word, sentence
    # emacs  ⌃P ⌃N ⌥< ⌥> ⌥GG  => move row, goto line
    # emacs  fixme  => move match balance pair
    #
    # emacs  ⌃D ⌥D ⌥Z  => delete char, word, to char
    # emacs  ⌃@⌃@ ⌃@ ⌃X⌃X ⌃U⌃@  => mark: begin, place, bounce, goto
    # emacs  ⌃K ⌃W ⌥W ⌃Y ⌥Y ⌥T  => cut, copy, paste, paste-next-instead, join, transpose
    # emacs  ⌥H ⌥Q  => paragraph: mark, reflow
    #
    # emacs  ⌃U1234567890 ⌃- ⌃_ ⌃Xu  => repeat, undo, undo
    # emacs  ⌥L ⌥U ⌥C ⌃U1⌃XRNI⌃XR+I⌃XRII  => lower, upper, title, increment
    # emacs  ⌃S ⌃R ⌥%  => find, replace
    #
    # emacs  ⌃X( ⌃X) ⌃XE  => record input, replay input
    # emacs  fixme  => vertical delete copy paste insert
    # emacs  ⌃XTab ⌃XRD  => dent/dedent
    # emacs  ⌃U1⌥|  => pipe bash, such as ⌥H⌃U1⌥| or ⌥<⌃@⌥>⌃U1⌥|
    #
    # emacs  ⌃V ⌥V ⌃L  => scroll rows
    # emacs  ⌃X1 ⌃XK ⌃XO  => close others, close this, warp to next
    #
    # emacs  ⌃X⌃C ⌥~⌃X⌃C  => quit emacs, without saving
    #
    # emacs  ⌃Hk... ⌃Hb ⌃Ha...   => help for key chord sequence, for all keys, for word
    # emacs  ⌥X ⌥:  => execute-extended-command, eval-expression  => dry run ~/.emacs
    #
    # emacs  ⌃Z  => as per terminal or no-op
    #
    # emacs  ⌃] ⌃\  => obscure
    # emacs  ⌃Ca-z  => custom
    # emacs  ⌃C⌃C...  => custom
    #


    #
    # files/.emacs:  Emacs configuration
    #

    ; ~/.emacs

    ;
    ;; Configure Emacs

    (setq-default indent-tabs-mode nil)  ; indent with Spaces not Tabs
    (setq-default tab-width 4)  ; count out columns of C-x TAB S-LEFT/S-RIGHT

    (when (fboundp 'global-superword-mode) (global-superword-mode 't))  ; accelerate M-f M-b

    ;
    ;; Define new keys
    ;; (as dry run by M-x execute-extended-command, M-: eval-expression)

    (global-set-key (kbd "C-c %") 'query-replace-regexp)  ; for when C-M-% unavailable
    (global-set-key (kbd "C-c -") 'undo)  ; for when C-- alias of C-_ unavailable
    (global-set-key (kbd "C-c b") 'ibuffer)  ; for ? m Q I O multi-buffer replace
    (global-set-key (kbd "C-c m") 'xterm-mouse-mode)  ; toggle between move and select
    (global-set-key (kbd "C-c O") 'overwrite-mode)  ; aka toggle Insert
    (global-set-key (kbd "C-c o") 'occur)
    (global-set-key (kbd "C-c r") 'revert-buffer)
    (global-set-key (kbd "C-c s") 'superword-mode)  ; toggle accelerate of M-f M-b
    (global-set-key (kbd "C-c w") 'whitespace-cleanup)

    ;
    ;; Def C-c | = M-h C-u 1 M-| = Mark-Paragraph Universal-Argument Shell-Command-On-Region

    (global-set-key (kbd "C-c |") 'like-shell-command-on-region)
    (defun like-shell-command-on-region ()
        (interactive)
        (unless (mark) (mark-paragraph))
        (setq string (read-from-minibuffer
            "Shell command on region: " nil nil nil (quote shell-command-history)))
        (shell-command-on-region (region-beginning) (region-end) string nil 'replace)
        )

    ;
    ;; Turn off enough of macOS to run Emacs

    ; macOS Terminal > Preferences > Profile > Use Option as Meta Key
    ; ; or press Esc in place of Meta

    ; macOS System Preferences > Keyboard > Input Sources > Shortcuts > Previous Source
    ; ; or press ⌃⇧2 to reach C-@ to mean C-SPC 'set-mark-command


    #
    # files/git.bash:  Git
    #

    git --version

    git config core.editor
    git config --get-regexp '^user[.]'
    ls ~/.gitconfig .git/config

    echo 'git clean -ffxdq'  # destroy everything not added, without backup
    echo 'git reset --hard @{upstream}'  # shove all my comments into the "git reflog", take theirs instead

    git branch |grep '^[*]'
    git branch --all

    git checkout -  # for toggling between two branches

    git status  # gs gs
    git status --short --ignored
    git status --short --ignored |wc -l |grep '^ *0$'

    git apply -v ...'.patch'
    patch -p1 <...'.patch'  # silently drops new chmod ugo+x

    git log --pretty=format:"%h %an%x09%cd %s" -G regex file.ext  # grep changes
    git log --pretty=format:"%h %an%x09%cd %s" -S regex  # "pickaxe" grep insert/delete
    git log --pretty=format:"%h %an%x09%cd %s" --grep regex


    #
    # files/python.bash:  Python
    #

    pylint --rcfile=/dev/null --reports=n --disable=locally-disabled ...
    pylint --list-msgs
    pylint --help-msg E0012  # bad-option-value  # not adopted above

    python2 p.py
    python2 -m pdb p.py
    python3 p.py
    python3 -m pdb p.py

    python3 -i -c ''
    : # >>> o = [[0, 1, 2], [], [3], [4, 5]]
    : # >>> p = list(_ for listed in o for _ in listed)  # flatten/unravel list of lists
    : # >>> p  # [0, 1, 2, 3, 4, 5]
    : # >>> sum(o, list())  # [0, 1, 2, 3, 4, 5]  # flatten/unravel list of lists

    #
    # files/screen.bash:  Screen
    #

    screen --version

    screen -h 7654321  # escape from $STY with more than 1074 lines of transcript
    screen -h 7654321  # escape from $STY with more than 1074 lines of transcript
    screen -X hardcopy -h ~/s.screen  # export transcript
    screen -ls  # list sessions
    screen -r  # attach back to any session suspended by ⌃A D detach
    screen -r ...  # attach back to a choice of session suspended by ⌃A D detach
    screen -r ...  # attach back to a choice of session suspended by ⌃A D detach


    #
    # files/tmux.bash:  TMux
    #

    tmux --version

    tmux
    tmux attach  # attach.session til 'no sessions'
    tmux capture-pane -S -9999  # 1 of 3
    tmux save-buffer ~/t.tmux   # 2 of 3
    chmod ugo+r ~/t.tmux        # 3 of 3

    #
    # TMux ⌃B ?  => list all key bindings till ⌃X⌃C
    # TMux ⌃B [ Esc  => page up etc. a la Emacs
    # TMux ⌃B C  => new-window
    # TMux ⌃B D  => detach-client
    #


    #
    # files/ubuntu.bash:  Ubuntu
    #

    head /etc/apt/sources.list  # lsb_release
    cat /etc/lsb-release  # lsb_release
    lsb_release -a  # lsb_release

    : sudo true
    : date; : time sudo -n apt-get -y update
    : date; : time sudo -n apt-get -y upgrade
    : date; : time sudo -n apt-get -y dist-upgrade



    #
    # files/unicode-org.bash:  Unicode-Org
    #

    fmt.py --ruler  # Terminal column ruler

    #
    # printable ascii chars: in full, compressed lossily with "-", and escaped for Bash Echo
    # !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~
    # !"#$%&'()*+,-./0-9:;<=>?@A-Z[\]^_`a-z{|}~
    # echo ' !"#$%&'\''()*+,-./0-9:;<=>?@A-Z[\]^_`a-z{|}~'
    #

    #
    # ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑  # Apple key order:  Control/Ctrl Option/Alt Shift Command Left/Right/Down/Up
    #


    #
    # files/vim.bash:  Vim
    #

    vim --version
    vim  # glass-terminal scratchpad
    vim '+$' ~/.vimrc  # + option to say what line to start on

    # vim  :help ⌃V⌃C  "" help with key chord sequence
    # vim  :q  "" close help panel

    #
    # vim  Esc ⌃O  => stop inserting: indefinitely or temporarily
    # vim  ⌃V  => literal input, such as ⌃I Tab
    # vim  Q :+1,+5 :vi  => line-editor/ screen-editor mode
    #
    # vim  :set hlsearch / :set nohlsearch
    # vim  :set number / :set nonumber
    #

    #
    # vim  0 ^ $ fx tx Fx Tx ; , | h l  => leap to column
    # vim  b e w B E W ( ) { }  => leap across small word, large word, sentence, paragraph
    # vim  G 1G H L M - + _ ⌃J ⌃M ⌃N ⌃P j k  => leap to row, leap to line
    # vim  %  => leap to match balance pair
    #
    # vim  dx dd x D X p yx yy P Y J  => cut, copy, paste, join
    # vim  a cx i o s A C I O S ⌃O Esc ⌃C  => enter/ suspend-resume/ exit insert mode
    # vim  rx R ⌃O Esc ⌃C  => enter/ suspend-resume/ exit overlay mode
    #
    # vim  . 1234567890 u ⌃R ⌃O ⌃I  => do again, undo, repeat, revisit, undo-revisit
    # vim  ~ ⌃G ⌃L ⌃A ⌃X  => toggle case, say where, redraw, increment, decrement
    # vim  * / ? n N / .  => this, ahead, behind, next, previous, do again
    #
    # vim  :g/regex/  => preview what will be found
    # vim  :1,$s/regex/repl/gc  => find and replace, .../g for no confirmations
    #
    # vim  mm 'm '' `` `m  => mark, goto, bounce, bounce, bounce and mark
    # vim  qqq @q  => record input, replay input
    # vim  ⌃V I X Y P  => vertical: insert, delete, copy, paste
    # vim  >x <x  => dent/dedent
    # vim  !x  => pipe bash, such as {}!G or 1G!G
    #
    # vim  zb zt zz ⌃F ⌃B ⌃E ⌃Y ⌃D ⌃U  => scroll rows
    # vim  ⌃Wo ⌃WW ⌃Ww ⌃]  => close others, previous, next, goto link
    # vim  ⌃^  => replace panel with previous buffer
    #
    # vim  :e! ZZ ZQ  => quit-then-reopen, save-then-quit, quit-without-save
    # vim  Q :vi  => line-editor/ screen-editor mode
    #
    # vim  ⌃C ⌃Q ⌃S ⌃Z ⌃[  => vary by terminal, ⌃Z may need $ fg,  ⌃Q can mean ⌃V
    #
    # vim  U UU # & * = [ ] "  => obscure
    # vim  ⌃H ⌃K ⌃T ⌃\ ⌃_  => obscure
    # vim  ⌃@ ⌃A ⌃I ⌃O ⌃X g v V \ ⌃?  => not classic
    #

    #
    # vim  " to show visible space v tab with : syntax or : set list
    #
    # vim  :syntax on
    # vim  :set syntax=whitespace
    # vim  :set syntax=off
    # vim  :set list
    # vim  :set listchars=tab:>-
    # vim  :set nolist
    #

    #
    # see also:  https://cheat.sh/vim
    #


    #
    # files/.vimrc:  Vim configuration
    #

    " ~/.vimrc

    "
    " Lay out Spaces and Tabs

    :set softtabstop=4 shiftwidth=4 expandtab
    autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
    autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab

    "
    " Configure Vim

    :syntax on

    :set ignorecase
    :set nowrap
    " :set number

    :set hlsearch

    :highlight RedLight ctermbg=red
    :call matchadd('RedLight', '\s\+$')

    :set ruler  " not inferred from :set ttyfast at Mac
    :set showcmd  " not inferred from :set ttyfast at Linux or Mac

    "
    " Add keys (without redefining keys)
    " n-nore-map = map Normal (non insert) Mode and don't recurse through other remaps

    " \ Esc => cancel the :set hlsearch highlighting of all search hits on screen
    :nnoremap <Bslash><esc> :noh<return>

    " \ m => mouse moves cursor
    " \ M => mouse selects zigzags of chars to copy-paste
    :nnoremap <Bslash>m :set mouse=a<return>
    :nnoremap <Bslash>M :set mouse=<return>

    " \ w => delete the trailing whitespace from each line (not yet from file)
    :nnoremap <Bslash>w :call RStripEachLine()<return>
    function! RStripEachLine()
        let with_line = line(".")
        let with_col = col(".")
        %s/\s\+$//e
        call cursor(with_line, with_col)
    endfun


    #
    # files/zsh.zsh:  Zsh
    #

    zsh --version

    alias -- --history="history -t '%b %d %H:%M:%S' 0"
    fc -Dil -50
    vared _


    #
    # files/_.bash:  Default hit, first of the:  cd ~/.local/share/grep && echo files/[_a-z]*
    #

    cd -

"""

# FIXME: mention how to shut off profiles:  ssh -F /dev/null, emacs, vim, bash, zsh, etc


if __name__ == "__main__":
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
