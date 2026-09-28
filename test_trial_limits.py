import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.events import DownloadObserver, DisciplineEvent, StatusEvent
from core.state_manager import DownloadStateManager
from core.downloader import sanitize_filename
from legal.license_manager import LicenseManager, generate_license_key
from core.processor import process_courses


class MockObserver(DownloadObserver):
    def __init__(self):
        self.discipline_events = []
        self.status_events = []

    def on_discipline(self, event: DisciplineEvent) -> None:
        self.discipline_events.append(event)

    def on_status(self, event: StatusEvent) -> None:
        self.status_events.append(event)


class TestTrialLimits(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_patch = patch("core.config.CONFIG_FILE_PATH", os.path.join(self.test_dir, "config.json"))
        self.app_dir_patch = patch("core.config.get_app_dir", return_value=self.test_dir)
        self.config_patch.start()
        self.app_dir_patch.start()

        self.state_mgr = DownloadStateManager(self.test_dir, sanitize_func=sanitize_filename)
        self.observer = MockObserver()
        self.http_session = MagicMock()
        self.driver = MagicMock()

    def tearDown(self):
        self.config_patch.stop()
        self.app_dir_patch.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_trial_allows_first_discipline_and_blocks_subsequent(self):
        lm = LicenseManager()
        self.assertFalse(lm.is_premium())

        # Primeira disciplina permitida
        allowed1, msg1 = lm.can_download_discipline("Direito Constitucional")
        self.assertTrue(allowed1)
        self.assertEqual(msg1, "")

        # Simula conclusão da 1ª disciplina no modo Free
        lm.record_free_discipline_completed("Direito Constitucional")

        # Retomada da mesma disciplina permitida
        allowed_same, _ = lm.can_download_discipline("Direito Constitucional")
        self.assertTrue(allowed_same)

        # Tentativa de baixar uma SEGUNDA disciplina no modo Free é bloqueada
        allowed2, msg2 = lm.can_download_discipline("Direito Administrativo")
        self.assertFalse(allowed2)
        self.assertIn("Limite da versão de demonstração", msg2)
        self.assertIn("Direito Constitucional", msg2)

    def test_pro_license_unlimited_disciplines(self):
        lm = LicenseManager()
        key = generate_license_key(client_id="aluno@teste.com", tier="vitalicio")
        activated, _ = lm.activate(key)
        self.assertTrue(activated)
        self.assertTrue(lm.is_premium())

        # Ambas permitidas sem limite
        allowed1, _ = lm.can_download_discipline("Direito Constitucional")
        allowed2, _ = lm.can_download_discipline("Direito Administrativo")
        self.assertTrue(allowed1)
        self.assertTrue(allowed2)

    @patch("core.processor.get_lesson_data")
    @patch("core.processor.download_lesson_materials")
    def test_package_download_cuts_at_one_discipline_in_free_mode(
        self, mock_download, mock_get_lessons
    ):
        mock_get_lessons.return_value = [
            {"title": "Aula 01", "url": "https://example.com/aula1"}
        ]
        def fake_download(*args, **kwargs):
            course_title = kwargs.get("course_title", "")
            os.makedirs(os.path.join(self.test_dir, sanitize_filename(course_title)), exist_ok=True)
            return True

        mock_download.side_effect = fake_download

        courses = [
            {"title": "Português", "url": "https://example.com/port"},
            {"title": "Direito Constitucional", "url": "https://example.com/const"},
            {"title": "Direito Administrativo", "url": "https://example.com/adm"},
        ]

        lm = LicenseManager()
        self.assertFalse(lm.is_premium())

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.test_dir,
            observer=self.observer,
            http_session=self.http_session,
            state_mgr=self.state_mgr,
            license_mgr=lm,
        )

        # Português foi baixado com sucesso
        self.assertTrue(self.state_mgr.is_discipline_completed("Português"))
        # As outras duas NÃO foram baixadas
        self.assertFalse(self.state_mgr.is_discipline_completed("Direito Constitucional"))
        self.assertFalse(self.state_mgr.is_discipline_completed("Direito Administrativo"))

        # mock_download só foi chamado 1 vez (para a Aula 01 de Português)
        self.assertEqual(mock_download.call_count, 1)

        # Verifica eventos de skip com motivo do Plano Free
        skipped_events = [e for e in self.observer.discipline_events if e.status == "skipped"]
        self.assertEqual(len(skipped_events), 2)
        self.assertIn("Plano Free", skipped_events[0].reason)
        self.assertIn("Plano Free", skipped_events[1].reason)

    @patch("core.processor.get_lesson_data")
    @patch("core.processor.download_lesson_materials")
    def test_package_download_all_disciplines_in_pro_mode(
        self, mock_download, mock_get_lessons
    ):
        mock_get_lessons.return_value = [
            {"title": "Aula 01", "url": "https://example.com/aula1"}
        ]
        def fake_download(*args, **kwargs):
            course_title = kwargs.get("course_title", "")
            os.makedirs(os.path.join(self.test_dir, sanitize_filename(course_title)), exist_ok=True)
            return True

        mock_download.side_effect = fake_download

        courses = [
            {"title": "Português", "url": "https://example.com/port"},
            {"title": "Direito Constitucional", "url": "https://example.com/const"},
        ]

        lm = LicenseManager()
        key = generate_license_key(client_id="aluno@teste.com", tier="vitalicio")
        lm.activate(key)

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.test_dir,
            observer=self.observer,
            http_session=self.http_session,
            state_mgr=self.state_mgr,
            license_mgr=lm,
        )

        # Ambas disciplinas foram concluídas
        self.assertTrue(self.state_mgr.is_discipline_completed("Português"))
        self.assertTrue(self.state_mgr.is_discipline_completed("Direito Constitucional"))
        self.assertEqual(mock_download.call_count, 2)


if __name__ == "__main__":
    unittest.main()
