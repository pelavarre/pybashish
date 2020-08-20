#!/usr/bin/env python3

r"""
usage: cspsh.py [-h] [-f] [-i] [-q] [-v]

chat of "communicating sequential processes"

optional arguments:
  -h, --help      show this help message and exit
  -f, --force     ask less questions
  -i, --interact  ask more questions
  -q, --quiet     say less
  -v, --verbose   say more

csp examples:
  tick → STOP
  tick → tick → STOP
  CLOCK = (tick → CLOCK)
  CLOCK

examples:
  cspsh.py -i
"""
# FIXME: limit the trace of ProcessWithSuch to its alphabet


import argparse
import re
import sys
import textwrap

import argdoc


NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[():={}µ•→])"
BLANKS_REGEX = r"(?P<blanks>[ ]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


OPEN_MARK_REGEX = r"[(\[{]"
CLOSE_MARK_REGEX = r"[)\]}]"


def main():

    args = argdoc.parse_args()
    main.args = args

    if all((_ is None) for _ in vars(args).values()):
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("cspsh.py: error: choose --force or --interact")
        sys.exit(2)  # exit 2 from rejecting usage

    verbose_print()
    verbose_print()

    lines = list()
    if args.force:

        lines = (
            textwrap.dedent(
                """

                # test examples from the help lines

                tick → STOP
                tick → tick → STOP
                CLOCK = (tick → CLOCK)
                CLOCK

                # test more examples from us

                HER.WALTZ = (
                    her.right.back → her.left.hook.back → her.right.close →
                    her.left.forward → her.right.hook.forward → her.left.close
                    )
                HIS.WALTZ = (
                    his.left.forward → his.right.hook.forward → his.left.close →
                    his.right.back → his.left.hook.back → his.right.close
                )
                HER.WALTZ
                HIS.WALTZ

                # test examples from the textbook

                coin → STOP  # 1.1 X1
                coin → choc → coin → choc → STOP  # 1.1 X2

                CLOCK = (tick → CLOCK)  # 1.1.2
                CLOCK

                CLOCK = µ X : {tick} • (tick → X)  # 1.1.2 X1
                CLOCK

                VMS = (coin → (choc → VMS))  # 1.1.2 X2
                VMS

                CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
                CH5A

                CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4
                CH5B

                """
            )
            .strip()
            .splitlines(keepends=True)
        )

        lines.append("")

    if not args.quiet:
        stderr_print("Type some line of CSP, press Return to see it run")
        stderr_print("Such as:  coin → choc → coin → choc → STOP")
        stderr_print(r"Press ⌃D EOF or ⌃C SIGINT or ⌃\ SIGQUIT to quit")

    while True:

        line = pull_line(lines, stdin=sys.stdin)

        if not line:
            break

        ccl = CspCommandLine()
        ccl.give_one_sourceline(line)
        try:
            worker = ccl.take_one_worker(ccl.taker)
        except Exception:
            stderr_print(ccl.taker.shards)
            raise

        verbose_print("+", worker)
        verbose_print()

        top = argparse.Namespace()
        vars(top)[type(worker).__name__] = worker

        worker()

        verbose_print()
        verbose_print()


def pull_line(lines, stdin):

    line = ""
    while True:

        open_marks = csp_pick_open_marks(line)
        if line and not open_marks:
            break

        prompt = "{} > ".format(open_marks) if line else "? "

        if lines:

            stderr_print(prompt + lines[0])

        else:

            stderr_print(prompt, end="")
            sys.stdout.flush()
            more = stdin.readline()
            if not more:
                stderr_print()

            lines.append(more)

        more = lines[0]
        lines[:] = lines[1:]

        if not more:
            assert not lines
            break

        line += "\n"
        line += more

    return line


