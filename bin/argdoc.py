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
        nargs="?",
        help="some python file begun by a docstring (often your main py file)",
    )

    parser.add_argument(
        "words",
        metavar="WORD",
        nargs="*",
        help="an arg to parse for the file, or a word of a line of docstring",
    )

    parser.add_argument(
        "--rip", metavar="SHRED", help="rip one of doc|argparse|argdoc|args|patch"
    )

    parser_exit_unless_doc_eq(parser)  # Require the Parser to match its Doc

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
    parser_exit_unless_doc_eq(parser2)

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

    drop_help = not parser_add_help_from_doc(doc=doc)
    epi = parser_epi_from_doc(doc)

    parser = parser_from_doc(doc, drop_help=drop_help, epi=epi)
    parser_adds_from_doc(parser, doc=doc)

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

    chars = rip_py_add_patch(parser, words=args.words, pychars=pychars)

    return chars


# deffed in many files  # missing from docs.python.org
def ast_literal_eval_py_doc(path):
    """Fetch the DocString from a Python Source File"""

    # Default to the EXAMPLE_ARGDOC_PY

    chars = pychars_fabricate()

    if path is not None:

        # Read the chosen File

        alt_path = "/dev/stdin" if (path == "-") else path
        try:
            with open(alt_path, "r") as reading:
                if reading.isatty():
                    stderr_print("Press ⌃D EOF to quit")  # or ⌃C SIGINT or ⌃\ SIGQUIT
                path_chars = reading.read()
        except OSError as exc:
            stderr_print("{}: {}".format(type(exc).__name__, exc))

            sys.exit(1)  # exit 1 to require input file found

        # Step away from our main example only when chosen File not empty

        if path_chars:

            chars = path_chars  # mutate

    doc = eval_doc_from_pychars(chars)

    return doc


def eval_doc_from_pychars(chars):
    """Pick the DocString out from the top of a File of Python Source Chars"""

    marks = ['"""', '"', "'''", "'", 'r"""', 'r"', "r'''", "r'"]

    # Skip over comments and blank lines

    pylines = chars.splitlines()
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

            pychars = mark1 + tail[start:end] + mark2
            evalled = ast.literal_eval(pychars)

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

    alt_doc = parser_doc_upgrade(doc)
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

    if para[0].startswith("options"):
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
        nargs = "?"
    elif "[{} ...]".format(metavar) in usage:
        dest = plural_en(metavar.lower())  # mutate
        nargs = "*"

    # Tell the Parser to add this Arg

    alt_help_tail = help_tail if help_tail else None
    alt_help_tail = alt_help_tail.replace("%", "%%") if alt_help_tail else None
    parser.add_argument(dest, metavar=metavar, nargs=nargs, help=alt_help_tail)


def parser_add_option_line(parser, usage, line):
    """Rip one Add_Argument Call of an Option or two from one Doc Line"""

    dests = list()
    help_tail = line.strip()

    words = line.split()
    for (index, word) in enumerate(words):
        if not word.startswith("-"):

            break

        dests.append(word.split(",")[0])
        after_word = help_tail.index(word) + len(word)

        help_tail = help_tail[after_word:].strip()  # mutate

        if index == 0:
            if not word.endswith(","):

                break

        if index >= 1:

            break

    if len(dests) in (1, 2):

        parser_add_option_dests(parser, usage=usage, dests=dests, help_tail=help_tail)


