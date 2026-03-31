"""
Redux Browser — Painel de Controle do Bloqueador de Anúncios

Painel estilo FingerprintPanel para configurar o ad blocker:
  - Níveis: Desativado / Padrão / Agressivo
  - Badge com contagem de bloqueios
  - Whitelist por domínio
  - Filtros customizados do usuário
  - Gerenciamento de listas de filtro
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QGroupBox, QButtonGroup, QWidget,
    QGraphicsDropShadowEffect, QTextEdit, QCheckBox,
    QInputDialog, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QIcon

from browser.security.adblock_engine import AdBlockLevel, DEFAULT_FILTER_LISTS
from browser.ui.icons import Icons
from browser.ui.theme import Theme
from browser.config.settings_manager import get_settings


class AdBlockPanel(QDialog):
    """
    Painel de controle do bloqueador de anúncios do Redux Browser.
    Design minimalista seguindo o padrão do FingerprintPanel.
    """

    def __init__(self, adblock_engine, current_domain: str = "", parent=None):
        super().__init__(parent)
        self.engine = adblock_engine
        self.current_domain = current_domain
        self._settings = get_settings()

        current_theme = getattr(parent, 'current_theme', 'dark') if parent else 'dark'
        self._theme = current_theme
        self._p = Theme.DARK if current_theme == "dark" else Theme.LIGHT

        self._setup_ui()

    def _setup_ui(self):
        p = self._p

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Container com sombra
        container = QWidget(self)
        container.setObjectName("adblockContainer")
        container.setStyleSheet(f"""
            QWidget#adblockContainer {{
                background-color: {p['bg_primary']};
                border: 1px solid {p['border']};
                border-radius: 16px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(0, 0, 0, int(255 * 0.7 if self._theme == 'dark' else 255 * 0.25)))
        shadow.setOffset(0, 16)
        container.setGraphicsEffect(shadow)
        main_layout.addWidget(container)

        # Scroll area dentro do container
        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # --- Header ---
        header = QHBoxLayout()

        title_label = QLabel("🛡️ Bloqueador de Anúncios")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {p['text_primary']};")
        header.addWidget(title_label)

        header.addStretch()

        # Badge de contagem
        blocked_count = self.engine.get_blocked_count()
        self.badge_label = QLabel(f"🚫 {blocked_count}")
        self.badge_label.setStyleSheet(f"""
            background: {p['accent']};
            color: white;
            border-radius: 10px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 700;
        """)
        self.badge_label.setToolTip(f"{blocked_count} requisições bloqueadas nesta sessão")
        header.addWidget(self.badge_label)

        # Botão fechar
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

        layout.addLayout(header)

        # --- Descrição ---
        desc = QLabel(
            "Bloqueia anúncios, rastreadores e pop-ups. "
            "Usa listas de filtro no formato EasyList/ABP."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {p['text_secondary']}; font-size: 13px;")
        layout.addWidget(desc)

        # --- Info de regras ---
        rules_label = QLabel(f"📋 {self.engine.total_rules:,} regras carregadas")
        rules_label.setStyleSheet(f"color: {p['text_tertiary']}; font-size: 12px;")
        layout.addWidget(rules_label)

        # --- Nível de proteção ---
        level_group = QGroupBox("Nível de Bloqueio")
        level_group.setStyleSheet(f"""
            QGroupBox {{
                color: {p['text_primary']}; font-weight: 600; font-size: 13px;
                border: 1px solid {p['border']}; border-radius: 12px;
                margin-top: 1ex; padding: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 10px; padding: 0 3px;
            }}
            QRadioButton {{
                color: {p['text_primary']}; font-weight: bold; font-size: 13px;
            }}
            QRadioButton::indicator {{
                width: 14px; height: 14px; border-radius: 7px;
                border: 1px solid {p['text_tertiary']};
                background-color: {p['bg_secondary']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {p['accent']};
                border: 1px solid {p['accent']};
            }}
        """)
        level_layout = QVBoxLayout(level_group)
        level_layout.setSpacing(10)

        self.btn_group = QButtonGroup(self)

        # OFF
        self.radio_off = QRadioButton("Desativado")
        self.radio_off.setStyleSheet("color: #FF6B6B;")
        off_desc = QLabel("Nenhum anúncio será bloqueado.")
        off_desc.setStyleSheet(f"color: {p['text_secondary']}; font-size: 12px;")
        self.btn_group.addButton(self.radio_off, 0)
        level_layout.addWidget(self.radio_off)
        level_layout.addWidget(off_desc)

        # STANDARD
        self.radio_standard = QRadioButton("Padrão (Recomendado)")
        self.radio_standard.setStyleSheet("color: #4CAF50;")
        std_desc = QLabel("Bloqueia anúncios e rastreadores sem quebrar sites.")
        std_desc.setStyleSheet(f"color: {p['text_secondary']}; font-size: 12px;")
        self.btn_group.addButton(self.radio_standard, 1)
        level_layout.addWidget(self.radio_standard)
        level_layout.addWidget(std_desc)

        # AGGRESSIVE
        self.radio_aggressive = QRadioButton("Agressivo")
        self.radio_aggressive.setStyleSheet("color: #FFC107;")
        agg_desc = QLabel("Bloqueia também cookies banners, pop-ups de newsletter e sponsored content.")
        agg_desc.setStyleSheet(f"color: {p['text_secondary']}; font-size: 12px;")
        agg_desc.setWordWrap(True)
        self.btn_group.addButton(self.radio_aggressive, 2)
        level_layout.addWidget(self.radio_aggressive)
        level_layout.addWidget(agg_desc)

        # Selecionar nível atual
        if self.engine.level == AdBlockLevel.OFF:
            self.radio_off.setChecked(True)
        elif self.engine.level == AdBlockLevel.STANDARD:
            self.radio_standard.setChecked(True)
        else:
            self.radio_aggressive.setChecked(True)

        self.btn_group.idClicked.connect(self._on_level_changed)
        layout.addWidget(level_group)

        # --- Whitelist do site atual ---
        if self.current_domain:
            site_group = QWidget()
            site_layout = QHBoxLayout(site_group)
            site_layout.setContentsMargins(0, 0, 0, 0)

            is_wl = self.engine.is_whitelisted(self.current_domain)
            self.wl_btn = QPushButton(
                f"{'✅ Site permitido' if is_wl else '🚫 Permitir neste site'}: {self.current_domain}"
            )
            self.wl_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {p['bg_secondary']};
                    color: {p['text_primary']};
                    border: 1px solid {p['border']};
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{ background: {p['bg_tertiary']}; }}
            """)
            self.wl_btn.clicked.connect(self._toggle_whitelist)
            site_layout.addWidget(self.wl_btn)

            layout.addWidget(site_group)

        # --- Listas de Filtro ---
        lists_group = QGroupBox("Listas de Filtro")
        lists_group.setStyleSheet(f"""
            QGroupBox {{
                color: {p['text_primary']}; font-weight: 600; font-size: 13px;
                border: 1px solid {p['border']}; border-radius: 12px;
                margin-top: 1ex; padding: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 10px; padding: 0 3px;
            }}
            QCheckBox {{
                color: {p['text_primary']}; font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px; border-radius: 3px;
                border: 1px solid {p['text_tertiary']};
                background-color: {p['bg_secondary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {p['accent']};
                border: 1px solid {p['accent']};
            }}
        """)
        lists_layout = QVBoxLayout(lists_group)
        lists_layout.setSpacing(8)

        self._list_checkboxes = {}
        lists_config = self._settings.get("adblock_lists", DEFAULT_FILTER_LISTS)

        for list_id, list_info in lists_config.items():
            cb = QCheckBox(list_info.get("name", list_id))
            cb.setChecked(list_info.get("enabled", True))
            cb.stateChanged.connect(lambda state, lid=list_id: self._on_list_toggled(lid, state))
            lists_layout.addWidget(cb)
            self._list_checkboxes[list_id] = cb

        # Botões de ação para listas
        list_btn_layout = QHBoxLayout()

        add_list_btn = QPushButton("+ Adicionar Lista")
        add_list_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['bg_secondary']}; color: {p['accent']};
                border: 1px solid {p['border']}; border-radius: 6px;
                padding: 6px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {p['bg_tertiary']}; }}
        """)
        add_list_btn.clicked.connect(self._add_custom_list)
        list_btn_layout.addWidget(add_list_btn)

        update_btn = QPushButton("🔄 Atualizar Listas")
        update_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['bg_secondary']}; color: {p['text_primary']};
                border: 1px solid {p['border']}; border-radius: 6px;
                padding: 6px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {p['bg_tertiary']}; }}
        """)
        update_btn.clicked.connect(self._update_lists)
        list_btn_layout.addWidget(update_btn)

        list_btn_layout.addStretch()
        lists_layout.addLayout(list_btn_layout)

        layout.addWidget(lists_group)

        # --- Filtros Customizados ---
        custom_group = QGroupBox("Filtros Customizados")
        custom_group.setStyleSheet(f"""
            QGroupBox {{
                color: {p['text_primary']}; font-weight: 600; font-size: 13px;
                border: 1px solid {p['border']}; border-radius: 12px;
                margin-top: 1ex; padding: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 10px; padding: 0 3px;
            }}
        """)
        custom_layout = QVBoxLayout(custom_group)

        custom_hint = QLabel("Uma regra por linha. Formato ABP (ex: ||ads.example.com^, ##.ad-banner)")
        custom_hint.setWordWrap(True)
        custom_hint.setStyleSheet(f"color: {p['text_tertiary']}; font-size: 11px;")
        custom_layout.addWidget(custom_hint)

        self.custom_filters_edit = QTextEdit()
        self.custom_filters_edit.setPlaceholderText("||ads.example.com^\n##.ad-banner\n##.sponsored")
        self.custom_filters_edit.setMaximumHeight(100)
        self.custom_filters_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {p['bg_secondary']};
                color: {p['text_primary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        # Carregar filtros salvos
        saved_custom = self._settings.get("adblock_custom_filters", "")
        self.custom_filters_edit.setPlainText(saved_custom)
        custom_layout.addWidget(self.custom_filters_edit)

        save_custom_btn = QPushButton("Salvar Filtros")
        save_custom_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p['accent']}; color: white;
                border: none; border-radius: 6px;
                padding: 8px 16px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {p['accent_hover']}; }}
        """)
        save_custom_btn.clicked.connect(self._save_custom_filters)
        custom_layout.addWidget(save_custom_btn)

        layout.addWidget(custom_group)

        # --- Status ---
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"font-size: 12px; color: {p['text_tertiary']};")
        self._update_status()
        layout.addWidget(self.status_label)

        scroll.setWidget(scroll_widget)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)

        self.resize(500, 640)
        self._drag_pos = None

    # --- Drag support ---
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

    # --- Callbacks ---

    def _on_level_changed(self, id: int):
        levels = {0: AdBlockLevel.OFF, 1: AdBlockLevel.STANDARD, 2: AdBlockLevel.AGGRESSIVE}
        self.engine.level = levels[id]
        self._settings.set("adblock_level", levels[id].value)
        self._update_status()

    def _toggle_whitelist(self):
        is_wl = self.engine.toggle_whitelist(self.current_domain)
        self._settings.set("adblock_whitelist", self.engine.get_whitelist())
        p = self._p
        self.wl_btn.setText(
            f"{'✅ Site permitido' if is_wl else '🚫 Permitir neste site'}: {self.current_domain}"
        )
        self._update_status()

    def _on_list_toggled(self, list_id: str, state: int):
        lists_config = self._settings.get("adblock_lists", dict(DEFAULT_FILTER_LISTS))
        if list_id in lists_config:
            lists_config[list_id]["enabled"] = (state == 2)  # Qt.CheckState.Checked = 2
        self._settings.set("adblock_lists", lists_config)

    def _add_custom_list(self):
        url, ok = QInputDialog.getText(
            self, "Adicionar Lista de Filtro",
            "URL da lista (formato ABP/EasyList):",
        )
        if ok and url.strip():
            url = url.strip()
            # Gerar ID a partir da URL
            import hashlib
            list_id = "custom_" + hashlib.md5(url.encode()).hexdigest()[:8]
            name = url.split("/")[-1].split("?")[0] or "Lista Customizada"

            lists_config = self._settings.get("adblock_lists", dict(DEFAULT_FILTER_LISTS))
            lists_config[list_id] = {
                "name": name,
                "url": url,
                "enabled": True,
            }
            self._settings.set("adblock_lists", lists_config)

            # Adicionar checkbox
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, lid=list_id: self._on_list_toggled(lid, state))
            self._list_checkboxes[list_id] = cb

            self.status_label.setText(f"✅ Lista '{name}' adicionada. Clique em Atualizar.")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")

    def _update_lists(self):
        self.status_label.setText("🔄 Atualizando listas...")
        self.status_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")

        # Recarregar em thread separada para não travar a UI
        from PyQt6.QtCore import QThread, pyqtSignal

        class UpdateWorker(QThread):
            done = pyqtSignal(int)

            def __init__(self, engine):
                super().__init__()
                self.engine = engine

            def run(self):
                self.engine.load_all_lists(force_download=True)
                self.done.emit(self.engine.total_rules)

        self._update_worker = UpdateWorker(self.engine)
        self._update_worker.done.connect(self._on_lists_updated)
        self._update_worker.start()

    def _on_lists_updated(self, total_rules: int):
        self.status_label.setText(f"✅ Listas atualizadas! {total_rules:,} regras carregadas.")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")

    def _save_custom_filters(self):
        text = self.custom_filters_edit.toPlainText()
        self._settings.set("adblock_custom_filters", text)

        # Recarregar filtros customizados no engine
        count = self.engine.load_filters_from_text(text)

        self.status_label.setText(f"✅ {count} filtros customizados salvos e carregados.")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")

    def _update_status(self):
        if self.engine.level == AdBlockLevel.OFF:
            self.status_label.setText("Status: Bloqueio desativado")
            self.status_label.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 12px;")
        elif self.engine.level == AdBlockLevel.STANDARD:
            self.status_label.setText("Status: Proteção padrão ativa")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
        elif self.engine.level == AdBlockLevel.AGGRESSIVE:
            self.status_label.setText("Status: Proteção agressiva ativa")
            self.status_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")
