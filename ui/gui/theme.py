"""
Design System e Tokens Visuais da Interface Gráfica Moderna do CorujaSync.
Centraliza paletas de cores, tipografia, cantos arredondados e estilos consistentes.
"""
from typing import Dict, Any, Tuple
import customtkinter as ctk

# Paleta de Cores Inspirada no Google Stitch (Obsidian & Electric Indigo)
THEME_COLORS = {
    # Fundo principal da aplicação (Obsidian Dark)
    "bg_main": ("#F1F5F9", "#0B0F17"),
    # Barra lateral de navegação (Panel)
    "bg_sidebar": ("#FFFFFF", "#0F172A"),
    # Fundo de cards e containers agrupados (Dark Surface)
    "card_bg": ("#FFFFFF", "#111827"),
    # Fundo secundário / inputs / terminal
    "input_bg": ("#F8FAFC", "#070B12"),
    "terminal_bg": ("#F8FAFC", "#070B12"),
    # Bordas sutis de 1px
    "border": ("#E2E8F0", "#1E293B"),
    "border_focus": ("#6366F1", "#818CF8"),
    # Ações e Destaques Primários (Electric Indigo)
    "accent_primary": ("#4F46E5", "#6366F1"),
    "accent_primary_hover": ("#4338CA", "#4F46E5"),
    # Sucesso / Telemetria Ativa (Emerald)
    "success": ("#059669", "#10B981"),
    "success_hover": ("#047857", "#059669"),
    # Perigo / Cancelar (Rose Red)
    "danger": ("#DC2626", "#F43F5E"),
    "danger_hover": ("#B91C1C", "#E11D48"),
    # Alerta / Atenção (Amber)
    "warning": ("#D97706", "#F59E0B"),
    "warning_hover": ("#B45309", "#D97706"),
    # Ciano / Buffers
    "cyan": ("#0891B2", "#06B6D4"),
    # Secundário / Slate
    "slate": ("#475569", "#1E293B"),
    "slate_hover": ("#334155", "#334155"),
    # Textos
    "text_primary": ("#0F172A", "#F8FAFC"),
    "text_secondary": ("#475569", "#94A3B8"),
    "text_muted": ("#94A3B8", "#64748B"),
    # Cores de tags do terminal
    "tag_info": ("#2563EB", "#38BDF8"),
    "tag_success": ("#059669", "#34D399"),
    "tag_warning": ("#D97706", "#FBBF24"),
    "tag_error": ("#DC2626", "#F87171"),
    # Badges e modais de diálogo
    "dialog_bg": ("#FFFFFF", "#0F172A"),
    "badge_info": ("#EEF2FF", "#1E1B4B"),
    "badge_success": ("#ECFDF5", "#064E3B"),
    "badge_warning": ("#FFFBEB", "#78350F"),
    "badge_error": ("#FFF1F2", "#881337"),
    "badge_confirm": ("#F5F3FF", "#2E1065"),
}

# Geometria e Estilização (Cantos Arredondados Raycast/Linear)
RADIUS_CARD = 14
RADIUS_INPUT = 10
RADIUS_BUTTON = 10
RADIUS_DIALOG = 16
BORDER_WIDTH_CARD = 1
BORDER_WIDTH_DIALOG = 1


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
