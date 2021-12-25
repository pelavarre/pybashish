#!/usr/bin/env python3

"""
usage: import pyish

collect Python Def's before much developing their clients
"""


# deffed in many files  # missing from docs.python.org
def textwrap_unbreak_paragraphs(text):
    """Divide the lines of each paragraph by single spaces, not "\n" line-endings"""

    paras = list()

    para = None
    for line in (text + "\n\n").splitlines():
        if not line.strip():
            if para is not None:
                paras.append(para)
            para = None
        elif not para:
            para = line.strip()
        else:
            para += " " + line.strip()

    assert para is None

    chars = "\n".join(paras)

    return chars


# copied from:  git clone https://github.com/pelavarre/pybashish.git
