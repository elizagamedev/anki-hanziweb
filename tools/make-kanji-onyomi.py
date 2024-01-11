from typing import Any, Iterable
import json
import re
import sys


def gather_readings(kanji: str, definition: list[str]) -> dict[str, list[str]]:
    # HACK: Entry for 灯 is uniquely formatted.
    # Data retrieved from Wiktionary 2024-01-21.
    # https://ja.wiktionary.org/wiki/%E7%81%AF
    if kanji == "灯":
        return {
            "呉音": ["チョウ（チャゥ）（表外）"],
            "漢音": [" テイ（ティ）（表外）"],
            "慣用音": ["チン（表外）", "トン（表外）"],
        }

    try:
        onyomi_index = next(i for i, it in enumerate(definition) if "音読" in it) + 1
    except StopIteration:
        return {}

    result: dict[str, list[str]] = {}
    for it in definition[onyomi_index:]:
        if it.startswith("ー") or it.startswith("＝") or "訓読" in it or it == "無し":
            break

        split = re.split(r"\s*[：:]\s*", it, maxsplit=2)
        if len(split) == 1:
            # unspecified
            kinds_str = "音読み"
            readings_str = split[0]
        elif len(split) == 2:
            kinds_str, readings_str = split
        else:
            # shouldn't happen, but...
            continue

        # Separate and clean up kinds.
        kinds = re.split(r"\s*[,、・\s]\s*", kinds_str)
        if kanji == "谷":
            kinds = ["慣用音" if kind == "特殊な慣用音" else kind for kind in kinds]
        if not kinds:
            continue

        # Separate and clean up readings.
        if not readings_str:
            continue
        readings = re.split(r"\s*[,、\s]\s*", readings_str)
        readings = [reading for reading in readings if re.match(r"^[ァ-ヾ]", reading)]
        readings = [reading.replace("(", "（") for reading in readings]
        readings = [reading.replace(")", "）") for reading in readings]
        if not readings:
            continue

        for kind in kinds:
            if kind in result:
                extant = result[kind]
                for reading in readings:
                    if reading not in extant:
                        extant.append(reading)
            else:
                result[kind] = list(readings)
    return result


# Roughly sorted by age, excepting 慣用音.
SORT_ORDER = [
    "音読み",
    "古音",
    "呉音",
    "漢音",
    "唐宋音",
    "唐音",
    "宋音",
    "新漢音",
    "慣用音",
]


def sort_readings(
    kanji: str,
    readings_by_kind: dict[str, list[str]],
) -> list[list[str]]:
    result: list[list[str]] = []
    for kind in SORT_ORDER:
        if readings := readings_by_kind.get(kind):
            result.append([kind] + readings)
    if len(result) != len(readings_by_kind):
        raise Exception(
            f"Unknown reading kind for {kanji} found in {readings_by_kind.keys()}"
        )
    return result


# I can't believe this function didn't exist until 3.12 :\
def batched_compat(lst: list[Any], n: int) -> Iterable[Iterable[Any]]:
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def generate_onyomi_by_kanji(
    entries: list[list[Any]],
    kanjidic: dict[str, list[str]],
) -> dict[str, list[list[str]]]:
    result: dict[str, list[list[str]]] = {}
    missing: set[str] = set()
    for kanji, _, _, _, definition, _ in entries:
        if readings := gather_readings(kanji, definition):
            result[kanji] = sort_readings(kanji, readings)
        elif backup_readings := kanjidic.get(kanji):
            missing.add(kanji)
            result[kanji] = [["音読み"] + backup_readings]
    print(
        f"Missing detailed on'yomi information for the following kanji:",
        file=sys.stderr,
    )
    for it in batched_compat(sorted(missing), 60):
        print(f"  {''.join(it)}", file=sys.stderr)
    return result


with open(sys.argv[1], encoding="utf-8") as fp:
    kanji_bank = json.load(fp)
with open(sys.argv[2], encoding="utf-8") as fp:
    kanji_dic = json.load(fp)

json.dump(
    generate_onyomi_by_kanji(kanji_bank, kanji_dic),
    sys.stdout,
    ensure_ascii=False,
    separators=(",", ":"),
)
