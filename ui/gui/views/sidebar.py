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
        import os
        import shutil

        # 1. Top Brand Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(16, 16))

        brand_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_row.pack(fill="x")

        # Owl glyph in rounded gradient-like box
        glyph_box = ctk.CTkFrame(
            brand_row,
            width=36,
            height=36,
            corner_radius=10,
            fg_color=("#4F46E5", "#4338CA"),
        )
        glyph_box.pack(side="left", padx=(0, 10))
        glyph_box.pack_propagate(False)
        ctk.CTkLabel(glyph_box, text="🦉", font=get_font(18)).place(relx=0.5, rely=0.5, anchor="center")

        brand_text_box = ctk.CTkFrame(brand_row, fg_color="transparent")
        brand_text_box.pack(side="left", fill="x", expand=True)

        title_row = ctk.CTkFrame(brand_text_box, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text="CorujaSync", font=get_font(14, "bold"), text_color=THEME_COLORS["text_primary"]).pack(side="left")
        ctk.CTkLabel(title_row, text="PRO", font=get_font(9, "bold"), fg_color=("#FEF3C7", "#78350F"), text_color=("#B45309", "#FBBF24"), corner_radius=4, padx=5, pady=1).pack(side="left", padx=5)

        ctk.CTkLabel(brand_text_box, text="Backup Inteligente", font=get_font(10), text_color=THEME_COLORS["text_muted"], anchor="w").pack(fill="x")

        # Divisor sutil
        sep = ctk.CTkFrame(self, height=1, fg_color=THEME_COLORS["border"])
        sep.pack(fill="x", padx=15, pady=(4, 12))

        # 2. Itens de Navegação (Stitch Design)
        items = [
            ("download", "📥 Download Studio"),
            ("search", "🔍 Spotlight Search"),
            ("watcher", "⏱ Smart Watcher"),
            ("license", "🔑 Licença Pro"),
            ("settings", "⚙️ Configurações"),
            ("about", "📄 Sobre & Termos"),
        ]

        nav_container = ctk.CTkFrame(self, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, padx=10)

        for view_key, label in items:
            btn = ctk.CTkButton(
                nav_container,
                text=label,
                anchor="w",
                font=get_font(12, "bold"),
                height=38,
                corner_radius=RADIUS_BUTTON,
                fg_color="transparent",
                text_color=THEME_COLORS["text_secondary"],
                hover_color=("#E2E8F0", "#1E293B"),
                command=lambda k=view_key: self._on_btn_click(k),
            )
            btn.pack(fill="x", pady=2.5)
            self.nav_buttons[view_key] = btn

        # 3. Rodapé com Widget de Armazenamento e Alternador de Tema
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", padx=12, pady=12)

        # Divisor superior do rodapé
        sep_bottom = ctk.CTkFrame(footer_frame, height=1, fg_color=THEME_COLORS["border"])
        sep_bottom.pack(fill="x", pady=(0, 10))

        # Widget de Armazenamento em Disco (Google Stitch Style)
        storage_card = ctk.CTkFrame(
            footer_frame,
            fg_color=THEME_COLORS["input_bg"],
            border_color=THEME_COLORS["border"],
            border_width=1,
            corner_radius=10,
        )
        storage_card.pack(fill="x", pady=(0, 8))

        st_head = ctk.CTkFrame(storage_card, fg_color="transparent")
        st_head.pack(fill="x", padx=8, pady=(6, 1))
        ctk.CTkLabel(st_head, text="💾 Disco:", font=get_font(10, "bold"), text_color=THEME_COLORS["text_secondary"]).pack(side="left")
        self.lbl_storage_free = ctk.CTkLabel(st_head, text="-- GB livre", font=get_font(10, "bold"), text_color=THEME_COLORS["success"])
        self.lbl_storage_free.pack(side="right")

        self.storage_progress = ctk.CTkProgressBar(storage_card, height=4, corner_radius=2)
        self.storage_progress.pack(fill="x", padx=8, pady=(2, 6))
        self.storage_progress.set(0.5)

        self._update_disk_usage()

        # Badge de Status Operacional
        self.lbl_status = ctk.CTkLabel(
            footer_frame,
            text="🟢 Conectado & Pronto",
            font=get_font(10, "bold"),
            text_color=THEME_COLORS["success"],
            anchor="w",
        )
        self.lbl_status.pack(fill="x", pady=(0, 8))

        # Botão Rápido de Tema
        current_mode = ctk.get_appearance_mode().lower()
        theme_icon = "☀️ Modo Claro" if current_mode == "dark" else "🌙 Modo Escuro"
        self.btn_theme = ctk.CTkButton(
            footer_frame,
            text=theme_icon,
            font=get_font(11),
            height=30,
            corner_radius=RADIUS_BUTTON,
            fg_color=("#F1F5F9", "#1E293B"),
            text_color=THEME_COLORS["text_secondary"],
            hover_color=("#E2E8F0", "#334155"),
            command=self._handle_theme_toggle,
        )
        self.btn_theme.pack(fill="x")

        # Seleciona Download por padrão
        self.set_active("download")

    def _update_disk_usage(self):
        try:
            import os
            import shutil
            from core.config import get_default_download_dir, load_config
            cfg = load_config()
            target_dir = cfg.get("download_dir", get_default_download_dir())
            path_to_check = target_dir if os.path.exists(target_dir) else "/"
            total, used, free = shutil.disk_usage(path_to_check)
            free_gb = free / (1024**3)
            used_pct = used / total if total > 0 else 0.0
            self.lbl_storage_free.configure(text=f"{free_gb:.1f} GB livre")
            self.storage_progress.set(min(max(used_pct, 0.0), 1.0))
        except Exception:
            pass

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
