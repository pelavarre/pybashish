#!/usr/bin/env python3

"""
usage: cal.py [--help] [-h] [YMD]

show what day it is, or was, of which year and month

positional arguments:
  YMD     print for another %d|%m%d|%y%m%d|%Y%m%d, a la bash "cal -H yyyy-mm-dd"

optional arguments:
  --help  show this help message and exit
  -h      stop coloring one day (default: color when stdout isatty)

bugs:
  starts each week on Monday, a la linux "ncal -MC", as in England
  doesn't pad every line with two blanks at the end
  doesn't fit well into a x25x80 terminal

examples:
  cal.py  # show the two weeks behind and ahead of today
  cal.py 101  # show the start of this year
  cal.py 1231  # show the end of this year
  cal.py 19700101  # show the start of 1970
"""
# FIXME: default to .us -S Sunday weeks, option .uk -M Monday weeks
# FIXME: ~ cal  # inside "grep.py", for the England -M Monday weeks
# FIXME: "uk" and "us" as hints on the command line


import calendar as cal
import datetime as dt
import sys

import argdoc


WIDTH = 7 * len("dd ") - 1


def main():
    """Interpret a Cal command line"""

    args = argdoc.parse_args()
    args.color = sys.stdout.isatty() and not args.h
    # FIXME: make --color=yes easy to say when not isatty

    main.args = args

    now = dt.datetime.now()
    today = dt.datetime(now.year, now.month, now.day, 12, 00)  # duck 2am DST etc
    if args.ymd:
        today = misread_ymd_12n(args.ymd)

    two_weeks_back = today - dt.timedelta(weeks=2)
    two_weeks_ahead = today + dt.timedelta(weeks=2)

    week = when_last_12n(two_weeks_back, weekday=cal.MONDAY)

    month = week.month
    print_start_of_month(week.replace(day=1), week)
    if week.day > 1:
        print_rstripped("...".center(WIDTH))

    while week < two_weeks_ahead:
        end_of_week = week_last_day(week)

        if month != week.month:
            month = week.month
            print_start_of_month(week.replace(day=1), week=week)

        print_week_in_month(week, month=month, today=today)

        if end_of_week.month != month:
            month = end_of_week.month
            print_start_of_month(end_of_week.replace(day=1), week=week)

            print_week_in_month(week, month=month, today=today)

        week += dt.timedelta(weeks=1)

    if month == (end_of_week + dt.timedelta(days=1)).month:
        print_rstripped("...".center(WIDTH))

    print()


def print_start_of_month(month, week):
    """Print the start of a month"""

    print()
    print_rstripped(month.strftime("%B %Y").center(WIDTH))
    print_day_column_names(week)


def print_day_column_names(week):
    """Print day column names:  Mo Tu We Th Fr Sa Su"""

    stdouts = list()

    sep = ""
    for days in range(7):
        ww = (week + dt.timedelta(days=days)).strftime("%a")[:2]
        stdouts.append(sep + ww)
        sep = " "

    print_rstripped("".join(stdouts))  # rstrip unneeded


def print_week_in_month(week, month, today):
    """Print the days of this week found inside this month"""

    bold = "\x1b[1m"  # [1m Bold
    underline = "\x1b[4m"  # [4m Underline
    plain = "\x1b[0m"  # [0m Plain

    wild = (bold + underline) if main.args.color else ""
    calm = plain if main.args.color else ""

    stdouts = list()

    sep = ""
    for days in range(7):
        printing = week + dt.timedelta(days=days)
        if printing.month == month:
            pad = (len("  ") - len(str(printing.day))) * " "
            if (printing.month, printing.day,) == (today.month, today.day,):
                stdout = "{}{}{}{}{}".format(sep, pad, wild, printing.day, calm)
            else:
                stdout = "{}{:2d}".format(sep, printing.day)
        else:
            stdout = "{}  ".format(sep)
        stdouts.append(stdout)
        sep = " "

    print_rstripped("".join(stdouts).rstrip())


def week_last_day(week):
    """Find the last day of the week, given the first day"""

    end_of_week = week + dt.timedelta(days=6)

    return end_of_week


#
# Git-track some Python idioms here
#


# deffed in many files  # missing from docs.python.org
def misread_ymd_12n(ymd):
    """Guess what YYYY-MM-DD 12:00:00 is meant, from briefer input"""

    now = dt.datetime.now()

    syntaxes = list()
    syntaxes.append(["%d", "day"])
    syntaxes.append(["%m%d", "month day".split()])
    syntaxes.append(["%y%m%d", "year month day".split()])
    syntaxes.append(["%Y%m%d", "year month day".split()])
    # 19nn/20nn %y split varies by year maybe

    parsed = None
    for syntax in syntaxes:
        (format_, keys,) = syntax
        try:
            parsed = dt.datetime.strptime(ymd, format_)
            break
        except ValueError:
            if syntax == syntaxes[-1]:
                raise

    assert parsed and keys

    today = dt.datetime(now.year, now.month, now.day, 12, 00)  # duck 2am DST etc
    replaces = {k: getattr(parsed, k) for k in keys}
    asif_today = today.replace(**replaces)

    return asif_today


# deffed in many files  # missing from docs.python.org
def print_rstripped(*args):
    """Like print, but end lines quickly:  don't pad with spaces past the end"""

    reps = "".join(str(_) for _ in args)
    print(reps.rstrip())


# deffed in many files  # missing from docs.python.org
def when_last_12n(today, weekday):
    """Find the last 12noon at today or before, but on a chosen weekday"""

    when = dt.datetime(today.year, today.month, today.day, 12, 00)
    while True:  # FIXME: solve correctly, but without loop
        if when <= today:
            if when.weekday() == weekday:
                break
        when -= dt.timedelta(days=1)

    return when


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
