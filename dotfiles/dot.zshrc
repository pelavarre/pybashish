# ~/.zshrc  # called after "~/.zprofile" or without "~/.zprofile"


if [ ! "${_DOT_ZPROFILE_:-}" ]; then
    source ~/.zprofile
fi

export OLDPS1="$PS1"  &&: # back up the default prompt here, as if it's screaming loud
export PS1="$(echo $PS1 |sed 's,\\\[\\033\[[^\\]*\\\],,g') "  # no color for no glare
if (( $SHLVL <= 1 )); then  # only to start with, in the top Shell per Terminal
    export PS1='%# '  # no hostname, no pwd, etc etc
fi


# copied from:  git clone https://github.com/pelavarre/pybashish.git
