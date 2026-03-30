"""
Redux Browser — Barra de URL com Autocomplete
QLineEdit customizado com sugestões de histórico e search engines.
"""

from PyQt6.QtWidgets import QLineEdit, QCompleter, QStyledItemDelegate
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Optional
from browser.ui.theme import Theme
from browser.config.search_engines import (
    ALL_ENGINES, PRIVATE_ENGINES, POPULAR_ENGINES,
    get_current_engine, set_current_engine, build_search_url,
    is_search_query
)


class UrlCompletionModel(QAbstractListModel):
    """Model para autocomplete de URLs com histórico e search engines."""
    
    def __init__(self, history_manager=None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self._items: List[dict] = []
        self._current_query = ""
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._items)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
            
        item = self._items[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return item.get('display', item.get('url', ''))
        elif role == Qt.ItemDataRole.ToolTipRole:
            return item.get('url', '')
        elif role == Qt.ItemDataRole.UserRole:
            return item.get('url', '')
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if item.get('type') == 'search':
                font.setItalic(True)
            return font
            
        return None
    
    def set_query(self, query: str):
        """Atualiza sugestões baseado na query digitada."""
        self._current_query = query.lower()
        self._items.clear()
        
        if not query or len(query) < 2:
            self.layoutChanged.emit()
            return
        
        current = get_current_engine()
        
        # Search suggestions - current engine
        if is_search_query(query):
            self._items.append({
                'display': f'{current.icon} Pesquisar "{query}" no {current.name}',
                'url': build_search_url(query),
                'type': 'search'
            })
            
            # Show 2 alternative engines
            shown = {current.name}
            for engine in ALL_ENGINES:
                if engine.name not in shown and len(shown) < 4:
                    shown.add(engine.name)
                    self._items.append({
                        'display': f'{engine.icon} Pesquisar "{query}" no {engine.name}',
                        'url': build_search_url(query, engine),
                        'type': 'search'
                    })
        
        # History matches
        if self.history_manager:
            for entry in self.history_manager.get_history()[:30]:
                if query.lower() in entry.url.lower() or query.lower() in entry.title.lower():
                    self._items.append({
                        'display': entry.title[:50] + ('...' if len(entry.title) > 50 else ''),
                        'url': entry.url,
                        'type': 'history'
                    })
                    if len(self._items) >= 10:
                        break
        
        self.layoutChanged.emit()
    
    def get_url_at(self, row: int) -> Optional[str]:
        if 0 <= row < len(self._items):
            return self._items[row].get('url')
        return None


class CompletionDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)


class UrlBar(QLineEdit):
    """Barra de URL com autocomplete e motores de busca."""
    
    navigate_requested = pyqtSignal(str)
    
    def __init__(self, history_manager=None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self._is_secure = False
        self._current_theme = "dark"
        self._is_loading = False
        
        self.setObjectName("urlBar")
        self.setPlaceholderText("Pesquisar ou digitar URL")
        self.setMinimumWidth(400)
        
        # Completion model
        self._completion_model = UrlCompletionModel(history_manager, self)
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.activated.connect(self._on_completion_selected)
        
        popup = self._completer.popup()
        popup.setStyleSheet(self._get_popup_style())
        popup.setItemDelegate(CompletionDelegate(popup))
        
        self.setCompleter(self._completer)
        
        self.returnPressed.connect(self._on_return_pressed)
        self.textChanged.connect(self._on_text_changed)
        
        self._apply_style()
        
    def _get_popup_style(self) -> str:
        p = Theme.DARK if self._current_theme == "dark" else Theme.LIGHT
        return f"""
            QListView {{
                background-color: {p['bg_secondary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QListView::item {{
                height: 28px;
                padding: 4px 12px;
                border-radius: 4px;
                color: {p['text_primary']};
            }}
            QListView::item:hover {{
                background-color: {p['bg_tertiary']};
            }}
            QListView::item:selected {{
                background-color: {p['accent_subtle']};
                color: {p['text_primary']};
            }}
        """
        
    def set_theme(self, theme: str):
        self._current_theme = theme
        self._apply_style()
        if self._completer.popup():
            self._completer.popup().setStyleSheet(self._get_popup_style())
            
    def set_secure(self, is_secure: bool):
        self._is_secure = is_secure
        self._apply_style()
        
    def set_loading(self, is_loading: bool):
        self._is_loading = is_loading
        self._apply_style()
        
    def _apply_style(self):
        p = Theme.DARK if self._current_theme == "dark" else Theme.LIGHT
        
        left_pad = "32px" if self._is_secure or self._is_loading else "12px"
        
        self.setStyleSheet(f"""
            QLineEdit#urlBar {{
                background-color: {p['bg_tertiary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 0 12px 0 {left_pad};
                height: 32px;
                font-size: 13px;
                color: {p['text_primary']};
                selection-background-color: {p['accent_subtle']};
            }}
            QLineEdit#urlBar:focus {{
                border: 1px solid {p['border_focus']};
            }}
            QLineEdit#urlBar::placeholder {{
                color: {p['text_tertiary']};
            }}
        """)
        
    def _on_text_changed(self, text: str):
        self._completion_model.set_query(text)
        
    def _on_completion_selected(self, index):
        url = self._completion_model.get_url_at(index.row())
        if url:
            self.setText(url)
            self.navigate_requested.emit(url)
            
    def _on_return_pressed(self):
        text = self.text().strip()
        if not text:
            return
            
        if "://" in text:
            self.navigate_requested.emit(text)
        elif '.' in text and ' ' not in text:
            self.navigate_requested.emit(f'https://{text}')
        else:
            url = build_search_url(text)
            self.navigate_requested.emit(url)
            
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
