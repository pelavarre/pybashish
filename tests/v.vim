1234567

    5
    5
    5

usage: vi.py [-h] [+PLUS] [--pwnme [BRANCH]] [--version] [FILE ...]

read files, accept edits, write files

positional arguments:
  FILE              a file to edit (default: '/dev/stdin')

optional arguments:
  -h, --help        show this help message and exit
  +PLUS             next Ex command to run, just after loading first File
  --pwnme [BRANCH]  update and run this Code, don't just run it
  --version         print a hash of this Code (its Md5Sum)

quirks:
  works as pipe filter, pipe source, or pipe drain, like the pipe drain:  ls |vi -

keyboard cheat sheet:
  ZQ ZZ ⌃Zfg  :q!⌃M :n!⌃M :w!⌃M :wq!⌃M  => how to quit Vi Py
  ⌃C Up Down Right Left Space Delete Return  => natural enough
  0 ^ $ fx tx Fx Tx ; , | h l  => leap to column
  b e w B E W { }  => leap across small word, large word, paragraph
  G 1G H L M - + _ ⌃J ⌃N ⌃P j k  => leap to row, leap to line
  1234567890 Esc  => repeat, or don't
  ⌃F ⌃B ⌃E ⌃Y zb zt zz 99zz  => scroll rows
  ⌃L 999⌃L ⌃G  => clear lag, inject lag, measure lag and show version
  \n \i \F Esc ⌃G  => toggle line numbers, search case/ regex, show hits
  /... Delete ⌃U ⌃C Return  ?...   * £ # n N  => start search, next, previous
  :?Return :/Return :g/Return  => search behind, ahead, print all, or new search
  a i rx o A I O R ⌃O Esc ⌃C  => enter/ suspend-resume/ exit insert/ replace
  x X D J s S C  => cut chars, join lines, cut & insert

keyboard easter eggs:
  9^ G⌃F⌃F 1G⌃B G⌃F⌃E 1G⌃Y ; , n N 2G9k \n99zz ?Return /Return :g/Return
  Esc ⌃C 123Esc 123⌃C zZZQ /⌃G⌃CZQ 3ZQ f⌃C w*Esc w*⌃C w*123456n⌃C w*:g/⌃M⌃C g/⌃Z
  Qvi⌃My REsc R⌃Zfg OO⌃O_⌃O^ \Fw*/Up \F/$Return 2⌃G :vi⌃M :n

