import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional


STATE_FILENAME = ".download_state.json"


def _now_iso() -> str:
    return datetime.now().isoformat()


class DownloadStateManager:
    """
    Gerencia a persistência do progresso de downloads em um arquivo JSON local.
    Permite pular disciplinas e aulas já finalizadas sem sobrecarregar o Selenium.
    """

    def __init__(self, target_dir: str, sanitize_func=None):
        self.target_dir = os.path.abspath(target_dir)
        self.state_file_path = os.path.join(self.target_dir, STATE_FILENAME)
        self.sanitize_func = sanitize_func or (lambda s: s)
        self.state: Dict[str, Any] = {
            "version": 1,
            "target_dir": self.target_dir,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "disciplines": {},
        }
        self.load_state()

    def load_state(self) -> None:
        """Carrega o estado existente do disco se houver."""
        if not os.path.exists(self.state_file_path):
            return

        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "disciplines" in data:
                    self.state = data
        except (json.JSONDecodeError, OSError):
            # Em caso de leitura corrompida, mantém o estado padrão mas faz backup do arquivo
            backup_path = f"{self.state_file_path}.corrupt_{int(time.time())}"
            try:
                os.rename(self.state_file_path, backup_path)
            except OSError:
                pass

    def save_state(self) -> None:
        """Salva o estado de forma atômica no arquivo JSON."""
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            self.state["updated_at"] = _now_iso()
            tmp_path = f"{self.state_file_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.state_file_path)
        except OSError as e:
            print(f"[Aviso] Falha ao salvar estado de download: {e}")

    def _get_discipline_key(self, discipline_title: str) -> str:
        return self.sanitize_func(discipline_title)

    def is_discipline_completed(self, discipline_title: str, check_videos: bool = False) -> bool:
        """
        Verifica se a disciplina já foi completamente baixada e se sua pasta existe.
        Se check_videos=True, verifica também se os vídeos foram baixados.
        """
        key = self._get_discipline_key(discipline_title)
        disc_data = self.state.get("disciplines", {}).get(key)
        if not disc_data:
            return False

        if disc_data.get("status") != "completed":
            return False

        if check_videos and not disc_data.get("videos_completed", False):
            return False

        disc_path = os.path.join(self.target_dir, key)
        if not os.path.isdir(disc_path):
            return False

        return True

    def is_lesson_completed(self, discipline_title: str, lesson_title: str, check_videos: bool = False) -> bool:
        """
        Verifica se uma aula específica já foi baixada com sucesso e se sua pasta existe.
        Se check_videos=True, verifica se os vídeos da aula também foram baixados ou verificados.
        """
        key = self._get_discipline_key(discipline_title)
        disc_data = self.state.get("disciplines", {}).get(key)
        if not disc_data:
            return False

        lesson_key = self.sanitize_func(lesson_title)
        lessons = disc_data.get("lessons", {})
        lesson_data = lessons.get(lesson_key)
        if not lesson_data:
            return False

        if lesson_data.get("status") != "completed":
            return False

        if check_videos and not lesson_data.get("videos_completed", False):
            return False

        lesson_path = os.path.join(self.target_dir, key, lesson_key)
        if not os.path.isdir(lesson_path):
            return False

        return True

    def mark_lesson_completed(
        self,
        discipline_title: str,
        lesson_title: str,
        files: Optional[List[str]] = None,
        videos_completed: bool = False,
    ) -> None:
        """Marca uma aula individual como concluída e persiste no disco."""
        disc_key = self._get_discipline_key(discipline_title)
        lesson_key = self.sanitize_func(lesson_title)

        disciplines = self.state.setdefault("disciplines", {})
        disc_data = disciplines.setdefault(
            disc_key,
            {
                "title": discipline_title,
                "status": "in_progress",
                "lessons": {},
                "created_at": _now_iso(),
            },
        )

        lessons = disc_data.setdefault("lessons", {})
        existing_lesson = lessons.setdefault(lesson_key, {})
        existing_files = set(existing_lesson.get("files", []))
        if files:
            existing_files.update(files)

        lessons[lesson_key] = {
            "title": lesson_title,
            "status": "completed",
            "files": sorted(list(existing_files)),
            "videos_completed": videos_completed or existing_lesson.get("videos_completed", False),
            "completed_at": _now_iso(),
        }

        self.save_state()

    def mark_discipline_completed(
        self, discipline_title: str, total_lessons: int = 0, videos_completed: bool = False
    ) -> None:
        """Marca a disciplina inteira como concluída."""
        disc_key = self._get_discipline_key(discipline_title)
        disciplines = self.state.setdefault("disciplines", {})
        disc_data = disciplines.setdefault(
            disc_key,
            {
                "title": discipline_title,
                "created_at": _now_iso(),
            },
        )

        disc_data["status"] = "completed"
        disc_data["completed_at"] = _now_iso()
        if videos_completed:
            disc_data["videos_completed"] = True
        if total_lessons > 0:
            disc_data["total_lessons"] = total_lessons

        self.save_state()

    def bootstrap_from_disk(
        self, discipline_title: str, lessons: List[Dict[str, Any]], check_videos: bool = False
    ) -> bool:
        """
        Verifica o sistema de arquivos para sincronizar aulas/disciplinas baixadas
        anteriormente (antes da criação do arquivo de estado).

        Retorna True se TODAS as aulas já existirem com PDFs válidos no disco,
        marcando a disciplina como completada.
        """
        if not lessons:
            return False

        disc_key = self._get_discipline_key(discipline_title)
        disc_path = os.path.join(self.target_dir, disc_key)

        if not os.path.isdir(disc_path):
            return False

        all_completed = True
        completed_count = 0

        for lesson_info in lessons:
            lesson_title = lesson_info.get("title", "")
            if not lesson_title:
                continue

            lesson_key = self.sanitize_func(lesson_title)
            lesson_path = os.path.join(disc_path, lesson_key)

            if os.path.isdir(lesson_path):
                files_in_folder = os.listdir(lesson_path)
                pdf_files = [
                    f
                    for f in files_in_folder
                    if f.lower().endswith(".pdf")
                    and os.path.getsize(os.path.join(lesson_path, f)) > 1024
                ]
                mp4_files = [
                    f
                    for f in files_in_folder
                    if f.lower().endswith(".mp4")
                    and os.path.getsize(os.path.join(lesson_path, f)) > 10240
                ]

                # Se checar vídeos for exigido, precisa ter mp4 OU pdf
                has_required_files = bool(pdf_files)
                if check_videos:
                    has_required_files = bool(pdf_files and mp4_files)

                if has_required_files:
                    all_found_files = pdf_files + mp4_files
                    self.mark_lesson_completed(
                        discipline_title,
                        lesson_title,
                        all_found_files,
                        videos_completed=bool(mp4_files),
                    )
                    completed_count += 1
                    continue

            all_completed = False

        if all_completed and completed_count == len(lessons):
            self.mark_discipline_completed(
                discipline_title, len(lessons), videos_completed=check_videos
            )
            return True

        return False
