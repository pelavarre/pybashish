# ~/.zprofile  # called before "~/.zshrc" or not called

# todo: contrast with Ubuntu ~/.bash_aliases


_DOT_ZPROFILE_=~/.zprofile  # don't export, to say if this file has been sourced

date


#
# Grow my keyboard
#


alias -- '::'=--colon-colon
function --colon-colon () {
    if which pbcopy >/dev/null; then
        (echo '# £ ← ↑ → ↓ ⇧ ⋮ ⌃ ⌘ ⌥ ⎋' |tee >(pbcopy))
    else
        echo '# £ ← ↑ → ↓ ⇧ ⋮ ⌃ ⌘ ⌥ ⎋'
    fi
}


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

function unix-filename-rubout () {
    : :: 'approximately undo Tab-Completion'
    local WORDCHARS="*?_[]~=&;\!#$%^(){}<>.-"
    zle backward-kill-word
}
zle -N unix-filename-rubout unix-filename-rubout  && : 'create new keymap'
bindkey "^W" unix-filename-rubout  # define Control+W to nearly undo Tab-Completion

function ps1 () {
    : :: 'toggle the prompt off and on'
    if [ "$PS1" != '%# ' ]; then
        export PS1='%# '  # no hostname, no pwd, etc etc
    else
        export PS1="$OLDPS1"  # trust ~/.zshrc to init OLDPS1
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

function --do-loudly () {
    : :: "say what you'll do, do what you do, say what you did, and when"
    local xs

    echo "$(date) + $@" >&2

    "$@"
    xs=$?

    echo "$(date) + exit $xs"
    return $xs
}


#
# Configure Zsh (with "unsetopt" and "setopt" and so on)
#


setopt PRINT_EXIT_VALUE  && : 'stop silencing nonzero exit status'

autoload -U edit-command-line  && : 'from ".oh-my-zsh/", else "No such shell function"'
zle -N edit-command-line  && : 'create new keymap'
bindkey '\C-x\C-e' edit-command-line  && : 'define ⌃X⌃E'

setopt AUTO_CD  && : 'lacks Tab-completion, emulates Bash shopt -s autocd 2>/dev/null'

# setopt INTERACTIVE_COMMENTS  # Zsh forwards #... as arg when not interactive


#
# Capture every input line (no drops a la Bash HISTCONTROL=ignorespace)
#


if [ ! "${HISTFILE+True}" ]; then  # emulate macOS Catalina, if HISTFILE unset
    HISTFILE=~/.zsh_history
    HISTSIZE=2000
    SAVEHIST=1000
fi

setopt EXTENDED_HISTORY  && : 'keep history over lotsa shells'
unsetopt INC_APPEND_HISTORY  && : 'make room for INC_APPEND_HISTORY_TIME  # unneeded?'
setopt INC_APPEND_HISTORY_TIME  && : "feed well into  history -t '%Y-%m-%d %H:%M:%S'"
setopt SHARE_HISTORY  && : 'reload fresh history after each INC_APPEND'

_HISTORY_1_="history -t '%b %d %H:%M:%S' -1"
_LOGME_='echo "$$ $(whoami)@$(hostname):$(pwd)$('$_HISTORY_1_')" >>~/.zsh_command.log'
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND ; }$_LOGME_"
unset _HISTORY_1_
unset _LOGME_

type -f precmd >/dev/null
if [[ $? != 0 ]]; then
    function precmd () { eval "$PROMPT_COMMAND"; }
fi

function --history () {
    --exec-echo-xe "history -t '%b %d %H:%M:%S' 0"  # a la Bash HISTTIMEFORMAT
}
alias -- --more-history="--exec-echo-xe 'cat ~/.*command*log*'"


#
# Push out and merge back in configuration secrets
#


function --dotfiles-dir () {
    : :: 'say where to push out the dotfiles'
    dotfiles=$(dirname $(dirname $(which read.py)))/dotfiles
    dotfiles=$(cd $dotfiles && dirs -p|head -1)
    echo $dotfiles
}

function --dotfiles-find () {
    : :: 'name the files to push out, and do not name the files to hide'

    echo .bash_profile
    echo .bashrc
    echo .emacs
    echo .insert.vimrc
    echo .pipe.luck
    echo .python.py
    echo .python.lazy.py
    echo .vimrc
    echo .zprofile
    echo .zshrc

    : 'drop from this list the secrets local to this host'
}

