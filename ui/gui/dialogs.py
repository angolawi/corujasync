"""
Módulo de diálogos e modais modernas em CustomTkinter para o CorujaSync.
Substitui as caixas de mensagem nativas do Tkinter arcaico (messagebox) por
janelas estilizadas, centradas, acessíveis e harmonizadas com o tema Dark/Light.
"""
from typing import Optional
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    RADIUS_DIALOG,
    RADIUS_BUTTON,
    BORDER_WIDTH_DIALOG,
    get_font,
)


class ModernDialog(ctk.CTkToplevel):
    """
    Janela modal moderna estilizada com CustomTkinter.
    Centraliza-se automaticamente sobre a janela mãe e bloqueia eventos externos.
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        dialog_type: str = "info",
        confirm_text: str = "OK",
        cancel_text: Optional[str] = None,
        width: int = 420,
        height: int = 230,
    ):
        super().__init__(parent)
        self.parent = parent
        self.result: bool = False

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=THEME_COLORS["dialog_bg"])

        # Metadados de cada tipo de diálogo
        type_configs = {
            "info": {
                "icon": "ℹ️",
                "badge_bg": THEME_COLORS["badge_info"],
                "accent": THEME_COLORS["accent_primary"],
                "btn_color": THEME_COLORS["accent_primary"],
                "btn_hover": THEME_COLORS["accent_primary_hover"],
            },
            "success": {
                "icon": "✓",
                "badge_bg": THEME_COLORS["badge_success"],
                "accent": THEME_COLORS["success"],
                "btn_color": THEME_COLORS["success"],
                "btn_hover": THEME_COLORS["success_hover"],
            },
            "warning": {
                "icon": "⚠️",
                "badge_bg": THEME_COLORS["badge_warning"],
                "accent": THEME_COLORS["tag_warning"],
                "btn_color": THEME_COLORS["tag_warning"],
                "btn_hover": ("#92400E", "#D97706"),
            },
            "error": {
                "icon": "✕",
                "badge_bg": THEME_COLORS["badge_error"],
                "accent": THEME_COLORS["danger"],
                "btn_color": THEME_COLORS["danger"],
                "btn_hover": THEME_COLORS["danger_hover"],
            },
            "confirm": {
                "icon": "❓",
                "badge_bg": THEME_COLORS["badge_confirm"],
                "accent": ("#7C3AED", "#8B5CF6"),
                "btn_color": THEME_COLORS["danger"],
                "btn_hover": THEME_COLORS["danger_hover"],
            },
        }

        cfg = type_configs.get(dialog_type, type_configs["info"])

        # Montagem do Layout do Diálogo
        main_container = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["dialog_bg"],
            corner_radius=RADIUS_DIALOG,
            border_color=THEME_COLORS["border"],
            border_width=BORDER_WIDTH_DIALOG,
        )
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Cabeçalho: Ícone em Destaque + Título
        header_row = ctk.CTkFrame(main_container, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(16, 8))

        icon_badge = ctk.CTkLabel(
            header_row,
            text=cfg["icon"],
            font=get_font(18, "bold"),
            fg_color=cfg["badge_bg"],
            text_color=cfg["accent"],
            corner_radius=10,
            width=42,
            height=42,
        )
        icon_badge.pack(side="left", padx=(0, 12))

        title_lbl = ctk.CTkLabel(
            header_row,
            text=title,
            font=get_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Corpo: Mensagem Descritiva
        msg_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        msg_frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        msg_lbl = ctk.CTkLabel(
            msg_frame,
            text=message,
            font=get_font(12),
            text_color=THEME_COLORS["text_secondary"],
            justify="left",
            anchor="w",
            wraplength=width - 60,
        )
        msg_lbl.pack(fill="both", expand=True, anchor="w")

        # Rodapé: Botões de Ação
        btn_bar = ctk.CTkFrame(main_container, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 16))

        if cancel_text:
            btn_cancel = ctk.CTkButton(
                btn_bar,
                text=cancel_text,
                font=get_font(12, "bold"),
                fg_color=THEME_COLORS["slate"],
                hover_color=THEME_COLORS["slate_hover"],
                text_color="#FFFFFF",
                corner_radius=RADIUS_BUTTON,
                height=34,
                width=100,
                command=self._on_cancel,
            )
            btn_cancel.pack(side="right", padx=(8, 0))

        btn_confirm = ctk.CTkButton(
            btn_bar,
            text=confirm_text,
            font=get_font(12, "bold"),
            fg_color=cfg["btn_color"],
            hover_color=cfg["btn_hover"],
            text_color="#FFFFFF",
            corner_radius=RADIUS_BUTTON,
            height=34,
            width=110,
            command=self._on_confirm,
        )
        btn_confirm.pack(side="right")

        # Atalhos de Teclado
        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self._on_cancel())

        # Centralização sobre a janela mãe
        self._center_on_parent(width, height)

        # Transparência e Modalidade
        if parent:
            try:
                self.transient(parent)
                self.grab_set()
            except Exception:
                pass

        btn_confirm.focus_set()

    def _center_on_parent(self, width: int, height: int):
        self.update_idletasks()
        try:
            if self.parent and self.parent.winfo_exists():
                pw = self.parent.winfo_width()
                ph = self.parent.winfo_height()
                px = self.parent.winfo_rootx()
                py = self.parent.winfo_rooty()
                x = px + max(0, (pw - width) // 2)
                y = py + max(0, (ph - height) // 2)
            else:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                x = max(0, (sw - width) // 2)
                y = max(0, (sh - height) // 2)
        except Exception:
            x, y = 200, 200

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _on_confirm(self):
        self.result = True
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_cancel(self):
        self.result = False
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def show_info(parent, title: str, message: str, confirm_text: str = "OK"):
    """Exibe um diálogo informativo moderno com CustomTkinter."""
    dlg = ModernDialog(
        parent=parent,
        title=title,
        message=message,
        dialog_type="info",
        confirm_text=confirm_text,
    )
    dlg.wait_window()


def show_success(parent, title: str, message: str, confirm_text: str = "Entendido"):
    """Exibe um diálogo de sucesso moderno com CustomTkinter."""
    dlg = ModernDialog(
        parent=parent,
        title=title,
        message=message,
        dialog_type="success",
        confirm_text=confirm_text,
    )
    dlg.wait_window()


def show_warning(parent, title: str, message: str, confirm_text: str = "OK"):
    """Exibe um diálogo de aviso moderno com CustomTkinter."""
    dlg = ModernDialog(
        parent=parent,
        title=title,
        message=message,
        dialog_type="warning",
        confirm_text=confirm_text,
    )
    dlg.wait_window()


def show_error(parent, title: str, message: str, confirm_text: str = "Fechar"):
    """Exibe um diálogo de erro moderno com CustomTkinter."""
    dlg = ModernDialog(
        parent=parent,
        title=title,
        message=message,
        dialog_type="error",
        confirm_text=confirm_text,
    )
    dlg.wait_window()


def ask_confirm(
    parent,
    title: str,
    message: str,
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar",
) -> bool:
    """
    Exibe um diálogo de confirmação com opções de Confirmar e Cancelar.
    Retorna True se confirmado pelo usuário, False caso contrário.
    """
    dlg = ModernDialog(
        parent=parent,
        title=title,
        message=message,
        dialog_type="confirm",
        confirm_text=confirm_text,
        cancel_text=cancel_text,
    )
    dlg.wait_window()
    return dlg.result
