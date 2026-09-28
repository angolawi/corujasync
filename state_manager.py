"""
Módulo de compatibilidade retroativa para DownloadStateManager.
A implementação canônica agora reside em core.state_manager.DownloadStateManager.
"""
from core.state_manager import DownloadStateManager, STATE_FILENAME

__all__ = ["DownloadStateManager", "STATE_FILENAME"]
