import time
import threading
from typing import List, Dict, Any, Optional, Callable

from core.events import DownloadObserver, StatusEvent, DisciplineEvent, LessonEvent
from core.state_manager import DownloadStateManager
from core.crawler import get_lesson_data, normalize_course_url
from core.processor import download_lesson_materials
from core.downloader import sanitize_filename


class CourseWatcher:
    """
    Monitor inteligente (Smart Watcher) que inspeciona cursos periodicamente
    e sincroniza apenas aulas e materiais recém-publicados pelos professores.
    """

    def __init__(
        self,
        driver_factory: Callable[[], Any],
        http_session_factory: Callable[[], Any],
        observer: Optional[DownloadObserver] = None,
        check_interval_seconds: int = 3600,
    ):
        self.driver_factory = driver_factory
        self.http_session_factory = http_session_factory
        self.observer = observer
        self.check_interval_seconds = check_interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def check_course_updates(
        self,
        driver,
        course_url: str,
        course_title: str,
        download_dir: str,
        http_session,
        download_videos: bool = False,
        preferred_quality: str = "720p",
        auto_download: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Compara o estado atual das aulas no portal com o banco local .download_state.json
        e identifica novas aulas publicadas.
        """
        state_mgr = DownloadStateManager(download_dir, sanitize_func=sanitize_filename)
        online_lessons = get_lesson_data(driver, course_url, observer=self.observer)

        if not online_lessons:
            return []

        new_or_pending_lessons = []
        for lesson in online_lessons:
            title = lesson["title"]
            if not state_mgr.is_lesson_completed(course_title, title, check_videos=download_videos):
                new_or_pending_lessons.append(lesson)

        if self.observer:
            if new_or_pending_lessons:
                self.observer.on_status(
                    StatusEvent(
                        level="info",
                        message=f"Smart Watcher: {len(new_or_pending_lessons)} novas aulas/atualizações detectadas para '{course_title}'.",
                    )
                )
            else:
                self.observer.on_status(
                    StatusEvent(
                        level="info",
                        message=f"Smart Watcher: Curso '{course_title}' está 100% atualizado.",
                    )
                )

        if auto_download and new_or_pending_lessons:
            for idx, lesson in enumerate(new_or_pending_lessons, start=1):
                if self.observer:
                    self.observer.on_lesson(
                        LessonEvent(
                            index=idx,
                            total=len(new_or_pending_lessons),
                            title=lesson["title"],
                            status="started",
                        )
                    )
                download_lesson_materials(
                    driver=driver,
                    lesson_info=lesson,
                    course_title=course_title,
                    download_dir=download_dir,
                    http_session=http_session,
                    observer=self.observer,
                    state_manager=state_mgr,
                    download_videos=download_videos,
                    preferred_quality=preferred_quality,
                )

        return new_or_pending_lessons

    def start_background_watcher(
        self,
        watched_courses: List[Dict[str, str]],
        download_dir: str,
        download_videos: bool = False,
    ) -> None:
        """Inicia o loop de monitoramento contínuo em background."""
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                driver = None
                try:
                    driver = self.driver_factory()
                    http_session = self.http_session_factory()
                    for course in watched_courses:
                        if self._stop_event.is_set():
                            break
                        self.check_course_updates(
                            driver=driver,
                            course_url=course["url"],
                            course_title=course["title"],
                            download_dir=download_dir,
                            http_session=http_session,
                            download_videos=download_videos,
                            auto_download=True,
                        )
                except Exception as e:
                    if self.observer:
                        self.observer.on_status(
                            StatusEvent(level="warning", message=f"Erro no ciclo do Smart Watcher: {e}")
                        )
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass

                # Aguarda o intervalo respeitando o sinal de parada
                self._stop_event.wait(self.check_interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_watcher(self) -> None:
        """Interrompe o monitoramento em background."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
