import os
import sys
import re
import time
import argparse
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from state_manager import DownloadStateManager
from download_ui import DownloadUI

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
BASE_URL = "https://www.estrategiaconcursos.com.br"
MY_COURSES_URL = urljoin(BASE_URL, "/app/dashboard/cursos")

# Prefixos de URL reconhecidos pelo script no modo --curso
_URL_PREFIXO_PACOTE = "/app/dashboard/pacote/"
_URL_PREFIXO_CURSOS = "/app/dashboard/cursos/"

# ---------------------------------------------------------------------------
# Sessão HTTP Persistente
# ---------------------------------------------------------------------------

def create_http_session():
    """
    Cria uma sessão requests reutilizável com pool de conexões (HTTP Keep-Alive)
    e política de retries com backoff exponencial para quedas temporárias de rede.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Funções Auxiliares
# ---------------------------------------------------------------------------

def sanitize_filename(original_filename, max_length=None):
    """
    Remove caracteres inválidos de um nome de arquivo/diretório para garantir
    compatibilidade com o sistema de arquivos.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '', original_filename)
    sanitized = re.sub(r'[.,]', '', sanitized)
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    sanitized = sanitized.strip('._- ')
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('._- ')
    return sanitized.strip()


def download_file(
    url,
    file_path,
    session_cookies=None,
    current_page_url=None,
    http_session=None,
    ui=None,
):
    """
    Realiza o download atômico de um arquivo usando requests e a interface visual Rich,
    transferindo os cookies da sessão do Selenium para autenticar a requisição.
    """
    if ui is None:
        ui = DownloadUI()

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        ),
    }
    if current_page_url:
        headers['Referer'] = current_page_url

    session = http_session if http_session is not None else requests.Session()
    if session_cookies:
        for cookie in session_cookies:
            session.cookies.set(cookie['name'], cookie['value'])

    filename = os.path.basename(file_path)

    try:
        response = session.get(url, stream=True, timeout=60, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            ui.log_warning(
                f"A resposta é HTML (possivelmente página de erro ou login expirado). "
                f"Content-Type={content_type!r}. Abortando download de '{filename}'."
            )
            return False

        # Delega streaming com progresso ao vivo e salvamento atômico em .part
        return ui.download_stream(response, file_path, filename)

    except requests.exceptions.HTTPError as e:
        ui.log_error(f"Erro HTTP ao baixar {filename}: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        ui.log_error(f"Erro de conexão ao baixar {filename}: {e}")
        return False
    except requests.exceptions.Timeout:
        ui.log_error(f"Tempo esgotado ao baixar {filename}.")
        return False
    except requests.exceptions.RequestException as e:
        ui.log_error(f"Erro de requisição ao baixar {filename}: {e}")
        return False
    except OSError as e:
        ui.log_error(f"Erro de I/O ao salvar {filename}: {e}")
        return False


def handle_popups(driver, ui=None):
    """Tenta fechar popups conhecidos que podem interceptar cliques."""
    try:
        getsitecontrol_widget = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.ID, "getsitecontrol-44266"))
        )
        if ui:
            ui.log_info("Widget 'getsitecontrol' detectado. Ocultando via JavaScript.")
        driver.execute_script("arguments[0].style.display = 'none';", getsitecontrol_widget)
        time.sleep(1)
    except TimeoutException:
        pass
    except Exception as e:
        if ui:
            ui.log_warning(f"Erro ao lidar com popups: {e}")


# ---------------------------------------------------------------------------
# Extração de dados
# ---------------------------------------------------------------------------

def get_course_data(driver, ui=None):
    """
    Navega até a página 'Minhas Matrículas' e extrai os links e títulos dos cursos.
    """
    if ui:
        ui.log_info("Navegando para a página 'Meus Cursos'...")
    else:
        print("Navegando para a página 'Meus Cursos'...")
    driver.get(MY_COURSES_URL)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "section[id^='card'] a[href*='/app/dashboard/cursos/']")
            )
        )
        time.sleep(2)
    except TimeoutException:
        msg = (
            "Tempo esgotado ao aguardar os cards de cursos. "
            "Verifique se o login foi realizado corretamente."
        )
        if ui:
            ui.log_error(msg)
        else:
            print(f"ERRO: {msg}")
        return []

    course_elements = driver.find_elements(
        By.CSS_SELECTOR, "section[id^='card']"
    )
    courses = []
    for course_elem in course_elements:
        try:
            link_elem = course_elem.find_element(
                By.CSS_SELECTOR, "a[href*='/app/dashboard/cursos/']"
            )
            title_elem = course_elem.find_element(By.CSS_SELECTOR, "h1")
            course_href = link_elem.get_attribute('href')
            course_title = title_elem.text.strip()
            if course_href and course_title:
                if course_href.startswith('/'):
                    course_href = urljoin(BASE_URL, course_href)
                courses.append({"title": course_title, "url": course_href})
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    msg = f"Encontrados {len(courses)} cursos."
    if ui:
        ui.log_info(msg)
    else:
        print(msg)
    return courses


