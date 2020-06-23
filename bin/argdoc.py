#!/usr/bin/env python3

r"""
usage: argdoc.py [-h] [--doc] FILE [-- [ARG [ARG ...]]]

parse args as helped by module help doc

positional arguments:
  FILE        where the arg doc is
  ARG         an arg to parse as per the arg doc

optional arguments:
  -h, --help  show this help message and exit
  --doc       print the arg doc without compiling it

usage as a python import:

  import argdoc

  if __name__ == '__main__':
    args = argdoc.parse_args()
    print(args)

examples:

./argdoc.py -h                      # show this help message
./argdoc.py argdoc.py               # translate a file's arg doc to python
./argdoc.py --doc argdoc.py         # show a file's arg doc
./argdoc.py argdoc.py --            # parse no arg with the file's arg doc
./argdoc.py argdoc.py -- --help     # parse the arg "--help" with the file's arg doc
./argdoc.py argdoc.py -- hi world   # parse two args with the file's arg doc

"""  # FIXME: parsed args whose names begin with a '_' skid don't print here

from __future__ import print_function

import argparse
import inspect
import os
import re
import sys
import textwrap


def main(argv):
    """Run from the command line"""

    args = parse_args(argv[1:])
    args.file_doc = read_docstring_from(args.file)

    args_separated = "--" in argv[1:]
    if args.doc:

        print(args.file_doc)

    elif not args_separated:

        source = _ArgDocCoder().compile_argdoc(args.file_doc)
        print(source)

    else:

        file_args = parse_args(args.args, doc=args.file_doc)
        file_parser = file_args._argument_parser

        if not file_parser.add_help:
            if file_args.help:
                file_parser.print_help()
                sys.exit(0)

        for (k, v,) in sorted(vars(file_args).items()):
            if not k.startswith("_"):
                print("{k}={v!r}".format(k=k, v=v))


def read_docstring_from(relpath):
    """
    Read the docstring from a python file without importing the rest of it

    Specifically read the first lines from triple-quote to triple-quote \"\"\" or ''',
    but ignore leading lines begun with a hash #
    """

    if not os.path.exists(relpath):
        try:
            open(relpath, "rt")
        except FileNotFoundError as exc:
            stderr_print("{}: {}".format(type(exc).__name__, exc))
            sys.exit(1)

    texts = []
    qqq = None
    with open(relpath, "rt") as reading:
        for line in reading.readlines():
            text = line.rstrip()
            if texts or text:
                if not text.startswith("#"):
                    if not qqq:
                        if '"""' in text:
                            texts.append(text)
                            qqq = '"""'
                        elif "'''" in text:
                            texts.append(text)
                            qqq = "'''"
                        else:
                            pass
                    else:
                        texts.append(text)
                        if qqq in text:
                            break

    source = "doc = " + "\n".join(texts)

    global_vars = {}
    exec(source, global_vars)

    doc = global_vars["doc"]
    return doc


def parse_args(args=None, namespace=None, doc=None):
    """Parse args as helped by doc"""

    parser = argument_parser(doc)

    if args is None:
        args = sys.argv[1:]
    if namespace is None:
        namespace = argparse.Namespace(_argument_parser=parser)
    space = parser.parse_args(args, namespace=namespace)

    return space


def argument_parser(doc=None):
    """Compile the doc into a parser"""

    if doc is None:
        main = sys.modules["__main__"]
        doc = main.__doc__

    coder = _ArgDocCoder()
    source = coder.compile_argdoc(doc)

    parser = coder.run_argdoc(doc)
    return parser


