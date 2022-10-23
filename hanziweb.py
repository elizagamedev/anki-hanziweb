import json
from dataclasses import dataclass
from pathlib import PurePath
from re import Pattern
from typing import Any, Callable, Iterable, Optional, Sequence

from anki.collection import SearchNode
from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId
from aqt.qt import QAction, QMenu  # type: ignore
from aqt.utils import qconnect, showInfo, tooltip

from .common import (
    HANZI_REGEXP,
    VERSION,
    Config,
    assert_is_not_none,
    mw,
    normalize_unicode,
    show_report,
)
from .kyujipy import BasicConverter
from .phonetics import COMPONENT_BY_PHONETIC_SERIES

GPL = (
    "This program is free software: you can redistribute it and/or modify it "
    "under the terms of the GNU General Public License as published by the "
    "Free Software Foundation, either version 3 of the License, or (at your "
    "option) any later version.\n\n"
    "This program is distributed in the hope that it will be useful, but "
    "WITHOUT ANY WARRANTY; without even the implied warranty of "
    "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General "
    "Public License for more details.\n\n"
    "You should have received a copy of the GNU General Public License along "
    "with this program. If not, see <https://www.gnu.org/licenses/>."
)

ABOUT_TEXT = (
    f"Hanzi Web {VERSION} by Eliza\n\n"
    "For detailed usage instructions, see the addon page.\n\n" + GPL
)


@dataclass(eq=False, frozen=True)
class HanziModel:
    id: NotetypeId
    name: str
    fields: Sequence[str]
    has_web_field: bool


def create_hanzi_model(
    hanzi_fields_regexp: Pattern[Any],
    web_field: str,
    note_type: NotetypeNameId,
) -> Optional[HanziModel]:
    id = NotetypeId(note_type.id)
    all_fields = mw.col.models.field_names(assert_is_not_none(mw.col.models.get(id)))
    fields = [name for name in all_fields if hanzi_fields_regexp.fullmatch(name)]
    if not fields:
        return None
    has_web_field = web_field in all_fields
    return HanziModel(id, note_type.name, fields, has_web_field)


@dataclass(eq=False, frozen=True)
class HanziNote:
    id: NoteId
    model: HanziModel
    fields: list[str]
    terms: Sequence[str]
    web_field: Optional[str]
    hanzi: Sequence[str]
    phonetic_series: Sequence[Optional[str]]
    latest_review: int
    chinese_reading: bool


def create_hanzi_note(
    config: Config,
    id: NoteId,
    hanzi_models: dict[NotetypeId, HanziModel],
    chinese_reading_note_ids: set[NoteId],
    converter: BasicConverter,
) -> HanziNote:
    note = mw.col.get_note(id)

    model = hanzi_models[note.mid]
    fields = note.fields
    web_field = note[config.web_field] if model.has_web_field else None

    terms = [normalize_unicode(note[field]) for field in hanzi_models[note.mid].fields]

    hanzi = []
    for value in terms:
        hanzi.extend(HANZI_REGEXP.findall(value))

    chinese_reading = id in chinese_reading_note_ids

    if chinese_reading:
        # This is a Chinese reading of a note, so the sound series is relevant.
        phonetic_series = [
            COMPONENT_BY_PHONETIC_SERIES.get(
                converter.shinjitai_to_kyujitai(h)  # type: ignore
            )
            for h in hanzi
        ]
    else:
        # This is not a Chinese reading (e.g. Japanese kun-yomi), so its sound series is
        # not relevant.
        phonetic_series = [None] * len(hanzi)

    latest_review = max(
        [mw.col.card_stats_data(card_id).latest_review for card_id in note.card_ids()]
    )

    return HanziNote(
        id,
        model,
        fields,
        terms,
        web_field,
        hanzi,
        phonetic_series,
        latest_review,
        chinese_reading,
    )


@dataclass(eq=False, frozen=True)
class HanziWeb:
    web: dict[str, list[HanziNote]]
    total_hanzi: int

    def entry(
        self,
        config: Config,
        hanzi: str,
        hanzi_class: str,
        terms_class: str,
        hanzi_note: HanziNote,
    ) -> str:
        note_list = self.web.get(hanzi)
        if not note_list:
            return ""
        terms: list[str] = []
        # TODO: Do this smarter
        reached_term_limit: Callable[[], bool] = (
            (lambda: False)
            if config.max_terms_per_hanzi == 0
            else (lambda: len(terms) >= config.max_terms_per_hanzi)
        )
        for other_hanzi_note in note_list:
            if other_hanzi_note == hanzi_note:
                # Don't inculde ourselves
                continue
            for term in other_hanzi_note.terms:
                if reached_term_limit():
                    break
                terms.append(term)
            if reached_term_limit():
                break
        if terms:
            terms_str = config.term_separator.join(terms)
            return (
                f'<span class="{hanzi_class}">{hanzi}</span>'
                f'<span class="{terms_class}">{terms_str}</span>'
            )
        return ""


