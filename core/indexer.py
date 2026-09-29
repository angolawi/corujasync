import os
import re
import json
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.config import get_app_dir

INDEX_FILE_PATH = get_app_dir() / "pdf_search_index.json"


def remove_accents(input_str: str) -> str:
    """Normaliza texto removendo acentos e diacríticos para buscas flexíveis."""
    if not input_str:
        return ""
    nfkd = unicodedata.normalize("NFKD", input_str)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def find_subjects_file(lesson_dir: Path) -> Optional[Path]:
    """
    Localiza o arquivo descritor de assuntos da aula (Assuntos_dessa_aula.txt ou variantes).
    """
    if not lesson_dir.is_dir():
        return None

    # 1. Procura direta pelos nomes mais comuns
    common_names = [
        "assuntos_dessa_aula.txt",
        "assunto.txt",
        "assuntos.txt",
        "ementa.txt",
    ]
    for item in lesson_dir.iterdir():
        if item.is_file():
            name_lower = item.name.lower()
            if name_lower in common_names or "[ementa]" in name_lower or "ementa" in name_lower:
                return item

    return None


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

    # Tentativa 2: Fallback rápido apenas para arquivos pequenos (< 2MB)
    try:
        if os.path.getsize(pdf_path) < 2 * 1024 * 1024:
            with open(pdf_path, "rb") as f:
                content = f.read(500_000).decode("latin1", errors="ignore")
            text_chunks = re.findall(r"\((.*?)\)\s*T[jJ]", content)
            if text_chunks:
                full_text = " ".join(text_chunks)
                full_text = re.sub(r"\s+", " ", full_text).strip()
                if full_text:
                    pages_text[1] = full_text
    except Exception:
        pass

    return pages_text


