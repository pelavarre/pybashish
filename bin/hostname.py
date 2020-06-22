#!/usr/bin/env python3

"""
usage: hostname.py [-h] [-s] [-f] [-v]

print name of host

optional arguments:
  -h, --help     show this help message and exit
  -s, --short    print the hostname without its domain
  -f, --fqdn     print the hostname and its domain
  -v, --verbose  say more

Note:  Fqdn falls back to Short, if need be
"""


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

    verbose_print(f"platform_node={platform_node}")
    verbose_print(f"socket_hostname={socket_hostname!r}")
    verbose_print(f"socket_fqdn={socket_fqdn}")
    verbose_print(f"socket_canonname={socket_canonname}")

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


def verbose_print(*args):

    message = "".join(str(a) for a in args)
    if main.args.verbose:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