def parser_add_option_dests(parser, usage, dests, help_tail):
    """Rip one Add_Argument Call of an Option or Two from their names and help"""

    # Take mentions of Action or Metavar from first such Usage of any Option Name

    metavar = None
    nargs = None
    action = None

    for opt in dests:

        if "[{}]".format(opt) in usage:
            action = "count"

            break

        mark = "[{} ".format(opt)
        if mark in usage:
            metavar_usage_tail = usage[usage.index(mark) :]

            metavar_usage = metavar_usage_tail.split()[1]
            if metavar_usage.endswith("]"):
                metavar_usage = metavar_usage[: -len("]")]

            metavar = metavar_usage.replace("[", "").replace("]", "")

            break

    # Cut the Metavar out from leading the Help, if present

    if metavar is not None:
        maybe_metavar = "[{}]".format(metavar)
        if help_tail:
            help_word = help_tail.split()[0]
            if help_word in (metavar, maybe_metavar):

                nargs = "?" if (help_word == maybe_metavar) else None
                help_tail = help_tail[len(help_word) :].strip()  # mutate

    # Tell the Parser to add this Option

    option = argparse.Namespace(
        dests=dests, metavar=metavar, nargs=nargs, action=action
    )

    parser_add_option_call(parser, option=option, help_tail=help_tail)


def parser_add_option_call(parser, option, help_tail):
    """Tell the Parser to add this Option"""

    # Keep on working with many choices

    dests = option.dests
    metavar = option.metavar
    nargs = option.nargs
    action = option.action

    # Default to Arg False when NArgs "?", so that no Arg is distinct from Arg None
    # Default to Count up from False, so that the Int of Count is Int, not TypeError

    default = False if ((nargs == "?") or (action == "count")) else None

    # Call victory when Parser Add_Help already did add this Option

    if (dests == ["-h", "--help"]) and (metavar is None) and (nargs is None):
        if help_tail == "show this help message and exit":
            if action == "count":

                if parser.add_help:

                    return

    # Solve just a few cases

    assert len(dests) in (1, 2)
    if metavar is None:
        assert nargs is None
        assert action == "count"
    else:
        assert nargs in (None, "?")
        assert action is None

    # Call Add Argument once, to add one or two Option Strings

    alt_help_tail = help_tail if help_tail else None
    alt_help_tail = alt_help_tail.replace("%", "%%") if alt_help_tail else None

    if not metavar:

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
        assert not action

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
        plural = word + "es"  # diagnosis, diagnoses
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

    return plural

    # TODO: make the Plural_En choice of Dest easy for ArgDoc clients to override


def _plural_en_test():

    singulars = "vortex leaf basis appendix diagnosis criterion lorry lutz word".split()
    plurals = "vortices leaves bases appendices diagnoses criteria lorries lutzes words"

    guesses = " ".join(plural_en(_) for _ in singulars)
    assert guesses == plurals

    joke_singulars = "deer sheep".split()
    joke_plurals = "deers sheeps"

    joke_guesses = " ".join(plural_en(_) for _ in joke_singulars)
    assert joke_guesses == joke_plurals


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


def rip_py_on_argparse(parser):
    """Rip a Py Prog that runs on ArgParse to form and run the Parser"""

    doc = parser.format_help().rstrip()

    pylines = rip_pylines_on_argparse(parser)
    parser_exit_unless_exec_eq(parser, pychars="\n".join(pylines))

    pychars = pychars_fabricate(doc, prog=parser.prog, lines=pylines)

    return pychars


def rip_pylines_on_argparse(parser):
    """Rip a Py Prog that runs on ArgParse to form the Parser, without running it"""

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

    for action in parser._get_positional_actions():  # pylint: disable=protected-access
        action_pychars = rip_py_arg_action(action)
        assert action_pychars is not None

        pylines.append("")
        pylines.extend(action_pychars.splitlines())

    for action in parser._get_optional_actions():  # pylint: disable=protected-access
        action_pychars = rip_py_option_action(parser, action=action)
        if action_pychars is not None:

            pylines.append("")
            pylines.extend(action_pychars.splitlines())

            # never just:  -h, --help  show this help message and exit

    return pylines


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


