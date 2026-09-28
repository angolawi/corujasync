import os
import re
import time
from typing import List, Dict, Any, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from core.events import (
    DownloadObserver,
    StatusEvent,
    DisciplineEvent,
    LessonEvent,
    VideoEvent,
)
from core.downloader import sanitize_filename, download_file
from core.state_manager import DownloadStateManager
from core.crawler import handle_popups, get_lesson_data


def download_video_materials(
    driver,
    lesson_info: Dict[str, Any],
    course_title: str,
    lesson_download_path: str,
    preferred_quality: str = "720p",
    http_session=None,
    observer: Optional[DownloadObserver] = None,
    cancel_flag: Optional[callable] = None,
) -> List[str]:
    """
    Extrai a playlist de vídeos da aula, baixa os materiais de apoio de cada vídeo
    (Resumos, Slides, Mapas Mentais) e a videoaula (.mp4) na qualidade desejada.
    """
    playlist_selectors = [
        "div.ListVideos-items-video a.VideoItem",
        "a.VideoItem",
        "div.ListVideos a[href*='/videos/']",
        "a[href*='/videos/']",
    ]

    playlist_items = []
    for selector in playlist_selectors:
        try:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                playlist_items = items
                break
        except (NoSuchElementException, WebDriverException):
            pass

    if not playlist_items:
        if observer:
            observer.on_status(StatusEvent(level="info", message="Nenhum vídeo disponível na playlist desta aula."))
        return []

    videos_to_download = []
    seen_video_urls = set()
    for item in playlist_items:
        try:
            video_href = item.get_attribute("href")
            if not video_href or video_href in seen_video_urls:
                continue
            seen_video_urls.add(video_href)

            video_title = ""
            try:
                title_elem = item.find_element(
                    By.CSS_SELECTOR, "span.VideoItem-info-title, div.VideoItem-info, p"
                )
                video_title = title_elem.text.strip()
            except NoSuchElementException:
                video_title = item.text.strip()

            if not video_title:
                video_title = f"Video_{len(videos_to_download) + 1}"

            videos_to_download.append({"url": video_href, "title": video_title})
        except StaleElementReferenceException:
            pass

    if not videos_to_download:
        if observer:
            observer.on_status(StatusEvent(level="info", message="Nenhum link de vídeo derivável encontrado."))
        return []

    total_videos = len(videos_to_download)
    if observer:
        observer.on_video_playlist(total_videos)

    if preferred_quality == "720p":
        qualities_order = ["720p", "480p", "360p"]
    elif preferred_quality == "480p":
        qualities_order = ["480p", "360p", "720p"]
    else:
        qualities_order = ["360p", "480p", "720p"]

    downloaded_files = []

    for idx, video_info in enumerate(videos_to_download, start=1):
        if cancel_flag and cancel_flag():
            break

        video_url = video_info["url"]
        video_title = video_info["title"]
        sanitized_video_title = sanitize_filename(video_title, max_length=80)
        sanitized_lesson_title = sanitize_filename(lesson_info["title"])

        # Checa se o vídeo já existe no disco em qualquer qualidade válida (> 10KB)
        existing_video = None
        for q in qualities_order:
            candidate_name = f"{sanitized_video_title}_Video_{q}.mp4"
            candidate_path = os.path.join(lesson_download_path, candidate_name)
            if os.path.exists(candidate_path) and os.path.getsize(candidate_path) > 10240:
                existing_video = candidate_name
                break

        if existing_video:
            if observer:
                observer.on_video(VideoEvent(index=idx, total=total_videos, title=video_title, status="skipped"))
            downloaded_files.append(existing_video)
            continue

        if observer:
            observer.on_video(VideoEvent(index=idx, total=total_videos, title=video_title, status="started"))

        driver.get(video_url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.Video, div.VideoPlayer, a.LessonButton, div.Collapse-header")
                )
            )
            time.sleep(1)
        except TimeoutException:
            if observer:
                observer.on_status(
                    StatusEvent(level="warning", message=f"Tempo esgotado ao carregar vídeo '{video_title}'. Pulando.")
                )
            continue

        handle_popups(driver, observer=observer)
        selenium_cookies = driver.get_cookies()

        # Baixa materiais de apoio do vídeo
        video_pdf_types = {
            "Baixar Resumo": f"_Resumo_{idx}.pdf",
            "Baixar Slides": f"_Slides_Video_{idx}.pdf",
            "Baixar Mapa Mental": f"_Mapa_Mental_{idx}.pdf",
        }

        for pdf_button_text, filename_suffix in video_pdf_types.items():
            if cancel_flag and cancel_flag():
                break
            try:
                pdf_link_elem = driver.find_element(
                    By.XPATH,
                    f"//a[contains(@class, 'LessonButton') and .//span[contains(text(), '{pdf_button_text}')]]",
                )
                pdf_url = pdf_link_elem.get_attribute("href")
                if pdf_url and "api.estrategiaconcursos.com.br" in pdf_url:
                    support_filename = f"{sanitized_lesson_title}_{sanitized_video_title}{filename_suffix}"
                    support_path = os.path.join(lesson_download_path, support_filename)
                    if os.path.exists(support_path) and os.path.getsize(support_path) > 1024:
                        downloaded_files.append(support_filename)
                    else:
                        if observer:
                            observer.on_status(
                                StatusEvent(level="info", message=f"Encontrado {pdf_button_text} para o vídeo '{video_title}'.")
                            )
                        if download_file(
                            url=pdf_url,
                            file_path=support_path,
                            session_cookies=selenium_cookies,
                            current_page_url=driver.current_url,
                            http_session=http_session,
                            observer=observer,
                            cancel_flag=cancel_flag,
                        ):
                            downloaded_files.append(support_filename)
            except NoSuchElementException:
                pass
            except Exception as e:
                if observer:
                    observer.on_status(
                        StatusEvent(level="warning", message=f"Erro ao processar '{pdf_button_text}': {e}")
                    )

        # Expande opções de download do vídeo
        try:
            download_header = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@class, 'Collapse-header')]//*[contains(text(), 'Opções de download')]")
                )
            )
            driver.execute_script("arguments[0].click();", download_header)
            time.sleep(1)
        except TimeoutException:
            try:
                alt_header = driver.find_element(By.XPATH, "//*[contains(text(), 'Opções de download')]")
                driver.execute_script("arguments[0].click();", alt_header)
                time.sleep(1)
            except NoSuchElementException:
                pass

        # Baixa vídeo na resolução preferencial
        video_downloaded = False
        for quality in qualities_order:
            if cancel_flag and cancel_flag():
                break
            video_filename = f"{sanitized_video_title}_Video_{quality}.mp4"
            video_path = os.path.join(lesson_download_path, video_filename)

            try:
                video_link_elem = driver.find_element(
                    By.XPATH,
                    f"//a[contains(text(), '{quality}')] | //a[contains(@href, '{quality}')]",
                )
                video_url = video_link_elem.get_attribute("href")
                if video_url:
                    if observer:
                        observer.on_status(StatusEvent(level="info", message=f"Baixando vídeo em {quality}..."))
                    if download_file(
                        url=video_url,
                        file_path=video_path,
                        session_cookies=selenium_cookies,
                        current_page_url=driver.current_url,
                        http_session=http_session,
                        observer=observer,
                        cancel_flag=cancel_flag,
                    ):
                        downloaded_files.append(video_filename)
                        video_downloaded = True
                        break
            except NoSuchElementException:
                continue
            except Exception as e:
                if observer:
                    observer.on_status(
                        StatusEvent(level="warning", message=f"Falha ao tentar baixar vídeo em {quality}: {e}")
                    )

        if not video_downloaded and observer:
            observer.on_status(
                StatusEvent(level="warning", message=f"Não foi possível baixar nenhuma qualidade para '{video_title}'.")
            )

        time.sleep(1)

    return downloaded_files


