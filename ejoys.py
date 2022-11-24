# Eliza's Jank On-Yomi Sucker
#
# Attempts to suck out all the kanji in a phrase which use the on-yomi reading. Very
# jank and pretty naive.

import json
from dataclasses import dataclass
from pathlib import PurePath
from typing import Callable, Iterable, Optional, Sequence

from anki.collection import SearchNode
from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId
from aqt.qt import QAction, QMenu  # type: ignore
from aqt.utils import qconnect, showInfo, tooltip

from .common import (
    HANZI_REGEXP,
    KATAKANA_GREEDY_REGEXP,
    VERSION,
    Config,
    assert_is_not_none,
    html_tag,
    mw,
    normalize_unicode,
    show_report,
)


def expand_onyomi(onyomi: dict[str, list[str]]) -> dict[str, list[str]]:
    """Adds extra entries to the onyomi dict (like tenten, small tsu) to increase
    sucking ability."""
    result = {}
    for kanji, onyomi_list in onyomi.items():
        new_onyomi_list = list(onyomi_list)
        result[kanji] = new_onyomi_list

        # Small tsu
        for an_onyomi in onyomi_list:
            if an_onyomi.endswith("ツ") or an_onyomi.endswith("チ"):
                new_onyomi_list.append(an_onyomi[0:-1] + "ッ")

        # Ten-ten, maru
        for an_onyomi in onyomi_list:
            if an_onyomi.endswith("ツ") or an_onyomi.endswith("チ"):
                new_onyomi_list.append(an_onyomi[0:-1] + "ッ")


def suck(onyomi: dict[str, list[str]], expression: str, reading: str) -> list[str]:
    if not expression or not reading:
        return []

    leading_katakana_match = KATAKANA_GREEDY_REGEXP.match(expression)
    if leading_katakana_match:
        leading_katakana = leading_katakana_match[0]
        if reading.startswith(leading_katakana):
            length = len(leading_katakana)
            return suck(onyomi, expression[length:], reading[length:])
        return []

    onyomi_list = onyomi.get(expression[0])
    if not onyomi_list:
        return []

    candidates = []
    for an_onyomi in onyomi_list:
        if reading.startswith(an_onyomi):
            an_onyomi_length = len(an_onyomi)
            candidate = suck(onyomi, expression[1:], reading[an_onyomi_length:])
            if candidate:
                candidates.append((an_onyomi, candidate))
    best = max(candidates, default=None, key=lambda x: len(x[1]))
    if best is None:
        return []
    return [best[0]] + best[1]
