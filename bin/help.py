#!/usr/bin/env python3

import glob
import os
import sys


def main():

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(file_dir)

    globbed = glob.glob("*.py")

    verbs = list()
    for where in globbed:
        verb = os.path.splitext(where)[0]
        verbs.append(verb)

    stderr_print()
    stderr_print("For more information, try one of these:")
    stderr_print()

    for verb in sorted(verbs):
        print("{} --help".format(verb))

    stderr_print()


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()
