import os
import sys
import subprocess
import shutil
from typing import Callable, Optional, Dict, Any, Union
from tkinter import filedialog
from datetime import datetime
import customtkinter as ctk

from ui.gui.dialogs import show_info, show_success, show_error, show_warning, ask_confirm
from ui.gui.theme import (
    THEME_COLORS,
    RADIUS_CARD,
    RADIUS_BUTTON,
    RADIUS_INPUT,
    create_card_frame,
    get_font,
)
from core.config import get_default_download_dir
from core.diagnostics import DiagnosticsStore
from legal.license_manager import LicenseManager


class DownloadView(ctk.CTkScrollableFrame):
    """
    Download Studio & Mission Control HUD moderno inspirado no Google Stitch.
    Combina seleção de conteúdo, opções granulares de mídia, dashboard de
    telemetria em tempo real (MB/s, ETA, progresso duplo) e console de terminal.
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
        # =====================================================================
        # CARD 1: Modo e Seleção de Conteúdo (Alvo do Download)
        # =====================================================================
        card_target = create_card_frame(self)
        card_target.pack(fill="x", padx=15, pady=(15, 8))

        # Cabeçalho: Título da Seção + Badge VIP/Licença
        head_row = ctk.CTkFrame(card_target, fg_color="transparent")
        head_row.pack(fill="x", padx=16, pady=(14, 8))

        title_left = ctk.CTkFrame(head_row, fg_color="transparent")
        title_left.pack(side="left")

        dot_ind = ctk.CTkLabel(
            title_left,
            text="●",
            font=get_font(12),
            text_color=THEME_COLORS["accent_primary"],
        )
        dot_ind.pack(side="left", padx=(0, 6))

        lbl_target_title = ctk.CTkLabel(
            title_left,
            text="1. Modo e Seleção de Conteúdo",
            font=get_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_target_title.pack(side="left")

        is_pro = self.license_manager.is_premium()
        badge_text = "★ LICENÇA VITALÍCIA PRO ATIVA" if is_pro else "★ PLANO FREE (1 DISCIPLINA DEMO)"
        badge_fg = ("#DCFCE7", "#064E3B") if is_pro else ("#FEF3C7", "#78350F")
        badge_tc = ("#15803D", "#34D399") if is_pro else ("#B45309", "#FBBF24")

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

        # Segmented Control para Alternar Modo (Google Stitch style)
        self.mode_var = ctk.StringVar(value="single")
        self.seg_mode = ctk.CTkSegmentedButton(
            card_target,
            values=["📦 Pacote / Curso Específico", "📚 Todos os Cursos Matriculados"],
            variable=self.mode_var,
            font=get_font(12, "bold"),
            height=34,
            corner_radius=RADIUS_BUTTON,
            selected_color=THEME_COLORS["accent_primary"],
            selected_hover_color=THEME_COLORS["accent_primary_hover"],
            command=self._on_mode_change,
        )
        self.seg_mode.pack(fill="x", padx=16, pady=(0, 12))

        # Linha Entrada de URL / ID
        self.row_input = ctk.CTkFrame(card_target, fg_color="transparent")
        self.row_input.pack(fill="x", padx=16, pady=3)

        self.lbl_curso = ctk.CTkLabel(
            self.row_input,
            text="URL ou ID:",
            width=90,
            anchor="w",
            font=get_font(11, "bold"),
            text_color=THEME_COLORS["text_secondary"],
        )
        self.lbl_curso.pack(side="left")

        self.entry_curso = ctk.CTkEntry(
            self.row_input,
            placeholder_text="Cole a URL ou ID do pacote (ex: https://.../pacote/400565 ou 400565)",
            font=get_font(11, family="mono"),
            height=36,
            corner_radius=RADIUS_INPUT,
            fg_color=THEME_COLORS["input_bg"],
            border_color=THEME_COLORS["border"],
        )
        self.entry_curso.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_clear = ctk.CTkButton(
            self.row_input,
            text="✕",
            width=36,
            height=36,
            font=get_font(11, "bold"),
            corner_radius=RADIUS_BUTTON,
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=lambda: self.entry_curso.delete(0, "end"),
        )
        btn_clear.pack(side="right")

        # Linha Diretório de Destino
        row_dir = ctk.CTkFrame(card_target, fg_color="transparent")
        row_dir.pack(fill="x", padx=16, pady=(4, 14))

        lbl_dir = ctk.CTkLabel(
            row_dir,
            text="Destino:",
            width=90,
            anchor="w",
            font=get_font(11, "bold"),
            text_color=THEME_COLORS["text_secondary"],
        )
        lbl_dir.pack(side="left")

        self.entry_dir = ctk.CTkEntry(
            row_dir,
            font=get_font(11, family="mono"),
            height=36,
            corner_radius=RADIUS_INPUT,
            fg_color=THEME_COLORS["input_bg"],
            border_color=THEME_COLORS["border"],
        )
        initial_dir = self.config.get("download_dir", get_default_download_dir())
        self.entry_dir.insert(0, initial_dir)
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_browse = ctk.CTkButton(
            row_dir,
            text="📁 Procurar",
            width=95,
            height=36,
            font=get_font(11, "bold"),
            corner_radius=RADIUS_BUTTON,
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=self._browse_dir,
        )
        btn_browse.pack(side="right")

        # =====================================================================
        # CARD 2: Opções de Mídia e Rechecagem Inteligente
        # =====================================================================
        card_options = create_card_frame(self)
        card_options.pack(fill="x", padx=15, pady=4)

        opt_head = ctk.CTkFrame(card_options, fg_color="transparent")
        opt_head.pack(fill="x", padx=16, pady=(12, 6))

        opt_left = ctk.CTkFrame(opt_head, fg_color="transparent")
        opt_left.pack(side="left")
        ctk.CTkLabel(opt_left, text="●", font=get_font(12), text_color=THEME_COLORS["cyan"]).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(opt_left, text="2. Opções de Mídia e Rechecagem Inteligente", font=get_font(13, "bold"), text_color=THEME_COLORS["text_primary"]).pack(side="left")

        ctk.CTkLabel(
            opt_head,
            text="Resolução de Conflitos: Smart Resume 0,001s",
            font=get_font(10, family="mono"),
            text_color=THEME_COLORS["accent_primary"],
        ).pack(side="right")

        row_toggles = ctk.CTkFrame(card_options, fg_color="transparent")
        row_toggles.pack(fill="x", padx=16, pady=(0, 12))

        # Switch de Videoaulas
        self.var_videos = ctk.BooleanVar(value=self.config.get("download_videos", False))
        self.switch_videos = ctk.CTkSwitch(
            row_toggles,
            text="🎬 Videoaulas (.mp4)",
            variable=self.var_videos,
            font=get_font(11, "bold"),
            progress_color=THEME_COLORS["accent_primary"],
        )
        self.switch_videos.pack(side="left", padx=(0, 16))

        # Seletor de Resolução
        lbl_qual = ctk.CTkLabel(row_toggles, text="Resolução:", font=get_font(11), text_color=THEME_COLORS["text_secondary"])
        lbl_qual.pack(side="left", padx=(0, 6))

        self.var_quality = ctk.StringVar(value=self.config.get("preferred_quality", "720p HD"))
        self.seg_quality = ctk.CTkSegmentedButton(
            row_toggles,
            values=["720p HD", "480p", "360p"],
            variable=self.var_quality,
            font=get_font(10, "bold"),
            height=28,
            corner_radius=RADIUS_BUTTON,
            selected_color=THEME_COLORS["accent_primary"],
        )
        self.seg_quality.pack(side="left", padx=(0, 16))

        # Switch de Hierarquia Inteligente
        self.var_hierarchy = ctk.BooleanVar(value=True)
        self.switch_hierarchy = ctk.CTkSwitch(
            row_toggles,
            text="📁 Hierarquia por Concurso",
            variable=self.var_hierarchy,
            font=get_font(11),
            progress_color=THEME_COLORS["success"],
        )
        self.switch_hierarchy.pack(side="left", padx=(0, 16))

        # Switch de Rechecagem Forçada
        self.var_force = ctk.BooleanVar(value=False)
        self.switch_force = ctk.CTkSwitch(
            row_toggles,
            text="🔄 Forçar Rechecagem",
            variable=self.var_force,
            font=get_font(11),
            progress_color=THEME_COLORS["warning"],
        )
        self.switch_force.pack(side="left")

        # =====================================================================
        # CARD 3: Painel de Telemetria em Tempo Real (HUD)
        # =====================================================================
        card_telemetry = create_card_frame(self)
        card_telemetry.pack(fill="x", padx=15, pady=4)

        # Header do HUD
        hud_head = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        hud_head.pack(fill="x", padx=16, pady=(12, 6))

        hud_left = ctk.CTkFrame(hud_head, fg_color="transparent")
        hud_left.pack(side="left")
        ctk.CTkLabel(hud_left, text="●", font=get_font(12), text_color=THEME_COLORS["success"]).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(hud_left, text="3. Painel de Telemetria em Tempo Real (HUD)", font=get_font(13, "bold"), text_color=THEME_COLORS["text_primary"]).pack(side="left")

        ctk.CTkLabel(
            hud_head,
            text="Sessão: TLSv1.3 Encrypted",
            font=get_font(10, family="mono"),
            text_color=THEME_COLORS["accent_primary"],
        ).pack(side="right")

        # Grid de 4 Gauges (Google Stitch HUD)
        kpi_grid = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        kpi_grid.pack(fill="x", padx=16, pady=(4, 10))

        # Gauge 1: Taxa de Download (MB/s)
        g1 = ctk.CTkFrame(kpi_grid, fg_color=THEME_COLORS["input_bg"], border_color=THEME_COLORS["border"], border_width=1, corner_radius=10)
        g1.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(g1, text="TAXA DE DOWNLOAD", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_speed = ctk.CTkLabel(g1, text="0.00 MB/s", font=get_font(15, "bold"), text_color=THEME_COLORS["accent_primary"])
        self.lbl_speed.pack(anchor="w", padx=10, pady=(0, 6))

        # Gauge 2: Estimativa de Tempo (ETA)
        g2 = ctk.CTkFrame(kpi_grid, fg_color=THEME_COLORS["input_bg"], border_color=THEME_COLORS["border"], border_width=1, corner_radius=10)
        g2.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(g2, text="TEMPO RESTANTE (ETA)", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_eta = ctk.CTkLabel(g2, text="--:--", font=get_font(15, "bold"), text_color=THEME_COLORS["cyan"])
        self.lbl_eta.pack(anchor="w", padx=10, pady=(0, 6))

        # Gauge 3: Progresso da Aula Atual
        g3 = ctk.CTkFrame(kpi_grid, fg_color=THEME_COLORS["input_bg"], border_color=THEME_COLORS["border"], border_width=1, corner_radius=10)
        g3.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(g3, text="AULA ATUAL", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_percent = ctk.CTkLabel(g3, text="0%", font=get_font(15, "bold"), text_color=THEME_COLORS["warning"])
        self.lbl_percent.pack(anchor="w", padx=10, pady=(0, 6))

        # Gauge 4: Progresso Geral
        g4 = ctk.CTkFrame(kpi_grid, fg_color=THEME_COLORS["input_bg"], border_color=THEME_COLORS["border"], border_width=1, corner_radius=10)
        g4.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(g4, text="ARQUIVO / STATUS", font=get_font(9, "bold"), text_color=THEME_COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_current_file = ctk.CTkLabel(g4, text="Pronto para iniciar", font=get_font(11, "bold"), text_color=THEME_COLORS["success"])
        self.lbl_current_file.pack(anchor="w", padx=10, pady=(2, 6))

        # Barra de Progresso Principal
        prog_row = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        prog_row.pack(fill="x", padx=16, pady=(2, 2))
        ctk.CTkLabel(prog_row, text="Progresso do Bloco Atual:", font=get_font(11), text_color=THEME_COLORS["text_secondary"]).pack(side="left")
        self.lbl_prog_title = ctk.CTkLabel(prog_row, text="Sincronização Inativa", font=get_font(11, "bold"), text_color=THEME_COLORS["text_primary"])
        self.lbl_prog_title.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(card_telemetry, height=8, corner_radius=4, progress_color=THEME_COLORS["success"])
        self.progress_bar.pack(fill="x", padx=16, pady=(2, 12))
        self.progress_bar.set(0.0)

        # Barra de Botões de Ação
        btn_bar = ctk.CTkFrame(card_telemetry, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 14))

        self.btn_start = ctk.CTkButton(
            btn_bar,
            text="▶ Iniciar Sincronização Inteligente",
            fg_color=THEME_COLORS["success"],
            hover_color=THEME_COLORS["success_hover"],
            font=get_font(12, "bold"),
            height=38,
            corner_radius=RADIUS_BUTTON,
            command=self.on_start,
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_bar,
            text="⏹ Interromper",
            fg_color=THEME_COLORS["danger"],
            hover_color=THEME_COLORS["danger_hover"],
            font=get_font(12, "bold"),
            height=38,
            width=120,
            corner_radius=RADIUS_BUTTON,
            state="disabled",
            command=self.on_stop,
        )
        self.btn_stop.pack(side="left", padx=(0, 8))

        btn_open_folder = ctk.CTkButton(
            btn_bar,
            text="📁 Abrir Pasta",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            font=get_font(11, "bold"),
            height=38,
            width=110,
            corner_radius=RADIUS_BUTTON,
            command=self._open_download_dir,
        )
        btn_open_folder.pack(side="left")

        self.btn_diag = ctk.CTkButton(
            btn_bar,
            text="🛠 Diagnóstico",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            font=get_font(11),
            height=38,
            width=100,
            corner_radius=RADIUS_BUTTON,
            command=self._export_diagnostics,
        )
        self.btn_diag.pack(side="right")

        # =====================================================================
        # CARD 4: Terminal Log Console & Activity Stream
        # =====================================================================
        card_log = create_card_frame(self)
        card_log.pack(fill="both", expand=True, padx=15, pady=(4, 15))

        log_head = ctk.CTkFrame(card_log, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(10, 4))

        log_left = ctk.CTkFrame(log_head, fg_color="transparent")
        log_left.pack(side="left")
        ctk.CTkLabel(log_left, text="●", font=get_font(12), text_color=THEME_COLORS["accent_primary"]).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(log_left, text="4. Console de Atividades em Tempo Real", font=get_font(12, "bold"), text_color=THEME_COLORS["text_primary"]).pack(side="left")

        log_btns = ctk.CTkFrame(log_head, fg_color="transparent")
        log_btns.pack(side="right")

        self.btn_clear_log = ctk.CTkButton(
            log_btns,
            text="🗑 Limpar",
            fg_color="transparent",
            hover_color=("#E2E8F0", "#1E293B"),
            text_color=THEME_COLORS["text_secondary"],
            font=get_font(11),
            height=28,
            width=70,
            corner_radius=RADIUS_BUTTON,
            command=self.clear_logs,
        )
        self.btn_clear_log.pack(side="left", padx=2)

        self.btn_copy_log = ctk.CTkButton(
            log_btns,
            text="📋 Copiar Logs",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            text_color=THEME_COLORS["text_primary"],
            font=get_font(11, "bold"),
            height=28,
            width=100,
            corner_radius=RADIUS_BUTTON,
            command=self.copy_logs,
        )
        self.btn_copy_log.pack(side="left", padx=2)

        self.log_box = ctk.CTkTextbox(
            card_log,
            wrap="none",
            font=get_font(11, family="mono"),
            height=180,
            corner_radius=10,
            fg_color=THEME_COLORS["input_bg"],
            border_color=THEME_COLORS["border"],
            border_width=1,
        )
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _open_download_dir(self):
        target = self.entry_dir.get().strip()
        if not target or not os.path.exists(target):
            try:
                os.makedirs(target, exist_ok=True)
            except Exception:
                pass
        if os.path.exists(target):
            try:
                if sys.platform == "win32":
                    os.startfile(target)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", target])
                else:
                    subprocess.Popen(["xdg-open", target])
            except Exception as e:
                self.append_log(f"\n[AVISO] Não foi possível abrir pasta: {e}\n", tag="warning")

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
            short_name = os.path.basename(current_file) if len(current_file) > 40 else current_file
            self.lbl_current_file.configure(text=short_name)
            self.lbl_prog_title.configure(text=short_name)
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
            self.btn_start.configure(state="disabled", text="⏳ Sincronização em Andamento...")
            self.btn_stop.configure(state="normal")
            self.seg_mode.configure(state="disabled")
        else:
            self.btn_start.configure(state="normal", text="▶ Iniciar Sincronização Inteligente")
            self.btn_stop.configure(state="disabled")
            self.seg_mode.configure(state="normal")
            self.lbl_speed.configure(text="0.00 MB/s")
            self.lbl_eta.configure(text="--:--")
            self.lbl_prog_title.configure(text="Sincronização Inativa")

    def get_run_parameters(self) -> Dict[str, Any]:
        """Extrai todos os parâmetros configurados pelo usuário na tela."""
        is_single = "Específico" in self.mode_var.get() or self.mode_var.get() == "single"
        raw_quality = self.var_quality.get().split()[0]
        return {
            "mode": "single" if is_single else "batch",
            "curso_input": self.entry_curso.get().strip() if is_single else None,
            "download_dir": self.entry_dir.get().strip(),
            "download_videos": self.var_videos.get(),
            "preferred_quality": raw_quality,
            "force": self.var_force.get(),
        }