def csp_pick_open_marks(string):
    """
    List the marks not yet closed

    Count the ) ] } marks as closing the ( [ { marks

    Count the other marks (such as = µ • →) as closed by the next name
    """

    # To list which marks are left open, if any:  open marks, and close the last mark

    pairs = list()
    for ch in string:

        if re.match(r"^{}$".format(OPEN_MARK_REGEX), string=ch):

            open_mark = ch
            close_mark = CLOSE_MARK_REGEX[OPEN_MARK_REGEX.index(ch)]
            assert (open_mark + close_mark) in "() [] {}".split()

            pair = (
                open_mark,
                close_mark,
            )
            pairs.append(pair)

        elif pairs and (ch == pairs[-1][-1]):

            pairs = pairs[:-1]

    # Count the last mark as an open mark if no name follows it

    open_marks = "".join(_[0] for _ in pairs)
    chars = string.rstrip()
    if chars:
        last_mark = chars[-1]

        if re.match(r"^{}$".format(MARK_REGEX), string=last_mark):
            if not re.match(r"^{}$".format(OPEN_MARK_REGEX), string=last_mark):
                if not re.match(r"^{}$".format(CLOSE_MARK_REGEX), string=last_mark):

                    open_marks += last_mark

    return open_marks


class CspWorker(argparse.Namespace):
    """Work through a process"""

    def __call__(self):
        if self.worker:
            self.worker()

    def __repr__(self):
        return object.__repr__(self)

    def __str__(self):
        chars = "".join(str(_) for _ in vars(self).values()).strip()
        chars = chars.replace("  ", " ")
        return chars


class CspCommandLine(CspWorker):
    """Work through a line of source code"""

    top_worker = None

    processes_by_name = dict()

    def __init__(self, **kwargs):
        CspWorker.__init__(self, **kwargs)

        self.gotos = list()
        self.taker = ShardsTaker()

        CspCommandLine.top_worker = self

    def __str__(self):
        return str(self.worker)

    def call_named_process(self, name, process):
        assert name and process

        self.gotos.append(name)
        count = self.gotos.count(name)

        if count > 3:
            print(name, "...")
        else:
            process()

    @classmethod
    def take_one_worker(cls, taker):

        worker = None
        if taker.peek_more():

            words = taker.peek_some_shards(2)
            if words[-1] and (words[1][1] == "="):
                worker = DefineProcess.take_one_worker(taker)
            else:
                worker = Process.take_one_worker(taker)

            taker.take_beyond_shards()

        worker = CspCommandLine(worker=worker)
        return worker

    def give_one_sourceline(self, line):

        taker = self.taker

        text = line[: line.index("#")] if ("#" in line) else line

        text = text.strip()

        tabsize_8 = 8
        text = text.expandtabs(tabsize_8)  # replace "\t" with between 1 and 8 " "
        text = " ".join(text.splitlines())  # replace "\r\n" or "\r" or "\n" with " "
        text = text.rstrip()

        items = list()
        while text:

            match = re.match(SHARDS_REGEX, string=text)
            try:
                assert match
            except AssertionError:
                stderr_print(repr(text))
                raise

            match_items = match.groupdict().items()
            match_items = list((k, v,) for (k, v,) in match_items if v)

            assert len(match_items) == 1
            match_item = match_items[0]

            assert text.startswith(match_item[-1])
            text = text[len(match_item[-1]) :]

            items.append(match_item)

        words = [_ for _ in items if _[0] != "blanks"]

        taker.give_shards(words)


class Process(CspWorker):
    """Work through a process"""

    @classmethod
    def take_one_worker(cls, taker):

        words = taker.peek_some_shards(2)
        if words[-1] and (words[0][-1] == "("):
            worker = OpenProcessClose.take_one_worker(
                taker, after_mark="(", upto_mark=")"
            )
        elif words[-1] and (words[1][-1] == "→"):
            worker = EventThenProcess.take_one_worker(taker)
        else:
            worker = ProcessCaller.take_one_worker(taker)

        worker = Process(worker=worker)
        return worker


class OpenProcessClose(CspWorker):
    """Define a process as the work after a "(" mark and before a ")" mark"""

    @classmethod
    def take_one_worker(self, taker, after_mark, upto_mark):

        open_after = CspOpenMark.take_one_worker(taker, after_mark)
        worker = Process.take_one_worker(taker)
        upto_close = CspCloseMark.take_one_worker(taker, upto_mark)

        worker = OpenProcessClose(
            open_after=open_after, worker=worker, upto_close=upto_close,
        )
        return worker


