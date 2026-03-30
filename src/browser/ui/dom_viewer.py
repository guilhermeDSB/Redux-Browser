from PyQt6.QtWidgets import (
    QDockWidget, QTreeWidget, QTreeWidgetItem, 
    QVBoxLayout, QWidget, QTextEdit, QSplitter, QTabWidget, QLabel,
    QTreeWidget as QNetworkTreeWidget, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from typing import Optional
from browser.engine.html_parser import DOMNode
from browser.engine.render_tree import RenderNode
from browser.ui.theme import Theme
from browser.ui.console_widget import ReduxConsole


class DOMViewer(QDockWidget):
    """
    Visualizador da Árvore DOM para o Redux Browser (Redesign Minimalista).
    Inclui Elements, Console e Network.
    """
    def __init__(self, parent=None):
        super().__init__("DevTools", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setMinimumWidth(300)
        
        self._current_webview = None
        self.node_map = {}
        self.current_theme = "dark"
        
        self.container = QWidget()
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tabs para Elements/Console/Network
        self.tabs = QTabWidget()
        
        # === Página Elements ===
        elements_page = QWidget()
        elements_layout = QVBoxLayout(elements_page)
        elements_layout.setContentsMargins(0, 0, 0, 0)
        elements_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(16)
        self.tree_widget.itemClicked.connect(self._on_item_clicked)
        self.splitter.addWidget(self.tree_widget)
        
        self.style_view = QTextEdit()
        self.style_view.setReadOnly(True)
        self.splitter.addWidget(self.style_view)
        
        elements_layout.addWidget(self.splitter)
        self.tabs.addTab(elements_page, "Elements")
        
        # === Página Console ===
        self.console = ReduxConsole(self.current_theme)
        self.tabs.addTab(self.console, "Console")
        
        # === Página Network ===
        network_page = QWidget()
        network_layout = QVBoxLayout(network_page)
        network_layout.setContentsMargins(0, 0, 0, 0)
        network_layout.setSpacing(0)
        
        self.network_tree = QTreeWidget()
        self.network_tree.setHeaderLabels(["Name", "Status", "Type", "Size", "Time"])
        self.network_tree.header().setStretchLastSection(False)
        self.network_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.network_tree.setColumnWidth(1, 60)
        self.network_tree.setColumnWidth(2, 80)
        self.network_tree.setColumnWidth(3, 70)
        self.network_tree.setColumnWidth(4, 70)
        self.network_tree.setIndentation(0)
        self._network_data = []
        network_layout.addWidget(self.network_tree)
        
        self.tabs.addTab(network_page, "Network")
        
        layout.addWidget(self.tabs)
        self.setWidget(self.container)
        
        self.apply_theme("dark")

    def set_webview(self, webview):
        """Conecta o DevTools a uma QWebEngineView."""
        self._current_webview = webview
        self.console.set_webview(webview)
        
        if hasattr(webview, 'page'):
            webview.page().loadFinished.connect(self._on_page_load_finished)

    def _on_page_load_finished(self, ok: bool):
        if ok and self._current_webview:
            url = self._current_webview.url().toString()
            self.add_network_entry(url, "200", "document", "-", "ok")

    def add_network_entry(self, name: str, status: str, rtype: str, size: str, duration: str):
        """Adiciona uma entrada na aba Network."""
        item = QTreeWidgetItem()
        item.setText(0, name[:60] + ('...' if len(name) > 60 else ''))
        item.setText(1, status)
        item.setText(2, rtype)
        item.setText(3, size)
        item.setText(4, duration)
        
        p = Theme.DARK if self.current_theme == "dark" else Theme.LIGHT
        if status == "200":
            item.setForeground(1, QColor(p.get('success', '#2EA043')))
        elif status.startswith("3"):
            item.setForeground(1, QColor(p.get('warning', '#D29922')))
        else:
            item.setForeground(1, QColor(p.get('error', '#F85149')))
        
        self.network_tree.insertTopLevelItem(0, item)

    def apply_theme(self, current_theme: str):
        self.current_theme = current_theme
        p = Theme.DARK if current_theme == "dark" else Theme.LIGHT
        
        self.setStyleSheet(f"""
            QDockWidget {{
                background: {p['bg_primary']};
                color: {p['text_secondary']};
                border-left: 1px solid {p['border']};
                titlebar-close-icon: none;
            }}
            QDockWidget::title {{
                background: {p['bg_secondary']};
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                color: {p['text_primary']};
                border-bottom: 1px solid {p['border']};
            }}
        """)

        self.container.setStyleSheet(f"background: {p['bg_primary']};")
        
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; border-top: 1px solid {p['border']}; }}
            QTabBar {{ background: {p['bg_primary']}; border: none; height: 28px; }}
            QTabBar::tab {{
                background: transparent; color: {p['text_secondary']}; padding: 4px 16px; 
                font-size: 12px; font-weight: 500; border: none; border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{ color: {p['text_primary']}; border-bottom: 2px solid {p['accent']}; }}
            QTabBar::tab:hover {{ color: {p['text_primary']}; }}
        """)
        
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background: {p['border']}; height: 1px; }}")
        
        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background: {p['bg_primary']}; border: none; outline: none;
                font-family: 'Consolas', 'SF Mono', monospace; font-size: 12px;
            }}
            QTreeWidget::item {{ height: 24px; color: {p['text_secondary']}; }}
            QTreeWidget::item:hover {{ background: {p['bg_tertiary']}; }}
            QTreeWidget::item:selected {{ background: {p['accent_subtle']}; border-left: 2px solid {p['accent']}; }}
        """)
        
        self.style_view.setStyleSheet(f"""
            QTextEdit {{
                background: {p['bg_primary']}; border: none; color: {p['text_primary']};
                font-family: 'Consolas', 'SF Mono', monospace; font-size: 12px;
                padding: 8px;
            }}
        """)
        
        self.style_view.setHtml(f"<span style='color:{p['text_secondary']};'>Selecione um elemento para ver seus estilos computados...</span>")
        
        if hasattr(self, 'console'):
            self.console.set_theme(current_theme)
        
        self.network_tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {p['bg_primary']}; border: none; outline: none;
                font-family: 'Consolas', 'SF Mono', monospace; font-size: 11px;
                color: {p['text_primary']};
            }}
            QTreeWidget::item {{ height: 22px; }}
            QTreeWidget::item:hover {{ background: {p['bg_tertiary']}; }}
            QTreeWidget::item:selected {{ background: {p['accent_subtle']}; }}
            QHeaderView::section {{
                background: {p['bg_secondary']}; color: {p['text_secondary']};
                border: none; border-bottom: 1px solid {p['border']};
                padding: 4px 8px; font-size: 11px; font-weight: 600;
            }}
        """)

    def populate(self, root_node: Optional[DOMNode], render_root: Optional[RenderNode] = None):
        self.tree_widget.clear()
        self.node_map.clear()
        
        if not root_node:
            return
            
        self.render_map = {}
        if render_root:
            self._build_render_map(render_root)

        root_item = self._create_tree_item(root_node)
        self.tree_widget.addTopLevelItem(root_item)
        root_item.setExpanded(True)

    def _build_render_map(self, r_node: RenderNode):
        self.render_map[id(r_node.dom_node)] = r_node
        for child in r_node.children:
            self._build_render_map(child)

    def _format_html_tag(self, node: DOMNode) -> str:
        if node.tag_name == "#text":
           return f"\"{node.text_content.strip()[:30]}\""
           
        attrs = []
        for k, v in node.attributes.items():
            attrs.append(f"{k}='{v}'")
        attr_str = " ".join(attrs)
        
        if attr_str:
            return f"<{node.tag_name} {attr_str}>"
        return f"<{node.tag_name}>"

    def _create_tree_item(self, node: DOMNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        p = Theme.DARK if getattr(self, 'current_theme', 'dark') == "dark" else Theme.LIGHT
        
        if node.tag_name == "#text":
            text_preview = node.text_content.replace('\\n', '').strip()
            item.setText(0, f"\"{text_preview[:40]}...\"" if len(text_preview) > 40 else f"\"{text_preview}\"")
            item.setForeground(0, QColor(p['text_secondary']))
        else:
            item.setText(0, self._format_html_tag(node))
            tag_color = "#FF8080" if getattr(self, 'current_theme', 'dark') == 'dark' else "#D32F2F"
            item.setForeground(0, QColor(tag_color))
            
        self.node_map[id(item)] = node
        
        for child in node.children:
            child_item = self._create_tree_item(child)
            item.addChild(child_item)
            
        return item

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        node = self.node_map.get(id(item))
        if not node: return
        p = Theme.DARK if getattr(self, 'current_theme', 'dark') == "dark" else Theme.LIGHT
        tag_color = "#FF8080" if getattr(self, 'current_theme', 'dark') == 'dark' else "#D32F2F"
        prop_color = "#88DDFF" if getattr(self, 'current_theme', 'dark') == 'dark' else "#1976D2"
        val_color = "#C3E88D" if getattr(self, 'current_theme', 'dark') == 'dark' else "#388E3C"
            
        if node.tag_name == "#text":
            self.style_view.setHtml(f"<span style='color:{p['text_secondary']};'>Nó de Texto<br/>(Herda estilos do pai)</span>")
            return
            
        html = f"<div style='margin-bottom: 8px;'><span style='color:{tag_color};'>{node.tag_name}</span> {{</div>"
        
        r_node = self.render_map.get(id(node))
        if r_node:
            for prop, val in sorted(r_node.styles.items()):
                html += f"<div style='margin-left: 16px;'><span style='color:{prop_color};'>{prop}</span>: <span style='color:{val_color};'>{val}</span>;</div>"
            
            html += "</div>"
            
            if r_node.layout_box:
                lb = r_node.layout_box
                html += f"<hr style='border: none; border-bottom: 1px solid {p['border']};'/>"
                html += f"<div style='color:{p['text_tertiary']};'>/* Box Model */</div>"
                html += f"<div style='margin-left: 16px;'><span style='color:{prop_color};'>width</span>: <span style='color:{val_color};'>{lb.content.width:.1f}px</span>;</div>"
                html += f"<div style='margin-left: 16px;'><span style='color:{prop_color};'>height</span>: <span style='color:{val_color};'>{lb.content.height:.1f}px</span>;</div>"
        else:
            html += f"<div style='color:{p['text_tertiary']}; margin-left: 16px;'>/* display: none / unrendered */</div></div>"
            if node.attributes:
                html += f"<hr style='border: none; border-bottom: 1px solid {p['border']};'/>"
                html += f"<div style='color:{p['text_tertiary']};'>/* Attributes */</div>"
                for k, v in node.attributes.items():
                    html += f"<div style='margin-left: 16px;'><span style='color:{prop_color};'>{k}</span>: <span style='color:{val_color};'>\"{v}\"</span></div>"
            
        self.style_view.setHtml(html)
