#
# files/ubuntu.bash:  Ubuntu
#

head /etc/apt/sources.list  # lsb_release
cat /etc/lsb-release  # lsb_release
lsb_release -a  # lsb_release

: sudo true
: date; : time sudo -n apt-get -y update
: date; : time sudo -n apt-get -y upgrade
: date; : time sudo -n apt-get -y dist-upgrade