#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: argdoc.py [-h] [-q] [-v] [--rip SHRED] [FILE] [-- [WORD [WORD ...]]]

parse command line args as doc'ced by a top-of-file arg docstring of help lines

positional arguments:
  FILE           the file begun by an arg docstring (often your main py file)
  WORD           an arg to parse for the file, or a word of a line of arg docstring

optional arguments:
  -h, --help     show this help message and exit
  -q, --quiet    say less
  -v, --verbose  say more
  --rip SHRED    rip to stdout one of doc|argparse|helpdoc|argdoc|args|patch

quirks:
  only the "doc" is the input, the other things you can rip are outputs
  plural args go to an english plural key, such as "[top [top ..]]" to ".tops"
  you lose your "-h" and "--help" options if you drop all "optional arguments:"
  you don't see review comments coming to work with you, till you try a damaged arg doc
  you can't mix more python into your argparse by inserting it into your arg doc

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "cat -"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  takes file "-" as meaning "/dev/stdin"

examples:

  argdoc.py -h                          # show this help message and exit
  argdoc.py                             # same as:  argdoc.py --rip argparse

  argdoc.py --rip argparse              # show an example argparse prog, don't run it
  argdoc.py --rip argdoc                # show an example argdoc prog, don't run it

  argdoc.py p.py                        # same as:  argdoc.py --rip argparse p.py
  argdoc.py --rip doc p.py              # rip and print the doc, don't run it

  argdoc.py --  -x, --extra  'do more'  # show the patch to add an optional counted arg
  argdoc.py --  -a ARG                  # show the patch to add an optional taken arg
  argdoc.py --  ARG                     # show the patch to add a positional arg

  argdoc.py --rip args p.py --          # parse no arg with the file's arg doc
  argdoc.py --rip args p.py --  --help  # parse the arg "--help" with the file's arg doc
  argdoc.py --rip args p.py --  hi you  # parse "hi you" with the file's arg doc