def get_lesson_data(driver, course_url, ui=None):
    """
    Navega para a página de um curso e extrai os links, títulos e subtítulos
    das aulas.
    """
    if ui:
        ui.log_info(f"Navegando para a página do curso: {course_url}")
    else:
        print(f"   Navegando para a página do curso: {course_url}")
    driver.get(course_url)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.LessonList-item")
            )
        )
        time.sleep(2)
    except TimeoutException:
        msg = "Tempo esgotado ao carregar a lista de aulas."
        if ui:
            ui.log_warning(msg)
        else:
            print(f"   AVISO: {msg}")
        return []

    lesson_elements = driver.find_elements(By.CSS_SELECTOR, "div.LessonList-item")
    lessons = []
    for lesson_elem in lesson_elements:
        try:
            link_elem = lesson_elem.find_element(By.CSS_SELECTOR, "a.Collapse-header")
            lesson_href = link_elem.get_attribute('href')

            if not lesson_href or lesson_href.endswith('/aulas'):
                item_id = lesson_elem.get_attribute('id') or ''
                aula_id = item_id.replace('aula', '').strip()
                if aula_id:
                    lesson_href = urljoin(
                        course_url.rstrip('/') + '/', aula_id
                    )
                else:
                    continue

            if lesson_href.startswith('/'):
                lesson_href = urljoin(BASE_URL, lesson_href)

            title_h2_elem = lesson_elem.find_element(
                By.CSS_SELECTOR, "h2.SectionTitle"
            )
            lesson_title = title_h2_elem.text.strip()

            lesson_subtitle = ""
            try:
                subtitle_elem = lesson_elem.find_element(
                    By.CSS_SELECTOR,
                    "div.LessonCollapseHeader-title p"
                )
                lesson_subtitle = subtitle_elem.text.strip()
            except NoSuchElementException:
                pass

            if lesson_title:
                lessons.append({
                    "title": lesson_title,
                    "subtitle": lesson_subtitle,
                    "url": lesson_href,
                })
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    msg = f"Encontradas {len(lessons)} aulas disponíveis."
    if ui:
        ui.log_info(msg)
    else:
        print(f"    {msg}")
    return lessons


def get_courses_from_pacote(driver, pacote_url, ui=None):
    """
    Navega até a página de um pacote e retorna a lista de disciplinas (cursos)
    contidas nele: [{"title": str, "url": str}, ...]
    """
    if ui:
        ui.log_info(f"Navegando para a página do pacote: {pacote_url}")
    else:
        print(f"   Navegando para a página do pacote: {pacote_url}")
    driver.get(pacote_url)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.containerCursos"))
        )
        time.sleep(2)
    except TimeoutException:
        msg = (
            "Tempo esgotado ao aguardar a lista de disciplinas do pacote. "
            "A URL pode ser inválida, o pacote não existe, ou você não tem acesso."
        )
        if ui:
            ui.log_error(msg)
        else:
            print(f"   ERRO: {msg}")
        return [], ""

    pacote_title = ""
    try:
        titulo_elem = driver.find_element(By.CSS_SELECTOR, "h2.SectionTitle")
        pacote_title = titulo_elem.text.strip()
    except NoSuchElementException:
        pacote_title = f"Pacote_{pacote_url.rstrip('/').split('/')[-1]}"

    discipline_links = driver.find_elements(
        By.CSS_SELECTOR,
        "div.containerCursos a[href*='/cursos/']"
    )

    courses = []
    seen_hrefs = set()
    for link_elem in discipline_links:
        try:
            href = link_elem.get_attribute("href") or ""
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            if href.startswith("/"):
                href = urljoin(BASE_URL, href)

            title = ""
            try:
                p_elem = link_elem.find_element(By.CSS_SELECTOR, "div.boxCurso p")
                title = p_elem.text.strip()
            except NoSuchElementException:
                title = link_elem.text.strip()

            if not title:
                title = href.rstrip("/").split("/")[-2]

            if not href.endswith("/aulas"):
                href = href.rstrip("/") + "/aulas"

            courses.append({"title": title, "url": href})

        except StaleElementReferenceException:
            pass

    msg = f"Encontradas {len(courses)} disciplinas no pacote."
    if ui:
        ui.log_info(msg)
    else:
        print(f"   {msg}")
    return courses, pacote_title


