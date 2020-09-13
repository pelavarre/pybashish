#!/usr/bin/env python3

"""
usage: pq.py [-h] [-b] [-c] [-l] [-w] [--rip EXT] [DEFNAME [DEFNAME ...]]

tell a stack machine to walk input to produce output

positional arguments:
  DEFNAME      name of filter, defined by python, such as "len" or "str" or "encode"

optional arguments:
  -h, --help   show this help message and exit
  -b, --bytes  sponge up clipboard, split into bytes
  -c, --chars  sponge up clipboard, split into chars
  -l, --lines  sponge up clipboard, split into lines (default: 1)
  -w, --words  sponge up clipboard, split into words
  --rip EXT    just write the python program, don't sponge clipboard and run it

bugs:
  sponges up a copy of the clipboard into "./clip~1~", "./~clip~2~", etc
  replaces clipboard with its output
  rips source to stdout on request, doesn't run that source then
  as a programming language, asks the question: what if every thing was a sponge?
  runs only at Mac, except for Linuxes that understand "pbpaste" and "pbcopy"

defnames:
  _, ., ..  # abbreviations of --words, --lines, --chars
  bin, eval, hex, int, len, oct, str, repr, ...  # defined as __builtins__
  join, lower, lstrip, strip, title, upper, ... # defined on str and on bytes

examples:

  (echo hello; echo pb world) | pbcopy
  pbpaste

  pq.py .  # cat -
  pq.py sorted  # sort
  pq.py set sorted  # sort | uniq
  # pq.py .. set sorted "".join  # tr.py  # list the chars present, each char once only
  # pq.py collections.Counter items ...  # sort | uniq -c | sort -nr
  pq.py reversed  # linux tac, mac tail -r

  pq.py . len str, _ . len str, .. len str, -b len str encode  # count l, w, c, b
  pq.py -lwc len str -b len str encode | pq.py _  # counts joined as words of one line
  pq.py -b len str encode -cwl len str | pq.py _  # same one line, reversed
  pq.py -b len str encode -cwl len str | pq.py _ reversed  # reversed twice (as nop)
"""
# FIXME: pq.py expand, ...  # stop tripping over &nbsp; etc


import glob
import io
import os
import platform
import re
import subprocess
import sys
import textwrap

import argdoc

BUILTINS = __builtins__


def main(argv):

    # Supply help, or fail bad args, else fall through

    args = argdoc.parse_args(argv[1:])

    _ = args.defnames
    _ = args.bytes
    _ = args.chars
    _ = args.words
    _ = args.lines

    rip = ".py" if (args.rip is None) else args.rip
    if rip is not False:
        if not rip.startswith(os.extsep):
            rip = os.extsep + args.rip

        rips = ".py".split()
        if rip not in rips:
            sys.stderr.write(
                "pq.py: error: "
                "choose --rip from {}, do not choose {!r}\n".format(rips, args.rip)
            )
            sys.exit(2)  # exit 2 from rejecting usage

    # Capture the input clipboard

    if not rip:
        clippath = name_clippath()
        shline = "pbpaste >{}".format(os_path_briefpath(clippath))
        check_and_log_shell(shline)

    # Replace the captured input clipboard with captured output

    pd = PqDraftsbot()
    source = pd.rip_py(argv)  # original argv, not parsed args
    if rip:
        sys.stdout.write(source)
    else:
        with open(clippath, "rb") as incoming:
            sponge_bytes = incoming.read()
        sponge_bytes = pd.run_py(source, sponge_bytes)
        with open(clippath, "wb") as outgoing:
            outgoing.write(sponge_bytes)

    # Replace the clipboard

    if not rip:
        shline = "pbcopy <{}".format(os_path_briefpath(clippath))
        check_and_log_shell(shline)


