import os
import uuid
from urllib.parse import urlparse
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView

from browser.engine.html_parser import HTMLParser
from browser.engine.css_parser import CSSParser
from browser.engine.render_tree import RenderTree
from browser.engine.layout import LayoutEngine
from browser.ui.dom_viewer import DOMViewer

class ReduxRenderWidget(QWidget):
    """
    (Movido da MainWindow) Widget customizado que desenha a RenderTree usando QPainter.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.render_tree_root = None
        self.setStyleSheet("background-color: white;")

    def set_render_tree(self, root):
        self.render_tree_root = root
        self.update() 

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.render_tree_root: return
        self._paint_node(painter, self.render_tree_root)

    def _paint_node(self, painter, node):
        if not node.layout_box: return
        box = node.layout_box
        x, y = int(box.content.x), int(box.content.y)
        w, h = int(box.content.width), int(box.content.height)

        if node.dom_node.tag_name == "#text":
            text = node.dom_node.text_content.strip()
            if text:
                from PyQt6.QtGui import QColor, QFont
                painter.setPen(QColor(node.styles.get('color', 'black')))
                fs_str = node.styles.get('font-size', '16px').replace('px', '').replace('em', '')
                try: 
                    font_size = int(float(fs_str)) 
                    if 'em' in node.styles.get('font-size', '16px'): font_size *= 16
                except: font_size = 16
                font_size = max(1, font_size)  # QFont requires size >= 1
                font = QFont(node.styles.get('font-family', 'sans-serif'), font_size)
                if node.styles.get('font-weight') == 'bold': font.setBold(True)
                if node.styles.get('font-style') == 'italic': font.setItalic(True)
                painter.setFont(font)
                painter.drawText(x, y + font_size, text) 
        else:
            bg_color = node.styles.get('background-color', 'transparent')
            if bg_color != 'transparent':
                from PyQt6.QtGui import QColor
                painter.fillRect(x, y, w, h, QColor(bg_color))
        for child in node.children:
            self._paint_node(painter, child)


class Tab(QWidget):
    """
    Representa uma única aba no navegador.
    Gerencia seu próprio QtWebEngineView, Redux Engine, árvore DOM local e histórico.
    """
    # Sinais emitidos para a MainWindow ou TabWidget atualizar a UI
    urlChanged = pyqtSignal(str)
    titleChanged = pyqtSignal(str)
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, tab_widget, history_manager, farbling_injector, is_private=False, adblock_injector=None):
        super().__init__()
        self.tab_widget = tab_widget
        self.history_manager = history_manager
        self.farbling_injector = farbling_injector
        self.adblock_injector = adblock_injector
        self.id = str(uuid.uuid4())
        self.is_private = is_private
        
        # 0: QtWebEngine, 1: Redux Engine
        self.active_engine = 0 
        
        # Parsers próprios da aba instanciados localmente para não poluir via concorrência
        self.html_parser = HTMLParser()
        self.css_parser = CSSParser()
        self.dom_last_root = None
        self.render_last_root = None

        self._setup_ui()
        
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self._internal_url = None
        
        # Engine Principal (WebEngine)
        self.qt_view = QWebEngineView()
        
        def _on_url_changed(qurl):
            url_str = qurl.toString()
            # For internal pages, show the display URL instead of file path
            if self._internal_url and url_str.startswith("file:///"):
                url_str = self._internal_url
            self.urlChanged.emit(url_str)
            if hasattr(self.window(), 'content_script_loader'):
                self.window().content_script_loader.inject_scripts_for_page(self.qt_view.page(), url_str)
                
        self.qt_view.urlChanged.connect(_on_url_changed)
        self.qt_view.loadStarted.connect(self.loadStarted.emit)
        
        def _on_load_finished(ok):
            title = self.qt_view.title() or "Página sem título"
            self.titleChanged.emit(title)
            self.loadFinished.emit(ok)
        self.qt_view.loadFinished.connect(_on_load_finished)
        
        # Engine Redux
        self.redux_view = ReduxRenderWidget()
        self.redux_view.hide()
        
        self.layout.addWidget(self.qt_view)
        self.layout.addWidget(self.redux_view)

    def switch_engine(self, engine_index: int):
        if self.active_engine == engine_index: return
        self.active_engine = engine_index
        if engine_index == 0:
            self.redux_view.hide()
            self.qt_view.show()
        else:
            self.qt_view.hide()
            self.redux_view.show()

    def _extract_domain(self, url: str) -> str:
        """Extrai o domínio da URL para gerar seed de farbling."""
        try:
            parsed = urlparse(url)
            return parsed.netloc or parsed.path or "unknown"
        except Exception:
            return "unknown"

    def load_url(self, url: str):
        """Dispara no motor ativo."""
        self.loadStarted.emit()
        
        # Injetar farbling baseado no DOMÍNIO da URL
        domain = self._extract_domain(url)
        self.farbling_injector.inject(self.qt_view.page(), domain)
        
        # Injetar filtros cosméticos do ad blocker
        if self.adblock_injector:
            self.adblock_injector.inject(self.qt_view.page(), domain)
        
        if self.active_engine == 0:
            self.qt_view.setUrl(QUrl(url))
        else:
            # Integração temporária do Redux
            import requests
            try:
                resp = requests.get(url, timeout=5)
                self.load_html(resp.text, url, url)
            except Exception as e:
                self.load_html(f"<html><body><h1>Erro</h1><p>{e}</p></body></html>", url, "Erro")

    def load_html(self, html: str, url: str, title: str):
        """Carrega HTML cru dependendo da engine"""
        self.urlChanged.emit(url)
        self.titleChanged.emit(title)
        self._internal_url = url  # Store the display URL
        
        if self.active_engine == 0:
            import tempfile, os
            tmp_dir = os.path.join(tempfile.gettempdir(), "redux_browser")
            os.makedirs(tmp_dir, exist_ok=True)
            safe_name = url.replace(":", "_").replace("/", "_")[:20]
            tmp_file = os.path.join(tmp_dir, f"{safe_name}.html")
            with open(tmp_file, 'w', encoding='utf-8') as f:
                f.write(html)
            self.qt_view.setUrl(QUrl.fromLocalFile(tmp_file))
        else:
            self.dom_last_root = self.html_parser.parse(html).root
            
            # Extrai CSS de tags <style> encontradas no DOM
            def _find_style_tags(node, results):
                if node.tag_name == 'style':
                    results.append(node)
                for child in node.children:
                    _find_style_tags(child, results)
            
            style_nodes = []
            _find_style_tags(self.dom_last_root, style_nodes)
            for style_node in style_nodes:
                for child in style_node.children:
                    if child.tag_name == '#text' and child.text_content.strip():
                        self.css_parser.load_css(child.text_content)

            render_tree = RenderTree(self.dom_last_root, self.css_parser)
            render_tree.build()
            self.render_last_root = render_tree.root
            
            layout = LayoutEngine(self.redux_view.width(), self.redux_view.height())
            layout.layout(self.render_last_root)
            
            self.redux_view.set_render_tree(self.render_last_root)
            self.loadFinished.emit(True)

    def current_url(self) -> str:
        return self.qt_view.url().toString() if self.active_engine == 0 else ""

    def back(self):
        if self.active_engine == 0: 
            self.qt_view.back()
        else:
            url = self.history_manager.go_back(self.id)
            if url: self.load_url(url)

    def forward(self):
        if self.active_engine == 0:
            self.qt_view.forward()
        else:
            url = self.history_manager.go_forward(self.id)
            if url: self.load_url(url)

    def reload(self):
        if self.active_engine == 0: self.qt_view.reload()
        # TODO Redux reload

    def cleanup(self):
        """Garante que WebEngine seja destruído corretamente, limpa temp files e para som/vídeo."""
        self.qt_view.stop()
        # Limpa arquivos temporários criados por esta tab
        import tempfile, glob
        tmp_dir = os.path.join(tempfile.gettempdir(), "redux_browser")
        if os.path.exists(tmp_dir):
            for f in glob.glob(os.path.join(tmp_dir, "*.html")):
                try:
                    os.remove(f)
                except Exception:
                    pass
        # Remove tab state do histórico
        if self.history_manager:
            self.history_manager.remove_tab_state(self.id)
        self.qt_view.deleteLater()
