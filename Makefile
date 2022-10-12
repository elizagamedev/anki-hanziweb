ZIP		?= zip

NAME		:= hanziweb
ANKIADDON	:= $(NAME).ankiaddon
DEPS		:= __init__.py config.json config.md

all: 	$(ANKIADDON)
clean:	; rm -rf $(ANKIADDON) __pycache__
.PHONY: all clean

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -9 $@ $^
