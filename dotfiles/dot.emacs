; ~/.emacs


;; Configure Emacs

(setq-default indent-tabs-mode nil)  ; indent with Spaces not Tabs
(setq-default tab-width 4)  ; count out columns of C-x TAB S-LEFT/S-RIGHT

(when (fboundp 'global-superword-mode) (global-superword-mode 't))  ; accelerate M-f M-b


;; Add keys (without redefining keys)
;; (as dry run by M-x execute-extended-command, M-: eval-expression)

(global-set-key (kbd "C-c %") 'query-replace-regexp)  ; for when C-M-% unavailable
(global-set-key (kbd "C-c -") 'undo)  ; for when C-- alias of C-_ unavailable
(global-set-key (kbd "C-c b") 'ibuffer)  ; for ? m Q I O multi-buffer replace
(global-set-key (kbd "C-c m") 'xterm-mouse-mode)  ; toggle between move and select
(global-set-key (kbd "C-c O") 'overwrite-mode)  ; aka toggle Insert
(global-set-key (kbd "C-c o") 'occur)
(global-set-key (kbd "C-c r") 'revert-buffer)
(global-set-key (kbd "C-c s") 'superword-mode)  ; toggle accelerate of M-f M-b
(global-set-key (kbd "C-c w") 'whitespace-cleanup)


;; Def C-c | = M-h C-u 1 M-| = Mark-Paragraph Universal-Argument Shell-Command-On-Region

(global-set-key (kbd "C-c |") 'like-shell-command-on-region)
(defun like-shell-command-on-region ()
    (interactive)
    (unless (mark) (mark-paragraph))
    (setq string (read-from-minibuffer
        "Shell command on region: " nil nil nil (quote shell-command-history)))
    (shell-command-on-region (region-beginning) (region-end) string nil 'replace)
    )


;; Turn off enough of macOS to run Emacs

; press Esc to mean Meta, or run Emacs Py in place of Emacs, or else
;   macOS Terminal > Preferences > Profiles > Keyboard > Use Option as Meta Key

; press ⌃⇧2 or ⌃Space and hope it comes out as C-@ or C-SPC to mean 'set-mark-command
;   even though older macOS needed you to turn off System Preferences > Keyboard >
;   Input Sources > Shortcuts > Select The Previous Input Source  ⌃Space


; copied from:  git clone https://github.com/pelavarre/pybashish.git
