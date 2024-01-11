ZIP		?= zip
KANJI_BANK	?= kanji_bank_1.json

NAME		:= hanziweb
VERSION	:= 1.0.0
ANKIADDON	:= $(NAME)-$(VERSION).ankiaddon
DEPS		:= __init__.py \
		   common.py \
		   hanziweb.py \
		   jitai.py \
		   config.json \
		   config.md \
		   manifest.json \
		   README.md \
		   CHANGELOG.md \
		   LICENSE \
		   kyujipy \
		   kanji-onyomi.json \
		   phonetics.json

all: 	$(ANKIADDON)
clean:	; rm -rf *.ankiaddon __pycache__ README.html kanji-onyomi.json phonetics.json
.PHONY: all clean format
.DELETE_ON_ERROR:

format:
	isort *.py
	black *.py

kanji-onyomi.json: tools/make-kanji-onyomi.py $(KANJI_BANK)
	python3 tools/make-kanji-onyomi.py < $(KANJI_BANK) > kanji-onyomi.json

phonetics.json: tools/make-phonetics.py
	python3 tools/make-phonetics.py > phonetics.json

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -r9 $@ $^ -x '*/__pycache__/*'
