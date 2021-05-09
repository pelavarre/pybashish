# ~/.bash_profile  # called before "~/.bashrc" or not called

_DOT_BASH_PROFILE_=~/.bash_profile  # don't export, to say if this file has been sourced


#
# Grow my keyboard
#

alias -- '::'="(set -xeuo pipefail; echo '⋮' |tee >(pbcopy))"


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

eval "$(dircolors <(dircolors -p | sed 's,1;,0;,g'))"  &&: # no bold for light mode

function ps1 () {
    : : toggle the prompt off and on
    if [ "$PS1" != '\$ ' ]; then
        export PS1='\$ '  # no hostname, no pwd, etc etc
    else
        export PS1="$OLDPS1"  # trust ~/.bashrc to init OLDPS1
    fi
}


#
# Configure Bash
#

if shopt -p | grep autocd  >/dev/null; then shopt -s autocd; fi


#
# Capture every input line (no drops a la Bash HISTCONTROL=ignorespace)
#

HISTTIMEFORMAT='%b %d %H:%M:%S  '

_LOGME_='echo "$$ $(whoami)@$(hostname):$(pwd)$(history 1)" >>~/.bash_command.log'
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND ; }$_LOGME_"
unset _LOGME_


#
# Push out and merge back in configuration secrets of Bash, Zsh, etc
#

function --dotfiles-dir () {
    : : say where to push out the dotfiles
    dotfiles=$(dirname $(dirname $(which bash.py)))/dotfiles
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
        --exec-xe "cp -p ~/$F $dotfiles/dot$F"
    done
    echo ": not backing up ~/.bash_profile_secrets" >&2
}

function --dotfiles-restore () {
    : : restore the dot files  - take theirs, lose mine
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-xe "echo cp -p $dotfiles/dot$F ~/$F"
    done
    touch ~/.zprofile-zsecrets
}


#
# Work with command line input history
#

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
# Supply MM DD JQL HH MM SS date/time stamps
#

# alias -- '-'='cd -'
alias -- '..'='cd .. && (dirs -p |head -1)'

function --jqd () {
    : : guess the initials of the person at the keyboard
    echo 'jqd'  # J Q Doe
}  # redefined by ~/.zprofile-zsecrets

function --like-cp() {
    : : back up to date-author-time stamp
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; cp -ip "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-do() {
    : : add date-author-time stamp as the last arg
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; "$@" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-mv() {
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


#
# Often trace and sometimes confirm expansions of shorthand
#

alias -- '?'="echo -n '? '>/dev/tty && cat -"  # press ⌃D for Yes, ⌃C for No

function --exec-xe () {
    : : execute the args, but trace them first
    echo "+ $@" >&2  &&: # less decoration than "$PS4"
    source <(echo "$@")
}

function --exec-xe-maybe () {
    : : execute the args, but trace them first and press ⌃D to proceed
    echo "did you mean:  $@" >&2
    echo 'press ⌃D to execute, or ⌃C to quit' >&2
    cat - >/dev/null
    echo '⌃D'
    echo "+ $@" >&2  &&: # echo like "$PS4", but more calmly
    source <(echo "$@")
}


#
# Work with Git
#

function --like-git-status() {
    : : Git Status for hulking large slow Git repos
    (set -xe; git status -u no "$@" && git status && git status --short --ignored "$@")
}

alias -- -g=--like-git-status

alias -- -ga='--exec-xe git add'
alias -- -gb="--exec-xe git branch"
alias -- -gc="pwd && --exec-xe-maybe 'git clean -ffxdq'"
alias -- -gf='--exec-xe git fetch'
alias -- -gd='--exec-xe git diff'
alias -- -gg='--exec-xe git grep'
alias -- -gl='--exec-xe git log --decorate --oneline -9'
alias -- -gr='--exec-xe git rebase'
alias -- -gs='--exec-xe git show'

alias -- -gbq="--exec-xe \"git branch |grep '[*]'\""
alias -- -gca='--exec-xe git commit --amend'
alias -- -gcd='--exec-xe '\''cd $(git rev-parse --show-toplevel) && dirs -p |head -1'\'
alias -- -gco='--exec-xe git checkout'  # especially:  gco -
alias -- -gd1='--exec-xe git diff HEAD~1'
alias -- -gfr="--exec-xe '(set -xe; git fetch && git rebase)'"
alias -- -gl1='--exec-xe git log --decorate -1'
alias -- -glf='--exec-xe git ls-files'
alias -- -glq='--exec-xe git log --no-decorate --oneline -9'
alias -- -gri='--exec-xe git rebase -i --autosquash HEAD~9'
alias -- -grl='--exec-xe git reflog'
alias -- -grv='--exec-xe git remote -vvv'

alias -- -gcaa='--exec-xe git commit --all --amend'
alias -- -grhu="pwd && --exec-xe-maybe 'git reset --hard @{upstream}'"
alias -- -gsno="--exec-xe git show --name-only --pretty=''"
alias -- -gssn='--exec-xe git shortlog --summary --numbered'

alias -- -gdno1='--exec-xe git diff --name-only HEAD~1'


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
source ~/.bash_profile_secrets
echo "$(dirs -p |head -1)/"


#
# Fall through to patches added onto this source file later, and then to " ~/.bashrc"
#

source ~/.bashrc


# above copied from:  git clone https://github.com/pelavarre/pybashish.git
