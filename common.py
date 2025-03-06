import json
import re
import unicodedata
import html
import urllib
from pathlib import PurePath
from enum import Enum
from re import Pattern
from typing import Any, Optional, Protocol, Tuple, Union, Sequence
from io import StringIO

from anki.notes import NoteId
from anki.config import Config as AnkiConfig
from aqt import mw as mw_optional
from aqt.main import AnkiQt
from aqt.qt import (  # type: ignore
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QVBoxLayout,
)
from aqt.utils import qconnect, showWarning, showInfo


def assert_is_not_none(optional: Optional[Any]) -> Any:
    assert optional is not None
    return optional


mw: AnkiQt = assert_is_not_none(mw_optional)

VERSION = "1.3.1"
CONFIG_VERSION = 1
JS_VERSION = 1

# Matches each hanzi character individually.
HANZI_REGEXP = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# Matches JS sigil in template.
_JS_SIGIL = f"/* DO NOT EDIT! -- Hanzi Web JS v{JS_VERSION} */\n"
_JS_SIGIL_REGEXP = re.compile(
    r"/\s*\*\s*DO NOT EDIT! -- Hanzi Web JS v(?P<version>\d+)\s*\*/\n?"
)

# Matches a trailing newline plus whitespace.
_TRAILING_NEWLINE_REGEXP = re.compile(r".*\n\s*$", flags=re.DOTALL)

# https://stackoverflow.com/a/19730306
_TAG_REGEXP = re.compile(r"(<!--.*?-->|<[^>]*>)")

# https://github.com/ankitects/anki/blob/a6426bebe21ea1fe85f5cf31a711134b06447788/rslib/src/template_filters.rs#L113
_FURIGANA_REGEXP = re.compile(r" ?([^ >]+?)\[(.+?)\]")


class Config:
    auto_run_on_sync: bool
    click_hanzi_action: Any
    click_hanzi_term_action: Any
    click_phonetic_action: Any
    click_phonetic_term_action: Any
    config_version: int
    days_to_update: int
    hanzi_fields_regexp: Optional[Pattern[Any]]
    japanese_search_query: str
    kyujitai_field: str
    max_terms_per_hanzi: int
    search_query: str
    term_separator: str
    web_field: str

    js_required: bool

    def __init__(self, config: dict[str, Any]):
        self.config_version = config.get("config_version") or 0
        if self.config_version > CONFIG_VERSION:
            raise Exception(
                f"`config_version' {self.config_version} too new "
                f"(expecting <= {CONFIG_VERSION})"
            )

        self.click_hanzi_action = (
            self._validate_click_action(config.get("click_hanzi_action")) or ":browse"
        )
        self.click_hanzi_term_action = (
            self._validate_click_action(config.get("click_hanzi_term_action"))
            or ":edit"
        )
        self.click_phonetic_action = (
            self._validate_click_action(config.get("click_phonetic_action"))
            or ":browse"
        )
        self.click_phonetic_term_action = (
            self._validate_click_action(config.get("click_phonetic_term_action"))
            or ":edit"
        )

        self.days_to_update = config.get("days_to_update") or 0

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

        self.kyujitai_field = config.get("kyujitai_field") or "Kyujitai"

        self.japanese_search_query = config.get("japanese_search_query") or ""

        auto_run_on_sync = config.get("auto_run_on_sync")
        self.auto_run_on_sync = False if auto_run_on_sync is None else auto_run_on_sync

        # Derived properties.
        self.js_required = (
            self.click_hanzi_action != ":none"
            or self.click_hanzi_term_action != ":none"
            or self.click_phonetic_action != ":none"
            or self.click_phonetic_term_action != ":none"
        )

    @classmethod
    def _validate_click_action(cls, object: Any) -> Any:
        def show_warning() -> None:
            showWarning(f"Invalid click action: {object}")

        if not object:
            return None
        if isinstance(object, str):
            if object.startswith(":"):
                if object not in {":none", ":edit", ":browse"}:
                    show_warning()
                    return None
            return object
        if isinstance(object, list):
            for pair in object:
                if not isinstance(pair, list):
                    show_warning()
                    return None
                if len(pair) != 2:
                    show_warning()
                    return None
                for item in pair:
                    if not isinstance(item, str):
                        show_warning()
                        return None
            return object
        show_warning()
        return None


def load_config() -> Config:
    return Config(assert_is_not_none(mw.addonManager.getConfig(__name__)))


class LazyData:
    onyomi: dict[str, list[Tuple[str, list[str]]]]
    phonetics: dict[str, str]
    js: str

    def __init__(
        self,
        onyomi: dict[str, list[list[str]]],
        phonetics: dict[str, str],
        js: str,
    ):
        self.onyomi = {
            kanji: [(readings[0], readings[1:]) for readings in all_readings]
            for kanji, all_readings in onyomi.items()
        }
        self.phonetics = phonetics
        self.js = js


