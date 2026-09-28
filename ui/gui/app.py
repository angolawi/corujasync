import os
import sys
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Auto-configura caminhos para libtk/libtcl se estiverem em ~/.local
local_lib = os.path.expanduser("~/.local/usr/lib")
if os.path.isdir(local_lib):
    tcl_dir = os.path.join(local_lib, "tcl8.6")
    tk_dir = os.path.join(local_lib, "tk8.6")
    if os.path.isdir(tcl_dir) and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = tcl_dir
    if os.path.isdir(tk_dir) and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = tk_dir
    if sys.platform != "win32":
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if local_lib not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{local_lib}:{current_ld}"

import customtkinter as ctk
from tkinter import messagebox

from core.config import load_config, save_config
from legal.license_verifier import is_eula_accepted
from ui.gui.theme import THEME_COLORS
from ui.gui.views.eula_dialog import EulaDialog
from ui.gui.views.sidebar import SidebarNav
from ui.gui.views.download_view import DownloadView
from ui.gui.views.search_view import SearchView
from ui.gui.views.watcher_view import WatcherView
from ui.gui.views.license_view import LicenseView
from ui.gui.views.settings_view import SettingsView
from ui.gui.views.about_view import AboutView
from ui.gui.workers import DownloadWorker


class ConcursoDownloaderApp(ctk.CTk):
    """
    Aplicação desktop principal moderna e modular para download, busca e
    gerenciamento offline de materiais de concursos públicos.
    """

    def __init__(self):
        super().__init__()

        self.config = load_config()
        initial_theme = self.config.get("theme", "dark")
        ctk.set_appearance_mode(initial_theme)
        ctk.set_default_color_theme("blue")

        self.title("Concurso Downloader Pro v2.0 - Backup Inteligente")
        self.geometry("980x700")
        self.minsize(880, 600)

        self.event_queue = queue.Queue()
        self.worker: Optional[DownloadWorker] = None
        self.current_view_key: Optional[str] = None
        self.views: Dict[str, Any] = {}

        self._build_layout()
        self._after_eula_id = self.after(200, self._check_first_boot_eula)
        self._after_poll_id = self.after(100, self._poll_event_queue)

    def _check_first_boot_eula(self):
        if not is_eula_accepted():
            EulaDialog(self, on_accepted_callback=self._on_eula_accepted)

    def _on_eula_accepted(self):
        if "download" in self.views:
            self.views["download"].append_log(
                "[INFO] Termos de Uso aceitos com sucesso. Bem-vindo ao Concurso Downloader!\n",
                tag="success",
            )

    def _build_layout(self):
        # 1. Barra Lateral de Navegação
        self.sidebar = SidebarNav(
            self,
            on_view_change=self.switch_view,
            on_theme_toggle=self.toggle_theme,
        )
        self.sidebar.pack(side="left", fill="y")

        # 2. Container Central Dinâmico
        self.content_container = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["bg_main"],
            corner_radius=0,
        )
        self.content_container.pack(side="right", fill="both", expand=True)

        # 3. Instanciação Lazy/Modular das Views
        self.views["download"] = DownloadView(
            self.content_container,
            config=self.config,
            on_start=self._start_download,
            on_stop=self._stop_download,
        )
        self.views["search"] = SearchView(self.content_container, config=self.config)
        self.views["watcher"] = WatcherView(self.content_container, config=self.config)
        self.views["settings"] = SettingsView(
            self.content_container,
            config=self.config,
            on_saved=self._on_settings_saved,
        )
        self.views["license"] = LicenseView(self.content_container)
        self.views["about"] = AboutView(self.content_container, config=self.config)

        # Exibe view inicial
        self.switch_view("download")

    def switch_view(self, view_key: str):
        """Alterna a tela central preservando o estado dos componentes."""
        if self.current_view_key == view_key:
            return

        if self.current_view_key and self.current_view_key in self.views:
            self.views[self.current_view_key].pack_forget()

        if view_key in self.views:
            self.views[view_key].pack(fill="both", expand=True)
            self.current_view_key = view_key
            self.sidebar.set_active(view_key)

    def toggle_theme(self):
        """Alterna entre Dark Mode e Light Mode e salva a preferência."""
        current = ctk.get_appearance_mode().lower()
        new_theme = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new_theme)
        self.config["theme"] = new_theme
        save_config(self.config)

    def _on_settings_saved(self):
        self.config = load_config()

    def _start_download(self):
        """Inicia o processo de download na thread do worker."""
        if self.worker and self.worker.is_alive():
            return

        dl_view: DownloadView = self.views["download"]
        params = dl_view.get_run_parameters()

        if params["mode"] == "single" and not params["curso_input"]:
            messagebox.showwarning(
                "Atenção",
                "Por favor, informe a URL ou o ID numérico do curso/pacote que deseja baixar.",
            )
            return

        # Prepara a UI
        dl_view.set_running_state(True)
        dl_view.clear_logs()
        self.sidebar.set_status("Baixando...", state="working")

        self.worker = DownloadWorker(
            event_queue=self.event_queue,
            download_dir=params["download_dir"],
            curso_input=params["curso_input"],
            email=self.config.get("email", ""),
            senha=self.config.get("senha", ""),
            download_videos=params["download_videos"],
            preferred_quality=params["preferred_quality"],
            force=params["force"],
            preferred_browser=self.config.get("preferred_browser", "auto"),
            wait_time=int(self.config.get("wait_time", 60)),
        )
        self.worker.start()

    def _stop_download(self):
        """Sinaliza parada ao worker ativo."""
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            dl_view: DownloadView = self.views["download"]
            dl_view.append_log(
                "\n[AVISO] Solicitação de cancelamento enviada. Finalizando bloco em andamento...\n",
                tag="warning",
            )
            self.sidebar.set_status("Cancelando...", state="warning")

    def _poll_event_queue(self):
        """Consome eventos da fila thread-safe gerados pelo worker."""
        try:
            dl_view: DownloadView = self.views.get("download")
            while True:
                event_type, data = self.event_queue.get_nowait()

                if event_type == "banner":
                    banner_msg = f"\n=== {data.get('mode')} ===\nDestino: {data.get('dir')}\n"
                    if data.get("name"):
                        banner_msg += f"Alvo: {data.get('name')}\n"
                    dl_view.append_log(banner_msg)

                elif event_type == "status":
                    prefix = {
                        "info": "  [INFO] ",
                        "warning": "  [AVISO] ",
                        "error": "  [ERRO] ",
                        "success": "  [✓] ",
                    }.get(data.level, "  ")
                    dl_view.append_log(f"{prefix}{data.message}\n", tag=data.level)

                elif event_type == "discipline":
                    if data.status == "started":
                        dl_view.append_log(f"\n━━━ [{data.index}/{data.total}] Disciplina: {data.title}\n")
                    elif data.status == "skipped":
                        dl_view.append_log(f"  ↷ [{data.index}/{data.total}] {data.title} (Já concluída)\n")
                    elif data.status == "completed":
                        dl_view.append_log(f"✓ Concluída disciplina: {data.title} ({data.lesson_count} aulas)\n", tag="success")

                elif event_type == "lesson":
                    if data.status == "started":
                        dl_view.append_log(f"  → [{data.index}/{data.total}] {data.title}\n")
                    elif data.status == "skipped":
                        dl_view.append_log(f"  ↷ [{data.index}/{data.total}] {data.title} (já baixada)\n")

                elif event_type == "video_playlist":
                    dl_view.append_log(f"    🎬 Playlist identificada: {data} blocos de vídeo disponíveis.\n")

                elif event_type == "video":
                    if data.status == "started":
                        dl_view.append_log(f"    → [{data.index}/{data.total}] {data.title}\n")
                    elif data.status == "skipped":
                        dl_view.append_log(f"    ↷ [{data.index}/{data.total}] {data.title} (vídeo já baixado)\n")

                elif event_type == "progress":
                    dl_view.update_telemetry(
                        current_file=data.filename,
                        speed_mbps=data.speed_mbps,
                        eta_seconds=data.eta_seconds,
                        progress_ratio=data.ratio,
                    )

                elif event_type == "finished":
                    dl_view.set_running_state(False)
                    elapsed = data.get("elapsed_seconds", 0)
                    if data.get("success"):
                        dl_view.append_log(
                            f"\n=======================================================\n"
                            f"✓ DOWNLOADS CONCLUÍDOS COM SUCESSO! (Tempo: {elapsed:.1f}s)\n"
                            f"=======================================================\n",
                            tag="success",
                        )
                        self.sidebar.set_status("Concluído", state="ready")
                    else:
                        dl_view.append_log(f"\n[ERRO FINAL] Falha na execução: {data.get('error')}\n", tag="error")
                        self.sidebar.set_status("Erro na Execução", state="error")

        except queue.Empty:
            pass

        self._after_poll_id = self.after(100, self._poll_event_queue)

    def destroy(self):
        """Limpa callbacks pendentes antes de fechar a janela."""
        if hasattr(self, "_after_poll_id") and self._after_poll_id:
            try:
                self.after_cancel(self._after_poll_id)
            except Exception:
                pass
        if hasattr(self, "_after_eula_id") and self._after_eula_id:
            try:
                self.after_cancel(self._after_eula_id)
            except Exception:
                pass
        super().destroy()


def run_gui():
    """Função de entrada para inicialização da interface gráfica moderna."""
    app = ConcursoDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
