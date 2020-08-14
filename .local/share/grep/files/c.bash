#
# files/c.bash:  The C Programming Language
#

gcc --version

#
(cat >c.c <<EOF
main() {
    puts("Hello, World!");
}
EOF
) && gcc -Wno-implicit-int -Wno-implicit-function-declaration c.c && ./a.out
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
