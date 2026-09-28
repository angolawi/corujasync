from typing import Dict, Any, Callable
from tkinter import messagebox
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    create_card_frame,
    get_font,
)
from core.config import save_config


class SettingsView(ctk.CTkFrame):
    """
    Painel de configurações e preferências da aplicação:
    Credenciais locais, motor de navegador e delays operacionais.
    """

    def __init__(self, parent, config: Dict[str, Any], on_saved: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.on_saved = on_saved
        self.password_visible = False

        self._build_ui()

    def _build_ui(self):
        # 1. Card: Autenticação na Plataforma
        card_cred = create_card_frame(self)
        card_cred.pack(fill="x", padx=15, pady=(15, 10))

        lbl_cred_title = ctk.CTkLabel(
            card_cred,
            text="Autenticação na Plataforma",
            font=get_font(14, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_cred_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_cred_desc = ctk.CTkLabel(
            card_cred,
            text="Suas credenciais são armazenadas exclusivamente no arquivo de configuração local do seu computador.",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        lbl_cred_desc.pack(fill="x", padx=15, pady=(0, 10))

        # E-mail
        row_email = ctk.CTkFrame(card_cred, fg_color="transparent")
        row_email.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(row_email, text="E-mail:", width=110, anchor="w", font=get_font(12, "bold")).pack(side="left")
        self.entry_email = ctk.CTkEntry(row_email, width=320, font=get_font(12), height=34)
        self.entry_email.insert(0, self.config.get("email", ""))
        self.entry_email.pack(side="left")

        # Senha com botão de alternância de visibilidade
        row_pass = ctk.CTkFrame(card_cred, fg_color="transparent")
        row_pass.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(row_pass, text="Senha:", width=110, anchor="w", font=get_font(12, "bold")).pack(side="left")
        self.entry_senha = ctk.CTkEntry(row_pass, width=320, show="*", font=get_font(12), height=34)
        self.entry_senha.insert(0, self.config.get("senha", ""))
        self.entry_senha.pack(side="left", padx=(0, 6))

        self.btn_eye = ctk.CTkButton(
            row_pass,
            text="👁",
            width=34,
            height=34,
            font=get_font(13),
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=self._toggle_password,
        )
        self.btn_eye.pack(side="left")

        # Espera de Login Manual
        row_wait = ctk.CTkFrame(card_cred, fg_color="transparent")
        row_wait.pack(fill="x", padx=15, pady=(4, 15))
        ctk.CTkLabel(row_wait, text="Espera Login (s):", width=110, anchor="w", font=get_font(12)).pack(side="left")
        self.entry_wait = ctk.CTkEntry(row_wait, width=90, font=get_font(12), height=34)
        self.entry_wait.insert(0, str(self.config.get("wait_time", 60)))
        self.entry_wait.pack(side="left")

        # 2. Card: Motor de Navegador
        card_browser = create_card_frame(self)
        card_browser.pack(fill="x", padx=15, pady=5)

        lbl_browser_title = ctk.CTkLabel(
            card_browser,
            text="Motor de Navegador e Automação",
            font=get_font(14, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_browser_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_browser_desc = ctk.CTkLabel(
            card_browser,
            text="Selecione o navegador padrão. 'Auto' detecta automaticamente Edge, Chrome ou Firefox com fallback transparente.",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        lbl_browser_desc.pack(fill="x", padx=15, pady=(0, 10))

        row_b = ctk.CTkFrame(card_browser, fg_color="transparent")
        row_b.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(row_b, text="Navegador:", width=110, anchor="w", font=get_font(12, "bold")).pack(side="left")

        self.var_browser = ctk.StringVar(value=self.config.get("preferred_browser", "auto"))
        self.opt_browser = ctk.CTkOptionMenu(
            row_b,
            values=["auto", "edge", "chrome", "firefox"],
            variable=self.var_browser,
            font=get_font(12, "bold"),
            width=160,
            height=34,
        )
        self.opt_browser.pack(side="left")

        # 3. Botão de Salvar Preferências
        btn_save = ctk.CTkButton(
            self,
            text="💾 Salvar Preferências",
            font=get_font(13, "bold"),
            fg_color=THEME_COLORS["accent_primary"],
            hover_color=THEME_COLORS["accent_primary_hover"],
            height=38,
            width=180,
            command=self._save_settings,
        )
        btn_save.pack(anchor="w", padx=15, pady=20)

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.entry_senha.configure(show="")
            self.btn_eye.configure(text="🔒")
        else:
            self.entry_senha.configure(show="*")
            self.btn_eye.configure(text="👁")

    def _save_settings(self):
        self.config["email"] = self.entry_email.get().strip()
        self.config["senha"] = self.entry_senha.get().strip()
        try:
            self.config["wait_time"] = int(self.entry_wait.get().strip())
        except ValueError:
            self.config["wait_time"] = 60
        self.config["preferred_browser"] = self.var_browser.get()

        save_config(self.config)
        if self.on_saved:
            self.on_saved()
        messagebox.showinfo("Sucesso", "Preferências salvas com sucesso!")
