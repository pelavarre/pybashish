#
# files/vim.bash:  Vim
#

vim --version
vim  # glass-terminal scratchpad
vim '+$' ~/.vimrc  # + option to say what line to start on

# vim  :help ⌃V...  "" help with key chord sequence
# vim  :q  "" close help panel

#
# vim  Esc  => cancel
# vim  ⌃V  => literal input, such as ⌃I Tab
#

#
# vim  0 ^ $ fx h l tx Fx Tx | ; ,  => move column
# vim  b e w B E W ( ) { }  => move small word, large word, sentence, paragraph
# vim  j k G 1G !G H L M - + _ ⌃J ⌃M ⌃N ⌃P  => move row
# vim  %  => move match balance pair
#
# vim  dx dd x D X p yx yy P Y J  => cut, copy, paste, join
# vim  a cx i o s Esc A C O S  => enter/ exit insert mode
# vim  R Esc  => enter/ exit overlay mode
#
# vim  . 1234567890 u ⌃R U UU ⌃O  => repeat, do again, undo, redo, revisit
# vim  ~ ⌃G ⌃L ⌃A  => toggle case, say where, redraw, increment
# vim  n N / ? .  => find and repeat
#
# vim  :g/regex/  => preview find and replace
# vim  :s/regex/repl/gc  => find and replace, .../g for no confirmations
#
# vim  mm 'm '' `` `m  => mark, goto, bounce, bounce, bounce and mark
# vim  qqq @q  => record, replay
# vim  ⌃V I X Y P  => vertical: insert, delete, copy, paste
# vim  >x <x  => dent/dedent
# vim  !x  => pipe bash
#
# vim  zb zt zz ⌃B ⌃D ⌃E ⌃F ⌃U ⌃Y  => scroll rows
# vim  ⌃Wo ⌃WW ⌃Ww ⌃]  => close others, previous, next, goto link
# vim  ⌃^  => replace panel with previous buffer
#
# vim  :e! ZZ ZQ  => quit-then-reopen, save-then-quit, quit-without-save
# vim  Q :vi  => line-editor/ screen-editor mode
#
# vim  ⌃C ⌃Q ⌃S ⌃Z ⌃[  => vary by terminal, ⌃Z may need $ fg,  ⌃Q can mean ⌃V
#
# vim  # & * = [ ] "  => obscure
# vim  ⌃H ⌃I ⌃T ⌃X ⌃\ ⌃_  => obscure
# vim  ⌃@ ⌃A g v V \ ⌃?  => not classic
#

#
# vim  " to show visible space v tab with : syntax or : set list
#
# vim  :syntax on
# vim  :set syntax=whitespace
# vim  :set syntax=off
# vim  :set list
# vim  :set listchars=tab:>-
# vim  :set nolist
#

#
# see also:  https://cheat.sh/vim
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
