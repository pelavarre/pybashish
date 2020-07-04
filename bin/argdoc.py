#!/usr/bin/env python3

'''
usage: argdoc.py [-h] [--doc] [FILE] [-- [ARG [ARG ...]]]

parse command line args precisely as helped by module help doc

positional arguments:
  FILE        where the arg doc is (else it is "/dev/null")
  ARG         an arg to parse as per the arg doc

optional arguments:
  -h, --help  show this help message and exit
  --doc       print and review the arg doc, but don't run it

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

examples:
  argdoc.py -h                      # show this help message
  argdoc.py --doc                   # show a template arg doc to start with
  argdoc.py argdoc.py               # translate a file's arg doc to python
  argdoc.py --doc argdoc.py         # show a file's arg doc (and test that it compiles)
  argdoc.py argdoc.py --            # parse no arg with the file's arg doc
  argdoc.py argdoc.py -- --help     # parse the arg "--help" with the file's arg doc
  argdoc.py argdoc.py -- hi world   # parse two args with the file's arg doc

notes:
  damage an arg doc and run this again, to see review comments pop up to work with you
'''
# FIXME: parsed args whose names begin with a '_' skid shouldn't print here, via argparse.SUPPRESS

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


def main(argv):
    """Run from the command line"""

    args_separator = "--" if ("--" in argv[1:]) else None

    argv_ = list(argv)
    if argv[1:] and (argv[1] == "--"):
        argv_[1:1] = [os.devnull]

    args = parse_args(argv_[1:])

    _run_args_file(
        args.file, args_separator=args_separator, args_args=args.args, args_doc=args.doc
    )


def _run_args_file(args_file, args_separator, args_args, args_doc):
    """Print the Arg Doc, or compile it, or run it"""

    str_args_file = args_file if args_file else repr("")
    arg_doc_file = args_file if args_file else os.devnull

    # Fail fast if extra args supplied before or in place of the "--" args separator

    if not args_separator:
        if (
            args_args
        ):  # fail for "args", barely distinguishable from conventional "arguments"
            reason = "unrecognized args: {}".format(shlex_join(args_args))
            stderr_print("argdoc.py: error: {}".format(reason))
            sys.exit(1)

    # Fetch the Arg Doc, compile it, and hope it doesn't crash the compiler

    file_doc = read_docstring_from(arg_doc_file)
    file_prog = os.path.split(arg_doc_file)[-1]

    (source, parser,) = _run_arg_doc(file_doc, file_prog=file_prog)
    helped_doc = parser.format_help()

    qqq = (
        "'''" if ('"""' in helped_doc) else '"""'
    )  # FIXME: get this choice correct more often

    # Print the Arg Parser that results

    if args_file and (not args_doc) and (not args_separator):

        print(source.rstrip())

        return

    # Print the compiled Arg Doc, and compare it with the original Arg Doc

    if not args_separator:

        _print_arg_doc(
            arg_doc_file=arg_doc_file, qqq=qqq, helped_doc=helped_doc, file_doc=file_doc
        )

        return

    # Run Args through the Arg Parser, compiled from the Arg Doc

    _parse_and_print_args(str_args_file, parser=parser, args_args=args_args)


def _print_arg_doc(arg_doc_file, qqq, helped_doc, file_doc):
    """Print the compiled Arg Doc, and compare it with the original Arg Doc"""

    if not file_doc:
        print(qqq)
        print(helped_doc.strip())
        print(qqq)
        return

    print(qqq)
    print(file_doc.strip())
    print(qqq)

    if file_doc.strip() != helped_doc.strip():
        if file_doc.strip():

            help_shline = "bin/argdoc.py {} -- --help".format(arg_doc_file)
            help_reason = "warning: doc != help, doc at:  {}".format(help_shline)
            stderr_print(help_reason)

            # file_doc_shline = "bin/argdoc.py --doc {}".format(arg_doc_file)
            file_doc_shline = "vim {}".format(arg_doc_file)
            file_doc_reason = "warning: doc != help, doc at:  {}".format(
                file_doc_shline
            )
            stderr_print(file_doc_reason)


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