def download_lesson_materials(
    driver,
    lesson_info: Dict[str, Any],
    course_title: str,
    download_dir: str,
    http_session=None,
    observer: Optional[DownloadObserver] = None,
    state_manager: Optional[DownloadStateManager] = None,
    download_videos: bool = False,
    preferred_quality: str = "720p",
    cancel_flag: Optional[callable] = None,
) -> bool:
    """Navega para a página de uma aula, baixa os PDFs e videoaulas."""
    lesson_title = lesson_info["title"]
    lesson_subtitle = lesson_info.get("subtitle", "")
    lesson_url = lesson_info["url"]

    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Acessando aula no navegador: {lesson_title}"))
    driver.get(lesson_url)

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.Lesson-contentTop, div.LessonButtonList, div.LessonList")
            )
        )
        time.sleep(1)
    except TimeoutException:
        if observer:
            observer.on_status(
                StatusEvent(
                    level="warning",
                    message=f"Tempo esgotado ao carregar aula '{lesson_title}'. A aula pode não ter conteúdo.",
                )
            )
        return False

    handle_popups(driver, observer=observer)

    sanitized_course_title = sanitize_filename(course_title)
    sanitized_lesson_title = sanitize_filename(lesson_title)
    lesson_download_path = os.path.join(download_dir, sanitized_course_title, sanitized_lesson_title)

    try:
        os.makedirs(lesson_download_path, exist_ok=True)
    except OSError as e:
        if observer:
            observer.on_status(
                StatusEvent(level="error", message=f"Erro ao criar diretório '{lesson_download_path}': {e}")
            )
        return False

    if lesson_subtitle:
        subjects_file_path = os.path.join(lesson_download_path, "Assuntos_dessa_aula.txt")
        if not os.path.exists(subjects_file_path):
            try:
                with open(subjects_file_path, "w", encoding="utf-8") as f:
                    f.write(lesson_subtitle)
            except OSError as e:
                if observer:
                    observer.on_status(StatusEvent(level="warning", message=f"Erro ao criar 'Assuntos_dessa_aula.txt': {e}"))

    selenium_cookies = driver.get_cookies()
    all_downloads_ok = True
    downloaded_files = []

    try:
        pdf_links = driver.find_elements(By.CSS_SELECTOR, "a.LessonButton")
        pdfs_encontrados = 0

        for pdf_link in pdf_links:
            if cancel_flag and cancel_flag():
                return False

            pdf_url = pdf_link.get_attribute("href") or ""
            if "api.estrategiaconcursos.com.br" not in pdf_url:
                continue

            pdfs_encontrados += 1
            pdf_text_raw = "original"
            try:
                version_span = pdf_link.find_element(By.CSS_SELECTOR, "span.LessonButton-text > span")
                pdf_text_raw = version_span.text.strip()
            except NoSuchElementException:
                try:
                    full_text = pdf_link.find_element(By.CSS_SELECTOR, "span.LessonButton-text").text.strip()
                    if full_text:
                        pdf_text_raw = re.sub(
                            r"^baixar\s+livro\s+eletrônico\s*", "", full_text, flags=re.IGNORECASE
                        ).strip() or "original"
                except NoSuchElementException:
                    pass

            filename_suffix = "_" + sanitize_filename(pdf_text_raw) if pdf_text_raw else ""
            filename = f"{sanitized_lesson_title}_Livro_Eletronico{filename_suffix}.pdf"
            full_file_path = os.path.join(lesson_download_path, filename)

            if os.path.exists(full_file_path) and os.path.getsize(full_file_path) > 1024:
                if observer:
                    observer.on_status(StatusEvent(level="info", message=f"PDF '{filename}' já existe no disco. Pulando."))
                downloaded_files.append(filename)
                continue

            if observer:
                observer.on_status(StatusEvent(level="info", message=f"Encontrado PDF: versão '{pdf_text_raw}'"))

            ok = download_file(
                url=pdf_url,
                file_path=full_file_path,
                session_cookies=selenium_cookies,
                current_page_url=driver.current_url,
                http_session=http_session,
                observer=observer,
                cancel_flag=cancel_flag,
            )
            if ok:
                downloaded_files.append(filename)
            else:
                all_downloads_ok = False

        if pdfs_encontrados == 0 and observer:
            observer.on_status(StatusEvent(level="info", message="Nenhum PDF encontrado nesta aula."))

        if download_videos:
            video_files = download_video_materials(
                driver=driver,
                lesson_info=lesson_info,
                course_title=course_title,
                lesson_download_path=lesson_download_path,
                preferred_quality=preferred_quality,
                http_session=http_session,
                observer=observer,
                cancel_flag=cancel_flag,
            )
            downloaded_files.extend(video_files)

        if all_downloads_ok and state_manager:
            state_manager.mark_lesson_completed(
                course_title,
                lesson_title,
                downloaded_files,
                videos_completed=download_videos,
            )

        return all_downloads_ok

    except StaleElementReferenceException:
        if observer:
            observer.on_status(StatusEvent(level="warning", message="Elemento de PDF ficou obsoleto durante o processamento."))
        return False
    except WebDriverException as e:
        if observer:
            observer.on_status(StatusEvent(level="error", message=f"Erro do WebDriver ao processar aula: {e}"))
        return False
    except Exception as e:
        if observer:
            observer.on_status(StatusEvent(level="error", message=f"Erro inesperado ao processar aula: {e}"))
        return False


