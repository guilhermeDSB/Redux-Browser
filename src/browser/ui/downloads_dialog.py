"""
Redux Browser — Dialog do Gerenciador de Downloads
Interface visual para gerenciar downloads ativos e concluídos.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QScrollArea, QProgressBar, QGraphicsDropShadowEffect, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QIcon, QPixmap
from browser.ui.downloads_manager import DownloadManager, DownloadItem, DownloadState
from browser.ui.icons import Icons
from browser.ui.theme import Theme


class DownloadItemWidget(QWidget):
    """Widget visual para um único download na lista."""
    
    def __init__(self, download: DownloadItem, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.download = download
        self._theme = theme
        self._setup_ui()
        
    def _setup_ui(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Ícone de arquivo
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background: {p['bg_tertiary']};
                border-radius: 6px;
                font-size: 14px;
            }}
        """)
        
        # Determinar ícone por tipo
        mime = self.download.mime_type.lower()
        if 'image' in mime:
            icon_label.setText("IMG")
        elif 'pdf' in mime:
            icon_label.setText("PDF")
        elif 'video' in mime:
            icon_label.setText("VID")
        elif 'audio' in mime:
            icon_label.setText("AUD")
        elif 'zip' in mime or 'compress' in mime or 'rar' in mime:
            icon_label.setText("ZIP")
        else:
            icon_label.setText("FILE")
        layout.addWidget(icon_label)
        
        # Info do arquivo
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Nome do arquivo
        name_label = QLabel(self.download.filename[:40] + ('...' if len(self.download.filename) > 40 else ''))
        name_label.setStyleSheet(f"color: {p['text_primary']}; font-size: 13px; font-weight: 500;")
        info_layout.addWidget(name_label)
        
        # URL da fonte (truncada)
        url_text = self.download.url[:50] + ('...' if len(self.download.url) > 50 else '')
        url_label = QLabel(url_text)
        url_label.setStyleSheet(f"color: {p['text_tertiary']}; font-size: 11px;")
        info_layout.addWidget(url_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.download.progress * 100))
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {p['bg_tertiary']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {p['accent']};
                border-radius: 2px;
            }}
        """)
        info_layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel(self.download.status_text)
        self.status_label.setStyleSheet(f"color: {p['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, 1)
        
        # Botão de ação
        self.action_btn = QPushButton()
        self.action_btn.setFixedSize(32, 32)
        self._update_action_button(p)
        layout.addWidget(self.action_btn)
        
        self.setStyleSheet(f"QWidget {{ background: {p['bg_secondary']}; border-radius: 8px; }}")
        
    def _update_action_button(self, palette):
        if self.download.state == DownloadState.DOWNLOADING:
            self.action_btn.setText("⏸")
            self.action_btn.setToolTip("Pausar")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {palette['bg_tertiary']};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background: {palette['bg_active']}; }}
            """)
        elif self.download.state == DownloadState.PAUSED:
            self.action_btn.setText("▶")
            self.action_btn.setToolTip("Retomar")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {palette['accent_subtle']};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background: {palette['bg_active']}; }}
            """)
        elif self.download.is_finished:
            self.action_btn.setText("📂")
            self.action_btn.setToolTip("Abrir")
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {palette['accent_subtle']};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background: {palette['bg_tertiary']}; }}
            """)
        
    def update_progress(self):
        self.progress_bar.setValue(int(self.download.progress * 100))
        self.status_label.setText(self.download.status_text)


