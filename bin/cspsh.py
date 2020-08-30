#!/usr/bin/env python3

r"""
usage: cspsh.py [-h] [-c COMMAND] [-f] [-i] [-q] [-v]

chat of "communicating sequential processes"

optional arguments:
  -h, --help      show this help message and exit
  -c COMMAND      interpret one command without prompting for more
  -f, --force     ask less questions
  -i, --interact  ask more questions
  -q, --quiet     say less
  -v, --verbose   say more

csp examples:
  tick → STOP
  tick → tick → STOP
  CLOCK = (tick → tock → CLOCK)
  CLOCK

examples:
  cspsh.py -i  # chat out one result at a time
  cspsh.py -f  # dump a large pile of results
"""
# FIXME: bring in the maths unicode that doesn't copy-paste well from 1.4..1.10

# FIXME: disentangle "passme.cspvm" from "def CspCommandLine"
# FIXME: add labels into the trace as labels X: CLOCK: etc
# FIXME: flush events to trace when they happen: stop delaying whole trace lines
# FIXME: trace EventChoice sources indented as well as traces

# FIXME: rename "-f, --force" to "-s, --self-test"? because "-fi" should cancel out?
# FIXME: clean up the echo to interleave prompt and input, for paste of multiple input lines
# FIXME: limit the trace of ProcessWithSuch to its alphabet

# FIXME: test more of the book and/or chase into the parts of the book commented out of TEST_LINES
# FIXME: compile CSP to Python, and run as Python, like for lazy eval of infinite mutual definitions
# FIXME: such as CT[n+1] = (up → CT[n+2] | down → CT[n])

# FIXME: all the f-i-x-m-e scattered far below


import argparse
import collections
import re
import sys
import textwrap

import argdoc


CspWord = collections.namedtuple("CspWord", "kind, chars".split(", "))


NAME_REGEX = r"(?P<name>[A-Za-z_][.0-9A-Za-z_]*)"
MARK_REGEX = r"(?P<mark>[(),:={|}µ•→⟨⟩])"
BLANKS_REGEX = r"(?P<blanks>[ ]+)"

SHARDS_REGEX = r"|".join([NAME_REGEX, MARK_REGEX, BLANKS_REGEX])


OPEN_MARK_REGEX = r"[(\[{⟨]"
CLOSE_MARK_REGEX = r"[)\]}⟩]"


class CspError(SyntaxError):
    """Mark compilation errors"""


def main():

    args = argdoc.parse_args()
    main.args = args

    if all((_ is None) for _ in vars(args).values()):
        stderr_print(argdoc.format_usage().rstrip())
        stderr_print("cspsh.py: error: choose --force or --interact")
        sys.exit(2)  # exit 2 from rejecting usage

    lines = list()
    if args.force:
        lines = textwrap.dedent(TEST_LINES).strip().splitlines(keepends=True)
        lines.append("")

    if args.command is not None:
        lines.append(args.command + "\n")
        lines.append("")

    run_cspvm(lines, args=args)


def run_cspvm(lines, args):

    verbose_print()
    verbose_print()

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
            ccl_ccl = ccl.take_one(ccl.taker)  # FIXME: disentangle ccl_ccl vs ccl
        except CspError as exc:
            stderr_print("cspsh.py: error: {}: {}".format(type(exc).__name__, exc))
            continue
        except Exception as exc:
            stderr_print("cspsh.py: info: line", repr(line))
            stderr_print("cspsh.py: info: shards", ccl.taker.shards)
            stderr_print("cspsh.py: error: {}: {}".format(type(exc).__name__, exc))
            raise

        str_worker = str(ccl_ccl)
        if str_worker:
            verbose_print("+++", str_worker)
            verbose_print()

        top = argparse.Namespace()
        vars(top)[type(ccl_ccl).__name__] = ccl_ccl

        ccl_ccl()

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

            if not lines[0]:
                if main.args.interact:
                    lines[0] = "\n"  # mutate

        else:

            stderr_print(prompt, end="")
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
        print(type(self).__name__)  # FIXME: more of a log message here
        assert False

    def __repr__(self):
        return object.__repr__(self)

    def __str__(self):
        chars = "".join(str(_) for _ in vars(self).values()).strip()
        chars = chars.replace("  ", " ")
        return chars


