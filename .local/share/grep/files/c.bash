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
) && gcc -w c.c && ./a.out
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
