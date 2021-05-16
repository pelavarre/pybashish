" ~/.vimrc


" Lay out Spaces and Tabs

:set softtabstop=4 shiftwidth=4 expandtab
autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab


" Configure Vim

:syntax on

:set ignorecase
:set nowrap
" :set number

:set hlsearch
" :nnoremap <esc><esc> :noh<return>  " nope, corrupts multiple Esc
" hlsearch, noh = toggle on/off the highlighting of all hits of search on screen
" n-no-remap = remap in the normal (not-insert) mode except don't recurse thru other remaps

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:set ruler  " not inferred from :set ttyfast at Mac
:set showcmd  " not inferred from :set ttyfast at Linux or Mac


" Add keys (without redefining keys)

:nnoremap <Bslash>m :set mouse=a<return>  " mouse moves cursor
:nnoremap <Bslash>M :set mouse=<return>   " mouse selects chars to copy-paste

:nnoremap <Bslash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun
" RStripEachLine = delete the trailing whitespace from each line (not yet from file)
