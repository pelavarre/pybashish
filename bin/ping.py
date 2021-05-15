# give time since start
# give time between kinds of output


_ = """

import os
import select
import subprocess
import sys


proc = subprocess.Popen(
    "ping -c 3 localhost".split(),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)


if False:

    outs, errs = proc.communicate()
    os.write(sys.stderr.fileno(), errs)
    sys.stderr.flush()
    os.write(sys.stdout.fileno(), outs)
    sys.stdout.flush()

    sys.exit()

if False:

    os.write(sys.stderr.fileno(), proc.stderr.read())
    sys.stderr.flush()
    os.write(sys.stdout.fileno(), proc.stdout.read())
    sys.stdout.flush()

    sys.exit()

while True:

    rlist = [proc.stdout, proc.stderr]
    wlist = list()
    xlist = list()
    (rlist_, wlist_, xlist_) = select.select(rlist, wlist, xlist)

    if proc.stderr in wlist_:
        while proc.stderr in wlist_:
            ch = proc.stderr.read(1)
            sys.stderr.write(ch)
            rlist = [proc.stderr]
            (rlist_, wlist_, xlist_) = select.select(rlist, wlist, xlist)
        sys.stdout.flush()

        continue

    if proc.stdout in wlist_:
        while proc.stdout in wlist_:
            ch = proc.stdout.read(1)
            sys.stderr.write(ch)
            rlist = [proc.stdout]
            (rlist_, wlist_, xlist_) = select.select(rlist, wlist, xlist)
        sys.stdout.flush()

        continue

    continue


"""


# copied from:  git clone https://github.com/pelavarre/pybashish.git
