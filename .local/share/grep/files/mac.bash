#
# files/mac.bash:  Bash of Mac Clipboard, indexed by Python of Str
#

cat - | grep . | tr -c '[ -~\n]' '@'  # substitute '@', when Mac 'cat -etv' doesn't

curl -O -Ss ...  # Mac a la Linux wget
gunzip -c ...  # Mac a la Linux zcat
openssl dgst -md5 ...  # Mac a la Linux md5sum
openssl dgst -sha1 ...  # Mac a la Linux sha1sum
tail -r  # Mac a la Linux tac

pbpaste | hexdump -C | pbcopy  # hexdump
pbpaste | sed 's,^,    ,' | pbcopy  # indent
pbpaste | sed 's,^    ,,' | pbcopy  # dedent undent
pbpaste | tr '[A-Z]' '[a-z]' | pbcopy  # lower
pbpaste | sed 's,^  *,,' | pbcopy  # lstrip
pbpaste | cat <(tr '\n' ' ') <(echo) | pbcopy  # join
pbpaste | cat -n | sort -nr | cut -f2- | pbcopy  # reverse
pbpaste | sed 's,  *$,,' | pbcopy  # rstrip
pbpaste | sort | pbcopy  # sort
pbpaste | sed 's,  *, ,g' | tr ' ' '\n' | pbcopy  # split
pbpaste | sed 's,^\(.*\)\([.][^.]*\)$,\1 \2,' | pbcopy  # splitext
pbpaste | sed 's,^  *,,'  | sed 's,  *$,,' | pbcopy  # strip
pbpaste | tr '[a-z]' '[A-Z]' | pbcopy  # upper
pbpaste | sed 's,[^ -~],?,g' | pbcopy  # ascii errors replace with "\x3F" question mark
pbpaste | sed 's,[^ -~],,g' | pbcopy  # ascii errors ignore

pbpaste >p  # pb stash
cat p | pbcopy  # pb stash pop

uname

# copied from:  git clone https://github.com/pelavarre/pybashish.git
