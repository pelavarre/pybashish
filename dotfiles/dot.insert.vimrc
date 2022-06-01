" ~/.insert.vimrc

" usage =>  :source ~/.insert.vimrc
"
" redefine the Option/Alt keys to mean stay in Insert Mode
"

"
" == 1 of 8 ==
"
" Save this file as your own:  ~/.insert.vimrc
"
"       https://raw.githubusercontent.com/pelavarre/pybashish/main/dotfiles/dot.insert.vimrc
"
" Run it like so
"
"       vim +'source ~/.insert.vimrc' ~/.insert.vimrc
"
" Or keep it added into your own:  ~/.vimrc
"
"       :source ~/.insert.vimrc
"


"
" == 2 of 8 ==
"
" Tell Vim to start in Insert Mode, and to tell you how long you remained
"


:set showmode  " say '-- INSERT --' in bottom line while you remain in Insert Mode
:set showcmd  " show the Option/Alt key pressed, while waiting for next Key pressed
:set ruler  " show the Line & Column Numbers of the Cursor
:set number  " show the Line Number of each Line

:startinsert  " start in Insert Mode, not in Normal View Mode


"
" == 3 of 8 ==
"
" You can run Vim and never leave Insert Mode,
"   so that you stop getting confused over whether you left or not
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
" == 4 of 8 ==
"
" You can see what your macOS Option/Alt key can mean outside of Basic Latin Unicode
"
" Visit macOS > System Preferences > Keyboard > Input Sources >
"   > Show Input Menu In Menu Bar
"       > Menu Bar > Show/Hide Keyboard Viewer
" to see something much like
"
"   ¡ ™ £ ¢ ∞ § ¶ • ª º – ≠         ⁄ € ‹ › ﬁ ﬂ ‡ ° · ‚ — ±
"
"    œ ∑ ´ ® † \ ¨ ˆ ø π “ ‘ «       Œ „ ´ ‰ ˇ Á ¨ ˆ Ø ∏ ” ’ »
"     å ß ∂ ƒ © ˙ ∆ ˚ ¬ … æ           Å Í Î Ï ˝ Ó Ô  Ò Ú Æ
"      Ω ≈ ç √ ∫ ˜ µ ≤ ≥ ÷             ¸ ˛ Ç ◊ ı  Â ¯ ˘ ˘ ¿
"


"
" == 5 of 8 ==
"
" Your Option/Alt + Left Click already means move the cursor there
"


"
" == 6 of 8 ==
"
" You can define your macOS Option/Alt key to mean ⌃O in Insert Mode
"
" :I-NoRe-Map = Map only for Insert Mode and don't Recurse through other maps
"
" the macOS Terminal > Preferences > ... > Keyboard
" starts you out with two different definitions of the Option/Alt key
"
" first of three, here are the definitions for
"   > Use Option as Meta Key = No (default)
"


" ⌥⇧Z⇧Z to save then quit, ⌥⇧Z⇧Q to quit without saving

:inoremap ¸ <C-o>Z

" ⌥: escape to Ex Mode, till you press Return
"   such as :e! to discard changes, or :w to save them
" ⇧⌥Q escape to Ex Mode, till you press v i Return
:inoremap Ú <C-o>:
:inoremap Œ <C-o>Q
" Windows folk may still have to press ⌃O: to mean ⌥:

" leap to column
" " ⌥$ jumps to insert past the last Character, same as ⌥A
:inoremap › <C-o>$
:inoremap ﬂ <C-o>^
:inoremap º <C-o>0
:inoremap ƒ <C-o>f
:inoremap † <C-o>t
:inoremap Ï <C-o>F
:inoremap Ê <C-o>T
:inoremap … <C-o>;
:inoremap ≤ <C-o>,
:inoremap ˙ <C-o>h
:inoremap ¬ <C-o>l

" leap across small words, large words, or paragraphs,
" except you press ⌥E E to mean E (because ⌥E⌥E comes across as ⌥⇧E ⌥⇧E)
:inoremap ∑ <C-o>w
:inoremap é <C-o>e
:inoremap ∫ <C-o>b
:inoremap „ <C-o>W
:inoremap ´ <C-o>E
:inoremap ı <C-o>B
:inoremap ” <C-o>{
:inoremap ’ <C-o>}

" leap to line, screen row
:inoremap ˝ <C-o>G
:inoremap Ò <C-o>L
:inoremap Â <C-o>M
:inoremap Ó <C-o>H
:inoremap ± <C-o>+
:inoremap — <C-o>_
:inoremap – <C-o>-
:inoremap ∆ <C-o>j
:inoremap ˚ <C-o>k