function --dotfiles-backup () {
    : :: 'back up the dot files - take mine, lose theirs'
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "cp -p ~/$F $dotfiles/dot$F"
    done
    echo ": not backing up ~/.zprofilesecrets" >&2
}

function --dotfiles-restore () {
    : :: 'restore the dot files  - take theirs, lose mine'
    dotfiles=$(--dotfiles-dir)
    for F in $(--dotfiles-find); do
        --exec-echo-xe "echo cp -p $dotfiles/dot$F ~/$F"
    done
    touch ~/.zprofilesecrets
}


#
# Abbreviate command lines down to:  ?
# mostly for pipe filters, but also 'm' for 'make', 'p' for 'popd', ...
#


function o () {
    if [ $# = 0 ]; then
        o ~/Desktop
    else
        --exec-echo-xe open "$@"
        --exec-echo-xe cd "$@"
        --exec-echo-xe pwd
    fi
}


# todo:  explain Terminal hung by:  h |l


function hi () {
    local arg1=$1
    shift
    (--more-history; --history) | --exec-echo-xe grep "$arg1$@"
}


function p () { --exec-echo-xe popd >/dev/null && --dir-p-tac; }

function --dir-p-tac () {
    if [[ "$(uname)" == "Darwin" ]]; then
        dirs -p |tail -r
    else
        # dirs -p |tac  # Linux 'tac' needs free space at shared '/tmp/' dir
        dirs -p |cat -n |sort -nr |cut -d$'\t' -f2-
    fi
}


#
# Work with dirs of files, and supply MM DD JQL HH MM SS date/time stamps
#


alias -- '?'="echo -n '? '>/dev/tty && cat -"  # press ⌃D for Yes, ⌃C for No

function -jqd () {
    : :: 'guess the initials of the person at the keyboard'
    echo 'jqd'  # J Q Doe
}  # odds on redefined by secrets local to this host

function -cp () {
    : :: 'back up to date-author-time stamp'
    local F="$1"
    local JQD=$(-jqd)
    (set -xe; cp -ipR "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

function -mv () {
    : :: 'back up to date-author-time stamp and remove'
    local F="$1"
    local JQD=$(-jqd)
    (set -xe; mv -i "$F" "$F~$(date +%m%d$JQD%H%M%S)~")
}

alias l='ls -CF'  && : 'define "l", "la", and "ll" by Linux conventions'
alias la='ls -A'
alias ll='ls -alF'

alias -- --ls='(set -xe; ls -alF -rt)'

# TODO: abbreviate $(ls -rt |tail -1)
# TODO: abbreviate $(ls -rtc |tail -1)


#
# Work with Ssh
#

function --while-ssh () {
    while :; do
        echo
        date
        ssh "$@"
        echo Press Ctrl+C to exit, else we try again in 3 seconds
        sleep 3
    done
}


#
# Shut up PyLint enough, so it can begin to speak clearly with us
#


function --pylint1 () {
    (
        set -xe
        ~/.venvs/pylint/bin/pylint \
            --rcfile=/dev/null --reports=n --score=n --disable=locally-disabled \
            -d W1514 -d R1734,R1735 -d C0103,C0201,C0209,C0302,C0325,C0411 \
            "$@"
    )
}

    #
    # (unspecified-encoding)
    # W1514: Using open without explicitly specifying an encoding
    # nope, i keep simply reading text from a file simple, viva default "utf_8"
    #

    #
    # R1734: Consider using [] instead of list() (use-list-literal)
    # R1735: Consider using {} instead of dict() (use-dict-literal)
    # nope, my old eyes appreciate the louder more explicit 'list()' mark
    #

    #
    # (invalid-name)
    # C0103: Variable name "..." doesn... conform to snake_case naming style
    # nope, my one and two letter variable names do have a place, albeit only rarely
    #
    # (consider-iterating-dictionary)
    # C0201: Consider iterating the dictionary directly instead of calling .keys()
    # nope, explicit better than implicit, for keeping part separate from whole
    #
    # (consider-using-f-string)
    # C0209: Formatting a regular string which could be a f-string'
    # nope, going with F Strings always doesn't always make the source more clear
    #
    # (too-many-lines)
    # C0302: Too many lines in module (.../1000)
    # yes, but large files do have a place, albeit only rarely
    #
    # (superfluous-parens)
    # C0325: Unnecessary parens after 'not' keyword
    # nope, i applaud the clarity of 'if not (0 < i <= last):'
    #
    # (wrong-import-order)
    # C0411: standard import "import ..." should be placed before "import __main__"
    # nope, i give the win to Flake8
    #

function --pylint2 () {
    --pylint1 \
        -d W0511 -d R0913,R0915 \
        "$@"
}

    #
    # (fixme)
    # W0511: FIXME, TODO
    #
    # (too-many-arguments)
    # R0913: Too many arguments
    #
    # (too-many-statements)
    # R0915: Too many statementss
    #


#
# Work with Emacs, Python, Vim, and such
#


function -p () {
    if [ $# = 0 ]; then
        ( set -xe; python3 -i "$@" ~/.python.py; )
    else
        local F="$1"
        if [[ "$1" == "bin/em.py" ]]; then  # TODO: un-hackify this?
            F="bin/vi.py"
        fi
        (
            set -xe

            echo |python3 -m pdb $F >&2  # explain SyntaxError's better than Black does

            ~/.venvs/pips/bin/black $F

            local WIDE='--max-line-length=999'
            ~/.venvs/pips/bin/flake8 $WIDE --max-complexity 10 --ignore=E203,W503 $F
            # --ignore=E203  # Black '[ : ]' rules over E203 whitespace before ':'
            # --ignore=W503  # 2017 Pep 8 and Black over W503 line break before bin op

            echo

            python3 "$@"
        )
    fi
}

function -p3 () {
    ( set -xe; python3 -i "$@" ~/.python.py 'print(sys.version.split()[0])'; )
}

function -p2 () {
    ( set -xe; python2 -i "$@" ~/.python.py 'print(sys.version.split()[0])'; )
}


function -ps () {
    (
        echo '+ source ~/bin/pips.source' >&2
        source ~/bin/pips.source
        set -xe
        python3 -i "$@" ~/.python.lazy.py
    )
}


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
# Copy in my secrets at work, such as
#
#   alias 0, 1, 2, ..., a, b, c, ... aa, bb, cc ... etc for reaching hosts I like
#   alias first words for pasting back printed lines as input
#   patch tools into PATH
#   pushd my favorite dirs
#


: export PATH="${PATH:+$PATH:}$HOME/bin"

# TODO: more trace in how these do what they do

alias -- --futurize='futurize --no-diffs -wW $PWD'
alias -- --2to3='2to3 --no-diffs -wW $PWD'

alias -- --black='~/.venvs/pips/bin/black'

alias -- --flake8='~/.venvs/pips/bin/flake8 --max-line-length=999 --max-complexity 10 --ignore=E203,W503'
: --max-line-length=999  # Black max line lengths over Flake8 max line lengths
: --ignore=E203  # Black '[ : ]' rules over Flake8 E203 whitespace before ':'
: --ignore=W503  # 2017 Pep 8 and Black over Flake8 W503 line break before binary op

export PATH="${PATH:+$PATH:}$HOME/bin"

source ~/.zprofilesecrets

export PATH="${PATH:+$PATH:}$HOME/Public/byobash/bash"
export PATH="${PATH:+$PATH:}$HOME/Public/byobash/bin"
export PATH="${PATH:+$PATH:}$HOME/Public/byobash/py"
export PATH="${PATH:+$PATH:}$HOME/Public/byobash/qbin"
export PATH="${PATH:+$PATH:}$HOME/Public/byobash/qb"
export PATH="${PATH:+$PATH:}$HOME/Public/shell2py/bin"
export PATH="${PATH:+$PATH:}$HOME/Public/pybashish/bin"


#
# Fall through more configuration script lines, & override some of them, or not
#


# source ~/.zshrc  # sometimes needed in Bash as:  source ~/.bashrc


# Setting PATH for Python 3.10
# The original version is saved in .zprofile.pysave
# PATH="/Library/Frameworks/Python.framework/Versions/3.10/bin:${PATH}"
# export PATH

# Setting PATH for Python 2.7
# The original version is saved in .zprofile.pysave
# PATH="/Library/Frameworks/Python.framework/Versions/2.7/bin:${PATH}"
# export PATH


# above copied from:  git clone https://github.com/pelavarre/pybashish.git
