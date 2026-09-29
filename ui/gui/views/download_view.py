import os
from typing import Callable, Optional, Dict, Any, Union
from tkinter import filedialog
import customtkinter as ctk

from ui.gui.dialogs import show_info, show_success, show_error, show_warning, ask_confirm

from ui.gui.theme import (
    THEME_COLORS,
    RADIUS_CARD,
    RADIUS_BUTTON,
    create_card_frame,
    get_font,
)
from core.config import get_default_download_dir
from core.diagnostics import DiagnosticsStore
from legal.license_manager import LicenseManager
from datetime import datetime


class DownloadView(ctk.CTkScrollableFrame):
    """
    Estúdio principal de downloads com organização moderna em cards visuais,
    dashboard de telemetria em tempo real (MB/s, ETA, progresso) e console de logs.
    """

    def __init__(
        self,
        parent,
        config: Dict[str, Any],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.license_manager = LicenseManager()

        self._build_ui()

    def _build_ui(self):
        # 1. Card Superior: Alvo e Modo de Download
        card_target = create_card_frame(self)
        card_target.pack(fill="x", padx=15, pady=(15, 10))

        # Título da Seção + Badge de Plano
        head_row = ctk.CTkFrame(card_target, fg_color="transparent")
        head_row.pack(fill="x", padx=15, pady=(12, 8))

        lbl_target_title = ctk.CTkLabel(
            head_row,
            text="1. Modo e Seleção de Conteúdo",
            font=get_font(14, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_target_title.pack(side="left")

        is_pro = self.license_manager.is_premium()
        badge_text = "★ LICENÇA PRO ATIVA" if is_pro else "★ PLANO FREE (1 DISCIPLINA DEMO)"
        badge_fg = ("#D1FAE5", "#064E3B") if is_pro else ("#FEF3C7", "#78350F")
        badge_tc = ("#065F46", "#34D399") if is_pro else ("#92400E", "#FBBF24")

        lbl_plan_badge = ctk.CTkLabel(
            head_row,
            text=badge_text,
            font=get_font(10, "bold"),
            fg_color=badge_fg,
            text_color=badge_tc,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        lbl_plan_badge.pack(side="right")

        # Segmented Button para o Modo
        self.mode_var = ctk.StringVar(value="single")
        self.seg_mode = ctk.CTkSegmentedButton(
            card_target,
            values=["📦 Pacote / Curso Específico", "📚 Todos os Cursos Matriculados"],
            variable=self.mode_var,
            font=get_font(12, "bold"),
            command=self._on_mode_change,
        )
        self.seg_mode.pack(fill="x", padx=15, pady=(0, 10))

        # Linha Entrada de URL / ID
        self.row_input = ctk.CTkFrame(card_target, fg_color="transparent")
        self.row_input.pack(fill="x", padx=15, pady=4)

        self.lbl_curso = ctk.CTkLabel(self.row_input, text="URL ou ID:", width=90, anchor="w", font=get_font(12, "bold"))
        self.lbl_curso.pack(side="left")

        self.entry_curso = ctk.CTkEntry(
            self.row_input,
            placeholder_text="Cole a URL ou ID numérico (ex: 400565 ou https://.../pacote/400565)",
            font=get_font(12),
            height=34,
        )
        self.entry_curso.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_clear = ctk.CTkButton(
            self.row_input,
            text="✕",
            width=34,
            height=34,
            font=get_font(12, "bold"),
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=lambda: self.entry_curso.delete(0, "end"),
        )
        btn_clear.pack(side="right")

        # Linha Diretório de Destino
        row_dir = ctk.CTkFrame(card_target, fg_color="transparent")
        row_dir.pack(fill="x", padx=15, pady=(4, 12))

        lbl_dir = ctk.CTkLabel(row_dir, text="Destino:", width=90, anchor="w", font=get_font(12, "bold"))
        lbl_dir.pack(side="left")

        self.entry_dir = ctk.CTkEntry(row_dir, font=get_font(12), height=34)
        self.entry_dir.insert(0, self.config.get("download_dir", get_default_download_dir()))
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_browse = ctk.CTkButton(
            row_dir,
            text="📁 Procurar",
            width=90,
            height=34,
            font=get_font(12, "bold"),
            command=self._browse_dir,
        )
        btn_browse.pack(side="right")

        # 2. Card: Opções de Download e Qualidade de Vídeo
        card_options = create_card_frame(self)
        card_options.pack(fill="x", padx=15, pady=5)

        lbl_opt_title = ctk.CTkLabel(
            card_options,
            text="2. Opções de Mídia e Rechecagem",
            font=get_font(14, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_opt_title.pack(fill="x", padx=15, pady=(12, 8))

        row_toggles = ctk.CTkFrame(card_options, fg_color="transparent")
        row_toggles.pack(fill="x", padx=15, pady=(0, 12))

        # Switch de Videoaulas
        self.var_videos = ctk.BooleanVar(value=self.config.get("download_videos", False))
        self.switch_videos = ctk.CTkSwitch(
            row_toggles,
            text="🎬 Baixar Videoaulas (.mp4)",
            variable=self.var_videos,
            font=get_font(12, "bold"),
        )
        self.switch_videos.pack(side="left", padx=(0, 20))

        # Segmented Button de Qualidade
        lbl_qual = ctk.CTkLabel(row_toggles, text="Resolução:", font=get_font(12))
        lbl_qual.pack(side="left", padx=(0, 6))

        self.var_quality = ctk.StringVar(value=self.config.get("preferred_quality", "720p"))
        self.seg_quality = ctk.CTkSegmentedButton(
            row_toggles,
            values=["720p HD", "480p", "360p"],
            variable=self.var_quality,
            font=get_font(11, "bold"),
        )
        self.seg_quality.pack(side="left", padx=(0, 20))

        # Switch de Rechecagem Forçada
        self.var_force = ctk.BooleanVar(value=False)
        self.switch_force = ctk.CTkSwitch(
            row_toggles,
            text="🔄 Forçar Rechecagem no Navegador",
            variable=self.var_force,
            font=get_font(12),
        )
        self.switch_force.pack(side="left")

        # 3. Card: Painel de Controle e Métricas em Tempo Real
        card_telemetry = create_card_frame(self)
        card_telemetry.pack(fill="x", padx=15, pady=5)

        # Botões de Ação Principais
        btn_bar = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=(12, 10))

        self.btn_start = ctk.CTkButton(
            btn_bar,
            text="▶ Iniciar Download",
            fg_color=THEME_COLORS["success"],
            hover_color=THEME_COLORS["success_hover"],
            font=get_font(13, "bold"),
            height=38,
            width=160,
            command=self.on_start,
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_bar,
            text="⏹ Cancelar",
            fg_color=THEME_COLORS["danger"],
            hover_color=THEME_COLORS["danger_hover"],
            font=get_font(13, "bold"),
            height=38,
            width=120,
            state="disabled",
            command=self.on_stop,
        )
        self.btn_stop.pack(side="left", padx=(0, 10))

        self.btn_diag = ctk.CTkButton(
            btn_bar,
            text="🛠 Exportar Diagnóstico",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            font=get_font(12, "bold"),
            height=38,
            width=160,
            command=self._export_diagnostics,
        )
        self.btn_diag.pack(side="right")

        self.btn_copy_log = ctk.CTkButton(
            btn_bar,
            text="📋 Copiar Logs",
            fg_color="transparent",
            hover_color=("#E5E7EB", "#252836"),
            text_color=THEME_COLORS["text_secondary"],
            font=get_font(11, "bold"),
            height=38,
            width=110,
            command=self.copy_logs,
        )
        self.btn_copy_log.pack(side="right", padx=4)

        self.btn_clear_log = ctk.CTkButton(
            btn_bar,
            text="🗑 Limpar",
            fg_color="transparent",
            hover_color=("#E5E7EB", "#252836"),
            text_color=THEME_COLORS["text_secondary"],
            font=get_font(11),
            height=38,
            width=80,
            command=self.clear_logs,
        )
        self.btn_clear_log.pack(side="right", padx=2)

        # Divisor
        sep_telemetry = ctk.CTkFrame(card_telemetry, height=1, fg_color=THEME_COLORS["border"])
        sep_telemetry.pack(fill="x", padx=15, pady=4)

        # Grid de KPIs em tempo real
        kpi_row = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        kpi_row.pack(fill="x", padx=15, pady=8)

        # KPI 1: Arquivo Ativo
        kpi_file_box = ctk.CTkFrame(kpi_row, fg_color=THEME_COLORS["input_bg"], corner_radius=8)
        kpi_file_box.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=2)
        ctk.CTkLabel(kpi_file_box, text="ARQUIVO ATIVO", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_current_file = ctk.CTkLabel(kpi_file_box, text="Nenhum download em andamento", font=get_font(11, "bold"), anchor="w")
        self.lbl_current_file.pack(anchor="w", padx=10, pady=(0, 6))

        # KPI 2: Velocidade
        kpi_speed_box = ctk.CTkFrame(kpi_row, fg_color=THEME_COLORS["input_bg"], corner_radius=8, width=120)
        kpi_speed_box.pack(side="left", fill="y", padx=4, pady=2)
        ctk.CTkLabel(kpi_speed_box, text="VELOCIDADE", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_speed = ctk.CTkLabel(kpi_speed_box, text="0.00 MB/s", font=get_font(12, "bold"), text_color=THEME_COLORS["accent_primary"])
        self.lbl_speed.pack(anchor="w", padx=10, pady=(0, 6))

        # KPI 3: Tempo Estimado (ETA)
        kpi_eta_box = ctk.CTkFrame(kpi_row, fg_color=THEME_COLORS["input_bg"], corner_radius=8, width=110)
        kpi_eta_box.pack(side="left", fill="y", padx=(4, 0), pady=2)
        ctk.CTkLabel(kpi_eta_box, text="RESTANTE (ETA)", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_eta = ctk.CTkLabel(kpi_eta_box, text="--:--", font=get_font(12, "bold"))
        self.lbl_eta.pack(anchor="w", padx=10, pady=(0, 6))

        # Barra de Progresso com Indicador Numérico
        prog_header = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        prog_header.pack(fill="x", padx=15, pady=(4, 2))
        ctk.CTkLabel(prog_header, text="Progresso do Bloco Atual:", font=get_font(11), text_color=THEME_COLORS["text_secondary"]).pack(side="left")
        self.lbl_percent = ctk.CTkLabel(prog_header, text="0%", font=get_font(11, "bold"), text_color=THEME_COLORS["accent_primary"])
        self.lbl_percent.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(card_telemetry, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=15, pady=(2, 12))
        self.progress_bar.set(0.0)

        # 4. Card: Console de Logs Integrado
        card_log = create_card_frame(self)
        card_log.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        lbl_log_title = ctk.CTkLabel(
            card_log,
            text="3. Terminal de Eventos e Execução",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_log_title.pack(fill="x", padx=15, pady=(10, 4))

        self.log_box = ctk.CTkTextbox(
            card_log,
            wrap="none",
            font=get_font(11, family="mono"),
            height=200,
            corner_radius=8,
            fg_color=THEME_COLORS["input_bg"],
        )
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    def _browse_dir(self):
        selected = filedialog.askdirectory(initialdir=self.entry_dir.get())
        if selected:
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, selected)

    def _on_mode_change(self, choice: str):
        if "Todos" in choice:
            self.entry_curso.configure(state="disabled")
        else:
            self.entry_curso.configure(state="normal")

    def _export_diagnostics(self):
        default_name = f"diagnostico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar Relatório de Diagnóstico Seguro",
            initialfile=default_name,
            filetypes=[("Arquivo JSON", "*.json"), ("Todos os Arquivos", "*.*")],
        )
        if target:
            try:
                saved = DiagnosticsStore.get_instance().export_report_file(target)
                self.append_log(f"\n[INFO] Relatório de diagnóstico exportado com sucesso: {saved}\n", tag="success")
                show_success(
                    self.winfo_toplevel(),
                    "Diagnóstico Exportado",
                    f"Relatório salvo com sucesso em:\n\n{saved}\n\nEnvie este arquivo ao suporte para análise rápida.",
                )
            except Exception as e:
                self.append_log(f"\n[ERRO] Falha ao exportar diagnóstico: {e}\n", tag="error")
                show_error(
                    self.winfo_toplevel(),
                    "Erro ao Exportar",
                    f"Não foi possível salvar o arquivo de diagnóstico:\n{e}",
                )

    def append_log(self, text: str, tag: str = "normal"):
        """Adiciona mensagem ao terminal de logs de forma thread-safe."""
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def copy_logs(self):
        """Copia todo o histórico do terminal de logs para a área de transferência."""
        content = self.log_box.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            show_success(
                self.winfo_toplevel(),
                "Logs Copiados",
                "O histórico do terminal de eventos foi copiado com sucesso para a sua área de transferência!",
            )
        else:
            show_info(
                self.winfo_toplevel(),
                "Terminal Vazio",
                "Não há registros de eventos no terminal para copiar no momento.",
            )

    def clear_logs(self):
        self.log_box.delete("1.0", "end")

    def update_telemetry(
        self,
        current_file: Optional[str] = None,
        speed_mbps: Optional[float] = None,
        eta_seconds: Optional[Union[int, float]] = None,
        progress_ratio: Optional[float] = None,
    ):
        """Atualiza os indicadores do dashboard em tempo real."""
        if current_file:
            self.lbl_current_file.configure(text=current_file)
        if speed_mbps is not None:
            self.lbl_speed.configure(text=f"{speed_mbps:.2f} MB/s")
        if eta_seconds is not None:
            total_secs = max(0, int(round(eta_seconds)))
            if total_secs < 60:
                self.lbl_eta.configure(text=f"{total_secs}s")
            else:
                mins = total_secs // 60
                secs = total_secs % 60
                self.lbl_eta.configure(text=f"{mins}m {secs:02d}s")
        if progress_ratio is not None:
            clamped = max(0.0, min(1.0, progress_ratio))
            self.progress_bar.set(clamped)
            self.lbl_percent.configure(text=f"{int(clamped * 100)}%")

    def set_running_state(self, is_running: bool):
        """Alterna a disponibilidade dos botões durante execução."""
        if is_running:
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.seg_mode.configure(state="disabled")
        else:
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.seg_mode.configure(state="normal")
            self.lbl_speed.configure(text="0.00 MB/s")
            self.lbl_eta.configure(text="--:--")

    def get_run_parameters(self) -> Dict[str, Any]:
        """Extrai todos os parâmetros configurados pelo usuário na tela."""
        is_single = "Específico" in self.mode_var.get() or self.mode_var.get() == "single"
        # Trata resolução (remove ' HD')
        raw_quality = self.var_quality.get().split()[0]
        return {
            "mode": "single" if is_single else "batch",
            "curso_input": self.entry_curso.get().strip() if is_single else None,
            "download_dir": self.entry_dir.get().strip(),
            "download_videos": self.var_videos.get(),
            "preferred_quality": raw_quality,
            "force": self.var_force.get(),
        }
