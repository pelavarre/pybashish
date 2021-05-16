; ~/.emacs


;; Configure Emacs

(setq-default indent-tabs-mode nil)  ; indent with Spaces not Tabs

(when (fboundp 'global-superword-mode) (global-superword-mode 't))  ; accelerate M-f M-b


;; Define new keys
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

; macOS Terminal > Preferences > Profile > Use Option as Meta Key
; ; or press Esc in place of Meta

; macOS System Preferences > Keyboard > Input Sources > Shortcuts > Previous Source
; ; or press ⌃⇧2 to reach C-@ to mean C-SPC 'set-mark-command


; copied from:  git clone https://github.com/pelavarre/pybashish.git
