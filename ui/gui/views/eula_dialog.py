import customtkinter as ctk
import sys
from legal.eula_text import EULA_TITLE, EULA_SUMMARY, EULA_FULL_TEXT
from legal.license_verifier import accept_eula


class EulaDialog(ctk.CTkToplevel):
    """
    Modal não-fechável para aceite vinculante de termos de uso e responsabilidade no 1º boot.
    """

    def __init__(self, parent, on_accepted_callback):
        super().__init__(parent)
        self.on_accepted_callback = on_accepted_callback

        self.title("Aviso Legal e Termos de Uso")
        self.geometry("720x560")
        self.minsize(600, 480)
        self.transient(parent)
        self.grab_set()

        # Impede fechar pelo X sem aceitar
        self.protocol("WM_DELETE_WINDOW", self._on_reject)

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=EULA_TITLE,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#3B8ED0",
            wraplength=660,
        )
        title_label.pack(anchor="w")

        summary_label = ctk.CTkLabel(
            header_frame,
            text=EULA_SUMMARY,
            font=ctk.CTkFont(size=12),
            text_color="#A0A0A0",
            wraplength=660,
            justify="left",
        )
        summary_label.pack(anchor="w", pady=(5, 0))

        # Caixa com texto integral rolável
        text_box = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(family="monospace", size=11))
        text_box.pack(fill="both", expand=True, padx=20, pady=10)
        text_box.insert("1.0", EULA_FULL_TEXT.strip())
        text_box.configure(state="disabled")

        # Footer com Checkbox e Botões
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.accept_var = ctk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(
            footer_frame,
            text="Declaro que sou assinante legítimo e concordo integralmente com os termos.",
            variable=self.accept_var,
            command=self._on_checkbox_toggle,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.checkbox.pack(anchor="w", pady=(0, 10))

        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(fill="x")

        self.reject_btn = ctk.CTkButton(
            btn_row,
            text="Recusar e Sair",
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            width=140,
            command=self._on_reject,
        )
        self.reject_btn.pack(side="left")

        self.accept_btn = ctk.CTkButton(
            btn_row,
            text="Aceitar e Continuar",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            width=180,
            state="disabled",
            command=self._on_accept,
        )
        self.accept_btn.pack(side="right")

    def _on_checkbox_toggle(self):
        if self.accept_var.get():
            self.accept_btn.configure(state="normal")
        else:
            self.accept_btn.configure(state="disabled")

    def _on_accept(self):
        accept_eula()
        self.grab_release()
        self.destroy()
        if self.on_accepted_callback:
            self.on_accepted_callback()

    def _on_reject(self):
        self.grab_release()
        self.destroy()
        sys.exit(0)
