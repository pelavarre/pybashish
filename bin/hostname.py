#!/usr/bin/env python3

"""
usage: hostname.py [-h] [-s] [-f] [-v]

print name of host

options:
  -h, --help     show this help message and exit
  -s, --short    print the hostname without its domain (default: True)
  -f, --fqdn     print the hostname and its domain
  -v, --verbose  say more

quirks:
  Fqdn falls back to Short, if need be, and still returns exit status zero

examples:
  hostname
  hostname -f
"""


from __future__ import print_function

import collections
import platform
import socket
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    main.args = args

    platform_node = platform.node()
    socket_hostname = socket.gethostname()
    socket_fqdn = socket.getfqdn()
    socket_canonname = calc_socket_canonname_else_none(socket_hostname)

    verbose_print("platform_node={}".format(platform_node))
    verbose_print("socket_hostname={!r}".format(socket_hostname))
    verbose_print("socket_fqdn={}".format(socket_fqdn))
    verbose_print("socket_canonname={}".format(socket_canonname))

    assert "." not in platform_node
    assert "." not in socket_hostname
    assert platform_node == socket_hostname

    if args.fqdn:
        print(socket_fqdn)
    else:
        print(platform_node)


def calc_socket_canonname_else_none(socket_hostname):

    SocketResolution = collections.namedtuple(
        "SocketResolution", "family, type, proto, canonname, sockaddr".split(", ")
    )  # aka:  af, socktype, proto, canonname, sa

    resolutions = None
    try:
        resolutions = socket.getaddrinfo(
            socket_hostname, port=0, flags=socket.AI_CANONNAME
        )
    except socket.gaierror:
        return None

    resolution = resolutions[0]  # forward the first result, silently drop the rest
    resolution = SocketResolution(*resolution)
    canonname = resolution.canonname

    return canonname


#
# Define some Python idioms
#


# FIXME: demo is_numeric_hostname
# deffed in many files  # missing from docs.python.org
def is_numeric_hostname(hostname):
    """Say if a hostname feels much like IPv6 hextets or IPv4 octets"""

    numeric = False
    if hostname.count(":"):
        if not (set(hostname.lower()) - set("0123456789abcdef:")):
            numeric = True
    if hostname.count("."):
        if not (set(hostname.lower()) - set("0123456789.")):
            numeric = True

    return numeric


# deffed in many files  # missing from docs.python.org
def verbose_print(*args):
    sys.stdout.flush()
    if main.args.verbose:
        print(*args, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