" spell out how many times to repeat,
" except you have to release the Option key after striking the last digit,
" and the ⌃J, ⌃N, and ⌃P all work with the Control key alone, no Option key needed
:inoremap ¡ <C-o>1
:inoremap € <C-o>2
:inoremap £ <C-o>3
:inoremap ¢ <C-o>4
:inoremap ∞ <C-o>5
:inoremap § <C-o>6
:inoremap ¶ <C-o>7
:inoremap • <C-o>8
:inoremap ª <C-o>9

" redo and undo
:inoremap ≥ <C-o>.
:inoremap ü <C-o>u
:inoremap ¨ <C-o>U
:inoremap <C-r> <C-o><C-r>

" scroll or refresh screen, such as ⌥Z T, ⌥Z Z, ⌥Z B,
" except you have to release the Option key after striking Option+Z,
:inoremap Ω <C-o>z

" tell ⌃F, ⌃B, ⌃E, ⌃Y, ⌃G, and ⌃L to work with the Control key alone, without Option key
" but for ⌃I and ⌃O themselves you have to press ⌃O⌃I and ⌃O⌃O from Insert Mode;
" also you have to press ⌃O⌃G to see Buffer '[Modified]' or not, i dunno why
:inoremap <C-f> <C-o><C-f>
:inoremap <C-b> <C-o><C-b>
:inoremap <C-e> <C-o><C-e>
:inoremap <C-y> <C-o><C-y>
:inoremap <C-l> <C-o><C-l>

" search ahead, behind, and next,
" except you press ⌥N N to mean N (because ⌥N⌥N comes across as ⌥⇧N ⌥⇧N)
:inoremap ÷ <C-o>/
:inoremap ¿ <C-o>?
:inoremap ° <C-o>*
:inoremap ‹ <C-o>#
:inoremap ñ <C-o>n
:inoremap ˜ <C-o>N

" move and replace and insert, or not
" ⌥R changes to Replace Mode from Insert Mode
" ⌥A jumps to insert past the last Character, same as ⌥$
:inoremap ® <C-o>r
:inoremap å <C-o>a
:inoremap î <C-o>i
:inoremap ø <C-o>o
:inoremap ‰ <C-o>R
:inoremap Å <C-o>A
:inoremap ˆ <C-o>I
:inoremap Ø <C-o>O

" cut chars, join/ cut lines, insert after cut,
" except you have to release the Option key after striking D or C or Y
" and you have to press ⌃O Y to get Y when Option/Alt is not Meta Key, i dunno why
:inoremap ≈ <C-o>x
:inoremap ˛ <C-o>X
:inoremap Ô <C-o>J
:inoremap ß <C-o>s
:inoremap Í <C-o>S
:inoremap ∂ <C-o>d
:inoremap ç <C-o>c
:inoremap Î <C-o>D
:inoremap Ç <C-o>C
:inoremap π <C-o>p
:inoremap ∏ <C-o>P
:inoremap ¥ <C-o>y
:inoremap Á <C-o>Y

