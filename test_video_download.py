import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from download_ui import DownloadUI
from state_manager import DownloadStateManager
from main import (
    download_video_materials,
    download_lesson_materials,
    process_courses,
    sanitize_filename,
)


class TestVideoDownload(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_patch = patch("core.config.CONFIG_FILE_PATH", os.path.join(self.test_dir, "config.json"))
        self.app_dir_patch = patch("core.config.get_app_dir", return_value=self.test_dir)
        self.config_patch.start()
        self.app_dir_patch.start()

        self.ui = DownloadUI(no_color=True)
        self.http_session = MagicMock()
        self.driver = MagicMock()

    def tearDown(self):
        self.config_patch.stop()
        self.app_dir_patch.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_empty_playlist_returns_empty_list(self):
        # Quando find_elements não encontra itens de playlist
        self.driver.find_elements.return_value = []
        lesson_info = {"title": "Aula 01", "subtitle": "", "url": "https://example.com/aula1"}

        res = download_video_materials(
            driver=self.driver,
            lesson_info=lesson_info,
            course_title="Português",
            lesson_download_path=self.test_dir,
            preferred_quality="720p",
            http_session=self.http_session,
            ui=self.ui,
        )
        self.assertEqual(res, [])

    @patch("main.download_file")
    def test_existing_video_is_skipped(self, mock_download_file):
        lesson_info = {"title": "Aula 01", "subtitle": "", "url": "https://example.com/aula1"}

        # Simula arquivo de vídeo já existente (> 10KB)
        existing_mp4 = os.path.join(self.test_dir, "Bloco_1_Video_720p.mp4")
        with open(existing_mp4, "wb") as f:
            f.write(b"V" * 20000)

        # Mock de 1 item na playlist
        mock_item = MagicMock()
        mock_item.get_attribute.return_value = "https://example.com/video1"
        mock_title = MagicMock()
        mock_title.text = "Bloco 1"
        mock_item.find_element.return_value = mock_title
        self.driver.find_elements.return_value = [mock_item]

        res = download_video_materials(
            driver=self.driver,
            lesson_info=lesson_info,
            course_title="Português",
            lesson_download_path=self.test_dir,
            preferred_quality="720p",
            http_session=self.http_session,
            ui=self.ui,
        )

        # Como já existe, deve pular sem chamar download_file nem driver.get do vídeo
        mock_download_file.assert_not_called()
        self.assertEqual(len(res), 1)
        self.assertIn("Bloco_1_Video_720p.mp4", res)

    @patch("main.download_video_materials")
    @patch("main.download_file")
    def test_download_lesson_materials_triggers_videos_when_enabled(
        self, mock_download_file, mock_download_videos
    ):
        mock_download_videos.return_value = ["Video_1_720p.mp4"]
        mock_download_file.return_value = True

        lesson_info = {"title": "Aula 01", "subtitle": "Sintaxe", "url": "https://example.com/aula1"}
        state_mgr = DownloadStateManager(self.test_dir, sanitize_func=sanitize_filename)

        # Simula nenhum PDF na página para isolar a chamada
        self.driver.find_elements.return_value = []

        ok = download_lesson_materials(
            driver=self.driver,
            lesson_info=lesson_info,
            course_title="Português",
            download_dir=self.test_dir,
            http_session=self.http_session,
            ui=self.ui,
            state_manager=state_mgr,
            download_videos=True,
            preferred_quality="720p",
        )

        self.assertTrue(ok)
        mock_download_videos.assert_called_once()
        # Verifica se o estado registrou o vídeo como concluído
        self.assertTrue(state_mgr.is_lesson_completed("Português", "Aula 01", check_videos=True))

    @patch("main.get_lesson_data")
    @patch("main.download_lesson_materials")
    def test_process_courses_with_videos_flag_checks_video_completion(
        self, mock_download_materials, mock_get_lessons
    ):
        state_mgr = DownloadStateManager(self.test_dir, sanitize_func=sanitize_filename)
        disc_folder = os.path.join(self.test_dir, "Português")
        os.makedirs(disc_folder, exist_ok=True)

        # Disciplina marcada como completed APENAS para PDFs (sem videos_completed)
        state_mgr.mark_discipline_completed("Português", total_lessons=1, videos_completed=False)

        courses = [{"title": "Português", "url": "https://example.com/portugues"}]
        mock_get_lessons.return_value = [
            {"title": "Aula 01", "subtitle": "", "url": "https://example.com/aula1"}
        ]
        mock_download_materials.return_value = True

        # Executa COM --videos
        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.test_dir,
            ui=self.ui,
            http_session=self.http_session,
            state_mgr=state_mgr,
            force=False,
            download_videos=True,
            preferred_quality="720p",
        )

        # Não deve pular a disciplina, pois os vídeos ainda não estavam concluídos!
        mock_get_lessons.assert_called_once()
        mock_download_materials.assert_called_once()
        _, kwargs = mock_download_materials.call_args
        self.assertTrue(kwargs["download_videos"])

        # Agora a disciplina deve estar marcada como concluída com vídeos
        self.assertTrue(state_mgr.is_discipline_completed("Português", check_videos=True))


if __name__ == "__main__":
    unittest.main()