# ---------------------------------------------------------------------------
# Download de Materiais e Vídeos
# ---------------------------------------------------------------------------

def download_video_materials(
    driver,
    lesson_info,
    course_title,
    lesson_download_path,
    preferred_quality="720p",
    http_session=None,
    ui=None,
):
    """
    Extrai a playlist de vídeos da aula, baixa os materiais de apoio de cada vídeo
    (Resumos, Slides, Mapas Mentais) e a videoaula no formato .mp4 na qualidade desejada.
    """
    if ui is None:
        ui = DownloadUI()

    # Busca a playlist de vídeos com múltiplos seletores de fallback
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
        ui.log_info("Nenhum vídeo disponível na playlist desta aula.")
        return []

    videos_to_download = []
    seen_video_urls = set()
    for item in playlist_items:
        try:
            video_href = item.get_attribute('href')
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

            videos_to_download.append({'url': video_href, 'title': video_title})
        except StaleElementReferenceException:
            pass

    if not videos_to_download:
        ui.log_info("Nenhum link de vídeo derivável encontrado.")
        return []

    total_videos = len(videos_to_download)
    ui.log_video_playlist(total_videos)

    # Ordem de preferência de qualidade com fallback inteligente
    if preferred_quality == "720p":
        qualities_order = ["720p", "480p", "360p"]
    elif preferred_quality == "480p":
        qualities_order = ["480p", "360p", "720p"]
    else:
        qualities_order = ["360p", "480p", "720p"]

    downloaded_files = []

    for idx, video_info in enumerate(videos_to_download, start=1):
        video_url = video_info['url']
        video_title = video_info['title']
        sanitized_video_title = sanitize_filename(video_title, max_length=80)
        sanitized_lesson_title = sanitize_filename(lesson_info['title'])

        # Checa se o vídeo já existe no disco em qualquer qualidade válida (> 10KB)
        existing_video = None
        for q in qualities_order:
            candidate_name = f"{sanitized_video_title}_Video_{q}.mp4"
            candidate_path = os.path.join(lesson_download_path, candidate_name)
            if os.path.exists(candidate_path) and os.path.getsize(candidate_path) > 10240:
                existing_video = candidate_name
                break

        if existing_video:
            ui.log_video_skip(idx, total_videos, video_title)
            downloaded_files.append(existing_video)
            continue

        ui.log_video_start(idx, total_videos, video_title)
        driver.get(video_url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.Video, div.VideoPlayer, a.LessonButton, div.Collapse-header")
                )
            )
            time.sleep(1)
        except TimeoutException:
            ui.log_warning(f"Tempo esgotado ao carregar vídeo '{video_title}'. Pulando.")
            continue

        handle_popups(driver, ui=ui)
        selenium_cookies = driver.get_cookies()

        # A. Baixa PDFs de apoio específicos deste bloco de vídeo
        video_pdf_types = {
            "Baixar Resumo": f"_Resumo_{idx}.pdf",
            "Baixar Slides": f"_Slides_Video_{idx}.pdf",
            "Baixar Mapa Mental": f"_Mapa_Mental_{idx}.pdf",
        }

        for pdf_button_text, filename_suffix in video_pdf_types.items():
            try:
                pdf_link_elem = driver.find_element(
                    By.XPATH,
                    f"//a[contains(@class, 'LessonButton') and .//span[contains(text(), '{pdf_button_text}')]]"
                )
                pdf_url = pdf_link_elem.get_attribute('href')
                if pdf_url and 'api.estrategiaconcursos.com.br' in pdf_url:
                    support_filename = f"{sanitized_lesson_title}_{sanitized_video_title}{filename_suffix}"
                    support_path = os.path.join(lesson_download_path, support_filename)
                    if os.path.exists(support_path) and os.path.getsize(support_path) > 1024:
                        downloaded_files.append(support_filename)
                    else:
                        ui.log_info(f"Encontrado {pdf_button_text} para o vídeo '{video_title}'.")
                        if download_file(
                            url=pdf_url,
                            file_path=support_path,
                            session_cookies=selenium_cookies,
                            current_page_url=driver.current_url,
                            http_session=http_session,
                            ui=ui,
                        ):
                            downloaded_files.append(support_filename)
            except NoSuchElementException:
                pass
            except Exception as e:
                ui.log_warning(f"Erro ao processar '{pdf_button_text}' do vídeo: {e}")

        # B. Expande a seção 'Opções de download' do vídeo
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

        # C. Localiza o link na qualidade preferencial e efetua o download
        video_downloaded = False
        for quality in qualities_order:
            video_filename = f"{sanitized_video_title}_Video_{quality}.mp4"
            video_path = os.path.join(lesson_download_path, video_filename)

            try:
                video_link_elem = driver.find_element(
                    By.XPATH,
                    f"//a[contains(text(), '{quality}')] | //a[contains(@href, '{quality}')]"
                )
                video_url = video_link_elem.get_attribute('href')
                if video_url:
                    ui.log_info(f"Baixando vídeo em {quality}...")
                    if download_file(
                        url=video_url,
                        file_path=video_path,
                        session_cookies=selenium_cookies,
                        current_page_url=driver.current_url,
                        http_session=http_session,
                        ui=ui,
                    ):
                        downloaded_files.append(video_filename)
                        video_downloaded = True
                        break
            except NoSuchElementException:
                continue
            except Exception as e:
                ui.log_warning(f"Falha ao tentar baixar vídeo em {quality}: {e}")

        if not video_downloaded:
            ui.log_warning(f"Não foi possível baixar nenhuma qualidade para o vídeo '{video_title}'.")

        time.sleep(1)

    return downloaded_files


