#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
usage: argdoc.py [-h] [--rip SHRED] [FILE] [WORD ...]

parse command line args as per a top-of-file docstring of help lines

positional arguments:
  FILE         some python file begun by a docstring (often your main py file)
  WORD         an arg to parse for the file, or a word of a line of docstring

options:
  -h, --help   show this help message and exit
  --rip SHRED  rip one of doc|argparse|argdoc|args|patch

quirks:
  plural args go to an english plural key, such as '[top ...]' to '.tops'
  you lose your '-h' and '--help' options if you drop all your 'options:'

unsurprising quirks:
  takes file '-' as meaning '/dev/stdin', rips args as json
  prompts before reading a tty, like mac bash 'grep -R .', unlike bash 'cat -'
  accepts 'stty -a' line-editing c0-control's, no bash 'bind -p' c0-control's

examples:

  argdoc.py -h                          # show this help message and exit
  argdoc.py                             # same as:  argdoc.py --rip argparse

  argdoc.py --rip argparse              # show an argparse prog, don't run it
  argdoc.py --rip argdoc                # show an argdoc prog, don't run it
  argdoc.py --rip argparse >p.py        # form and name an argparse prog

  argdoc.py --rip doc p.py              # eval the doc from top of file
  argdoc.py p.py                        # same as:  --rip argparse p.py
  argdoc.py --rip args p.py --          # run the file doc to parse no args
  argdoc.py --rip args p.py --  --help  # run the file doc to parse:  --help
  argdoc.py --rip args p.py --  hi you  # run the file doc to parse:  hi you

  argdoc.py --  -x, --extra  do more    # show patch to add a counted option
  argdoc.py --  -a OPT, --also OPT  ya  # show patch to add an option with arg
  argdoc.py --  POS  thing              # show patch to add a positional arg