" also map ! ' < > @ m q | ~
" but beware i haven't made tests of ⌃O @ Q work in Vim Insert Mode
:inoremap ⁄ <C-o>!
:inoremap æ <C-o>'
:inoremap ¯ <C-o><
:inoremap ˘ <C-o>>
:inoremap € <C-o>@
:inoremap µ <C-o>m
:inoremap œ <C-o>q
:inoremap » <C-o><Bar>
:inoremap ` <C-o>~

" gateway to custom code you have dropped onto Vim <BSlash>, if any
:imap « <C-o><BSlash>


"
" == 7 of 8 ==
"
" second of three, here are the definitions for
"   > Use Option as Meta Key = Yes
"
" but there ⌥← collides with ⌥B, so you have to choose if they mean ↑B or B
" and there ⌥→ collides with ⌥F, so again you choose if they mean ↑F or F
"

:inoremap <C-[>SPC <C-o>SPC
:inoremap <C-[>! <C-o>!
" "
:inoremap <C-[># <C-o>#
:inoremap <C-[>$ <C-o>$
" %
" &
:inoremap <C-[>' <C-o>'
" (
" )
:inoremap <C-[>* <C-o>*
:inoremap <C-[>+ <C-o>+
:inoremap <C-[>, <C-o>,
:inoremap <C-[>- <C-o>-
:inoremap <C-[>. <C-o>.
:inoremap <C-[>/ <C-o>/

:inoremap <C-[>0 <C-o>0
:inoremap <C-[>1 <C-o>1
:inoremap <C-[>2 <C-o>2
:inoremap <C-[>3 <C-o>3
:inoremap <C-[>4 <C-o>4
:inoremap <C-[>5 <C-o>5
:inoremap <C-[>6 <C-o>6
:inoremap <C-[>7 <C-o>7
:inoremap <C-[>8 <C-o>8
:inoremap <C-[>9 <C-o>9
:inoremap <C-[>: <C-o>:
:inoremap <C-[>; <C-o>;
:inoremap <C-[>< <C-o><
" =
:inoremap <C-[>> <C-o>>
:inoremap <C-[>? <C-o>?

:inoremap <C-[>@ <C-o>@
:inoremap <C-[>A <C-o>A
:inoremap <C-[>B <C-o>B
:inoremap <C-[>C <C-o>C
:inoremap <C-[>D <C-o>D
:inoremap <C-[>E <C-o>E
:inoremap <C-[>F <C-o>F
:inoremap <C-[>G <C-o>G
:inoremap <C-[>H <C-o>H
:inoremap <C-[>I <C-o>I
:inoremap <C-[>J <C-o>J
:inoremap <C-[>L <C-o>L
:inoremap <C-[>M <C-o>M
:inoremap <C-[>N <C-o>N
:inoremap <C-[>O <C-o>O

:inoremap <C-[>OA <C-o>k
:inoremap <C-[>OB <C-o>j
:inoremap <C-[>OC <C-o>l
:inoremap <C-[>OD <C-o>h

:inoremap <C-[>P <C-o>P
:inoremap <C-[>Q <C-o>Q
:inoremap <C-[>R <C-o>R
:inoremap <C-[>S <C-o>S
:inoremap <C-[>T <C-o>T
:inoremap <C-[>U <C-o>U
" V
:inoremap <C-[>W <C-o>W
:inoremap <C-[>X <C-o>X
:inoremap <C-[>Y <C-o>Y
:inoremap <C-[>Z <C-o>Z
:inoremap <C-[><BSlash> <C-o><BSlash>

" ]
:inoremap <C-[>^ <C-o>^
:inoremap <C-[>_ <C-o>_

:inoremap <C-[>a <C-o>a
" :inoremap <C-[>b <C-o>b
:inoremap <C-[>c <C-o>c
:inoremap <C-[>d <C-o>d
:inoremap <C-[>e <C-o>e
" :inoremap <C-[>f <C-o>f
" g
:inoremap <C-[>h <C-o>h
:inoremap <C-[>i <C-o>i
:inoremap <C-[>j <C-o>j
:inoremap <C-[>k <C-o>k
:inoremap <C-[>l <C-o>l
:inoremap <C-[>m <C-o>m
:inoremap <C-[>n <C-o>n
:inoremap <C-[>o <C-o>o

:inoremap <C-[>p <C-o>p
:inoremap <C-[>q <C-o>q
:inoremap <C-[>r <C-o>r
:inoremap <C-[>s <C-o>s
:inoremap <C-[>t <C-o>t
:inoremap <C-[>u <C-o>u
" v
:inoremap <C-[>w <C-o>w
:inoremap <C-[>x <C-o>x
:inoremap <C-[>y <C-o>y
:inoremap <C-[>z <C-o>z
:inoremap <C-[>{ <C-o>{
:inoremap <C-[><Bar> <C-o><Bar>
:inoremap <C-[>} <C-o>}
:inoremap <C-[>~ <C-o>~

:imap <C-[><BSlash> <C-o><BSlash>


"
" == 8 of 8 ==
"
" third of three, here are the definitions
"
" for Normal View mode, so that
" accidentally unknowingly falling out of Insert Mode
" doesn't immediately much trip you up, and
" often puts you back into Insert Mode
"


:nnoremap ¸ Z
:nnoremap Ú :
:nnoremap Œ Q
:nnoremap › $i
:nnoremap ﬂ ^i
:nnoremap º 0i
:nnoremap ƒ f
:nnoremap † t
:nnoremap Ï F
:nnoremap Ê T
:nnoremap … ;i
:nnoremap ≤ ,i
:nnoremap ˙ hi
:nnoremap ¬ li
:nnoremap ∑ wi
:nnoremap é ei
:nnoremap ∫ bi
:nnoremap „ Wi
:nnoremap ´ Ei
:nnoremap ı Bi
:nnoremap ” {
:nnoremap ’ }
:nnoremap ˝ Gi
:nnoremap Ò Li
:nnoremap Â Mi
:nnoremap Ó Hi
:nnoremap ± +i
:nnoremap — _i
:nnoremap – -i
:nnoremap ∆ ji
:nnoremap ˚ ki
:nnoremap ¡ 1
:nnoremap € 2
:nnoremap £ 3
:nnoremap ¢ 4
:nnoremap ∞ 5
:nnoremap § 6
:nnoremap ¶ 7
:nnoremap • 8
:nnoremap ª 9
:nnoremap ≥ .i
:nnoremap ¨ Ui
:nnoremap Ω z
:nnoremap ÷ /
:nnoremap ¿ ?
:nnoremap ° *i
:nnoremap ‹ #i
:nnoremap ñ ni
:nnoremap ˜ Ni
:nnoremap ® r
:nnoremap å a
:nnoremap î i
:nnoremap ø o
:nnoremap ‰ R
:nnoremap Å A
:nnoremap ˆ I
:nnoremap Ø O
:nnoremap ≈ xi
:nnoremap ˛ Xi
:nnoremap Ô Ji
:nnoremap ß s
:nnoremap Í S
:nnoremap ∂ d
:nnoremap ç c
:nnoremap Î D
:nnoremap Ç C
:nnoremap π pi
:nnoremap ∏ Pi
:nnoremap Á Y
:nnoremap ⁄ !
:nnoremap æ '
:nnoremap ¯ <
:nnoremap ˘ >
:nnoremap € @
:nnoremap µ m
:nnoremap œ q
:nnoremap » <Bar>i
:nnoremap ` ~i

