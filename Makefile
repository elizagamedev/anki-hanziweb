ZIP		?= zip

NAME		:= hanziweb
VERSION		:= 0.1.1
ANKIADDON	:= $(NAME)-$(VERSION).ankiaddon
DEPS		:= __init__.py \
		   config.json \
		   config.md \
		   manifest.json \
		   README.md \
		   CHANGELOG.md \
		   LICENSE

all: 	$(ANKIADDON)
clean:	; rm -rf $(ANKIADDON) __pycache__
.PHONY: all clean

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -9 $@ $^
