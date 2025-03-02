import sys

from dataclasses import dataclass
from re import Pattern
from typing import Any, Callable, Iterable, Optional, Sequence, Collection, Tuple, Union
from functools import cached_property

from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId, Note
from anki.cards import Card
from anki.consts import (
    CARD_TYPE_NEW,
    CARD_TYPE_LRN,
    CARD_TYPE_REV,
    CARD_TYPE_RELEARNING,
)
from aqt.utils import askUser

from .common import (
    Config,
    HANZI_REGEXP,
    JS_VERSION,
    assert_is_not_none,
    html_click_action,
    html_tag,
    inject_js_into_html,
    log,
    mw,
    normalize_unicode,
)
from .kyujipy import BasicConverter


def inject_into_templates(model_dict: dict[str, Any], js: str) -> tuple[int, int]:
    min_previous_js_version: Optional[int] = None
    max_previous_js_version = -1
    is_dirty = False
    for template in model_dict["tmpls"]:
        for side in ("qfmt", "afmt"):
            html, this_previous_js_version = inject_js_into_html(js, template[side])
            min_previous_js_version = (
                this_previous_js_version
                if min_previous_js_version is None
                else min(min_previous_js_version, this_previous_js_version)
            )
            max_previous_js_version = max(
                max_previous_js_version, this_previous_js_version
            )
            if this_previous_js_version != JS_VERSION:
                template[side] = html
    if min_previous_js_version is None:
        min_previous_js_version = max_previous_js_version
    return min_previous_js_version, max_previous_js_version


@dataclass(eq=False, frozen=True)
class HanziModel:
    id: NotetypeId
    name: str
    fields: Sequence[str]
    has_web_field: bool
    model_dict: dict[str, Any]
    previous_js_version: tuple[int, int]

    def apply(self) -> None:
        mw.col.models.update_dict(self.model_dict)


def create_hanzi_model(
    hanzi_fields_regexp: Pattern[Any],
    web_field: str,
    note_type: NotetypeNameId,
    js: str,
) -> Optional[HanziModel]:
    id = NotetypeId(note_type.id)
    model_dict = assert_is_not_none(mw.col.models.get(id))
    all_fields = mw.col.models.field_names(model_dict)
    fields = [name for name in all_fields if hanzi_fields_regexp.fullmatch(name)]
    if not fields:
        return None
    has_web_field = web_field in all_fields
    previous_js_version = inject_into_templates(model_dict, js)
    return HanziModel(
        id, note_type.name, fields, has_web_field, model_dict, previous_js_version
    )


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

    is_new = all([card.type == CARD_TYPE_NEW for card in cards])

    def get_order(card: Card) -> int:
        if card.type == CARD_TYPE_NEW:
            return sys.maxsize
        if card.type == CARD_TYPE_LRN or card.type == CARD_TYPE_RELEARNING:
            return -1
        if card.type == CARD_TYPE_REV:
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
        term_separator: str,
        max_terms_per_hanzi: int,
        click_term_action: Union[None, Config.ClickAction, str],
        hanzi: str,
        select: Callable[[HanziNote], bool],
    ) -> Tuple[str, list[NoteId]]:
        note_list = self.web.get(hanzi)
        if not note_list:
            return "", []
        terms: list[str] = []
        ids: list[NoteId] = []
        # TODO: Do this smarter
        reached_term_limit: Callable[[], bool] = (
            (lambda: False)
            if max_terms_per_hanzi == 0
            else (lambda: len(terms) >= max_terms_per_hanzi)
        )
        for other_hanzi_note in note_list:
            if not select(other_hanzi_note):
                continue
            if not reached_term_limit():
                for term in other_hanzi_note.terms:
                    if reached_term_limit():
                        break
                    terms.append(
                        html_click_action(
                            term,
                            click_term_action,
                            [other_hanzi_note.id],
                            {"hanzi": hanzi, "term": term},
                        )
                    )
            ids.append(other_hanzi_note.id)
        ids.sort()
        return term_separator.join(terms), ids


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


