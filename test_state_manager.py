import os
import shutil
import tempfile
import unittest
from state_manager import DownloadStateManager


class TestDownloadStateManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = DownloadStateManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initial_state_empty(self):
        self.assertFalse(self.state_mgr.is_discipline_completed("Direito Tributário"))
        self.assertFalse(self.state_mgr.is_lesson_completed("Direito Tributário", "Aula 00"))

    def test_mark_lesson_completed(self):
        disc = "Direito Tributário"
        lesson = "Aula 00"
        disc_folder = os.path.join(self.test_dir, disc)
        lesson_folder = os.path.join(disc_folder, lesson)
        os.makedirs(lesson_folder, exist_ok=True)

        self.state_mgr.mark_lesson_completed(disc, lesson, ["aula00.pdf"])
        self.assertTrue(self.state_mgr.is_lesson_completed(disc, lesson))
        self.assertFalse(self.state_mgr.is_discipline_completed(disc))

        # Recarrega do disco para verificar persistência
        reloaded = DownloadStateManager(self.test_dir)
        self.assertTrue(reloaded.is_lesson_completed(disc, lesson))

    def test_mark_discipline_completed(self):
        disc = "Português"
        disc_folder = os.path.join(self.test_dir, disc)
        os.makedirs(disc_folder, exist_ok=True)

        self.state_mgr.mark_discipline_completed(disc, total_lessons=5)
        self.assertTrue(self.state_mgr.is_discipline_completed(disc))

        # Se a pasta for deletada, não deve mais considerar como completa
        shutil.rmtree(disc_folder)
        self.assertFalse(self.state_mgr.is_discipline_completed(disc))

    def test_bootstrap_from_disk(self):
        disc = "Contabilidade"
        disc_folder = os.path.join(self.test_dir, disc)
        lesson0 = os.path.join(disc_folder, "Aula_00")
        lesson1 = os.path.join(disc_folder, "Aula_01")
        os.makedirs(lesson0, exist_ok=True)
        os.makedirs(lesson1, exist_ok=True)

        # Cria PDFs válidos (> 1KB)
        with open(os.path.join(lesson0, "aula00.pdf"), "wb") as f:
            f.write(b"0" * 2000)
        with open(os.path.join(lesson1, "aula01.pdf"), "wb") as f:
            f.write(b"1" * 2000)

        lessons = [{"title": "Aula_00"}, {"title": "Aula_01"}]
        res = self.state_mgr.bootstrap_from_disk(disc, lessons)
        self.assertTrue(res)
        self.assertTrue(self.state_mgr.is_discipline_completed(disc))
        self.assertTrue(self.state_mgr.is_lesson_completed(disc, "Aula_00"))
        self.assertTrue(self.state_mgr.is_lesson_completed(disc, "Aula_01"))


if __name__ == "__main__":
    unittest.main()
