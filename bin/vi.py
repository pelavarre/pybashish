#!/usr/bin/env python3

# To change defaults, rename this file to:  em.py, emacs.py, vi.py, vim.py

# The __main__.__doc__ of "vi.py" is =>

r"""
usage: vi.py [-h] [-u SCRIPT] [-c COMMAND] [--pwnme [BRANCH]] [--version] [FILE ...]

read files, accept edits, write files, in the way of classical vim

positional arguments:
  FILE              a file to edit (default: '/dev/stdin')

optional arguments:
  -h, --help        show this help message and exit
  -u SCRIPT         file of ex commands to run after args (default: '/dev/null')
  -c COMMAND        another ex command to run after args and after '-u'
  --pwnme [BRANCH]  update and run this code, don't just run it
  --version         print a hash of this code (its md5sum)

quirks:
  works as pipe filter, source, or drain, a la the vim drain:  ls |vi -
  accepts ⌥ Option shift in place of ⌃O while inserting or replacing chars
  loses input at crashes, and input of C0 Control bytes, except after ⌃V

keyboard cheat sheet:
  ⇧Z⇧Q ⇧Z⇧Z  ⌃Zfg  :q!⌃M :n!⌃M :w!⌃M  ⌃C Esc ⌃G  => how to quit & show version
  ⇧$ ⇧^ 0 Fx Tx ⇧Fx ⇧Tx ; , ⇧| H L  => leap to column
  W E B ⇧W ⇧E ⇧B ⌥→ ⌥← ⇧} ⇧{  => leap across small/ large words, paragraphs
  ⇧G 1⇧G ⇧L ⇧M ⇧H ⇧+ ⇧_ - ⌃J ⌃N ⌃P J K  => leap to line, screen row
  1234567890 ⌃C Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y ZT Z. ZB  99Z.  => scroll screen
  \N \I \⇧F ⌃C Esc ⌃G  => toggle line numbers, search case/ regex, show hits
  /... Delete ⌃U ⌃C Return  ?...   * # N ⇧N  => search ahead, behind, next
  /Return ?Return :g/Return  => search ahead, behind, lots
  ⌃L 999⌃L  ⌥EE ⇧⌥E⇧⌥E  ⌥NN ⇧⌥N⇧⌥N  => clear/ inject lag, escape mac einu accent
  Rx A I O ⇧R ⇧A ⇧I ⇧O ⌃V ⌃O ⌃C Esc  => replace, insert, & view, once or awhile
  X ⇧X ⇧J ⇧D ⇧C ⇧S S DD CC  => cut chars or lines, join lines, insert after cut

keyboard easter eggs:
  9^ $⌃OSpace ⇧G⌃F⌃F 1⇧G⌃B G⌃F⌃E 1⇧G⌃Y ; , N ⇧N 2G9k \N99Z.  3⇧Z⇧Q 512⇧Z⇧Q
  ⌃C Esc  123Esc ⇧A⌃OZ⇧Q⌃O⇧Z⇧Q /⌃G⌃C⇧Z⇧Q F⌃C W*⌃C W*123456N⌃C W*G/⌃M⌃C G/⌃Z
  ⇧QVI⌃MY ⇧REsc ⇧R⌃Zfg ⇧OO⌃O_⌃O^ \⇧FW*/Up \⇧F/$Return ⌃G2⌃G :vi⌃M :n
  C2W DD3. GJ  Z⇧Z⇧Z⇧Q ⇧ZZ ZQ Z⇧Q ⇧ZQ ⇧QZ ⇧Q⇧Z  :Esc 10⌃H

pipe tests of ⇧Z⇧Q vs ⇧Z⇧Z:
  ls |bin/vi.py -  # pipe drain
  cat bin/vi.py |bin/vi.py |grep import  # pipe filter

how to get Vi Py:
  R=pelavarre/pybashish/pelavarre-patch-1/bin/vi,py
  echo curl -sSO https=//raw,githubusercontent,com/$R |tr ,= .: |bash
  python3 vi.py vi.py  # with updates at:  python3 vi.py --pwnme
  /egg
"""

#
# Vim and Vi Py both
#   take '+...' as an arg in place of '-c "..."', and Vi Py
#   take the U0008 ⌃H BS \b chord in place of the U007F ⌃? DEL chord
#
# Unlike Vi Py, Vim quirkily
#   runs only as a pipe drain, declines to run as a pipe source or filter
#   does blink the screen for '+q' without '+vi'
#   defaults to neglect to accept ⌥ Option shift in place of ⌃O while insert/ replace
#   fails to conclude macOS ':set ttyfast' can afford ':set showcmd' and ':set ruler'
#   neglects to keep Z⇧Z undefined
#


# This code runs on top of basic Python 3, no additional 'pip install's required

# Flake8 feels the Import's must come after the first '__main__.__doc__' =>

import __main__
import argparse
import collections
import datetime as dt
import difflib
import hashlib
import inspect
import os
import pdb
import re
import select
import shlex
import signal
import string
import subprocess
import sys
import termios
import time
import traceback
import tty

subprocess_run = subprocess.run  # evade Linters who freak over "shell=True"

ENV_HOME = os.environ["HOME"]


# The __main__.__doc__ of "em.py" is =>

ALT_DOC = r"""
usage: em.py [-h] [-nw] [-Q] [--no-splash] [-q] [--script SCRIPT] [--eval COMMAND]
             [--pwnme [BRANCH]] [--version]
             [FILE ...]

read files, accept edits, write files, in the way of classical emacs

positional arguments:
  FILE                a file to edit (default: '/dev/stdin')

optional arguments:
  -h, --help          show this help message and exit
  -nw                 stay inside this terminal, don't open another terminal
  -Q, --quick         run as if --no-splash and --no-init-file (but slow after crash)
  --no-splash         start with an empty file, not a file of help
  -q, --no-init-file  don't default to run '~/.emacs' after args
  --script SCRIPT     file of elisp commands to run after args (default: '/dev/null')
  --eval COMMAND      another elisp command to run after args and after --script
  --pwnme [BRANCH]    update and run this code, don't just run it
  --version           print a hash of this code (its md5sum)

quirks:
  works in Mac Terminal, even without Use Option As Meta Key < Keyboard < Profiles
  works as pipe filter, source, or drain, a la the vim drain:  ls |vi -
  defaults to -Q --eval '(menu-bar-mode -1)', not the quirky '--script ~/.emacs'
  loses input at crashes, and input outside Basic Latin bytes, except after ⌃Q

keyboard cheat sheet:
  ⌃X⌃S⌃X⌃C  ⌃X⌃C  ⌃Zfg  ⌃G  => how to quit & show version
  ⌃E ⌥M ⌃A ⌃U⌥GTab ⌃F ⌃B  => leap to column
  ⌥← ⌥→  => leap across words
  ⇧⌥> ⇧⌥< ⌃N ⌃P ⌥G⌥G ⌃U99⌥G⌥G ⌥R⌥R⌥R  => leap to line, screen row
  ⌃U ⌃U -0123456789 ⌃U ⌥-⌥0..⌥9 ⌃G  => repeat, or don't
  ⌃L⌃L⌃L ⌃U⌃L  => scroll screen
  ⌃CN ⌃Q  => toggle line numbers, insert ⌥ and ⌃ chars
  ⌃D ⌃K  => cut chars of lines, join lines

keyboard easter eggs:
  ⌃Q⌃J  ⌃G⌃G ⌃U123⌃G  PQQ⇧P⌃A⌥Z⇧P  ⌃U-0 ⌃U07 ⌃U9⌃Z
  ⌃XC ⌃CX ⌃C⌃X ⇧⌥>⌃V⌃V⌃V ⇧⌥<⌥V ⌃X⌃G⌃X⌃C ⌃U⌃X⌃C ⌃U512⌃X⌃C

pipe tests:
  ls |bin/em.py -  # pipe drain
  cat bin/em.py |bin/em.py |grep import  # pipe filter

how to get Em Py:
  R=pelavarre/pybashish/pelavarre-patch-1/bin/vi,py
  echo curl -sSO https=//raw,githubusercontent,com/$R |tr ,= .: |bash
  echo cp -ip vi_py em_py |tr _ . |bash
  python3 em.py em.py  # with updates at:  python3 em.py --pwnme
  ⌃Segg
"""

#
# Emacs and Em Py both
#   misread a pasted Return to mean add the indentation of the line above  # TODO
#
# Unlike Em Py, Emacs quirkily
#   declines to run as pipe drain, source, or filter
#   declines to take Mac ⌥ Keystrokes of A..Z (minus EINU) as Meta Keyboard Chords
#   neglects to tab-complete and history-complete incremental searches  # TODO
#   neglects to keep ⌃X⌃G undefined
#

# TODO: ⌃S ⌃R ⇧⌥% ⌃XI ⌃X⌃U ⌃X⌃L ...
# TODO: ⌃X⌃X ...
# TODO: ⌃C% ⌃C- ⌃C⇧O ⌃CO ⌃CB ⌃CM ⌃CN ⌃CO ⌃CR ⌃CS ⌃CW ⌃C⇧|


#
# Run Vi Py or Em Py from the Command Line
#


def main(argv):
    """Run from the Command Line"""

    main.since = dt.datetime.now()

    args = parse_main_argv(argv)

    if args.pwnme is not False:
        do_main_arg_pwnme(branch=args.pwnme)
        assert False  # unreached

    if args.version:
        do_main_arg_version()
        if not (args.files or args.evals):

            sys.exit()

    # Load each File

    run_with_files(files=args.files, script=args.script, evals=args.evals)


def parse_main_argv(argv):
    """Convert a Vi Sys ArgV to an Args Namespace, or print some Help and quit"""

    doc = ALT_DOC if wearing_em() else None

    # Declare the Args,
    # and choose 'drop_help=True' to let 'parser_format_help' correct the Help Lines

    parser = argparse_compile_argdoc(epi="quirks", drop_help=True, doc=doc)

    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a file to edit (default: '/dev/stdin')",
    )

    parser.add_argument(
        "-h", "--help", action="count", help="show this help message and exit"
    )

    if not wearing_em():

        parser.add_argument(
            "-u",
            metavar="SCRIPT",
            dest="script",
            help="file of ex commands to run after args (default: '/dev/null')",
        )

        parser.add_argument(
            "-c",
            metavar="COMMAND",
            dest="evals",
            action="append",  # 'man vim' says <= 10 commands
            help="another ex command to run after args and after '-u'",
        )

    if wearing_em():

        parser.add_argument(
            "-nw",
            action="count",
            help="stay inside this terminal, don't open another terminal",
        )

        parser.add_argument(
            "-Q",
            "--quick",
            action="count",
            help="run as if --no-splash and --no-init-file (but slow after crash)",
        )

        parser.add_argument(
            "--no-splash",
            action="count",
            help="start with an empty file, not a file of help",
        )

        parser.add_argument(
            "-q",
            "--no-init-file",
            action="count",
            help="don't default to run '~/.emacs' after args",
        )

        parser.add_argument(
            "--script",
            metavar="SCRIPT",
            help="file of elisp commands to run after args (default: '/dev/null')",
        )

        parser.add_argument(
            "--eval",
            metavar="COMMAND",
            dest="evals",
            action="append",  # 'man vim' says <= 10 commands
            help="another elisp command to run after args and after --script",
        )

    parser.add_argument(
        "--pwnme",  # Vim quirkily doesn't do software-update-in-place
        metavar="BRANCH",
        nargs="?",
        default=False,
        help="update and run this code, don't just run it",
    )

    parser.add_argument(
        "--version",
        action="count",
        help="print a hash of this code (its md5sum)",
    )

    argparse_exit_unless_doc_eq(parser, doc=doc)

    # Auto-correct the Args

    if wearing_em():

        argv_tail = argv[1:]

    else:

        argv_tail = list()
        for arg in argv[1:]:
            if not arg.startswith("+"):
                argv_tail.append(arg)
            else:
                argv_tail.append("-c")
                argv_tail.append(arg[len("+") :])

    # Parse the Args (or print Help Lines to Stdout and Exit 0)

    args = parser.parse_args(argv_tail)
    if args.help:
        sys.stdout.write(parser_format_help(parser))

        sys.exit(0)  # return an explicit 0, same as Parser Add Help Parse Args would

    return args


def wearing_em():
    """True to look 'n feel more like Emacs, False to look 'n feel more like Vim"""

    verb = os_path_corename(sys.argv[0])
    em_in_verb = "em" in verb

    return em_in_verb


def parser_format_help(parser):
    """Patch around bugs in Python ArgParse formatting Help Lines inflexibly"""

    doc = parser.format_help()

    # Diff the Vi Py we distribute vs the Em Py, Emacs Py, and Vim Py we also run

    want_verb = "em" if wearing_em() else "vi"
    want_py = want_verb + ".py"  # such as "vi.py"
    want_qpy = want_verb + "?py"  # such as "vi?py"
    want_title_py = "Em Py" if wearing_em() else "Vi Py"

    got_verb = os_path_corename(sys.argv[0])  # such as "vim"
    got_py = got_verb + ".py"  # such as "vim.py"
    got_qpy = got_verb + "?py"  # such as "vim?py"
    got_title_py = got_verb.title() + " Py"  # such as "Vim Py"

    # When the version we run isn't the version we distribute

    if got_verb != want_verb:

        # Work out what patch we need

        wider = len(got_py) - len(want_py)
        assert wider >= 0, (got_verb, want_verb)

        want_cp_line = "  echo cp -ip vi_py em_py |tr _ . |bash"
        got_cp_line = want_cp_line.replace("em_py", got_py.replace(".", "_"))

        python3_line = "  python3 vi?py vi?py"

        # Apply the patch

        if want_cp_line in doc:
            doc = doc.replace(want_cp_line, got_cp_line)
        else:
            doc = doc.replace(
                "\n" + python3_line, "\n" + got_cp_line + "\n" + python3_line
            )

        doc = doc.replace(want_py, got_py)
        doc = doc.replace(want_qpy, got_qpy)
        doc = doc.replace("\n   ", "\n   " + (wider * " "))

        doc = doc.replace(want_title_py, got_title_py)  # such as "Em Py" --> "Emacs Py"

    return doc

    # TODO: stop bypassing 'argparse_exit_unless_doc_eq' here


def do_main_arg_version():
    """Print a hash of this Code (its Md5Sum) and exit"""

    version = module_file_version_zero()
    str_hash = module_file_hash()
    str_short_hash = str_hash[:4]  # conveniently fewer nybbles  # good enough?

    verb = os_path_corename(sys.argv[0])
    title_py = verb.title() + " Py"  # version of "Vi Py", "Em Py", etc

    print("{} {} hash {} ({})".format(title_py, version, str_short_hash, str_hash))


def do_main_arg_pwnme(branch):
    """Download fresh Code to run in place of this stale Code"""
    # pylint: disable=too-many-locals

    # Find present Self

    from_abspath = module_file_path()
    from_relpath = os.path.relpath(from_abspath)

    # Find future Self  # TODO: rename to branch "main" from branch "master"

    assert branch in (None, "", "master", "pelavarre-patch-1"), branch
    branch_ = branch if branch else "master"

    link = (
        "https://raw.githubusercontent.com/" "pelavarre/pybashish/{}/" "bin/vi.py"
    ).format(branch_)

    to_relpath = from_relpath

    callpath = to_relpath
    callpath = callpath if (os.sep in callpath) else os.path.join(os.curdir, callpath)

    # Compose a Bash Script
    # to back up Self, replace Self, mark Self as executable, call new Self

    when = main.since
    stamp = when.strftime("%m%djqd%H%M%S")
    mv_shline = "mv -i {relpath} {relpath}~{stamp}~".format(
        relpath=from_relpath, stamp=stamp
    )

    curl_shline = "curl -sS --location {link} >{relpath}".format(
        link=link, relpath=to_relpath
    )

    chmod_shline = "chmod ugo+x {relpath}".format(relpath=to_relpath)

    version_shline_0 = shlex_join([callpath, "--version"])

    shlines = [mv_shline, curl_shline, chmod_shline, version_shline_0]

    # Compose one more Bash Line to call new Self with Args, if more Args were given

    argv = list()
    argv.append(callpath)
    for (index, arg) in enumerate(sys.argv):
        if index:
            if arg.startswith("--pwnme"):
                pass
            elif (sys.argv[index - 1] == "--pwnme") and (arg[:1] not in "-+"):
                pass
            else:
                argv.append(arg)

    if argv[1:]:
        version_shline_1 = shlex_join(argv)
        shlines.append(version_shline_1)

    # Run the Bash Script, and exit with its process exit status returncode

    do_main_arg_version()  # print the Old Self, before download & run of the new Self

    for shline in shlines:
        stderr_print("+ {}".format(shline))
        try:
            _ = subprocess_run(shline, shell=True, check=True)
        except subprocess.CalledProcessError as exc:
            stderr_print("+ exit {}".format(exc.returncode))

            sys.exit(exc.returncode)

    sys.exit()  # exit old Self, after calling new Self once or twice


#
# Name some Terminal Input magic
#


C0_CONTROL_STDINS = list(chr(codepoint).encode() for codepoint in range(0x00, 0x20))
C0_CONTROL_STDINS.append(chr(0x7F).encode())

BASIC_LATIN_STDINS = list(chr(codepoint).encode() for codepoint in range(0x20, 0x7F))
BASIC_LATIN_CHARS_SET = set("".join(_.decode() for _ in BASIC_LATIN_STDINS))

assert len(C0_CONTROL_STDINS) == 33 == (128 - 95) == ((0x20 - 0x00) + 1)
assert len(BASIC_LATIN_STDINS) == 95 == (128 - 33) == (0x7F - 0x20)
assert len(C0_CONTROL_STDINS + BASIC_LATIN_STDINS) == 128

ORD_LF = 0x0A  # LF, ⌃J, 10 \n
LF_CHAR = chr(ORD_LF)

ORD_CR = 0x0D  # CR, ⌃M, 13 \r  # the Return key on a Mac Keyboard
CR_CHAR = chr(ORD_CR)
CR_STDIN = CR_CHAR.encode()

ORD_ESC = 0x1B  # ESC, ⌃[, 27
ESC_CHAR = chr(ORD_ESC)
ESC_STDIN = ESC_CHAR.encode()

X40_CONTROL_MASK = 0x40

X20_LOWER_MASK = 0x20
X20_UPPER_MASK = 0x20

# FIXME:  shuffle lots of the TerminalNudgeIn to here


#
# Name some Terminal Output magic
#

ESC = "\x1B"  # Esc
CSI = ESC + "["  # Control Sequence Introducer (CSI)

ED_2 = "\x1B[2J"  # Erase in Display (ED)  # 2 = Whole Screen
CUP_Y_X = "\x1B[{};{}H"  # Cursor Position (CUP)
CUP_1_1 = "\x1B[H"  # Cursor Position (CUP)  # (1, 1) = Upper Left

DECSCUSR_N = "\x1B[{} q"  # Set Cursor Style
DECSCUSR = "\x1B[ q"  # Clear Cursor Style (but doc'ed poorly)

SGR_N = "\x1B[{}m"  # Select Graphic Rendition
SGR = "\x1B[m"  # SGR > Reset, Normal, All Attributes Off

DECSC = ESC + "7"  # DEC Save Cursor
DECRC = ESC + "8"  # DEC Restore Cursor

_XTERM_ALT_ = "\x1B[?1049h"  # show Alt Screen
_XTERM_MAIN_ = "\x1B[?1049l"  # show Main Screen

SMCUP = DECSC + _XTERM_ALT_  # Set-Mode Cursor-Positioning
RMCUP = ED_2 + _XTERM_MAIN_ + DECRC  # Reset-Mode Cursor-Positioning


#
# Configure some Terminal Output magic
#


_CURSES_INITSCR_ = SMCUP + ED_2 + CUP_1_1
_CURSES_ENDWIN_ = RMCUP

_EOL_ = "\n"  # TODO: sometimes "\r\n" Dos, sometimes "\r" Classic Mac

_LIT_OPEN_ = SGR_N.format(7)  # Reverse Video, Invert, overriden by default Cursor
_LIT_CLOSE_ = SGR

_VIEW_CURSOR_STYLE_ = DECSCUSR_N.format(2)  # Steady Block  # Mac Terminal default
_REPLACE_CURSOR_STYLE_ = DECSCUSR_N.format(4)  # Steady Underline
_INSERT_CURSOR_STYLE_ = DECSCUSR_N.format(6)  # Steady Bar


#
# Parse some Terminal Output magic
#


class TerminalWriter(argparse.Namespace):
    """Split a mix of C0_CONTROL and other Chars into complete TerminalOrder's"""

    # pylint: disable=too-few-public-methods

    def __init__(self, chars):
        # pylint: disable=super-init-not-called

        regex = TerminalOrder.TERMINAL_WRITE_REGEX

        orders = list()
        for match in re.finditer(regex, string=chars):
            order = TerminalOrder(match)

            orders.append(order)

        self.orders = orders


class TerminalOrder(argparse.Namespace):
    """Split one whole Terminal Output Order into its Parts"""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    TERMINAL_WRITE_REGEX = r"".join(
        [
            r"(\x1B\[",  # Control Sequence Introducer (CSI)
            r"(([0-9?]+)(;([0-9?]+))?)?",  # 0, 1, or 2 Decimal Int or Question Args
            r"([^A-Z_a-z]*[A-Z_a-z]))",  # any Chars, then Ascii Letter
            r"|",
            r"(\x1B.)",  # else one escaped Char
            r"|",
            r"(\r\n|[\x00-\x1F\x7F])",  # else one or a few C0_CONTROL Chars
            r"|",
            r"([^\x00-\x1F\x7F]+)",  # else literal Chars
        ]
    )

    def __init__(self, match):
        # pylint: disable=super-init-not-called

        self.match = match

        # Name Groups of the Re Match of TERMINAL_WRITE_REGEX

        m = match
        self.chars = m.string[m.start() : m.end()]

        assert len(m.groups()) == 9

        self.literals = m.group(9)
        self.controls = m.group(8)
        self.escape_plus = m.group(7)
        self.csi_plus = m.group(1)

        groups = (self.literals, self.controls, self.escape_plus, self.csi_plus)
        assert sum(bool(_) for _ in groups) == 1, (self.chars, groups)
        assert self.chars in groups, (self.chars, groups)

        self.a = m.group(6)
        self.x = m.group(5)
        self.y = m.group(3)

        if not self.csi_plus:
            assert self.a is self.x is self.y is None, (self.chars, groups)
        else:
            assert self.a, (self.chars, groups)

        # Raise ValueError if CSI Order carries an X or Y that is not Decimal Int

        exc_arg = repr(self.chars)

        self.int_x = None
        if self.x is not None:
            try:
                self.int_x = int(self.x)
            except ValueError:

                raise ValueError(exc_arg) from None

        self.int_y = None
        if self.y is not None:
            try:
                self.int_y = int(self.y)
            except ValueError:
                assert False, (self.chars, groups)

        # Raise ValueError if CSI Order started and not ended

        if self.escape_plus and self.escape_plus.endswith(CSI):  # "\x1B["
            assert self.escape_plus == CSI  # as per TERMINAL_WRITE_REGEX

            raise ValueError(exc_arg)  # incomplete CSI TerminalOrder

        if self.controls and self.controls.endswith(ESC):  # "\x1B"

            raise ValueError(exc_arg)  # incomplete CSI TerminalOrder


#
# Run from the Command Line, with Files
#


def run_with_files(files, script, evals):
    """Load the first File and then execute Script then Evals, in the way of Vim"""

    if wearing_em():
        runner = TerminalEm(files, script=script, evals=evals)
    else:
        runner = TerminalVi(files, script=script, evals=evals)

    returncode = None
    try:

        runner.run_inside_terminal()  # like till SystemExit
        assert False  # unreached

    except OSError as exc:

        stderr_print("{}: {}".format(type(exc).__name__, exc))

        sys.exit(1)

    except SystemExit as exc:

        # Log the last lost Python Traceback to XTerm Main Screen

        returncode = exc.code
        if runner.main_traceback:
            stderr_print(runner.main_traceback)

        # Log the lost bits of Return Code to XTerm Main Screen, such as for 512ZQ Egg

        chopped_returncode = None if (returncode is None) else (returncode & 0xFF)
        if returncode != chopped_returncode:
            stderr_print(
                "{typename}: {str_exc} (0x{rc:X}) -> {r} (0x{r:X})".format(
                    typename=type(exc).__name__,
                    str_exc=str(exc),
                    rc=returncode,
                    r=chopped_returncode,
                )
            )

        sys.exit(returncode)

    assert False  # unreached


#
# Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim
#


VI_BLANK_SET = set(" \t")
VI_SYMBOLIC_SET = set(string.ascii_letters + string.digits + "_")  # r"[A-Za-z0-9_]"