class _ArgDocCoder(argparse.Namespace):  # FIXME: produce Black'ened style
    """Work up an ArgumentParser to match its ArgDoc"""

    def __init__(self):
        self.prog = None
        self.optionals = None
        self.positionals = None
        self.remains = None

    def run_argdoc(self, doc):
        """Return an ArgumentParser constructed from a run of its ArgDoc"""

        source = self.compile_argdoc(doc)
        global_vars = {}
        exec(source, global_vars)

        parser = global_vars["parser"]
        return parser

    def compile_argdoc(self, doc):
        """Compile an arg doc into Python source lines"""

        d = r"    "
        picker = _ArgDocPicker()

        parts = picker.pick_apart_doc(doc)
        self.parts = parts

        if (
            True
        ):  # FIXME: allow free text in epilog, after these stop being bug consequences
            assert "positional arguments:" not in parts.epilog
            assert "optional arguments:" not in parts.epilog
            # FIXME: explain better when people get these two backwards in the arg doc

        args_py_lines = self.compile_arguments()

        lines = []

        lines.append("import argparse")
        lines.append("import textwrap")
        lines.append("")

        lines.append("parser = argparse.ArgumentParser(")
        lines.append(d + "prog={prog!r},".format(prog=parts.prog))

        if self.parts.usage != self.calculated_usage:
            stderr_print("doc'ced {}".format(self.parts.usage))
            stderr_print("calculated {}".format(self.calculated_usage))
            # FIXME:  resolve conflicts between argdoc and parser more elegantly

        if "..." in self.calculated_usage:
            lines.append(d + "usage={usage!r},".format(usage=self.calculated_usage))

        if parts.description:
            lines.append(
                d + "description={description!r},".format(description=parts.description)
            )

        lines.append(d + "add_help={add_help},".format(add_help=bool(parts.add_help)))
        lines.append(
            d + "formatter_class=argparse.RawTextHelpFormatter,"
        )  # for .print_help()

        lines.append(d + 'epilog=textwrap.dedent("""')
        for line in parts.epilog.splitlines():
            lines.append((d + d + line).rstrip())
        lines.append(d + '""")')
        lines.append(")")
        lines.append("")

        lines.extend(args_py_lines)

        source = "\n".join(lines)
        return source

    def compile_arguments(self):
        """Compile the positionals and optionals of the arg doc"""

        parts = self.parts

        args_py_lines = []

        # Compile the positionals of the arg doc

        self.usage_words = []
        if parts.positionals:  # call add_argument for each positional
            py_lines = []
            for index in range(len(parts.positionals)):
                py_lines.extend(
                    self.compile_positional(parts, parts.positionals, index)
                )
            py_lines.append("")
            args_py_lines.extend(py_lines)

        positional_words = self.usage_words

        # Compile the optionals of the arg doc

        self.usage_words = []
        if (
            parts.optionals
        ):  # call add_argument for each optionals, except not for add_help
            py_lines = []
            for index in range(len(parts.optionals)):
                py_lines.extend(self.compile_optional(parts, parts.optionals, index))
            py_lines = (py_lines + [""]) if py_lines else []
            args_py_lines.extend(py_lines)

        optional_words = self.usage_words

        # Calculate a usage line summing up the parsed parts

        self.calculated_usage = " ".join(
            [parts.prog] + optional_words + positional_words
        )

        return args_py_lines

    def compile_positional(self, parts, positionals, index):
        """Compile an arg doc positional argument line into Python source lines"""

        positional = positionals[index]

        (metavar, help_) = _split_first_word(positional.lstrip())
        help_ = help_.lstrip()

        nargs = 1
        if parts.uses.remains and (index == len(positionals) - 1):
            nargs = "..."

        if nargs == 1:
            self.usage_words.append(metavar)
        else:
            assert nargs == "..."
            if (
                metavar == "ARG"
            ):  # FIXME: stop solving only the "argdoc.py" case of this
                self.usage_words.append("[-- [{} [{} ...]]]".format(metavar, metavar))
            else:
                self.usage_words.append("[{} [{} ...]]".format(metavar, metavar))

        dest = metavar.lower()
        if nargs != 1:
            dest = (metavar + "s").lower()

        if nargs == 1:

            if dest == metavar:
                lines = [
                    "parser.add_argument({dest!r},".format(dest=dest),
                    "                    help={help_!r})".format(help_=help_),
                ]
            else:
                lines = [
                    "parser.add_argument({dest!r}, metavar={metavar!r},".format(
                        dest=dest, metavar=metavar
                    ),
                    "                    help={help_!r})".format(help_=help_),
                ]

        else:

            if dest == metavar:
                lines = [
                    "parser.add_argument({dest!r}, nargs={nargs!r},".format(
                        dest=dest, nargs=nargs
                    ),
                    "                    help={help_!r})".format(help_=help_),
                ]
            else:
                lines = [
                    "parser.add_argument({dest!r}, metavar={metavar!r}, nargs={nargs!r},".format(
                        dest=dest, metavar=metavar, nargs=nargs
                    ),
                    "                    help={help_!r})".format(help_=help_),
                ]

        return lines

    def compile_optional(self, parts, optionals, index):
        """Compile an arg doc positional argument line into Python source lines"""

        optional = optionals[index]
        words = optional.split()

        option = words[0]
        help_ = optional[optional.index(option) :][len(option) :].lstrip()
        assert option.startswith("-") or option.startswith("--")
        assert not option.startswith("---")

        if not option.endswith(","):

            self.usage_words.append("[{}]".format(option))

            assert option not in ("-h", "--help",)
            action = "store_true"
            lines = [
                "parser.add_argument({option!r}, action={action!r},".format(
                    option=option, action=action
                ),
                "                    help={help_!r})".format(help_=help_),
            ]

        else:

            concise = words[0][: -len(",")]
            mnemonic = words[1]
            help_ = optional[optional.index(mnemonic) :][len(mnemonic) :].lstrip()

            self.usage_words.append("[{}]".format(concise))

            assert not concise.startswith("--")
            assert mnemonic.startswith("--") and not mnemonic.startswith("---")

            _h_help = "show this help message and exit"
            if (concise == "-h") and (mnemonic == "--help") and (help_ == _h_help):
                parts.add_help = True
                lines = []
            else:
                action = "store_true"
                lines = [
                    "parser.add_argument({concise!r}, {mnemonic!r}, action={action!r},".format(
                        concise=concise, mnemonic=mnemonic, action=action
                    ),
                    "                    help={help_!r})".format(help_=help_),
                ]

        return lines


