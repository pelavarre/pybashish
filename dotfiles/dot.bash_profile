# ~/.bash_profile  # called before "~/.bashrc" or not called

_DOT_BASH_PROFILE_=~/.bash_profile  # don't export, to say if this file has been sourced

date

# TODO: contrast with Ubuntu ~/.bash_aliases


#
# Grow my keyboard
#


alias -- '::'="(echo '⌃ ⌥ ⇧ ⌘ ⎋ ⇥ ⋮' |tee >(pbcopy))"



#
# Repair macOS Bluetooth after the next reboot
#


function --rehab-bluetooth () {
    : :: 'help the next macOS boot find your Bluetooth widgets'
    find ~/Library/Preferences -iname '*bluetooth*'
    ls -l $(find ~/Library/Preferences -iname '*bluetooth*')
    rm -i $(find ~/Library/Preferences -iname '*bluetooth*')
    find ~/Library/Preferences -iname '*bluetooth*'
}


#
# Calm my prompts
#


stty -ixon  && : 'define Control+S to undo Control+R, not XOFF'

if dircolors >/dev/null 2>&1; then
    eval $(dircolors <(dircolors -p |sed 's,1;,0;,g'))  && : 'no bold for light mode'
fi

function ps1 () {
    : :: 'toggle the prompt off and on'
    if [ "$PS1" != '\$ ' ]; then
        export PS1='\$ '  # no hostname, no pwd, etc etc
    else
        export PS1="$OLDPS1"  # trust ~/.bashrc to init OLDPS1
    fi
}


#
# Expand shorthand, but trace most of it and confirm some of it in advance
#


function --exec-echo-xe () {
    : :: 'unquote and execute the args, but unquote and trace them first'
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
# Configure Bash (with "shopt" and so on)
#


if shopt -p |grep autocd  >/dev/null; then shopt -s autocd; fi


#
# Capture every input line (no drops a la Bash HISTCONTROL=ignorespace)
#

_LOGME_='echo "$$ $(whoami)@$(hostname):$(pwd)$(history 1)" >>~/.bash_command.log'
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND ; }$_LOGME_"
unset _LOGME_

alias -- -h=--history
HISTTIMEFORMAT='%b %d %H:%M:%S  '
function --history () {
    --exec-echo-xe "history"  # a la Zsh:  history -t '%b %d %H:%M:%S' 0"
}
alias -- --more-history="--exec-echo-xe 'cat ~/.*command*log* |grep'"
alias -- --null="--exec-echo-xe 'cat - >/dev/null'"


#
# Push out and merge back in configuration secrets of Bash, Zsh, etc
#


function --dotfiles-dir () {
    : :: 'say where to push out the dotfiles'
    dotfiles=$(dirname $(dirname $(which bash.py)))/dotfiles
    dotfiles=$(cd $dotfiles && dirs -p|head -1)
    echo $dotfiles
}

function --dotfiles-find () {
    : :: 'name the files to push out, and do not name the files to hide'

    echo .bash_profile
    echo .bashrc
    echo .emacs
    echo .pipe.luck
    echo .python.py
    echo .vimrc
    echo .zprofile
    echo .zshrc

    : 'do Not echo ".bash_profile_secrets" because local per host'
}

function --dotfiles-backup () {
    : :: 'back up the dot files - take mine, lose theirs'
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "cp -p ~/$F $dotfiles/dot$F"
    done
    echo ": not backing up ~/.bash_profile_secrets" >&2
}

function --dotfiles-restore () {
    : :: 'restore the dot files  - take theirs, lose mine'
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "echo cp -p $dotfiles/dot$F ~/$F"
    done
    touch ~/.bash_profile_secrets
}


#
# Abbreviate pipes
#

function a () {
    local shline=$(--awk $@)
    echo "+ $shline" >&2
    eval $shline
}

