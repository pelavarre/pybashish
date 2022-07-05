" ~/.vimrc


"
" Lay out Spaces and Tabs
"


:set softtabstop=4 shiftwidth=4 expandtab
:autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
:autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab


"
" Configure Vim
" Don't trust ':set ttyfast' to imply ':set showcmd' and ':set ruler'
"


:set background=dark
:set background=light
:syntax off
:syntax on

:set noshowmode
:set showmode  " say '-- INSERT --' in bottom line while you remain in Insert Mode
:set noshowcmd
:set showcmd  " show the Key pressed with Option/Alt, while waiting for next Key
:set noruler
:set ruler  " show the Line & Column Numbers of the Cursor
:set nonumber
:set invnumber
:set number  " show the Line Number of each Line  "

:set noignorecase
:set invignorecase
:set ignorecase
:set wrap
:set nowrap

:set nohlsearch
:set hlsearch

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:startinsert  " start in Insert Mode, vs default of start in Normal (View) Mode
:stopinsert  " start in Normal View Mode, not in Insert Mode


"
" Add keys (without redefining keys)
"
" N-NoRe-Map = Map only for Normal (View) Mode and don't Recurse through other maps
"


" macOS ⌥← Option Left-Arrow  => Esc B = take as alias of ⇧B
" macOS ⌥→ Option Right-Arrow  => Esc F = take as alias of ⇧W
:nnoremap <Esc>b B
:nnoremap <Esc>f W


" \ \  => gracefully do nothing
:nnoremap <BSlash><BSlash> :<return>

" \ Esc  => cancel the :set hlsearch highlighting of all search hits on screen
:nnoremap <BSlash><Esc> :noh<return>

" \ ⇧I  => toggle ignoring case in searches, but depends on :set nosmartcase
:nnoremap <BSlash>i :set invignorecase<return>

" \ M  => mouse moves cursor
" \ ⇧M  => mouse selects zigzags of chars to copy-paste
:nnoremap <BSlash>m :set mouse=a<return>
:nnoremap <BSlash>M :set mouse=<return>

" \ N  => toggle line numbers
:nnoremap <BSlash>n :set invnumber<return>

" \ W  => delete the trailing whitespace from each line (not yet from file)
:nnoremap <BSlash>w :call RStripEachLine()<return>
:function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

" ⇧Z E  => reload, if no changes not-saved
:nnoremap Ze :e<return>
" ⇧Z ⇧E  => discard changes and reload
:nnoremap ZE :e!<return>
" ⇧Z ⇧Q => Quit Without Saving, by default
" ⇧Z ⇧W  => save changes
:nnoremap ZW :w<return>
" ⇧Z ⇧Z => Save Then Quit, by default


"
" Call out to run Vim mostly in Insert Mode, by redefining many mostly unused keys
"   and
"

:source ~/.insert.vimrc  " redefine obscure Option/Alt keys to stay in Insert Mode
:set nonumber


" copied from:  git clone https://github.com/pelavarre/pybashish.git
