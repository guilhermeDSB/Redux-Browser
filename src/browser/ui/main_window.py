from PyQt6.QtCore import QUrl, Qt, QTimer, QPoint, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QLineEdit, QStatusBar, 
    QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QMessageBox, QMenu, QToolButton, QLabel,
    QProgressBar, QFileDialog
)
from PyQt6.QtGui import QAction, QIcon, QPixmap, QFont
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineProfile
import base64
import os
from pathlib import Path
from typing import Optional

from browser.extensions.extension_manager import ExtensionManager
from browser.extensions.content_script_loader import ContentScriptLoader
from browser.ui.extension_toolbar import ExtensionToolbar
from browser.ui.extension_page import ExtensionPageGenerator

from browser.history.history_manager import HistoryManager
from browser.bookmarks.bookmark_manager import BookmarkManager
from browser.ui.bookmarks_bar import BookmarksBar
from browser.ui.history_dialog import HistoryDialog
from browser.ui.bookmarks_dialog import BookmarksDialog
from browser.cache.cache_manager import CacheManager
from browser.ui.tab_widget import TabWidget
from browser.ui.dom_viewer import DOMViewer
from browser.ui.url_bar import UrlBar
from browser.ui.downloads_manager import DownloadManager
from browser.ui.downloads_dialog import DownloadsDialog
from browser.config.search_engines import get_current_engine, build_search_url, ALL_ENGINES, set_current_engine

from browser.security.brave_farbling import FarblingEngine, FarblingLevel
from browser.security.farbling_injector import FarblingInjector
from browser.security.adblock_engine import AdBlockEngine, AdBlockLevel
from browser.security.adblock_interceptor import AdBlockInterceptor
from browser.security.adblock_injector import AdBlockInjector
from browser.ui.fingerprint_panel import FingerprintPanel
from browser.ui.adblock_panel import AdBlockPanel
from browser.ui.theme import Theme
from browser.ui.icons import Icons
from browser.config.settings_manager import get_settings
from browser.updater.update_manager import UpdateManager
from browser.__version__ import APP_VERSION, APP_NAME