class CspCommandLine(CspWorker):
    """Work through a line of source code"""

    cspvm = None

    process_callers_by_name = dict()

    def __init__(self, **kwargs):
        CspWorker.__init__(self, **kwargs)

        self.taker = ShardsTaker()
        self.traces = list()
        self.crossings = list()
        self.gotos = list()

        CspCommandLine.cspvm = self

    def __call__(self):

        worker = self.worker
        if worker:

            self.trace_open(crossing=False)
            worker()
            self.trace_close()

    def __str__(self):
        if self.str_worker:
            return str(self.str_worker)
        return ""

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
        else:
            if chars[-1] != "⟨":
                chars += ","

        assert "None" not in chars  # PL FIXME: too strict?

        print(dents + chars)

    def goto_named_process(self, name, process):
        """Call the process, else print a less infinite substitute"""

        assert process

        crossings = self.crossings
        crossing = crossings[-1] if crossings else None
        if crossing:
            if process in self.gotos:
                CspCommandLine.cspvm.trace(name, ". . .")
                return

        self.gotos.append(process)

        count = self.gotos.count(process)
        if count > 3:
            CspCommandLine.cspvm.trace(name, "...")
            return

        process()

    @classmethod
    def take_one(cls, taker):

        str_worker = None
        worker = None
        if taker.peek_more():

            words = taker.peek_some_shards(2)
            if words[-1] and (words[1][1] == "="):
                define_process = DefineProcess.take_one(taker)
                worker = None
                str_worker = define_process
            else:
                process = Process.take_one(taker)
                worker = process
                str_worker = process

            if taker.peek_more():
                words = SomeCspWords.take_one(taker)
                raise CspError("gave up before reading: {}".format(words))

            taker.take_beyond_shards()

        ccl = CspCommandLine(worker=worker, str_worker=str_worker)
        return ccl

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

    def __call__(self):
        self.worker()

    @classmethod
    def take_one(cls, taker):

        words = taker.peek_some_shards(2)
        if words[-1] and (words[0].chars == "("):
            opc = OpenProcessClose.take_one(taker, after_mark="(", upto_mark=")")
            worker = opc
        elif words[-1] and (words[1].chars == "→"):
            event_choice = EventChoice.take_one(taker)
            worker = event_choice
        else:
            process_caller = ProcessCaller.take_one(taker)
            worker = process_caller

        process = Process(worker=worker)
        return process


class OpenProcessClose(CspWorker):
    """Define a process as the work after a "(" mark and before a ")" mark"""

    def __call__(self):
        self.process()

    @classmethod
    def take_one(cls, taker, after_mark, upto_mark):

        open_after = CspOpenMark.take_one(taker, after_mark)
        process = Process.take_one(taker)
        upto_close = CspCloseMark.take_one(taker, upto_mark)

        opc = OpenProcessClose(
            open_after=open_after, process=process, upto_close=upto_close,
        )
        return opc


class EventChoice(CspWorker):
    """Let the work through a first event choose which process comes next"""

    def __call__(self):
        if len(self.choices) == 1:
            choice = self.choices[0]
            choice()
        else:
            last_index = len(self.choices) - 1
            for (index, choice,) in enumerate(self.choices):
                crossing = index < last_index
                CspCommandLine.cspvm.trace_open(crossing)
                choice()
                CspCommandLine.cspvm.trace_close()

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
    def take_one(cls, taker):

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

        event_choice = EventChoice(choices=choices, bars=bars)
        return event_choice