class DownloadsDialog(QDialog):
    """
    Janela completa de gerenciamento de downloads.
    """
    
    def __init__(self, manager: DownloadManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._theme = getattr(parent, 'current_theme', 'dark') if parent else 'dark'
        self._item_widgets = {}
        self._setup_ui()
        self._connect_signals()
        self._refresh()
        
    def _setup_ui(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        
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
        shadow.setColor(QColor(0, 0, 0, int(255 * 0.25 if self._theme == 'light' else 255 * 0.7)))
        shadow.setOffset(0, 16)
        self.container.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.container)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Downloads")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p['text_primary']};")
        header.addWidget(title)
        header.addStretch()
        
        self.count_label = QLabel()
        self.count_label.setStyleSheet(f"font-size: 12px; color: {p['text_secondary']};")
        header.addWidget(self.count_label)
        
        close_btn = QPushButton()
        pixmap = QPixmap()
        pixmap.loadFromData(Icons.CLOSE.replace('currentColor', p['text_secondary']).encode(), "SVG")
        close_btn.setIcon(QIcon(pixmap))
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; padding: 4px; border-radius: 6px; }}
            QPushButton:hover {{ background: {p['bg_tertiary']}; }}
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        self.layout.addLayout(header)
        
        # Scroll Area para downloads
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['border_hover']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)
        
        # Empty state label
        self.empty_label = QLabel("Nenhum download.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {p['text_tertiary']}; font-size: 14px; padding: 40px;")
        self.layout.addWidget(self.empty_label)
        
        # Footer buttons
        footer = QHBoxLayout()
        
        clear_btn = QPushButton("Limpar Concluídos")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {p['error']}; font-size: 13px;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        clear_btn.clicked.connect(self._clear_completed)
        footer.addWidget(clear_btn)
        
        footer.addStretch()
        self.layout.addLayout(footer)
        
        # Tamanho
        parent_h = parent.screen().size().height() if parent else 700
        self.resize(600, int(parent_h * 0.7))
        
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
        
    def _connect_signals(self):
        self.manager.download_added.connect(lambda _: self._refresh())
        self.manager.download_updated.connect(self._on_download_updated)
        self.manager.download_finished.connect(lambda _: self._refresh())
        self.manager.download_removed.connect(lambda _: self._refresh())

        # Auto-refresh timer for live progress
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._tick_progress)
        self._refresh_timer.start()

    def _tick_progress(self):
        """Atualiza progresso de downloads ativos sem recriar widgets."""
        has_active = False
        for did, widget in self._item_widgets.items():
            dl = self.manager.get_download(did)
            if dl and not dl.is_finished:
                widget.download = dl
                widget.update_progress()
                has_active = True
        if not has_active and self._refresh_timer.isActive():
            self._refresh_timer.stop()
        
    def _refresh(self):
        # Limpar widgets existentes
        for wid in self._item_widgets.values():
            wid.deleteLater()
        self._item_widgets.clear()
        
        downloads = self.manager.get_all()
        
        if not downloads:
            self.empty_label.show()
            self.scroll_area.hide()
            self.count_label.setText("0 items")
            return
        
        self.empty_label.hide()
        self.scroll_area.show()
        self.count_label.setText(f"{len(downloads)} items")
        
        for dl in downloads:
            item_widget = DownloadItemWidget(dl, self._theme)
            
            # Connect action button based on state
            if dl.is_finished:
                item_widget.action_btn.clicked.connect(lambda _, did=dl.id: self._open_file(did))
            elif dl.state == DownloadState.DOWNLOADING:
                item_widget.action_btn.clicked.connect(lambda _, did=dl.id: self._pause_download(did))
            elif dl.state == DownloadState.PAUSED:
                item_widget.action_btn.clicked.connect(lambda _, did=dl.id: self._resume_download(did))
            else:
                item_widget.action_btn.clicked.connect(lambda _, did=dl.id: self._cancel_download(did))
            
            self._item_widgets[dl.id] = item_widget
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, item_widget)
    
    def _on_download_updated(self, download_id: str):
        widget = self._item_widgets.get(download_id)
        dl = self.manager.get_download(download_id)
        if widget and dl:
            widget.update_progress()
            if dl.is_finished:
                self._refresh()
    
    def _open_file(self, download_id: str):
        self.manager.open_folder(download_id)
    
    def _pause_download(self, download_id: str):
        self.manager.pause_download(download_id)
        self._refresh()

    def _resume_download(self, download_id: str):
        self.manager.resume_download(download_id)
        self._refresh()

    def _cancel_download(self, download_id: str):
        self.manager.cancel_download(download_id)
    
    def _clear_completed(self):
        self.manager.clear_completed()
        self._refresh()
