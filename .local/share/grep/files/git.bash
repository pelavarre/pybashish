#
# files/git.bash:  Git
#

git --version

echo 'git clean -ffxdq'  # destroy everything not added, without backup
echo 'git reset --hard @{upstream}'  # shove all my comments into the "git reflog", take theirs instead

git branch | grep '^[*]'
git branch --all

git checkout -  # for toggling between two branches

git status  # gs gs
git status --short --ignored
git status --short --ignored | wc -l | grep '^ *0$'

git apply -v ...'.patch'
patch -p1 <...'.patch'  # silently drops new chmod ugo+x

# copied from:  git clone https://github.com/pelavarre/pybashish.git
