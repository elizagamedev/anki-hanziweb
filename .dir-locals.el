;;; Directory Local Variables
;;; For more information see (info "(emacs) Directory Variables")

((python-mode . ((eglot-workspace-configuration . (:pylsp
                                                   (:plugins
                                                    (:autopep8
                                                     (:enabled :json-false)
                                                     :yapf
                                                     (:enabled :json-false)
                                                     :black
                                                     (:enabled t)))))
                 (fill-column . 88))))
