#!/usr/bin/env python3

import os
import sys
import subprocess


def main():

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    bin_bash_py = os.path.join(file_dir, "bin", "bash.py")
    ran = subprocess.run([bin_bash_py])
    sys.exit(ran.returncode)


if __name__ == "__main__":
    main()
