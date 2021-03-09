#!/usr/bin/env python3

"""
usage: _base58.py

demo SNakamoto/ MSporny https://tools.ietf.org/html/draft-msporny-base58-02

examples:
  black bin/_base58.py && python3 -i bin/_base58.py
"""

import string

B58 = set(string.digits + string.ascii_uppercase + string.ascii_lowercase)
B58 = "".join(sorted(B58 - set("0OIl"))).encode()
assert B58 == b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
assert len(B58) == 58 == 10 + 26 + 26 - 4


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


def b58decode(encodeds):
    raise NotImplementedError()


print(b"2NEpo7TZRRrLZSi2U")
print(b58encode(b"Hello World!"))
print()

print(b"USm3fpXnKG5EUBx2ndxBDMPVciP5hGey2Jh4NDv6gmeo1LkMeiKrLJUUBk6Z")
print(b58encode(b"The quick brown fox jumps over the lazy dog."))
print()

print(b"111233QC4")
print(b58encode(b"\x00\x00\x28\x7F\xB4\xCD"))
print()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
