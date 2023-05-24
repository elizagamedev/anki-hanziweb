from dataclasses import dataclass
from re import Pattern
from typing import Any, Optional, Sequence

from anki.models import NotetypeId, NotetypeNameId
from anki.notes import NoteId

from .common import Config, assert_is_not_none, mw
from .kyujipy import KyujitaiConverter

CONFIG_NORMALIZE_NOTE_TEXT = "normalize_note_text"


@dataclass
class JitaiModel:
    id: NotetypeId
    name: str
    from_field: str
    to_field: str


def create_jitai_model_from_notetype_name_id(
    shinjitai: Pattern[Any],
    kyujitai: str,
    note_type: NotetypeNameId,
) -> Optional[JitaiModel]:
    id = NotetypeId(note_type.id)
    all_fields = mw.col.models.field_names(assert_is_not_none(mw.col.models.get(id)))
    from_field = next(
        (field for field in all_fields if shinjitai.fullmatch(field)), None
    )
    to_field = next((field for field in all_fields if kyujitai == field), None)
    if from_field is None or to_field is None:
        return None
    return JitaiModel(id, note_type.name, from_field, to_field)


@dataclass
class JitaiNote:
    id: NoteId
    model: JitaiModel
    from_value: str
    to_value: str


def create_jitai_note_from_id(
    id: NoteId, models: dict[NotetypeId, JitaiModel]
) -> Optional[JitaiNote]:
    note = mw.col.get_note(id)
    model = models.get(note.mid)
    if model is None:
        return None
    from_value = note[model.from_field]
    if not from_value:
        # Skip over notes with empty sources.
        return None
    return JitaiNote(id, model, from_value, note[model.to_field])


def generate_report(
    models: dict[NotetypeId, JitaiModel],
    converted_notes: list[tuple[JitaiNote, str]],
) -> str:
    report = [
        "== Shinjitai to kyūjitai conversion.\n\n",
    ]
    if models:
        report.append(f"Note types ({len(models)}):\n")
        for model in models.values():
            report.append(f"  {model.name} [{model.from_field} -> {model.to_field}]\n")

        if converted_notes:
            report.append(f"\nNotes to update ({len(converted_notes)}):\n")
            for note, to_value in converted_notes:
                report.append(f"  {note.id} {note.from_value} -> {to_value}\n")
        else:
            report.append("\nNo notes to update.\n")
    else:
        report.append("No note types found which have shinjitai and kyūjitai fields.\n")

    return "".join(report)


class PendingChanges:
    config: Config
    report: str
    notes: list[tuple[JitaiNote, str]]

    def __init__(self, config: Config, note_ids: Sequence[NoteId]):
        self.config = config
        converter = KyujitaiConverter()  # type: ignore

        def convert(x: str) -> str:
            return str(converter.shinjitai_to_kyujitai(x))  # type: ignore

        models = (
            {
                model.id: model
                for model in [
                    create_jitai_model_from_notetype_name_id(
                        config.hanzi_fields_regexp, config.kyujitai_field, note_type
                    )
                    for note_type in mw.col.models.all_names_and_ids()
                ]
                if model
            }
            if config.hanzi_fields_regexp
            else {}
        )
        notes = [
            note
            for note in [create_jitai_note_from_id(id, models) for id in note_ids]
            if note
        ]
        self.notes = [
            (note, conversion)
            for note in notes
            if (conversion := convert(note.from_value)) != note.to_value
        ]

        self.report = generate_report(models, self.notes)

    @property
    def is_empty(self) -> bool:
        return not self.notes

    def apply(self) -> Optional[str]:
        if not self.notes:
            return None

        # Prevent Anki from un-kyujitai-ing these character forms.
        normalize_note_text = mw.col.conf.get(CONFIG_NORMALIZE_NOTE_TEXT)
        try:
            mw.col.conf[CONFIG_NORMALIZE_NOTE_TEXT] = False

            for jitai_note, to_value in self.notes:
                note = mw.col.get_note(jitai_note.id)
                note[jitai_note.model.to_field] = to_value
                note.flush()
            return f"Kyūjitai: {len(self.notes)} notes updated."
        finally:
            if normalize_note_text is None:
                del mw.col.conf[CONFIG_NORMALIZE_NOTE_TEXT]
            else:
                mw.col.conf[CONFIG_NORMALIZE_NOTE_TEXT] = normalize_note_text
