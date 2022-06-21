" ~/.insert.vimrc

" usage =>  :source ~/.insert.vimrc
"
" redefine Vim's Option/Alt Key Chords to work without toggling Insert Mode
"


"
" == 1 of 9 ==
"
" Download this file as your own:  ~/.insert.vimrc
"
"       https://raw.githubusercontent.com/pelavarre/pybashish/main/dot.insert.vimrc
"       https://raw.githubusercontent.com/pelavarre/pybashish/main/dotfiles/dot.insert.vimrc
"
"       mv -i ~/Downloads/dot.insert.vimrc ~/.insert.vimrc
"
" Test it like so
"
"       vim +'source ~/.insert.vimrc' ~/.insert.vimrc
"
" When you like it, add it into your own:  ~/.vimrc
"
"       :source ~/.insert.vimrc
"


"
" == 2 of 9 ==
"
" Tell Vim to show Insert Mode, the Keys you've pressed, and where the Cursor is
"


:set noshowmode
:set showmode  " say '-- INSERT --' in bottom line while you remain in Insert Mode
:set noshowcmd
:set showcmd  " show the Key pressed with Option/Alt, while waiting for next Key
:set noruler
:set ruler  " show the Line & Column Numbers of the Cursor
:set nonumber
:set number  " show the Line Number of each Line

:startinsert " start in Insert Mode, not in Normal View Mode
:stopinsert  " start in Normal View Mode, not in Insert Mode


"
" == 3 of 9 ==
"
" Look at what your macOS Option/Alt Key can mean outside of Basic Latin Unicode
"
" Visit macOS > System Preferences > Keyboard > Input Sources >
"   > Show Input Menu In Menu Bar
"       > Menu Bar > Show/Hide Keyboard Viewer
" to see a plot of what each Key means with Option/Alt, and without or with Shift
"
"    Option/Alt without Shift         Option/Alt with Shift
"   --------------------------      --------------------------
"
"   ¡ ™ £ ¢ ∞ § ¶ • ª º – ≠         ⁄ € ‹ › ﬁ ﬂ ‡ ° · ‚ — ±
"
"    œ ∑ ´ ® † \ ¨ ˆ ø π “ ‘ «       Œ „ ´ ‰ ˇ Á ¨ ˆ Ø ∏ ” ’ »
"     å ß ∂ ƒ © ˙ ∆ ˚ ¬ … æ           Å Í Î Ï ˝ Ó Ô  Ò Ú Æ
"      Ω ≈ ç √ ∫ ˜ µ ≤ ≥ ÷             ¸ ˛ Ç ◊ ı  Â ¯ ˘ ˘ ¿
"
" Take a look at your macOS Terminal > Preferences > ... > Keyboard
"
"   > Use Option as Meta Key = No (default)
"   > Use Option as Meta Key = Yes
"


"
" == 4 of 9 ==
"
" Look into the plenty you can do without leaving Insert Mode
"
" :help i_CTRL-V
"   ⌃V in Insert Mode means take the next Keystroke as Input, not as Command
"       except it doesn't correctly show that ⌥Y means ¥ Yen not \ Backslash
"
" :help i_CTRL-O
"   ⌃O in Insert Mode means take the next Keystroke as Command, not as Input
"
" :help ZZ
" :help ZQ
"   press ⌃O ⇧Z ⇧Z
"	to save then quit
"   press ⌃O ⇧Z ⇧Q
"	to quit without saving
"   press ⌃O ⇧Q v i Return i
"	to go into : Ex Mode but then come back to Insert Mode
"


"
" == 5 of 9 ==
"
" Notice Option/Alt + Left Click already means move the Cursor there
"


"
" == 6 of 9 ==
"
" Keep the Option/Alt Key in Insert Mode meaning what it means after ⌃V
" but define your macOS Option/Alt Key to mean leave Insert Mode
"
" :I-NoRe-Map = Map only for Insert Mode and don't Recurse through other maps
"
" first of four, define the Option/Alt Keys for
" the Insert Mode of the macOS Terminal > Preference of
"   > Use Option as Meta Key = No (default)
"
" note i've only ever seen Esc Q and Esc @ work, not also ⌃O Q and ⌃O ⌃@
"

" ⌥⇧Z⇧Z to save then quit, ⌥⇧Z⇧Q to quit without saving

:inoremap ¸ <Esc>Z

