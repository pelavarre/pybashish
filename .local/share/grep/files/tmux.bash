#
# files/tmux.bash:  TMux
#

tmux --version

tmux
tmux attach  # attach.session til 'no sessions'
tmux capture-pane -S -9999  # 1 of 3
tmux save-buffer ~/t.tmux   # 2 of 3
chmod ugo+r ~/t.tmux        # 3 of 3

#
# TMux ⌃B ?  => list all key bindings till ⌃X⌃C
# TMux ⌃B [ Esc  => page up etc. a la Emacs
# TMux ⌃B C  => new-window
# TMux ⌃B D  => detach-client
#