"""

# TODO:  --rip .txt, .py3, .py for doc, argdoc, argparse
# TODO:  save to path, not stdout, if more path provided, not just the .ext or ext

# TODO:  take a whole file without """ and without ''' as a whole argdoc

# FIXME:  reject dropped args such as the "-- hello" of
# FIXME:    bin/argdoc.py --rip argparse bin/tar.py -- hello >/dev/null


from __future__ import print_function

import __main__
import argparse
import ast
import difflib
import inspect
import json
import os
import pdb
import re
import sys
import textwrap


_89_COLUMNS = 89  # the Black app for styling Python promotes 89 columns per line


def b():
    """Break into the Debugger when called"""

    pdb.set_trace()  # pylint: disable=forgotten-debug-statement


#
# Run as a command line:  ./argdoc.py ...
#


def main():
    """Run an Arg Doc Py command line"""

    run_self_tests()

    args = parse_argdoc_args()

    chars = rip_chars(args)
    print(chars)


def run_self_tests():
    """Run some Self Tests, as part of every Launch"""

    _plural_en_test()
    _argdoc_test()


def parse_argdoc_args():
    """Print the top-of-file Doc and exit, else parse an Arg Doc Py command line"""

    parser = argdoc_py_parser_from_doc()

    # Parse the Args

    args = parser.parse_args()

    # Mystically auto-correct the Parse when the first Word slips into the File place

    file_indices = list(_[0] for _ in enumerate(sys.argv[1:]) if _[-1] == args.file)
    sep_indices = list(_[0] for _ in enumerate(sys.argv[1:]) if _[-1] == "--")
    if sep_indices and file_indices:
        if sep_indices[0] <= file_indices[0]:

            args.words.insert(0, args.file)
            args.file = None

    # Default to Rip Patch if we have Words, else default to Rip ArgParse,
    # but fail now if asked to Rip anything we don't have

    shred = args.rip
    if args.rip is None:
        shred = "patch" if args.words else "argparse"

    str_rips = "doc|argparse|argdoc|args|patch"
    if shred not in str_rips.split("|"):
        stderr_print(
            "error: argdoc.py: choose one of {}, not:  --rip {}".format(str_rips, shred)
        )

        sys.exit(2)  # exit 2 to reject usage

    if shred == "patch":
        if not args.words:
            stderr_print("error: argdoc.py: '--rip patch' requires the argument WORD")

            sys.exit(2)  # exit 2 to reject usage

    args.shred = shred

    # Succeed

    return args


def argdoc_py_parser_from_doc():
    """Print the top-of-file Doc and exit, else parse an Arg Doc Py command line"""

    # Compile an ArgumentParser from the top-of-file Doc here

    parser = parser_from_doc(epi="quirks")

    parser.add_argument(
        "file",
        metavar="FILE",
        nargs="?",  # argparse.OPTIONAL
        help="some python file begun by a docstring (often your main py file)",
    )

    parser.add_argument(
        "words",
        metavar="WORD",
        nargs="*",  # argparse.ZERO_OR_MORE
        help="an arg to parse for the file, or a word of a line of docstring",
    )

    parser.add_argument(
        "--rip", metavar="SHRED", help="rip one of doc|argparse|argdoc|args|patch"
    )

    try:
        parser_exit_unless_doc_eq(parser)  # Constrain the Doc of ArgDoc Py
    except SystemExit:
        stderr_print("argdoc.py: error: want Doc, got Parser, and they don't match")

        raise

    return parser


def _argdoc_test():
    """Run some Self Tests of this Arg Doc Py"""

    # Declare the meaning of an empty ArgDoc Py command line
    # ordered like later Python:  args0_dict = dict(file=None, words=list(), rip=None)

    args0_dict = dict()
    args0_dict["file"] = None
    args0_dict["words"] = list()
    args0_dict["rip"] = None

    # Compile an ArgumentParser from the top-of-file Doc here, as Self

    file1 = "parser_from_doc"

    parser1 = argdoc_py_parser_from_doc()

    args1 = parser1.parse_args([])
    assert vars(args1) == args0_dict
    if sys.version_info >= (3, 6):
        assert vars(args1).items() == args0_dict.items()

    # Compile an ArgumentParser from the top-of-file Doc here, as a client of Self

    file2 = "ArgumentParser"

    parser2 = ArgumentParser()
    parser_exit_unless_doc_eq(parser2)  # Pass or fail as part of Self Test

    args2 = parser2.parse_args([])
    assert vars(args2) == args0_dict
    if sys.version_info >= (3, 6):
        assert vars(args2).items() == args0_dict.items()

    # Compare the two compiled ArgumentParser's

    py1 = rip_py_on_argparse(parser1)
    py2 = rip_py_on_argparse(parser2)

    if sys.version_info >= (3, 6):

        difflines = list(
            difflib.unified_diff(
                a=py1.splitlines(), b=py2.splitlines(), fromfile=file1, tofile=file2
            )
        )
        diffchars = "\n".join(_.splitlines()[0] for _ in difflines)
        if diffchars:
            stderr_print(diffchars)  # 'parser_from_doc' vs 'ArgumentParser'

        assert py1 == py2  # TODO: pass test with OrderedDict's in CPython < 3.6


#
# Rip out the Doc, or a Python Prog, or some Json, or a Patch
#


def rip_chars(args):
    """Rip out the Doc, or a Python Prog, or some Json, or a Patch"""

    # Rip the Doc, before compiling an ArgumentParser out of it

    doc = ast_literal_eval_py_doc(path=args.file)
    doc = None if (doc is None) else doc.strip()

    if args.shred == "doc":
        chars = doc

        return chars

    # Compile an ArgumentParser out of the Doc

    parser = rip_whole_parser_from_doc(doc, path=args.file)
    pychars = rip_py_on_argparse(parser)

    # Rip out a Python Prog to call on ArgParse to form the ArgumentParser

    if args.shred == "argparse":
        chars = pychars

        return chars

    # Rip out a much a smaller Python Prog to call on ArgDoc to form the ArgumentParser

    if args.shred == "argdoc":
        _ = parser.format_usage().rstrip()
        chars = rip_py_on_argdoc(parser)

        return chars

    # Rip out a Json of the Args as parsed by the Source

    if args.shred == "args":
        args = parser.parse_args(args.words)
        chars = json.dumps(vars(args), indent=4)

        return chars

    # Rip out a Patch to add yet another Arg, or yet another Option

    chars = rip_py_add_patch(parser, path=args.file, words=args.words, pychars=pychars)

    return chars

    # TODO: amp up the '# : boom : broken_heart : boom :' to survive instantiation

    # TODO: test Prog's other than Py File names, such as no Ext
    # TODO: think into PyLint's 7 loud complaints

    # TODO: parsed dest startswith '_' skid shouldn't print, via argparse.SUPPRESS

    # TODO: instantiated template should raise separate NotImplementedError per Option


# deffed in many files  # missing from docs.python.org
def ast_literal_eval_py_doc(path):
    """Fetch the DocString from a Python Source File"""

    pychars = pychars_fabricate()
    doc1 = eval_doc_from_pychars(pychars)

    doc2 = eval_doc_from_path(path)

    if doc2 is not None:

        return doc2

    return doc1


def eval_doc_from_path(path):
    """Pick the DocString out from top of a File, else None"""

    if path is None:

        return None

    # Read the chosen File

    alt_path = "/dev/stdin" if (path == "-") else path
    try:
        with open(alt_path, "r") as reading:
            if reading.isatty():
                stderr_print("Press ⌃D EOF to quit")  # or ⌃C SIGINT or ⌃\ SIGQUIT
            chars = reading.read()
    except OSError as exc:
        stderr_print("{}: {}".format(type(exc).__name__, exc))

        sys.exit(1)  # exit 1 to require input file found

    doc = eval_doc_from_pychars(chars)

    return doc

    # TODO: read what's needed, not whole file


def eval_doc_from_pychars(pychars):
    """Pick the DocString out from top of a File of Python Source Chars, else None"""

    marks = ['"""', '"', "'''", "'", 'r"""', 'r"', "r'''", "r'"]

    # Skip over comments and blank lines

    pylines = pychars.splitlines()
    for (index, pyline) in enumerate(pylines):
        stripped = pyline.strip()
        if stripped and not stripped.startswith("#"):

            # Fail if first sourceline is Not a quoted String of Chars

            matches = list(_ for _ in marks if stripped.startswith(_))
            if not matches:

                return None

            mark1 = matches[0]
            mark2 = mark1.lstrip("r")

            # Fail if DocString starts without ending

            tail = "\n".join(pylines[index:])
            start = tail.index(mark1) + len(mark1)
            end = tail.find(mark2, start)
            if end < 0:

                return None

            # Else pick out the DocString between matching Mark's

            evallable = mark1 + tail[start:end] + mark2
            evalled = ast.literal_eval(evallable)

            return evalled

    # Fail if DocString never starts

    return None


#
# Rip Add_Argument calls out from the Doc
#


def parser_adds_from_doc(parser, doc):
    """Rip the Add_Argument Calls from Doc of Positional Arguments and/or Options"""

    if doc is None:

        return

    alt_doc = argparse_doc_upgrade(doc)
    paras = textwrap_split_paras(text=alt_doc)

    # Take one Para of Usage

    usage = " ".join(paras[0])
    assert usage.startswith("usage: ")
    paras = paras[1:]

    # Skip the Para of Description

    paras = paras[1:]

    # Take the next Para as Lines of Args, if tagged as Positional Arguments

    if paras:
        if parser_add_args_from_para(parser, para=paras[0], usage=usage):
            paras = paras[1:]

    # Take the next Para as Lines of Options, if tagged as Options

    if paras:
        if parser_add_options_from_para(parser, para=paras[0], usage=usage):
            paras = paras[1:]


def parser_add_args_from_para(parser, para, usage):
    """Take the next Para as Lines of Args, if tagged as Positional Arguments"""

    if para[0].startswith("positional arguments"):
        for line in textwrap_para_unbreakdent_lines(para=para[1:]):
            parser_add_arg_line(parser, usage=usage, line=line)

        return True

    return False


def parser_add_options_from_para(parser, para, usage):
    """Take the next Para as Lines of Options, if tagged as Options"""

    if para[0].startswith("options") or para[0].startswith("optional arguments"):
        for line in textwrap_para_unbreakdent_lines(para=para[1:]):
            parser_add_option_line(parser, usage=usage, line=line)

        return True

    return False


def textwrap_para_unbreakdent_lines(para):
    """Join the continuation lines dented beneath each leading line"""

    above_dent = None

    lines = list()
    for line in para:
        lstripped = line.lstrip()

        dent = ""
        if line != lstripped:
            dent = line[: -len(lstripped)]

        if lines:
            if len(dent) > len(above_dent):
                lines[-1] += " " + line.strip()

                continue

        lines.append(line)
        above_dent = dent

    return lines

    # such as:  [' a', '    b', ' c']  ->  [' a b', ' c']


def parser_add_arg_line(parser, usage, line):
    """Rip out one Add_Argument Call of a Positional Arg from one Doc Line"""
    # pylint: disable=duplicate-string-formatting-argument

    words = line.split()
    if not words:

        return

    # Divide the Line into Metavar and Help

    word = words[0]

    after_word = line.index(word) + len(word)
    help_tail = line[after_word:].strip()

    dest = word.lower()  # Python 3 could '.casefold()'
    metavar = word

    # Take mentions of NArgs ? or NArgs * from Usage

    nargs = None
    if "[{}]".format(metavar) in usage:
        nargs = "?"  # argparse.OPTIONAL
    elif " {} [{} ...]".format(metavar, metavar) in usage:
        dest = plural_en(metavar.lower())  # mutate
        nargs = "+"  # argparse.ONE_OR_MORE
    elif "[{} ...]".format(metavar) in usage:
        dest = plural_en(metavar.lower())  # mutate
        nargs = "*"  # argparse.ZERO_OR_MORE

    # Tell the Parser to add this Arg

    alt_help_tail = help_tail if help_tail else None
    alt_help_tail = alt_help_tail.replace("%", "%%") if alt_help_tail else None
    parser.add_argument(dest, metavar=metavar, nargs=nargs, help=alt_help_tail)


def parser_add_option_line(parser, usage, line):
    """Rip one Add_Argument Call of an Option or two from one Doc Line"""

    dests = list()
    alt_metavar = None  # cut from Help here, then picked up or not from Usage
    help_tail = line.strip()

    # Visit each Word

    words = line.split()
    matched_index = -1
    for (index, word) in enumerate(words):
        next_word = words[index + 1] if words[(index + 1) :] else None

        # Pull each Dashed Option out of the Help, and
        # let earlier Words pull subsequent Words out of the Help too

        if word.startswith("-") or (index <= matched_index):

            after_word = help_tail.index(word) + len(word)
            help_tail = help_tail[after_word:].strip()  # mutate

            if index <= matched_index:

                continue

        # Break after the last Dashed Option

        if not word.startswith("-"):

            break

        dests.append(word.split(",")[0])

        # Loop again to pick up a Metavar for each Dashed Option

        if not word.endswith(","):
            if alt_metavar or next_word.endswith(","):
                alt_metavar = next_word.split(",")[0]
                matched_index = index + 1

                continue

            # Break if the Option doesn't call for another Option

            break

        # Break after the 2nd Dashed Option

        if len(dests) >= 2:

            break

    if len(dests) in (1, 2):

        parser_add_option_dests(parser, usage=usage, dests=dests, help_tail=help_tail)


def parser_add_option_dests(parser, usage, dests, help_tail):
    """Rip one Add_Argument Call of an Option or Two from their names and help"""
    # pylint: disable=too-many-locals  # TODO: 18/15

    # Take mentions of Action or Metavar from first such Usage of any Option Name

    metavar = None
    nargs = None

    for opt in dests:

        opt_at = usage.find("[{}]".format(opt))
        alt_index = 1

        if opt_at < 0:

            opt_at = usage.find("[{} ".format(opt))
            alt_index = 2

            if opt_at < 0:

                continue

        usage_tail = usage[opt_at:]
        alt_words = usage_tail.split()

        alt_metavar = None
        if alt_index == 2:
            alt_metavar = alt_words[1]
            if (not alt_metavar.startswith("[")) and alt_metavar.endswith("]"):
                alt_metavar = alt_metavar[: -len("]")]
            elif alt_metavar.endswith("]]"):
                alt_metavar = alt_metavar[: -len("]")]

        (metavar, nargs, _) = _parser_choose_metavar_nargs_index(
            alt_words, dests=dests, alt_metavar=alt_metavar, alt_index=alt_index
        )

        break

    # Take Action Count from Help Line, when Option missing from Usage

    alt_help_tail = help_tail

    action = "count"
    if metavar is not None:
        action = None

        # Cut the Metavar out from leading the Help, if present

        maybe_metavar = "[{}]".format(metavar)
        if help_tail:
            help_word = help_tail.split()[0]
            if help_word in (metavar, maybe_metavar):
                alt_help_tail = help_tail[len(help_word) :].strip()  # mutate

                # Take NArgs "?" from Help Line, when Option missing from Usage

                if help_word == maybe_metavar:
                    if nargs is None:
                        nargs = "?"  # argparse.OPTIONAL

    # Tell the Parser to add this Option

    option = argparse.Namespace(
        dests=dests, metavar=metavar, nargs=nargs, action=action
    )

    parser_add_option_call(parser, option=option, help_tail=alt_help_tail)


def parser_add_option_call(parser, option, help_tail):
    """Tell the Parser to add this Option"""

    # Keep on working with many choices

    dests = option.dests
    metavar = option.metavar
    nargs = option.nargs
    action = option.action

    assert len(dests) in (1, 2)

    # Default to Arg False when Option NArgs "?", to set apart No Option from None Arg
    # Default to Count up from Zero, so that the Int of Count is Int, not TypeError

    default = None
    if nargs == "?":
        assert action is None
        default = False  # for 'nargs="?'"
    elif action == "count":
        assert nargs is None
        default = 0  # for 'action="count"'

    # Call victory when Parser Add_Help already did add this Option

    if (dests == ["-h", "--help"]) and (metavar is None) and (nargs is None):
        if help_tail == "show this help message and exit":
            if action == "count":

                if parser.add_help:

                    return

    # Call Add Argument once, to add one or two Option Strings

    alt_help_tail = help_tail if help_tail else None
    alt_help_tail = alt_help_tail.replace("%", "%%") if alt_help_tail else None

    if not metavar:
        assert nargs is None
        assert action == "count"

        if len(dests) == 1:
            parser.add_argument(
                dests[0], action=action, default=default, help=alt_help_tail
            )
        else:
            assert len(dests) == 2
            parser.add_argument(
                dests[0], dests[1], action=action, default=default, help=alt_help_tail
            )

    else:
        assert action is None
        assert nargs in (None, "?")

        if len(dests) == 1:
            parser.add_argument(
                dests[0],
                metavar=metavar,
                nargs=nargs,
                default=default,
                help=alt_help_tail,
            )
        else:
            assert len(dests) == 2
            parser.add_argument(
                dests[0],
                dests[1],
                metavar=metavar,
                nargs=nargs,
                default=default,
                help=alt_help_tail,
            )


# deffed in many files  # missing from docs.python.org
def plural_en(word):
    """Guess the English plural of a word"""

    consonants = "bcdfghjklmnpqrstvwxz"  # without "y"

    if re.match(r"^.*ex$", string=word):
        plural = word[: -len("ex")] + "ices"  # vortex, vortices
    elif re.match(r"^.*f$", string=word):
        plural = word[: -len("f")] + "ves"  # leaf, leaves
    elif re.match(r"^.*is$", string=word):
        plural = word[: -len("is")] + "es"  # basis, bases
    elif re.match(r"^.*ix$", string=word):
        plural = word[: -len("ix")] + "ices"  # appendix, appendices
    elif re.match(r"^.*o$", string=word):
        plural = word + "es"  # tomato, tomatoes
    elif re.match(r"^.*on$", string=word):
        plural = word[: -len("on")] + "a"  # criterion, criteria
    else:
        if re.match(r"^.*[{consonants}]y$".format(consonants=consonants), string=word):
            plural = word[: -len("y")] + "ies"  # lorry, lorries
        elif re.match(r"^.*(ch|s|sh|x|z)$", string=word):
            plural = word + "es"
            # stitch bus ash box lutz, stitches buses ashes boxes lutzes
        else:
            plural = word + "s"  # word, words

            # don't try to solve:  nucleus, nuclei

    return plural

    # TODO: override the Plural_En choice of Dest
    # TODO: parse 'usage: MICE ...' as last to match with any Arg, thus match 'MOUSE'
    # TODO: accept ArgumentParser(dests="mice")
    # TODO: accept parse_args(dests=dict(mouse="mice"))
    # TODO: override Dest such as '.n' at '-n COUNT, --lines COUNT'


def _plural_en_test():

    # Test correct plurals

    singulars = "vortex leaf basis appendix tomato criterion lorry lutz".split()
    plurals = "vortices leaves bases appendices tomatoes criteria lorries lutzes"

    singulars.extend("cafe diagnosis safe word".split())
    plurals += " cafes diagnoses safes words"

    guesses = " ".join(plural_en(_) for _ in singulars)
    assert guesses == plurals

    # Test incorrect plurals

    incorrect_singulars = "bacterium child locus knife nucleus ox roof cello".split()
    incorrect_plurals = "bacteriums childs locuses knifes nucleuses oxes rooves celloes"

    incorrect_singulars.extend("deer mouse sheep".split())
    incorrect_plurals += " deers mouses sheeps"

    incorrect_guesses = " ".join(plural_en(_) for _ in incorrect_singulars)
    assert incorrect_guesses == incorrect_plurals


# deffed in many files  # missing from docs.python.org
def textwrap_split_paras(text):
    """Divide the Chars into a List of non-empty Lists of possibly dented Lines"""

    if text is None:

        return None

    paras = list()

    para = None
    for line in (text + "\n\n").splitlines():
        if not line.strip():
            if para is not None:
                paras.append(para)
            para = None
        elif not para:
            para = [line]
        else:
            para.append(line)

    assert para is None

    return paras

    # such as:  "  a\n    b\n  c\n"  ->  [['  a', '    b', '  c']]


#
# Rip out a small Py Prog on ArgDoc, or a less small Py Prog on ArgParse
#


def rip_py_on_argdoc(parser):
    """Rip a Py Prog that runs on ArgDoc to form and run the Parser"""

    doc = parser.format_help().rstrip()

    chars = pychars_fabricate(doc, prog=parser.prog)

    return chars

    # TODO: test how Black our Python on ArgDoc style is


def rip_whole_parser_from_doc(doc, path):
    """Compile an ArgumentParser out of the Doc"""

    paras = textwrap_split_paras(doc)

    alt_doc = doc
    if len(paras) < 2:  # 1 paragraph of Usage, 1 paragraph of Desc
        alt_doc = "usage: null\n\ndo stuff"
        if path is not None:
            alt_doc = "usage: {}\n\ndo stuff".format(os.path.basename(path))

    drop_help = not parser_add_help_from_doc(doc=alt_doc)
    epi = parser_epi_from_doc(alt_doc)

    parser = parser_from_doc(doc=alt_doc, drop_help=drop_help, epi=epi)
    parser_adds_from_doc(parser, doc=alt_doc)

    return parser


def rip_py_on_argparse(parser):
    """Rip a whole Py Prog that runs on ArgParse to form and run the Parser"""

    doc = parser.format_help().rstrip()

    pylines = rip_pylines_on_argparse(parser)

    with_main_doc = __main__.__doc__
    __main__.__doc__ = doc  # only needed at 'epilog = doc[epi_at:]'
    try:
        parser_exit_unless_exec_eq(parser, pychars="\n".join(pylines))
    finally:
        __main__.__doc__ = with_main_doc

    pychars = pychars_fabricate(doc, prog=parser.prog, lines=pylines)

    return pychars

    # TODO: test how Black our Python on ArgParse style is


def rip_pylines_on_argparse(parser):
    """Rip a Py Prog that runs on ArgParse to form the Parser without running it"""

    pylines1 = argparse_pylines_epi_twice(parser)
    pylines2 = argparse_pylines_epi_index(parser)

    assert pylines1 is not None
    if pylines2 is None:

        return pylines1

    if (len(pylines2) + 1) < len(pylines1):

        return pylines2

    return pylines1

    # keep it at flat 'pylines1' til plainly shorter after adding 'import __main__'


def argparse_pylines_epi_twice(parser):
    """Rip a Py Prog that declares Epilog twice to run on ArgParse"""

    dent = "    "

    rep_epilog = parser.epilog
    if parser.epilog is not None:
        rep_epilog = black_repr_doc(text=parser.epilog)
        rep_epilog = ("\n" + dent + dent).join(rep_epilog.splitlines())
        rep_epilog = "\n".join(_.rstrip() for _ in rep_epilog.splitlines())
        rep_epilog = "textwrap.dedent(\n" + dent + dent + rep_epilog + "\n" + dent + ")"

    pylines = list()

    pylines.append("parser = argparse.ArgumentParser(")
    pylines.append("    prog={},".format(black_repr(parser.prog)))
    pylines.append("    description={},".format(black_repr(parser.description)))
    pylines.append("    add_help={},".format(parser.add_help))
    pylines.append("    formatter_class=argparse.RawTextHelpFormatter,")
    pylines.append("    epilog={},".format(rep_epilog))
    pylines.append(")")

    argparse_add_pylines_args_options(parser, pylines)

    pylines = "\n".join(pylines).splitlines()

    return pylines


def argparse_pylines_epi_index(parser):
    """Rip a Py Prog that finds Epilog in the Main Doc to run on ArgParse"""

    # Give up if it's difficult

    if parser.epilog is None:

        return None

    stripped = parser.epilog.strip()
    if not stripped:

        return None

    doc = parser.format_help()
    epi = stripped.splitlines()[0]

    if epi not in doc:

        return None

    alt_epilog = doc[doc.index(epi) :].strip()
    if alt_epilog != stripped:

        return None

    # Make it so

    pylines = list()

    pylines.append("doc = __main__.__doc__")
    pylines.append("epi_at = doc.index({})".format(black_repr(epi)))
    pylines.append("epilog = doc[epi_at:]")

    pylines.append("")
    pylines.append("parser = argparse.ArgumentParser(")
    pylines.append("    prog={},".format(black_repr(parser.prog)))
    pylines.append("    description={},".format(black_repr(parser.description)))
    pylines.append("    add_help={},".format(parser.add_help))
    pylines.append("    formatter_class=argparse.RawTextHelpFormatter,")
    pylines.append("    epilog=epilog,")
    pylines.append(")")

    argparse_add_pylines_args_options(parser, pylines)

    pylines = "\n".join(pylines).splitlines()

    return pylines


def argparse_add_pylines_args_options(parser, pylines):
    """Rip the Py Lines for adding Args and Options"""

    for action in parser._get_positional_actions():  # pylint: disable=protected-access
        action_pychars = rip_py_arg_action(action)
        assert action_pychars is not None

        pylines.append("")
        pylines.extend(action_pychars.splitlines())

    for action in parser._get_optional_actions():  # pylint: disable=protected-access
        if not parser_action_is_from_add_help(parser, action=action):
            action_pychars = rip_py_option_action(parser, action=action)
            if action_pychars is not None:

                pylines.append("")
                pylines.extend(action_pychars.splitlines())


def rip_py_arg_action(action):
    """Rip a Py Fragment that runs on ArgParse to add this one Positional Arg"""

    pylines = list()

    pylines.append("parser.add_argument(")
    pylines.append("    {},".format(black_repr(action.dest)))
    if action.metavar is not None:
        pylines.append("    metavar={},".format(black_repr(action.metavar)))
    if action.nargs is not None:
        pylines.append("    nargs={},".format(black_repr(action.nargs)))
    if action.help is not None:
        pylines.append("    help={},".format(black_repr(action.help)))
    pylines.append(")")

    oneline = " ".join(_.strip() for _ in pylines[1:-1]).rstrip(",")
    oneline = "parser.add_argument({})".format(oneline)
    if len(oneline) < _89_COLUMNS:

        return oneline

    chars = "\n".join(pylines)

    return chars


def parser_action_is_from_add_help(parser, action):
    """Say if an Action is the Action from Parser Add Help"""

    if action.option_strings == ["-h", "--help"]:
        if action.help == "show this help message and exit":
            if action.nargs == 0:  # this bit? not well-doc'ed

                if parser.add_help:

                    return True

    return False


def rip_py_option_action(parser, action):
    """Rip a Py Fragment that runs on ArgParse to add this one Option"""

    _ = parser

    pylines = list()

    pylines.append("parser.add_argument(")

    for opt in action.option_strings:
        pylines.append("    {},".format(black_repr(opt)))

    if action.metavar is not None:
        pylines.append("    metavar={},".format(black_repr(action.metavar)))

    if type(action).__name__ == "_CountAction":
        assert action.nargs == 0
        pylines.append("    action={},".format(black_repr("count")))
        assert str(action.default) == "0"
    elif action.nargs is not None:
        assert action.default in (None, False)
        pylines.append("    nargs={},".format(black_repr(action.nargs)))

    if action.default is not None:
        assert action.default in (False, 0), repr(action.default)
        pylines.append("    default={},".format(action.default))

    if action.help is not None:
        pylines.append("    help={},".format(black_repr(action.help)))

    pylines.append(")")

    oneline = " ".join(_.strip() for _ in pylines[1:-1]).rstrip(",")
    oneline = "parser.add_argument({})".format(oneline)
    if len(oneline) < _89_COLUMNS:

        return oneline

    chars = "\n".join(pylines)

    return chars


#
# Rip Add_Argument calls out from the Command Line
#


def rip_py_add_patch(parser, path, words, pychars):
    """Rip a Py Patch to add one Arg or Option, to Python that runs on ArgParse"""

    try:

        patcher = _patcher_from_words(words)
        alt_pychars = _patcher_patch_parser(patcher, parser=parser)
        diffchars = _patcher_diff_patch(path, pychars=pychars, alt_pychars=alt_pychars)

    except argparse.ArgumentError as exc:
        stderr_print("{}: {}".format(type(exc).__name__, exc))

        sys.exit(1)  # exit 1 to require compatible patch

    return diffchars


def _patcher_from_words(words):
    """Take the Words after "--" from an ArgDoc Py Command Line, to choose a Patch"""

    assert words

    # Round off common variations in how Shells quote Args of ArgDoc Py

    alt_joined = " ".join(words)
    if alt_joined.startswith("[-") and alt_joined.endswith("]"):
        alt_joined = alt_joined[len("[") : -len("]")]  # keep '-', strip 1 '[' and 1 ']'

    alt_words = alt_joined.split()

    # Look to add one or two Dests

    dests = list()
    alt_metavar = None  # cut roughly from Words here, then cut well apart from NArgs

    alt_index = 0
    for looks in range(2):

        if not alt_words[alt_index:]:

            break

        word = alt_words[alt_index]
        dest = word.split(",")[0]
        if looks and not dest.startswith("-"):

            break

        # Pick out the positional ARG, or the first Option, or the second Option

        alt_index += 1

        if not dest.startswith("-"):
            alt_metavar = word

            break

        dests.append(dest)

        # Pick out a MetaVar from the first Option, from the second, or from both
        # Gloss over whether the MetaVar is spelled twice, and forget the first spelling

        if alt_index < len(alt_words):
            next_word = alt_words[alt_index]
            if next_word.endswith(","):
                alt_metavar = next_word.split(",")[0]
                alt_index += 1
            elif len(next_word) >= 2:
                if next_word[:2] == next_word[:2].upper() != next_word[:2].lower():
                    alt_metavar = next_word
                    alt_index += 1

    # Pick NArgs out of Metavar

    (metavar, nargs, index) = _parser_choose_metavar_nargs_index(
        alt_words, dests, alt_metavar=alt_metavar, alt_index=alt_index
    )

    # Pick Help

    help_else = _parser_choose_help(alt_words, index=index)

    # Succeed

    patcher = argparse.Namespace(
        dests=dests,
        metavar=metavar,
        nargs=nargs,
        help_else=help_else,
    )

    return patcher


def _parser_choose_metavar_nargs_index(alt_words, dests, alt_metavar, alt_index):
    """Pick NArgs out of Metavar"""

    word0 = alt_words[0]
    word1 = alt_words[1] if alt_words[1:] else None
    word2 = alt_words[2] if alt_words[2:] else None

    # Pick Nargs out of an Arg Metavar

    if (not dests) and word0.startswith("[") and word0.endswith("]"):
        assert alt_metavar == word0, (alt_metavar, word0)

        metavar = word0[len("[") : -len("]")]
        nargs = "?"  # argparse.OPTIONAL
        index = 1  # from usage: [ARG]

    elif word0.startswith("[") and word1 == "...]":
        assert alt_metavar == word0, (alt_metavar, word0)

        metavar = word0[len("[") :]
        nargs = "*"  # argparse.ZERO_OR_MORE
        index = 2  # from usage: [ARG ...]

    elif word1 == "...":
        assert alt_metavar == word0, (alt_metavar, word0)

        metavar = word0
        nargs = "+"  # argparse.ONE_OR_MORE
        index = 2  # from unconventional usage: ARG ...

    elif (word1 == ("[" + word0)) and (word2 == "...]"):
        assert alt_metavar == word0, (alt_metavar, word0)

        metavar = word0
        nargs = "+"  # argparse.ONE_OR_MORE
        index = 3  # from usage: ARG [ARG ...]

    elif word0.startswith("[") and (word0 == word1) and (word2 == "...]]"):
        assert alt_metavar == word0, (alt_metavar, word0)

        metavar = word0[len("[") :]
        nargs = "*"  # argparse.ZERO_OR_MORE
        index = 3  # from classical usage: [ARG [ARG ...]]

    # Or pick Nargs out of an Option Metavar

    elif alt_metavar and alt_metavar.startswith("[") and alt_metavar.endswith("]"):

        metavar = alt_metavar[len("[") : -len("]")]
        nargs = "?"  # argparse.OPTIONAL
        index = alt_index  # from usage: -o [OPT], --option [OPT], etc

    # Else take Metavar and/or Dests without NArgs

    else:

        metavar = alt_metavar
        nargs = None
        index = alt_index  # from usage: OPT, -o, --option, -o OPT, --option OPT, etc

    # Force the Metavar into Uppercase

    metavar = None if (metavar is None) else metavar.upper()

    # Succeed

    return (metavar, nargs, index)


def _parser_choose_help(alt_words, index):
    """Take all the remain Word's as help (and respect Space's inside the Word's)"""

    help_tail = " ".join(alt_words[index:])
    if not alt_words[index:]:
        help_tail = " ".join(_.lstrip("-") for _ in alt_words)
        help_tail = help_tail.replace("[", "").replace("]", "")
        help_tail = help_tail.title()

    help_else = help_tail if help_tail else None

    return help_else


