import threading
import queue
import time
from typing import Optional, Dict, Any, List

from core.events import (
    DownloadObserver,
    ProgressEvent,
    StatusEvent,
    DisciplineEvent,
    LessonEvent,
    VideoEvent,
)
from core.session import create_http_session
from core.state_manager import DownloadStateManager
from core.downloader import sanitize_filename
from core.crawler import (
    normalize_course_url,
    get_courses_from_pacote,
    get_course_data,
    login,
    URL_PREFIX_PACOTE,
    URL_PREFIX_CURSOS,
)
from core.processor import process_courses
from core.selector_manager import get_selector_manager
from browser.driver_manager import create_driver


class GuiDownloadObserver(DownloadObserver):
    """Encaminha todos os eventos para a queue da interface gráfica de forma thread-safe."""

    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue

    def on_banner(
        self,
        mode: str,
        target_dir: str,
        target_name: Optional[str] = None,
        total_items: Optional[int] = None,
    ) -> None:
        self.event_queue.put(("banner", {"mode": mode, "dir": target_dir, "name": target_name, "total": total_items}))

    def on_discipline(self, event: DisciplineEvent) -> None:
        self.event_queue.put(("discipline", event))

    def on_lesson(self, event: LessonEvent) -> None:
        self.event_queue.put(("lesson", event))

    def on_video_playlist(self, count: int) -> None:
        self.event_queue.put(("video_playlist", count))

    def on_video(self, event: VideoEvent) -> None:
        self.event_queue.put(("video", event))

    def on_progress(self, event: ProgressEvent) -> None:
        self.event_queue.put(("progress", event))

    def on_status(self, event: StatusEvent) -> None:
        self.event_queue.put(("status", event))

    def on_finished(self, summary: Dict[str, Any]) -> None:
        self.event_queue.put(("finished", summary))


class DownloadWorker(threading.Thread):
    """Worker assíncrono que executa todo o fluxo de download sem travar a GUI."""

    def __init__(
        self,
        event_queue: queue.Queue,
        download_dir: str,
        curso_input: Optional[str] = None,
        email: str = "",
        senha: str = "",
        download_videos: bool = False,
        preferred_quality: str = "720p",
        force: bool = False,
        preferred_browser: str = "auto",
        wait_time: int = 60,
    ):
        super().__init__(daemon=True)
        self.event_queue = event_queue
        self.download_dir = download_dir
        self.curso_input = curso_input
        self.email = email
        self.senha = senha
        self.download_videos = download_videos
        self.preferred_quality = preferred_quality
        self.force = force
        self.preferred_browser = preferred_browser
        self.wait_time = wait_time

        self.cancel_requested = threading.Event()
        self.observer = GuiDownloadObserver(self.event_queue)
        self.driver = None

    def cancel(self):
        """Sinaliza parada imediata das operações."""
        self.cancel_requested.set()
        self.observer.on_status(StatusEvent(level="warning", message="Solicitação de cancelamento enviada..."))

    def is_cancelled(self) -> bool:
        return self.cancel_requested.is_set()

    def run(self):
        start_time = time.time()
        http_session = create_http_session()

        # Atualização assíncrona OTA de seletores em background
        try:
            get_selector_manager().fetch_remote_async()
        except Exception:
            pass

        try:
            self.observer.on_status(
                StatusEvent(level="info", message="Iniciando navegador para autenticação...")
            )
            self.driver = create_driver(preferred_browser=self.preferred_browser, headless=False)

            if self.is_cancelled():
                return

            login(
                driver=self.driver,
                email=self.email,
                senha=self.senha,
                wait_time=self.wait_time,
                observer=self.observer,
            )

            if self.is_cancelled():
                return

            # Modo de curso específico ou modo batch
            if self.curso_input:
                self._run_single_course(http_session)
            else:
                self._run_batch_courses(http_session)

            elapsed = time.time() - start_time
            self.observer.on_finished({"success": True, "elapsed_seconds": elapsed})

        except Exception as e:
            self.observer.on_status(StatusEvent(level="error", message=f"Erro durante execução: {e}"))
            self.observer.on_finished({"success": False, "error": str(e)})

        finally:
            if self.driver:
                try:
                    self.observer.on_status(
                        StatusEvent(level="info", message="Fechando navegador em 3 segundos...")
                    )
                    time.sleep(3)
                    self.driver.quit()
                except Exception:
                    pass

    def _run_single_course(self, http_session):
        try:
            url = normalize_course_url(self.curso_input)
        except ValueError as e:
            self.observer.on_status(StatusEvent(level="error", message=str(e)))
            return

        from urllib.parse import urlparse
        parsed_path = urlparse(url).path

        if URL_PREFIX_PACOTE in parsed_path:
            courses, pacote_title = get_courses_from_pacote(self.driver, url, observer=self.observer)
            if not courses:
                self.observer.on_status(
                    StatusEvent(level="error", message="Nenhuma disciplina encontrada no pacote.")
                )
                return

            folder_title = pacote_title or f"Pacote_{parsed_path.rstrip('/').split('/')[-1]}"
            target_download_dir = f"{self.download_dir}/{sanitize_filename(folder_title)}"
            mode_label = "Pacote de Disciplinas"

        elif URL_PREFIX_CURSOS in parsed_path:
            curso_url = url if url.endswith("/aulas") else url.rstrip("/") + "/aulas"
            self.observer.on_status(StatusEvent(level="info", message="Obtendo título do curso..."))
            self.driver.get(curso_url)
            time.sleep(2)

            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import NoSuchElementException

            folder_title = ""
            elem = get_selector_manager().find_element(self.driver, "single_course_title")
            if elem:
                folder_title = elem.text.strip()
            if not folder_title:
                folder_title = f"Curso_{parsed_path.rstrip('/').split('/')[-2]}"

            courses = [{"title": folder_title, "url": curso_url}]
            target_download_dir = self.download_dir
            mode_label = "Curso Individual"
        else:
            self.observer.on_status(
                StatusEvent(level="error", message="URL não reconhecida como pacote nem curso individual.")
            )
            return

        state_mgr = DownloadStateManager(target_download_dir, sanitize_func=sanitize_filename)
        self.observer.on_banner(
            mode=f"{mode_label} (Vídeos: {'Sim [' + self.preferred_quality + ']' if self.download_videos else 'Não'})",
            target_dir=target_download_dir,
            target_name=folder_title,
            total_items=len(courses),
        )

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=target_download_dir,
            observer=self.observer,
            http_session=http_session,
            state_mgr=state_mgr,
            force=self.force,
            download_videos=self.download_videos,
            preferred_quality=self.preferred_quality,
            cancel_flag=self.is_cancelled,
        )

    def _run_batch_courses(self, http_session):
        courses = get_course_data(self.driver, observer=self.observer)
        if not courses:
            self.observer.on_status(
                StatusEvent(level="warning", message="Nenhum curso matriculado encontrado.")
            )
            return

        state_mgr = DownloadStateManager(self.download_dir, sanitize_func=sanitize_filename)
        self.observer.on_banner(
            mode=f"Todos os Cursos (Vídeos: {'Sim' if self.download_videos else 'Não'})",
            target_dir=self.download_dir,
            total_items=len(courses),
        )

        process_courses(
            driver=self.driver,
            courses=courses,
            target_download_dir=self.download_dir,
            observer=self.observer,
            http_session=http_session,
            state_mgr=state_mgr,
            force=self.force,
            download_videos=self.download_videos,
            preferred_quality=self.preferred_quality,
            cancel_flag=self.is_cancelled,
        )
