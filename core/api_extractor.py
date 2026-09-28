import json
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

BASE_URL = "https://www.estrategiaconcursos.com.br"


def get_next_data(driver) -> Optional[Dict[str, Any]]:
    """Tenta extrair o payload JSON do __NEXT_DATA__ (Next.js) do navegador."""
    try:
        data = driver.execute_script("return window.__NEXT_DATA__;")
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        from selenium.webdriver.common.by import By
        script_elem = driver.find_element(By.ID, "__NEXT_DATA__")
        if script_elem:
            content = script_elem.get_attribute("innerHTML") or script_elem.text
            if content:
                return json.loads(content)
    except Exception:
        pass

    return None


def get_window_state(driver) -> Optional[Dict[str, Any]]:
    """Tenta obter estados globais comuns em SPAs (Redux, Vuex, etc.)."""
    try:
        state = driver.execute_script(
            "return window.__INITIAL_STATE__ || window.__APP_INITIAL_STATE__ || window.__STATE__ || null;"
        )
        if isinstance(state, dict):
            return state
    except Exception:
        pass
    return None


def extract_auth_tokens(driver) -> Dict[str, str]:
    """Extrai tokens JWT ou Bearer do localStorage e sessionStorage do navegador."""
    tokens = {}
    try:
        storage_data = driver.execute_script("""
            var tokens = {};
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                if (key && (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth') || key.toLowerCase().includes('jwt'))) {
                    tokens[key] = localStorage.getItem(key);
                }
            }
            return tokens;
        """)
        if isinstance(storage_data, dict):
            tokens.update(storage_data)
    except Exception:
        pass
    return tokens


def extract_lessons_from_state(driver, course_url: str) -> Optional[List[Dict[str, str]]]:
    """
    Tenta extrair a lista estruturada de aulas a partir dos dados do estado da página,
    contornando completamente as classes CSS e o DOM.
    """
    next_data = get_next_data(driver) or get_window_state(driver)
    if not next_data:
        return None

    # Procura recursivamente por listas contendo aulas
    def _search_lessons(obj: Any) -> Optional[List[Dict[str, Any]]]:
        if isinstance(obj, dict):
            # Chaves comuns onde as aulas residem no payload
            for k in ("lessons", "aulas", "items", "courseLessons"):
                val = obj.get(k)
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    # Verifica se parece com aula (tem id, titulo/name/title)
                    sample = val[0]
                    if any(key in sample for key in ("title", "titulo", "name", "id")):
                        return val

            for v in obj.values():
                res = _search_lessons(v)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = _search_lessons(item)
                if res is not None:
                    return res
        return None

    lessons_raw = _search_lessons(next_data)
    if not lessons_raw:
        return None

    parsed_lessons: List[Dict[str, str]] = []
    for item in lessons_raw:
        title = item.get("title") or item.get("titulo") or item.get("name") or ""
        subtitle = item.get("subtitle") or item.get("subtitulo") or item.get("description") or ""
        lesson_id = str(item.get("id") or item.get("lesson_id") or item.get("aula_id") or "").strip()
        url = item.get("url") or ""

        if not url and lesson_id:
            url = urljoin(course_url.rstrip("/") + "/", lesson_id)
        elif url and url.startswith("/"):
            url = urljoin(BASE_URL, url)

        if title and url:
            parsed_lessons.append({
                "title": str(title).strip(),
                "subtitle": str(subtitle).strip(),
                "url": url,
            })

    return parsed_lessons if parsed_lessons else None


def extract_materials_from_page_source(page_source: str) -> Dict[str, List[str]]:
    """
    Analisa o código-fonte HTML da página em busca de URLs diretas de API para PDFs e vídeos.
    Útil como fallback de última linha quando botões foram modificados.
    """
    pdf_urls = re.findall(
        r'https?://api\.estrategiaconcursos\.com\.br/[^"\'\s>]+(?:download|livro|pdf)[^"\'\s>]*',
        page_source,
        flags=re.IGNORECASE,
    )
    # Deduplica preservando ordem
    seen_pdfs = set()
    unique_pdfs = []
    for u in pdf_urls:
        if u not in seen_pdfs:
            seen_pdfs.add(u)
            unique_pdfs.append(u)

    video_urls = re.findall(
        r'https?://[^"\'\s>]+\.(?:mp4|m3u8)[^"\'\s>]*',
        page_source,
        flags=re.IGNORECASE,
    )
    seen_videos = set()
    unique_videos = []
    for v in video_urls:
        if v not in seen_videos:
            seen_videos.add(v)
            unique_videos.append(v)

    return {
        "pdfs": unique_pdfs,
        "videos": unique_videos,
    }