def _patcher_patch_parser(patcher, parser):
    """Patch the Parser, rip it back as Python"""

    dests = patcher.dests
    metavar = patcher.metavar
    nargs = patcher.nargs
    help_else = patcher.help_else

    # Add the Arg or Option to the Parser, with/ without Metavar and Help

    if not dests:
        dest = plural_en(metavar.lower()) if (nargs in ("+", "*")) else metavar.lower()

        parser.add_argument(dest, metavar=metavar, nargs=nargs, help=help_else)

    elif len(dests) == 1:
        assert dests[0].startswith("-")

        if metavar is None:
            assert nargs is None, nargs
            default = 0  # for 'action="count"'
            parser.add_argument(
                dests[0], action="count", default=default, help=help_else
            )
        else:
            default = False if (nargs == "?") else None
            parser.add_argument(
                dests[0], metavar=metavar, nargs=nargs, default=default, help=help_else
            )

    else:
        assert len(dests) == 2, dests

        assert dests[0].startswith("-")
        assert dests[-1].startswith("-")

        if metavar is None:
            assert nargs is None, nargs
            default = 0  # for 'action="count"'
            parser.add_argument(
                dests[0], dests[1], action="count", default=default, help=help_else
            )
        else:
            default = False if (nargs == "?") else None
            parser.add_argument(
                dests[0],
                dests[1],
                metavar=metavar,
                nargs=nargs,
                default=default,
                help=help_else,
            )

    # Require that we rip an equal Parser from the Doc from the patched Parser

    alt_parser = ArgumentParser(doc=parser.format_help())
    parser_require_eq(parser, alt_parser=alt_parser)

    # Rip the Parser back as Python

    alt_pychars = rip_py_on_argparse(parser)

    return alt_pychars