# FIXME: run as stack machine on stack of classnames
# .[3]
# . .. _ -b # lines, chars, words, bytes, file - in the stack of streams
#
# .   # lines
# ..  # chars
# .. ..  # bytes
# .. .. ..  # file
# ..*3  # file
# _  # words
# _ upper ..  # line of the word
#
_ = """

. len  # count of lines
.. len  # count of chars
.. .. len  # count of bytes
-b len  # alt count of bytes

. for len  # length of each line in chars
. split len  # length of each line in words
-b splitlines for len  # length of each line in bytes
-b splitlines.keepends=True  # length of each line in bytes including lineseps

. len str, _ len str, .. len str, -b len str encode  # wc -lwcb
-l len str, -w . len str, -c len str, -b len str encode  # alt1 wc -lwcb
-lwc len str, -b len str encode  # alt2 wc -lwcb
-lwc len, -b len  # alt3 wc -lwcb

.. textwrap.dedent  # lstrip each line, but not the indents of each line

"""
#
# pq.py . len range, zip  # enumerate: iterable -> int, each

# FIXME: change pipekind to classname:  bytes, str, list, dict
# FIXME: change sponge name in source eg sponge_int = len(sponge_str)
# FIXME: change sponge name in source eg sponge_str = str(int)
# FIXME: change sponge name in source eg sponge_dict = collections.Counter(sponge_list)
# FIXME: allow change of type eg read list of strs write list of bytes


BYTES_PIPE = textwrap.dedent(
    r"""
    # bytes to write as binary, not text
    sys.stdout.flush()
    sys.stderr.flush()
    with open("dev/stdin", "rb") as incoming:
        sponge = incoming.read()
    #
    ...
    #
    with open("dev/stdout", "wb") as outgoing:
        outgoing.write(sponge)
    """
)

OBJECTS_PIPE = textwrap.dedent(
    r"""
    # objects such as chars, ints, etc
    sys.stdout.flush()
    sys.stderr.flush()
    sponge = sys.stdin.read()
    #
    ...
    #
    sys.stdout.write(sponge)
    """
)

LINES_STRS_PIPE = textwrap.dedent(
    r"""
    # strs to join as lines
    sys.stdout.flush()
    sys.stderr.flush()
    sponge = sys.stdin.read()
    sponge = sponge.splitlines()
    #
    ...
    #
    sys.stdout.write("\n".join(sponge) + "\n")
    """
)

WORDS_PIPE = textwrap.dedent(
    r"""
    # words to join
    sys.stdout.flush()
    sys.stderr.flush()
    sponge = sys.stdin.read()
    sponge = sponge.split()
    #
    ...
    #
    sys.stdout.write(" ".join(sponge) + "\n")
    """
)

PIPES_BY_PIPEKIND = {  # FIXME:  add --json pipe, add --csv pipe, etc
    "--bytes": BYTES_PIPE,
    "--chars": OBJECTS_PIPE,
    "--ints": OBJECTS_PIPE,
    "--lines": LINES_STRS_PIPE,
    "--strs": LINES_STRS_PIPE,
    "--words": WORDS_PIPE,
}