def rip_py_option_action(parser, action):  # noqa C901 too complex (11)
    """Rip a Py Fragment that runs on ArgParse to add this one Option"""

    pylines = list()

    if action.option_strings == ["-h", "--help"]:
        if action.help == "show this help message and exit":
            if action.nargs == 0:  # this bit? not well-doc'ed

                if parser.add_help:

                    return None

    pylines.append("parser.add_argument(")

    for opt in action.option_strings:
        pylines.append("    {},".format(black_repr(opt)))

    if action.metavar is not None:
        pylines.append("    metavar={},".format(black_repr(action.metavar)))

    if type(action).__name__ == "_CountAction":
        assert action.nargs == 0
        pylines.append("    action={},".format(black_repr("count")))
    elif action.nargs is not None:
        pylines.append("    nargs={},".format(black_repr(action.nargs)))

    if action.default is not None:
        assert action.default is False, repr(action.default)
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


def rip_py_add_patch(parser, words, pychars):  # noqa C901 too complex (16)
    """Rip a Py Patch to add one Arg or Option, to Python that runs on ArgParse"""

    patcher = _parser_patch_words(words)
    diffchars = _parser_diff_patch(parser, patcher=patcher, pychars=pychars)

    return diffchars


def _parser_patch_words(words):
    """Take the Words after "--" from an ArgDoc Py Command Line, to choose a Patch"""

    assert words
    alt_words = " ".join(words).split()

    # Look to add one or two Dests

    dests = list()
    metavar = None

    index = 0
    for looks in range(2):

        if not alt_words[index:]:

            break

        word = alt_words[index]
        dest = word.split(",")[0]
        if looks and not dest.startswith("-"):

            break

        # Pick out the positional ARG, or the first Option, or the second Option

        index += 1

        if not dest.startswith("-"):
            metavar = word.upper()

            break

        dests.append(dest)

        # Pick out a MetaVar from the first Option, from the second, or from both
        # Gloss over whether the MetaVar is spelled twice, and forget the first spelling

        if index < len(alt_words):
            next_word = alt_words[index]
            if next_word.endswith(","):
                metavar = next_word.split(",")[0]  # mutate
                index += 1
            elif len(next_word) >= 2:
                if next_word[:2] == next_word[:2].upper() != next_word[:2].lower():
                    metavar = next_word  # mutate
                    index += 1

    # Pick NArgs out of Metavar

    (metavar, nargs, index) = _parser_choose_metavar_nargs_index(
        alt_words, index=index, metavar=metavar
    )

    # Pick Help

    help_else_none = _parser_choose_help(alt_words, index=index)

    # Succeed

    patcher = argparse.Namespace(
        alt_words=alt_words,
        dests=dests,
        metavar=metavar,
        nargs=nargs,
        help_else_none=help_else_none,
    )

    return patcher


def _parser_choose_metavar_nargs_index(alt_words, index, metavar):
    """Pick NArgs out of Metavar"""

    word0 = alt_words[index - 1]
    word1 = alt_words[index] if alt_words[index:] else None
    word2 = alt_words[index + 1] if alt_words[(index + 1) :] else None

    nargs = None
    if word0.startswith("[") and word0.endswith("]"):
        assert metavar == word0
        metavar = metavar[len("[") : -len("]")]
        nargs = "?"
    elif word0.startswith("[") and word1 == "...]":
        assert metavar == word0
        metavar = metavar[len("[") :]
        index += 1
        nargs = "*"
    elif word0.startswith("[") and (word0 == word1) and (word2 == "...]]"):
        assert metavar == word0
        metavar = metavar[len("[") :]
        index += 2
        nargs = "*"

    return (metavar, nargs, index)


def _parser_choose_help(alt_words, index):
    """Take all the remain Word's as help (and respect Space's inside the Word's)"""

    help_tail = " ".join(alt_words[index:])
    if not alt_words[index:]:
        help_tail = " ".join(_.lstrip("-") for _ in alt_words[:index])
        help_tail = help_tail.replace("[", "").replace("]", "")
        help_tail = help_tail.title()

    help_else_none = help_tail if help_tail else None

    return help_else_none


