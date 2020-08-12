#!/usr/bin/env python3

"""
usage: date.py [-h]

show what time it is now, of which day

optional arguments:
  -h, --help  show this help message and exit

bugs:
  formats the date as yyyy-mm-dd hh:mm:ss.ffffff, not localised, not rounded down to :ss
  doesn't calculate difference, product, and quotient of elapsed times
  doesn't diff timestamps
  doesn't help with timezones

examples:
  date
"""
# FIXME: usage: date.py [-h] [--start] [--lap] [--stop]
# FIXME:   --start     show now, and start a first lap
# FIXME:   --lap       show lap, and start next
# FIXME:   --stop      show laps, and stop last lap
# FIXME: examples:
# FIXME: date.py --start && sleep 0.1 && date.py --lap && sleep 0.2 && date.py --stop

import datetime as dt

import argdoc


# FIXME: DATE_LAPS_DIR = os.path.join(os.environ["HOME"], ".local/share/date/laps")


def main():
    _ = argdoc.parse_args()

    now = dt.datetime.now()
    stdout = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    print(stdout)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
