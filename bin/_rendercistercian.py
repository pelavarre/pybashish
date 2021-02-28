#!/usr/bin/env python3

"""
usage: _rendercistercian.py

do good stuff

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""


import __main__

PIXELS = """
.....
..|..
..|..
..|..
.....
""".strip().splitlines()

GLYPHS = r"""
...  ._.  ...  ...  ...  ._.  ...  ._.  ...  ._.
|..  |..  |_.  |\.  |/.  |./  |.|  |.|  |_|  |_|
""".strip().splitlines()


def add_rune():
    for (index, chars) in enumerate(PIXELS):
        __main__.lines[index] += "  " + chars


def draw_chars(chars, y, x):
    line = __main__.lines[y]
    x_ = len(line) - 5 + x
    for (i, c) in enumerate(chars):
        xi = x_ + i
        line = line[:xi] + c + line[(xi + 1) :]
    __main__.lines[y] = line


def draw_digit(digit, y, x):

    i = int(digit)
    if i:

        a = GLYPHS[0].split()[i]
        b = GLYPHS[1].split()[i]
        c = "|.."
        if not x:
            a = a[::-1]
            b = b[::-1]
            c = c[::-1]

        d = b
        if bool(x) == bool(y):
            d = b.replace("/", "?").replace("\\", "/").replace("?", "\\")

        (p, q) = (a, d)
        if y:
            p = "".join((dd if (dd == "_") else cc) for (dd, cc) in zip(d, c))
            q = "".join(
                (aa if ((aa == "_") or (dd == "_")) else dd) for (aa, dd) in zip(a, d)
            )

        draw_chars(p, y=y, x=x)
        draw_chars(q, y=(y + 1), x=x)


def draw_one_rune(rune):
    quad = "{:04d}".format(rune)
    add_rune()
    draw_digit(quad[3], y=0, x=2)
    draw_digit(quad[2], y=0, x=0)
    draw_digit(quad[1], y=2, x=2)
    draw_digit(quad[0], y=2, x=0)


def print_drawn_runes():
    chars = "\n".join(__main__.lines).replace(".", " ")
    print(chars)


def print_some_runes(runes):
    runes_list = list(runes)
    __main__.lines = list("" for _ in PIXELS)
    for rune in runes_list:
        draw_one_rune(rune)
    line = "".join("  {:<5d}".format(_) for _ in runes_list)
    __main__.lines.append(line)
    __main__.lines.append("")
    print_drawn_runes()


def print_lotsa_runes():
    print()
    print()
    print_some_runes(range(1, 10, 1))
    print_some_runes(range(10, 100, 10))
    print_some_runes(range(100, 1_000, 100))
    print_some_runes(range(1_000, 10_000, 1_000))
    print()
    print()
    print_some_runes([1642, 1776, 1789, 1865, 1919, 1945, 1991])
    print()
    print()


print_lotsa_runes()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
