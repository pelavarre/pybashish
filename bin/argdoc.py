#!/usr/bin/env python3

'''
usage: argdoc.py [-h] [--compile] [FILE] [-- [ARG [ARG ...]]]

parse command line args precisely as helped by module help doc

positional arguments:
  FILE        where the arg doc is (default: os.devnull)
  ARG         an arg to parse as per the arg doc

optional arguments:
  -h, --help  show this help message and exit
  --compile   still translate the file to python, but show it, don't run it

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
  an arg doc with no optional arguments passively gets no "-h, --help" optional argument

examples:
  argdoc.py -h                      # show this help message
  argdoc.py                         # show a template arg doc (including import) to start with
  argdoc.py --compile argdoc.py     # still translate the file to python, but show it, don't run it
  argdoc.py argdoc.py               # show a file's help doc (as printed by its arg doc)
  argdoc.py argdoc.py --            # parse no arg with the file's arg doc
  argdoc.py argdoc.py -- --help     # parse the arg "--help" with the file's arg doc
  argdoc.py argdoc.py -- hi world   # parse two args with the file's arg doc
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


class ArgDocParseError(Exception):
    pass


def main(argv):
    try:
        main_(argv)
    except SystemExit:
        raise
    except Exception:
        shline = shlex_join(argv)
        stderr_print("error: argdoc.py: unhandled exception at:  {}".format(shline))
        raise


def main_(argv):
    """Run from the command line"""

    args_separator = "--" if ("--" in argv[1:]) else None

    argv_ = list(argv)
    if argv[1:] and (argv[1] == "--"):
        argv_[1:1] = [os.devnull]

    args = parse_args(argv_[1:])

    _run_args_file(
        args.file,
        args_separator=args_separator,
        args_args=args.args,
        args_compile=args.compile,
    )


def _run_args_file(args_file, args_separator, args_args, args_compile):
    """Print the Arg Doc, or compile it, or run it"""

    str_args_file = args_file if args_file else repr("")
    doc_filename = args_file if args_file else os.devnull

    # Fail fast if extra args supplied before or in place of the "--" args separator

    if not args_separator:
        if (
            args_args
        ):  # fail for "args", barely distinguishable from conventional "arguments"
            stderr_print(
                "error: argdoc.py: unrecognized args: {}".format(shlex_join(args_args))
            )
            sys.exit(1)

    # Fetch the Arg Doc, compile it, and hope it doesn't crash the compiler

    filename = doc_filename
    if doc_filename == "-":
        filename = "/dev/stdin"
        prompt_tty_stdin()

    file_doc = read_docstring_from(filename).strip()

    (source, parser,) = _run_arg_doc(file_doc, doc_filename=doc_filename)
    help_doc = parser.format_help()

    # Print the Arg Parser compiled from the Arg Doc, but don't run it

    if args_compile:
        _print_arg_parser_source(file_doc, source=source)
        return

    # Print the compiled Arg Doc, if there was no original Arg Doc
    # Fill it out to become a whole Python source file

    if not args_separator:

        if not file_doc:
            _print_py_file(help_doc)
            return

        # Print the compiled Arg Doc, and compare it with the original Arg Doc

        _print_help_doc(doc_filename=doc_filename, help_doc=help_doc, file_doc=file_doc)
        return

    # Run Args through the Arg Parser compiled from the Arg Doc

    _parse_and_print_args(str_args_file, parser=parser, args_args=args_args)


def _print_arg_parser_source(file_doc, source):

    print(source.rstrip())

    if not file_doc:
        print()
        print("args = parser.parse_args()")


def _print_py_file(help_doc):
    """Show a Py file containing the file's help doc (as printed by its arg doc)"""

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
                print(args)


            if __name__ == '__main__':
                main()
            """
        ).strip()
    )


def _print_help_doc(doc_filename, help_doc, file_doc):
    """Show a file's help doc, as compiled from its arg doc, and diff'ed with its arg doc"""

    print(black_triple_quote_repr(help_doc.strip()))

    if file_doc.strip() != help_doc.strip():

        if file_doc.strip():

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


def _parse_and_print_args(str_args_file, parser, args_args):
    """Run Args through the Arg Parser, compiled from the Arg Doc"""

    print("+ {}".format(shlex_join([str_args_file] + args_args)))

    file_args = parser.parse_args(args_args)

    # After letting the Arg Doc explain "--help" in its own way,
    # still print the help and exit, as part of ".parse_args", when asked for help

    if not parser.add_help:
        if vars(file_args).get("help"):
            parser.print_help()
            sys.exit(0)

    # Print the parsed args, but in sorted order

    for (k, v,) in sorted(vars(file_args).items()):
        if not k.startswith("_"):
            print("{k}={v!r}".format(k=k, v=v))


def black_triple_quote_repr(
    chars,
):  # FIXME:  Fix leading trailing whitespace, other corner cases
    '''Quote the chars like Black, with triple quotes, preferring triple '"""' double quotes'''

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


def black_repr(
    chars,
):  # FIXME: does this agree with the Black autostyling app? Agrees always?
    """Quote the chars like Black, preferring an opening and closing pair of '"' double quotes"""

    source = repr(chars)
    if '"' not in chars:
        source = '"{}"'.format(chars)

    return source


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

    texts = []
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
    source = "doc = " + repr_doc

    global_vars = {}
    exec(source, global_vars)  # 1st of 2 calls on "exec"

    doc = global_vars["doc"]
    return doc


def parse_args(args=None, namespace=None, doc=None, doc_filename=None):
    """Parse args as helped by doc"""

    if args is None:
        args = sys.argv[1:]
    if namespace is None:
        namespace = argparse.Namespace()

    (source, parser,) = _run_arg_doc(doc, doc_filename=doc_filename)

    space = parser.parse_args(args, namespace=namespace)

    return space


def format_help(doc=None, doc_filename=None):  # FIXME: what about ".print_help()" etc
    """Format help as helped by doc"""

    (source, parser,) = _run_arg_doc(doc, doc_filename=doc_filename)

    help_doc = parser.format_help()

    return help_doc


def _run_arg_doc(doc, doc_filename):
    """Compile the doc into a parser"""

    if doc is None:
        main = sys.modules["__main__"]
        doc = main.__doc__

    coder = _ArgDocCoder()
    (source, parser,) = coder.run_arg_doc(doc, doc_filename=doc_filename)

    return (
        source,
        parser,
    )


class _ArgDocCoder(argparse.Namespace):  # FIXME: test how black'ened this style is
    """Work up an ArgumentParser to match its Arg Doc"""

    def __init__(self):
        self.prog = None
        self.optionals = None
        self.positionals = None
        self.remains = None

    def run_arg_doc(self, doc, doc_filename):
        """Return an ArgumentParser constructed from a run of its Arg Doc"""

        source = self.compile_arg_doc(doc, doc_filename=doc_filename)
        global_vars = {}
        exec(source, global_vars)  # 2nd of 2 calls on "exec"

        parser = global_vars["parser"]
        return (
            source,
            parser,
        )

    def compile_arg_doc(self, doc, doc_filename):
        """Compile an Arg Doc into Python source lines"""

        # Parse the Arg Doc

        parts = _ArgDocParts(doc)

        self.parts = parts

        # Compile the arguments, and construct a one line summary of usage

        args_py_lines = self.emit_arguments()
        args_emitted_usage = self.emitted_usage

        # Import dependencies and open a call to the Parser constructor

        d = r"    "  # choose indentation

        lines = []

        lines.append("import argparse")
        lines.append("import textwrap")
        lines.append("")

        lines.append("parser = argparse.ArgumentParser(")

        # Name the app

        prog = parts.prog
        if not prog:
            prog = os.path.split(doc_filename)[-1]

        assert prog  # ArgParse guesses the calling prog name, if none chosen
        lines.append(d + "prog={prog},".format(prog=black_repr(prog)))

        # Improve on the conventional usage line, when desperate

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

        description = parts.description
        if not doc:
            assert not parts.usage
            assert not parts.description
            description = "do good stuff"

        if parts.usage and not parts.description:
            stderr_print(
                "warning: argdoc.py: no one line description explains prog {!r}".format(
                    prog
                )
            )

        if description:
            lines.append(
                d
                + "description={description},".format(
                    description=black_repr(description)
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

        epilog = DEFAULT_EPILOG if (parts.epilog is None) else parts.epilog
        lines.append(d + "epilog=textwrap.dedent(")
        for line in black_triple_quote_repr(epilog).splitlines():
            lines.append(d + d + line)
        lines.append(d + "),")

        # Close the constructor

        lines.append(")")
        lines.append("")

        lines.extend(args_py_lines)

        source = "\n".join(lines)
        return source

    def emit_arguments(self):
        """Compile the Positionals and Optionals Parts of the Arg Doc"""

        parts = self.parts

        args_py_lines = []

        # Emit one call to "add_argument" for each Positional argument

        self.usage_words = []
        if parts.positionals:
            py_lines = []
            for index in range(len(parts.positionals)):
                py_lines.extend(self.emit_positional(parts, parts.positionals, index))
            py_lines.append("")
            args_py_lines.extend(py_lines)

        positional_words = self.usage_words

        # Emit one call to "add_argument" for each Optional argument
        # except emit the call for the Optional "-h, --help" argument only if "add_help=False,"

        self.usage_words = []
        if parts.optionals:
            py_lines = []
            for index in range(len(parts.optionals)):
                py_lines.extend(self.emit_optional(parts, parts.optionals, index))
            py_lines = (py_lines + [""]) if py_lines else []
            args_py_lines.extend(py_lines)

        optional_words = self.usage_words

        # Construct a one line summary of usage

        emitted_usage = None
        if parts.prog:
            emitted_usage = " ".join([parts.prog] + optional_words + positional_words)
            if emitted_usage == "fmt [-h] [--ruler]":
                emitted_usage = "fmt [-h] [-w WIDTH] [--ruler]"  # FIXME FIXME nargs

        self.emitted_usage = emitted_usage

        return args_py_lines

    def emit_positional(self, parts, positionals, index):  # FIXME FIXME  # noqa C901
        """Compile an Arg Doc Positional argument line into Python source lines"""

        positional = positionals[index]

        (metavar, help_) = str_splitword(positional.lstrip())
        help_ = help_.lstrip()

        # Calculate "nargs"
        # FIXME FIXME: nargs

        nargs = 1
        if parts.uses.remains and (index == len(positionals) - 1):
            nargs = "..."  # argparse.REMAINDER  # FIXME FIXME: nargs "*" e.g. allow FILE -v / -v FILE

        if metavar == "FILE":
            if parts.uses.remains is None:
                if not parts.usage.endswith(" FILE"):  # for "cp.py", "mv.py"
                    nargs = "?"  # for "touch.py"
            elif parts.uses.remains == "[FILE] [-- [ARG [ARG ...]]]":
                nargs = "?"  # for "argdoc.py"
            elif parts.uses.remains == "[FILE]":
                nargs = "?"  # for "touch.py"
        elif metavar == "TOP":
            nargs = "?"  # argparse.OPTIONAL  # for "find.py"
        elif metavar == "VERB":
            if parts.uses.remains == "[VERB]":
                nargs = "?"  # for "help_.py"

        # Calculate "usage:"

        if nargs == 1:
            self.usage_words.append(metavar)
        elif nargs == "?":
            self.usage_words.append("[{}]".format(metavar))
        elif nargs == "...":
            if metavar == "ARG":
                self.usage_words.append("[-- [{} [{} ...]]]".format(metavar, metavar))
            else:
                self.usage_words.append("[{} [{} ...]]".format(metavar, metavar))

        # Calculate "dest"

        dest = metavar.lower()
        if nargs == "...":
            dest = (metavar + "s").lower()

        # Emit one positional "add_argument" call

        lines = self._emit_positional_permutation(
            dest=dest, metavar=metavar, nargs=nargs, help_=help_
        )

        return lines

    def _emit_positional_permutation(self, dest, metavar, nargs, help_):
        """Emit Dest, and Metavar if needed, and NArgs if needed, and Help if available"""

        if nargs == 1:

            if dest == metavar:
                lines = [
                    "parser.add_argument(",
                    "    {dest},".format(dest=black_repr(dest)),
                    "    help={help_}".format(help_=black_repr(help_)),
                    ")",
                ]
            else:
                lines = [
                    "parser.add_argument(",
                    "    {dest}, metavar={metavar},".format(
                        dest=black_repr(dest), metavar=black_repr(metavar)
                    ),
                    "    help={help_}".format(help_=black_repr(help_)),
                    ")",
                ]

        else:

            if dest == metavar:
                lines = [
                    "parser.add_argument(",
                    "    {dest}, nargs={nargs},".format(
                        dest=black_repr(dest), nargs=black_repr(nargs)
                    ),
                    "    help={help_}".format(help_=black_repr(help_)),
                    ")",
                ]
            else:
                lines = [
                    "parser.add_argument(",
                    "   {dest}, metavar={metavar}, nargs={nargs},".format(
                        dest=black_repr(dest),
                        metavar=black_repr(metavar),
                        nargs=black_repr(nargs),
                    ),
                    "    help={help_}".format(help_=black_repr(help_)),
                    ")",
                ]

        return lines

    def emit_optional(self, parts, optionals, index):  # FIXME FIXME  # noqa C901
        """Compile an Arg doc Optional argument line into Python source lines"""

        optional = optionals[index]
        words = optional.split()

        option = words[0]
        help_ = optional[optional.index(option) :][len(option) :].lstrip()

        try:
            assert option.startswith("-") or option.startswith("--")
            assert not option.startswith("---")
        except AssertionError:
            raise ValueError("optional argument: {}".format(optional))

        # FIXME FIXME: nargs of -x XYZ

        if len(words) >= 3 and not str_splitword(optional)[-1].startswith("  "):
            (concise_word, metavar_word,) = words[:2]
            if concise_word.startswith("-") and not concise_word.startswith("--"):
                if not metavar_word.startswith("--"):
                    help_ = str_splitword(optional, 2)[-1].strip()
                    assert not help_.startswith("_")

                    concise = concise_word
                    metavar = metavar_word.upper()
                    dest = metavar.lower()

                    assert option not in ("-h", "--help",)
                    lines = [
                        "parser.add_argument(",
                        "    {concise}, dest={dest}, metavar={metavar},".format(
                            concise=black_repr(concise),
                            dest=black_repr(dest),
                            metavar=black_repr(metavar),
                        ),
                        "    help={help_}".format(help_=black_repr(help_)),
                        ")",
                    ]

                    return lines

        # FIXME FIXME: nargs of -x XYZ, --xyz XYZ

        if len(words) >= 5:
            (concise_word, metavar_word_1, mnemonic_word, metavar_word_3,) = words[:4]
            if concise_word.startswith("-") and not concise_word.startswith("--"):
                if mnemonic_word.startswith("--"):
                    if metavar_word_1 == (metavar_word_3 + ","):

                        concise = concise_word
                        mnemonic = mnemonic_word
                        help_ = str_splitword(optional, 4)[-1].strip()

                        assert metavar_word_3 == mnemonic.split("-")[2].upper()

                        assert option not in ("-h", "--help",)
                        lines = [
                            "parser.add_argument(",
                            "    {concise}, {mnemonic},".format(
                                concise=black_repr(concise),
                                mnemonic=black_repr(mnemonic),
                            ),
                            "    help={help_}".format(help_=black_repr(help_)),
                            ")",
                        ]

                        return lines

        # FIXME FIXME: nargs of -x or nargs of --xyz

        if not option.endswith(","):

            if (option == "-h") or (option == "--help"):
                assert parts.add_help is None
                parts.add_help = False

            self.usage_words.append("[{}]".format(option))

            action = "count"
            lines = [
                "parser.add_argument(",
                "    {option}, action={action},".format(
                    option=black_repr(option), action=black_repr(action)
                ),
                "    help={help_}".format(help_=black_repr(help_)),
                ")",
            ]

            return lines

        concise = words[0][: -len(",")]
        mnemonic = words[1]
        help_ = optional[optional.index(mnemonic) :][len(mnemonic) :].lstrip()

        self.usage_words.append("[{}]".format(concise))

        try:
            assert concise.startswith("-") and not concise.startswith("--")
            assert mnemonic.startswith("--") and not mnemonic.startswith("---")
        except AssertionError:
            raise ValueError("optional argument: {}".format(optional))

        # Emit no Python here to tell "argparse.parse_args" to "add_help" for us elsewhere

        if (concise == "-h") or (mnemonic == "--help"):
            assert parts.add_help is None

            parts.add_help = False

            _h_help = "show this help message and exit"
            if (concise == "-h") and (mnemonic == "--help") and (help_ == _h_help):

                parts.add_help = True

                lines = []

                return lines

        # Emit Python here to add this argument
        # such as any ordinary Optional, or an unconventional "--help" argument

        action = "count"
        lines = [
            "parser.add_argument(",
            "    {concise}, {mnemonic}, action={action},".format(
                concise=black_repr(concise),
                mnemonic=black_repr(mnemonic),
                action=black_repr(action),
            ),
            "    help={help_}".format(help_=black_repr(help_)),
            ")",
        ]

        return lines


class _ArgDocParts(argparse.Namespace):
    """Name the parts of an Arg Doc"""

    def __init__(self, doc):

        self.prog = None

        self.usage = None
        self.description = None
        self.add_help = None

        self.positionals = None
        self.optionals = None

        self.epilog = None
        self.uses = None

        taker = _ArgDocTaker(doc=doc)
        taker.take_arg_doc_into(parts=self)


class _ArgDocTaker:
    """Pick an Arg Doc apart, line by line"""

    TAGLINE_PATTERNS = (
        r"^positional arguments:$",
        r"^optional arguments:$",
        r"^usage:",
    )

    def __init__(self, doc):

        self.parts = None

        tabsize_8 = 8
        doc_chars = textwrap.dedent(doc.expandtabs(tabsize_8)).strip()

        self.taker = ShardTaker()
        self.taker.give_sourcelines(doc_chars)

    def take_arg_doc_into(self, parts):
        """Take every source line"""

        self.parts = parts

        taker = self.taker

        if taker.peek_more():
            self.take_usage()
            self.accept_description()
            self.accept_positionals()
            self.accept_optional_arguments()
            self.accept_epilog()

        self.take_end()

    def take_usage(self):
        """Take the line of Usage"""

        taker = self.taker

        line = taker.peek_shard()

        uses = _ArgUsageParts(line)

        self.parts.uses = uses
        self.parts.usage = uses.usage
        self.parts.prog = uses.prog

        taker.take_shard()

    def accept_description(self):
        """Take the line of description"""

        taker = self.taker
        taker.accept_empty_shards()

        self.parts.description = None
        if taker.peek_more():
            line = taker.peek_shard()

            if not any(re.match(p, string=line) for p in _ArgDocTaker.TAGLINE_PATTERNS):
                self.parts.description = line
                taker.take_shard()

    def accept_positionals(self):
        """Take the Positional arguments"""

        self.parts.positionals = self.accept_argblock("positional arguments:")

    def accept_optional_arguments(self):
        """Take the Optional arguments"""

        self.parts.optionals = self.accept_argblock("optional arguments:")

    def accept_argblock(self, tagline):
        """Take the Positional or Optional arguments"""

        arglines = None

        taker = self.taker
        taker.accept_empty_shards()

        if taker.peek_more():
            line = taker.peek_shard()

            if line == tagline:
                taker.take_shard()
                taker.accept_empty_shards()
                arglines = self.accept_arglines(tagline=tagline)

        return arglines

    def accept_arglines(self, tagline):
        """Take zero or more indented definitions of Positional or Optional arguments"""

        taker = self.taker
        taker.accept_empty_shards()

        arglines = []
        while taker.peek_more():
            line = taker.peek_shard()
            if not line.startswith(" "):
                break
            assert line.startswith("  ")

            arglines.append(line)
            taker.take_shard()

            taker.accept_empty_shards()

        return arglines

    def accept_epilog(self):
        """Take zero or more trailing lines"""

        taker = self.taker

        lines = []
        while taker.peek_more():
            line = taker.peek_shard()  # may be blank

            # FIXME: rethink these practical defenses

            if (not self.parts.positionals) and (not self.parts.optionals):
                if ("positional arg" in line) or ("optional arg" in line):
                    reason = "Arg Doc declares Arg @ {!r}".format(line)
                    raise ArgDocParseError("error: argdoc.py: {}".format(reason))

            if self.parts.optionals:
                if "positional arguments:" in line:
                    reason = "Optionals before Positionals in Arg Doc"
                    raise ArgDocParseError("error: argdoc.py: {}".format(reason))

            lines.append(line)
            taker.take_shard()

        self.parts.epilog = "\n".join(lines)

    def take_end(self):
        """Do nothing if all lines consumed, else crash"""

        taker = self.taker
        taker.take_end()


class _ArgUsageParts(argparse.Namespace):
    """Name the parts of an Arg Doc Usage line"""

    def __init__(self, usage):

        self.prog = None

        self.optionals = None
        self.positionals = None

        self.remains = None

        taker = _UsageLineTaker(usage=usage)
        taker.take_usage_line_into(uses=self)


class _UsageLineTaker:
    """Pick an Arg Doc Usage Line apart, char by char"""

    def __init__(self, usage):

        self.usage = usage
        self.taker = ShardTaker(shards=usage)

    def take_usage_line_into(self, uses):
        """Pick an Arg Doc Usage line apart, word by word"""

        self.uses = uses

        usage = self.usage

        uses.optionals = []
        uses.positionals = []

        chars = usage.lstrip()
        (use, chars,) = str_splitword(chars)
        if use != "usage:":
            stderr_print(
                "error: argdoc.py: first word of Arg Doc must be 'usage:' not {!r}".format(
                    use
                )
            )
            sys.exit(1)

        usage = chars.lstrip()
        uses.usage = usage

        chars = usage
        while chars:
            unsplit = chars.lstrip()
            (use, chars,) = str_splitword(unsplit)

            if not uses.prog:
                uses.prog = use
            elif not use.startswith("["):
                uses.positionals.append(use)
            elif use.startswith("[-") and use.endswith("]"):
                uses.optionals.append(use)
            else:  # FIXME: nargs=='?', nargs > 1, etc.
                uses.remains = unsplit
                chars = ""


class ShardTaker:
    """Walk once thru source chars, as split

    Define "take" to mean require and consume
    Define "peek" to mean look ahead
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, shards=()):
        self.shards = list(shards)

    def give_sourcelines(self, chars):
        """Give chars, split into lines, but drop the trailing whitespace from each line"""

        lines = chars.splitlines()
        lines = list(_.rstrip() for _ in lines)

        self.give_shards(shards=lines)

    def give_shards(self, shards):
        """Give shards"""

        self.shards.extend(shards)

    def take_shard(self):
        """Consume the next shard, without returning it"""

        self.shards = self.shards[1:]

    def peek_shard(self):
        """Return the next shard, without consuming it"""

        return self.shards[0]

    def peek_more(self):
        """Return True while shards remain"""

        more = bool(self.shards)
        return more

    def take_end(self):
        """Do nothing if all shards consumed, else crash"""

        assert not self.peek_more()

    def accept_empty_shards(self):
        """Discard zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_shard()
            if shard.strip():
                break
            self.take_shard()


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


def prompt_tty_stdin():  # deffed in many files
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


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


# call inline to define 'import argdoc' to require Python >= June/2019 Python 3.7
require_sys_version_info()


if __name__ == "__main__":
    sys.exit(main(sys.argv))


#
# See also
#
# "Parsing: a timeline" JKegler 2019, via @CompSciFact
# https://jeffreykegler.github.io/personal/timeline_v3
#


# copied from:  git clone https://github.com/pelavarre/pybashish.git