def _patcher_diff_patch(path, pychars, alt_pychars):
    """Diff the Python ripped from Parser before patching, vs after patching"""

    alt_path = os.devnull if (path is None) else path
    fromfile = "a" + os.sep + alt_path.lstrip(os.sep)
    tofile = "b" + os.sep + alt_path.lstrip(os.sep)

    a_lines = pychars.splitlines()
    b_lines = alt_pychars.splitlines()

    difflines = list(
        difflib.unified_diff(a=a_lines, b=b_lines, fromfile=fromfile, tofile=tofile)
    )
    diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

    return diffchars


#
# Work with an ArgumentParser compiled from the DocString of the Calling Module
#


def parse_args(args=None, namespace=None, doc=None):
    """
    Call 'argparse.parse_arg' on a Parser of the calling Module's DocString

    However,
    + mutate the given Namespace, if any, rather than creating a new Namespace
    + work instead from the given Doc, if any
    + print help and exit zero when Args call for Help
    + print diff and exit, if the Doc doesn't match the Parser it sketches
    """

    alt_argv = sys.argv[1:] if (args is None) else args

    f = inspect.currentframe()
    (alt_doc, alt_file) = module_find_doc_and_file(doc=doc, f=f)
    parser = ArgumentParser(doc=alt_doc)
    try:
        parser_exit_unless_doc_eq(parser, doc=alt_doc)  # Constrain Parse Args Doc
    except SystemExit:
        stderr_print(
            "{}: error: Doc doesn't match Parser compiled from Doc".format(
                os.path.basename(alt_file)
            )
        )

        raise

    alt_namespace = parser.parse_args(alt_argv, namespace=namespace)
    assert (not namespace) or (alt_namespace is namespace)

    return alt_namespace


