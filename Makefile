# pybashish/Makefile:  Run the self-test's


default:
	@echo ''
	@echo 'ls'
	@echo ''
	@echo 'open https://github.com/pelavarre/pybashish#readme'
	@echo ''
	@echo 'make help'
	@echo 'make push'
	@echo ''
	@echo 'open https://twitter.com/intent/tweet?text=@PELaVarre'


push: style test
	git log --oneline --no-decorate -1
	git status --short --ignored
	git describe --always --dirty
	:
	: did you mean:  git push
	: press ⌃D to execute, or ⌃C to quit
	cat -
	git push


help:
	: # usage: make {black,default,flake8,me,pylint,style,test,tgz}
	: #
	: # work to add Code into GitHub PyBashIsh
	: #
	: # make verbs:
	: #
	: #     black    edit the Python sources here and below into the Black Style
	: #     default  style and test
	: #     flake8   review the Python sources here against most Flake8 Styles
	: #     me       run:  python3 ../pybashish/
	: #     pylint   review some Python sources against many PyLint Styles
	: #     style    make black, make flake8, and make pylint
	: #     test     run the tests here, just once
	: #     tgz      replace ../pybashish.tgz, but exclude '.*' from each Dir
	: #
	: # quirks:
	: #
	: #     prompts with "? ", unlike the "" of Bash "read" with no -p PROMPT
	: #
	: # examples:
	: #
	: #   open https://github.com/pelavarre/pybashish#readme
	: #
	: #   make  # show these examples and exit
	: #   make help  # show this help message and exit
	: #   make push  # restyle the Source, review it, and ask to push it
	: #
	: #   open https://twitter.com/intent/tweet?text=@PELaVarre


style: black flake8 pylint
	:


test:
	:
	rm -fr ../pybashish/.local/share/grep/files/
	bin/_grep1.py >/dev/null
	# :
	# : catch up with
	# @echo 'bin/cspsh.py -f 2>&1 |sed '\''s,  *$$,,'\''  >tests/cspsh-f.txt'
	# :
	# bin/cspsh.py -fv >/dev/null 2>&1
	# bash -c 'diff -burp tests/cspsh-f.txt <(bin/cspsh.py -f 2>&1)'
	# :
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
	rm -fr ../pybashish/bin/argdoc.pyc
	rm -fr ../pybashish/bin/py3ish.pyc
	rm -fr ../pybashish/bin/__pycache__
	git status --short --ignored
	:


tgz:
	cd .. && rm -fr pybashish.tgz && tar --exclude '.*' -czf pybashish.tgz pybashish/

me:
	python3 ../pybashish/


black:
	. ~/bin/pips.source && black $$PWD/../pybashish/


FLAKE8_OPTS=--max-line-length=999 --ignore=E203,W503

flake8:
	. ~/bin/pips.source && flake8 ${FLAKE8_OPTS} $$PWD/../pybashish/

# --max-line-length=999  # Black max line lengths over Flake8 max line lengths
# --ignore=E203  # Black '[ : ]' rules over Flake8 E203 whitespace before ':'
# --ignore=W503  # 2017 Pep 8 and Black over Flake8 W503 line break before binary op


PYLINT_OPTS=--rcfile=/dev/null --reports=n --score=n --disable=locally-disabled \
	-d W1514 -d R1734,R1735 -d C0103,C0201,C0209,C0302,C0325,C0411 \
	-d W0511 -d R0913,R0915

pylint:
	. ~/bin/pips.source && pylint ${PYLINT_OPTS} $$PWD/bin/argdoc.py
	. ~/bin/pips.source && pylint ${PYLINT_OPTS} $$PWD/bin/vi.py

#
# (unspecified-encoding)
# W1514: Using open without explicitly specifying an encoding
# nope, i keep simply reading text from a file simple, viva default "utf_8"
#

#
# R1734: Consider using [] instead of list() (use-list-literal)
# R1735: Consider using {} instead of dict() (use-dict-literal)
# nope, my old eyes appreciate the louder more explicit 'list()' mark
#

#
# (invalid-name)
# C0103: Variable name "..." doesn... conform to snake_case naming style
# nope, my one and two letter variable names do have a place, albeit only rarely
#
# (consider-iterating-dictionary)
# C0201: Consider iterating the dictionary directly instead of calling .keys()
# nope, explicit better than implicit, for keeping part separate from whole
#
# (consider-using-f-string)
# C0209: Formatting a regular string which could be a f-string'
# nope, going with F Strings always doesn't always make the source more clear
#
# (too-many-lines)
# C0302: Too many lines in module (.../1000)
# yes, but large files do have a place, albeit only rarely
#
# (superfluous-parens)
# C0325: Unnecessary parens after 'not' keyword
# nope, i applaud the clarity of 'if not (0 < i <= last):'
#
# (wrong-import-order)
# C0411: standard import "import ..." should be placed before "import __main__"
# nope, i give the win to Flake8
#

#
# (fixme)
# W0511: FIXME, TODO
#
# (too-many-arguments)
# R0913: Too many arguments
#
# (too-many-statements)
# R0915: Too many statementss
#


# copied from:  git clone https://github.com/pelavarre/pybashish.git
