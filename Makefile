ZIP		?= zip

NAME		:= hanziweb
VERSION		:= 0.1.0
ANKIADDON	:= $(NAME)-$(VERSION).ankiaddon
DEPS		:= __init__.py config.json config.md manifest.json

all: 	$(ANKIADDON)
clean:	; rm -rf $(ANKIADDON) __pycache__
.PHONY: all clean

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -9 $@ $^
