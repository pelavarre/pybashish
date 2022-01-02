#!/usr/bin/env python3

r"""
usage: subsh.py [-h] [WORD ...]

pass a command line through to a subshell

positional arguments:
  WORD        a word of command

options:
  -h, --help  show this help message and exit

usage as a python import:

  >>> import subsh
  >>>

  >>> echo = subsh.ShVerb("echo")
  >>>
  >>> rc = echo("Hello", "ShVerb", "World")
  >>> rc
  0
  >>> pprint.pprint(rc.vars)
  {'args': ['echo', 'Hello', 'ShVerb', 'World'],
   'returncode': 0,
   'stderr': b'',
   'stdout': b'Hello ShVerb World\n'}
  >>>

examples:
  subsh.py echo 'Hello, Subsh World!'
  subsh.py ls
"""
# FIXME: more test of:  subsh.py -- bash -i
# FIXME: think deeper into no args opening up a Bash subshell


from __future__ import print_function

import argparse
import pprint
import shlex
import subprocess
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])
    words = args.words

    verb = ShVerb()
    if words:
        verb = ShVerb(words[0])

    verbed = verb(*words[1:])

    pprint.pprint(verbed.vars)

    exit_status = verbed
    sys.exit(exit_status)


class Int(int):
    """Feel like an int, but define additional attributes"""


class ShVerb(object):
    """Feel like a Bash verb, but run inside Python"""

    def __init__(self, shline=None, **kwargs):

        self.shline = shline
        if shline is None:
            self.args = shlex.split("bash")
            self.kwargs = dict()
        else:
            self.args = shlex.split(shline)
            self.kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.kwargs.update(kwargs)

    def __call__(self, *args, **kwargs):

        args_ = self.args
        kwargs_ = self.kwargs

        args__ = args_ + list(args)

        kwargs__ = dict(kwargs_)
        kwargs__.update(kwargs)

        ran = subprocess_run(args__, **kwargs__)
        vars_ = vars(ran)

        int_ = Int(ran.returncode)
        int_.vars = vars_
        vars(int_).update(vars_)

        return int_


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to encode empty Stdin as:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(args, **kwargs)  # pylint: disable=subprocess-run-check

        return run

    # Convert KwArgs to Python 2

    kwargs2 = dict(kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    for kw in "encoding errors text universal_newlines".split():
        if kw in kwargs:
            raise NotImplementedError("keyword {}".format(kw))

    for kw in "check input".split():
        if kw in kwargs:
            del kwargs2[kw]  # drop now, catch later

    input2 = None
    if "input" in kwargs:
        input2 = kwargs["input"]

        if "stdin" in kwargs:
            raise ValueError("stdin and input arguments may not both be used.")

        assert "stdin" not in kwargs2
        kwargs2["stdin"] = subprocess.PIPE

    # Emulate the library roughly, because often good enough

    sub = subprocess.Popen(args, **kwargs2)  # pylint: disable=consider-using-with
    (stdout, stderr) = sub.communicate(input=input2)
    returncode = sub.poll()

    if "check" in kwargs:
        if returncode != 0:

            raise subprocess.CalledProcessError(
                returncode=returncode, cmd=args, output=stdout
            )

    # Succeed

    run = argparse.Namespace(
        args=args, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
