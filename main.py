import re
import unicodedata
from re import Pattern
from typing import Any, Callable, Iterable, Optional, Sequence

from anki.collection import SearchNode
from anki.config import Config as AnkiConfig
from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId
from aqt import mw as mw_optional
from aqt.main import AnkiQt
from aqt.qt import (  # type: ignore
    QAction,
    QDialog,
    QDialogButtonBox,
    QMenu,
    QPlainTextEdit,
    QVBoxLayout,
)
from aqt.utils import qconnect, showInfo, tooltip

VERSION = "0.1.2"
CONFIG_VERSION = 0

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


# Matches each hanzi character individually.
HANZI_REGEXP = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def assert_is_not_none(optional: Optional[Any]) -> Any:
    assert optional is not None
    return optional


mw: AnkiQt = assert_is_not_none(mw_optional)


def normalize_unicode(string: str) -> str:
    return (
        unicodedata.normalize("NFC", string)
        if mw.col.get_config_bool(AnkiConfig.Bool.NORMALIZE_NOTE_TEXT)
        else string
    )


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


class Config:
    config_version: int
    hanzi_fields_regexp: Optional[Pattern[Any]]
    max_terms_per_hanzi: int
    search_query: str
    term_separator: str
    web_field: str

    def __init__(self, config: dict[str, Any]):
        config_version = config.get("config_version") or 0
        if config_version > CONFIG_VERSION:
            raise Exception(
                f"`config_version' {config_version} too new "
                f"(expecting <= {CONFIG_VERSION})"
            )

        hanzi_fields_regexp = config.get("hanzi_fields_regexp")
        self.hanzi_fields_regexp = (
            re.compile(hanzi_fields_regexp) if hanzi_fields_regexp else None
        )

        max_terms_per_hanzi = config.get("max_terms_per_hanzi")
        self.max_terms_per_hanzi = (
            5 if max_terms_per_hanzi is None else max_terms_per_hanzi
        )

        self.search_query = config.get("search_query") or ""

        self.term_separator = config.get("term_separator") or "、"

        self.web_field = config.get("web_field") or "HanziWeb"


class HanziModel:
    id: NotetypeId
    name: str
    fields: Sequence[str]
    has_web_field: bool

    def __init__(
        self, id: NotetypeId, name: str, fields: Sequence[str], has_web_field: bool
    ):
        self.id = id
        self.name = name
        self.fields = fields
        self.has_web_field = has_web_field


