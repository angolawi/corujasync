import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from state_manager import DownloadStateManager
from download_ui import DownloadUI
from main import process_courses, sanitize_filename


class TestProcessCoursesSmartResume(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_patch = patch("core.config.CONFIG_FILE_PATH", os.path.join(self.test_dir, "config.json"))
        self.app_dir_patch = patch("core.config.get_app_dir", return_value=self.test_dir)
        self.config_patch.start()
        self.app_dir_patch.start()

        self.state_mgr = DownloadStateManager(self.test_dir, sanitize_func=sanitize_filename)
        self.ui = DownloadUI(no_color=True)
        self.http_session = MagicMock()
        self.driver = MagicMock()

    def tearDown(self):
        self.config_patch.stop()
        self.app_dir_patch.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("main.get_lesson_data")
    @patch("main.download_lesson_materials")
    def test_instant_skip_completed_discipline(self, mock_download_materials, mock_get_lessons):
        disc_title = "Direito Constitucional"
        disc_folder = os.path.join(self.test_dir, sanitize_filename(disc_title))
        os.makedirs(disc_folder, exist_ok=True)

        # Marca como concluída no estado
        self.state_mgr.mark_discipline_completed(disc_title, total_lessons=3)

        courses = [{"title": disc_title, "url": "https://example.com/disc"}]

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.test_dir,
            ui=self.ui,
            http_session=self.http_session,
            state_mgr=self.state_mgr,
            force=False,
        )

        # Não deve chamar get_lesson_data e nem tentar baixar nada
        mock_get_lessons.assert_not_called()
        mock_download_materials.assert_not_called()
        self.driver.get.assert_not_called()

    @patch("main.get_lesson_data")
    @patch("main.download_lesson_materials")
    def test_skip_already_completed_lesson_in_partial_discipline(
        self, mock_download_materials, mock_get_lessons
    ):
        disc_title = "Direito Administrativo"
        disc_folder = os.path.join(self.test_dir, sanitize_filename(disc_title))
        aula00_folder = os.path.join(disc_folder, "Aula_00")
        os.makedirs(aula00_folder, exist_ok=True)

        # Aula 00 concluída, Aula 01 pendente
        self.state_mgr.mark_lesson_completed(disc_title, "Aula 00", ["aula00.pdf"])

        mock_get_lessons.return_value = [
            {"title": "Aula 00", "subtitle": "Intro", "url": "https://example.com/aula0"},
            {"title": "Aula 01", "subtitle": "Atos", "url": "https://example.com/aula1"},
        ]
        mock_download_materials.return_value = True

        courses = [{"title": disc_title, "url": "https://example.com/disc"}]

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.test_dir,
            ui=self.ui,
            http_session=self.http_session,
            state_mgr=self.state_mgr,
            force=False,
        )

        # get_lesson_data foi chamado 1 vez para inspecionar as aulas
        mock_get_lessons.assert_called_once()
        # download_lesson_materials só foi chamado para Aula 01, pulando Aula 00!
        self.assertEqual(mock_download_materials.call_count, 1)
        args, kwargs = mock_download_materials.call_args
        self.assertEqual(kwargs["lesson_info"]["title"], "Aula 01")

        # Ao final, com Aula 01 concluída, a disciplina inteira deve ser marcada como concluída!
        self.assertTrue(self.state_mgr.is_discipline_completed(disc_title))


if __name__ == "__main__":
    unittest.main()
