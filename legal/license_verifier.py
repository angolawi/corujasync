from datetime import datetime
from typing import Tuple
from core.config import load_config, save_config
from legal.eula_text import EULA_TITLE, EULA_FULL_TEXT


def is_eula_accepted() -> bool:
    """Verifica se o usuário já aceitou os termos de responsabilidade."""
    cfg = load_config()
    return bool(cfg.get("eula_accepted", False))


def accept_eula() -> None:
    """Registra a aceitação dos termos com carimbo de data/hora no arquivo de configuração local."""
    cfg = load_config()
    cfg["eula_accepted"] = True
    cfg["eula_accepted_at"] = datetime.now().isoformat()
    save_config(cfg)


def verify_or_prompt_cli() -> bool:
    """
    Exibe os termos no terminal e solicita confirmação explícita do usuário caso ainda não aceito.
    Retorna True se aceito, False se rejeitado.
    """
    if is_eula_accepted():
        return True

    print("\n" + "=" * 70)
    print(EULA_TITLE)
    print("=" * 70)
    print(EULA_FULL_TEXT)
    print("=" * 70)

    try:
        resp = input("\nVocê leu, compreendeu e concorda integralmente com estes termos? (s/N): ").strip().lower()
        if resp in ("s", "sim", "y", "yes"):
            accept_eula()
            print("[✓] Termos aceitos. Prosseguindo...\n")
            return True
        else:
            print("\n[!] O uso do software requer concordância com os termos. Execução cancelada.\n")
            return False
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.")
        return False
