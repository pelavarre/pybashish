#!/usr/bin/env python3

r"""
usage: cspsh.py [-h] [-i]

chat of "communicating sequential processes"

optional arguments:
  -h, --help      show this help message and exit
  -i, --interact  ask more questions

csp examples:
  coin → STOP  # 1.1 X1
  coin → choc → coin → choc → STOP  # 1.1 X2
  CLOCK = (tick → CLOCK)  # 1.1.2
  CLOCK
  # CLOCK = µ X : {tick} • (tick → X)  # 1.1.2 X1
  VMS = (coin → (choc → VMS))  # 1.1.2 X2
  VMS
  CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
  CH5A
  CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4
  CH5B

examples:
  cspsh.py -i
"""


import argparse
import pprint
import re
import sys
import textwrap

import argdoc


NAME_REGEX = r"(?P<name>[A-Za-z_][0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[=()→])"
BLANKS_REGEX = r"(?P<blanks>[ ]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


def main():

    args = argdoc.parse_args()

    if not args.interact:
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("cspsh.py: warning: arguments other than -i not implemented")
        sys.exit()

    print()
    print()

    lines = list()
    if False:

        lines = (
            textwrap.dedent(
                """

                coin → STOP  # 1.1 X1
                coin → choc → coin → choc → STOP  # 1.1 X2

                CLOCK = (tick → CLOCK)  # 1.1.2
                CLOCK

                # CLOCK = µ X : {tick} • (tick → X)  # 1.1.2 X1

                VMS = (coin → (choc → VMS))  # 1.1.2 X2
                VMS

                CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
                CH5A

                CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4
                CH5B

                """
            )
            .strip()
            .splitlines()
        )

        lines.append(None)

    print("Type some line of CSP, press Return to see it run")
    print("Such as:  coin → choc → coin → choc → STOP")
    print("Press ⌃D EOF or ⌃C SIGINT or ⌃\ SIGQUIT to quit")

    while True:

        if lines:

            print("? ", lines[0])

        else:

            print("? ", end="")
            sys.stdout.flush()
            line = sys.stdin.readline()

            if not line:
                break

            lines.append(line)

        line = lines[0]
        lines = lines[1:]

        if line is None:
            break

        print()

        text = line[: line.index("#")] if ("#" in line) else line
        text = text.strip()

        if not text:
            continue

        cwt = CspWordsTaker(text.rstrip())
        try:
            cursor = cwt.take_line()
            # print()
        except Exception:
            print(cwt.taker.shards)
            raise

        source = cursor.format_source()
        print(source)
        print()

        top = argparse.Namespace()
        vars(top)[type(cursor).__name__] = cursor
        if False:
            pprint.pprint(namespace_to_dict(cursor))
            print()

        SourceGraph.reinit()
        cursor.run()

        print()
        print()


class SourceGraph(argparse.Namespace):

    process_by_name = dict()

    def format_source(self):
        chars = " ".join(_.format_source() for _ in vars(self).values())
        return chars

    @classmethod
    def reinit(cls):

        cls.gotos = list()

    @classmethod
    def run_to(cls, name):

        count = cls.gotos.count(name)
        cls.gotos.append(name)

        if name in cls.process_by_name:
            process = cls.process_by_name[name]
            if count < 2:
                return process

        print(name)


class ProcessCall(SourceGraph):
    def run(self):
        name = self.process_name.name
        cursor = SourceGraph.run_to(name)
        if cursor:
            cursor.run()


class ProcessDefinition(SourceGraph):
    def run(self):
        name = self.process_name.name
        SourceGraph.process_by_name[name] = self.open_process_close


class OpenProcessClose(SourceGraph):
    def run(self):
        self.runnable.run()


class EventThenProcess(SourceGraph):
    def run(self):
        print(self.event_name.name)
        self.runnable.run()


class CspMark(SourceGraph):
    def format_source(self):
        chars = self.mark
        return chars


class CspName(SourceGraph):
    def format_source(self):
        chars = self.name
        return chars


