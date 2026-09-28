import os
import re
import time
from typing import Optional, List
import requests

from core.events import ProgressEvent, StatusEvent, DownloadObserver
from core.session import DEFAULT_HEADERS


def sanitize_filename(original_filename: str, max_length: Optional[int] = None) -> str:
    """
    Remove caracteres inválidos de um nome de arquivo/diretório para garantir
    compatibilidade universal com sistemas de arquivos (Windows/Linux/macOS).
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '', original_filename)
    sanitized = re.sub(r'[.,]', '', sanitized)
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    sanitized = sanitized.strip('._- ')
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('._- ')
    return sanitized.strip()


def stream_download(
    response: requests.Response,
    destination_path: str,
    filename: str,
    observer: Optional[DownloadObserver] = None,
    chunk_size: Optional[int] = None,
    cancel_flag: Optional[callable] = None,
) -> bool:
    """
    Transfere o stream de bytes para um arquivo temporário (.part), emitindo
    ProgressEvents para o observer em tempo real.
    Ao final, valida e renomeia atomicamente para destination_path.
    NUNCA altera metadados nem marcas d'água dos arquivos originais.
    """
    if chunk_size is None:
        chunk_size = 262144 if filename.lower().endswith(".mp4") else 131072

    temp_path = f"{destination_path}.part"
    content_length = response.headers.get("content-length")
    total_size = int(content_length) if content_length and content_length.isdigit() else None

    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    start_time = time.time()
    downloaded_bytes = 0
    last_emit_time = 0.0

    try:
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if cancel_flag and cancel_flag():
                    raise InterruptedError("Download cancelado pelo usuário.")

                if not chunk:
                    continue

                f.write(chunk)
                downloaded_bytes += len(chunk)

                now = time.time()
                # Emite evento de progresso com taxa calibrada (a cada 100ms para suavidade na UI)
                if observer and (now - last_emit_time >= 0.1 or downloaded_bytes == total_size):
                    elapsed = max(now - start_time, 0.001)
                    speed = downloaded_bytes / elapsed
                    eta = (total_size - downloaded_bytes) / speed if (total_size and speed > 0) else None
                    percent = (downloaded_bytes / total_size * 100.0) if total_size else 0.0

                    observer.on_progress(
                        ProgressEvent(
                            filename=filename,
                            downloaded_bytes=downloaded_bytes,
                            total_bytes=total_size,
                            speed_bytes_sec=speed,
                            eta_seconds=eta,
                            percent=percent,
                        )
                    )
                    last_emit_time = now

        # Validação pós-download: tamanho mínimo de 1 KB para evitar páginas de erro salvas
        file_size = os.path.getsize(temp_path)
        if file_size < 1024:
            if observer:
                observer.on_status(
                    StatusEvent(
                        level="warning",
                        message=(
                            f"Arquivo '{filename}' suspeitamente pequeno ({file_size} bytes). "
                            f"Pode ser página de erro ou sessão expirada."
                        ),
                    )
                )

        os.replace(temp_path, destination_path)
        return True

    except (KeyboardInterrupt, InterruptedError) as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        if observer:
            observer.on_status(StatusEvent(level="warning", message=f"Download de '{filename}' interrompido."))
        raise e

    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        if observer:
            observer.on_status(StatusEvent(level="error", message=f"Erro ao transferir '{filename}': {e}"))
        return False


def download_file(
    url: str,
    file_path: str,
    session_cookies: Optional[List[dict]] = None,
    current_page_url: Optional[str] = None,
    http_session: Optional[requests.Session] = None,
    observer: Optional[DownloadObserver] = None,
    cancel_flag: Optional[callable] = None,
) -> bool:
    """
    Executa o download de um arquivo com autenticação por cookies do Selenium.
    """
    headers = DEFAULT_HEADERS.copy()
    if current_page_url:
        headers["Referer"] = current_page_url

    session = http_session if http_session is not None else requests.Session()
    if session_cookies:
        for cookie in session_cookies:
            session.cookies.set(cookie["name"], cookie["value"])

    filename = os.path.basename(file_path)

    try:
        response = session.get(url, stream=True, timeout=60, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            if observer:
                observer.on_status(
                    StatusEvent(
                        level="warning",
                        message=(
                            f"A resposta é HTML (possivelmente página de erro ou login expirado). "
                            f"Content-Type={content_type!r}. Abortando '{filename}'."
                        ),
                    )
                )
            return False

        return stream_download(
            response=response,
            destination_path=file_path,
            filename=filename,
            observer=observer,
            cancel_flag=cancel_flag,
        )

    except requests.exceptions.RequestException as e:
        if observer:
            observer.on_status(StatusEvent(level="error", message=f"Erro de rede ao baixar {filename}: {e}"))
        return False
    except OSError as e:
        if observer:
            observer.on_status(StatusEvent(level="error", message=f"Erro de disco ao salvar {filename}: {e}"))
        return False
