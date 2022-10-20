from re import Pattern
from typing import Any, Optional

from kyujipy import KyujitaiConverter
from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId
from aqt import gui_hooks
from aqt.browser.browser import Browser
from aqt.utils import qconnect, showInfo, tooltip
from enum import Enum

from .common import (
    assert_is_not_none,
    mw,
    Config,
    show_report,
)


class Direction(Enum):
    KYUJITAI_TO_SHINJITAI = 1
    SHINJITAI_TO_KYUJITAI = 2

    def __str__(self) -> str:
        if self == self.__class__.KYUJITAI_TO_SHINJITAI:
            return "From Kyūjitai to Shinjitai"
        if self == self.__class__.SHINJITAI_TO_KYUJITAI:
            return "From Shinjitai to Kyūjitai"
        raise Exception("Invalid conversion direction")


class JitaiModel:
    id: NotetypeId
    name: str
    from_field: str
    to_field: str

    def __init__(self, id: NotetypeId, name: str, from_field: str, to_field: str):
        self.id = id
        self.name = name
        self.from_field = from_field
        self.to_field = to_field


def create_jitai_model_from_notetype_name_id(
    from_regexp: Pattern[Any],
    to_regexp: Pattern[Any],
    note_type: NotetypeNameId,
) -> Optional[JitaiModel]:
    id = NotetypeId(note_type.id)
    all_fields = mw.col.models.field_names(assert_is_not_none(mw.col.models.get(id)))
    from_field = next(
        (field for field in all_fields if from_regexp.fullmatch(field)), None
    )
    to_field = next((field for field in all_fields if to_regexp.fullmatch(field)), None)
    if from_field is None or to_field is None:
        return None
    return JitaiModel(id, note_type.name, from_field, to_field)


class JitaiNote:
    id: NoteId
    model: JitaiModel
    from_value: str

    def __init__(self, id: NoteId, model: JitaiModel, from_value: str):
        self.id = id
        self.model = model
        self.from_value = from_value


def create_jitai_note_from_id(
    id: NoteId, models: dict[NotetypeId, JitaiModel]
) -> Optional[JitaiNote]:
    note = mw.col.get_note(id)
    model = models.get(note.mid)
    if model is None:
        return None
    if note[model.to_field] or not note[model.from_field]:
        # Skip over notes with filled destinations and empty sources.
        return None
    return JitaiNote(id, model, note[model.from_field])


def generate_report(
    direction: Direction,
    models: dict[NotetypeId, JitaiModel],
    converted_notes: list[tuple[JitaiNote, str]],
) -> str:
    report = [
        "Hanzi Web will update the following notes. Please ensure this ",
        "looks correct before continuing.\n\n",
        f"Direction: {direction}\n\n",
    ]
    if models:
        report.append(f"Note types ({len(models)}):\n")
        for model in models.values():
            report.append(f"  {model.name} [{model.from_field} -> {model.to_field}]\n")

        if converted_notes:
            report.append(f"\nNotes to update ({len(converted_notes)}):\n")
            for (note, to_value) in converted_notes:
                report.append(f"  {note.id} {note.from_value} -> {to_value}\n")
        else:
            report.append(
                "\nNo selected notes have empty destination and non-empty "
                "source fields.\n"
            )
    else:
        report.append("No note types found which have shinjitai and kyūjitai fields.\n")

    return "".join(report)


def apply_changes(
    browser: Browser, direction: Direction, notes: list[tuple[JitaiNote, str]]
) -> None:
    if not notes:
        tooltip("Nothing done.", parent=browser)
        return

    # The checkpoint system (mw.checkpoint() and mw.reset()) are "obsoleted" in favor of
    # Collection Operations. However, Collection Operations have a very short-term
    # memory (~30), which is unsuitable for the potentially massive amounts of changes
    # that Hanzi Web will do on a collection.
    #
    # https://addon-docs.ankiweb.net/background-ops.html?highlight=undo#collection-operations
    mw.checkpoint(f"Hanzi Web: {direction}")
    browser.begin_reset()
    for jitai_note, to_value in notes:
        note = mw.col.get_note(jitai_note.id)
        note[jitai_note.model.to_field] = to_value
        note.flush()
    browser.end_reset()
    mw.reset()
    tooltip(f"{len(notes)} notes updated.", parent=browser)


def add_jitai(browser: Browser, direction: Direction) -> None:
    config = Config(assert_is_not_none(mw.addonManager.getConfig(__name__)))
    converter = KyujitaiConverter()

    if direction == Direction.KYUJITAI_TO_SHINJITAI:
        from_regexp = config.kyujitai_fields_regexp
        to_regexp = config.shinjitai_fields_regexp

        def convert(x: str) -> str:
            return str(converter.kyujitai_to_shinjitai(x))

    elif direction == Direction.SHINJITAI_TO_KYUJITAI:
        from_regexp = config.shinjitai_fields_regexp
        to_regexp = config.kyujitai_fields_regexp

        def convert(x: str) -> str:
            return str(converter.shinjitai_to_kyujitai(x))

    else:
        raise Exception("Invalid conversion direction")

    models = {
        model.id: model
        for model in [
            create_jitai_model_from_notetype_name_id(from_regexp, to_regexp, note_type)
            for note_type in mw.col.models.all_names_and_ids()
        ]
        if model
    }
    note_ids = browser.selected_notes()
    notes = [
        note
        for note in [create_jitai_note_from_id(id, models) for id in note_ids]
        if note
    ]
    converted_notes = [(note, convert(note.from_value)) for note in notes]

    report = generate_report(direction, models, converted_notes)
    if not show_report(report):
        return

    apply_changes(browser, direction, converted_notes)


def init_browser_menu(browser: Browser) -> None:
    menu = browser.form.menuEdit
    menu.addSeparator()
    kyujitai = menu.addAction("Add &Kyūjitai...")
    kyujitai.setShortcut("Ctrl+Alt+K")
    qconnect(
        kyujitai.triggered,
        lambda _, b=browser: add_jitai(b, Direction.SHINJITAI_TO_KYUJITAI),
    )
    shinjitai = menu.addAction("Add &Shinjitai...")
    shinjitai.setShortcut("Ctrl+Alt+S")
    qconnect(
        shinjitai.triggered,
        lambda _, b=browser: add_jitai(b, Direction.KYUJITAI_TO_SHINJITAI),
    )


def init() -> None:
    gui_hooks.browser_menus_did_init.append(init_browser_menu)