class EventThenProcess(CspWorker):
    """Work through one (or more) events and then a process"""

    def __call__(self):
        name = self.event_name.name
        assert name
        print(name)
        self.worker()

    @classmethod
    def take_one_worker(self, taker):

        event_names = list()
        then_marks = list()
        while True:

            words = taker.peek_some_shards(2)
            if not words[-1]:
                break
            if words[1][-1] != "→":
                break

            event_name = CspName.take_one_worker(taker)
            then_mark = CspMark.take_one_worker(taker, "→")

            event_names.append(event_name)
            then_marks.append(then_mark)

        word = taker.peek_one_shard()
        if word[-1] == "(":
            worker = OpenProcessClose.take_one_worker(
                taker, after_mark="(", upto_mark=")"
            )
        else:
            worker = Process.take_one_worker(taker)

        pairs = zip(event_names, then_marks)
        for (event_name, then_mark,) in reversed(list(pairs)):
            worker = EventThenProcess(
                event_name=event_name, then_mark=then_mark, worker=worker
            )

        return worker


class ProcessCaller(CspWorker):
    """Call a process by name"""

    def __str__(self):
        return str(self.source)

    def __call__(self):

        source = self.source
        name = self.process_name.name
        process = self.process

        if not source:
            process()
        elif process:
            CspCommandLine.top_worker.call_named_process(name, process)
        else:
            print(name)

    @classmethod
    def take_one_worker(cls, taker):

        process_name = CspName.take_one_worker(taker)
        source = process_name.name

        process = None
        process_name = process_name
        if process_name.name in CspCommandLine.processes_by_name:
            process = CspCommandLine.processes_by_name[process_name.name]
            process_name = process.process_name

        worker = ProcessCaller(
            source=source, process_name=process_name, process=process
        )
        return worker


class DefineProcess(CspWorker):
    """Name a process to call"""

    def __call__(self):
        pass

    @classmethod
    def take_one_worker(self, taker):

        process_name = CspName.take_one_worker(taker)
        is_mark = CspMark.take_one_worker(taker, "=")

        process_caller = ProcessCaller(source=None, process_name=process_name)
        CspCommandLine.processes_by_name[process_name.name] = process_caller

        word = taker.peek_one_shard()
        if word[-1] != "(":
            body = ProcessWithSuch.take_one_worker(taker, process_caller)
        else:
            body = OpenProcessClose.take_one_worker(
                taker, after_mark="(", upto_mark=")"
            )
            process_caller.process = body

        assert CspCommandLine.processes_by_name[process_name.name] == process_caller

        worker = DefineProcess(process_name=process_name, is_mark=is_mark, body=body)
        return worker


class ProcessWithSuch(CspWorker):
    """Give a process a local name and an alphabet"""

    def __call__(self):
        assert False

    @classmethod
    def take_one_worker(self, taker, process_caller):

        the_process_mark = CspMark.take_one_worker(taker, "µ")
        process_name = CspName.take_one_worker(taker)

        assert process_name.name not in CspCommandLine.processes_by_name.keys()
        CspCommandLine.processes_by_name[process_name.name] = process_caller

        with_alphabet_mark = CspMark.take_one_worker(taker, ":")
        alphabet = CspAlphabet.take_one_worker(taker, after_mark="{", upto_mark="}")

        such_that_mark = CspMark.take_one_worker(taker, "•")
        process = Process.take_one_worker(taker)

        assert CspCommandLine.processes_by_name[process_name.name] == process_caller
        process_caller.process = process
        del CspCommandLine.processes_by_name[process_name.name]

        worker = ProcessWithSuch(
            the_process_mark=the_process_mark,
            process_name=process_name,
            with_alphabet_mark=with_alphabet_mark,
            alphabet=alphabet,
            such_that_mark=such_that_mark,
            process=process,
        )
        return worker


