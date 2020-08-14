#
# files/emacs.bash:  Emacs
#

emacs --version

emacs -nw --no-splash  # free-text glass-terminal

emacs -nw ~/.emacs

#
# emacs  ⌃G  => cancel
# emacs  ⌃Q  => literal input
#
# emacs  ⌃A ⌃B ⌃E ⌃F ⌥M  => move column
# emacs  ⌥B ⌥F ⌥A ⌥E  => move small word, sentence
# emacs  ⌃P ⌃N ⌥G⌥G  => move row, goto line
# emacs  fixme => move balance
#
# emacs  ⌃D ⌥D ⌥Z  => delete char, word, to char
# emacs  ⌃K ⌃W ⌥W ⌃Y ⌥Y ⌥T  => cut, copy, paste, paste-next-instead, join, transpose
# emacs  ⌥H ⌥Q  => paragraph: mark, reflow
#
# emacs  ⌃U1234567890 ⌃- ⌃_ ⌃Xu ⌥L ⌥U ⌥C  => repeat, undo, undo, lower, upper, title
# emacs  ⌃S ⌃R ⌥% => find, replace
#
# emacs  ⌃@⌃@ ⌃@ ⌃X⌃X ⌃U⌃@  => mark: begin, place, bounce, goto
# emacs  ⌃X( ⌃X) ⌃Xe  => record replay
# emacs  fixme => vertical delete copy paste insert
# emacs  fixme => dent/dedent
# emacs  ⌥H⌃U1⌥|  => pipe
#
# emacs  ⌃V ⌥V ⌃L  => scroll rows
# emacs  ⌃X1 ⌃Xk ⌃Xo  => close others, close this, warp to next
#
# emacs  ⌃Xc ⌥~  => quit emacs, without saving
#
# emacs  ⌃Hk... ⌃Ha...  => help with key chord sequence, help with word
#
# emacs  ⌃Z  => as per terminal or no-op
#
# emacs  ⌃] ⌃\  => obscure
# emacs  ⌃Ca-z => custom
#

#
# emacs ⌥X describe-bindings Return  => help with lots of key chord sequences
#