class PqDraftsbot:
    """Rip (and option to run) Python from the Main ArgV"""

    def __init__(self):

        self.last_pipekind = "--lines"  # figuratively
        self.pipekind = None
        self.pipestages = None

        self.sourcelines = None

    def rip_py(self, argv):
        """Walk the Argv"""

        opts = list(argv[1:])

        self.sourcelines = list()

        undashing = None
        while opts:

            # Take the next opt

            opt = opts[0]
            opts = opts[1:]

            # sys.stderr.write("opt={!r}\n".format(opt))

            assert opt

            # Compile most opts

            if undashing or (opt == "-") or not opt.startswith("-"):

                self.compile_opt(opt)
                continue

            # Take "--" as the last of the dashed opts

            if opt == "--":

                undashing = True
                continue

            # Drop "--rip EXT"

            concise_choices = "-b -c -l -w".split()
            mnemonic_choices = "--bytes --chars --lines --words".split()

            if "--rip".startswith(opt):

                ext = opts[0]
                opts = opts[1:]

                _ = ext

                continue

            # Compile the "--mnemonic" opt, after disambiguating it

            if opt.startswith("--"):

                mnemonic_opts = list(_ for _ in mnemonic_choices if _.startswith(opt))

                assert len(mnemonic_opts) == 1
                mnemonic_opt = mnemonic_opts

                self.open_next_pipe(pipekind=mnemonic_opt)

                continue

            # Compile each concise opt

            for letter in opt[1:]:
                concise_opt = "-{}".format(letter)
                mnemonic_opt = mnemonic_choices[concise_choices.index(concise_opt)]

                self.open_next_pipe(pipekind=mnemonic_opt)

            continue  # explicit, unneeded

        self.close_pipe()

        source = "\n".join(self.sourcelines) + "\n"
        return source

    def open_next_pipe(self, pipekind):

        self.close_pipe()  # harmless if pipe not opened

        pipekind_choices = "--bytes --chars --lines --words".split()
        assert pipekind in pipekind_choices

        self.pipekind = pipekind
        self.pipestages = list()

        # sys.stderr.write("close_open_pipe pipekind={!r}\n".format(pipekind))

    def close_pipe(self):

        pipekind = self.pipekind
        pipestages = self.pipestages
        sourcelines = self.sourcelines

        if pipekind:

            template = PIPES_BY_PIPEKIND[pipekind].strip() + "\n"

            if not pipestages:
                pipe = template.replace("...\n", "")
            else:
                repl = "\n".join(pipestages) + "\n"
                pipe = template.replace("...\n", repl)
            pipe += "\n"

            # sys.stderr.write("pipe={!r}\n".format(pipe))

            sourcelines.extend(pipe.splitlines())
            sourcelines.extend([])

        self.pipekind = None
        self.pipestages = None

    def compile_opt(self, opt):

        pipekind = self.pipekind
        last_pipekind = self.last_pipekind

        words = opt.split(",")
        assert words

        for (index, word,) in enumerate(words):
            reverse_index = index - len(words)

            # Compile words between commas

            if word == "":
                pass
            elif word == "_":
                self.open_next_pipe("--words")
            elif word == ".":
                self.open_next_pipe("--lines")
            elif word == "..":
                self.open_next_pipe("--chars")
            else:
                if not pipekind:
                    self.open_next_pipe(pipekind=last_pipekind)
                self.compile_word(word)  # compile between commas

            # Compile commas, but drop last trailing

            if reverse_index != -1:
                if len(words) > 1:
                    self.close_pipe()

    def compile_word(self, word):

        hit = self.find_word(word)
        self.emit_found_word(word, hit)

    def find_word(self, word):

        hits = self.find_word_for(exemplar=None, word=word)

        exemplar = self.pull_exemplar()
        more_hits = self.find_word_for(exemplar=exemplar, word=word)
        if more_hits:
            hits.extend(more_hits)

        assert len(hits) <= 1

        if not hits:
            if exemplar is None:
                sys.stderr.write("pq.py: error: meaningless word {!r}\n".format(word))
            else:
                sys.stderr.write(
                    "pq.py: error: word {!r} meaningless at {} {!r}\n".format(
                        word, type(exemplar).__name__, exemplar
                    )
                )
            sys.stderr.write("SQUIRREL\n")
            sys.exit(2)  # exit 2 from rejecting usage

        hit = hits[0]
        return hit

    def pull_exemplar(self):

        pipekind = self.pipekind

        exemplar = str()
        if pipekind is None:
            exemplar = None
        elif pipekind in "--bytes".split():
            exemplar = bytes()
        elif pipekind in "--ints".split():
            exemplar = int()
        else:
            assert pipekind in "--chars --words --lines --strs".split()

        return exemplar

    def emit_found_word(self, word, hit):

        modulename = word.split(".")[0] if ("." in word) else None

        (exemplar, deffed,) = hit
        name = deffed.__name__

        if exemplar is None:

            if modulename is None:
                line = "sponge = {}(sponge)".format(name)
            else:
                line = "sponge = {}.{}(sponge)".format(modulename, name)
                # FIXME FIXME: test textwrap.dedent and emit import sourcelines up front

        elif exemplar in (b"", "", 0):

            line = "sponge = sponge.{}()".format(name)

            if exemplar == "":
                if deffed is str_join:
                    repr_implication = '" "'
                    line = "sponge = {}.sponge.{}".format(repr_implication, name)

        else:

            assert False  # "def find_word" said it found a hit

        self.pipestages.append(line)

        if name in "bytes".split():
            self.pipekind = "--bytes"
        elif name in "int".split():
            self.pipekind = "--ints"
        elif name in "len".split():
            self.pipekind = "--ints"
        elif name in "str".split():
            self.pipekind = "--strs"

        # sys.stderr.write("name={!r}\n".format(name))
        # sys.stderr.write("self.pipekind={!r}\n".format(self.pipekind))
        # sys.stderr.write("\n")

    def find_word_for(self, exemplar, word):

        # sys.stderr.write("exemplar={!r}\n".format(exemplar))
        # sys.stderr.write("word={!r}\n".format(word))

        deffeds = list()

        if isinstance(exemplar, bytes):
            source = "bytes." + word
            deffeds.extend(self.collect_evalleds(source))
        elif isinstance(exemplar, int):
            source = "int." + word
            deffeds.extend(self.collect_evalleds(source))
        elif isinstance(exemplar, str):
            source = "str." + word
            deffeds.extend(self.collect_evalleds(source))
        else:
            assert exemplar is None
            source = word
            deffeds.extend(self.collect_evalleds(source))

        assert len(deffeds) <= 1

        hits = list(zip([exemplar], deffeds))
        return hits

    def collect_evalleds(self, source):

        try:
            evalled = eval(source)
            evalleds = [evalled]
            return evalleds
        except AttributeError:
            return []
        except NameError:
            return []
        except SyntaxError:
            return []


