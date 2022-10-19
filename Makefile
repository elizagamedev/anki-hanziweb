ZIP		?= zip

NAME		:= hanziweb
VERSION		:= 0.1.2
ANKIADDON	:= $(NAME)-$(VERSION).ankiaddon
DEPS		:= __init__.py \
		   config.json \
		   config.md \
		   manifest.json \
		   README.md \
		   CHANGELOG.md \
		   LICENSE \
		   thirdparty

all: 	$(ANKIADDON)
clean:	; rm -rf *.ankiaddon __pycache__ README.html
.PHONY: all clean

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -r9 $@ $^ -x '*/.git'