"""


from __future__ import print_function

import __main__
import argparse
import collections
import os
import pprint
import re
import shlex
import sys
import textwrap


class ArgDocError(Exception):
    pass


#
# Run as a command line:  ./argdoc.py ...
#


def main(argv):
    """Run a command line"""

    # Parse the command line

    taker = _CommandLineSyntaxTaker(argv)

    shred = taker.args.shred
    verbose = taker.args.verbose

    path = taker.args.file
    if taker.args.file == "-":
        path = "/dev/stdin"
        prompt_tty_stdin()

    # Pick apart one Arg Doc to produce one ArgumentParser Parser
    # except do obey "--rip doc|argparse|argdoc" commands to exit early

    ripper = ArgDocRipper(verbose=verbose)

    try:
        parser = ripper.make_argument_parser(doc=None, path=path)
    except ArgDocError as exc:
        stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)
    except Exception:
        stderr_print(
            "argdoc.py: error: unhandled exception at:  {}".format(taker.shline)
        )
        raise

    # Rip one thing or another

    if shred == "doc":
        sys.stdout.write(ripper.repr_file_doc + "\n")
    elif shred == "argparse":
        sys.stdout.write(ripper.ripped_argparse_py + "\n")
    elif shred == "helpdoc":
        sys.stdout.write(ripper.repr_help_doc + "\n")
    elif shred == "argdoc":
        sys.stdout.write(ripper.ripped_argdoc_py + "\n")

    elif shred == "args":
        argv = [ripper.file_path] + taker.args.words
        stderr_print("+ {}".format(shlex_join(argv)))

        args = parser.parse_args(argv[1:])
        pprint.pprint(vars(args))  # sorts "args" like "argparse.Namespace.str"

    # Else rip diff from parsing without new arg declaration, to with new arg

    else:
        assert shred == "patch"  # per other if-elif-shred

        raise NotImplementedError("you got --rip patch, did you mean --rip args")

        next_ripper = ripper.take_next_words(taker.args.words)

        diffed_files = ripper.rip_diff_argparse_py_files(next_ripper)
        sys.stdout.write(diffed_files + "\n")


class _CommandLineSyntaxTaker(argparse.Namespace):
    """Parse an ArgDoc command line"""

    def __init__(self, argv):
        """Call an ArgParse "parse_args" and then finish what it started"""

        # Name the client calling us

        self.shline = shlex_join(argv)

        # Option to comment in bootstrap

        # rip = "doc"
        # rip = "argparse"
        # rip = "argdoc"
        # rip = "args"
        # rip = "patch"
        # args = argparse.Namespace(file=None, rip=rip, quiet=0, verbose=0, words=[])

        # Begin to parse the command line

        args = parse_args(argv[1:])  # as if calling argdoc.parse_args

        self.args = args

        # Complete the parse of the command line

        args.verbose = args.verbose - args.quiet  # mutating
        args.verbose += 1  # mutating
        del args.quiet  # mutating

        args.file = os.devnull if (args.file is None) else args.file
        args.argv_separator = "--" if ("--" in argv[1:]) else None

        self._complete_args_file(argv=argv)
        self._complete_args_words(argv=argv)
        self._complete_args_shred()

    def _complete_args_file(self, argv):
        """Fix "args" when the arg "--" taken in place of FILE at [FILE] [-- ..."""

        args = self.args

        if argv[1:] and (argv[1] == "--") and args.file:
            assert args.file == argv[2]  # postcondition

            args.words = [args.file] + args.words  # mutating
            args.file = None

    def _complete_args_words(self, argv):
        """Complete the WORDS in usage: ... [-- [WORD [WORD ...]]]"""

        args = self.args

        if args.words and not args.argv_separator:
            stderr_print(format_usage().rstrip())
            stderr_print(  # a la standard error: unrecognized arguments
                "argdoc.py: error: unrecognized args: {!r}, in place of {!r}".format(
                    shlex_join(args.words), shlex_join(["--"] + args.words)
                )
            )
            sys.exit(2)  # exit 2 from rejecting usage

        return args

    def _complete_args_shred(self):
        """Complete the SHRED in usage: ... --rip SHRED"""

        args = self.args

        shred = None
        if not args.rip:

            shred = "patch" if args.argv_separator else "argparse"

        else:

            str_shreds = "doc|argparse|helpdoc|argdoc|args|patch"
            shreds = str_shreds.split("|")

            matching_shreds = list()
            for shred in shreds:
                if shred.startswith(args.rip):
                    matching_shreds.append(shred)

            if len(matching_shreds) == 1:
                shred = matching_shreds[0]

            if shred is None:
                stderr_print(
                    "argdoc.py: error: choose from --rip {}, do not choose {!r}".format(
                        str_shreds, args.rip
                    )
                )

                sys.exit(2)  # exit 2 from rejecting usage

        args.shred = shred


#
# Run as an imported module:  import argdoc
#


# "argdoc.format_help()" like to ArgParse "parser.format_help()"
def format_help():
    """Return the Arg Doc as a string of lines"""
    parser = ArgDocRipper(verbose=1).make_argument_parser()
    doc = parser.format_help()
    return doc


# "argdoc.format_usage()" like to ArgParse "parser.format_usage()"
def format_usage():
    """Return the Usage Line of the Arg Doc, including its trailing Line Sep"""
    parser = ArgDocRipper().make_argument_parser()
    usage = parser.format_usage()
    return usage


# "argdoc.parse_args" like to ArgParse "parser.parse_args(args, namespace)"
def parse_args(args=None, namespace=None, doc=None, path=None):
    """Parse Command Line Args as helped by a top-of-file Arg Docstring of Help Lines"""

    argv_tail = args  # accept argv[1:] from caller, else encode sys.argv[1:] as None

    ripper = ArgDocRipper(verbose=0)
    try:
        parser = ripper.make_argument_parser(doc, path=path)
    except ArgDocError as exc:
        stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)

    try:
        named_args = parser.parse_args(argv_tail, namespace=namespace)
        if not parser.add_help:
            if ripper.asking_for_help(named_args):
                parser.print_help()
                sys.exit(0)  # exit zero from printing help
    except SystemExit:
        ArgDocRipper(verbose=1).make_argument_parser(doc, path=path)
        raise

    return named_args


# "argdoc.print_help" like to ArgParse "parser.print_help(file)"
def print_help(file=None):
    """Print the Arg Doc to file, else to Stdout"""
    parser = ArgDocRipper(verbose=1).make_argument_parser()
    parser.print_help(file=file)


# "argdoc.print_usage" like to ArgParse "parser.print_usage(file)"
def print_usage(file=None):
    """Print the usage line to the file, else to Stdout"""
    parser = ArgDocRipper().make_argument_parser()
    parser.print_usage(file=file)


# "argdoc.ArgumentParser" like to ArgParse "ArgumentParser(description, epilog, ...)"
# FIXME FIXME: make this "class" not "def"
def ArgumentParser(doc=None, path=None):
    """Construct the ArgumentParser but don't run it now"""
    parser = ArgDocRipper().make_argument_parser()
    return parser


#
# Rip doc, or argparse parser source, or parser, or parsed args, or parser source diff
#


class ArgDocRipper(argparse.Namespace):
    """Parse Command Line Args as doc'ced by a top-of-file Arg Docstring of Help Lines"""

    def __init__(self, verbose=0):

        self.coder = _ArgDocCoder(verbose=verbose)
        self.verbose = verbose

    def make_argument_parser(self, doc=None, path=None):
        """Don't format help differently when Env Var COLUMNS=1 etc"""

        with_columns = os.environ.get("COLUMNS")
        if with_columns is None:
            parser = self._make_argument_parser(doc=doc, path=path)
        else:
            del os.environ["COLUMNS"]
            try:
                parser = self._make_argument_parser(doc=doc, path=path)
            finally:
                os.environ["COLUMNS"] = with_columns

        return parser

    def _make_argument_parser(self, doc=None, path=None):
        "Make an ArgumentParser from Arg Doc" ""

        coder = self.coder

        # Fetch the Arg Doc from Arg else from Path else from Main Module

        file_doc = self.fetch_file_doc(doc, path=path)
        file_path = self.file_path  # initted alongside .file_doc by .fetch_file_doc

        repr_file_doc = black_triple_quote_repr(file_doc.strip() + "\n")
        self.repr_file_doc = repr_file_doc

        # Translate the ripped Arg Doc to Python Source Calling ArgParse
        # Race ahead to run the Python Source to compare the bot's Help Doc to input

        parser_source = self.code_as_argparse(file_doc, file_path=file_path)

        parser = coder.exec_parser_source(parser_source)
        help_doc = parser.format_help()
        repr_help_doc = black_triple_quote_repr(help_doc.strip() + "\n")

        self.parser = parser
        self.help_doc = help_doc
        self.repr_help_doc = repr_help_doc

        if file_doc.strip():
            self.compare_file_to_help_doc(
                file_doc, help_doc=help_doc, file_path=file_path
            )

        # Translate the Arg Doc to whole example Python programs

        parser_doc = file_doc
        if not file_doc.strip():
            parser_doc = help_doc

        ripped_argparse_py = self.rip_argparse_py(
            parser_source, parser_doc=parser_doc, file_path=file_path
        )

        ripped_argdoc_py = self.rip_argdoc_py(help_doc, file_path=file_path)

        self.ripped_argparse_py = ripped_argparse_py
        self.ripped_argdoc_py = ripped_argdoc_py

        # Succeed

        return parser

    def fetch_file_doc(self, doc, path):
        """Fetch the Arg Doc from Arg else from Path else from Main Module"""

        main_doc = __main__.__doc__
        main_file = __main__.__file__

        file_doc = doc
        file_path = path

        if doc is not None:
            if path is None:
                file_path = os.devnull
        else:
            if path is None:
                file_doc = main_doc if main_doc else ""
                file_path = main_file
            else:
                file_doc = self.read_eval_docstring_from(path)
                file_path = path

        assert file_doc is not None
        assert file_path is not None

        self.file_doc = file_doc
        self.file_path = file_path

        return file_doc

    def read_eval_docstring_from(self, path):
        """Fetch the leading Docstring from a file of Python source"""

        try:
            with open(path) as incoming:
                chars = incoming.read()  # TODO: read what's needed, not whole file
        except IOError as exc:  # such as Python 3 FileNotFoundError
            stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)

        stripped_repr_doc = take_docstring_of(chars).strip()

        if chars:

            if not stripped_repr_doc:
                qqq1 = '"""'
                qqq2 = "'''"
                verbose_print(
                    self.verbose,
                    "argdoc.py: warning: found no {} and found no {} in {}".format(
                        qqq1, qqq2, path
                    ),
                )

            if stripped_repr_doc and not stripped_repr_doc.startswith("r"):
                if "\\" in stripped_repr_doc:
                    qqq = stripped_repr_doc[:3]
                    verbose_print(
                        self.verbose,
                        "argdoc.py: warning: "
                        "docstring of backslash led by {} not by r{} in {}".format(
                            qqq, qqq, path
                        ),
                    )

        doc = ""
        if stripped_repr_doc:
            doc = eval(stripped_repr_doc)

        return doc

    def code_as_argparse(self, file_doc, file_path):
        """Rip the argparse source to make the parser"""

        coder = self.coder
        parser_source = coder.compile_parser_source_from(file_doc, file_path=file_path)

        self.parser_source = parser_source

        return parser_source

    def rip_argparse_py(self, parser_source, parser_doc, file_path):
        """Say how to call ArgParse to parse Args in the way of the Arg Doc"""

        lines_by_key = collections.defaultdict(list)

        # Pick apart the Example Source

        self._split_argparse_example(lines_by_key)

        # Pick apart the Parser Doc

        key = "parser_doc"
        repr_parser_doc = black_triple_quote_repr(parser_doc.strip())
        lines_by_key[key].extend(repr_parser_doc.splitlines())

        # Pick apart the Parser Source  # FIXME: less brittle

        self._split_parser_source(lines_by_key, parser_source=parser_source)

        # Adapt the Example Parser  # FIXME: less brittle

        self._merge_parsers(lines_by_key)

        # Pick and choose the sourcelines to keep

        lines = list()
        # lines.append("--".join(lines_by_key.keys()).upper())
        # lines.append("<<HEAD>>")
        lines.extend(lines_by_key["head"])
        # lines.append("<<PARSER_DOC>>")
        lines.extend(lines_by_key["parser_doc"])
        # lines.append("<<MIDDLE>>")
        lines.extend(lines_by_key["middle"])
        # lines.append("<<MERGED_PARSER>>")
        lines.extend(lines_by_key["merged_parser"])
        # lines.append("<<MADE_TAIL>>")
        lines.extend(lines_by_key["made_tail"])
        # lines.append("<<TAIL>>")
        lines.extend(lines_by_key["tail"])
        # lines.append("<<EOF>>")

        # Succeed

        joined_lines = "\n".join(lines) + "\n"

        prog = parser_doc.strip().splitlines()[0].split()[1]  # usage: prog ...
        repl = "{}:".format(prog)
        ripped_argparse_py = joined_lines.replace("null:", repl)

        self.ripped_argparse_py = ripped_argparse_py

        return ripped_argparse_py

    def _split_argparse_example(self, lines_by_key):
        '''Feed the ArgParse Example into "lines_by_key"'''

        coder = self.coder

        epilog = coder.epilog
        epilog_keys = epilog.strip().splitlines()
        epilog_key = epilog_keys[0] if epilog_keys else ""
        repr_epilog_key = black_repr(epilog_key)

        d4 = r"    "

        key = "head"
        for line in ARGPARSE_EXAMPLE.strip().splitlines():
            stripped = line.strip()

            if stripped.startswith(r'"""'):
                if key == "head":
                    key = "example_docstring"
                    # fall through, do not continue, here
                else:
                    lines_by_key[key].append(line)
                    key = "middle"
                    continue
            elif stripped.startswith(r"epilog_at = "):
                merged_line = r"epilog_at = doc.index({})".format(repr_epilog_key)
                lines_by_key[key].append((d4 + merged_line).rstrip())
                continue
            elif stripped.startswith(r"epilog = "):
                if not epilog_key:
                    merged_line = r"""epilog = None  # = doc.index("...")"""
                    lines_by_key[key].append((d4 + merged_line).rstrip())
                    continue
                # fall through, do not continue, here
            elif stripped.startswith(r"parser = argparse.ArgumentParser("):
                key = "example_parser"
                # fall through, do not continue, here
            elif stripped == r")":
                lines_by_key[key].append(line)
                key = "tail"
                continue

            lines_by_key[key].append(line)

    def _split_parser_source(self, lines_by_key, parser_source):
        '''Feed the Parse Source into "lines_by_key"'''

        d4 = r"    "

        key = "made_head"
        for line in parser_source.strip().splitlines():
            stripped = line.strip()

            if stripped.startswith(r"parser = argparse.ArgumentParser"):
                key = "made_parser"
            elif stripped == r")":
                lines_by_key[key].append((d4 + line).rstrip())
                key = "made_tail"
                continue

            lines_by_key[key].append((d4 + line).rstrip())

    def _merge_parsers(self, lines_by_key):
        '''Merge the "made_parser" into the "example_parser"'''

        to_key = "merged_parser"
        made_parser_lines = lines_by_key["made_parser"]

        parser_eqs = 0
        progs = 0
        add_helps = 0

        for (index, line) in enumerate(lines_by_key["example_parser"]):
            stripped = line.strip()

            merged_line = line

            if stripped.startswith(r"parser = argparse.ArgumentParser("):
                parser_eqs += 1

                merged_line = self._find_one_startswith(
                    made_parser_lines, leftmost=r"parser = argparse.ArgumentParser("
                )

                assert merged_line  # for the 'copied from' comment

            elif stripped.startswith(r"add_help="):
                add_helps += 1

                merged_line = self._find_one_startswith(
                    made_parser_lines, leftmost=r"add_help="
                )

                assert merged_line

            lines_by_key[to_key].append(merged_line)

            if stripped.startswith(r"prog="):
                progs += 1

                made_line = self._find_one_startswith(
                    made_parser_lines, leftmost=r"usage="
                )

                if made_line:
                    lines_by_key[to_key].append(made_line)

        assert parser_eqs == 1
        assert progs == 1
        assert add_helps <= 1

    def _find_one_startswith(self, iterable, leftmost):
        """Find one, or None, but never more"""

        some = list(_ for _ in iterable if _.strip().startswith(leftmost))

        if not some:
            return None

        assert len(some) == 1
        one = some[0]
        return one

    def rip_argdoc_py(self, help_doc, file_path):
        """Say how to call ArgDoc to parse Args in the way of the Arg Doc"""

        lines_by_key = collections.defaultdict(list)

        # Pick apart the Example Source

        key = "head"
        for line in ARGDOC_EXAMPLE.strip().splitlines():
            stripped = line.strip()

            if stripped.startswith(r'"""'):
                if key == "head":
                    key = "example_docstring"
                else:
                    lines_by_key[key].append(line)
                    key = "tail"
                    continue

            lines_by_key[key].append(line)

        # Pick apart the Help Doc

        key = "help_doc"
        repr_help_doc = black_triple_quote_repr(help_doc.strip())
        lines_by_key[key].extend(repr_help_doc.splitlines())

        # Pick and choose the sourcelines to keep

        lines = list()
        lines.extend(lines_by_key["head"])
        lines.extend(lines_by_key["help_doc"])
        lines.extend(lines_by_key["tail"])

        # Succeed

        joined_lines = "\n".join(lines) + "\n"

        prog = help_doc.strip().splitlines()[0].split()[1]  # usage: prog ...
        repl = "{}:".format(prog)
        ripped_argdoc_py = joined_lines.replace("null:", repl)

        self.ripped_argdoc_py = ripped_argdoc_py

        return ripped_argdoc_py

    def compare_file_to_help_doc(self, file_doc, file_path, help_doc):
        """Show the Help Doc printed by an Arg Doc file calling Arg Parse"""

        file_doc = file_doc.replace("\noptional arguments:", "\noptions:")
        help_doc = help_doc.replace("\noptional arguments:", "\noptions:")
        # TODO:  Accept Arg Doc Options change from Oct/2021 Python 3.10 more elegantly

        if file_doc.strip() == help_doc.strip():

            return

        file_doc_shline = "argdoc.py --rip doc {} >a".format(file_path)
        doc_help_shline = "argdoc.py --rip helpdoc {} >b".format(file_path)
        diff_urp_hline = "diff -urp a b"

        verbose_print(
            self.verbose,
            "argdoc.py: warning: doc vs help diffs at: {}".format(file_path),
        )
        verbose_print(
            self.verbose,
            "argdoc.py: diff details at:  {} && {} && {}".format(
                file_doc_shline, doc_help_shline, diff_urp_hline
            ),
        )

    def asking_for_help(self, args):
        '''Count args asking to "show this help message and exit"'''

        coder = self.coder

        asks = list(v for (k, v) in vars(args).items() if (k in coder.help_dests) and v)
        asked = len(asks)

        return asked


