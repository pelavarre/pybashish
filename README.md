# pybashish

Come here to patch the unlicensed Python source code inside Bash

Take these source files and fork them, to meet your own need today, as you decline to
settle for the points-of-view that Bash shoves on you, leftover from last century

Four steps

1 )

Try this out:

    git clone https://github.com/pelavarre/pybashish.git
    cd pybashish/bin/
    export PATH="${PATH:+$PATH:}$PWD"

to answer the question of:

Is your Bash broken in corners coming to bite you soon, or
has it already put the work in to defend you from such painful surprises?

1.1 ) Does your Mac Bash Cat misprint each &nbsp; Non-Break Space as a Space?

    echo $'\x5A\xC2\xA0' |cat -etv  # misprints Nbsp as Space

    echo $'\x5A\xC2\xA0' |cat.py -etv

1.2 ) Does your Bash Cp make you dream up a distinct name for every backup you make?

    touch  # usage error
    cp file.txt  # usage error

    touch.py
    cp.py file.txt

1.3 ) Does your Bash Expand leave all your Smart Chars dragging you out of US-Ascii?

    echo $'\xC2\xA0 « » “ ’ ” – — ′ ″ ‴ ' |expand
    echo -n $'\n\nHello, Plain Text World' |expand

    echo $'\xC2\xA0 « » “ ’ ” – — ′ ″ ‴ ' |expand.py
    echo -n $'\n\nHello, Plain Text World' |expand.py

1.4 ) Does your Bash Echo never tell you how many words it broke your line into?

    echo 'Hello,' 'Echo World!'

    echo.py 'Hello,' 'Echo World!'
    echo.py --v 'Hello,' 'Echo World!'

1.5 ) Does your Bash Head insist on counting the trailing lines to drop from the top?

    seq 1 19 |head +16  # no such file

    seq 1 19 |head.py +16

1.6 ) Does your Bash HexDump only show you visual patterns for bytes 0x20..0x7e?

    python3 -c 'import os; os.write(1, bytearray(range(256)))' |hexdump -C
    echo -n 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' |hexdump -C

    python3 -c 'import os; os.write(1, bytearray(range(256)))' |hexdump.py -C
    echo -n 'åéîøü←↑→↓⇧⌃⌘⌥💔💥😊😠😢' |hexdump.py --chars

1.7 ) Does your Bash MkDir force you to name your new dir before you fill it?

    mkdir  # usage error

    mkdir.py

1.8 ) Does your Bash Ls give you no column headings? And no precise timestamps?

    ls --headings  # usage error
    ls --full-time  # usage error at mac, works at linux

    ls.py --headings
    ls.py --full-time

1.9 ) Does your Bash Tr never tell you which unusual chars you're dealing with?

    tr --unique-everseen  # usage error

    cat $(git ls-files) |tr.py -d '[ -~]\t\r\n' --unique-everseen && echo

2 )

Does your Bash write the equivalent Python for the Bash lines you give it, or does it
shove that chore of translation onto you?

    grep --rip .py  Key1 file.txt  # usage error

    grep.py --rip .py  Key1 file.txt  # shows you the source
    grep.py --rip .py --patterns  Key1 Key2 Key3  # lets you choose multiple keys
    zcat.py --rip .py  # lets you compress the input

3 )

Does your Python write the equivalent ArgParse calls for the Help Doc you give it, or
does it shove that chore of translation onto you?

    cat --help  # usage error

    cat.py --help
    argdoc.py --rip .py cat.py

4 )

Stand up and push back, why not?

- PyBashIsh, born 20/Jun/2020