class TerminalVi:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Vim"""

    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, files, script, evals):

        self.main_traceback = None  # capture Python Tracebacks

        self.em = None
        self.script = script  # Ex commands to run after Args
        self.evals = evals  # Ex commands to run after Script

        self.files = files  # file paths to read
        self.files_index = None  # last file path fetched

        self.held_vi_file = None  # last file fetched

        self.editor = None  # Terminal driver stack
        self.last_formatted_reply = None  # last TerminalReplyOut formatted by Self

        self.slip_choice = None  # find Char in Row
        self.slip_after = None  # slip off by one Column after finding Char
        self.slip_redo = None  # find later Char
        self.slip_undo = None  # find earlier Char

        self.seeking_column = None  # leap to Column in next Row, True to leap beyond
        self.seeking_more = None  # remembering the Seeking Column into next Nudge

        self.after_pin = None  # where the next move came from
        self.after_cut = None  # what to do after the next move
        self.after_did = None  # how to repeat the last cut or change

    #
    # Load each of the Files
    #

    def do_might_next_vi_file(self):  # Vim :n\r
        """Halt if touches Not flushed, else load the next (or first) File"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        if self.might_keep_changes(alt=":wn"):

            return

        self.next_vi_file()
        self.say_more()

    def do_next_vi_file(self):  # Vim :n!\r
        """Load the next (or first) File"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        self.next_vi_file()
        self.say_more()

    def next_vi_file(self):  # Vim :n!\r
        """Load the next (or first) File"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        editor = self.editor
        files_index = self.files_index
        files = self.files

        # Choose next File, else quit after last File

        if files_index is None:
            next_files_index = 0
            file_path = None if (not files) else files[next_files_index]
        elif files_index < (len(files) - 1):
            next_files_index = files_index + 1
            file_path = files[next_files_index]
        else:
            self.quit_vi()
            assert False  # unreached

            # Vi Py :n quits after last File
            # Vim :n Quirk chokes over no more Files chosen, after last File

        self.files_index = next_files_index

        # Map more abstract File Path Aliases to more concrete File Paths

        read_path = file_path
        if file_path == "-":
            read_path = "/dev/stdin"
        elif file_path is None:
            if not sys.stdin.isatty():
                read_path = "/dev/stdin"

        # Load the chosen File

        held_vi_file = TerminalFile(path=read_path)

        if read_path == "/dev/stdin":
            held_vi_file.touches = len(held_vi_file.iobytes)

        if not wearing_em():
            self.take_vi_views()  # turn off inserting/ replacing of ⌃O:n\r etc

        editor.load_editor_file(held_vi_file)

        self.held_vi_file = held_vi_file

    #
    # Layer thinly over TerminalEditor
    #

    def run_inside_terminal(self, em=None):
        """Enter Terminal Driver, then run Vi Keyboard, then exit Terminal Driver"""

        self.em = em

        script = self.script  # Vim Quirk falls back to lines of '~/.vimrc'
        evals = self.evals

        first_chords = self.fabricate_first_vi_chords(
            script=script,
            evals=evals,
        )

        # Form stack

        editor = TerminalEditor(chords=first_chords)
        self.editor = editor

        if not em:
            keyboard = TerminalKeyboardVi(vi=self)
        else:
            keyboard = TerminalKeyboardEm(em=em, vi=self)
            em.take_em_inserts()

        # Feed Keyboard into Screen, like till SystemExit

        try:

            editor.run_terminal_with_keyboard(keyboard)  # TerminalKeyboardVi
            assert False  # unreached

        except (Exception, SystemExit):

            # Log losing Lines from Dev Stdin Input, if quit without deleting some

            held_vi_file = self.held_vi_file
            if held_vi_file and held_vi_file.touches:
                if held_vi_file.read_path == "/dev/stdin":
                    ended_lines = held_vi_file.ended_lines

                    if ended_lines:
                        stderr_print(
                            "vi.py: dropping {} lines of Stdin".format(len(ended_lines))
                        )

            # Log losing Bytes from Tty Keyboard Input

            skin = editor.skin
            if skin:
                chord_ints_ahead = skin.chord_ints_ahead
                stdins = b"".join(
                    chr(_).encode(errors="surrogateescape") for _ in chord_ints_ahead
                )

                if stdins:
                    stderr_print("vi.py: dropping input: {}".format(repr(stdins)))

            raise

        finally:

            self.main_traceback = editor.skin.traceback  # /⌃G⌃C⇧Z⇧Q Egg

    def fabricate_first_vi_chords(self, script, evals):
        """Merge the first Chords from the Command Line with basic Vi Py Startup"""
        # pylint: disable=no-self-use

        chords = b""

        if wearing_em():
            chords += b"\x07"  # welcome with BEL, ⌃G, 7 \a  => do_em_keyboard_quit
        else:
            chords += b":n\r"  # autoload the first file => do_next_vi_file

        if script:
            with open(script) as reading:
                chars = reading.read()
            for line in chars.splitlines():
                ended_line = ":" + line + "\r"
                chords += ended_line.encode()

        if evals:
            for evalling in evals:
                ended_line = ":" + evalling + "\r"
                chords += ended_line.encode()

        if not wearing_em():
            chords += b":vi\r"  # go with XTerm Alt Screen  => do_resume_vi
            chords += b"\x03"  # welcome with ETX, ⌃C, 3  => do_vi_c0_control_etx

        return chords

        # TODO: Em Py to Load File before Script before Evals

    #
    # Layer thinly under the rest of TerminalVi
    #

    def do_vi_prefix_chord(self, chord):
        """Take r"[1-9][0-9]+"s as a Prefix to more Chords"""

        editor = self.editor

        prefix = editor.skin.nudge.prefix
        chords = editor.skin.nudge.chords

        keyboard = editor.skin.keyboard
        intake_chords_set = keyboard.choose_intake_chords_set()

        prefix_plus = chord if (prefix is None) else (prefix + chord)

        # Don't take more Prefix Chords after the first of the Chords to Call

        if chords or (chord in intake_chords_set):

            return False

        # Take this Chord as part of a Prefix before the Chords to Call
        # Else tell the Caller to take this Chord

        prefix_chords = b"123456789"
        more_prefix_chords = b"0123456789"

        if (chord in prefix_chords) or (prefix and chord in more_prefix_chords):
            editor.skin.nudge.prefix = prefix_plus

            return True

        return False

    def eval_vi_prefix(self, prefix):
        """Take the Chords before the Called Chords as a positive Int Prefix"""
        # pylint: disable=no-self-use

        evalled = int(prefix) if prefix else None
        assert (evalled is None) or (evalled >= 1)

        return evalled

    def vi_get_arg0_digit(self):
        """Pick out which Decimal Digit called this Code"""

        editor = self.editor
        chars = editor.get_arg0_chars()

        #

        esc_chars = r"\e0 \e1 \e2 \e3 \e4 \e5 \e6 \e7 \e8 \e9".replace(r"\e", "\x1B")
        esc_digits = esc_chars.split()

        optdigits = "⌥0 ⌥1 ⌥2 ⌥3 ⌥4 ⌥5 ⌥6 ⌥7 ⌥8 ⌥9".split()

        #

        optchars = chars

        if chars not in esc_digits:
            if chars not in optdigits:

                optchars = None

                items = TerminalNudgeIn.UNICHARS_BY_OPTCHARS.items()
                for (key, unichars) in items:
                    if chars == unichars:

                        optchars = key

                        break

                assert optchars in optdigits, (chars, optchars)

        str_digit = optchars[-1]

        assert str_digit in "0123456789", (chars, optchars)

        return str_digit

    def do_vi_c0_control_syn(self):  # Vim ⌃V during ⇧R ⇧A ⇧I ⇧O A I O
        """Define ⌃V during ⇧R ⇧A ⇧I ⇧O A I O, but not yet otherwise"""

        editor = self.editor
        if editor.intake_beyond:
            self.do_vi_quoted_insert()
        else:
            editor.do_raise_name_error()

    def do_vi_quoted_insert(self):  # Vim ⌃V inside ⇧R ⇧A ⇧I ⇧O A I O
        """Take the next Input Keyboard Chord to replace or insert, not as Control"""

        editor = self.editor
        keyboard = editor.skin.keyboard

        if editor.intake_beyond == "inserting":  # ⇧A ⇧I ⇧O A I O then ⌃V
            self.vi_print("Type one char to insert")
        else:
            assert editor.intake_beyond == "replacing"  # ⇧R then ⌃V
            self.vi_print("Type one char to replace")

        keyboard.intake_ish = True

    def get_vi_arg0_chars(self):
        """Get the Chars of the Chords pressed to call this Func"""

        return self.editor.get_arg0_chars()

    def get_vi_arg1_int(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        count = self.editor.get_arg1_int(default=default)
        assert (count is None) or isinstance(count, int), repr(count)

        return count

    def get_vi_arg2_chars(self):
        """Get the Bytes of the Suffix supplied after the Input Chords"""

        return self.editor.get_arg2_chars()

    def vi_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        self.editor.editor_print(*args)  # 'def vi_print' calling

    def check_vi_count(self):
        """Raise the Arg 0 and its Arg 1 Repeat Count as a NotImplementedError"""

        self.editor.check_repeat_count()

    def check_vi_index(self, truthy):
        """Fail fast, else proceed"""
        # pylint: disable=no-self-use

        if not truthy:

            raise IndexError()

    def keep_up_vi_column_seek(self):
        """Ask to seek again, like to keep on choosing the last Column in each Row"""

        assert self.seeking_column is not None
        self.seeking_more = True

    #
    # Define Chords for pausing TerminalVi
    #

    def do_say_more(self):  # Vim ⌃G
        """Reply once with more verbose details"""

        count = self.get_vi_arg1_int()

        editor = self.editor
        if editor.finding_line:
            editor.finding_highlights = True

        self.say_more(count)

        # Vim ⌃G Quirk doesn't turn Search highlights back on, Vi Py ⌃G does
        # TODO: Think more deeply into Vi Py ⌃C Esc vs Vi Py ⌃G

    def say_more(self, count=0):
        """Reply once with some details often left unmentioned"""

        editor = self.editor
        showing_lag = editor.showing_lag

        held_vi_file = self.held_vi_file
        write_path = held_vi_file.write_path

        # Mention the full Path only if asked

        homepath = os_path_homepath(write_path)
        nickname = held_vi_file.pick_file_nickname() if held_vi_file else None

        enough_path = homepath if (count > 1) else nickname  # ⌃G2⌃G Egg

        # Mention the Search in progress only if it's highlit

        if editor.finding_highlights:
            editor.reply_with_finding()

        # Mention injecting Lag

        str_lag = None
        if showing_lag is not None:
            str_lag = "{}s lag".format(showing_lag)

        # Collect the Mentions

        joins = list()

        joins.append(repr(enough_path))

        if str_lag:
            joins.append(str_lag)

        if held_vi_file.touches:
            joins.append("{} bytes touched".format(held_vi_file.touches))

        verb = os_path_corename(sys.argv[0])
        title_py = verb.title() + " Py"  # "Vi Py", "Em Py", etc
        joins.append(title_py)

        # Join the Mentions into one Status Row

        more_status = "  ".join(joins)
        editor.editor_print(more_status)  # such as "'bin/vi.py'  less lag"

    # TODO: explore Vim Quirk of scrolling and pausing to make room for wide pathnames

    def do_vi_c0_control_etx(self):  # Vim ⌃C  # Vi Py Init
        """Cancel Prefix, or close Replace/ Insert, or suggest ⇧Z⇧Q to quit Vi Py"""

        self.vi_keyboard_quit("Cancelled")

        # Vim ⌃C Quirk rings a Bell for each extra ⌃C, Vi Py doesn't

    def do_vi_c0_control_esc(self):  # Vim Esc
        """Cancel Prefix, or close Replace/ Insert, or suggest ⇧Z⇧Z to quit Vi Py"""

        self.vi_keyboard_quit("Escaped")

        # Vim Esc Quirk slowly rings a Bell for each extra Esc, Vi Py doesn't

    def vi_keyboard_quit(self, verbed):
        """Cancel or escape some one thing that is most going on"""

        count = self.get_vi_arg1_int(default=None)

        editor = self.editor
        skin = editor.skin
        keyboard = skin.keyboard

        if count is not None:  # 123⌃C Egg, 123Esc Egg, etc

            self.vi_print("{} Repeat Count".format(verbed))

        elif keyboard.intake_bypass:  # ⌃O⌃C Egg, ⌃O⌃Esc Egg

            self.vi_print("{} ⌃O Bypass".format(verbed))

        elif editor.intake_beyond == "inserting":  # ⇧A ⇧I ⇧O A I O then Esc ⌃C

            self.take_vi_views()
            rep_count = editor.format_touch_count()
            self.vi_print("{} after {} inserted".format(verbed, rep_count))

            skin.doing_traceback = skin.traceback  # ⌃C of A⌃OZ⇧Q⌃C⇧Z⇧Q Egg

            # FIXME report chars inserted this time, not since last save

        elif editor.intake_beyond == "replacing":  # ⇧R then Esc or ⌃C

            skin.doing_traceback = skin.traceback  # ⌃C of R⌃OZ⇧Q⌃C⇧Z⇧Q Egg

            self.take_vi_views()
            rep_count = editor.format_touch_count()
            self.vi_print("{} after {} replaced".format(verbed, rep_count))

            # FIXME report chars replaced this time, not since last save

        elif editor.finding_highlights:  # *⌃C Egg, *Esc Egg, etc

            self.vi_print("{} Search".format(verbed))
            editor.finding_highlights = None  # Vim ⌃C, Esc Quirks leave highlights up

        elif verbed == "Escaped":

            self.suggest_quit_vi("Press ⇧Z⇧Z to save changes")  # Esc Egg

        else:

            self.suggest_quit_vi("Press ⇧Z⇧Q to lose changes")  # ⌃C Egg

    def suggest_quit_vi(self, how):
        """Print how to Quit Em Py or Vi Py, etc"""

        version = module_file_version_zero()

        held_vi_file = self.held_vi_file
        nickname = held_vi_file.pick_file_nickname() if held_vi_file else None

        verb = os_path_corename(sys.argv[0])
        title_py = verb.title() + " Py"  # version of "Vi Py", "Em Py", etc

        self.vi_print(
            "{!r}  {} and quit {} {}".format(nickname, how, title_py, version)
        )

        # such as '/dev/stdout'  Press ⇧Z⇧Q to lose changes and quit Vim Py  0.1.23

    def do_continue_vi(self):  # Vim ⇧Q V I Return  # not Ex mode
        """Accept Q v i Return, without ringing the Terminal bell"""

        editor = self.editor

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Offer to play a game

        self.vi_ask("Would you like to play a game? (y/n)")

        chords = editor.take_one_chord_cluster()

        editor.skin.nudge.suffix = chords

        # Begin game, or don't

        verb = os_path_corename(sys.argv[0])
        title_py = verb.title() + " Py"  # version of "Vi Py", "Em Py", etc

        if chords in (b"y", b"Y"):
            self.vi_print("Ok, now try to quit {}".format(title_py))  # Qvi⌃My Egg
        else:
            self.vi_print("Ok")  # Qvi⌃Mn Egg

    def vi_ask(self, *args):
        """Ask a question, but don't wait for its answer"""

        editor = self.editor

        message = " ".join(str(_) for _ in args)
        message += " "  # place the cursor after a Space after the Message
        self.vi_print(message)  # 'def vi_ask' calling

        vi_reply = self.format_vi_status(self.editor.skin.reply)
        ex = TerminalEx(editor, vi_reply=vi_reply)
        ex.flush_ex_status()

    def do_resume_vi(self):  # Vim :vi\r  # Vi Py :em\r
        """Set up XTerm Alt Screen & Keyboard, till Painter Exit"""

        editor = self.editor

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        editor.do_resume_editor()

        # Vi Py :em without arg switches into running like Em Py
        # Vim :em Quirk defines :em only with args

    def do_vi_suspend_frame(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        editor = self.editor

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        reply = TerminalReplyOut(self.last_formatted_reply)
        reply.bell = False

        editor.do_suspend_frame()

        if self.seeking_column is not None:
            self.keep_up_vi_column_seek()

        editor.skin.reply = reply

    def do_cut_back_after_take_inserts(self):  # Vim C
        """Call to cut from here to there, after next move, and then take inserts"""

        after_cut = self.after_cut
        editor = self.editor

        self.check_vi_count()  # TODO: multiply Repeat Count into movement

        # Escape recursion of Vim C inside Vim C

        if self.editor.after_func and (after_cut == "changing"):

            self.after_cut = None
            self.after_pin = None
            assert self.after_did is None

            self.editor.after_func = None

            self.do_slip_first_chop_take_inserts()  # Vim C C

            return

        # Call for 'def do_cut_back' and 'def take_inserts' after next move

        self.after_cut = "changing"
        self.after_pin = editor.spot_pin()
        self.after_did = None

        self.editor.after_func = self.do_cut_back

        self.take_one_bypass()
        self.vi_print("Move the cursor ahead past end, or back to start, of cut")

        # FIXME: Code up lots more of Vim C

    def do_cut_back_after(self):  # Vim D
        """Call to cut from here to there, after next move"""

        after_cut = self.after_cut
        editor = self.editor

        self.check_vi_count()  # TODO: multiply Repeat Count into movement

        # Escape recursion of Vim D inside Vim D

        if self.editor.after_func and (after_cut == "deleting"):

            self.after_cut = None
            self.after_pin = None
            self.after_did = self.do_chop_down  # Vim D D

            self.editor.after_func = None

            self.after_did()

            return

        # Call for 'def do_cut_back' after next move

        self.after_cut = "deleting"
        self.after_pin = editor.spot_pin()
        self.after_did = None

        self.editor.after_func = self.do_cut_back

        self.take_one_bypass()
        self.vi_print("Move the cursor ahead past end, or back to start, of cut")

        # FIXME: For an empty File, Egg DG wrongly says "Cut back 1 lines"
        # FIXME: Code up lots more of Vim D
        # FIXME: Vim quirk deletes an extra Char at any of DFx D⇧Fx CFx C⇧Fx
        # FIXME: Vim quirk deletes an extra Line at D⇧G
        # FIXME: Vim quirk differs from Vi Py at ⇧MD⇧H

    def do_cut_back(self):
        """Cut from there to here"""

        after_cut = self.after_cut
        after_pin = self.after_pin  # TODO: work on the pin/ after_pin/ head/ tail names
        editor = self.editor
        keyboard = editor.skin.keyboard

        pin = editor.spot_pin()

        # Stop calling for work after move

        self.after_cut = None
        self.after_pin = None
        self.after_did = None

        # Cut the Selection, after leaping to its Upper Left

        self.cut_across(here_pin=pin, there_pin=after_pin)

        # Also start taking Inserts, if changing and not just deleting

        self.vi_print()  # Cancel the Status from Movement

        if after_cut != "changing":

            rep_count = editor.format_touch_count()
            self.vi_print("Cut back {}".format(rep_count))

        else:

            if keyboard.intake_bypass:  # TODO: make this less ugly
                keyboard.with_intake_bypass = ""
                keyboard.intake_beyond = keyboard.intake_bypass
                keyboard.intake_bypass = ""

            self.take_vi_inserts()

    def cut_across(self, here_pin, there_pin):
        """Cut the Selection, after leaping to its Upper Left"""

        editor = self.editor
        columns = editor.count_columns_in_row()

        # Sort the two Pins, so as to speak from Upper Left to Lower Right

        (here, there) = (here_pin, there_pin)
        if there_pin < here_pin:
            (here, there) = (there_pin, here_pin)

        # Leap to the upper left of the Selection

        editor.row = here.row
        editor.column = here.column

        # Option to just cut Chars within this Line

        if here.row == there.row:

            count = there.column - here.column

            touches = editor.delete_some_chars(count)
            self.held_vi_file.touches += touches

        else:

            # 1 ) Chop this Line

            touches = editor.delete_some_chars(count=columns)
            self.held_vi_file.touches += touches

            # 2 ) Delete the Lines in between

            count = there.row - here.row
            self.chop_down(count)

            # 3 ) Delete the Leftmost Chars of the last Line involved

            editor.row += 1

            touches = editor.delete_some_chars(there.column)
            self.held_vi_file.touches += touches

            editor.row -= 1

    def do_replay_cut(self):  # Vim .
        """Replay input Keyboard Chords recorded when last cutting Chars"""

        self.check_vi_index(self.after_did)

        self.after_did()

        # FIXME: Code up lots more of Vim .

    def do_record_over_choice(self):  # Vim Qx
        """Record input Keyboard Chords till next Q, into Macro labelled by Char"""

        raise NotImplementedError()

    #
    # Define Chords for entering, pausing, and exiting TerminalVi
    #

    def do_might_flush_next_vi(self):  # Vim :wn\r
        """Write this File and load Next File, with less force"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        self.do_flush_next_vi()  # TODO: distinguish :wn from :wn!

        # Vi Py :wn quits after last File
        # Vim :wn Quirk chokes over no more Files chosen, after last File

    def do_flush_next_vi(self):  # Vim :wn!\r
        """Write this File and load Next File, with more force"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        self.vi_save_buffer()
        self.next_vi_file()

        # Vi Py :wn! quits after last File
        # Vim :wn! Quirk chokes over no more Files chosen, after last File

        # Vi Py :wn and :wn! announce the Write, and not the Next
        # Vim :wn :wn! Quirks announce the Next, and not the Write

    def do_might_flush_quit_vi(self):  # Vim :wq\r
        """Write the File and quit Vi, except only write without quit if more Files"""

        if self.might_keep_files(alt=":wn"):

            return

        self.do_flush_quit_vi()
        assert False  # unreached

        # Vi Py :wq doesn't write nor quit, while more Files chosen than fetched
        # Vim :wq Quirk doesn't quit and does write, when more Files chosen than fetched
        # Vim :wq :wq Quirk quits, despite more Files chosen than fetched

    def do_talk_of_shift_z_shift_z(self):  # Vim ⇧ZZ, akin to Vim ⇧QZ
        """Suggest ⇧Z⇧Z in place of a ⇧ZZ shifting error, etc"""

        self.vi_print("Did you mean ⇧Z ⇧Z")

    def do_flush_quit_vi(self):  # Vim ⇧Z⇧Z  # Vim :wq!\r
        """Write the File and quit Vi"""

        self.vi_save_buffer()

        self.quit_vi()
        assert False  # unreached

        # Vi Py ⇧Z⇧Z and :wq! do quit, despite more Files chosen than fetched
        # Vim ⇧Z⇧Z Quirk doesn't, but Vim ⇧Z⇧Z, ⇧Z⇧Z, and :wq! do quit

    def do_might_vi_save_buffer(self):  # Vim :w\r
        """Write the File and do Not quit it, with less force"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count
        self.vi_save_buffer()  # TODO: distinguish :w from :w!

    def do_vi_save_buffer(self):  # Vim :w!\r
        """Write the File and do Not quit it, with more force"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count
        self.vi_save_buffer()

    def vi_save_buffer(self):
        """Write the File"""

        editor = self.editor
        held_vi_file = self.held_vi_file

        painter = editor.painter

        if held_vi_file.write_path == held_vi_file.read_path:
            held_vi_file.flush_file()
        else:
            exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
            painter.__exit__(*exc_info)
            try:
                held_vi_file.flush_file()
                time.sleep(0.001)  # TODO: wout this, fails 1 of 10:  ls |vi.py |cat -n
            finally:
                painter.__enter__()

            # TODO: shuffle this code down into TerminalEditor

        self.vi_print(
            "wrote {:_} lines as {:_} bytes".format(
                len(held_vi_file.ended_lines), len(held_vi_file.iobytes)
            )
        )

        # TODO: Vim :w! vs Vim :w

    def do_might_quit_vi(self):  # Vim :q\r
        """Halt if Touches not Flushed or More Files, else quit Vi"""

        if self.might_keep_changes(alt=":wq"):

            return

        if self.might_keep_files(alt=":n"):

            return

        self.quit_vi()
        assert False  # unreached

        # Vi Py :q doesn't quit while more Files chosen than fetched, Vi Py :q! does
        # Vim :q :q Quirk quits, despite more Files chosen than fetched

    def might_keep_changes(self, alt):
        """True if said how to bypass, False if no Touches held"""

        held_vi_file = self.held_vi_file

        if held_vi_file:
            touches = held_vi_file.touches
            if touches:
                self.vi_print("{} bytes touched - Do you mean {}".format(touches, alt))

                return True

        return False

    def might_keep_files(self, alt):
        """True if said how to bypass, False if no Files held"""

        files = self.files
        files_index = self.files_index

        more_files = files[files_index:][1:]
        if more_files:
            self.vi_print("{} more files - Do you mean {}".format(len(more_files), alt))

            return True

        return False

    def do_talk_of_shift_z_shift_q(self):  # Vim ⇧Q⇧Z, akin to Emacs ⌃C⌃X
        """Suggest ⇧Z⇧Q in place of a ⇧Q⇧Z⇧Q framing error, etc"""

        self.vi_print("Did you mean ⇧Z ⇧Q")

    def do_quit_vi(self):  # Vim ⇧Z⇧Q  # Vim :q!\r
        """Lose last changes, but keep last Python Traceback, and quit Vi"""

        editor = self.editor
        skin = editor.skin

        skin.doing_traceback = skin.traceback  # ⇧Z⇧Q of such eggs as Z⇧Z⇧Z⇧Q
        self.quit_vi()

    def quit_vi(self):
        """Lose last changes and maybe last Python Traceback too, but now quit Vi"""

        editor = self.editor
        skin = editor.skin

        skin.traceback = skin.doing_traceback  # option to log last Python Traceback
        skin.doing_traceback = None

        returncode = self.get_vi_arg1_int(default=None)

        sys.exit(returncode)  # Mac & Linux truncate 'returncode' to 'returncode & 0xFF'

    #
    # Define Chords to take a Word of this Line as the Search Key, and look for it
    #

    def do_find_ahead_vi_this(self):  # Vim ⇧*
        """Take a Search Key from this Line, and then look ahead for it"""

        editor = self.editor
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if self.slip_find_fetch_vi_this(slip=+1) is None:
                self.vi_print("Press * # only when Not on a blank line")  # * Egg

                return

        # Try the Search

        if editor.find_ahead_and_reply():

            editor.continue_do_loop()

        # Vi Py "*" echoes its Search Key as Status, at *, at /Up, at :g/Up, etc
        # Vim "*" Quirk echoes its Search Key as Status, only if ahead on same screen

    def do_find_behind_vi_this(self):  # Vim ⇧#
        """Take a Search Key from this Line, and then look behind for it"""

        editor = self.editor
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if self.slip_find_fetch_vi_this(slip=-1) is None:  # # Egg
                self.vi_print("Press # * only when Not on a blank line")

                return

        # Try the Search

        if editor.find_behind_and_reply():

            editor.continue_do_loop()

        # Vi Py "#" echoes its Search Key as Status, at #, at /Up, at :g/Up, etc
        # Vim "#" Quirk echoes its Search Key as Status, only if behind on same screen

    def slip_find_fetch_vi_this(self, slip):
        """Take a Word from this Line and return Truthy, else don't"""

        editor = self.editor

        # Take this Word

        word = self.slip_fetch_vi_word_here()
        if word is not None:
            assert word != ""

            # Make this Word into a Search Key for Words

            search_key = word  # partial Words and whole Words
            if word and editor.finding_regex:
                search_key = r"\b" + re.escape(search_key) + r"\b"  # whole Words only

            # Search for the Key

            editor.finding_line = search_key
            editor.finding_slip = slip

            assert editor.finding_line != ""
            editor.reopen_found_spans()

            # Pass back Word found, but with no mention of more Match'es found or not

            return word

        return None

    def slip_fetch_vi_word_here(self):
        """Slip to start Symbolic word, else Non-Blank word, in Line and return it"""

        # Setup

        editor = self.editor

        column = editor.column
        columns = editor.count_columns_in_row()

        def in_vi_symbolic(ch):

            return ch in VI_SYMBOLIC_SET

        def not_in_vi_blank(ch):

            return ch not in VI_BLANK_SET

        # Take a Symbolic word, else a Non-Blank word

        behind = column
        for in_vi_word_func in (in_vi_symbolic, not_in_vi_blank):

            # Look behind to first Char of Word

            while behind:
                ch = editor.fetch_column_char(column=behind)
                if not in_vi_word_func(ch):

                    break

                behind -= 1

            # Look ahead to first Char of Word

            for start in range(behind, columns):
                ch = editor.fetch_column_char(column=start)
                if in_vi_word_func(ch):

                    # Slip ahead to Start of Word

                    editor.column = start

                    # Collect one or more Chars of Word

                    word = ""

                    for end in range(start, columns):
                        ch = editor.fetch_column_char(column=end)
                        if in_vi_word_func(ch):
                            word += ch
                        else:

                            break

                    assert word

                    return word

    #
    # Define Chords to take a Search Key as additional Input, and look for it
    #

    def do_find_ahead_vi_line(self):  # Vim /
        """Take a Search Key as input, and then look ahead for it"""

        editor = self.editor
        editor.reply_with_finding()

        # Take up a new Search Key

        if not editor.skin.doing_done:
            if not self.take_read_vi_line(slip=+1):

                return

        # Try the Search

        if editor.find_ahead_and_reply():  # TODO: extra far scroll <= zb H 23Up n

            editor.continue_do_loop()

        # Vi Py / echoes its Search Key as Status, at /, at /Up, at :g/Up, etc
        # Vim / Quirk echoes its Search Key as Status, only if ahead on same screen

    def do_find_trailing_vi_lines(self):  # Vim :g/   # Vi Py :g/, g/
        """Across all the File, print each Line containing 1 or More Matches"""

        editor = self.editor
        editor.reply_with_finding()

        # Take Search Key as input, but leave Search Slip unchanged

        if not self.take_read_vi_line(slip=0):

            return

        # Print Matches

        stale_status = self.format_vi_status(editor.skin.reply) + editor.finding_line

        if editor.find_ahead_and_reply():
            self.vi_print()  # consume such as '1/358  Found 3 chars ahead as:  def'

            iobytespans = editor.iobytespans
            assert iobytespans

            last_span = iobytespans[-1]
            pin = editor.span_to_pin_on_char(last_span)
            (editor.row, editor.column) = pin

            editor.print_some_found_spans(stale_status)

            self.vi_print(  # "{}/{} Found {} chars"  # :g/, g/ Eggs
                "{}/{} Found {} chars".format(
                    len(iobytespans),
                    len(iobytespans),
                    last_span.beyond - last_span.column,
                )
            )

        # Vi Py :g/ lands the Cursor on the last Hit in File
        # Vim :g/ Quirk kicks the Cursor to the first non-blank Column in Line of Hit

        # Vi Py :g? lands the Cursor on the first Hit in File  # TODO
        # Vim :g? Quirk takes it as an alias of Vim :g/

        # Vi Py shares one Search Key input history across ⇧* ⇧# / ⇧? g/ g? :g/ :g?
        # Vim ⇧* ⇧# / ⇧? :g/ :g? Quirks divide their work into three input histories

        # TODO: Vim :4g/ Quirk means search only line 4, not pick +-Nth match

    def do_find_behind_vi_line(self):  # Vim ⇧?
        """Take a Search Key as input, and then look behind for it"""

        editor = self.editor
        editor.reply_with_finding()

        if not editor.skin.doing_done:
            if not self.take_read_vi_line(slip=-1):

                return

        if editor.find_behind_and_reply():  # TODO: extra far scroll # <= zt L 23Down N

            editor.continue_do_loop()

        # Vi Py ⇧? echoes its Search Key as Status, at ?, at ?Up, at :g?Up, etc
        # Vim ⇧? Quirk echoes its Search Key as Status, only if ahead on same screen

    def take_read_vi_line(self, slip):
        """Take a Search Key"""

        editor = self.editor

        assert editor.finding_line != ""  # may be None, but never Empty
        slip_ = slip if slip else editor.finding_slip

        # Ask for fresh Search Key

        finding_line = None
        finding_line = self.read_vi_line()

        # Cancel Search if accepting stale Search Key while no stale Search Key exists

        if not finding_line:

            if finding_line is None:
                self.vi_print("Search cancelled")  # /⌃C, ?⌃C Eggs

                return False

            if not editor.finding_line:  # Vim Return  # /Return Egg, ?Return Egg
                if slip < 0:  # ?Return Egg
                    self.vi_print("Press one of ? / # * to enter a Search Key")
                else:  # /Return Egg
                    self.vi_print("Press one of / ? * # to enter a Search Key")

                return False

        # Take fresh Slip always, and take fresh Search Key if given

        editor.finding_slip = slip_

        if finding_line:
            editor.finding_line = finding_line

        # Pick out Matches

        assert editor.finding_line != ""
        editor.reopen_found_spans()

        return True

    def read_vi_line(self):
        """Take a Line of Input"""

        editor = self.editor

        vi_reply = self.format_vi_status(self.editor.skin.reply)
        ex = TerminalEx(editor, vi_reply=vi_reply)
        line = ex.read_ex_line()

        return line

    #
    # Define Chords to search again for the same old Search Key
    #

    def do_vi_find_earlier(self):  # Vim ⇧N
        """Leap to earlier Search Key Match"""

        editor = self.editor

        ahead_and_reply = editor.find_ahead_and_reply
        behind_and_reply = editor.find_behind_and_reply
        slip = editor.finding_slip

        editor.reply_with_finding()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press one of ? / # * to enter a Search Key")  # N Egg

            return

        # Try the Search

        and_earlier_func = behind_and_reply if (slip >= 0) else ahead_and_reply
        if and_earlier_func():

            editor.continue_do_loop()

    def do_vi_find_later(self):  # Vim N
        """Leap to later Search Key Match"""

        editor = self.editor

        ahead_and_reply = editor.find_ahead_and_reply
        behind_and_reply = editor.find_behind_and_reply
        slip = editor.finding_slip

        editor.reply_with_finding()

        # Take up an old Search Key

        if editor.finding_line is None:
            self.vi_print("Press one of / ? * # to enter a Search Key")  # n Egg

            return

        # Try the Search

        and_later_func = ahead_and_reply if (slip >= 0) else behind_and_reply
        if and_later_func():

            editor.continue_do_loop()

    #
    # Slip the Cursor into place, in some other Column of the same Row
    #

    def do_slip(self):  # Vim |
        """Leap to first Column, else to a chosen Column"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        max_column = editor.spot_max_column()
        column = min(max_column, count - 1)

        editor.column = column

    def do_slip_dent(self):  # Vim ⇧^
        """Leap to just past the Indent, but first Step Down if Arg"""

        count = self.get_vi_arg1_int(default=None)

        editor = self.editor

        if count is not None:
            self.vi_print("Do you mean {} _".format(count))  # 9^ Egg, etc

        if False:  # pylint: disable=using-constant-test
            editor.clear_intake_bypass()  # OO⌃O_⌃O^ Egg

        editor.slip_dent()

        # Vim ⌃O Quirk past a Line of 1 Dented Char snaps back after _ but not after ^
        # Vi Py could, and does Not, repro this Quirk

    def do_slip_first(self):  # Vim 0  # Vim ⌥0
        """Leap to the first Column in Row"""

        editor = self.editor
        if editor.skin.arg1 is None:

            editor.column = 0

        else:

            self.do_vi_digit_argument()

    def do_slip_left(self):  # Vim H, ← Left-Arrow
        """Slip left one Column or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        self.check_vi_index(editor.column)

        left = min(editor.column, count)
        editor.column -= left

    def do_slip_right(self):  # Vim L, → Right-Arrow
        """Slip Right one Column or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        max_column = editor.spot_max_column()
        self.check_vi_index(editor.column < max_column)

        right = min(max_column - editor.column, count)
        editor.column += right

    #
    # Step the Cursor across zero, one, or more Columns of the same Row
    #

    def do_slip_ahead(self):  # Vim Space
        """Slip right, then down"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        if self.slip_ahead_one():

            editor.continue_do_loop()

    def slip_ahead_one(self):
        """Slip right or down, and return 1, else return 0 at End of File"""

        editor = self.editor

        max_column = editor.spot_max_column()
        last_row = editor.spot_last_row()

        if editor.column < max_column:
            editor.column += 1

            return 1

        if editor.row < last_row:
            editor.column = 0
            editor.row += 1

            return 1

        return 0

        # Vi Py ⌃O Delete does slip behind into the column beyond end of line
        # Vim ⌃O Delete and Vi Py ⌃O Space does too, but
        # Vim ⌃O Space Quirk slips over the column beyond end of line, oops

    def do_slip_behind(self):  # Vim Delete
        """Slip left, then up"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_first_pin() < editor.spot_pin())

        if self.slip_behind_one():

            editor.continue_do_loop()

        # Vim ⌃H Quirk says 45 ⌃H  means 45, not 4 of something else
        # Vim Delete Quirk says 45 Delete means 45, not 4 of something else
        # Vi Py ⌃H Quirk and Vi Py Delete Quirk says same  # TODO: maybe shouldn't?

    def slip_behind_one(self):
        """Slip left or up, and return -1, else return 0 at Start of File"""

        editor = self.editor

        if editor.column:
            editor.column -= 1

            return -1

        if editor.row:
            editor.row -= 1
            row_max_column = editor.spot_max_column(row=editor.row)
            editor.column = row_max_column

            return -1

        return 0

    #
    # Step the Cursor across zero, one, or more Lines of the same File
    #

    def do_step_for_count(self):  # Vim ⇧G, 1⇧G
        """Leap to last Row, else to a chosen Row"""

        editor = self.editor
        last_row = editor.spot_last_row()

        editor.step_for_count_slip_to_dent(default=(last_row + 1))

    def do_step_down_dent(self):  # Vim ⇧+, Return
        """Step down a Row or more, but land just past the Indent"""

        self.step_down_for_count()
        self.editor.slip_dent()

    def step_down_for_count(self):
        """Step down one Row or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor
        row = editor.row
        last_row = editor.spot_last_row()

        self.check_vi_index(row < last_row)
        down = min(last_row - row, count)

        editor.row += down

    def do_step_down_minus_dent(self):  # Vim ⇧_
        """Leap to just past the Indent, but first Step Down if Arg"""

        self.step_down_for_count_minus()
        self.editor.slip_dent()

    def step_down_for_count_minus(self):
        """Step down zero or more Rows, not one or more Rows"""

        count = self.get_vi_arg1_int()

        down = count - 1
        if down:
            self.editor.skin.arg1 -= 1  # mutate  # ugly
            self.step_down_for_count()

    def do_step_max_low(self):  # Vim ⇧L
        """Leap to first Word of Bottom Row on Screen"""

        editor = self.editor
        editor.row = editor.spot_bottom_row()
        editor.slip_dent()

        self.vi_print("bounced the Cursor to Left Column of Bottom Row")

    def do_step_max_high(self):  # Vim ⇧H
        """Leap to first Word of Top Row on Screen"""

        editor = self.editor
        editor.row = editor.top_row
        editor.slip_dent()

        self.vi_print("bounced the Cursor to Left Column of Top Row")

    def do_step_to_middle(self):  # Vim ⇧M
        """Leap to first Word of Middle Row on Screen"""

        editor = self.editor
        editor.row = editor.spot_middle_row()
        editor.slip_dent()

        self.vi_print("bounced the Cursor to Left Column of Middle Row")

    def do_step_up_dent(self):  # Vim -
        """Step up a Row or more, but land just past the Indent"""

        self.step_up_for_count()
        self.editor.slip_dent()

    def step_up_for_count(self):
        """Step up one Row or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor
        self.check_vi_index(editor.row)
        up = min(editor.row, count)

        editor.row -= up

    #
    # Step the Cursor up and down between Rows, while holding on to the Column
    #

    def do_slip_max_seek(self):  # Vim ⇧$
        """Leap to the last Column in Row, and keep seeking last Columns"""

        editor = self.editor

        self.seeking_column = True

        self.step_down_for_count_minus()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def do_step_down_seek(self):  # Vim J, ⌃J, ⌃N, ↓ Down-Arrow
        """Step down one Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_down_for_count()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def do_step_up_seek(self):  # Vim K, ⌃P, ↑ Up-Arrow
        """Step up a Row or more, but seek the current Column"""

        editor = self.editor

        if self.seeking_column is None:
            self.seeking_column = editor.column

        self.step_up_for_count()

        editor.column = self.seek_vi_column()
        self.keep_up_vi_column_seek()

    def seek_vi_column(self):
        """Begin seeking a Column, if not begun already"""

        editor = self.editor

        max_column = editor.spot_max_column()

        if self.seeking_column is True:
            sought_column = max_column
        else:
            sought_column = min(max_column, self.seeking_column)

        return sought_column

    #
    # Scroll ahead or behind almost one Whole Screen of Rows
    #

    def do_scroll_ahead_much(self):  # Vim ⌃F
        """Scroll ahead much"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row
        editor = self.editor
        painter = editor.painter

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        bottom_row = editor.spot_bottom_row()
        last_row = editor.spot_last_row()

        # Quit at last Row

        if top_row == last_row:
            if not self.editor.skin.doing_done:
                self.vi_print("Do you mean ⌃B")  # G⌃F⌃F Egg

            return

        # Step one Up if in Bottom Row already

        if (row == bottom_row) and (row != last_row):
            if row:
                row -= 1

        # Choose new Top Row

        if row == last_row:
            top_row = last_row
        else:
            top_row += rows_per_screen
            top_row = min(top_row, last_row)

        editor.top_row = top_row

        # Choose new Row and Column

        if row < top_row:  # pylint: disable=consider-using-max-builtin
            row = top_row

        editor.row = row

        editor.slip_dent()

        editor.continue_do_loop()

    def do_scroll_behind_much(self):  # Vim ⌃B
        """Show the previous Screen of Rows"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row
        editor = self.editor
        painter = editor.painter

        last_row = editor.spot_last_row()

        # Quit at top Row

        if not top_row:
            if not self.editor.skin.doing_done:
                self.vi_print("Do you mean ⌃F")  # 1G⌃B Egg

            return

        assert painter.scrolling_rows >= 2
        rows_per_screen = painter.scrolling_rows - 2

        # Step one Down if in Top Row already

        if row == top_row:
            if top_row < last_row:
                row += 1

        # Choose new Top Row

        if rows_per_screen >= top_row:
            top_row = 0
        else:
            top_row -= rows_per_screen

        editor.top_row = top_row

        # Choose new Row and Column

        bottom_row = editor.spot_bottom_row()
        if row > bottom_row:  # pylint: disable=consider-using-min-builtin
            editor.row = bottom_row

        editor.slip_dent()

        editor.continue_do_loop()

    #
    # Scroll ahead or behind one Row of Screen
    #

    def do_scroll_ahead_one(self):  # Vim ⌃E Line Down
        """Scroll to show the next Row of Screen"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row

        editor = self.editor
        last_row = editor.spot_last_row()

        # Quit at last Row

        if editor.top_row == last_row:
            if not editor.skin.doing_done:
                self.vi_print("Do you mean ⌃Y")  # G⌃F⌃E Egg

            return

        # Scroll ahead one, but keep Cursor on Screen

        if top_row < last_row:
            top_row += 1
            if row < top_row:  # pylint: disable=consider-using-max-builtin
                row = top_row

        editor.top_row = top_row  # always different Top Row

        editor.row = row  # same or different Row
        editor.slip_dent()  # same or different Column

        editor.continue_do_loop()

    def do_scroll_behind_one(self):  # Vim ⌃Y Line Up
        """Scroll to show the previous Row of Screen"""

        editor = self.editor

        row = editor.row
        top_row = editor.top_row

        # Quit at top Row

        if not top_row:
            if not editor.skin.doing_done:
                self.vi_print("Do you mean ⌃E")  # 1G⌃Y Egg

            return

        # Scroll behind one, but keep Cursor on Screen

        if top_row:
            top_row -= 1

            bottom_row = editor.spot_bottom_row(top_row)
            if row > bottom_row:  # pylint: disable=consider-using-min-builtin
                row = bottom_row

        editor.top_row = top_row  # always different Top Row

        editor.row = row  # same or different Row
        editor.slip_dent()  # same or different Column

        editor.continue_do_loop()

    #
    # Scroll Rows of the Screen
    #

    def do_scroll_till_top(self):  # Vim Z T
        """Scroll up or down till Cursor Row lands in Top Row of Screen"""

        editor = self.editor
        editor.step_for_count_slip_to_dent(default=(editor.row + 1))
        editor.scroll_till_top()

    def do_scroll_till_middle(self):  # Vim Z .  # not Vim ⇧Z⇧Z
        """Scroll up or down till Cursor Row lands in Middle Row of Screen"""

        editor = self.editor
        editor.step_for_count_slip_to_dent(default=(editor.row + 1))
        editor.scroll_till_middle()

    def do_scroll_till_bottom(self):  # Vim Z B
        """Scroll up or down till Cursor Row lands in Bottom Row of Screen"""

        editor = self.editor
        editor.step_for_count_slip_to_dent(default=(editor.row + 1))
        editor.scroll_till_bottom()

    #
    # Search ahead for an Empty Line (while ignoring Blank Lines)
    #

    def do_paragraph_ahead(self):  # Vim ⇧}
        """Step down over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor

        if editor.skin.doing_done:
            if editor.spot_pin() >= editor.spot_last_pin():

                raise IndexError()

        while not editor.count_columns_in_row():
            if editor.row >= editor.spot_last_row():

                break

            editor.row += 1
            editor.column = 0

        while editor.count_columns_in_row():
            if editor.row >= editor.spot_last_row():
                editor.column = editor.spot_last_column()  # end at last Pin, not max

                break

            editor.row += 1
            editor.column = 0

        editor.continue_do_loop()

    def do_paragraph_behind(self):  # Vim ⇧{
        """Step up over Empty Lines, then over Non-Empty Lines"""

        editor = self.editor

        if editor.skin.doing_done:
            if not editor.row:

                raise IndexError()

        while not editor.count_columns_in_row():
            if not editor.row:

                break

            editor.row -= 1

        while editor.count_columns_in_row():
            if not editor.row:

                break

            editor.row -= 1

        editor.column = 0

        editor.continue_do_loop()

    #
    # Step across "Big" Words between Blanks, and "Lil" Words of Symbolic/Not Chars
    #

    def do_big_word_end_ahead(self):  # Vim ⇧E
        """Slip ahead to last Char of this else next Big Word"""

        self.word_end_ahead_for_count(VI_BLANK_SET)

    def do_lil_word_end_ahead(self):  # Vim E
        """Slip ahead to last Char of this else next Lil Word"""

        self.word_end_ahead_for_count(VI_BLANK_SET, VI_SYMBOLIC_SET)

    def word_end_ahead_for_count(self, *charsets):
        """Slip ahead to last Char of this else next Word"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_end_ahead_once(charsets)

        editor.continue_do_loop()

    def word_end_ahead_once(self, charsets):
        """Slip ahead to last Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        self.slip_ahead_one()

        # Slip ahead across Blanks and Empty Lines, between Words, up to End of File

        while not editor.charsets_find_column(charsets):
            if not self.slip_ahead_one():

                break

        # Slip ahead across Chars of Word in Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                row_last_column = editor.spot_last_column(row=editor.row)
                if editor.column == row_last_column:

                    return

                ahead = self.slip_ahead_one()
                assert ahead, (editor.column, editor.count_columns_in_row())

            behind = self.slip_behind_one()  # backtrack
            assert behind, (editor.column, editor.count_columns_in_row())

    def do_big_word_start_ahead(self):  # Vim ⇧W, Vi Py ⌥→  # inverse of Vim ⇧B
        """Slip ahead to first Char of next Big Word"""

        self.word_start_ahead_for_count(VI_BLANK_SET)

        # Vi Py ⌥→ Option Right-Arrow works like Vi Py ⇧W
        # Vim ⌥→ Quirk defaults to block Option Right-Arrow from working like Vim ⇧W

    def do_lil_word_start_ahead(self):  # Vim W  # inverse of Vim B
        """Slip ahead to first Char of next Lil Word"""

        self.word_start_ahead_for_count(VI_BLANK_SET, VI_SYMBOLIC_SET)

    def word_start_ahead_for_count(self, *charsets):
        """Slip ahead to first Char of next Word"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_start_ahead_once(charsets)

        editor.continue_do_loop()

    def word_start_ahead_once(self, charsets):
        """Slip ahead to first Char of this else next Word"""

        editor = self.editor

        # Slip ahead at least once (unless at End of File)

        here = editor.charsets_find_column(charsets)

        _ = self.slip_ahead_one()

        # Slip ahead across more Chars of Word in Line

        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    break

                if not self.slip_ahead_one():

                    break

        # Slip ahead across Blanks, but not across Empty Lines, nor End of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_ahead_one():

                break

    def do_big_word_start_behind(self):  # Vim ⇧B, Vi Py ⌥←  # inverse of Vim ⇧W
        """Slip behind to first Char of Big Word"""

        self.word_start_behind_for_count(VI_BLANK_SET)

        # Vi Py ⌥← Option Left-Arrow works like Vi Py ⇧B
        # Vim ⌥← Quirk defaults to block Option Right-Arrow from working like Vim ⇧B

    def do_lil_word_start_behind(self):  # Vim B  # inverse of Vim W
        """Slip behind first Char of Lil Word"""

        self.word_start_behind_for_count(VI_BLANK_SET, VI_SYMBOLIC_SET)

        # TODO: add option for B E W to see '.' as part of the word with '_'

    def word_start_behind_for_count(self, *charsets):
        """Slip behind to first Char of Word"""

        editor = self.editor

        if not editor.skin.doing_done:
            self.check_vi_index(editor.spot_pin() < editor.spot_last_pin())

        self.word_start_behind_once(charsets)

        editor.continue_do_loop()

    def word_start_behind_once(self, charsets):
        """Slip behind to first Char of this else next Word"""

        editor = self.editor

        # Slip behind at least once (unless at Start of File)

        _ = self.slip_behind_one()

        # Slip behind across Blanks, but not across Empty Lines, nor Start of File

        while not editor.charsets_find_column(charsets):
            if not editor.count_columns_in_row():

                break

            if not self.slip_behind_one():

                break

        # Slip behind across Chars of Word, except stop at Start of Line

        here = editor.charsets_find_column(charsets)
        if here:
            while editor.charsets_find_column(charsets) == here:
                if not editor.column:

                    return

                behind = self.slip_behind_one()
                assert behind, (editor.column, editor.count_columns_in_row())

            ahead = self.slip_ahead_one()  # backtrack
            assert ahead, (editor.column, editor.count_columns_in_row())

    #
    # Search ahead inside the Row for a single Char
    #

    def do_slip_index_choice(self):  # Vim Fx
        """Find Char to right in Row, once or more"""

        choice = self.get_vi_arg2_chars()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

        # TODO: Vi Py vs Vim F, T, ⇧F, ⇧T Quirks
        # Vim F Esc Quirk means escaped without Bell
        # Vim F ⌃C Quirk means cancelled with Bell
        # Vim F ⌃Vx Quirk means literally go find a ⌃V char, not go find the X char

    def do_slip_index_minus_choice(self):  # Vim Tx
        """Find Char to Right in row, once or more, but then slip left one Column"""

        choice = self.get_vi_arg2_chars()

        self.slip_choice = choice
        self.slip_after = -1
        self.slip_redo = self.slip_index
        self.slip_undo = self.slip_rindex

        self.slip_redo()

    def slip_index(self):
        """Find Char to Right in row, once or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        last_column = editor.spot_last_column()
        line = editor.fetch_row_line()

        choice = self.slip_choice
        after = self.slip_after

        # Index each

        column = editor.column

        for _ in range(count):

            self.check_vi_index(column < last_column)
            column += 1

            try:
                right = line[column:].index(choice)
            except ValueError:
                exc_arg = "substring {!r} not found ahead".format(choice)

                raise ValueError(exc_arg) from None  # substring ... not found ahead

            column += right

        # Option to slip back one column

        if after:
            self.check_vi_index(column)
            column -= 1

        editor.column = column

    #
    # Search behind inside the Row for a single Char
    #

    def do_slip_rindex_choice(self):  # Vim ⇧Fx
        """Find Char to left in Row, once or more"""

        choice = self.get_vi_arg2_chars()

        self.slip_choice = choice
        self.slip_after = 0
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def do_slip_rindex_plus_choice(self):  # Vim ⇧Tx
        """Find Char to left in Row, once or more, but then slip right one Column"""

        choice = self.get_vi_arg2_chars()

        self.slip_choice = choice
        self.slip_after = +1
        self.slip_redo = self.slip_rindex
        self.slip_undo = self.slip_index

        self.slip_redo()

    def slip_rindex(self):
        """Find Char to left in Row, once or more"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        last_column = editor.spot_last_column()
        line = editor.fetch_row_line()

        choice = self.slip_choice
        after = self.slip_after

        # R-Index each

        column = editor.column

        for _ in range(count):

            self.check_vi_index(column)
            column -= 1

            try:
                column = line[: (column + 1)].rindex(choice)
            except ValueError:
                exc_arg = "substring {!r} not found behind".format(choice)

                raise ValueError(exc_arg) from None  # substring ... not found behind

        # Option to slip right one column

        if after:

            self.check_vi_index(column < last_column)
            column += 1

        editor.column = column

    #
    # Repeat search inside the Row for a single Char
    #

    def do_slip_redo(self):  # Vim ;
        """Repeat the last 'slip_index' or 'slip_rindex' once or more"""

        editor = self.editor

        if self.slip_choice is None:
            self.vi_print("Do you mean fx ;")  # ; Egg

            return

        after = self.slip_after
        if not after:

            self.slip_redo()

        else:

            row_last_column = editor.spot_last_column(row=editor.row)

            with_column = editor.column
            try:

                if after < 0:
                    assert editor.column < row_last_column
                    editor.column += 1
                elif after > 0:
                    assert editor.column
                    editor.column -= 1

                self.slip_redo()

                assert editor.column != with_column

            finally:
                editor.column = with_column

    def do_slip_undo(self):  # Vim ,
        """Undo the last 'slip_index' or 'slip_rindex' once or more"""

        editor = self.editor

        if self.slip_choice is None:
            self.vi_print("Do you mean Fx ,")  # , Egg

            return

        after = self.slip_after
        if not after:

            self.slip_undo()

        else:

            row_last_column = editor.spot_last_column(row=editor.row)

            with_column = editor.column
            try:

                if after < 0:
                    assert editor.column
                    editor.column -= 1
                elif after > 0:
                    assert editor.column < row_last_column
                    editor.column += 1

                self.slip_undo()

                assert editor.column != with_column

            finally:
                editor.column = with_column

    #
    # Map Keyboard Inputs to Code, for when feeling like Vi
    #

    def enter_do_vi(self):
        """Run before each Vi Func chosen by Chords"""

        # Default to stop remembering the last Seeking Column

        self.seeking_more = None  # break loop of Vi Column Seek

    def exit_do_vi(self):
        """Run after each Vi Func chosen by Chords"""

        # Remember the last Seeking Column across Funcs that ask for it

        if not self.seeking_more:
            self.seeking_column = None

    def format_vi_status(self, reply):
        """Format a Status Line of Row:Column, Nudge, and Message"""

        self.last_formatted_reply = TerminalReplyOut(reply)  # capture for Vim ⌃Z

        # Format parts, a la Vim ':set showcmd' etc

        pin_chars = "{},{}".format(1 + self.editor.row, 1 + self.editor.column)
        flags_chars = str(reply.flags) if reply.flags else ""
        nudge_chars = "" if (reply.nudge is None) else reply.nudge.to_chars()
        message_chars = str(reply.message) if reply.message else ""
        bell_chars = "?" if reply.bell else ""

        # Join parts

        replies = (pin_chars, flags_chars, nudge_chars, message_chars, bell_chars)
        vi_status = "  ".join(_ for _ in replies if _)

        return vi_status

    def place_vi_cursor(self):
        """Place the Cursor"""

        editor = self.editor

        row = editor.row - editor.top_row
        column = editor.column

        return TerminalPin(row, column=column)

    #
    # Variations on Switch Keyboards
    #

    def do_slip_beyond_last_take_inserts(self):  # Vim ⇧A of ⇧R ⇧A ⇧I ⇧O A I O
        """Take Input Chords after the Last Char of this Line"""

        editor = self.editor
        columns = editor.count_columns_in_row()

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert beyond Last Column

        if not columns:
            editor.column = 0
        else:
            editor.column = columns

        self.take_vi_inserts()

    def do_slip_dent_take_inserts(self):  # Vim ⇧I of ⇧R ⇧A ⇧I ⇧O A I O
        """Take Input Chords after the Dent of the Line"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert beyond Dent

        self.editor.slip_dent()
        self.take_vi_inserts()

    def do_slip_first_split_take_inserts(self):  # Vim ⇧O of ⇧R ⇧A ⇧I ⇧O A I O
        """Insert an empty Line before this Line, and take Input Chords into it"""

        editor = self.editor

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert an empty Line before this Line, but land in front of it

        editor.column = 0
        editor.insert_one_line()  # insert an empty Line before Cursor Line
        self.held_vi_file.touches += 1
        editor.row -= 1

        # Take Input Chords into the new empty Line

        self.take_vi_inserts()

    def do_slip_take_inserts(self):  # Vim A of ⇧R ⇧A ⇧I ⇧O A I O
        """Take Input Chords after the Char Beneath the Cursor"""

        editor = self.editor

        column = editor.column
        columns = editor.count_columns_in_row()

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert beyond this Char

        if columns:
            if column <= columns:
                editor.column = column + 1

        self.take_vi_inserts()

    def do_slip_last_split_take_inserts(self):  # Vim O of ⇧R ⇧A ⇧I ⇧O A I O
        """Insert an empty Line after this Line, and take Input Chords into it"""

        editor = self.editor
        ended_lines = editor.ended_lines

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert an empty Line after this Line, but land in front of it

        if ended_lines:
            editor.row += 1
        editor.column = 0

        editor.insert_one_line()  # insert an empty Line after Cursor Line
        self.held_vi_file.touches += 1

        editor.row -= 1

        # Take Input Chords into the new empty Line

        self.take_vi_inserts()

    def do_take_inserts(self):  # Vim I of of ⇧R ⇧A ⇧I ⇧O A I O
        """Take many keyboard Input Chords as meaning insert Chars, till Esc"""

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        # Insert before the Char beneath the Cursor

        self.take_vi_inserts()

    #
    # Switch Keyboards
    #

    def take_vi_inserts(self):
        """Take keyboard Input Chords to mean insert Chars, till Esc"""

        editor = self.editor
        skin = editor.skin
        keyboard = skin.keyboard

        self.vi_print("Press Esc to quit, else type chars to insert")
        skin.cursor_style = _INSERT_CURSOR_STYLE_

        chords_set = set(BASIC_LATIN_STDINS) | set([CR_STDIN])
        keyboard.intake_chords_set = chords_set

        keyboard.intake_func = self.do_insert_per_chord
        editor.intake_beyond = "inserting"  # as if many 'do_vi_self_insert_command'
        editor.intake_taken = False

    def do_take_replaces(self):  # Vim ⇧R of ⇧R ⇧A ⇧I ⇧O A I O
        """Take keyboard Input Chords to mean replace Chars, till Esc"""

        self.take_vi_replaces()

    def take_vi_replaces(self):
        """Take keyboard Input Chords to mean replace Chars, till Esc"""

        editor = self.editor
        skin = editor.skin
        keyboard = skin.keyboard

        self.check_vi_count()  # raise NotImplementedError: Repeat Count

        self.vi_print("Press Esc to quit, else type chars to write over")
        skin.cursor_style = _REPLACE_CURSOR_STYLE_

        chords_set = set(BASIC_LATIN_STDINS) | set([CR_STDIN])
        keyboard.intake_chords_set = chords_set

        keyboard.intake_func = self.do_replace_per_chord
        editor.intake_beyond = "replacing"  # as if 'C-u M-x overwrite-mode'
        editor.intake_taken = False

    def take_vi_views(self):
        """Stop taking keyboard Input Chords to mean replace/ insert Chars"""

        editor = self.editor
        skin = editor.skin
        keyboard = skin.keyboard

        if editor.intake_beyond:

            editor.intake_beyond = ""
            skin.cursor_style = _VIEW_CURSOR_STYLE_

            keyboard.intake_chords_set = set()
            keyboard.intake_func = None

            if editor.column:
                editor.column -= 1

    def do_vi_c0_control_si(self):
        """Define ⌃O during ⇧R ⇧A ⇧I ⇧O A I O, but not yet otherwise"""

        editor = self.editor
        if editor.intake_beyond:
            self.do_take_one_bypass()
        else:
            editor.do_raise_name_error()

    def do_vi_digit_argument(self):  # Vim ⌥0, ⌥1, ⌥2, ⌥3, ⌥4, ⌥5, ⌥6, ⌥7, ⌥8, ⌥9
        """Mostly work like 0, 1, 2, 3, 4, 5, 6, 7, 8, 9"""

        editor = self.editor
        skin = editor.skin

        arg1 = skin.arg1
        chord_ints_ahead = skin.chord_ints_ahead

        # FIXME: explain, and discuss re-entry into 'def do_take_one_bypass'  : -)

        self.do_take_one_bypass()

        # FIXME: explain

        str_digit = self.vi_get_arg0_digit()

        if arg1 is None:
            chars_ahead = str_digit
        else:
            chars_ahead = str(arg1) + str_digit

        chord_ints_ahead[::] = chord_ints_ahead + list(chars_ahead.encode())

    def do_take_one_bypass(self):  # Vim ⌃O during ⇧R ⇧A ⇧I ⇧O A I O
        """Pause taking keyboard Input Chords to mean replace/ insert Chars"""

        self.take_one_bypass()
        self.vi_print("Type one command")

    def take_one_bypass(self):
        """Take next keyboard Input Chords to mean replace/ insert Chars"""

        editor = self.editor

        column = editor.column
        row = editor.row
        skin = editor.skin

        keyboard = skin.keyboard

        #

        if not editor.intake_beyond:

            if keyboard.intake_bypass:
                keyboard.with_intake_bypass = ""  # TODO: make this less ugly

            return

        #

        keyboard.intake_bypass = editor.intake_beyond
        editor.intake_beyond = None

        #

        editor.intake_column = column

        row_max_column = editor.spot_max_column(row=row)
        if column > row_max_column:
            assert column == (row_max_column + 1), (row_max_column, column)

            editor.column -= 1

        #

        skin.cursor_style = _VIEW_CURSOR_STYLE_

        skin.doing_traceback = skin.traceback  # A⌃OZ⇧Q⌃O⇧Z⇧Q Egg

    def do_insert_per_chord(self):  # Vim Bypass View to Insert
        """Insert a copy of the Input Char, else insert a Line"""
        # Emacs Self-Insert-Command outside of 'overwrite-mode'

        chars = self.get_vi_arg0_chars()
        if chars == CR_CHAR:
            self.do_insert_one_line()
        else:
            self.do_insert_one_char()

        # TODO: calling for another 'self.do_...' can too easily spiral out of control

    def do_insert_one_line(self):  # Vim Return during Replace/ Insert
        """Insert one Line"""

        editor = self.editor
        editor.insert_one_line()
        self.held_vi_file.touches += 1
        self.vi_print("inserted line")

    def do_insert_one_char(self):  # Vim Literals of Replace past Last, or of Insert
        """Insert one Char"""

        editor = self.editor

        chars = self.get_vi_arg0_chars()
        if (len(chars) == 1) and (ord(chars) >= 0x80):

            editor.intake_taken = True

        editor.insert_some_chars(chars)  # insert as inserting itself

        self.held_vi_file.touches += 1
        self.vi_print("inserted char")

    def do_replace_per_choice(self):  # Vim Rx
        """Replace one Char with the Input Suffix Char, else insert a Line"""

        editor = self.editor

        column = editor.column
        columns = editor.count_columns_in_row()

        self.check_vi_index(editor.column < columns)

        choice = self.get_vi_arg2_chars()
        editor.replace_some_chars(chars=choice)
        editor.column = column

        self.held_vi_file.touches += 1
        self.vi_print("{} replaced".format(editor.format_touch_count()))

        editor.continue_do_loop()

        # Vi Py defines ⌃V inside ⇧R ⇧A ⇧I ⇧O Rx A I O Fx Tx ⇧Fx ⇧Tx  # TODO: someday
        # Vi Py defines ⌃V inside ⇧R ⇧A ⇧I ⇧O A I O today
        # Vim Quirk defines ⌃V inside Rx A I O X ⇧R ⇧A ⇧I ⇧O, not inside F T ⇧F ⇧T 123

    def do_replace_per_chord(self):  # Vim Bypass View to Replace
        """Replace one Char with the Input Chars"""
        # Emacs Self-Insert-Command inside of 'overwrite-mode'

        chars = self.get_vi_arg0_chars()
        if chars == CR_CHAR:
            self.do_insert_one_line()
        else:
            self.do_replace_one_char()

    def do_replace_one_char(self):  # Vim Literals of Replace
        """Replace one Char"""

        editor = self.editor
        column = editor.column
        columns = editor.count_columns_in_row()

        chars = self.get_vi_arg0_chars()
        if (len(chars) == 1) and (ord(chars) >= 0x80):

            editor.intake_taken = True

        editor.replace_some_chars(chars)
        self.held_vi_file.touches += 1

        if column < columns:
            self.vi_print("replaced char")
        else:
            self.vi_print("inserted char")

    #
    # Variations on Cut Char and Cut Lines
    #

    def do_cut_behind(self):  # Vim ⇧X
        """Cut as many as the count of Chars behind"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        left = min(editor.column, count)
        editor.column -= left  # a la Vim H Left

        touches = editor.delete_some_chars(count=left)
        self.held_vi_file.touches += touches

    def do_cut_ahead_take_inserts(self):  # Vim S
        """Cut as many as the count of Chars ahead, and then take Chords as Inserts"""

        count = self.get_vi_arg1_int()

        self.cut_some_vi_chars(count)

        self.take_vi_inserts()

    def do_cut_ahead(self):  # Vim X
        """Cut as many as the count of Chars ahead, but keep the Cursor in Bounds"""

        count = self.get_vi_arg1_int()

        self.cut_some_vi_chars(count)
        self.slip_back_into_vi_line()

    def slip_back_into_vi_line(self):
        """Slip back to the Max Column if now just beyond it"""

        editor = self.editor
        column = editor.column
        max_column = editor.spot_max_column()
        columns = editor.count_columns_in_row()

        if column == columns == (max_column + 1):
            editor.column = columns - 1

    def cut_some_vi_chars(self, count):
        """Cut as many as the count of Chars ahead"""

        editor = self.editor

        columns = editor.count_columns_in_row()  # a la Vim L Right
        right = min(columns - editor.column, count)

        touches = editor.delete_some_chars(count=right)
        self.held_vi_file.touches += touches

    def do_slip_last_join_right(self):  # Vim ⇧J
        """Join 1 Line or N - 1 Lines to this Line, as if dented by single Spaces"""

        count = self.get_vi_arg1_int()
        count_below = (count - 1) if (count > 1) else 1

        editor = self.editor
        row = editor.row
        last_row = editor.spot_last_row()
        max_column = editor.spot_max_column()

        if row >= last_row:

            editor.column = max_column

        else:

            joinings = min(last_row - row, count_below)
            touches = editor.join_some_lines(joinings)
            self.held_vi_file.touches += touches

        self.after_did = self.do_slip_last_join_right

        # Vim ⇧J Quirk rings a bell at End-of-File, Emacs doesn't, Vi Py doesn't

    def do_chop_take_inserts(self):  # Vim ⇧C
        """Cut N - 1 Lines below & Chars to right in Line, and take Chords as Inserts"""

        count = self.get_vi_arg1_int()

        self.chop_some_vi_lines(count)

        self.take_vi_inserts()

    def do_chop(self):  # Vim ⇧D  # TODO: ugly to doc
        """Cut N - 1 Lines below & Chars to right in Line, and land Cursor in Line"""
        # except if N > 1 and at or left of Dent, then delete N Lines and Slip to Dent

        count = self.get_vi_arg1_int()

        editor = self.editor

        column = editor.column
        row = editor.row

        columns = editor.count_columns_in_row()
        last_row = editor.spot_last_row()
        line = editor.fetch_row_line()

        # If N > 1 and at or left of Dent, then delete N Lines and Slip to Dent

        len_dent = len(line) - len(line.lstrip())
        if count > 1:
            if column <= len_dent:

                self.check_vi_index(row < last_row)
                self.chop_down(count)

                return

        # Cut N - 1 Lines below & Chars to right in Line, and land Cursor in Line

        self.check_vi_index(columns)  # Vim ⇧D Quirk doesn't beep when failing to delete

        self.chop_some_vi_lines(count)
        self.slip_back_into_vi_line()

    def do_chop_down(self):  # Vim D D
        """Delete N Lines and Slip to Dent"""

        count = self.get_vi_arg1_int()

        self.chop_down(count)

    def chop_down(self, count):
        "Delete at least 1 but no more than N Lines and Slip to Dent"

        editor = self.editor

        row = editor.row
        rows = editor.count_rows_in_file()

        down = min(rows - row, count)

        touches = editor.delete_some_lines(count=down)
        self.held_vi_file.touches += touches

        editor.slip_dent()

    def do_slip_first_chop_take_inserts(self):  # Vim ⇧S, Vim C C
        """Cut N - 1 Lines below & all Chars of this Line, and take Chords as Inserts"""

        count = self.get_vi_arg1_int()

        editor = self.editor

        editor.column = 0
        self.chop_some_vi_lines(count)

        self.take_vi_inserts()

    def chop_some_vi_lines(self, count):
        """Cut N - 1 Lines below & Chars to right in Line"""

        editor = self.editor

        if count > 1:
            self.delete_vi_lines_below(count=(count - 1))

        row = editor.row
        rows = editor.count_rows_in_file()

        if row < rows:

            columns = editor.count_columns_in_row(row=editor.row)
            touches = editor.delete_some_chars(count=columns)
            self.held_vi_file.touches += touches

    def delete_vi_lines_below(self, count):
        """Cut N Lines below"""

        editor = self.editor

        row = editor.row
        last_row = editor.spot_last_row()

        self.check_vi_index(row < last_row)
        down = min(last_row - row, count)

        editor.row += 1
        touches = editor.delete_some_lines(count=down)
        self.held_vi_file.touches += touches

        editor.row = row


class TerminalKeyboard:
    """Map Keyboard Inputs to Code"""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self):

        self.format_status_func = lambda reply: None
        self.place_cursor_func = lambda: None

        self.with_intake_bypass = ""
        self.intake_bypass = ""
        self.intake_chords_set = set()
        self.intake_func = None
        self.intake_ish = False

        self.do_prefix_chord_func = lambda chord: False
        self.eval_prefix_func = lambda prefix: None
        self.uneval_prefix_func = lambda prefix: prefix

        self.corrections_by_chords = dict()
        self.func_by_chords = dict()
        self.suffixes_by_chords = dict()

        self.enter_do_func = lambda: None
        self.exit_do_func = lambda: None

    def _init_corrector(self, chords, corrections):
        """Map one sequence of keyboard Input Chords to another"""

        corrections_by_chords = self.corrections_by_chords

        self._init_func(chords, func=None)
        corrections_by_chords[chords] = corrections

    def _init_suffix_func(self, chords, func):
        """Map a sequence of keyboard Input Chords that needs 1 Suffix Chord"""

        self._init_func(chords, func=func, suffixes=1)

    def _init_func(self, chords, func, suffixes=None):
        """Map a sequence of keyboard Input Chords"""

        funcs = self.func_by_chords
        suffixes_by_chords = self.suffixes_by_chords

        # Ask for more Chords while holding some, but not all, of these Chords

        for some in range(1, len(chords)):
            some_chords = chords[:some]

            if some_chords not in funcs.keys():
                funcs[some_chords] = None
            else:
                some_func = funcs[some_chords]
                assert some_func is None, (some_chords, chords, some_func)

        # Call this Func after collecting all these Chords

        funcs[chords] = func  # may be init, may be mutate

        # Except first ask for 1 Suffix Chord, if wanted

        if suffixes:
            assert chords not in suffixes_by_chords, chords
            suffixes_by_chords[chords] = suffixes

    def choose_intake_chords_set(self):
        """Choose the Chords to route into Intake Chords Func, else an empty Set"""

        chords_set = set()
        if not self.intake_bypass:
            chords_set = self.intake_chords_set

        return chords_set

    def init_unichars_func(self, unichars, optchords):
        """Let people type the From Chars in place of the To Chars"""

        unichords = unichars.encode()

        funcs = self.func_by_chords
        suffixes_by_chords = self.suffixes_by_chords

        optfunc = funcs[optchords]
        if optchords in suffixes_by_chords.keys():
            self._init_suffix_func(unichords, func=optfunc)
        else:
            self._init_func(unichords, func=optfunc)

    def to_optchords(self, optchars):
        """Pick out the Keyboard Input Chords of a Key shifted by the Option Key"""
        # pylint: disable=no-self-use

        if optchars.startswith("⌥"):

            optchords = b"\x1B"  # ESC, ⌃[, 27
            assert optchars[1] == optchars[1].upper()
            optchords += optchars[1].lower().encode()

            opttail = optchars[2:]

        elif optchars.startswith("⇧⌥:"):

            optchords = b":" + optchars[len("⇧⌥:") :].replace("⇧", "").encode()

            return optchords  # TODO: make this less ugly

        else:
            assert optchars.startswith("⇧⌥")

            optchords = b"\x1B"  # ESC, ⌃[, 27
            assert optchars[2] == optchars[2].upper()
            optchords += optchars[2].encode()

            opttail = optchars[3:]

        if opttail:
            if (len(opttail) == 1) and (opttail in BASIC_LATIN_CHARS_SET):
                optchords += opttail.encode().lower()  # Em Py ⌥GG, Vi Py ⌥EE, etc
            elif opttail == "Tab":
                optchords += b"\x09"  # TAB, ⌃I, 9 \t
            elif (len(opttail) == 2) and (opttail[-1] in string.ascii_uppercase):
                if opttail[0] == "⌥":  # Em Py ⌥G⌥G, Vi Py ⌥E⌥E, etc
                    optchords += b"\x1B" + opttail[-1].encode().lower()  # ESC, ⌃[, 27
                else:
                    assert opttail[0] == "⇧"
                    optchords += opttail[-1].encode()
            elif (len(opttail) == 3) and (opttail[-1] in string.ascii_uppercase):
                assert opttail[:2] == "⇧⌥"
                assert opttail[:2] == "⇧⌥", repr(opttail)  # Vi Py ⇧⌥E⇧⌥E, etc
                optchords += b"\x1B" + opttail[-1].encode()  # ESC, ⌃[, 27
            else:
                assert not opttail, repr(opttail)

            # TODO: loosen up this logic to accept more additions before they arrive

        return optchords


class ViPyNameError(NameError):
    """Signal trouble like a NameError but mention the Vi Py keymap"""


class TerminalKeyboardVi(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Vi"""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, vi):
        super().__init__()

        self.vi = vi
        self.editor = vi.editor

        self.format_status_func = vi.format_vi_status
        self.place_cursor_func = vi.place_vi_cursor

        self.do_prefix_chord_func = vi.do_vi_prefix_chord
        self.eval_prefix_func = vi.eval_vi_prefix

        self._init_by_vi_chords_()

        self.enter_do_func = vi.enter_do_vi
        self.exit_do_func = vi.exit_do_vi

    def _init_by_vi_chords_(self):
        # pylint: disable=too-many-statements

        editor = self.editor
        funcs = self.func_by_chords
        vi = self.vi

        # Define the C0_CONTROL_STDINS

        # funcs[b"\x00"] = vi.do_c0_control_nul  # NUL, ⌃@, 0
        # funcs[b"\x01"] = vi.do_c0_control_soh  # SOH, ⌃A, 1
        funcs[b"\x02"] = vi.do_scroll_behind_much  # STX, ⌃B, 2
        funcs[b"\x03"] = vi.do_vi_c0_control_etx  # ETX, ⌃C, 3
        # funcs[b"\x04"] = vi.do_scroll_ahead_some  # EOT, ⌃D, 4
        funcs[b"\x05"] = vi.do_scroll_ahead_one  # ENQ, ⌃E, 5
        funcs[b"\x06"] = vi.do_scroll_ahead_much  # ACK, ⌃F, 6
        funcs[b"\x07"] = vi.do_say_more  # BEL, ⌃G, 7 \a
        funcs[b"\x08"] = vi.do_slip_behind  # BS, ⌃H, 8 \b
        # funcs[b"\x09"] = vi.do_c0_control_tab  # TAB, ⌃I, 9 \t
        funcs[b"\x0A"] = vi.do_step_down_seek  # LF, ⌃J, 10 \n
        # funcs[b"\x0B"] = vi.do_c0_control_vt  # VT, ⌃K, 11 \v
        funcs[b"\x0C"] = editor.do_redraw  # FF, ⌃L, 12 \f
        funcs[b"\x0D"] = vi.do_step_down_dent  # CR, ⌃M, 13 \r
        funcs[b"\x0E"] = vi.do_step_down_seek  # SO, ⌃N, 14
        funcs[b"\x0F"] = vi.do_vi_c0_control_si  # SI, ⌃O, 15
        funcs[b"\x10"] = vi.do_step_up_seek  # DLE, ⌃P, 16
        # funcs[b"\x11"] = vi.do_c0_control_dc1  # DC1, XON, ⌃Q, 17
        # funcs[b"\x12"] = vi.do_c0_control_dc2  # DC2, ⌃R, 18
        # funcs[b"\x13"] = vi.do_c0_control_dc3  # DC3, XOFF, ⌃S, 19
        # funcs[b"\x14"] = vi.do_c0_control_dc4  # DC4, ⌃T, 20
        # funcs[b"\x15"] = vi.do_scroll_behind_some  # NAK, ⌃U, 21
        funcs[b"\x16"] = vi.do_vi_c0_control_syn  # SYN, ⌃V, 22
        # funcs[b"\x17"] = vi.do_c0_control_etb  # ETB, ⌃W, 23
        # funcs[b"\x18"] = vi.do_c0_control_can  # CAN, ⌃X , 24
        funcs[b"\x19"] = vi.do_scroll_behind_one  # EM, ⌃Y, 25
        funcs[b"\x1A"] = vi.do_vi_suspend_frame  # SUB, ⌃Z, 26

        funcs[b"\x1B"] = vi.do_vi_c0_control_esc  # ESC, ⌃[, 27

        funcs[b"\x1B[A"] = vi.do_step_up_seek  # ↑ Up-Arrow
        funcs[b"\x1B[B"] = vi.do_step_down_seek  # ↓ Down-Arrow
        funcs[b"\x1B[C"] = vi.do_slip_right  # → Right-Arrow
        funcs[b"\x1B[D"] = vi.do_slip_left  # ← Left-Arrow

        funcs[b"\x1Bb"] = vi.do_big_word_start_behind  # ⌥← Option Left-Arrow, ⌥B
        funcs[b"\x1Bf"] = vi.do_big_word_start_ahead  # ⌥→ Option Right-Arrow, ⌥F

        # funcs[b"\x1C"] = vi.do_eval_vi_line   # FS, ⌃\, 28
        # funcs[b"\x1D"] = vi.do_c0_control_gs  # GS, ⌃], 29
        # funcs[b"\x1E"] = vi.do_c0_control_rs  # RS, ⌃^, 30
        # funcs[b"\x1F"] = vi.do_c0_control_us  # US, ⌃_, 31

        funcs[b"\x7F"] = vi.do_slip_behind  # DEL, ⌃?, 127

        # Define the BASIC_LATIN_STDINS

        funcs[b" "] = vi.do_slip_ahead
        # funcs[b"!"] = vi.do_pipe
        # funcs[b'"'] = vi.do_arg
        funcs[b"#"] = vi.do_find_behind_vi_this
        funcs[b"$"] = vi.do_slip_max_seek
        # funcs[b"%"]  # TODO: leap to match
        # funcs[b"&"]  # TODO: & and && for repeating substitution
        # funcs[b"'"]  # TODO: leap to pin
        # funcs[b"("]  # TODO: sentence behind
        # funcs[b")"]  # TODO: sentence ahead
        funcs[b"*"] = vi.do_find_ahead_vi_this
        funcs[b"+"] = vi.do_step_down_dent
        funcs[b","] = vi.do_slip_undo
        funcs[b"-"] = vi.do_step_up_dent
        funcs[b"."] = vi.do_replay_cut
        funcs[b"/"] = vi.do_find_ahead_vi_line

        funcs[b"0"] = vi.do_slip_first
        funcs[b"1"] = vi.do_vi_digit_argument
        funcs[b"2"] = vi.do_vi_digit_argument
        funcs[b"3"] = vi.do_vi_digit_argument
        funcs[b"4"] = vi.do_vi_digit_argument
        funcs[b"5"] = vi.do_vi_digit_argument
        funcs[b"6"] = vi.do_vi_digit_argument
        funcs[b"7"] = vi.do_vi_digit_argument
        funcs[b"8"] = vi.do_vi_digit_argument
        funcs[b"9"] = vi.do_vi_digit_argument

        self._init_corrector(b":/", corrections=b"/")
        self._init_corrector(b":?", corrections=b"?")
        # FIXME: Solve Vi Py ⌥⇧:/ ⌥⇧:?

        # self._init_func(b":em\r", func=em.do_resume_em)
        # self._init_func(b":g?", func=vi.do_find_leading_vi_lines)
        self._init_func(b":g/", func=vi.do_find_trailing_vi_lines)
        self._init_func(b":n!\r", func=vi.do_next_vi_file)
        self._init_func(b":n\r", func=vi.do_might_next_vi_file)
        self._init_func(b":q!\r", func=vi.do_quit_vi)
        self._init_func(b":q\r", func=vi.do_might_quit_vi)
        self._init_func(b":vi\r", func=vi.do_resume_vi)
        self._init_func(b":w!\r", func=vi.do_vi_save_buffer)
        self._init_func(b":w\r", func=vi.do_might_vi_save_buffer)
        self._init_func(b":wn!\r", func=vi.do_flush_next_vi)
        self._init_func(b":wn\r", func=vi.do_might_flush_next_vi)
        self._init_func(b":wq!\r", func=vi.do_flush_quit_vi)
        self._init_func(b":wq\r", func=vi.do_might_flush_quit_vi)
        # TODO: think deeper into Vim ⇧:

        funcs[b";"] = vi.do_slip_redo
        # funcs[b"<"]  # TODO: dedent
        # funcs[b"="]  # TODO: dent after
        # funcs[b">"]  # TODO: indent
        funcs[b"?"] = vi.do_find_behind_vi_line
        # self._init_suffix_func(b"@", func=vi.do_replay_from_choice)

        funcs[b"A"] = vi.do_slip_beyond_last_take_inserts
        funcs[b"B"] = vi.do_big_word_start_behind
        funcs[b"C"] = vi.do_chop_take_inserts
        funcs[b"D"] = vi.do_chop
        funcs[b"E"] = vi.do_big_word_end_ahead

        self._init_suffix_func(b"F", func=vi.do_slip_rindex_choice)

        funcs[b"G"] = vi.do_step_for_count
        funcs[b"H"] = vi.do_step_max_high
        funcs[b"I"] = vi.do_slip_dent_take_inserts
        funcs[b"J"] = vi.do_slip_last_join_right
        # funcs[b"K"] = vi.do_lookup
        funcs[b"L"] = vi.do_step_max_low
        funcs[b"M"] = vi.do_step_to_middle
        funcs[b"N"] = vi.do_vi_find_earlier
        funcs[b"O"] = vi.do_slip_first_split_take_inserts
        # funcs[b"P"] = vi.do_paste_behind

        self._init_func(b"Qvi\r", func=vi.do_continue_vi)
        self._init_func(b"QZ", func=vi.do_talk_of_shift_z_shift_q)
        self._init_func(b"Qz", func=vi.do_talk_of_shift_z_shift_q)
        # TODO: think deeper into Vim Q

        funcs[b"R"] = vi.do_take_replaces
        funcs[b"S"] = vi.do_slip_first_chop_take_inserts

        self._init_suffix_func(b"T", func=vi.do_slip_rindex_plus_choice)

        # funcs[b"U"] = vi.do_row_undo
        # funcs[b"V"] = vi.do_gloss_rows
        funcs[b"W"] = vi.do_big_word_start_ahead
        funcs[b"X"] = vi.do_cut_behind
        # funcs[b"Y"] = vi.do_copy_row

        self._init_func(b"ZQ", func=vi.do_quit_vi)
        self._init_func(b"ZZ", func=vi.do_flush_quit_vi)
        self._init_func(b"Zq", func=vi.do_talk_of_shift_z_shift_q)
        self._init_func(b"Zz", func=vi.do_talk_of_shift_z_shift_z)

        # funcs[b"["]  # TODO: b"["

        self._init_func(b"\\F", func=editor.do_set_invregex)
        self._init_func(b"\\i", func=editor.do_set_invignorecase)
        self._init_func(b"\\n", func=editor.do_set_invnumber)
        # TODO: stop commandeering the personal \Esc \⇧F \I \N Chord Sequences

        # funcs[b"]"]  # TODO: b"]"
        funcs[b"^"] = vi.do_slip_dent
        funcs[b"_"] = vi.do_step_down_minus_dent
        # funcs[b"`"]  # TODO: close to b"'"

        funcs[b"a"] = vi.do_slip_take_inserts
        funcs[b"b"] = vi.do_lil_word_start_behind
        funcs[b"c"] = vi.do_cut_back_after_take_inserts
        funcs[b"d"] = vi.do_cut_back_after

        funcs[b"e"] = vi.do_lil_word_end_ahead

        self._init_suffix_func(b"f", func=vi.do_slip_index_choice)

        self._init_corrector(b"g/", corrections=b":g/")
        self._init_corrector(b"g?", corrections=b":g?")
        # TODO: stop commandeering the personal g/ g? Chord Sequences
        # FIXME: Solve Vi Py ⌥⇧:g/ ⌥⇧:g⇧?

        # funcs[b"g"]
        funcs[b"h"] = vi.do_slip_left
        funcs[b"i"] = vi.do_take_inserts
        funcs[b"j"] = vi.do_step_down_seek
        funcs[b"k"] = vi.do_step_up_seek
        funcs[b"l"] = vi.do_slip_right

        # self._init_suffix_func(b"m", func=vi.do_drop_pin)

        funcs[b"n"] = vi.do_vi_find_later
        funcs[b"o"] = vi.do_slip_last_split_take_inserts

        # funcs[b"p"] = vi.do_paste_ahead

        self._init_suffix_func(b"q", func=vi.do_record_over_choice)
        self._init_suffix_func(b"r", func=vi.do_replace_per_choice)

        funcs[b"s"] = vi.do_cut_ahead_take_inserts

        self._init_suffix_func(b"t", func=vi.do_slip_index_minus_choice)

        # funcs[b"u"] = vi.do_undo
        # funcs[b"v"] = vi.do_gloss_chars
        funcs[b"w"] = vi.do_lil_word_start_ahead
        funcs[b"x"] = vi.do_cut_ahead
        # funcs[b"y"] = vi.do_copy_after

        self._init_func(b"z.", func=vi.do_scroll_till_middle)
        self._init_func(b"zb", func=vi.do_scroll_till_bottom)
        self._init_func(b"zq", func=vi.do_talk_of_shift_z_shift_q)
        self._init_func(b"zt", func=vi.do_scroll_till_top)

        funcs[b"{"] = vi.do_paragraph_behind
        funcs[b"|"] = vi.do_slip
        funcs[b"}"] = vi.do_paragraph_ahead
        # funcs[b"~"] = vi.do_flip_char_case

        # Define Vi Py Esc Keyboard Input Chords, other than ⌥E ⌥I ⌥N ⌥U,
        # found at Keyboard > Use Option as Meta Key = No
        # inside macOS Terminal > Preferences > Profiles

        vi_optchars_list = r"""
            ⇧⌥Z⇧⌥Q ⇧⌥Z⇧⌥Z ⇧⌥QVI⌃M
            ⇧⌥:g/ ⇧⌥:n⇧!⌃M ⇧⌥:n⌃M ⇧⌥:q⇧!⌃M ⇧⌥:q⌃M ⇧⌥:vi⌃M
            ⇧⌥:w⇧!⌃M ⇧⌥:w⌃M ⇧⌥:wn⇧!⌃M ⇧⌥:wn⌃M ⇧⌥:wq⇧!⌃M ⇧⌥:wq⌃M
            ⇧⌥$ ⇧⌥^ ⌥0 ⌥F ⇧⌥F ⌥T ⇧⌥T ⌥; ⌥, ⇧⌥| ⌥H ⌥L
            ⌥W ⌥EE ⌥B ⇧⌥W ⇧⌥E⇧⌥E ⇧⌥B ⇧⌥} ⇧⌥{
            ⇧⌥G ⇧⌥L ⇧⌥M ⇧⌥H ⇧⌥+ ⇧⌥_ ⌥- ⌥J ⌥K
            ⌥1 ⌥2 ⌥3 ⌥4 ⌥5 ⌥6 ⌥7 ⌥8 ⌥9
            ⌥ZT ⌥ZB ⌥Z.
            ⌥\I ⌥\N ⌥\⇧F
            ⌥/ ⇧⌥? ⇧⌥* ⇧⌥# ⌥NN ⇧⌥N⇧⌥N
            ⌥R ⌥A ⌥II ⌥O ⇧⌥R ⇧⌥A ⇧⌥I⇧⌥I ⇧⌥O
            ⌥X ⇧⌥X ⇧⌥D ⇧⌥J ⌥S ⇧⌥S ⇧⌥C ⌥D ⌥C
        """.split()

        # ⌥→ ⌥← not solved here

        for optchars in vi_optchars_list:

            kind0 = optchars.startswith("⌥")
            kind1 = optchars.startswith("⇧⌥"), repr(optchars)
            kind2 = optchars == "⇧⌥QVI⌃M"

            assert kind0 or kind1 or kind2

        for optchars in vi_optchars_list:
            unichars = TerminalNudgeIn.UNICHARS_BY_OPTCHARS[optchars]

            if optchars == "⇧⌥QVI⌃M":

                alt_optchords = b"Qvi\r"

            elif optchars.startswith("⇧⌥:"):

                alt_optchars = optchars
                alt_optchars = alt_optchars[len("⇧⌥") :]  # keep only the ":"
                alt_optchars = alt_optchars.replace("⇧", "")
                alt_optchars = alt_optchars.replace("⌃M", "\r")

                alt_optchords = alt_optchars.encode()

            else:

                optchords = self.to_optchords(optchars)
                assert optchords[:1] == b"\x1B", repr(optchords)  # ESC, ⌃[, 27
                alt_optchords = optchords.replace(b"\x1B", b"")
                if alt_optchords in (b"ee", b"EE", b"ii", b"II", b"nn", b"NN"):
                    alt_optchords = alt_optchords[-1:]  # TODO:  b"uu", b"UU"

            self.init_unichars_func(unichars, optchords=alt_optchords)

            # print(repr(unichars), repr(alt_optchords), funcs[alt_optchords])


#
# Feed Keyboard into Bottom Lines of the Screen, a la the Ex inside Vim
#


class TerminalEx:
    """Feed Keyboard into Line at Bottom of Screen of Scrolling Rows, a la Ex"""

    def __init__(self, editor, vi_reply):

        self.editor = editor
        self.vi_reply = vi_reply

        self.ex_line = None

    def read_ex_line(self):
        """Take an Input Line from beneath the Scrolling Rows"""

        editor = self.editor

        self.ex_line = ""

        keyboard = TerminalKeyboardEx(ex=self)
        try:
            editor.run_skin_with_keyboard(keyboard)  # TerminalKeyboardEx
            assert False  # unreached
        except SystemExit:
            line = self.ex_line

            editor.skin.doing_traceback = editor.skin.traceback

            return line

    def flush_ex_status(self):
        """Paint Status and Cursor now"""

        editor = self.editor

        keyboard = editor.skin.keyboard
        reply = editor.skin.reply

        editor.flush_editor(keyboard, reply=reply)  # for 'flush_ex_status'

    def format_ex_status(self, reply):
        """Keep up the Vi Reply while working the Ex Keyboard, but add the Input Line"""

        _ = reply

        ex_line = self.ex_line
        vi_reply = self.vi_reply

        ex_reply = vi_reply + ex_line

        return ex_reply

    def place_ex_cursor(self):
        """Place the Cursor"""

        editor = self.editor
        painter = editor.painter

        ex_reply = self.format_ex_status(editor.skin.reply)

        row = painter.status_row
        column = len(ex_reply)

        return TerminalPin(row, column=column)

    def do_clear_chars(self):  # Ex ⌃U in Vim
        """Undo all the Append Chars, if any Not undone already"""

        self.ex_line = ""

    def do_append_char(self):
        """Append the Chords to the Input Line"""

        editor = self.editor
        chars = editor.get_arg0_chars()

        self.ex_line += chars

    def do_undo_append_char(self):
        """Undo the last Append Char, else Quit Ex"""

        ex_line = self.ex_line
        if ex_line:
            self.ex_line = ex_line[:-1]
        else:
            self.ex_line = None

            sys.exit()

    def do_quit_ex(self):  # Ex ⌃C in Vim
        """Lose all input and quit Ex"""

        self.ex_line = None

        sys.exit()

    def do_copy_down(self):  # Ex ⌃P, ↑ Up-Arrow, in Vim
        """Recall last input line"""

        editor = self.editor
        ex_line = self.ex_line

        editor_finding_line = editor.finding_line
        if ex_line is not None:
            if editor_finding_line is not None:
                if editor_finding_line.startswith(ex_line):

                    self.ex_line = editor_finding_line

                    return

        raise ValueError("substring not found")


class TerminalKeyboardEx(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Ex"""

    # pylint: disable=too-few-public-methods

    def __init__(self, ex):
        super().__init__()

        self.ex = ex
        self.editor = ex.editor

        self.format_status_func = ex.format_ex_status
        self.place_cursor_func = ex.place_ex_cursor

        self._init_by_ex_chords_()

    def _init_by_ex_chords_(self):

        ex = self.ex
        funcs = self.func_by_chords
        editor = self.editor

        # Define the C0_CONTROL_STDINS

        for chords in C0_CONTROL_STDINS:
            funcs[chords] = editor.do_raise_name_error

        # Mutate the C0_CONTROL_STDINS definitions

        funcs[b"\x03"] = ex.do_quit_ex  # ETX, ⌃C, 3
        funcs[b"\x08"] = ex.do_undo_append_char  # BS, ⌃H, 8 \b
        funcs[b"\x0D"] = editor.do_sys_exit  # CR, ⌃M, 13 \r
        funcs[b"\x10"] = ex.do_copy_down  # DLE, ⌃P, 16
        funcs[b"\x1A"] = editor.do_suspend_frame  # SUB, ⌃Z, 26
        funcs[b"\x15"] = ex.do_clear_chars  # NAK, ⌃U, 21

        funcs[b"\x1B[A"] = ex.do_copy_down  # ↑ Up-Arrow

        funcs[b"\x7F"] = ex.do_undo_append_char  # DEL, ⌃?, 127

        # Define the BASIC_LATIN_STDINS

        for chords in BASIC_LATIN_STDINS:
            funcs[chords] = ex.do_append_char

        # TODO: input Search Keys containing more than BASIC_LATIN_STDINS and #
        # TODO: Define Chords beyond the C0_CONTROL_STDINS and BASIC_LATIN_STDINS
        # TODO: such as U00A3 PoundSign

        # TODO: define Esc to replace live Regex punctuation with calmer r"."


#
# Carry an Em Py for Emacs inside this Vi Py for Vim
#


class TerminalEm:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars, a la Emacs"""

    # pylint: disable=too-many-public-methods

    def __init__(self, files, script, evals):

        self.main_traceback = None

        vi = TerminalVi(files, script=script, evals=evals)
        self.vi = vi

    def run_inside_terminal(self):
        """Enter Terminal Driver, then run Emacs Keyboard, then exit Terminal Driver"""

        vi = self.vi
        try:
            vi.run_inside_terminal(em=self)
        finally:
            self.main_traceback = vi.main_traceback  # ⌃X⌃G⌃X⌃C Egg

    def take_em_inserts(self):
        """Take keyboard Input Chords to mean insert Chars"""

        editor = self.vi.editor
        editor.intake_beyond = "inserting"  # as if many 'do_em_self_insert_command'

    def do_em_prefix_chord(self, chord):  # TODO  # noqa C901 too complex
        """Take ⌃U { ⌃U } [ "-" ] { "0123456789" } [ ⌃U ] as a Prefix to more Chords"""
        # Emacs ⌃U Universal-Argument

        editor = self.vi.editor

        prefix = editor.skin.nudge.prefix
        chords = editor.skin.nudge.chords

        keyboard = editor.skin.keyboard
        intake_chords_set = keyboard.choose_intake_chords_set()

        prefix_plus = chord if (prefix is None) else (prefix + chord)
        prefix_opened = b"\x15" + prefix_plus.lstrip(b"\x15")

        # Don't take more Prefix Chords after the first of the Chords to Call

        if chords:

            return False

        assert b"\x15" not in intake_chords_set

        # Start with one or more ⌃U, close with ⌃U, or start over with next ⌃U

        if chord == b"\x15":

            if not prefix:
                editor.skin.nudge.prefix = prefix_plus
            elif set(prefix) == set(b"\x15"):
                editor.skin.nudge.prefix = prefix_plus
            elif not prefix.endswith(b"\x15"):
                editor.skin.nudge.prefix = prefix_plus
            else:
                editor.skin.nudge.prefix = chord

            return True

        # Take no more Chords after closing ⌃U (except for a next ⌃U above)

        if prefix:

            opening = set(prefix) == set(b"\x15")
            closed = prefix.endswith(b"\x15") or (prefix.lstrip(b"\x15") == b"0")

            if opening or not closed:

                if (chord == b"-") and opening:
                    editor.skin.nudge.prefix = prefix_opened

                    return True

                if (chord == b"0") and not prefix.endswith(b"-"):
                    editor.skin.nudge.prefix = prefix_opened

                    return True

                if chord in b"123456789":
                    editor.skin.nudge.prefix = prefix_opened

                    return True

        # Else declare Prefix complete

        return False

        # Em Py takes ⌃U - 0 and ⌃U 0 0..9 as complete
        # Emacs quirkily disappears 0's after ⌃U if after -, after 0, or before 1..9

    def eval_em_prefix(self, prefix):
        """Take the Chords of a Signed Int Prefix before the Called Chords"""
        # pylint: disable=no-self-use

        evalled = None
        if prefix is not None:  # then drop the ⌃U's and eval the Digits

            prefix_digits = prefix.decode()
            prefix_digits = "".join(_ for _ in prefix_digits if _ in "-0123456789")

            if prefix_digits == "-":  # except take "-" alone as -1
                prefix_digits = "-1"
            elif prefix and not prefix_digits:  # and take ⌃U's alone as powers of 4
                prefix_digits = str(4 ** len(prefix)).encode()

            evalled = int(prefix_digits) if prefix_digits else None

        return evalled  # may be negative, zero, or positive int

        # Emacs quirkily takes ⌃U's alone as powers of 4, Em Py does too

    def uneval_em_prefix(self, prefix):
        """Rewrite history to make the Prefix Chords more explicit"""

        _ = prefix

        nudge = self.vi.editor.skin.nudge

        lead_chord = nudge.chords[0] if nudge.chords else b"\x07"  # TODO: ugly b"\x07"

        # Echo no Prefix as no Prefix

        arg1 = self.vi.editor.skin.arg1
        if arg1 is None:

            return None

        # Echo Decimal Digits before Other Chords, with or without a leading Minus Sign

        prefix = b"\x15" + str(arg1).encode()
        if arg1 == -1:
            prefix = b"\x15" + b"-"

        if (lead_chord not in b"123456789") or (arg1 == 0):

            return prefix

        # Close the Prefix with ⌃U to separate from a Decimal Digit Chord

        prefix += b"\x15"

        return prefix

        # Em Py echoes the Evalled Prefix, Emacs quirkily does Not

    def do_em_negative_argument(self):  # Emacs ⌥-
        """Mostly work like ⌃U -"""

        skin = self.vi.editor.skin
        arg1 = skin.arg1

        chars_ahead = "\x15"  # NAK, ⌃U, 21
        if arg1 is None:
            chars_ahead += "-"
        else:
            int_arg1 = int(arg1)  # unneeded, ducks PyLint invalid-unary-operand-type
            chars_ahead += str(-int_arg1)

        skin.chord_ints_ahead = list(chars_ahead.encode())

    def do_em_digit_argument(self):  # Emacs ⌥0, ⌥1, ⌥2, ⌥3, ⌥4, ⌥5, ⌥6, ⌥7, ⌥8, ⌥9
        """Mostly work like ⌃U 0, 1, 2, 3, 4, 5, 6, 7, 8, 9"""

        vi = self.vi
        editor = vi.editor
        skin = editor.skin

        arg1 = skin.arg1
        chord_ints_ahead = skin.chord_ints_ahead

        #

        str_digit = vi.vi_get_arg0_digit()

        chars_ahead = "\x15"  # NAK, ⌃U, 21
        if arg1 is None:
            chars_ahead += str_digit
        else:
            chars_ahead += str(arg1) + str_digit

        chord_ints_ahead[::] = chord_ints_ahead + list(chars_ahead.encode())

    def do_em_quoted_insert(self):  # Emacs ⌃Q
        """Take the next Input Keyboard Chord to replace or insert, not as Control"""

        self.vi.do_vi_quoted_insert()

    #
    # Define Control Chords
    #

    def do_em_keyboard_quit(self):  # Emacs ⌃G  # Em Py Init
        """Cancel stuff, and eventually prompt to quit Em Py"""

        # Start up lazily, so as to blink into XTerm Alt Screen only when needed

        vi = self.vi
        if not vi.editor.painter.rows:

            vi.do_next_vi_file()  # as if Vi Py b":n\r"
            vi.vi_print()  # clear the announce of First File
            vi.do_resume_vi()  # as if Vi Py b":em\r"

        # Cancel stuff, and eventually prompt to quit Em Py

        count = self.vi.editor.get_arg1_int(default=None)
        if count is not None:  # ⌃U 123 ⌃G Egg

            self.vi.vi_print("Quit Repeat Count")

        else:

            verb = os_path_corename(sys.argv[0])
            title_py = verb.title() + " Py"  # version of "Vi Py", "Em Py", etc

            version = module_file_version_zero()

            held_vi_file = vi.held_vi_file
            nickname = held_vi_file.pick_file_nickname() if held_vi_file else None

            vi.vi_print(
                "{!r}  Press ⌃X⌃C to save changes and quit {} {}".format(
                    nickname, title_py, version
                )
            )
            # such as '/dev/stdout'  Press ⌃X⌃C to save changes and quit Emacs Py  0.1.2

        # Emacs ⌃G Quirk rings a Bell for each extra ⌃G, Em Py doesn't
        # FIXME: ⌃U⌃X⌃C should mean Exit 1, not Exit 4

    def do_em_save_buffer(self):  # Emacs ⌃X⌃S
        """Write the File"""

        vi = self.vi
        vi.vi_save_buffer()

    def do_em_talk_of_control_x_control_c(self):  # Emacs ⌃C⌃X, akin to Vim ⇧Q⇧Z
        """Suggest ⌃X⌃C in place of a 1⌃C⌃X⌃C framing error, etc"""

        self.vi.vi_print("Did you mean ⌃X ⌃C")

    def do_em_save_buffers_kill_terminal(self):  # Emacs ⌃X⌃C
        """Write the File and quit Em"""

        vi = self.vi
        editor = vi.editor
        skin = editor.skin

        vi.vi_save_buffer()

        skin.doing_traceback = skin.traceback  # ⌃X⌃C of the ...⌃X⌃C Eggs
        vi.quit_vi()

    def do_em_suspend_frame(self):  # Emacs ⌃Z
        """Don't save changes now, do stop Em Py process, till like Bash 'fg'"""

        self.vi.do_vi_suspend_frame()

    def do_em_display_line_numbers_mode(self):  # Em Py ⌃CN Egg
        """Show Line Numbers or not, but without rerunning Search"""

        self.vi.editor.do_set_invnumber()

    #
    # Slip the Cursor to a Column, or step it to a Row
    #
    # TODO: code up ⌃U Arg1 and Bounds Checks
    #

    def do_em_back_to_indentation(self):  # Emacs ⌥M
        """Leap to the Column after the Indent"""

        self.vi.editor.slip_dent()

    def do_em_backward_char(self):  # Emacs ⌃B
        """Slip left or up"""

        self.vi.slip_behind_one()

    def do_em_beginning_of_buffer(self):  # Emacs ⇧⌥<
        """Leap to the first Column of the first Line"""

        editor = self.vi.editor

        editor.row = 0
        editor.column = 0

    def do_em_end_of_buffer(self):  # Emacs ⇧⌥>
        """Leap to the last Column of the last Line"""

        editor = self.vi.editor
        last_row = editor.spot_last_row()

        editor.row = last_row
        editor.column = editor.spot_max_column()

    def do_em_forward_char(self):  # Emacs ⌃F
        """Slip right or down"""

        self.vi.slip_ahead_one()

    def do_em_goto_line(self):  # Emacs ⌥G⌥G  # Emacs ⌥GG
        """Leap to the first Column of the chosen Line"""

        editor = self.vi.editor
        last_row = editor.spot_last_row()

        self.vi.check_vi_index(editor.skin.arg1 is not None)
        self.vi.check_vi_index(editor.skin.arg1 > 0)
        # TODO: Emacs prompt "Goto line:"

        count = editor.get_arg1_int(default=None)
        row = min(last_row, count - 1)

        editor.row = row
        editor.column = 0

        # Em Py rejects zero and negative Row Indices
        # Emacs quirkily takes zero and negative Row Indices as aliases of 1

    def do_em_move_beginning_of_line(self):  # Emacs ⌃A
        """Leap to the first Column in Row"""

        editor = self.vi.editor
        editor.column = 0

    def do_em_move_end_of_line(self):  # Emacs ⌃E
        """Leap to just beyond the last Column in Row"""

        editor = self.vi.editor
        editor.column = editor.spot_max_column()

    def do_em_next_line(self):  # Emacs ⌃N, Down
        """Step to the next Row below"""

        editor = self.vi.editor
        editor.row += 1

    def do_em_move_to_column(self):  # Emacs ⌥GTab
        """Leap to the chosen Column up from zero"""

        editor = self.vi.editor
        max_column = editor.spot_max_column()

        self.vi.check_vi_index(editor.skin.arg1 is not None)
        self.vi.check_vi_index(editor.skin.arg1 > 0)
        # TODO: Emacs prompt "Move to column:"

        count = editor.get_arg1_int(default=None)
        column = min(max_column, count - 1)

        editor.column = column

        # Emacs and Em Py reject a negative Column Index
        # Emacs quirkily counts Columns up from 0, whereas Em Py counts up from 1

    def do_em_previous_line(self):  # Emacs ⌃P, Up
        """Step to the next Row above"""

        editor = self.vi.editor
        editor.row -= 1

    #
    # Scroll Rows of the Screen
    #

    def do_em_move_to_window_line_top_bottom(self):  # ⌥R
        """Step Cursor to Middle/ Top/ Bottom Row"""

        vi = self.vi
        editor = vi.editor
        count = len(editor.skin.doing_funcs[1:]) % 3

        if count == 0:
            editor.row = editor.spot_middle_row()
            vi.vi_print("bounced the Cursor to Leftmost Column of Middle Row")
        elif count == 1:
            editor.row = editor.top_row
            vi.vi_print("bounced the Cursor to Leftmost Column of Top Row")
        else:
            assert count == 2
            editor.row = editor.spot_bottom_row()
            vi.vi_print("bounced the Cursor to Leftmost Column of Bottom Row")

        editor.column = 0

    def do_em_recenter_top_bottom(self):  # Emacs ⌃U⌃L, Emacs ⌃L
        """Scroll up or down till Cursor Row lands on Middle/ Top/ Bottom Row"""

        editor = self.vi.editor
        count = len(editor.skin.doing_funcs[1:]) % 3

        if count == 0:
            editor.scroll_till_middle()
        elif count == 1:
            editor.scroll_till_top()
        else:
            assert count == 2
            editor.scroll_till_bottom()

        # Emacs quirkily blinks the screen & flashes the cursor left at first call
        # Em Py doesn't

    def do_em_scroll_up_command(self):  # Emacs ⌃V Page Down
        """Scroll to show the next Rows of Screen"""

        vi = self.vi
        editor = vi.editor
        painter = editor.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows >= 3
        default_count = scrolling_rows - 2

        count = editor.get_arg1_int(default=default_count)
        for index in range(count):

            row = editor.row
            top_row = editor.top_row
            last_row = editor.spot_last_row()

            # Quit at last Row

            if editor.top_row == last_row:
                if not index:
                    vi.vi_print("Do you mean ⌃U1⌥V")  # ⇧⌥>⌃V Egg

                return

            # Scroll ahead one, but keep Cursor on Screen

            if top_row < last_row:
                top_row += 1
                if row < top_row:  # pylint: disable=consider-using-max-builtin
                    row = top_row

            editor.top_row = top_row  # always different Top Row

            editor.row = row  # same or different Row
            editor.column = 0  # same or different Column

    def do_em_scroll_down_command(self):  # Emacs ⌥V Page Up
        """Page Up"""

        vi = self.vi
        editor = vi.editor
        painter = editor.painter
        scrolling_rows = painter.scrolling_rows

        assert scrolling_rows >= 3
        default_count = scrolling_rows - 2

        count = editor.get_arg1_int(default=default_count)
        for index in range(count):

            row = editor.row
            top_row = editor.top_row

            # Quit at top Row

            if not top_row:
                if not index:
                    vi.vi_print("Do you mean ⌃U1⌃V")  # ⇧⌥<⌥V Egg

                return

            # Scroll behind one, but keep Cursor on Screen

            if top_row:
                top_row -= 1

                bottom_row = editor.spot_bottom_row(top_row)
                if row > bottom_row:  # pylint: disable=consider-using-min-builtin
                    row = bottom_row

            editor.top_row = top_row  # always different Top Row

            editor.row = row  # same or different Row
            editor.column = 0  # same or different Column

    #
    # Slip across Words
    #

    def do_em_backward_word(self):  # Emacs ⌥B
        """Leap behind over Separators & Letters to the first Letter of that Word"""

        self.vi.do_big_word_start_behind()

        # FIXME: code up Em Py ⌥B 'backward_word' as distinct from Vi Py ⌥B

    def do_em_forward_word(self):  # Emacs ⌥F
        """Leap ahead over Separators & Letters to the next Separator or Beyond Line"""

        self.vi.do_big_word_start_ahead()

        # FIXME: code up Em Py ⌥F 'forward_word' as distinct from Vi Py ⌥F

    def do_em_mark_paragraph(self):  # Emacs ⌥H
        """Mark the blank Line before a Paragraph and the Lines of the Paragraph"""

        raise NotImplementedError()  # TODO: code up ⌥H 'mark_paragraph'

    #
    # Search for Hits
    #

    def do_em_query_replace(self):  # Emacs ⇧⌥%
        """Walk Hits and ask:  y Space . Y, or n Delete N, or q Return, etc"""

        raise NotImplementedError()  # TODO: code up ⇧⌥% 'query_replace'

    #
    # Insert Chords as Chars
    #

    def do_em_self_insert_command(self):  # Emacs Bypass Vim View to Insert
        """Insert the Chord as one Char"""

        vi = self.vi
        editor = vi.editor

        chars = editor.get_arg0_chars()
        if chars == LF_CHAR:  # Emacs ⌃Q⌃J
            vi.do_insert_one_line()
        else:
            vi.do_insert_one_char()

    def do_em_newline(self):  # Emacs Return
        """Open a new indented Line below"""

        vi = self.vi

        vi.vi_print("Do you mean ⌃Q⌃J")

    #
    # Delete Chars
    #

    def do_em_delete_char(self):  # Emacs ⌃D
        """Cut as many as the count of Chars ahead, but keep the Cursor in Bounds"""

        vi = self.vi
        editor = vi.editor

        column = editor.column
        max_column = editor.spot_max_column()

        if column == max_column:  # FIXME: join for ⌃D without inserting a Space
            vi.do_slip_last_join_right()
        else:
            vi.do_cut_ahead()

    def do_delete_backward_char(self):  # Emacs Delete
        """Cut as many as the count of Chars behind, but keep the Cursor in Bounds"""

        self.vi.do_cut_behind()

    def do_em_kill_line(self):  # Emacs ⌃K  # FIXME: doc well
        """Cut Chars ahead in Line, else cut Line, and complex with Count"""

        vi = self.vi
        editor = vi.editor

        column = editor.column
        max_column = editor.spot_max_column()

        if column == max_column:  # FIXME: join for ⌃K without inserting a Space
            vi.do_slip_last_join_right()
        else:
            vi.do_chop()

        # FIXME: Em Py ⌃K 'kill_line' so much wrong with count

    def do_em_zap_to_char(self):  # Emacs ⌥Z
        """Cut from here to past where found, if found, else raise an Exception"""

        count = self.vi.get_vi_arg1_int()
        choice = self.vi.get_vi_arg2_chars()

        vi = self.vi
        editor = vi.editor
        ch = editor.fetch_column_char()

        # Reject non-positive ⌥Z for now

        if count < 1:
            raise NotImplementedError()  # TODO: non-positive ⌥Z

        # Move to select just some Chars, or some Chars and Lines

        here_pin = editor.spot_pin()

        if ch != choice:
            vi.do_slip_index_choice()

        vi.slip_ahead_one()

        there_pin = editor.spot_pin()

        # Cut the Selection, after leaping to its Upper Left

        vi.cut_across(here_pin, there_pin=there_pin)

        # Em Py ⌥Z respects case, because the Search Key is so small, just 1 Char
        # Emacs ⌥Z Quirk disrespects case, unless you tell All Searches to respect case

        # FIXME: Emacs ⌥Z Space accepts an empty File, because Space is blank

    def do_em_kill_word(self):  # Emacs ⌥D
        """Cut from here to where ⌥F 'forward-word' finds blanks begin"""

        raise NotImplementedError()  # TODO: code up ⌥D 'kill_word'

    #
    # Shell out
    #

    def do_em_shell_command_on_region(self):  # ⇧⌥|
        """Take a Bash command line to pipe some Chars through"""

        raise NotImplementedError()  # TODO: code up ⇧⌥| 'shell_command_on_region'

    def do_em_execute_extended_command(self):  # ⌥X
        """Take an ELisp command line to run"""

        raise NotImplementedError()  # TODO: code up ⌥X 'execute_extended_command'


class EmPyNameError(NameError):
    """Signal trouble like a NameError but mention the Em Py keymap"""


class TerminalKeyboardEm(TerminalKeyboard):
    """Map Keyboard Inputs to Code, for when feeling like Emacs"""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, em, vi):
        super().__init__()

        self.em = em
        self.vi = vi
        self.editor = vi.editor

        self.format_status_func = vi.format_vi_status
        self.place_cursor_func = vi.place_vi_cursor

        self.do_prefix_chord_func = em.do_em_prefix_chord
        self.eval_prefix_func = em.eval_em_prefix
        self.uneval_prefix_func = em.uneval_em_prefix

        self._init_by_em_chords_()

    def _init_by_em_chords_(self):
        # pylint: disable=too-many-statements

        funcs = self.func_by_chords
        em = self.em

        # Define the C0_CONTROL_STDINS

        # funcs[b"\x00"] = em.do_em_c0_control_nul  # NUL, ⌃@, 0
        funcs[b"\x01"] = em.do_em_move_beginning_of_line  # SOH, ⌃A, 1
        funcs[b"\x02"] = em.do_em_backward_char  # STX, ⌃B, 2

        self._init_func(b"\x03\x18", func=em.do_em_talk_of_control_x_control_c)  # ⌃C⌃X
        self._init_func(b"\x03n", func=em.do_em_display_line_numbers_mode)  # ⌃CN
        self._init_func(b"\x03x", func=em.do_em_talk_of_control_x_control_c)  # ⌃CX
        # TODO: stop commandeering the personal ⌃CN ⌃CX Chord Sequences
        funcs[b"\x04"] = em.do_em_delete_char  # EOT, ⌃D, 4
        funcs[b"\x05"] = em.do_em_move_end_of_line  # ENQ, ⌃E, 5
        funcs[b"\x06"] = em.do_em_forward_char  # ACK, ⌃F, 6
        funcs[b"\x07"] = em.do_em_keyboard_quit  # BEL, ⌃G, 7 \a
        # funcs[b"\x08"] = em.do_em_c0_control_bs  # BS, ⌃H, 8 \b
        # funcs[b"\x09"] = em.do_em_c0_control_tab  # TAB, ⌃I, 9 \t
        # funcs[b"\x0A"] = em.do_em_c0_control_lf  # LF, ⌃J, 10 \n
        funcs[b"\x0B"] = em.do_em_kill_line  # VT, ⌃K, 11 \v
        funcs[b"\x0C"] = em.do_em_recenter_top_bottom  # FF, ⌃L, 12 \f
        funcs[b"\x0D"] = em.do_em_newline  # CR, ⌃M, 13 \r
        funcs[b"\x0E"] = em.do_em_next_line  # SO, ⌃N, 14
        # funcs[b"\x0F"] = em.do_em_c0_control_si  # SI, ⌃O, 15
        funcs[b"\x10"] = em.do_em_previous_line  # DLE, ⌃P, 16
        # funcs[b"\x11"] = em.do_em_c0_control_dc1  # DC1, XON, ⌃Q, 17
        funcs[b"\x11"] = em.do_em_quoted_insert  # DC1, XON, ⌃Q, 17
        # funcs[b"\x12"] = em.do_em_c0_control_dc2  # DC2, ⌃R, 18
        # funcs[b"\x13"] = em.do_em_c0_control_dc3  # DC3, XOFF, ⌃S, 19
        # funcs[b"\x14"] = em.do_em_c0_control_dc4  # DC4, ⌃T, 20
        # funcs[b"\x15"] = em.do_em_scroll_behind_some  # NAK, ⌃U, 21
        funcs[b"\x16"] = em.do_em_scroll_up_command  # SYN, ⌃V, 22
        # funcs[b"\x17"] = em.do_em_c0_control_etb  # ETB, ⌃W, 23

        # funcs[b"\x18"] = em.do_em_c0_control_can  # CAN, ⌃X , 24
        self._init_func(b"\x18\x03", func=em.do_em_save_buffers_kill_terminal)  # ⌃X⌃C
        self._init_func(b"\x18\x13", func=em.do_em_save_buffer)  # ⌃X⌃S
        self._init_func(b"\x18c", func=em.do_em_talk_of_control_x_control_c)  # ⌃XC

        # funcs[b"\x19"] = em.do_em_c0_control_em  # EM, ⌃Y, 25

        funcs[b"\x1A"] = em.do_em_suspend_frame  # SUB, ⌃Z, 26
        # funcs[b"\x1B"] = ...  # ESC, ⌃[, 27  # taken below by Use Option as Meta Key

        funcs[b"\x1B[A"] = em.do_em_previous_line  # ↑ Up-Arrow
        funcs[b"\x1B[B"] = em.do_em_next_line  # ↓ Down-Arrow
        funcs[b"\x1B[C"] = em.do_em_forward_char  # → Right-Arrow
        funcs[b"\x1B[D"] = em.do_em_backward_char  # ← Left-Arrow

        # funcs[b"\x1C"] = em.do_em_eval_em_line   # FS, ⌃\, 28
        # funcs[b"\x1D"] = em.do_em_c0_control_gs  # GS, ⌃], 29
        # funcs[b"\x1E"] = em.do_em_c0_control_rs  # RS, ⌃^, 30
        # funcs[b"\x1F"] = em.do_em_c0_control_us  # US, ⌃_, 31

        funcs[b"\x7F"] = em.do_delete_backward_char  # DEL, ⌃?, 127

        # Define the BASIC_LATIN_STDINS (without defining the CR_STDIN outside)

        self.intake_chords_set = set(BASIC_LATIN_STDINS)
        self.intake_func = em.do_em_self_insert_command

        # Define Em Py Esc Keyboard Input Chords
        # found at Keyboard > Use Option as Meta Key = Yes
        # inside macOS Terminal > Preferences > Profiles

        self._init_func(b"\x1B%", em.do_em_query_replace)  # ⇧⌥%
        self._init_func(b"\x1B-", em.do_em_negative_argument)  # ⌥-
        self._init_func(b"\x1B0", em.do_em_digit_argument)  # ⌥0
        self._init_func(b"\x1B1", em.do_em_digit_argument)  # ⌥1
        self._init_func(b"\x1B2", em.do_em_digit_argument)  # ⌥2
        self._init_func(b"\x1B3", em.do_em_digit_argument)  # ⌥3
        self._init_func(b"\x1B4", em.do_em_digit_argument)  # ⌥4
        self._init_func(b"\x1B5", em.do_em_digit_argument)  # ⌥5
        self._init_func(b"\x1B6", em.do_em_digit_argument)  # ⌥6
        self._init_func(b"\x1B7", em.do_em_digit_argument)  # ⌥7
        self._init_func(b"\x1B8", em.do_em_digit_argument)  # ⌥8
        self._init_func(b"\x1B9", em.do_em_digit_argument)  # ⌥9
        self._init_func(b"\x1B<", em.do_em_beginning_of_buffer)  # ⇧⌥<
        self._init_func(b"\x1B>", em.do_em_end_of_buffer)  # ⇧⌥>
        self._init_func(b"\x1Bb", em.do_em_backward_word)  # ⌥B
        self._init_func(b"\x1Bd", em.do_em_kill_word)  # ⌥D
        self._init_func(b"\x1Bf", em.do_em_forward_word)  # ⌥F
        self._init_func(b"\x1Bg\x09", em.do_em_move_to_column)  # ⌥GTab
        self._init_func(b"\x1Bg\x1Bg", em.do_em_goto_line)  # ⌥G⌥G
        self._init_func(b"\x1Bgg", em.do_em_goto_line)  # ⌥GG
        self._init_func(b"\x1Bh", em.do_em_mark_paragraph)  # ⌥H
        self._init_func(b"\x1Bm", em.do_em_back_to_indentation)  # ⌥M
        self._init_func(b"\x1Br", em.do_em_move_to_window_line_top_bottom)  # ⌥R
        self._init_func(b"\x1Bv", em.do_em_scroll_down_command)  # ⌥V

        self._init_func(b"\x1Bx", em.do_em_execute_extended_command)  # ⌥X
        # self._init_func(b"\x1Bxvi\r", vi.do_vi_resume_vi)  # ⌥X

        self._init_suffix_func(b"\x1Bz", em.do_em_zap_to_char)  # ⌥Z
        self._init_func(b"\x1B|", em.do_em_shell_command_on_region)  # ⇧⌥|

        em_optchars_list = """
            ⇧⌥% ⌥-
            ⌥0 ⌥1 ⌥2 ⌥3 ⌥4 ⌥5 ⌥6 ⌥7 ⌥8 ⌥9 ⇧⌥< ⇧⌥>
            ⌥B ⌥D ⌥F ⌥G ⌥GG ⌥GTab ⌥G⌥G ⌥H ⌥M ⌥R ⌥V ⌥X ⌥Z ⇧⌥|
        """.split()

        for optchars in em_optchars_list:
            unichars = TerminalNudgeIn.UNICHARS_BY_OPTCHARS[optchars]
            optchords = self.to_optchords(optchars)

            self.init_unichars_func(unichars, optchords=optchords)


#
# Define the Editors in terms of Keyboard, Screen, Files of Bytes, & Spans of Chars
#


class TerminalNudgeIn(argparse.Namespace):
    """Collect the parts of one Nudge In from the Keyboard"""

    # pylint: disable=too-few-public-methods

    NAME_BY_CHAR = {
        "\x09": "Tab",  # kin to ⇥ U21E5 Rightward Arrows to Bar
        "\x0D": "Return",  # kin to ⏎ U23CE Return Symbol
        "\x1B": "Esc",  # kin to ⎋ U238B Broken Circle With Northwest Arrow
        " ": "Space",  # kin to ␢ U2422 Blank Symbol, ␣ U2423 Open Box
        "\x7F": "Delete",  # kin to ⌫ U232B Erase To The Left
    }

    # Striking Option + Key produces one Unichar in place of the Option ⌥ Char Pair
    # when struck inside Keyboard > Use Option as Meta Key = No
    # inside macOS Terminal > Preferences > Profiles

    UNICHARS_BY_OPTCHARS = {
        "⇧⌥#": "\u2039",  # SingleLeftPointingAngleQuotationMark
        "⇧⌥$": "\u203A",  # SingleRightPointingAngleQuotationMark
        "⇧⌥%": "\uFB01",  # LatinSmallLigatureFI
        "⇧⌥*": "\u00B0",  # DegreeSign
        "⇧⌥+": "\u00B1",  # PlusMinusSign
        "⌥,": "\u2264",  # LessThanOrEqualTo
        "⌥-": "\u2013",  # EnDash
        "⌥/": "\u00F7",  # DivisionSign
        "⌥0": "\u00BA",  # MasculineOrdinalIndicator
        "⌥1": "\u00A1",  # InvertedExclamationMark
        "⌥2": "\u2122",  # TradeMarkSign  # ⌥2 at UK Keyboard is \20AC EuroSign
        "⌥3": "\u00A3",  # PoundSign  # ⌥3 at UK Keyboard is \0023 NumberSign
        "⌥4": "\u00A2",  # CentSign
        "⌥5": "\u221E",  # Infinity
        "⌥6": "\u00A7",  # SectionSign
        "⌥7": "\u00B6",  # PilcrowSign
        "⌥8": "\u2022",  # Bullet [Pearl]
        "⌥9": "\u00AA",  # FeminineOrdinalIndicator
        "⌥;": "\u2026",  # HorizontalEllipsis
        "⇧⌥:": "\u00DA",  # LatinCapitalLetterAWithAcute
        "⇧⌥:g/": "\u00DAg/",  # LatinCapitalLetterAWithAcute : ...
        "⇧⌥:n⇧!⌃M": "\u00DAn!\r",
        "⇧⌥:n⌃M": "\u00DAn\r",
        "⇧⌥:q⇧!⌃M": "\u00DAq!\r",
        "⇧⌥:q⌃M": "\u00DAq\r",
        "⇧⌥:vi⌃M": "\u00DAvi\r",
        "⇧⌥:w⇧!⌃M": "\u00DAw!\r",
        "⇧⌥:w⌃M": "\u00DAw\r",
        "⇧⌥:wn⇧!⌃M": "\u00DAwn!\r",
        "⇧⌥:wn⌃M": "\u00DAwn\r",
        "⇧⌥:wq⇧!⌃M": "\u00DAwq!\r",
        "⇧⌥:wq⌃M": "\u00DAwq\r",
        "⇧⌥<": "\u00AF",  # Macron
        "⇧⌥>": "\u02D8",  # Breve
        "⇧⌥?": "\u00BF",  # InvertedQuestionMark
        "⌥A": "\u00E5",  # LatinSmallLetterAWithRingAbove
        "⌥B": "\u222B",  # Integral  # ⌥← comes in as Esc B
        "⌥C": "\u00E7",  # LatinSmallLetterCWithCedilla
        "⌥D": "\u2202",  # PartialDifferential
        "⌥EE": "\u00E9",  # LatinSmallLetterEWithAcute E
        "⌥F": "\u0192",  # LatinSmallLetterFWithHook  # ⌥→ comes in as Esc F
        "⌥G": "\u00A9",  # CopyrightSign
        "⌥GG": "\u00A9g",  # CopyrightSign G
        "⌥GTab": "\u00A9\x09",  # CopyrightSign Tab
        "⌥G⌥G": "\u00A9\u00A9",  # 2x CopyrightSign
        "⌥H": "\u02D9",  # DotAbove
        "⌥II": "\u00EE",  # LatinSmallLetterIWithCircumflex
        "⌥J": "\u2206",  # Increment
        "⌥K": "\u02DA",  # RingAbove
        "⌥L": "\u00AC",  # NotSign
        "⌥M": "\u00B5",  # MicroSign
        "⌥NN": "\u00F1",  # LatinSmallLetterNWithTilde
        "⌥O": "\u00F8",  # LatinSmallLetterOWithStroke
        "⌥R": "\u00AE",  # RegisteredSign
        "⌥S": "\u00DF",  # LatimSmallLetterSharpS
        "⌥T": "\u2020",  # Dagger
        "⌥V": "\u221A",  # SquareRoot
        "⌥W": "\u2211",  # NArySummation
        "⌥X": "\u2248",  # AlmostEqualTo
        "⌥Z": "\u03A9",  # GreekCapitalLetterOmega
        "⌥Z.": "\u03A9.",  # GreekCapitalLetterOmega .
        "⌥ZB": "\u03A9b",  # GreekCapitalLetterOmega B
        "⌥ZT": "\u03A9t",  # GreekCapitalLetterOmega T
        r"⌥\I": "\u00ABi",  # LeftPointingDoubleAngleQuotationMark I
        r"⌥\N": "\u00ABn",  # LeftPointingDoubleAngleQuotationMark N
        r"⌥\⇧F": "\u00ABF",  # LeftPointingDoubleAngleQuotationMark ⇧F
        "⇧⌥^": "\uFB02",  # LatinSmallLigatureFL
        "⇧⌥_": "\u2014",  # EmDash
        "⇧⌥{": "\u201D",  # RightDoubleQuotationMark
        "⇧⌥|": "\u00BB",  # RightPointingDoubleAngleQuotationMark
        "⇧⌥}": "\u2019",  # RightSingleQuotationMark
        "⇧⌥A": "\u00C5",  # LatinCapitalLetterAWithRingAbove
        "⇧⌥B": "\u0131",  # LatinSmallLetterDotlessI
        "⇧⌥C": "\u00C7",  # LatinCapitalLetterCWithCedilla
        "⇧⌥D": "\u00CE",  # LatinCapitalLetterIWithCircumflex
        "⇧⌥E⇧⌥E": "\u00B4",  # AcuteAccent
        "⇧⌥F": "\u00CF",  # LatinCapitalLetterIWithDiaeresis
        "⇧⌥G": "\u02DD",  # DoubleAcuteAccent
        "⇧⌥H": "\u00D3",  # LatinCapitalLetterOWithAcute
        "⇧⌥I⇧⌥I": "\u02C6",  # ModifierLetterCircumflexAccent
        "⇧⌥J": "\u00D4",  # LatinCapitalLetterOWithCircumflex
        "⇧⌥L": "\u00D2",  # LatinCapitalLetterOWithGrave
        "⇧⌥QVI⌃M": "\u0152vi\r",  # LatinCapitalLigatureOE V I Return
        "⇧⌥M": "\u00C2",  # LatinCapitalLetterAWithCircumflex
        "⇧⌥N⇧⌥N": "\u02DC",  # SmallTilde
        "⇧⌥O": "\u00D8",  # LatinCapitalLetterOWithStroke
        "⇧⌥R": "\u2030",  # PerMilleSign
        "⇧⌥S": "\u00CD",  # LatinCapitalLetterIWithAcute
        "⇧⌥T": "\u02C7",  # Caron
        "⇧⌥W": "\u201E",  # DoubleLow9QuotationMark
        "⇧⌥X": "\u02DB",  # Ogonek
        "⇧⌥Z⇧⌥Q": "\u00B8\u0152",  # Cedilla LatinCapitalLigatureOE
        "⇧⌥Z⇧⌥Z": "\u00B8\u00B8",  # 2x Cedilla
    }

    # FIXME: macOS Option keys outside Basic Latin for Vi Py  # ⌥C ⌥D 1234567890

    OPTCHARS_COUNTER = collections.Counter(UNICHARS_BY_OPTCHARS.values())
    OPTCHARS_DUPES = list(_ for _ in OPTCHARS_COUNTER.items() if _[-1] != 1)
    OPTCHARS_BY_UNICHARS = {v: k for (k, v) in UNICHARS_BY_OPTCHARS.items()}

    assert not OPTCHARS_DUPES, ascii(OPTCHARS_DUPES)
    assert len(UNICHARS_BY_OPTCHARS.keys()) == len(OPTCHARS_BY_UNICHARS.keys())

    # MacOS UK/USA Keyboards reserve ⌥E, ⌥I, ⌥N, ⌥U for adding diacritical marks
    # and they alias X5E ^ at ⌥I⌥I, and X7E ~ at ⌥N⌥N

    def __init__(self, nudge=None):
        # pylint: disable=super-init-not-called

        self.prefix = None  # such as Repeat Count b"1234567890" before Vi Chords
        self.chords = None  # such as b"Qvi\r" Vi Chords
        self.suffix = None  # such as b"x" of b"fx" to Find Char "x" in Vi
        self.epilog = None  # such as b"⌃C" of b"f⌃C" to cancel b"f"

        # FIXME: Below is too much work to do for each new TerminalNudgeIn?

        # Map the ⌃@, ⌃A, ⌃B, ... ⌃Z, ⌃[, ⌃\, ⌃], ⌃^, ⌃_, and ⌃? to themselves

        name_by_char = dict(TerminalNudgeIn.NAME_BY_CHAR)

        for chord in C0_CONTROL_STDINS:  # for ord(chord) in 0x00..0x1F and 0x7F
            name = "⌃" + chr(ord(chord) ^ 0x40)  # ⌃ U2303 UpArrowhead
            assert name[len("⌃") :].encode() in BASIC_LATIN_STDINS, (chord, name)
            ch = chord.decode()
            if ch not in name_by_char.keys():

                name_by_char[ch] = name

        # Map the r"[A-Z]" to themselves: ⇧A to ⇧A, A to A, etc

        for chord in BASIC_LATIN_STDINS:
            ch = chord.decode()
            if ch.lower() != ch.upper():

                if ch == ch.upper():
                    name = "⇧" + ch
                else:
                    name = ch.upper()

                assert ch not in name_by_char.keys(), (ch, name, name_by_char[ch])
                name_by_char[ch] = name

        # Map the shifted punctuation to themselves

        ascii_shifted_marks = '~!@#$%^&*()_+{}|:"<>?'
        for ch in ascii_shifted_marks:
            name = "⇧" + ch
            name_by_char[ch] = name

        # Map enough of the ⌥ Option Keys to themselves

        for (optchars, unichars) in TerminalNudgeIn.UNICHARS_BY_OPTCHARS.items():

            assert unichars not in name_by_char.keys(), (unichars, optchars)
            name_by_char[unichars] = optchars

        self.name_by_char = name_by_char

        # Remake Self into a 'copy.deepcopy' of 'nudge'

        if nudge is not None:

            vars(self).update(vars(nudge))

            assert (self.prefix is None) or isinstance(self.prefix, bytes)
            assert (self.chords is None) or isinstance(self.chords, bytes)
            assert (self.suffix is None) or isinstance(self.suffix, bytes)
            assert (self.epilog is None) or isinstance(self.epilog, bytes)

    def to_chars(self):
        """Echo keyboard input without asking people to memorise b'\a\b\t\n\v\f\r'"""

        nudge_bytes = b""
        if self.prefix is not None:
            nudge_bytes += self.prefix
        if self.chords is not None:
            nudge_bytes += self.chords
        if self.suffix is not None:
            nudge_bytes += self.suffix
        if self.epilog is not None:
            nudge_bytes += self.epilog

        nudge_chars = nudge_bytes.decode(errors="surrogateescape")

        prefix = self.prefix
        prefix_bytes = b"" if (prefix is None) else prefix
        prefix_chars = prefix_bytes.decode(errors="surrogateescape")

        echo = self._to_echoed_chars(prefix_chars, nudge_chars=nudge_chars)
        echo = self._rep_escaped_chars(echo)
        echo = echo.strip()

        return echo

        # such as '⌃L' at FF, ⌃L, 12, '\f'
        # such as echo the single Char '  £  ' in place of its Byte encoding '  Â £  '

    def _to_echoed_chars(self, prefix_chars, nudge_chars):
        """Form the Chars of Echo for the Called Chords + Suffix + Epilog"""
        # pylint: disable=no-self-use

        name_by_char = self.name_by_char

        echo = ""

        for (index, ch) in enumerate(nudge_chars):
            name = ch
            if ch in name_by_char.keys():
                name = name_by_char[ch]

            # Show the Chords as if inserted, for the : Ex Commands of Vim

            if index == len(prefix_chars):
                if ch == ":":
                    if not wearing_em():

                        tail = nudge_chars[index:]

                        ex_tail = tail
                        if tail.endswith("\r"):
                            ex_tail = tail[: -len("\r")]

                        rep_ex_tail = repr(ex_tail)
                        assert rep_ex_tail[0] == rep_ex_tail[-1], rep_ex_tail
                        rep_ex_line = rep_ex_tail[1:][:-1]

                        if rep_ex_line == ex_tail:
                            echo += rep_ex_line

                            return echo

            # Show each Prefix Chord without Spaces in between them

            if index < len(prefix_chars):
                if echo and (echo[-1] in "+-.0123456789") and (ch in "0123456789"):

                    echo += ch  # such as after ⌃U of Em Py

                    continue

            # Show most Chords as named or as themselves

            echo += " " + name

        return echo

    def _rep_escaped_chars(self, echo):
        """Name Chars as more themselves, not so much as Esc ..."""
        # pylint: disable=no-self-use

        echo = echo.replace("Esc [ ⇧A", "Up")  # ↑ U2191 Upwards Arrow
        echo = echo.replace("Esc [ ⇧B", "Down")  # ↓ U2193 Downwards Arrow
        echo = echo.replace("Esc [ ⇧C", "Right")  # → U2192 Rightwards Arrow
        echo = echo.replace("Esc [ ⇧D", "Left")  # ← U2190 Leftwards Arrows

        echo = echo.replace("Esc B", "⌥←")  # ← U2190 Leftwards Arrows
        echo = echo.replace("Esc F", "⌥→")  # → U2192 Rightwards Arrow

        for chord in BASIC_LATIN_STDINS:
            ch = chord.decode()

            if ch.lower() == ch.upper():
                esc_name = "Esc " + ch
                optname = "⌥" + ch
            else:
                if ch == ch.upper():
                    esc_name = "Esc ⇧" + ch
                    optname = "⇧⌥" + ch
                else:
                    esc_name = "Esc " + ch.upper()
                    optname = "⌥" + ch.upper()

            echo = echo.replace(esc_name, optname)

        return echo

        # ⌥B and ⌥F echo as themselves only inside Use Option As Meta Key = No


class TerminalReplyOut(argparse.Namespace):
    """Collect the parts of one Reply Out to the Screen"""

    # pylint: disable=too-few-public-methods

    def __init__(self, reply=None):
        # pylint: disable=super-init-not-called

        self.flags = None  # such as "-Fin" Grep-Like Search
        self.nudge = None  # keep up a trace of the last input that got us here
        self.message = None  # say more
        self.bell = None  # ring bell

        # Remake Self into a 'copy.deepcopy' of 'reply'

        if reply is not None:

            vars(self).update(vars(reply))

            assert (self.flags is None) or isinstance(self.flags, str)
            self.nudge = TerminalNudgeIn(self.nudge)
            assert (self.message is None) or isinstance(self.message, str)
            assert (self.bell is None) or isinstance(self.bell, bool)


class TerminalFile:
    """Hold a copy of the Bytes of a File awhile"""

    def __init__(self, path=None):
        # pylint: disable=super-init-not-called

        self.read_path = None  # Path to Fetched File

        self.iobytes = b""  # Bytes of File, else None
        self.iochars = ""  # Chars of File, else None
        self.ended_lines = list()  # Ended Lines of File
        self.touches = 0  # count of Changes to File

        self.write_path = "/dev/stdout"  # Path to Stored File

        # reinit by loading the File, if some File chosen

        if path is not None:
            self.load_file(path)

    def pick_file_nickname(self):
        """Sketch the Write Path concisely"""

        write_path = self.write_path

        nickname = os.path.basename(write_path)
        if write_path.startswith("/dev/"):
            nickname = write_path

        return nickname

    def load_file(self, path):
        """Read the Bytes of the File, decode as Chars, split as Lines"""

        read_path = os.path.abspath(path)
        self.read_path = read_path

        with open(read_path, "rb") as reading:
            if reading.isatty():
                stderr_print("Press ⌃D EOF to quit")
            try:
                self.iobytes = reading.read()
            except KeyboardInterrupt:  # Egg at:  bin/vi.py -
                stderr_print()

                sys.exit(1)

        self.iochars = self.iobytes.decode(errors="surrogateescape")

        self.ended_lines = self.iochars.splitlines(keepends=True)
        if not lines_last_has_no_end(self.ended_lines):
            if wearing_em():
                self.ended_lines.append("")

        self.write_path = "/dev/stdout" if (path == "/dev/stdin") else read_path

    def decode_file(self):
        """Re-decode the File after changes"""

        if not self.ended_lines:

            return ""

        self.iochars = "".join(self.ended_lines)
        self.iobytes = self.iochars.encode(errors="surrogateescape")

        return self.iochars

        # TODO: stop re-decode'ing while 'self.ended_lines' unchanged

    def encode_file(self):
        """Re-encode the File after changes"""

        if not self.ended_lines:

            return b""

        self.iochars = "".join(self.ended_lines)
        self.iobytes = self.iochars.encode(errors="surrogateescape")

        return self.iobytes

        # TODO: stop re-encode'ing while 'self.ended_lines' unchanged

    def flush_file(self):
        """Store the File"""

        write_path = self.write_path

        iobytes = self.encode_file()
        with open(write_path, "wb") as writing:
            writing.write(iobytes)

        self.touches = 0


class TerminalPin(  # pylint: disable=too-few-public-methods
    collections.namedtuple("TerminalPin", "row, column".split(", ")),
):
    """Pair up a Row with a Column"""

    # TODO:  class TerminalPinVi - to slip and step in the way of Vi


class TerminalPinPlus(  # pylint: disable=too-few-public-methods
    collections.namedtuple("TerminalPinPlus", "row, column, obj".split(", ")),
):
    """Add one more Thing to pairing up a Row with a Column"""


class TerminalSpan(
    collections.namedtuple("TerminalSpan", "row, column, beyond".split(", ")),
):
    """Pick out the Columns of Rows covered by a Match of Chars"""

    # pylint: disable=too-few-public-methods

    @staticmethod
    def find_spans(matches):
        """Quickly calculate the Row and Column of each of a List of Spans"""
        # pylint: disable=too-many-locals

        if not matches:

            return list()

        # Split the Lines apart

        some_match = matches[-1]

        chars = some_match.string
        ended_lines = chars.splitlines(keepends=True)

        # Search each Line for the next Match

        spanned_lines = list()
        spanned_chars = ""

        spans = list()
        for match in matches:
            assert match.string is some_match.string

            start = match.start()
            while start > len(spanned_chars):
                ended_line = ended_lines[len(spanned_lines)]

                spanned_lines.append(ended_line)
                spanned_chars += ended_line

            # Find the Row of the Match, in or beyond the Spanned Lines

            row = 0
            line_at = 0
            if spanned_lines:

                row = len(spanned_lines) - 1
                spanned_line = spanned_lines[-1]
                line_at = len(spanned_chars) - len(spanned_line)

                if start == len(spanned_chars):

                    row = len(spanned_lines)
                    line_at = len(spanned_chars)

            # Find the Column of the Match

            column = start - line_at
            beyond = column + (match.end() - match.start())

            # Collect this Span

            span = TerminalSpan(row, column=column, beyond=beyond)
            spans.append(span)

        # Silently drop the extra Match past the last Line,
        # to duck out of the case of an extra Match past the End of the last Line
        # as per: list(re.finditer(r"$", string="a\n\nz\n", flags=re.MULTILINE))

        if spans:

            last_span = spans[-1]
            if last_span.row >= len(ended_lines):

                del spans[-1]

        return spans


class TerminalSkin:
    """Form a Skin out of keyboard Input Chords and an Output Reply"""

    # pylint: disable=too-few-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, chords=()):

        self.traceback = None  # capture Python Tracebacks

        self.reply = TerminalReplyOut()  # begin with no Reply
        self.cursor_style = _VIEW_CURSOR_STYLE_

        self.keyboard = None  # map Keyboard Inputs to Code
        self.chord_ints_ahead = list(chords)  # defer keyboard Input Chords

        self.nudge = TerminalNudgeIn()  # begin with no Input pulled from Keyboard
        self.arg0_chords = None  # take all the Chords as Chars in a Row
        self.arg1 = None  # take the Prefix Bytes as an Int of Decimal Digits
        self.arg2_chars = None  # take the Suffix Bytes as one Encoded Char

        self.doing_less = None  # reject the Arg1 when not explicitly accepted
        self.doing_more = None  # take the Arg1 as a Count of Repetition's
        self.doing_done = None  # count the Repetition's completed before now
        self.doing_funcs = list()  # count the Call's of the same Func before now
        self.doing_traceback = None  # retain a Python Traceback till after more Chords

        # TODO: mutable namespaces for doing_, etc


#
# Define the Editors above in terms of Inputs, Outputs, & Spans of Chars
#


class TerminalEditor:
    """Feed Keyboard into Scrolling Rows of File of Lines of Chars"""

    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes

    def __init__(self, chords):

        self.skin = TerminalSkin(chords)

        self.stdio = sys.stderr  # layer over a Terminal I/O Stack
        self.driver = TerminalDriver(stdio=self.stdio)
        self.shadow = TerminalShadow(terminal=self.driver)
        self.painter = TerminalPainter(terminal=self.shadow)

        self.terminal_size = None  # detect changes in Terminal Column:Lines

        self.showing_line_number = None  # show Line Numbers or not
        self.showing_lag = None  # inject None or 0s or more Lag

        self.intake_beyond = ""  # take input from Cursor past Last Char, or don't
        self.intake_taken = False
        self.intake_column = None  # struggle to snap Cursor past Last Char, or don't
        self.intake_pins = list()  # collect a TerminalPinPlus per edit

        self.finding_case = None  # ignore Upper/Lower Case in Searching or not
        self.finding_line = None  # remember the Search Key
        self.finding_regex = None  # search as Regex or search as Chars
        self.finding_slip = 0  # remember to Search again ahead or again behind
        self.finding_highlights = None  # show Searching as Highlights, or don't

        self.row = None  # pacify PyLint W0201 'attribute-defined-outside-init'
        self.column = None
        self.top_row = None

        self.after_func = None  # call for doing more work after calling Chords Func

        # self.held_file = None  # dunno why PyLint doesn't need these too
        # self.ended_lines = None
        # self.iobytespans = None

        self.load_editor_file(TerminalFile())

        # TODO: mutable namespaces for self.finding_, etc

    def load_editor_file(self, held_vi_file):
        """Swap in a new File of Lines"""

        self.held_file = held_vi_file
        self.ended_lines = held_vi_file.ended_lines

        self.row = 0  # point the Cursor to a Row of File
        self.column = 0  # point the Cursor to a Column of File

        self.top_row = 0  # scroll through more Lines than fit on Screen

        self.iobytespans = list()  # cache the spans in file

        self.reopen_found_spans()
        self.finding_highlights = None

    #
    # Stack Skin's with Keyboard's on top of a Terminal I/O Stack
    #

    def reopen_terminal(self):
        """Clear the Caches of this Terminal, here and below, if cacheing here"""

        showing_lag = self.showing_lag
        painter = self.painter

        if not painter.rows:

            return None

        if showing_lag is not None:
            self.driver.lag = showing_lag
            painter.terminal = self.driver
        else:
            self.driver.lag = None
            painter.terminal = self.shadow

        size = painter.reopen_terminal()
        self.terminal_size = size

        return size

    def keep_busy(self, reply):
        """Work while waiting for input"""

        keyboard = self.skin.keyboard

        if self.terminal_size is not None:
            if self.driver.get_terminal_size() != self.terminal_size:

                self.reopen_terminal()  # for resize
                self.flush_editor(keyboard, reply=reply)  # for resize

    def run_terminal_with_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        assert self.showing_lag is None

        # self.painter.__enter__()  # no, enter lazily, via 'do_resume_editor'
        try:
            self.run_skin_with_keyboard(keyboard)  # like till SystemExit
        finally:
            self.painter.__exit__(*sys.exc_info())

    def run_skin_with_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        painter = self.painter
        skin = self.skin

        chords = skin.chord_ints_ahead  # TODO: works, but clashes types

        self.skin = TerminalSkin(chords)

        try:

            self.run_keyboard(keyboard)  # like till SystemExit

        except SystemExit:

            while self.driver.kbhit(timeout=0):
                chord = painter.take_painter_chord()
                for chord_int in chord:
                    self.skin.chord_ints_ahead.append(chord_int)

            raise

            # TODO: solve queued keyboard input Chords surviving '__exit__'

        finally:

            skin.chord_ints_ahead = self.skin.chord_ints_ahead
            skin.traceback = self.skin.traceback  # ⇧Z⇧Q of A⌃OZ⇧Q⌃C⇧Z⇧Q Egg

            self.skin = skin

        # TODO: reconceive 'run_skin_with_keyboard' as one of .intake_beyond

    def run_keyboard(self, keyboard):
        """Prompt, take nudge, give reply, repeat till quit"""

        self.skin.keyboard = keyboard

        # Repeat like till SystemExit raised

        while True:

            # Scroll and prompt

            chord = self.peek_one_editor_chord()
            if chord is None:
                if self.painter.rows:
                    self.scroll_cursor_into_screen()
                    self.flush_editor(keyboard, reply=self.skin.reply)  # for prompt
                    self.skin.reply.bell = False  # ring the Bell at most once per ask

            # Take one Chord in, or next Chord, or cancel Chords to start again

            chords = self.take_one_chord_cluster()

            chords_func = self.choose_chords_func(chords)
            if chords_func is None:

                continue

            # Reply

            keyboard.enter_do_func()
            keyboard.with_intake_bypass = keyboard.intake_bypass
            try:

                self.call_chords_func(chords_func)  # reply to one whole Nudge

            except KeyboardInterrupt:  # Egg of *123456n⌃C, etc
                self.skin.reply = TerminalReplyOut()

                self.editor_print("Interrupted")
                self.reply_with_bell()

                # self.skin.chord_ints_ahead = list()  # TODO: cancel Input at Exc
                self.skin.traceback = traceback.format_exc()

            except Exception as exc:  # pylint: disable=broad-except
                # TODO: file_print(traceback.format_exc())

                line = self.format_exc(exc)  # Egg of NotImplementedError, etc

                self.editor_print("")
                self.editor_print(line)  # "{exc_type}: {str_exc}"
                self.reply_with_bell()

                # self.skin.chord_ints_ahead = list()  # TODO: cancel Input at Exc
                self.skin.traceback = traceback.format_exc()
                if not self.painter.rows:

                    raise

            finally:
                if keyboard.with_intake_bypass:
                    self.close_keyboard_intake()
                keyboard.exit_do_func()

            self.skin.nudge = TerminalNudgeIn()  # consume the whole Nudge

        # TODO: shuffle away 'run_keyboard', 'choose_chords_func', 'call_chords_func'

    def format_exc(self, exc):
        """Mention an Exception, but try not to Abs Path the "~" Home"""
        # pylint: disable=no-self-use

        name = type(exc).__name__

        str_exc = str(exc)
        str_exc = str_exc.replace(ENV_HOME + os.sep, "~" + os.sep)

        line = "{}: {}".format(name, str_exc) if str_exc else name

        return line

    def do_resume_editor(self):
        """Set up XTerm Alt Screen & Keyboard, till Painter Exit"""

        self.painter.__enter__()
        self.reopen_terminal()

    def scroll_cursor_into_screen(self):
        """Scroll to place Cursor on Screen"""

        row = self.row
        painter = self.painter
        top_row = self.top_row

        half_screen = painter.scrolling_rows // 2
        last_row = self.spot_last_row()
        screen_minus = painter.scrolling_rows - 1

        # Keep the choice of Top Row on File

        top = top_row
        if not (0 <= top_row < len(self.ended_lines)):
            top = 0

        # Scroll behind to get Cursor on Screen, if need be

        if row < top:
            if (top - row) <= half_screen:
                top = row
            elif row < half_screen:
                top = row
            else:
                top = row - half_screen  # a la 'do_scroll_till_middle' Vim Z .

        # Scroll ahead to get Cursor on Screen, if need be

        bottom = self.spot_bottom_row(top_row=top)
        if row > bottom:
            if (row - bottom) <= half_screen:
                top = row - screen_minus
            elif (last_row - row) < half_screen:
                top = last_row - screen_minus
            else:
                top = row - half_screen  # a la 'do_scroll_till_middle' Vim Z .

        # After fixing the choice, assert the Top Row always was on File

        self.top_row = top

        if top_row:
            if not (0 <= top_row < len(self.ended_lines)):

                raise KwArgsException(before=top_row, after=self.top_row)

    def flush_editor(self, keyboard, reply):
        """Paint Screen, Cursor, and Bell now"""

        ended_lines = self.ended_lines
        painter = self.painter
        skin = self.skin

        # 1st: Option to rewrite whole Screen slowly

        if (self.showing_lag is None) and reply.bell:
            self.reopen_terminal()  # for bell

        # 2nd: Call back to format Status and place Cursor

        status = keyboard.format_status_func(reply)
        cursor = keyboard.place_cursor_func()
        cursor_style = skin.cursor_style

        # Paint Screen, Cursor, and Bell

        assert painter.scrolling_rows

        model_line_number = 1 + len(ended_lines)
        if wearing_em():
            model_line_number = 1 + self.top_row + (painter.scrolling_rows - 1)
            if False:  # pylint: disable=using-constant-test
                model_line_number += 1  # Egg of ⌃CN⌥9⌥9⌥G⌥G⌃L⌃L⌃L⌃U1⌥V

        painter.top_line_number = 1 + self.top_row
        painter.model_line_number = model_line_number
        painter.painting_line_number = self.showing_line_number

        screen_lines = ended_lines[self.top_row :][: painter.scrolling_rows]
        screen_spans = self.spot_spans_on_screen()

        painter.paint_screen(
            ended_lines=screen_lines,
            spans=screen_spans,
            status=status,
            cursor_style=cursor_style,
            cursor=cursor,
            bell=reply.bell,
        )

        # Flush Screen, Cursor, and Bell

        painter.flush_painter()

    def spot_spans_on_screen(self):
        """Spot where to highlight each Match of the Search Key on Screen"""

        if not self.finding_highlights:

            return list()

        iobytespans = self.iobytespans
        top_row = self.top_row
        bottom_row = self.spot_bottom_row()

        screen_spans = list()
        for span in iobytespans:
            if top_row <= span.row <= bottom_row:

                screen_span_row = span.row - top_row
                screen_span = TerminalSpan(
                    screen_span_row, column=span.column, beyond=span.beyond
                )
                screen_spans.append(screen_span)

        return screen_spans

    def choose_chords_func(self, chords):  # TODO:  # noqa C901 too complex
        """Accept one Keyboard Input into Prefix, into main Chords, or as Suffix"""
        # pylint: disable=too-many-locals

        chord_ints_ahead = self.skin.chord_ints_ahead
        old_chords = self.skin.nudge.chords
        prefix = self.skin.nudge.prefix

        keyboard = self.skin.keyboard

        do_prefix_chord_func = keyboard.do_prefix_chord_func
        eval_prefix_func = keyboard.eval_prefix_func
        uneval_prefix_func = keyboard.uneval_prefix_func

        corrections_by_chords = keyboard.corrections_by_chords
        intake_chords_set = keyboard.choose_intake_chords_set()

        assert self.skin.nudge.suffix is None, (old_chords, chords)  # one Stroke only

        # Callback to build a Prefix before the Chords to Call

        if do_prefix_chord_func(chords):

            self.editor_print("...")

            return None  # ask for more Prefix, or for other Chords

        self.skin.arg1 = eval_prefix_func(prefix)

        # Echo the Evalled Prefix + Chords + Suffix

        self.skin.nudge.prefix = uneval_prefix_func(self.skin.nudge.prefix)

        # At KeyboardInterrupt, cancel these keyboard Input Chords and start over

        chords_plus = chords if (old_chords is None) else (old_chords + chords)

        if not wearing_em():
            if prefix or old_chords:
                if chords in (b"\x03", b"\x1B"):  # ETX, ⌃C, 3  # ESC, ⌃[, 27
                    self.skin.nudge.epilog = chords

                    self.editor_print()

                    return self.do_little

                    # TODO: fail fast inside '._init_func' calls to redefine ⌃C, ESC

        # If not taking a Suffix now

        chords_func = self.editor_func_by_chords(old_chords)
        chords_plus_func = self.editor_func_by_chords(chords=chords_plus)

        keyboard.intake_ish = False
        self.intake_taken = False

        chords_plus_want_suffix = False
        if chords_plus not in intake_chords_set:
            chords_plus_want_suffix = chords_plus in keyboard.suffixes_by_chords.keys()

        if (not chords_func) or chords_plus_want_suffix:
            self.skin.nudge.chords = chords_plus
            self.skin.arg0_chords = chords_plus

            # If need more Chords

            if (not chords_plus_func) or chords_plus_want_suffix:
                if chords_plus not in corrections_by_chords.keys():

                    # Ask for more Chords, or for Suffix

                    self.editor_print("...")

                    return None

                # Auto-correct the Chords

                self.skin.nudge.chords = b""

                corrected_chords = corrections_by_chords[chords_plus]
                corrected_ints = list(corrected_chords)
                chord_ints_ahead[:] = corrected_ints + chord_ints_ahead

                self.editor_print()

                return None

            self.skin.arg2_chars = None

            # Call a Func with or without Prefix, and without Suffix

            assert chords_plus not in corrections_by_chords.keys(), (old_chords, chords)
            assert chords_plus_func is not None, (old_chords, chords)

            self.editor_print()

            return chords_plus_func

        arg0_chords = self.skin.arg0_chords
        assert arg0_chords == old_chords, (old_chords, chords, arg0_chords)

        # Call a Func chosen by Chords plus Suffix

        suffix = chords
        self.skin.nudge.suffix = suffix

        self.skin.arg2_chars = suffix.decode(errors="surrogateescape")

        # Call a Func with Suffix, but with or without Prefix

        assert old_chords not in corrections_by_chords.keys()
        assert chords_func is not None, (old_chords, chords)

        self.editor_print()

        return chords_func

    def editor_func_by_chords(self, chords):  # noqa C901 too complex
        """Choose the Func for some Chords"""

        intake_taken = self.intake_taken

        chars = chords.decode(errors="surrogateescape") if chords else ""
        chars_intake_ish = (len(chars) == 1) and (ord(chars) >= 0x80)

        keyboard = self.skin.keyboard
        keyboard_intake_ish = keyboard.intake_ish

        funcs = keyboard.func_by_chords
        intake_func = keyboard.intake_func
        intake_chords_set = keyboard.choose_intake_chords_set()

        # Pick out when to take the first Input Keyboard Chord for replace or insert

        intake_ish = False

        if chords and intake_func:
            if chords == b"\x0A":  # LF, ⌃J, 10

                intake_ish = True

            elif chords in intake_chords_set:

                intake_ish = True

            elif all((_ not in C0_CONTROL_STDINS) for _ in chords):
                if keyboard_intake_ish:

                    intake_ish = True

                elif chars_intake_ish:
                    if intake_taken or (chords not in funcs.keys()):

                        intake_ish = True

        # Ask first for one Chord

        chords_func = None
        if chords:

            # Take simple Chords as Input Chars on demand

            chords_func = intake_func
            if not intake_ish:

                # Accept Chords that do name Funcs

                chords_func = self.do_raise_name_error
                if chords in funcs.keys():

                    chords_func = funcs[chords]

        return chords_func

    def call_chords_func(self, chords_func):  # TODO  # noqa C901 too complex
        """Call the Func once or more, in reply to one Terminal Nudge In"""

        after_func = self.after_func

        skin = self.skin
        doing_funcs = skin.doing_funcs

        # Setup before first calling the Func
        # TODO: rewrite this work as a chain of 'enter_do_func's

        skin.doing_done = 0

        skin.doing_less = True

        if doing_funcs and (doing_funcs[-1] is not chords_func):
            doing_funcs[::] = list()
        doing_funcs.append(chords_func)

        # Call the Func once or more

        while True:
            skin.doing_more = None

            # Call the Func, for the first time or again
            # Forget any Python Traceback older than the Func after the Func exits

            try:

                try:
                    chords_func()
                    pin = self.spot_pin()
                finally:
                    self.keep_cursor_on_file()

            except Exception:  # do Not finally catch SystemExit, KeyboardInterrupt
                skin.traceback = skin.doing_traceback
                skin.doing_traceback = None

                self.after_func = None

                raise

            skin.traceback = skin.doing_traceback
            skin.doing_traceback = None

            # Raise an Exception when the Func has gone egregiously wrong

            self.raise_blame_for_chords_func(pin)

            # Let the Func take the Arg as a Count of Repetitions, but don't force it

            if skin.doing_more:
                skin.doing_done += 1
                if skin.doing_done < self.get_arg1_int():

                    # Raise KeyboardInterrupt at ⌃C

                    chord = self.peek_one_editor_chord()
                    if chord == b"\x03":  # ETX, ⌃C, 3

                        raise KeyboardInterrupt()

                    skin.reply = TerminalReplyOut()  # clear pending Status

                    continue

            break

        # Do call for work after calling Chords, but then stop this call for work

        if after_func and (self.after_func is after_func):

            self.after_func()

            self.after_func = None

    def close_keyboard_intake(self):
        """Shut down the Keyboard Intake Bypass, or the Counting of Keyboard Intake"""

        column = self.column
        row = self.row
        skin = self.skin

        keyboard = skin.keyboard

        # Clear the Keyboard Bypass

        if keyboard.intake_bypass:

            assert not self.intake_beyond

            self.intake_beyond = keyboard.intake_bypass
            keyboard.intake_bypass = ""

            # Restore the Cursor Style

            if self.intake_beyond == "inserting":
                skin.cursor_style = _INSERT_CURSOR_STYLE_
            else:
                assert self.intake_beyond == "replacing"
                skin.cursor_style = _REPLACE_CURSOR_STYLE_

            # Restore the choice of Column

            row_max_column = self.spot_max_column(row=row)
            if column == (row_max_column - 1):
                if self.intake_column == row_max_column:

                    self.column += 1

            self.intake_column = None

            return

        # Clear the changes counted while taking commands to View, not Replace/ Insert

        if not self.intake_beyond:
            self.intake_pins[:] = list()

    def raise_blame_for_chords_func(self, pin):
        """Raise an Exception when the Func has gone egregiously wrong"""

        # Blame the Func when Cursor slips off File

        if self.spot_pin() != pin:

            raise KwArgsException(before=tuple(pin), after=tuple(self.spot_pin()))

        # Blame the Func when Repeat Count given but Not taken

        if self.skin.doing_less:
            self.check_repeat_count()

    def check_repeat_count(self):
        """Raise the Arg 0 and its Arg 1 Repeat Count as a NotImplementedError"""

        nudge = self.skin.nudge

        arg1_int = self.get_arg1_int(default=None)
        if arg1_int is not None:
            exc_arg = "{} Repeat Count".format(nudge.to_chars())

            raise NotImplementedError(exc_arg)

        # Vi Py raises not-implemented Repeat Count Prefixes
        # Vim quirkily loses not-implemented Repeat Count Prefixes

        # Em Py raises not-implemented ⌃U - as ⌃U -1, and ⌃U ⌃U as ⌃U 16, and so on
        # Emacs quirkily loses not-implemented ⌃U args at ⌃J, ⌃S, ⌃R, ⌃Z, etc

    def keep_cursor_on_file(self):
        """Fail faster, like when some Bug shoves the Cursor off of Buffer of File"""

        row = self.row
        rows = self.count_rows_in_file()
        if not rows:
            row = 0
        elif row < 0:
            row = 0
        elif row >= rows:
            row = rows - 1

        column = self.column
        max_column = self.spot_max_column(row=row)
        if column < 0:
            column = 0
        elif column > max_column:
            column = max_column

        self.row = row
        self.column = column

    #
    # Take the Args as given, or substitute a Default Arg Value
    #

    def get_arg0_chars(self):
        """Get the Bytes of the Input Chords"""

        chords = self.skin.arg0_chords
        assert chords is not None

        chars = chords.decode(errors="surrogateescape")

        return chars

    def get_arg1_int(self, default=1):
        """Get the Int of the Prefix Digits before the Chords, else the Default Int"""

        took = self.skin.arg1
        took_int = default if (took is None) else took

        self.skin.doing_less = False

        return took_int

    def get_arg2_chars(self):
        """Get the Bytes of the Suffix supplied after the Input Chords"""

        chords = self.skin.arg2_chars
        assert chords is not None

        return chords

    def continue_do_loop(self):
        """Ask to run again, like to run for a total of 'self.skin.arg1' times"""

        assert self.skin.doing_more is None, self.skin.doing_more

        self.skin.doing_less = False
        self.skin.doing_more = True

    #
    # Keep hold of the one Reply to send out, & take input keyboard Chords in
    #

    def editor_print(self, *args):
        """Capture some Status now, to show with next Prompt"""

        message = " ".join(str(_) for _ in args)

        old_message = self.skin.reply.message
        assert not (old_message and message), (old_message, message)

        self.skin.reply.message = message

    def reply_with_finding(self):
        """Show Search Flags a la Bash Grep Switches"""

        letters = ""
        if not self.finding_regex:
            letters += "F"
        if not self.finding_case:
            letters += "i"
        if self.showing_line_number:
            letters += "n"

        flags = "-{}".format(letters) if letters else ""

        self.skin.reply.flags = flags

    def reply_with_nudge(self):
        """Capture the Nudge In to echo, as part of the next Reply Out"""

        self.skin.reply.nudge = self.skin.nudge

    def reply_with_bell(self):
        """Ring the Terminal Bell as part of the next Prompt"""

        self.skin.reply.bell = True

    def take_one_chord_cluster(self):
        """Block Self till next Cluster of keyboard input Chords"""

        chords = self.take_one_editor_chord()
        if chords == b"\x1B":  # ESC, ⌃[, 27
            peeked = self.peek_one_editor_chord()
            if peeked is not None:  # Vim ⌥← b"b"  # Vim ⌥→ b"f"
                chords += self.take_one_editor_chord()

        return chords

    def peek_one_editor_chord(self):
        """Reveal the next keyboard input Chord"""

        chord_ints_ahead = self.skin.chord_ints_ahead
        painter = self.painter

        # Return a copy of the first deferred Chord

        if chord_ints_ahead:

            chord_int = chord_ints_ahead[0]  # copy, do Not consume
            chord = chr(chord_int).encode()

            return chord

        # Give up now, if no input available

        if not self.driver.kbhit(timeout=0):

            return None

        # Consume the Chord and raise KeyboardInterrupt, if it is ETX, ⌃C, 3

        if self.showing_lag is None:
            self.keep_busy(reply=self.skin.reply)  # give 1 Time Slice for this Chord

        chords = painter.take_painter_chord()

        # Else defer this first keyboard input Chord for later, but return a copy now

        for chord_int in chords:
            chord_ints_ahead.insert(0, chord_int)

        chord = chords[:1]  # copy, do Not consume

        return chord

    def take_one_editor_chord(self):
        """Block Self till next keyboard input Chord"""

        chord_ints_ahead = self.skin.chord_ints_ahead
        painter = self.painter

        # Consume the Reply

        stale_reply = self.skin.reply

        self.skin.reply = TerminalReplyOut()
        self.reply_with_nudge()

        # Consume one deferred Chord and return it

        if chord_ints_ahead:

            chord_int = chord_ints_ahead.pop(0)  # consume, do Not copy
            chord = chr(chord_int).encode(errors="surrogateescape")

            return chord

        # Block to take and return the next keyboard input Chord,
        # except do give >=1 Time Slices per Chord

        if self.showing_lag is None:
            while True:
                self.keep_busy(reply=stale_reply)
                if self.driver.kbhit(timeout=0.250):

                    break

        chord = painter.take_painter_chord()

        return chord

    #
    # Focus on one Line of a File of Lines
    #

    def charsets_find_column(self, charsets):
        """Return the Index of the first CharSet containing Column Char, else -1"""

        chars = self.fetch_column_char(default=" ")

        for (index, charset) in enumerate(charsets):
            if chars in charset:

                return index

        return -1

    def count_columns_in_row(self, row=None):
        """Count Columns in Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_lines = self.ended_lines
        if not ended_lines:

            return 0

        if row_ >= len(ended_lines):

            raise IndexError(row)

        ended_line = ended_lines[row_]
        line = str_remove_line_end(ended_line)

        columns = len(line)

        return columns

    def count_rows_in_file(self):
        """Count Rows in Buffer of File"""

        rows = len(self.ended_lines)

        return rows

    def fetch_column_char(self, column=None, default=" "):
        """Get the one Char at the Column in the Row beneath the Cursor"""

        if self.ended_lines:

            column_ = self.column if (column is None) else column

            ended_line = self.ended_lines[self.row]
            line = str_remove_line_end(ended_line)

            if column_ < len(line):

                ch = line[column_]

                return ch

        return default

    def fetch_row_line(self, row=None):
        """Get Chars of Columns in Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_line = self.ended_lines[row_] if self.ended_lines else _EOL_
        line = str_remove_line_end(ended_line)

        return line

    def fetch_row_line_end(self, row=None):
        """Get the Line Ending of the Row beneath Cursor"""

        row_ = self.row if (row is None) else row

        ended_line = self.ended_lines[row_] if self.ended_lines else _EOL_
        line = str_remove_line_end(ended_line)
        line_end = ended_line[len(line) :]

        return line_end

    def spot_bottom_row(self, top_row=None):
        """Spot the Bottom Row of File on Screen"""

        top_row_ = self.top_row if (top_row is None) else top_row
        painter = self.painter

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        bottom_row = top_row_ + (painter.scrolling_rows - 1)
        bottom_row = min(bottom_row, last_row)

        return bottom_row

    def spot_first_pin(self):
        """Spot the First Char of File, else as if it were a File of 1 Char"""
        # pylint: disable=no-self-use

        first_pin = TerminalPin(0, column=0)

        return first_pin

    def spot_pin(self):
        """Spot the Char of File beneath the Cursor of File"""

        pin = TerminalPin(self.row, column=self.column)

        return pin

    def spot_pin_plus(self, obj):
        """Spot the Char of File beneath the Cursor of File"""

        pin_plus = TerminalPinPlus(self.row, column=self.column, obj=obj)

        return pin_plus

    def spot_last_pin(self):
        """Spot the last Char of File, else as if it were a File of 1 Char"""

        last_row = self.spot_last_row()
        last_column = self.spot_last_column()
        last_pin = TerminalPin(last_row, column=last_column)

        return last_pin

    def spot_last_row(self):
        """Find the last Row in File, else as if it were a File of 1 Char"""

        rows = len(self.ended_lines)
        last_row = (rows - 1) if rows else 0

        return last_row

    def spot_max_column(self, row=None):
        """Spot the last Column in Row, else one beyond while inserting/ replacing"""

        if self.intake_beyond or self.skin.keyboard.intake_bypass:
            max_column = self.count_columns_in_row(row=row)
        else:
            max_column = self.spot_last_column(row=row)

        return max_column

    def spot_last_column(self, row=None):
        """Find the last Column in Row, else as if it were a File of 1 Char"""

        row_ = self.row if (row is None) else row

        ended_lines = self.ended_lines
        if not ended_lines:

            return 0

        if row_ >= len(ended_lines):

            raise IndexError(row)

        ended_line = ended_lines[row_]
        line = str_remove_line_end(ended_line)

        columns = len(line)
        last_column = (columns - 1) if columns else 0

        return last_column

    def spot_middle_row(self):
        """Find the Middle Row on Screen, of the Rows that carry Lines of File"""

        top_row = self.top_row
        bottom_row = self.spot_bottom_row()
        rows_on_screen = bottom_row - top_row + 1

        half_screen = rows_on_screen // 2  # for Vim Z ., Vim ⇧M, Emacs ⌃L, Emacs ⌥R
        middle_row = top_row + half_screen

        return middle_row

    #
    # Define Chords common to many TerminalEditor's
    #

    def do_little(self):
        """Accept worthless Keyboard Input without doing much of anything with it"""

        _ = self.get_arg1_int()

        self.editor_print("Cancelled input")  # 123⌃C Egg, f⌃C Egg, etcA

    def do_raise_name_error(self):  # Vim Z⇧Z  # Emacs ⌃X⌃G  # etc
        """Reply to meaningless Keyboard Input"""

        nudge = TerminalNudgeIn(self.skin.nudge)
        nudge.prefix = None

        if wearing_em():
            raise EmPyNameError()

        raise ViPyNameError()

    def do_redraw(self):  # Vim ⌃L
        """Toggle between more and less Lag"""

        lag_plus = self.get_arg1_int(default=None)
        lag = None if (lag_plus is None) else ((lag_plus - 1) / 1e6)
        lag = 0 if (lag == 0) else lag  # echo 0 as '0', not as '0.0'

        self.showing_lag = lag

        if lag is None:
            self.editor_print(":set no_lag_")
        else:
            self.editor_print(":set _lag_={}".format(lag))

        self.reopen_terminal()  # for redraw

        # Vi Py ⌃L does work in the absence of Redraw bugs
        # Vim ⌃L Quirk just adds lag, each time it's called

    def do_suspend_frame(self):  # Vim ⌃Zfg
        """Don't save changes now, do stop Vi Py process, till like Bash 'fg'"""

        painter = self.painter

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        painter.__exit__(*exc_info)
        os.kill(os.getpid(), signal.SIGTSTP)
        painter.__enter__()

    def do_sys_exit(self):  # Ex Return
        """Stop taking more Keyboard Input"""
        # pylint: disable=no-self-use

        sys.exit()

    def do_set_invnumber(self):  # Vi Py \N Egg
        """Show Line Numbers or not, but without rerunning Search"""

        self.showing_line_number = not self.showing_line_number

        if wearing_em():
            if self.showing_line_number:
                self.editor_print("⌃U ⌥X display-line-numbers-mode ⌥X linum-mode")
            else:
                self.editor_print("⌃U - ⌥X display-line-numbers-mode ⌥X linum-mode")
        else:
            if self.showing_line_number:
                self.editor_print(":set number")
            else:
                self.editor_print(":set nonumber")

    #
    # Move Cursor and scroll Lines
    #

    def step_for_count_slip_to_dent(self, default):
        """Step to chosen Row, else to default Row, and slip past Dent"""

        last_row = self.spot_last_row()

        count = self.get_arg1_int(default=default)
        row = min(last_row, count - 1)

        self.row = row
        self.slip_dent()

    def slip_dent(self):
        """Leap to the Column after the Indent"""

        line = self.fetch_row_line()
        lstripped = line.lstrip()
        column = len(line) - len(lstripped)

        self.column = column

    def scroll_till_top(self):
        """Scroll up or down till Cursor Row lands in Top Row of Screen"""

        self.top_row = self.row

        self.editor_print("scrolled the Row to the Top")

    def scroll_till_middle(self):
        """Scroll up or down till Cursor Row lands in Middle Row of Screen"""

        painter = self.painter
        row = self.row

        scrolling_rows = painter.scrolling_rows
        assert scrolling_rows
        half_screen = scrolling_rows // 2

        up = half_screen
        top_row = (row - up) if (row >= up) else 0

        self.top_row = top_row

        if row < half_screen:
            self.editor_print("scrolled the Row to above the Middle")
        else:
            self.editor_print("scrolled the Row to the Middle")

    def scroll_till_bottom(self):
        """Scroll up or down till Cursor Row lands in Bottom Row of Screen"""

        row = self.row
        painter = self.painter

        scrolling_rows = painter.scrolling_rows
        assert scrolling_rows

        up = scrolling_rows - 1
        top_row = (row - up) if (row >= up) else 0

        self.top_row = top_row

        if row < (scrolling_rows - 1):
            self.editor_print("scrolled the Row to above the Bottom")
        else:
            self.editor_print("scrolled the Row to the Bottom")

    #
    # Find Spans of Chars
    #

    def do_set_invignorecase(self):  # Vi Py \I Egg
        """Search Upper/Lower Case or not"""

        self.finding_case = not self.finding_case

        self.reopen_found_spans()

        if self.finding_case:
            self.editor_print(":set noignorecase")
        else:
            self.editor_print(":set ignorecase")

    def do_set_invregex(self):  # Vi Py \⇧F Egg
        """Search as Regex or search as Chars"""

        self.finding_regex = not self.finding_regex

        self.reopen_found_spans()

        if self.finding_regex:
            self.editor_print(":set regex")  # kin to Vim default
        else:
            self.editor_print(":set noregex")  # doesn't exist in Vim

    def reopen_found_spans(self):
        """Find Chars in File"""

        iobytespans = self.iobytespans

        iochars = self.held_file.decode_file()

        # Cancel the old Spans

        iobytespans.clear()

        # Find the New Spans

        self.finding_highlights = None
        if self.finding_line is not None:
            self.finding_highlights = True

            pattern = self.finding_line
            if not self.finding_regex:
                pattern = re.escape(pattern)

            flags = 0
            flags |= re.MULTILINE
            if not self.finding_case:
                flags |= re.IGNORECASE

            matches = list(re.finditer(pattern, string=iochars, flags=flags))
            iobytespans[::] = TerminalSpan.find_spans(matches)

            if matches:  # as many Spans as Matches, except for such as r"$" in "abc\n"
                assert iobytespans
                assert len(iobytespans) in (len(matches), len(matches) - 1)

    def print_some_found_spans(self, stale_status):
        """Print as many of the Found Spans as fit on screen"""
        # pylint: disable=too-many-locals

        ended_lines = self.ended_lines
        iobytespans = self.iobytespans
        keyboard = self.skin.keyboard
        painter = self.painter
        reply = self.skin.reply
        shadow = self.shadow
        showing_line_number = self.showing_line_number

        assert iobytespans

        model_line_number = 1 + len(ended_lines)
        str_model_line_number = "{:3} ".format(model_line_number)  # TODO: em
        model_width = len(str_model_line_number)

        # Scroll up the Status Line

        painter.terminal_print()  # could reprint 'stale_status'

        # Visit each Span

        printed_row = None
        for span in iobytespans:

            (found_row, _, _) = span

            line_number = 1 + found_row
            str_line_number = ""  # TODO: merge with 'format_as_line_number'
            if showing_line_number:
                str_line_number = "{:3} ".format(line_number).rjust(model_width)

            line = self.fetch_row_line(row=found_row)

            # Print each Line of Spans only once

            if found_row != printed_row:
                printed_row = found_row

                painter.terminal_print(str_line_number + line)  # may wrap rows

        # Recover the Status Line destroyed by scrolling inside of 'terminal_print'

        if painter.terminal == shadow:
            if shadow.scroll > painter.scrolling_rows:
                assert shadow.row == painter.status_row
                assert shadow.column == 0

                painter.terminal_write_scrolled_status(
                    shadow.spot_shadow_pin(), status=stale_status
                )

        # Prompt for next keyboard input Chord, and block till it arrives

        self.editor_print(  # "{}/{} Press Return or ⌃C to continue . . .
            "{}/{} Press Return or ⌃C to continue . . .".format(
                len(iobytespans), len(iobytespans)
            )
        )

        fresh_status = keyboard.format_status_func(reply)

        painter.terminal_print(fresh_status, end=" ")
        self.driver.flush()

        try:
            _ = self.take_one_chord_cluster()
        except KeyboardInterrupt:
            pass  # take ⌃C as Return here

        self.reopen_terminal()  # after 'painter.terminal_print'

        # TODO: highlight Matches in :g/ Lines
        # TODO: Vim prints more through a Less-like Paginator

    def find_ahead_and_reply(self):  # pylint: disable=inconsistent-return-statements
        """Find the Search Key ahead, else after start, else fail silently"""
        # pylint: disable=too-many-locals

        rep_line = self.format_finding_line()
        spans = self.iobytespans

        # Find none

        if not spans:
            self.editor_print("No chars found as:  {}".format(rep_line))

            return

        # Find one or more, ahead, else after start

        self.finding_highlights = True

        here0 = self.spot_pin()
        here1 = TerminalPin(row=-1, column=-1)  # before any Pin of File
        heres = (here0, here1)

        vague_how0 = "{}/{}  Found {} chars ahead as:  {}"
        vague_how1 = "{}/{}  Found {} chars after start, none found ahead, as:  {}"
        vague_hows = (vague_how0, vague_how1)

        for (here, vague_how) in zip(heres, vague_hows):
            for (index, span) in enumerate(spans):
                len_chars = span.beyond - span.column
                there = self.span_to_pin_on_char(span)

                if here < there:

                    how = vague_how
                    if len(spans) == 1:  # so often 'there == here0', but not always
                        how = "{}/{}  Found {} chars, only here, as {}"

                    self.editor_print(  # "{}/{}  Found ...
                        how.format(1 + index, len(spans), len_chars, rep_line)
                    )

                    if "none found" in how:
                        self.reply_with_bell()

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def find_behind_and_reply(self):  # pylint: disable=inconsistent-return-statements
        """Find the Search Key loudly: behind, else before end, else not"""
        # pylint: disable=too-many-locals

        rep_line = self.format_finding_line()
        rows = self.count_rows_in_file()
        spans = self.iobytespans

        # Find none

        if not spans:
            self.editor_print("No chars found as: {}".format(rep_line))

            return

        # Find one or more, behind, else before end

        self.finding_highlights = True

        here0 = self.spot_pin()
        here1 = TerminalPin(row=rows, column=0)  # after any Pin of File
        heres = (here0, here1)

        vague_how0 = "{}/{}  Found {} chars behind as:  {}"
        vague_how1 = "{}/{}  Found {} chars before end, none found behind, as:  {}"
        vague_hows = (vague_how0, vague_how1)

        for (here, vague_how) in zip(heres, vague_hows):
            for (reverse_index, span) in enumerate(reversed(spans)):
                index = len(spans) - 1 - reverse_index
                len_chars = span.beyond - span.column
                there = self.span_to_pin_on_char(span)

                if there < here:

                    how = vague_how
                    if len(spans) == 1:  # so often 'there == here0', but not always
                        how = "{}/{}  Found {} chars, only here, as:  {}"

                    self.editor_print(  # "{}/{}  Found ...
                        how.format(1 + index, len(spans), len_chars, rep_line)
                    )

                    if "none found" in how:
                        self.reply_with_bell()

                    (self.row, self.column) = there

                    return True

        assert False, spans  # unreached

    def format_finding_line(self):
        """Echo the Search Key"""

        line = self.finding_line

        if self.finding_regex:
            rep_line = "r'{}'".format(line)
        elif self.finding_case:
            rep_line = repr(line)
        else:
            rep_line = line

        return rep_line

    def span_to_pin_on_char(self, span):
        """Find the Row:Column in Chars of File nearest to a Span"""

        there_row = span.row

        row_max_column = self.spot_max_column(row=there_row)
        there_column = min(row_max_column, span.column)

        there = TerminalPin(row=there_row, column=there_column)

        return there

    #
    # Replace Lines, replace Chars, insert Lines, insert Chars
    #

    def replace_some_chars(self, chars):
        """Replace some Chars inside a Line, or an empty Line"""

        ended_lines = self.ended_lines
        column = self.column
        row = self.row

        columns = self.count_columns_in_row()
        column_plus = column + 1

        # Fall back to insert the Fresh Char, if there is no Stale Char to delete

        if column >= columns:

            self.insert_some_chars(chars=chars)  # insert as fallen back from replacing

        # Delete one Char to insert one Char

        else:

            (head, _, ended_tail) = self.split_row_line_for_chars(chars)
            ended_lines[row] = head + chars + ended_tail[1:]

            self.column = column_plus

    def insert_some_chars(self, chars):
        """Insert some Chars inside a Line"""

        assert str_remove_line_end(chars) == chars

        ended_lines = self.ended_lines
        column = self.column
        row = self.row

        (head, _, ended_tail) = self.split_row_line_for_chars(chars)
        if not ended_lines:
            ended_lines[:] = [""]
        ended_lines[row] = head + chars + ended_tail

        self.column = column + 1

    def insert_one_line(self):
        """Insert an empty Line, and land the Cursor in it"""

        ended_lines = self.ended_lines
        row = self.row
        row_plus = row + 1

        (_, ended_head, ended_tail) = self.split_row_line_for_chars(chars=None)
        if ended_lines:
            ended_lines[row] = ended_head
        ended_lines.insert(row_plus, ended_tail)

        self.row = row_plus if ended_lines else 0
        self.column = 0

    def delete_some_chars(self, count):
        """Count and delete between 0 and N chars"""

        ended_lines = self.ended_lines
        row = self.row

        (head, _, ended_tail) = self.split_row_line_for_chars(chars=None)
        tail = str_remove_line_end(ended_tail)
        line_end = ended_tail[len(tail) :]  # may be empty

        if not count:

            return 0

        chars_dropped = tail[:count]

        pin_plus = self.spot_pin_plus(chars_dropped)
        self.intake_pins[-1] = pin_plus  # ugly

        chopped_tail = tail[count:]

        if ended_lines:
            ended_lines[row] = head + chopped_tail + line_end

        touches = len(chars_dropped)

        return touches

    def delete_some_lines(self, count):
        """Count and delete between 0 and N Lines at this Row"""

        ended_lines = self.ended_lines
        row = self.row
        rows = self.count_rows_in_file()

        # Fall back to delete 0 Rows

        if row >= rows:

            return 0

        # Delete between 1 and N Lines

        row_below = min(rows, row + count)
        ended_lines[row:] = ended_lines[row_below:]

        touches = row_below - row

        # Recover from deleting the Line beneath the Cursor

        row_rows = self.count_rows_in_file()
        if row >= row_rows:
            assert row == row_rows

            if row_rows:
                self.row = row_rows - 1

        return touches

    def join_some_lines(self, joinings):
        """Join N Lines to this Line, as if dented by single Spaces"""

        ended_lines = self.ended_lines

        for _ in range(joinings):
            row = self.row
            row_below = row + 1
            rows = self.count_rows_in_file()

            assert row_below <= rows

            # Leap just beyond End of Line

            columns = self.count_columns_in_row(row=row)
            self.column = columns

            # Copy the next Line into this Line, as if dented by a single Space

            ended_line = ended_lines[row]
            line = str_remove_line_end(ended_line)
            sep = " " if (line and (line.rstrip() == line)) else ""

            ended_line_below = ended_lines[row_below]
            line_below = str_remove_line_end(ended_line_below)
            line_end_below = ended_line_below[len(line_below) :]

            # Delete the copied Line

            ended_lines[row:] = ended_lines[row_below:]
            ended_lines[row] = line + sep + line_below.lstrip() + line_end_below

        return joinings

    def split_row_line_for_chars(self, chars):
        """Split this Line to replace or insert Char or Line, and remember where"""

        ended_lines = self.ended_lines
        row = self.row
        column = self.column

        pin_plus = self.spot_pin_plus(chars)
        self.intake_pins.append(pin_plus)

        ended_line = ended_lines[row] if ended_lines else _EOL_

        (head, ended_tail) = (ended_line[:column], ended_line[column:])
        ended_head = head + "\n"

        return (head, ended_head, ended_tail)

    def format_touch_count(self):
        """Describe the list of Touched Pins"""

        pins = self.intake_pins

        if not pins:
            rep = "0 chars"
        else:

            line_pins = list(_ for _ in pins if _.obj is None)
            char_pins = list(_ for _ in pins if _.obj is not None)

            assert line_pins or char_pins

            if not line_pins:
                rep = "{} chars".format(len(pins))
            elif not char_pins:
                rep = "{} lines".format(len(pins))
            else:
                char_rows = len(set(_.row for _ in char_pins))
                if char_rows == 1:
                    rep = "{} chars in 1 line".format(len(char_pins))
                else:
                    rep = "{} chars across {} lines".format(len(char_pins), char_rows)

        return rep


#
# Stack the I/O of a Terminal
# as TerminalPainter > TerminalShadow > TerminalDriver
#


class TerminalPainter:
    """Paint a Screen of Rows of Chars"""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, terminal):

        self.terminal = terminal  # layer over a TerminalShadow

        self.rows = None  # count Rows on Screen
        self.columns = None  # count Columns per Row

        self.scrolling_rows = None  # count Scrolling Rows at top of Screen
        self.status_row = None  # index the 1 Status Row at bottom of Screen

        self.top_line_number = 1  # number the Scrolling Rows down from First of Screen
        self.model_line_number = 1  # right-justify the Line Numbers
        self.painting_line_number = None  # number the Scrolling Rows visibly, or not

        # TODO: all = None in TerminalPainter.__init__

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        if self.rows is None:
            self.terminal.__enter__()
            self.reopen_terminal()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        rows = self.rows
        terminal = self.terminal

        if rows is not None:
            self.rows = None
            self.columns = None  # TODO: think into how much TerminalPainter to wipe

            terminal.__exit__(exc_type, exc_value, exc_traceback)  # pos args

    def reopen_terminal(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        size = terminal.reopen_terminal()  # a la os.get_terminal_size(fd)

        (columns, rows) = (size.columns, size.lines)
        assert rows
        assert columns
        self.rows = rows
        self.columns = columns

        self.scrolling_rows = rows - 1  # reserve last 1 line for Status
        self.status_row = self.scrolling_rows

        return size

    def pdb_set_trace(self):
        """Visit Pdb, if Stdin is Tty, else raise 'bdb.BdbQuit'"""

        exc_info = (None, None, None)  # commonly equal to 'sys.exc_info()' here
        self.__exit__(*exc_info)
        pdb.set_trace()  # pylint: disable=forgotten-debug-statement
        self.__enter__()

    def flush_painter(self):
        """Stop waiting for more Writes from above"""

        self.terminal.flush()

    def take_painter_chord(self):
        """Block till TerminalDriver 'kbhit', to return next Keyboard Input"""

        chord = self.terminal.getch()

        return chord

    def terminal_print(self, *args, end="\r\n"):
        """Bypass the cache here:  Write line, slip to next, and scroll up if need be"""

        line = " ".join(str(_) for _ in args)
        self.terminal_write(line + end)

    def terminal_write(self, chars):
        """Bypass the cache here:  Write the Chars immediately, precisely as given"""

        self.terminal.write(chars)

    def terminal_write_scrolled_status(self, pin, status):
        """Repaint a copy of the Status Line, as if scrolled to top of Screen"""

        erased_line = self.columns * " "

        self.terminal_write(CUP_1_1)
        self.terminal_write(erased_line)

        self.terminal_write(CUP_1_1)
        self.terminal_write(status[: (self.columns - 1)])

        y = 1 + pin.row
        x = 1 + pin.column
        self.terminal_write(CUP_Y_X.format(y, x))

    def paint_screen(self, ended_lines, spans, status, cursor_style, cursor, bell):
        """Write over the Rows of Chars on Screen"""
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals

        (row, column) = self.spot_nearby_cursor(cursor.row, column=cursor.column)

        columns = self.columns
        terminal = self.terminal

        # Fill the Screen with Lines of "~" past the last Line of File

        viewing = cursor_style == _VIEW_CURSOR_STYLE_
        lines = self._format_screen_lines(ended_lines, viewing)

        # Write the formatted chars

        terminal.write(ED_2)
        terminal.write(CUP_1_1)

        for (index, line) in enumerate(lines):
            (styled, line_plus) = self.style_line(
                index, line=line, cursor=cursor, spans=spans
            )
            if len(line_plus) < columns:
                terminal.write(styled + "\r\n")
            else:
                terminal.write(styled)  # depend on automagic "\r\n" after Last Column

        # Show status, inside the last Row
        # but don't write over the Lower Right Char  # TODO: test vs xterm autoscroll

        str_status = "" if (status is None) else str(status)

        status_columns = columns - 1
        status_line = str_status[:status_columns].ljust(status_columns)
        for chord in sorted(C0_CONTROL_STDINS):
            if chord.decode() in status_line:

                status_line = repr(status_line)[:status_columns].ljust(status_columns)

                assert False, status_line  # unreached

                break

        terminal.write(status_line)

        # Style the cursor

        if cursor_style is not None:
            terminal.write(cursor_style)

        # Place the cursor

        y = 1 + row
        x = 1 + column
        terminal.write(CUP_Y_X.format(y, x))

        # Ring the bell

        if bell:
            terminal.write("\a")

        # Vi Py ends with . ~ ~ ~ ... when the File ends without a Line-End
        # Vim quirkily shows the last Lines the same, no matter ended by Line-End

        # TODO: invent ways for Vi Py and Em Py to edit the Line-End's

    def _format_screen_lines(self, ended_lines, viewing):
        """Choose a Screen of Lines to show many Columns of these Ended Lines"""

        columns = self.columns
        scrolling_rows = self.scrolling_rows

        # Drop the Line End's

        bare_lines = list(str_remove_line_end(_) for _ in ended_lines)

        # Pick out the Vi Py case of inserting or replacing into an Empty File
        # and lead with an empty Filler Line in that case

        if not bare_lines:
            if not viewing:
                if not wearing_em():
                    bare_lines.append("")

        # Number the Scrolling Lines of the Screen

        lines = list()
        for (index, bare_line) in enumerate(bare_lines):
            str_line_number = self.format_as_line_number(index)
            line = (str_line_number + bare_line)[:columns]
            lines.append(line)

        # Pick out the Vi Py case of a File whose Last Line has no Line End,
        # and lead with a Filler Line of a single "." Dot in that case

        if len(lines) < scrolling_rows:
            if lines_last_has_no_end(ended_lines):
                if not wearing_em():
                    lines.append(".")

        # Complete the screen, with "~" for Vi Py or with "" for Em Py

        while len(lines) < scrolling_rows:
            if wearing_em():
                lines.append("")
            else:
                lines.append("~")

                # Vi Py shows an empty File as occupying no space
                # Vim Quirk presents empty File same as a File of 1 Blank Line

        # Assert Screen completed

        assert len(lines) == scrolling_rows, (len(lines), scrolling_rows)

        return lines

    def spot_nearby_cursor(self, row, column):
        """Choose a Row:Column to stand for a Row:Column on or off Screen"""

        columns = self.columns
        scrolling_rows = self.scrolling_rows
        rows = self.rows

        assert rows
        assert columns

        found_row = min(rows - 1, row)

        left_column = self.spot_left_column() if (row < scrolling_rows) else 0
        found_column = min(columns - 1, left_column + column)

        return (found_row, found_column)

    def spot_left_column(self):
        """Find the leftmost Column occupied by the Chars of the Scrolling Lines"""

        formatted = self.format_as_line_number(row=0)
        left_column = len(formatted)

        return left_column

    def format_as_line_number(self, row):
        """Format a Row Index on Screen as a Line Number of File"""

        if not self.painting_line_number:

            return ""

        str_model_line_number = "{:3} ".format(self.model_line_number)
        if wearing_em():
            str_model_line_number = " {} ".format(self.model_line_number)
        last_width = len(str_model_line_number)

        line_number = self.top_line_number + row
        formatted = "{:3} ".format(line_number).rjust(last_width)
        if wearing_em():
            formatted = " {} ".format(line_number).rjust(last_width)

        return formatted

    def style_line(self, row, line, cursor, spans):
        """Inject kinds of SGR so as to style the Chars of a Row"""
        # pylint: disable=too-many-locals

        # Work only inside this Row

        (spans0, line_plus) = self.spread_spans(row, line=line, spans=spans)

        # Add a one Char Span at the Cursor
        # to show SGR_N in placed of DECSCUSR_N for styling the Cursor

        spans1 = list(spans0)
        if False:  # pylint: disable=using-constant-test
            if row == cursor.row:
                cursor_span = TerminalSpan(
                    row=cursor.row, column=cursor.column, beyond=(cursor.column + 1)
                )
                spans1.append(cursor_span)
                spans1.sort()

        # Add one Empty Span beyond the end

        beyond = len(line_plus)
        empty_beyond_span = TerminalSpan(row, column=beyond, beyond=beyond)

        spans2 = list(spans1)
        spans2.append(empty_beyond_span)

        # Visit the Chars between each pair of Spans, and the Chars of the Spans

        visited = 0
        opened = False

        styled = ""
        for span in spans2:

            # Write the Chars before this Span, as Highlight never opened or as closed

            if visited < span.column:

                fragment = line_plus[visited : span.column]

                styled += _LIT_CLOSE_ if opened else ""
                styled += fragment

                opened = False
                visited = span.column

            # Write the Chars of this Span, as Highlight opened

            if span.column < span.beyond:

                fragment = line_plus[span.column : span.beyond]

                styled += "" if opened else _LIT_OPEN_
                styled += fragment

                opened = True
                visited = span.beyond

        # Close the last opened Highlight, if it exists

        styled += _LIT_CLOSE_ if opened else ""

        return (styled, line_plus)

    def spread_spans(self, row, line, spans):
        """Spread each Empty Span to cover one more Column beyond it"""
        # pylint: disable=too-many-locals

        columns = self.columns
        left_column = self.spot_left_column()

        assert len(line) <= columns, (len(line), columns)

        # Look only at the Columns on Screen of This Row

        row_spans = list()
        for span in spans:

            if span.row == row:
                column = left_column + span.column
                if column < columns:
                    beyond = min(columns, left_column + span.beyond)

                    row_span = TerminalSpan(row, column=column, beyond=beyond)
                    row_spans.append(row_span)

        # Visit each Empty Span

        for (index, span) in enumerate(row_spans):

            column = left_column + span.column
            beyond = left_column + span.beyond

            assert span.column <= span.beyond <= columns, (span, columns)

            if span.column == span.beyond:

                # Don't spread off Screen

                if span.column == columns:

                    continue

                # Don't spread into the next Span

                next_spans = row_spans[(index + 1) :]
                if next_spans:
                    next_span = next_spans[0]
                    if next_span.column == span.column:

                        continue

                # Else do spread to cover one Column

                column_plus = span.column + 1
                spread_span = TerminalSpan(row, column=span.column, beyond=column_plus)

                row_spans[index] = spread_span

        # Add one Space to grow the Line, when Span runs past End of Line

        len_line = len(line) if (not row_spans) else max(_.beyond for _ in row_spans)

        assert len_line <= columns, (len_line, columns)

        line_plus = line
        if len_line > len(line):

            line_plus = line + " "
            assert len_line == len(line_plus), (row, len_line, len(line_plus))

        # Succeed

        return (row_spans, line_plus)


class TerminalShadow:
    """Simulate a Terminal, to mostly write just the Diffs, to reduce Lag"""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, terminal):

        self.terminal = terminal

        self.rows = None  # count Rows on Screen
        self.columns = None  # count Columns per Row

        self.row = None  # place the Cursor in a Row of Screen, at Flush
        self.column = None  # place the Cursor in a Column of Screen, at Flush
        self.enter_cursor_style_chars = None  # change the Cursor Shape, at Enter
        self.exit_cursor_style_chars = None  # change the Cursor Shape, at Exit
        self.writing_bell_chars = None  # ring the Bell, at next Flush

        self.flushed_lines = list()  # don't rewrite Lines unchanged since last Flush
        self.held_lines = list()  # collect the Lines to rewrite at next Flush

        self.scroll = None  # count Terminal Lines scrolled by Writes

        # TODO: defer overriding default Terminal Cursor Style till first change

    def __enter__(self):
        """Connect Keyboard and switch Screen to XTerm Alt Screen"""

        enter_cursor_style_chars = self.enter_cursor_style_chars
        rows = self.rows
        terminal = self.terminal

        if rows is None:

            terminal.__enter__()
            self.reopen_terminal()

            if enter_cursor_style_chars:
                terminal.write(enter_cursor_style_chars)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        exit_cursor_style_chars = self.exit_cursor_style_chars
        rows = self.rows
        terminal = self.terminal

        if rows is not None:

            if exit_cursor_style_chars:
                terminal.write(self.exit_cursor_style_chars)

            self.rows = None
            self.columns = None  # TODO: think into how much TerminalShadow to wipe

            terminal.__exit__(exc_type, exc_value, exc_traceback)  # pos args

    def reopen_terminal(self):
        """Clear the Caches of this Terminal, here and below"""

        terminal = self.terminal

        # Count Rows x Columns below

        size = terminal.reopen_terminal()
        (columns, rows) = (size.columns, size.lines)

        # Size this Terminal to match the Terminal Below

        assert rows >= 1
        assert columns >= 1
        self.rows = rows
        self.columns = columns

        # Clear the Terminal Caches below

        terminal.write(ED_2)
        terminal.write(CUP_1_1)
        terminal.flush()

        # Clear the Terminal Cache here

        self.flushed_lines[::] = rows * [None]
        self.writing_bell_chars = None

        self.write(ED_2)
        self.write(CUP_1_1)

        self.scroll = 0

        return size

        # TODO: ugly to have enter_cursor_style_chars/ exit_cursor_style_chars endure?

        # TODO: deal with $LINES, $COLUMNS, and fallback,
        # TODO: like 'shutil.get_terminal_size' would

    def spot_shadow_pin(self):
        """Point to the Cursor on Screen"""

        pin = TerminalPin(self.row, column=self.column)

        return pin

    def flush(self):
        """Stop waiting for more Writes from above"""

        columns = self.columns
        enter_cursor_style_chars = self.enter_cursor_style_chars
        exit_cursor_style_chars = self.exit_cursor_style_chars
        flushed_lines = self.flushed_lines
        held_lines = self.held_lines
        rows = self.rows
        terminal = self.terminal
        writing_bell_chars = self.writing_bell_chars

        erased_line = columns * " "
        bottom_row = rows - 1

        # Visit each row, top down

        assert len(held_lines) == rows, (len(held_lines), rows)  # flush after ED_2

        terminal.write(CUP_1_1)

        for (row, held_line) in enumerate(held_lines):
            flushable_line = "\r\n" if (held_line is None) else held_line

            # If row written differently

            flushed_line = flushed_lines[row]
            if flushed_line != flushable_line:
                if row < bottom_row:

                    # Write a Scrolling Row above the Bottom Row

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(erased_line)

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(flushable_line.rstrip())

                else:

                    # Write the Bottom Row, but without closing it
                    # and without writing its Last Column

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(erased_line[:-1])

                    self.terminal_write_cursor_order(row, column=0)
                    terminal.write(flushable_line.rstrip())

                # Remember this Write, as if all Columns written

                flushed_lines[row] = flushable_line

        # Clear the Terminal Cache of Lines to write

        held_lines[::] = list()

        # Place the Terminal Cursor, and sometimes change the Cursor's Shape

        self.terminal_write_cursor_order(self.row, column=self.column)

        if enter_cursor_style_chars and not exit_cursor_style_chars:
            self.exit_cursor_style_chars = DECSCUSR

            terminal.write(enter_cursor_style_chars)

        # Ring the Terminal Bell below

        if writing_bell_chars:
            self.writing_bell_chars = None

            terminal.write(writing_bell_chars)

        # Flush the Terminal Writes below

        terminal.flush()

    def terminal_write_cursor_order(self, row, column):
        """Position the Terminal Cursor below, without telling this Shadow"""

        terminal = self.terminal

        y = 1 + row
        x = 1 + column
        terminal.write(CUP_Y_X.format(y, x))

    def getch(self):
        """Block till next keyboard input Chord"""

        chord = self.terminal.getch()

        return chord

    def write(self, chars):
        """Write into the Shadow now, write the Terminal Below at next Flush"""

        held_lines = self.held_lines
        column = self.column
        columns = self.columns
        rows = self.rows
        terminal = self.terminal

        row_ = self.row

        # Flush through the Write of anything but ED_2 after Flush before ED_2
        # TODO: Shadow Literals written after ED_2 to Flush at GetCh

        writer = TerminalWriter(chars)
        orders = writer.orders

        writing_ed_2 = False
        if len(orders) == 1:
            order = orders[-1]
            if order.csi_plus == ED_2:
                writing_ed_2 = True

        if not held_lines and not writing_ed_2:
            terminal.write(chars)
            terminal.flush()

        # Hold the Write of one or more Literals from Erase Display to Flush

        if held_lines:

            if column == columns:

                (row_, column_) = self.find_step_ahead()
                self.write_cursor_order(row=row_, column=column_)

            if any(_.literals for _ in orders):

                assert len(held_lines) == rows, (len(held_lines), row_)
                assert row_ < len(held_lines), (row_, chars)

                held_line = held_lines[row_]
                assert held_line is None, (row_, held_line, chars)

                held_lines[row_] = chars

        # Write the Orders into the Shadow Cursor

        self.write_some_orders(orders)

    def write_some_orders(self, orders):
        """Write the Orders into the Shadow Cursor"""

        columns = self.columns

        for order in orders:

            # Accept CR LF beyond the last Column, but nothing else

            if self.column == columns:
                self.write_beyond_row_order()
                if order.controls == "\r\n":

                    continue

            # Write whichever kind of order

            if order.csi_plus:
                self.write_csi_order(order)
            elif order.escape_plus:
                self.write_escape_order(order)
            elif order.controls:
                self.write_controls_order(order)
            elif order.literals:
                self.write_literals_order(order)
            else:
                assert False, order  # unreached

    def write_beyond_row_order(self):
        """Wrap into next Row, to accept Write past Last Column"""

        (row, column) = self.find_step_ahead()

        self.write_cursor_order(row, column=column)

    def write_csi_order(self, order):
        """Write one CSI Order into the Shadow Cursor"""

        if order.csi_plus == ED_2:
            self.write_ed_2_order()
        elif order.a == CUP_Y_X[-1] == "H":
            self.write_csi_cup_order(order)
        elif order.a == SGR_N[-1] == "m":
            self.write_csi_sgr_order(order)
        elif order.a == DECSCUSR_N[-2:] == " q":
            self.write_csi_cursor_decscusr_order(order)
        else:

            raise NotImplementedError(order)

    def write_ed_2_order(self):
        """Write one instance of ED_2"""

        held_lines = self.held_lines
        rows = self.rows

        held_lines[::] = rows * [None]
        self.write_cursor_order(row=None, column=None)

    def write_csi_cup_order(self, order):
        """Write one instance of CUP_Y_X"""

        if order.csi_plus == CUP_1_1:
            self.write_cursor_order(row=0, column=0)
        else:
            self.write_cursor_order(row=(order.int_y - 1), column=(order.int_x - 1))

            # may move the Cursor past Last Column

    def write_csi_sgr_order(self, order):
        """Write one instance of SGR_N"""
        # pylint: disable=no-self-use

        if order.x is None:
            if order.int_y in (None, 7):

                return  # TODO: learn to shadow SGR_N, more than its Cursor movement

        raise NotImplementedError(order)

    def write_csi_cursor_decscusr_order(self, order):
        """Write once instance of DECSCUSR_N"""

        if order.x is None:
            if order.int_y in (2, 4, 6):
                enter_cursor_style_chars = DECSCUSR_N.format(order.int_y)

                if self.enter_cursor_style_chars != enter_cursor_style_chars:
                    self.enter_cursor_style_chars = DECSCUSR_N.format(order.int_y)
                    self.exit_cursor_style_chars = None  # till after DECSCUSR_N

                return

        raise NotImplementedError(order)

    def write_escape_order(self, order):
        """Write one Escape Order into the Shadow Cursor"""

        raise NotImplementedError(order)

    def write_controls_order(self, order):
        """Write one Controls Order into the Shadow Cursor"""

        row = self.row

        if order.controls == "\a":
            self.writing_bell_chars = "\a"

        elif order.controls == "\r":
            self.write_cursor_order(row, column=0)

        elif order.controls == "\r\n":  # "\r\n" past last Column don't come here
            self.write_beyond_row_order()

        else:

            raise NotImplementedError(order)

    def write_literals_order(self, order):
        """Write one Literals Order into the Shadow Cursor"""

        (row, column) = self.find_slip_ahead(slips=len(order.literals))

        self.write_cursor_order(row, column=column)

    def write_cursor_order(self, row, column):
        """Place the Shadow Cursor, but never out of bounds"""

        columns = self.columns
        rows = self.rows

        # Assert Row:Column on Screen, or just past the Last Column of a Row

        if row is not None:
            assert 0 <= row < rows, (row, rows)

        if column is not None:
            assert 0 <= column <= columns, (column, columns)

        # Move the Shadow Cursor

        self.row = row
        self.column = column

    def find_slip_ahead(self, slips):
        """Scroll up the Rows when given an Order before or up to the Lower Right"""

        rows = self.rows
        columns = self.columns

        # Scroll as needed to slip ahead,
        # but accept landing one Column past the Lower Right

        row_ = self.row
        column_ = self.column

        column_ += slips

        while column_ > columns:
            column_ -= columns
            if row_ < (rows - 1):
                row_ += 1
            else:
                self.scroll += 1

        return (row_, column_)

    def find_step_ahead(self):
        """Scroll up the Rows when given an Order past the Lower Right"""

        rows = self.rows

        column_ = self.column
        row_ = self.row

        column_ = 0
        if row_ < rows - 1:
            row_ += 1
        else:
            self.scroll += 1

        return (row_, column_)

    # TODO: Add API to write Scroll CSI in place of rewriting Screen to Scroll
    # TODO: Reduce writes to Chars needed, smaller than whole Lines needed


