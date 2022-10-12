import re
import unicodedata
from re import Pattern
from sys import platform
from typing import Any, Callable, Iterable, Optional, Sequence

from anki.collection import SearchNode
from anki.models import NotetypeId
from anki.notes import Note
from aqt import mw as mw_optional
from aqt.qt import (  # type: ignore
    QAction,
    QDialog,
    QDialogButtonBox,
    QMenu,
    QPlainTextEdit,
    QVBoxLayout,
)
from aqt.utils import qconnect, showInfo

VERSION = "0.1.0"

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

CONTROL_HINT = "Cmd" if platform == "darwin" else "Ctrl"

ABOUT_TEXT = (
    f"Hanzi Web {VERSION} by Eliza\n\n"
    'To configure Hanzi Web, go to "Tools -> Addons" '
    f'({CONTROL_HINT}+Shift+A), select "Hanzi Web", and click '
    '"Config".\n\n' + GPL
)


# Matches each hanzi character individually.
HANZI_REGEXP = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def assert_is_not_none(optional: Optional[Any]) -> Any:
    assert optional is not None
    return optional


mw = assert_is_not_none(mw_optional)


class Config:
    config_version: int
    search_query: str
    hanzi_fields_regexp: Optional[Pattern[Any]]
    web_field: str
    term_separator: str
    max_terms_per_hanzi: int

    def __init__(self, config: dict[str, Any]):
        self.config_version = config.get("config_version") or 0
        self.search_query = config.get("search_query") or ""
        hanzi_fields_regexp = config.get("hanzi_fields_regexp")
        self.hanzi_fields_regexp = (
            re.compile(hanzi_fields_regexp) if hanzi_fields_regexp else None
        )
        self.web_field = config.get("web_field") or "HanziWeb"
        self.term_separator = config.get("term_separator") or "、"
        self.max_terms_per_hanzi = config.get("max_terms_per_hanzi") or 5


CONFIG = Config(assert_is_not_none(mw).addonManager.getConfig(__name__))


