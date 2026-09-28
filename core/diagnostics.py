import os
import re
import sys
import json
import time
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.config import get_app_dir

CPF_REGEX = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
TOKEN_REGEX = re.compile(r"(token|bearer|jwt|auth|password|senha)=['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE)


def sanitize_sensitive_data(text: str) -> str:
    """
    Remove ou ofusca dados sensíveis (CPF, e-mails, senhas e tokens de autenticação)
    em conformidade com a LGPD e privacidade do usuário.
    """
    if not text:
        return ""

    # Máscara de CPF
    def _mask_cpf(m):
        raw = m.group(0)
        return "***.***.***-**" if len(raw) > 11 else "***"

    sanitized = CPF_REGEX.sub(_mask_cpf, text)

    # Máscara de E-mail
    def _mask_email(m):
        email = m.group(0)
        parts = email.split("@")
        if len(parts) == 2:
            user, domain = parts
            masked_user = user[0] + "***" if len(user) > 0 else "***"
            return f"{masked_user}@{domain}"
        return "***@***"

    sanitized = EMAIL_REGEX.sub(_mask_email, sanitized)

    # Máscara de Senhas e Tokens
    sanitized = TOKEN_REGEX.sub(r"\1=***REDACTED***", sanitized)

    return sanitized


class DiagnosticsStore:
    """
    Armazena em memória o histórico de operações, falhas e snapshots
    para geração sob demanda de relatórios de suporte.
    """
    _instance: Optional["DiagnosticsStore"] = None

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.last_failure: Optional[Dict[str, Any]] = None
        self.session_started_at = datetime.now().isoformat()

    @classmethod
    def get_instance(cls) -> "DiagnosticsStore":
        if cls._instance is None:
            cls._instance = DiagnosticsStore()
        return cls._instance

    def record_event(self, level: str, message: str) -> None:
        """Registra um evento operacional."""
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": sanitize_sensitive_data(message),
        })
        # Mantém até 300 eventos mais recentes
        if len(self.events) > 300:
            self.events.pop(0)

    def record_failure(
        self,
        driver,
        expected_action: str,
        expected_selector: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Captura um snapshot semântico estruturado quando ocorre uma falha ou ausência de elemento."""
        snapshot = self._capture_semantic_snapshot(
            driver=driver,
            expected_action=expected_action,
            expected_selector=expected_selector,
            error_message=error_message,
        )
        self.last_failure = snapshot
        self.record_event(
            level="error",
            message=f"Falha registrada: Esperado '{expected_action}' ({expected_selector}). Erro: {error_message}",
        )
        return snapshot

    def _capture_semantic_snapshot(
        self,
        driver,
        expected_action: str,
        expected_selector: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspeciona o DOM atual sem extrair dados pessoais e compara o esperado com o encontrado."""
        now_iso = datetime.now().isoformat()
        if not driver:
            return {
                "timestamp": now_iso,
                "expected_action": expected_action,
                "expected_selector": expected_selector,
                "error": error_message or "Navegador não instanciado",
            }

        current_url = ""
        page_title = ""
        try:
            current_url = sanitize_sensitive_data(driver.current_url)
            page_title = driver.title
        except Exception:
            pass

        # Resumo semântico do DOM
        buttons_found = []
        links_found = []
        headings_found = []

        try:
            from selenium.webdriver.common.by import By
            # Localiza botões visíveis
            btn_elements = driver.find_elements(By.CSS_SELECTOR, "button, a.LessonButton, a[class*='btn']")
            for b in btn_elements[:15]:
                try:
                    txt = b.text.strip()
                    cls = b.get_attribute("class") or ""
                    tag = b.tag_name
                    if txt or cls:
                        buttons_found.append({
                            "tag": tag,
                            "class": cls,
                            "text": sanitize_sensitive_data(txt[:50]),
                        })
                except Exception:
                    pass

            # Localiza links relevantes
            link_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='download'], a[href*='api'], a[href*='aula']")
            for l in link_elements[:15]:
                try:
                    href = l.get_attribute("href") or ""
                    cls = l.get_attribute("class") or ""
                    links_found.append({
                        "class": cls,
                        "href_prefix": href.split("?")[0] if href else "",
                    })
                except Exception:
                    pass

            # Títulos da página
            h_elements = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3")
            for h in h_elements[:10]:
                try:
                    txt = h.text.strip()
                    if txt:
                        headings_found.append(sanitize_sensitive_data(txt[:60]))
                except Exception:
                    pass
        except Exception as e:
            self.record_event("warning", f"Erro parcial ao coletar resumo semântico: {e}")

        # Snippet seguro do código-fonte (primeiros 20KB higienizados)
        html_snippet = ""
        try:
            raw_html = driver.page_source or ""
            html_snippet = sanitize_sensitive_data(raw_html[:20480])
        except Exception:
            pass

        return {
            "timestamp": now_iso,
            "expected_action": expected_action,
            "expected_selector": expected_selector,
            "error_message": error_message,
            "current_url": current_url,
            "page_title": page_title,
            "dom_found": {
                "interactive_buttons_count": len(buttons_found),
                "buttons_sample": buttons_found,
                "relevant_links_count": len(links_found),
                "links_sample": links_found,
                "headings": headings_found,
            },
            "html_snippet_sample": html_snippet,
        }

    def generate_full_report(self) -> Dict[str, Any]:
        """Gera o dicionário completo do relatório de diagnóstico pronto para exportação."""
        return {
            "report_generated_at": datetime.now().isoformat(),
            "session_started_at": self.session_started_at,
            "environment": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "os": platform.system(),
                "release": platform.release(),
            },
            "last_failure": self.last_failure,
            "event_log_tail": self.events[-100:],
        }

    def export_report_file(self, target_path: Optional[str] = None) -> str:
        """Exporta o relatório para arquivo .json sanitizado."""
        report = self.generate_full_report()
        if not target_path:
            filename = f"diagnostico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            target_path = str(get_app_dir() / filename)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return target_path