class CoursePdfIndexer:
    """
    Indexador textual global e base de conhecimento offline para busca rápida em
    todas as aulas, livros eletrônicos e assuntos baixados no computador do aluno.
    Utiliza os arquivos 'Assuntos_dessa_aula.txt' e os PDFs para busca instantânea.
    """

    def __init__(self, index_file: Optional[Path] = None):
        self.index_file = index_file or INDEX_FILE_PATH
        self.index_data: Dict[str, Any] = {
            "version": 2,
            "last_updated": None,
            "lessons": {},    # {lesson_dir: {"course": ..., "lesson": ..., "subjects": ..., "primary_pdf": ..., ...}}
            "documents": {},  # {rel_path: {"course": ..., "lesson": ..., "filename": ..., "pages": ...}}
        }
        self._load_index()

    def _load_index(self) -> None:
        """Carrega o índice persistido do disco se existir."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.index_data["version"] = data.get("version", 2)
                        self.index_data["last_updated"] = data.get("last_updated")
                        self.index_data["lessons"] = data.get("lessons", {})
                        self.index_data["documents"] = data.get("documents", {})
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
        Varre recursivamente a pasta de downloads e indexa:
        1. Os arquivos 'Assuntos_dessa_aula.txt' com o conteúdo programático de cada aula.
        2. Os livros eletrônicos e PDFs associados.
        Retorna o total de itens indexados/atualizados.
        """
        root_path = Path(root_dir)
        if not root_path.exists():
            return 0

        indexed_count = 0
        lessons = self.index_data.setdefault("lessons", {})
        documents = self.index_data.setdefault("documents", {})

        # Varre todas as pastas que contenham arquivos ou subpastas
        for dirpath, dirnames, filenames in os.walk(str(root_path)):
            current_dir = Path(dirpath)
            
            # Se for a raiz ou diretórios ocultos, pula
            if current_dir.name.startswith("."):
                continue

            has_txt = any(
                f.lower() in ["assuntos_dessa_aula.txt", "assunto.txt"] or "[ementa]" in f.lower() or "ementa" in f.lower()
                for f in filenames
            )
            has_pdf = any(f.lower().endswith(".pdf") for f in filenames)

            # Se a pasta contém arquivos de aula (assunto ou pdf)
            if has_txt or has_pdf:
                dir_key = str(current_dir.resolve())

                # Lê os assuntos da aula se existir
                subjects_text = ""
                subj_file = find_subjects_file(current_dir)
                if subj_file and subj_file.exists():
                    try:
                        subjects_text = subj_file.read_text(encoding="utf-8", errors="ignore").strip()
                    except Exception:
                        pass

                # Identifica nome do concurso, curso e aula a partir da hierarquia de pastas
                try:
                    rel_parts = current_dir.relative_to(root_path).parts
                except ValueError:
                    rel_parts = current_dir.parts

                if len(rel_parts) >= 3:
                    concurso_name = rel_parts[0]
                    course_name = rel_parts[1]
                    lesson_name = rel_parts[-1]
                elif len(rel_parts) == 2:
                    concurso_name = "Cursos Gerais"
                    course_name = rel_parts[0]
                    lesson_name = rel_parts[1]
                elif len(rel_parts) == 1:
                    concurso_name = "Cursos Gerais"
                    course_name = rel_parts[0]
                    lesson_name = rel_parts[0]
                else:
                    concurso_name = "Cursos Gerais"
                    course_name = "Curso"
                    lesson_name = "Aula"

                # Identifica todos os PDFs e elege o livro eletrônico principal
                pdf_files = [f for f in filenames if f.lower().endswith(".pdf")]
                primary_pdf_path = None
                for pdf_name in pdf_files:
                    if "original" in pdf_name.lower():
                        primary_pdf_path = str((current_dir / pdf_name).resolve())
                        break
                if not primary_pdf_path and pdf_files:
                    primary_pdf_path = str((current_dir / pdf_files[0]).resolve())

                # Registra a aula no catálogo
                if force_reindex or dir_key not in lessons or not lessons[dir_key].get("subjects"):
                    lessons[dir_key] = {
                        "concurso": concurso_name,
                        "course": course_name,
                        "lesson": lesson_name,
                        "subjects": subjects_text,
                        "primary_pdf": primary_pdf_path,
                        "lesson_path": dir_key,
                        "files": pdf_files,
                        "mtime": os.path.getmtime(current_dir),
                    }
                    indexed_count += 1

                # Indexa os PDFs individuais em 'documents' para retrocompatibilidade
                for pdf_name in pdf_files:
                    pdf_full_path = current_dir / pdf_name
                    doc_key = str(pdf_full_path.resolve())

                    if force_reindex or doc_key not in documents:
                        try:
                            # Se a aula não possui arquivo de assuntos, tenta extração de texto do PDF
                            pages_dict = {}
                            if not subjects_text:
                                pages_dict = extract_pdf_text_by_pages(str(pdf_full_path))

                            documents[doc_key] = {
                                "concurso": concurso_name,
                                "course": course_name,
                                "lesson": lesson_name,
                                "filename": pdf_name,
                                "mtime": os.path.getmtime(pdf_full_path),
                                "pages": {str(k): v for k, v in pages_dict.items()},
                            }
                        except Exception:
                            pass

        if indexed_count > 0 or force_reindex:
            self.save_index()

        return indexed_count

    def get_concursos(self) -> List[str]:
        """Retorna a lista de nomes de concursos únicos presentes na base de conhecimento."""
        concursos = set()
        for info in self.index_data.get("lessons", {}).values():
            c = info.get("concurso")
            if c:
                concursos.add(c)
        for doc in self.index_data.get("documents", {}).values():
            c = doc.get("concurso")
            if c:
                concursos.add(c)
        return sorted(list(concursos))

    def search(
        self,
        query: str,
        concurso: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Realiza busca textual inteligente em toda a biblioteca indexada.
        Permite filtrar por um concurso específico ou buscar globalmente.
        Busca termos nos assuntos da aula (Assuntos_dessa_aula.txt), no nome do concurso,
        no nome da disciplina/curso, no título da aula e no conteúdo interno dos PDFs.
        """
        raw_terms = [t.strip() for t in query.split() if t.strip()]
        if not raw_terms:
            return []

        norm_terms = [remove_accents(t) for t in raw_terms]
        results: List[Dict[str, Any]] = []
        seen_keys = set()

        # Normaliza filtro de concurso se informado
        norm_filter_concurso = None
        if concurso and concurso not in ["Todos", "Todos os Concursos", ""]:
            norm_filter_concurso = remove_accents(concurso)

        lessons = self.index_data.get("lessons", {})
        documents = self.index_data.get("documents", {})

        # -------------------------------------------------------------------
        # 1. Busca de Alta Relevância: Base de Assuntos das Aulas
        # -------------------------------------------------------------------
        for lesson_key, info in lessons.items():
            item_concurso = info.get("concurso", "Concurso")
            if norm_filter_concurso and norm_filter_concurso != remove_accents(item_concurso):
                continue

            subjects = info.get("subjects", "")
            lesson_title = info.get("lesson", "")
            course_title = info.get("course", "")

            # Constrói texto unificado normalizado para busca
            searchable_blob = f"{item_concurso} {subjects} {lesson_title} {course_title}"
            norm_blob = remove_accents(searchable_blob)

            # Verifica se todos os termos aparecem na aula
            if all(term in norm_blob for term in norm_terms):
                # Extrai snippet dos assuntos ou título
                snippet = subjects if subjects else f"Aula: {lesson_title}"
                # Formata snippet destacando contexto
                if len(snippet) > 220:
                    first_idx = remove_accents(snippet).find(norm_terms[0])
                    if first_idx != -1:
                        start = max(0, first_idx - 40)
                        end = min(len(snippet), first_idx + 140)
                        snippet = f"...{snippet[start:end]}..."
                    else:
                        snippet = snippet[:200] + "..."

                primary_pdf = info.get("primary_pdf")
                pdf_name = Path(primary_pdf).name if primary_pdf else None

                results.append({
                    "concurso": item_concurso,
                    "course": course_title,
                    "lesson": lesson_title,
                    "filename": pdf_name or "Assuntos_dessa_aula.txt",
                    "filepath": primary_pdf or lesson_key,
                    "lesson_path": lesson_key,
                    "subjects": subjects,
                    "page": 1,
                    "snippet": snippet,
                    "source": "subjects",
                })
                seen_keys.add(lesson_key)

                if len(results) >= max_results:
                    return results

        # -------------------------------------------------------------------
        # 2. Busca Complementar: Conteúdo interno textual dos PDFs
        # -------------------------------------------------------------------
        for file_path, doc_info in documents.items():
            lesson_dir = str(Path(file_path).parent.resolve())
            if lesson_dir in seen_keys:
                continue

            item_concurso = doc_info.get("concurso", "Concurso")
            if norm_filter_concurso and norm_filter_concurso != remove_accents(item_concurso):
                continue

            pages = doc_info.get("pages", {})
            for page_str, text in pages.items():
                norm_page_text = remove_accents(text)
                if all(term in norm_page_text for term in norm_terms):
                    first_idx = norm_page_text.find(norm_terms[0])
                    start = max(0, first_idx - 50)
                    end = min(len(text), first_idx + 120)
                    snippet = text[start:end].strip()

                    results.append({
                        "concurso": item_concurso,
                        "course": doc_info.get("course"),
                        "lesson": doc_info.get("lesson"),
                        "filename": doc_info.get("filename"),
                        "filepath": file_path,
                        "lesson_path": lesson_dir,
                        "subjects": "",
                        "page": int(page_str) if page_str.isdigit() else 1,
                        "snippet": f"...{snippet}..." if start > 0 else f"{snippet}...",
                        "source": "pdf",
                    })
                    seen_keys.add(lesson_dir)

                    if len(results) >= max_results:
                        return results

        return results