class ReportDialog(QDialog):  # type: ignore
    def __init__(self, text: str):
        super().__init__()
        self.setWindowTitle("Hanzi Web")
        self.resize(400, 400)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Construct text area
        textedit = QPlainTextEdit(self)
        textedit.setPlainText(text)
        textedit.setReadOnly(True)
        layout.addWidget(textedit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        apply_button.setAutoDefault(True)
        apply_button.setDefault(True)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setAutoDefault(False)
        cancel_button.setDefault(False)

        layout.addWidget(button_box)
        qconnect(apply_button.clicked, self.accept)
        qconnect(button_box.accepted, self.accept)
        qconnect(button_box.rejected, self.reject)


class HanziField:
    name: str
    ord: int

    def __init__(self, name: str, ord: int):
        self.name = name
        self.ord = ord


class HanziModel:
    name: str
    fields: Sequence[HanziField]

    def __init__(self, name: str, fields: Sequence[HanziField]):
        self.name = name
        self.fields = fields


class HanziNote:
    note: Note
    field_values: Sequence[str]
    hanzi: Sequence[str]
    latest_review: int

    def __init__(self, note: Note, hanzi_models: dict[NotetypeId, HanziModel]):
        self.note = note

        note_values = note.values()
        self.field_values = [
            unicodedata.normalize("NFKC", note_values[field.ord])
            for field in hanzi_models[note.mid].fields
        ]

        self.hanzi = []
        for value in self.field_values:
            self.hanzi.extend(HANZI_REGEXP.findall(value))

        self.latest_review = max(
            [
                mw.col.card_stats_data(card_id).latest_review
                for card_id in note.card_ids()
            ]
        )


def get_hanzi_models() -> dict[NotetypeId, HanziModel]:
    models = mw.col.models
    if not CONFIG.hanzi_fields_regexp:
        return {}
    return {
        NotetypeId(note_type.id): HanziModel(note_type.name, fields)
        for (note_type, fields) in [
            (
                note_type,
                [
                    HanziField(name, ord)
                    for (name, (ord, _)) in models.field_map(
                        assert_is_not_none(models.get(NotetypeId(note_type.id)))
                    ).items()
                    if CONFIG.hanzi_fields_regexp.fullmatch(name)
                ],
            )
            for note_type in models.all_names_and_ids()
        ]
        if fields
    }


def get_web_models(hanzi_model_ids: Iterable[NotetypeId]) -> dict[NotetypeId, int]:
    models = mw.col.models
    if not CONFIG.web_field:
        return {}
    return {
        id: field[0]
        for (id, field) in [
            (
                id,
                models.field_map(assert_is_not_none(models.get(id))).get(
                    CONFIG.web_field
                ),
            )
            for id in hanzi_model_ids
        ]
        if field
    }


def get_hanzi_web(notes: Iterable[HanziNote]) -> dict[str, list[HanziNote]]:
    # Comb through notes for each hanzi and construct the web.
    hanzi_web_sets: dict[str, set[HanziNote]] = {}
    for hanzi_note in notes:
        # Skip this one if we've never seen it.
        if hanzi_note.latest_review == 0:
            continue
        for hanzi in hanzi_note.hanzi:
            note_set = hanzi_web_sets.get(hanzi)
            if note_set:
                note_set.add(hanzi_note)
            else:
                hanzi_web_sets[hanzi] = {hanzi_note}
    return {
        hanzi: sorted(
            note_set,
            key=lambda x: -x.latest_review,
        )
        for (hanzi, note_set) in hanzi_web_sets.items()
    }


def get_notes_to_update(
    notes: Iterable[HanziNote],
    web_models: dict[NotetypeId, int],
    hanzi_web: dict[str, list[HanziNote]],
) -> list[tuple[HanziNote, str]]:
    notes_to_maybe_update = [note for note in notes if note.note.mid in web_models]

    # Actually build the updates and see if they differ from the extant note,
    # collecting them in a new set.
    notes_to_update = []
    for hanzi_note in notes_to_maybe_update:
        entries = []
        for hanzi in hanzi_note.hanzi:
            note_list = hanzi_web.get(hanzi)
            if not note_list:
                # No other notes for this hanzi. This shouldn't really be
                # possible since we ourselves are a note.
                continue
            terms: list[str] = []
            # TODO: Do this smarter
            reached_term_limit: Callable[[], bool] = (
                (lambda: False)
                if CONFIG.max_terms_per_hanzi == 0
                else (lambda: len(terms) >= CONFIG.max_terms_per_hanzi)
            )
            for other_hanzi_note in note_list:
                if other_hanzi_note == hanzi_note:
                    # Don't inculde ourselves
                    continue
                for term in other_hanzi_note.field_values:
                    if reached_term_limit():
                        break
                    terms.append(term)
                if reached_term_limit():
                    break
            if terms:
                terms_str = CONFIG.term_separator.join(terms)
                entries.append(
                    (
                        f'<li><span class="hanziweb-hanzi">{hanzi}</span>'
                        f'<span class="hanziweb-terms">{terms_str}</span></li>'
                    )
                )
        entries_str = f"<ol class='hanziweb'>{''.join(entries)}</ol>" if entries else ""

        # Add to the list if the fields differ.
        web_ord = web_models[hanzi_note.note.mid]
        extant_entries = hanzi_note.note.values()[web_ord]
        if entries_str != extant_entries:
            notes_to_update.append((hanzi_note, entries_str))

    return notes_to_update


def update() -> None:
    hanzi_models = get_hanzi_models()

    search_string = mw.col.build_search_string(
        CONFIG.search_query,
        mw.col.group_searches(
            *[SearchNode(parsable_text=f"mid:{id}") for id in hanzi_models.keys()],
            joiner="OR",
        ),
    )

    notes = {
        note: HanziNote(note, hanzi_models)
        for note in [
            mw.col.get_note(note_id) for note_id in mw.col.find_notes(search_string)
        ]
    }

    web_models = get_web_models(hanzi_models.keys())
    hanzi_web = get_hanzi_web(notes.values())
    notes_to_update = get_notes_to_update(notes.values(), web_models, hanzi_web)

    # Summarize the operation to the user.
    summary = [
        (
            "Hanzi Web will update the following notes. Please ensure this "
            "looks correct before continuing.\n"
        ),
        f"Search query:\n  {search_string}\n\nNote types:",
    ]
    web_field = CONFIG.web_field or "<not set>"
    for model in hanzi_models.values():
        fields = ", ".join([field.name for field in model.fields])
        summary.append(f"  {model.name} [{fields}]")
    summary.append(f"\nNotes to update [{web_field}] ({len(notes_to_update)}):")
    for (note, _) in notes_to_update:
        summary.append(f"  {note.note.id} {note.note.values()[0]}")

    if ReportDialog("\n".join(summary)).exec() == QDialog.DialogCode.Rejected:
        return

    for (hanzi_note, entries) in notes_to_update:
        web_ord = web_models[hanzi_note.note.mid]
        hanzi_note.note.values()[web_ord] = entries
        mw.col.update_note(hanzi_note.note)


# Build menu.
menu = QMenu("Hanzi &Web", mw)
update_action = QAction("&Update notes", menu)
about_action = QAction("&About...", menu)
update_action.setShortcut("Ctrl+W")
menu.addAction(update_action)
menu.addAction(about_action)
qconnect(update_action.triggered, update)
qconnect(about_action.triggered, lambda: showInfo(ABOUT_TEXT))
mw.form.menuTools.addMenu(menu)
