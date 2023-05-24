ZIP		?= zip
KANJIDIC	?= kanjidic2.xml

NAME		:= hanziweb
VERSION		:= 1.0.0
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

format:
	isort *.py
	black *.py

kanji-onyomi.json: tools/make-kanji-onyomi.sh $(KANJIDIC)
	tools/make-kanji-onyomi.sh $(KANJIDIC) kanji-onyomi.json

phonetics.json: tools/make-phonetics.py
	python3 tools/make-phonetics.py > phonetics.json

$(ANKIADDON): $(DEPS)
	rm -f $@
	$(ZIP) -r9 $@ $^ -x '*/__pycache__/*'
