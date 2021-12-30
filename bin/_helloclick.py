#!/usr/bin/env python3

r"""
Usage: helloclick.py [OPTIONS]

  Show a small Python Click CLI with an ArgParse Epilog of Examples

Options:
  --h, --he, --hel, --help, -h  Show this message and exit.

Workflow::
  : git clone https://github.com/pelavarre/pybashish.git
  cd pybashish/
  cd bin/
  black _helloclick.py && \
      flake8 --max-line-length=999 --ignore=E203,W503 _helloclick.py && \
      echo && ./_helloclick.py -h
  : --max-line-length=999  # Black max line lengths over Flake8 max line lengths
  : --ignore=E203  # Black '[ : ]' rules over Flake8 E203 whitespace before ':'
  : --ignore=W503  # 2017 Pep 8 and Black over Flake8 W503 line break before binary op

Examples:
  _helloclick.py --h  # Show Click accepting an abbreviated long option
"""


import __main__
import argparse
import textwrap

import click


# deffed in many files  # missing from docs.python.org
def parse_main_doc(epi=None):
    """Pick the Epilog of help lines out of the Main Doc String"""

    doc = __main__.__doc__

    desc = list(_ for _ in doc.strip().splitlines() if _)[1]

    epilog = None
    if epi is not None:
        # pylint: disable=unsubscriptable-object
        epilog_at = doc.index(epi)
        epilog = textwrap.dedent(doc[epilog_at:]).strip()

    space = argparse.Namespace(desc=desc, epilog=epilog)

    return space


@click.command(
    context_settings=dict(
        help_option_names="--h --he --hel --help -h".split(),
    ),
    help=parse_main_doc().desc,
)
def main():
    main.click_main = click_main

    args = argparse.Namespace()
    print(args)


# deffed in many files  # missing from docs.python.org
def click_main(func):
    _ = func
    try:
        main()
    except SystemExit as exc:
        if exc.code == 0:
            if not hasattr(main, "click_main"):
                print()
                print(parse_main_doc(epi="Workflow").epilog)
        raise


if __name__ == "__main__":
    click_main(main)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
