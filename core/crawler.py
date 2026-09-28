import re
import time
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Tuple, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from core.events import DownloadObserver, StatusEvent, VideoEvent
from core.downloader import sanitize_filename, download_file

BASE_URL = "https://www.estrategiaconcursos.com.br"
MY_COURSES_URL = urljoin(BASE_URL, "/app/dashboard/cursos")
URL_PREFIX_PACOTE = "/app/dashboard/pacote/"
URL_PREFIX_CURSOS = "/app/dashboard/cursos/"


def normalize_course_url(entrada: str) -> str:
    """Aceita URL completa, ID numérico ou caminho relativo e retorna a URL canônica."""
    entrada = entrada.strip()
    if re.fullmatch(r"\d+", entrada):
        return urljoin(BASE_URL, f"{URL_PREFIX_PACOTE}{entrada}")

    parsed = urlparse(entrada)
    if parsed.scheme in ("http", "https"):
        if "estrategiaconcursos.com.br" not in parsed.netloc:
            raise ValueError(f"A URL não pertence ao domínio estrategiaconcursos.com.br: {entrada!r}")
        return entrada

    if entrada.startswith("/"):
        return urljoin(BASE_URL, entrada)

    raise ValueError(
        f"Não foi possível interpretar a entrada como URL ou ID de pacote: {entrada!r}\n"
        f"Use uma URL completa ou apenas o ID numérico."
    )


def handle_popups(driver, observer: Optional[DownloadObserver] = None) -> None:
    """Tenta fechar popups conhecidos que podem interceptar cliques."""
    try:
        getsitecontrol_widget = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.ID, "getsitecontrol-44266"))
        )
        if observer:
            observer.on_status(StatusEvent(level="info", message="Widget 'getsitecontrol' detectado. Ocultando."))
        driver.execute_script("arguments[0].style.display = 'none';", getsitecontrol_widget)
        time.sleep(1)
    except TimeoutException:
        pass
    except Exception as e:
        if observer:
            observer.on_status(StatusEvent(level="warning", message=f"Erro ao lidar com popups: {e}"))


def login(
    driver,
    email: str,
    senha: str,
    wait_time: int = 60,
    observer: Optional[DownloadObserver] = None,
) -> bool:
    """
    Realiza o login automaticamente se credenciais forem fornecidas.
    Se falhar ou não houver credenciais, aguarda wait_time para login manual pelo usuário.
    """
    if observer:
        observer.on_status(StatusEvent(level="info", message="Navegando para a página de login..."))
    driver.get("https://perfil.estrategia.com/login")
    time.sleep(3)

    login_automatico_ok = False

    if email and senha:
        if observer:
            observer.on_status(StatusEvent(level="info", message="Tentando autenticação com credenciais salvas..."))
        try:
            email_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
            )
            email_input.clear()
            email_input.send_keys(email)

            senha_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            senha_input.clear()
            senha_input.send_keys(senha)

            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_btn.click()

            time.sleep(6)

            url_atual = driver.current_url
            if "login" not in url_atual and "perfil.estrategia.com" in url_atual:
                if observer:
                    observer.on_status(StatusEvent(level="success", message=f"Autenticação realizada com sucesso."))
                login_automatico_ok = True
            else:
                if observer:
                    observer.on_status(
                        StatusEvent(level="warning", message=f"Login automático pendente de confirmação.")
                    )

        except (TimeoutException, NoSuchElementException) as e:
            if observer:
                observer.on_status(StatusEvent(level="warning", message=f"Falha na tentativa de login automático: {e}"))

    if not login_automatico_ok:
        msg = (
            f"AÇÃO NECESSÁRIA: Faça login na janela do navegador aberta.\n"
            f"O aplicativo aguardará por {wait_time}s antes de continuar."
        )
        if observer:
            observer.on_status(StatusEvent(level="warning", message=msg))
        time.sleep(wait_time)

    return True


