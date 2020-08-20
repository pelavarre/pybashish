# pybashish/Makefile:  Run the self-test's

default: black test-once
	:
	git status | grep -v '^$$'
	:
	: make: passed
	:

help:
	: # usage: make {default|blacken-here|help|test-here}
	: #
	: # help develop this code
	: #
	: # make verbs:
	: #     black           blacken the Python style here, again
	: #     default         blacken and test
	: #     me              run:  python3 ../pybashish/
	: #     test-once       run the tests here, just once more
	: #
	: # bugs:
	: #     prompts with "? ", unlike the "" of Bash "read" with no -p PROMPT
	: #

black:
	. ~/bin/black.source && black $$PWD/../pybashish/

test-once:
	:
	rm -fr ../pybashish/.local/share/grep/files/
	bin/grep.py >/dev/null
	:
	bin/doctestbash.py tests/ || (bin/doctestbash.py -vv tests/; exit 1)
	:
	for F in bin/*.py; do bin/argdoc.py $$F >/dev/null && continue; echo "make: error:  python3 -m pdb bin/argdoc.py $$F" >&2; exit 1; done
	: argdoc: tests passed
	:
	(cd bin; python3 -m doctest -- ../tests/_test_subsh-typescript.txt)
	: doctest: tests passed
	:
	tests/_test_subsh.py >/dev/null
	: test_subsh: tests passed
	:
	rm -fr a b
	git ls-files | grep -vE '(README.md|__init__.py|.gitignore)' >a
	git grep -l copied.from $$(git ls-files) >b
	diff -burp a b
	rm -fr a b
	:
	rm -fr ../pybashish/bin/pyish.pyc
	:

grep-fixme:
	echo && echo && echo && git grep 'F'IXME | awk -F: '{ n=$$1; if (n != o) {o=n; print ""; print $$1":"}; $$1=""; print substr($$0, 2)}' | less -FRX

me:
	python3 ../pybashish/

# copied from:  git clone https://github.com/pelavarre/pybashish.git
