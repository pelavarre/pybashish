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
