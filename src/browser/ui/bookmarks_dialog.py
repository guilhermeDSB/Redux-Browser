from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QPushButton, QHBoxLayout, QInputDialog, QMessageBox, QMenu,
    QWidget, QLabel, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap
from browser.bookmarks.bookmark_manager import BookmarkManager, BookmarkItem
from browser.ui.icons import Icons
from browser.ui.theme import Theme

class BookmarksDialog(QDialog):
    """
    Janela completa para gerenciar favoritos e pastas (Redesign Minimalista).
    """
    def __init__(self, manager: BookmarkManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
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
        title_label = QLabel("Favoritos")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p['text_primary']};")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        close_btn = QPushButton()
        pixmap = QPixmap()
        pixmap.loadFromData(Icons.CLOSE.replace('currentColor', p['text_secondary']).encode(), "SVG")
        close_btn.setIcon(QIcon(pixmap))
        close_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; padding: 4px; border-radius: 6px; }} QPushButton:hover {{ background: {p['bg_tertiary']}; }}")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        self.layout.addLayout(header_layout)
        
        # Árvore
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nome", "URL"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{ background: transparent; color: {p['text_primary']}; border: 1px solid {p['border']}; border-radius: 8px; outline: none; padding: 4px; }}
            QTreeWidget::item {{ height: 32px; border-radius: 6px; }}
            QTreeWidget::item:hover {{ background: {p['bg_tertiary']}; }}
            QTreeWidget::item:selected {{ background: {p['accent_subtle']}; color: {p['accent']}; }}
            QHeaderView::section {{ background: {p['bg_secondary']}; color: {p['text_secondary']}; border: none; padding: 4px; border-bottom: 1px solid {p['border']}; }}
        """)
        self.layout.addWidget(self.tree)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        self.btn_new_bkm = QPushButton("Novo Favorito")
        self.btn_new_bkm.setStyleSheet(f"QPushButton {{ background: {p['bg_secondary']}; color: {p['text_primary']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 16px; }} QPushButton:hover {{ background: {p['bg_tertiary']}; border-color: {p['border_hover']}; }}")
        self.btn_new_bkm.clicked.connect(self._add_bookmark)
        btn_layout.addWidget(self.btn_new_bkm)
        
        self.btn_new_folder = QPushButton("Nova Pasta")
        self.btn_new_folder.setStyleSheet(f"QPushButton {{ background: {p['bg_secondary']}; color: {p['text_primary']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 16px; }} QPushButton:hover {{ background: {p['bg_tertiary']}; border-color: {p['border_hover']}; }}")
        self.btn_new_folder.clicked.connect(self._add_folder)
        btn_layout.addWidget(self.btn_new_folder)
        
        btn_layout.addStretch()
        
        self.btn_remove = QPushButton("Remover")
        self.btn_remove.setStyleSheet(f"QPushButton {{ background: transparent; color: {p['error']}; border: none; }} QPushButton:hover {{ text-decoration: underline; }}")
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.btn_remove)
        
        self.layout.addLayout(btn_layout)
        
        if parent:
            screen_h = parent.screen().size().height()
            self.resize(560, int(screen_h * 0.7))
        else:
            self.resize(560, 600)
            
        self.populate()
        
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

    def populate(self):
        self.tree.clear()
        root_node = self.manager.get_bookmarks_tree()
        self._build_tree(root_node, self.tree.invisibleRootItem())
        self.tree.expandAll()

    def _build_tree(self, bkm_node: BookmarkItem, tree_item_parent):
        for child in bkm_node.children:
            item = QTreeWidgetItem(tree_item_parent)
            icon = "📁" if child.is_folder() else "🔗"
            item.setText(0, f"{icon} {child.title}")
            item.setText(1, child.url or "")
            item.setData(0, Qt.ItemDataRole.UserRole, child.id)
            self._build_tree(child, item)

    def _get_selected_id(self) -> str:
        selected = self.tree.selectedItems()
        if not selected: return "root"
        return selected[0].data(0, Qt.ItemDataRole.UserRole)

    def _add_bookmark(self):
        parent_id = self._get_selected_id()
        title, ok1 = QInputDialog.getText(self, "Novo Favorito", "Nome do Favorito:")
        if ok1 and title:
            url, ok2 = QInputDialog.getText(self, "Novo Favorito", "URL:")
            if ok2 and url:
                if "://" not in url: url = "https://" + url
                self.manager.add_bookmark(title, url, parent_id)
                self.populate()

    def _add_folder(self):
        parent_id = self._get_selected_id()
        title, ok = QInputDialog.getText(self, "Nova Pasta", "Nome da Pasta:")
        if ok and title:
            self.manager.add_folder(title, parent_id)
            self.populate()

    def _remove_selected(self):
        selected = self.tree.selectedItems()
        if not selected: return
        item_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        self.manager.remove_item(item_id)
        self.populate()