class EventThenProcess(CspWorker):
    """Work through one (or more) events and then a process"""

    def __call__(self):

        name = self.event_name.name
        assert name
        CspCommandLine.cspvm.trace(name)

        self.worker()

    @classmethod
    def take_one(cls, taker):

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

        event_then_process = None
        pairs = zip(event_names, then_marks)
        for (event_name, then_mark,) in reversed(list(pairs)):
            event_then_process = EventThenProcess(
                event_name=event_name, then_mark=then_mark, worker=worker
            )
            worker = event_then_process

        assert event_then_process
        return event_then_process


class ProcessCaller(CspWorker):
    """Call a process by name"""  # a la Lisp Label

    def __call__(self):

        name = self.name
        process = self.process

        if process:
            if not isinstance(process, ProcessCaller):
                CspCommandLine.cspvm.goto_named_process(name, process=process)
            else:  # trace → X as the P at µ X in P = µ X : ... • ... → X
                process_caller = process
                CspCommandLine.cspvm.goto_named_process(
                    process_caller.name, process=process_caller.process
                )

        elif name in CspCommandLine.cspvm.process_callers_by_name:

            process_caller = CspCommandLine.cspvm.process_callers_by_name[name]
            CspCommandLine.cspvm.goto_named_process(name, process=process_caller)
            # FIXME: think into making this late binding sticky or no

        else:

            if name == "STOP":
                CspCommandLine.cspvm.trace(name)
            else:
                CspCommandLine.cspvm.trace(name + "!")

    def __str__(self):
        return str(self.process_name)

    @classmethod
    def take_one(cls, taker):

        process_name = ProcessName.take_one(taker)
        name = process_name.name

        process = None
        if name in CspCommandLine.process_callers_by_name:
            inner_process_caller = CspCommandLine.process_callers_by_name[name]
            process = inner_process_caller

        process_caller = ProcessCaller(process_name=process_name, process=process,)
        process_caller.name = name

        return process_caller


class DefineProcess(CspWorker):
    """Name a process to call"""

    @classmethod
    def take_one(cls, taker):

        process_caller = ProcessCaller.take_one(taker)

        name = process_caller.name
        if process_caller.process is not None:
            process_caller.process = None  # mutate, when not single-assignment

        CspCommandLine.process_callers_by_name[name] = process_caller  # add or mutate

        is_mark = CspMark.take_one(taker, "=")

        word = taker.peek_one_shard()
        if word.chars != "µ":
            process = Process.take_one(taker)
            definition = process
            process_caller_process = process
        else:
            process_with_such = ProcessWithSuch.take_one(taker)
            definition = process_with_such
            process_caller_process = definition.process_caller

            assert process_with_such.process_caller.name
            process_with_such.process_caller.name = name
            # trace µ X as P in P = µ X : ... • ... → X

        assert CspCommandLine.process_callers_by_name[name] == process_caller
        assert process_caller.process is None
        process_caller.process = process_caller_process

        define_process = DefineProcess(
            process_caller=process_caller, is_mark=is_mark, definition=definition
        )
        return define_process


class ProcessWithSuch(CspWorker):
    """Give a process a local name and an alphabet"""

    def __call__(self):
        self.body()

    def __str__(self):

        kvs = dict(vars(self))
        if not self.with_alphabet_mark and not self.alphabet:
            del kvs["with_alphabet_mark"]
            del kvs["alphabet"]

        chars = "".join(str(_) for _ in kvs.values()).strip()
        chars = chars.replace("  ", " ")

        return chars

    @classmethod
    def take_one(cls, taker):

        the_process_mark = CspMark.take_one(taker, "µ")

        process_caller = ProcessCaller.take_one(taker)
        name = process_caller.name

        assert name not in CspCommandLine.process_callers_by_name
        assert process_caller.process is None

        CspCommandLine.process_callers_by_name[name] = process_caller
        if True:

            word = taker.peek_one_shard()
            if word and (word.chars != ":"):  # defer EOF into "with_alphabet_mark ="
                with_alphabet_mark = None
                alphabet = None
            else:
                with_alphabet_mark = CspMark.take_one(taker, ":")
                alphabet = CspAlphabet.take_one(taker, after_mark="{", upto_mark="}")

            such_that_mark = CspMark.take_one(taker, "•")
            body = Process.take_one(taker)

            assert CspCommandLine.process_callers_by_name[name] == process_caller
            assert process_caller.process is None
            process_caller.process = body

        del CspCommandLine.process_callers_by_name[name]

        process_with_such = ProcessWithSuch(
            the_process_mark=the_process_mark,
            process_caller=process_caller,
            with_alphabet_mark=with_alphabet_mark,
            alphabet=alphabet,
            such_that_mark=such_that_mark,
            body=body,
        )
        return process_with_such


