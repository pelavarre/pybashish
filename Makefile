# pybashish/Makefile:  Run the self-test's

default:
	:
	bin/doctestbash.py || (bin/doctestbash.py -vv; exit 1)
	:
	for F in bin/*.py; do bin/argdoc.py --doc $$F >/dev/null; done
	: argdoc: tests passed
	:
	(cd bin; python3 -m doctest -- ../tests/_test_subsh-typescript.txt)
	: doctest: tests passed
	:
	tests/_test_subsh.py >/dev/null
	: test_subsh: tests passed
	:
	: make: passed
	:

# copied from:  git clone https://github.com/pelavarre/pybashish.git