def download_lesson_materials(
    driver,
    lesson_info,
    course_title,
    download_dir,
    http_session=None,
    ui=None,
    state_manager=None,
    download_videos: bool = False,
    preferred_quality: str = "720p",
):
    """
    Navega para a página de uma aula, salva o subtítulo, baixa os PDFs e,
    se download_videos=True, baixa os vídeos da playlist e seus apoios.
    Atualiza o estado persistente caso todas as etapas tenham sucesso.
    """
    if ui is None:
        ui = DownloadUI()

    lesson_title = lesson_info['title']
    lesson_subtitle = lesson_info['subtitle']
    lesson_url = lesson_info['url']

    ui.log_info(f"Acessando aula no navegador: {lesson_title}")
    driver.get(lesson_url)

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.Lesson-contentTop, div.LessonButtonList, div.LessonList")
            )
        )
        time.sleep(1)
    except TimeoutException:
        ui.log_warning(
            f"Tempo esgotado ao carregar a página da aula '{lesson_title}'. "
            f"A aula pode não ter conteúdo visível. Pulando."
        )
        return False

    handle_popups(driver, ui=ui)

    sanitized_course_title = sanitize_filename(course_title)
    sanitized_lesson_title = sanitize_filename(lesson_title)

    lesson_download_path = os.path.join(
        download_dir, sanitized_course_title, sanitized_lesson_title
    )

    try:
        os.makedirs(lesson_download_path, exist_ok=True)
    except OSError as e:
        ui.log_error(f"Erro ao criar diretório '{lesson_download_path}': {e}")
        return False

    # Salva o subtítulo (assuntos da aula) em arquivo de texto
    if lesson_subtitle:
        subjects_file_path = os.path.join(lesson_download_path, "Assuntos_dessa_aula.txt")
        if not os.path.exists(subjects_file_path):
            try:
                with open(subjects_file_path, 'w', encoding='utf-8') as f:
                    f.write(lesson_subtitle)
            except OSError as e:
                ui.log_warning(f"Erro ao criar 'Assuntos_dessa_aula.txt': {e}")

    # Captura os cookies da sessão autenticada do Selenium
    selenium_cookies = driver.get_cookies()

    all_downloads_ok = True
    downloaded_files = []

    try:
        pdf_links = driver.find_elements(By.CSS_SELECTOR, "a.LessonButton")
        pdfs_encontrados = 0

        for pdf_link in pdf_links:
            pdf_url = pdf_link.get_attribute('href') or ''

            if 'api.estrategiaconcursos.com.br' not in pdf_url:
                continue

            pdfs_encontrados += 1

            pdf_text_raw = "original"
            try:
                version_span = pdf_link.find_element(
                    By.CSS_SELECTOR, "span.LessonButton-text > span"
                )
                pdf_text_raw = version_span.text.strip()
            except NoSuchElementException:
                try:
                    full_text = pdf_link.find_element(
                        By.CSS_SELECTOR, "span.LessonButton-text"
                    ).text.strip()
                    if full_text:
                        pdf_text_raw = re.sub(
                            r'^baixar\s+livro\s+eletrônico\s*', '',
                            full_text, flags=re.IGNORECASE
                        ).strip() or "original"
                except NoSuchElementException:
                    pass

            filename_suffix = "_" + sanitize_filename(pdf_text_raw) if pdf_text_raw else ""
            filename = f"{sanitized_lesson_title}_Livro_Eletronico{filename_suffix}.pdf"
            full_file_path = os.path.join(lesson_download_path, filename)

            # Se o arquivo já existe no disco com tamanho válido (> 1KB), pula
            if os.path.exists(full_file_path) and os.path.getsize(full_file_path) > 1024:
                ui.log_info(f"PDF '{filename}' já existe no disco. Pulando.")
                downloaded_files.append(filename)
                continue

            ui.log_info(f"Encontrado PDF: versão '{pdf_text_raw}'")
            ok = download_file(
                url=pdf_url,
                file_path=full_file_path,
                session_cookies=selenium_cookies,
                current_page_url=driver.current_url,
                http_session=http_session,
                ui=ui,
            )
            if ok:
                downloaded_files.append(filename)
            else:
                all_downloads_ok = False

        if pdfs_encontrados == 0:
            ui.log_info("Nenhum PDF encontrado nesta aula.")

        # Se solicitado, baixa as videoaulas e apoios da playlist
        if download_videos:
            video_files = download_video_materials(
                driver=driver,
                lesson_info=lesson_info,
                course_title=course_title,
                lesson_download_path=lesson_download_path,
                preferred_quality=preferred_quality,
                http_session=http_session,
                ui=ui,
            )
            downloaded_files.extend(video_files)

        # Se todos os downloads foram bem-sucedidos, registra no estado persistente
        if all_downloads_ok and state_manager:
            state_manager.mark_lesson_completed(
                course_title,
                lesson_title,
                downloaded_files,
                videos_completed=download_videos,
            )

        return all_downloads_ok

    except StaleElementReferenceException:
        ui.log_warning("Elemento de PDF ficou obsoleto durante o processamento.")
        return False
    except WebDriverException as e:
        ui.log_error(f"Erro do WebDriver ao processar aula: {e}")
        return False
    except Exception as e:
        ui.log_error(f"Erro inesperado ao processar aula: {e}")
        return False