class CspAlphabet(CspWorker):
    """Collect events into an alphabet"""

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
    def take_one(cls, taker, after_mark, upto_mark):

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
        csp_alphabet = CspAlphabet(
            open_after=open_after,
            event_names=event_names,
            comma_marks=comma_marks,
            upto_close=upto_close,
        )
        return csp_alphabet


class EventName(CspWorker):
    """Capture the lowercase name of an event"""

    @classmethod
    def take_one(cls, taker):

        csp_name = CspName.take_one(taker)

        if csp_name.name != csp_name.name.lower():
            raise CspError(
                "event name {!r} is not lower case {!r}".format(
                    csp_name.name, csp_name.name.lower()
                )
            )

        event_name = EventName(name=csp_name.name)
        return event_name


class ProcessName(CspWorker):
    """Capture the uppercase name of a process"""

    @classmethod
    def take_one(cls, taker):

        csp_name = CspName.take_one(taker)

        if csp_name.name != csp_name.name.upper():
            raise CspError(
                "process name {!r} is not upper case {!r}".format(
                    csp_name.name, csp_name.name.upper()
                )
            )

        process_name = ProcessName(name=csp_name.name)
        return process_name


class CspName(CspWorker):
    """Capture a fragment of source that names something else"""

    @classmethod
    def take_one(cls, taker):

        word = taker.peek_one_shard()
        assert word.kind == "name"
        name = word.chars
        taker.take_one_shard()

        csp_name = CspName(name=name)
        return csp_name


class CspOpenMark(CspWorker):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = " {}".format(self.mark)  # no blank inside on the right
        return chars

    @classmethod
    def take_one(cls, taker, mark):

        csp_mark = CspMark.take_one(taker, mark=mark)

        csp_open_mark = CspOpenMark(mark=csp_mark.mark)
        return csp_open_mark


class CspCloseMark(CspWorker):
    """Capture a mark that opens a scope of source"""

    def __str__(self):
        chars = "{} ".format(self.mark)  # no blank inside on the left
        return chars

    @classmethod
    def take_one(cls, taker, mark):

        csp_mark = CspMark.take_one(taker, mark=mark)

        csp_close_mark = CspCloseMark(mark=csp_mark.mark)
        return csp_close_mark


class CspMark(CspWorker):
    """Capture a fragment of source that names itself"""

    def __str__(self):
        chars = " {} ".format(self.mark)
        return chars

    @classmethod
    def take_one(cls, taker, mark):

        word = taker.peek_one_shard()
        assert word.kind == "mark"
        assert word.chars == mark
        taker.take_one_shard()

        csp_mark = CspMark(mark=word.chars)
        return csp_mark


class SomeCspWords(CspWorker):
    """Take the remaining words"""

    def __str__(self):

        chars = "".join(str(_) for _ in self.workers)

        return chars

    @classmethod
    def take_one(cls, taker):

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

        some_csp_words = SomeCspWords(workers=workers)
        return some_csp_words


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


#
# Supply the self-test with input
#


BASIC_TEST_LINES = """

    #
    # examples from the help lines
    #

    tick → STOP
    tick → tick → STOP
    CLOCK = (tick → tock → CLOCK)
    CLOCK


    #
    # more examples from us
    #

    CLOCK = µ X : {tick, tock} • (tick → tock → X)
    CLOCK

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

"""

