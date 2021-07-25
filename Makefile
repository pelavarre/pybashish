# pybashish/Makefile:  Run the self-test's


default: black flake8 test-once
	:
	git status |grep -v '^$$'
	:
	: consider
	:
	@echo 'git clean -ffxdq'
	@echo 'git commit --all --amend'
	@echo 'git status'
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
	. ~/bin/pips.source && black $$PWD/../pybashish/


FLAKE8_OPTS=--max-line-length=999 --ignore=E203,W503
# --max-line-length=999  # Black max line lengths over Flake8 max line lengths
# --ignore=E203  # Black '[ : ]' rules over Flake8 E203 whitespace before ':'
# --ignore=W503  # 2017 Pep 8 and Black over Flake8 W503 line break before binary op

flake8:
	. ~/bin/pips.source && flake8 ${FLAKE8_OPTS} $$PWD/../pybashish/


test-once:
	:
	rm -fr ../pybashish/.local/share/grep/files/
	bin/_grep1.py >/dev/null
	:
	: catch up with
	@echo 'bin/cspsh.py -f 2>&1 |sed '\''s,  *$$,,'\''  >tests/cspsh-f.txt'
	:
	bin/cspsh.py -fv >/dev/null 2>&1
	bash -c 'diff -burp tests/cspsh-f.txt <(bin/cspsh.py -f 2>&1)'
	:
	bin/doctestbash.py tests/ || (bin/doctestbash.py -vv tests/; exit 1)
	:
	for F in $(find bin/*.py -perm -0111); do bin/argdoc.py $$F >/dev/null && continue; echo "make: error:  python3 -m pdb bin/argdoc.py $$F" >&2; exit 1; done
	: argdoc: tests passed
	:
	(cd bin; python3 -m doctest -- ../tests/_test_subsh-typescript.txt)
	: doctest: tests passed
	:
	tests/_test_subsh.py >/dev/null
	: test_subsh: tests passed
	:
	rm -fr a b
	git ls-files |grep -vE '(.gitignore|__init__.py|README.md|tests/cspsh-f.txt)' >a
	git grep -l copied.from $$(git ls-files) >b
	diff -burp a b || :
	rm -fr a b
	:
	rm -fr ../pybashish/__pycache__
	rm -fr ../pybashish/bin/pyish.pyc
	rm -fr ../pybashish/bin/__pycache__
	git status --short --ignored
	:


grep-fixme:
	echo && echo && echo && git grep 'F'IXME |awk -F: '{ n=$$1; if (n != o) {o=n; print ""; print $$1":"}; $$1=""; print substr($$0, 2)}' |less -FRX


me:
	python3 ../pybashish/


# copied from:  git clone https://github.com/pelavarre/pybashish.git
