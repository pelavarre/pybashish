# ~/.bash_profile  # called before "~/.bashrc" or not called

_DOT_BASH_PROFILE_=~/.bash_profile  # don't export, to say if this file has been sourced


#
# Grow my keyboard
#


alias -- ':::'="(echo '⋮' |tee >(pbcopy))"


#
# Repair macOS Bluetooth after the next reboot
#


function -rehab-bluetooth () {
    : :: help the next macOS boot find your Bluetooth widgets
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

function ps1 () {
    : :: toggle the prompt off and on
    if [ "$PS1" != '\$ ' ]; then
        export PS1='\$ '  # no hostname, no pwd, etc etc
    else
        export PS1="$OLDPS1"  # trust ~/.bashrc to init OLDPS1
    fi
}


#
# Configure Bash (with "shopt" and so on)
#


if shopt -p |grep autocd  >/dev/null; then shopt -s autocd; fi


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
    : :: say where to push out the dotfiles
    dotfiles=$(dirname $(dirname $(which bash.py)))/dotfiles
    dotfiles=$(cd $dotfiles && dirs -p|head -1)
    echo $dotfiles
}

function --dotfiles-find () {
    : :: name the files to push out, and do not name the files to hide

    echo .bash_profile
    echo .bashrc
    echo .emacs
    echo .pipe.hits
    echo .python.py
    echo .vimrc
    echo .zprofile
    echo .zshrc

    : :: # echo .zprofile-zsecrets
}

function --dotfiles-backup () {
    : :: back up the dot files - take mine, lose theirs
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "cp -p ~/$F $dotfiles/dot$F"
    done
    echo ": not backing up ~/.bash_profile_secrets" >&2
}

function --dotfiles-restore () {
    : :: restore the dot files  - take theirs, lose mine
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "echo cp -p $dotfiles/dot$F ~/$F"
    done
    touch ~/.zprofile-zsecrets
}


#
# Work with input and output history
#


alias -- '-'="--source-lucky-search-hit --search-hits 'cd -'"
alias -- '--'="--search-hits 'cd -'"

function , () {
    : :: capture os copy-paste buffer, and pipe it out
    echo '+ pbpaste |tee ~/.pbpaste.history' >&2
    pbpaste |tee ~/.pbpaste.history | \
        --source-lucky-search-hit --search-hits 'cat -' "$@"
}

function ,, () {
    : :: apply filter inside the os copy-paste buffer, and capture result

    echo '+ pbpaste |tee ~/.pbpaste.history' >&2
    pbpaste |tee ~/.pbpaste.history | \
        --source-lucky-search-hit --search-hits 'cat -' "$@" >~/.pbcopy.history
    local xs=$?
    if [ $xs = 0 ]; then
        echo '+ tee ~/.pbcopy.history |pbcopy' >&2
        cat ~/.pbcopy.history |pbcopy
        xs=$?
    fi
    return $xs
}

function --source-lucky-search-hit () {
    : :: trace and source a strong hit as input, else trace the weak hits

    : search

    local sourceable=$(mktemp)
    "$@" >"$sourceable"
    local xs=$?

    : quit now if search failed

    if [ $xs != 0 ]; then
        cat "$sourceable" >&2
    else

        : forward usage with zeroed exit status, if usage

        local usage=''
        cat "$sourceable" |head -1 |grep '^usage: ' |read usage
        if [ "$usage" ]; then
            cat "$sourceable" >&2
        else

            : forward strong hit as input

            cat "$sourceable" |sed 's,^,+ ,' >&2
            source "$sourceable"

        fi
    fi

    rm "$sourceable"
    return $xs
}

function --search-hits () {
    : :: search the curated input hits saved at '~/.*.hits'

    : find first arg when given no search key

    if [ $# = 1 ]; then
        echo "$1"
        return
    fi

    shift

    : exit nonzero when multiple hits found, or zero hits found

    local hits=$(mktemp)
    cat /dev/null ~/.*.hits |grep "$@" >"$hits"
    local wcl=$(($(cat "$hits" |wc -l)))
    if [ "$wcl" != "1" ]; then
        echo "$wcl hits found by:  grep $@ ~/.*.hits" >&2
        cat "$hits" >&2
        return 1
    fi

    : forward to stdout and exit zero when exactly one hit found

    cat "$hits"
}


#
# Work with dirs of files, and supply MM DD JQL HH MM SS date/time stamps
#


# alias -- '-'='cd -'
alias -- '..'='cd .. && (dirs -p |head -1)'

alias -- '?'="echo -n '? '>/dev/tty && cat -"  # press ⌃D for Yes, ⌃C for No

function --jqd () {
    : :: guess the initials of the person at the keyboard
    echo 'jqd'  # J Q Doe
}  # redefined by ~/.zprofile-zsecrets

function --like-cp () {
    : :: back up to date-author-time stamp
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; cp -ipR "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-do () {
    : :: add date-author-time stamp as the last arg
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; "$@" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-mv () {
    : :: back up to date-author-time stamp and remove
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
    : :: unquote and execute the args, but unquote and trace them first
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
    : :: Git Status for huge Git Repos - as in hulking, large, and slow
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
alias -- -gcaf='--exec-echo-xe git commit --all --fixup'
alias -- -gcam='--exec-echo-xe git commit --all -m WIP-$(basename $(pwd))'
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
# Work with Emacs, Python, Vim, and such
#


alias -- -e='emacs -nw --no-splash'
alias -- -v='vim'

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
    : :: edit a file mentioned as changed in the style of Git Diff
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

if dircolors >/dev/null 2>&1; then
    eval "$(dircolors <(dircolors -p |sed 's,1;,0;,g'))"  &&: # no bold for light mode
fi


# above copied from:  git clone https://github.com/pelavarre/pybashish.git