#
# Style some templates for ArgDoc and for ArgParse
#


ARGDOC_EXAMPLE = textwrap.dedent(
    r'''
    #!/usr/bin/env python
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


    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))

    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("null: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage
    '''
).strip()


ARGPARSE_EXAMPLE = textwrap.dedent(
    r'''
    #!/usr/bin/env python
    # -*- coding: utf-8 -*-

    """
    usage: null [-h]

    do good stuff

    optional arguments:
      -h, --help  show this help message and exit

    examples:
      Oh no! No examples disclosed!! 💥 💔 💥
    """  # : boom : broken_heart : boom :


    import __main__
    import argparse
    import sys


    def main(argv):
        """Run a command line"""

        doc = __main__.__doc__

        prog = doc.strip().splitlines()[0].split()[1]
        description = list(_ for _ in doc.strip().splitlines() if _)[1]
        epilog_at = doc.index("examples:")
        epilog = doc[epilog_at:]

        parser = argparse.ArgumentParser(  # copied from '/dev/null' by 'argdoc.py'
            prog=prog,
            description=description,
            add_help=True,
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=epilog,
        )

        args = parser.parse_args(argv[1:])
        sys.stderr.write("{}\n".format(args))

        main.args = args
        main.parser = parser

        sys.stderr.write("{}\n".format(parser.format_usage().rstrip()))
        sys.stderr.write("null: error: not implemented\n")
        sys.exit(2)  # exit 2 from rejecting usage


    if __name__ == "__main__":
        sys.exit(main(sys.argv))
        '''
).strip()


DEFAULT_EPILOG = textwrap.dedent(
    """
    examples:
      Oh no! No examples disclosed!! 💥 💔 💥
    """  # : boom : broken_heart : boom :
).strip()

assert DEFAULT_EPILOG in ARGDOC_EXAMPLE
assert DEFAULT_EPILOG in ARGPARSE_EXAMPLE
# TODO: pull DEFAULT_EPILOG from there


