#!/usr/bin/env python3

import os


def main():

    whats = sorted(w for w in os.listdir() if not os_stat_hidden(w))

    sep = "  "
    rows = spill_cells(whats, columns=os.get_terminal_size().columns, sep=sep)
    for row in rows:
        print(sep.join(row).rstrip())

    # FIXME: implement ls -1, ls -C, and auto by stdin is tty
    # FIXME: implement ls -alF -rt, etc
    # FIXME: implement glob args


def os_stat_hidden(what):

    hidden = what.startswith(".")  # correct at Mac and Linux, where os.name == "posix"
    return hidden


def spill_cells(cells, columns, sep):  # FIXME  # noqa C901

    cell_strs = list(str(c) for c in cells)

    no_floors = list()
    if not cell_strs:
        return no_floors

    floors = None  # FIXME: review spill_cells closely, now that it mostly works
    widths = None  # FIXME: offer tabulation with 1 to N "\t" in place of 1 to N " "

    for width in reversed(range(1, len(cell_strs) + 1)):
        height = (len(cell_strs) + width - 1) // width
        assert (width * height) >= len(cell_strs)

        shafts = list()
        for shaft_index in range(width):
            shaft = cell_strs[(shaft_index * height) :][:height]
            shafts.append(shaft)

        floors = list()
        for floor_index in range(height):
            floor = list()
            for shaft in shafts:
                if floor_index < len(shaft):
                    str_cell = shaft[floor_index]
                    floor.append(str_cell)
            floors.append(floor)

        widths = len(floors[0]) * [
            0
        ]  # FIXME: stop requiring first row to be 1 of the longest
        for floor in floors:
            for (shaft_index, str_cell,) in enumerate(floor):
                widths[shaft_index] = max(widths[shaft_index], len(str_cell))

        sep = "  "
        if (sum(widths) + (len(sep) * (len(widths) - 1))) < columns:
            break

        if width == 1:
            break

    rows = list()
    for floor in floors:
        row = list()
        for (shaft_index, str_cell,) in enumerate(floor):
            padded_str_cell = str_cell.ljust(widths[shaft_index])
            row.append(padded_str_cell)
        rows.append(row)

    return rows


if __name__ == "__main__":
    main()


# pulled from:  git clone git@github.com:pelavarre/pybashish.git