# deffed in many files  # missing from docs.python.org
def module_find_doc_and_file(doc, f):
    """Take the Doc as from Main File, else pick the Doc out of the Calling Module"""

    module_doc = doc
    module_file = __main__.__file__  # kin to 'sys.argv[0]'

    if doc is None:
        module = inspect.getmodule(f.f_back)

        module_doc = module.__doc__
        module_file = f.f_back.f_code.co_filename

    return (module_doc, module_file)


def format_help():
    """Call 'argparse.format_help' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (alt_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=alt_doc)

    chars = parser.format_help()

    return chars


def print_help(file=None):
    """Call 'argparse.print_help' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (alt_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=alt_doc)

    parser.print_help(file=file)


def format_usage():
    """Call 'argparse.format_usage' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (alt_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=alt_doc)

    chars = parser.format_usage()

    return chars


def print_usage(file=None):
    """Call 'argparse.print_usage' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (alt_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=alt_doc)

    parser.print_usage(file=file)


class ArgumentParser(argparse.ArgumentParser):
    """Form an ArgumentParser with Args and Options and Epilog, from a Doc"""

    def __init__(self, doc=None, drop_help=None):

        # pylint: disable=super-with-arguments
        # pylint: disable=super-init-not-called

        # Pick the Doc to compile into an ArgumentParser

        f = inspect.currentframe()
        (alt_doc, _) = module_find_doc_and_file(doc=doc, f=f)

        # Form Self

        super_func = super(ArgumentParser, self).__init__
        untested_argument_parser_init(
            self, super_func=super_func, doc=alt_doc, drop_help=drop_help
        )

        # Require that Self is a Parser from which we can rip Source

        _ = rip_py_on_argparse(parser=self)


