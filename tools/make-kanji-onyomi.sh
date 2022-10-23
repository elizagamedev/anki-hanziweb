#!/usr/bin/env nix-shell
#!nix-shell -i bash -p yq

# This script generates a JSON object which maps kanji to their onyomi.

set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "usage: make-kanji-onyomi.sh KANJIDIC-XML-FILE OUTPUT-FILE" >&2
  exit 1
fi

xq '
  [.kanjidic2.character | .[]
    | {"key": .literal,
       "value": [.reading_meaning.rmgroup.reading
      | if type=="array" then .[]
        else . end
      | select(."@r_type" == "ja_on")
      | ."#text"]}
    | select(.value | length > 0)]
  | from_entries' \
   "$1" > "$2"
if [[ $? -ne 0 ]]; then
  rm -f "$2"
  exit 1
fi
