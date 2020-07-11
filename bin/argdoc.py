#!/usr/bin/env python3

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
  to see review comments pop up to work with you, you must damage an arg doc and run this again
  cutting out all "optional arguments" declarations leaves you with no "-h, --help" option

examples:
  argdoc.py -h                          # show this help message
  argdoc.py                             # show a template doc and how to call arg doc
  argdoc.py argdoc.py                   # show the file doc and how to call (same as --rip argdoc)

  argdoc.py --rip doc argdoc.py         # show just the docstring (by reading without importing)
  argdoc.py --rip argparse argdoc.py    # show how the file calls arg parse
  argdoc.py --rip argdoc argdoc.py      # show how the file could call arg doc

  argdoc.py argdoc.py --                # parse no arg with the file's arg doc
  argdoc.py argdoc.py -- --help         # parse the arg "--help" with the file's arg doc
  argdoc.py argdoc.py -- hi world       # parse the two args "hi world" with the file's arg doc
'''
# FIXME: parsed args whose names begin with a '_' skid shouldn't print here, via argparse.SUPPRESS
# FIXME: consider looping over a list of [FILE [FILE ...]]
# FIXME: autocorrect wrong Arg Docs

from __future__ import print_function

import argparse
import os
import re
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


def parse_args(args=None, namespace=None, doc=None, doc_filename=None):
    """Parse args as helped by Module Doc"""

    if args is None:
        args = sys.argv[1:]

    parser = make_parser(doc, doc_filename=doc_filename)
    space = parser.parse_args(args, namespace=namespace)

    return space


def make_parser(doc=None, doc_filename=None):
    """Compile the Doc into Parser Source, and exec that source to build the Parser"""

    main_module = sys.modules["__main__"]
    if doc is None:
        doc = main_module.__doc__
    if doc_filename is None:
        doc_filename = main_module.__file__

    coder = _ArgDocCoder()
    parser_source = coder.compile_parser_source_from(doc, doc_filename=doc_filename)
    parser = coder.exec_parser_source(parser_source)

    return parser


#
# Run from the command line
#


class ArgDocError(Exception):
    pass


def main(argv):
    """Run from the command line"""

    shline = shlex_join(argv)
    app = _ArgDocApp()

    try:
        app.run_main_argv(argv)
    except ArgDocError as exc:
        shline = shlex_join(argv)
        stderr_print("error: argdoc.py: ArgDocError: {}".format(exc))
        sys.exit(1)
    except Exception:
        stderr_print("error: argdoc.py: unhandled exception at:  {}".format(shline))
        raise


class _ArgDocApp:
    """Bundle some command-line services"""

    def run_main_argv(self, argv):
        """Run from the command line, but trust the caller to interpret exceptions"""

        args = self.parse_main_argv(argv)

        main.args = args

        self.run_parsed_main_args(
            doc_filename=args.file,
            shred=args.shred,
            argv_separator=args.argv_separator,
            doc_args=args.args,
        )

    def parse_main_argv(self, argv):
        """Call the ArgParse "parse_args" but finish what it started"""

        # Begin by calling the ArgParse "parse_args"

        args = parse_args(argv[1:])

        if argv[1:] and (argv[1] == "--"):
            if args.file:
                assert args.file == argv[2]

                parseable_argv = list(argv)
                parseable_argv[1:1] = [os.devnull]
                args = parse_args(parseable_argv[1:])

                assert args.file == os.devnull

        # Notice if a list of zero or more ARG's follows the FILE in the command line

        args.argv_separator = "--" if ("--" in argv[1:]) else None

        # Complete the FILE

        args.file = args.file if args.file else os.devnull

        # Complete the SHRED in --rip SHRED

        shred = None
        if args.rip:

            shreds = "argdoc argparse doc".split()
            for shred in shreds:  # FIXME: invent how to say this in Arg Doc
                if shred.startswith(args.rip):
                    shred = shred
                    break

            if not shred:
                stderr_print(
                    "error: argdoc.py: choose --rip from {}, do not choose {!r}".format(
                        shreds, args.rip
                    )
                )
                sys.exit(1)

        args.shred = shred

        # Fail fast if extra args appear before or in place of the "--" args argv_separator
        # Speak of "unrecognized args", almost equal to conventional "unrecognized arguments"

        if args.args:
            if (not args.argv_separator) or (shred and (shred != "argdoc")):
                stderr_print(
                    "error: argdoc.py: unrecognized args: {}".format(
                        shlex_join(args.args)
                    )
                )
                sys.exit(1)

        return args

    def run_parsed_main_args(self, doc_filename, shred, argv_separator, doc_args):
        """Print the Arg Doc, or compile it, or run it"""

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

        if shred == "argparse":
            self.rip_argparse(parser_source)

            return

        # Run the parser source to build the parser, with an option to rip and quit

        parser = coder.exec_parser_source(parser_source)
        help_doc = parser.format_help()
        if file_doc.strip():
            self.compare_file_to_help_doc(
                file_doc, doc_filename=doc_filename, help_doc=help_doc
            )

        if (shred == "argdoc") or not argv_separator:
            self.rip_argdoc(help_doc)

            return

        # Run the parser, and rip the args that result (unless it prints help and exits zero)

        print(
            "+ {}".format(shlex_join([doc_filename] + doc_args))
        )  # trace like Bash PS4

        args = parser.parse_args(doc_args)

        if not parser.add_help:
            if vars(args).get("help"):
                parser.print_help()
                sys.exit(0)

        self.rip_args(args)

    def rip_doc(self, file_doc):
        """Show just the docstring"""

        print(black_triple_quote_repr(file_doc.strip()))

    def rip_argparse(self, parser_source):
        """Show how the file calls Arg Parse"""

        print(parser_source.rstrip())

        print()
        print("args = parser.parse_args()")

    def compare_file_to_help_doc(self, file_doc, doc_filename, help_doc):
        """Show the Help Doc printed by an Arg Doc file calling Arg Parse"""

        if file_doc.strip() == help_doc.strip():
            return

        if False:  # FIXME: configure logging
            with open("a", "w") as outgoing:
                outgoing.write(file_doc.strip())
            with open("b", "w") as outgoing:
                outgoing.write(help_doc.strip())

        help_shline = "bin/argdoc.py --doc {}".format(doc_filename)
        help_message = "warning: argdoc.py: doc != help, help at:  {}".format(
            help_shline
        )
        stderr_print(help_message)

        file_doc_shline = "vim {}".format(doc_filename)
        file_doc_message = "warning: argdoc.py: doc != help, doc at:  {}".format(
            file_doc_shline
        )
        stderr_print(file_doc_message)

    def rip_argdoc(self, help_doc):
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

        print(
            textwrap.dedent(
                """
                import argdoc


                def main():
                    args = argdoc.parse_args()
                    main.args = args
                    print(args)


                if __name__ == '__main__':
                    main()
                """
            ).strip()
        )

    def rip_args(self, args):
        """Show the results of parsing the args with the Arg Doc"""

        for (k, v,) in sorted(vars(args).items()):
            if not k.startswith("_"):
                print("{k}={v!r}".format(k=k, v=v))


class _ArgDocCoder(argparse.Namespace):  # FIXME: test how black'ened this style is
    """Work up an ArgumentParser to match its Arg Doc"""

    def compile_parser_source_from(self, doc, doc_filename):
        """Compile an Arg Doc into Parse Source"""

        # Parse the Arg Doc

        parts = _ArgDocSyntax()
        taker = _ArgDocTaker(parts, doc=doc)
        taker.take_arg_doc_into(parts=parts)

        self.parts = parts

        # Compile the arguments, and construct a one line summary of usage

        args_py_lines = self.emit_arguments()
        args_emitted_usage = self.emitted_usage

        # Import dependencies and open a call to the Parser constructor

        d = r"    "  # choose indentation

        lines = list()

        lines.append("import argparse")
        lines.append("import textwrap")
        lines.append("")

        comment = "  # copied from {!r} by {!r}".format(doc_filename, __file__)
        lines.append("parser = argparse.ArgumentParser({}".format(comment))

        # Name the app

        prog = parts.prog
        if not prog:
            prog = os.path.split(doc_filename)[-1]

        assert prog  # ArgParse guesses the calling prog name, if none chosen
        lines.append(d + "prog={repr_prog},".format(repr_prog=black_repr(prog)))

        # Improve on the conventional Usage Line, when desperate

        parts_usage = prog if (self.parts.usage is None) else self.parts.usage
        emitted_usage = prog if (args_emitted_usage is None) else args_emitted_usage

        if parts_usage != emitted_usage:
            stderr_print("warning: argdoc.py: doc'ced usage: {}".format(parts_usage))
            stderr_print("warning: argdoc.py: emitted usage: {}".format(emitted_usage))

        if emitted_usage:
            if "..." in emitted_usage:
                lines.append(
                    d + "usage={usage},".format(usage=black_repr(emitted_usage))
                )

        # Explain the App up front in one line, if possible

        description_line = parts.description_line
        if not doc:
            assert not parts.usage
            assert not parts.description_line
            description_line = "do good stuff"

        if parts.usage and not parts.description_line:
            stderr_print(
                "warning: argdoc.py: no one line description explains prog {!r}".format(
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

        lines.append(d + "add_help={add_help},".format(add_help=add_help))

        # Don't invite bots to incompetently resplit text

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

        metavar = positionals_declaration.line.metavar

        nargs = positionals_declaration.phrase.nargs
        usage_phrase = positionals_declaration.phrase.format_usage_phrase()

        arg_help_line = positionals_declaration.line.arg_help_line

        # Name the attribute for this positional option in the namespace built by "parse_args"
        # Go with the metavar, else guess the English plural of the metavar

        dest = metavar.lower()
        if nargs == "...":  # "..." argparse.REMAINDER
            dest = plural_en(metavar.lower())

        # Emit usage phrase

        self.args_py_phrases.append(usage_phrase)

        # Emit Python source

        repr_dest = black_repr(dest)
        repr_metavar = black_repr(metavar)
        repr_nargs = black_repr(nargs)
        repr_help = black_repr(arg_help_line)

        head_lines = [
            "parser.add_argument(",
        ]

        if nargs == 1:

            if dest == metavar:
                mid_lines = [
                    f"    {repr_dest},",
                ]
            else:
                mid_lines = [
                    f"    {repr_dest}, metavar={repr_metavar},",
                ]

        else:
            assert nargs != 1

            if dest == metavar:
                mid_lines = [
                    f"    {repr_dest}, nargs={repr_nargs},",
                ]
            else:
                mid_lines = [
                    f"   {repr_dest}, metavar={repr_metavar}, nargs={repr_nargs},",
                ]

        tail_lines = [
            f"    help={repr_help}" ")",
        ]

        lines = head_lines + mid_lines + tail_lines

        return lines

    def emit_optional(self, optionals_declaration):
        """Compile an Arg Doc Optional argument line into Python source lines"""

        parts = self.parts

        # Pick out source fragments

        option = optionals_declaration.line.option
        metavar = optionals_declaration.line.metavar
        alt_option = optionals_declaration.line.alt_option
        alt_metavar = optionals_declaration.line.alt_metavar

        nargs = optionals_declaration.phrase.nargs
        usage_phrase = optionals_declaration.phrase.format_usage_phrase()

        arg_help_line = optionals_declaration.line.arg_help_line

        assert option
        assert (not metavar) or (nargs == 1)
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
            assert parts.add_help is None
            parts.add_help = False
            addable_help = "show this help message and exit"
            if (
                (concise == "-h")
                and (mnemonic == "--help")
                and (arg_help_line == addable_help)
            ):
                parts.add_help = True
                no_lines = list()

                return no_lines

        # Emit Python source

        repr_option = black_repr(option)
        repr_alt = black_repr(alt_option)
        repr_var = black_repr(metavar)
        repr_dest = black_repr(dest)

        head_lines = [
            "parser.add_argument(",
        ]

        if not nargs:

            action = "count"
            repr_action = black_repr(action)

            if not alt_option:
                assert dest == option.lower()
                mid_lines = [f"    {repr_option}, action={repr_action},"]
            else:
                assert dest == mnemonic.lower()
                mid_lines = [f"    {repr_option}, {repr_alt}, action={repr_action},"]

        else:  # FIXME: "argparse" "add_argument" expresses our nargs=1 as "action=None"?
            assert nargs == 1

            if not alt_option:
                if dest == option.lower():
                    mid_lines = [f"    {repr_option}, metavar={repr_var},"]
                else:
                    mid_lines = [
                        f"    {repr_option}, metavar={repr_var}, dest={repr_dest},"
                    ]
            else:
                assert dest == mnemonic.lower()
                mid_lines = [f"    {repr_option}, {repr_alt}, metavar={repr_var},"]

        tail_lines = [
            "    help={repr_help}".format(repr_help=black_repr(arg_help_line)),
            ")",
        ]

        lines = head_lines + mid_lines + tail_lines

        return lines

    def exec_parser_source(self, parser_source):
        """Run the parser source to build the Parser"""

        global_vars = {}
        try:
            exec(parser_source, global_vars)
        except Exception:
            print(parser_source)
            raise

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

        self.taker = ShardsTaker()
        self.taker.give_sourcelines(doc_chars)

    def take_arg_doc_into(self, parts):
        """Parse an Arg Doc into its Parts"""

        self.parts = parts
        self.take_arg_doc()

    def take_arg_doc(self):
        """Take each source line of an Arg Doc"""

        taker = self.taker

        if taker.peek_more():

            self.take_usage_line()
            self.accept_description()

            self.accept_positionals_declarations()  # Positionals before Optionals in Arg Doc lines
            self.accept_optionals_declarations()

            self.accept_doc_remains()

        self.take_end_doc()

    def take_usage_line(self):
        """Take the line of Usage to get started"""

        taker = self.taker

        usage_line = taker.peek_one_shard()

        uses = _UsagePhrasesSyntax()
        uses_taker = _UsagePhrasesTaker(usage_line)
        uses_taker.take_usage_line_into(uses)

        self.parts.uses = uses
        self.parts.usage = uses.usage_tail
        self.parts.prog = uses.prog_phrase

        taker.take_one_shard()

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
            line_mark="",
            phrases=self.parts.uses.positionals_phrases,
        )

    def accept_optionals_declarations(self):
        """Take the Optional arguments"""

        self.parts.optionals_declarations = self.accept_tabulated_arguments(
            "optional arguments:",
            line_mark="-",
            phrases=self.parts.uses.optionals_phrases,
        )

    def accept_tabulated_arguments(self, tagline, line_mark, phrases):
        """Take the Positional or Optional arguments led by a tagline followed by dented lines"""

        arg_declarations = None

        taker = self.taker
        taker.accept_blank_shards()

        if taker.peek_more():
            line = taker.peek_one_shard()

            if line == tagline:
                taker.take_one_shard()
                taker.accept_blank_shards()

                argument_lines = self.accept_argument_lines(tagline=tagline)
                # FIXME: more test of empty tables of Positionals or Optionals

                arg_declarations = self.reconcile_lines_phrases(
                    argument_lines,
                    tagline=tagline,
                    line_mark=line_mark,
                    phrases=phrases,
                )

        return arg_declarations

    def reconcile_lines_phrases(self, argument_lines, tagline, line_mark, phrases):

        # Calculate words comparable between Usage Phrases and Argument Declaration Lines
        # FIXME: detect multiple phrase declarations earlier

        phrases_by_words = dict()
        for phrase in phrases:
            words = phrase._tuple_comparable_words()

            if words in phrases_by_words.keys():
                raise ArgDocError("multiple phrase declarations of {}".format(words))

            phrases_by_words[words] = phrase

        # Require Positionals declared with Positionals
        # strictly separate from Optionals declared with Optionals

        for argument_line in argument_lines:
            stripped = argument_line.strip()

            doc_line_mark = "-" if stripped.startswith("-") else ""
            if doc_line_mark != line_mark:

                raise ArgDocError(
                    "{!r} != {!r} inside {!r} at:  {}".format(
                        doc_line_mark, line_mark, tagline, argument_line
                    )
                )

        # Calculate words comparable between Argument Declaration Lines and Usage Phrase

        lines_by_words = dict()
        for argument_line in argument_lines:
            line = ArgumentLineSyntaxTaker(argument_line)
            words = line._tuple_comparable_words()

            if words in lines_by_words.keys():
                raise ArgDocError("multiple line declarations of {}".format(words))

            lines_by_words[words] = line

        # Require comparable declarations in the Usage Line and in the Argument Lines

        via_phrases = list(phrases_by_words.keys())
        via_lines = list(lines_by_words.keys())
        if via_phrases != via_lines:
            stderr_print("warning: argdoc.py: via_phrases:  {}".format(via_phrases))
            stderr_print("warning: argdoc.py: via_lines:  {}".format(via_lines))
            raise ArgDocError(
                "different lists of words declared as usage and as arguments"
            )

        # Group together the Usage Line for NArg with the Argument Line for Alt Option and Help

        args_by_words = via_phrases

        arg_declarations = list()
        for words in args_by_words:
            phrase = phrases_by_words[words]
            line = lines_by_words[words]

            assert phrase.concise in (line.option, line.alt_option, None,)
            assert phrase.mnemonic in (line.option, line.alt_option, None,)
            assert line.metavar == phrase.metavar
            assert (not line.alt_metavar) or (line.alt_metavar == phrase.metavar)

            if not line_mark:  # positional argument
                assert phrase.nargs
                assert phrase.metavar and line.metavar
            else:  # optional argument
                assert phrase.concise or phrase.mnemonic
                assert line.option or line.alt_option

            arg_declaration = argparse.Namespace(phrase=phrase, line=line)
            arg_declarations.append(arg_declaration)

        return arg_declarations

    def accept_argument_lines(self, tagline):
        """Take zero or more dented lines as defining Positional or Optional arguments"""

        taker = self.taker
        taker.accept_blank_shards()

        argument_lines = list()
        while taker.peek_more():
            line = taker.peek_one_shard()
            if not line.startswith(" "):
                break
            assert line.startswith("  ")

            argument_lines.append(line)
            taker.take_one_shard()

            taker.accept_blank_shards()

        return argument_lines

    def accept_doc_remains(self):
        """Take zero or more trailing lines, as if they must be the Epilog"""

        taker = self.taker

        lines = list()
        while taker.peek_more():
            line = taker.peek_one_shard()  # may be blank

            # FIXME: rethink these practical defenses

            if self.parts.optionals_declarations:
                if "positional arguments:" in line:
                    reason = "Optionals before Positionals in Arg Doc"
                    raise ArgDocError("error: argdoc.py: {}".format(reason))

            if (not self.parts.positionals_declarations) and (
                not self.parts.optionals_declarations
            ):
                if ("positional arg" in line) or ("optional arg" in line):
                    reason = "Arg Doc came too late with Arg Line Declaration @ {!r}".format(
                        line
                    )
                    raise ArgDocError("error: argdoc.py: {}".format(reason))

            lines.append(line)
            taker.take_one_shard()

        self.parts.epilog_chars = "\n".join(lines)

    def take_end_doc(self):
        """Do nothing if all lines consumed, else crash"""

        taker = self.taker
        taker.take_end_shard()


class _UsagePhrasesSyntax(argparse.Namespace):
    """Name the uses spelled out by an Arg Doc Usage line"""

    def __init__(self):

        self.usage_line = None  # the whole Usage line
        self.usage_tail = None  # the line without its "usage:" leading chars
        self.prog_phrase = None  # the 2nd word of the Usage line

        self.optionals_phrases = None  # the [-h] or [--help] or [-w WIDTH] and such
        self.positionals_phrases = None  # the FILE or [FILE] or [FILE [FILE ...]] or [-- [ARG [ARG ...]] and such


class _UsagePhrasesTaker(argparse.Namespace):
    """Pick an Arg Doc Usage Line apart, char by char"""

    def __init__(self, usage_line):

        self.uses = None  # the fragments of source matched by this parser
        self.taker = ShardsTaker(shards=usage_line)

    def take_usage_line_into(self, uses):
        """Parse an Arg Doc Usage Line into its Uses"""

        self.uses = uses
        self.take_usage_line()

    def take_usage_line(self):
        """Take each Use of an Arg Doc Usage Line"""

        taker = self.taker

        if taker.peek_more():

            self.accept_peeked_usage_line()

            self.take_usage_word()
            self.take_prog()

            self.accept_optionals_phrases()
            self.accept_positionals_phrases()

            self.accept_usage_remains()

        taker.take_end_shard()

    def accept_peeked_usage_line(self):
        """Name a copy of the entire Usage Line, including its "usage:" prefix"""

        taker = self.taker
        uses = self.uses

        strung_remains = taker.peek_strung_remains()

        usage_line = strung_remains.strip()
        uses.usage_line = usage_line

    def take_usage_word(self):
        """Take the chars of "usage:" to get started"""

        taker = self.taker
        uses = self.uses

        hopes = "usage:"
        many = taker.peek_some_shards(hopes)
        if many != hopes:

            word = taker.peek_one_strung_word()
            reason = "{!r} is here, but the first word of an Arg Doc is{!r}".format(
                word, hopes
            )

            raise ArgDocError(reason)

        taker.take_counted_shards(len(hopes))
        taker.accept_blank_shards()

        usage_tail = taker.peek_strung_remains()
        uses.usage_tail = usage_tail

    def take_prog(self):
        """Take the second word of "usage: {verb}" as the name of the app"""

        taker = self.taker
        uses = self.uses

        taker.accept_blank_shards()

        if not taker.peek_more():
            reason = "second word of Arg Doc must exist, to name the app"

            raise ArgDocError(reason)

        prog_phrase = taker.peek_one_strung_word()
        taker.take_counted_shards(len(prog_phrase))
        taker.accept_blank_shards()

        uses.prog_phrase = prog_phrase

    def accept_optionals_phrases(self):
        """Accept zero or more of [-h] or [--help] or [-w WIDTH] and such"""

        taker = self.taker
        uses = self.uses

        uses.optionals_phrases = list()
        while taker.peek_some_shards("[-") == "[-":
            argument_phrase = self.accept_argument_phrase()

            kwarg_phrase = OptionalPhraseSyntaxTaker(argument_phrase)
            uses.optionals_phrases.append(kwarg_phrase)

    def accept_positionals_phrases(self):
        """Accept zero or more of FILE or [FILE] or [FILE [FILE ...]] and such"""

        taker = self.taker
        uses = self.uses

        uses.positionals_phrases = list()
        while taker.peek_more():
            argument_phrase = self.accept_argument_phrase()

            arg_phrase = PositionalPhraseSyntaxTaker(argument_phrase)
            uses.positionals_phrases.append(arg_phrase)

    def accept_argument_phrase(self):
        """Take one word, or more, but require the [...] brackets to balance"""

        taker = self.taker

        words = list()

        argument_phrase = ""
        openings = 0
        closings = 0

        while taker.peek_more():

            word = taker.peek_one_strung_word()
            assert word

            taker.take_counted_shards(len(word))
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

        remains = taker.peek_strung_remains()
        taker.take_counted_shards(len(remains))


class ArgumentLineSyntaxTaker(argparse.Namespace):
    """Parse one line of Arg Doc argument declaration"""

    def __init__(self, argument_line):

        self.option = None
        self.metavar = None
        self.alt_option = None
        self.alt_metavar = None
        self.arg_help_line = None

        self._take_argument_line(argument_line)

        troubles = list()
        troubles.append(not self.option and not self.metavar)
        troubles.append(
            self.metavar and self.alt_metavar and (self.metavar != self.alt_metavar)
        )
        troubles.append(self._format_argument_line().split() != argument_line.split())

        stripped = argument_line.strip()
        if any(troubles):
            raise ArgDocError(
                "want: {{[-c|--mnemonic] [METAVAR], ...}} got:  {}".format(stripped)
            )

    def _take_argument_line(self, argument_line):
        """Pick attributes out of the argument line"""

        # Split off the help words

        stripped = argument_line.strip()
        index = stripped.find("  ")
        if index >= 0:
            self.arg_help_line = stripped[index:].lstrip()
            stripped = stripped[:index].rstrip()

        # Reject too many words showing up before the help words

        words = stripped.split()

        len_words = len(words)
        if len_words not in (1, 2, 4,):
            return

        # Take the 1 word of -c, --mnemonic, or METAVAR

        (word0, metavar0, concise0, mnemonic0,) = self._take_argument_word(words)

        if word0.startswith("--"):
            self.option = mnemonic0
        elif word0.startswith("-"):
            self.option = concise0
        else:
            self.metavar = metavar0

        # Take the 2 words of -c METAVAR, or --mnemonic METAVAR, or -c, --mnemonic
        # Or even take the 2 words of --mnemonic, -c out of order like that

        if words:

            (word1, metavar1, concise1, mnemonic1,) = self._take_argument_word(words)

            if word1.startswith("--"):
                self.alt_option = mnemonic1
            elif word1.startswith("-"):
                self.alt_option = concise1
            else:
                self.metavar = metavar1

            # Take the 4 words of -c METAVAR, --mnemonic METAVAR
            # Or even take the 4 words of --mnemonic METAVAR, -c METAVAR out of order like that

            if words:

                (word2, metavar2, concise2, mnemonic2,) = self._take_argument_word(
                    words
                )
                (word3, metavar3, concise3, mnemonic3,) = self._take_argument_word(
                    words
                )

                self.alt_option = mnemonic2
                self.metavar = metavar3

    def _take_argument_word(self, words):
        """Take the next word and return its potential -c, --mnemonic, METAVAR parses"""

        word = words[0]
        words[:] = words[1:]

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

    def _format_argument_line(self):
        """Format as a line of optional or positional argument declaration in an Arg Doc"""

        words = self._tuple_argument_words()
        shards = (
            (list(words) + ["", self.arg_help_line]) if self.arg_help_line else words
        )
        strung = " ".join(str(_) for _ in shards)  # tolerate None's

        return strung

    def _tuple_argument_words(self):
        """Format as a tuple of words to begin an argument declaration line in an Arg Doc"""

        if not self.option and not self.alt_option:

            words = (self.metavar,)

        elif self.option and self.alt_option:

            if not self.metavar:
                words = (
                    (self.option + ","),
                    self.alt_option,
                )
            else:
                words = (
                    self.option,
                    (self.metavar + ","),
                    self.alt_option,
                    self.alt_metavar,
                )

        else:
            assert self.option and not self.alt_option

            if not self.metavar:
                words = (self.option,)
            else:
                words = (
                    self.option,
                    self.metavar,
                )

        return words

    def _tuple_comparable_words(self):
        """Format as a tuple of words to compare with an argument declaration line in an Arg Doc"""

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

        self._take_optional_phrase(argument_phrase)

    def _take_optional_phrase(self, argument_phrase):

        # Pick out the ArgParse "concise", "mnemonic", and/or "metavar

        shards = argument_phrase.replace("[", " ").replace("]", " ").split()
        dashdash = "--" in shards

        words = list(_ for _ in shards if _ not in "-- ...".split())
        if not words:
            raise ArgDocError("no metavars in optional {}".format(argument_phrase))

        if len(words) > 2:
            raise ArgDocError(
                "too many concise or mnemonic in optional usage {}".format(
                    argument_phrase
                )
            )

        concise = words[0] if not words[0].startswith("--") else None
        mnemonic = words[0] if words[0].startswith("--") else None
        metavar = words[1] if words[1:] else None
        nargs = 1 if metavar else None

        # Publish results

        self.concise = concise
        self.mnemonic = mnemonic
        self.dashdash = dashdash
        self.metavar = metavar
        self.nargs = nargs

        # Require emitted usage equals usage source

        emitted_usage = self.format_usage_phrase()
        if argument_phrase != emitted_usage:
            stderr_print(
                "error: argdoc: optional argument_phrase:  {}".format(argument_phrase)
            )
            stderr_print(
                "error: argdoc: optional emitted_usage:  {}".format(emitted_usage)
            )
            raise ArgDocError(
                "meaningless optional usage phrase {}".format(argument_phrase)
            )

    def format_usage_phrase(self):
        """Format as a phrase of a Usage Line in an Arg Doc"""

        strung = "[{}]".format(" ".join(self._tuple_comparable_words()))

        return strung

    def _tuple_comparable_words(self):
        """Format as a tuple of words to compare with an argument declaration line in an Arg Doc"""

        if not self.nargs:
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
            raise ArgDocError("no metavars in positional {}".format(argument_phrase))

        if list(set(words)) != [words[0]]:
            raise ArgDocError(
                "too many metavars in positional {}".format(argument_phrase)
            )

        metavar = words[0]

        # Pick out the one ArgParse "nargs"
        # FIXME: sometimes prefer nargs="*" argparse.ZERO_OR_MORE, or nargs > 1

        nargs = 1
        if "..." in argument_phrase:
            nargs = "..."  # "..." argparse.REMAINDER
        elif "[" in argument_phrase:
            nargs = "?"  # # "?" argparse.OPTIONAL

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
                "error: argdoc: positional argument_phrase:  {}".format(argument_phrase)
            )
            stderr_print(
                "error: argdoc: positional emitted_usage:  {}".format(emitted_usage)
            )
            raise ArgDocError(
                "meaningless positional usage phrase {}".format(argument_phrase)
            )

    def format_usage_phrase(self):
        """Format as a phrase of a Usage Line in an Arg Doc"""

        if self.nargs == "...":
            strung = "[{} [{} ...]]".format(self.metavar, self.metavar)
            if self.dashdash:
                strung = "[-- [{} [{} ...]]]".format(self.metavar, self.metavar)
        elif self.nargs == "?":
            strung = "[{}]".format(self.metavar)
        else:
            strung = "{}".format(self.metavar)

        return strung

    def _tuple_comparable_words(self):
        """Format as a tuple of words to compare with an argument declaration line in an Arg Doc"""

        words = (self.metavar,)

        return words


class ShardsTaker(argparse.Namespace):
    """Walk once thru source chars, as split

    Define "take" to mean require and consume
    Define "peek" to mean look ahead
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_sourcelines(self, chars):
        """Give chars, split into lines, but drop the trailing whitespace from each line"""

        lines = chars.splitlines()
        lines = list(_.rstrip() for _ in lines)

        self.give_shards(shards=lines)

    def give_shards(self, shards):
        """Give shards"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Consume the next shard, without returning it"""

        self.shards = self.shards[1:]

    def peek_one_shard(self):
        """Return the next shard, without consuming it"""

        return self.shards[0]

    def peek_more(self):
        """Return True while shards remain"""

        more = bool(self.shards)
        return more

    def take_end_shard(self):
        """Do nothing if all shards consumed, else crash"""

        assert not self.peek_more()

    def accept_blank_shards(self):
        """Discard zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():
                break
            self.take_one_shard()

    def peek_strung_remains(self):
        """Return the remaining shards strung together """

        strung_remains = "".join(self.shards)
        return strung_remains

    def peek_one_strung_word(self):
        """Return the first word of the remaining shards strung together"""

        strung_remains = "".join(self.shards)

        words = strung_remains.split()
        if not words:
            raise ArgDocError("precondition violated: no words available")

        word = words[0]

        return word

    def peek_some_shards(self, hopes):
        """Return a copy of the hopes strung together, if and only if available to be taken now"""

        shards = self.shards

        if len(shards) < len(hopes):
            return None

        for (shard, hope,) in zip(shards, hopes):
            if shard != hope:
                return None

        strung = "".join(hopes)
        return strung

    def take_counted_shards(self, count):
        """Take a number of shards"""

        if count:
            self.shards = self.shards[count:]


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

    source = "\n".join(lines)

    return source


def black_repr(chars):
    """Quote chars or None like Black, preferring " double quotes over ' single quotes"""
    # FIXME: does this agree with the Black autostyling app? Agrees always?

    source = repr(chars)

    if chars == str(chars):  # not None, and not int, etc
        if '"' not in chars:
            source = '"{}"'.format(chars)

    return source


def plural_en(word):  # FIXME FIXME: make this easy to override
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


def prompt_tty_stdin():  # deffed in many files
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


def read_docstring_from(relpath):
    """
    Read the docstring from a python file without importing the rest of it

    Specifically read the first lines from triple-quote to triple-quote \"\"\" or ''',
    but ignore leading lines begun with a hash #
    """

    try:
        with open(relpath, "rt") as reading:
            return _read_docstring_from_stream(reading)
    except IOError as exc:  # such as Python 3 FileNotFoundError
        stderr_print("error: argdoc.py: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)


def _read_docstring_from_stream(reading):
    # FIXME: see the quoted text as r""" only when explicitly marked as "r"
    # FIXME: correctly forward the leading and trailing whitespace

    texts = list()
    qqq = None
    lines = 0

    for line in reading.readlines():
        lines += 1

        text = line.rstrip()

        if texts or text:
            if not text.startswith("#"):
                if not qqq:
                    if '"""' in text:
                        qqq = '"""'
                    elif "'''" in text:
                        qqq = "'''"
                    else:
                        pass
                elif qqq in text:
                    break
                else:
                    texts.append(text)

    if lines and (qqq is None):
        qqq1 = '"""'
        qqq2 = "'''"
        stderr_print(
            "warning: argdoc.py: no {} found and no {} found in {}".format(
                qqq1, qqq2, reading.name
            )
        )

    repr_doc = black_triple_quote_repr("\n".join(texts))
    doc_source = "doc = " + repr_doc

    global_vars = {}
    exec(doc_source, global_vars)

    doc = global_vars["doc"]
    return doc


def require_sys_version_info(*min_info):  # deffed in many files
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


def shlex_join(argv):  # FIXME: substitute "shlex.join" since Oct/2019 Python 3.8
    """Undo the "shlex.split", well enough for now"""

    flattened = " ".join(argv)

    if "'" not in flattened:

        joined = ""
        for arg in argv:
            assert "\\" not in arg
            assert "'" not in arg
            joined += " "
            joined += "'{}'".format(arg) if (" " in arg) else arg

        return joined[len(" ") :]

    if '"' not in flattened:

        joined = ""
        for arg in argv:
            assert "\\" not in arg
            assert "$" not in arg
            assert "`" not in arg
            assert '"' not in arg
            joined += " "
            joined += '"{}"'.format(arg) if (" " in arg) else arg

        return joined[len(" ") :]

    return flattened  # both wrong, and good enough for now


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


def str_splitword(chars, count=1):  # deffed in many files
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