def create_hanzi_web(
    notes: Iterable[HanziNote], field: Callable[[HanziNote], Sequence[str]]
) -> HanziWeb:
    total_hanzi: set[str] = set()
    hanzi_sets: dict[str, set[HanziNote]] = {}
    for hanzi_note in notes:
        all_hanzi = field(hanzi_note)
        total_hanzi.update(all_hanzi)
        # Skip this one if we've never seen it.
        if hanzi_note.latest_review == 0:
            continue
        for hanzi in all_hanzi:
            note_set = hanzi_sets.get(hanzi)
            if note_set:
                note_set.add(hanzi_note)
            else:
                hanzi_sets[hanzi] = {hanzi_note}
    web = {
        hanzi: sorted(
            note_set,
            key=lambda x: -x.latest_review,
        )
        for (hanzi, note_set) in hanzi_sets.items()
    }
    return HanziWeb(web, len(total_hanzi))


def get_hanzi_models(config: Config) -> dict[NotetypeId, HanziModel]:
    if not config.hanzi_fields_regexp:
        return {}
    return {
        model.id: model
        for model in [
            create_hanzi_model(config.hanzi_fields_regexp, config.web_field, note_type)
            for note_type in mw.col.models.all_names_and_ids()
        ]
        if model
    }


def get_notes_to_update(
    config: Config,
    notes: Iterable[HanziNote],
    hanzi_web: HanziWeb,
    phonetic_series_web: HanziWeb,
    onyomi: dict[str, list[str]],
) -> list[tuple[HanziNote, str]]:
    notes_to_maybe_update = [note for note in notes if note.model.has_web_field]

    def build_web_entry(
        hanzi: str, phonetic_component: Optional[str], hanzi_note: HanziNote
    ) -> str:
        hanzi_web_entry = hanzi_web.entry(
            config, hanzi, "hanziweb-hanzi", "hanziweb-terms", hanzi_note
        )
        phonetic_component_entry = (
            phonetic_series_web.entry(
                config,
                phonetic_component,
                "hanziweb-phonetic-component",
                "hanziweb-phonetic-terms",
                hanzi_note,
            )
            if phonetic_component is not None
            else ""
        )
        if hanzi_web_entry and phonetic_component_entry:
            return f"{hanzi_web_entry}<br>{phonetic_component_entry}"
        return f"{hanzi_web_entry}{phonetic_component_entry}"

    def build_onyomi_entry(hanzi: str, chinese_reading: bool) -> str:
        if not chinese_reading:
            return ""
        terms = onyomi.get(hanzi)
        if not terms:
            return ""
        terms_str = config.term_separator.join(terms)
        return f'<span class="hanziweb-onyomi">{terms_str}</span>'

    def build_entry(
        hanzi: str, phonetic_component: Optional[str], hanzi_note: HanziNote
    ) -> str:
        web_entry = build_web_entry(hanzi, phonetic_component, hanzi_note)
        onyomi_entry = build_onyomi_entry(hanzi, hanzi_note.chinese_reading)
        if web_entry and onyomi_entry:
            return f"{web_entry}<br>{onyomi_entry}"
        return f"{web_entry}{onyomi_entry}"

    # Actually build the updates and see if they differ from the extant note,
    # collecting them in a new set.
    notes_to_update = []
    for hanzi_note in notes_to_maybe_update:
        entries: list[str] = []
        for (hanzi, phonetic_component) in zip(
            hanzi_note.hanzi, hanzi_note.phonetic_series
        ):
            entry = build_entry(hanzi, phonetic_component, hanzi_note)
            if entry:
                entries.append(f"<li>{entry}</li>")

        # Add to the list if the fields differ.
        entries_str = f'<ol class="hanziweb">{"".join(entries)}</ol>' if entries else ""
        if entries_str != hanzi_note.web_field:
            notes_to_update.append((hanzi_note, entries_str))

    return notes_to_update


