#
# files/b.bash:  Bash
#

autopep8 --max-line-length 100 --in-place ...

awk '{print ...}'

bash --version

cat /dev/null/child  # always fails, often outside the shell
cd /dev/null  # always fails inside the shell

cat - | grep . | grep .  # free-text glass-terminal till ⌃C

cd -  # for toggling between two dirs

diff -x .git -burp ... ...

echo -n $'\e[8;'$(stty size | cut -d' ' -f1)';101t'  # 101 cols
echo >/dev/full  # always fails

export PS1='\$ '
export PS1="$PS1"'\n\$ '

find . -not \( -path './.git' -prune \)  # akin to:  git ls-files

if false; then echo y; else echo n; fi
if true; then echo y; else echo n; fi

last | head

ls *.csv | sed 's,[.]csv$,,' | xargs -I{} mv -i {}.csv {}.txt  # demo replace ext
ls --full-time ...  # to the second, at Linux
ls | LC_ALL=C sort | cat -n

rename 's,[.]csv$,-csv.txt,' *.csv  # replace ext, at Perl Linux

sed -e $'3i\\\n...' | tee >(head -3) >(tail -2) >/dev/null  # first two, ellipsis, last two
sed -i~ 's,STALE,FRESH,' *.json  # global edit find search replace

ssh -G ...
ssh -vvv ...

ssh-add -l

stat ...

tar kxf ...  # FIXME: test CACHEDIR.TAG
tar zcf ... ...

# !?memo  # feeling lucky enough to authorize find and run again

# copied from:  git clone https://github.com/pelavarre/pybashish.git