class CspAlphabet(CspWorker):
    """Collect events into an alphabet"""

    def __call__(self):
        assert False

    def __str__(self):

        str_pairs = zip(
            list(str(_) for _ in self.event_names[:-1]),
            list(str(_) for _ in self.comma_marks),
        )
        str_event_name = str(self.event_names[-1])

        chars = ""
        chars += str(self.open_after)
        chars += " ".join(list("{}{}".format(*_) for _ in str_pairs) + [str_event_name])
        chars += str(self.upto_close)

        return chars

    @classmethod
    def take_one_worker(self, taker, after_mark, upto_mark):

        open_after = CspOpenMark.take_one_worker(taker, after_mark)

        event_names = list()
        comma_marks = list()
        while True:

            words = taker.peek_some_shards(2)
            if not words:
                break
            if words[1][-1] != ",":
                break

            event_name = CspName.take_one_worker(taker)
            comma_mark = CspMark.take_one_worker(taker, ",")

            event_names.append(event_name)
            comma_marks.append(comma_mark)

        event_name = CspName.take_one_worker(taker)
        event_names.append(event_name)

        upto_close = CspCloseMark.take_one_worker(taker, upto_mark)
        worker = CspAlphabet(
            open_after=open_after,
            event_names=event_names,
            comma_marks=comma_marks,
            upto_close=upto_close,
        )
        return worker


class CspName(CspWorker):
    """Capture a fragment of source that names something else"""

    @classmethod
    def take_one_worker(self, taker):

        word = taker.peek_one_shard()
        assert word[0] == "name"
        name = word[-1]
        taker.take_one_shard()

        worker = CspName(name=name)
        return worker


class CspMark(CspWorker):
    """Capture a fragment of source that names itself"""

    def __str__(self):
        chars = " {} ".format(self.mark)
        return chars

    @classmethod
    def take_one_mark(self, taker, mark):
        word = taker.peek_one_shard()
        assert word[0] == "mark"
        assert word[-1] == mark
        taker.take_one_shard()

    @classmethod
    def take_one_worker(self, taker, mark):

        CspMark.take_one_mark(taker, mark=mark)

        worker = CspMark(mark=mark)
        return worker


class CspOpenMark(CspMark):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = " {}".format(self.mark)  # no blank inside on the right
        return chars

    @classmethod
    def take_one_worker(self, taker, mark):

        CspMark.take_one_mark(taker, mark=mark)

        worker = CspOpenMark(mark=mark)
        return worker


class CspCloseMark(CspMark):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = "{} ".format(self.mark)  # no blank inside on the left
        return chars

    @classmethod
    def take_one_worker(self, taker, mark):

        CspMark.take_one_mark(taker, mark=mark)

        worker = CspCloseMark(mark=mark)
        return worker


#
# Divide a source line into words
#

# deffed in many files  # missing from docs.python.org
class ShardsTaker(argparse.Namespace):
    """
    Walk once thru source chars, as split

    Define "take" to mean require and consume
    Define "peek" to mean look ahead if present, else into an infinite stream of None's
    Define "accept" to mean take if given, and don't take if not given
    """

    def __init__(self, shards=()):
        self.shards = list(shards)  # the shards being peeked, taken, and accepted

    def give_shards(self, shards):
        """Give shards"""

        self.shards.extend(shards)

    def take_one_shard(self):
        """Consume the next shard, without returning it"""

        self.shards = self.shards[1:]

    def take_some_shards(self, count):
        """Take a number of shards"""

        self.shards = self.shards[count:]

    def peek_one_shard(self):
        """Return the next shard, without consuming it"""

        if self.shards:  # infinitely many None's past the end
            return self.shards[0]

    def peek_some_shards(self, count):
        """Return the next few shards, without consuming them"""

        nones = count * [None]
        some = (self.shards[:count] + nones)[:count]

        return some

    def peek_equal_shards(self, hopes):
        """Return the next few"""

        some = self.peek_some_shards(len(hopes))
        if some == list(hopes):
            return True

    def take_beyond_shards(self):
        """Do nothing if all shards consumed, else mystically crash"""

        assert not self.peek_more()

    def peek_more(self):
        """Return True while shards remain"""

        more = bool(self.shards)
        return more

    def peek_more_shards(self):
        """List remaining shards """

        more_shards = list(self.shards)
        return more_shards

    def accept_blank_shards(self):
        """Discard zero or more blank shards"""

        while self.peek_more():
            shard = self.peek_one_shard()
            if shard.strip():
                break
            self.take_one_shard()

    def peek_upto_blank_shard(self):
        """Peek the non-blank shards here, if any"""

        shards = list()
        for shard in self.shards:
            if not shard.strip():
                break
            shards.append(shard)

        return shards


#
# Copy-paste some "def"s from elsewhere
#


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # for when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
def verbose_print(*args, **kwargs):
    sys.stdout.flush()
    if main.args.verbose:
        print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # for when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()
