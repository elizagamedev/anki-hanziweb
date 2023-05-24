from anki.collection import SearchNode
from aqt import gui_hooks
from aqt.qt import QAction, QMenu  # type: ignore
from aqt.utils import qconnect, showInfo, tooltip

from .common import (
    CONFIG_VERSION,
    VERSION,
    Config,
    SupportsPendingChanges,
    load_config,
    mw,
    show_report,
    show_update_nag,
)
from .hanziweb import PendingChanges as PendingHanziWebChanges
from .hanziweb import get_hanzi_models
from .jitai import PendingChanges as PendingJitaiChanges

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
    hanzi_models = get_hanzi_models(config)

    search_string = mw.col.build_search_string(
        config.search_query,
        mw.col.group_searches(
            *[SearchNode(parsable_text=f"mid:{id}") for id in hanzi_models.keys()],
            joiner="OR",
        ),
    )

    japanese_search_string = (
        mw.col.build_search_string(
            search_string,
            config.japanese_search_query,
        )
        if config.japanese_search_query
        else "N/A"
    )

    note_ids = mw.col.find_notes(search_string)

    japanese_note_ids = (
        mw.col.find_notes(japanese_search_string)
        if config.japanese_search_query
        else []
    )

    pending_changes: list[SupportsPendingChanges] = [
        PendingHanziWebChanges(config, note_ids, japanese_note_ids, hanzi_models),
        PendingJitaiChanges(config, japanese_note_ids),
    ]

    report = [
        "Hanzi Web will update the following notes. Please ensure this ",
        "looks correct before continuing.\n\n",
        f"Search query:\n  {search_string}\n",
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

    if is_interactive:
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


init()
