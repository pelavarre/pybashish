# ~/.bashrc  # called after "~/.bash_profile" or without "~/.bash_profile"

source ~/.bashrc-theirs

if [ "$(uname)" = Darwin ]; then
    if [ ! "${_DOT_BASH_PROFILE_:-}" ]; then
        echo + source ~/.bash_profile
        source ~/.bash_profile
    fi
fi
# TODO: work up better answer for ~/.bash_profile skipped by macOS Zsh

export OLDPS1="$PS1"  &&: # back up the default prompt here, as if it's screaming loud
export PS1="$(echo $PS1 |sed 's,\\\[\\033\[[^\\]*\\\],,g') "  # no color for no glare
if (( $SHLVL <= 1 )); then  # only to start with, in the top Shell per Terminal
    export PS1='\$ '  # no hostname, no pwd, etc etc
else
    export PS1='\[\e]0;\u@\h: \w\a\]\[\033[00;32m\]\u@\h\[\033[00m\]:\[\033[00;34m\]\w\[\033[00m\]\$ '
fi
# TODO: settle all my hosts on SHLVL <= 1, not macOS at SHLVL <= 2


shopt -s histverify  # a la Zsh:  setopt histverify


function = {
  : : 'Show Stack, else else do other Stack Work' : :
  if [ "$#" = 0 ]; then
      ~/Public/byobash/bin/byopyvm.py ls
  else
      ~/Public/byobash/bin/byopyvm.py "$@"
  fi
}


function - () { echo + cd - && cd - >/dev/null && (dirs -p |head -1); }
# Bash will say 'bash: cd: OLDPWD not set' and fail, till after Cd

function .. () { echo + cd .. && cd .. && (dirs -p |head -1); }

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


# copied from:  git clone https://github.com/pelavarre/pybashish.git