def create_hanzi_model_from_notetype_name_id(
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


class HanziNote:
    id: NoteId
    model: HanziModel
    fields: list[str]
    web_field: Optional[str]
    normalized_hanzi_fields: Sequence[str]
    hanzi: Sequence[str]
    latest_review: int

    def __init__(
        self,
        config: Config,
        id: NoteId,
        hanzi_models: dict[NotetypeId, HanziModel],
    ):
        self.id = id

        note = mw.col.get_note(id)

        self.model = hanzi_models[note.mid]
        self.fields = note.fields
        self.web_field = note[config.web_field] if self.model.has_web_field else None

        self.normalized_hanzi_fields = [
            normalize_unicode(note[field]) for field in hanzi_models[note.mid].fields
        ]

        self.hanzi = []
        for value in self.normalized_hanzi_fields:
            self.hanzi.extend(HANZI_REGEXP.findall(value))

        self.latest_review = max(
            [
                mw.col.card_stats_data(card_id).latest_review
                for card_id in note.card_ids()
            ]
        )


def get_hanzi_models(config: Config) -> dict[NotetypeId, HanziModel]:
    if not config.hanzi_fields_regexp:
        return {}
    return {
        model.id: model
        for model in [
            create_hanzi_model_from_notetype_name_id(
                config.hanzi_fields_regexp, config.web_field, note_type
            )
            for note_type in mw.col.models.all_names_and_ids()
        ]
        if model
    }


def get_hanzi_web(notes: Iterable[HanziNote]) -> tuple[dict[str, list[HanziNote]], int]:
    # Comb through notes for each hanzi and construct the web. Also, count the number of
    # unique hanzi total.
    total_hanzi: set[str] = set()
    hanzi_web_sets: dict[str, set[HanziNote]] = {}
    for hanzi_note in notes:
        total_hanzi.update(hanzi_note.hanzi)
        # Skip this one if we've never seen it.
        if hanzi_note.latest_review == 0:
            continue
        for hanzi in hanzi_note.hanzi:
            note_set = hanzi_web_sets.get(hanzi)
            if note_set:
                note_set.add(hanzi_note)
            else:
                hanzi_web_sets[hanzi] = {hanzi_note}
    hanzi_web = {
        hanzi: sorted(
            note_set,
            key=lambda x: -x.latest_review,
        )
        for (hanzi, note_set) in hanzi_web_sets.items()
    }
    return (hanzi_web, len(total_hanzi))


def get_notes_to_update(
    config: Config,
    notes: Iterable[HanziNote],
    hanzi_web: dict[str, list[HanziNote]],
) -> list[tuple[HanziNote, str]]:
    notes_to_maybe_update = [note for note in notes if note.model.has_web_field]

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
                if config.max_terms_per_hanzi == 0
                else (lambda: len(terms) >= config.max_terms_per_hanzi)
            )
            for other_hanzi_note in note_list:
                if other_hanzi_note == hanzi_note:
                    # Don't inculde ourselves
                    continue
                for term in other_hanzi_note.normalized_hanzi_fields:
                    if reached_term_limit():
                        break
                    terms.append(term)
                if reached_term_limit():
                    break
            if terms:
                terms_str = config.term_separator.join(terms)
                entries.append(
                    (
                        f'<li><span class="hanziweb-hanzi">{hanzi}</span>'
                        f'<span class="hanziweb-terms">{terms_str}</span></li>'
                    )
                )
        entries_str = f'<ol class="hanziweb">{"".join(entries)}</ol>' if entries else ""

        # Add to the list if the fields differ.
        if entries_str != hanzi_note.web_field:
            notes_to_update.append((hanzi_note, entries_str))

    return notes_to_update


def generate_report(
    config: Config,
    search_string: str,
    hanzi_models: dict[NotetypeId, HanziModel],
    notes_to_update: list[tuple[HanziNote, str]],
    total_hanzi: int,
    total_known_hanzi: int,
) -> str:
    report = [
        "Hanzi Web will update the following notes. Please ensure this ",
        "looks correct before continuing.\n\n",
        f"Search query:\n  {search_string}\n\n",
        f"Unique hanzi: {total_known_hanzi} seen, {total_hanzi} total\n\n",
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


def apply_changes(config: Config, notes_to_update: list[tuple[HanziNote, str]]) -> None:
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
    hanzi_models = get_hanzi_models(config)

    search_string = mw.col.build_search_string(
        config.search_query,
        mw.col.group_searches(
            *[SearchNode(parsable_text=f"mid:{id}") for id in hanzi_models.keys()],
            joiner="OR",
        ),
    )

    notes = {
        id: HanziNote(config, id, hanzi_models)
        for id in mw.col.find_notes(search_string)
    }

    hanzi_web, total_hanzi = get_hanzi_web(notes.values())
    notes_to_update = get_notes_to_update(config, notes.values(), hanzi_web)

    # Summarize the operation to the user.
    report = generate_report(
        config,
        search_string,
        hanzi_models,
        notes_to_update,
        total_hanzi,
        len(hanzi_web),
    )
    if ReportDialog(report).exec() == QDialog.DialogCode.Rejected:
        return

    apply_changes(config, notes_to_update)


def main() -> None:
    menu = QMenu("Hanzi &Web", mw)
    update_action = QAction("&Update notes", menu)
    about_action = QAction("&About...", menu)
    update_action.setShortcut("Ctrl+W")
    menu.addAction(update_action)
    menu.addAction(about_action)
    qconnect(update_action.triggered, update)
    qconnect(about_action.triggered, lambda: showInfo(ABOUT_TEXT))
    mw.form.menuTools.addMenu(menu)