_lazy_data: Optional[LazyData] = None


def get_lazy_data() -> LazyData:
    global _lazy_data
    if not _lazy_data:
        addon_directory = PurePath(__file__).parent

        with open(
            addon_directory / "kanji-onyomi.json", "r", encoding="utf-8"
        ) as onyomi_file:
            onyomi = json.load(onyomi_file)

        with open(
            addon_directory / "phonetics.json", "r", encoding="utf-8"
        ) as phonetics_file:
            phonetics = json.load(phonetics_file)

        with open(
            addon_directory / "hanziweb.min.js", "r", encoding="utf-8"
        ) as js_file:
            js = js_file.read().strip()

        _lazy_data = LazyData(onyomi, phonetics, js)
    return _lazy_data


def normalize_unicode(string: str) -> str:
    return (
        unicodedata.normalize("NFC", string)
        if mw.col.get_config_bool(AnkiConfig.Bool.NORMALIZE_NOTE_TEXT)
        else string
    )


class ReportDialog(QDialog):  # type: ignore
    def __init__(self, text: str):
        super().__init__(mw)
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


def show_update_nag() -> None:
    showWarning(
        "Hanzi Web has been updated, and your configuration is out of date. "
        + "Please review the README and update your configuration file."
    )


def html_tag(
    tag: str, content: str, clazz: Optional[str] = None, **kwargs: Optional[str]
) -> str:
    kwargs["class"] = clazz
    properties = " ".join([f'{k}="{v}"' for k, v in kwargs.items() if v is not None])
    if properties:
        return f"<{tag} {properties}>{content}</{tag}>"
    return f"<{tag}>{content}</{tag}>"


def strip_kana_and_html(text: str) -> str:
    text = _TAG_REGEXP.sub("", text)
    text = text.replace("&nbsp;", " ")
    text = _FURIGANA_REGEXP.sub(r"\1", text)
    return html.escape(text)


def log(message: str) -> None:
    print(f"HanziWeb: {message}")


class SupportsPendingChanges(Protocol):
    @property
    def is_empty(self) -> bool:
        pass

    def confirm(self) -> bool:
        pass

    @property
    def report(self) -> str:
        pass

    def apply(self) -> Optional[str]:
        pass


def inject_js_into_html(config: Config, js: str, html: str) -> tuple[str, int]:
    buffer = StringIO()
    previous_version = -1

    def dump_object(name: str, object: Any) -> None:
        buffer.write(f"window.{name}=")
        json.dump(object, buffer, ensure_ascii=False, separators=(",", ":"))
        buffer.write(";\n")

    def inject() -> None:
        buffer.write(_JS_SIGIL)
        buffer.write("(function(){\n")
        dump_object("hanziwebHanziActions", config.click_hanzi_action)
        dump_object("hanziwebHanziTermActions", config.click_hanzi_term_action)
        dump_object("hanziwebPhoneticActions", config.click_phonetic_action)
        dump_object(
            "hanziwebPhoneticTermActions",
            config.click_phonetic_term_action,
        )
        buffer.write(js)
        buffer.write("\n})();\n")

    class Status(Enum):
        NONE = 0
        IN_SCRIPT = 1
        IN_HANZIWEB_SCRIPT = 2
        PAST_HANZIWEB_SCRIPT = 3

    status = Status.NONE
    script_line = "<script>\n"
    final_line_is_empty = False

    for line in html.splitlines(keepends=True):
        if status == Status.PAST_HANZIWEB_SCRIPT:
            buffer.write(line)
        elif status == Status.NONE:
            if line.strip() == "<script>":
                status = Status.IN_SCRIPT
                script_line = line
            else:
                buffer.write(line)
        elif status == Status.IN_SCRIPT:
            if m := re.fullmatch(_JS_SIGIL_REGEXP, line):
                status = Status.IN_HANZIWEB_SCRIPT
                previous_version = int(m.group("version"))
                if config.js_required:
                    buffer.write(script_line)
                    inject()
            else:
                status = Status.NONE
                buffer.write(script_line)
                buffer.write(line)
        elif status == Status.IN_HANZIWEB_SCRIPT:
            if line.strip() == "</script>":
                status = Status.PAST_HANZIWEB_SCRIPT
                if config.js_required:
                    buffer.write(line)
        else:
            raise Exception("unreachable")

    if status != Status.PAST_HANZIWEB_SCRIPT and config.js_required:
        # Didn't find extant version, so append to end.
        if not _TRAILING_NEWLINE_REGEXP.fullmatch(html):
            buffer.write("\n")
        buffer.write("<script>\n")
        inject()
        buffer.write("</script>")

    return buffer.getvalue(), previous_version
