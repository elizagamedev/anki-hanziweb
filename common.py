import re
import unicodedata
from re import Pattern
from typing import Any, Optional

from anki.config import Config as AnkiConfig
from aqt import mw as mw_optional
from aqt.main import AnkiQt
from aqt.qt import (  # type: ignore
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QVBoxLayout,
)
from aqt.utils import qconnect


def assert_is_not_none(optional: Optional[Any]) -> Any:
    assert optional is not None
    return optional


mw: AnkiQt = assert_is_not_none(mw_optional)

VERSION = "0.1.2"
CONFIG_VERSION = 0

# Matches each hanzi character individually.
HANZI_REGEXP = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


class Config:
    config_version: int
    hanzi_fields_regexp: Optional[Pattern[Any]]
    max_terms_per_hanzi: int
    search_query: str
    term_separator: str
    web_field: str
    kyujitai_fields_regexp: Pattern[Any]
    shinjitai_fields_regexp: Pattern[Any]
    chinese_reading_search_query: str

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

        self.kyujitai_fields_regexp = re.compile(
            config.get("kyujitai_fields_regexp") or "Kyujitai"
        )

        self.shinjitai_fields_regexp = re.compile(
            config.get("shinjitai_fields_regexp") or "Shinjitai"
        )

        self.chinese_reading_search_query = (
            config.get("chinese_reading_search_query") or ""
        )


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


def show_report(text: str) -> bool:
    return bool(ReportDialog(text).exec() == QDialog.DialogCode.Accepted)
