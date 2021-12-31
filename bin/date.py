#!/usr/bin/env python3

"""
usage: date.py [-h] [-j YMD] [--date YMD]

show what time it is now, of which day

options:
  -h, --help  show this help message and exit
  -j YMD      test a time other than now in mac tradition, such as -j 123123591970.59
  --date YMD  test a time other than now in linux tradition, such as --date '1970-12-31 23:59:59'

quirks:
  formats the date as yyyy-mm-dd hh:mm:ss.ffffff, not localised, not rounded down to :ss
  doesn't calculate difference, product, and quotient of elapsed times
  doesn't diff timestamps
  doesn't help with timezones

examples:
  date
  date -j 123123591970.59  # mac only
  date.py -j 123123591970.59123456
  date --date '1970-12-31 23:59:59.123456' +'%Y-%m-%d %H:%M:%S.%N'  # linux only
  date.py --date '1970-12-31 23:59:59.123456'
"""
# FIXME: usage: date.py [-h] [--start] [--lap] [--stop]
# FIXME:   --start     show now, and start a first lap
# FIXME:   --lap       show lap, and start next
# FIXME:   --stop      show laps, and stop last lap
# FIXME: examples:
# FIXME: date.py --start && sleep 0.1 && date.py --lap && sleep 0.2 && date.py --stop


import datetime as dt
import sys

import argdoc


# FIXME: DATE_LAPS_DIR = os.path.join(os.environ["HOME"], ".local/share/date/laps")


def main():

    args = argdoc.parse_args()

    if None not in (args.j, args.date):
        stderr_print("date.py: error: choose -j or --date, not both")
        sys.exit(2)  # exit 2 from rejecting usage

    if args.j:
        now = misread_ymdhms_mac(args.j)
    elif args.date:
        now = misread_ymdhms_linux(args.date)
    else:
        now = dt.datetime.now()

    stdout = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    print(stdout)


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def misread_ymdhms_mac(ymd):
    """Guess what YYYY-MM-DD HH:MM:SS is meant, from briefer input"""

    now = dt.datetime.now()

    syntaxes = list()
    syntaxes.append(["%d", "day"])
    syntaxes.append(["%m%d", "month day".split()])
    syntaxes.append(["%m%d%H", "month day hour".split()])
    syntaxes.append(["%m%d%H%M", "month day hour minute".split()])
    syntaxes.append(["%m%d%H%M%y", "month day hour minute year".split()])
    syntaxes.append(["%m%d%H%M%Y", "month day hour minute year".split()])
    syntaxes.append(["%m%d%H%M%y.%S", "month day hour minute year second".split()])
    syntaxes.append(["%m%d%H%M%Y.%S", "month day hour minute year second".split()])
    syntaxes.append(
        ["%m%d%H%M%y.%S%f", "month day hour minute year second microsecond".split()]
    )
    syntaxes.append(
        ["%m%d%H%M%Y.%S%f", "month day hour minute year second microsecond".split()]
    )
    # 19nn/20nn %y split varies by year maybe

    parsed = None
    for syntax in syntaxes:
        (format_, keys) = syntax
        try:
            parsed = dt.datetime.strptime(ymd, format_)
            break
        except ValueError:
            if syntax == syntaxes[-1]:
                raise

    assert parsed and keys

    today = dt.datetime(now.year, now.month, now.day, 12, 00)  # duck 2am DST etc
    replaces = {k: getattr(parsed, k) for k in keys}
    as_today = today.replace(**replaces)

    return as_today


# deffed in many files  # missing from docs.python.org
def misread_ymdhms_linux(ymd):
    """Guess what YYYY-MM-DD HH:MM:SS is meant, from briefer input"""

    now = dt.datetime.now()

    syntaxes = list()
    syntaxes.append(["%m-%d", "month day".split()])
    syntaxes.append(["%m-%d %H", "month day hour".split()])
    syntaxes.append(["%m-%d %H:%M:%S", "month day hour minute second".split()])
    syntaxes.append(
        ["%m-%d %H:%M:%S.%f", "month day hour minute second microsecond".split()]
    )
    syntaxes.append(["%y-%m-%d", "year month day".split()])
    syntaxes.append(["%y-%m-%d %H", "year month day hour".split()])
    syntaxes.append(["%y-%m-%d %H:%M", "year month day hour minute".split()])
    syntaxes.append(["%y-%m-%d %H:%M:%S", "year month day hour minute second".split()])
    syntaxes.append(
        [
            "%y-%m-%d %H:%M:%S.%f",
            "year month day hour minute second microsecond".split(),
        ]
    )
    syntaxes.append(["%Y-%m-%d", "year month day".split()])
    syntaxes.append(["%Y-%m-%d %H", "year month day hour".split()])
    syntaxes.append(["%Y-%m-%d %H:%M", "year month day hour minute".split()])
    syntaxes.append(["%Y-%m-%d %H:%M:%S", "year month day hour minute second".split()])
    syntaxes.append(
        [
            "%Y-%m-%d %H:%M:%S.%f",
            "year month day hour minute second microsecond".split(),
        ]
    )
    # 19nn/20nn %y split varies by year maybe

    parsed = None
    for syntax in syntaxes:
        (format_, keys) = syntax
        try:
            parsed = dt.datetime.strptime(ymd, format_)
            break
        except ValueError:
            if syntax == syntaxes[-1]:
                raise

    assert parsed and keys

    today = dt.datetime(now.year, now.month, now.day, 12, 00)  # duck 2am DST etc
    replaces = {k: getattr(parsed, k) for k in keys}
    as_today = today.replace(**replaces)

    return as_today


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
