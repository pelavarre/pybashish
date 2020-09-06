#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
usage: argdoc.py [-h] [--rip SHRED] [FILE] [-- [ARG [ARG ...]]]

parse command line args precisely as helped by module doc

positional arguments:
  FILE         where the arg doc is (default: os.devnull)
  ARG          an arg to parse as per the arg doc

optional arguments:
  -h, --help   show this help message and exit
  --rip SHRED  one of doc|argparse|argdoc

usage as a python import:

  r"""
  usage: ... [-h]

  optional arguments:
    -h, --help  show this help message and exit
  """

  import argdoc

  if __name__ == '__main__':
    args = argdoc.parse_args()
    print(args)

bugs:
  to see review comments pop up to work with you, you must damage an arg doc and run it
  long option and metavar names split their line and spill their words of help onto the next line
  you lose your "-h" and "--help" options if you drop all "optional arguments:" from an arg doc
  you get only english plural "dest"s for plural args, such as "[top [top ..]]" goes to "args.tops"
  you get only simple argparses unless you rip and edit, you can't mix your python into the arg doc

unsurprising bugs:
  does prompt once for stdin when called as "argdoc -", like bash "grep -R", unlike bash "cat -"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  argdoc.py -h                          # show this help message and exit
  argdoc.py                             # show a template doc and how to call arg doc
  argdoc.py argdoc.py                   # show the file doc and how to call (same as --rip argdoc)

  argdoc.py --rip doc argdoc.py         # show just the docstring (by reading without importing)
  argdoc.py --rip argparse argdoc.py    # show how the file calls arg parse
  argdoc.py --rip argdoc argdoc.py      # show how the file could call arg doc

  argdoc.py argdoc.py --                # parse no arg with the file's arg doc
  argdoc.py argdoc.py -- --help         # parse the arg "--help" with the file's arg doc
  argdoc.py argdoc.py -- hi world       # parse the two args "hi world" with the file's arg doc