" ⌥: escape to Ex Mode, till you press Return
"   such as :e! to discard changes, or :w to save them
" ⇧⌥Q escape to Ex Mode, till you press v i Return
:inoremap Ú <Esc>:
:inoremap Œ <Esc>Q
" Windows folk may still have to press ⌃O: to mean ⌥:

" leap to column
" ⌥$ jumps to the last Character, not past the last Character, except as ⌃O $
:inoremap › <Esc>$
:inoremap ﬂ <Esc>^
:inoremap º <Esc>0
:inoremap ƒ <Esc>f
:inoremap † <Esc>t
:inoremap Ï <Esc>F
:inoremap Ê <Esc>T
:inoremap … <Esc>;
:inoremap ≤ <Esc>,
:inoremap ˙ <Esc>h
:inoremap ¬ <Esc>l
" ⌥Space comes through as Space, so you can't make it into Esc Space

" leap across small words, large words, or paragraphs,
" except you press ⌥E E to mean E (because ⌥E⌥E comes across as ⌥⇧E ⌥⇧E)
:inoremap ∑ <Esc>w
:inoremap é <Esc>e
:inoremap ∫ <Esc>b
:inoremap „ <Esc>W
:inoremap ´ <Esc>E
:inoremap ı <Esc>B
:inoremap ” <Esc>{
:inoremap ’ <Esc>}

" leap to line, screen row
:inoremap ˝ <Esc>G
:inoremap Ò <Esc>L
:inoremap Â <Esc>M
:inoremap Ó <Esc>H
:inoremap ± <Esc>+
:inoremap — <Esc>_
:inoremap – <Esc>-
:inoremap ∆ <Esc>j
:inoremap ˚ <Esc>k

" spell out how many times to repeat,
" except you have to release the Option Key after striking the last digit,
" and the ⌃J, ⌃N, and ⌃P all work with the Control Key alone, no Option Key needed
:inoremap ¡ <Esc>1
:inoremap € <Esc>2
:inoremap £ <Esc>3
:inoremap ¢ <Esc>4
:inoremap ∞ <Esc>5
:inoremap § <Esc>6
:inoremap ¶ <Esc>7
:inoremap • <Esc>8
:inoremap ª <Esc>9

" redo and undo
:inoremap ≥ <Esc>.
:inoremap ü <Esc>u
:inoremap ¨ <Esc>U
:inoremap <C-r> <Esc><C-r>

" scroll or refresh screen, such as ⌥Z T, ⌥Z Z, ⌥Z B,
" except you have to release the Option Key after striking Option+Z,
:inoremap Ω <Esc>z

" search ahead, behind, and next,
" except you press ⌥N N to mean N (because ⌥N⌥N comes across as ⌥⇧N ⌥⇧N)
:inoremap ÷ <Esc>/
:inoremap ¿ <Esc>?
:inoremap ° <Esc>*
:inoremap ‹ <Esc>#
:inoremap ñ <Esc>n
:inoremap ˜ <Esc>N

" move and replace and insert, or not
" ⌥R changes to Replace Mode from Insert Mode
" ⌥A jumps to insert past the last Character, same as ⌥$ A
:inoremap ® <Esc>r
:inoremap å <Esc>a
:inoremap î <Esc>i
:inoremap ø <Esc>o
:inoremap ‰ <Esc>R
:inoremap Å <Esc>A
:inoremap ˆ <Esc>I
:inoremap Ø <Esc>O

" cut chars, join/ cut lines, insert after cut,
" except you have to release the Option Key after striking D or C or Y
" and you have to press ⌃O Y to get Y when Option/Alt is not Meta Key, i dunno why
:inoremap ≈ <Esc>x
:inoremap ˛ <Esc>X
:inoremap Ô <Esc>J
:inoremap ß <Esc>s
:inoremap Í <Esc>S
:inoremap ∂ <Esc>d
:inoremap ç <Esc>c
:inoremap Î <Esc>D
:inoremap Ç <Esc>C
:inoremap π <Esc>p
:inoremap ∏ <Esc>P
:inoremap ¥ <Esc>y
:inoremap Á <Esc>Y

