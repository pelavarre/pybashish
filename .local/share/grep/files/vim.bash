#
# files/vim.bash:  Vim
#

vim --version

vim  # free-text glass-terminal

vim '+$' ~/.vimrc  # + option to say what line to start on

#
# vim  Esc  => cancel
# vim  ⌃V  => literal input
#
# vim  0 ^ fx h l tx Fx Tx | ; , _  => move column
# vim  b e w B E W ( ) { }  => move small word, large word, sentence, paragraph
# vim  j k G 1G !G H L M $ - + ⌃J ⌃N ⌃P  => move row
# vim  %  => move match balance pair
#
# vim  dx x D X p yx P Y J  => cut, copy, paste, join
# vim  a cx i o s Esc A C O S  => enter/ exit insert mode
# vim  R Esc  => enter/ exit overlay mode
#
# vim  123456789 u UU ~ . ⌃G ⌃R  => repeat, undo, revisit, redo
# vim  ~ ^A  => toggle-case, increment
# vim  n N / ? => find
# vim  %s/pattern/repl/g  => find and replace
#
# vim  mm 'm '' `m ``  => mark, goto, bounce, via either tick
# vim  qqq @q  => record, replay
# vim  ⌃V I X Y P  => vertical: insert, delete, copy, paste
# vim  <x >x  => dedent/indent
# vim  !x  => pipe
#
# vim  zb zt zz ⌃B ⌃D ⌃E ⌃F ⌃U ⌃Y  => scroll rows
# vim  ⌃Wo ⌃WW ⌃Ww ⌃]  => close others, previous, next, goto link
# vim  ⌃^  => warp to previous buffer
#
# vim  : ZZ ZQ  => ex command such as :q, save-then-quit-vim, quit-vim-without-saving
#
# vim  ⌃C ⌃Q ⌃S ⌃Z ⌃[  => as per terminal or no-op
#
# vim  Q # & * = [ ] "  => obscure
# vim  ⌃H ⌃I ⌃O ⌃T ⌃X ⌃\ ⌃_  => obscure
# vim  ⌃@ ⌃A g v V \ ⌃?  => not classic
#

# vim  :help ⌃V...  # help with key chord sequence

#
# vim  " to show visible space v tab with : syntax or : set list
# vim  :syntax on
# vim  :set syntax=whitespace
# vim  :set list
#
# see also:  https://cheat.sh/vim
# FIXME:  :%s/foo/bar/gc
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
