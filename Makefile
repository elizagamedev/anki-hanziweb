ZIP		?= zip
KANJIDIC	?= kanjidic2.xml

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
		   kyujipy \
		   kanji-onyomi.json

all: 	$(ANKIADDON)
clean:	; rm -rf *.ankiaddon __pycache__ README.html kanji-onyomi.json
.PHONY: all clean format

format:
	isort *.py
	black *.py
.PHONY: format

kanji-onyomi.json: tools/make-kanji-onyomi.sh $(KANJIDIC)
	tools/make-kanji-onyomi.sh $(KANJIDIC) kanji-onyomi.json

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -r9 $@ $^ -x '*/.git'
