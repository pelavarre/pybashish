# ~/.zshrc  # called after "~/.zprofile" or without "~/.zprofile"


if [ ! "${_DOT_ZPROFILE_:-}" ]; then
    source ~/.zprofile
fi

export OLDPS1="$PS1"  &&: # back up the default prompt here, as if it's screaming loud
export PS1="$(echo $PS1 |sed 's,\\\[\\033\[[^\\]*\\\],,g') "  # no color for no glare
if (( $SHLVL <= 1 )); then  # only to start with, in the top Shell per Terminal
    export PS1='%# '  # no hostname, no pwd, etc etc
fi


setopt histverify  # a la Bash:  shopt -s histverify


function cd.py () {
  : : 'Print some kind of Help, else change the Sh Working Dir' : :
  if [ "$#" = 0 ]; then
    command cd.py
  elif [ "$#" = 1 ] && [ "$1" = "-" ]; then
    'cd' -
  elif [ "$#" = 1 ] && [[ "$1" =~ ^--h ]] && [[ "--help" =~ ^"$1" ]]; then
    command cd.py --help
  else
    'cd' "$(command cd.py --for-chdir $@)" && (dirs -p |head -1)
  fi
}


function echo.py {
  local xc=$?
  : : 'Print and clear the Process Exit Status ReturnCode, else print the Parms' : :
  if [ "$#" = 1 ] && [ "$1" = "--" ]; then
    command echo.py "+ exit $xc"
  else
    command echo.py "$@"
  fi
}


function git.py () {
  : : 'Show Git Status, else change the Sh Working Dir, else do other Git Work' : :
  if [ "$#" = 1 ] && [ "$1" = "--" ]; then
    command git.py --for-shproc --
  elif [ "$#" = 1 ] && [ "$1" = "cd" ]; then
    'cd' "$(command git.py --for-chdir $@)" && (dirs -p |head -1)
  else
    command git.py --for-shproc "$@"
  fi
}

function qcd () {
  'cd' "$(command git.py --for-chdir cd $@)" && (dirs -p |head -1)
}


# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/plavarre/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/plavarre/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
#if [ -f '/Users/plavarre/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/plavarre/google-cloud-sdk/completion.zsh.inc'; fi


# copied from:  git clone https://github.com/pelavarre/pybashish.git
