#!/usr/bin/env python3

r"""
usage: bin/_grep.py [--help] [-h] [--rip [SHRED]] [PATTERN [PATTERN ...]]

write and run code to search for patterns, or just write it

positional arguments:
  PATTERN        search key, in the syntax of a Python regular expression

optional arguments:
  --help         show this help message and exit
  -h             say less (same as grep -h)
  --rip [SHRED]  rip code to stdout (or to a filename with a '.' dot in it)

quirks in the syntax:
  writes code that works like "|zgrep -in ... |zgrep -in ..."
  welcomes only more patterns, leaves you to do the work of searching multiple files

examples:
  bin/_grep.py key1  # search stdin lines for key, ignoring case and wordseps and order
  bin/_grep.py key1 key2  # search stdin lines for both keys, ignoring case etc
  bin/_grep.py key1 key2 --r  # just print the code, don't run it
  bin/_grep.py key1 key2 --rip py  # rip out only python code, no other kind
  bin/_grep.py key1 key2 --r p.py  # just save the code in "p.py", don't run it
  grep -n . bin/*.py |bin/_grep.py key1 key2  # search multiple py files
  bin/_grep.py -- -key3 # search stdin for "key3" but spell it starting with a dash
"""

# FIXME: convert between regexes, such as from "grep -E" to "grep"

# FIXME: argdoc: accept, do not require, [--] separating optionals from positionals

# FIXME: see unmarked args as and-also when presented as patterns then >= 0 files

import os
import sys
import textwrap

import argdoc


def main(argv):
    """Run once"""

    # Parse the command line, per the top-of-file docstring

    args = argdoc.parse_args(argv[1:])

    if args.h:
        sys.stderr.write("bin/_grep.py: -h not implemented\n")
        sys.exit(2)  # exit 2 from rejecting usage

    # Pick out the ext (and notice when given a filename)

    p_py = None
    ext = ".py3"  # default: ".py3"

    if args.rip not in (False, None):
        ext = args.rip  # # ".py3" etc mean themselves
        if not args.rip.startswith(os.path.extsep):
            ext = os.path.extsep + args.rip  # "py3" etc means ".py3" etc
            if os.path.extsep in args.rip:

                p_py = args.rip
                ext = os.path.splitext(p_py)[-1]  # else {name}.{ext}

    # Agree to speak only some languages

    exts = ".py .py2 .py23 .py3".split()
    if ext not in exts:
        sys.stderr.write(
            "bin/_grep.py: choose ext from one of {}, not {!r}\n".format(
                "|".join(exts), ext
            )
        )
        sys.exit(2)  # exit 2 from rejecting usage

    # Write the code

    py = emit_searches_as_py(ext, p_py=p_py, patterns=args.patterns)

    # Run the code, print the code, or save the code

    if args.rip is False:

        exec(py, globals())  # pylint: disable=exec-used
        # call through Class ZCatLines via the main Globals

    elif p_py is not None:

        with open(p_py, "w") as writing:
            writing.write(py)

    else:

        sys.stdout.write(py)
        sys.stdout.flush()


def emit_searches_as_py(ext, p_py, patterns):

    py = r""

    py += emit_header(ext, p_py=p_py)
    py += "\n"
    py += emit_body(patterns)
    py += "\n"
    py += "\n"  # twice
    py += emit_trailer()

    return py


def emit_header(ext, p_py):

    py = (
        textwrap.dedent(
            r'''
            #!/usr/bin/env python3

            """
            usage: p.py

            search "/dev/stdin" for keys, ignoring case and wordseps and order
            """

            import contextlib
            import gzip
            import io
            import re
            import sys


            def main(argv):

                lines = {}

                filename = "/dev/stdin"
                # with open(filename) as reading:
                with ZCatLines(filename) as reading:

                    for (index, ended_line) in enumerate(reading):
                        line_number = 1 + index
                        line = ended_line.splitlines()[0]

                        lines[index] = line

                        text = line.expandtabs(tabsize=8).strip()
                        text = text.replace("_", "-")
                        text = text.replace("-", " ")
                        text = text.strip()

            '''
        ).strip()
        + "\n"
    )

    if p_py is not None:
        py = py.replace(r"p.py", p_py)

    if ext == ".py2":
        py = py.replace(r"python3", r"python2")
    elif ext == ".py23":
        py = py.replace(r"python3", r"python")

    return py


