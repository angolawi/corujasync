import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Bootstrap transparente para carregar libtk no Linux
local_lib = os.path.expanduser("~/.local/usr/lib")
if os.path.isdir(local_lib) and sys.platform != "win32":
    curr_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if local_lib not in curr_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{local_lib}:{curr_ld}"
        os.environ["TCL_LIBRARY"] = os.path.join(local_lib, "tcl8.6")
        os.environ["TK_LIBRARY"] = os.path.join(local_lib, "tk8.6")
        os.execv(sys.executable, [sys.executable] + sys.argv)

from ui.gui.theme import THEME_COLORS, create_card_frame, get_font
from ui.gui.app import CorujaSyncApp, ConcursoDownloaderApp
from ui.gui.dialogs import ModernDialog, show_info, show_success, show_warning, show_error, ask_confirm
from core.events import ProgressEvent


class TestGuiComponents(unittest.TestCase):

    def setUp(self):
        # Cria a janela sem abrir loop infinito
        self.app = CorujaSyncApp()
        self.app.withdraw()  # Oculta janela durante testes
        self.app.update()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass

    def test_theme_tokens(self):
        # Garante que todos os tokens de cores são tuplas (light, dark)
        for token_name, color_pair in THEME_COLORS.items():
            self.assertIsInstance(color_pair, tuple, f"Token {token_name} deve ser uma tupla")
            self.assertEqual(len(color_pair), 2, f"Token {token_name} deve ter 2 valores (light, dark)")

    def test_app_initialization_and_views(self):
        # Verifica se todas as views modulares foram instanciadas
        expected_views = ["download", "search", "watcher", "settings", "license", "about"]
        for v in expected_views:
            self.assertIn(v, self.app.views)
            self.assertIsNotNone(self.app.views[v])

        # Verifica view ativa padrão
        self.assertEqual(self.app.current_view_key, "download")

    def test_view_switching(self):
        # Testa alternância suave entre todas as views
        for v in ["search", "watcher", "settings", "license", "about", "download"]:
            self.app.switch_view(v)
            self.assertEqual(self.app.current_view_key, v)
            self.assertEqual(self.app.sidebar.active_view, v)

    def test_toggle_theme(self):
        initial_theme = self.app.config.get("theme", "dark")
        self.app.toggle_theme()
        toggled_theme = self.app.config.get("theme")
        self.assertNotEqual(initial_theme, toggled_theme)

    def test_download_view_parameters_and_telemetry(self):
        dl_view = self.app.views["download"]

        # Testa parâmetros padrão
        params = dl_view.get_run_parameters()
        self.assertEqual(params["mode"], "single")
        self.assertIn(params["preferred_quality"], ["720p", "480p", "360p"])

        # Testa atualização de telemetria sem erro
        dl_view.update_telemetry(
            current_file="Livro_01.pdf",
            speed_mbps=3.45,
            eta_seconds=75,
            progress_ratio=0.5,
        )
        self.assertEqual(dl_view.lbl_current_file.cget("text"), "Livro_01.pdf")
        self.assertEqual(dl_view.lbl_speed.cget("text"), "3.45 MB/s")
        self.assertEqual(dl_view.lbl_eta.cget("text"), "1m 15s")
        self.assertEqual(dl_view.lbl_percent.cget("text"), "50%")

        # Testa ETA float sem crash
        dl_view.update_telemetry(
            eta_seconds=75.6,
        )
        self.assertEqual(dl_view.lbl_eta.cget("text"), "1m 16s")

    def test_poll_event_queue_progress(self):
        # Testa o processamento do evento de progresso diretamente pela fila da UI
        event = ProgressEvent(
            filename="Aula_01.pdf",
            downloaded_bytes=1048576,
            total_bytes=2097152,
            speed_bytes_sec=1048576.0,
            eta_seconds=1.5,
            percent=50.0,
        )
        self.app.event_queue.put(("progress", event))
        self.app._poll_event_queue()

        dl_view = self.app.views["download"]
        self.assertEqual(dl_view.lbl_current_file.cget("text"), "Aula_01.pdf")
        self.assertEqual(dl_view.lbl_speed.cget("text"), "1.00 MB/s")
        self.assertEqual(dl_view.lbl_eta.cget("text"), "2s")
        self.assertEqual(dl_view.lbl_percent.cget("text"), "50%")

    def test_sidebar_status_update(self):
        self.app.sidebar.set_status("Baixando vídeos...", state="working")
        self.assertIn("Baixando", self.app.sidebar.lbl_status.cget("text"))

    def test_modern_dialog_instantiation(self):
        # Testa a criação de todas as variantes de diálogos sem exceções
        for dtype in ["info", "success", "warning", "error", "confirm"]:
            dlg = ModernDialog(
                parent=self.app,
                title=f"Teste {dtype.title()}",
                message="Mensagem de teste unitário do modal.",
                dialog_type=dtype,
                confirm_text="Confirmar",
                cancel_text="Cancelar" if dtype == "confirm" else None,
            )
            dlg.withdraw()
            dlg.update()
            self.assertFalse(dlg.result)
            dlg._on_confirm()
            self.assertTrue(dlg.result)

    def test_modern_dialog_cancel(self):
        dlg = ModernDialog(
            parent=self.app,
            title="Teste Cancelar",
            message="Cancelamento do modal.",
            dialog_type="confirm",
            cancel_text="Cancelar",
        )
        dlg.withdraw()
        dlg.update()
        dlg._on_cancel()
        self.assertFalse(dlg.result)

    @patch("ui.gui.views.download_view.show_info")
    @patch("ui.gui.views.download_view.show_success")
    def test_download_view_copy_logs(self, mock_success, mock_info):
        dl_view = self.app.views["download"]
        dl_view.clear_logs()
        # Sem logs -> dispara show_info
        dl_view.copy_logs()
        mock_info.assert_called_once()

        # Com logs -> copia para clipboard e dispara show_success
        dl_view.append_log("Linha de teste para cópia de log.")
        dl_view.copy_logs()
        mock_success.assert_called_once()
        self.assertEqual(dl_view.clipboard_get(), "Linha de teste para cópia de log.")


if __name__ == "__main__":
    unittest.main()
