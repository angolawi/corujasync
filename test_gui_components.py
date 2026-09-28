import os
import unittest
from unittest.mock import MagicMock

# Configura caminhos para teste
local_lib = os.path.expanduser("~/.local/usr/lib")
if os.path.isdir(local_lib):
    os.environ["LD_LIBRARY_PATH"] = f"{local_lib}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ["TCL_LIBRARY"] = os.path.join(local_lib, "tcl8.6")
    os.environ["TK_LIBRARY"] = os.path.join(local_lib, "tk8.6")

from ui.gui.theme import THEME_COLORS, create_card_frame, get_font
from ui.gui.app import CorujaSyncApp, ConcursoDownloaderApp


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

    def test_sidebar_status_update(self):
        self.app.sidebar.set_status("Baixando vídeos...", state="working")
        self.assertIn("Baixando", self.app.sidebar.lbl_status.cget("text"))


if __name__ == "__main__":
    unittest.main()
