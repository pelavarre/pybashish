"
" files/.vimrc:  Vim configuration
"

" ~/.vimrc

:set softtabstop=4 shiftwidth=4 expandtab
autocmd FileType c,cpp   set softtabstop=8 shiftwidth=8 expandtab
autocmd FileType python  set softtabstop=4 shiftwidth=4 expandtab

:syntax on

:set ignorecase
:set nowrap
" :set number

:set hlsearch
:nnoremap <esc><esc> :noh<return>
" hlsearch, noh = toggle on/off highlighting of all hits of search
" n-no-remap = remap in the normal (not-insert) mode except don't recurse thru other remaps

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:nnoremap <Bslash>w :call RStripEachLine()<return>
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun
" RStripEachLine = delete the trailing whitespace from each line (not from file)

" copied from:  git clone https://github.com/pelavarre/pybashish.git
