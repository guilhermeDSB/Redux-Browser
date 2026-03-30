"""
Redux Browser — Sistema de Temas
Gerencia tema claro/escuro e gera QSS dinâmico.
"""

class Theme:
    """Paleta de cores e constantes de estilização."""
    
    DARK = {
        "bg_primary": "#0A0A0A",
        "bg_secondary": "#141414",
        "bg_tertiary": "#1E1E1E",
        "bg_active": "#252525",
        "text_primary": "#E8E8E8",
        "text_secondary": "#888888",
        "text_tertiary": "#555555",
        "accent": "#FF3B3B",
        "accent_hover": "#FF5252",
        "accent_subtle": "rgba(255,59,59,0.08)",
        "border": "#1F1F1F",
        "border_hover": "#333333",
        "border_focus": "rgba(255,59,59,0.25)",
        "success": "#2EA043",
        "warning": "#D29922",
        "error": "#F85149",
        "radius_sm": "6px",
        "radius_md": "8px",
        "radius_lg": "12px",
        "radius_xl": "16px",
    }
    
    LIGHT = {
        "bg_primary": "#FFFFFF",
        "bg_secondary": "#F7F7F7",
        "bg_tertiary": "#EFEFEF",
        "bg_active": "#FFFFFF",
        "text_primary": "#1A1A1A",
        "text_secondary": "#666666",
        "text_tertiary": "#999999",
        "accent": "#E63030",
        "accent_hover": "#D42020",
        "accent_subtle": "rgba(230,48,48,0.06)",
        "border": "#E5E5E5",
        "border_hover": "#CCCCCC",
        "border_focus": "rgba(230,48,48,0.2)",
        "success": "#1F883D",
        "warning": "#BF8700",
        "error": "#CF222E",
        "radius_sm": "6px",
        "radius_md": "8px",
        "radius_lg": "12px",
        "radius_xl": "16px",
    }
    
    @staticmethod
    def generate_qss(palette: dict) -> str:
        """Gera a stylesheet QSS completa do Redux Browser."""
        p = palette
        return f"""
        /* ============= GLOBAL ============= */
        QMainWindow {{
            background-color: {p['bg_primary']};
        }}

        /* ============= TOOLBAR ============= */
        QToolBar {{
            background-color: {p['bg_primary']};
            border: none;
            padding: 4px 8px;
            spacing: 2px;
            max-height: 40px;
        }}

        QToolBar QToolButton {{
            background: transparent;
            border: none;
            border-radius: {p['radius_sm']};
            padding: 4px 6px;
            color: {p['text_secondary']};
            font-size: 14px;
        }}

        QToolBar QToolButton:hover {{
            background-color: {p['bg_tertiary']};
            color: {p['text_primary']};
        }}

        QToolBar QToolButton:pressed {{
            background-color: {p['bg_active']};
        }}

        QToolBar QToolButton:disabled {{
            opacity: 0.3;
            color: {p['text_tertiary']};
        }}

        /* ============= ADDRESS BAR ============= */
        QLineEdit#addressBar {{
            background-color: {p['bg_tertiary']};
            border: 1px solid {p['border']};
            border-radius: {p['radius_md']};
            padding: 0 12px;
            height: 28px;
            font-size: 13px;
            color: {p['text_primary']};
            selection-background-color: {p['accent_subtle']};
        }}

        QLineEdit#addressBar:focus {{
            border: 1px solid {p['border_focus']};
        }}

        QLineEdit#addressBar::placeholder {{
            color: {p['text_tertiary']};
        }}

        /* ============= TAB BAR ============= */
        QTabWidget::pane {{
            border: none;
            background: {p['bg_primary']};
        }}

        QTabBar {{
            background: {p['bg_primary']};
            border: none;
            max-height: 32px;
        }}

        QTabBar::tab {{
            background: transparent;
            color: {p['text_secondary']};
            padding: 6px 12px;
            margin: 0 1px;
            border: none;
            border-top-left-radius: {p['radius_md']};
            border-top-right-radius: {p['radius_md']};
            font-size: 12px;
            max-width: 200px;
            min-width: 60px;
        }}

        QTabBar::tab:selected {{
            background: {p['bg_active']};
            color: {p['text_primary']};
            border-bottom: 2px solid {p['accent']};
        }}

        QTabBar::tab:hover:!selected {{
            background: {p['bg_tertiary']};
        }}

        QTabBar::close-button {{
            image: none;
            subcontrol-position: right;
            padding: 2px;
            border-radius: 3px;
        }}

        QTabBar::close-button:hover {{
            background: {p['error']};
        }}

        QTabBar QToolButton {{
            background: transparent; border: none; border-radius: {p['radius_sm']};
            margin: 4px; padding: 4px;
        }}
        
        QTabBar QToolButton:hover {{
            background: {p['bg_tertiary']};
        }}

        /* ============= SCROLLBARS ============= */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {p['border_hover']};
            border-radius: 4px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {p['text_tertiary']};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
        }}

        QScrollBar::handle:horizontal {{
            background: {p['border_hover']};
            border-radius: 4px;
            min-width: 30px;
        }}

        /* ============= MENUS ============= */
        QMenu {{
            background-color: {p['bg_secondary']};
            border: 1px solid {p['border']};
            border-radius: {p['radius_lg']};
            padding: 6px;
        }}

        QMenu::item {{
            padding: 6px 12px;
            border-radius: {p['radius_sm']};
            font-size: 13px;
            color: {p['text_primary']};
        }}

        QMenu::item:selected {{
            background-color: {p['bg_tertiary']};
        }}

        QMenu::separator {{
            height: 1px;
            background: {p['border']};
            margin: 4px 8px;
        }}

        QMenu::item:disabled {{
            color: {p['text_tertiary']};
        }}

        /* ============= DIALOGS ============= */
        QDialog {{
            background-color: {p['bg_primary']};
            border: 1px solid {p['border']};
            border-radius: {p['radius_xl']};
        }}

        /* ============= DOCK (DevTools) ============= */
        QDockWidget {{
            background: {p['bg_primary']};
            border: none;
            titlebar-close-icon: none;
        }}

        QDockWidget::title {{
            background: {p['bg_secondary']};
            padding: 6px 12px;
            font-size: 12px;
            color: {p['text_secondary']};
            border-bottom: 1px solid {p['border']};
        }}

        /* ============= TREE VIEWS (DOM/Bookmarks) ============= */
        QTreeWidget, QTreeView {{
            background: {p['bg_primary']};
            border: none;
            font-family: 'Consolas', 'SF Mono', monospace;
            font-size: 12px;
            color: {p['text_primary']};
        }}

        QTreeWidget::item:hover {{
            background: {p['bg_tertiary']};
        }}

        QTreeWidget::item:selected {{
            background: {p['accent_subtle']};
            border-left: 2px solid {p['accent']};
        }}

        /* ============= BUTTONS ============= */
        QPushButton {{
            background: {p['bg_tertiary']};
            border: 1px solid {p['border']};
            border-radius: {p['radius_md']};
            padding: 6px 16px;
            font-size: 13px;
            color: {p['text_primary']};
        }}

        QPushButton:hover {{
            background: {p['bg_active']};
            border-color: {p['border_hover']};
        }}

        QPushButton#primaryButton {{
            background: {p['accent']};
            border: none;
            color: white;
            font-weight: 600;
        }}

        QPushButton#primaryButton:hover {{
            background: {p['accent_hover']};
        }}

        QPushButton#dangerButton {{
            background: transparent;
            border: none;
            color: {p['error']};
        }}

        QPushButton#dangerButton:hover {{
            text-decoration: underline;
        }}

        /* ============= TOOLTIPS ============= */
        QToolTip {{
            background: {p['bg_secondary']};
            border: 1px solid {p['border']};
            border-radius: {p['radius_sm']};
            padding: 4px 8px;
            font-size: 11px;
            color: {p['text_secondary']};
        }}

        /* ============= STATUS BAR ============= */
        QStatusBar {{
            background: transparent;
            border: none;
            font-size: 11px;
            color: {p['text_tertiary']};
        }}
        
        /* ============= PROGRESS BAR ============= */
        QProgressBar {{
            background: transparent;
            border: none;
            border-radius: 2px;
            height: 2px;
            max-height: 2px;
        }}
        
        QProgressBar::chunk {{
            background: {p['accent']};
            border-radius: 2px;
        }}
        """
