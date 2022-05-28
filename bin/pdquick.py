#!/usr/bin/env python3

"""
usage: from pybashish.bin import pdquick as pdq

work with Rows of Columns a la 'import pandas as pd', but start up in 10 ms, not 500


-- example input --

git clone https://github.com/pelavarre/pybashish.git
PYTHONPATH=$PWD/.. python3 -i -c ''


import collections

Row = collections.namedtuple("Row", "a b c".split())

row_0 = Row(a=1.0, b=2.0, c=3.0)
row_1 = Row(a=1.1, b=2.11, c=3.1)
row_2 = Row(a=1.222, b=2.2, c=3.2)
row_3 = Row(a=1.3, b=2.3, c=3.3333)


from pybashish.bin import pdquick as pdq

rows = [row_0, row_1, row_2, row_3]
qf = pdq.QuickFrame(rows)

qf
qf.iloc[1:3]  # pick some Rows by Number
qf["b"]  # pick one Column by Name
qf["a c".split()]  # pick some Columns by Name
print(qf.to_string(index=False))  # print without Row Names
qf.values.tolist()  # pick out List of Rows without Row or Column Names
pdq.QuickFrame()


import pandas as pd
df = pd.DataFrame(rows)

df
df.iloc[1:3]  # pick some Rows by Number
df["b"]  # pick one Column by Name
df["a c".split()]  # pick some Columns by Name
print(df.to_string(index=False))  # print without Row Names
df.values.tolist()  # pick out List of Rows without Row or Column Names
pd.DataFrame()


-- example output --


>>> qf
 . |   a   |  b   |   c
 - | ----- | ---- | ------
 0 |   1.0 |  2.0 |    3.0
 1 |   1.1 | 2.11 |    3.1
 2 | 1.222 |  2.2 |    3.2
 3 |   1.3 |  2.3 | 3.3333
(4 rows)
>>>

>>> qf.iloc[1:3]  # pick some Rows by Number
 . |   a   |  b   |  c
 - | ----- | ---- | ---
 1 |   1.1 | 2.11 | 3.1
 2 | 1.222 |  2.2 | 3.2
(2 rows)
>>>

>>> qf["b"]  # pick one Column by Name
 . |  b
 - | ----
 0 |  2.0
 1 | 2.11
 2 |  2.2
 3 |  2.3
(4 rows)
>>>

>>> qf["a c".split()]  # pick some Columns by Name
 . |   a   |   c
 - | ----- | ------
 0 |   1.0 |    3.0
 1 |   1.1 |    3.1
 2 | 1.222 |    3.2
 3 |   1.3 | 3.3333
(4 rows)
>>>

>>> print(qf.to_string(index=False))  # print without Row Names
   a   |  b   |   c
 ----- | ---- | ------
   1.0 |  2.0 |    3.0
   1.1 | 2.11 |    3.1
 1.222 |  2.2 |    3.2
   1.3 |  2.3 | 3.3333
(4 rows)
>>>

>>> qf.values.tolist()  # pick out List of Rows without Row or Column Names
[(1.0, 2.0, 3.0), (1.1, 2.11, 3.1), (1.222, 2.2, 3.2), (1.3, 2.3, 3.3333)]
>>>

>>> pdq.QuickFrame()
 .
 -
(0 rows)
>>>


"""


import __main__
import collections
import collections.abc


# QuickFrame
# Dict of Column by Key
# QuickSeries