# ---------------------------------------------------------------------------
# Processador de Cursos / Disciplinas com Smart Resume
# ---------------------------------------------------------------------------

def process_courses(
    driver,
    courses,
    target_download_dir,
    ui,
    http_session,
    state_mgr,
    force: bool = False,
    download_videos: bool = False,
    preferred_quality: str = "720p",
):
    """
    Executa a iteração sobre disciplinas e aulas de forma inteligente:
    - Pula instantaneamente disciplinas já concluídas no histórico (0s Selenium).
    - Se encontrar pasta em disco de sessões anteriores, faz bootstrap rápido.
    - Para disciplinas incompletas, pula direto para as aulas pendentes.
    - Salva estado atômico a cada aula e disciplina.
    """
    total_cursos = len(courses)

    for i, course in enumerate(courses, start=1):
        disciplina_title = course["title"]
        disciplina_url = course["url"]

        # 1. Pulo instantâneo se a disciplina já está concluída no histórico
        if not force and state_mgr.is_discipline_completed(disciplina_title, check_videos=download_videos):
            ui.log_discipline_skip(
                i,
                total_cursos,
                disciplina_title,
                reason="Já concluída no histórico (.download_state.json)",
            )
            continue

        ui.log_discipline_start(i, total_cursos, disciplina_title)

        lessons = get_lesson_data(driver, disciplina_url, ui=ui)
        if not lessons:
            ui.log_warning(f"Nenhuma aula encontrada para '{disciplina_title}'. Pulando.")
            continue

        # 2. Bootstrap inteligente: verifica se todos os arquivos já estão no disco
        if not force and state_mgr.bootstrap_from_disk(disciplina_title, lessons, check_videos=download_videos):
            ui.log_discipline_skip(
                i,
                total_cursos,
                disciplina_title,
                reason="Todas as aulas já no disco (sincronizado automaticamente)",
            )
            continue

        # 3. Itera sobre as aulas da disciplina
        all_lessons_ok = True
        for j, lesson_info in enumerate(lessons, start=1):
            lesson_title = lesson_info['title']

            # Pula aula se já concluída no histórico
            if not force and state_mgr.is_lesson_completed(disciplina_title, lesson_title, check_videos=download_videos):
                ui.log_lesson_skip(j, len(lessons), lesson_title)
                continue

            ui.log_lesson_start(j, len(lessons), lesson_title)
            success = download_lesson_materials(
                driver=driver,
                lesson_info=lesson_info,
                course_title=disciplina_title,
                download_dir=target_download_dir,
                http_session=http_session,
                ui=ui,
                state_manager=state_mgr,
                download_videos=download_videos,
                preferred_quality=preferred_quality,
            )
            if not success:
                all_lessons_ok = False

            # Pausa suave apenas quando realmente navegamos e baixamos nova aula
            time.sleep(1)

        if all_lessons_ok:
            state_mgr.mark_discipline_completed(
                disciplina_title, len(lessons), videos_completed=download_videos
            )
            ui.log_discipline_completed(i, total_cursos, disciplina_title, len(lessons))


# ---------------------------------------------------------------------------
# Fluxo de curso único (modo --curso)
# ---------------------------------------------------------------------------

