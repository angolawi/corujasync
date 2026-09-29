import os
import tempfile
import unittest
from pathlib import Path

from core.indexer import CoursePdfIndexer, remove_accents, find_subjects_file


class TestCoursePdfIndexer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.index_file = self.root_path / "test_index.json"
        self.indexer = CoursePdfIndexer(index_file=self.index_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_remove_accents(self):
        self.assertEqual(remove_accents("Constituição Federal"), "constituicao federal")
        self.assertEqual(remove_accents("Língua Portuguesa e Acentuação Gráfica"), "lingua portuguesa e acentuacao grafica")
        self.assertEqual(remove_accents("Jurisprudência & Licitações"), "jurisprudencia & licitacoes")
        self.assertEqual(remove_accents(""), "")
        self.assertEqual(remove_accents(None), "")

    def test_find_subjects_file(self):
        lesson_dir = self.root_path / "Aula_01"
        lesson_dir.mkdir()
        self.assertIsNone(find_subjects_file(lesson_dir))

        subj_file = lesson_dir / "Assuntos_dessa_aula.txt"
        subj_file.write_text("Conceito de Constituição e Poder Constituinte", encoding="utf-8")
        found = find_subjects_file(lesson_dir)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Assuntos_dessa_aula.txt")

    def test_index_directory_and_search(self):
        # Cria estrutura de curso simulada
        course_dir = self.root_path / "Direito Constitucional"
        aula1_dir = course_dir / "Aula 00 - Conceito e Classificacao"
        aula1_dir.mkdir(parents=True)
        (aula1_dir / "Assuntos_dessa_aula.txt").write_text(
            "Conceito de Constituição. Classificação das Constituições. Poder Constituinte Originário e Derivado.",
            encoding="utf-8"
        )
        pdf1 = aula1_dir / "Aula 00 - Livro Original.pdf"
        pdf1.write_bytes(b"%PDF-1.4 simulated pdf")

        aula2_dir = course_dir / "Aula 01 - Direitos e Garantias Fundamentais"
        aula2_dir.mkdir(parents=True)
        (aula2_dir / "Assuntos_dessa_aula.txt").write_text(
            "Artigo 5º da CF/88. Remédios Constitucionais: Habeas Corpus, Mandado de Segurança.",
            encoding="utf-8"
        )

        # Indexa diretório
        count = self.indexer.index_directory(str(self.root_path))
        self.assertEqual(count, 2)
        self.assertEqual(len(self.indexer.index_data["lessons"]), 2)

        # 1. Busca sem acento para termo acentuado no texto ("constituinte" -> "Poder Constituinte")
        res1 = self.indexer.search("constituinte")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["lesson"], "Aula 00 - Conceito e Classificacao")
        self.assertEqual(res1[0]["course"], "Direito Constitucional")
        self.assertEqual(res1[0]["source"], "subjects")
        self.assertIn("Constituinte", res1[0]["snippet"])
        self.assertEqual(res1[0]["filepath"], str(pdf1.resolve()))

        # 2. Busca com acento ("remédios")
        res2 = self.indexer.search("remédios")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["lesson"], "Aula 01 - Direitos e Garantias Fundamentais")
        self.assertIn("Habeas Corpus", res2[0]["snippet"])

        # 3. Busca por termos no nome do curso e da aula
        res3 = self.indexer.search("Direito Constitucional")
        self.assertEqual(len(res3), 2)

        # 4. Busca por termo inexistente
        res4 = self.indexer.search("TermoCompletamenteInexistente")
        self.assertEqual(len(res4), 0)

    def test_concurso_hierarchy_and_filtering(self):
        # Cria estrutura com 2 Concursos distintos
        concurso1_dir = self.root_path / "Camara_dos_Deputados_Pacote"
        concurso2_dir = self.root_path / "Receita_Federal_Pacote"

        disc1 = concurso1_dir / "Direito_Constitucional" / "Aula_01"
        disc1.mkdir(parents=True)
        (disc1 / "Assuntos_dessa_aula.txt").write_text("Processo Legislativo e Emendas à Constituição", encoding="utf-8")

        disc2 = concurso2_dir / "Direito_Tributario" / "Aula_01"
        disc2.mkdir(parents=True)
        (disc2 / "Assuntos_dessa_aula.txt").write_text("Competência Tributária e Limitações ao Poder de Tributar", encoding="utf-8")

        self.indexer.index_directory(str(self.root_path), force_reindex=True)

        concursos = self.indexer.get_concursos()
        self.assertIn("Camara_dos_Deputados_Pacote", concursos)
        self.assertIn("Receita_Federal_Pacote", concursos)

        # Busca filtrada por concurso específico
        res_camara = self.indexer.search("Constituição", concurso="Camara_dos_Deputados_Pacote")
        self.assertEqual(len(res_camara), 1)
        self.assertEqual(res_camara[0]["concurso"], "Camara_dos_Deputados_Pacote")

        res_receita = self.indexer.search("Constituição", concurso="Receita_Federal_Pacote")
        self.assertEqual(len(res_receita), 0)

        # Busca global (sem filtro) encontra
        res_global = self.indexer.search("Constituição", concurso="Todos os Concursos")
        self.assertEqual(len(res_global), 1)


if __name__ == "__main__":
    unittest.main()
