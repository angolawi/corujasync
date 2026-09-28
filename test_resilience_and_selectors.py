import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from core.selector_manager import SelectorManager
from core.api_extractor import (
    get_next_data,
    extract_lessons_from_state,
    extract_materials_from_page_source,
    extract_auth_tokens,
)
from core.crawler import get_lesson_data
from core.processor import download_lesson_materials


class TestSelectorManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bundled_json = Path(self.test_dir) / "test_bundled.json"
        self.cache_json = Path(self.test_dir) / "test_cache.json"

        # Cria arquivo base bundled de teste
        base_data = {
            "version": 1,
            "selectors": {
                "test_key": [
                    {"by": "css", "value": "div.primary"},
                    {"by": "xpath", "value": "//div[@class='fallback']"},
                ],
                "template_key": [
                    {"by": "xpath", "value": "//button[text()='{label}']"}
                ],
            },
        }
        with open(self.bundled_json, "w", encoding="utf-8") as f:
            json.dump(base_data, f)

        self.sm = SelectorManager(
            bundled_file=self.bundled_json,
            cache_file=self.cache_json,
            remote_url="https://mock.url/selectors.json",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initialization_loads_bundled(self):
        self.assertEqual(self.sm.version, 1)
        candidates = self.sm.get_candidates("test_key")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0], (By.CSS_SELECTOR, "div.primary"))
        self.assertEqual(candidates[1], (By.XPATH, "//div[@class='fallback']"))

    def test_template_formatting(self):
        candidates = self.sm.get_candidates("template_key", label="Clique Aqui")
        self.assertEqual(candidates[0], (By.XPATH, "//button[text()='Clique Aqui']"))

    def test_find_elements_fallback_chain(self):
        mock_driver = MagicMock()
        mock_elem = MagicMock()

        # Primeiro seletor (primary) retorna lista vazia
        # Segundo seletor (fallback) retorna [mock_elem]
        mock_driver.find_elements.side_effect = [
            [],
            [mock_elem],
        ]

        found = self.sm.find_elements(mock_driver, "test_key")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], mock_elem)
        self.assertEqual(mock_driver.find_elements.call_count, 2)

    def test_find_element_first_match(self):
        mock_driver = MagicMock()
        mock_elem = MagicMock()

        mock_driver.find_element.return_value = mock_elem

        elem = self.sm.find_element(mock_driver, "test_key")
        self.assertEqual(elem, mock_elem)
        # Como o primeiro casou, não deve chamar o segundo
        self.assertEqual(mock_driver.find_element.call_count, 1)

    def test_update_from_dict_and_cache_saving(self):
        new_payload = {
            "version": 2,
            "selectors": {
                "test_key": [{"by": "css", "value": "div.new-layout"}],
                "added_key": [{"by": "id", "value": "new-id"}],
            },
        }

        updated = self.sm.update_from_dict(new_payload, save_cache=True)
        self.assertTrue(updated)
        self.assertEqual(self.sm.version, 2)
        self.assertTrue(self.cache_json.exists())

        # Verifica se nova instância lê o cache v2 automaticamente
        sm2 = SelectorManager(
            bundled_file=self.bundled_json,
            cache_file=self.cache_json,
        )
        self.assertEqual(sm2.version, 2)
        self.assertEqual(sm2.get_candidates("added_key")[0], (By.ID, "new-id"))

    @patch("requests.get")
    def test_ota_fetch_remote_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "version": 3,
            "selectors": {
                "test_key": [{"by": "css", "value": "div.ota-updated"}],
            },
        }
        mock_requests_get.return_value = mock_response

        # Força atualização remota
        success = self.sm.fetch_remote(force=True)
        self.assertTrue(success)
        self.assertEqual(self.sm.version, 3)

        candidates = self.sm.get_candidates("test_key")
        self.assertEqual(candidates[0], (By.CSS_SELECTOR, "div.ota-updated"))