# TODO: test how black'ened its emitted style is
class _ArgDocCoder(argparse.Namespace):
    """Work up an ArgumentParser to match its Arg Doc"""

    def __init__(self, verbose):

        self.verbose = verbose

    def compile_parser_source_from(self, file_doc, file_path):
        """Compile an Arg Doc into Parse Source"""

        # Patch up the outliers with nothing so permanent as a temporary workaround

        ls_py_outlier = "ls.py"

        # Parse the Arg Doc

        parts = _ArgDocSyntax()
        taker = _ArgDocTaker(parts, doc=file_doc, verbose=self.verbose)
        taker.take_arg_doc_into(parts=parts)

        self.parts = parts

        self.help_dests = list()

        # Compile the arguments first, so as to construct a one line summary of usage
        # Don't mention duplicate "add_argument" "dest"s  # FIXME: maybe someday?

        args_py_lines = self.emit_arguments()
        args_emitted_usage = self.emitted_usage

        # Emit imports

        d4 = r"    "  # choose indentation

        lines = list()

        lines.append(r"#!/usr/bin/env python")
        lines.append(r"# -*- coding: utf-8 -*-")
        # <= dashed "utf-8" slightly more standard than skidded "utf_8"
        # per https://docs.python.org/3/library/codecs.html

        lines.append(r"import argparse")
        lines.append(r"import textwrap")
        lines.append(r"")

        # Open a call to the Parser constructor

        what = os.path.split(__file__)[-1]
        comment = r"  # copied from {!r} by {!r}".format(file_path, what)
        lines.append(r"parser = argparse.ArgumentParser({}".format(comment))

        # Name the app

        prog = parts.prog if parts.prog else os.path.split(file_path)[-1]
        self.emitted_prog = prog

        assert prog  # always give a prog name to ArgParse, don't let them guess
        repr_prog = black_repr(prog)
        lines.append(d4 + r"prog={repr_prog},".format(repr_prog=repr_prog))
        # FIXME: think into {what} in place of {what}.py, and more unusual prog names
        # assert prog == os.path.split(file_path)[-1]

        # Construct Usage from Prog and zero or more Broken Argument Lines

        emitted_usage = prog if (args_emitted_usage is None) else args_emitted_usage
        if prog == ls_py_outlier:  # FIXME FIXME: emit multiline usage
            ls_split = "\n{}".format(13 * (" "))
            emitted_usage = emitted_usage.replace(
                "[-F] ", "[-F]{}".format(ls_split)
            )  # old, new
            emitted_usage = emitted_usage.replace(
                "[--ascending] ", "[--ascending]{}".format(ls_split)
            )
            emitted_usage = emitted_usage.replace("[-r] ", "[-r]{}".format(ls_split))

        # Contrast the constructed summary with the given summary

        parts_usage = prog if (self.parts.usage is None) else self.parts.usage

        if parts_usage.split() != emitted_usage.split():
            verbose_print(
                self.verbose,
                "argdoc.py: warning: doc'ced usage: {}".format(parts_usage),
            )
            verbose_print(
                self.verbose,
                "argdoc.py: warning: emitted usage: {}".format(emitted_usage),
            )

        # Resort to bypassing the ArgParse constructor of Usage Lines, only when desperate

        if emitted_usage:
            if "..." in emitted_usage:
                lines.append(
                    d4 + r"usage={usage},".format(usage=black_repr(emitted_usage))
                )

        # Explain the App in one line, if possible

        description_line = parts.description_line
        if not file_doc:
            assert not parts.usage
            assert not parts.description_line
            description_line = "do good stuff"

        if parts.usage and not parts.description_line:
            verbose_print(
                self.verbose,
                "argdoc.py: warning: no one line description explains prog {!r}".format(
                    prog
                ),
            )

        if description_line:
            lines.append(
                d4
                + r"description={repr_description},".format(
                    repr_description=black_repr(description_line)
                )
            )

        # Explicitly override the conventional help optional argument, or explicitly don't

        add_help = bool(parts.add_help)
        if not file_doc:
            assert parts.add_help is None
            add_help = True

        self.coder_added_help = add_help

        lines.append(d4 + r"add_help={add_help},".format(add_help=add_help))

        # Stop ArgParse from aggressively incompetently resplitting text

        lines.append(d4 + r"formatter_class=argparse.RawTextHelpFormatter,")

        # Nudge people to give examples to explain how to call the App well

        epilog = DEFAULT_EPILOG if (parts.epilog_chars is None) else parts.epilog_chars
        self.epilog = epilog

        lines.append(d4 + r"epilog=textwrap.dedent(")
        for line in black_triple_quote_repr(epilog).splitlines():
            lines.append(d4 + d4 + line)
        lines.append(d4 + r"),")

        # Close the constructor

        lines.append(")")
        lines.append("")

        lines.extend(args_py_lines)

        # Succeed

        parser_source = "\n".join(_.rstrip() for _ in lines)

        return parser_source

    def emit_arguments(self):
        """Compile the Positionals and Optionals Parts of the Arg Doc"""

        parts = self.parts

        args_py_lines = list()

        # Emit one call to "add_argument" for each Positional argument

        self.args_py_phrases = list()
        positionals_py_phrases = self.args_py_phrases

        if parts.positionals_declarations:
            for positionals_declaration in parts.positionals_declarations:
                lines = self.emit_positional(positionals_declaration)
                assert lines
                args_py_lines.extend(lines)
                args_py_lines.append("")

        self.args_py_phrases = None

        # Emit one call to "add_argument" for each Optional argument
        # except emit the call for the Optional "-h, --help" argument only if "add_help=False,"

        self.args_py_phrases = list()
        optionals_py_phrases = self.args_py_phrases

        if parts.optionals_declarations:
            for optionals_declaration in parts.optionals_declarations:
                lines = self.emit_optional(optionals_declaration)
                if lines:  # if not arriving via "argparse.ArgumentParser.add_help"
                    args_py_lines.extend(lines)
                    args_py_lines.append("")

        self.args_py_phrases = None

        # Construct a one line summary of usage

        emitted_usage = None  # FIXME: py_phrases when not parts.prog
        if parts.prog:
            emitted_usage = " ".join(
                [parts.prog] + optionals_py_phrases + positionals_py_phrases
            )

        self.emitted_usage = emitted_usage

        return args_py_lines

    def emit_positional(self, positionals_declaration):
        """Compile an Arg Doc Positional argument line into Python source lines"""

        # Pick out source fragments

        metavar = positionals_declaration.arg_line.metavar
        nargs = positionals_declaration.arg_phrase.nargs

        usage_phrase = positionals_declaration.arg_phrase.format_usage_phrase()
        arg_help = positionals_declaration.arg_line.arg_help

        assert nargs in (None, "*", "?")  # .ZERO_OR_MORE .OPTIONAL

        # Name the attribute for this positional option in the namespace built by "parse_args"
        # Go with the metavar, else guess the English plural of the metavar

        dest = metavar.lower()
        if nargs == "*":  # "*" argparse.ZERO_OR_MORE
            dest = plural_en(metavar.lower())

        # Emit usage phrase

        self.args_py_phrases.append(usage_phrase)

        # Emit Python source

        d4 = r"    "  # choose indentation

        repr_dest = black_repr(dest)
        repr_metavar = black_repr(metavar)
        repr_help = black_repr(arg_help).replace("%", "%%")

        repr_nargs = black_repr(nargs)
        if False:  # FIXME: "*" argparse.ZERO_OR_MORE vs "..." argparse.REMAINDER
            if nargs == "*":
                repr_nargs = black_repr("...")

        head_lines = [
            "parser.add_argument(",
        ]

        if nargs is None:

            if dest == metavar:
                mid_lines = [
                    d4 + r"{repr_dest},".format(repr_dest=repr_dest),
                ]
            else:
                mid_lines = [
                    d4
                    + "{repr_dest}, metavar={repr_metavar},".format(
                        repr_dest=repr_dest, repr_metavar=repr_metavar
                    ),
                ]

        else:

            if dest == metavar:
                mid_lines = [
                    d4
                    + "{repr_dest}, nargs={repr_nargs},".format(
                        repr_dest=repr_dest, repr_nargs=repr_nargs
                    ),
                ]
            else:
                mid_lines = [
                    d4
                    + "{repr_dest}, metavar={repr_metavar}, nargs={repr_nargs},".format(
                        repr_dest=repr_dest,
                        repr_metavar=repr_metavar,
                        repr_nargs=repr_nargs,
                    ),
                ]

        tail_lines = [
            d4 + r"help={repr_help}".format(repr_help=repr_help),
            d4 + r")",
        ]

        lines = head_lines + mid_lines + tail_lines

        return lines

    def emit_optional(self, optionals_declaration):
        """Compile an Arg Doc Optional argument line into Python source lines"""

        parts = self.parts

        # Pick out source fragments

        option = optionals_declaration.arg_line.option
        metavar = optionals_declaration.arg_line.metavar
        alt_option = optionals_declaration.arg_line.alt_option
        alt_metavar = optionals_declaration.arg_line.alt_metavar

        usage_phrase = optionals_declaration.arg_phrase.format_usage_phrase()
        arg_help = optionals_declaration.arg_line.arg_help

        assert option
        assert (not alt_metavar) or (alt_metavar == metavar)

        # Separate concise and mnemonic options

        options = (option, alt_option)

        concise_options = list(_ for _ in options if _ and not _.startswith("--"))
        assert len(concise_options) <= 1
        concise = concise_options[0] if concise_options else None

        mnemonic_options = list(_ for _ in options if _ and _.startswith("--"))
        assert len(mnemonic_options) <= 1
        mnemonic = mnemonic_options[0] if mnemonic_options else None

        # Name the attribute for this positional option in the namespace built by "parse_args"
        # Go with the mnemonic option, else the metavar, else the concise option

        if mnemonic:
            dest = mnemonic.lstrip("-").lower()
        elif metavar:
            dest = metavar.lower()
        else:
            assert concise
            dest = concise.lstrip("-").lower()

        # Emit usage phrase

        self.args_py_phrases.append(usage_phrase)

        # Emit no Python here to tell "argparse.parse_args" to "add_help" for us elsewhere

        if (concise == "-h") or (mnemonic == "--help"):
            if not parts.add_help:

                parts.add_help = False

                addable_help = "show this help message and exit"
                if (
                    (concise == "-h")
                    and (mnemonic == "--help")
                    and (arg_help == addable_help)
                    and (metavar is None)
                ):
                    parts.add_help = True

                    no_lines = list()
                    return no_lines

        # Empty Python Source

        lines = self.emit_optional_as_python(
            optionals_declaration, mnemonic=mnemonic, dest=dest
        )

        return lines

    def emit_optional_as_python(self, optionals_declaration, mnemonic, dest):

        # Pick out source fragments

        option = optionals_declaration.arg_line.option
        metavar = optionals_declaration.arg_line.metavar
        alt_option = optionals_declaration.arg_line.alt_option
        alt_metavar = optionals_declaration.arg_line.alt_metavar

        nargs = optionals_declaration.arg_line.nargs
        default = optionals_declaration.arg_line.default

        arg_help = optionals_declaration.arg_line.arg_help

        repr_help = black_repr(arg_help).replace("%", "%%")

        assert option
        assert (not alt_metavar) or (alt_metavar == metavar)
        assert nargs in (None, "?")  # .OPTIONAL  # FIXME: add "*" .ZERO_OR_MORE

        # Collect help dests

        addable_help = "show this help message and exit"
        if arg_help == addable_help:
            self.help_dests.append(dest)

        # Emit Python source

        d4 = r"    "  # choose indentation

        repr_option = black_repr(option)
        repr_alt = black_repr(alt_option)
        repr_var = black_repr(metavar)
        repr_dest = black_repr(dest)
        repr_default = None if (default is None) else black_repr(default)
        repr_nargs = None if (nargs is None) else black_repr(nargs)

        head_lines = [
            r"parser.add_argument(",
        ]

        if not metavar:

            assert '"count"' == black_repr("count")
            repr_kwargs = r"""action="count", default=0"""

            if not alt_option:
                assert dest == option.lstrip("-").lower()
                mid_lines = [
                    d4
                    + r"{repr_option}, {repr_kwargs},".format(
                        repr_option=repr_option, repr_kwargs=repr_kwargs
                    )
                ]
            else:
                assert dest == mnemonic.lstrip("-").lower()
                mid_lines = [
                    d4
                    + r"{repr_option}, {repr_alt}, {repr_kwargs},".format(
                        repr_option=repr_option,
                        repr_alt=repr_alt,
                        repr_kwargs=repr_kwargs,
                    )
                ]

        else:

            suffixes = r""
            if nargs is not None:
                suffixes += r" nargs={repr_nargs},".format(repr_nargs=repr_nargs)
            if default is not None:
                suffixes += r" default={repr_default},".format(
                    repr_default=repr_default
                )

            if not alt_option:
                if dest == option.lstrip().lower():
                    mid_lines = [
                        d4
                        + r"{repr_option}, metavar={repr_var},{suffixes}".format(
                            repr_option=repr_option,
                            repr_var=repr_var,
                            suffixes=suffixes,
                        )
                    ]
                else:
                    mid_lines = [
                        d4
                        + r"{repr_option}, metavar={repr_var}, dest={repr_dest},{suffixes}".format(
                            repr_option=repr_option,
                            repr_var=repr_var,
                            repr_dest=repr_dest,
                            suffixes=suffixes,
                        )
                    ]
            else:
                assert dest == mnemonic.lstrip("-").lower()
                mid_lines = [
                    d4
                    + r"{repr_option}, {repr_alt}, metavar={repr_var},{suffixes}".format(
                        repr_option=repr_option,
                        repr_alt=repr_alt,
                        repr_var=repr_var,
                        suffixes=suffixes,
                    )
                ]

        tail_lines = [
            d4 + r"help={repr_help}".format(repr_help=repr_help),
            r")",
        ]

        lines = head_lines + mid_lines + tail_lines

        return lines

    def exec_parser_source(self, parser_source):
        """Run the parser source to build the Parser"""

        global_vars = dict()

        try:
            exec(parser_source, global_vars)
        except argparse.ArgumentError as exc:
            stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(2)  # exit 2 from rejecting usage

        as_parser = global_vars["parser"]

        return as_parser


class _ArgDocSyntax(argparse.Namespace):
    """Pick an Arg Doc apart into named fragments"""

    def __init__(self):

        self.prog = None  # the name of the app

        self.usage = None  # the "usage:" line of Arg Doc, without its "usage: " prefix
        self.uses = None  # the parse of the "usage:" line of Arg Doc

        self.description_line = None  # the one-line description of the app

        self.positionals_declarations = None  # positional argument declarations
        self.optionals_declarations = None  # optional argument declarations
        self.add_help = None  # True/False as in ArgParse, else None if not doc'ced

        self.epilog_chars = None  # the trailing lines of the Arg Doc


