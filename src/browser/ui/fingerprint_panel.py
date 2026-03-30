from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QRadioButton, QGroupBox, QButtonGroup, QMessageBox, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QPixmap, QIcon

from browser.security.brave_farbling import FarblingLevel
from browser.ui.icons import Icons
from browser.ui.theme import Theme
from browser.config.settings_manager import get_settings

class FingerprintPanel(QDialog):
    """
    Painel de controle de Fingerprint do Redux Browser (Redesign Minimalista).
    """
    def __init__(self, farbling_engine, parent=None):
        super().__init__(parent)
        self.engine = farbling_engine
        
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
        title_label = QLabel("Proteção Fingerprint")
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

        desc = QLabel(
            "Adiciona ruído sutil aos dados de fingerprinting, evitando assinaturas "
            "únicas através do método de farbling."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {p['text_secondary']}; margin-bottom: 12px; font-size: 13px;")
        self.layout.addWidget(desc)

        # Radio buttons
        level_group = QGroupBox("Nível de Proteção")
        level_group.setStyleSheet(f"""
            QGroupBox {{ color: {p['text_primary']}; font-weight: 600; font-size: 13px; border: 1px solid {p['border']}; border-radius: 12px; margin-top: 1ex; padding: 16px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}
            QRadioButton {{ color: {p['text_primary']}; font-weight: bold; font-size: 13px; }}
            QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 1px solid {p['text_tertiary']}; background-color: {p['bg_secondary']}; }}
            QRadioButton::indicator:checked {{ background-color: {p['accent']}; border: 1px solid {p['accent']}; }}
        """)
        level_layout = QVBoxLayout(level_group)
        level_layout.setSpacing(12)

        self.btn_group = QButtonGroup(self)

        # OFF
        self.radio_off = QRadioButton("Desativado")
        self.radio_off.setStyleSheet("color: #FF6B6B;")
        off_desc = QLabel("Sem proteção. Dados reais são expostos.")
        off_desc.setStyleSheet(f"color: {p['text_secondary']}; left: 24px; font-size: 12px;")
        self.btn_group.addButton(self.radio_off, 0)
        level_layout.addWidget(self.radio_off)
        level_layout.addWidget(off_desc)

        # BALANCED
        self.radio_balanced = QRadioButton("Balanceado (Padrão)")
        self.radio_balanced.setStyleSheet("color: #4CAF50;")
        bal_desc = QLabel("Ruído em Canvas, Áudio e Fontes. Não gera quebras de layout.")
        bal_desc.setStyleSheet(f"color: {p['text_secondary']}; left: 24px; font-size: 12px;")
        self.btn_group.addButton(self.radio_balanced, 1)
        level_layout.addWidget(self.radio_balanced)
        level_layout.addWidget(bal_desc)

        # MAXIMUM
        self.radio_max = QRadioButton("Máximo")
        self.radio_max.setStyleSheet("color: #FFC107;")
        max_desc = QLabel("Bloqueia WebRTC (IP) + Normaliza APIs agressivamente.")
        max_desc.setStyleSheet(f"color: {p['text_secondary']}; left: 24px; font-size: 12px;")
        self.btn_group.addButton(self.radio_max, 2)
        level_layout.addWidget(self.radio_max)
        level_layout.addWidget(max_desc)

        if self.engine.level == FarblingLevel.OFF: self.radio_off.setChecked(True)
        elif self.engine.level == FarblingLevel.BALANCED: self.radio_balanced.setChecked(True)
        elif self.engine.level == FarblingLevel.MAXIMUM: self.radio_max.setChecked(True)

        self.btn_group.idClicked.connect(self._on_level_changed)
        self.layout.addWidget(level_group)

        # Botões
        btn_layout = QHBoxLayout()
        self.btn_new_session = QPushButton("Nova Sessão")
        self.btn_new_session.setStyleSheet(f"QPushButton {{ background: {p['bg_secondary']}; color: {p['text_primary']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 8px 16px; }} QPushButton:hover {{ background: {p['bg_tertiary']}; }}")
        self.btn_new_session.clicked.connect(self._on_new_session)
        btn_layout.addWidget(self.btn_new_session)
        btn_layout.addStretch()

        self.layout.addLayout(btn_layout)

        # Status
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; margin-top: 8px;")
        self._update_status()
        self.layout.addWidget(self.status_label)

        self.resize(480, 560)
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

    def _on_level_changed(self, id: int):
        levels = {0: FarblingLevel.OFF, 1: FarblingLevel.BALANCED, 2: FarblingLevel.MAXIMUM}
        self.engine.level = levels[id]
        get_settings().set("farbling_level", levels[id].value)
        self._update_status()

    def _on_new_session(self):
        self.engine.reset_session()
        QMessageBox.information(
            self, "Sessão Renovada",
            "Nova sessão gerada. Recarregue as páginas para aplicar."
        )

    def _update_status(self):
        if self.engine.level == FarblingLevel.OFF:
            self.status_label.setText("Status: Dados expostos (Perigoso)")
            self.status_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        elif self.engine.level == FarblingLevel.BALANCED:
            self.status_label.setText("Status: Proteção ativa e funcional")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif self.engine.level == FarblingLevel.MAXIMUM:
            self.status_label.setText("Status: Proteção radical")
            self.status_label.setStyleSheet("color: #FFC107; font-weight: bold;")