class TestApiExtractor(unittest.TestCase):

    def test_get_next_data_from_window(self):
        mock_driver = MagicMock()
        fake_payload = {"props": {"pageProps": {"course": {"name": "Auditor Fiscal"}}}}
        mock_driver.execute_script.return_value = fake_payload

        data = get_next_data(mock_driver)
        self.assertEqual(data, fake_payload)

    def test_extract_lessons_from_state(self):
        mock_driver = MagicMock()
        fake_state = {
            "props": {
                "pageProps": {
                    "lessons": [
                        {"id": "101", "title": "Aula 00 - Conceitos", "subtitle": "Origens do Direito", "url": "/aula/101"},
                        {"id": "102", "title": "Aula 01 - Princípios", "subtitle": "Legalidade e Moralidade", "url": "/aula/102"},
                    ]
                }
            }
        }
        mock_driver.execute_script.return_value = fake_state

        lessons = extract_lessons_from_state(mock_driver, "https://www.estrategiaconcursos.com.br/app/dashboard/cursos/10/aulas")
        self.assertIsNotNone(lessons)
        self.assertEqual(len(lessons), 2)
        self.assertEqual(lessons[0]["title"], "Aula 00 - Conceitos")
        self.assertEqual(lessons[0]["url"], "https://www.estrategiaconcursos.com.br/aula/101")
        self.assertEqual(lessons[1]["title"], "Aula 01 - Princípios")

    def test_extract_materials_from_page_source_fallback(self):
        html_content = """
        <html>
            <body>
                <a href="https://api.estrategiaconcursos.com.br/download/pdf/12345?token=abc">Download</a>
                <a href="https://api.estrategiaconcursos.com.br/download/pdf/12345?token=abc">Duplicado</a>
                <video src="https://cdn.estrategia.com/video_720p.mp4"></video>
            </body>
        </html>
        """
        extracted = extract_materials_from_page_source(html_content)
        self.assertEqual(len(extracted["pdfs"]), 1)
        self.assertIn("https://api.estrategiaconcursos.com.br/download/pdf/12345?token=abc", extracted["pdfs"])
        self.assertEqual(len(extracted["videos"]), 1)
        self.assertIn("https://cdn.estrategia.com/video_720p.mp4", extracted["videos"])

    def test_extract_auth_tokens(self):
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = {
            "user_token": "bearer-xyz",
            "jwt_session": "jwt-token-123",
        }
        tokens = extract_auth_tokens(mock_driver)
        self.assertEqual(tokens["user_token"], "bearer-xyz")
        self.assertEqual(tokens["jwt_session"], "jwt-token-123")


class TestCrawlerAndProcessorResilience(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.driver = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("core.crawler.extract_lessons_from_state")
    def test_get_lesson_data_uses_state_extraction_first(self, mock_state_extractor):
        mock_state_extractor.return_value = [
            {"title": "Aula 00", "subtitle": "Introdução", "url": "https://example.com/00"}
        ]

        lessons = get_lesson_data(self.driver, "https://example.com/curso/1/aulas")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["title"], "Aula 00")
        # Se extraiu do estado, não deve ter precisado varrer o DOM
        self.driver.find_elements.assert_not_called()

    @patch("core.processor.download_file")
    def test_download_lesson_materials_html_regex_fallback(self, mock_download):
        mock_download.return_value = True

        # Simula DOM sem nenhum a.LessonButton
        self.driver.find_elements.return_value = []
        # Mas page_source contém URL de download da API
        self.driver.page_source = (
            '<div><a href="https://api.estrategiaconcursos.com.br/api/download/livro_123.pdf">PDF</a></div>'
        )

        lesson_info = {"title": "Aula 01", "subtitle": "", "url": "https://example.com/aula1"}

        success = download_lesson_materials(
            driver=self.driver,
            lesson_info=lesson_info,
            course_title="Contabilidade",
            download_dir=self.test_dir,
            http_session=MagicMock(),
        )

        self.assertTrue(success)
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        self.assertIn("api.estrategiaconcursos.com.br", call_kwargs["url"])


if __name__ == "__main__":
    unittest.main()