def check_and_log_shell(shline):
    """Call through to check_shell_stdout, but first log the shline if --verbose"""

    stderr_print("+")
    stderr_print("+ {}".format(shline))
    _ = check_shell_stdout(shline)
    stderr_print("+")


def name_clippath(cwd=None):
    """Coin a new name for the next edited copy of the cut/ copy/ paste clipboard"""

    # Peek into the current working dir

    gotcwd = os.getcwd() if (cwd is None) else cwd

    # Find the last name

    finds = glob.glob("{}/clip~*~".format(gotcwd))
    filenames = list(os.path.split(_)[-1] for _ in finds)
    clips = list(_ for _ in filenames if re.match(r"^clip[~][0-9]+~$", string=_))
    versions = list(int(_.split("~")[-2]) for _ in clips)
    last = max(versions) if versions else 0

    # Take the next name

    version = last + 1
    clippath = os.path.join(gotcwd, "clip~{}~".format(version))  # as in Emacs

    # Succeed

    return clippath


#
#
#


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
def check_shell_stdout(shline, stderr=None, returncode=(0,)):
    """Call silently, else trace and raise surprise Stderr or surprise Exit Status"""

    run_stderr = subprocess.PIPE if (stderr is None) else stderr

    # Call shell to run silently

    ran = subprocess.run(
        shline,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=run_stderr,
        shell=True,
    )

    # Raise CalledProcessError if surprise Stderr or surprise Exit Status

    if ran.stderr or (ran.returncode not in returncode):

        # First trace shell-like prompts and the input

        ps1 = platform.node() + os.pathsep + os.getcwd() + os.sep + "# "

        sys.stdout.flush()

        sys.stderr.write("...\n")
        sys.stderr.write("\n")
        sys.stderr.write("\n")

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

            if ran.stderr is not None:
                os.write(stderr_fd, ran.stderr)
                sys.stderr.flush()

        else:

            ipyout = ran.stdout.decode()
            sys.stdout.write(ipyout)
            sys.stdout.flush()

            if ran.stderr is not None:
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

    return ran


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
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


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

if __name__ == "__main__":
    main(sys.argv)

# copied from:  git clone https://github.com/pelavarre/pybashish.git