def _parser_diff_patch(parser, patcher, pychars):
    """Patch the Parser, rip it back as Python, and Diff vs the Rip before Patch"""

    alt_words = patcher.alt_words
    dests = patcher.dests
    metavar = patcher.metavar
    nargs = patcher.nargs
    help_else_none = patcher.help_else_none

    # Add the Arg or Option to the Parser, with/ without Metavar and Help
    # Add the Arg or Option to the Parser, with/ without Metavar and Help

    if not dests:

        parser.add_argument(
            metavar.lower(), metavar=metavar, nargs=nargs, help=help_else_none
        )

    elif len(dests) == 1:

        if metavar is None:
            assert nargs is None, nargs
            parser.add_argument(dests[0], action="count", help=help_else_none)
        else:
            parser.add_argument(
                dests[0], metavar=metavar, nargs=nargs, help=help_else_none
            )

    else:
        assert len(dests) == 2, dests

        if metavar is None:
            assert nargs is None, nargs
            parser.add_argument(dests[0], dests[1], action="count", help=help_else_none)
        else:
            parser.add_argument(
                dests[0],
                dests[1],
                metavar=metavar,
                nargs=nargs,
                help=help_else_none,
            )

    # Diff the Parser before the Add, vs after the Add

    after_pychars = rip_py_on_argparse(parser)

    a_lines = pychars.splitlines()
    b_lines = after_pychars.splitlines()
    difflines = list(
        difflib.unified_diff(
            a=a_lines, b=b_lines, fromfile="", tofile=" ".join(alt_words)
        )
    )
    diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

    return diffchars


#
# Work with an ArgumentParser compiled from the DocString of the Calling Module
#


def format_usage():
    """Call 'argparse.format_usage' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (chosen_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=chosen_doc)

    chars = parser.format_usage()

    return chars


# deffed in many files  # missing from docs.python.org
def module_find_doc_and_file(doc, f):
    """Take the Doc as from Main File, else pick the Doc out of the Calling Module"""

    module_doc = doc
    module_file = __main__.__file__

    if doc is None:
        module = inspect.getmodule(f.f_back)

        module_doc = module.__doc__
        module_file = f.f_back.f_code.co_filename

    return (module_doc, module_file)


def parse_args(args=None, namespace=None, doc=None):
    """Call 'argparse.parse_arg' on a Parser of the calling Module's DocString"""

    chosen_args = sys.argv[1:] if (args is None) else args

    f = inspect.currentframe()
    (chosen_doc, _) = module_find_doc_and_file(doc=doc, f=f)
    parser = ArgumentParser(doc=chosen_doc)

    alt_namespace = parser.parse_args(chosen_args, namespace=namespace)
    assert (not namespace) or (alt_namespace is namespace)

    return alt_namespace


def print_usage(file=None):
    """Call 'argparse.format_usage' on a Parser of the calling Module's DocString"""

    f = inspect.currentframe()
    (chosen_doc, _) = module_find_doc_and_file(doc=None, f=f)
    parser = ArgumentParser(doc=chosen_doc)

    parser.print_usage(file=file)