class _ArgDocTaker(argparse.Namespace):
    """Walk through an Arg Doc line by line and pick out fragments along the way"""

    TAGLINE_PATTERNS = (
        r"^positional arguments:$",
        r"^optional arguments:$",
        r"^usage:",
    )

    def __init__(self, parts, doc, verbose):

        self.parts = None  # the fragments of source matched by this parser
        self.verbose = verbose

        tabsize_8 = 8
        doc_chars = textwrap.dedent(doc.expandtabs(tabsize_8)).strip()

        taker = ShardsTaker()
        self.taker = taker

        self._give_doclines(doc_chars)

    def _give_doclines(self, chars):
        """Give chars, split into lines, but drop the trailing whitespace from each line"""

        taker = self.taker

        lines = chars.splitlines()
        lines = list(_.rstrip() for _ in lines)

        taker.give_shards(shards=lines)

    def take_arg_doc_into(self, parts):
        """Parse an Arg Doc into its Parts"""

        self.parts = parts
        self.take_arg_doc()

    def take_arg_doc(self):
        """Take each source line of an Arg Doc"""

        taker = self.taker

        if taker.peek_more():

            self.take_usage_chars()
            self.accept_description()

            self.parts.taglines = list()
            self.accept_positionals_declarations()  # Positionals before Optionals in Arg Doc lines
            self.accept_optionals_declarations()

            if "positional arguments:" not in self.parts.taglines:
                self.accept_positionals_declarations()
                if "positional arguments:" in self.parts.taglines:
                    verbose_print(
                        self.verbose,
                        "argdoc.py: warning: optionals declared before positionals",
                    )

            self.accept_doc_remains()

        self.take_end_doc()

    def take_usage_chars(self):
        """Take one line or some lines of Usage to get started"""

        taker = self.taker

        usage_lines = list()
        line = taker.peek_one_shard()
        while True:
            usage_lines.append(line)
            taker.take_one_shard()
            if taker.peek_more():
                line = taker.peek_one_shard()
                if line.strip():
                    if line.startswith(" "):

                        continue

            break

        usage_chars = "\n".join(usage_lines)

        uses = _UsagePhrasesSyntax()
        uses_taker = _UsagePhrasesTaker(usage_chars)
        uses_taker.take_usage_chars_into(uses)

        self.parts.uses = uses
        self.parts.usage = uses.usage_tail
        self.parts.prog = uses.prog_phrase

        if uses.remains:  # FIXME: does this never happen?
            verbose_print(
                self.verbose,
                "argdoc.py: warning: meaningless (late?) usage phrases:  {}".format(
                    uses.remains
                ),
            )

    def accept_description(self):
        """Take the line of description"""

        taker = self.taker
        taker.accept_blank_shards()

        self.parts.description_line = None
        if taker.peek_more():
            line = taker.peek_one_shard()

            if not any(re.match(p, string=line) for p in _ArgDocTaker.TAGLINE_PATTERNS):
                self.parts.description_line = line
                taker.take_one_shard()

    def accept_positionals_declarations(self):
        """Take the Positional arguments"""

        self.parts.positionals_declarations = self.accept_tabulated_arguments(
            "positional arguments:",
            marked_optional="",  # encoded as empty "", because unmarked
            arg_phrases=self.parts.uses.positionals_phrases,
        )

    def accept_optionals_declarations(self):
        """Take the Optional arguments"""

        self.parts.optionals_declarations = self.accept_tabulated_arguments(
            "optional arguments:",
            marked_optional="-",
            arg_phrases=self.parts.uses.optionals_phrases,
        )

    def accept_tabulated_arguments(self, tagline, marked_optional, arg_phrases):
        """Take the Positional or Optional arguments led by a tagline followed by dented lines"""

        arg_declarations = None

        taker = self.taker
        taker.accept_blank_shards()

        if taker.peek_more():
            line = taker.peek_one_shard()

            if line == tagline:
                self.parts.taglines.append(tagline)

                taker.take_one_shard()
                taker.accept_blank_shards()

                broken_argument_lines = self.accept_broken_argument_lines(
                    tagline=tagline
                )

                if not broken_argument_lines:
                    verbose_print(
                        self.verbose,
                        "argdoc.py: warning: no arguments declared inside {!r}".format(
                            tagline
                        ),
                    )

                arg_declarations = self.reconcile_arg_lines_phrases(
                    broken_argument_lines,
                    tagline=tagline,
                    marked_optional=marked_optional,
                    arg_phrases=arg_phrases,
                )

        return arg_declarations

    def reconcile_arg_lines_phrases(
        self, broken_argument_lines, tagline, marked_optional, arg_phrases
    ):

        self._disentangle_optionals_positionals(
            broken_argument_lines, tagline=tagline, marked_optional=marked_optional
        )

        phrases_by_arg_key = self._index_phrases_by_arg_key(arg_phrases)
        lines_by_arg_key = self._index_lines_by_arg_key(broken_argument_lines)

        phrase_arg_keys = list(phrases_by_arg_key.keys())
        line_arg_keys = list(lines_by_arg_key.keys())
        self._require_matching_argument_declarations(
            tagline, phrase_arg_keys=phrase_arg_keys, line_arg_keys=line_arg_keys
        )

        arg_keys = line_arg_keys + phrase_arg_keys  # lines before phrases
        arg_declarations = self._reconcile_arg_declarations(
            arg_keys,
            phrases_by_arg_key=phrases_by_arg_key,
            lines_by_arg_key=lines_by_arg_key,
            marked_optional=marked_optional,
        )

        return arg_declarations

    def _reconcile_arg_declarations(
        self, arg_keys, phrases_by_arg_key, lines_by_arg_key, marked_optional
    ):

        declarations_by_arg_key = collections.OrderedDict()  # till Dec/2016 CPython 3.6
        for arg_key in arg_keys:

            if arg_key in declarations_by_arg_key.keys():

                continue

            arg_phrase = phrases_by_arg_key.get(arg_key)
            arg_line = lines_by_arg_key.get(arg_key)
            if not arg_phrase:
                arg_phrase = self._fabricate_arg_phrase(arg_line)
            if not arg_line:
                arg_line = self._fabricate_arg_line(arg_phrase)

            assert arg_phrase.concise in (arg_line.option, arg_line.alt_option, None)
            assert arg_phrase.mnemonic in (arg_line.option, arg_line.alt_option, None)
            assert arg_line.metavar == arg_phrase.metavar
            assert (not arg_line.alt_metavar) or (
                arg_line.alt_metavar == arg_phrase.metavar
            )

            if not marked_optional:  # positional argument
                assert arg_phrase.nargs in (None, "*", "?")  # .ZERO_OR_MORE .OPTIONAL
                assert arg_phrase.metavar and arg_line.metavar
            else:  # optional argument
                assert arg_phrase.concise or arg_phrase.mnemonic
                assert arg_line.option or arg_line.alt_option

            arg_declaration = argparse.Namespace(
                arg_phrase=arg_phrase, arg_line=arg_line
            )

            declarations_by_arg_key[arg_key] = arg_declaration

        arg_declarations = declarations_by_arg_key.values()

        return arg_declarations

    def _index_phrases_by_arg_key(self, arg_phrases):
        """Calculate words comparable between Usage Phrases and Argument Declaration Lines"""

        phrases_by_arg_key = collections.OrderedDict()  # till Dec/2016 CPython 3.6
        for arg_phrase in arg_phrases:

            # FIXME: detect multiple phrase declarations earlier

            arg_key = arg_phrase._calc_arg_key()
            if arg_key in phrases_by_arg_key.keys():
                verbose_print(
                    self.verbose,
                    "argdoc.py: warning: multiple phrase declarations of {}".format(
                        arg_key
                    ),
                )

            phrases_by_arg_key[arg_key] = arg_phrase

        return phrases_by_arg_key

    def _index_lines_by_arg_key(self, broken_argument_lines):
        """Calculate words comparable between Argument Declaration Lines and Usage Phrase"""

        lines_by_arg_key = collections.OrderedDict()  # till Dec/2016 CPython 3.6
        for broken_argument_line in broken_argument_lines:

            arg_line = ArgumentLineSyntaxTaker(broken_argument_line)
            # call ArgumentLineSyntaxTaker as early as the two PhraseSyntaxTaker's
            # FIXME: detect multiple line declarations earlier

            arg_key = arg_line._calc_arg_key()
            if arg_key in lines_by_arg_key.keys():
                verbose_print(
                    self.verbose,
                    "argdoc.py: warning: multiple line declarations of {}".format(
                        arg_key
                    ),
                )

            lines_by_arg_key[arg_key] = arg_line

        return lines_by_arg_key

    def _disentangle_optionals_positionals(
        self, broken_argument_lines, tagline, marked_optional
    ):
        """Require Positionals declared strictly apart from Optionals, and vice versa"""

        for broken_argument_line in broken_argument_lines:
            bb = "  "
            stripped = bb.join(broken_argument_line.splitlines()).strip()

            doc_marked_optional = "-" if stripped.startswith("-") else ""
            if doc_marked_optional != marked_optional:

                raise ArgDocError(
                    "{!r} != {!r} inside {!r} at:  {}".format(
                        doc_marked_optional, marked_optional, tagline, stripped
                    )
                )

    def _fabricate_arg_phrase(self, arg_line):
        """Fabricate a usage phrase that matches an arg doc line declaring an arg"""

        assert arg_line.option or arg_line.metavar

        argument_phrase = ""
        if arg_line.option:
            argument_phrase += "["
            argument_phrase += arg_line.option
        if arg_line.metavar:
            argument_phrase += " "
            argument_phrase += arg_line.metavar

        if arg_line.option:
            argument_phrase += "]"
            arg_phrase = OptionalPhraseSyntaxTaker(argument_phrase)
        else:
            arg_phrase = PositionalPhraseSyntaxTaker(argument_phrase)

        return arg_phrase

    def _fabricate_arg_line(self, arg_phrase):
        """Fabricate an arg doc line that matches a usage phrase declaring an arg"""

        # assert bool(arg_phrase.concise) ^ bool(arg_phrase.mnemonic)

        broken_argument_line = ""
        if arg_phrase.concise:
            broken_argument_line += arg_phrase.concise
        if arg_phrase.mnemonic:
            broken_argument_line += arg_phrase.mnemonic
        if arg_phrase.metavar:
            broken_argument_line += " "
            broken_argument_line += arg_phrase.metavar
            # arg phrase alone can't imply:  --mnemonic [OPTIONAL_METAVAR]
            # FIXME FIXME: challenge this, I jittered over how lifted up the [] are

        assert broken_argument_line  # FIXME FIXME: is this the assert we want?

        arg_line = ArgumentLineSyntaxTaker(broken_argument_line)

        return arg_line

    def _require_matching_argument_declarations(
        self, tagline, phrase_arg_keys, line_arg_keys
    ):
        """Require same args declared line by line and in usage line"""

        usage_phrase_arg_keys = " ".join(
            "[{}]".format(" ".join(_)) for _ in phrase_arg_keys
        )
        usage_line_arg_keys = " ".join(
            "[{}]".format(" ".join(_)) for _ in line_arg_keys
        )

        if phrase_arg_keys != line_arg_keys:

            verbose_print(
                self.verbose,
                "argdoc.py: warning: usage via phrases:  {}".format(
                    usage_phrase_arg_keys
                ),
            )
            verbose_print(
                self.verbose,
                "argdoc.py: warning: vs usage at lines:  {}".format(
                    usage_line_arg_keys
                ),
            )
            # FIXME: suggest multiple usage lines when too wide for one usage line

            if set(phrase_arg_keys) == set(line_arg_keys):
                verbose_print(
                    self.verbose,
                    "argdoc.py: warning: same sets, different orders, as usage and as {}".format(
                        tagline.rstrip(":")
                    ),
                )
            else:
                verbose_print(
                    self.verbose,
                    "argdoc.py: warning: different sets of words as usage and as {}".format(
                        tagline.rstrip(":")
                    ),
                )

    def accept_broken_argument_lines(self, tagline):
        """Take zero or more dented lines as defining Positional or Optional arguments"""

        taker = self.taker
        taker.accept_blank_shards()

        broken_argument_lines = list()
        denting = None
        while taker.peek_more():

            argument_shard = taker.peek_one_shard()
            if not argument_shard.startswith(" "):

                break

            dent = str_splitdent(argument_shard)[0]
            if denting and (denting < dent):  # later guess  # FIXME: mutation
                broken_argument_lines[-1] += "\n" + argument_shard
            else:
                broken_argument_line = argument_shard  # first guess
                broken_argument_lines.append(broken_argument_line)
                denting = dent  # not much tested <= was misplaced

            taker.take_one_shard()

        taker.accept_blank_shards()  # not much tested <= was wrongly indented

        return broken_argument_lines

    def accept_doc_remains(self):
        """
        Take zero or more trailing lines, as if they must be the Epilog

        Aggressively take whatever trailing lines exist as arbitrary epilog:
        like let them be reserved lines of  "optional" or "positional arguments:"
        like let them be blank or indented randomly
        """

        taker = self.taker

        lines = list()
        while taker.peek_more():

            line = taker.peek_one_shard()
            lines.append(line)

            taker.take_one_shard()

        self.parts.epilog_chars = "\n".join(lines)

    def take_end_doc(self):
        """Do nothing if all lines consumed, else crash"""

        taker = self.taker
        taker.take_beyond_shards()


