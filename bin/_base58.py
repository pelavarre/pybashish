#!/usr/bin/env python3

r"""
usage: _base58.py

demo SNakamoto/ MSporny https://tools.ietf.org/html/draft-msporny-base58-02

wrong-headed because Ietf draft doesn't make clear:

  it's about converting a wide natural numbers between Base 2^N and Base 58

  like correctly encoding the b"\xFF\xFF" of Base 100 into Base 58 gives us b"LUv"

    65535 % 58 = 53  # b"v"
    65535 // 58 = 1129
    1129 % 58 = 27  # b"U"
    1129 // 58 = 19  # b"L"

wrong answers from revisions of "def b58encode":

  b'oGU3JqabjWkQ'
  b'mRp4L4W7xW8gjqimnjEXTX9oF9XKv14bur4GQ1VcyaC2'
  b'11ZbCh'

examples:

  black bin/_base58.py && python3 -i bin/_base58.py

"""

import string

B58 = set(string.digits + string.ascii_uppercase + string.ascii_lowercase)
B58 = "".join(sorted(B58 - set("0OIl"))).encode()
assert B58 == b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
assert len(B58) == 58 == 10 + 26 + 26 - 4


def b58decode(coded_bytes):

    carry = 0

    for coded in coded_bytes:

        carry = B58.index(coded)  # may raise ValueError: subsection not found

        # remainder = carry % len(B58)
        carry = carry // len(B58)

    return b"NotImplementedError"


def b58encode(plain_bytes):

    b58_bytearray = bytearray()
    encoding_flag = False
    zero_counter = 0
    carry = 0

    for plain in plain_bytes:

        if not encoding_flag:

            if plain == 0:
                zero_counter += 1
            else:
                encoding_flag = True

        if encoding_flag:

            carry += 0x100 * plain

            encoded = B58[carry % len(B58)]
            carry = carry // len(B58)

            b58_bytearray += bytearray([encoded])

    b58_encoding = zero_counter * b"1"
    b58_encoding += bytes(b58_bytearray)

    return b58_encoding


def b58test(plain_bytes, coded_bytes):
    print(plain_bytes)
    print(b58decode(coded_bytes))
    print(coded_bytes)
    print(b58encode(plain_bytes))
    print()


if __name__ == "__main__":

    b58test(b"Hello World!", coded_bytes=b"2NEpo7TZRRrLZSi2U")

    b58test(
        b"The quick brown fox jumps over the lazy dog.",
        coded_bytes=b"USm3fpXnKG5EUBx2ndxBDMPVciP5hGey2Jh4NDv6gmeo1LkMeiKrLJUUBk6Z",
    )

    b58test(b"\x00\x00\x28\x7F\xB4\xCD", coded_bytes=b"111233QC4")


# copied from:  git clone https://github.com/pelavarre/pybashish.git
