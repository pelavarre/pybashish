#
# files/python.bash:  Python
#

pylint --rcfile=/dev/null --reports=n --disable=locally-disabled ...
pylint --list-msgs
pylint --help-msg E0012  # bad-option-value  # not adopted above

python2 p.py
python2 -m pdb p.py
python3 p.py
python3 -m pdb p.py

python3 -i -c ''
: # >>> o = [[0, 1, 2], [], [3], [4, 5]]
: # >>> p = list(_ for listed in o for _ in listed)  # flatten/unravel list of lists
: # >>> p  # [0, 1, 2, 3, 4, 5]
: # >>> sum(o, list())  # [0, 1, 2, 3, 4, 5]  # flatten/unravel list of lists

#
# files/screen.bash:  Screen
#

screen --version

screen -h 7654321  # escape from $STY with more than 1074 lines of transcript
screen -h 7654321  # escape from $STY with more than 1074 lines of transcript
screen -X hardcopy -h ~/s.screen  # export transcript
screen -ls  # list sessions
screen -r  # attach back to any session suspended by ⌃A D detach
screen -r ...  # attach back to a choice of session suspended by ⌃A D detach
screen -r ...  # attach back to a choice of session suspended by ⌃A D detach

# copied from:  git clone https://github.com/pelavarre/pybashish.git