class _UsagePhrasesSyntax(argparse.Namespace):
    """Name the uses spelled out by an Arg Doc Usage line"""

    def __init__(self):

        self.usage_chars = None  # the usage lines catenated with "\n" marks in between
        self.usage_tail = None  # the line without its "usage:" leading chars
        self.prog_phrase = None  # the 2nd word of the Usage line

        self.optionals_phrases = None  # the [-h] or [--help] or [-w WIDTH] and such
        self.positionals_phrases = None  # the FILE or [FILE] or [FILE [FILE ...]] or [-- [WORD [WORD ...]] and such


class _UsagePhrasesTaker(argparse.Namespace):
    """Pick an Arg Doc Usage Line apart, char by char"""

    def __init__(self, usage_chars):

        self.usage_chars = usage_chars
        self.uses = None  # the fragments of source matched by this parser
        self.taker = ShardsTaker(shards=usage_chars)

    def _arg_doc_error(self, reason):
        """Construct an ArgDocError that says it came from the usage line"""

        reason_here = (
            textwrap.dedent(
                """
            {} in
              {}
        """
            )
            .format(reason, self.usage_chars)
            .strip()
        )

        return ArgDocError(reason_here)

    def take_usage_chars_into(self, uses):
        """Parse an Arg Doc Usage Line into its Uses"""

        self.uses = uses
        self.take_usage_chars()

    def take_usage_chars(self):
        """Take each Use of an Arg Doc Usage Line"""

        taker = self.taker

        if taker.peek_more():

            self.accept_peeked_usage_chars()

            self.take_usage_word()
            self.take_prog()
            self.accept_arg_phrases()

            self.accept_usage_remains()

        taker.take_beyond_shards()

    def accept_peeked_usage_chars(self):
        """Name a copy of the entire Usage Line, including its "usage:" prefix"""

        taker = self.taker
        uses = self.uses

        joined_remains = "".join(taker.peek_more_shards())

        usage_chars = joined_remains.strip()
        uses.usage_chars = usage_chars

    def take_usage_word(self):
        """Take the chars of "usage:" to get started"""

        taker = self.taker
        uses = self.uses

        hopes = "usage:"
        if not taker.peek_equal_shards(hopes):

            word = "".join(taker.peek_upto_blank_shard())
            reason = "{!r} is here, but the first word of an Arg Doc is{!r}".format(
                word, hopes
            )

            raise self._arg_doc_error(reason)

        taker.take_some_shards(len(hopes))
        taker.accept_blank_shards()

        usage_tail = "".join(taker.peek_more_shards())
        uses.usage_tail = usage_tail

    def take_prog(self):
        """Take the second word of "usage: {verb}" as the name of the app"""

        taker = self.taker
        uses = self.uses

        taker.accept_blank_shards()

        prog_phrase = "".join(taker.peek_upto_blank_shard())
        if not prog_phrase:
            reason = "second word of Arg Doc must exist, to name the app"

            raise self._arg_doc_error(reason)

        taker.take_some_shards(len(prog_phrase))
        taker.accept_blank_shards()

        uses.prog_phrase = prog_phrase

    def accept_arg_phrases(self):
        """Accept zero or more arg phrases of the usage lines"""

        taker = self.taker
        uses = self.uses

        uses.optionals_phrases = list()
        uses.positionals_phrases = list()

        while taker.peek_more():

            startswith_bracket_dash = taker.peek_equal_shards("[-")
            startswith_bracket_dash_dash_space = taker.peek_equal_shards("[-- ")
            # FIXME: simplify the syntax differences between optionals and positionals

            argument_phrase = self.accept_one_arg_phrase()

            # Accept [-h] or [--help] or [-w WIDTH] and such, and
            # accept FILE or [FILE] or [FILE [FILE ...]] and such

            if startswith_bracket_dash and not startswith_bracket_dash_dash_space:
                optional_phrase = OptionalPhraseSyntaxTaker(argument_phrase)
                uses.optionals_phrases.append(optional_phrase)
            else:
                positional_phrase = PositionalPhraseSyntaxTaker(argument_phrase)
                uses.positionals_phrases.append(positional_phrase)

    def accept_one_arg_phrase(self):
        """Take one word, or more, but require the [...] brackets to balance"""

        taker = self.taker

        words = list()

        argument_phrase = ""
        openings = 0
        closings = 0

        while taker.peek_more():

            word = "".join(taker.peek_upto_blank_shard())
            assert word

            taker.take_some_shards(len(word))
            taker.accept_blank_shards()

            words.append(word)
            argument_phrase = " ".join(words)
            openings = argument_phrase.count("[")
            closings = argument_phrase.count("]")

            if openings == closings:
                break

            if not taker.peek_more():
                reason = "{} of [ not balanced by {}".format(openings, closings)
                raise self._arg_doc_error(reason)

        return argument_phrase

    def accept_usage_remains(self):

        taker = self.taker
        uses = self.uses

        remains = "".join(taker.peek_more_shards())
        taker.take_some_shards(len(remains))

        uses.remains = remains  # FIXME: is this always empty?


