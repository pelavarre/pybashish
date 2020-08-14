#!/usr/bin/env python3

"""
usage: cal.py [--help] [-h] [YMD]

show what day it is, or was, of which year and month

positional arguments:
  YMD     print for another DD or MMDD or YYYYMMDD, akin to "cal -H YMD"

optional arguments:
  --help  show this help message and exit
  -h      stop emphasizing one day

bugs:
  starts each week on Monday, a la Linux "ncal -MC", as in England
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
    main.args = args

    today = misread_ymd_12n(args.ymd)
    two_weeks_back = today - dt.timedelta(weeks=2)
    two_weeks_ahead = today + dt.timedelta(weeks=2)

    week = when_last_12n(two_weeks_back, weekday=cal.MONDAY)

    month = week.month
    print_start_of_month(week.replace(day=1), week)
    if week.day > 1:
        print("...".center(WIDTH))

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
        print("...".center(WIDTH))

    print()


def misread_ymd_12n(ymd):
    """Guess what YYYY-MM-DD is meant, from briefer input"""

    now = dt.datetime.now()

    year = now.year
    month = now.month
    day = now.day

    if ymd:
        str_day = ymd[-2:]
        day = int(str_day)
        ymd = ymd[: -len(str_day)]
        if ymd:
            str_month = ymd[-2:]
            month = int(str_month)
            ymd = ymd[: -len(str_month)]
            if ymd:
                year = int(ymd)

    today = dt.datetime(year, month, day, 12, 00)

    return today


def print_start_of_month(month, week):
    """Print the start of a month"""

    print()
    print(month.strftime("%B %Y").center(WIDTH))
    print_day_column_names(week)


def print_day_column_names(week):
    """Print day column names:  Mo Tu We Th Fr Sa Su"""

    stdouts = list()

    sep = ""
    for days in range(7):
        ww = (week + dt.timedelta(days=days)).strftime("%a")[:2]
        stdouts.append(sep + ww)
        sep = " "

    print("".join(stdouts))


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

    print("".join(stdouts))


def week_last_day(week):
    """Find the last day of the week, given the first day"""

    end_of_week = week + dt.timedelta(days=6)

    return end_of_week


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
