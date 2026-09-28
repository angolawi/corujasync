import os
import sys
import queue
import time
from pathlib import Path
from tkinter import filedialog, messagebox

# Auto-configura caminhos para libtk/libtcl se estiverem em ~/.local
local_lib = os.path.expanduser("~/.local/usr/lib")
if os.path.isdir(local_lib):
    tcl_dir = os.path.join(local_lib, "tcl8.6")
    tk_dir = os.path.join(local_lib, "tk8.6")
    if os.path.isdir(tcl_dir) and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = tcl_dir
    if os.path.isdir(tk_dir) and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = tk_dir
    if sys.platform != "win32":
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if local_lib not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{local_lib}:{current_ld}"

import customtkinter as ctk

from core.config import load_config, save_config, get_default_download_dir
from core.events import ProgressEvent, StatusEvent, DisciplineEvent, LessonEvent, VideoEvent
from legal.license_verifier import is_eula_accepted
from ui.gui.views.eula_dialog import EulaDialog
from ui.gui.workers import DownloadWorker


class ConcursoDownloaderApp(ctk.CTk):
    """Aplicação desktop principal para download de materiais de estudo."""

    def __init__(self):
        super().__init__()

        self.config = load_config()
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        ctk.set_default_color_theme("blue")

        self.title("Concurso Downloader - Backup Pessoal de Estudos")
        self.geometry("920x680")
        self.minsize(800, 580)

        self.event_queue = queue.Queue()
        self.worker: Optional[DownloadWorker] = None

        self._build_ui()
        self.after(200, self._check_first_boot_eula)
        self.after(100, self._poll_event_queue)

    def _check_first_boot_eula(self):
        if not is_eula_accepted():
            EulaDialog(self, on_accepted_callback=self._on_eula_accepted)

    def _on_eula_accepted(self):
        self._append_log("[INFO] Termos de Uso aceitos. Bem-vindo ao Concurso Downloader!\n", tag="info")

    def _build_ui(self):
        # Header Superior
        header_frame = ctk.CTkFrame(self, height=65, corner_radius=0)
        header_frame.pack(fill="x", side="top")

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Concurso Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#3B8ED0",
        )
        title_lbl.pack(side="left", padx=20, pady=(10, 0))

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Backup Inteligente e Offline de Estudos",
            font=ctk.CTkFont(size=12),
            text_color="#9E9E9E",
        )
        sub_lbl.pack(side="left", padx=5, pady=(15, 0))

        self.session_badge = ctk.CTkLabel(
            header_frame,
            text="⚪ Pronto",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9E9E9E",
        )
        self.session_badge.pack(side="right", padx=20, pady=10)

        # Tabs Principais
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        self.tab_download = self.tabview.add("Download")
        self.tab_settings = self.tabview.add("Configurações & Login")
        self.tab_about = self.tabview.add("Termos & Sobre")

        self._build_download_tab()
        self._build_settings_tab()
        self._build_about_tab()

    def _build_download_tab(self):
        # Painel superior de parâmetros de download
        top_box = ctk.CTkFrame(self.tab_download)
        top_box.pack(fill="x", padx=10, pady=10)

        # Modo de Download
        mode_row = ctk.CTkFrame(top_box, fg_color="transparent")
        mode_row.pack(fill="x", padx=10, pady=5)

        self.mode_var = ctk.StringVar(value="single")
        self.radio_single = ctk.CTkRadioButton(
            mode_row,
            text="Pacote ou Curso Específico (URL ou ID)",
            variable=self.mode_var,
            value="single",
            command=self._on_mode_change,
        )
        self.radio_single.pack(side="left", padx=(0, 20))

        self.radio_batch = ctk.CTkRadioButton(
            mode_row,
            text="Todos os Cursos Matriculados (Modo Batch)",
            variable=self.mode_var,
            value="batch",
            command=self._on_mode_change,
        )
        self.radio_batch.pack(side="left")

        # Entrada de URL / ID
        input_row = ctk.CTkFrame(top_box, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=5)

        self.input_lbl = ctk.CTkLabel(input_row, text="Curso / Pacote:", width=110, anchor="w")
        self.input_lbl.pack(side="left")

        self.entry_curso = ctk.CTkEntry(
            input_row,
            placeholder_text="Cole a URL ou ID do pacote (ex: 400565 ou https://.../pacote/400565)",
        )
        self.entry_curso.pack(side="left", fill="x", expand=True, padx=5)

        # Pasta de Destino
        dir_row = ctk.CTkFrame(top_box, fg_color="transparent")
        dir_row.pack(fill="x", padx=10, pady=5)

        dir_lbl = ctk.CTkLabel(dir_row, text="Pasta Destino:", width=110, anchor="w")
        dir_lbl.pack(side="left")

        self.entry_dir = ctk.CTkEntry(dir_row)
        self.entry_dir.insert(0, self.config.get("download_dir", get_default_download_dir()))
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=5)

        btn_browse = ctk.CTkButton(dir_row, text="Procurar...", width=90, command=self._browse_directory)
        btn_browse.pack(side="right")

        # Linha de Opções Rápidas
        options_row = ctk.CTkFrame(top_box, fg_color="transparent")
        options_row.pack(fill="x", padx=10, pady=5)

        self.var_videos = ctk.BooleanVar(value=self.config.get("download_videos", False))
        self.chk_videos = ctk.CTkCheckBox(options_row, text="Baixar Videoaulas (.mp4)", variable=self.var_videos)
        self.chk_videos.pack(side="left", padx=(0, 20))

        qual_lbl = ctk.CTkLabel(options_row, text="Qualidade:")
        qual_lbl.pack(side="left", padx=(0, 5))

        self.var_quality = ctk.StringVar(value=self.config.get("preferred_quality", "720p"))
        self.opt_quality = ctk.CTkOptionMenu(
            options_row,
            values=["720p", "480p", "360p"],
            variable=self.var_quality,
            width=90,
        )
        self.opt_quality.pack(side="left", padx=(0, 20))

        self.var_force = ctk.BooleanVar(value=False)
        self.chk_force = ctk.CTkCheckBox(options_row, text="Forçar Rechecagem no Navegador", variable=self.var_force)
        self.chk_force.pack(side="left")

        # Botões de Ação
        btn_row = ctk.CTkFrame(top_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(10, 5))

        self.btn_start = ctk.CTkButton(
            btn_row,
            text="▶ Iniciar Download",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_download,
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_row,
            text="⏹ Cancelar",
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            state="disabled",
            command=self._stop_download,
        )
        self.btn_stop.pack(side="left")

        self.btn_diag = ctk.CTkButton(
            btn_row,
            text="🛠 Exportar Diagnóstico",
            fg_color="#455A64",
            hover_color="#37474F",
            command=self._export_diagnostics,
        )
        self.btn_diag.pack(side="right")

        # Painel Central de Progresso
        progress_box = ctk.CTkFrame(self.tab_download)
        progress_box.pack(fill="x", padx=10, pady=(5, 10))

        prog_labels = ctk.CTkFrame(progress_box, fg_color="transparent")
        prog_labels.pack(fill="x", padx=10, pady=(5, 0))

        self.lbl_current_file = ctk.CTkLabel(
            prog_labels, text="Nenhum download ativo", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        self.lbl_current_file.pack(side="left")

        self.lbl_speed_eta = ctk.CTkLabel(
            prog_labels, text="", font=ctk.CTkFont(size=11), text_color="#A0A0A0"
        )
        self.lbl_speed_eta.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(progress_box)
        self.progress_bar.pack(fill="x", padx=10, pady=(5, 10))
        self.progress_bar.set(0.0)

        # Console de Logs
        self.log_box = ctk.CTkTextbox(
            self.tab_download, wrap="none", font=ctk.CTkFont(family="monospace", size=11)
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 5))

    def _build_settings_tab(self):
        container = ctk.CTkFrame(self.tab_settings)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # Seção Credenciais
        lbl_cred = ctk.CTkLabel(
            container, text="Autenticação na Plataforma", font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_cred.pack(anchor="w", padx=15, pady=(15, 5))

        cred_note = ctk.CTkLabel(
            container,
            text="As credenciais são salvas exclusivamente de forma local no seu computador.",
            text_color="#888888",
            font=ctk.CTkFont(size=11),
        )
        cred_note.pack(anchor="w", padx=15, pady=(0, 10))

        row_email = ctk.CTkFrame(container, fg_color="transparent")
        row_email.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_email, text="E-mail:", width=110, anchor="w").pack(side="left")
        self.entry_email = ctk.CTkEntry(row_email, width=320)
        self.entry_email.insert(0, self.config.get("email", ""))
        self.entry_email.pack(side="left")

        row_pass = ctk.CTkFrame(container, fg_color="transparent")
        row_pass.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_pass, text="Senha:", width=110, anchor="w").pack(side="left")
        self.entry_senha = ctk.CTkEntry(row_pass, width=320, show="*")
        self.entry_senha.insert(0, self.config.get("senha", ""))
        self.entry_senha.pack(side="left")

        row_wait = ctk.CTkFrame(container, fg_color="transparent")
        row_wait.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_wait, text="Espera Login (s):", width=110, anchor="w").pack(side="left")
        self.entry_wait = ctk.CTkEntry(row_wait, width=90)
        self.entry_wait.insert(0, str(self.config.get("wait_time", 60)))
        self.entry_wait.pack(side="left")

        # Seção Navegador
        lbl_browser = ctk.CTkLabel(
            container, text="Preferências do Navegador", font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_browser.pack(anchor="w", padx=15, pady=(20, 5))

        row_b = ctk.CTkFrame(container, fg_color="transparent")
        row_b.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_b, text="Navegador:", width=110, anchor="w").pack(side="left")
        self.var_browser = ctk.StringVar(value=self.config.get("preferred_browser", "auto"))
        self.opt_browser = ctk.CTkOptionMenu(
            row_b,
            values=["auto", "edge", "chrome", "firefox"],
            variable=self.var_browser,
            width=140,
        )
        self.opt_browser.pack(side="left")

        # Seção Tema Visual
        row_theme = ctk.CTkFrame(container, fg_color="transparent")
        row_theme.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_theme, text="Tema Visual:", width=110, anchor="w").pack(side="left")
        self.var_theme = ctk.StringVar(value=self.config.get("theme", "dark"))
        self.opt_theme = ctk.CTkOptionMenu(
            row_theme,
            values=["dark", "light"],
            variable=self.var_theme,
            command=self._change_theme,
            width=140,
        )
        self.opt_theme.pack(side="left")

        # Seção Licenciamento & Ativação
        lbl_lic = ctk.CTkLabel(
            container, text="Licenciamento & Ativação Premium", font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_lic.pack(anchor="w", padx=15, pady=(20, 5))

        from legal.license_manager import LicenseManager, get_machine_id
        lm = LicenseManager()
        lic_status = lm.get_status()

        row_mid = ctk.CTkFrame(container, fg_color="transparent")
        row_mid.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(row_mid, text="ID da Máquina:", width=110, anchor="w").pack(side="left")
        entry_mid = ctk.CTkEntry(row_mid, width=220)
        entry_mid.insert(0, get_machine_id())
        entry_mid.configure(state="readonly")
        entry_mid.pack(side="left")

        row_key = ctk.CTkFrame(container, fg_color="transparent")
        row_key.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_key, text="Chave de Licença:", width=110, anchor="w").pack(side="left")
        self.entry_license_key = ctk.CTkEntry(row_key, width=320, placeholder_text="Cole sua chave (CDL-...)")
        if lic_status.get("license_key"):
            self.entry_license_key.insert(0, lic_status["license_key"])
        self.entry_license_key.pack(side="left", padx=(0, 10))

        btn_activate = ctk.CTkButton(
            row_key,
            text="Ativar Chave",
            width=100,
            command=self._activate_license_key,
        )
        btn_activate.pack(side="left")

        status_text = f"Status: {lic_status.get('tier', '').upper()} - {lic_status.get('message')}"
        status_color = "#4CAF50" if lic_status.get("is_active") else "#FF9800"
        self.lbl_lic_status = ctk.CTkLabel(
            container, text=status_text, font=ctk.CTkFont(size=11, weight="bold"), text_color=status_color
        )
        self.lbl_lic_status.pack(anchor="w", padx=15, pady=(2, 10))

        btn_save = ctk.CTkButton(
            container,
            text="Salvar Preferências",
            fg_color="#1976D2",
            hover_color="#1565C0",
            width=160,
            command=self._save_settings,
        )
        btn_save.pack(anchor="w", padx=15, pady=20)

    def _build_about_tab(self):
        container = ctk.CTkFrame(self.tab_about)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(
            container,
            text="Concurso Downloader v2.0 - Backup Inteligente",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#3B8ED0",
        )
        title.pack(anchor="w", padx=20, pady=(15, 5))

        disclaimer_text = (
            "Aviso de Isenção de Responsabilidade e Propriedade Intelectual:\n\n"
            "• Este software é um utilitário de código aberto para fins estritamente privados de estudo "
            "e backup offline (Art. 46, II da Lei 9.610/98).\n"
            "• O software NÃO remove, altera ou oculta marcas d'água (CPF, nome do aluno) dos PDFs e vídeos.\n"
            "• A redistribuição, venda, doação ou compartilhamento de materiais com terceiros constitui "
            "crime previsto no Artigo 184 do Código Penal Brasileiro.\n"
            "• Não há afiliação, patrocínio ou parceria com o Estratégia Concursos ou qualquer entidade de ensino.\n"
            "• Toda a execução é 100% local (client-side), sem servidores intermediários ou guarda de dados na nuvem."
        )

        lbl_desc = ctk.CTkLabel(
            container, text=disclaimer_text, justify="left", wraplength=700, font=ctk.CTkFont(size=12)
        )
        lbl_desc.pack(anchor="w", padx=20, pady=10)

        accepted_at = self.config.get("eula_accepted_at", "Não registrado")
        lbl_eula = ctk.CTkLabel(
            container,
            text=f"Status da Licença: Termos de Uso Aceitos em {accepted_at}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4CAF50",
        )
        lbl_eula.pack(anchor="w", padx=20, pady=10)

        btn_eula = ctk.CTkButton(
            container,
            text="Exibir Termos de Uso Completos",
            width=220,
            command=lambda: EulaDialog(self, on_accepted_callback=None),
        )
        btn_eula.pack(anchor="w", padx=20, pady=10)

    def _browse_directory(self):
        selected = filedialog.askdirectory(initialdir=self.entry_dir.get())
        if selected:
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, selected)

    def _export_diagnostics(self):
        from core.diagnostics import DiagnosticsStore
        from datetime import datetime

        default_name = f"diagnostico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar Relatório de Diagnóstico Seguro",
            initialfile=default_name,
            filetypes=[("Arquivo JSON", "*.json"), ("Todos os Arquivos", "*.*")],
        )
        if target:
            try:
                saved_path = DiagnosticsStore.get_instance().export_report_file(target)
                self._append_log(f"\n[INFO] Relatório de diagnóstico exportado para: {saved_path}\n", tag="success")
                messagebox.showinfo(
                    "Diagnóstico Exportado",
                    f"O relatório de diagnóstico seguro foi salvo com sucesso em:\n\n{saved_path}\n\nEnvie este arquivo ao suporte para análise técnica.",
                )
            except Exception as e:
                self._append_log(f"\n[ERRO] Falha ao exportar diagnóstico: {e}\n", tag="error")
                messagebox.showerror("Erro", f"Não foi possível salvar o diagnóstico: {e}")

    def _activate_license_key(self):
        from legal.license_manager import LicenseManager
        key = self.entry_license_key.get().strip()
        if not key:
            messagebox.showwarning("Aviso", "Por favor, informe uma chave de licença válida.")
            return

        lm = LicenseManager()
        success, msg = lm.activate(key)
        if success:
            self.lbl_lic_status.configure(text=f"Status: ATIVA - {msg}", text_color="#4CAF50")
            self._append_log(f"\n[✓] {msg}\n", tag="success")
            messagebox.showinfo("Sucesso", msg)
        else:
            self.lbl_lic_status.configure(text=f"Status: INVÁLIDA - {msg}", text_color="#D32F2F")
            self._append_log(f"\n[ERRO] Ativação falhou: {msg}\n", tag="error")
            messagebox.showerror("Falha na Ativação", msg)

    def _on_mode_change(self):
        if self.mode_var.get() == "batch":
            self.entry_curso.configure(state="disabled")
        else:
            self.entry_curso.configure(state="normal")

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.config["theme"] = choice
        save_config(self.config)

    def _save_settings(self):
        self.config["email"] = self.entry_email.get().strip()
        self.config["senha"] = self.entry_senha.get().strip()
        try:
            self.config["wait_time"] = int(self.entry_wait.get().strip())
        except ValueError:
            self.config["wait_time"] = 60
        self.config["preferred_browser"] = self.var_browser.get()
        self.config["download_dir"] = self.entry_dir.get().strip()
        self.config["download_videos"] = self.var_videos.get()
        self.config["preferred_quality"] = self.var_quality.get()

        save_config(self.config)
        messagebox.showinfo("Sucesso", "Preferências salvas com sucesso!")

    def _append_log(self, text: str, tag: str = "normal"):
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def _start_download(self):
        if not is_eula_accepted():
            EulaDialog(self, on_accepted_callback=self._start_download)
            return

        download_dir = self.entry_dir.get().strip()
        if not download_dir:
            messagebox.showerror("Erro", "Por favor, especifique uma pasta de destino.")
            return

        mode = self.mode_var.get()
        curso_input = self.entry_curso.get().strip() if mode == "single" else None

        if mode == "single" and not curso_input:
            messagebox.showerror("Erro", "Por favor, informe a URL ou ID do pacote/curso.")
            return

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.session_badge.configure(text="🟡 Executando...", text_color="#FFA000")
        self.progress_bar.set(0.0)

        # Inicia Worker Thread
        self.worker = DownloadWorker(
            event_queue=self.event_queue,
            download_dir=download_dir,
            curso_input=curso_input,
            email=self.entry_email.get().strip(),
            senha=self.entry_senha.get().strip(),
            download_videos=self.var_videos.get(),
            preferred_quality=self.var_quality.get(),
            force=self.var_force.get(),
            preferred_browser=self.var_browser.get(),
            wait_time=int(self.entry_wait.get().strip() or "60"),
        )
        self.worker.start()

    def _stop_download(self):
        if self.worker and self.worker.is_alive():
            self.worker.cancel()
            self._append_log("\n[AVISO] Cancelamento solicitado. Aguardando conclusão do bloco atual...\n")
            self.btn_stop.configure(state="disabled")

    def _poll_event_queue(self):
        """Processa eventos vindos da thread do worker sem travar a interface."""
        try:
            while True:
                event_type, data = self.event_queue.get_nowait()

                if event_type == "banner":
                    msg = f"\n=== {data.get('mode')} ===\nDestino: {data.get('dir')}\n"
                    if data.get("name"):
                        msg += f"Alvo: {data.get('name')}\n"
                    self._append_log(msg)

                elif event_type == "status":
                    prefix = {
                        "info": "  [INFO] ",
                        "warning": "  [AVISO] ",
                        "error": "  [ERRO] ",
                        "success": "  [✓] ",
                    }.get(data.level, "  ")
                    self._append_log(f"{prefix}{data.message}\n")

                elif event_type == "discipline":
                    if data.status == "started":
                        self._append_log(f"\n━━━ [{data.index}/{data.total}] Disciplina: {data.title}\n")
                    elif data.status == "skipped":
                        self._append_log(f"  ↷ [{data.index}/{data.total}] {data.title} (Já concluída)\n")
                    elif data.status == "completed":
                        self._append_log(f"✓ Concluída disciplina: {data.title} ({data.lesson_count} aulas)\n")

                elif event_type == "lesson":
                    if data.status == "started":
                        self._append_log(f"  → [{data.index}/{data.total}] {data.title}\n")
                    elif data.status == "skipped":
                        self._append_log(f"  ↷ [{data.index}/{data.total}] {data.title} (já baixada)\n")

                elif event_type == "video_playlist":
                    self._append_log(f"       🎬 Playlist: {data} vídeos encontrados.\n")

                elif event_type == "video":
                    if data.status == "started":
                        self._append_log(f"        ▶ [{data.index}/{data.total}] {data.title}\n")
                    elif data.status == "skipped":
                        self._append_log(f"        ↷ [{data.index}/{data.total}] {data.title} (já baixado)\n")

                elif event_type == "progress":
                    event: ProgressEvent = data
                    self.lbl_current_file.configure(text=f"Baixando: {event.filename}")
                    pct_fraction = min(max(event.percent / 100.0, 0.0), 1.0)
                    self.progress_bar.set(pct_fraction)

                    speed_mb = event.speed_bytes_sec / (1024 * 1024)
                    eta_str = f"{int(event.eta_seconds)}s" if event.eta_seconds else "--"
                    down_mb = event.downloaded_bytes / (1024 * 1024)
                    total_mb = (event.total_bytes / (1024 * 1024)) if event.total_bytes else 0

                    self.lbl_speed_eta.configure(
                        text=f"{down_mb:.1f}/{total_mb:.1f} MB | {speed_mb:.2f} MB/s | ETA: {eta_str}"
                    )

                elif event_type == "finished":
                    self.btn_start.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    if data.get("success"):
                        self.session_badge.configure(text="🟢 Concluído", text_color="#4CAF50")
                        self._append_log("\n[✓] Processo de download finalizado com sucesso!\n")
                    else:
                        self.session_badge.configure(text="🔴 Interrompido", text_color="#F44336")
                        self._append_log(f"\n[✗] Finalizado com avisos/erros: {data.get('error', '')}\n")

        except queue.Empty:
            pass

        self.after(100, self._poll_event_queue)


def run_gui():
    app = ConcursoDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
