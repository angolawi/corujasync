import os
import time
import subprocess
import sys
from typing import Dict, Any, List, Optional
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    RADIUS_CARD,
    RADIUS_BUTTON,
    RADIUS_INPUT,
    create_card_frame,
    get_font,
)
from core.indexer import CoursePdfIndexer
from core.config import get_default_download_dir


class SearchView(ctk.CTkFrame):
    """
    Spotlight Search & Base de Conhecimento Offline inspirada no Google Stitch.
    Permite pesquisa instantânea por tópicos de editais, legislações e ementas
    geradas em 'Assuntos_dessa_aula.txt' em todos os concursos baixados.
    """

    def __init__(self, parent, config: Dict[str, Any], **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.indexer = CoursePdfIndexer()

        self._build_ui()

    def _build_ui(self):
        # 1. Floating Omnibar Card (Google Stitch Style)
        omnibar_card = create_card_frame(self)
        omnibar_card.pack(fill="x", padx=15, pady=(15, 8))

        # Linha Principal de Entrada
        row_input = ctk.CTkFrame(omnibar_card, fg_color="transparent")
        row_input.pack(fill="x", padx=16, pady=(14, 8))

        self.entry_query = ctk.CTkEntry(
            row_input,
            placeholder_text="Pesquise qualquer tema (ex: atos administrativos, poder constituinte, licitação, crase)...",
            font=get_font(13),
            height=42,
            corner_radius=RADIUS_INPUT,
            fg_color=THEME_COLORS["input_bg"],
            border_color=THEME_COLORS["border_focus"],
            border_width=1,
        )
        self.entry_query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_query.bind("<Return>", lambda e: self._perform_search())

        btn_clear = ctk.CTkButton(
            row_input,
            text="✕ Limpar",
            width=80,
            height=42,
            font=get_font(11),
            corner_radius=RADIUS_BUTTON,
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=self._clear_search,
        )
        btn_clear.pack(side="left", padx=(0, 6))

        btn_search = ctk.CTkButton(
            row_input,
            text="🔍 Pesquisar",
            fg_color=THEME_COLORS["accent_primary"],
            hover_color=THEME_COLORS["accent_primary_hover"],
            font=get_font(12, "bold"),
            height=42,
            width=110,
            corner_radius=RADIUS_BUTTON,
            command=self._perform_search,
        )
        btn_search.pack(side="left")

        # Linha de Filtros & Telemetria do Índice
        row_filters = ctk.CTkFrame(omnibar_card, fg_color="transparent")
        row_filters.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            row_filters,
            text="🏛️ Concurso:",
            font=get_font(11, "bold"),
            text_color=THEME_COLORS["text_secondary"],
        ).pack(side="left", padx=(0, 6))

        concursos_list = ["Todos os Concursos (Geral)"] + self.indexer.get_concursos()
        self.combo_concurso = ctk.CTkOptionMenu(
            row_filters,
            values=concursos_list,
            font=get_font(11),
            height=32,
            width=230,
            corner_radius=RADIUS_BUTTON,
            fg_color=THEME_COLORS["input_bg"],
            button_color=THEME_COLORS["slate"],
            button_hover_color=THEME_COLORS["slate_hover"],
            command=lambda _: self._perform_search(),
        )
        self.combo_concurso.set("Todos os Concursos (Geral)")
        self.combo_concurso.pack(side="left", padx=(0, 10))

        btn_reindex = ctk.CTkButton(
            row_filters,
            text="🔄 Reindexar Acervo",
            font=get_font(11),
            height=32,
            width=130,
            corner_radius=RADIUS_BUTTON,
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            command=self._reindex_library,
        )
        btn_reindex.pack(side="left")

        # Contador de Resultados / Status
        self.lbl_stats = ctk.CTkLabel(
            row_filters,
            text="Base pronta para pesquisa instantânea",
            font=get_font(11, family="mono"),
            text_color=THEME_COLORS["success"],
            anchor="e",
        )
        self.lbl_stats.pack(side="right")

        # 2. Container Rolável de Resultados
        self.results_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            label_text="Resultados da Busca Spotlight",
            label_font=get_font(13, "bold"),
        )
        self.results_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._show_empty_state("Digite uma palavra-chave acima ou selecione um concurso para iniciar a busca.")

    def _clear_search(self):
        self.entry_query.delete(0, "end")
        self._show_empty_state("Digite uma palavra-chave acima ou selecione um concurso para iniciar a busca.")

    def _show_empty_state(self, message: str):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        empty_box = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        empty_box.pack(fill="both", expand=True, pady=40)

        ctk.CTkLabel(
            empty_box,
            text="🦉",
            font=get_font(28),
        ).pack(pady=(0, 8))

        lbl_msg = ctk.CTkLabel(
            empty_box,
            text=message,
            font=get_font(12),
            text_color=THEME_COLORS["text_muted"],
        )
        lbl_msg.pack()

    def _perform_search(self):
        query = self.entry_query.get().strip()
        if not query:
            self._show_empty_state("Por favor, digite um termo para pesquisar.")
            return

        download_dir = self.config.get("download_dir", get_default_download_dir())
        if not self.indexer.index_data.get("lessons") and not self.indexer.index_data.get("documents"):
            self.indexer.index_directory(download_dir)

        concurso_raw = self.combo_concurso.get() if hasattr(self, "combo_concurso") else None
        concurso_filter = None if "Todos os Concursos" in (concurso_raw or "") else concurso_raw

        t0 = time.time()
        results = self.indexer.search(query, concurso=concurso_filter, max_results=50)
        elapsed = time.time() - t0

        self.lbl_stats.configure(
            text=f"{len(results)} resultados encontrados em {elapsed:.2f}s"
        )
        self._display_results(results, query)

    def _reindex_library(self):
        download_dir = self.config.get("download_dir", get_default_download_dir())
        self.indexer.index_directory(download_dir, force_reindex=True)
        lessons_count = len(self.indexer.index_data.get("lessons", {}))
        docs_count = len(self.indexer.index_data.get("documents", {}))
        if hasattr(self, "combo_concurso"):
            self.combo_concurso.configure(values=["Todos os Concursos (Geral)"] + self.indexer.get_concursos())
        self.lbl_stats.configure(
            text=f"✓ {lessons_count} aulas e {docs_count} PDFs catalogados"
        )

    def _display_results(self, results: List[Dict[str, Any]], query: str):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not results:
            self._show_empty_state(f"Nenhum resultado encontrado para o termo '{query}'. Tente outros termos ou reindexe a pasta.")
            return

        for res in results:
            card = create_card_frame(self.results_frame)
            card.pack(fill="x", pady=5)

            # Cabeçalho do Card (Badges + Botões)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=14, pady=(12, 4))

            badge_row = ctk.CTkFrame(head, fg_color="transparent")
            badge_row.pack(side="left", fill="x", expand=True)

            # Badge do Concurso (Gold/Amber Stitch)
            raw_concurso = res.get("concurso", "Concurso").replace("_", " ")
            concurso_label = raw_concurso if len(raw_concurso) <= 30 else raw_concurso[:28] + "..."
            badge_concurso = ctk.CTkLabel(
                badge_row,
                text=f"🏛️ {concurso_label}",
                font=get_font(10, "bold"),
                fg_color=("#FEF3C7", "#78350F"),
                text_color=("#B45309", "#FBBF24"),
                corner_radius=6,
                padx=8,
                pady=2,
            )
            badge_concurso.pack(side="left", padx=(0, 6))

            # Badge da Disciplina (Indigo Stitch)
            badge_course = ctk.CTkLabel(
                badge_row,
                text=res.get("course", "Curso").replace("_", " "),
                font=get_font(10, "bold"),
                fg_color=("#EEF2FF", "#1E1B4B"),
                text_color=("#4338CA", "#818CF8"),
                corner_radius=6,
                padx=8,
                pady=2,
            )
            badge_course.pack(side="left", padx=(0, 6))

            # Badge da Aula
            is_subjects = res.get("source") == "subjects"
            badge_source = ctk.CTkLabel(
                badge_row,
                text="📋 Assuntos da Aula" if is_subjects else f"📄 PDF (Pág. {res.get('page', 1)})",
                font=get_font(10, "bold"),
                fg_color=("#DCFCE7", "#064E3B") if is_subjects else ("#F1F5F9", "#1E293B"),
                text_color=("#15803D", "#34D399") if is_subjects else THEME_COLORS["text_secondary"],
                corner_radius=6,
                padx=8,
                pady=2,
            )
            badge_source.pack(side="left")

            # Botões de Ação na Direita
            btn_frame = ctk.CTkFrame(head, fg_color="transparent")
            btn_frame.pack(side="right")

            filepath = res.get("filepath")
            if filepath and filepath.lower().endswith(".pdf") and os.path.exists(filepath):
                btn_open_pdf = ctk.CTkButton(
                    btn_frame,
                    text="📄 Abrir Livro (PDF)",
                    font=get_font(10, "bold"),
                    height=28,
                    corner_radius=RADIUS_BUTTON,
                    fg_color=THEME_COLORS["accent_primary"],
                    hover_color=THEME_COLORS["accent_primary_hover"],
                    command=lambda p=filepath: self._open_file(p),
                )
                btn_open_pdf.pack(side="left", padx=(0, 6))

            lesson_path = res.get("lesson_path")
            if lesson_path and os.path.exists(lesson_path):
                btn_open_dir = ctk.CTkButton(
                    btn_frame,
                    text="📁 Abrir Pasta",
                    font=get_font(10, "bold"),
                    height=28,
                    corner_radius=RADIUS_BUTTON,
                    fg_color=THEME_COLORS["slate"],
                    hover_color=THEME_COLORS["slate_hover"],
                    command=lambda p=lesson_path: self._open_file(p),
                )
                btn_open_dir.pack(side="left")

            # Título da Aula e Arquivo
            lesson_title = res.get("lesson", "Aula")
            if not is_subjects and res.get("filename"):
                lesson_title = f"{lesson_title}  •  {res.get('filename')}"

            lbl_file = ctk.CTkLabel(
                card,
                text=lesson_title,
                font=get_font(12, "bold"),
                text_color=THEME_COLORS["text_primary"],
                anchor="w",
            )
            lbl_file.pack(fill="x", padx=14, pady=(2, 4))

            # Caixa com o Snippet do Assunto / Trecho
            snippet_box = ctk.CTkFrame(card, fg_color=THEME_COLORS["input_bg"], corner_radius=8, border_color=THEME_COLORS["border"], border_width=1)
            snippet_box.pack(fill="x", padx=14, pady=(0, 10))

            snippet_text = res.get("snippet", "").strip()
            lbl_snippet = ctk.CTkLabel(
                snippet_box,
                text=f"[Ementa]: {snippet_text}" if is_subjects else f"[Trecho]: {snippet_text}",
                font=get_font(11, family="mono"),
                text_color=THEME_COLORS["text_secondary"],
                wraplength=680,
                justify="left",
                anchor="w",
            )
            lbl_snippet.pack(fill="x", padx=10, pady=8)

    def _open_file(self, target_path: Optional[str]):
        if not target_path or not os.path.exists(target_path):
            return
        try:
            if sys.platform == "win32":
                os.startfile(target_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target_path])
            else:
                subprocess.Popen(["xdg-open", target_path])
        except Exception:
            pass
