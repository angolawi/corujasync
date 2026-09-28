import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)

from core.config import get_app_dir, load_config

BY_MAP = {
    "css": By.CSS_SELECTOR,
    "xpath": By.XPATH,
    "id": By.ID,
    "name": By.NAME,
    "class": By.CLASS_NAME,
    "tag": By.TAG_NAME,
}

DEFAULT_OTA_URL = "https://raw.githubusercontent.com/corujasync/corujasync/main/core/selectors.json"
CACHE_TTL_SECONDS = 86400  # 24 horas


class SelectorManager:
    """
    Gerenciador de seletores com suporte a fallbacks em cadeia,
    cache local no diretório do usuário e atualização remota Over-The-Air (OTA).
    """

    def __init__(
        self,
        bundled_file: Optional[Union[str, Path]] = None,
        cache_file: Optional[Union[str, Path]] = None,
        remote_url: Optional[str] = None,
    ):
        if bundled_file is None:
            bundled_file = Path(__file__).parent / "selectors.json"
        self.bundled_file = Path(bundled_file)

        if cache_file is None:
            cache_file = get_app_dir() / "selectors_cache.json"
        self.cache_file = Path(cache_file)

        self.remote_url = remote_url or DEFAULT_OTA_URL
        self.version = 1
        self.selectors: Dict[str, List[Dict[str, str]]] = {}
        self.last_sync_timestamp = 0.0

        self._lock = threading.Lock()
        self._load_selectors()

    def _normalize_entry(self, raw_entry: Any) -> List[Dict[str, str]]:
        """Converte strings ou listas de dicionários em formato padronizado."""
        normalized = []
        if isinstance(raw_entry, str):
            by = "xpath" if raw_entry.startswith(("//", "(")) else "css"
            normalized.append({"by": by, "value": raw_entry})
        elif isinstance(raw_entry, dict):
            normalized.append({
                "by": raw_entry.get("by", "css").lower(),
                "value": raw_entry.get("value", ""),
            })
        elif isinstance(raw_entry, list):
            for item in raw_entry:
                if isinstance(item, dict):
                    normalized.append({
                        "by": item.get("by", "css").lower(),
                        "value": item.get("value", ""),
                    })
                elif isinstance(item, str):
                    by = "xpath" if item.startswith(("//", "(")) else "css"
                    normalized.append({"by": by, "value": item})
        return normalized

    def _load_selectors(self) -> None:
        """Carrega seletores do pacote embutido e mescla com cache local mais recente."""
        # 1. Carrega seletores embutidos no pacote
        bundled_data = {}
        if self.bundled_file.exists():
            try:
                with open(self.bundled_file, "r", encoding="utf-8") as f:
                    bundled_data = json.load(f)
            except Exception as e:
                print(f"[Aviso] Falha ao ler seletores embutidos: {e}")

        self.version = bundled_data.get("version", 1)
        raw_selectors = bundled_data.get("selectors", {})
        for k, v in raw_selectors.items():
            self.selectors[k] = self._normalize_entry(v)

        # 2. Carrega cache local se existir e for mais recente
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                cache_version = cache_data.get("version", 0)
                self.last_sync_timestamp = cache_data.get("last_sync_timestamp", 0.0)

                if cache_version >= self.version:
                    self.version = cache_version
                    cached_selectors = cache_data.get("selectors", {})
                    for k, v in cached_selectors.items():
                        self.selectors[k] = self._normalize_entry(v)
            except Exception as e:
                print(f"[Aviso] Falha ao carregar cache de seletores: {e}")

    def get_candidates(self, key: str, **kwargs) -> List[Tuple[By, str]]:
        """Retorna uma lista de tuplas (By, selector_string) para o seletor solicitado."""
        with self._lock:
            entries = self.selectors.get(key, [])

        result = []
        for item in entries:
            by_str = item.get("by", "css").lower()
            val = item.get("value", "")
            if kwargs:
                try:
                    val = val.format(**kwargs)
                except KeyError:
                    pass
            by_obj = BY_MAP.get(by_str, By.CSS_SELECTOR)
            result.append((by_obj, val))
        return result

    def find_elements(self, driver_or_elem, key: str, **kwargs) -> List[Any]:
        """Tenta encontrar elementos usando a cadeia ordenada de seletores de fallback."""
        candidates = self.get_candidates(key, **kwargs)
        for by_type, val in candidates:
            try:
                elems = driver_or_elem.find_elements(by_type, val)
                if elems:
                    return elems
            except (NoSuchElementException, WebDriverException):
                continue
        return []

    def find_element(self, driver_or_elem, key: str, **kwargs) -> Optional[Any]:
        """Retorna o primeiro elemento encontrado ou None se nenhum seletor casar."""
        candidates = self.get_candidates(key, **kwargs)
        for by_type, val in candidates:
            try:
                return driver_or_elem.find_element(by_type, val)
            except (NoSuchElementException, WebDriverException):
                continue
        return None

    def wait_presence(self, driver, key: str, timeout: float = 15, **kwargs) -> Any:
        """Aguarda a presença de qualquer um dos seletores candidatos."""
        candidates = self.get_candidates(key, **kwargs)
        if not candidates:
            raise NoSuchElementException(f"Nenhum seletor registrado para a chave '{key}'.")

        end_time = time.time() + timeout
        last_exception = None

        while time.time() < end_time:
            for by_type, val in candidates:
                try:
                    elem = driver.find_element(by_type, val)
                    if elem:
                        return elem
                except (NoSuchElementException, StaleElementReferenceException) as e:
                    last_exception = e
            time.sleep(0.5)

        raise TimeoutException(
            f"Tempo esgotado ({timeout}s) aguardando presença de '{key}' com candidatos: {candidates}"
        )

    def wait_all_present(self, driver, key: str, timeout: float = 15, **kwargs) -> List[Any]:
        """Aguarda até que elementos de algum candidato estejam presentes e retorna a lista."""
        candidates = self.get_candidates(key, **kwargs)
        if not candidates:
            raise NoSuchElementException(f"Nenhum seletor registrado para a chave '{key}'.")

        end_time = time.time() + timeout
        while time.time() < end_time:
            for by_type, val in candidates:
                try:
                    elems = driver.find_elements(by_type, val)
                    if elems:
                        return elems
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
            time.sleep(0.5)

        raise TimeoutException(
            f"Tempo esgotado ({timeout}s) aguardando lista de elementos para '{key}'."
        )

    def update_from_dict(self, data: Dict[str, Any], save_cache: bool = True) -> bool:
        """Atualiza a tabela de seletores em memória e opcionalmente salva no disco."""
        if not isinstance(data, dict):
            return False

        new_version = data.get("version", self.version)
        new_selectors = data.get("selectors", {})

        if not new_selectors:
            return False

        with self._lock:
            self.version = max(self.version, new_version)
            for k, v in new_selectors.items():
                self.selectors[k] = self._normalize_entry(v)
            self.last_sync_timestamp = time.time()

        if save_cache:
            self._save_cache()
        return True

    def _save_cache(self) -> None:
        """Grava o cache de seletores atual no diretório de dados do usuário."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_payload = {
                "version": self.version,
                "last_sync_timestamp": self.last_sync_timestamp,
                "selectors": self.selectors,
            }
            tmp = self.cache_file.parent / f"{self.cache_file.name}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cache_payload, f, indent=2, ensure_ascii=False)
            tmp.replace(self.cache_file)
        except OSError as e:
            print(f"[Aviso] Falha ao gravar cache de seletores: {e}")

    def fetch_remote(self, timeout: float = 3.0, force: bool = False) -> bool:
        """
        Sincroniza seletores via OTA a partir de URL remota.
        Não bloqueia se falhar (retorna False e mantém seletores locais).
        """
        cfg = load_config()
        if not cfg.get("ota_selectors_enabled", True) and not force:
            return False

        target_url = cfg.get("ota_selectors_url", self.remote_url)
        now = time.time()

        if not force and (now - self.last_sync_timestamp < CACHE_TTL_SECONDS):
            # Cache ainda é recente
            return False

        try:
            resp = requests.get(
                target_url,
                timeout=timeout,
                headers={"User-Agent": "CorujaSync/ResilientCrawler"},
            )
            if resp.status_code == 200:
                payload = resp.json()
                return self.update_from_dict(payload, save_cache=True)
        except Exception:
            # Em caso de erro de rede ou URL inválida, falha silenciosa
            pass
        return False

    def fetch_remote_async(self, timeout: float = 3.0) -> None:
        """Dispara a sincronização remota em segundo plano para não congelar o boot."""
        t = threading.Thread(target=self.fetch_remote, args=(timeout, False), daemon=True)
        t.start()


_global_selector_manager: Optional[SelectorManager] = None


def get_selector_manager() -> SelectorManager:
    """Retorna a instância singleton do SelectorManager."""
    global _global_selector_manager
    if _global_selector_manager is None:
        _global_selector_manager = SelectorManager()
    return _global_selector_manager
