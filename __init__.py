from aqt import mw
from aqt.utils import showInfo, qconnect
from aqt.qt import QMenu, QAction
from sys import platform

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

config = mw.addonManager.getConfig(__name__)


def update() -> None:
    cardCount = mw.col.cardCount()
    showInfo("Card count: %d" % cardCount)


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
