#!/usr/bin/env python3

r"""
usage: hexdump.py [-h] [-C] [--bytes BYTES] [--charset CHARSET] [--dump-byteset] [FILE [FILE ...]]

show bytes as nybbles and more

positional arguments:
  FILE                 a file to copy out (default: stdin)

optional arguments:
  -h, --help           show this help message and exit
  -C                   show bytes as eight-bit chars:  distinct monospaced glyphs
  --bytes [BYTES]      group bytes as each single 1 byte, or pairs of 2, or quads of 4, etc
  --charset [CHARSET]  show bytes as decoded by a charset (default: "utf-8")
  --dump-byteset       write the bytes b"\x00" through b"\xff" to stdout

bugs:
  too many emoji don't do monospace, and passing through arbitrary unicode has arbitrary effects
  shows terminal control (not data) characters of \u0000..\u00ff as \u0100..\u01ff
  shows utf-8 emoji as themselves, followed by as many spaces as they have bytes
  shows the bytes of encoding errors as if decoding the characters \u0000..\u00ff
  shows nybbles in uppercase (following black python not linux c, for the sake of human eyes)
  shows empty files as a zeroed count of bytes (unlike bash showing nothing to mean zero)
  shows the --bytes in groups of n at a time (doesn't always make you count off all the bytes)
  ends each line when it ends, doesn't pad some with spaces
  doesn't (yet?) compress duplicate lines of hex

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "hexdump"
  accepts only the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", unlike mac and linux

examples:
  echo -n hexdump.py | hexdump  # classic eight-bit groups at Mac, but messy at Linux
  echo -n hexdump.py | hexdump.py
  echo -n hexdump.py | hexdump -C  # classic shorthand close to meaning --bytes 1
  echo -n hexdump.py | hexdump.py -C
  echo -n hexdump.py | hexdump.py --c  # our shorthand meaning --charset utf-8
  echo -n 0123456789abcdef | hexdump.py --bytes 4 -C  # quads
  /bin/echo -n $'ijk\xC0\x80nop' | hexdump.py --chars  # overlong encoding, aka non-shortest form
  echo -n 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' | hexdump.py --chars  # common non-ascii
  echo -n $'\xC2\xA0 « » “ ’ ” – — ′ ″ ‴ ' | hexdump.py --chars  # common 'smart' chars
  hexdump.py --dump-byteset | hexdump.py --chars
  hexdump.py /dev/null  # visibly empty
"""

#
# see also:
#
# Python3 UnicodeDecodeError "invalid start byte" for (all?) overlong encodings
#
# Unicode-org:  Control Chars of C0/C1, and Data Chars of Latin Basic/ Supplement/ Extended A/B
# https://unicode.org/charts/PDF/U0000.pdf
# https://unicode.org/charts/PDF/U0080.pdf
# https://unicode.org/charts/PDF/U0100.pdf
#
# Google Search:  site:docs.python.org us-ascii
# => "utf-8" and "latin-1" defined at:  https://docs.python.org/3/library/codecs.html
#

# FIXME: add -v to stop compressing duplicate lines of hex, and turn it on by default
# FIXME: work out precisely how to make Linux "hexdump" match the style of the default Mac dump
# FIXME: consider shipping "hd", "od", etc as additions or replacements of "hexdump.py"

# FIXME: delete the CHARSET variations, or code something real such as "cp500, ebcdic-cp-be"

# FIXME: implement usage: hexdump.py -s OFFSET -n LENGTH  # accept 0x hex for either
# FIXME: add --no-offsets


import contextlib
import os
import sys

import argdoc