class ArgumentLineSyntaxTaker(argparse.Namespace):
    """Parse one line of Arg Doc argument declaration"""

    def __init__(self, broken_argument_line):

        self.arg_source_left = None
        self.arg_help = None

        self.option = None
        self.metavar = None
        self.alt_option = None
        self.alt_metavar = None
        self.nargs = None
        self.default = None

        accepted = self._accept_broken_argument_line(broken_argument_line)
        # sys.stderr.write("{}\n".format(self))
        if not accepted:
            self._reject_broken_argument_line(broken_argument_line)

    def _accept_broken_argument_line(self, broken_argument_line):
        """Pick attributes out of the broken argument line"""

        # Split off the help words
        # found past "  " in the first line, or past the indentation of later lines

        bb = "  "
        stripped = bb.join(broken_argument_line.splitlines()).strip()

        arg_source_left = stripped
        arg_help = None

        index = stripped.find("  ")
        if index >= 0:

            arg_help = stripped[index:].lstrip()
            arg_source_left = stripped[:index].rstrip()

        self.arg_source_left = arg_source_left
        self.arg_help = arg_help

        # Take 1, 2, or 4 words presented before the first "  " double-blank, if any

        words = arg_source_left.split()

        len_words = len(words)
        if len_words not in (1, 2, 4):

            return

        self._take_1_2_4_argument_words(words)

        # Take "[METAVAR]" in the line as meaning nargs = "?"  # argparse.OPTIONAL

        if self.metavar:
            if (self.alt_metavar is None) or (self.metavar == self.alt_metavar):
                name = self.metavar.replace("[", "").replace("]", "")
                if self.metavar == "[{}]".format(name):
                    self.metavar = name
                    self.nargs = "?"  # argparse.OPTIONAL
                    self.default = False

        # Require a positional metavar, or else the dash/ dashes of an optional argument

        if (not self.metavar) and (not self.option):

            return

        # Require consistent metavars, or else no metavars

        if self.metavar and self.alt_metavar and (self.metavar != self.alt_metavar):

            return

        # Require emitted source output to match compiled source input, precisely,
        # except don't check the width of single space " " or double "  ", etc

        if self.format_broken_argument_line().split() != stripped.split():

            return

        # Succeed

        return True

    def _reject_broken_argument_line(self, broken_argument_line):
        """Raise ArgDocError to reject the "broken_argument_line" not taken"""

        arg_source_left = self.arg_source_left

        want = "[-c|--mnemonic] [METAVAR|[METAVAR]][,] ..."  # approximately

        bb = "  "
        stripped = bb.join(broken_argument_line.splitlines()).strip()
        got = stripped

        if arg_source_left:  # false only if ArgumentLineSyntaxTaker took an empty line

            words = arg_source_left.split()

            got = " ".join(words)
            if len(words) != 1:
                got = "{} words {}".format(len(words), got)

            if not words[0].startswith("-"):  # if more like a positional argument line

                want = "METAVAR|[METAVAR]"
                if len(words) != 1:
                    want = "1 word of {}".format(want)

            else:  # if more like an optional argument line

                want = "4 words of -c METAVAR|[METAVAR], --optional METAVAR|[METAVAR]"
                if len(words) < 3:
                    want = "2 words of -c|--optional METAVAR|[METAVAR]"
                    if len(words) < 2:
                        want = "-c|--optional"

        stderr_print("argdoc.py: error: want: {}".format(want))
        raise ArgDocError("got: {}".format(got))

    def _take_1_2_4_argument_words(self, words):
        """Return possible parses of [-c|--mnemonic] [METAVAR] argument syntax"""

        # Take the 1 word of --mnemonic, -c, or METAVAR

        (word0, metavar0, concise0, mnemonic0) = self._take_argument_word(words[0])

        if word0.startswith("--"):
            self.option = mnemonic0
        elif word0.startswith("-"):
            self.option = concise0
        else:
            self.metavar = metavar0

        # Take the 2 words of -c, --mnemonic, --mnemonic, -c, or -c|--mnemonic METAVAR

        if words[1:]:

            (word1, metavar1, concise1, mnemonic1) = self._take_argument_word(words[1])

            if word1.startswith("--"):
                self.alt_option = mnemonic1
            elif word1.startswith("-"):
                self.alt_option = concise1
            else:
                self.metavar = metavar1

            # Take the 4 words of -c METAVAR, --mnemonic METAVAR,
            # Or reversed as --mnemonic METAVAR, -c METAVAR

            if words[2:]:

                (word2, _, concise2, mnemonic2) = self._take_argument_word(words[2])
                (word3, metavar3, _, _) = self._take_argument_word(words[3])

                if word2.startswith("--"):
                    self.alt_option = mnemonic2
                    self.alt_metavar = metavar3
                elif word2.startswith("-"):
                    self.alt_option = concise2
                    self.alt_metavar = metavar3

    def _take_argument_word(self, word):
        """Return the possible -c, --mnemonic, METAVAR parses of a word"""

        name = word.strip("-").strip(",")
        metavar = name

        concise = None
        mnemonic = None
        if name:
            n = name[0]
            concise = "-{}".format(n)
            mnemonic = "--{}".format(name)

        return (word, metavar, concise, mnemonic)

    def format_broken_argument_line(self):
        """Format as a line of optional or positional argument declaration"""

        source_words = list(self.format_arg_source_left_words())

        words = (source_words + ["", self.arg_help]) if self.arg_help else source_words
        assert None not in words

        joined = " ".join(str(_) for _ in words)

        return joined

    def format_arg_source_left_words(self):
        """Format as the first 1, 2, or 4 words of an argument declaration line"""

        metavar = self.metavar
        alt_metavar = self.alt_metavar
        if self.nargs:
            assert self.nargs == "?"  # argparse.OPTIONAL
            assert self.default is False
            metavar = "[{}]".format(self.metavar)
            alt_metavar = "[{}]".format(self.alt_metavar)

        if not self.option and not self.alt_option:

            words = (metavar,)

        elif self.option and self.alt_option:

            if not metavar:
                words = ((self.option + ","), self.alt_option)
            else:
                words = (self.option, (metavar + ","), self.alt_option, alt_metavar)

        else:
            assert self.option and not self.alt_option

            if not metavar:
                words = (self.option,)
            else:
                words = (self.option, metavar)

        return words

    def _calc_arg_key(self):
        """Choose words to find the Positional Arg Line to mix into this Usage Phrase"""

        if not self.option:
            words = (self.metavar,)
        else:
            if (
                not self.metavar
            ):  # self.option shuts out self.alt_option from Usage Line
                words = (self.option,)
            else:
                words = (self.option, self.metavar)

        return words


class OptionalPhraseSyntaxTaker(argparse.Namespace):
    """Parse one of the [-h] or [--help] or [-w WIDTH] and such"""

    def __init__(self, argument_phrase):
        assert argument_phrase.startswith("[-")

        self._take_optional_phrase(argument_phrase)

    def _take_optional_phrase(self, argument_phrase):

        # Pick out the ArgParse "concise", "mnemonic", and/or "metavar

        shards = argument_phrase.replace("[", " ").replace("]", " ").split()
        dashdash = "--" in shards

        words = list(_ for _ in shards if _ not in "-- ...".split())
        if not words:
            raise ArgDocError(
                "no concise nor mnemonic in optional usage {}".format(argument_phrase)
            )

        if len(words) > 2:
            raise ArgDocError(
                "too many concise or mnemonic in optional usage {}".format(
                    argument_phrase
                )
            )

        concise = words[0] if not words[0].startswith("--") else None
        mnemonic = words[0] if words[0].startswith("--") else None
        metavar = words[1] if words[1:] else None
        optional = metavar and ("[" in argument_phrase.split()[1])

        # Publish results

        self.concise = concise
        self.mnemonic = mnemonic
        self.dashdash = dashdash
        self.metavar = metavar
        self.nargs = "?" if optional else None  # argparse.OPTIONAL

        # Require emitted usage equals usage source

        emitted_usage = self.format_usage_phrase()
        if argument_phrase != emitted_usage:
            stderr_print(
                "argdoc.py: error: optional doc usage phrase:  {}".format(
                    argument_phrase
                )
            )
            stderr_print(
                "argdoc.py: error: optional emitted usage phrase:  {}".format(
                    emitted_usage
                )
            )
            raise ArgDocError(
                "meaningless optional doc usage phrase {}".format(argument_phrase)
            )

    def format_usage_phrase(self):
        """Format optional arg line as a phrase of a Usage Line in an Arg Doc"""

        words = list(self._calc_arg_key())
        if self.nargs == "?":  # argparse.OPTIONAL  # FIXME
            assert words[-1] == self.metavar
            words[-1] = "[{}]".format(self.metavar)

        joined = "[{}]".format(" ".join(words))

        return joined

    def _calc_arg_key(self):
        """Choose words to find the Optional Arg Line to mix into this Usage Phrase"""

        if not self.metavar:
            if self.concise:
                words = (self.concise,)
            elif self.mnemonic:
                words = (self.mnemonic,)
        else:
            if self.concise:
                words = (self.concise, self.metavar)
            elif self.mnemonic:
                words = (self.mnemonic, self.metavar)

        return words


