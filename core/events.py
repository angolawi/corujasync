from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ProgressEvent:
    filename: str
    downloaded_bytes: int
    total_bytes: Optional[int]
    speed_bytes_sec: float
    eta_seconds: Optional[float]
    percent: float


@dataclass
class StatusEvent:
    level: str  # 'info', 'warning', 'error', 'success'
    message: str
    course_name: Optional[str] = None
    lesson_name: Optional[str] = None


@dataclass
class DisciplineEvent:
    index: int
    total: int
    title: str
    status: str  # 'started', 'skipped', 'completed'
    reason: Optional[str] = None
    lesson_count: Optional[int] = None


@dataclass
class LessonEvent:
    index: int
    total: int
    title: str
    status: str  # 'started', 'skipped', 'completed'


@dataclass
class VideoEvent:
    index: int
    total: int
    title: str
    status: str  # 'started', 'skipped', 'completed'


class DownloadObserver:
    """
    Interface abstrata (Observer) para ser implementada tanto pela CLI (Rich)
    quanto pela GUI (CustomTkinter) e por testes automatizados.
    """

    def on_banner(
        self,
        mode: str,
        target_dir: str,
        target_name: Optional[str] = None,
        total_items: Optional[int] = None,
    ) -> None:
        pass

    def on_discipline(self, event: DisciplineEvent) -> None:
        pass

    def on_lesson(self, event: LessonEvent) -> None:
        pass

    def on_video_playlist(self, count: int) -> None:
        pass

    def on_video(self, event: VideoEvent) -> None:
        pass

    def on_progress(self, event: ProgressEvent) -> None:
        pass

    def on_status(self, event: StatusEvent) -> None:
        pass

    def on_finished(self, summary: Dict[str, Any]) -> None:
        pass
