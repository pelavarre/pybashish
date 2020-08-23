#!/usr/bin/env python3

r"""
usage: hexdump.py [-h] [-C] [--bytes] [FILE [FILE ...]]

show bytes as nybbles and more

positional arguments:
  FILE        a file to copy out

optional arguments:
  -h, --help  show this help message and exit
  -C          show bytes visibly as characters, not just as visually overloaded nybbles
  --bytes     discard stdin and write the bytes b"\x00" through b"\xff" to stdout

bugs:
  too many emoji don't do monospace, and passing through arbitrary unicode has arbitrary effects
  shows us-ascii terminal control codes \x00..\x1f and \x7f as if unicode \u100..\u11f and \u17f
  shows utf-8 emoji as themselves, repeated for the byte length of their encoding
  shows the bytes of encoding errors as if decoding \u0 ..\uff
  shows nybbles in uppercase (following black python not linux c, for the sake of human eyes)
  shows empty files as a zeroed count of bytes (unlike bash showing nothing to mean zero)
  groups the -C nybbles and chars four at a time, never makes you count out eight of them
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
  hexdump.py --bytes | hexdump.py -C
"""
# FIXME: implement usage: hexdump.py -s OFFSET -n LENGTH  # accept 0x hex for either


import contextlib
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])

    # Discard Stdin and write the bytes b"\x00" through b"\xFF" to Stdout

    if args.bytes:
        assert not args.files

        for xx in range(0x100):
            xxs = bytearray(1)
            xxs[0] = xx
            os.write(sys.stdout.fileno(), xxs)

        sys.exit()

    # Dump each file

    dumper = HexDumper(args)

    relpaths = args.files if args.files else ["-"]

    if "-" in relpaths:
        prompt_tty_stdin()

    for relpath in relpaths:
        openable = "/dev/stdin" if (relpath == "-") else relpath
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
        self.decodeds = ""

        self.offset = 0

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

        while True:

            some = b""
            rep = ""

            incomings = self.incomings
            if incomings:

                # Quit if more bytes needed for decode, till there are no more

                xx = incomings[0]
                len_decode = self.len_utf8_decode(xx)
                if more:
                    if len(incomings) < len_decode:
                        break

                # Split off one to eight bytes

                encodeds = incomings[:len_decode]

                # Decode all the bytes, else just the first byte

                some = encodeds
                if (len(encodeds) == 1) and (
                    (ord(encodeds) < 0x20) or (ord(encodeds) == 0x7F)
                ):
                    _ = encodeds.decode()  # affirm no UnicodeDecodeError raised
                    rep = chr(0x100 + ord(encodeds))  # not as decoded
                else:
                    try:
                        rep = encodeds.decode()
                    except UnicodeDecodeError:
                        some = encodeds[:1]
                        rep = chr(0x100 + ord(encodeds[:1]))  # as if decoded

                assert some
                assert len(rep) == 1

                self.incomings = incomings[len(some) :]

            # Emit the byte or bytes, and the character

            more_here = more or self.incomings
            self.dump_encodeds_decoded(some, rep=rep, more=more_here)

            # Quit after decoding all the fetched bytes

            if not self.incomings:
                break

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

    def dump_encodeds_decoded(self, some, rep, more):
        """Dump a line at a time, untill there is no more"""

        self.encodeds += some
        self.decodeds += len(some) * rep

        width = 0x10
        if (len(self.encodeds) >= width) or (not more):

            self.dump_line(
                self.encodeds[:width], decodeds=self.decodeds[:width], more=more
            )
            self.encodeds = self.encodeds[width:]
            self.decodeds = self.decodeds[width:]

            assert len(self.encodeds) < width

        assert len(self.encodeds) == len(self.decodeds)

    def dump_line(self, encodeds, decodeds, more):
        """Dump 0x30 columns of 2 .. 0x20 nybbles, with an option for 1 .. 0x10 characters too"""

        str_offset = "{:07X}".format(self.offset)
        str_nybbles = self.str_nybbles(encodeds)
        str_bytes = self.str_chars(decodeds)

        if not self.args.C:
            sep = " "
            line = str_offset.lower() + sep[:-1] + str_nybbles.lower().replace("-", " ")
        else:
            sep = "  "
            line = str_offset + sep[:-1] + str_nybbles + sep + "|" + str_bytes + "|"

        if encodeds:
            print(line.rstrip())

        self.offset += len(encodeds)

        if not more:  # print the last offset as the size of file, even when zero
            if not self.args.C:
                print("{:07x}".format(self.offset))
            else:
                print("{:07X}".format(self.offset))

    def str_nybbles(self, encodeds):
        """Format 0x30 chars  to rep between 2 and 0x20 nybbles"""

        reps = ""
        for index in range(0x10):
            if index >= len(encodeds):
                reps += "   "
            else:
                ord_byte = encodeds[index]
                sep = "-" if (index % 4) else " "
                reps += "{}{:02X}".format(sep, ord_byte)

        return reps

    def str_chars(self, decodeds):

        reps = ""
        for index in range(0, len(decodeds), 4):
            reps += " "
            reps += decodeds[index:][:4]
        if decodeds:
            reps += " "

        return reps


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


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