:nnoremap <C-[>SPC SPCi
:nnoremap <C-[>! !
:nnoremap <C-[># #i
:nnoremap <C-[>$ $i
:nnoremap <C-[>' '
:nnoremap <C-[>* *i
:nnoremap <C-[>+ +i
:nnoremap <C-[>, ,i
:nnoremap <C-[>- -i
:nnoremap <C-[>. .i
:nnoremap <C-[>/ /
:nnoremap <C-[>0 0
:nnoremap <C-[>1 1
:nnoremap <C-[>2 2
:nnoremap <C-[>3 3
:nnoremap <C-[>4 4
:nnoremap <C-[>5 5
:nnoremap <C-[>6 6
:nnoremap <C-[>7 7
:nnoremap <C-[>8 8
:nnoremap <C-[>9 9
:nnoremap <C-[>: :
:nnoremap <C-[>; ;i
:nnoremap <C-[>< <
:nnoremap <C-[>> >
:nnoremap <C-[>? ?
:nnoremap <C-[>@ @
:nnoremap <C-[>A A
:nnoremap <C-[>B Bi
:nnoremap <C-[>C C
:nnoremap <C-[>D D
:nnoremap <C-[>E Ei
:nnoremap <C-[>F F
:nnoremap <C-[>G Gi
:nnoremap <C-[>H Hi
:nnoremap <C-[>I I
:nnoremap <C-[>J Ji
:nnoremap <C-[>L Li
:nnoremap <C-[>M Mi
:nnoremap <C-[>N Ni
:nnoremap <C-[>O O
:nnoremap <C-[>OA k
:nnoremap <C-[>OB j
:nnoremap <C-[>OC l
:nnoremap <C-[>OD h
:nnoremap <C-[>P Pi
:nnoremap <C-[>Q Q
:nnoremap <C-[>R R
:nnoremap <C-[>S S
:nnoremap <C-[>T T
:nnoremap <C-[>U Ui
:nnoremap <C-[>W Wi
:nnoremap <C-[>X Xi
:nnoremap <C-[>Y Y
:nnoremap <C-[>Z Z
:nnoremap <C-[><BSlash> <BSlash>
:nnoremap <C-[>^ ^i
:nnoremap <C-[>_ _i
:nnoremap <C-[>a a
" :nnoremap <C-[>b bi
:nnoremap <C-[>c c
:nnoremap <C-[>d d
:nnoremap <C-[>e ei
" :nnoremap <C-[>f f
:nnoremap <C-[>h hi
:nnoremap <C-[>i i
:nnoremap <C-[>j ji
:nnoremap <C-[>k ki
:nnoremap <C-[>l li
:nnoremap <C-[>m m
:nnoremap <C-[>n ni
:nnoremap <C-[>o o
:nnoremap <C-[>p pi
:nnoremap <C-[>q q
:nnoremap <C-[>r r
:nnoremap <C-[>s s
:nnoremap <C-[>t t
:nnoremap <C-[>u ui
:nnoremap <C-[>w wi
:nnoremap <C-[>x xi
:nnoremap <C-[>y y
:nnoremap <C-[>z z
:nnoremap <C-[>{ {
:nnoremap <C-[><Bar> <Bar>i
:nnoremap <C-[>} }
:nnoremap <C-[>~ ~i


" copied from:  git clone https://github.com/pelavarre/pybashish.git