class TerminalDriver:
    r"""
    Emulate a glass teletype at Stdio, such as the 1978 DEC VT100 Video Terminal

    Apply Terminal Input Magic to read ⌃@ ⌃C ⌃D ⌃J ⌃M ⌃T ⌃Z ⌃\ etc as themselves,
    not as SIGINT SIGINFO SIGQUIT etc

    Apply Terminal Output Magic to write the XTerm Alt Screen without Scrollback,
    in place of the XTerm Main Screen with Scrollback

    Compare Bash 'bind -p', Zsh 'bindkey', Bash 'stty -a', and Unicode-Org U0000.pdf

    Compare Bash 'vim' and 'less -FIXR', and https://unicode.org/charts/PDF/
    """

    def __init__(self, stdio):

        self.stdio = stdio

        self.fd = self.stdio.fileno()
        self.with_termios = None
        self.inputs = None

        self.lag = None

    def __enter__(self):
        """Switch Screen to XTerm Alt Screen and take single Chords from Keyboard"""

        fd = self.fd

        self.stdio.flush()

        if self.stdio.isatty():

            self.with_termios = termios.tcgetattr(fd)
            tty.setraw(fd, when=termios.TCSADRAIN)  # not TCSAFLUSH

            self.stdio.write(_CURSES_INITSCR_)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Switch Screen to Xterm Main Screen and disconnect Keyboard"""

        _ = (exc_type, exc_value, exc_traceback)

        self.stdio.flush()

        attributes = self.with_termios
        if attributes:
            self.with_termios = None

            self.stdio.write(_CURSES_ENDWIN_)
            self.stdio.flush()

            fd = self.fd
            when = termios.TCSADRAIN
            termios.tcsetattr(fd, when, attributes)

    def reopen_terminal(self):
        """Do nothing much, when running TerminalDriver in place of TerminalShadow"""

        size = os.get_terminal_size(self.fd)

        return size

        # TODO: resolve the clash between no 'flush' here while named as 'reopen'

    def flush(self):
        """Stop waiting for more Writes from above"""

        self.stdio.flush()

    def get_terminal_size(self):
        """Get a (Columns, Lines) Terminal Size, a la 'os.get_terminal_size'"""

        size = os.get_terminal_size(self.fd)

        return size

    def kbhit(self, timeout):
        """Wait till next Keystroke, or next burst of Paste pasted"""

        if self.inputs:

            return True

        rlist = [self.stdio]
        wlist = list()
        xlist = list()
        selected = select.select(rlist, wlist, xlist, timeout)
        (rlist_, _, _) = selected

        if rlist_ == rlist:

            return True

        return False

    def getch(self):
        """Block to fetch next Char of Paste, next Keystroke, or empty Eof"""

        # Block to fetch next Keystroke, if no Paste already queued

        inputs = "" if (self.inputs is None) else self.inputs
        if not inputs:

            stdin = self._pull_stdin()

            if len(stdin) > 1:  # TODO: cope more robustly with ⌃J before '__enter__'
                stdin = stdin.replace(b"\n", b"\r")

            if len(stdin) <= 1:

                return stdin

            inputs = stdin.decode(errors="surrogateescape")

        # Pick a CSI Esc [ sequence apart from more Paste

        if len(inputs) >= 3:
            if inputs[:2] == (ESC_CHAR + "["):

                stdin = inputs[:3].encode()
                self.inputs = inputs[3:]

                return stdin

        # Fetch next whole Char of Paste, such as
        # ⌃ ⌥ ⇧ ⌘ ← → ↓ ↑  # Control Option Alt Shift Command, Left Right Down Up Arrows

        stdin = inputs[:1].encode(errors="surrogateescape")
        self.inputs = inputs[1:]

        return stdin

    def _pull_stdin(self):
        """Pull a burst of Paste, else one slow single Keystroke, else empty at Eof"""

        # Block to fetch one more Byte
        # (or fetch no Bytes at end of input when Stdin is not Tty)

        stdin = os.read(self.stdio.fileno(), 1)
        assert stdin or not self.with_termios

        # Call for more, while available, while Line not closed
        # Trust no multibyte char encoding contains b"\r" or b"\n" (as per UTF-8)

        calls = 1
        while stdin and (b"\r" not in stdin) and (b"\n" not in stdin):

            lag = 0
            try:
                _ = stdin.decode()
            except UnicodeDecodeError:
                lag = 0.333  # 2021-12-11 failures at 0, 100, and 250ms

            if self.with_termios:
                if not self.kbhit(timeout=lag):

                    break

            more = os.read(self.stdio.fileno(), 1)
            if not more:
                assert not self.with_termios

                break

            stdin += more
            calls += 1

        assert calls <= len(stdin) if self.with_termios else (len(stdin) + 1)

        return stdin

    def write(self, chars):
        """Compare with Chars at Cursor, write Diffs now, move Cursor soon"""

        self.stdio.write(chars)

        if self.lag:
            time.sleep(self.lag)


#
# Track how to configure Vim to feel like Vi Py,
# especially after backing up or removing your history at:  -rw------- ~/.viminfo
#

_DOT_VIMRC_ = r"""


