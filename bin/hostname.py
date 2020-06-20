#!/usr/bin/env python3

import platform


def main():

    hostname = platform.node()
    print(hostname)


if __name__ == "__main__":
    main()
