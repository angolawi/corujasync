import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.diagnostics import sanitize_sensitive_data, DiagnosticsStore
from legal.license_manager import (
    get_machine_id,
    generate_license_key,
    validate_license_key,
    LicenseManager,
)
from core.watcher import CourseWatcher
from core.indexer import CoursePdfIndexer, extract_pdf_text_by_pages


class TestDiagnostics(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.store = DiagnosticsStore()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sanitize_sensitive_data_cpf_email_tokens(self):
        raw_text = (
            "Erro do usuario joao.silva@gmail.com com CPF 123.456.789-00 "
            "ao autenticar token='abc123secrettokenxyz' no portal."
        )
        sanitized = sanitize_sensitive_data(raw_text)

        self.assertNotIn("123.456.789-00", sanitized)
        self.assertIn("***.***.***-**", sanitized)

        self.assertNotIn("joao.silva@gmail.com", sanitized)
        self.assertIn("j***@gmail.com", sanitized)

        self.assertNotIn("abc123secrettokenxyz", sanitized)
        self.assertIn("token=***REDACTED***", sanitized)

    def test_record_failure_and_export_report(self):
        mock_driver = MagicMock()
        mock_driver.current_url = "https://www.estrategiaconcursos.com.br/app/dashboard/cursos/10/aulas"
        mock_driver.title = "Direito Constitucional"
        mock_driver.page_source = "<html><body><h1>Aula 01</h1><button class='btn'>Download</button></body></html>"

        mock_btn = MagicMock()
        mock_btn.text = "Download"
        mock_btn.tag_name = "button"
        mock_btn.get_attribute.return_value = "btn"

        mock_h1 = MagicMock()
        mock_h1.text = "Aula 01"

        mock_driver.find_elements.side_effect = [
            [mock_btn],  # buttons
            [],          # links
            [mock_h1],   # headings
        ]

        snapshot = self.store.record_failure(
            driver=mock_driver,
            expected_action="localizar_pdf",
            expected_selector="a.LessonButton",
            error_message="Elemento não encontrado",
        )

        self.assertEqual(snapshot["expected_action"], "localizar_pdf")
        self.assertEqual(snapshot["expected_selector"], "a.LessonButton")
        self.assertEqual(snapshot["page_title"], "Direito Constitucional")

        # Exporta arquivo de diagnóstico
        report_path = Path(self.test_dir) / "diag.json"
        exported = self.store.export_report_file(str(report_path))
        self.assertTrue(os.path.exists(exported))

        with open(exported, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("environment", data)
        self.assertIn("last_failure", data)
        self.assertEqual(data["last_failure"]["expected_action"], "localizar_pdf")


class TestLicensingSystem(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / "config.json"
        self.patch_config = patch("core.config.CONFIG_FILE_PATH", self.config_path)
        self.patch_config.start()

    def tearDown(self):
        self.patch_config.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_machine_id_deterministic(self):
        mid1 = get_machine_id()
        mid2 = get_machine_id()
        self.assertEqual(mid1, mid2)
        self.assertEqual(len(mid1.split("-")), 4)

    def test_generate_and_validate_annual_license(self):
        key = generate_license_key(
            client_id="estudante@concursos.com",
            tier="anual",
            machine_id="ANY",
            days_valid=365,
        )

        is_valid, msg, payload = validate_license_key(key)
        self.assertTrue(is_valid)
        self.assertEqual(payload["client"], "estudante@concursos.com")
        self.assertEqual(payload["tier"], "anual")

    def test_tampered_license_rejected(self):
        key = generate_license_key(
            client_id="aluno@teste.com",
            tier="vitalicio",
            machine_id="ANY",
        )
        # Altera um caractere da assinatura ou payload
        parts = key.split("-")
        tampered_sig = ("0" if parts[3][0] != "0" else "1") + parts[3][1:]
        tampered_key = f"{parts[0]}-{parts[1]}-{parts[2]}-{tampered_sig}"

        is_valid, msg, _ = validate_license_key(tampered_key)
        self.assertFalse(is_valid)
        self.assertIn("inválida", msg.lower())

    def test_expired_license_rejected(self):
        # Gera chave expirada (dias negativos)
        key = generate_license_key(
            client_id="expirado@teste.com",
            tier="anual",
            days_valid=-5,
        )
        is_valid, msg, _ = validate_license_key(key)
        self.assertFalse(is_valid)
        self.assertIn("expirou", msg.lower())

    def test_machine_id_lock_enforcement(self):
        current_machine = get_machine_id()
        # Chave travada em outra máquina
        foreign_machine = "AAAA-BBBB-CCCC-DDDD"

        locked_key = generate_license_key(
            client_id="trava@teste.com",
            tier="pro",
            machine_id=foreign_machine,
        )

        is_valid, msg, _ = validate_license_key(locked_key, enforce_machine=True)
        self.assertFalse(is_valid)
        self.assertIn("vinculada ao computador", msg.lower())

        # Chave travada nesta máquina deve ser aceita
        local_key = generate_license_key(
            client_id="trava@teste.com",
            tier="pro",
            machine_id=current_machine,
        )
        is_valid, msg, _ = validate_license_key(local_key, enforce_machine=True)
        self.assertTrue(is_valid)

    def test_license_manager_activate_flow(self):
        lm = LicenseManager()
        self.assertFalse(lm.is_premium())

        valid_key = generate_license_key("cliente@vip.com", tier="vitalicio", machine_id="ANY")
        success, msg = lm.activate(valid_key)

        self.assertTrue(success)
        self.assertTrue(lm.is_premium())

        status = lm.get_status()
        self.assertEqual(status["client"], "cliente@vip.com")
        self.assertEqual(status["tier"], "vitalicio")

        lm.deactivate()
        self.assertFalse(lm.is_premium())


class TestWatcherAndIndexer(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("core.watcher.download_lesson_materials")
    @patch("core.watcher.get_lesson_data")
    def test_course_watcher_detects_new_lessons(self, mock_get_lessons, mock_download):
        mock_download.return_value = True
        mock_driver = MagicMock()
        mock_session = MagicMock()

        watcher = CourseWatcher(
            driver_factory=lambda: mock_driver,
            http_session_factory=lambda: mock_session,
        )

        mock_get_lessons.return_value = [
            {"title": "Aula 00", "subtitle": "Intro", "url": "https://example.com/00"},
            {"title": "Aula 01", "subtitle": "Nova Matéria", "url": "https://example.com/01"},
        ]

        # Simula que Aula 00 já foi baixada anteriormente e pasta existe no disco
        from core.state_manager import DownloadStateManager
        from core.downloader import sanitize_filename
        aula00_path = os.path.join(
            self.test_dir,
            sanitize_filename("Direito Constitucional"),
            sanitize_filename("Aula 00"),
        )
        os.makedirs(aula00_path, exist_ok=True)
        sm = DownloadStateManager(self.test_dir, sanitize_func=sanitize_filename)
        sm.mark_lesson_completed("Direito Constitucional", "Aula 00", ["aula00.pdf"])

        updates = watcher.check_course_updates(
            driver=mock_driver,
            course_url="https://example.com/curso",
            course_title="Direito Constitucional",
            download_dir=self.test_dir,
            http_session=mock_session,
            auto_download=True,
        )

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["title"], "Aula 01")
        mock_download.assert_called_once()

    def test_pdf_indexer_and_search(self):
        # Cria estrutura de pastas e arquivo PDF simulado
        course_folder = Path(self.test_dir) / "Direito_Administrativo" / "Aula_01"
        course_folder.mkdir(parents=True, exist_ok=True)
        pdf_file = course_folder / "Aula_01_Livro_Eletronico.pdf"

        # Simula stream PDF com conteúdo textual em formato padrão de texto
        pdf_content = b"%PDF-1.4\nBT\n(Principio da Legalidade e Moralidade na Administracao Publica) Tj\nET\n%%EOF"
        with open(pdf_file, "wb") as f:
            f.write(pdf_content)

        index_file = Path(self.test_dir) / "test_index.json"
        indexer = CoursePdfIndexer(index_file=index_file)

        indexed = indexer.index_directory(self.test_dir)
        self.assertEqual(indexed, 1)

        # Busca por palavra existente
        results = indexer.search("Legalidade Moralidade")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lesson"], "Aula_01")
        self.assertIn("Legalidade", results[0]["snippet"])

        # Busca por palavra inexistente
        no_results = indexer.search("Direito Tributario Inexistente")
        self.assertEqual(len(no_results), 0)


if __name__ == "__main__":
    unittest.main()
