import os
import subprocess
import sys
from typing import Dict, Any, List
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
            text="🔍 Busca Global Textual em PDFs",
            font=get_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"],
            anchor="w",
        )
        lbl_title.pack(fill="x", padx=15, pady=(12, 4))

        lbl_desc = ctk.CTkLabel(
            search_card,
            text="Pesquise por artigos de leis, jurisprudência ou conceitos em todos os livros eletrônicos já baixados no disco.",
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
            placeholder_text="Digite o termo ou frase (ex: Legalidade e Moralidade, Art. 5, Licitação)...",
            font=get_font(13),
            height=40,
        )
        self.entry_query.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_query.bind("<Return>", lambda e: self._perform_search())

        btn_search = ctk.CTkButton(
            row_search,
            text="🔍 Pesquisar",
            fg_color=THEME_COLORS["accent_primary"],
            hover_color=THEME_COLORS["accent_primary_hover"],
            font=get_font(13, "bold"),
            height=40,
            width=120,
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
            width=100,
            command=self._reindex_library,
        )
        btn_reindex.pack(side="left")

        # Barra de Status do Índice
        docs_count = len(self.indexer.index_data.get("documents", {}))
        self.lbl_stats = ctk.CTkLabel(
            search_card,
            text=f"📚 Biblioteca indexada: {docs_count} arquivos PDF prontos para busca instantânea.",
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
        if not self.indexer.index_data.get("documents"):
            self.indexer.index_directory(download_dir)

        results = self.indexer.search(query, max_results=40)
        self._display_results(results, query)

    def _reindex_library(self):
        download_dir = self.config.get("download_dir", get_default_download_dir())
        new_count = self.indexer.index_directory(download_dir, force_reindex=True)
        docs_count = len(self.indexer.index_data.get("documents", {}))
        self.lbl_stats.configure(
            text=f"✓ Reindexação concluída! {docs_count} PDFs disponíveis no catálogo ({new_count} novos processados)."
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

            # Cabeçalho do Card
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=12, pady=(10, 4))

            # Badges
            badge_course = ctk.CTkLabel(
                head,
                text=res.get("course", "Curso"),
                font=get_font(10, "bold"),
                fg_color=("#DBEAFE", "#1E3A8A"),
                text_color=("#1D4ED8", "#93C5FD"),
                corner_radius=4,
                padx=6,
                pady=2,
            )
            badge_course.pack(side="left", padx=(0, 6))

            badge_page = ctk.CTkLabel(
                head,
                text=f"Página {res.get('page')}",
                font=get_font(10, "bold"),
                fg_color=("#E5E7EB", "#374151"),
                text_color=THEME_COLORS["text_secondary"],
                corner_radius=4,
                padx=6,
                pady=2,
            )
            badge_page.pack(side="left")

            btn_open = ctk.CTkButton(
                head,
                text="Abrir PDF ↗",
                font=get_font(10, "bold"),
                width=80,
                height=24,
                corner_radius=4,
                fg_color=THEME_COLORS["slate"],
                hover_color=THEME_COLORS["slate_hover"],
                command=lambda path=res.get("filepath"): self._open_file(path),
            )
            btn_open.pack(side="right")

            # Nome da Aula e Arquivo
            lbl_file = ctk.CTkLabel(
                card,
                text=f"{res.get('lesson')}  •  {res.get('filename')}",
                font=get_font(12, "bold"),
                text_color=THEME_COLORS["text_primary"],
                anchor="w",
            )
            lbl_file.pack(fill="x", padx=12, pady=(2, 4))

            # Trecho com contexto
            snippet_box = ctk.CTkFrame(card, fg_color=THEME_COLORS["input_bg"], corner_radius=6)
            snippet_box.pack(fill="x", padx=12, pady=(0, 10))

            lbl_snippet = ctk.CTkLabel(
                snippet_box,
                text=res.get("snippet", ""),
                font=get_font(11),
                text_color=THEME_COLORS["text_secondary"],
                wraplength=640,
                justify="left",
                anchor="w",
            )
            lbl_snippet.pack(fill="x", padx=8, pady=6)

    def _open_file(self, filepath: Optional[str]):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", filepath])
            else:
                subprocess.Popen(["xdg-open", filepath])
        except Exception:
            pass
