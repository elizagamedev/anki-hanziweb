#!/usr/bin/env nix-shell
#!nix-shell -i bash -p yq

# This script displays a list of all kokuji in KANJIDIC that contain an
# on-reading, excluding kanji that are known to not have a phonetic component.

set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "usage: list-kokuji-with-on-readings.sh KANJIDIC-XML-FILE" >&2
  exit 1
fi

xq -r '
  .kanjidic2.character[]
  | select(.reading_meaning.rmgroup.meaning
    | if type=="array" then map(. == "(kokuji)") | any
      else . == "kokuji" end)
  | select(.reading_meaning.rmgroup.reading
    | if type=="array" then map(."@r_type" == "ja_on") | any
      else ."@r_type" == "ja_on" end)
  | .literal' \
   "$1" | sed '/[雫腺鱈弖扨鮠桛]/d'