'''

# FIXME: option (surely not default?) to push the autocorrection into the Arg Doc
# FIXME: comment --rip argparse at colliding "dest"s from multiple args, such as "[--ymd YMD] [YMD]"
# FIXME: parsed args whose names begin with a '_' skid shouldn't print, via argparse.SUPPRESS
# FIXME: consider [FILE [FILE ...]] in usage: argdoc.py [-h] [--rip SHRED] [FILE] [-- ...]

# FIXME: think into who signs as author of ArgumentError log message: "argdoc.py" or the "prog"?


from __future__ import print_function

import argparse
import collections
import os
import re
import shlex
import sys
import textwrap


DEFAULT_EPILOG = textwrap.dedent(
    """
    examples:
      Oh no! No examples disclosed!! 💥 💔 💥
    """
).strip()  # style with "Oh no! ... 💥 💔 💥" to rhyme with failures of the Black auto-styling app


#
# Serve as an importable module
#


def format_usage():
    """Sum the usage into a line of text closed by an end-of-line char"""

    parser = ArgumentParser()
    usage_chars = parser.format_usage()

    return usage_chars


def parse_args(args=None, namespace=None, doc=None, doc_filename=None):
    """Parse args as helped by Module Doc"""

    argdoc_argv_tail = sys.argv[1:] if (args is None) else args

    quiet = True
    for arg in argdoc_argv_tail:
        if (arg == "-h") or ((len(arg) >= len("--h")) and "--help".startswith(arg)):
            quiet = False
        # FIXME: fit quiet/not more tightly to apps that declare alternative help options

    try:
        parser = ArgumentParser(doc, doc_filename=doc_filename, quiet=quiet)
    except ArgDocError as exc:
        stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)

    args_ = parser.parse_args(args, namespace=namespace)
    help_options = scrape_help_options(doc=parser.format_help())

    joined_help_options = " ".join(help_options)
    assert joined_help_options.split() == help_options

    if any(vars(args_).get(_) for _ in help_options):
        parser.print_help()
        sys.exit(0)  # exit zero from printing help

    return args_


def print_help(file=None):
    """Print the help lines to the file, else to Stdout"""

    file_ = file if file else sys.stdout
    parser = ArgumentParser()
    parser.print_help(file=file_)


def print_usage(file=None):
    """Print the usage line to the file, else to Stdout"""

    file_ = file if file else sys.stdout
    parser = ArgumentParser()
    parser.print_usage(file=file_)


# FIXME: class ArgumentParser
def ArgumentParser(doc=None, doc_filename=None, quiet=False):
    """Compile the Doc into Parser Source, and exec that source to build the Parser"""
    # FIXME: factor out overlap with the "def run_argdoc_app" of _ArgDocApp

    if not quiet:
        main.args.verbose += 1

    main_module = sys.modules["__main__"]
    if doc is None:
        doc = main_module.__doc__
    if doc_filename is None:
        doc_filename = main_module.__file__

    coder = _ArgDocCoder()
    parser_source = coder.compile_parser_source_from(doc, doc_filename=doc_filename)
    parser = coder.exec_parser_source(parser_source)

    if not quiet:

        app = _ArgDocApp()
        file_doc = doc

        help_doc = parser.format_help()

        if file_doc.strip():
            app.compare_file_to_help_doc(
                file_doc, doc_filename=doc_filename, help_doc=help_doc
            )

    return parser


def scrape_help_options(doc):
    """Print help and exit zero, if an option parsed is doc'ced as print help"""

    help_lines = doc.splitlines()

    help_options = list()
    while help_lines and (help_lines[0] != "optional arguments:"):
        help_lines = help_lines[1:]
    if help_lines and (help_lines[0] == "optional arguments:"):
        help_lines = help_lines[1:]

        while help_lines and (
            help_lines[0].startswith(" ") or not help_lines[0].strip()
        ):
            words = help_lines[0].split()
            help_lines = help_lines[1:]

            if words and words[0].startswith("-"):
                options = words[:1]
                help_words = words[1:]
                if words[0].endswith(","):
                    options = words[:2]
                    help_words = words[2:]

                if "show this help message and exit" == " ".join(help_words):
                    help_options.extend(_.lstrip("-").rstrip(",") for _ in options)

    return help_options


#
# Run from the command line
#


class ArgDocError(Exception):
    pass


def main(argv):
    """Run from the command line"""

    shline = pyish_shlex_join(argv)
    app = _ArgDocApp()

    try:
        app.run_main_argv(argv)
    except ArgDocError as exc:
        stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)
    except Exception:
        stderr_print("argdoc.py: error: unhandled exception at:  {}".format(shline))
        raise


main.args = argparse.Namespace(verbose=0)


class _ArgDocApp:
    """Bundle some command-line services"""

    def run_main_argv(self, argv):
        """Run from the command line, but trust the caller to interpret exceptions"""

        args = self.parse_argdoc_argv(argv)
        args.verbose = True

        main.args = args

        self.run_argdoc_app(
            doc_filename=args.file,
            shred=args.shred,
            argv_separator=args.argv_separator,
            tail_argv=args.args,
        )

    def parse_argdoc_argv(self, argv):
        """Call the ArgParse "parse_args" but finish what it started"""

        argdoc_argv_tail = argv[1:]
        args = parse_args(argdoc_argv_tail)
        args = self._complete_args_file(args, argv=argv)
        self._complete_args_shred(args)
        self._complete_args_args(args, argv=argv)

        return args

    def _complete_args_file(self, args, argv):
        """Complete the FILE in usage: ... [FILE] [-- [ARG [ARG ...]]]"""

        #  Auto-correct the ArgV Tail to choose a FILE, if arg "--" given in place of FILE

        if argv[1:] and (argv[1] == "--") and args.file:

            assert args.file == argv[2]

            argdoc_argv_tail = argv[1:]
            completed_argv_tail = [os.devnull] + argdoc_argv_tail
            args = parse_args(completed_argv_tail)  # call again, if needed

            assert args.file == os.devnull

        # Supply the FILE if not given on the command line, and not supplied by auto-correction

        args.file = os.devnull if (args.file is None) else args.file

        # Succeed

        return args

    def _complete_args_shred(self, args):
        """Complete the SHRED in usage: ... --rip SHRED"""

        shred = None
        if args.rip:

            shreds = "argdoc argparse doc".split()  # FIXME: pull these from the arg doc
            for shred_ in shreds:
                if shred_.startswith(args.rip):
                    shred = shred_
                    break

            if not shred:
                stderr_print(
                    "argdoc.py: error: choose --rip from {}, do not choose {!r}".format(
                        shreds, args.rip
                    )
                )
                sys.exit(1)

        args.shred = shred

    def _complete_args_args(self, args, argv):
        """Complete the ARGS in usage: ... [-- [ARG [ARG ...]]]"""

        argdoc_argv_tail = argv[1:]
        args.argv_separator = "--" if ("--" in argdoc_argv_tail) else None

        if args.args and not args.argv_separator:
            stderr_print(format_usage().rstrip())
            stderr_print(  # a la standard error: unrecognized arguments
                "argdoc.py: error: unrecognized args: {!r}, in place of {!r}".format(
                    pyish_shlex_join(args.args), pyish_shlex_join(["--"] + args.args),
                )
            )
            sys.exit(2)  # exit 2 from rejecting usage

        return args

    def run_argdoc_app(self, doc_filename, shred, argv_separator, tail_argv):
        """Print the Arg Doc, or compile it, or run it"""
        # FIXME: factor out overlap with the "class ArgumentParser" of "argdoc.py"

        coder = _ArgDocCoder()

        # Fetch the Arg Doc, compile it, and hope it doesn't crash the compiler

        relpath = doc_filename
        if doc_filename == "-":
            relpath = "/dev/stdin"
            prompt_tty_stdin()

        # Read the module doc from the file, with an option to rip and quit

        file_doc = read_docstring_from(relpath).strip()

        if shred == "doc":
            self.rip_doc(file_doc)

            return

        # Compile the file doc, with an option to rip and quit

        parser_source = coder.compile_parser_source_from(
            file_doc, doc_filename=doc_filename
        )

        help_options = list()
        if file_doc:
            help_options = scrape_help_options(file_doc)
            if coder.coder_added_help:
                assert "help" in help_options
                assert "h" in help_options
                del help_options[help_options.index("help")]
                del help_options[help_options.index("h")]

        joined_help_options = " ".join(help_options)
        assert joined_help_options.split() == help_options

        if shred == "argparse":
            self.rip_argparse(parser_source, joined_help_options)

            return

        # Run the parser source to build the parser, with an option to rip and quit

        parser = coder.exec_parser_source(parser_source)
        help_doc = parser.format_help()

        if file_doc.strip():
            self.compare_file_to_help_doc(
                file_doc, doc_filename=doc_filename, help_doc=help_doc
            )

        if (shred == "argdoc") or not argv_separator:
            self.rip_argdoc(help_doc, doc_filename=doc_filename)

            return

        # Run the parser, and rip the args that result (except when printing help and exiting zero)
        # Trace the args prefaced by "+ ", as if prefaced by Bash PS4

        print("+ {}".format(pyish_shlex_join([doc_filename] + tail_argv)))

        args = parser.parse_args(tail_argv)

        if any(vars(args).get(_) for _ in help_options):
            parser.print_help()
            sys.exit(0)  # exit zero from printing help

        self.rip_args(args)

    def rip_doc(self, file_doc):
        """Show just the docstring"""

        print(black_triple_quote_repr(file_doc.strip()))

    def rip_argparse(self, parser_source, joined_help_options):
        """Show how the file calls Arg Parse"""

        two_imports = "import argparse\nimport textwrap"
        assert two_imports in parser_source

        patched = parser_source
        if joined_help_options:
            three_imports = "import argparse\nimport sys\nimport textwrap"
            patched = parser_source.replace(two_imports, three_imports)

        print(patched.rstrip())
        print()

        d = r"    "  # choose indentation
        print("args = parser.parse_args()")
        if joined_help_options:
            # FIXME: reduce this down to:  if args.help or args.h or ...:
            # FIXME: by way of choosing the "add_argument" "dest" correctly, eg, at --x -y
            print(
                "if any(vars(args).get(_) for _ in {}.split()):".format(
                    black_repr(joined_help_options)
                )
            )
            print(d + "parser.print_help()")
            print(d + "sys.exit(0)  # exit zero from printing help")
        print()

        print("print(args)")

    def compare_file_to_help_doc(self, file_doc, doc_filename, help_doc):
        """Show the Help Doc printed by an Arg Doc file calling Arg Parse"""

        if file_doc.strip() == help_doc.strip():
            return

        file_doc_shline = "argdoc.py --rip doc {} >a".format(doc_filename)
        doc_help_shline = "argdoc.py --rip argdoc {} >b".format(doc_filename)
        diff_urp_hline = "diff -urp a b"

        stderr_print(
            "argdoc.py: warning: doc vs help diffs at: {}".format(doc_filename)
        )
        stderr_print(
            "argdoc.py: diff details at:  {} && {} && {}".format(
                file_doc_shline, doc_help_shline, diff_urp_hline
            )
        )

    def rip_argdoc(self, help_doc, doc_filename):
        """Show how the file could call Arg Doc"""

        print(
            textwrap.dedent(
                """
                #!/usr/bin/env python3
                """
            ).strip()
        )
        print()

        print(black_triple_quote_repr(help_doc.strip()))
        print()
        print()  # suggest two blank lines between docstring and first import

        print(
            textwrap.dedent(
                r"""
                import sys

                import argdoc


                def main():
                    args = argdoc.parse_args()
                    main.args = args
                    sys.stderr.write("{}\n".format(args))
                    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
                    sys.stderr.write("$prog: error: not implemented\n")
                    sys.exit(2)  # exit 2 from rejecting usage


                if __name__ == '__main__':
                    main()
                """.replace(
                    "$prog", doc_filename  # "$prog" a la "string.Template"s
                )
            ).strip()
        )

    def rip_args(self, args):
        """Show the results of parsing the args with the Arg Doc"""

        for (k, v,) in sorted(vars(args).items()):
            if not k.startswith("_"):
                print("{k}={v!r}".format(k=k, v=v))


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


class _ArgDocCoder(
    argparse.Namespace
):  # FIXME: test how black'ened its emitted style is
    """Work up an ArgumentParser to match its Arg Doc"""

    def compile_parser_source_from(self, doc, doc_filename):
        """Compile an Arg Doc into Parse Source"""

        # Parse the Arg Doc

        parts = _ArgDocSyntax()
        taker = _ArgDocTaker(parts, doc=doc)
        taker.take_arg_doc_into(parts=parts)

        self.parts = parts

        # Compile the arguments first, so as to construct a one line summary of usage
        # Don't mention duplicate "add_argument" "dest"s  # FIXME: maybe someday?

        args_py_lines = self.emit_arguments()
        args_emitted_usage = self.emitted_usage

        # Emit imports

        d = r"    "  # choose indentation

        lines = list()

        lines.append("#!/usr/bin/env python")
        lines.append("# -*- coding: utf-8 -*-")
        # <= dashed "utf-8" slightly more standard than skidded "utf_8"
        # per https://docs.python.org/3/library/codecs.html

        lines.append("import argparse")
        lines.append("import textwrap")
        lines.append("")

        # Open a call to the Parser constructor

        what = os.path.split(__file__)[-1]
        comment = "  # copied from {!r} by {!r}".format(doc_filename, what)
        lines.append("parser = argparse.ArgumentParser({}".format(comment))

        # Name the app

        prog = parts.prog if parts.prog else os.path.split(doc_filename)[-1]

        assert prog  # always give a prog name to ArgParse, don't let them guess
        repr_prog = black_repr(prog)
        lines.append(d + "prog={repr_prog},".format(repr_prog=repr_prog))
        # FIXME: think into {what} in place of {what}.py, and more unusual prog names
        # assert prog == os.path.split(doc_filename)[-1]

        # Construct a summary Usage Line from the Prog and the zero or more Argument Lines

        emitted_usage = prog if (args_emitted_usage is None) else args_emitted_usage
        if prog == "ls.py":  # FIXME FIXME: teach "argdoc.py" to emit multiline usage
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
            verbose_print("argdoc.py: warning: doc'ced usage: {}".format(parts_usage))
            verbose_print("argdoc.py: warning: emitted usage: {}".format(emitted_usage))

        # Resort to bypassing the ArgParse constructor of Usage Lines, only when desperate

        if emitted_usage:
            if "..." in emitted_usage:
                lines.append(
                    d + "usage={usage},".format(usage=black_repr(emitted_usage))
                )

        # Explain the App in one line, if possible

        description_line = parts.description_line
        if not doc:
            assert not parts.usage
            assert not parts.description_line
            description_line = "do good stuff"

        if parts.usage and not parts.description_line:
            stderr_print(
                "argdoc.py: warning: no one line description explains prog {!r}".format(
                    prog
                )
            )

        if description_line:
            lines.append(
                d
                + "description={repr_description},".format(
                    repr_description=black_repr(description_line)
                )
            )

        # Explicitly override the conventional help optional argument, or explicitly don't

        add_help = bool(parts.add_help)
        if not doc:
            assert parts.add_help is None
            add_help = True

        self.coder_added_help = add_help

        lines.append(d + "add_help={add_help},".format(add_help=add_help))

        # Stop ArgParse from aggressively incompetently resplitting text

        lines.append(d + "formatter_class=argparse.RawTextHelpFormatter,")

        # Nudge people to give examples to explain how to call the App well

        epilog = DEFAULT_EPILOG if (parts.epilog_chars is None) else parts.epilog_chars
        lines.append(d + "epilog=textwrap.dedent(")
        for line in black_triple_quote_repr(epilog).splitlines():
            lines.append(d + d + line)
        lines.append(d + "),")

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

        emitted_usage = None  # FIXME: think more about py_phrases when not parts.prog
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

        assert nargs in (None, "*", "?",)  # .ZERO_OR_MORE .OPTIONAL

        # Name the attribute for this positional option in the namespace built by "parse_args"
        # Go with the metavar, else guess the English plural of the metavar

        dest = metavar.lower()
        if nargs == "*":  # "*" argparse.ZERO_OR_MORE
            dest = plural_en(metavar.lower())

        # Emit usage phrase

        self.args_py_phrases.append(usage_phrase)

        # Emit Python source

        d = r"    "  # choose indentation

        repr_dest = black_repr(dest)
        repr_metavar = black_repr(metavar)
        repr_nargs = black_repr(nargs)
        repr_help = black_repr(arg_help).replace("%", "%%")

        head_lines = [
            "parser.add_argument(",
        ]

        if nargs is None:

            if dest == metavar:
                mid_lines = [
                    d + "{repr_dest},".format(repr_dest=repr_dest),
                ]
            else:
                mid_lines = [
                    d
                    + "{repr_dest}, metavar={repr_metavar},".format(
                        repr_dest=repr_dest, repr_metavar=repr_metavar
                    ),
                ]

        else:

            if dest == metavar:
                mid_lines = [
                    d
                    + "{repr_dest}, nargs={repr_nargs},".format(
                        repr_dest=repr_dest, repr_nargs=repr_nargs
                    ),
                ]
            else:
                mid_lines = [
                    d
                    + "{repr_dest}, metavar={repr_metavar}, nargs={repr_nargs},".format(
                        repr_dest=repr_dest,
                        repr_metavar=repr_metavar,
                        repr_nargs=repr_nargs,
                    ),
                ]

        tail_lines = [
            d + "help={repr_help}".format(repr_help=repr_help),
            d + ")",
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

        options = (
            option,
            alt_option,
        )

        concise_options = list(_ for _ in options if _ and not _.startswith("--"))
        assert len(concise_options) <= 1
        concise = concise_options[0] if concise_options else None

        mnemonic_options = list(_ for _ in options if _ and _.startswith("--"))
        assert len(mnemonic_options) <= 1
        mnemonic = mnemonic_options[0] if mnemonic_options else None

        # Name the attribute for this positional option in the namespace built by "parse_args"
        # Go with the mnemonic option, else the metavar, else the concise option

        if mnemonic:
            dest = mnemonic.lower()
        elif metavar:
            dest = metavar.lower()
        else:
            assert concise
            dest = concise.lower()

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
        assert nargs in (None, "?",)  # .OPTIONAL  # FIXME: add "*" .ZERO_OR_MORE

        # Emit Python source

        d = r"    "  # choose indentation

        repr_option = black_repr(option)
        repr_alt = black_repr(alt_option)
        repr_var = black_repr(metavar)
        repr_dest = black_repr(dest)
        repr_default = None if (default is None) else black_repr(default)
        repr_nargs = None if (nargs is None) else black_repr(nargs)

        head_lines = [
            "parser.add_argument(",
        ]

        if not metavar:

            action = "count"
            repr_action = black_repr(action)

            if not alt_option:
                assert dest == option.lower()
                mid_lines = [
                    d
                    + "{repr_option}, action={repr_action},".format(
                        repr_option=repr_option, repr_action=repr_action
                    )
                ]
            else:
                assert dest == mnemonic.lower()
                mid_lines = [
                    d
                    + "{repr_option}, {repr_alt}, action={repr_action},".format(
                        repr_option=repr_option,
                        repr_alt=repr_alt,
                        repr_action=repr_action,
                    )
                ]

        else:

            suffixes = ""
            if nargs is not None:
                suffixes += " nargs={repr_nargs},".format(repr_nargs=repr_nargs)
            if default is not None:
                suffixes += " default={repr_default},".format(repr_default=repr_default)

            if not alt_option:
                if dest == option.lower():
                    mid_lines = [
                        d
                        + "{repr_option}, metavar={repr_var},{suffixes}".format(
                            repr_option=repr_option,
                            repr_var=repr_var,
                            suffixes=suffixes,
                        )
                    ]
                else:
                    mid_lines = [
                        d
                        + "{repr_option}, metavar={repr_var}, dest={repr_dest},{suffixes}".format(
                            repr_option=repr_option,
                            repr_var=repr_var,
                            repr_dest=repr_dest,
                            suffixes=suffixes,
                        )
                    ]
            else:
                assert dest == mnemonic.lower()
                mid_lines = [
                    d
                    + "{repr_option}, {repr_alt}, metavar={repr_var},{suffixes}".format(
                        repr_option=repr_option,
                        repr_alt=repr_alt,
                        repr_var=repr_var,
                        suffixes=suffixes,
                    )
                ]

        tail_lines = [
            d + "help={repr_help}".format(repr_help=repr_help),
            ")",
        ]

        lines = head_lines + mid_lines + tail_lines

        return lines

    def exec_parser_source(self, parser_source):
        """Run the parser source to build the Parser"""

        global_vars = {}
        try:
            exec(parser_source, global_vars)
        except argparse.ArgumentError as exc:
            stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(2)  # exit 2 from rejecting usage

        parser = global_vars["parser"]
        return parser


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

    def __init__(self, parts, doc):

        self.parts = None  # the fragments of source matched by this parser

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
                        "argdoc.py: warning: optionals declared before positionals"
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
                "argdoc.py: warning: meaningless (late?) usage phrases:  {}".format(
                    uses.remains
                )
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
            startswith_dash="",
            arg_phrases=self.parts.uses.positionals_phrases,
        )

    def accept_optionals_declarations(self):
        """Take the Optional arguments"""

        self.parts.optionals_declarations = self.accept_tabulated_arguments(
            "optional arguments:",
            startswith_dash="-",
            arg_phrases=self.parts.uses.optionals_phrases,
        )

    def accept_tabulated_arguments(self, tagline, startswith_dash, arg_phrases):
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

                argument_lines = self.accept_argument_lines(tagline=tagline)

                if not argument_lines:
                    verbose_print(
                        "argdoc.py: warning: no arguments declared inside {!r}".format(
                            tagline
                        )
                    )

                arg_declarations = self.reconcile_arg_lines_phrases(
                    argument_lines,
                    tagline=tagline,
                    startswith_dash=startswith_dash,
                    arg_phrases=arg_phrases,
                )

        return arg_declarations

    def reconcile_arg_lines_phrases(
        self, argument_lines, tagline, startswith_dash, arg_phrases
    ):

        self._disentangle_optionals_positionals(
            argument_lines, tagline=tagline, startswith_dash=startswith_dash
        )

        phrases_by_arg_key = self._index_phrases_by_arg_key(arg_phrases)
        lines_by_arg_key = self._index_lines_by_arg_key(argument_lines)

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
            startswith_dash=startswith_dash,
        )

        return arg_declarations

    def _reconcile_arg_declarations(
        self, arg_keys, phrases_by_arg_key, lines_by_arg_key, startswith_dash,
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

            assert arg_phrase.concise in (arg_line.option, arg_line.alt_option, None,)
            assert arg_phrase.mnemonic in (arg_line.option, arg_line.alt_option, None,)
            assert arg_line.metavar == arg_phrase.metavar
            assert (not arg_line.alt_metavar) or (
                arg_line.alt_metavar == arg_phrase.metavar
            )

            if not startswith_dash:  # positional argument
                assert arg_phrase.nargs in (None, "*", "?",)  # .ZERO_OR_MORE .OPTIONAL
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
                    "argdoc.py: warning: multiple phrase declarations of {}".format(
                        arg_key
                    )
                )

            phrases_by_arg_key[arg_key] = arg_phrase

        return phrases_by_arg_key

    def _index_lines_by_arg_key(self, argument_lines):
        """Calculate words comparable between Argument Declaration Lines and Usage Phrase"""

        lines_by_arg_key = collections.OrderedDict()  # till Dec/2016 CPython 3.6
        for argument_line in argument_lines:

            arg_line = ArgumentLineSyntaxTaker(argument_line)
            # call ArgumentLineSyntaxTaker as early as the two PhraseSyntaxTaker's
            # FIXME: detect multiple line declarations earlier

            arg_key = arg_line._calc_arg_key()
            if arg_key in lines_by_arg_key.keys():
                verbose_print(
                    "argdoc.py: warning: multiple line declarations of {}".format(
                        arg_key
                    )
                )

            lines_by_arg_key[arg_key] = arg_line

        return lines_by_arg_key

    def _disentangle_optionals_positionals(
        self, argument_lines, tagline, startswith_dash
    ):
        """Require Positionals declared strictly apart from Optionals, and vice versa"""

        for argument_line in argument_lines:
            stripped = argument_line.strip()

            doc_startswith_dash = "-" if stripped.startswith("-") else ""
            if doc_startswith_dash != startswith_dash:

                raise ArgDocError(
                    "{!r} != {!r} inside {!r} at:  {}".format(
                        doc_startswith_dash, startswith_dash, tagline, argument_line
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

        assert bool(arg_phrase.concise) ^ bool(arg_phrase.mnemonic)

        argument_line = ""
        if arg_phrase.concise:
            argument_line += arg_phrase.concise
        if arg_phrase.mnemonic:
            argument_line += arg_phrase.mnemonic
        if arg_phrase.metavar:
            argument_line += " "
            argument_line += arg_phrase.metavar
            # an arg phrase alone can't imply an arg line of:  --mnemonic [OPTIONAL_METAVAR]

        arg_line = ArgumentLineSyntaxTaker(argument_line)

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
                "argdoc.py: warning: usage via phrases:  {}".format(
                    usage_phrase_arg_keys
                )
            )
            verbose_print(
                "argdoc.py: warning: vs usage at lines:  {}".format(usage_line_arg_keys)
            )
            # FIXME: suggest multiple usage lines when too wide for one usage line

            if set(phrase_arg_keys) == set(line_arg_keys):
                verbose_print(
                    "argdoc.py: warning: same sets, different orders, as usage and as {}".format(
                        tagline.rstrip(":")
                    )
                )
            else:
                verbose_print(
                    "argdoc.py: warning: different sets of words as usage and as {}".format(
                        tagline.rstrip(":")
                    )
                )

    def accept_argument_lines(self, tagline):
        """Take zero or more dented lines as defining Positional or Optional arguments"""

        taker = self.taker
        taker.accept_blank_shards()

        argument_lines = list()
        dent = None
        while taker.peek_more():
            argument_line = taker.peek_one_shard()
            if not argument_line.startswith(" "):
                break
            assert argument_line.startswith(" ")

            denting = dent
            dent = str_splitdent(argument_line)
            if denting and (denting[0] < dent[0]):
                argument_lines[-1] += "\n" + argument_line  # FIXME: mutation
            else:
                argument_lines.append(argument_line)

            taker.take_one_shard()

            taker.accept_blank_shards()

        return argument_lines

    def accept_doc_remains(self):
        """
        Take zero or more trailing lines, as if they must be the Epilog

        Aggressively take whatever trailing lines exist as arbitrary epilog:
        like let them "optional args:", or "positional arguments", or blank, whatever
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
        self.positionals_phrases = None  # the FILE or [FILE] or [FILE [FILE ...]] or [-- [ARG [ARG ...]] and such


class _UsagePhrasesTaker(argparse.Namespace):
    """Pick an Arg Doc Usage Line apart, char by char"""

    def __init__(self, usage_chars):

        self.uses = None  # the fragments of source matched by this parser
        self.taker = ShardsTaker(shards=usage_chars)

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

            raise ArgDocError(reason)

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

            raise ArgDocError(reason)

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
            startswith_bracket_dash_dash_blank = taker.peek_equal_shards("[-- ")
            # FIXME: simplify the syntax differences between optionals and positionals

            argument_phrase = self.accept_one_arg_phrase()

            # Accept [-h] or [--help] or [-w WIDTH] and such, and
            # accept FILE or [FILE] or [FILE [FILE ...]] and such

            if startswith_bracket_dash and not startswith_bracket_dash_dash_blank:
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
                reason = "{} of [ not balanced by {} of ]".format(openings, closings)
                raise ArgDocError(reason)

        return argument_phrase

    def accept_usage_remains(self):

        taker = self.taker
        uses = self.uses

        remains = "".join(taker.peek_more_shards())
        taker.take_some_shards(len(remains))

        uses.remains = remains  # FIXME: is this always empty?


class ArgumentLineSyntaxTaker(argparse.Namespace):
    """Parse one line of Arg Doc argument declaration"""

    def __init__(self, argument_line):

        self.arg_source = None
        self.arg_help = None

        self.option = None
        self.metavar = None
        self.alt_option = None
        self.alt_metavar = None
        self.nargs = None
        self.default = None

        accepted = self._accept_argument_line(argument_line)
        if not accepted:
            self._reject_argument_line(argument_line)

    def _accept_argument_line(self, argument_line):
        """Pick attributes out of the argument line"""

        # Split off the help words
        # found past "  " in the first line, or found past the indentation of later lines

        arg_source = argument_line.strip()
        arg_help = None

        index = arg_source.find("  ")
        if index >= 0:
            arg_help = arg_source[index:].lstrip()
            arg_source = arg_source[:index].rstrip()

        self.arg_source = arg_source
        self.arg_help = arg_help

        # Take one, two, or four words presented before the first "  " double-blank, if any

        words = arg_source.split()

        len_words = len(words)
        if len_words not in (1, 2, 4,):
            return

        self._take_1_2_4_argument_words(words)

        # Take "[METAVAR]" in the argument line as meaning nargs = "?"  # argparse.OPTIONAL

        if self.metavar:
            if (self.alt_metavar is None) or (self.metavar == self.alt_metavar):
                name = self.metavar.replace("[", "").replace("]", "")
                if self.metavar == "[{}]".format(name):
                    self.metavar = name
                    self.nargs = (
                        "?"  # argparse.OPTIONAL  # for positional or optional argument
                    )
                    self.default = False

        # Require a positional metavar, or else the dash or dashes of an optional argument

        if (not self.metavar) and (not self.option):
            return

        # Require consistent metavars, or else no metavars

        if self.metavar and self.alt_metavar and (self.metavar != self.alt_metavar):
            return

        # Require emitted source output to match compiled source input, precisely

        if self.format_argument_line().split() != argument_line.split():
            return

        # Succeed

        return True

    def _reject_argument_line(self, argument_line):
        """Raise ArgDocError to reject the "argument_line" not taken"""

        arg_source = self.arg_source

        want = "[-c|--mnemonic] [METAVAR|[METAVAR]][,] ..."  # approximately
        got = argument_line.strip()

        if arg_source:  # true while no calls ArgumentLineSyntaxTaker on an empty line

            words = arg_source.split()

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
        """Return the possible parses of one or two [-c|--mnemonic] [METAVAR] argument syntax"""

        # Take the 1 word of --mnemonic, -c, or METAVAR

        (word0, metavar0, concise0, mnemonic0,) = self._take_argument_word(words[0])

        if word0.startswith("--"):
            self.option = mnemonic0
        elif word0.startswith("-"):
            self.option = concise0
        else:
            self.metavar = metavar0

        # Take the 2 words of -c, --mnemonic, --mnemonic, -c, or -c|--mnemonic METAVAR

        if words[1:]:

            (word1, metavar1, concise1, mnemonic1,) = self._take_argument_word(words[1])

            if word1.startswith("--"):
                self.alt_option = mnemonic1
            elif word1.startswith("-"):
                self.alt_option = concise1
            else:
                self.metavar = metavar1

            # Take the 4 words of -c METAVAR, --mnemonic METAVAR,
            # Or reversed as --mnemonic METAVAR, -c METAVAR

            if words[2:]:

                (word2, _, concise2, mnemonic2,) = self._take_argument_word(words[2])
                (word3, metavar3, _, _,) = self._take_argument_word(words[3])

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

        return (
            word,
            metavar,
            concise,
            mnemonic,
        )

    def format_argument_line(self):
        """Format as a line of optional or positional argument declaration in an Arg Doc"""

        source_words = list(self.format_argument_line__source_words())

        words = (source_words + ["", self.arg_help]) if self.arg_help else source_words
        assert None not in words

        joined = " ".join(str(_) for _ in words)
        return joined

    def format_argument_line__source_words(self):
        """Format as the first 1, 2, or 4 words of an argument declaration line in an Arg Doc"""

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
                words = (
                    (self.option + ","),
                    self.alt_option,
                )
            else:
                words = (
                    self.option,
                    (metavar + ","),
                    self.alt_option,
                    alt_metavar,
                )

        else:
            assert self.option and not self.alt_option

            if not metavar:
                words = (self.option,)
            else:
                words = (
                    self.option,
                    metavar,
                )

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
                words = (
                    self.option,
                    self.metavar,
                )

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
                words = (
                    self.concise,
                    self.metavar,
                )
            elif self.mnemonic:
                words = (
                    self.mnemonic,
                    self.metavar,
                )

        return words


class PositionalPhraseSyntaxTaker(argparse.Namespace):
    """Parse one of FILE or [FILE] or [FILE [FILE ...]] or [-- [ARG [ARG ...]] and such"""

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


# deffed in many files  # missing from docs.python.org
class ShardsTaker(argparse.Namespace):
    """
    Walk once thru source chars, as split

    Define "take" to mean require and consume
    Define "peek" to mean look ahead if present, else into an infinite stream of None's
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_shards(self, shards):
        """Give shards"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Consume the next shard, without returning it"""

        self.shards = self.shards[1:]

    def take_some_shards(self, count):
        """Take a number of shards"""

        self.shards = self.shards[count:]

    def peek_one_shard(self):
        """Return the next shard, without consuming it"""

        if self.shards:  # infinitely many None's past the end
            return self.shards[0]

    def peek_some_shards(self, count):
        """Return the next few shards, without consuming them"""

        nones = count * [None]
        some = (self.shards[:count] + nones)[:count]

        return some

    def peek_equal_shards(self, hopes):
        """Return the next few"""

        some = self.peek_some_shards(len(hopes))
        if some == list(hopes):
            return True

    def take_beyond_shards(self):
        """Do nothing if all shards consumed, else mystically crash"""

        assert not self.peek_more()

    def peek_more(self):
        """Return True while shards remain"""

        more = bool(self.shards)
        return more

    def peek_more_shards(self):
        """List remaining shards """

        more_shards = list(self.shards)
        return more_shards

    def accept_blank_shards(self):
        """Discard zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():
                break
            self.take_one_shard()

    def peek_upto_blank_shard(self):
        """Peek the non-blank shards here, if any"""

        shards = list()
        for shard in self.shards:
            if not shard.strip():
                break
            shards.append(shard)

        return shards


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


def read_docstring_from(relpath):
    """
    Read the docstring from a python file without importing the rest of it

    Specifically read the first lines from triple-quote to triple-quote \"\"\" or ''',
    but ignore leading lines begun with a hash #
    """

    try:
        with open(relpath, "rt") as reading:
            (texts, raw, qqq, len_lines,) = _scrape_docstring_from(reading)
    except IOError as exc:  # such as Python 3 FileNotFoundError
        stderr_print("argdoc.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)

    doc = _eval_scraped_docstring(texts, raw, qqq, len_lines, relpath)
    return doc


def _scrape_docstring_from(reading):
    """Scrap sourcelines of docstring from source of module"""
    # FIXME: correctly forward the leading and trailing whitespace

    texts = list()
    raw = None
    qqq = None
    len_lines = 0

    for line in reading.readlines():
        len_lines += 1

        text = line.rstrip()

        if texts or text:
            if not text.strip().startswith("#"):
                if not qqq:
                    if '"""' in text:
                        qqq = '"""'
                        raw = 'r"""' in text
                    elif "'''" in text:
                        qqq = "'''"
                        raw = "r'''" in text
                    else:
                        pass
                elif qqq in text:
                    break
                else:
                    texts.append(text)

    return (
        texts,
        raw,
        qqq,
        len_lines,
    )


