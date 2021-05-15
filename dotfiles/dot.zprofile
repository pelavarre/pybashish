# ~/.zprofile  # called before "~/.zshrc" or not called

_DOT_ZPROFILE_=~/.zprofile  # don't export, to say if this file has been sourced

date



#
# Grow my keyboard
#


alias -- ':::'="(echo '⋮' |tee >(pbcopy))"


#
# Repair macOS Bluetooth after the next reboot
#


function -rehab-bluetooth () {
    : : help the next macOS boot find your Bluetooth widgets
    find ~/Library/Preferences -iname '*bluetooth*'
    ls -l $(find ~/Library/Preferences -iname '*bluetooth*')
    rm -i $(find ~/Library/Preferences -iname '*bluetooth*')
    find ~/Library/Preferences -iname '*bluetooth*'
}


#
# Calm my prompts
#


stty -ixon  &&: # define Control+S to undo Control+R, not XOFF

if dircolors >/dev/null 2>&1; then
    eval "$(dircolors <(dircolors -p |sed 's,1;,0;,g'))"  &&: # no bold for light mode
fi

function unix-filename-rubout () {
    : : approximately undo Tab-Completion
    local WORDCHARS="*?_[]~=&;\!#$%^(){}<>.-"
    zle backward-kill-word
}
zle -N unix-filename-rubout unix-filename-rubout  &&: # create new keymap
bindkey "^W" unix-filename-rubout  # define Control+W to nearly undo Tab-Completion

function ps1 () {
    : : toggle the prompt off and on
    if [ "$PS1" != '%# ' ]; then
        export PS1='%# '  # no hostname, no pwd, etc etc
    else
        export PS1="$OLDPS1"  # trust ~/.zshrc to init OLDPS1
    fi
}


#
# Configure Zsh (with "unsetopt" and "setopt" and so on)
#


setopt PRINT_EXIT_VALUE  &&: # stop silencing nonzero exit status

autoload -U edit-command-line  &&: # from ".oh-my-zsh/", else "No such shell function"
zle -N edit-command-line  &&: # create new keymap
bindkey '\C-x\C-e' edit-command-line  &&: # define ⌃X⌃E

setopt AUTO_CD  &&: # lacks Tab-completion, emulates Bash shopt -s autocd 2>/dev/null

# setopt INTERACTIVE_COMMENTS  # Zsh forwards #... as arg when not interactive


#
# Capture every input line (no drops a la Bash HISTCONTROL=ignorespace)
#


if [ ! "${HISTFILE+True}" ]; then  # emulate macOS Catalina, if HISTFILE unset
    HISTFILE=~/.zsh_history
    HISTSIZE=2000
    SAVEHIST=1000
fi

setopt EXTENDED_HISTORY  &&: # keep history over lotsa shells
unsetopt INC_APPEND_HISTORY  &&: # make room for INC_APPEND_HISTORY_TIME  # unneeded?
setopt INC_APPEND_HISTORY_TIME  &&: # feed well into  history -t '%Y-%m-%d %H:%M:%S'
setopt SHARE_HISTORY  &&: # reload fresh history after each INC_APPEND

alias -- --history="history -t '%b %d %H:%M:%S' 0"  &&:
# a la Bash HISTTIMEFORMAT='%b %d %H:%M:%S  ' history

_HISTORY_1_="history -t '%b %d %H:%M:%S' -1"
_LOGME_='echo "$$ $(whoami)@$(hostname):$(pwd)$('$_HISTORY_1_')" >>~/.zsh_command.log'
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND ; }$_LOGME_"
unset _HISTORY_1_
unset _LOGME_

type -f precmd >/dev/null
if [[ "$?" != 0 ]]; then
    function precmd () { eval "$PROMPT_COMMAND"; }
fi


#
# Push out and merge back in configuration secrets of Zsh, Bash, etc
#


function --dotfiles-dir () {
    : : say where to push out the dotfiles
    dotfiles=$(dirname $(dirname $(which zsh.py)))/dotfiles
    dotfiles=$(cd $dotfiles && dirs -p|head -1)
    echo $dotfiles
}

function --dotfiles-find () {
    : : name the files to push out, and do not name the files to hide

    echo .bash_profile
    echo .bashrc
    echo .python.py
    echo .zprofile
    echo .zshrc

    : : # echo .zprofile-zsecrets
}

function --dotfiles-backup () {
    : : back up the dot files - take mine, lose theirs
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "cp -p ~/$F $dotfiles/dot$F"
    done
    echo ": not backing up ~/.zprofile-zsecrets" >&2
}

function --dotfiles-restore () {
    : : restore the dot files  - take theirs, lose mine
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "echo cp -p $dotfiles/dot$F ~/$F"
    done
    touch ~/.zprofile-zsecrets
}


