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
" :set hlsearch  " highlight all hits of search
" /$$  " turn the highlights off by failing a search
" :noh  " turn the highlights off by command
" :nnoremap <esc><esc> :noh<return>  " nope, fails tests of multiple Esc

:highlight RedLight ctermbg=red
:call matchadd('RedLight', '\s\+$')

:nnoremap <Bslash>w :call RStripEachLine()<return>
" n-no-remap = remap in the normal (not-insert) mode except don't recurse thru other remaps
function! RStripEachLine()
    let with_line = line(".")
    let with_col = col(".")
    %s/\s\+$//e
    call cursor(with_line, with_col)
endfun
" RStripEachLine = delete the trailing whitespace from each line (not from file)

" copied from:  git clone https://github.com/pelavarre/pybashish.git
