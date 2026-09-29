from typing import Dict, Any
import customtkinter as ctk

from ui.gui.dialogs import show_info, show_success, show_error

from ui.gui.theme import (
    THEME_COLORS,
    create_card_frame,
    get_font,
)
from legal.license_manager import LicenseManager, get_machine_id


class LicenseView(ctk.CTkFrame):
    """
    Painel de Licenciamento, Machine ID e Ativação de Recursos Pro.
    Permite aos usuários visualizarem o status da licença e ativarem chaves criptográficas.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.license_manager = LicenseManager()

        self._build_ui()

    def _build_ui(self):
        status = self.license_manager.get_status()
        is_active = status.get("is_active", False)

        # 1. Card Hero: Status da Conta / Licença
        hero_card = create_card_frame(self)
        hero_card.pack(fill="x", padx=15, pady=(15, 10))

        head_row = ctk.CTkFrame(hero_card, fg_color="transparent")
        head_row.pack(fill="x", padx=15, pady=(15, 6))

        lbl_hero_title = ctk.CTkLabel(
            head_row,
            text="Status da Sua Conta",
            font=get_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_hero_title.pack(side="left")

        # Badge Visual
        badge_text = f"★ {status.get('tier', '').upper()}" if is_active else "MODO TRIAL / BÁSICO"
        badge_fg = ("#D1FAE5", "#064E3B") if is_active else ("#FEF3C7", "#78350F")
        badge_text_color = ("#065F46", "#34D399") if is_active else ("#92400E", "#FBBF24")

        self.badge_plan = ctk.CTkLabel(
            head_row,
            text=badge_text,
            font=get_font(11, "bold"),
            fg_color=badge_fg,
            text_color=badge_text_color,
            corner_radius=6,
            padx=10,
            pady=4,
        )
        self.badge_plan.pack(side="right")

        self.lbl_details = ctk.CTkLabel(
            hero_card,
            text=f"Cliente: {status.get('client')}  •  Validade: {status.get('expires_at')}\n{status.get('message')}",
            font=get_font(11),
            text_color=THEME_COLORS["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.lbl_details.pack(fill="x", padx=15, pady=(0, 15))

        # 2. Card: Identificação de Máquina
        mid_card = create_card_frame(self)
        mid_card.pack(fill="x", padx=15, pady=5)

        lbl_mid_title = ctk.CTkLabel(
            mid_card,
            text="ID de Hardware Deste Computador",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_mid_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_mid_desc = ctk.CTkLabel(
            mid_card,
            text="Código anônimo e exclusivo gerado para validação offline. Forneça este ID caso sua licença seja nominal.",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        lbl_mid_desc.pack(fill="x", padx=15, pady=(0, 8))

        row_mid = ctk.CTkFrame(mid_card, fg_color="transparent")
        row_mid.pack(fill="x", padx=15, pady=(0, 15))

        self.entry_mid = ctk.CTkEntry(
            row_mid,
            font=get_font(12, family="mono"),
            height=36,
        )
        self.entry_mid.insert(0, get_machine_id())
        self.entry_mid.configure(state="readonly")
        self.entry_mid.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_copy_mid = ctk.CTkButton(
            row_mid,
            text="📋 Copiar ID",
            font=get_font(12, "bold"),
            height=36,
            width=110,
            command=self._copy_mid,
        )
        btn_copy_mid.pack(side="right")

        # 3. Card: Ativação de Chave
        act_card = create_card_frame(self)
        act_card.pack(fill="x", padx=15, pady=5)

        lbl_act_title = ctk.CTkLabel(
            act_card,
            text="Ativar Nova Chave de Licença",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_act_title.pack(fill="x", padx=15, pady=(12, 4))

        row_key = ctk.CTkFrame(act_card, fg_color="transparent")
        row_key.pack(fill="x", padx=15, pady=(0, 12))

        self.entry_key = ctk.CTkEntry(
            row_key,
            placeholder_text="Cole a chave fornecida na compra (ex: CSYNC-ANU-...)",
            font=get_font(12, family="mono"),
            height=36,
        )
        self.entry_key.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_act = ctk.CTkButton(
            row_key,
            text="⚡ Ativar Chave",
            font=get_font(12, "bold"),
            fg_color=THEME_COLORS["success"],
            hover_color=THEME_COLORS["success_hover"],
            height=36,
            width=120,
            command=self._activate_key,
        )
        btn_act.pack(side="right")

        self.lbl_act_feedback = ctk.CTkLabel(
            act_card,
            text="",
            font=get_font(11, "bold"),
            anchor="w",
        )
        self.lbl_act_feedback.pack(fill="x", padx=15, pady=(0, 10))

    def _copy_mid(self):
        mid = self.entry_mid.get()
        self.clipboard_clear()
        self.clipboard_append(mid)
        show_success(
            self.winfo_toplevel(),
            "ID Copiado",
            f"Machine ID copiado com sucesso para a sua área de transferência:\n\n{mid}",
        )

    def _activate_key(self):
        key = self.entry_key.get().strip()
        if not key:
            self.lbl_act_feedback.configure(text="Por favor, digite ou cole uma chave de licença válida.", text_color="#EF4444")
            return

        success, msg = self.license_manager.activate(key)
        if success:
            self.lbl_act_feedback.configure(text=f"✓ {msg}", text_color="#10B981")
            status = self.license_manager.get_status()
            self.badge_plan.configure(
                text=f"★ {status.get('tier', '').upper()}",
                fg_color=("#D1FAE5", "#064E3B"),
                text_color=("#065F46", "#34D399"),
            )
            self.lbl_details.configure(
                text=f"Cliente: {status.get('client')}  •  Validade: {status.get('expires_at')}\n{status.get('message')}"
            )
            show_success(
                self.winfo_toplevel(),
                "Licença Ativada",
                f"{msg}\n\nTodos os recursos Pro do CorujaSync foram liberados com sucesso!",
            )
        else:
            self.lbl_act_feedback.configure(text=f"✗ {msg}", text_color="#EF4444")
            show_error(
                self.winfo_toplevel(),
                "Falha na Ativação",
                msg,
            )
