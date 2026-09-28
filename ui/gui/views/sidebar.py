from typing import Callable, Dict, Optional
import customtkinter as ctk

from ui.gui.theme import THEME_COLORS, RADIUS_BUTTON, get_font


class SidebarNav(ctk.CTkFrame):
    """
    Barra lateral fixa de navegação inspirada em ferramentas profissionais modernas.
    Oferece acesso instantâneo a todas as áreas funcionais da aplicação.
    """

    def __init__(
        self,
        parent,
        on_view_change: Callable[[str], None],
        on_theme_toggle: Callable[[], None],
        **kwargs,
    ):
        super().__init__(
            parent,
            width=220,
            corner_radius=0,
            fg_color=THEME_COLORS["bg_sidebar"],
            border_color=THEME_COLORS["border"],
            border_width=1,
            **kwargs,
        )
        self.on_view_change = on_view_change
        self.on_theme_toggle = on_theme_toggle
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.active_view = "download"

        self._build_ui()

    def _build_ui(self):
        # 1. Top Brand Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(20, 20))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="🦉 CorujaSync",
            font=get_font(18, "bold"),
            text_color=THEME_COLORS["accent_primary"],
            anchor="w",
        )
        title_lbl.pack(fill="x")

        sub_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        sub_frame.pack(fill="x", pady=(2, 0))

        sub_lbl = ctk.CTkLabel(
            sub_frame,
            text="Backup Inteligente",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        sub_lbl.pack(side="left")

        badge_pro = ctk.CTkLabel(
            sub_frame,
            text="PRO v2.0",
            font=get_font(10, "bold"),
            text_color="#10B981",
            fg_color=("#E6F4EA", "#064E3B"),
            corner_radius=6,
            padx=6,
            pady=1,
        )
        badge_pro.pack(side="right")

        # Divisor sutil
        sep = ctk.CTkFrame(self, height=1, fg_color=THEME_COLORS["border"])
        sep.pack(fill="x", padx=15, pady=(0, 15))

        # 2. Itens de Navegação
        items = [
            ("download", "📥 Download"),
            ("search", "🔍 Busca em PDFs"),
            ("watcher", "⏱ Smart Watcher"),
            ("settings", "⚙️ Configurações"),
            ("license", "🔑 Licença Pro"),
            ("about", "📄 Termos & Sobre"),
        ]

        nav_container = ctk.CTkFrame(self, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, padx=10)

        for view_key, label in items:
            btn = ctk.CTkButton(
                nav_container,
                text=label,
                anchor="w",
                font=get_font(13, "bold"),
                height=38,
                corner_radius=RADIUS_BUTTON,
                fg_color="transparent",
                text_color=THEME_COLORS["text_secondary"],
                hover_color=("#E5E7EB", "#252836"),
                command=lambda k=view_key: self._on_btn_click(k),
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[view_key] = btn

        # 3. Rodapé com Status e Alternador de Tema
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", padx=15, pady=15)

        # Divisor superior do rodapé
        sep_bottom = ctk.CTkFrame(footer_frame, height=1, fg_color=THEME_COLORS["border"])
        sep_bottom.pack(fill="x", pady=(0, 12))

        # Badge de Status Operacional
        self.lbl_status = ctk.CTkLabel(
            footer_frame,
            text="🟢 Sistema Pronto",
            font=get_font(11, "bold"),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        self.lbl_status.pack(fill="x", pady=(0, 10))

        # Botão Rápido de Tema
        current_mode = ctk.get_appearance_mode().lower()
        theme_icon = "☀️ Modo Claro" if current_mode == "dark" else "🌙 Modo Escuro"
        self.btn_theme = ctk.CTkButton(
            footer_frame,
            text=theme_icon,
            font=get_font(11),
            height=30,
            corner_radius=6,
            fg_color=("#F3F4F6", "#202330"),
            text_color=THEME_COLORS["text_secondary"],
            hover_color=("#E5E7EB", "#2A2E40"),
            command=self._handle_theme_toggle,
        )
        self.btn_theme.pack(fill="x")

        # Seleciona Download por padrão
        self.set_active("download")

    def _on_btn_click(self, view_key: str):
        self.set_active(view_key)
        self.on_view_change(view_key)

    def set_active(self, view_key: str):
        """Atualiza o botão ativo com visual em destaque."""
        self.active_view = view_key
        for key, btn in self.nav_buttons.items():
            if key == view_key:
                btn.configure(
                    fg_color=THEME_COLORS["accent_primary"],
                    text_color="#FFFFFF",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME_COLORS["text_secondary"],
                )

    def set_status(self, text: str, state: str = "ready"):
        """Atualiza o badge de status do rodapé."""
        icons = {
            "ready": "🟢",
            "working": "🔵",
            "warning": "🟡",
            "error": "🔴",
        }
        icon = icons.get(state, "⚪")
        self.lbl_status.configure(text=f"{icon} {text}")

    def _handle_theme_toggle(self):
        self.on_theme_toggle()
        current_mode = ctk.get_appearance_mode().lower()
        theme_label = "☀️ Modo Claro" if current_mode == "dark" else "🌙 Modo Escuro"
        self.btn_theme.configure(text=theme_label)
