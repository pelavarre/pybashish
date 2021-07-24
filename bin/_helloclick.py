#!/usr/bin/env python3

r"""
Usage: helloclick.py [OPTIONS]

Options:
  -h      Show this message and exit.
  --help  Show this message and exit.

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
  _helloclick.py -h  # Show Click interpreting a short option flag
"""


import __main__
import argparse
import sys
import textwrap

import click


@click.command()
@click.pass_context
@click.option("-h", is_flag=True, help="Show this message and exit.")
def main(ctx, h):

    if h:
        click.echo(main.get_help(ctx))
        sys.exit()

    main.click_main = click_main

    args = argparse.Namespace(h=h)
    print(args)


# deffed in many files  # missing from docs.python.org
def click_main(func):
    try:
        main()
    except SystemExit:
        if not hasattr(main, "click_main"):
            print()
            print(main_doc_epilog(epi="Workflow"))
        raise


# deffed in many files  # missing from docs.python.org
def main_doc_epilog(epi):
    """Pick the Epilog of help lines out of the Main Doc String"""

    doc = __main__.__doc__

    epilog_at = doc.index(epi)
    epilog = textwrap.dedent(doc[epilog_at:]).strip()

    return epilog


if __name__ == "__main__":
    click_main(main)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