" ~/.vimrc


"
" Lay out Spaces and Tabs
"


:set softtabstop=4 shiftwidth=4 expandtab
autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab


"
" Configure Vim
"


:set background=light
:syntax on

:set ignorecase
:set nowrap

:set hlsearch

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:set ruler  " quirkily not inferred from :set ttyfast at Mac
:set showcmd  " quirkily not inferred from :set ttyfast at Linux or Mac


"
" Add keys (without redefining keys)
"
" N-NoRe-Map = Map only for Normal (View) Mode and don't Recurse through other maps
"


" Esc b  => macOS ⌥← Option Left-Arrow  => take as alias of ⇧B
" Esc f  => macOS ⌥→ Option Right-Arrow  => take as alias of ⇧W
:nnoremap <Esc>b B
:nnoremap <Esc>f W

" \ Delay  => gracefully do nothing
:nnoremap <BSlash> :<return>

" \ Esc  => cancel the :set hlsearch highlighting of all search hits on screen
:nnoremap <BSlash><Esc> :noh<return>

" \ e  => reload, if no changes not-saved
:nnoremap <BSlash>e :e<return>

" \ i  => toggle ignoring case in searches, but depends on :set nosmartcase
:nnoremap <BSlash>i :set invignorecase<return>

" \ m  => mouse moves cursor
" \ M  => mouse selects zigzags of chars to copy-paste
:nnoremap <BSlash>m :set mouse=a<return>
:nnoremap <BSlash>M :set mouse=<return>

