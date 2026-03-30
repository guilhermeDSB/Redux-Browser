from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QToolButton, QMenu, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from browser.bookmarks.bookmark_manager import BookmarkManager, BookmarkItem
from browser.ui.theme import Theme

class BookmarksBar(QWidget):
    """
    Barra horizontal para exibir atalhos rápidos de favoritos.
    Fica visível debaixo do QToolBar de URL.
    """
    bookmarkClicked = pyqtSignal(str) # Emite URL clicada
    manageRequested = pyqtSignal()   # Emite pedido p/ abrir o Bookmark Dialog

    def __init__(self, manager: BookmarkManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._current_theme = 'dark'
        
        self._apply_theme()
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        self.layout.setSpacing(5)
        
        self.setFixedHeight(30)
        self.populate()
    
    def set_theme(self, theme: str):
        """Atualiza o tema da barra de favoritos."""
        self._current_theme = theme
        self._apply_theme()
        self.populate()
    
    def _apply_theme(self):
        p = Theme.DARK if self._current_theme == 'dark' else Theme.LIGHT
        self.setStyleSheet(
            f"BookmarksBar {{ background: {p['bg_secondary']}; border-bottom: 1px solid {p['border']}; }}"
            f" QToolButton {{ color: {p['text_secondary']}; border: none; padding: 4px 8px; border-radius: 3px; }}"
            f" QToolButton:hover {{ background: {p['bg_tertiary']}; }}"
        )

    def populate(self):
        """Lê os favs root e cria os botões iterativamente"""
        # Limpa layout antigo
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        # "Apps" ou atalho pro Dialog
        manage_btn = QToolButton()
        manage_btn.setText("⭐ Gerenciar")
        manage_btn.setStyleSheet("font-weight: bold; color: #e94560;")
        manage_btn.clicked.connect(self.manageRequested.emit)
        self.layout.addWidget(manage_btn)
        
        # Cria os atalhos baseados nos filhos do Root
        self._build_buttons_recursive(self.manager.get_bookmarks_tree(), self.layout)
        
        self.layout.addStretch() # Empurra tudo para esquerda

    def _build_buttons_recursive(self, node: BookmarkItem, target_layout, limit=15):
        # Apenas lemos o nivel base root para a barra horizontal, ou se for pasta cria um dropdown nativo
        if node.id == "root":
            for child in node.children[:limit]:
                btn = QToolButton()
                icon = "📁" if child.is_folder() else "🔗"
                btn.setText(f"{icon} {child.title}")
                
                if child.is_folder():
                    menu = QMenu(self)
                    self._populate_menu(menu, child)
                    btn.setMenu(menu)
                    btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                else:
                    # Captura closure pra mandar a URL certa
                    url = child.url
                    btn.clicked.connect(lambda checked, u=url: self.bookmarkClicked.emit(u))
                    
                target_layout.addWidget(btn)

    def _populate_menu(self, menu: QMenu, node: BookmarkItem):
        for child in node.children:
            if child.is_folder():
                # Menu Misto
                submenu = menu.addMenu(f"📁 {child.title}")
                self._populate_menu(submenu, child)
            else:
                action = QAction(f"🔗 {child.title}", self)
                url = child.url
                action.triggered.connect(lambda checked, u=url: self.bookmarkClicked.emit(u))
                menu.addAction(action)