class PositionalPhraseSyntaxTaker(argparse.Namespace):
    """Parse one of FILE or [FILE] or [FILE [FILE ...]] or [-- [WORD [WORD ...]] and such"""

    def __init__(self, argument_phrase):

        self._take_positional_phrase(argument_phrase)

    def _take_positional_phrase(self, argument_phrase):

        # Pick out the one ArgParse "metavar"

        shards = argument_phrase.replace("[", " ").replace("]", " ").split()
        dashdash = "--" in shards

        words = list(_ for _ in shards if _ not in "-- ...".split())
        if not words:
            raise ArgDocError(
                "no metavars in positional usage phrase:  {}".format(argument_phrase)
            )

        metavar = words[0]

        if list(set(words)) != [metavar]:
            raise ArgDocError(
                "too many metavars in positional usage phrase:  {}".format(
                    argument_phrase
                )
            )

        # Pick out the one ArgParse "nargs"
        # FIXME: parse and emit nargs="..." argparse.REMAINDER, or nargs = 1, or nargs > 1

        nargs = None
        if "..." in argument_phrase:
            nargs = "*"  # "*" argparse.ZERO_OR_MORE
        elif "[" in argument_phrase:
            nargs = "?"  # "?" argparse.OPTIONAL

        # Publish results

        self.concise = None
        self.mnemonic = None
        self.dashdash = dashdash
        self.metavar = metavar
        self.nargs = nargs

        # Require emitted usage equals usage source

        emitted_usage = self.format_usage_phrase()
        if argument_phrase != emitted_usage:
            stderr_print(
                "argdoc.py: error: positional argument_phrase:  {}".format(
                    argument_phrase
                )
            )
            stderr_print(
                "argdoc.py: error: positional emitted_usage:  {}".format(emitted_usage)
            )
            raise ArgDocError(
                "meaningless positional usage phrase {}".format(argument_phrase)
            )

    def format_usage_phrase(self):
        """Format positional arg line as a phrase of a Usage Line in an Arg Doc"""

        if self.nargs == "*":  # "*" argparse.ZERO_OR_MORE
            joined = "[{} [{} ...]]".format(self.metavar, self.metavar)
            if self.dashdash:
                joined = "[-- [{} [{} ...]]]".format(self.metavar, self.metavar)
        elif self.nargs == "?":  # "?" argparse.OPTIONAL
            joined = "[{}]".format(self.metavar)
        else:
            assert self.nargs is None
            joined = "{}".format(self.metavar)

        return joined

    def _calc_arg_key(self):
        """Format as a tuple of words to compare with an argument declaration line in an Arg Doc"""

        words = (self.metavar,)

        return words


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
class ShardsTaker(argparse.Namespace):
    """
    Walk once thru source chars, as split, working as yet another Lexxer

    Define "take" to mean require and consume
    Define "peek" to mean look ahead into the shards followed by infinitely many None's
    Define "accept" to mean take if present, else quietly don't bother
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_shards(self, shards):
        """Give shards, such as from r"(?P<...>...)+" via 'match.groupdict().items()'"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Take one shard, and drop it, don't return it"""

        self.shards = self.shards[1:]

    def take_some_shards(self, count):
        """Take the next few shards, and drop them, don't return them"""

        self.shards = self.shards[count:]

    def peek_one_shard(self):
        """Return the next shard, but without consuming it"""

        if self.shards:  # infinitely many None's past the last shard

            return self.shards[0]

    def peek_some_shards(self, count):
        """Return the next few shards, without consuming them"""

        nones = count * [None]
        some = (self.shards[:count] + nones)[:count]

        return some

    def peek_equal_shards(self, hopes):
        """Return the next few shards, but only if they equal our hopes"""

        some = self.peek_some_shards(len(hopes))
        if some == list(hopes):

            return True

    def take_beyond_shards(self):
        """Do nothing if all shards consumed, else raise mystic IndexError"""

        count = len(self.shards)
        if count:

            raise IndexError("{} remaining shards".format(count))

    def peek_more(self):
        """Return True if more shards remain"""

        more = bool(self.shards)  # see also:  self.peek_more_shards

        return more

    def peek_more_shards(self):
        """List zero or more remaining shards"""

        more_shards = list(self.shards)  # see also:  self.peek_more

        return more_shards

    def accept_blank_shards(self):
        """Drop zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():

                break

            self.take_one_shard()

    def peek_upto_blank_shard(self):
        """List zero or more non-blank shards found here"""

        shards = list()
        for shard in self.shards:
            if not shard.strip():

                break

            shards.append(shard)

        return shards


# deffed in many files  # missing from docs.python.org
def black_triple_quote_repr(chars):
    '''Quote the chars like Black, with triple quotes, preferring triple '"""' double quotes'''
    # FIXME:  Fix leading trailing whitespace, other corner cases

    qqq = "'''" if ('"""' in chars) else '"""'

    rqqq = qqq
    if "\\" in chars:
        rqqq = "r" + qqq

    lines = list()
    lines.append(rqqq)
    if chars:
        lines.append(chars)
    lines.append(qqq)

    rep = "\n".join(lines)

    return rep


# deffed in many files  # missing from docs.python.org
def black_repr(chars):
    """Quote chars or None like Black, preferring " double quotes over ' single quotes"""
    # FIXME: does this agree with the Black autostyling app? Agrees always?

    rep = repr(chars)

    if chars == str(chars):  # not None, and not int, etc
        if '"' not in chars:
            # FIXME: these chars can be simply quoted, and how many more?
            if all((ord(" ") <= ord(_) <= ord("~")) for _ in chars):
                if chars and (chars[-1] == "\\"):
                    pass
                elif "\\" in chars:
                    rep = 'r"{}"'.format(chars)
                else:
                    rep = '"{}"'.format(chars)

    return rep


# deffed in many files  # missing from docs.python.org
def plural_en(word):  # FIXME: make this easy to override
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


def _plural_en_test():

    singulars = "vortex leaf basis appendix diagnosis criterion lorry lutz word".split()
    plurals = "vortices leaves bases appendices diagnoses criteria lorries lutzes words"

    guesses = " ".join(plural_en(_) for _ in singulars)
    assert guesses == plurals


# deffed in many files  # missing from docs.python.org
def take_docstring_of(chars):
    """
    Take the lines between the first triple-quote and the next,
    such as from \"\"\" to \"\"\", or from \'\'\' to \'\'\'
    but ignore empty lines and ignore leading lines begun with a hash #
    """

    qqq = None

    lines = list()
    for line in chars.splitlines():
        stripped = line.rstrip()

        if qqq is None:

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            if stripped.startswith('"""'):
                qqq = '"""'
            elif stripped.startswith("'''"):
                qqq = "'''"
            elif stripped.startswith('r"""'):
                qqq = '"""'
            elif stripped.startswith("r'''"):
                qqq = "'''"

            else:

                break

        elif qqq in stripped:

            qqq_at = stripped.index(qqq)
            lines.append(stripped[:qqq_at] + qqq)
            break

        lines.append(line)

    repr_doc = "\n".join(lines) + "\n"

    return repr_doc


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # since Oct/2019 Python 3.8
def shlex_join(argv):
    """Undo enough of the "shlex.split" to log its work reasonably well"""

    rep = " ".join((repr(_) if (" " in _) else _) for _ in argv)

    if '"' not in rep:  # like don't guess what "'$foo'" means
        try:
            if shlex.split(rep) == argv:

                return rep

        except ValueError:
            pass

    rep = repr(argv)

    return rep


# deffed in many files  # missing from docs.python.org
def require_sys_version_info(*min_info):
    """Decline to test Python older than the chosen version"""

    min_info_ = min_info if min_info else (3, 7)  # June/2019 Python 3.7

    str_min_info = ".".join(str(i) for i in min_info_)
    str_sys_info = "/ ".join(sys.version.splitlines())

    if sys.version_info < min_info:

        stderr_print()
        stderr_print("This is Python {}".format(str_sys_info))
        stderr_print()
        stderr_print("Please try Python {} or newer".format(str_min_info))
        stderr_print()

        sys.exit(1)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    sys.stdout.flush()
    # print(*args, **kwargs, file=sys.stderr)  # SyntaxError in Python 2
    print(*args, file=sys.stderr)
    sys.stderr.flush()


# deffed in many files  # missing from docs.python.org
def str_splitdent(line):
    """Split apart the indentation of a line, from the remainder of the line"""

    lstripped = line.lstrip()
    len_dent = len(line) - len(lstripped)

    tail = lstripped
    if not lstripped:  # see no chars, not all chars, as the indentation of a blank line
        tail = line
        len_dent = 0

    dent = len_dent * " "

    return (dent, tail)


# deffed in many files  # missing from docs.python.org
def str_splitword(chars, count=1):
    """Return the leading whitespace and words, split from the remaining chars"""

    tail = chars
    if count >= 1:
        counted_words = chars.split()[:count]
        for word in counted_words:
            tail = tail[tail.index(word) :][len(word) :]

    if not tail:

        return (chars, "")

    head = chars[: -len(tail)]

    return (head, tail)


# deffed in many files  # missing from docs.python.org
def verbose_print(verbose, *args):
    if verbose:
        stderr_print(*args)


# call inline to define 'import argdoc' to require Python >= June/2019 Python 3.7
require_sys_version_info()

# run a bit of self-test as part of the first "import argdoc" per Python program
_plural_en_test()


if __name__ == "__main__":
    sys.exit(main(sys.argv))


#
# See also
#
# "Parsing: a timeline" JKegler 2019, via @CompSciFact
# https://jeffreykegler.github.io/personal/timeline_v3
#


# newer bugs =>

# FIXME: Adopt the new [FILE ...] syntax from Python ArgParse for zero or more Args
# FIXME: Take 'usage: ... FILE ...' to mean require at least one Arg


# older bugs =>

# FIXME: Get the /dev/null template to mention the : boom : broken_heart : boom : decode

# FIXME: AssertionError at pos arg of -a A, --aaa A, yah  hmm

# FIXME: argdoc default action="count" should be also default=0
# FIXME: opt arg with METAVAR - work out when to take singular, vs append to plural dest
# FIXME: could be:  argdoc.complete_action(args, dest="alphas", action="store")
# FIXME: could be:  argdoc.complete_action(args, dest="bravo", action="store_true")
# FIXME: vs argdoc default action="append", action="count"
# FIXME: custom help-opts should be action="help"

# FIXME: take a whole file without """ and without ''' as a whole argdoc

# FIXME: --rip .txt, .py, .py2 for doc, argdoc, argparse
# FIXME: save to path, not stdout, if more path provided, not just the .ext or ext

# FIXME: option (surely not default?) to push the autocorrection into the Arg Doc
# FIXME: comment --rip argparse at colliding "dest"s from multiple args, such as "[--ymd YMD] [YMD]"
# FIXME: parsed args whose names begin with a '_' skid shouldn't print, via argparse.SUPPRESS
# FIXME: consider [FILE [FILE ...]] in usage: argdoc.py [-h] [--rip SHRED] [FILE] [-- ...]

# FIXME: think into who signs as author of ArgumentError log message: "argdoc.py" or the "prog"?

# FIXME: "argparse.Parser.add_argument" does already have an ' action="help" '
# FIXME: so likewise, it should have an ' action="raise" ' to raise NotImplementedError
# FIXME: even when called to do so by ' parser.set_defaults '

# FIXME: reject dropped args such as the "-- hello" of
# FIXME:    bin/argdoc.py --rip argparse bin/tar.py -- hello >/dev/null

# add class ArgParseAuthor to wrap around _ArgDocCoder
#
# develop some good way to patch up the Python, such as
#
#   author = ArgParseAuthor()  # move  [TOP [TOP ...]] to args.cimas
#
#   author.ArgumentParser.add_help = False
#   author.add_argument(metavar="TOP").metavar = "cimas"
#   author.add_argument(dest="width").type = int
#   author.add_argument("--verbose").action = "store_true"
#
#   assert author.parser.add_help == False
#
#   args = author.parse_args()
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