def generate_report(
    config: Config,
    search_string: str,
    chinese_reading_search_string: str,
    hanzi_models: dict[NotetypeId, HanziModel],
    notes_to_update: list[tuple[HanziNote, str]],
    hanzi_web: HanziWeb,
    phonetic_series_web: HanziWeb,
) -> str:
    def unique_hanzi(web: HanziWeb) -> str:
        return f"{len(web.web)} seen, {web.total_hanzi} total"

    report = [
        "Hanzi Web will update the following notes. Please ensure this ",
        "looks correct before continuing.\n\n",
        f"Search query:\n  {search_string}\n",
        f"Chinese reading search query:\n  {chinese_reading_search_string}\n\n",
        f"Unique hanzi: {unique_hanzi(hanzi_web)}\n",
        f"Unique phonetic series: {unique_hanzi(phonetic_series_web)}\n\n",
        "Note types:\n",
    ]
    for model in hanzi_models.values():
        fields = ", ".join(model.fields)
        report.append(f"  {model.name} [{fields}]\n")
    if notes_to_update:
        report.append(
            f"\nNotes to update [{config.web_field}] ({len(notes_to_update)}):\n"
        )
        for (note, _) in notes_to_update:
            report.append(f"  {note.id} {note.fields[0]}\n")
    else:
        report.append("\nAll notes already up to date.\n")
    return "".join(report)


def apply_changes(
    config: Config, notes_to_update: Sequence[tuple[HanziNote, str]]
) -> None:
    if not notes_to_update:
        tooltip("Nothing done.", parent=mw)
        return

    # The checkpoint system (mw.checkpoint() and mw.reset()) are "obsoleted" in favor of
    # Collection Operations. However, Collection Operations have a very short-term
    # memory (~30), which is unsuitable for the potentially massive amounts of changes
    # that Hanzi Web will do on a collection.
    #
    # https://addon-docs.ankiweb.net/background-ops.html?highlight=undo#collection-operations
    mw.checkpoint("Hanzi Web")
    for hanzi_note, entries in notes_to_update:
        note = mw.col.get_note(hanzi_note.id)
        note[config.web_field] = entries
        note.flush()
    mw.reset()
    tooltip(f"{len(notes_to_update)} notes updated.", parent=mw)


def update() -> None:
    config = Config(assert_is_not_none(mw.addonManager.getConfig(__name__)))
    converter = BasicConverter()  # type: ignore
    hanzi_models = get_hanzi_models(config)

    with open(
        PurePath(__file__).parent / "kanji-onyomi.json", "r", encoding="utf-8"
    ) as onyomi_file:
        onyomi = json.load(onyomi_file)

    search_string = mw.col.build_search_string(
        config.search_query,
        mw.col.group_searches(
            *[SearchNode(parsable_text=f"mid:{id}") for id in hanzi_models.keys()],
            joiner="OR",
        ),
    )

    chinese_reading_search_string = mw.col.build_search_string(
        search_string,
        config.chinese_reading_search_query,
    )

    chinese_reading_note_ids = set(mw.col.find_notes(chinese_reading_search_string))

    notes = {
        id: create_hanzi_note(
            config, id, hanzi_models, chinese_reading_note_ids, converter
        )
        for id in mw.col.find_notes(search_string)
    }

    hanzi_web = create_hanzi_web(notes.values(), lambda x: x.hanzi)
    phonetic_series_web = create_hanzi_web(
        notes.values(), lambda x: [y for y in x.phonetic_series if y is not None]
    )
    notes_to_update = get_notes_to_update(
        config, notes.values(), hanzi_web, phonetic_series_web, onyomi
    )

    # Summarize the operation to the user.
    report = generate_report(
        config,
        search_string,
        chinese_reading_search_string,
        hanzi_models,
        notes_to_update,
        hanzi_web,
        phonetic_series_web,
    )
    if not show_report(report):
        return

    apply_changes(config, notes_to_update)


def init() -> None:
    menu = QMenu("Hanzi &Web", mw)
    update_action = QAction("&Update notes", menu)
    about_action = QAction("&About...", menu)
    update_action.setShortcut("Ctrl+W")
    menu.addAction(update_action)
    menu.addAction(about_action)
    qconnect(update_action.triggered, update)
    qconnect(about_action.triggered, lambda: showInfo(ABOUT_TEXT))
    mw.form.menuTools.addMenu(menu)
