import sys

from dataclasses import dataclass
from re import Pattern
from typing import Any, Callable, Iterable, Optional, Sequence, Collection, Tuple
from functools import cached_property

from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId, Note
from anki.cards import Card

from .common import (
    HANZI_REGEXP,
    Config,
    assert_is_not_none,
    get_lazy_data,
    html_tag,
    mw,
    normalize_unicode,
    log,
)
from .kyujipy import BasicConverter


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
    phonetic_series: Sequence[str]
    order: int
    is_japanese: bool
    is_new: bool


def create_hanzi_note(
    config: Config,
    id: NoteId,
    hanzi_models: dict[NotetypeId, HanziModel],
    japanese_note_ids: set[NoteId],
    converter: BasicConverter,
    components_by_phonetic_series: dict[str, str],
) -> HanziNote:
    note = mw.col.get_note(id)

    model = hanzi_models[note.mid]
    fields = note.fields
    web_field = note[config.web_field] if model.has_web_field else None

    terms = [normalize_unicode(note[field]) for field in hanzi_models[note.mid].fields]

    hanzi = []
    for value in terms:
        hanzi.extend(HANZI_REGEXP.findall(value))

    is_japanese = id in japanese_note_ids

    phonetic_series = [
        components_by_phonetic_series.get(
            converter.shinjitai_to_kyujitai(h) if is_japanese else h  # type: ignore
        )
        or ""
        for h in hanzi
    ]

    cards = note.cards()

    is_new = all([card.type == 0 for card in cards])

    def get_order(card: Card) -> int:
        if card.type == 0:  # new
            return sys.maxsize
        if card.type == 1:  # learning
            return -1
        if card.type == 2:  # due
            return card.due
        raise Exception(f"Unknown card type: {card.type}")

    order = min([get_order(card) for card in cards])

    return HanziNote(
        id,
        model,
        fields,
        terms,
        web_field,
        hanzi,
        phonetic_series,
        order,
        is_japanese,
        is_new,
    )


@dataclass(eq=False, frozen=True)
class HanziWeb:
    web: dict[str, list[HanziNote]]
    total_hanzi: int

    def entry(
        self,
        config: Config,
        hanzi: str,
        select: Callable[[HanziNote], bool],
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
            if not select(other_hanzi_note):
                continue
            for term in other_hanzi_note.terms:
                if reached_term_limit():
                    break
                terms.append(term)
            if reached_term_limit():
                break
        return config.term_separator.join(terms)


def create_hanzi_web(
    notes: Iterable[HanziNote], field: Callable[[HanziNote], set[str]]
) -> HanziWeb:
    total_hanzi: set[str] = set()
    hanzi_sets: dict[str, set[HanziNote]] = {}
    for hanzi_note in notes:
        all_hanzi = field(hanzi_note)
        total_hanzi.update(all_hanzi)
        # Skip this one if we've never seen it.
        if hanzi_note.is_new:
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
            key=lambda x: (x.order, x.id),
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
    notes: dict[NoteId, HanziNote],
    destination_note_ids: set[NoteId],
    hanzi_web: HanziWeb,
    phonetic_series_web: HanziWeb,
    onyomi: dict[str, list[Tuple[str, list[str]]]],
) -> list[tuple[HanziNote, str]]:
    def build_phonetic_series_entry_line(hanzi_note: HanziNote, component: str) -> str:
        entry = phonetic_series_web.entry(
            config,
            component,
            # Exclude any other entries that contain the exact same hanzi as this
            # one; it just creates noise in the output.
            lambda x: x != hanzi_note and hanzi not in x.hanzi,
        )
        if not entry:
            return ""
        return f"{component}：{entry}"

    notes_to_update = []
    for note_id in destination_note_ids:
        hanzi_note = notes[note_id]
        if not hanzi_note.model.has_web_field:
            continue
        entries: list[str] = []
        for hanzi, phonetic_components in zip(
            hanzi_note.hanzi, hanzi_note.phonetic_series
        ):
            this_onyomi = (onyomi.get(hanzi) or []) if hanzi_note.is_japanese else []

            same_terms_td_text = hanzi_web.entry(
                config, hanzi, lambda x: x != hanzi_note
            )
            phonetic_series_terms_td_text = "<br>".join(
                line
                for line in [
                    build_phonetic_series_entry_line(hanzi_note, component)
                    for component in phonetic_components
                ]
                if line
            )
            all_terms_td_text = [
                same_terms_td_text,
                phonetic_series_terms_td_text,
            ] + [config.term_separator.join(readings) for (_, readings) in this_onyomi]

            rowspan = len([x for x in all_terms_td_text if x])

            hanzi_td = html_tag(
                "td",
                hanzi,
                clazz="hanziweb-hanzi",
                rowspan=str(max(rowspan, 1)),
            )

            if rowspan == 0:
                entries.append(
                    html_tag("tr", hanzi_td + html_tag("td", "", colspan="2"))
                )
                continue

            for clazz, kind_td_text, terms_td_text in zip(
                ["hanziweb-same", "hanziweb-phonetic-series"]
                + ["hanziweb-onyomi"] * len(this_onyomi),
                ["", "諧聲"] + [kind for (kind, _) in this_onyomi],
                all_terms_td_text,
            ):
                if not terms_td_text:
                    continue
                kind_td = html_tag("td", kind_td_text, clazz=f"{clazz} hanziweb-kind")
                terms_td = html_tag(
                    "td",
                    terms_td_text,
                    clazz=f"{clazz} hanziweb-terms",
                )
                entries.append(html_tag("tr", hanzi_td + kind_td + terms_td))
                hanzi_td = ""

        # Add to the list if the fields differ.
        entries_str = html_tag(
            "table", html_tag("tbody", "".join(entries)), clazz="hanziweb"
        )
        if entries_str != hanzi_note.web_field:
            notes_to_update.append((hanzi_note, entries_str))

    return notes_to_update


