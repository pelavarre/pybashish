# ~/.bashrc  # called after "~/.bash_profile" or without "~/.bash_profile"

source ~/.bashrc-theirs


# if [ ! "${_DOT_BASH_PROFILE_:-}" ]; then
#     source ~/.bash_profile
# fi
# TODO: settle all my hosts on "~/.bashrc" calls "~/.bash_profile" or not, like macOS

export OLDPS1="$PS1"  &&: # back up the default prompt here, as if it's screaming loud
export PS1="$(echo $PS1 |sed 's,\\\[\\033\[[^\\]*\\\],,g') "  # no color for no glare
if (( $SHLVL <= 1 )); then  # only to start with, in the top Shell per Terminal
    export PS1='\$ '  # no hostname, no pwd, etc etc
else
    export PS1='\[\e]0;\u@\h: \w\a\]\[\033[00;32m\]\u@\h\[\033[00m\]:\[\033[00;34m\]\w\[\033[00m\]\$ '
fi
# TODO: settle all my hosts on SHLVL <= 1, not macOS at SHLVL <= 2


# copied from:  git clone https://github.com/pelavarre/pybashish.git