class ArgumentParser(argparse.ArgumentParser):
    """Form an ArgumentParser with Args and Options and Epilog, from a Doc"""

    def __init__(self, doc=None, drop_help=None):

        # pylint: disable=super-with-arguments
        # pylint: disable=super-init-not-called

        # Pick the Doc to compile into an ArgumentParser

        f = inspect.currentframe()
        (chosen_doc, _) = module_find_doc_and_file(doc=doc, f=f)

        # Form Self

        super_func = super(ArgumentParser, self).__init__
        untested_argument_parser_init(
            self, super_func=super_func, doc=chosen_doc, drop_help=drop_help
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
        next_line = lines[index + 1] if ((index + 1) < len(lines)) else ""

        stripped = line.strip()
        if stripped.startswith("-h, --help"):
            help_tail = "show this help message and exit"
            if stripped.endswith(help_tail) or (next_line.strip() == help_tail):

                return True

    return False


def parser_epi_from_doc(doc):
    """Pick the first Line of an ArgParse Epilog out of a Doc"""

    if doc is None:

        return None

    alt_doc = parser_doc_upgrade(doc)
    paras = textwrap_split_paras(text=alt_doc)

    paras = paras[2:]  # Skip over Usage and Desc

    if paras:
        para = paras[0]
        if para[0].startswith("positional arguments"):

            paras = paras[1:]  # mutate

    if paras:
        para = paras[0]
        if para[0].startswith("options"):

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
    description = headlines[1]

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

    fromdoc = parser_doc_upgrade(doc=module_doc)
    todoc = parser_doc_upgrade(doc=parser_doc)

    # Count significant differences between Doc's of ArgParse Help Lines

    diffchars = diff_fuzzed_else_complete(
        fromdoc=fromdoc, todoc=todoc, fromfile=fromfile, tofile=tofile
    )

    if diffchars:

        stderr_print(diffchars)  # '... --help' vs 'ArgumentParser(...'

        sys.exit(1)  # exit 1 to require Parser == Doc


# deffed in many files  # missing from docs.python.org
def parser_doc_upgrade(doc):
    """Cut the jitter in Doc from ArgParse evolving across Python 3, from Python 2"""

    if doc is None:

        return None

    alt_doc = doc
    alt_doc = alt_doc.strip()
    alt_doc = textwrap_unwrap_one_paragraph(alt_doc)

    pattern = r" \[([A-Z]+) \[[A-Z]+ [.][.][.]\]\]"
    alt_doc = re.sub(pattern, repl=r" [\1 ...]", string=alt_doc)
    # TODO: think deeper into mixed case metavars, and into '.group(1) != .group(2)'

    alt_doc = alt_doc.replace("\noptional arguments:", "\noptions:")

    return alt_doc


def textwrap_unwrap_one_paragraph(text):
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

        if not diff_precision:

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
# Supply one Py as a template to copy-edit
#


EXAMPLE_ARGDOC_PY = r'''
    #!/usr/bin/env python3
    # -*- coding: utf-8 -*-

    """
    usage: null [-h]

    do good stuff

    optional arguments:
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

    py1 = "\nimport sys\n"
    alt = alt.replace(py1, "\nimport argparse\nimport sys\nimport textwrap\n")  # mutate

    py2 = "\nimport argdoc\n\n"
    alt = alt.replace(py2, "\n")  # mutate

    py3 = "\nparser = argdoc.ArgumentParser()\n"
    start = alt.index(py3)
    stop = start + len(py3)
    repl = "\n" + "\n".join(lines) + "\n"
    alt = alt[:start] + repl + alt[stop:]  # mutate

    return alt


def parser_exit_unless_exec_eq(parser, pychars):
    """Run the PyChars to produce an Alt Parser, and require that it's equal"""

    pyglobals = dict(argparse=argparse, textwrap=textwrap)
    pylocals = dict()
    exec(pychars, pyglobals, pylocals)  # pylint: disable=exec-used

    alt_parser = pylocals["parser"]
    parser_require_eq(parser, alt_parser=alt_parser)


def parser_require_eq(parser, alt_parser):
    """Require that two Parser's look the same to us"""

    pylines = rip_pylines_on_argparse(parser)
    alt_pylines = rip_pylines_on_argparse(alt_parser)

    difflines = list(
        difflib.unified_diff(
            a=pylines, b=alt_pylines, fromfile="ripped", tofile="formed"
        )
    )
    diffchars = "\n".join(_.splitlines()[0] for _ in difflines)

    if sys.version_info >= (3, 6):

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


# FIXME: why no error when Doc wrong inside:  bin/__p__.py


# copied from:  git clone https://github.com/pelavarre/pybashish.git
