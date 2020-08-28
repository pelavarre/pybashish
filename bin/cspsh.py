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
  cspsh.py -i  # chat out one result at a time
  cspsh.py -f  # dump a large pile of results
"""
# FIXME: limit the trace of ProcessWithSuch to its alphabet
# FIXME: clean up the echo to interleave prompt and input, for paste of multiple input lines


import argparse
import collections
import re
import sys
import textwrap

import argdoc


CspWord = collections.namedtuple("CspWord", "kind, chars".split(", "))


NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[():={|}µ•→⟨⟩])"
BLANKS_REGEX = r"(?P<blanks>[ ]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


OPEN_MARK_REGEX = r"[(\[{⟨]"
CLOSE_MARK_REGEX = r"[)\]}⟩]"


class CspError(Exception):
    pass


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

                #
                # test examples from the help lines
                #

                tick → STOP
                tick → tick → STOP
                CLOCK = (tick → CLOCK)
                CLOCK


                #
                # test more examples from us
                #

                HER.WALTZ = (
                    her.right.back → her.left.hook.back → her.right.close →
                    her.left.forward → her.right.hook.forward → her.left.close →
                    HER.WALTZ)
                HIS.WALTZ = (
                    his.left.forward → his.right.hook.forward → his.left.close →
                    his.right.back → his.left.hook.back → his.right.close →
                    HIS.WALTZ)
                HER.WALTZ
                HIS.WALTZ


                #
                # test examples from the textbook
                #


                # 1.1.1 Prefix

                coin → STOP  # 1.1.1 X1
                coin → choc → coin → choc → STOP  # 1.1.1 X2

                CTR = (right → up → right → right → STOP)  # 1.1.1 X3
                CTR
                x → y  # meaningless per process name 'y' is not upper case 'Y'
                P → Q  # meaningless per event name 'P' is not lower case 'p'
                x → (y → STOP)


                # 1.1.2 Recursion

                CLOCK = (tick → CLOCK)
                CLOCK

                CLOCK = (tick → tick → tick → CLOCK)
                CLOCK

                CLOCK = µ X : {tick} • (tick → X)  # 1.1.2 X1
                CLOCK

                VMS = (coin → (choc → VMS))  # 1.1.2 X2
                VMS

                CH5A = (in5p → out2p → out1p → out2p → CH5A)  # 1.1.2 X3
                CH5A

                CH5B = (in5p → out1p → out1p → out1p → out2p → CH5B)  # 1.1.2 X4
                CH5B


                # 1.1.3 Choice

                (up → STOP | right → right → up → STOP)  # 1.1.3 X1

                CH5C = in5p → (  # 1.1.3 X2
                    out1p → out1p → out1p → out2p → CH5C |
                    out2p → out1p → out2p → CH5C)
                CH5C

                (x → P | y → Q)

                VMCT = µ X • (coin → (choc → X | toffee → X))  # 1.1.3 X3
                VMCT

                VMC = (in2p → (large → VMC |  # 1.1.3 X4
                               small → out1p → VMC) |
                       in1p → (small → VMC |
                               in1p → (large → VMC |
                                       in1p → STOP)))
                VMC

                VMCRED = µ X • (coin → choc → X | choc → coin → X)  # 1.1.3 X5
                VMCRED

                VMS2 = (coin → VMCRED)  # 1.1.3 X6
                VMS2

                COPYBIT = µ X • (in.0 → out.0 → X |  # 1.1.3 X7
                                 in.1 → out.1 → X)
                COPYBIT

                (x → P | y → Q | z → R)
                (x → P | x → Q)  # meaningless per choices not distinct: ['x', 'x']
                (x → P | y)  # meaningless per '| y)' is not '| y → Q'
                (x → P) | (y → Q)  # meaningless per | is not an operator on processes
                (x → P | (y → Q | z → R))

                # RUN-A = (x:A → RUN-A)  # 1.1.3 X8


                # 1.1.4 Mutual recursion

                DD1 = (setorange → O1 | setlemon → L1)
                O1 = (orange → O1 | setlemon → L1 | setorange → O1)
                L1 = (lemon → L1 | setorange → O1 | setlemon → L1)

                O2 = (orange → O2 | setlemon → L2 | setorange → O2)
                L2 = (lemon → L2 | setorange → O2 | setlemon → L2)
                DD2 = (setorange → O2 | setlemon → L2)

                L3 = (lemon → L3 | setorange → O3 | setlemon → L3)
                O3 = (orange → O3 | setlemon → L3 | setorange → O3)
                DD3 = (setlemon → L3 | setorange → O3)

                DD4 = (setorange → O4 | setlemon → L4)
                L4 = (lemon → L4 | setorange → O4 | setlemon → L4)
                O4 = (orange → O4 | setlemon → L4 | setorange → O4)

                DD1
                DD2
                DD3
                DD4

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
            worker = ccl.take_one(ccl.taker)
        except CspError as exc:
            stderr_print("cspsh.py: error: {}: {}".format(type(exc).__name__, exc))
            continue
        except Exception as exc:
            stderr_print("cspsh.py: info: line", repr(line))
            stderr_print("cspsh.py: info: shards", ccl.taker.shards)
            stderr_print("cspsh.py: error: {}: {}".format(type(exc).__name__, exc))
            raise

        verbose_print("+++", worker)
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

        prompt = "{}>  ".format(open_marks[-1]) if open_marks else "??  "
        if not open_marks:
            prompt = "\n" + prompt

        if lines:

            stderr_print(prompt + lines[0].rstrip())

        else:

            stderr_print(prompt, end="")
            sys.stdout.flush()
            more = stdin.readline()
            if not stdin.isatty():
                stderr_print(more.rstrip())
                # FIXME: make --echo-input=yes easy to say when not isatty
            if not more:
                stderr_print()

            lines.append(more)

        more = lines[0]
        lines[:] = lines[1:]

        if not more:
            assert not lines
            break

        enough = more[: more.index("#")] if ("#" in more) else more

        line += "\n"
        line += enough

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

        self.taker = ShardsTaker()
        self.traces = list()
        self.crossings = list()
        self.gotos = list()

        CspCommandLine.top_worker = self

    def __call__(self):
        worker = self.worker
        if worker:
            self.trace_open(crossing=False)
            worker()
            self.trace_close()

    def __str__(self):
        return str(self.str_worker)

    def trace_open(self, crossing):
        traces = self.traces

        if traces:
            trace = traces[-1]
            if trace:
                self.trace_print(len(traces[:-1]), trace=trace)
                traces[-1] = list()

        trace = list()
        self.traces.append(list())
        self.trace("⟨")
        self.crossings.append(crossing)

    def trace(self, *args):
        trace = self.traces[-1]
        trace.extend(args)

    def trace_close(self):
        traces = self.traces
        crossings = self.crossings

        self.trace("⟩")
        trace = traces.pop()
        crossings.pop()
        self.trace_print(len(traces), trace=trace)

    def trace_print(self, depth, trace):

        dents = depth * "    "

        chars = ""

        if trace and (trace[0] == "⟨"):
            chars += "⟨"
            trace = trace[1:]

        while trace and (trace[0] != "⟩"):
            event = trace[0]
            if chars not in ("", "⟨",):
                chars += ", "
            chars += str(event)
            trace = trace[1:]

        if trace and (trace[0] == "⟩"):
            chars += "⟩"
            trace = trace[1:]

        assert "None" not in chars  # PL FIXME: too strict?

        print(dents + chars)

    def call_named_process(self, name, process):
        assert name and process

        crossings = self.crossings
        crossing = crossings[-1] if crossings else None

        if crossing:

            CspCommandLine.top_worker.trace(name, ". . .")

        else:

            self.gotos.append(name)
            count = self.gotos.count(name)

            if count > 3:
                CspCommandLine.top_worker.trace(name, "...")
            else:
                process()

    @classmethod
    def take_one(cls, taker):

        str_worker = None
        worker = None
        if taker.peek_more():

            words = taker.peek_some_shards(2)
            if words[-1] and (words[1][1] == "="):
                define_process = DefineProcess.take_one(taker)
                str_worker = define_process
                worker = None  # FIXME FIXME: worker = CspStrWorker(define_process)
            else:
                worker = Process.take_one(taker)
                str_worker = worker

            if taker.peek_more():
                words = SomeCspWords.take_one(taker)
                raise CspError("gave up before reading: {}".format(words))

            taker.take_beyond_shards()

        worker = CspCommandLine(str_worker=str_worker, worker=worker)
        return worker

    def give_one_sourceline(self, line):

        taker = self.taker

        tabsize_8 = 8

        text = line.strip()
        text = text.expandtabs(tabsize_8)  # replace "\t" with between 1 and 8 " "
        text = " ".join(text.splitlines())  # replace "\r\n" or "\r" or "\n" with " "
        text = text.rstrip()

        csp_words = list()
        while text:

            shards_match = re.match(SHARDS_REGEX, string=text)
            try:
                assert shards_match
            except AssertionError:
                stderr_print(repr(text))
                raise

            matches = shards_match.groupdict().items()
            matches = list((k, v,) for (k, v,) in matches if v)

            assert len(matches) == 1
            (kind, chars,) = matches[0]
            csp_word = CspWord(kind=kind, chars=chars)

            assert text.startswith(csp_word.chars)
            text = text[len(csp_word.chars) :]

            csp_words.append(csp_word)

        words = [_ for _ in csp_words if _.kind != "blanks"]  # drop BLANKS_REGEX

        taker.give_shards(words)


class Process(CspWorker):
    """Work through a process"""

    @classmethod
    def take_one(cls, taker):

        words = taker.peek_some_shards(2)
        if words[-1] and (words[0].chars == "("):
            worker = OpenProcessClose.take_one(taker, after_mark="(", upto_mark=")")
        elif words[-1] and (words[1].chars == "→"):
            worker = EventChoice.take_one(taker)
        else:
            worker = ProcessCaller.take_one(taker)

        worker = Process(worker=worker)
        return worker


class OpenProcessClose(CspWorker):
    """Define a process as the work after a "(" mark and before a ")" mark"""

    @classmethod
    def take_one(self, taker, after_mark, upto_mark):

        open_after = CspOpenMark.take_one(taker, after_mark)
        worker = Process.take_one(taker)
        upto_close = CspCloseMark.take_one(taker, upto_mark)

        worker = OpenProcessClose(
            open_after=open_after, worker=worker, upto_close=upto_close,
        )
        return worker


class EventChoice(CspWorker):
    """Let the work through a first event choose which process comes next"""

    def __call__(self):
        last_index = len(self.choices) - 1
        for (index, choice,) in enumerate(self.choices):
            crossing = index < last_index
            CspCommandLine.top_worker.trace_open(crossing)
            choice()
            CspCommandLine.top_worker.trace_close()

    def __str__(self):

        bars = self.bars
        choices = self.choices

        choice = choices[0]
        chars = str(choice)
        for (bar, choice,) in zip(bars, choices[1:]):
            chars += str(bar)
            chars += str(choice)

        return chars

    @classmethod
    def take_one(self, taker):

        choices = list()
        bars = list()

        words = taker.peek_some_shards(2)
        assert words[-1] and (words[-1].chars == "→")

        choice = EventThenProcess.take_one(taker)
        choices.append(choice)

        while True:

            word = taker.peek_one_shard()
            if word and (word.chars == "|"):
                three_words = taker.peek_some_shards(3)

                bar = CspMark.take_one(taker, "|")
                bars.append(bar)

                if three_words[-1] and (three_words[-1].chars == "→"):
                    choice = EventThenProcess.take_one(taker)
                    choices.append(choice)

                else:

                    some_last_words = SomeCspWords.take_one(taker)
                    stderr_print(
                        "cspsh.py: warning: gave up before reading: {}".format(
                            some_last_words
                        )
                    )

                    str_three_words = " ".join(_.chars for _ in three_words)
                    raise CspError(
                        "'| y → Q' has meaning, {!r} does not".format(str_three_words)
                    )

            else:

                break

        names = set()
        collisions = list()
        for choice in choices:
            name = choice.event_name.name
            if name in names:
                if name not in collisions:
                    collisions.append(name)
                collisions.append(name)
            else:
                names.add(name)

        if collisions:
            raise CspError("choices not distinct: {}".format(collisions))

        if len(choices) == 1:
            worker = choices[0]
            return worker

        worker = EventChoice(choices=choices, bars=bars)
        return worker


class EventThenProcess(CspWorker):
    """Work through one (or more) events and then a process"""

    def __call__(self):

        name = self.event_name.name
        assert name
        CspCommandLine.top_worker.trace(name)

        self.worker()

    @classmethod
    def take_one(self, taker):

        event_names = list()
        then_marks = list()

        words = taker.peek_some_shards(2)
        assert words[-1] and (words[-1].chars == "→")

        while True:

            words = taker.peek_some_shards(2)
            if not words[-1]:
                break
            if words[1].chars != "→":
                break

            event_name = EventName.take_one(taker)
            then_mark = CspMark.take_one(taker, "→")

            event_names.append(event_name)
            then_marks.append(then_mark)

        assert event_names

        word = taker.peek_one_shard()
        if word.chars == "(":
            worker = OpenProcessClose.take_one(taker, after_mark="(", upto_mark=")")
        else:
            worker = Process.take_one(taker)

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
        elif name == "STOP":
            CspCommandLine.top_worker.trace(name)
        else:
            CspCommandLine.top_worker.trace(name + "!")

    @classmethod
    def take_one(cls, taker):

        process_name = ProcessName.take_one(taker)
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
        assert False

    def __str__(self):
        chars = "{}{}{}".format(self.process_name, self.is_mark, self.body)
        return chars

    @classmethod
    def take_one(self, taker):

        process_name = ProcessName.take_one(taker)
        is_mark = CspMark.take_one(taker, "=")

        process_caller = ProcessCaller(source=None, process_name=process_name)
        CspCommandLine.processes_by_name[process_name.name] = process_caller

        word = taker.peek_one_shard()
        if word.chars == "µ":
            body = ProcessWithSuch.take_one(taker, process_caller)
        else:
            body = Process.take_one(taker)
            process_caller.process = body

        assert CspCommandLine.processes_by_name[process_name.name] == process_caller

        worker = DefineProcess(process_name=process_name, is_mark=is_mark, body=body)
        return worker


class ProcessWithSuch(CspWorker):
    """Give a process a local name and an alphabet"""

    def __call__(self):
        assert False

    def __str__(self):

        kvs = dict(vars(self))
        if not self.with_alphabet_mark and not self.alphabet:
            del kvs["with_alphabet_mark"]
            del kvs["alphabet"]

        chars = "".join(str(_) for _ in kvs.values()).strip()
        chars = chars.replace("  ", " ")

        return chars

    @classmethod
    def take_one(self, taker, process_caller):

        the_process_mark = CspMark.take_one(taker, "µ")
        process_name = ProcessName.take_one(taker)

        assert process_name.name not in CspCommandLine.processes_by_name.keys()
        CspCommandLine.processes_by_name[process_name.name] = process_caller

        word = taker.peek_one_shard()
        if word and (word.chars != ":"):  # defer EOF into "with_alphabet_mark ="
            with_alphabet_mark = None
            alphabet = None
        else:
            with_alphabet_mark = CspMark.take_one(taker, ":")
            alphabet = CspAlphabet.take_one(taker, after_mark="{", upto_mark="}")

        such_that_mark = CspMark.take_one(taker, "•")
        process = Process.take_one(taker)

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
    def take_one(self, taker, after_mark, upto_mark):

        open_after = CspOpenMark.take_one(taker, after_mark)

        event_names = list()
        comma_marks = list()
        while True:

            words = taker.peek_some_shards(2)
            if not words:
                break
            if words[1].chars != ",":
                break

            event_name = EventName.take_one(taker)
            comma_mark = CspMark.take_one(taker, ",")

            event_names.append(event_name)
            comma_marks.append(comma_mark)

        event_name = EventName.take_one(taker)
        event_names.append(event_name)

        upto_close = CspCloseMark.take_one(taker, upto_mark)
        worker = CspAlphabet(
            open_after=open_after,
            event_names=event_names,
            comma_marks=comma_marks,
            upto_close=upto_close,
        )
        return worker


class EventName(CspWorker):
    """Capture the lowercase name of an event"""

    @classmethod
    def take_one(self, taker):

        csp_name = CspName.take_one(taker)

        if csp_name.name != csp_name.name.lower():
            raise CspError(
                "event name {!r} is not lower case {!r}".format(
                    csp_name.name, csp_name.name.lower()
                )
            )

        worker = EventName(name=csp_name.name)
        return worker


class ProcessName(CspWorker):
    """Capture the uppercase name of a process"""

    @classmethod
    def take_one(self, taker):

        csp_name = CspName.take_one(taker)

        if csp_name.name != csp_name.name.upper():
            raise CspError(
                "process name {!r} is not upper case {!r}".format(
                    csp_name.name, csp_name.name.upper()
                )
            )

        worker = EventName(name=csp_name.name)
        return worker


class CspName(CspWorker):
    """Capture a fragment of source that names something else"""

    @classmethod
    def take_one(self, taker):

        word = taker.peek_one_shard()
        assert word.kind == "name"
        name = word.chars
        taker.take_one_shard()

        worker = CspName(name=name)
        return worker


class CspOpenMark(CspWorker):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = " {}".format(self.mark)  # no blank inside on the right
        return chars

    @classmethod
    def take_one(self, taker, mark):

        csp_mark = CspMark.take_one(taker, mark=mark)

        worker = CspOpenMark(mark=csp_mark.mark)
        return worker


class CspCloseMark(CspWorker):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = "{} ".format(self.mark)  # no blank inside on the left
        return chars

    @classmethod
    def take_one(self, taker, mark):

        csp_mark = CspMark.take_one(taker, mark=mark)

        worker = CspCloseMark(mark=csp_mark.mark)
        return worker


class CspMark(CspWorker):
    """Capture a fragment of source that names itself"""

    def __str__(self):
        chars = " {} ".format(self.mark)
        return chars

    @classmethod
    def take_one(self, taker, mark):

        word = taker.peek_one_shard()
        assert word.kind == "mark"
        assert word.chars == mark
        taker.take_one_shard()

        worker = CspMark(mark=word.chars)
        return worker


class SomeCspWords(CspWorker):
    """Take the remaining words"""

    def __call__(self):
        assert False

    def __str__(self):

        chars = "".join(str(_) for _ in self.workers)

        return chars

    @classmethod
    def take_one(self, taker):

        assert taker.peek_more()

        workers = list()
        while taker.peek_more():
            word = taker.peek_one_shard()
            if word.kind == "name":
                worker = CspName.take_one(taker)
            else:
                assert word.kind == "mark"
                worker = CspMark.take_one(taker, mark=word[1])

            workers.append(worker)

        worker = SomeCspWords(workers=workers)
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


# copied from:  git clone https://github.com/pelavarre/pybashish.git
