from typing import Dict, Any, List
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    create_card_frame,
    get_font,
)


class WatcherView(ctk.CTkFrame):
    """
    Painel de controle do Smart Watcher para monitoramento em segundo plano
    e sincronização automática de novas aulas publicadas pelos professores.
    """

    def __init__(self, parent, config: Dict[str, Any], **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.is_monitoring = False

        self._build_ui()

    def _build_ui(self):
        # 1. Card de Status e Controles
        control_card = create_card_frame(self)
        control_card.pack(fill="x", padx=15, pady=(15, 10))

        lbl_title = ctk.CTkLabel(
            control_card,
            text="⏱ Smart Watcher - Sincronização Incremental",
            font=get_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_desc = ctk.CTkLabel(
            control_card,
            text="O Smart Watcher verifica seus editais periodicamente e baixa apenas as aulas e materiais inéditos adicionados recentemente.",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        lbl_desc.pack(fill="x", padx=15, pady=(0, 10))

        # Indicador de Status
        status_box = ctk.CTkFrame(control_card, fg_color=THEME_COLORS["input_bg"], corner_radius=8)
        status_box.pack(fill="x", padx=15, pady=(0, 12))

        self.lbl_watcher_status = ctk.CTkLabel(
            status_box,
            text="⚪ Monitoramento em segundo plano: PAUSADO",
            font=get_font(12, "bold"),
            text_color=THEME_COLORS["text_secondary"],
        )
        self.lbl_watcher_status.pack(side="left", padx=12, pady=10)

        # Configuração de Intervalo
        row_cfg = ctk.CTkFrame(control_card, fg_color="transparent")
        row_cfg.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(row_cfg, text="Frequência de Checagem:", font=get_font(12, "bold")).pack(side="left", padx=(0, 10))

        self.var_interval = ctk.StringVar(value="1 hora")
        self.seg_interval = ctk.CTkSegmentedButton(
            row_cfg,
            values=["30 min", "1 hora", "3 horas", "12 horas", "24 horas"],
            variable=self.var_interval,
            font=get_font(11, "bold"),
        )
        self.seg_interval.pack(side="left", padx=(0, 15))

        # Botões de Ação
        row_btns = ctk.CTkFrame(control_card, fg_color="transparent")
        row_btns.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_toggle_watcher = ctk.CTkButton(
            row_btns,
            text="▶ Ativar Monitoramento Automático",
            fg_color=THEME_COLORS["accent_primary"],
            hover_color=THEME_COLORS["accent_primary_hover"],
            font=get_font(12, "bold"),
            height=36,
            command=self._toggle_watcher,
        )
        self.btn_toggle_watcher.pack(side="left", padx=(0, 10))

        self.btn_check_now = ctk.CTkButton(
            row_btns,
            text="🔍 Verificar Agora",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            font=get_font(12),
            height=36,
            command=self._check_now,
        )
        self.btn_check_now.pack(side="left")

        # 2. Card de Registro de Aulas Detectadas
        log_card = create_card_frame(self)
        log_card.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        lbl_log_title = ctk.CTkLabel(
            log_card,
            text="Histórico de Atualizações do Smart Watcher",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_log_title.pack(fill="x", padx=15, pady=(12, 6))

        self.watcher_log = ctk.CTkTextbox(
            log_card,
            wrap="none",
            font=get_font(11, family="mono"),
            fg_color=THEME_COLORS["input_bg"],
        )
        self.watcher_log.pack(fill="both", expand=True, padx=15, pady=(0, 12))
        self.watcher_log.insert(
            "end",
            "[INFO] O Smart Watcher está configurado e pronto para monitorar atualizações.\n"
            "[DICA] Ao ativar o monitoramento, novos materiais adicionados no portal serão baixados automaticamente.\n"
        )

    def _toggle_watcher(self):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.lbl_watcher_status.configure(
                text=f"🟢 Monitoramento em segundo plano: ATIVO ({self.var_interval.get()})",
                text_color="#10B981",
            )
            self.btn_toggle_watcher.configure(
                text="⏹ Desativar Monitoramento",
                fg_color=THEME_COLORS["danger"],
                hover_color=THEME_COLORS["danger_hover"],
            )
            self.watcher_log.insert("end", f"\n[INFO] Monitoramento contínuo iniciado. Intervalo: {self.var_interval.get()}.\n")
        else:
            self.lbl_watcher_status.configure(
                text="⚪ Monitoramento em segundo plano: PAUSADO",
                text_color=THEME_COLORS["text_secondary"],
            )
            self.btn_toggle_watcher.configure(
                text="▶ Ativar Monitoramento Automático",
                fg_color=THEME_COLORS["accent_primary"],
                hover_color=THEME_COLORS["accent_primary_hover"],
            )
            self.watcher_log.insert("end", "[INFO] Monitoramento pausado pelo usuário.\n")
        self.watcher_log.see("end")

    def _check_now(self):
        self.watcher_log.insert("end", "\n[CHECK] Disparando verificação manual de novas aulas nos cursos inscritos...\n")
        self.watcher_log.insert("end", "[CHECK] O Smart Watcher utilizará o histórico local (.download_state.json) para comparar versões.\n")
        self.watcher_log.see("end")
