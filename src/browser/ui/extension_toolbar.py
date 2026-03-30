"""
Redux Browser — Ícones de extensões na toolbar
Mostra ícones das extensões habilitadas que estão fixadas (pinned) na toolbar.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QToolButton
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize
from .extension_popup import ExtensionPopup

class ExtensionToolbar(QWidget):
    def __init__(self, extension_manager, parent=None):
        super().__init__(parent)
        self.ext_manager = extension_manager
        self.main_window = parent
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        # Conectar sinais
        self.ext_manager.extension_installed.connect(self.update_icons)
        self.ext_manager.extension_removed.connect(self.update_icons)
        self.ext_manager.extension_enabled.connect(self.update_icons)
        self.ext_manager.extension_disabled.connect(self.update_icons)
        self.ext_manager.extension_pinned.connect(self.update_icons)
        
        self.update_icons()
        
    def update_icons(self, _ext_id=None):
        """Atualiza os ícones baseado nas extensões fixadas na toolbar."""
        # Limpar layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        # Adicionar novos ícones — apenas extensões pinned
        pinned_exts = self.ext_manager.get_pinned_extensions()
        for ext in pinned_exts:
            btn = QToolButton(self)
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            icon_path = ext.get_icon_path(size=16)
            if icon_path and icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))
                btn.setIconSize(QSize(16, 16))
            else:
                btn.setText(ext.name[:1].upper())
                
            if ext.action and ext.action.default_title:
                btn.setToolTip(ext.action.default_title)
            else:
                btn.setToolTip(ext.name)
                
            current_theme = getattr(self.main_window, 'current_theme', 'dark')
            theme_color = "#E8E8E8" if current_theme == "dark" else "#1A1A1A"
            btn_bg_hover = "#1E1E1E" if current_theme == "dark" else "#E5E5E5"
            
            btn.setStyleSheet(f"""
                QToolButton {{
                    background: transparent; border: none; border-radius: 6px; 
                    color: {theme_color}; font-weight: bold;
                }}
                QToolButton:hover {{ background: {btn_bg_hover}; }}
            """)
            
            btn.clicked.connect(lambda checked, e_id=ext.id: self._on_extension_icon_clicked(e_id))
            self.layout.addWidget(btn)
            
    def _on_extension_icon_clicked(self, extension_id: str):
        """Abre o popup da extensão."""
        ext = self.ext_manager.get_extension(extension_id)
        if not ext or not ext.action or not ext.action.default_popup:
            return
            
        popup = ExtensionPopup(ext, self.ext_manager, self.main_window)
        
        # Posicionar exatamente abaixo do botão na toolbar
        sender = self.sender()
        if sender:
            global_pos = sender.mapToGlobal(sender.rect().bottomLeft())
            global_pos.setY(global_pos.y() + 4)
            global_pos.setX(global_pos.x() - (popup.width() // 2) + (sender.width() // 2))
            popup.move(global_pos)
            
        popup.show()
