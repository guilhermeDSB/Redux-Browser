from PyQt6.QtWidgets import QTabWidget, QWidget, QTabBar, QToolButton, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QStandardItemModel, QStandardItem
from PyQt6.QtWebEngineCore import QWebEngineSettings
from browser.ui.tab import Tab
from browser.ui.icons import Icons
from browser.ui.theme import Theme

class ReduxTabBar(QTabBar):
    """QTabBar customizada para tratar tabs de nova aba mais graciosamente."""
    plusClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setTabsClosable(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)

class TabWidget(QTabWidget):
    """
    Gerenciador de Abas.
    Substitui o antigo layout central, orquestrando nós `Tab`.
    """
    
    currentTabUrlChanged = pyqtSignal(str)
    currentTabTitleChanged = pyqtSignal(str)
    hoveredUrlChanged = pyqtSignal(str)
    tabLoadStarted = pyqtSignal()
    tabLoadFinished = pyqtSignal(bool)

    def __init__(self, history_manager, farbling_injector, adblock_injector=None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.farbling_injector = farbling_injector
        self.adblock_injector = adblock_injector
        
        self.tab_bar = ReduxTabBar(self)
        self.setTabBar(self.tab_bar)
        
        self.setDocumentMode(True) 
        self.setMovable(True) 
        self.setTabsClosable(True)
        
        # O botão (+) é implementado como corner widget para melhor aparência (estilo Figma)
        self.plus_btn = QToolButton(self)
        self._setup_plus_button()
        self.setCornerWidget(self.plus_btn, Qt.Corner.TopLeftCorner) # Qt Bug: TopLeftCorner é usado para alinhar ao final em LTR dependendo do layout... mas vamos fixar com StyleSheet

        # Corrigir corner widget:
        self.setCornerWidget(self.plus_btn, Qt.Corner.TopRightCorner)
        
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_tab_changed)

    def _setup_plus_button(self):
        from PyQt6.QtGui import QPixmap, QIcon
        from browser.ui.icons import Icons
        svg_str = Icons.PLUS
        pixmap = QPixmap()
        pixmap.loadFromData(svg_str.replace('currentColor', '#888888').encode('utf-8'), "SVG")
        self.plus_btn.setIcon(QIcon(pixmap))
        # O Theme.generate_qss cuidará das cores do hover, removemos hardcoded stylesheet
        self.plus_btn.clicked.connect(lambda: self.add_new_tab("about:home"))

    def add_new_tab(self, url: str = "about:home", is_private: bool = False) -> Tab:
        """Cria e anexa uma aba nova com propriedades base."""
        tab = Tab(self, self.history_manager, self.farbling_injector, adblock_injector=self.adblock_injector, is_private=is_private)
        
        tab.urlChanged.connect(self._handle_url_change)
        tab.titleChanged.connect(self._handle_title_change)
        tab.loadStarted.connect(self._on_tab_load_started)
        tab.loadFinished.connect(self._on_tab_load_finished)
        
        # Interceptar hover do WebEngine (link flutuante)
        tab.qt_view.page().linkHovered.connect(self.hoveredUrlChanged.emit)
        
        # Favicon loading
        tab.qt_view.iconChanged.connect(lambda icon: self._on_icon_changed(tab, icon))
        
        icon_text = "🔒 " if is_private else ""
        index = self.addTab(tab, f"{icon_text}Nova Aba")
        self.setCurrentIndex(index)
        
        return tab
    
    def _on_tab_load_started(self):
        self.tabLoadStarted.emit()
        
    def _on_tab_load_finished(self, ok: bool):
        self.tabLoadFinished.emit(ok)
        
    def _on_icon_changed(self, tab: Tab, icon):
        index = self.indexOf(tab)
        if index >= 0:
            self.setTabIcon(index, icon)

    def get_current_tab(self) -> Tab | None:
        """Retorna a Tab presentemente ativa."""
        widget = self.currentWidget()
        if isinstance(widget, Tab):
            return widget
        return None

    def close_tab(self, index: int):
        """Fecha tab no index e deleta memoria atrelada."""
        widget = self.widget(index)
        if isinstance(widget, Tab):
            widget.cleanup()
        self.removeTab(index)
        widget.deleteLater()

    def _on_tab_changed(self, index: int):
        """Gatilho quando o usuário muda de aba ativa."""
        tab = self.get_current_tab()
        if tab:
            self.currentTabUrlChanged.emit(tab.current_url())
            title = self.tabText(index)
            self.currentTabTitleChanged.emit(title)

    def _handle_url_change(self, url: str):
        if self.sender() == self.get_current_tab():
            self.currentTabUrlChanged.emit(url)
            
    def _handle_title_change(self, title: str):
        sender_tab = self.sender()
        if sender_tab:
            index = self.indexOf(sender_tab)
            if index != -1:
                prefix = "🔒 " if sender_tab.is_private else ""
                short_title = title[:20] + "..." if len(title) > 20 else title
                self.setTabText(index, f"{prefix}{short_title}")
                self.setTabToolTip(index, title)
                
            if sender_tab == self.get_current_tab():
                self.currentTabTitleChanged.emit(title)
