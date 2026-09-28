from typing import Dict, Any
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    create_card_frame,
    get_font,
)
from ui.gui.views.eula_dialog import EulaDialog


class AboutView(ctk.CTkFrame):
    """
    Painel de Termos de Uso, Blindagem Jurídica e Informações Sobre o Software.
    """

    def __init__(self, parent, config: Dict[str, Any], **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config

        self._build_ui()

    def _build_ui(self):
        # 1. Card: Identificação do Software
        info_card = create_card_frame(self)
        info_card.pack(fill="x", padx=15, pady=(15, 10))

        head = ctk.CTkFrame(info_card, fg_color="transparent")
        head.pack(fill="x", padx=15, pady=(15, 6))

        lbl_app = ctk.CTkLabel(
            head,
            text="Concurso Downloader Desktop",
            font=get_font(16, "bold"),
            text_color=THEME_COLORS["accent_primary"],
        )
        lbl_app.pack(side="left")

        badge = ctk.CTkLabel(
            head,
            text="Versão 2.0.0 Pro",
            font=get_font(11, "bold"),
            fg_color=("#DBEAFE", "#1E3A8A"),
            text_color=("#1D4ED8", "#93C5FD"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        accepted_at = self.config.get("eula_accepted_at", "Registrado no primeiro boot")
        lbl_sub = ctk.CTkLabel(
            info_card,
            text=f"Status da Licença: Termos de Uso aceitos em {accepted_at}\nArquitetura: 100% Client-Side (Sem nuvem intermediária / Processamento local)",
            font=get_font(11),
            text_color=THEME_COLORS["text_secondary"],
            justify="left",
            anchor="w",
        )
        lbl_sub.pack(fill="x", padx=15, pady=(0, 15))

        # 2. Card: Salvaguardas Jurídicas e Aviso Legal
        legal_card = create_card_frame(self)
        legal_card.pack(fill="x", padx=15, pady=5)

        lbl_legal_title = ctk.CTkLabel(
            legal_card,
            text="Declaração de Isenção de Responsabilidade e Salvaguardas",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_legal_title.pack(fill="x", padx=15, pady=(12, 6))

        legal_text = (
            "• Finalidade Estritamente Privada: Este utilitário destina-se exclusivamente ao backup pessoal "
            "e estudo offline por assinantes legítimos das plataformas de ensino, respaldado pelo Art. 46, II "
            "da Lei de Direitos Autorais (Lei nº 9.610/98).\n\n"
            "• Preservação Absoluta das Marcas D'água: O software não altera, não oculta e não remove o CPF ou nome "
            "do aluno estampado nos PDFs e vídeos originais. Qualquer vazamento é de inteira responsabilidade do titular.\n\n"
            "• Proibição de Compartilhamento: A comercialização, doação, compartilhamento ou distribuição do material "
            "baixado a terceiros configura violação expressa de direitos autorais e crime previsto no Artigo 184 do Código Penal.\n\n"
            "• Não Afiliação: O software é independente e não possui vínculo, parceria, autorização ou patrocínio "
            "com o Estratégia Concursos ou qualquer entidade educacional."
        )

        lbl_legal_body = ctk.CTkLabel(
            legal_card,
            text=legal_text,
            font=get_font(11),
            text_color=THEME_COLORS["text_secondary"],
            justify="left",
            wraplength=660,
            anchor="w",
        )
        lbl_legal_body.pack(fill="x", padx=15, pady=(0, 12))

        btn_eula = ctk.CTkButton(
            legal_card,
            text="📄 Exibir Contrato de Licença (EULA) Completo",
            font=get_font(12, "bold"),
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            height=34,
            width=260,
            command=lambda: EulaDialog(self.winfo_toplevel(), on_accepted_callback=None),
        )
        btn_eula.pack(anchor="w", padx=15, pady=(0, 15))