def process_courses(
    driver,
    courses: List[Dict[str, str]],
    target_download_dir: str,
    observer: Optional[DownloadObserver],
    http_session,
    state_mgr: DownloadStateManager,
    force: bool = False,
    download_videos: bool = False,
    preferred_quality: str = "720p",
    cancel_flag: Optional[callable] = None,
) -> None:
    """Executa a iteração sobre disciplinas e aulas com Smart Resume e emissão de eventos."""
    total_cursos = len(courses)

    for i, course in enumerate(courses, start=1):
        if cancel_flag and cancel_flag():
            if observer:
                observer.on_status(StatusEvent(level="warning", message="Processamento interrompido pelo usuário."))
            break

        disciplina_title = course["title"]
        disciplina_url = course["url"]

        if not force and state_mgr.is_discipline_completed(disciplina_title, check_videos=download_videos):
            if observer:
                observer.on_discipline(
                    DisciplineEvent(
                        index=i,
                        total=total_cursos,
                        title=disciplina_title,
                        status="skipped",
                        reason="Já concluída no histórico (.download_state.json)",
                    )
                )
            continue

        if observer:
            observer.on_discipline(
                DisciplineEvent(index=i, total=total_cursos, title=disciplina_title, status="started")
            )

        lessons = get_lesson_data(driver, disciplina_url, observer=observer)
        if not lessons:
            if observer:
                observer.on_status(
                    StatusEvent(level="warning", message=f"Nenhuma aula encontrada para '{disciplina_title}'. Pulando.")
                )
            continue

        if not force and state_mgr.bootstrap_from_disk(disciplina_title, lessons, check_videos=download_videos):
            if observer:
                observer.on_discipline(
                    DisciplineEvent(
                        index=i,
                        total=total_cursos,
                        title=disciplina_title,
                        status="skipped",
                        reason="Todas as aulas já no disco (sincronizado automaticamente)",
                    )
                )
            continue

        all_lessons_ok = True
        for j, lesson_info in enumerate(lessons, start=1):
            if cancel_flag and cancel_flag():
                break

            lesson_title = lesson_info["title"]

            if not force and state_mgr.is_lesson_completed(disciplina_title, lesson_title, check_videos=download_videos):
                if observer:
                    observer.on_lesson(
                        LessonEvent(index=j, total=len(lessons), title=lesson_title, status="skipped")
                    )
                continue

            if observer:
                observer.on_lesson(
                    LessonEvent(index=j, total=len(lessons), title=lesson_title, status="started")
                )

            success = download_lesson_materials(
                driver=driver,
                lesson_info=lesson_info,
                course_title=disciplina_title,
                download_dir=target_download_dir,
                http_session=http_session,
                observer=observer,
                state_manager=state_mgr,
                download_videos=download_videos,
                preferred_quality=preferred_quality,
                cancel_flag=cancel_flag,
            )
            if not success:
                all_lessons_ok = False

            time.sleep(1)

        if all_lessons_ok:
            state_mgr.mark_discipline_completed(
                disciplina_title, len(lessons), videos_completed=download_videos
            )
            if observer:
                observer.on_discipline(
                    DisciplineEvent(
                        index=i,
                        total=total_cursos,
                        title=disciplina_title,
                        status="completed",
                        lesson_count=len(lessons),
                    )
                )