def main(argv):

    args = _parse_hexdump_argv(argv)

    # Write the bytes b"\x00" through b"\xFF" to Stdout, before doing more

    if args.dump_byteset:
        for xx in range(0x100):
            xxs = bytearray(1)
            xxs[0] = xx
            os.write(sys.stdout.fileno(), xxs)

    # Dump each file

    dumper = HexDumper(args)

    paths = args.files
    if not (args.files or args.dump_byteset):
        paths = ["-"]

    if "-" in paths:
        prompt_tty_stdin()

    for path in paths:
        readable = "/dev/stdin" if (path == "-") else path
        try:
            with open(readable, "rb") as incoming:
                dumper.dump_incoming(incoming)
        except FileNotFoundError as exc:
            stderr_print("hexdump.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


def _parse_hexdump_argv(argv):
    """Parse the command line"""

    args = argdoc.parse_args(argv[1:])

    args.classic = (args.bytes is False) and (args.charset is False)

    #

    args.stride = 1
    if (args.bytes is not None) and (args.bytes is not False):
        args.stride = int(args.bytes, 0)

    #

    args.encoding = args.C or (args.charset is not False)

    args.decoding = None
    far_codec_hint = "utf-8"
    if args.charset is not False:
        args.decoding = True
        if args.charset:
            far_codec_hint = args.charset

        if args.bytes is not False:
            stderr_print(argdoc.format_usage().rstrip())
            stderr_print("hexdump.py: error: choose --charset or --bytes, not both")
            sys.exit(2)  # exit 2 from rejecting usage

    "".encode(far_codec_hint)  # may raise LookupError: unknown encoding

    near_codec_hint = far_codec_hint.replace("-", "_").lower()

    ascii_codec_hints = "ascii 646 us_ascii"
    utf_8_codec_hints = "utf_8 u8 utf utf8 cp65001".split()
    latin_1_codec_hints = (
        "latin_1 iso_8859_1 iso8859_1 8859 cp819 latin latin1 l1".split()
    )

    args.codec = far_codec_hint
    if near_codec_hint in ascii_codec_hints:
        args.codec = "ascii"
    elif near_codec_hint in latin_1_codec_hints:
        args.codec = "latin-1"
    elif near_codec_hint in utf_8_codec_hints:
        args.codec = "utf-8"
    else:
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("hexdump.py: error: choose --charset from: ascii, latin-1, utf-8")
        sys.exit(2)  # exit 2 from rejecting usage

    #

    return args


class HexDumper:
    def __init__(self, args):

        self.args = args

        self.incomings = b""

        self.encodeds = b""
        self.decodeds = ""

        self.offset = 0
        self.skids_open = None

    def dump_incoming(self, incoming):
        """Pull each byte as needed"""

        while True:

            got_more = incoming.read(1)  # FIXME: run faster
            if not got_more:
                self.dump_decodables(got_more)
                break

            self.incomings += got_more
            self.dump_decodables(got_more)

    def dump_decodables(self, got_more):
        """Dump only what's decodable, till there are no more bytes"""

        args = self.args

        while True:

            some = b""
            rep = ""

            incomings = self.incomings
            if incomings:

                # Quit if more bytes needed for decode, till there are no more

                len_decode = self.len_decodable() if args.decoding else 1
                if got_more:
                    if len(incomings) < len_decode:
                        break

                # Split off one to eight bytes

                encodeds = incomings[:len_decode]

                # Decode all the bytes, else just the first byte

                some = encodeds
                rep = self.rep_byte_as_char(encodeds[0])
                if args.decoding:
                    try:  # decode if decodes, except keep \u00XX unprintables printable
                        decoded = encodeds.decode(args.codec)
                        if len(some) > 1:  # FIXME: when not "utf-8"/ "latin-1"/ "ascii"
                            rep = decoded
                    except UnicodeDecodeError:
                        some = encodeds[:1]

                assert some
                assert len(rep) == 1

                self.incomings = incomings[len(some) :]

            # Emit the byte or bytes, and the character

            got_more_here = got_more or self.incomings
            self.dump_one_char(some, rep=rep, got_more=got_more_here)

            # Quit after decoding all the fetched bytes

            if not self.incomings:
                break

    def rep_byte_as_char(self, xx):
        """Choose to print each undecoded byte as Latin or Extended Latin"""

        assert 0 <= xx <= 0xFF

        rep = chr(0x100 + xx)  # not as decoded, extended latin instead
        if 0x20 <= xx <= 0x7E:
            rep = chr(xx)  # basic latin data, not control
        elif (0xA1 <= xx) and (xx != 0xAD):
            rep = chr(xx)  # latin 1 data, not control

        return rep

    def len_decodable(self):
        """Group the bytes of the next char together"""

        args = self.args

        if args.codec in ("ascii", "latin-1",):
            return 1

        assert args.codec == "utf-8"

        xx = self.incomings[0]

        masks = [0x00, 0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE, 0xFF]
        for (index, left, right,) in zip(range(len(masks)), masks, masks[1:]):
            if (xx & right) == left:
                if left <= 0x80:
                    return 1  # one leading 0b1000_0000 is already not decodable
                len_decode = index
                return len_decode

        return len(masks)

    def dump_one_char(self, some, rep, got_more):
        """Dump a line at a time, untill there is no more"""

        self.encodeds += some
        self.decodeds += rep.ljust(len(some))

        width = 0x10
        if (len(self.encodeds) >= width) or (not got_more):

            self.dump_line_of_chars(
                self.encodeds[:width],
                decodeds=self.decodeds[:width],
                got_more=got_more,
            )

            self.encodeds = self.encodeds[width:]
            self.decodeds = self.decodeds[width:]

            assert len(self.encodeds) < width

        assert len(self.encodeds) == len(self.decodeds)

    def dump_line_of_chars(self, encodeds, decodeds, got_more):
        """Dump 0x30 columns of 2 .. 0x20 nybbles, with an option for 1 .. 0x10 characters too"""

        args = self.args

        rep_open = ("_" if self.skids_open else " ") if args.decoding else ""

        rep_offset = "{:07X}".format(self.offset)
        if args.classic:
            rep_offset = "{:07X}".format(self.offset).lower()

        rep_nybbles = self.str_nybbles(encodeds)

        rep_bytes = self.str_chars(decodeds)

        if args.encoding:

            sep = "  "
            left = "|"
            right = "|"
            line = (
                rep_offset
                + sep
                + rep_open
                + rep_nybbles
                + sep
                + left
                + rep_bytes
                + right
            )

        else:

            sep = " "
            line = rep_offset + sep + rep_open + rep_nybbles.lower().replace("_", " ")

        line = line.rstrip()

        if encodeds:
            print(line)
            self.skids_open = rep_nybbles.endswith("_")

        self.offset += len(encodeds)

        # Print the last offset as the size of file, even when file empty

        str_offset = None
        if not got_more:
            if args.classic:
                str_offset = "{:07X}".format(self.offset).lower()
            else:
                str_offset = "{:07X}".format(self.offset)

        if str_offset:
            print(str_offset)

    def str_nybbles(self, encodeds):
        """Format between 2 and 0x20 nybbles, spreading as wide as if 0x20 nybbles"""

        args = self.args
        width = 0x10

        reps = ""

        if args.C or (args.stride != 1):
            reps += " "

        for index in range(width):

            if index:
                if (args.stride != 1) and (index % args.stride):
                    reps += "_"
                else:
                    reps += " "

                if args.classic and args.encoding:
                    if index == 8:
                        reps += " "

            if index >= len(encodeds):

                reps += "  "

            else:

                xx = encodeds[index]
                if args.classic:
                    reps += "{:02X}".format(xx).lower()
                else:
                    reps += "{:02X}".format(xx)

        return reps

    def str_chars(self, decodeds):
        """Format between 1 and 0x10 chars, with " " spaces injected to group them, or not"""

        args = self.args
        stride = args.stride
        sep = " "

        if stride == 1:
            return decodeds

        reps = ""
        for index in range(0, len(decodeds), stride):
            reps += sep
            reps += decodeds[index:][:stride]
        if decodeds:
            reps += sep

        return reps


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
class BrokenPipeErrorSink(contextlib.ContextDecorator):
    """Cut unhandled BrokenPipeError down to sys.exit(1)

    Test with large Stdout cut sharply, such as:  find.py ~ | head

    More narrowly than:  signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)
    As per https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc, exc_traceback,) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


if __name__ == "__main__":
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
