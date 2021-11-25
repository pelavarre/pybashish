#
# files/vim.bash:  Vim
#

vim --version
vim  # glass-terminal scratchpad
vim '+$' ~/.vimrc  # + option to say what line to start on

# vim  :help ⌃V⌃C  "" help with key chord sequence
# vim  :q  "" close help panel

#
# vim  Esc ⌃O  => stop inserting: indefinitely or temporarily
# vim  ⌃V  => literal input, such as ⌃I Tab
# vim  Q :+1,+5 :vi  => line-editor/ screen-editor mode
#
# vim  :set hlsearch / :set nohlsearch
# vim  :set number / :set nonumber
#

#
# vim  0 ^ $ fx tx Fx Tx ; , | h l  => leap to column
# vim  b e w B E W ( ) { }  => leap across small word, large word, sentence, paragraph
# vim  G 1G H L M - + _ ⌃J ⌃M ⌃N ⌃P j k  => leap to row, leap to line
# vim  %  => leap to match balance pair
#
# vim  dx dd x D X p yx yy P Y J  => cut, copy, paste, join
# vim  a cx i o s A C I O S ⌃O Esc ⌃C  => enter/ suspend-resume/ exit insert mode
# vim  rx R ⌃O Esc ⌃C  => enter/ suspend-resume/ exit overlay mode
#
# vim  . 1234567890 u ⌃R ⌃O ⌃I  => do again, undo, repeat, revisit, undo-revisit
# vim  ~ ⌃G ⌃L ⌃A ⌃X  => toggle case, say where, redraw, increment, decrement
# vim  * / ? n N / .  => this, ahead, behind, next, previous, do again
#
# vim  :g/regex/  => preview what will be found
# vim  :1,$s/regex/repl/gc  => find and replace, .../g for no confirmations
#
# vim  mm 'm '' `` `m  => mark, goto, bounce, bounce, bounce and mark
# vim  qqq @q  => record input, replay input
# vim  ⌃V I X Y P  => vertical: insert, delete, copy, paste
# vim  >x <x  => dent/dedent
# vim  !x  => pipe bash, such as {}!G or 1G!G
#
# vim  zb zt zz ⌃F ⌃B ⌃E ⌃Y ⌃D ⌃U  => scroll rows
# vim  ⌃Wo ⌃WW ⌃Ww ⌃]  => close others, previous, next, goto link
# vim  ⌃^  => replace panel with previous buffer
#
# vim  :e! ZZ ZQ  => quit-then-reopen, save-then-quit, quit-without-save
# vim  Q :vi  => line-editor/ screen-editor mode
#
# vim  ⌃C ⌃Q ⌃S ⌃Z ⌃[  => vary by terminal, ⌃Z may need $ fg,  ⌃Q can mean ⌃V
#
# vim  U UU # & * = [ ] "  => obscure
# vim  ⌃H ⌃K ⌃T ⌃\ ⌃_  => obscure
# vim  ⌃@ ⌃A ⌃I ⌃O ⌃X g v V \ ⌃?  => not classic
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