def _eval_scraped_docstring(texts, raw, qqq, len_lines, relpath):
    """Convert to string from sourcelines of module docstring"""
    # FIXME: see the quoted text as r""" only when explicitly marked as "r"

    if len_lines and (qqq is None):
        qqq1 = '"""'
        qqq2 = "'''"
        stderr_print(
            "argdoc.py: warning: no {} found and no {} found in {}".format(
                qqq1, qqq2, relpath
            )
        )

    if not raw:
        fuzzes = list(_ for _ in texts if "\\" in _)
        if fuzzes:
            stderr_print(
                "argdoc.py: warning: docstring of backslash led by {} not by r{} in {}".format(
                    qqq, qqq, relpath
                )
            )

    repr_doc = black_triple_quote_repr("\n".join(texts))

    doc_source = "doc = " + repr_doc

    global_vars = {}
    exec(doc_source, global_vars)

    doc = global_vars["doc"]
    return doc


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # since Oct/2019 Python 3.8
def pyish_shlex_join(argv):
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

    min_info_ = min_info if min_info else (3, 7,)  # June/2019 Python 3.7

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

    return (
        dent,
        tail,
    )


# deffed in many files  # missing from docs.python.org
def str_splitword(chars, count=1):
    """Return the leading whitespace and words, split from the remaining chars"""

    tail = chars
    if count >= 1:
        counted_words = chars.split()[:count]
        for word in counted_words:
            tail = tail[tail.index(word) :][len(word) :]

    if not tail:
        return (
            chars,
            "",
        )

    head = chars[: -len(tail)]

    return (
        head,
        tail,
    )


# deffed in many files  # missing from docs.python.org
def verbose_print(*args):
    sys.stdout.flush()
    if main.args.verbose:
        # print(*args, **kwargs, file=sys.stderr)  # SyntaxError in Python 2
        print(*args, file=sys.stderr)
    sys.stderr.flush()


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


# copied from:  git clone https://github.com/pelavarre/pybashish.git