function --awk () {
    if [ $# = 0 ]; then
        echo "awk '{print \$NF}'"
    elif [[ "$1" =~ ^[A-Za-z0-9_]+$ ]]; then
        echo "awk '{print \$$1}'"
    elif [ $# = 1 ]; then
        echo "awk -F'$1' '{print \$NF}'"
    elif [[ "$2" =~ ^[A-Za-z0-9_]+$ ]]; then
        echo "awk -F'$1' '{print \$$2}'"
    else
        local sep="$1"
        shift
        echo "awk -F'$sep' '{print $@}'"
    fi
}

function --cd () {
    if [ $# != 0 ]; then
        cd "$@"
    fi
    echo "+ cd $(dirs -p |head -1)/"
}

function g () {
    --grep "$@"
}

function --grep () {
    : :: 'search for patterns, but ignore case & order, and let "-" dash start patterns'
    if [ $# = 0 ]; then
        echo + grep . >&2
        grep .
    else
        local pipe="grep -i -- $1"
        shift
        while [ $# != 0 ]; do
            pipe="$pipe |grep -i -- $1"
            shift
        done
        echo + "$pipe" >&2
        eval "$pipe"
    fi
}

function --grepq () {
    : :: 'like --grep but without trace of the pipe'
    if [ $# = 0 ]; then
        grep .
    else
        local pipe="grep -i -- $1"
        shift
        while [ $# != 0 ]; do
            pipe="$pipe |grep -i -- $1"
            shift
        done
        eval "$pipe"
    fi
}

function --pwd () {
    echo "+ cd $(dirs -p |head -1)/"
}


#
# Work with input and output history
#


alias -- ','="--take-pbpipe-from --search-dotluck 'expand.py'"
alias -- ',,'="--pbpaste-dotluck 'cat.py -entv'"
alias -- '-'="--take-input-from --search-dotluck 'cd -'"
alias -- '--'="--search-dotluck 'cd -'"
alias -- '@'="--pbpipe 'expand.py'"
alias -- '@@'="--pbpaste 'cat.py -entv'"

function --pbpaste () {
    : :: 'capture and pipe out through tail args, else pipe out through head arg'

    if [ $# = 1 ]; then
        echo + "pbpaste |tee ~/.pbpaste |$1" >&2
        pbpaste |tee ~/.pbpaste |eval "$1"
        return $?
    fi

    shift

    echo + "pbpaste |tee ~/.pbpaste |$@" >&2
    pbpaste |tee ~/.pbpaste |$@
}

function --pbpipe () {
    : :: 'capture and pipe through tail args, else pipe through head arg'

    if [ $# = 1 ]; then
        echo + "pbpaste |tee ~/.pbpaste |$1 |tee ~/.pbcopy |pbcopy" >&2
        pbpaste |tee ~/.pbpaste |eval "$1" |tee ~/.pbcopy |pbcopy
        return $?
    fi

    shift

    echo + "pbpaste |tee ~/.pbpaste |$@ |tee ~/.pbcopy |pbcopy" >&2
    pbpaste |tee ~/.pbpaste |$@ |tee ~/.pbcopy |pbcopy
}

function --pbpaste-dotluck () {
    : :: 'capture and pipe out through tail args, else pipe out through head arg'

    if [ $# = 1 ]; then
        --pbpaste "$@"
        return $?
    fi

    local else_hit="$1"
    shift

    echo + "pbpaste |tee ~/.pbpaste |- $@" >&2
    pbpaste |tee ~/.pbpaste |--take-input-from --search-dotluck "$else_hit" "$@"
}

function --take-pbpipe-from () {
    : :: 'trace and source a strong hit as pb filter, else trace the weak hits'

    : 'search'

    local sourceable=$(mktemp)
    "$@" >"$sourceable"
    local xs=$?

    : 'quit now if search failed'

    if [ $xs != 0 ]; then
        cat "$sourceable" >&2
    else

        : 'forward usage with zeroed exit status, if usage'

        local usage=''
        cat "$sourceable" |head -1 |grep '^usage: ' |read usage
        if [ "$usage" ]; then
            cat "$sourceable" >&2
        else

            : 'forward strong hit as pb filter'

            echo '+ inside (pbpaste |tee ~/.pbpaste |... |tee ~/.pbcopy |pbcopy) do' >&2
            cat "$sourceable" |sed 's,^,+     ,' >&2
            pbpaste |tee ~/.pbpaste |source "$sourceable" |tee ~/.pbcopy |pbcopy

        fi
    fi

    rm "$sourceable"
    return $xs
}

function --take-input-from () {
    : :: 'trace and source a strong hit as input, else trace the weak hits'

    : 'search'

    local sourceable=$(mktemp)
    "$@" >"$sourceable"
    local xs=$?

    : 'quit now if search failed'

    if [ $xs != 0 ]; then
        cat "$sourceable" >&2
    else

        : 'forward usage with zeroed exit status, if usage'

        local usage=''
        cat "$sourceable" |head -1 |grep '^usage: ' |read usage
        if [ "$usage" ]; then
            cat "$sourceable" >&2
        else

            : 'forward strong hit as input'

            cat "$sourceable" |sed 's,^,+ ,' >&2
            source "$sourceable"

        fi
    fi

    rm "$sourceable"
    return $xs
}

function --take-input-twice-from () {
    : :: 'trace and eval a strong hit as input, else trace the weak hits'

    : 'search once to capture hits, search again to capture exit status'

    local input=$($@)
    $@
    local xs=$?

    : 'quit now if search failed'

    if [ $xs != 0 ]; then
        echo "$input" >&2
    else

        : 'forward usage with zeroed exit status, if usage'

        local usage=''
        echo "$input" |head -1 |grep '^usage: ' |read usage
        if [ "$usage" ]; then
            echo "$input" >&2
        else

            : 'forward strong hit as input'

            echo "$input" |sed 's,^,+ ,' >&2
            eval "$input"

        fi
    fi

    return $xs
}

function --search-dotluck () {
    : :: 'search the curated input luck saved at "~/.*.luck"'

    : 'find first arg when given no search key'

    if [ $# = 1 ]; then
        echo "$1"
        return
    fi

    shift

    : 'exit nonzero when multiple hits found, or zero hits found'

    local hits=$(mktemp)
    cat /dev/null ~/.*.luck |--grepq "$@" >"$hits"
    local wcl=$(($(cat "$hits" |wc -l)))
    if [ "$wcl" != "1" ]; then
        echo "$wcl hits found by:  --grep $@ ~/.*.luck" >&2
        cat "$hits" >&2
        return 1
    fi

    : 'forward to stdout and exit zero when exactly one hit found'

    cat "$hits"
}
# TODO: solve 'search-dotluck' with 'eval', without 'mktemp'


#
# Work with dirs of files, and supply MM DD JQL HH MM SS date/time stamps
#


# alias -- '-'='cd -'
alias -- '..'='cd .. && (dirs -p |head -1)'

alias -- '?'="echo -n '? '>/dev/tty && cat -"  # press ⌃D for Yes, ⌃C for No

function --jqd () {
    : :: 'guess the initials of the person at the keyboard'
    echo 'jqd'  # J Q Doe
}  # redefined by ~/.bash_profile_secrets

function --like-cp () {
    : :: 'back up to date-author-time stamp'
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; cp -ipR "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-do () {
    : :: 'add date-author-time stamp as the last arg'
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; "$@" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function --like-mv () {
    : :: 'back up to date-author-time stamp and remove'
    local F="$1"
    local JQD=$(--jqd)
    (set -xe; mv -i "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

alias l='ls -CF'  && : 'define "l", "la", and "ll" by Linux conventions'
alias la='ls -A'
alias ll='ls -alF'

alias -- -cp=--like-cp
alias -- -do=--like-do
alias -- -ls='(set -xe; ls -alF -rt)'
alias -- -mv=--like-mv

# TODO: abbreviate $(ls -rt |tail -1)
# TODO: abbreviate $(ls -rtc |tail -1)


#
# Work with Git
#


alias -- -g=--git

alias -- -ga='--exec-echo-xe git add'
alias -- -gb='--exec-echo-xe git branch'
alias -- -gc='--exec-echo-xe git commit'
alias -- -gf='--exec-echo-xe git fetch'
alias -- -gd='--exec-echo-xe git diff'
alias -- -gg='--exec-echo-xe git grep'
alias -- -gl='--exec-echo-xe git log'
alias -- -gr='--exec-echo-xe git rebase'
alias -- -gs='--exec-echo-xe git show'

alias -- -gba='--exec-echo-xe git branch --all'
alias -- -gbq='--exec-echo-xe "git branch |grep '\''[*]'\''"'
alias -- -gca='--exec-echo-xe git commit --amend'
alias -- -gcd=--git-chdir
alias -- -gcf=--git-commit-fixup
alias -- -gcl='pwd && --exec-echo-xe-maybe git clean -ffxdq'
alias -- -gco='--exec-echo-xe git checkout'  # especially:  gco -
alias -- -gcp='--exec-echo-xe git cherry-pick'
alias -- -gdh=--git-diff-head
alias -- -gfr='--exec-echo-xe "(set -xe; git fetch && git rebase)"'
alias -- -ggl='--exec-echo-xe git grep -l'  # --files-with-matches
alias -- -gl1='--exec-echo-xe git log --decorate -1'
alias -- -glf=--git-ls-files
alias -- -glg='--exec-echo-xe git log --no-decorate --oneline --grep'
alias -- -glq='--exec-echo-xe git log --no-decorate --oneline -19'
alias -- -gls='--exec-echo-xe git log --stat'
alias -- -grh='dirs -p |head -1 && --exec-echo-xe-maybe git reset --hard'
alias -- -gri=--git-rebase-interactive
alias -- -grl='--exec-echo-xe git reflog'
alias -- -grv='--exec-echo-xe git remote -vvv'
alias -- -gs1='--git-show-conflict :1'
alias -- -gs2='--git-show-conflict :2'
alias -- -gs3='--git-show-conflict :3'

alias -- -gcaa='--exec-echo-xe git commit --all --amend'
alias -- -gcaf=--git-commit-all-fixup
alias -- -gcam='--exec-echo-xe git commit --all -m WIP-$(basename $(pwd))'
alias -- -gcls='pwd && --exec-echo-xe-maybe sudo git clean -ffxdq'
alias -- -gdno='--exec-echo-xe git diff --name-only'
alias -- -glq0='--exec-echo-xe git log --no-decorate --oneline'
alias -- -glqv='--exec-echo-xe git log --decorate --oneline -19'
alias -- -grhu='dirs -p |head -1 && --exec-echo-xe-maybe git reset --hard @{upstream}'
alias -- -gsno="--exec-echo-xe git show --name-only --pretty=''"
alias -- -gssi='--exec-echo-xe git status --short --ignored'
alias -- -gssn='--exec-echo-xe git shortlog --summary --numbered'
alias -- -gsun='--exec-echo-xe git status --untracked-files=no'

alias -- -gdno1='--exec-echo-xe git diff --name-only HEAD~1'
alias -- -glqv0='--exec-echo-xe git log --decorate --oneline'
alias -- -gpfwl='dirs -p |head -1 && --exec-echo-xe-maybe git push --force-with-lease'


# TODO: solve dry run of -gco -  => git log --oneline --decorate -1 @{-1}
# TODO: version test results by:  git describe --always --dirty

# TODO: solve -gg -ggl etc with quoted args
# TODO: give us -gg as -i and -ggi as not -i

# TODO: git log -G regex file.ext # grep the changes
# TODO: git log -S regex file.ext # grep the changes for an odd number (PickAxe)
# TODO: --pretty=format:'%h %aE %s'  |cat - <(echo) |sed "s,@$DOMAIN,,"
# TODO: git blame/log --abbrev


function --git () {
    : :: 'Git Status for huge Git Repos - as in hulking, large, and slow'

    echo + >&2
    if --exec-echo-xe git status --untracked-files=no "$@"; then

        echo + >&2
        if --exec-echo-xe git status "$@"; then

            if [ $# = 0 ]; then
                echo + >&2
                echo '+ git status --short --ignored |...' >&2
                git status --short --ignored |awk '{print $1}' |sort |uniq -c| expand
            else
                echo + >&2
                --exec-echo-xe git status --short --ignored "$@"
                : # available as:  --git --
            fi

        fi
    fi
}

function --git-chdir () {
    : :: 'ChDir to root of Git Clone'
    --exec-echo-xe 'cd $(git rev-parse --show-toplevel) && cd ./'$@' && dirs -p |head -1'
}

function --git-commit-all-fixup () {
    : :: 'Add all tracked and commit fixup to Head, else to some Commit'
    if [ $# = 0 ]; then
        --exec-echo-xe git commit --all --fixup HEAD
    else
        --exec-echo-xe git commit --all --fixup "$@"
    fi
}

function --git-commit-fixup () {
    : :: 'Commit fixup to Head, else to some Commit'
    if [ $# = 0 ]; then
        --exec-echo-xe git commit --fixup HEAD
    else
        --exec-echo-xe git commit --fixup "$@"
    fi
}

function --git-diff-head () {
    : :: 'Commit Diff since before Head, else since some Commit'
    if [ $# = 0 ]; then
        --exec-echo-xe git diff HEAD~1
    else
        --exec-echo-xe git diff HEAD~"$@"
    fi
}

function --git-ls-files () {
    : :: 'Find tracked files at and beneath root of Git Clone, else below some Dir'
    if [ $# = 0 ]; then
        local abs=$(git rev-parse --show-toplevel)
        local rel=$(python3 -c "import os; print(os.path.relpath('$abs'))")
        --exec-echo-xe git ls-files "$rel" "$@"
    else
        --exec-echo-xe git ls-files "$@"
    fi
}

function --git-rebase-interactive () {
    : :: 'Rebase Interactive with Auto Squash of the last 9, else of the last N'
    if [ $# = 0 ]; then
        --exec-echo-xe git rebase -i --autosquash HEAD~9
    else
        --exec-echo-xe git rebase -i --autosquash "HEAD~$@"
    fi
}

function --git-show-conflict () {
    : :: 'Exit loud & nonzero, else Show Conflict Base, else Show choice of Conflict'
    if [ $# = 1 ]; then
        --exec-echo-xe git show ":1:$1"
    elif [ $# = 2 ]; then
        --exec-echo-xe git show ":$1:$2"
    else
        echo 'usage: -gs 1|2|3 FILENAME |less  # base | theirs | ours'
        return 2
    fi
}


#
# Work with Emacs, Python, Vim, and such
#


alias -- -e='--exec-echo-xe emacs -nw --no-splash'
alias -- -v='--exec-echo-xe vim'

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

alias -- both=--edit-shifted
function --edit-shifted () {
    : :: 'edit a file mentioned as Conflicted in the style of Git Status'
    shift
    (set -xe; vim $@)
}  # such as:  both modified:   dotfiles/dot.zprofile

alias -- '+++'=--edit-shifted-slash
function --edit-shifted-slash () {
    : :: 'edit a file mentioned as Changed in the style of Git Diff'
    local filename=$(echo $1 |cut -d/ -f2-)
    shift
    (set -xe; vim $filename $@)
}  # such as:  +++ b/dotfiles/dot.zprofile +711


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
echo $(dirs -p |head -1)/


#
# Fall through to patches added onto this source file later, and then to " ~/.bashrc"
#


source ~/.bashrc

if dircolors >/dev/null 2>&1; then
    eval $(dircolors <(dircolors -p |sed 's,1;,0;,g'))  && : 'no bold for light mode'
fi


# above copied from:  git clone https://github.com/pelavarre/pybashish.git
