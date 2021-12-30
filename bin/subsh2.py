#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
usage: subsh2.py [-h] [WORD [WORD ...]]

pass a command line through to a subshell

positional arguments:
  WORD        a word of command

optional arguments:
  -h, --help  show this help message and exit

usage as a python import:

  >>> import subsh2
  >>>

  >>> echo = subsh2.ShVerb("echo")
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
  subsh2.py echo 'Hello, Subsh2 World!'
  subsh2.py ls
"""
# FIXME: more test of:  subsh.py -- bash -i
# FIXME: think deeper into no args opening up a Bash subshell


from __future__ import print_function

import pprint
import shlex
import subprocess
import sys

import argdoc

import py3ish


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

        run = py3ish.subprocess_run(args__, **kwargs__)
        vars_ = vars(run)

        int_ = Int(run.returncode)
        int_.vars = vars_
        vars(int_).update(vars_)

        return int_


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
