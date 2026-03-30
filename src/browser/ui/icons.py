"""
Redux Browser — Ícones SVG inline
Todos os ícones como strings SVG para evitar dependências externas.
Monocromáticos, 18px, stroke-width 1.5.
"""

class Icons:
    """Biblioteca de ícones SVG do Redux Browser."""

    @staticmethod
    def _svg(path_d: str, size: int = 18) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg"
            width="{size}" height="{size}" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="1.5"
            stroke-linecap="round" stroke-linejoin="round">
            {path_d}</svg>'''

    BACK = _svg('<polyline points="15 18 9 12 15 6"/>')
    FORWARD = _svg('<polyline points="9 18 15 12 9 6"/>')
    RELOAD = _svg('''<polyline points="23 4 23 10 17 10"/>
        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>''')
    HOME = _svg('''<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5
        a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>''')
    STAR = _svg('''<polygon points="12 2 15.09 8.26 22 9.27
        17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14
        2 9.27 8.91 8.26 12 2"/>''')
    STAR_FILLED = _svg('''<polygon points="12 2 15.09 8.26
        22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02
        7 14.14 2 9.27 8.91 8.26 12 2"
        fill="currentColor"/>''')
    SHIELD = _svg('''<path d="M12 22s8-4 8-10V5l-8-3-8 3v7
        c0 6 8 10 8 10z"/>''')
    MENU = _svg('''<line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="18" x2="21" y2="18"/>''')
    PLUS = _svg('''<line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>''')
    CLOSE = _svg('''<line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>''')
    SEARCH = _svg('''<circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>''')
    LOCK = _svg('''<rect x="3" y="11" width="18" height="11"
        rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>''')
    LOCK_OPEN = _svg('''<rect x="3" y="11" width="18" height="11"
        rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>''')
    HISTORY = _svg('''<circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>''')
    DOWNLOAD = _svg('''<path d="M21 15v4a2 2 0 0 1-2 2H5
        a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>''')
    SETTINGS = _svg('''<circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06
        a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06
        a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21
        a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4
        a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0
        2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15
        a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09
        A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06
        a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06
        a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3
        a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51
        1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0
        2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9
        a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2
        2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>''')
    SUN = _svg('''<circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/>
        <line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/>
        <line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>''')
    MOON = _svg('''<path d="M21 12.79A9 9 0 1 1 11.21 3
        7 7 0 0 0 21 12.79z"/>''')
    PRIVATE = _svg('''<path d="M1 12s4-8 11-8 11 8 11 8-4
        8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>''')
    FIND = _svg('''<circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>''')
    ZOOM_IN = _svg('''<circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>''')
    ZOOM_OUT = _svg('''<circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="8" y1="11" x2="14" y2="11"/>''')
    HTTPS = _svg('''<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4" fill="none"/>
        <circle cx="12" cy="16" r="1" fill="currentColor"/>''')
    REFRESH = _svg('''<path d="M23 4v6h-6"/>
        <path d="M1 20v-6h6"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" fill="none"/>''')