" \ n  => toggle line numbers
:nnoremap <BSlash>n :set invnumber<return>

" \ w  => delete the trailing whitespace from each line (not yet from file)
:nnoremap <BSlash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

""' commented out for now
"" accept Option+3 from US Keyboards as meaning '#' \u0023 Hash Sign
"
":cmap <Esc>3 #
":imap <Esc>3 #
":nmap <Esc>3 #
":omap <Esc>3 #
":smap <Esc>3 #
":vmap <Esc>3 #
":xmap <Esc>3 #


"
" Require ⌃V prefix to input some chars outside Basic Latin
" so as to take macOS Terminal Option Key as meaning Vim ⌃O
" despite macOS Terminal > Preferences > ... > Keyboard > Use Option as Meta Key = No
"


" ... redacted here to limit the character set of this source file ...


" copied from:  git clone https://github.com/pelavarre/pybashish.git


"""


#
# Track how to configure Emacs to feel like Em Py,
#

_DOT_EMACS_ = r"""


; ~/.emacs


;
; Configure Emacs
;


(setq-default indent-tabs-mode nil)  ; indent with Spaces not Tabs
(setq-default tab-width 4)  ; count out columns of C-x TAB S-LEFT/S-RIGHT

(when (fboundp 'global-superword-mode) (global-superword-mode 't))  ; accelerate M-f M-b

