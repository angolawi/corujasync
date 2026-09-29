import os
import subprocess
import sys
from typing import Dict, Any, List, Optional
import customtkinter as ctk

from ui.gui.theme import (
    THEME_COLORS,
    RADIUS_CARD,
    RADIUS_BUTTON,
    create_card_frame,
    get_font,
)
from core.indexer import CoursePdfIndexer
from core.config import get_default_download_dir


class SearchView(ctk.CTkFrame):
    """
    Interface de busca global offline em todos os PDFs baixados no computador.
    Permite aos estudantes localizar termos, legislações e tópicos em segundos.
    """

    def __init__(self, parent, config: Dict[str, Any], **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.config = config
        self.indexer = CoursePdfIndexer()

        self._build_ui()

    def _build_ui(self):
        # 1. Card de Pesquisa & Controles
        search_card = create_card_frame(self)
        search_card.pack(fill="x", padx=15, pady=(15, 10))

        lbl_title = ctk.CTkLabel(
            search_card,
            text="🔍 Busca Global em Aulas, Assuntos e Livros",
            font=get_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_desc = ctk.CTkLabel(
            search_card,
            text="Pesquise por tópicos do edital, conceitos jurídicos, legislações ou assuntos abordados em todas as aulas e livros eletrônicos.",
            font=get_font(11),
            text_color=THEME_COLORS["text_muted"],
            anchor="w",
        )
        lbl_desc.pack(fill="x", padx=15, pady=(0, 10))

        # Linha de Busca Principal
        row_search = ctk.CTkFrame(search_card, fg_color="transparent")
        row_search.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_query = ctk.CTkEntry(
            row_search,
            placeholder_text="Digite o assunto ou termo (ex: Princípios Fundamentais, Poder Constituinte, Licitação)...",
            font=get_font(13),
            height=40,
        )
        self.entry_query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_query.bind("<Return>", lambda e: self._perform_search())

        # Seletor de Concurso (Entidade de Topo)
        concursos_list = ["Todos os Concursos"] + self.indexer.get_concursos()
        self.combo_concurso = ctk.CTkOptionMenu(
            row_search,
            values=concursos_list,
            font=get_font(12),
            height=40,
            width=210,
            fg_color=THEME_COLORS["slate"],
            button_color=THEME_COLORS["slate_hover"],
            button_hover_color=THEME_COLORS["slate_hover"],
        )
        self.combo_concurso.set("Todos os Concursos")
        self.combo_concurso.pack(side="left", padx=(0, 8))

        btn_search = ctk.CTkButton(
            row_search,
            text="🔍 Pesquisar",
            fg_color=THEME_COLORS["accent_primary"],
            hover_color=THEME_COLORS["accent_primary_hover"],
            font=get_font(13, "bold"),
            height=40,
            width=110,
            command=self._perform_search,
        )
        btn_search.pack(side="left", padx=(0, 8))

        btn_reindex = ctk.CTkButton(
            row_search,
            text="🔄 Reindexar",
            fg_color=THEME_COLORS["slate"],
            hover_color=THEME_COLORS["slate_hover"],
            font=get_font(12),
            height=40,
            width=95,
            command=self._reindex_library,
        )
        btn_reindex.pack(side="left")

        # Barra de Status do Índice
        lessons_count = len(self.indexer.index_data.get("lessons", {}))
        docs_count = len(self.indexer.index_data.get("documents", {}))
        self.lbl_stats = ctk.CTkLabel(
            search_card,
            text=f"📚 Base de conhecimento: {lessons_count} aulas catalogadas ({docs_count} PDFs prontos para busca).",
            font=get_font(11, "bold"),
            text_color=THEME_COLORS["text_secondary"],
            anchor="w",
        )
        self.lbl_stats.pack(fill="x", padx=15, pady=(0, 12))

        # 2. Container de Resultados da Busca
        self.results_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            label_text="Resultados Encontrados",
            label_font=get_font(13, "bold"),
        )
        self.results_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._show_empty_state("Digite uma palavra-chave acima e pressione 'Pesquisar' para iniciar.")

    def _show_empty_state(self, message: str):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        empty_box = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        empty_box.pack(fill="both", expand=True, pady=40)

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

        # Auto-indexa se o índice estiver vazio
        download_dir = self.config.get("download_dir", get_default_download_dir())
        if not self.indexer.index_data.get("lessons") and not self.indexer.index_data.get("documents"):
            self.indexer.index_directory(download_dir)

        concurso_filter = self.combo_concurso.get() if hasattr(self, "combo_concurso") else None
        results = self.indexer.search(query, concurso=concurso_filter, max_results=50)
        self._display_results(results, query)

    def _reindex_library(self):
        download_dir = self.config.get("download_dir", get_default_download_dir())
        new_count = self.indexer.index_directory(download_dir, force_reindex=True)
        lessons_count = len(self.indexer.index_data.get("lessons", {}))
        docs_count = len(self.indexer.index_data.get("documents", {}))
        if hasattr(self, "combo_concurso"):
            self.combo_concurso.configure(values=["Todos os Concursos"] + self.indexer.get_concursos())
        self.lbl_stats.configure(
            text=f"✓ Reindexação concluída! {lessons_count} aulas e {docs_count} PDFs catalogados para busca instantânea."
        )

    def _display_results(self, results: List[Dict[str, Any]], query: str):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not results:
            self._show_empty_state(f"Nenhum resultado encontrado para o termo '{query}'. Tente outros termos ou reindexe a pasta.")
            return

        for res in results:
            card = create_card_frame(self.results_frame)
            card.pack(fill="x", pady=6)

            # Cabeçalho do Card (Badges + Botões de Ação)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=12, pady=(10, 4))

            # Badge do Concurso (Entidade de Topo)
            raw_concurso = res.get("concurso", "Concurso").replace("_", " ")
            concurso_label = raw_concurso if len(raw_concurso) <= 32 else raw_concurso[:30] + "..."
            badge_concurso = ctk.CTkLabel(
                head,
                text=f"🏛️ {concurso_label}",
                font=get_font(10, "bold"),
                fg_color=("#FEF3C7", "#78350F"),
                text_color=("#B45309", "#FDE68A"),
                corner_radius=4,
                padx=6,
                pady=2,
            )
            badge_concurso.pack(side="left", padx=(0, 6))

            # Badge da Disciplina / Curso
            badge_course = ctk.CTkLabel(
                head,
                text=res.get("course", "Curso").replace("_", " "),
                font=get_font(10, "bold"),
                fg_color=("#DBEAFE", "#1E3A8A"),
                text_color=("#1D4ED8", "#93C5FD"),
                corner_radius=4,
                padx=6,
                pady=2,
            )
            badge_course.pack(side="left", padx=(0, 6))

            # Badge da Origem (Assuntos da Aula vs Livro PDF)
            is_subjects = res.get("source") == "subjects"
            badge_source = ctk.CTkLabel(
                head,
                text="📋 Assuntos da Aula" if is_subjects else f"📄 PDF (Pág. {res.get('page', 1)})",
                font=get_font(10, "bold"),
                fg_color=("#DCFCE7", "#14532D") if is_subjects else ("#E5E7EB", "#374151"),
                text_color=("#166534", "#86EFAC") if is_subjects else THEME_COLORS["text_secondary"],
                corner_radius=4,
                padx=6,
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
                    height=26,
                    corner_radius=4,
                    fg_color=THEME_COLORS["accent_primary"],
                    hover_color=THEME_COLORS["accent_primary_hover"],
                    command=lambda p=filepath: self._open_file(p),
                )
                btn_open_pdf.pack(side="left", padx=(0, 6))

            lesson_path = res.get("lesson_path")
            if lesson_path and os.path.exists(lesson_path):
                btn_open_dir = ctk.CTkButton(
                    btn_frame,
                    text="📂 Abrir Pasta",
                    font=get_font(10, "bold"),
                    height=26,
                    corner_radius=4,
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
            lbl_file.pack(fill="x", padx=12, pady=(2, 4))

            # Caixa com o Snippet do Assunto / Trecho
            snippet_box = ctk.CTkFrame(card, fg_color=THEME_COLORS["input_bg"], corner_radius=6)
            snippet_box.pack(fill="x", padx=12, pady=(0, 10))

            snippet_text = res.get("snippet", "").strip()
            lbl_snippet = ctk.CTkLabel(
                snippet_box,
                text=snippet_text,
                font=get_font(11),
                text_color=THEME_COLORS["text_secondary"],
                wraplength=680,
                justify="left",
                anchor="w",
            )
            lbl_snippet.pack(fill="x", padx=8, pady=6)

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
