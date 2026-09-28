"""
Módulo de compatibilidade retroativa para DownloadUI.
A implementação canônica agora reside em ui.cli.rich_ui.RichDownloadUI.
"""
from ui.cli.rich_ui import RichDownloadUI as DownloadUI, RICH_AVAILABLE

__all__ = ["DownloadUI", "RICH_AVAILABLE"]