def black_repr(chars):
    """Get back to the Python source string, from the printed chars, in the Black style

    The Black autostyling app defaults to do this work for every source string

    Quote with double-quotes if no escapes, else fallback to quoting with single-quotes,
    is close enough for now
    """

    if '"' not in chars:
        return '"{}"'.format(chars)

    return repr(chars)


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
            return _read_docstring_from(reading)
    except IOError as exc:  # such as Python 3 FileNotFoundError
        reason = "{}: {}".format(type(exc).__name__, exc)
        stderr_print("argdoc.py: error: {}".format(reason))
        sys.exit(1)


def _read_docstring_from(reading):

    texts = []
    qqq = None
    for line in reading.readlines():
        text = line.rstrip()

        if texts or text:
            if not text.startswith("#"):
                if not qqq:
                    if '"""' in text:
                        qqq = '"""'
                        texts.append(qqq)
                    elif "'''" in text:
                        qqq = "'''"
                        texts.append(qqq)
                    else:
                        pass
                else:
                    texts.append(text)
                    if qqq in text:
                        break

    repr_doc = "\n".join(texts) if texts else ('"""' + '"""')
    source = "doc = " + repr_doc

    global_vars = {}
    exec(source, global_vars)  # 1st of 2 calls on "exec"

    doc = global_vars["doc"]
    return doc


def parse_args(args=None, namespace=None, doc=None, file_prog=None):
    """Parse args as helped by doc"""

    if args is None:
        args = sys.argv[1:]

    if namespace is None:
        namespace = argparse.Namespace()

    (source, parser,) = _run_arg_doc(doc, file_prog=file_prog)

    namespace._argument_parser_source = (
        source  # FIXME: review collisions with "import argparse"
    )
    namespace._argument_parser = parser
    space = parser.parse_args(args, namespace=namespace)

    return space