def untested_argument_parser_init(self, super_func, doc, drop_help):
    """Form an ArgumentParser from a Doc, but don't rip Python from it to test it"""

    paras = textwrap_split_paras(doc)
    paras = paras if paras[1:] else textwrap_split_paras("usage: prog\n\ndesc")

    # Pick the ArgParse Prog out of the top line

    usage_words = paras[0][0].split()
    prog = usage_words[1] if usage_words[1:] else "prog"

    # Pick the ArgParse Description out of the 2nd Paragraph of Doc

    description = " ".join(_.strip() for _ in paras[1])

    # Conclude ArgParse Help Option wanted, except if it's partly/ wholly missing

    add_help = not drop_help
    if drop_help is None:  # Also drop the ArgParse Help Option on request
        add_help = parser_add_help_from_doc(doc=doc)

    # Take up all the rest of the Doc as the ArgParse Epilog

    epilog = None
    epi = parser_epi_from_doc(doc)
    if epi:
        epilog_at = doc.index(epi)
        epilog = doc[epilog_at:]

    # Form an ArgumentParser with Epilog, but begin with no Args and no Options

    super_func(
        prog=prog,
        description=description,
        add_help=add_help,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    # Add zero or more Args and/or Options from the Doc

    parser_adds_from_doc(parser=self, doc=doc)


def parser_add_help_from_doc(doc):
    """Find the conventional H/ Help Option and return True, else False or None"""

    if doc is None:

        return None

    lines = doc.splitlines()
    for (index, line) in enumerate(lines):
        next_line = lines[index + 1] if lines[(index + 1) :] else ""
        next_rejoined = " ".join(next_line.split())

        rejoined = " ".join(line.split())
        if rejoined.startswith("-h, --help"):
            help_tail = "show this help message and exit"
            if rejoined.endswith(help_tail) or (next_rejoined == help_tail):

                return True

    return False


def parser_epi_from_doc(doc):
    """Pick the first Line of an ArgParse Epilog out of a Doc"""

    if doc is None:

        return None

    alt_doc = argparse_doc_upgrade(doc)
    paras = textwrap_split_paras(text=alt_doc)

    paras = paras[2:]  # Skip over Usage and Desc

    if paras:
        para = paras[0]
        if para[0].startswith("positional arguments"):

            paras = paras[1:]  # mutate

    if paras:
        para = paras[0]
        if para[0].startswith("options") or para[0].startswith("optional arguments"):

            paras = paras[1:]  # mutate

    if paras:
        para = paras[0]

        epi = para[0]

        return epi

    return None


#
# Help compile an ArgumentParser from a DocString
#


# deffed in many files  # missing from docs.python.org
def parser_from_doc(doc=None, drop_help=None, epi=None):
    """Form an ArgumentParser with Epilog, with no Args and no Options, from Doc"""

    f = inspect.currentframe()
    (module_doc, _) = module_find_doc_and_file(doc=doc, f=f)

    # Pick the ArgParse Prog, Description, & Epilog out of a Main Doc

    prog = module_doc.strip().splitlines()[0].split()[1]

    headlines = list(
        _ for _ in module_doc.strip().splitlines() if _ and not _.startswith(" ")
    )
    description = headlines[1]  # TODO: cope if ArgParse ever did wrap Desc Lines

    epilog = None
    if epi:
        epilog_at = module_doc.index(epi)
        epilog = module_doc[epilog_at:]

    # Form an ArgumentParser with Epilog, with no Args and no Options

    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=(not drop_help),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    # Succeed

    return parser


# deffed in many files  # missing from docs.python.org
def parser_exit_unless_doc_eq(parser, doc=None):
    """Exit nonzero, unless __main__.__doc__ equals 'parser.format_help()'"""

    f = inspect.currentframe()
    (module_doc, module_file) = module_find_doc_and_file(doc=doc, f=f)

    # Sketch where the Doc's came from

    fromfile = module_file
    fromfile = os.path.split(fromfile)[-1]
    fromfile = "{} --help".format(fromfile)

    tofile = "ArgumentParser(..."

    # Fetch the Parser Doc with Lines wrapped by a virtual Terminal of a fixed width

    with_columns = os.getenv("COLUMNS")  # often '!= os.get_terminal_size().columns'
    os.environ["COLUMNS"] = str(_89_COLUMNS)
    try:
        parser_doc = parser.format_help()
    finally:
        if with_columns is None:
            os.environ.pop("COLUMNS")
        else:
            os.environ["COLUMNS"] = with_columns

    # Cut the jitter in Doc from ArgParse evolving across Python 3, from Python 2

    fromdoc = argparse_doc_upgrade(doc=module_doc)
    todoc = argparse_doc_upgrade(doc=parser_doc)

    # Count significant differences between Doc's of ArgParse Help Lines

    diffchars = diff_fuzzed_else_complete(
        fromdoc=fromdoc, todoc=todoc, fromfile=fromfile, tofile=tofile
    )

    if diffchars:

        stderr_print(diffchars)  # '... --help' vs 'ArgumentParser(...'

        sys.exit(1)  # exit 1 to require Parser == Doc


# deffed in many files  # missing from docs.python.org
def argparse_doc_upgrade(doc):
    """Cut the jitter in Doc from ArgParse evolving across Python 3, from Python 2"""

    # Don't upgrade No Doc

    if doc is None:

        return None

    # Option to tighten up the comparison, by applying no Upgrade now

    if False:  # pylint: disable=using-constant-test

        return doc.strip()

    # Upgrade this copy of the Doc

    alt_doc = doc
    alt_doc = alt_doc.strip()
    alt_doc = textwrap_unwrap_first_paragraph(alt_doc)

    pattern = r" \[([A-Z]+) \[[A-Z]+ [.][.][.]\]\]"
    alt_doc = re.sub(pattern, repl=r" [\1 ...]", string=alt_doc)
    # TODO: think deeper into mixed case metavars, and into '.group(1) != .group(2)'

    alt_doc = alt_doc.replace("\noptional arguments:", "\noptions:")

    return alt_doc


def textwrap_unwrap_first_paragraph(text):
    """Join by single spaces all the leading lines up to the first empty line"""

    index = (text + "\n\n").index("\n\n")
    lines = text[:index].splitlines()
    chars = " ".join(_.strip() for _ in lines)
    alt_text = chars + text[index:]

    return alt_text


def diff_fuzzed_else_complete(fromdoc, todoc, fromfile, tofile):
    """Format Large, Small, or no Diffs as a string of lines joined by line-end"""

    # Look first for Large Diffs, then look again, but for Small Diffs

    for diff_precision in range(2):

        # When looking for Large Diffs

        fromlines = fromdoc.splitlines()
        tolines = todoc.splitlines()

        if (fromlines != tolines) and not diff_precision:

            # Compare from lists of words, ignoring leading/ trailing/ multiple Space's

            from_lists_of_words = list()
            for (index, fromline) in enumerate(fromlines):
                words = " ".join(fromline.split())
                from_lists_of_words.append(words)

            # Visit each fresh Line

            for (index, toline) in enumerate(tolines):
                words = " ".join(toline.split())
                if words in from_lists_of_words:

                    # Substitute the first matching Stale Line, if any

                    fromindex = from_lists_of_words.index(words)
                    fromline = fromlines[fromindex]

                    tolines[index] = fromline

        # Look for Large, else for Small, Diffs

        difflines = list(
            difflib.unified_diff(
                a=fromlines, b=tolines, fromfile=fromfile, tofile=tofile
            )
        )

        diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

        # Convert to Chars from Lines

        if difflines:

            assert diffchars, repr(difflines)

            return diffchars

    # Encode No Diffs found as an empty string

    return ""


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


#
# Supply one flat Py, as a template to copy-edit
#


EXAMPLE_ARGDOC_PY = r'''
    #!/usr/bin/env python3
    # -*- coding: utf-8 -*-

    """
    usage: null [-h]

    do good stuff

    options:
      -h, --help  show this help message and exit

    examples:
      Oh no! No examples disclosed!! 💥 💔 💥
    """  # : boom : broken_heart : boom :

    import sys

    import argdoc

    parser = argdoc.ArgumentParser()

    args = parser.parse_args()
    sys.stderr.write("{}\n".format(args))

    sys.stderr.write("{}\n".format(parser.format_usage().rstrip()))
    sys.stderr.write("null: error: not implemented\n")

    sys.exit(2)  # exit 2 to reject usage
    '''


def pychars_fabricate(doc=None, prog=None, lines=None):
    """Fetch the Source Chars of the EXAMPLE_ARGDOC_PY, after applying patches if any"""

    chars = textwrap.dedent(EXAMPLE_ARGDOC_PY).strip()

    if doc is not None:
        chars = pychars_replace_doc(chars, doc=doc)

    if prog is not None:
        chars = chars.replace("null:", "{}:".format(prog))

    if lines is not None:
        chars = pychars_replace_lines(chars, lines=lines)

    return chars


def pychars_replace_doc(chars, doc):
    """Replace the DocString with a quote of the Doc"""

    assert chars
    assert doc
    assert doc == doc.strip()

    mark = '"""'  # well known from inside EXAMPLE_ARGDOC_PY
    keepends_eq_true = True

    start = chars.index(mark)
    stop = chars.index(mark, start + 1) + len(mark)
    stop += len(chars[stop:].splitlines(keepends_eq_true)[0])

    alt = chars[:start] + black_repr_doc(text=doc) + "\n" + chars[stop:]

    return alt


def pychars_replace_lines(chars, lines):
    """Expand the 'argdoc.ArgumentParser' inline"""

    alt = chars

    # Say to import more than Sys from Python, if working below the level of Arg Doc

    repl = "\n" + "\n".join(lines) + "\n"

    imports = "__main__ argparse sys textwrap".split()
    if "__main__" not in repl:  # TODO: these if's wrongly accept quoted mentions
        imports.remove("__main__")
    if "textwrap" not in repl:
        imports.remove("textwrap")

    py_imports = "\nimport " + "\nimport ".join(imports) + "\n"

    # Apply some patches

    py1 = "\nimport sys\n"
    alt = alt.replace(py1, py_imports)  # mutate

    py2 = "\nimport argdoc\n\n"
    alt = alt.replace(py2, "\n")  # mutate

    py3 = "\nparser = argdoc.ArgumentParser()\n"
    start = alt.index(py3)
    stop = start + len(py3)
    alt = alt[:start] + repl + alt[stop:]  # mutate

    # Succeed

    return alt


def parser_exit_unless_exec_eq(parser, pychars):
    """Run the PyChars to produce an Alt Parser, and require that it's equal"""

    pyglobals = dict(__main__=__main__, argparse=argparse, textwrap=textwrap)
    pylocals = dict()
    exec(pychars, pyglobals, pylocals)  # pylint: disable=exec-used

    alt_parser = pylocals["parser"]
    parser_require_eq(parser, alt_parser=alt_parser)


def parser_require_eq(parser, alt_parser):
    """Require that two Parser's look the same to us"""

    parser_require_eq_doc(parser, alt_parser=alt_parser)
    parser_require_eq_rip(parser, alt_parser=alt_parser)


def parser_require_eq_doc(parser, alt_parser):
    """Require that two Parser's both print the same Doc"""

    doc_lines = parser.format_help().splitlines()
    alt_doc_lines = alt_parser.format_help().splitlines()

    difflines = list(
        difflib.unified_diff(
            a=doc_lines, b=alt_doc_lines, fromfile="ripped-doc", tofile="formed-doc"
        )
    )
    diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

    if diffchars:
        stderr_print(diffchars)  # 'ripped-doc' vs 'formed-doc'

    assert doc_lines == alt_doc_lines


def parser_require_eq_rip(parser, alt_parser):
    """Require that we rip the same Python from Both"""

    pylines = rip_pylines_on_argparse(parser)
    alt_pylines = rip_pylines_on_argparse(alt_parser)

    difflines = list(
        difflib.unified_diff(
            a=pylines, b=alt_pylines, fromfile="ripped", tofile="formed"
        )
    )
    diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

    if sys.version_info >= (3, 6):  # TODO: diff Python 2 sources

        if diffchars:
            stderr_print(diffchars)  # 'ripped' vs 'formed'

        assert pylines == alt_pylines


# deffed in many files  # missing from docs.python.org
def black_repr(text):
    """Format some Chars as Source Chars, in the Black Style of Python"""

    if text is None:

        return None

    assert text == str(text), repr(text)

    # Glance over the oneline Repr from Python

    repped = repr(text)

    q1 = repped[0]
    q2 = repped[-1]
    middle_repped = repped[1:][:-1]

    assert q1 == q2, (q1, q2)
    assert q1 in ("'", '"'), repr(q1)

    # Choose the Start Mark and End Mark from:  " ' r" r'

    q = '"' if ('"' not in middle_repped) else q1
    pychars = q + middle_repped + q

    if ("\\" in text) and not text.endswith("\\"):
        if '"' not in text:
            pychars = 'r"{}"'.format(text)
        elif "'" not in text:
            pychars = "r'{}'".format(text)

    # Require correct Eval

    evalled = ast.literal_eval(pychars)
    assert evalled == text, (text, pychars, evalled)

    return pychars


# deffed in many files  # missing from docs.python.org
def black_repr_doc(text):
    """Format some Chars as indented Source Chars, in the Black Style of Python"""

    if text is None:

        return None

    assert text == str(text), repr(text)

    alt_text = text.strip()
    lines = alt_text.splitlines()

    # Glance over the oneline Repr from Python

    repped = repr(alt_text)

    q1 = repped[0]
    q2 = repped[-1]
    middle_repped = repped[1:][:-1]

    assert q1 == q2, (q1, q2)
    assert q1 in ("'", '"'), repr(q1)

    # Choose the Start Mark and End Mark from:  """ ''' r""" r'''

    qqq = '"""' if ('"' not in middle_repped) else (q1 + q1 + q1)
    pychars = qqq + "\n" + "\n".join(repr(_)[1:][:-1] for _ in lines) + "\n" + qqq

    if ("\\" in alt_text) and not alt_text.endswith("\\"):
        if '"' not in alt_text:
            pychars = 'r"""\n{}\n"""'.format(alt_text)
        elif "'" not in alt_text:
            pychars = "r'''{}\n'''".format(alt_text)

    # Require correct Eval, but strip the PyChars for Python 2 Ast Literal Eval

    evalled = ast.literal_eval(pychars.strip())
    assert evalled == ("\n" + alt_text + "\n"), (alt_text, pychars, evalled)

    return pychars


#
# Run from the Terminal command line
#


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