class MainWindow(QMainWindow):
    """
    Janela Principal do Redux Browser - Redesign Minimalista
    """
    def __init__(self, is_private=False, history_mgr=None, bookmark_mgr=None, cache_mgr=None):
        super().__init__()
        self.is_private = is_private
        
        self.history_manager = history_mgr or HistoryManager()
        self.bookmark_manager = bookmark_mgr or BookmarkManager()
        self.cache_manager = cache_mgr or CacheManager()
        
        # Downloads Manager
        self.download_manager = DownloadManager(self)
        
        # Security: Farbling (Brave-style)
        self.farbling_engine = FarblingEngine()
        if self.is_private:
            self.farbling_engine.level = FarblingLevel.MAXIMUM
        self.farbling_injector = FarblingInjector(self.farbling_engine)
        
        # Security: Ad Blocker
        self.adblock_engine = AdBlockEngine()
        self.adblock_injector = AdBlockInjector(self.adblock_engine)
        
        private_str = " (Privado)" if self.is_private else ""
        self.setWindowTitle(f"Redux Browser{private_str}")
        self.setMinimumSize(1024, 768)
        
        # Carregar preferências salvas
        self._settings = get_settings()
        self.current_theme = self._settings.get("theme", "dark")
        
        # Restaurar nível de farbling salvo
        saved_farbling = self._settings.get("farbling_level", "balanced")
        try:
            self.farbling_engine.level = FarblingLevel(saved_farbling)
        except ValueError:
            pass
        
        # Restaurar config do adblock salva
        saved_adblock = self._settings.get("adblock_level", "standard")
        try:
            self.adblock_engine.level = AdBlockLevel(saved_adblock)
        except ValueError:
            pass
        saved_whitelist = self._settings.get("adblock_whitelist", [])
        self.adblock_engine.set_whitelist(saved_whitelist)
        
        self.apply_theme()
        
        self.extension_manager = ExtensionManager(self)
        self.content_script_loader = ContentScriptLoader(self.extension_manager)
        self.ext_page_gen = ExtensionPageGenerator(self.extension_manager)
        
        self._init_pages()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.active_engine = 0
        self.setup_ui()
        
        # Conectar download requests
        self._setup_downloads()
        
        # Instalar interceptor de ad block no profile
        self._setup_adblock()
        
        # Auto-update: verificar atualizações após o startup
        self._update_manager = UpdateManager(parent=self)
        self._update_manager.schedule_startup_check(delay_ms=8000)
        
    def _create_icon(self, svg_str: str, color_override: str = None) -> QIcon:
        """Helper para criar QIcon a partir de string SVG, injetando a cor correta."""
        
        # Pega a cor correspondente ao tema
        if color_override:
            color = color_override
        else:
            palette = Theme.DARK if self.current_theme == "dark" else Theme.LIGHT
            color = palette["text_secondary"]
            
        # Altera 'currentColor' na string SVG pelo HEX correto
        svg_colored = svg_str.replace('currentColor', color)
        
        pixmap = QPixmap()
        pixmap.loadFromData(svg_colored.encode('utf-8'), "SVG")
        return QIcon(pixmap)

    def apply_theme(self):
        """Aplica o TEMA escuro/claro."""
        palette = Theme.DARK if self.current_theme == "dark" else Theme.LIGHT
        self.setStyleSheet(Theme.generate_qss(palette))
        if self.is_private:
            # Sutil override para modo privado na toolbar
            bg = "#0D0D1A" if self.current_theme == "dark" else "#F0F0F5"
            border = "#2A2A4A" if self.current_theme == "dark" else "#E0E0E5"
            self.setStyleSheet(self.styleSheet() + f"QToolBar {{ background-color: {bg}; border-bottom: 1px solid {border}; }}")
            
        if hasattr(self, 'floating_status'):
            self._apply_floating_status_style()
            
        if hasattr(self, 'url_bar'):
            self.url_bar.set_theme(self.current_theme)
            
        if hasattr(self, 'bookmarks_bar'):
            self.bookmarks_bar.set_theme(self.current_theme)
            
        if hasattr(self, 'dom_viewer'):
            self.dom_viewer.apply_theme(self.current_theme)
            
        if hasattr(self, 'home_html'):
            self._init_pages()

    def _init_pages(self):
        """Página inicial do Redux Browser"""
        engine = get_current_engine()
        bg_class = ' class="light-theme"' if self.current_theme == 'light' else ''
        priv_label = '(Privacidade)' if engine.is_private else ''
        
        self.home_html = (
            '<!DOCTYPE html><html><head><title>Redux Browser</title>'
            '<style>'
            '*{box-sizing:border-box;margin:0;padding:0}'
            'body{background:#111;color:#EEE;font-family:system-ui,sans-serif;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}'
            '.logo{width:80px;height:80px;background:rgba(255,59,59,.15);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:700;color:#FF3B3B;margin-bottom:16px}'
            'h1{font-size:28px;font-weight:600;margin-bottom:32px}'
            '.search{position:relative;width:500px;max-width:80%;margin-bottom:48px}'
            '.search input{width:100%;background:#161616;border:1px solid #252525;border-radius:24px;padding:14px 20px 14px 48px;font-size:16px;color:#EEE;outline:none}'
            '.search input:focus{border-color:#FF3B3B}'
            '.search svg{position:absolute;left:16px;top:50%;transform:translateY(-50%);width:20px;height:20px;color:#888}'
            '.info{font-size:12px;color:#555;margin-bottom:48px}'
            '.dial{display:flex;gap:16px}'
            '.card{width:72px;height:72px;background:#161616;border:1px solid #252525;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-decoration:none;color:#EEE}'
            '.card:hover{border-color:#3A3A3A}'
            '.card b{font-size:18px;margin-bottom:4px}'
            '.card span{font-size:10px;color:#888}'
            'body.light-theme{background:#FFF;color:#111}'
            'body.light-theme input,body.light-theme .card{background:#FFF;border-color:#DDD;color:#111}'
            '</style></head><body' + bg_class + '>'
            '<div class="logo">R</div>'
            '<h1>Redux Browser</h1>'
            '<form class="search" action="' + engine.url_template.replace('{query}', '') + '" method="get">'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
            '<input type="text" name="q" placeholder="Pesquisar com ' + engine.name + '" autofocus/>'
            '</form>'
            '<div class="info">' + engine.icon + ' ' + engine.name + ' ' + priv_label + '</div>'
            '<div class="dial">'
            '<a href="https://google.com" class="card"><b style="color:#4285F4">G</b><span>Google</span></a>'
            '<a href="https://youtube.com" class="card"><b style="color:#F00">Y</b><span>YouTube</span></a>'
            '<a href="https://github.com" class="card"><b>GH</b><span>GitHub</span></a>'
            '<a href="https://reddit.com" class="card"><b style="color:#FF4500">R</b><span>Reddit</span></a>'
            '</div></body></html>'
        )
        self.error_html = self._generate_error_page()

    def _generate_error_page(self, error_type="connection"):
        """Gera página de erro customizada."""
        colors = {
            'bg': '#0A0A0A' if self.current_theme == 'dark' else '#FFFFFF',
            'text': '#E8E8E8' if self.current_theme == 'dark' else '#1A1A1A',
            'accent': '#FF3B3B',
            'secondary': '#888888' if self.current_theme == 'dark' else '#666666'
        }
        
        error_messages = {
            'connection': ('Falha na Conexão', 'Não foi possível conectar ao servidor.', 'Verifique sua conexão com a internet e tente novamente.'),
            'dns': ('DNS Não Encontrado', 'O domínio não foi encontrado.', 'Verifique se o endereço está correto.'),
            'ssl': ('Erro de Certificado', 'A conexão não é segura.', 'O certificado de segurança do site não é confiável.'),
            'timeout': ('Tempo Esgotado', 'A conexão demorou muito.', 'O servidor demorou muito para responder.')
        }
        
        title, subtitle, hint = error_messages.get(error_type, error_messages['connection'])
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Erro - Redux Browser</title>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    background: {colors['bg']}; color: {colors['text']};
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    height: 100vh; display: flex; flex-direction: column;
                    align-items: center; justify-content: center; text-align: center;
                    padding: 40px;
                }}
                .error-icon {{
                    width: 80px; height: 80px; background: rgba(255, 59, 59, 0.15);
                    border-radius: 50%; display: flex; align-items: center;
                    justify-content: center; margin-bottom: 24px;
                }}
                .error-icon svg {{ width: 40px; height: 40px; stroke: {colors['accent']}; }}
                h1 {{ font-size: 24px; font-weight: 600; margin-bottom: 8px; }}
                .subtitle {{ font-size: 14px; color: {colors['secondary']}; margin-bottom: 32px; }}
                .hint {{ font-size: 13px; color: {colors['secondary']}; margin-bottom: 24px; }}
                .actions {{ display: flex; gap: 12px; }}
                button {{
                    padding: 10px 20px; border-radius: 8px; font-size: 14px;
                    cursor: pointer; transition: 150ms;
                }}
                .btn-primary {{
                    background: {colors['accent']}; color: white;
                    border: none;
                }}
                .btn-primary:hover {{ opacity: 0.9; }}
                .btn-secondary {{
                    background: transparent; color: {colors['text']};
                    border: 1px solid {colors['secondary']}; opacity: 0.5;
                }}
                .btn-secondary:hover {{ opacity: 0.8; }}
            </style>
        </head>
        <body>
            <div class="error-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
            </div>
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <p class="hint">{hint}</p>
            <div class="actions">
                <button class="btn-primary" onclick="location.reload()">Tentar Novamente</button>
                <button class="btn-secondary" onclick="history.back()">Voltar</button>
            </div>
        </body>
        </html>
        """

    def setup_ui(self):
        # -- TOOLBAR --
        self.toolbar = QToolBar("Navegação")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Botões de navegação com tooltips
        self.back_btn = QAction(self._create_icon(Icons.BACK), "", self)
        self.back_btn.setToolTip("Voltar (Alt+Left)")
        self.back_btn.setShortcut("Alt+Left")
        self.back_btn.triggered.connect(self.navigate_back)
        self.toolbar.addAction(self.back_btn)
        
        self.forward_btn = QAction(self._create_icon(Icons.FORWARD), "", self)
        self.forward_btn.setToolTip("Avançar (Alt+Right)")
        self.forward_btn.setShortcut("Alt+Right")
        self.forward_btn.triggered.connect(self.navigate_forward)
        self.toolbar.addAction(self.forward_btn)
        
        self.reload_btn = QAction(self._create_icon(Icons.RELOAD), "", self)
        self.reload_btn.setToolTip("Recarregar (F5)")
        self.reload_btn.setShortcut("F5")
        self.reload_btn.triggered.connect(self.reload_page)
        self.toolbar.addAction(self.reload_btn)

        self.home_btn = QAction(self._create_icon(Icons.HOME), "", self)
        self.home_btn.setToolTip("Página Inicial (Alt+Home)")
        self.home_btn.setShortcut("Alt+Home")
        self.home_btn.triggered.connect(self.navigate_home)
        self.toolbar.addAction(self.home_btn)

        # Container flexível para a Action Bar
        spacer_left = QWidget()
        spacer_left.setFixedWidth(8)
        self.toolbar.addWidget(spacer_left)
        
        # Security Indicator (HTTPS icon)
        self.security_indicator = QLabel()
        self.security_indicator.setFixedWidth(24)
        self.security_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_security_indicator(False)
        self.toolbar.addWidget(self.security_indicator)
        
        # Address Bar com Autocomplete
        self.url_bar = UrlBar(self.history_manager, self)
        self.url_bar.navigate_requested.connect(self._load_network_url)
        self.url_bar.setMinimumWidth(400)
        self.toolbar.addWidget(self.url_bar)
        
        # Progress Bar (inline, abaixo da URL)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.hide()
        self.toolbar.addWidget(self.progress_bar)
        
        # Ações à direita da URL
        spacer_right = QWidget()
        spacer_right.setFixedWidth(8)
        self.toolbar.addWidget(spacer_right)
        
        self.fav_btn = QAction(self._create_icon(Icons.STAR), "", self)
        self.fav_btn.setToolTip("Adicionar aos Favoritos (Ctrl+D)")
        self.fav_btn.setShortcut("Ctrl+D")
        self.fav_btn.triggered.connect(self.toggle_bookmark)
        self.toolbar.addAction(self.fav_btn)
        
        self.shield_btn = QAction(self._create_icon(Icons.SHIELD), "", self)
        self.shield_btn.setToolTip("Proteção Fingerprint (Ctrl+Shift+F)")
        self.shield_btn.triggered.connect(self.show_fingerprint_panel)
        self.toolbar.addAction(self.shield_btn)
        
        self.adblock_btn = QAction(self._create_icon(Icons.ADBLOCK), "", self)
        self.adblock_btn.setToolTip("Bloqueador de Anúncios (Ctrl+Shift+A)")
        self.adblock_btn.triggered.connect(self.show_adblock_panel)
        self.toolbar.addAction(self.adblock_btn)
        
        # Badge de contagem de bloqueios
        self._adblock_badge = QLabel("0", self)
        self._adblock_badge.setStyleSheet("""
            QLabel {
                background: #FF3B3B;
                color: white;
                border-radius: 7px;
                padding: 1px 4px;
                font-size: 9px;
                font-weight: 700;
                min-width: 14px;
                max-height: 14px;
            }
        """)
        self._adblock_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._adblock_badge.hide()
        
        self.extension_toolbar = ExtensionToolbar(self.extension_manager, self)
        self.toolbar.addWidget(self.extension_toolbar)
        
        # O botão do Menu
        self.menu_btn = QToolButton()
        self.menu_btn.setIcon(self._create_icon(Icons.MENU))
        self.menu_btn.setToolTip("Menu")
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_btn.setMenu(self._create_dropdown_menu())
        self.toolbar.addWidget(self.menu_btn)
        
        # Global Shortcuts
        self.focus_url_btn = QAction("Focar URL", self)
        self.focus_url_btn.setShortcut("Ctrl+L")
        self.focus_url_btn.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(self.focus_url_btn)
        
        self.close_tab_btn = QAction("Fechar Aba", self)
        self.close_tab_btn.setShortcut("Ctrl+W")
        self.close_tab_btn.triggered.connect(self.close_current_tab)
        self.addAction(self.close_tab_btn)
        
        # Find in Page shortcut
        self.find_action = QAction("Buscar na Página", self)
        self.find_action.setShortcut("Ctrl+F")
        self.find_action.triggered.connect(self.show_find_bar)
        self.addAction(self.find_action)
        
        # Zoom shortcuts
        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.zoom_in_action.triggered.connect(lambda: self._zoom_page(1.1))
        self.addAction(self.zoom_in_action)
        
        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(lambda: self._zoom_page(0.9))
        self.addAction(self.zoom_out_action)
        
        self.zoom_reset_action = QAction("Reset Zoom", self)
        self.zoom_reset_action.setShortcut("Ctrl+0")
        self.zoom_reset_action.triggered.connect(lambda: self._zoom_page(1.0, reset=True))
        self.addAction(self.zoom_reset_action)
        
        # -- BARRA DE FAVORITOS --
        self.bookmarks_bar = BookmarksBar(self.bookmark_manager)
        self.bookmarks_bar.bookmarkClicked.connect(self._load_network_url)
        self.bookmarks_bar.manageRequested.connect(self.show_bookmarks)
        self.bookmarks_bar.hide()
        self.layout.addWidget(self.bookmarks_bar)
        
        # -- FIND BAR (hidden by default) --
        self._setup_find_bar()
        
        # -- TABS --
        self.tab_widget = TabWidget(self.history_manager, self.farbling_injector, self.adblock_injector)
        self.tab_widget.currentTabUrlChanged.connect(self.update_url_bar)
        self.tab_widget.currentTabTitleChanged.connect(self.update_title)
        self.tab_widget.hoveredUrlChanged.connect(self.show_floating_status)
        self.tab_widget.tabLoadStarted.connect(self._on_load_started)
        self.tab_widget.tabLoadFinished.connect(self._on_load_finished)
        self.layout.addWidget(self.tab_widget)
        
        # -- CHROME WEB STORE INSTALL WIDGET --
        from browser.ui.cws_install_widget import CWSInstallWidget
        self.cws_widget = CWSInstallWidget(self.current_theme, self)
        self.cws_widget.install_requested.connect(self._on_cws_install)
        self.cws_widget.hide()
        self.layout.addWidget(self.cws_widget)
        
        # -- DEVTOOLS PANE --
        self.dom_viewer = DOMViewer(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dom_viewer)
        self.dom_viewer.hide()
        
        # F12 atalho
        self.devtools_btn = QAction("DevTools", self)
        self.devtools_btn.setShortcut("F12")
        self.devtools_btn.triggered.connect(self.toggle_devtools)
        self.addAction(self.devtools_btn)
        
        # Floating Status Bar
        self.floating_status = QLabel(self.centralWidget())
        self._apply_floating_status_style()
        self.floating_status.hide()
        
        self.status_timer = QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.floating_status.hide)
        
        self.new_tab()
        
        # Onboarding — exibir wizard na primeira execução
        if not self._settings.get("onboarding_completed", False):
            QTimer.singleShot(300, self._show_onboarding)
        
    def _show_onboarding(self):
        """Exibe o wizard de primeiro uso."""
        from browser.ui.onboarding import OnboardingWizard
        wizard = OnboardingWizard(parent=self)
        wizard.finished_setup.connect(self._apply_onboarding_choices)
        wizard.exec()

    def _apply_onboarding_choices(self, choices: dict):
        """Aplica as escolhas feitas no onboarding ao browser."""
        # Tema
        new_theme = choices.get("theme", self.current_theme)
        if new_theme != self.current_theme:
            self.current_theme = new_theme
            self.apply_theme()
            # Atualizar ícones da toolbar como toggle_theme faz
            if new_theme == "light":
                self.theme_action.setText("Tema Escuro")
                self.theme_action.setIcon(self._create_icon(Icons.MOON))
            else:
                self.theme_action.setText("Tema Claro")
                self.theme_action.setIcon(self._create_icon(Icons.SUN))
            # Recriar ícones principais da toolbar
            self.back_btn.setIcon(self._create_icon(Icons.BACK))
            self.forward_btn.setIcon(self._create_icon(Icons.FORWARD))
            self.reload_btn.setIcon(self._create_icon(Icons.RELOAD))
            self.home_btn.setIcon(self._create_icon(Icons.HOME))
            self.fav_btn.setIcon(self._create_icon(Icons.STAR))
            self.shield_btn.setIcon(self._create_icon(Icons.SHIELD))
            self.adblock_btn.setIcon(self._create_icon(Icons.ADBLOCK))
            self.menu_btn.setIcon(self._create_icon(Icons.MENU))

        # Farbling
        farbling = choices.get("farbling_level", "balanced")
        try:
            self.farbling_engine.level = FarblingLevel(farbling)
        except ValueError:
            pass

        # AdBlock
        adblock = choices.get("adblock_level", "standard")
        try:
            self.adblock_engine.level = AdBlockLevel(adblock)
        except ValueError:
            pass
    def _setup_find_bar(self):
        """Setup da barra de busca (Ctrl+F)."""
        from PyQt6.QtWidgets import QPushButton
        self.find_bar = QWidget()
        self.find_bar.setStyleSheet("background: transparent;")
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(8, 4, 8, 4)
        find_layout.setSpacing(8)
        
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Buscar na página...")
        self.find_input.returnPressed.connect(self._find_next)
        self.find_input.textChanged.connect(self._find_text_changed)
        find_layout.addWidget(self.find_input)
        
        self.find_count_label = QLabel("0/0")
        self.find_count_label.setStyleSheet("color: #888;")
        find_layout.addWidget(self.find_count_label)
        
        self.find_prev_btn = QPushButton("↑")
        self.find_prev_btn.setFixedWidth(28)
        self.find_prev_btn.clicked.connect(self._find_prev)
        find_layout.addWidget(self.find_prev_btn)
        
        self.find_next_btn = QPushButton("↓")
        self.find_next_btn.setFixedWidth(28)
        self.find_next_btn.clicked.connect(self._find_next)
        find_layout.addWidget(self.find_next_btn)
        
        self.find_close_btn = QPushButton("✕")
        self.find_close_btn.setFixedWidth(28)
        self.find_close_btn.clicked.connect(self.hide_find_bar)
        find_layout.addWidget(self.find_close_btn)
        
        find_layout.addStretch()
        self.find_bar.setLayout(find_layout)
        self.find_bar.hide()
        self.layout.addWidget(self.find_bar)
        
    def show_find_bar(self):
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()
        
    def hide_find_bar(self):
        self.find_bar.hide()
        tab = self.tab_widget.get_current_tab()
        if tab:
            tab.qt_view.page().findText("")
            
    def _find_text_changed(self, text):
        tab = self.tab_widget.get_current_tab()
        if tab:
            tab.qt_view.page().findText(text, 0, self._on_find_result)
            
    def _find_next(self):
        tab = self.tab_widget.get_current_tab()
        if tab:
            tab.qt_view.page().findText(self.find_input.text(), 0)
            
    def _find_prev(self):
        from PyQt6.QtWebEngineCore import QWebEnginePage
        tab = self.tab_widget.get_current_tab()
        if tab:
            tab.qt_view.page().findText(self.find_input.text(), QWebEnginePage.FindFlag.FindBackward)
            
    def _on_find_result(self, found):
        """Atualiza o label de contagem de resultados da busca."""
        if found:
            self.find_count_label.setText("✓ Encontrado")
            self.find_count_label.setStyleSheet("color: #2EA043;")
        else:
            text = self.find_input.text()
            if text:
                self.find_count_label.setText("Não encontrado")
                self.find_count_label.setStyleSheet("color: #F85149;")
            else:
                self.find_count_label.setText("")
                self.find_count_label.setStyleSheet("color: #888;")
        
    def _update_security_indicator(self, is_secure: bool, url: str = ""):
        """Atualiza o indicador de segurança HTTPS."""
        p = Theme.DARK if self.current_theme == "dark" else Theme.LIGHT
        if is_secure:
            color = "#2EA043"
            self.security_indicator.setToolTip("Conexão Segura (HTTPS)")
        else:
            color = p['text_tertiary']
            self.security_indicator.setToolTip("Conexão Não Segura")
        self.security_indicator.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.security_indicator.setText("🔒" if is_secure else "🔓")
        
    def _on_load_started(self):
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.url_bar.set_loading(True)
        self._update_security_indicator(False)
        
    def _on_load_finished(self, success: bool):
        self.progress_bar.hide()
        self.url_bar.set_loading(False)
        if success:
            tab = self.tab_widget.get_current_tab()
            if tab:
                url = tab.qt_view.url()
                is_https = url.scheme() == "https"
                self._update_security_indicator(is_https, url.toString())
        
    def _apply_floating_status_style(self):
        p = Theme.DARK if self.current_theme == "dark" else Theme.LIGHT
        self.floating_status.setStyleSheet(f"""
            QLabel {{
                background-color: {p['bg_secondary']};
                color: {p['text_secondary']};
                border: 1px solid {p['border']};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
            }}
        """)
        
    def _zoom_page(self, factor: float, reset: bool = False):
        tab = self.tab_widget.get_current_tab()
        if not tab:
            return
        if reset:
            tab.qt_view.setZoomFactor(1.0)
        else:
            current = tab.qt_view.zoomFactor()
            new_factor = max(0.25, min(5.0, current * factor))
            tab.qt_view.setZoomFactor(new_factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Mantém a status bar flutuante no bottom-left
        self.floating_status.move(10, self.centralWidget().height() - self.floating_status.height() - 10)

    def show_floating_status(self, text: Optional[str]):
        if text:
            self.floating_status.setText(text)
            self.floating_status.adjustSize()
            self.floating_status.move(10, self.centralWidget().height() - self.floating_status.height() - 10)
            self.floating_status.show()
            self.floating_status.raise_()
            self.status_timer.start(2000)
        else:
            self.floating_status.hide()

    def _create_dropdown_menu(self) -> QMenu:
        menu = QMenu(self)
        
        a1 = menu.addAction("Nova Aba\tCtrl+T")
        a1.triggered.connect(self.new_tab)
        
        a2 = menu.addAction(self._create_icon(Icons.PRIVATE), "Nova Janela Privada\tCtrl+Shift+P")
        a2.triggered.connect(self.open_private_window)
        
        menu.addSeparator()
        
        a3 = menu.addAction(self._create_icon(Icons.HISTORY), "Histórico\tCtrl+H")
        a3.triggered.connect(self.show_history)
        
        a4 = menu.addAction(self._create_icon(Icons.STAR), "Favoritos\tCtrl+Shift+B")
        a4.triggered.connect(self.show_bookmarks) # Shortcut real
        
        a5 = menu.addAction(self._create_icon(Icons.DOWNLOAD), "Downloads\tCtrl+J")
        a5.triggered.connect(self.show_downloads)
        
        menu.addSeparator()
        
        a6 = menu.addAction(self._create_icon(Icons.SHIELD), "Fingerprint\tCtrl+Shift+F")
        a6.triggered.connect(self.show_fingerprint_panel)
        
        a_adblock = menu.addAction(self._create_icon(Icons.ADBLOCK), "Bloqueador de Anúncios\tCtrl+Shift+A")
        a_adblock.triggered.connect(self.show_adblock_panel)
        
        ext_menu = menu.addMenu(self._create_icon(Icons.SHIELD), "Extensões")
        ext_menu.addAction("Gerenciar Extensões", self.show_extensions)
        ext_menu.addAction("Carregar descompactada...", self.install_extension_unpacked)
        ext_menu.addAction("Instalar .crx...", self.install_extension_crx)
        
        a7 = menu.addAction("DevTools\tF12")
        a7.triggered.connect(self.toggle_devtools)
        
        menu.addSeparator()
        
        # Search Engines submenu
        engine_menu = menu.addMenu("Motor de Busca")
        current = get_current_engine()
        for engine in ALL_ENGINES:
            label = f"{engine.icon} {engine.name}"
            if engine.is_private:
                label += " 🔒"
            action = engine_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(engine.name == current.name)
            action.triggered.connect(lambda checked, e=engine: self._set_search_engine(e))
        
        menu.addSeparator()
        
        self.theme_action = menu.addAction(self._create_icon(Icons.SUN), "Tema Claro")
        self.theme_action.triggered.connect(self.toggle_theme)
        
        menu.addSeparator()

        a_update = menu.addAction("Verificar Atualizações...")
        a_update.triggered.connect(lambda: self._update_manager.check_for_updates(silent=False))

        a_about = menu.addAction(f"Sobre o {APP_NAME} v{APP_VERSION}")

        # Adicionar atalho p Bookmarks bar escondida
        toggle_bb = QAction("Toggle BB", self)
        toggle_bb.setShortcut("Ctrl+Shift+B")
        toggle_bb.triggered.connect(lambda: self.bookmarks_bar.setVisible(not self.bookmarks_bar.isVisible()))
        self.addAction(toggle_bb)
        
        return menu

    def _set_search_engine(self, engine):
        set_current_engine(engine)
        self.url_bar.setPlaceholderText(f"Pesquisar com {engine.name}")
        self._init_pages()
        # Reload home if currently on home
        tab = self.tab_widget.get_current_tab()
        if tab and tab.qt_view.url().toString() in ("about:home", "about:blank", ""):
            self.navigate_home()
        self.show_floating_status(f"Motor de busca: {engine.name}")

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.current_theme = "light"
            self.theme_action.setText("Tema Escuro")
            self.theme_action.setIcon(self._create_icon(Icons.MOON))
        else:
            self.current_theme = "dark"
            self.theme_action.setText("Tema Claro")
            self.theme_action.setIcon(self._create_icon(Icons.SUN))
        self.apply_theme()
        # Persistir escolha
        self._settings.set("theme", self.current_theme)

    def toggle_bookmark(self):
        url = self.url_bar.text()
        title = self.windowTitle().replace(" - Redux Browser", "")
        # Toggle logica simplificada
        if self.bookmark_manager.is_bookmarked(url):
            self.bookmark_manager.remove_bookmark(url)
            self.fav_btn.setIcon(self._create_icon(Icons.STAR))
        else:
            self.bookmark_manager.add_bookmark(title, url)
            self.fav_btn.setIcon(self._create_icon(Icons.STAR_FILLED))
        self.bookmarks_bar.populate()
        
    def new_tab(self):
        tab = self.tab_widget.add_new_tab("about:home", self.is_private)
        # Load home page directly
        self.url_bar.setText("about:home")
        self.url_bar.setCursorPosition(0)
        tab.load_html(self.home_html, "about:home", "Redux Browser")

    def close_current_tab(self):
        index = self.tab_widget.currentIndex()
        if index != -1:
            self.tab_widget.close_tab(index)
            if self.tab_widget.count() == 0:
                self.new_tab()

    def open_private_window(self):
        self.private_window = MainWindow(is_private=True, history_mgr=self.history_manager, bookmark_mgr=self.bookmark_manager, cache_mgr=self.cache_manager)
        self.private_window.show()

    def show_history(self):
        dlg = HistoryDialog(self.history_manager, self)
        dlg.exec()

    def show_bookmarks(self):
        dlg = BookmarksDialog(self.bookmark_manager, self)
        dlg.exec()
        self.bookmarks_bar.populate()

    def toggle_devtools(self):
        if self.dom_viewer.isVisible(): 
            self.dom_viewer.hide()
        else: 
            self.dom_viewer.show()
            # Conectar console ao webview ativo
            tab = self.tab_widget.get_current_tab()
            if tab and hasattr(tab, 'qt_view'):
                self.dom_viewer.set_webview(tab.qt_view)

    def show_fingerprint_panel(self):
        dlg = FingerprintPanel(self.farbling_engine, self)
        dlg.exec()

    def show_extensions(self):
        self.url_bar.setText("about:extensions")
        self.navigate_to_url()
        
    def install_extension_unpacked(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar diretório da extensão")
        if folder:
            try:
                from pathlib import Path
                self.extension_manager.install_from_folder(Path(folder))
                self.show_extensions()
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))
                
    def install_extension_crx(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar .crx ou .zip", "", "Extensões (*.crx *.zip)")
        if file_path:
            try:
                from pathlib import Path
                self.extension_manager.install_from_crx(Path(file_path))
                self.show_extensions()
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def navigate_home(self):
        self.url_bar.setText("about:home")
        self.navigate_to_url()
        
    def navigate_to_url(self):
        url_text = self.url_bar.text().strip()
        if not url_text: return
        tab = self.tab_widget.get_current_tab()
        
        if url_text == "about:home":
            tab.load_html(self.home_html, url_text, "Redux Browser")
            return
            
        if url_text == "about:extensions":
            ext_html = self.ext_page_gen.generate_html(self.current_theme)
            tab.load_html(ext_html, url_text, "Extensões")
            self._setup_extension_channel(tab)
            return
            
        if url_text == "about:error":
            tab.load_html(self.error_html, url_text, "Erro de Conexão")
            return
            
        if "://" not in url_text:
            url_text = "https://" + url_text
            self.url_bar.setText(url_text)
            
        self._load_network_url(url_text)

    def _load_network_url(self, url: str):
        tab = self.tab_widget.get_current_tab()
        if not tab: return
        
        self.url_bar.setText(url)
        self.history_manager.add_entry(tab.id, url, url, self.is_private)
        
        # update favicon logic will go to tab event
        if self.bookmark_manager.is_bookmarked(url):
            self.fav_btn.setIcon(self._create_icon(Icons.STAR_FILLED))
        else:
            self.fav_btn.setIcon(self._create_icon(Icons.STAR))
            
        tab.load_url(url)
        self.show_floating_status(f"Carregando {url}...")

    def update_url_bar(self, qurl_str):
        if qurl_str == "about:blank": return
        self.url_bar.setText(qurl_str)
        self.url_bar.setCursorPosition(0)
        
        # Chrome Web Store detection
        if self.cws_widget:
            self.cws_widget.update_for_url(qurl_str, self.extension_manager)
        
        if self.bookmark_manager.is_bookmarked(qurl_str):
            self.fav_btn.setIcon(self._create_icon(Icons.STAR_FILLED))
        else:
            self.fav_btn.setIcon(self._create_icon(Icons.STAR))
        
    def update_title(self, title):
        private_str = " (Privado 🔒)" if self.is_private else ""
        self.setWindowTitle(f"{title} - Redux Browser{private_str}")
        self.show_floating_status(None) # Ocultar ao terminar
            
    def navigate_back(self):
        tab = self.tab_widget.get_current_tab()
        if tab:
            if tab.active_engine == 0:
                tab.back()
            else:
                url = self.history_manager.go_back(tab.id)
                if url: self._load_network_url(url)
        
    def navigate_forward(self):
        tab = self.tab_widget.get_current_tab()
        if tab:
             if tab.active_engine == 0:
                 tab.forward()
             else:
                 url = self.history_manager.go_forward(tab.id)
                 if url: self._load_network_url(url)
        
    def reload_page(self):
        tab = self.tab_widget.get_current_tab()
        if tab: tab.reload()

    def _setup_downloads(self):
        """Conecta o download manager ao profile padrão do WebEngine."""
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self._on_download_requested)
        # Atalho Ctrl+J para downloads
        dl_shortcut = QAction("Downloads", self)
        dl_shortcut.setShortcut("Ctrl+J")
        dl_shortcut.triggered.connect(self.show_downloads)
        self.addAction(dl_shortcut)

    def _setup_adblock(self):
        """Instala o interceptor de ad block no profile e carrega listas."""
        from PyQt6.QtCore import QThread, pyqtSignal as Signal

        profile = QWebEngineProfile.defaultProfile()
        self._adblock_interceptor = AdBlockInterceptor(self.adblock_engine, parent=self)
        self._adblock_interceptor.blocked.connect(self._on_ad_blocked)
        profile.setUrlRequestInterceptor(self._adblock_interceptor)

        # Carregar listas de filtro em background após 3s
        class FilterLoadWorker(QThread):
            done = Signal(int)
            def __init__(self, engine):
                super().__init__()
                self.engine = engine
            def run(self):
                self.engine.load_all_lists()
                self.done.emit(self.engine.total_rules)

        def _start_filter_load():
            self._filter_worker = FilterLoadWorker(self.adblock_engine)
            self._filter_worker.done.connect(self._on_filters_loaded)
            self._filter_worker.start()

        QTimer.singleShot(3000, _start_filter_load)

        # Atalho Ctrl+Shift+A
        adblock_shortcut = QAction("AdBlock", self)
        adblock_shortcut.setShortcut("Ctrl+Shift+A")
        adblock_shortcut.triggered.connect(self.show_adblock_panel)
        self.addAction(adblock_shortcut)

    def _on_filters_loaded(self, total_rules: int):
        """Callback quando as listas de filtro terminam de carregar."""
        self.show_floating_status(f"🛡️ Ad Blocker: {total_rules:,} regras carregadas")

    def _on_ad_blocked(self, url: str, domain: str):
        """Callback quando uma requisição é bloqueada pelo ad block."""
        count = self.adblock_engine.get_blocked_count()
        self._adblock_badge.setText(str(count) if count < 1000 else f"{count // 1000}k")
        self._adblock_badge.adjustSize()
        self._adblock_badge.show()
        # Posicionar badge sobre o botão de adblock na toolbar
        try:
            btn_widget = self.toolbar.widgetForAction(self.adblock_btn)
            if btn_widget:
                pos = btn_widget.pos()
                self._adblock_badge.move(
                    pos.x() + btn_widget.width() - self._adblock_badge.width() - 2,
                    pos.y() + 2
                )
                self._adblock_badge.raise_()
        except Exception:
            pass

    def show_adblock_panel(self):
        """Abre o painel de controle do bloqueador de anúncios."""
        current_domain = ""
        tab = self.tab_widget.get_current_tab()
        if tab:
            url = tab.qt_view.url().toString()
            current_domain = self.adblock_engine._extract_domain(url)
        dlg = AdBlockPanel(self.adblock_engine, current_domain, self)
        dlg.exec()
        
    def _on_download_requested(self, download_item):
        """Recebe pedido de download do WebEngine."""
        self.download_manager.start_download(download_item)
        
    def show_downloads(self):
        dlg = DownloadsDialog(self.download_manager, self)
        dlg.exec()

    def _on_cws_install(self, ext_id: str, ext_name: str, crx_path: str):
        """Callback quando o usuário clica em 'Adicionar ao Redux' na Chrome Web Store."""
        try:
            crx_file = Path(crx_path)
            
            if crx_file.exists():
                self.extension_manager.install_from_crx(crx_file)
                # Clean up temp
                try:
                    crx_file.unlink()
                except Exception:
                    pass
            else:
                QMessageBox.warning(self, "Aviso", "Arquivo CRX não encontrado após download.")
                return
                
            self.show_floating_status(f"✓ {ext_name} instalado!")
            
            # Refresh the CWS widget
            tab = self.tab_widget.get_current_tab()
            if tab:
                url = tab.qt_view.url().toString()
                self.cws_widget.update_for_url(url, self.extension_manager)
        except Exception as e:
            QMessageBox.critical(self, "Erro na Instalação", str(e))

    def _setup_extension_channel(self, tab):
        if not hasattr(self, 'ext_api_obj'):
            self.ext_api_obj = ReduxExtAPI(self.extension_manager, self)
        
        channel = QWebChannel(tab.qt_view.page())
        channel.registerObject("reduxExtAPI", self.ext_api_obj)
        tab.qt_view.page().setWebChannel(channel)

class ReduxExtAPI(QObject):
    def __init__(self, ext_manager, main_window):
        super().__init__()
        self.ext_manager = ext_manager
        self.main_window = main_window
        
    @pyqtSlot(str, bool)
    def toggleExtension(self, ext_id, state):
        if state: self.ext_manager.enable(ext_id)
        else: self.ext_manager.disable(ext_id)
        self.main_window.show_extensions()
        
    @pyqtSlot(str)
    def removeExtension(self, ext_id):
        self.ext_manager.uninstall(ext_id)
        self.main_window.show_extensions()
    
    @pyqtSlot(str)
    def togglePinned(self, ext_id):
        self.ext_manager.toggle_pinned(ext_id)
        self.main_window.show_extensions()
        
    @pyqtSlot()
    def loadUnpacked(self):
        self.main_window.install_extension_unpacked()
        
    @pyqtSlot()
    def installCrx(self):
        self.main_window.install_extension_crx()