def _normalizar_url_curso(entrada):
    """
    Aceita URL completa, ID numérico ou caminho relativo e retorna a URL canônica.
    """
    entrada = entrada.strip()

    if re.fullmatch(r"\d+", entrada):
        return urljoin(BASE_URL, f"{_URL_PREFIXO_PACOTE}{entrada}")

    parsed = urlparse(entrada)
    if parsed.scheme in ("http", "https"):
        if "estrategiaconcursos.com.br" not in parsed.netloc:
            raise ValueError(
                f"A URL não pertence ao domínio estrategiaconcursos.com.br: {entrada!r}"
            )
        return entrada

    if entrada.startswith("/"):
        return urljoin(BASE_URL, entrada)

    raise ValueError(
        f"Não foi possível interpretar a entrada como URL ou ID de pacote: {entrada!r}\n"
        f"Use uma URL completa ou apenas o ID numérico."
    )


def download_single_course(
    driver,
    curso_input,
    download_dir,
    force=False,
    no_color=False,
    download_videos=False,
    preferred_quality="720p",
):
    """
    Baixa todos os materiais de um pacote ou curso individual com smart resume e UI Rich.
    """
    ui = DownloadUI(no_color=no_color)
    http_session = create_http_session()

    try:
        url = _normalizar_url_curso(curso_input)
    except ValueError as e:
        ui.log_error(str(e))
        return

    parsed_path = urlparse(url).path

    if _URL_PREFIXO_PACOTE in parsed_path:
        courses, pacote_title = get_courses_from_pacote(driver, url, ui=ui)
        if not courses:
            ui.log_error(
                "Nenhuma disciplina encontrada no pacote. "
                "Verifique se a URL está correta e se você tem acesso a esse pacote."
            )
            return

        folder_title = pacote_title or f"Pacote_{parsed_path.rstrip('/').split('/')[-1]}"
        target_download_dir = os.path.join(download_dir, sanitize_filename(folder_title))
        mode_label = "Pacote de Disciplinas"

    elif _URL_PREFIXO_CURSOS in parsed_path:
        curso_url = url if url.endswith("/aulas") else url.rstrip("/") + "/aulas"
        ui.log_info("Obtendo título do curso...")
        driver.get(curso_url)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.LessonList-item, div.CourseInfo")
                )
            )
            time.sleep(2)
        except TimeoutException:
            pass

        folder_title = ""
        try:
            titulo_elem = driver.find_element(
                By.CSS_SELECTOR,
                "div.CourseInfo-content-title, h1.ScreenHeader-title, h1"
            )
            folder_title = titulo_elem.text.strip()
        except NoSuchElementException:
            folder_title = f"Curso_{parsed_path.rstrip('/').split('/')[-2]}"

        courses = [{"title": folder_title, "url": curso_url}]
        target_download_dir = download_dir
        mode_label = "Curso Individual"

    else:
        ui.log_error(
            f"URL não reconhecida como pacote nem como curso individual.\n"
            f"  Esperado: .../pacote/{{id}} ou .../cursos/{{id}}/aulas\n"
            f"  Recebido: {url}"
        )
        return

    state_mgr = DownloadStateManager(target_download_dir, sanitize_func=sanitize_filename)
    mode_description = f"{mode_label} (Vídeos: {'Sim [' + preferred_quality + ']' if download_videos else 'Não'})"
    ui.print_banner(mode_description, target_download_dir, folder_title, len(courses))

    process_courses(
        driver=driver,
        courses=courses,
        target_download_dir=target_download_dir,
        ui=ui,
        http_session=http_session,
        state_mgr=state_mgr,
        force=force,
        download_videos=download_videos,
        preferred_quality=preferred_quality,
    )


# ---------------------------------------------------------------------------
# Login automatizado
# ---------------------------------------------------------------------------

