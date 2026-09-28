import os
import sys
import json
import time
import hmac
import base64
import hashlib
import platform
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

from core.config import load_config, save_config

# Chave secreta de assinatura interna para validação offline de integridade
_DEFAULT_HMAC_SECRET = "AGY_CONCURSO_DL_SECRET_KEY_v1_2026_SECURE_AUTH"


def get_machine_id() -> str:
    """
    Gera um identificador único de máquina, anônimo e determinístico.
    Combina atributos de hardware sem expor dados pessoais do usuário.
    Formato: XXXX-XXXX-XXXX-XXXX
    """
    raw_id = f"{uuid.getnode()}:{platform.node()}:{platform.system()}:{platform.machine()}"
    digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest().upper()
    return f"{digest[0:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"


def generate_license_key(
    client_id: str,
    tier: str = "anual",
    machine_id: str = "ANY",
    days_valid: Optional[int] = 365,
    secret_key: str = _DEFAULT_HMAC_SECRET,
) -> str:
    """
    Gera uma chave criptográfica assinada para um cliente.
    Suporta planos: 'vitalicio' (sem expiração), 'anual' (365 dias), 'edital' (180 dias) ou customizado.
    Se machine_id for 'ANY', a licença é flutuante; caso contrário, é travada ao computador do cliente.
    """
    if days_valid is None or tier.lower() == "vitalicio":
        expires_at = "NEVER"
    else:
        exp_date = datetime.now() + timedelta(days=days_valid)
        expires_at = exp_date.strftime("%Y-%m-%d")

    payload = {
        "client": client_id.strip(),
        "tier": tier.lower().strip(),
        "machine_id": machine_id.strip(),
        "expires_at": expires_at,
        "issued_at": datetime.now().strftime("%Y-%m-%d"),
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")

    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16].upper()

    tier_tag = tier.upper()[:3]
    return f"CDL-{tier_tag}-{payload_b64}-{signature}"


def validate_license_key(
    key: str,
    secret_key: str = _DEFAULT_HMAC_SECRET,
    enforce_machine: bool = True,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verifica a autenticidade criptográfica (HMAC-SHA256), a data de validade
    e a compatibilidade de máquina da chave fornecida.
    """
    if not key or not isinstance(key, str):
        return False, "Chave de licença não fornecida.", {}

    parts = key.strip().split("-")
    if len(parts) != 4 or parts[0] != "CDL":
        return False, "Formato de chave inválido. Esperado padrão CDL-XXX-XXXX-XXXX.", {}

    tier_tag, payload_b64, signature = parts[1], parts[2], parts[3]

    # Verifica assinatura HMAC
    expected_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16].upper()

    if not hmac.compare_digest(signature, expected_sig):
        return False, "Assinatura digital da licença é inválida ou foi adulterada.", {}

    # Decodifica payload JSON
    try:
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        return False, "Falha ao decodificar os dados internos da licença.", {}

    # Verifica expiração
    expires_at = payload.get("expires_at", "")
    if expires_at and expires_at != "NEVER":
        try:
            exp_date = datetime.strptime(expires_at, "%Y-%m-%d").date()
            if datetime.now().date() > exp_date:
                return False, f"Esta licença expirou em {expires_at}.", payload
        except ValueError:
            return False, "Data de expiração com formato corrompido.", payload

    # Verifica vinculação de máquina
    bound_machine = payload.get("machine_id", "ANY")
    current_machine = get_machine_id()
    if enforce_machine and bound_machine != "ANY" and bound_machine != current_machine:
        return (
            False,
            f"Esta licença está vinculada ao computador ID '{bound_machine}' (computador atual: '{current_machine}').",
            payload,
        )

    return True, "Licença válida e ativa com sucesso!", payload


class LicenseManager:
    """Gerencia o ciclo de vida e ativação de licenças do software no cliente."""

    def __init__(self):
        self.current_machine_id = get_machine_id()

    def get_status(self) -> Dict[str, Any]:
        """Retorna o status completo da licença instalada."""
        cfg = load_config()
        key = cfg.get("license_key")

        if not key:
            return {
                "is_active": False,
                "tier": "trial",
                "client": "Não Ativado",
                "expires_at": "Modo Básico / Avaliação",
                "machine_id": self.current_machine_id,
                "message": "Nenhuma chave de licença premium instalada.",
                "license_key": None,
            }

        is_valid, msg, payload = validate_license_key(key)
        return {
            "is_active": is_valid,
            "tier": payload.get("tier", "inválido") if is_valid else "expirado/inválido",
            "client": payload.get("client", "Desconhecido"),
            "expires_at": payload.get("expires_at", "N/A"),
            "machine_id": self.current_machine_id,
            "message": msg,
            "license_key": key if is_valid else None,
        }

    def activate(self, key: str) -> Tuple[bool, str]:
        """Valida e persiste a chave de licença nas configurações."""
        is_valid, msg, payload = validate_license_key(key)
        if not is_valid:
            return False, msg

        cfg = load_config()
        cfg["license_key"] = key.strip()
        save_config(cfg)
        return True, f"Licença {payload.get('tier', '').upper()} ativada com sucesso para {payload.get('client')}!"

    def deactivate(self) -> None:
        """Remove a chave de licença ativa."""
        cfg = load_config()
        if "license_key" in cfg:
            cfg["license_key"] = None
            save_config(cfg)

    def is_premium(self) -> bool:
        """Indica se o cliente possui licença válida ativa."""
        status = self.get_status()
        return status.get("is_active", False)
