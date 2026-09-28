"""Módulos de visualização da interface gráfica moderna."""
from ui.gui.views.sidebar import SidebarNav
from ui.gui.views.download_view import DownloadView
from ui.gui.views.search_view import SearchView
from ui.gui.views.watcher_view import WatcherView
from ui.gui.views.license_view import LicenseView
from ui.gui.views.settings_view import SettingsView
from ui.gui.views.about_view import AboutView
from ui.gui.views.eula_dialog import EulaDialog

__all__ = [
    "SidebarNav",
    "DownloadView",
    "SearchView",
    "WatcherView",
    "LicenseView",
    "SettingsView",
    "AboutView",
    "EulaDialog",
]