def get_hanzi_models(config: Config, js: str) -> dict[NotetypeId, HanziModel]:
    if not config.hanzi_fields_regexp:
        return {}
    return {
        model.id: model
        for model in [
            create_hanzi_model(
                config.hanzi_fields_regexp,
                config.web_field,
                note_type,
                js,
            )
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
    def build_phonetic_series_entry(
        hanzi_note: HanziNote, component: str
    ) -> Tuple[str, str]:
        terms_text, ids = phonetic_series_web.entry(
            config.term_separator,
            config.max_terms_per_hanzi,
            config.click_phonetic_term_action,
            component,
            # Exclude any other entries that contain the exact same hanzi as this
            # one; it just creates noise in the output.
            lambda x: x != hanzi_note and hanzi not in x.hanzi,
        )
        component_text = "音符 " + html_tag(
            "span", component, clazz="hanziweb-phonetic-component"
        )
        return (
            html_click_action(
                component_text,
                config.click_phonetic_action,
                ids,
                {"hanzi": hanzi, "phonetic": component},
            ),
            terms_text,
        )

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

            same_terms_text, same_terms_ids = hanzi_web.entry(
                config.term_separator,
                config.max_terms_per_hanzi,
                config.click_hanzi_term_action,
                hanzi,
                lambda x: x != hanzi_note,
            )

            all_terms = (
                ([("hanziweb-same", "", same_terms_text)] if same_terms_text else [])
                + [
                    (
                        "hanziweb-phonetic-series",
                        *build_phonetic_series_entry(hanzi_note, component),
                    )
                    for component in phonetic_components
                ]
                + [
                    ("hanziweb-onyomi", kind, config.term_separator.join(readings))
                    for (kind, readings) in this_onyomi
                ]
            )

            hanzi_td = html_tag(
                "td",
                html_click_action(
                    hanzi, config.click_hanzi_action, same_terms_ids, {"hanzi": hanzi}
                ),
                clazz="hanziweb-hanzi",
                rowspan=str(max(len(all_terms), 1)),
            )

            if len(all_terms) == 0:
                entries.append(
                    html_tag("tr", hanzi_td + html_tag("td", "", colspan="2"))
                )
                continue

            for clazz, kind_td_text, terms_td_text in all_terms:
                kind_td = (
                    html_tag(
                        "td",
                        kind_td_text,
                        clazz=f"{clazz} hanziweb-kind",
                    )
                    if kind_td_text
                    else ""
                )
                terms_td = (
                    html_tag(
                        "td",
                        terms_td_text,
                        clazz=f"{clazz} hanziweb-terms",
                    )
                    if kind_td_text
                    else html_tag(
                        "td",
                        terms_td_text,
                        clazz=f"{clazz} hanziweb-terms",
                        colspan="2",
                    )
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
    models_to_update: Sequence[HanziModel]
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
        phonetics: dict[str, str],
        onyomi: dict[str, list[Tuple[str, list[str]]]],
    ):
        self.config = config
        self.num_source_notes = len(source_note_ids)
        self.num_destination_notes = len(destination_note_ids)

        converter = BasicConverter()  # type: ignore

        self.models_to_update = [
            x
            for x in hanzi_models.values()
            if x.previous_js_version != (JS_VERSION, JS_VERSION)
        ]

        log("Creating HanziNotes")
        notes = {
            id: create_hanzi_note(
                config,
                id,
                hanzi_models,
                japanese_note_ids,
                converter,
                phonetics,
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
            onyomi,
        )

        log("Done")

    @property
    def is_empty(self) -> bool:
        return not self.models_to_update and not self.notes_to_update

    def confirm(self) -> bool:
        downgraded_models = [
            x
            for x in self.models_to_update
            if any([x > JS_VERSION for x in x.previous_js_version])
        ]
        if downgraded_models:
            return askUser(
                "The JavaScript of some note types will be downgraded. "
                + "You are likely running a newer version of Hanzi Web on another "
                + "device. You should update Hanzi Web on this device to prevent "
                + "issues. Continue?",
                defaultno=True,
            )
        return True

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
        if self.models_to_update:
            report.append(
                "\nModels to update: "
                + ", ".join([x.name for x in self.models_to_update])
                + "\n"
            )
        else:
            report.append("\nAll models already up to date.\n")
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
        if not self.models_to_update and not self.notes_to_update:
            return None

        tooltip = "Hanzi Web:"

        if self.models_to_update:
            tooltip += f" {len(self.models_to_update)} model(s) updated."
            for model in self.models_to_update:
                model.apply()

        if self.notes_to_update:
            tooltip += f" {len(self.notes_to_update)} note(s) updated."
            for hanzi_note, entries in self.notes_to_update:
                note = mw.col.get_note(hanzi_note.id)
                note[self.config.web_field] = entries
                mw.col.update_note(note)

        return tooltip