def emit_trailer():

    py = r""

    py += (
        textwrap.dedent(
            r'''

            # deffed in many files  # missing from docs.python.org
            class ZCatLines(contextlib.ContextDecorator):
                """GUnzip and read each line, else read each line"""

                def __init__(self, filename):  # a la open(file), gzip.open(filename)
                    self.filename = filename
                    self.closing = None

                def __enter__(self):
                    filename = self.filename

                    # read from uncompressed tty

                    reading = open(filename)

                    if reading.isatty():

                        self.closing = reading  # read a tty
                        return self.closing

                    reading.close()

                    # read from uncompressed file

                    with open(filename, mode="rb") as peeking:
                        peeked_bytes = peeking.read()

                    unzipped = None
                    with io.BytesIO(peeked_bytes) as copying:
                        with gzip.open(copying) as unzipping:
                            try:
                                unzipped = unzipping.read()
                            except Exception:  # often gzip.BadGzipFile

                                chars = peeked_bytes.decode()
                                self.closing = io.StringIO(chars)  # read uncompressed
                                return self.closing

                    # read from compressed file

                    lines = unzipped.decode().splitlines(keepends=True)
                    return lines

                def __exit__(self, *_):
                    if self.closing is not None:
                        return self.closing

            '''
        ).strip()
        + "\n"
    )

    py += "\n"
    py += "\n"  # twice

    py += (
        textwrap.dedent(
            r"""
            if __name__ == "__main__":
                sys.exit(main(sys.argv))
            """
        ).strip()
        + "\n"
    )

    return py


def emit_body(patterns):

    py = r""

    py += (
        textwrap.dedent(
            r"""
                if False:
                    print("visiting {}:{}".format(line_number, text), file=sys.stderr)
            """
        ).strip()
        + "\n"
    )
    py += "\n"

    for pattern in patterns:

        regex = pattern.expandtabs(tabsize=8).strip()
        regex = regex.replace("_", "-")
        regex = regex.replace("-", " ")
        regex = regex.strip()

        assert not (set(regex) & set(r"\""))  # FIXME: accept more patterns
        pattern_py = (
            textwrap.dedent(
                r"""
                    if not re.search(r"{regex}", string=text, flags=re.IGNORECASE):
                        continue
                """
            )
            .format(regex=regex)
            .strip()
            + "\n"
        )

        py = py + pattern_py

    py += "\n"

    py += (
        textwrap.dedent(
            r"""
                print("{}:{}".format(line_number, line), file=sys.stderr)
                sys.stdout.flush()
            """
        ).strip()
        + "\n"
    )

    dents = 3 * "    "
    py = "\n".join((dents + _).rstrip() for _ in py.splitlines()) + "\n"

    return py


_ = """
non-interactive examples, for testing more modes of Class ZCatLines:

  cat bin/_grep.py |bin/_grep.py key1

  rm -fr b.bin b.bin.gz
  cp -ip bin/_grep.py b.bin
  gzip b.bin  # make b.bin.gz
  cat b.bin.gz |bin/_grep.py key1 key2

  bin/_grep.py key1 key2 --rip >o
  bin/_grep.py key1 key2 --rip py >o.py
  bin/_grep.py key1 key2 --rip .py2 >o.py2
  bin/_grep.py key1 key2 --rip p.py23
  bin/_grep.py key1 key2 --rip p.py3
  diff -burp p.py3 o
  diff -burp p.py3 o.py
  diff -burp p.py3 o.py2
  diff -burp p.py3 p.py23
"""


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
