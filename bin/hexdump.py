#!/usr/bin/env python3

r"""
usage: hexdump.py [-h] [-C] [--bytes BYTES] [--dump-byteset] [FILE [FILE ...]]

show bytes as nybbles and more

positional arguments:
  FILE             a file to copy out

optional arguments:
  -h, --help       show this help message and exit
  -C               show bytes as characters, not just as visually overloaded nybbles
  --bytes [BYTES]  show bytes as bytes:  distinct monospaced glyphs (default: 1 at a time)
  --dump-byteset   first read a file of the bytes b"\x00" through b"\xff"

bugs:
  too many emoji don't do monospace, and passing through arbitrary unicode has arbitrary effects
  shows terminal control (not data) characters of \u0000..\u00ff as \u0100..\u01ff
  shows utf-8 emoji as themselves, followed by as many spaces as they have bytes
  shows the bytes of encoding errors as if decoding the characters \u0000..\u00ff
  shows nybbles in uppercase (following black python not linux c, for the sake of human eyes)
  shows empty files as a zeroed count of bytes (unlike bash showing nothing to mean zero)
  shows the --bytes in groups of n at a time (doesn't always make you count off all the bytes)
  ends each line when it ends, doesn't pad some with spaces

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "hexdump"
  accepts only the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  does accept "-" as meaning "/dev/stdin", unlike mac and linux

examples:
  echo hexdump | hexdump.py
  echo hexdump | hexdump.py -C
  hexdump.py /dev/null
  echo -n 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' | hexdump.py -C
  hexdump.py --dump-byteset | hexdump.py -C
"""
# FIXME: implement usage: hexdump.py -s OFFSET -n LENGTH  # accept 0x hex for either


import contextlib
import os
import sys

import argdoc


