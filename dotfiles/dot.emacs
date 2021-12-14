; ~/.emacs


;; Configure Emacs

(setq-default indent-tabs-mode nil)  ; indent with Spaces not Tabs
(setq-default tab-width 4)  ; count out columns of C-x TAB S-LEFT/S-RIGHT

(when (fboundp 'global-superword-mode) (global-superword-mode 't))  ; accelerate M-f M-b

(column-number-mode)  ; show column number up from 0, not just line number up from 1


;; Add keys (without redefining keys)
;; (as dry run by M-x execute-extended-command, M-: eval-expression)

(global-set-key (kbd "C-c %") 'query-replace-regexp)  ; for when C-M-% unavailable
(global-set-key (kbd "C-c -") 'undo)  ; for when C-- alias of C-_ unavailable
(global-set-key (kbd "C-c O") 'overwrite-mode)  ; aka toggle Insert
(global-set-key (kbd "C-c b") 'ibuffer)  ; for ? m Q I O multi-buffer replace
(global-set-key (kbd "C-c m") 'xterm-mouse-mode)  ; toggle between move and select
(global-set-key (kbd "C-c n") 'display-line-numbers-mode)  ; toggle line numbers
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


;; Give up unquoted entry of some chars outside Basic Latin
;; so as to define the Option/Alt Shift key to mean Meta anyhow
;; when macOS Terminal > Preferences > Profiles > Keyboard > Use Option as Meta Key = No

(define-prefix-command 'my-copyright-sign-map)
(global-set-key (kbd "©") 'my-copyright-sign-map)  ; U00A9 CopyrightSign
(global-set-key (kbd "© ©") (key-binding (kbd "M-g M-g")))
(global-set-key (kbd "© TAB") (key-binding (kbd "M-g TAB")))

(global-set-key (kbd "®") (key-binding (kbd "M-r")))  ; U00AE RegisteredSign
(global-set-key (kbd "¯") (key-binding (kbd "M-<")))  ; U00AF Macron
(global-set-key (kbd "µ") (key-binding (kbd "M-m")))  ; U00B5 MicroSign
(global-set-key (kbd "ƒ") (key-binding (kbd "M-f")))  ; U0192 LatinSmallLetterFWithHook
(global-set-key (kbd "˘") (key-binding (kbd "M->")))  ; U02D8 Breve
(global-set-key (kbd "˙") (key-binding (kbd "M-h")))  ; U02D9 DotAbove
(global-set-key (kbd "Ω") (key-binding (kbd "M-z")))  ; U03A9 GreekCapitalLetterOmega
(global-set-key (kbd "∂") (key-binding (kbd "M-d")))  ; U2202 PartialDifferential
(global-set-key (kbd "√") (key-binding (kbd "M-v")))  ; U221A SquareRoot
(global-set-key (kbd "∫") (key-binding (kbd "M-b")))  ; U222B Integral
(global-set-key (kbd "ﬁ") (key-binding (kbd "M-%")))  ; UFB01 LatinSmallLigatureFI

;; ⌥→ ⌥← come in and work like Esc f and Esc b without needing help

(global-set-key (kbd "»")  ; U00BB RightPointingDoubleAngleQuotationMark
    (key-binding (kbd "M-|")))

(global-set-key (kbd "–") (key-binding (kbd "M--")))  ; U2013 EnDash
(global-set-key (kbd "º")  ; U00BA MasculineOrdinalIndicator
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-0"))))
(global-set-key (kbd "¡")  ; U00A1 InvertedExclamationMark
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-1"))))
(global-set-key (kbd "€")  ; U20AC EuroSign
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-2"))))
(global-set-key (kbd "£")  ; U00A3 PoundSign
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-3"))))
(global-set-key (kbd "¢")  ; U00A2 CentSign
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-4"))))
(global-set-key (kbd "∞")  ; U221E Infinity
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-5"))))
(global-set-key (kbd "§")  ; U00A7 SectionSign
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-6"))))
(global-set-key (kbd "¶")  ; U00B6 PilcrowSign
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-7"))))
(global-set-key (kbd "•")  ; U2022 Bullet [Pearl]
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-8"))))
(global-set-key (kbd "ª")  ; U00AA FeminineOrdinalIndicator
    (lambda () (interactive) (execute-kbd-macro (read-kbd-macro "M-9"))))

; these M- decimal digits kind of work and kind of don't
; they get you started, but you have to let go the Meta key after the first keystroke


;; Sacrifice M-3 to get '# 'self-insert-command at Mac British Option As Meta Key

(global-set-key (kbd "M-3")
    (lambda () (interactive) (insert-char #x23)))  ; # '#' not '£'


; copied from:  git clone https://github.com/pelavarre/pybashish.git
