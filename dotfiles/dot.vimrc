" ~/.vimrc


"
" Lay out Spaces and Tabs
"


:set softtabstop=4 shiftwidth=4 expandtab
:autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
:autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab


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
" \ E  => discard changes and reload
:nnoremap <BSlash>E :e!<return>

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
:function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun

" \ W  => save changes
:nnoremap <BSlash>W :w<return>


"
" Call out to run Vim mostly in Insert Mode, by redefining many mostly unused keys
"   and
"

:source ~/.insert.vimrc  " redefine obscure Option/Alt keys to stay in Insert Mode
:startinsert  " start in Insert Mode, vs default of start in Normal (View) Mode


" copied from:  git clone https://github.com/pelavarre/pybashish.git
