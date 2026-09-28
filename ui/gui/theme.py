"""
Design System e Tokens Visuais da Interface Gráfica Moderna do Concurso Downloader.
Centraliza paletas de cores, tipografia, cantos arredondados e estilos consistentes.
"""
from typing import Dict, Any, Tuple
import customtkinter as ctk

# Paleta de Cores
THEME_COLORS = {
    # Fundo principal da aplicação
    "bg_main": ("#F3F4F6", "#0F1117"),
    # Barra lateral de navegação
    "bg_sidebar": ("#FFFFFF", "#161822"),
    # Fundo de cards e containers agrupados
    "card_bg": ("#FFFFFF", "#1E202B"),
    # Fundo secundário / inputs
    "input_bg": ("#F9FAFB", "#14161F"),
    # Bordas sutis de 1px
    "border": ("#E5E7EB", "#2B2E3D"),
    "border_focus": ("#3B82F6", "#60A5FA"),
    # Ações e Destaques Primários (Electric Blue)
    "accent_primary": ("#2563EB", "#3B82F6"),
    "accent_primary_hover": ("#1D4ED8", "#2563EB"),
    # Sucesso / Iniciar (Emerald)
    "success": ("#059669", "#10B981"),
    "success_hover": ("#047857", "#059669"),
    # Perigo / Cancelar (Rose Red)
    "danger": ("#DC2626", "#EF4444"),
    "danger_hover": ("#B91C1C", "#DC2626"),
    # Secundário / Slate
    "slate": ("#475569", "#334155"),
    "slate_hover": ("#334155", "#1E293B"),
    # Textos
    "text_primary": ("#111827", "#F9FAFB"),
    "text_secondary": ("#4B5563", "#9CA3AF"),
    "text_muted": ("#9CA3AF", "#6B7280"),
    # Cores de tags do terminal
    "tag_info": ("#1D4ED8", "#60A5FA"),
    "tag_success": ("#047857", "#34D399"),
    "tag_warning": ("#B45309", "#FBBF24"),
    "tag_error": ("#B91C1C", "#F87171"),
}

# Geometria e Estilização
RADIUS_CARD = 10
RADIUS_INPUT = 8
RADIUS_BUTTON = 8
BORDER_WIDTH_CARD = 1


def create_card_frame(parent, **kwargs) -> ctk.CTkFrame:
    """Cria um container estilizado no formato de card moderno com borda sutil."""
    default_kwargs = {
        "fg_color": THEME_COLORS["card_bg"],
        "border_color": THEME_COLORS["border"],
        "border_width": BORDER_WIDTH_CARD,
        "corner_radius": RADIUS_CARD,
    }
    default_kwargs.update(kwargs)
    return ctk.CTkFrame(parent, **default_kwargs)


def get_font(size: int = 12, weight: str = "normal", family: str = "default") -> ctk.CTkFont:
    """Retorna uma fonte tipográfica padronizada."""
    if family == "mono":
        mono_family = "Consolas" if ctk.get_appearance_mode() else "monospace"
        return ctk.CTkFont(family=mono_family, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)
