"""
Redux Browser — CWS Install Widget
Widget flutuante que aparece quando o usuário visita uma extensão da Chrome Web Store.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QColor, QPixmap, QIcon
from browser.ui.theme import Theme
from browser.extensions.chrome_web_store import (
    get_extension_info_from_url, download_crx
)
from pathlib import Path


class CRXDownloadThread(QThread):
    """Thread para baixar .crx sem travar a UI."""
    
    download_success = pyqtSignal(str)  # path to crx
    download_failed = pyqtSignal(str)   # error message
    
    def __init__(self, ext_id: str, dest_dir: str, parent=None):
        super().__init__(parent)
        self.ext_id = ext_id
        self.dest_dir = dest_dir
        
    def run(self):
        try:
            crx_path = download_crx(self.ext_id, self.dest_dir)
            self.download_success.emit(str(crx_path))
        except Exception as e:
            self.download_failed.emit(str(e))


class CWSInstallWidget(QWidget):
    """
    Widget que mostra "Adicionar ao Redux" quando o usuário está
    numa página de extensão da Chrome Web Store.
    """
    
    install_requested = pyqtSignal(str, str, str)  # ext_id, name, crx_path
    
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._ext_info = None
        self._download_thread = None
        self._is_installing = False
        self._setup_ui()
        self.hide()
        
    def _setup_ui(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            QWidget {{
                background: {p['bg_secondary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        # Extension icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                background: {p['accent']};
                border-radius: 4px;
                font-size: 10px;
                color: white;
                font-weight: bold;
            }}
        """)
        self.icon_label.setText("EXT")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # Extension name
        self.name_label = QLabel()
        self.name_label.setStyleSheet(f"color: {p['text_primary']}; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.name_label)
        
        # Install button
        self.install_btn = QPushButton("Adicionar ao Redux")
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {p['accent_hover']};
            }}
            QPushButton:disabled {{
                background: {p['bg_tertiary']};
                color: {p['text_tertiary']};
            }}
        """)
        self.install_btn.clicked.connect(self._on_install_clicked)
        layout.addWidget(self.install_btn)
        
        # Status label (hidden initially)
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {p['text_secondary']}; font-size: 11px;")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
    def set_theme(self, theme: str):
        self._theme = theme
        p = Theme.DARK if theme == "dark" else Theme.LIGHT
        self.setStyleSheet(f"""
            QWidget {{
                background: {p['bg_secondary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
            }}
        """)
    
    def update_for_url(self, url: str, extension_manager=None):
        """Atualiza o widget baseado na URL atual."""
        from browser.extensions.chrome_web_store import is_chrome_web_store_url
        
        if not is_chrome_web_store_url(url):
            self.hide()
            return
        
        self._ext_info = get_extension_info_from_url(url)
        if not self._ext_info:
            self.hide()
            return
        
        # Check if already installed
        if extension_manager:
            existing = extension_manager.get_extension(self._ext_info['id'])
            if existing:
                self.name_label.setText(self._ext_info['name'])
                self.install_btn.hide()
                self.status_label.setText("✓ Instalado")
                self.status_label.setStyleSheet(f"color: #2EA043; font-size: 11px; font-weight: 600;")
                self.status_label.show()
                self.show()
                return
        
        self.name_label.setText(self._ext_info['name'])
        self.install_btn.show()
        self.install_btn.setEnabled(True)
        self.install_btn.setText("Adicionar ao Redux")
        self.status_label.hide()
        self.show()
    
    def _on_install_clicked(self):
        if not self._ext_info or self._is_installing:
            return
        
        self._is_installing = True
        self.install_btn.setEnabled(False)
        self.install_btn.setText("Baixando...")
        self.install_btn.hide()
        self.status_label.setText("⏳ Baixando extensão...")
        self.status_label.setStyleSheet(f"color: #D29922; font-size: 11px;")
        self.status_label.show()
        
        dest_dir = os.path.expanduser("~/.redux_browser/crx_temp")
        self._download_thread = CRXDownloadThread(self._ext_info['id'], dest_dir)
        self._download_thread.download_success.connect(self._on_download_success)
        self._download_thread.download_failed.connect(self._on_download_failed)
        self._download_thread.start()
    
    @pyqtSlot(str)
    def _on_download_success(self, crx_path: str):
        self._is_installing = False
        self.install_requested.emit(self._ext_info['id'], self._ext_info['name'], crx_path)
        self.status_label.setText("✓ Extensão instalada!")
        self.status_label.setStyleSheet(f"color: #2EA043; font-size: 11px; font-weight: 600;")
        self.install_btn.hide()
    
    @pyqtSlot(str)
    def _on_download_failed(self, error: str):
        self._is_installing = False
        self.install_btn.show()
        self.install_btn.setEnabled(True)
        self.install_btn.setText("Tentar novamente")
        self.status_label.setText(f"✕ Falha: {error[:40]}")
        self.status_label.setStyleSheet(f"color: #F85149; font-size: 11px;")
        self.status_label.show()