def _run_arg_doc(doc, file_prog):
    """Compile the doc into a parser"""

    if doc is None:
        main = sys.modules["__main__"]
        doc = main.__doc__

    coder = _ArgDocCoder()
    (source, parser,) = coder.run_arg_doc(doc, file_prog=file_prog)

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

    def run_arg_doc(self, doc, file_prog):
        """Return an ArgumentParser constructed from a run of its Arg Doc"""

        source = self.compile_arg_doc(doc, file_prog=file_prog)
        global_vars = {}
        exec(source, global_vars)  # 2nd of 2 calls on "exec"

        parser = global_vars["parser"]
        return (
            source,
            parser,
        )

    def compile_arg_doc(self, doc, file_prog):
        """Compile an Arg Doc into Python source lines"""

        d = r"    "
        taker = _ArgDocTaker()

        parts = taker.take_arg_doc(doc)
        self.parts = parts

        args_py_lines = self.emit_arguments()

        lines = []

        lines.append("import argparse")
        lines.append("import textwrap")
        lines.append("")

        lines.append("parser = argparse.ArgumentParser(")

        prog = parts.prog if parts.prog else file_prog
        lines.append(d + "prog={prog},".format(prog=black_repr(prog)))

        if self.parts.usage != self.compiled_usage:
            stderr_print(
                "argdoc.py: warning: doc'ced ...... {}".format(self.parts.usage)
            )
            stderr_print(
                "argdoc.py: warning: calculated ... {}".format(self.compiled_usage)
            )
            # FIXME:  resolve conflicts between actual Usage and Arg Doc Usage more elegantly

        if self.compiled_usage:
            if "..." in self.compiled_usage:
                lines.append(
                    d + "usage={usage},".format(usage=black_repr(self.compiled_usage))
                )

        if parts.usage and not parts.description:
            stderr_print(
                "argdoc.py: warning: meaning of prog not disclosed by even one line of description"
            )

        if parts.description:
            lines.append(
                d
                + "description={description},".format(
                    description=black_repr(parts.description)
                )
            )

        assert parts.add_help in (False, True,)
        lines.append(d + "add_help={add_help},".format(add_help=parts.add_help))

        lines.append(
            d + "formatter_class=argparse.RawTextHelpFormatter,"
        )  # for .print_help()

        epilog = DEFAULT_EPILOG if (parts.epilog is None) else parts.epilog
        qqq = "'''" if ('"""' in epilog) else '"""'  # FIXME: breaks in corners
        lines.append(d + "epilog=textwrap.dedent(")
        lines.append(d + d + "r" + qqq)
        for line in epilog.splitlines():
            lines.append((d + d + line).rstrip())
        lines.append(d + d + qqq)
        lines.append(d + "),")

        lines.append(")")
        lines.append("")

        lines.extend(args_py_lines)

        source = "\n".join(lines)
        return source

    def emit_arguments(self):
        """Compile the Positionals and Optionals Parts of the Arg Doc"""

        parts = self.parts

        args_py_lines = []

        # Emit one call to "add_argument" for each Positional

        self.usage_words = []
        if parts.positionals:  # call "add_argument" for each Positional
            py_lines = []
            for index in range(len(parts.positionals)):
                py_lines.extend(self.emit_positional(parts, parts.positionals, index))
            py_lines.append("")
            args_py_lines.extend(py_lines)

        positional_words = self.usage_words

        # Emit one call to "add_argument" for each Optional
        # except no calls here for "add_help"

        self.usage_words = []
        if parts.optionals:
            py_lines = []
            for index in range(len(parts.optionals)):
                py_lines.extend(self.emit_optional(parts, parts.optionals, index))
            py_lines = (py_lines + [""]) if py_lines else []
            args_py_lines.extend(py_lines)

        optional_words = self.usage_words

        # Calculate a usage line summing up the parsed parts
        # Like sometimes trigger "argdoc.py: warning: doc'ced ... calculated ..."

        compiled_usage = None
        if parts.prog:
            compiled_usage = " ".join([parts.prog] + optional_words + positional_words)

        self.compiled_usage = compiled_usage

        # Inject concise "-h" and mnemonic "--help" as "optional arguments"
        # if both are missing  # FIXME: invent how to declare zero Optionals inside an Arg Doc

        if self.parts.add_help is None:
            self.parts.add_help = True

        return args_py_lines

    def emit_positional(self, parts, positionals, index):
        """Compile an Arg Doc Positional argument line into Python source lines"""

        positional = positionals[index]

        (metavar, help_) = splitword(positional.lstrip())
        help_ = help_.lstrip()

        # Calculate "nargs"
        # FIXME FIXME: stop solving only a few cases of "nargs"

        nargs = 1
        if parts.uses.remains and (index == len(positionals) - 1):
            nargs = "..."  # argparse.REMAINDER

        if metavar == "TOP":
            nargs = "?"  # argparse.OPTIONAL
        elif metavar == "FILE":
            if parts.uses.remains == "[FILE] [-- [ARG [ARG ...]]]":
                nargs = "?"  # argparse.OPTIONAL

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

    def emit_optional(self, parts, optionals, index):
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

        if not option.endswith(","):

            self.usage_words.append("[{}]".format(option))

            assert option not in ("-h", "--help",)
            action = "count"
            lines = [
                "parser.add_argument(",
                "    {option}, action={action},".format(
                    option=black_repr(option), action=black_repr(action)
                ),
                "    help={help_}".format(help_=black_repr(help_)),
                ")",
            ]

        else:

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


class _ArgUsageParts(argparse.Namespace):
    """Name the parts of an Arg Doc Usage line"""

    def __init__(self):

        self.prog = None

        self.optionals = None
        self.positionals = None

        self.remains = None


class _ArgDocParts(argparse.Namespace):
    """Name the parts of an Arg Doc"""

    def __init__(self):

        self.prog = None

        self.usage = None
        self.description = None
        self.add_help = None

        self.positionals = None
        self.optionals = None

        self.epilog = None
        self.uses = None