def login(driver, email, senha, wait_time, ui=None):
    """
    Realiza o login automaticamente usando as credenciais fornecidas.
    Se o login automático falhar, aguarda `wait_time` segundos para login manual.
    """
    if ui:
        ui.log_info("Navegando para a página de login...")
    else:
        print("Navegando para a página de login...")
    driver.get("https://perfil.estrategia.com/login")
    time.sleep(3)

    login_automatico_ok = False

    if email and senha:
        if ui:
            ui.log_info("Tentando login automático...")
        else:
            print("Tentando login automático...")
        try:
            email_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='email'], input[name='email']")
                )
            )
            email_input.clear()
            email_input.send_keys(email)

            senha_input = driver.find_element(
                By.CSS_SELECTOR, "input[type='password']"
            )
            senha_input.clear()
            senha_input.send_keys(senha)

            submit_btn = driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
            )
            submit_btn.click()

            time.sleep(6)

            url_atual = driver.current_url
            if 'login' not in url_atual and 'perfil.estrategia.com' in url_atual:
                if ui:
                    ui.log_success(f"Login automático bem-sucedido. URL: {url_atual}")
                else:
                    print(f"Login automático bem-sucedido. URL: {url_atual}")
                login_automatico_ok = True
            else:
                if ui:
                    ui.log_warning(f"Login automático pode ter falhado. URL atual: {url_atual}")
                else:
                    print(f"AVISO: Login automático pode ter falhado. URL atual: {url_atual}")

        except (TimeoutException, NoSuchElementException) as e:
            if ui:
                ui.log_warning(f"Não foi possível realizar login automático: {e}")
            else:
                print(f"AVISO: Não foi possível realizar login automático: {e}")

    if not login_automatico_ok:
        msg = (
            "=" * 60 + "\n"
            "AÇÃO NECESSÁRIA: FAÇA O LOGIN MANUALMENTE NO NAVEGADOR ABERTO\n"
            f"O script ficará pausado por {wait_time} segundos.\n"
            "Após o login, o script continuará automaticamente.\n"
            "NÃO feche o navegador.\n" +
            "=" * 60
        )
        if ui:
            ui.log_warning(msg)
        else:
            print(msg)
        time.sleep(wait_time)

    if ui:
        ui.log_info("Continuando o script...")
    else:
        print("Continuando o script...")


# ---------------------------------------------------------------------------
# Fluxo Principal
# ---------------------------------------------------------------------------

def _preparar_driver_e_login(download_dir, email, senha, login_wait_time, ui=None):
    """
    Cria o diretório de download, inicializa o WebDriver e realiza o login.
    Retorna o driver já autenticado.
    """
    try:
        os.makedirs(download_dir, exist_ok=True)
        if ui:
            ui.log_info(f"Diretório de download configurado: {os.path.abspath(download_dir)}")
        else:
            print(f"Diretório de download configurado: {os.path.abspath(download_dir)}")
    except OSError as e:
        if ui:
            ui.log_error(f"Não foi possível criar o diretório '{download_dir}': {e}")
        else:
            print(f"ERRO: Não foi possível criar o diretório '{download_dir}': {e}")
        sys.exit(1)

    try:
        from browser.driver_manager import create_driver
        driver = create_driver()
    except Exception:
        driver = webdriver.Edge()
        driver.maximize_window()
    login(driver, email, senha, login_wait_time, ui=ui)
    return driver


