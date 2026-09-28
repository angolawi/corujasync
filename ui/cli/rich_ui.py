import os
import sys
import time
from typing import Optional, Dict, Any

from core.events import (
    DownloadObserver,
    ProgressEvent,
    StatusEvent,
    DisciplineEvent,
    LessonEvent,
    VideoEvent,
)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
        TransferSpeedColumn,
    )
    from rich.theme import Theme

    custom_theme = Theme(
        {
            "info": "dim cyan",
            "warning": "bold yellow",
            "danger": "bold red",
            "success": "bold green",
            "course": "bold cyan",
            "lesson": "bold white",
            "file": "bold magenta",
        }
    )
    _console = Console(theme=custom_theme)
    RICH_AVAILABLE = True
except ImportError:
    _console = None
    RICH_AVAILABLE = False


class RichDownloadUI(DownloadObserver):
    """
    Interface visual no terminal utilizando Rich para exibir progresso com cores,
    velocidade de transferência e notificações organizadas.
    Implementa DownloadObserver.
    """

    def __init__(self, no_color: bool = False):
        self.no_color = no_color
        if RICH_AVAILABLE:
            self.console = Console(theme=custom_theme, no_color=no_color)
        else:
            self.console = None

    # --- Implementação dos métodos de DownloadObserver ---

    def on_banner(
        self,
        mode: str,
        target_dir: str,
        target_name: Optional[str] = None,
        total_items: Optional[int] = None,
    ) -> None:
        self.print_banner(mode, target_dir, target_name, total_items)

    def on_discipline(self, event: DisciplineEvent) -> None:
        if event.status == "started":
            self.log_discipline_start(event.index, event.total, event.title)
        elif event.status == "skipped":
            self.log_discipline_skip(
                event.index, event.total, event.title, event.reason or "Já concluída"
            )
        elif event.status == "completed":
            self.log_discipline_completed(
                event.index, event.total, event.title, event.lesson_count or 0
            )

    def on_lesson(self, event: LessonEvent) -> None:
        if event.status == "started":
            self.log_lesson_start(event.index, event.total, event.title)
        elif event.status == "skipped":
            self.log_lesson_skip(event.index, event.total, event.title)

    def on_video_playlist(self, count: int) -> None:
        self.log_video_playlist(count)

    def on_video(self, event: VideoEvent) -> None:
        if event.status == "started":
            self.log_video_start(event.index, event.total, event.title)
        elif event.status == "skipped":
            self.log_video_skip(event.index, event.total, event.title)

    def on_status(self, event: StatusEvent) -> None:
        if event.level == "info":
            self.log_info(event.message)
        elif event.level == "warning":
            self.log_warning(event.message)
        elif event.level == "error":
            self.log_error(event.message)
        elif event.level == "success":
            self.log_success(event.message)

    # --- Métodos nativos de log e renderização ---

    def print_banner(
        self,
        mode: str,
        target_dir: str,
        target_name: Optional[str] = None,
        total_items: Optional[int] = None,
    ) -> None:
        """Exibe o cabeçalho inicial com as informações da execução."""
        if not self.console:
            print(f"=== Concurso Downloader | Modo: {mode} ===")
            print(f"Destino: {target_dir}")
            if target_name:
                print(f"Alvo: {target_name}")
            return

        body = (
            f"[bold cyan]Modo:[/] {mode}\n"
            f"[bold cyan]Destino:[/] [dim]{target_dir}[/dim]\n"
        )
        if target_name:
            body += f"[bold cyan]Curso/Pacote:[/] [bold yellow]{target_name}[/]\n"
        if total_items is not None:
            body += f"[bold cyan]Total de Itens:[/] [bold green]{total_items}[/]\n"

        self.console.print(
            Panel(
                body,
                title="[bold green]Concurso Downloader - Backup Inteligente[/]",
                border_style="bright_blue",
            )
        )

    def log_discipline_start(self, index: int, total: int, title: str) -> None:
        if not self.console:
            print(f"\n[{index}/{total}] Disciplina: {title}")
            return
        self.console.print(
            f"\n[bold blue]━━━[/] [bold yellow][{index}/{total}][/] "
            f"[bold cyan]Disciplina:[/] [bold white]{title}[/]"
        )

    def log_discipline_skip(
        self, index: int, total: int, title: str, reason: str = "Já concluída no histórico"
    ) -> None:
        if not self.console:
            print(f"[{index}/{total}] [PULANDO] Disciplina: {title} ({reason})")
            return
        self.console.print(
            f"[dim]↷[/dim] [yellow][{index}/{total}][/] [dim cyan]{title}[/] "
            f"[bold green]✓ {reason}[/] [dim]- Pulando.[/dim]"
        )

    def log_discipline_completed(
        self, index: int, total: int, title: str, lesson_count: int
    ) -> None:
        if not self.console:
            print(f"[{index}/{total}] [CONCLUÍDO] Disciplina: {title} ({lesson_count} aulas)")
            return
        self.console.print(
            f"[bold green]✓ Concluída disciplina:[/] [cyan]{title}[/] "
            f"[dim]({lesson_count} aulas)[/dim]"
        )

    def log_lesson_start(self, index: int, total: int, title: str) -> None:
        if not self.console:
            print(f"  -> Aula {index}/{total}: {title}")
            return
        self.console.print(
            f"  [bold blue]→[/] [yellow][{index}/{total}][/] [bold white]{title}[/]"
        )

    def log_lesson_skip(self, index: int, total: int, title: str) -> None:
        if not self.console:
            print(f"  [PULANDO] Aula {index}/{total}: {title}")
            return
        self.console.print(
            f"  [dim]↷ [{index}/{total}] {title} (já baixada)[/dim]"
        )

    def log_info(self, msg: str) -> None:
        if not self.console:
            print(f"   {msg}")
            return
        self.console.print(f"   [dim cyan]{msg}[/dim cyan]")

    def log_warning(self, msg: str) -> None:
        if not self.console:
            print(f"   [AVISO] {msg}")
            return
        self.console.print(f"   [bold yellow]⚠ AVISO:[/] [yellow]{msg}[/]")

    def log_error(self, msg: str) -> None:
        if not self.console:
            print(f"   [ERRO] {msg}")
            return
        self.console.print(f"   [bold red]✗ ERRO:[/] [red]{msg}[/]")

    def log_success(self, msg: str) -> None:
        if not self.console:
            print(f"   [SUCESSO] {msg}")
            return
        self.console.print(f"   [bold green]✓[/] {msg}")

    def log_video_playlist(self, count: int) -> None:
        if not self.console:
            print(f"       Encontrados {count} vídeos na playlist.")
            return
        self.console.print(f"       [bold magenta]🎬 Playlist:[/] Encontrados [bold yellow]{count}[/] vídeos.")

    def log_video_start(self, index: int, total: int, title: str) -> None:
        if not self.console:
            print(f"        -> Vídeo {index}/{total}: {title}")
            return
        self.console.print(
            f"        [bold magenta]▶[/] [yellow][{index}/{total}][/] [bold white]{title}[/]"
        )

    def log_video_skip(self, index: int, total: int, title: str) -> None:
        if not self.console:
            print(f"        [PULANDO] Vídeo {index}/{total}: {title} (já baixado)")
            return
        self.console.print(
            f"        [dim]↷ [{index}/{total}] {title} (vídeo já baixado)[/dim]"
        )

    def download_stream(
        self, response, destination_path: str, filename: str, chunk_size: Optional[int] = None
    ) -> bool:
        """
        Transfere o stream de bytes para um arquivo temporário (.part), exibindo
        barra de progresso com taxa de download em tempo real e ETA.
        Ao final, renomeia atomicamente para destination_path.
        """
        if chunk_size is None:
            chunk_size = 262144 if filename.lower().endswith(".mp4") else 131072

        temp_path = f"{destination_path}.part"
        content_length = response.headers.get("content-length")
        total_size = int(content_length) if content_length and content_length.isdigit() else None

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        if not self.console or not RICH_AVAILABLE:
            try:
                with open(temp_path, "wb") as f:
                    downloaded = 0
                    start_time = time.time()
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                os.replace(temp_path, destination_path)
                print(f"     Baixado com sucesso: {filename}")
                return True
            except (KeyboardInterrupt, Exception) as e:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                return False

        # Com Rich: barra de progresso colorida
        progress = Progress(
            TextColumn("     [bold magenta]{task.fields[filename]}[/]"),
            BarColumn(bar_width=30, complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True,
        )

        try:
            with progress:
                task_id = progress.add_task(
                    "download",
                    filename=filename,
                    total=total_size,
                )
                start_t = time.time()
                downloaded_bytes = 0

                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        chunk_len = len(chunk)
                        downloaded_bytes += chunk_len
                        progress.update(task_id, advance=chunk_len)

            if os.path.getsize(temp_path) < 1024:
                self.log_warning(
                    f"Arquivo '{filename}' suspeitamente pequeno ({os.path.getsize(temp_path)} bytes). "
                    f"Pode ser página de erro."
                )

            os.replace(temp_path, destination_path)
            elapsed = max(time.time() - start_t, 0.01)
            mb = downloaded_bytes / (1024 * 1024)
            speed_mb = mb / elapsed
            self.console.print(
                f"     [bold green]✓[/] [white]{filename}[/] "
                f"[dim]({mb:.2f} MB em {elapsed:.1f}s - {speed_mb:.2f} MB/s)[/dim]"
            )
            return True

        except KeyboardInterrupt:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            self.log_warning("Download interrompido pelo usuário.")
            raise
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            self.log_error(f"Erro ao transferir arquivo: {e}")
            return False