" also map ! ' < > @ m q | ~
:inoremap ⁄ <Esc>!
:inoremap æ <Esc>'
:inoremap ¯ <Esc><
:inoremap ˘ <Esc>>
:inoremap € <Esc>@
:inoremap µ <Esc>m
:inoremap œ <Esc>q
:inoremap » <Esc><Bar>
:inoremap ` <Esc>~

" gateway to custom code you have dropped onto Vim <BSlash>, if any
:imap « <Esc><BSlash>


"
" == 7 of 9 ==
"
" second of four, define the Option/Alt Keys for
" the Insert Mode of the macOS Terminal > Preference of
"   > Use Option as Meta Key = Yes
"
" mostly its Option/Alt Keys come through ok by default
"   for example, its ⌥A comes through as Esc ⇧A,
"       so that leaves Insert Mode, then re-enters, in the style of $ A
"
" two special cases =>
"
"   macOS ⌥← Option Left-Arrow  => Esc B = take as alias of Esc ⇧B
"       although that choice stops ⌥B from meaning Esc B i
"
"   macOS ⌥→ Option Right-Arrow  => Esc F = take as alias of Esc ⇧W
"       although that choice stops ⌥F from meaning Esc F ... i
"
" four more special cases =>
"
"   ⌥R, ⌥A, ⌥I, ⌥O place the cursor wrong
"       if defined as Esc R, Esc A, Esc I, and Esc O,
"           but defining them as ⌃O R, ⌃O A, ⌃O I, and ⌃O O does work
"


:inoremap <Esc>b <Esc>B
:inoremap <Esc>f <Esc>W

:inoremap <Esc>r <C-o>r
:inoremap <Esc>a <C-o>a
:inoremap <Esc>i <C-o>i
:inoremap <Esc>o <C-o>o


"
" == 8 of 9 ==
"
" third of four, define the Option/Alt Keys for
" the Normal View Mode of the macOS Terminal > Preferences of
"   > Use Option as Meta Key = Yes
"   > Use Option as Meta Key = No
"
" but take care to not disrupt the two special cases above at Esc B, Esc F
"


:nnoremap ¸ Z
:nnoremap Ú :
:nnoremap Œ Q
:nnoremap › $
:nnoremap ﬂ ^
:nnoremap º 0
:nnoremap ƒ f
:nnoremap † t
:nnoremap Ï F
:nnoremap Ê T
:nnoremap … ;
:nnoremap ≤ ,
:nnoremap ˙ h
:nnoremap ¬ l
:nnoremap ∑ w
:nnoremap é e
:nnoremap ∫ b
:nnoremap „ W
:nnoremap ´ E
:nnoremap ı B
:nnoremap ” {
:nnoremap ’ }
:nnoremap ˝ G
:nnoremap Ò L
:nnoremap Â M
:nnoremap Ó H
:nnoremap ± +
:nnoremap — _
:nnoremap – -
:nnoremap ∆ j
:nnoremap ˚ k
:nnoremap ¡ 1
:nnoremap € 2
:nnoremap £ 3
:nnoremap ¢ 4
:nnoremap ∞ 5
:nnoremap § 6
:nnoremap ¶ 7
:nnoremap • 8
:nnoremap ª 9
:nnoremap ≥ .
:nnoremap ¨ U
:nnoremap Ω z
:nnoremap ÷ /
:nnoremap ¿ ?
:nnoremap ° *
:nnoremap ‹ #
:nnoremap ñ n
:nnoremap ˜ N
:nnoremap ® r
:nnoremap å a
:nnoremap î i
:nnoremap ø o
:nnoremap ‰ R
:nnoremap Å A
:nnoremap ˆ I
:nnoremap Ø O
:nnoremap ≈ x
:nnoremap ˛ X
:nnoremap Ô J
:nnoremap ß s
:nnoremap Í S
:nnoremap ∂ d
:nnoremap ç c
:nnoremap Î D
:nnoremap Ç C
:nnoremap π p
:nnoremap ∏ P
:nnoremap Á Y
:nnoremap ⁄ !
:nnoremap æ '
:nnoremap ¯ <
:nnoremap ˘ >
:nnoremap € @
:nnoremap µ m
:nnoremap œ q
:nnoremap » <Bar>
:nnoremap ` ~