class PendingChanges:
    config: Config
    notes_to_update: Sequence[Tuple[HanziNote, str]]
    hanzi_web: HanziWeb
    phonetic_series_web: HanziWeb
    num_source_notes: int
    num_destination_notes: int

    def __init__(
        self,
        config: Config,
        source_note_ids: set[NoteId],
        destination_note_ids: set[NoteId],
        japanese_note_ids: set[NoteId],
        hanzi_models: dict[NotetypeId, HanziModel],
    ):
        self.config = config
        self.num_source_notes = len(source_note_ids)
        self.num_destination_notes = len(destination_note_ids)

        converter = BasicConverter()  # type: ignore

        log("Reading lazy data")
        lazy_data = get_lazy_data()

        log("Creating HanziNotes")
        notes = {
            id: create_hanzi_note(
                config,
                id,
                hanzi_models,
                japanese_note_ids,
                converter,
                lazy_data.phonetics,
            )
            for id in source_note_ids.union(destination_note_ids)
        }

        log("Creating HanziWebs")
        self.hanzi_web = create_hanzi_web(notes.values(), lambda x: set(x.hanzi))
        self.phonetic_series_web = create_hanzi_web(
            notes.values(),
            lambda x: {p for s in x.phonetic_series for p in s},
        )

        log("Finding notes to update")
        self.notes_to_update = get_notes_to_update(
            config,
            notes,
            destination_note_ids,
            self.hanzi_web,
            self.phonetic_series_web,
            lazy_data.onyomi,
        )

        log("Done")

    @property
    def is_empty(self) -> bool:
        return not self.notes_to_update

    @property
    def report(self) -> str:
        def unique_hanzi(web: HanziWeb) -> str:
            return f"{len(web.web)} seen, {web.total_hanzi} total"

        report = [
            f"== Hanzi Web.\n\n",
            f"Unique hanzi: {unique_hanzi(self.hanzi_web)}\n",
            f"Unique phonetic series: {unique_hanzi(self.phonetic_series_web)}\n",
            f"Number of source notes: {self.num_source_notes}\n",
            f"Number of destination notes: {self.num_destination_notes}\n",
        ]
        if self.notes_to_update:
            report.append(
                f"\nNotes to update [{self.config.web_field}] ({len(self.notes_to_update)}):\n"
            )
            for note, _ in self.notes_to_update:
                report.append(f"  {note.id} {note.fields[0]}\n")
        else:
            report.append("\nAll notes already up to date.\n")
        return "".join(report)

    def apply(self) -> Optional[str]:
        if not self.notes_to_update:
            return None

        for hanzi_note, entries in self.notes_to_update:
            note = mw.col.get_note(hanzi_note.id)
            note[self.config.web_field] = entries
            mw.col.update_note(note)
        return f"Hanzi Web: {len(self.notes_to_update)} notes updated."