def main(argv):

    # Fetch and auto-correct the args

    args = argdoc.parse_args(argv[1:])

    if args.bytes is not False:
        args.bytes = 1 if (args.bytes is None) else int(args.bytes)
        args.C = True
        assert args.bytes

    # Discard Stdin and write the bytes b"\x00" through b"\xFF" to Stdout

    if args.dump_byteset:
        assert not args.files

        for xx in range(0x100):
            xxs = bytearray(1)
            xxs[0] = xx
            os.write(sys.stdout.fileno(), xxs)

        sys.exit()

    # Dump each file

    dumper = HexDumper(args)

    paths = args.files if args.files else ["-"]

    if "-" in paths:
        prompt_tty_stdin()

    for path in paths:
        openable = "/dev/stdin" if (path == "-") else path
        try:
            with open(openable, "rb") as incoming:
                dumper.dump_incoming(incoming)
        except FileNotFoundError as exc:
            stderr_print("hexdump.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


class HexDumper:
    def __init__(self, args):

        self.args = args

        self.incomings = b""

        self.encodeds = b""
        self.nybbleds = ""
        self.decodeds = ""

        self.offset = 0
        self.skids_open = None

    def dump_incoming(self, incoming):
        """Pull each byte as needed"""

        while True:

            more = incoming.read(1)  # FIXME: run faster
            if not more:
                self.dump_decodables(more)
                break

            self.incomings += more
            self.dump_decodables(more)

    def dump_decodables(self, more):
        """Dump only what's decodable, till there are no more bytes"""

        args = self.args

        while True:

            some = b""
            rep = ""

            incomings = self.incomings
            if incomings:

                # Quit if more bytes needed for decode, till there are no more

                xx = incomings[0]
                len_decode = 1 if args.bytes else self.len_utf8_decode(xx)
                if more:
                    if len(incomings) < len_decode:
                        break

                # Split off one to eight bytes

                encodeds = incomings[:len_decode]

                # Decode all the bytes, else just the first byte

                some = encodeds
                rep = self.rep_byte_as_char(encodeds[:1])
                if not args.bytes:
                    try:  # decode if decodes, except keep \u00XX unprintables printable
                        decoded = encodeds.decode()
                        if len(some) > 1:
                            rep = decoded
                    except UnicodeDecodeError:
                        some = encodeds[:1]

                assert some
                assert len(rep) == 1

                self.incomings = incomings[len(some) :]

            # Emit the byte or bytes, and the character

            more_here = more or self.incomings
            self.dump_one_char(some, rep=rep, more=more_here)

            # Quit after decoding all the fetched bytes

            if not self.incomings:
                break

    def rep_byte_as_char(self, encodeds):

        assert len(encodeds) == 1

        xx = ord(encodeds)
        assert 0 <= xx <= 0xFF

        rep = chr(0x100 + ord(encodeds))  # not as decoded
        if 0x20 <= xx <= 0x7E:
            rep = chr(xx)
        elif (0xA1 <= xx) and (xx != 0xDA):
            rep = chr(xx)

        return rep

    def len_utf8_decode(self, xx):
        """Group one to eight bytes together, in the way of utf-8"""

        masks = [0x00, 0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE, 0xFF]
        for (index, left, right,) in zip(range(len(masks)), masks, masks[1:]):
            if (xx & right) == left:
                if left <= 0x80:
                    return 1  # one leading 0b1000_0000 is already not decodable
                len_decode = index
                return len_decode

        return len(masks)

    def dump_one_char(self, some, rep, more):
        """Dump a line at a time, untill there is no more"""

        self.encodeds += some
        self.nybbleds += "_".join("{:02X}".format(_) for _ in some) + " "
        self.decodeds += rep.ljust(len(some))

        width = 0x10
        if (len(self.encodeds) >= width) or (not more):

            self.dump_line_of_chars(
                self.encodeds[:width],
                nybbleds=self.nybbleds[: (len("XX_") * width)],
                decodeds=self.decodeds[:width],
                more=more,
            )

            self.encodeds = self.encodeds[width:]
            self.nybbleds = self.nybbleds[(len("XX_") * width) :]
            self.decodeds = self.decodeds[width:]

            assert len(self.encodeds) < width

        assert len(self.encodeds) == len(self.decodeds)
        assert len(self.nybbleds) == (len("XX_") * len(self.encodeds))

    def dump_line_of_chars(self, encodeds, nybbleds, decodeds, more):
        """Dump 0x30 columns of 2 .. 0x20 nybbles, with an option for 1 .. 0x10 characters too"""

        str_open = ("_" if self.skids_open else " ") if self.args.C else ""

        str_offset = "{:07X}".format(self.offset)
        str_nybbles = self.str_nybbles(nybbleds)
        str_bytes = self.str_chars(decodeds)

        if not self.args.C:
            sep = " "
            line = (
                str_offset.lower()
                + sep
                + str_open
                + str_nybbles.lower().replace("_", " ")
            )
        else:
            sep = "  "
            line = (
                str_offset + sep + str_open + str_nybbles + sep + "|" + str_bytes + "|"
            )
        line = line.rstrip()

        if encodeds:
            print(line)
            self.skids_open = str_nybbles.endswith("_")

        self.offset += len(encodeds)

        if not more:  # print the last offset as the size of file, even when zero
            if not self.args.C:
                print("{:07x}".format(self.offset))
            else:
                print("{:07X}".format(self.offset))

    def str_nybbles(self, nybbleds):
        """Format 0x30 chars to rep between 2 and 0x20 nybbles"""

        reps = nybbleds.ljust(len("XX_") * 0x10)

        return reps

    def str_chars(self, decodeds):
        """Format between 1 and 0x10 chars, with " " spaces injected to group them, or not"""

        stride = self.args.bytes

        if stride is False:
            return decodeds

        assert stride

        reps = ""
        for index in range(0, len(decodeds), stride):
            reps += " "
            reps += decodeds[index:][:stride]
        if decodeds:
            reps += " "

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