:nnoremap <Esc>SPC SPC
:nnoremap <Esc>! !
:nnoremap <Esc># #
:nnoremap <Esc>$ $
:nnoremap <Esc>' '
:nnoremap <Esc>* *
:nnoremap <Esc>+ +
:nnoremap <Esc>, ,
:nnoremap <Esc>- -
:nnoremap <Esc>. .
:nnoremap <Esc>/ /
:nnoremap <Esc>0 0
:nnoremap <Esc>1 1
:nnoremap <Esc>2 2
:nnoremap <Esc>3 3
:nnoremap <Esc>4 4
:nnoremap <Esc>5 5
:nnoremap <Esc>6 6
:nnoremap <Esc>7 7
:nnoremap <Esc>8 8
:nnoremap <Esc>9 9
:nnoremap <Esc>: :
:nnoremap <Esc>; ;
:nnoremap <Esc>< <
:nnoremap <Esc>> >
:nnoremap <Esc>? ?
:nnoremap <Esc>@ @
:nnoremap <Esc>A A
:nnoremap <Esc>B B
:nnoremap <Esc>C C
:nnoremap <Esc>D D
:nnoremap <Esc>E E
:nnoremap <Esc>F F
:nnoremap <Esc>G G
:nnoremap <Esc>H H
:nnoremap <Esc>I I
:nnoremap <Esc>J J
:nnoremap <Esc>L L
:nnoremap <Esc>M M
:nnoremap <Esc>N N
:nnoremap <Esc>O O
:nnoremap <Esc>OA k
:nnoremap <Esc>OB j
:nnoremap <Esc>OC l
:nnoremap <Esc>OD h
:nnoremap <Esc>P P
:nnoremap <Esc>Q Q
:nnoremap <Esc>R R
:nnoremap <Esc>S S
:nnoremap <Esc>T T
:nnoremap <Esc>U U
:nnoremap <Esc>W W
:nnoremap <Esc>X X
:nnoremap <Esc>Y Y
:nnoremap <Esc>Z Z
:nnoremap <Esc><BSlash> <BSlash>
:nnoremap <Esc>^ ^
:nnoremap <Esc>_ _
:nnoremap <Esc>a a
" :nnoremap <Esc>b b
:nnoremap <Esc>c c
:nnoremap <Esc>d d
:nnoremap <Esc>e e
" :nnoremap <Esc>f f
:nnoremap <Esc>h h
:nnoremap <Esc>i i
:nnoremap <Esc>j j
:nnoremap <Esc>k k
:nnoremap <Esc>l l
:nnoremap <Esc>m m
:nnoremap <Esc>n n
:nnoremap <Esc>o o
:nnoremap <Esc>p p
:nnoremap <Esc>q q
:nnoremap <Esc>r r
:nnoremap <Esc>s s
:nnoremap <Esc>t t
:nnoremap <Esc>u u
:nnoremap <Esc>w w
:nnoremap <Esc>x x
:nnoremap <Esc>y y
:nnoremap <Esc>z z
:nnoremap <Esc>{ {
:nnoremap <Esc><Bar> <Bar>
:nnoremap <Esc>} }
:nnoremap <Esc>~ ~


"
" == 9 of 9 ==
"
" fourth of four, grab a hold of some Control Keys inside Insert Mode
"
" ⌃O⌃G works when you test it by hand, but doesn't work here, i dunno why
" i settle for defining Insert Mode ⌃G as Esc ⌃G, and Insert Mode ⌃L as Esc ⌃L
"
" you must choose to give up the usual ⌃O or not
" if you give it up, then you can press ⌃O to mean Esc ⌃O I
" and you can press ⌃O ⌃O to mean ⌃O
"
" if you give up the usual ⌃I, then you can press ⌃I (or Tab) to mean Esc ⌃O ⌃I
" and you can press ⌃I ⌃I (or Tab Tab) to mean ⌃I
"
" if you give up the usual ⌃V, then you can press ⌃V to mean Esc ⌃O ⌃V
" and you can press ⌃V ⌃V to mean ⌃V
"


:inoremap <C-f> <C-o><C-f>
:inoremap <C-b> <C-o><C-b>
:inoremap <C-e> <C-o><C-e>
:inoremap <C-y> <C-o><C-y>

:inoremap <C-g> <Esc><C-g>
:inoremap <C-l> <Esc><C-l>

:inoremap <C-o> <C-o><C-o>
:inoremap <C-i> <C-o><C-i>
:inoremap <C-v> <C-o><C-v>

:inoremap <C-i><C-i> <C-i>
:inoremap <C-o><C-o> <C-o>
:inoremap <C-v><C-v> <C-v>


" copied from:  git clone https://github.com/pelavarre/pybashish.git
