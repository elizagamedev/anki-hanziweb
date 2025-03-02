import aqt
from anki.collection import SearchNode
from aqt import gui_hooks
from aqt.qt import QAction, QMenu  # type: ignore
from aqt.utils import qconnect, showInfo, tooltip
from itertools import islice

from .common import (
    CONFIG_VERSION,
    Config,
    SupportsPendingChanges,
    VERSION,
    get_lazy_data,
    load_config,
    log,
    mw,
    show_report,
    show_update_nag,
)
from .hanziweb import PendingChanges as PendingHanziWebChanges
from .hanziweb import get_hanzi_models
from .jitai import PendingChanges as PendingJitaiChanges
from anki.notes import NoteId
from anki.decks import DeckId
from typing import Sequence, Tuple, Any
from pprint import pprint
from anki.consts import NEW_CARDS_DUE

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


def update(config: Config, is_interactive: bool) -> None:
    log("Reading lazy data")
    lazy_data = get_lazy_data()

    hanzi_models = get_hanzi_models(config, lazy_data.js)

    base_search_string = mw.col.build_search_string(
        config.search_query,
        mw.col.group_searches(
            *[SearchNode(parsable_text=f"mid:{id}") for id in hanzi_models.keys()],
            joiner="OR",
        ),
    )

    source_search_string = mw.col.build_search_string(
        base_search_string,
        SearchNode(parsable_text=f"is:review"),
    )

    japanese_search_string = (
        mw.col.build_search_string(
            base_search_string,
            config.japanese_search_query,
        )
        if config.japanese_search_query
        else "N/A"
    )

    source_note_ids = set(mw.col.find_notes(source_search_string))

    destination_note_ids = get_next_n_days_of_note_ids(
        base_search_string, config.days_to_update
    )

    japanese_note_ids = (
        set(mw.col.find_notes(japanese_search_string))
        if config.japanese_search_query
        else set()
    )

    pending_changes: list[SupportsPendingChanges] = [
        PendingHanziWebChanges(
            config,
            source_note_ids,
            destination_note_ids,
            japanese_note_ids,
            hanzi_models,
            lazy_data.phonetics,
            lazy_data.onyomi,
        ),
        PendingJitaiChanges(
            config,
            destination_note_ids,
            japanese_note_ids,
        ),
    ]

    for change in pending_changes:
        if not change.confirm():
            return

    if is_interactive:
        report = [
            "Hanzi Web will update the following notes. Please ensure this ",
            "looks correct before continuing.\n\n",
            f"Search query:\n  {base_search_string}\n",
            f"Japanese search query:\n  {japanese_search_string}\n",
            "Note types:\n",
        ]

        for model in hanzi_models.values():
            fields = ", ".join(model.fields)
            report.append(f"  {model.name} [{fields}]\n")
        report.append("\n")

        for change in pending_changes:
            report.append(change.report)
            report.append("\n")

        if not show_report("".join(report)):
            return

    # The checkpoint system (mw.checkpoint() and mw.reset()) are "obsoleted" in favor of
    # Collection Operations. However, Collection Operations have a very short-term
    # memory (~30), which is unsuitable for the potentially massive amounts of changes
    # that Hanzi Web will do on a collection.
    #
    # https://addon-docs.ankiweb.net/background-ops.html?highlight=undo#collection-operations
    if any(not x.is_empty for x in pending_changes):
        mw.checkpoint("Hanzi Web")
        tooltip_text = [x.apply() for x in pending_changes]
        mw.reset()
        tooltip(" ".join(x for x in tooltip_text if x), parent=mw)
    else:
        if is_interactive:
            tooltip("No changes.", parent=mw)


def get_next_n_days_of_note_ids(
    search_query: str,
    days_to_update: int,
) -> set[NoteId]:
    if days_to_update <= 0:
        return set(mw.col.find_notes(search_query))

    # Start the result with all notes due for review within the next N days.
    next_n_days_search_string = mw.col.build_search_string(
        search_query,
        SearchNode(parsable_text=f"prop:due<={days_to_update}"),
    )
    next_n_days_note_ids = set(mw.col.find_notes(next_n_days_search_string))

    # For each deck, find the next N days worth of new notes and add them.
    for deck in mw.col.decks.get_all_legacy():
        config = mw.col.decks.config_dict_for_deck_id(DeckId(deck["id"]))

        new_cards_search_string = mw.col.build_search_string(
            search_query,
            SearchNode(parsable_text=f"is:new"),
            SearchNode(deck=deck["name"]),
        )

        if config["new"]["order"] == NEW_CARDS_DUE:
            # Add any outstanding new cards today plus the next N days' worth.
            new_note_ids = mw.col.find_notes(
                new_cards_search_string,
                order="c.due asc, c.id asc",
            )

            new_cards_per_day = config["new"]["perDay"]
            remaining_cards_today = new_cards_per_day - deck["newToday"][1]
            total_cards_to_update = (
                remaining_cards_today + new_cards_per_day * days_to_update
            )

            next_n_days_note_ids.update(islice(new_note_ids, total_cards_to_update))
        else:
            # If the cards are pulled in randomly, we can't guess the next N to appear,
            # so include them all.
            new_note_ids = mw.col.find_notes(new_cards_search_string)
            next_n_days_note_ids.update(new_note_ids)

    return next_n_days_note_ids


def maybe_update_from_gui() -> None:
    config = load_config()
    if config.config_version < CONFIG_VERSION:
        show_update_nag()
    else:
        update(config, is_interactive=True)


def maybe_update_from_hook() -> None:
    config = load_config()
    if config.config_version >= CONFIG_VERSION and config.auto_run_on_sync:
        update(config, is_interactive=False)


def on_webview_did_receive_js_message(
    handled: Tuple[bool, Any], message: str, context: Any
) -> Tuple[bool, Any]:
    if not message.startswith("hanziweb"):
        return handled

    args = message.split(" ", maxsplit=1)
    ret = None
    if args[0] == "hanziwebEditNote":
        note_id = NoteId(int(args[1]))
        try:
            # Try using AnkiConnect's nice dialog.
            aqt.dialogs.open("foosoft.ankiconnect.Edit", mw.col.get_note(note_id))
        except KeyError:
            # But fall back to browser.
            browser = aqt.dialogs.open("Browser", mw.window())
            browser.search_for_terms(f"nid:{args[1]}")
    elif args[0] == "hanziwebBrowse":
        browser = aqt.dialogs.open("Browser", mw.window())
        browser.search_for_terms(args[1])
    return (True, ret)


def init() -> None:
    menu = QMenu("Hanzi &Web", mw)
    update_action = QAction("&Update notes", menu)
    about_action = QAction("&About...", menu)
    update_action.setShortcut("Ctrl+W")
    menu.addAction(update_action)
    menu.addAction(about_action)
    qconnect(update_action.triggered, maybe_update_from_gui)
    qconnect(about_action.triggered, lambda: showInfo(ABOUT_TEXT))
    mw.form.menuTools.addMenu(menu)

    gui_hooks.sync_will_start.append(maybe_update_from_hook)
    gui_hooks.sync_did_finish.append(maybe_update_from_hook)
    gui_hooks.webview_did_receive_js_message.append(on_webview_did_receive_js_message)


init()