class _ArgDocTaker(object):
    """Pick an Arg Doc apart, line by line"""

    TAGLINE_PATTERNS = (
        r"^positional arguments:$",
        r"^optional arguments:$",
        r"^usage:",
    )

    def take_arg_doc(self, doc):
        """Take every source line"""

        tabsize_8 = 8
        chars = textwrap.dedent(doc.expandtabs(tabsize_8)).strip()

        self.taker = _LineTaker()
        self.taker.give_chars(chars)

        self.parts = _ArgDocParts()

        if doc:

            self.take_usage()
            self.take_description()
            self.accept_positionals()
            self.accept_optional_arguments()
            self.accept_epilog()

        self.take_eof()

        return self.parts

    def take_usage(self):
        """Take the line of Usage"""
        taker = self.taker

        taker.accept_blanklines()
        line = taker.peek_line()

        uses = self.walk_usage(line)
        self.parts.uses = uses
        self.parts.usage = uses.usage
        self.parts.prog = uses.prog

        taker.take_line()

    def walk_usage(self, line):
        """Pick an Arg Doc Usage line apart, word by word"""

        uses = _ArgUsageParts()
        uses.optionals = []
        uses.positionals = []

        chars = line.lstrip()
        (use, chars,) = splitword(chars)
        assert use == "usage:"

        usage = chars.lstrip()
        uses.usage = usage

        chars = usage
        while chars:
            unsplit = chars.lstrip()
            (use, chars,) = splitword(unsplit)

            if not uses.prog:
                uses.prog = use
            elif not use.startswith("["):
                uses.positionals.append(use)
            elif use.startswith("[-") and use.endswith("]"):
                uses.optionals.append(use)
            else:  # FIXME: nargs=='?', nargs > 1, etc.
                uses.remains = unsplit
                chars = ""

        return uses

    def take_description(self):
        """Take the line of description"""
        taker = self.taker
        taker.accept_blanklines()

        self.parts.description = None
        line = taker.peek_line()
        if not any(re.match(p, string=line) for p in _ArgDocTaker.TAGLINE_PATTERNS):
            self.parts.description = line
            taker.take_line()

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
        taker.accept_blanklines()

        line = taker.peek_line()
        if line == tagline:
            taker.take_line()

            taker.accept_blanklines()
            arglines = self.accept_arglines(tagline=tagline)

        return arglines

    def accept_arglines(self, tagline):
        """Take zero or more indented definitions of Positional or Optional arguments"""
        taker = self.taker
        taker.accept_blanklines()

        arglines = []
        while not taker.peek_eof():
            line = taker.peek_line()
            if not line.startswith(" "):
                break
            assert line.startswith("  ")

            arglines.append(line)
            taker.take_line()

            taker.accept_blanklines()

        return arglines

    def accept_epilog(self):
        """Take zero or more trailing lines"""
        taker = self.taker

        lines = []
        while not taker.peek_eof():
            line = taker.peek_line()  # may be blank

            if self.parts.optionals:
                if "positional arguments:" in line:
                    reason = "Optionals before Positionals in Arg Doc"
                    stderr_print("argdoc.py: error: {}".format(reason))
                    sys.exit(1)

            lines.append(line)
            taker.take_line()

        self.parts.epilog = "\n".join(lines)

    def take_eof(self):
        """Do nothing if all lines consumed, else crash"""
        taker = self.taker
        taker.take_eof()


class _LineTaker(object):
    """Walk once thru source chars split into source lines

    Define "take_" to mean require and consume
    Define "peek_" to mean look ahead
    Define "accept_" to mean take if given, and don't take if not given
    """

    def __init__(self):
        self.lines = []

    def give_chars(self, chars):
        lines = chars.splitlines()
        lines = list(_.rstrip() for _ in lines)
        self.lines.extend(lines)

    def take_line(self):
        """Consume the next line"""
        self.lines = self.lines[1:]

    def peek_line(self):
        """Return a copy of the next line without consuming it"""
        return self.lines[0]

    def peek_eof(self):
        """Return True after consuming the last char of the last line"""
        eof = not self.lines
        return eof

    def take_eof(self):
        """Do nothing if all lines consumed, else crash"""
        assert self.peek_eof()

    def accept_blanklines(self):
        """Discard zero or more blank lines"""
        while not self.peek_eof():
            if self.peek_line().strip():
                break
            self.take_line()


def splitword(chars):
    """Return the leading whitespace and first word, split from the remaining chars"""

    head_word = chars.split()[0]
    head = chars[: (chars.index(head_word) + len(head_word))]
    tail = chars[len(head) :]

    return (
        head,
        tail,
    )


def stderr_print(*args):
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


# copied from:  git clone https://github.com/pelavarre/pybashish.git
