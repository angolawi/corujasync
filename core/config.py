import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

APP_NAME = "CorujaSync"


def get_app_dir() -> Path:
    """Retorna o diretório padrão de dados do aplicativo de acordo com o SO."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        app_dir = Path(base) / APP_NAME
    elif sys.platform == "darwin":
        app_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux e outros sistemas POSIX (XDG Base Directory)
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
        app_dir = Path(base) / APP_NAME.lower()

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_default_download_dir() -> str:
    """Retorna um diretório padrão de download amigável."""
    user_home = Path.home()
    preferred = user_home / "Downloads" / "Cursos"
    return str(preferred)


CONFIG_FILE_PATH = get_app_dir() / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "download_dir": get_default_download_dir(),
    "download_videos": False,
    "preferred_quality": "720p",
    "theme": "dark",  # "dark" ou "light"
    "eula_accepted": False,
    "eula_accepted_at": None,
    "rate_limit_delay_seconds": 1.0,
    "preferred_browser": "auto",  # "auto", "edge", "chrome", "firefox"
    "ota_selectors_enabled": True,
    "ota_selectors_url": "https://raw.githubusercontent.com/corujasync/corujasync/main/core/selectors.json",
}


def load_config() -> Dict[str, Any]:
    """Carrega as configurações salvas ou retorna as padrões."""
    cfg = DEFAULT_CONFIG.copy()
    config_path = Path(CONFIG_FILE_PATH)
    if not config_path.exists():
        for legacy_name in ("autoconcursodownloader", "AutoConcursoDownloader"):
            legacy_path = config_path.parent.parent / legacy_name / "config.json"
            if legacy_path.exists():
                try:
                    with open(legacy_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        if isinstance(saved, dict):
                            cfg.update(saved)
                            save_config(cfg)
                            return cfg
                except Exception:
                    pass

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    cfg.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    """Salva as configurações de forma atômica no arquivo JSON."""
    try:
        config_path = Path(CONFIG_FILE_PATH)
        temp_file = config_path.parent / f"{config_path.name}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        temp_file.replace(config_path)
    except OSError as e:
        print(f"[Aviso] Falha ao salvar configurações do app: {e}")