class CspWordsTaker(argparse.Namespace):
    """Parse a source line of CSP"""

    def __init__(self, line):

        self.taker = ShardsTaker()

        self.give_line(line)

    def give_line(self, line):
        """Give a source line as its non-blank words"""

        taker = self.taker

        items = list()
        while line:

            match = re.match(SHARDS_REGEX, string=line)
            try:
                assert match
            except AssertionError:
                print(repr(line))
                raise

            match_items = match.groupdict().items()
            match_items = list((k, v,) for (k, v,) in match_items if v)

            assert len(match_items) == 1
            match_item = match_items[0]

            assert line.startswith(match_item[-1])
            line = line[len(match_item[-1]) :]

            items.append(match_item)

        words = [_ for _ in items if _[0] != "blanks"]
        # print(words)
        # print()

        taker.give_shards(words)

    def take_line(self):

        taker = self.taker

        words = taker.peek_many_shards_else_none(2)
        if words and (words[1][1] == "="):
            space = self.take_process_definition()
        elif words and (words[1][1] == "→"):
            space = self.take_many_events_then_process()
        else:
            space = self.take_process_call()

        taker.take_end_shard()

        return space

    def take_process_call(self):

        process_name = self.take_process_name()

        space = ProcessCall(process_name=process_name)
        return space

    def take_process_definition(self):

        process_name = self.take_process_name()
        equals = self.take_mark("=")
        open_process_close = self.take_open_process_close("(", ")")

        space = ProcessDefinition(
            process_name=process_name,
            equals=equals,
            open_process_close=open_process_close,
        )
        return space

    def take_open_process_close(self, after_mark, upto_mark):

        open_after = self.take_mark(after_mark)
        runnable = self.take_many_events_then_process()
        upto_close = self.take_mark(upto_mark)

        space = OpenProcessClose(
            open_after=open_after, runnable=runnable, upto_close=upto_close,
        )
        return space

    def take_many_events_then_process(self):

        taker = self.taker

        event_names = list()
        while True:

            words = taker.peek_many_shards_else_none(2)
            if not words:
                break
            if words[1][-1] != "→":
                break

            event_name = self.take_event_name()
            mark = self.take_mark("→")

            event_names.append(event_name)

        word = taker.peek_one_shard()
        if word[-1] == "(":
            runnable = self.take_open_process_close(after_mark="(", upto_mark=")")
        else:
            runnable = self.take_process_call()

        for event_name in reversed(event_names):
            runnable = EventThenProcess(
                event_name=event_name, then_mark=mark, runnable=runnable
            )

        return runnable

    def take_mark(self, mark):

        taker = self.taker

        word = taker.peek_one_shard()

        assert word[0] == "mark"

        assert word[-1] == mark
        taker.take_one_shard()

        space = CspMark(mark=mark)
        return space

    def take_event_name(self):

        taker = self.taker

        word = taker.peek_one_shard()

        assert word[0] == "name"
        name = word[-1]

        assert name == name.lower()
        taker.take_one_shard()

        space = CspName(name=name)
        return space

    def take_process_name(self):

        taker = self.taker

        word = taker.peek_one_shard()

        assert word[0] == "name"
        name = word[-1]

        assert name == name.upper()
        taker.take_one_shard()

        space = CspName(name=name)
        return space


# deffed in many files  # missing from docs.python.org
class ShardsTaker(argparse.Namespace):
    """Walk once thru source chars, as split

    Define "take" to mean require and consume
    Define "peek" to mean look ahead
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_sourcelines(self, chars):
        """Give chars, split into lines, but drop the trailing whitespace from each line"""

        lines = chars.splitlines()
        lines = list(_.rstrip() for _ in lines)

        self.give_shards(shards=lines)

    def give_shards(self, shards):
        """Give shards"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Consume the next shard, without returning it"""

        # print("take_one_shard", self.shards[0])

        self.shards = self.shards[1:]

    def peek_one_shard(self):
        """Return the next shard, without consuming it"""

        return self.shards[0]

    def peek_many_shards_else_none(self, many):
        """Return the next few shards, without consuming them"""

        some = self.shards[:many]
        if len(some) == many:
            return some

    def peek_more(self):
        """Return True while shards remain"""

        more = bool(self.shards)
        return more

    def take_end_shard(self):
        """Do nothing if all shards consumed, else crash"""

        assert not self.peek_more()

    def accept_blank_shards(self):
        """Discard zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():
                break
            self.take_one_shard()

    def peek_strung_remains(self):
        """Return the remaining shards strung together """

        strung_remains = "".join(self.shards)
        return strung_remains

    def peek_one_strung_word(self):
        """Return the first word of the remaining shards strung together"""

        strung_remains = "".join(self.shards)

        words = strung_remains.split()
        assert words

        word = words[0]

        return word

    def peek_some_shards(self, hopes):
        """Return a copy of the hopes strung together, if and only if available to be taken now"""

        shards = self.shards

        if len(shards) < len(hopes):
            return None

        for (shard, hope,) in zip(shards, hopes):
            if shard != hope:
                return None

        strung = "".join(hopes)
        return strung

    def take_counted_shards(self, count):
        """Take a number of shards"""

        if count:
            self.shards = self.shards[count:]


def namespace_to_dict(space):

    v_by_k = dict(vars(space))
    for (k, v,) in v_by_k.items():
        if isinstance(v_by_k[k], argparse.Namespace):
            v_by_k[k] = namespace_to_dict(v)  # recursive

    return v_by_k


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()
