" ~/.vimrc


"
" Lay out Spaces and Tabs
"


:set softtabstop=4 shiftwidth=4 expandtab
autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab


"
" Configure Vim
"


:set background=light
:syntax on

:set ignorecase
:set nowrap

:set hlsearch

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:set ruler  " quirkily not inferred from :set ttyfast at Mac
:set showcmd  " quirkily not inferred from :set ttyfast at Linux or Mac


"
" Add keys (without redefining keys)
"
" N-NoRe-Map = Map only for Normal (View) Mode and don't Recurse through other maps
"


" Esc b  => macOS ⌥← Option Left-Arrow  => take as alias of ⇧B
" Esc f  => macOS ⌥→ Option Right-Arrow  => take as alias of ⇧W
:nnoremap <Esc>b B
:nnoremap <Esc>f W

" \ Delay  => gracefully do nothing
:nnoremap <BSlash> :<return>

" \ Esc  => cancel the :set hlsearch highlighting of all search hits on screen
:nnoremap <BSlash><Esc> :noh<return>

" \ e  => reload, if no changes not-saved
:nnoremap <BSlash>e :e<return>

" \ i  => toggle ignoring case in searches, but depends on :set nosmartcase
:nnoremap <BSlash>i :set invignorecase<return>

" \ m  => mouse moves cursor
" \ M  => mouse selects zigzags of chars to copy-paste
:nnoremap <BSlash>m :set mouse=a<return>
:nnoremap <BSlash>M :set mouse=<return>

" \ n  => toggle line numbers
:nnoremap <BSlash>n :set invnumber<return>

" \ w  => delete the trailing whitespace from each line (not yet from file)
:nnoremap <BSlash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

" accept Option+3 from US Keyboards as meaning '#' \u0023 Hash Sign

:cmap <Esc>3 #
:imap <Esc>3 #
:nmap <Esc>3 #
:omap <Esc>3 #
:smap <Esc>3 #
:vmap <Esc>3 #
:xmap <Esc>3 #


"
" Require ⌃V prefix to input some chars outside Basic Latin
" so as to take macOS Terminal Option Key as meaning Vim ⌃O
" despite macOS Terminal > Preferences > ... > Keyboard > Use Option as Meta Key = No
"

" leap to column
:inoremap › <C-o>$
:nnoremap › $
:inoremap ﬂ <C-o>^
:nnoremap ﬂ ^
:inoremap º <C-o>0
:nnoremap º 0
:inoremap ƒ <C-o>f
:nnoremap ƒ f
:inoremap † <C-o>t
:nnoremap † t
:inoremap Ï <C-o>F
:nnoremap Ï F
:inoremap Ê <C-o>T
:nnoremap Ê T
:inoremap … <C-o>;
:nnoremap … ;
:inoremap ≤ <C-o>,
:nnoremap ≤ ,
:inoremap ˙ <C-o>h
:nnoremap ˙ h
:inoremap ¬ <C-o>l
:nnoremap ¬ l

" leap across small words, large words, or paragraphs,
" except you press ⌥E E to mean E (because ⌥E⌥E comes across as ⌥⇧E ⌥⇧E)
:inoremap ∑ <C-o>w
:nnoremap ∑ w
:inoremap é <C-o>e
:nnoremap é e
:inoremap ∫ <C-o>b
:nnoremap ∫ b
:inoremap „ <C-o>W
:nnoremap „ W
:inoremap ´ <C-o>E
:nnoremap ´ E
:inoremap ı <C-o>B
:nnoremap ı B
:inoremap ” <C-o>{
:nnoremap ” {
:inoremap ’ <C-o>}
:nnoremap ’ }

" leap to line, screen row
:inoremap ˝ <C-o>G
:nnoremap ˝ G
:inoremap Ò <C-o>L
:nnoremap Ò L
:inoremap Â <C-o>M
:nnoremap Â M
:inoremap Ó <C-o>H
:nnoremap Ó H
:inoremap ± <C-o>+
:nnoremap ± +
:inoremap — <C-o>_
:nnoremap — _
:inoremap – <C-o>-
:nnoremap – -
:inoremap ∆ <C-o>j
:nnoremap ∆ j
:inoremap ˚ <C-o>k
:nnoremap ˚ k

" spell out how many times to repeat,
" except you have to release the Option key after striking the last digit,
" and the ⌃J, ⌃N, and ⌃P all work with the Control key alone, no Option key needed
:inoremap ¡ <C-o>1
:nnoremap ¡ 1
:inoremap € <C-o>2
:nnoremap € 2
:inoremap £ <C-o>3
:nnoremap £ 3
:inoremap ¢ <C-o>4
:nnoremap ¢ 4
:inoremap ∞ <C-o>5
:nnoremap ∞ 5
:inoremap § <C-o>6
:nnoremap § 6
:inoremap ¶ <C-o>7
:nnoremap ¶ 7
:inoremap • <C-o>8
:nnoremap • 8
:inoremap ª <C-o>9
:nnoremap ª 9
:inoremap º <C-o>0
:nnoremap º 0

" scroll or refresh screen,
" except you have to release the Option key after striking Option+Z,
" and ⌃F, ⌃B, ⌃E, and ⌃Y all work with the Control key alone, no Option key needed,
" and ⌃L works with the Control key alone too because of this setup
:inoremap Ω <C-o>z
:nnoremap Ω z
:inoremap <C-l> <C-o><C-l>

" gateway to whatever custom code you have dropped onto Vim <BSlash>
:imap « <C-o>\
:nmap « \

" search ahead, behind, next,
" except you press ⌥N N to mean N (because ⌥N⌥N comes across as ⌥⇧N ⌥⇧N)
:inoremap ÷ <C-o>/
:nnoremap ÷ /
:inoremap ¿ <C-o>?
:nnoremap ¿ ?
:inoremap ° <C-o>*
:nnoremap ° *
:inoremap ‹ <C-o>#
:nnoremap ‹ #
:inoremap ñ <C-o>n
:nnoremap ñ n
:inoremap ˜ <C-o>N
:nnoremap ˜ N

" move and replace and insert, or not
:inoremap ® <C-o>r
:nnoremap ® r
:inoremap å <C-o>a
:nnoremap å a
:inoremap î <C-o>i
:nnoremap î i
:inoremap o <C-o>o
:nnoremap o o
:inoremap ‰ <C-o>R
:nnoremap ‰ R
:inoremap Å <C-o>A
:nnoremap Å A
:inoremap ˆ <C-o>I
:nnoremap ˆ I
:inoremap Ø <C-o>O
:nnoremap Ø O

" cut chars, join/ cut lines, insert after cut,
" except you have to release the Option key after striking D or C
:inoremap ≈ <C-o>x
:nnoremap ≈ x
:inoremap ˛ <C-o>X
:nnoremap ˛ X
:inoremap Ô <C-o>J
:nnoremap Ô J
:inoremap ß <C-o>s
:nnoremap ß s
:inoremap Í <C-o>S
:nnoremap Í S
:inoremap ∂ <C-o>d
:nnoremap ∂ d
:inoremap ç <C-o>c
:nnoremap ç c


" copied from:  git clone https://github.com/pelavarre/pybashish.git
