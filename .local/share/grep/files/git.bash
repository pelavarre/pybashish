#
# files/git.bash:  Git
#

git --version

# git clean -ffxdq  # destroy everything not added, without backup
# git reset --hard @{upstream}  # shove all my comments into the "git reflog", take theirs instead

git branch | grep '^[*]'
git branch --all

git checkout -  # for toggling between two branches

git status  # gs gs
git status --ignored --short

git apply -v ...'.patch'
patch -p1 <...'.patch'  # silently drops new chmod ugo+x