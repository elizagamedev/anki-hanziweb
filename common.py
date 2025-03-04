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

VERSION = "1.2.0"
CONFIG_VERSION = 1
JS_VERSION = 1

# Matches each hanzi character individually.
HANZI_REGEXP = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# Matches JS sigil in template.
JS_SIGIL = f"/* DO NOT EDIT! -- Hanzi Web JS v{JS_VERSION} */\n"
JS_SIGIL_REGEXP = re.compile(
    r"/\s*\*\s*DO NOT EDIT! -- Hanzi Web JS v(?P<version>\d+)\s*\*/\n?"
)

# https://stackoverflow.com/a/19730306
_TAG_REGEXP = re.compile(r"(<!--.*?-->|<[^>]*>)")

# https://github.com/ankitects/anki/blob/a6426bebe21ea1fe85f5cf31a711134b06447788/rslib/src/template_filters.rs#L113
_FURIGANA_REGEXP = re.compile(r" ?([^ >]+?)\[(.+?)\]")


class Config:
    class ClickAction(Enum):
        EDIT = 0
        BROWSE = 1

    auto_run_on_sync: bool
    click_hanzi_action: Union[None, ClickAction, str]
    click_hanzi_term_action: Union[None, ClickAction, str]
    click_phonetic_action: Union[None, ClickAction, str]
    click_phonetic_term_action: Union[None, ClickAction, str]
    config_version: int
    days_to_update: int
    hanzi_fields_regexp: Optional[Pattern[Any]]
    japanese_search_query: str
    kyujitai_field: str
    max_terms_per_hanzi: int
    search_query: str
    term_separator: str
    web_field: str

    def __init__(self, config: dict[str, Any]):
        self.config_version = config.get("config_version") or 0
        if self.config_version > CONFIG_VERSION:
            raise Exception(
                f"`config_version' {self.config_version} too new "
                f"(expecting <= {CONFIG_VERSION})"
            )

        self.click_hanzi_action = self._string_to_click_action(
            config.get("click_hanzi_action"), self.ClickAction.BROWSE
        )
        self.click_hanzi_term_action = self._string_to_click_action(
            config.get("click_hanzi_term_action"), self.ClickAction.EDIT
        )
        self.click_phonetic_action = self._string_to_click_action(
            config.get("click_phonetic_action"), self.ClickAction.BROWSE
        )
        self.click_phonetic_term_action = self._string_to_click_action(
            config.get("click_phonetic_term_action"), self.ClickAction.EDIT
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

    @classmethod
    def _string_to_click_action(
        cls,
        string: Optional[str],
        default: Union[None, ClickAction, str],
    ) -> Union[None, ClickAction, str]:
        if not string:
            return default
        if string == ":none":
            return None
        if string.startswith(":"):
            result = {
                ":edit": cls.ClickAction.EDIT,
                ":browse": cls.ClickAction.BROWSE,
            }.get(string)
            if not result:
                showWarning(f"Invalid click action: {string}")
                return default
            return result
        return string


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


def _urlencode(text: str) -> str:
    no_tags = _TAG_REGEXP.sub("", text)
    unescaped = html.unescape(no_tags)
    return urllib.parse.quote(unescaped, safe="")


def kana_filter(text: str) -> str:
    return _FURIGANA_REGEXP.sub(r"\2", text.replace("&nbsp;", " "))


def kanji_filter(text: str) -> str:
    return _FURIGANA_REGEXP.sub(r"\1", text.replace("&nbsp;", " "))


def _html_onclick(content: str, onclick: str) -> str:
    return html_tag(
        "a", content, href="#", onclick=f"{onclick};event.preventDefault();"
    )


def html_click_action(
    content: str,
    click_action: Union[None, Config.ClickAction, str],
    ids: Sequence[NoteId],
    replacements: dict[str, str],
) -> str:
    if click_action is None:
        return content
    if click_action == Config.ClickAction.EDIT:
        if ids:
            return _html_onclick(content, f"hanziwebEditNote('{ids[0]}')")
        return content
    if click_action == Config.ClickAction.BROWSE:
        if ids:
            search_query = " OR ".join([f"nid:{x}" for x in ids])
            return _html_onclick(content, f"hanziwebBrowse('{search_query}')")
        return content
    if isinstance(click_action, str):
        s = click_action
        for k, v in replacements.items():
            s = s.replace("{" + k + "}", _urlencode(v))
            s = s.replace("{kana:" + k + "}", _urlencode(kana_filter(v)))
            s = s.replace("{kanji:" + k + "}", _urlencode(kanji_filter(v)))
        return html_tag("a", content, href=s)
    raise Exception("unreachable")


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


def inject_js_into_html(js: str, html: str) -> tuple[str, int]:
    buffer = StringIO()
    previous_version = -1

    class Status(Enum):
        none = 0
        in_script = 1
        in_hanziweb_script = 2
        past_hanziweb_script = 3

    status = Status.none

    for line in html.splitlines(keepends=True):
        if status == Status.past_hanziweb_script:
            buffer.write(line)
        elif status == Status.none:
            if line.strip() == "<script>":
                status = Status.in_script
            buffer.write(line)
        elif status == Status.in_script:
            if m := re.fullmatch(JS_SIGIL_REGEXP, line):
                status = Status.in_hanziweb_script
                previous_version = int(m.group("version"))
                buffer.write(JS_SIGIL)
                buffer.write("(function(){\n")
                buffer.write(js)
                buffer.write("\n})();")
            else:
                status = Status.none
                buffer.write(line)
        elif status == Status.in_hanziweb_script:
            if line.strip() == "</script>":
                status = Status.past_hanziweb_script
                buffer.write(line)
        else:
            raise Exception("unreachable")

    if status != Status.past_hanziweb_script:
        # Didn't find extant version, so append to end.
        buffer.write("\n<script>\n")
        buffer.write(JS_SIGIL)
        buffer.write(js)
        buffer.write("\n</script>")

    return buffer.getvalue(), previous_version
