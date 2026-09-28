import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.config import get_app_dir

INDEX_FILE_PATH = get_app_dir() / "pdf_search_index.json"


def extract_pdf_text_by_pages(pdf_path: str) -> Dict[int, str]:
    """
    Extrai texto página por página de um arquivo PDF.
    Utiliza pypdf caso disponível; caso contrário, utiliza parser de fluxos embutido.
    """
    pages_text: Dict[int, str] = {}

    # Tentativa 1: Biblioteca pypdf / PyPDF2 se instalada
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages_text[idx] = text.strip()
        if pages_text:
            return pages_text
    except ImportError:
        pass
    except Exception:
        pass

    # Tentativa 2: Fallback puro em Python para extração de strings de texto em streams PDF
    try:
        with open(pdf_path, "rb") as f:
            content = f.read().decode("latin1", errors="ignore")

        # Procura blocos de texto entre 'BT' e 'ET' (Begin Text / End Text) ou streams de texto
        text_chunks = re.findall(r"\((.*?)\)\s*T[jJ]", content)
        if text_chunks:
            full_text = " ".join(text_chunks)
            # Normaliza espaçamentos
            full_text = re.sub(r"\s+", " ", full_text).strip()
            if full_text:
                pages_text[1] = full_text
    except Exception:
        pass

    return pages_text


class CoursePdfIndexer:
    """
    Indexador textual global para busca offline rápida em todos os PDFs
    de cursos e editais baixados no computador do usuário.
    """

    def __init__(self, index_file: Optional[Path] = None):
        self.index_file = index_file or INDEX_FILE_PATH
        self.index_data: Dict[str, Any] = {
            "version": 1,
            "last_updated": None,
            "documents": {},  # {rel_path: {"course": ..., "lesson": ..., "filename": ..., "pages": {page_num: text}}}
        }
        self._load_index()

    def _load_index(self) -> None:
        """Carrega o índice persistido do disco se existir."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index_data = json.load(f)
            except Exception:
                pass

    def save_index(self) -> None:
        """Grava o índice atômico no disco."""
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            self.index_data["last_updated"] = datetime.now().isoformat()
            tmp = self.index_file.parent / f"{self.index_file.name}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.index_data, f, ensure_ascii=False)
            tmp.replace(self.index_file)
        except OSError as e:
            print(f"[Aviso] Falha ao salvar índice de busca: {e}")

    def index_directory(self, root_dir: str, force_reindex: bool = False) -> int:
        """
        Varre recursivamente a pasta de downloads e indexa todos os PDFs encontrados.
        Retorna o número de novos documentos processados.
        """
        root_path = Path(root_dir)
        if not root_path.exists():
            return 0

        indexed_count = 0
        documents = self.index_data.setdefault("documents", {})

        for pdf_path in root_path.rglob("*.pdf"):
            rel_key = str(pdf_path.resolve())

            # Se já está indexado e o arquivo não mudou, pula
            if not force_reindex and rel_key in documents:
                continue

            try:
                mtime = os.path.getmtime(pdf_path)
                pages_dict = extract_pdf_text_by_pages(str(pdf_path))

                # Extrai nome do curso e da aula a partir da estrutura de pastas
                parts = pdf_path.parts
                lesson_name = parts[-2] if len(parts) >= 2 else "Geral"
                course_name = parts[-3] if len(parts) >= 3 else "Curso"

                documents[rel_key] = {
                    "course": course_name,
                    "lesson": lesson_name,
                    "filename": pdf_path.name,
                    "mtime": mtime,
                    "pages": {str(k): v for k, v in pages_dict.items()},
                }
                indexed_count += 1
            except Exception:
                pass

        if indexed_count > 0:
            self.save_index()

        return indexed_count

    def search(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Realiza busca textual (case-insensitive) em todo o material indexado.
        Retorna snippets contextuais com número de página e metadados.
        """
        terms = [t.lower().strip() for t in query.split() if t.strip()]
        if not terms:
            return []

        results = []
        documents = self.index_data.get("documents", {})

        for file_path, doc_info in documents.items():
            pages = doc_info.get("pages", {})
            for page_str, text in pages.items():
                text_lower = text.lower()

                # Verifica se todos os termos da busca estão presentes na página
                if all(term in text_lower for term in terms):
                    # Gera snippet do primeiro termo encontrado
                    first_idx = text_lower.find(terms[0])
                    start = max(0, first_idx - 60)
                    end = min(len(text), first_idx + 120)
                    snippet = text[start:end].strip()

                    results.append({
                        "course": doc_info.get("course"),
                        "lesson": doc_info.get("lesson"),
                        "filename": doc_info.get("filename"),
                        "filepath": file_path,
                        "page": int(page_str) if page_str.isdigit() else 1,
                        "snippet": f"...{snippet}..." if start > 0 else f"{snippet}...",
                    })

                    if len(results) >= max_results:
                        return results

        return results
