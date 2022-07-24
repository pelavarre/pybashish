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


#
# Take in Sh Alias'es and Sh Function's from 'byobash/dotfiles/dot.byo.bashrc'
# todo: adjust correctly for Mac Zsh when not run by Bash
#


# for 'byobash/bin/zsh.py', in place of 'byobash/bin/bash.py'

function aliases () { echo + alias >&2 && alias; }

function funcs () {
  local L="functions |grep \$'^[^ \\t=]* ('"  # not Bash 'set |grep'
  echo + $L >&2
  echo
  functions |grep $'^[^ \t=]* ('
  echo
  echo ': # you might next like:  declare -f funcs'
}


# for 'byobash/bin/bash.py', distinct from 'byobash/bin/zsh.py'

function aliases () { echo + alias >&2 && alias; }

function funcs () {
  local L="set |grep '^[^ =]* ('"  # not Zsh 'set |grep'
  echo + $L >&2
  echo
  set |grep '^[^ =]* ('
  echo
  echo ': # you might next like:  declare -f funcs'
}


# for 'byobash/bin/byopyvm.py'

alias @='~/Public/byobash/bin/byopyvm.py buttonfile'

function = {
  : : 'Show Stack, else else do other Stack Work' : :
  if [ "$#" = 0 ]; then
      ~/Public/byobash/bin/byopyvm.py =
  else
      ~/Public/byobash/bin/byopyvm.py "$@"
  fi
}


# for 'byobash/bin/cd.py'

function - () { echo + cd - && cd - >/dev/null && (dirs -p |head -1); }
# some Bash says 'bash: cd: OLDPWD not set' and fails, till after first Cd

function .. () { echo + cd .. && cd .. && (dirs -p |head -1); }
# macOS Nov/2014 Bash 3.2.57 doesn't do:  shopt -p |grep autocd

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


# for 'byobash/bin/echo.py'

function echo.py {
  local xc=$?
  : : 'Print and clear the Process Exit Status ReturnCode, else print the Parms' : :
  if [ "$#" = 1 ] && [ "$1" = "--" ]; then
    command echo.py "+ exit $xc"
  else
    command echo.py "$@"
  fi
}

# Bash says 'not a valid identifier' if you quote the Function Name a la Zsh, but
# some Vi ':syntax on' sneers at the '}' brace closing an unquoted 'function echo.py'


# for 'byobash/bin/git.py'

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


#
#
#


# The next line updates PATH for the Google Cloud SDK.
if [ -f ~/google-cloud-sdk/path.zsh.inc ]; then . ~/google-cloud-sdk/path.zsh.inc; fi

# The next line enables shell command completion for gcloud.
#if [ -f ~/google-cloud-sdk/completion.zsh.inc ]; then . ~/google-cloud-sdk/completion.zsh.inc; fi


# copied from:  git clone https://github.com/pelavarre/pybashish.git
