#
# files/cpp.bash:  The C++ Programming Language
#

g++ version

#
(cat >c.cpp <<EOF
#include <iostream>
int main() {
        std::cout << "Hello, C++ World" << std::endl;
}
EOF
) && g++ -Wall -Wpedantic c.cpp && ./a.out
# TODO: evaluate g++ -Weverything -Werror -w c.c
#

# copied from:  git clone https://github.com/pelavarre/pybashish.git
