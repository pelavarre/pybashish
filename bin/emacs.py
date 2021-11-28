#!/bin/bash -xe
cp -p $(dirname $0)/vi.py $(dirname $0)/emacs~.py
$(dirname $0)/emacs~.py "$@"