class QuickFrame:
    """Collect Columns by Name"""

    def __init__(self, data=None, index=None, columns=None):

        list_of_rows = list() if (data is None) else list(data)
        list_of_columns = list(zip(*list_of_rows))

        row_names = list()
        if index is not None:
            row_names = list(index)
        elif list_of_rows:
            row_names = list(str(_) for _ in range(len(list_of_rows)))

        column_names = list()
        if columns is not None:
            column_names = list(columns)
        elif list_of_rows:
            column_names = list(list_of_rows[0]._asdict().keys())

        column_by_name = dict(zip(column_names, list_of_columns))

        self.row_names = row_names
        self.column_names = column_names
        self.column_by_name = column_by_name

    def __getitem__(self, key):
        """Pick Columns"""

        if not isinstance(key, collections.abc.Iterable):

            raise KeyError(key)

        if isinstance(key, str):
            column_name = str(key)

            qf = QuickFrame()
            qf.row_names = self.row_names
            qf.column_names = [column_name]

            column_by_name = dict()
            column_by_name[column_name] = self.column_by_name[column_name]
            qf.column_by_name = column_by_name

            return qf

        column_names = list(key)

        qf = QuickFrame()
        qf.row_names = self.row_names
        qf.column_names = column_names
        for name in qf.column_names:
            qf.column_by_name[name] = self.column_by_name[name]

        return qf

    def __repr__(self):
        """Format as Lines of Chars, with straight vertical lines dividing Columns"""

        strung = self.to_string()

        return strung

    @property
    def iloc(self):
        """Index as Rows by Number, in place of Columns by Name"""

        qr = QuickRows(qf=self)

        return qr

    def to_string(self, index=True):
        """Format as Lines of Chars, with straight vertical lines dividing Columns"""

        rows = list()
        rows.append(tuple(self.column_names))
        rows.extend(zip(*self.column_by_name.values()))

        if not index:
            strung = rows_psql_format_quick(rows)
        else:
            row_names = ["."] + self.row_names
            indexed = list(((i,) + r) for (i, r) in zip(row_names, rows))
            strung = rows_psql_format_quick(rows=indexed)

        return strung

    @property
    def values(self):
        """Index as Rows by Number, in place of Columns by Name"""  # same as .iloc

        qr = QuickRows(qf=self)

        return qr


class QuickRows:
    """Collect Rows by Number"""

    def __init__(self, qf):
        self.row_names = qf.row_names
        self.column_names = qf.column_names
        self.rows = list(zip(*qf.column_by_name.values()))

    def __getitem__(self, key):
        """Pick Rows, but then Index as Columns, in place of Rows"""

        rows = self.rows.__getitem__(key)
        row_names = self.row_names.__getitem__(key)
        qf = QuickFrame(rows, columns=self.column_names, index=row_names)

        return qf

    def __repr__(self):
        """Format as Lines of Chars, with straight vertical lines dividing Columns"""

        qf = QuickFrame(self.rows, columns=self.column_names, index=self.row_names)
        strung = repr(qf)

        return strung

    def tolist(self):
        """Convert to List of Rows by Number, without Row and Column Names"""

        rows = list(self.rows)

        return rows


def rows_psql_format_quick(rows):
    """Format Rows of Cells as if fetched from PSql"""

    padded_rows = rows_str_lrjust_quick(rows)

    head = list(n.center(len(c)) for (n, c) in zip(rows[0], padded_rows[0]))
    sep = list(("-" * len(_)) for _ in padded_rows[0])
    psql_rows = [head] + [sep] + padded_rows[1:]

    chars = "\n".join((" " + " | ".join(_)).rstrip() for _ in psql_rows)
    chars += "\n({} rows)".format(len(padded_rows[1:]))

    return chars


def rows_str_lrjust_quick(rows):
    """Widen Columns to equal width, and left-justify Str's, else right-justify"""

    padded_columns = list()

    columns = list(zip(*rows))
    for column in columns:
        cells = column

        str_cells = list(str(_) for _ in cells)
        max_width = max(len(_) for _ in str_cells)

        padded_column = list()
        for (cell, str_cell) in zip(cells, str_cells):
            if isinstance(cell, str):
                padded = str_cell.ljust(max_width)
            else:
                padded = str_cell.rjust(max_width)
            padded_column.append(padded)

        padded_columns.append(padded_column)

    padded_rows = list(zip(*padded_columns))

    return padded_rows


def self_test_pdquick(pdq):
    """Test that our examples don't raise unhandled exceptions"""

    Row = collections.namedtuple("Row", "a b c".split())

    row_0 = Row(a=1.0, b=2.0, c=3.0)
    row_1 = Row(a=1.1, b=2.11, c=3.1)
    row_2 = Row(a=1.222, b=2.2, c=3.2)
    row_3 = Row(a=1.3, b=2.3, c=3.3333)

    rows = [row_0, row_1, row_2, row_3]
    qf = pdq.QuickFrame(rows)

    _ = qf
    _ = qf.iloc[1:3]  # pick some Rows by Number
    _ = qf["b"]  # pick one Column by Name
    _ = qf["a c".split()]  # pick some Columns by Name
    _ = qf.to_string(index=False)  # print without Row Names
    _ = qf.values.tolist()  # pick out List of Rows without Row or Column Names
    _ = pdq.QuickFrame()


# do run from the Command Line, when not imported into some other main module
if __name__ == "__main__":
    self_test_pdquick(pdq=__main__)
    print("pdquick.py: self-test PASSED")


# copied from:  git clone https://github.com/pelavarre/pybashish.git