class _ArgDocParts(argparse.Namespace):
    """Name the parts of an ArgDoc"""

    def __init__(self):
        self.prog = None
        self.usage = None
        self.description = None
        self.add_help = None
        self.positionals = None
        self.optionals = None
        self.epilog = None
        self.uses = None


class _ArgUsageParts(argparse.Namespace):
    """Name the parts of an ArgDoc Usage line"""

    def __init__(self):
        self.prog = None
        self.optionals = None
        self.positionals = None
        self.remains = None


class _ArgDocPicker(object):
    """Pick an ArgDoc apart, line by line"""

    TAGLINE_PATTERNS = (
        r"^positional arguments:$",
        r"^optional arguments:$",
        r"^usage:",
    )

    def pick_apart_doc(self, doc):
        """Take every source line, else raise exception"""

        tabsize_8 = 8
        chars = textwrap.dedent(doc.expandtabs(tabsize_8)).strip()

        self.walker = _LineWalker()
        self.walker.give_chars(chars)

        self.parts = _ArgDocParts()

        self.take_usage()
        self.take_description()
        self.accept_positionals()
        self.accept_optional_arguments()
        self.accept_epilog()
        self.take_eof()

        return self.parts

    def take_usage(self):
        """Take the line of usage"""
        walker = self.walker

        walker.accept_blanklines()
        line = walker.peek_line()

        uses = self.walk_usage(line)
        self.parts.uses = uses
        self.parts.usage = uses.usage
        self.parts.prog = uses.prog

        walker.take_line()

    def walk_usage(self, line):
        """Pick an ArgDoc Usage line apart, word by word"""

        uses = _ArgUsageParts()
        uses.optionals = []
        uses.positionals = []

        chars = line.lstrip()
        (use, chars,) = _split_first_word(chars)
        assert use == "usage:"

        usage = chars.lstrip()
        uses.usage = usage

        chars = usage
        while chars:
            unsplit = chars.lstrip()
            (use, chars,) = _split_first_word(unsplit)

            if not uses.prog:
                uses.prog = use
            elif not use.startswith("["):
                uses.positionals.append(use)
            elif use.startswith("[-") and use.endswith("]"):
                uses.optionals.append(use)
            else:  # TODO: nargs=='?', nargs > 1, etc.
                uses.remains = unsplit
                chars = ""

        return uses

    def take_description(self):
        """Take the line of description"""
        walker = self.walker
        walker.accept_blanklines()

        self.parts.description = None
        line = walker.peek_line()
        if not any(re.match(p, string=line) for p in _ArgDocPicker.TAGLINE_PATTERNS):
            self.parts.description = line
            walker.take_line()

    def accept_positionals(self):
        """Take the positional arguments"""
        self.parts.positionals = self.accept_argblock("positional arguments:")

    def accept_optional_arguments(self):
        """Take the optional arguments"""
        self.parts.optionals = self.accept_argblock("optional arguments:")

    def accept_argblock(self, tagline):
        """Take the positional or optional arguments"""
        arglines = None

        walker = self.walker
        walker.accept_blanklines()

        line = walker.peek_line()
        if line == tagline:
            walker.take_line()

            walker.accept_blanklines()
            arglines = self.accept_arglines(tagline=tagline)

        return arglines

    def accept_arglines(self, tagline):
        """Take zero or more indented definitions of positional or optional arguments"""
        walker = self.walker
        walker.accept_blanklines()

        arglines = []
        while not walker.peek_eof():
            line = walker.peek_line()
            if not line.startswith(" "):
                break
            assert line.startswith("  ")

            arglines.append(line)
            walker.take_line()

            walker.accept_blanklines()

        return arglines

    def accept_epilog(self):
        """Take zero or more trailing lines"""
        walker = self.walker

        lines = []
        while not walker.peek_eof():
            lines.append(walker.peek_line())  # may be blank
            walker.take_line()

        self.parts.epilog = "\n".join(lines)

    def take_eof(self):
        """Do nothing if all lines consumed, else crash"""
        walker = self.walker
        walker.take_eof()


class _LineWalker(object):
    """Walk once thru source chars split into source lines"""

    def __init__(self):
        self.lines = []

    def give_chars(self, chars):
        lines = chars.splitlines()
        lines = [l.rstrip() for l in lines]
        self.lines.extend(lines)

    def accept_blanklines(self):
        """Discard zero or more blank lines"""
        while not self.peek_eof():
            if self.peek_line().strip():
                break
            self.take_line()

    def peek_line(self):
        """Return a copy of the next line without consuming it"""
        return self.lines[0]

    def take_line(self):
        """Consume the next line"""
        self.lines = self.lines[1:]

    def peek_eof(self):
        """Return True after consuming the last char of the last line"""
        eof = not self.lines
        return eof

    def take_eof(self):
        """Do nothing if all lines consumed, else crash"""
        assert self.peek_eof()


def _split_first_word(chars):  # FIXME: promote up into the Git Log
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


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
