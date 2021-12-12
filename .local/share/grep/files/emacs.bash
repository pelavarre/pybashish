#
# files/emacs.bash:  Emacs
#

emacs --version
emacs -nw --no-splash --eval '(menu-bar-mode -1)'  # free-text glass-terminal
emacs -nw ~/.emacs

#
# emacs  ⌃G  => cancel
# emacs  ⌃Q ⌃J  => literal input, literal newline
#
# emacs  ⌃A ⌃B ⌃E ⌃F ⌥M ⌥GTab  => move column
# emacs  ⌥B ⌥F ⌥A ⌥E  => move small word, sentence
# emacs  ⌃P ⌃N ⌥< ⌥> ⌥GG  => move row, goto line
# emacs  fixme  => move match balance pair
#
# emacs  ⌃D ⌥D ⌥Z  => delete char, word, to char
# emacs  ⌃@⌃@ ⌃@ ⌃X⌃X ⌃U⌃@  => mark: begin, place, bounce, goto
# emacs  ⌃K ⌃W ⌥W ⌃Y ⌥Y ⌥T  => cut, copy, paste, paste-next-instead, join, transpose
# emacs  ⌥H ⌥Q  => paragraph: mark, reflow
#
# emacs  ⌃U1234567890 ⌃- ⌃_ ⌃Xu  => repeat, undo, undo
# emacs  ⌥L ⌥U ⌥C ⌃U1⌃XRNI⌃XR+I⌃XRII  => lower, upper, title, increment
# emacs  ⌃S ⌃R ⌥%  => find, replace
#
# emacs  ⌃X( ⌃X) ⌃XE  => record input, replay input
# emacs  fixme  => vertical delete copy paste insert
# emacs  ⌃XTab ⌃XRD  => dent/dedent
# emacs  ⌃U1⌥|  => pipe bash, such as ⌥H⌃U1⌥| or ⌥<⌃@⌥>⌃U1⌥|
#
# emacs  ⌃V ⌥V ⌃L  => scroll rows
# emacs  ⌃X1 ⌃XK ⌃XO  => close others, close this, warp to next
#
# emacs  ⌃X⌃C ⌥~⌃X⌃C  => quit emacs, without saving
#
# emacs  ⌃Hk... ⌃Hb ⌃Ha...   => help for key chord sequence, for all keys, for word
# emacs  ⌥X ⌥:  => execute-extended-command, eval-expression  => dry run ~/.emacs
#
# emacs  ⌃Z  => as per terminal or no-op
#
# emacs  ⌃] ⌃\  => obscure
# emacs  ⌃Ca-z  => custom
# emacs  ⌃C⌃C...  => custom
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