def get_course_data(driver, observer: Optional[DownloadObserver] = None) -> List[Dict[str, str]]:
    """Navega até a página 'Minhas Matrículas' e extrai os links e títulos dos cursos."""
    if observer:
        observer.on_status(StatusEvent(level="info", message="Navegando para 'Meus Cursos'..."))
    driver.get(MY_COURSES_URL)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "section[id^='card'] a[href*='/app/dashboard/cursos/']")
            )
        )
        time.sleep(2)
    except TimeoutException:
        if observer:
            observer.on_status(
                StatusEvent(
                    level="error",
                    message="Tempo esgotado ao aguardar os cursos. Verifique se o login foi concluído.",
                )
            )
        return []

    course_elements = driver.find_elements(By.CSS_SELECTOR, "section[id^='card']")
    courses = []
    for course_elem in course_elements:
        try:
            link_elem = course_elem.find_element(By.CSS_SELECTOR, "a[href*='/app/dashboard/cursos/']")
            title_elem = course_elem.find_element(By.CSS_SELECTOR, "h1")
            course_href = link_elem.get_attribute("href")
            course_title = title_elem.text.strip()
            if course_href and course_title:
                if course_href.startswith("/"):
                    course_href = urljoin(BASE_URL, course_href)
                courses.append({"title": course_title, "url": course_href})
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Encontrados {len(courses)} cursos."))
    return courses


def get_courses_from_pacote(
    driver,
    pacote_url: str,
    observer: Optional[DownloadObserver] = None,
) -> Tuple[List[Dict[str, str]], str]:
    """Navega até a página de um pacote e retorna a lista de disciplinas contidas nele."""
    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Acessando pacote: {pacote_url}"))
    driver.get(pacote_url)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.containerCursos"))
        )
        time.sleep(2)
    except TimeoutException:
        if observer:
            observer.on_status(
                StatusEvent(
                    level="error",
                    message="Tempo esgotado ao aguardar disciplinas do pacote. Verifique seu acesso.",
                )
            )
        return [], ""

    pacote_title = ""
    try:
        titulo_elem = driver.find_element(By.CSS_SELECTOR, "h2.SectionTitle")
        pacote_title = titulo_elem.text.strip()
    except NoSuchElementException:
        pacote_title = f"Pacote_{pacote_url.rstrip('/').split('/')[-1]}"

    discipline_links = driver.find_elements(
        By.CSS_SELECTOR, "div.containerCursos a[href*='/cursos/']"
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

    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Encontradas {len(courses)} disciplinas no pacote."))
    return courses, pacote_title


def get_lesson_data(
    driver,
    course_url: str,
    observer: Optional[DownloadObserver] = None,
) -> List[Dict[str, str]]:
    """Navega para a página de um curso e extrai a lista de aulas."""
    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Carregando aulas de: {course_url}"))
    driver.get(course_url)

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.LessonList-item"))
        )
        time.sleep(2)
    except TimeoutException:
        if observer:
            observer.on_status(StatusEvent(level="warning", message="Tempo esgotado ao carregar lista de aulas."))
        return []

    lesson_elements = driver.find_elements(By.CSS_SELECTOR, "div.LessonList-item")
    lessons = []
    for lesson_elem in lesson_elements:
        try:
            link_elem = lesson_elem.find_element(By.CSS_SELECTOR, "a.Collapse-header")
            lesson_href = link_elem.get_attribute("href")

            if not lesson_href or lesson_href.endswith("/aulas"):
                item_id = lesson_elem.get_attribute("id") or ""
                aula_id = item_id.replace("aula", "").strip()
                if aula_id:
                    lesson_href = urljoin(course_url.rstrip("/") + "/", aula_id)
                else:
                    continue

            if lesson_href.startswith("/"):
                lesson_href = urljoin(BASE_URL, lesson_href)

            title_h2_elem = lesson_elem.find_element(By.CSS_SELECTOR, "h2.SectionTitle")
            lesson_title = title_h2_elem.text.strip()

            lesson_subtitle = ""
            try:
                subtitle_elem = lesson_elem.find_element(
                    By.CSS_SELECTOR, "div.LessonCollapseHeader-title p"
                )
                lesson_subtitle = subtitle_elem.text.strip()
            except NoSuchElementException:
                pass

            if lesson_title:
                lessons.append(
                    {
                        "title": lesson_title,
                        "subtitle": lesson_subtitle,
                        "url": lesson_href,
                    }
                )
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    if observer:
        observer.on_status(StatusEvent(level="info", message=f"Encontradas {len(lessons)} aulas disponíveis."))
    return lessons