(column-number-mode)  ; show column number up from 0, not just line number up from 1


;
; Add keys (without redefining keys)
; (as dry run by M-x execute-extended-command, M-: eval-expression)
;


(global-set-key (kbd "C-c %") 'query-replace-regexp)  ; for when C-M-% unavailable
(global-set-key (kbd "C-c -") 'undo)  ; for when C-- alias of C-_ unavailable
(global-set-key (kbd "C-c O") 'overwrite-mode)  ; aka toggle Insert
(global-set-key (kbd "C-c b") 'ibuffer)  ; for ? m Q I O multi-buffer replace
(global-set-key (kbd "C-c m") 'xterm-mouse-mode)  ; toggle between move and select
(global-set-key (kbd "C-c o") 'occur)
(global-set-key (kbd "C-c r") 'revert-buffer)
(global-set-key (kbd "C-c s") 'superword-mode)  ; toggle accelerate of M-f M-b
(global-set-key (kbd "C-c w") 'whitespace-cleanup)

(setq linum-format "%2d ")
(global-set-key (kbd "C-c n") 'linum-mode)  ; toggle line numbers
(when (fboundp 'display-line-numbers-mode)
    (global-set-key (kbd "C-c n") 'display-line-numbers-mode))

(global-set-key (kbd "C-c r")
    (lambda () (interactive) (revert-buffer 'ignoreAuto 'noConfirm)))


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
; Doc how to turn off enough of macOS Terminal to run Emacs well
;

; Press Esc to mean Meta, or run Emacs Py in place of Emacs, or else
;   macOS Terminal > Preferences > Profiles > Keyboard > Use Option as Meta Key

; Press ⌃⇧2 or ⌃Space and hope ⌃H K says it comes out as C-@ or C-SPC
;   to mean 'set-mark-command, even though older macOS needed you to turn off
;   System Preferences > Keyboard > Input Sources >
;   Shortcuts > Select The Previous Input Source  ⌃Space

; Except don't work so hard if you have the following in place to keep this easy =>


;
; Require ⌃Q prefix to input some chars outside Basic Latin
; so as to take macOS Terminal Option Key as meaning Emacs Meta anyhow
; despite macOS Terminal > Preferences > ... > Keyboard > Use Option as Meta Key = No
;


; ... redacted here to limit the character set of this source file ...


; copied from:  git clone https://github.com/pelavarre/pybashish.git


"""


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
class KwArgsException(Exception):
    """Raise a string of Key-Value Pairs"""

    def __init__(self, **kwargs):
        # pylint: disable=super-init-not-called

        self.kwargs = kwargs

    def __str__(self):
        kwargs = self.kwargs
        str_exc = ", ".join("{}={!r}".format(k, v) for (k, v) in kwargs.items())

        return str_exc


# deffed in many files  # missing from docs.python.org
def argparse_compile_argdoc(epi, drop_help=None, doc=None):
    """Construct the 'argparse.ArgumentParser' with Epilog but without Arguments"""

    f = inspect.currentframe()
    (module_doc, _) = argparse_module_doc_and_file(doc=doc, f=f)

    # Pick the ArgParse Prog, Description, & Epilog out of the Main Arg Doc

    prog = module_doc.strip().splitlines()[0].split()[1]

    headlines = list(
        _ for _ in module_doc.strip().splitlines() if _ and not _.startswith(" ")
    )
    description = headlines[1]

    epilog_at = module_doc.index(epi)
    epilog = module_doc[epilog_at:]

    # Start forming the ArgParse Parser

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=(not drop_help),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    return parser


# deffed in many files  # missing from docs.python.org
def argparse_exit_unless_doc_eq(parser, doc=None):
    """Exit nonzero, unless __main__.__doc__ equals 'parser.format_help()'"""

    f = inspect.currentframe()
    (module_doc, module_file) = argparse_module_doc_and_file(doc=doc, f=f)

    # Fetch the two docs

    with_columns = os.getenv("COLUMNS")
    os.environ["COLUMNS"] = str(89)  # Black promotes 89 columns per line
    try:
        parser_doc = parser.format_help()
    finally:
        if with_columns is None:
            os.environ.pop("COLUMNS")
        else:
            os.environ["COLUMNS"] = with_columns

    # Cut the worthless jitter we wish away

    alt_module_doc = module_doc.strip()
    alt_parser_doc = parser_doc

    if sys.version_info[:3] < (3, 9, 6):

        alt_module_doc = str_join_first_paragraph(alt_module_doc)
        alt_parser_doc = str_join_first_paragraph(alt_parser_doc)

        if "[FILE ...]" in module_doc:
            alt_parser_doc = alt_parser_doc.replace("[FILE [FILE ...]]", "[FILE ...]")
            # older Python needed this accomodation, such as Feb/2015 Python 3.4.3

    # Sketch where the Doc's came from

    alt_module_file = module_file
    alt_module_file = os.path.split(alt_module_file)[-1]
    alt_module_file = "{} --help".format(alt_module_file)

    alt_parser_file = "argparse.ArgumentParser(..."

    # Count significant differences

    got_diffs = argparse_stderr_print_diffs(
        alt_module_doc,
        alt_parser_doc=alt_parser_doc,
        alt_module_file=alt_module_file,
        alt_parser_file=alt_parser_file,
    )

    if got_diffs:

        sys.exit(1)  # trust caller to log SystemExit exceptions well


# deffed in many files  # missing from docs.python.org
def argparse_stderr_print_diffs(
    alt_module_doc, alt_parser_doc, alt_module_file, alt_parser_file
):
    """True after Printing Diffs, False when no Diffs found"""

    # pylint: disable=too-many-locals

    for diff_precision in range(2):

        a_lines = alt_module_doc.splitlines()
        b_lines = alt_parser_doc.splitlines()

        # First count differences ignoring blank space between Words,
        # but end by counting even the smallest differences in Chars

        if not diff_precision:

            a_words_by_index = list()
            for (index, a_line) in enumerate(a_lines):
                a_words = " ".join(a_line.split())
                a_words_by_index.append(a_words)

            for (index, b_line) in enumerate(b_lines):
                b_words = " ".join(b_line.split())
                if b_words in a_words_by_index:
                    a_index = a_words_by_index.index(b_words)
                    a_line = a_lines[a_index]

                    b_lines[index] = a_line

        diff_lines = list(
            difflib.unified_diff(
                a=a_lines,
                b=b_lines,
                fromfile=alt_module_file,
                tofile=alt_parser_file,
            )
        )

        # Return True if differences found, but first print these differents to Stderr

        if diff_lines:  # TODO: ugly contingent '.rstrip()'

            lines = list((_.rstrip() if _.endswith("\n") else _) for _ in diff_lines)
            stderr_print("\n".join(lines))

            return True

    # Return False if no differences found

    return False


# deffed in many files  # missing from docs.python.org
def argparse_module_doc_and_file(doc, f):
    """Take the Doc as from Main File, else pick the Doc out of the Calling Module"""

    module_doc = doc
    module_file = __main__.__file__

    if doc is None:
        module = inspect.getmodule(f.f_back)

        module_doc = module.__doc__
        module_file = f.f_back.f_code.co_filename

    return (module_doc, module_file)


# deffed in many files  # missing from docs.python.org
def module_file_hash():
    """Hash the Bytes of this SourceFile"""

    abs_module_file = os.path.abspath(module_file_path())
    with open(abs_module_file, "rb") as reading:
        file_bytes = reading.read()

    hasher = hashlib.md5()
    hasher.update(file_bytes)
    hash_bytes = hasher.digest()

    str_hash = hash_bytes.hex()
    str_hash = str_hash.upper()  # such as 32 nybbles 'D41D8CD98F00B204E9800998ECF8427E'

    return str_hash


# deffed in many files  # missing from docs.python.org
def module_file_path():
    """Find the Doc of caller, even when not Main, and when:  __main__ is None"""

    f = inspect.currentframe()
    module_file = f.f_back.f_code.co_filename  # more available than 'module.__file__'

    return module_file


# deffed in many files  # missing from docs.python.org
def module_file_version_zero():
    """Pick a conveniently small, reasonably distinct, decimal Version Number"""

    str_hash = module_file_hash()

    major = 0
    minor = int(str_hash[0], 0x10)  # 0..15
    micro = int(str_hash[1:][:2], 0x10)  # 0..255

    version = "{}.{}.{}".format(major, minor, micro)

    return version


# deffed in many files  # missing from docs.python.org
def file_print(*args):  # later Python 3 accepts ', **kwargs' here
    """Save out the Str of an Object as a File"""

    with open("f.file", "a") as printing:
        print(*args, file=printing)


# deffed in many files  # missing from docs.python.org
def lines_last_has_no_end(lines):
    """True when the last Line exists without Line End, else False"""

    if lines:

        last_ended_line = lines[-1]
        last_line = str_remove_line_end(last_ended_line)

        last_line_end = last_ended_line[len(last_line) :]
        if not last_line_end:

            return True

    return False


# deffed in many files  # missing from docs.python.org
def os_path_corename(path):
    """Return the File Basename part that means which look to wear"""

    basename = os.path.basename(path)
    name = os.path.splitext(basename)[0]
    corename = name.split("~")[0]

    return corename  # such as "vim" from "bin/vim~1205pl2108~.py"


# deffed in many files  # missing from docs.python.org
def os_path_homepath(path):  # inverse of 'os.path.expanduser'
    """Return the ~/... RelPath of a File or Dir of the Home, else the AbsPath"""

    home = os.path.abspath(os.environ["HOME"])

    homepath = path
    if path == home:
        homepath = "~"
    elif path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


# deffed in many files  # missing from Python till Oct/2019 Python 3.8
def shlex_join(argv):
    """Undo shlex.split"""

    # Trust the library, if available

    if hasattr(shlex, "join"):
        shline = shlex.join(argv)

        return shline

    # Emulate the library roughly, because often good enough

    shline = " ".join(shlex_quote(_) for _ in argv)

    return shline


# deffed in many files  # missing from Python till Oct/2019 Python 3.8
def shlex_quote(arg):
    """Mark up with quote marks and backslashes , but only as needed"""

    # Trust the library, if available

    if hasattr(shlex, "quote"):
        quoted = shlex.quote(arg)

        return quoted

    # Emulate the library roughly, because often good enough

    mostly_harmless = set(
        "%+,-./"  # not: !"#$&'()*
        + string.digits
        + ":=@"  # not ;<>?
        + string.ascii_uppercase
        + "_"  # not [\]^
        + string.ascii_lowercase
        + ""  # not {|}~
    )

    likely_harmful = set(arg) - set(mostly_harmless)
    if likely_harmful:
        quoted = repr(arg)  # as if the Py rules agree with Sh rules

        return quoted

    return arg


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):  # later Python 3 accepts ', **kwargs' here
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def str_join_first_paragraph(doc):
    """Join by single spaces all the leading lines up to the first empty line"""

    index = (doc + "\n\n").index("\n\n")
    lines = doc[:index].splitlines()
    chars = " ".join(_.strip() for _ in lines)
    alt = chars + doc[index:]

    return alt


# deffed in many files  # missing from docs.python.org
def str_remove_line_end(chars):
    """Remove one Line End from the end of the Chars if they end with a Line End"""

    line = (chars + "\n").splitlines()[0]

    return line


# Cite some Terminal Doc's and Git-track experience of Terminal Output magic
#
#       https://en.wikipedia.org/wiki/ANSI_escape_code
#           SGR (Select Graphic Rendition) parameters
#
#               "m"     Reset, Normal
#               "1m"    Bold, Increased Intensity
#               "2m"    Faint, Decreased Intensity, Dim  <-- Replace
#               "3m"    Italic
#               "4m"    Underline
#               "5m"    Slow Blink
#               "6m"    Rapid Blink  # ignored by Mac Terminal
#               "7m"    Reverse Video, Invert  # overriden by default Cursor
#               "8m"    Conceal, Hide
#               "9m"    Crossed-out, Strike  # ignored by Mac Terminal
#
#       https://invisible-island.net/xterm/ctlseqs/ctlseqs.html
#           CSI Pm m  Character Attributes (SGR)
#           CSI Ps SP q  Set Cursor Style (DECSCUSR), VT520
#
#               " q"    Reset, Normal (but doc'ed poorly)
#               "1 q"   Blinking Block (like after Screen still for 2s)
#               "2 q"   Steady Block (same as default of Mac Terminal)
#               "3 q"   Blinking Underline
#               "4 q"   Steady Underline
#               "5 q"   Blinking Bar
#               "6 q"   Steady Bar
#


#
# Track ideas of future work
#


# TODO: search the Sourcelines above here a la :g/FIXME
# TODO: search the Sourcelines above here a la :g/TODO\|FIXME


# -- bugs --

# FIXME: define Backspace and Delete differently for Vi Py Replace/ Insert
# FIXME: Vi Py replace/ insert/ delete should trigger re-eval of search spans in lines

# TODO:  find more bugs


# -- future inventions --


# TODO: ⌃O for Search Key input, not just Replace/ Insert input


# TODO: Delete after Replaces as undo Replaces, inside the R mode
# TODO: code Repeat Count for the Vi Py ⇧R ⇧A ⇧I ⇧O A I O variations of Replace/ Insert
# TODO: cancel Insert Repeat Count if moved away while inserting


# TODO: something akin to Vim :set cursorline, :set nocursorline
# TODO: Vim ⇧V ⇧V to highlight the Line at the Cursor
# TODO: Vim ⌃V for feeding into :!|pbcopy
# TODO: Vim ⇧! default into :!|pbcopy
# TODO: look back over keyboard timeline to guess initial shape of a stroke like ⌃V


# TODO: QR to draw with a Logo Turtle till QR,
# TODO: infinite Spaces per Row, rstrip at exit, moving relative not absolute
# TODO: 1234567890 Up Down Left Right, initially headed Up with |
# TODO: | - =| =- to draw a rectangle, |=-=|=- to draw a square
# TODO: [ ] for macro repetition
# TODO: escape to complete unabbreviated Logo:  Repeat 4 [ Forward 10 Right 90 ]
# TODO: escape to complete abbreviated Logo:  Rep 4 [ Fd 10 Rt 90 ]
# TODO: contrast with default Emacs Picture Modes |-/\+ ...


# TODO: stop passing through Controls from the File
# TODO: test hard Tabs in File
# TODO: solve /⌃V⌃IReturn
# TODO: accept b"\t" Hard Tabs as a form of b" " Space
# TODO: show the first ~ past the end differently when No End for Last Line
# TODO: revive the last Match of r"$" out there
# TODO: show, delete, and insert the Eol of the last line
# TODO: test Eol encodings of b"\r\n" and b"\r", apart from b"\n" in File
# TODO: test chars outside  and far outside the basic U0000..U00FF in File
# TODO: test SurrogateEscape's in File


# TODO: radically simplified undo:  3u to rollback 3 keystrokes
# TODO: radically simplified undo:  u to explain radically simplified undo


# TODO: save/load to/from local Os CopyPaste Buffer, like via Mac pbpaste/pbcopy


# -- future improvements --

# TODO: record and replay tests of:  cat bin/vi.py |vi.py - bin/vi.py

# TODO: teach :w! :wn! :wq! to temporarily override PermissionError's from 'chmod -w'

# TODO: insert U00C7 ç and U00F1 ñ etc - all the Unicode outside of C0 Controls
# TODO: #åçéîñøü←↑→↓⇧⋮⌃⌘⌥⎋💔💥😊😠😢

# TODO: Vim equivalent of \N somehow doesn't disrupt the 'keep_up_vi_column_seek' of $

# TODO: name errors for undefined keys inside Ex of / ? etc


# -- future features --

# TODO: show just the leading screen of hits and land on the first for g? :g?
# TODO: recover :g/ Status when ⌃L has given us :set _lag_ of >1 Screen of Hits

# TODO: ⌃X⌃X⌃G often gives Em Py something of an 'undo last big move'
# TODO: ⌃I ⌃O walk Vim Jump List of ' ` G / ? n N % ( ) [[ ]] { } L M H :s :tag :n etc
# TODO: despite Doc, to match Vim, include in the Jump List the * # forms of / ?
# TODO: against Vim, add the start of ⌃O to the ⌃I

# TODO: mm '' `` pins
# TODO: qqq @q  => record input, replay input

# TODO: :! for like :!echo $(whoami)@$(hostname):$(pwd)/
# TODO: accept more chords and DEL and ⌃U after : till \r
# TODO: accept :123\r, but suggest 123G etc
# TODO: accept :noh\r and :set ignorecase and so on, but suggest \I etc

# TODO: toggled :set wrap, :set nowrap
# TODO: ⌃D ⌃U scrolling
# TODO: ⌃V o  => rectangular: opposite

# TODO: code :r to try read files by name, pass and fail
# TODO: code :w to try write files by name, pass and fail

# TODO: ls |bin/vi.py +3 -  # start on chosen line
# TODO: ls |bin/vi.py +/Makefile -  # start on found line


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
