ZIP		?= zip
KANJIDIC	?= kanjidic2.xml
KANJI_BANK	?= kanji_bank_1.json

NAME		:= hanziweb
VERSION	:= 1.2.0
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
		   phonetics.json \
		   hanziweb.min.js

all: 	$(ANKIADDON)
clean:	; rm -rf *.ankiaddon \
		__pycache__ \
		kanji-onyomi.json \
		kanjidic-onyomi.json \
		phonetics.json \
		hanziweb.min.js
.PHONY: all clean format
.DELETE_ON_ERROR:

format:
	isort *.py
	black *.py

kanjidic-onyomi.json: tools/make-kanji-onyomi.sh $(KANJIDIC)
	tools/make-kanji-onyomi.sh $(KANJIDIC) $@

kanji-onyomi.json: tools/make-kanji-onyomi.py $(KANJI_BANK) kanjidic-onyomi.json
	python3 tools/make-kanji-onyomi.py $(KANJI_BANK) kanjidic-onyomi.json > $@

phonetics.json: tools/make-phonetics.py
	python3 tools/make-phonetics.py > $@

hanziweb.min.js: hanziweb.js
	closure-compiler --js $< --js_output_file $@

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -r9 $@ $^ -x '*/__pycache__/*'
