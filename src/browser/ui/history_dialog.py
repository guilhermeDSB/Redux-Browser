from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QHBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect,
    QMenu, QApplication
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap
from browser.history.history_manager import HistoryManager
from browser.ui.icons import Icons
from browser.ui.theme import Theme

class HistoryDialog(QDialog):
    """
    Interface para visualização e busca do Histórico Global (Redesign Minimalista).
    """
    urlRequested = None  # Será setado pelo parent para navegação
    
    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self._parent_window = parent
        
        current_theme = getattr(parent, 'current_theme', 'dark') if parent else 'dark'
        p = Theme.DARK if current_theme == "dark" else Theme.LIGHT
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.container = QWidget(self)
        self.container.setObjectName("dialogContainer")
        self.container.setStyleSheet(f"""
            QWidget#dialogContainer {{
                background-color: {p['bg_primary']};
                border: 1px solid {p['border']};
                border-radius: 16px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(0, 0, 0, int(255*0.25 if current_theme == 'light' else 255*0.7)))
        shadow.setOffset(0, 16)
        self.container.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.container)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)
        
        # Header (Título + Fechar)
        header_layout = QHBoxLayout()
        title_label = QLabel("Histórico")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p['text_primary']};")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        close_btn = QPushButton()
        pixmap = QPixmap()
        pixmap.loadFromData(Icons.CLOSE.replace('currentColor', p['text_secondary']).encode(), "SVG")
        close_btn.setIcon(QIcon(pixmap))
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; padding: 4px; border-radius: 6px; }}
            QPushButton:hover {{ background: {p['bg_tertiary']}; }}
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        self.layout.addLayout(header_layout)
        
        # Pesquisa
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Pesquisar no histórico...")
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {p['bg_secondary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 0 12px;
                height: 32px;
                font-size: 13px;
                color: {p['text_primary']};
            }}
            QLineEdit:focus {{ border: 1px solid {p['border_focus']}; }}
        """)
        self.search_bar.textChanged.connect(self._filter_history)
        self.layout.addWidget(self.search_bar)
        
        # Lista
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ 
                height: 40px; border-radius: 8px; color: {p['text_primary']}; padding-left: 8px;
            }}
            QListWidget::item:hover {{ background: {p['bg_tertiary']}; }}
            QListWidget::item:selected {{ background: {p['accent_subtle']}; color: {p['accent']}; }}
        """)
        self.list_widget.itemDoubleClicked.connect(self._navigate_to_item)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.layout.addWidget(self.list_widget)
        
        # Botão limpar
        self.clear_btn = QPushButton("Limpar Histórico")
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; font-size: 13px;
                color: {p['error']}; text-align: left; padding: 8px 0;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_all)
        self.layout.addWidget(self.clear_btn)
        
        # Tamanho dinâmico (500x70%_da_tela)
        if parent:
            screen_h = parent.screen().size().height()
            self.resize(540, int(screen_h * 0.7))
        else:
            self.resize(540, 600)
            
        self.populate()
        
        # Para arrastar a janela customizada
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        
    def populate(self, filter_text: str = ""):
        self.list_widget.clear()
        filter_text = filter_text.lower()
        
        # Agrupamento por data
        current_date_label = None
        
        for entry in self.history_manager.get_history():
            if filter_text in entry.title.lower() or filter_text in entry.url.lower():
                try: 
                    from datetime import datetime
                    dt = datetime.fromisoformat(entry.timestamp)
                    date_str = dt.strftime("%d/%m/%Y")
                    time_str = dt.strftime("%H:%M")
                except: 
                    date_str = ""
                    time_str = entry.timestamp

                # Adicionar separador de data
                if date_str != current_date_label:
                    current_date_label = date_str
                    separator = QListWidgetItem(f"📅 {date_str}")
                    separator.setFlags(Qt.ItemFlag.NoItemFlags)  # Não selecionável
                    self.list_widget.addItem(separator)

                item = QListWidgetItem(f"  🕒 {entry.title} — {entry.url}   {time_str}")
                item.setData(100, entry.url)
                item.setData(101, entry.timestamp)
                self.list_widget.addItem(item)
    
    def _navigate_to_item(self, item: QListWidgetItem):
        """Navega para a URL ao dar duplo-clique."""
        url = item.data(100)
        if url and self._parent_window:
            self.close()
            if hasattr(self._parent_window, '_load_network_url'):
                self._parent_window._load_network_url(url)
    
    def _show_context_menu(self, pos):
        """Menu de contexto com opção de deletar e abrir."""
        item = self.list_widget.itemAt(pos)
        if not item or not item.data(100):
            return
        
        menu = QMenu(self)
        open_action = menu.addAction("🔗 Abrir")
        delete_action = menu.addAction("🗑️ Remover do histórico")
        copy_action = menu.addAction("📋 Copiar URL")
        
        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == open_action:
            self._navigate_to_item(item)
        elif action == delete_action:
            url = item.data(100)
            timestamp = item.data(101)
            if url:
                self.history_manager.delete_entry(url, timestamp)
                self.populate(self.search_bar.text())
        elif action == copy_action:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(item.data(100) or "")
                
    def _filter_history(self, text: str):
        self.populate(text)
        
    def _clear_all(self):
        self.history_manager.clear_history()
        self.populate()