CHAPTER_1_TEST_LINES = """

    #
    # Chapter 1:  Processes
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

    # αDD = αO = αL = {setorange, setlemon, orange, lemon}

    DD = (setorange → O | setlemon → L)  # 1.1.4 X1
    O = (orange → O | setlemon → L | setorange → O)
    L = (lemon → L | setorange → O | setlemon → L)

    DD

    CT0 = (up → CT1 | around → CT0)  # 1.1.4 X2
    CT1 = (up → CT2 | down → CT0)
    CT2 = (up → CT3 | down → CT1)

    CT0

    CT0 = (around → CT0 | up → CT1)  # 1.1.4 X2  # Variation B
    CT1 = (down → CT0 | up → CT2)
    CT2 = (down → CT1 | up → CT3)

    CT0

    # CT[n+1] = (up → CT[n+2] | down → CT[n])


    # 1.2 Pictures


    # 1.3 Laws

    # (x → P | y → Q) = (y → Q | x → P)  # but our traces of these are inequal
    (x → P | y → Q)
    (y → Q | x → P)

    # (x → P) ≠ STOP
    (x → P)
    STOP

    # L1    (x:A → P(x)) = (y:B → Q(y))  ≡  (A = B  ∧  ∀ x:A • P(x)=Q(x))
    # L1A   STOP ≠ (d → P)
    # L1B   (c → P) ≠ (d → Q)
    # L1C   (c → P | d → Q) = (d → Q | c → P)
    # L1D   (c → P) = (c → Q)  ≡  P = Q

    # (coin → choc → coin → choc → STOP) ≠ (coin → STOP)  # 1.3 X1

    # µ X • (coin → (choc → X | toffee → X ))  =  # 1.3 X2
    #   µ X • (coin → (toffee → X | choc → X ))

    # L2    (Y = F(Y))  ≡  (Y = µ X • F(X))  # <= FIXME: what is this??
    # L2A   µ X • F(X) = F(µ X • F(X))  # <= FIXME: a la L2

    VM1 = (coin → VM2)
    VM2 = (choc → VM1)

    VM1
    VM2
    VMS

    # L3    if (∀ i:S • (Xi = F(i, X )  ∧  Yi = F(i, Y))) then X = Y  # <= FIXME: a la L2


    # 1.4  Implementation of processes

    # Bleep, Label, Choice2, Menu, Interact, Cons, Car


    # 1.5 Traces

    # first 4 events of VMS  # 1.5 X1
    # first 3 events of VMS  # 1.5 X2
    # first 0 events of any process, even STOP  # 1.5 X3
    # all traces of <= 2 events at VMC  # 1.5 X4
    # ⟨in1p, in1p, in1p⟩ ends the only trace it begins, because it STOP's  # 1.5 X5


    # 1.6 Operations on traces

    # 1.6.1 Catenation  # FIXME: math unicode that doesn't paste
    # 1.6.2 Restriction
    # 1.6.3 Head and tail
    # 1.6.4 Star
    # 1.6.5 Ordering
    # 1.6.6 Length

    # 1.7 Implementation of traces

    # 1.8 Traces of a process
    # 1.8.1 Laws [of traces]
    # 1.8.2 Implementation

    # 1.8.3 After

    # 1.9 More operations on traces
    # 1.9.1 Change of symbol
    # 1.9.2 Catenation [continued from 1.6.1]
    # 1.9.3 Interleaving
    # 1.9.4 Subscription
    # 1.9.5 Reversal
    # 1.9.6 Selection
    # 1.9.7 Composition

    # 1.10 Specifications
    # 1.10.1 Satisfaction
    # 1.10.2 Proofs

"""

CHAPTER_2_TEST_LINES = """

    #
    # Chapter 2:  Concurrency
    #

"""

TEST_LINES = BASIC_TEST_LINES + CHAPTER_1_TEST_LINES + CHAPTER_2_TEST_LINES


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