#
# Work with input and output history
#


function --pbpipe () { pbpaste |"$@" |tee >(pbcopy); }
alias ::='--pbpipe '  &&: # trailing space so its first arg can be an alias in Bash

function --source-one-search-hit () {
    : : trace and source a single hit as input, else trace the hits found

    local sourceable=$(mktemp)
    "$@" >"$sourceable"

    local xs=$?
    if [ $xs != 0 ]; then
        cat "$sourceable" >&2
    else
        local usage=''
        cat "$sourceable" |head -1 |grep '^usage: ' |read usage
        if [ "$usage" ]; then
            cat "$sourceable" >&2
        else

            cat "$sourceable" |sed 's,^,+ ,' >&2
            source "$sourceable"
            xs=$?

        fi
    fi

    rm "$sourceable"
    return $xs
}

function --search-histories () {
    : : search the curated input histories saved at '~/.histories*'

    : : find just the one line 'cd -' when given no args

    if [ $# = 0 ]; then
        echo 'cd -'
        return
    fi

    : : exit nonzero when multiple hits found, and when zero hits found

    local hits=$(mktemp)
    cat /dev/null ~/.histories* |grep "$@" >"$hits"
    local wcl=$(($(cat "$hits" |wc -l)))
    if [ "$wcl" != "1" ]; then
        echo "$wcl hits found by:  grep $@ ~/.histories*" >&2
        cat "$hits" >&2
        return 1
    fi

    : : print to stdout and exit zero when one hit found

    cat "$hits"
}

alias -- '-'='--source-one-search-hit --search-histories'
alias -- '--'='--search-histories'


#
# Work with dirs of files, and supply MM DD JQL HH MM SS date/time stamps
#


# alias -- '-'='cd -'
alias -- '..'='cd .. && (dirs -p |head -1)'

alias -- '?'="echo -n '? '>/dev/tty && cat -"  # press ⌃D for Yes, ⌃C for No

function --jqd () {
    : : guess the initials of the person at the keyboard
    echo 'jqd'  # J Q Doe
}  # redefined by ~/.zprofile-zsecrets

function --like-cp () {
    : : back up to date-author-time stamp
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; cp -ipR "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-do () {
    : : add date-author-time stamp as the last arg
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; "$@" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-mv () {
    : : back up to date-author-time stamp and remove
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; mv -i "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

alias l='ls -CF'  &&: # define "l", "la", and "ll" by Linux conventions
alias la='ls -A'
alias ll='ls -alF'

alias -- -cp=--like-cp
alias -- -do=--like-do
alias -- -ls='(set -xe; ls -alF -rt)'
alias -- -mv=--like-mv

# TODO: abbreviate $(ls -rt |tail -1)
# TODO: abbreviate $(ls -rtc |tail -1)


#
# Expand shorthand, but trace most of it and confirm some of it in advance
#



function --exec-echo-xe () {
    : : unquote and execute the args, but unquote and trace them first
    echo "+ $@" >&2
    source <(echo "$@")
}

function --authorize () {
    echo "$@" >&2
    echo 'press ⌃D to execute, or ⌃C to quit' >&2
    cat - >/dev/null
    echo '⌃D'
}

function --exec-echo-xe-maybe () {
    --authorize "did you mean:  $@"
    --exec-echo-xe "$@"
}


#
# Work with Git
#


function --exec-gcd-xe () {
    --exec-echo-xe 'cd $(git rev-parse --show-toplevel) && cd ./'$@' && dirs -p |head -1'
}

function --like-git-status () {
    : : Git Status for huge Git Repos - as in hulking, large, and slow
    (set -xe; git status -u no "$@" && git status && git status --short --ignored "$@")
}

alias -- -g=--like-git-status

alias -- -ga='--exec-echo-xe git add'
alias -- -gb='--exec-echo-xe git branch'
alias -- -gc='pwd && --exec-echo-xe-maybe git clean -ffxdq'
alias -- -gf='--exec-echo-xe git fetch'
alias -- -gd='--exec-echo-xe git diff'
alias -- -gg='--exec-echo-xe git grep'
alias -- -gl='--exec-echo-xe git log'
alias -- -gr='--exec-echo-xe git rebase'
alias -- -gs='--exec-echo-xe git show'

alias -- -gbq='--exec-echo-xe "git branch |grep '\''[*]'\''"'
alias -- -gca='--exec-echo-xe git commit --amend'
alias -- -gcd=--exec-gcd-xe
alias -- -gco='--exec-echo-xe git checkout'  # especially:  gco -
alias -- -gdh='--exec-echo-xe git diff HEAD~1'
alias -- -gfr='--exec-echo-xe "(set -xe; git fetch && git rebase)"'
alias -- -ggl='--exec-echo-xe git grep -l'  # --files-with-matches
alias -- -gl1='--exec-echo-xe git log --decorate -1'
alias -- -glf='--exec-echo-xe git ls-files'
alias -- -glg='--exec-echo-xe git log --no-decorate --oneline --grep'
alias -- -glq='--exec-echo-xe git log --no-decorate --oneline -9'
alias -- -grh='dirs -p |head -1 && --exec-echo-xe-maybe git reset --hard'
alias -- -gri='--exec-echo-xe git rebase -i --autosquash HEAD~9'
alias -- -grl='--exec-echo-xe git reflog'
alias -- -grv='--exec-echo-xe git remote -vvv'

alias -- -gcaa='--exec-echo-xe git commit --all --amend'
alias -- -gcaf='--exec-echo-xegit commit --all --fixup'
alias -- -gdno='--exec-echo-xe git diff --name-only'
alias -- -glq0='--exec-echo-xe git log --decorate --oneline'
alias -- -glqv='--exec-echo-xe git log --decorate --oneline -9'
alias -- -grhu='dirs -p |head -1 && --exec-echo-xe-maybe git reset --hard @{upstream}'
alias -- -gsno="--exec-echo-xe git show --name-only --pretty=''"
alias -- -gssn='--exec-echo-xe git shortlog --summary --numbered'

alias -- -gcafh='--exec-echo-xe git commit --all --fixup HEAD'
alias -- -gdno1='--exec-echo-xe git diff --name-only HEAD~1'
alias -- -glqv0='--exec-echo-xe git log --no-decorate --oneline'

# TODO: git log -G regex file.ext # grep the changes
# TODO: git log -S regex file.ext # grep the changes for an odd number (PickAxe)


#
# Work with Python
#


alias -- -p='( set -xe; python3 -i ~/.python.py )'
alias -- -p3="( set -xe; python3 -i ~/.python.py 'print(sys.version.split()[0])' )"
alias -- -p2="( set -xe; python2 -i ~/.python.py 'print(sys.version.split()[0])' )"


#
# Define first call of each Pip tool to activate its own virtual env and exit nonzero
#


function --activate-bin-source () {
    local F=$1
    echo INSTALLING $F >&2
    source ~/bin/$F.source
    return 1
}

for F in $(cd ~/bin; ls -1 *.source |sed 's,[.]source$,,'); do
    source <(echo "function $F () { unset -f $F; --activate-bin-source $F; }")
done
# TODO: cope when ~/bin/*.source not found

#
# for instance, set up like so
#
#   mkdir -p ~/.venvs/
#   rm -fr ~/.venvs/pip/
#
#   cd ~/.venvs/
#   python3 -m venv --prompt PIP pip
#   source pip/bin/activate
#   pip freeze --all |grep -v pkg-resources==0.0.0 |wc -l  # like 2
#   pip install --upgrade wheel
#   pip install --upgrade pip  # essentials:  wheel, pip, black, requests, ...
#   pip freeze --all |grep -v pkg-resources==0.0.0 |wc -l  # like 3
#
#   rm -fr ~/bin/pip.source
#   ln -s ~/.venvs/pip/bin/activate ~/bin/pip.source
#   logout
#
#   pip --version  # call once to activate
#   pip --version  # call again to work while activated
#


#
# Alias first words for pasting back printed lines as input
#


alias -- 'A'=vim  # such as git status:  A  dotfiles/dot.zprofile
alias -- 'M'=vim  # such as git status:  M dotfiles/dot.zprofile

alias -- '+++'=--feed-back-git-diff-plus
function --feed-back-git-diff-plus () {
    : : edit a file mentioned as changed in the style of Git Diff
    local filename="$(echo $1 |cut -d/ -f2-)"
    shift
    (set -xe; vim $filename $@)
}  # such as:  +++ b/dotfiles/dot.zprofile +185


#
# Copy in my secrets at work, such as
#
#   alias 0, 1, 2, ..., a, b, c, ... aa, bb, cc ... etc for reaching hosts I like
#   alias first words for pasting back printed lines as input
#   patch tools into PATH
#   pushd my favorite dirs
#


export PATH="${PATH:+$PATH:}$HOME/bin"
source ~/.zprofile-zsecrets
echo "$(dirs -p |head -1)/"


#
# Fall through to patches added onto this source file later, and then to ~/.zshrc
#


# source ~/.zshrc  # sometimes needed in Bash as:  source ~/.bashrc


# above copied from:  git clone https://github.com/pelavarre/pybashish.git