def run_downloader(
    download_dir,
    email,
    senha,
    login_wait_time,
    force=False,
    no_color=False,
    download_videos=False,
    preferred_quality="720p",
):
    """
    Modo batch: baixa os materiais de TODOS os cursos matriculados.
    """
    ui = DownloadUI(no_color=no_color)
    http_session = create_http_session()
    state_mgr = DownloadStateManager(download_dir, sanitize_func=sanitize_filename)

    driver = _preparar_driver_e_login(download_dir, email, senha, login_wait_time, ui=ui)

    try:
        courses = get_course_data(driver, ui=ui)
        if not courses:
            ui.log_warning("Nenhum curso encontrado ou erro ao carregar a página. Encerrando.")
            return

        mode_desc = f"Todos os Cursos Matriculados (Vídeos: {'Sim [' + preferred_quality + ']' if download_videos else 'Não'})"
        ui.print_banner(mode_desc, download_dir, total_items=len(courses))

        process_courses(
            driver=driver,
            courses=courses,
            target_download_dir=download_dir,
            ui=ui,
            http_session=http_session,
            state_mgr=state_mgr,
            force=force,
            download_videos=download_videos,
            preferred_quality=preferred_quality,
        )

    except KeyboardInterrupt:
        ui.log_warning("Interrompido pelo usuário.")
    except Exception as e:
        ui.log_error(f"Erro geral no script: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ui.log_info("Processo concluído. Fechando o navegador em 5 segundos.")
        time.sleep(5)
        driver.quit()


def run_single_course(
    download_dir,
    email,
    senha,
    login_wait_time,
    curso_input,
    force=False,
    no_color=False,
    download_videos=False,
    preferred_quality="720p",
):
    """
    Modo --curso: baixa os materiais de um pacote ou curso específico.
    """
    ui = DownloadUI(no_color=no_color)
    driver = _preparar_driver_e_login(download_dir, email, senha, login_wait_time, ui=ui)

    try:
        download_single_course(
            driver=driver,
            curso_input=curso_input,
            download_dir=download_dir,
            force=force,
            no_color=no_color,
            download_videos=download_videos,
            preferred_quality=preferred_quality,
        )
    except KeyboardInterrupt:
        ui.log_warning("Interrompido pelo usuário.")
    except Exception as e:
        ui.log_error(f"Erro ao processar curso/pacote: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ui.log_info("Processo concluído. Fechando o navegador em 5 segundos.")
        time.sleep(5)
        driver.quit()


def main():
    """
    Analisa os argumentos da linha de comando e despacha para o modo correto.
    """
    parser = argparse.ArgumentParser(
        description="Baixador inteligente de materiais (PDFs e Vídeos) do Estratégia Concursos.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        '-d', '--dir',
        dest='download_dir',
        metavar='PATH',
        type=str,
        default="E:/Estrategia",
        help="Caminho para a pasta onde os cursos serão salvos.\n(Padrão: E:/Estrategia)",
    )

    parser.add_argument(
        '-e', '--email',
        dest='email',
        metavar='EMAIL',
        type=str,
        default="",
        help="E-mail para login automático.",
    )

    parser.add_argument(
        '-p', '--senha',
        dest='senha',
        metavar='SENHA',
        type=str,
        default="",
        help="Senha para login automático.",
    )

    parser.add_argument(
        "-w", "--wait-time",
        type=int,
        default=60,
        help="Tempo (segundos) para aguardar login manual, caso o automático falhe.\n(Padrão: 60)",
    )

    parser.add_argument(
        "--curso",
        dest='curso',
        metavar='URL_OU_ID',
        type=str,
        default=None,
        help=(
            "URL completa ou ID numérico do pacote/curso a baixar.\n"
            "Quando informado, apenas esse curso/pacote é processado.\n"
            "Exemplos:\n"
            "  --curso 400565\n"
            "  --curso https://www.estrategiaconcursos.com.br/app/dashboard/pacote/400565\n"
            "  --curso https://www.estrategiaconcursos.com.br/app/dashboard/cursos/265813/aulas"
        ),
    )

    parser.add_argument(
        "--videos",
        dest='videos',
        action="store_true",
        default=False,
        help="Ativa o download das videoaulas da playlist e seus materiais de apoio (.mp4 e PDFs de vídeo).",
    )

    parser.add_argument(
        "--qualidade",
        dest='qualidade',
        type=str,
        choices=['720p', '480p', '360p'],
        default='720p',
        help="Qualidade preferencial dos vídeos (720p, 480p, 360p).\n(Padrão: 720p)",
    )

    parser.add_argument(
        "--force",
        dest='force',
        action="store_true",
        default=False,
        help="Força a re-verificação de todas as disciplinas e aulas no navegador,\nignorando o cache do .download_state.json.",
    )

    parser.add_argument(
        "--no-color",
        dest='no_color',
        action="store_true",
        default=False,
        help="Desativa cores e temas especiais no terminal.",
    )

    parser.add_argument(
        "--gui",
        dest='gui',
        action="store_true",
        default=False,
        help="Inicia a interface gráfica desktop (GUI) moderna.",
    )

    # Se nenhum argumento foi informado ou foi passado --gui explicitamente
    if len(sys.argv) == 1:
        try:
            from ui.gui.app import run_gui
            run_gui()
            return
        except Exception as e:
            print(f"[Aviso] Não foi possível iniciar a GUI automaticamente: {e}. Exibindo ajuda do terminal:")
            parser.print_help()
            return

    args = parser.parse_args()

    if args.gui:
        from ui.gui.app import run_gui
        run_gui()
        return

    # Verificação obrigatória de EULA/Termos no modo terminal
    from legal.license_verifier import verify_or_prompt_cli
    if not verify_or_prompt_cli():
        return

    if args.curso:
        run_single_course(
            download_dir=args.download_dir,
            email=args.email,
            senha=args.senha,
            login_wait_time=args.wait_time,
            curso_input=args.curso,
            force=args.force,
            no_color=args.no_color,
            download_videos=args.videos,
            preferred_quality=args.qualidade,
        )
    else:
        run_downloader(
            download_dir=args.download_dir,
            email=args.email,
            senha=args.senha,
            login_wait_time=args.wait_time,
            force=args.force,
            no_color=args.no_color,
            download_videos=args.videos,
            preferred_quality=args.qualidade,
        )


if __name__ == "__main__":
    _local_lib = os.path.expanduser("~/.local/usr/lib")
    if os.path.isdir(_local_lib) and sys.platform != "win32":
        _curr_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if _local_lib not in _curr_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{_local_lib}:{_curr_ld}"
            os.environ["TCL_LIBRARY"] = os.path.join(_local_lib, "tcl8.6")
            os.environ["TK_LIBRARY"] = os.path.join(_local_lib, "tk8.6")
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:])
    main()
