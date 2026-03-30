"""
Redux Browser — DevTools Console
Painel de console JavaScript funcional com execução de comandos.
"""

from PyQt6.QtWidgets import (
    QTextEdit, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QSplitter,
    QMenu, QPushButton, QListWidget, QListWidgetItem, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QAction
from typing import List, Optional
from datetime import datetime
import re
from browser.ui.theme import Theme


class ConsoleMessage:
    """Uma mensagem de console."""
    def __init__(self, msg_type: str, text: str, timestamp: str = None):
        self.type = msg_type  # log, info, warn, error, result, command
        self.text = text
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")
    
    @property
    def display_text(self) -> str:
        prefix = {
            'log': '>',
            'info': 'ℹ',
            'warn': '⚠',
            'error': '✕',
            'result': '<',
            'command': '»',
        }.get(self.type, '>')
        return f"[{self.timestamp}] {prefix} {self.text}"


class ConsoleOutputWidget(QTextEdit):
    """Widget de saída do console com syntax highlighting."""
    
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._apply_theme()
        
    def _apply_theme(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {p['bg_primary']};
                color: {p['text_primary']};
                border: none;
                font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'SF Mono', monospace;
                font-size: 12px;
                padding: 8px;
                selection-background-color: {p['accent_subtle']};
            }}
        """)
    
    def set_theme(self, theme: str):
        self._theme = theme
        self._apply_theme()
    
    def add_message(self, msg: ConsoleMessage):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Cores por tipo de mensagem
        colors = {
            'log': '#888888',
            'info': '#58A6FF',
            'warn': '#D29922',
            'error': '#F85149',
            'result': '#2EA043',
            'command': '#8B949E',
        }
        
        if self._theme == "light":
            colors = {
                'log': '#666666',
                'info': '#0969DA',
                'warn': '#9A6700',
                'error': '#CF222E',
                'result': '#116329',
                'command': '#57606A',
            }
        
        color = colors.get(msg.type, colors['log'])
        
        timestamp_fmt = f'<span style="color: {colors["command"]}; font-size: 10px;">[{msg.timestamp}]</span> '
        
        prefix = {
            'log': '',
            'info': '<span style="color: #58A6FF;">ℹ </span>',
            'warn': '<span style="color: #D29922;">⚠ </span>',
            'error': '<span style="color: #F85149;">✕ </span>',
            'result': '<span style="color: #2EA043;">← </span>',
            'command': '<span style="color: #8B949E;">» </span>',
        }.get(msg.type, '')
        
        escaped_text = msg.text.replace('<', '&lt;').replace('>', '&gt;')
        
        html = f'{timestamp_fmt}{prefix}<span style="color: {color};">{escaped_text}</span>'
        
        cursor.insertHtml(f'{html}<br>')
        # Auto-scroll para o final
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.ensureCursorVisible()


class ConsoleInputWidget(QLineEdit):
    """Input de comandos do console com histórico."""
    
    command_submitted = pyqtSignal(str)
    
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._history: List[str] = []
        self._history_index = -1
        self._current_input = ""
        self._apply_theme()
        
        self.setPlaceholderText("Digite um comando JavaScript e pressione Enter...")
        
    def _apply_theme(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {p['bg_tertiary']};
                border: 1px solid {p['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
                color: {p['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {p['border_focus']};
            }}
        """)
    
    def set_theme(self, theme: str):
        self._theme = theme
        self._apply_theme()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            text = self.text().strip()
            if text:
                self._history.insert(0, text)
                self._history_index = -1
                self.command_submitted.emit(text)
                self.clear()
        elif event.key() == Qt.Key.Key_Up:
            if self._history_index == -1:
                self._current_input = self.text()
            if self._history_index < len(self._history) - 1:
                self._history_index += 1
                self.setText(self._history[self._history_index])
        elif event.key() == Qt.Key.Key_Down:
            if self._history_index > 0:
                self._history_index -= 1
                self.setText(self._history[self._history_index])
            elif self._history_index == 0:
                self._history_index = -1
                self.setText(self._current_input)
        else:
            super().keyPressEvent(event)


class ReduxConsole(QWidget):
    """
    Console JavaScript completo para o Redux Browser DevTools.
    """
    
    execute_script = pyqtSignal(str)
    
    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._current_webview = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        
        label = QLabel("Console")
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        label.setStyleSheet(f"color: {p['text_secondary']}; font-size: 11px; font-weight: 600;")
        toolbar_layout.addWidget(label)
        toolbar_layout.addStretch()
        
        clear_btn = QPushButton("Limpar")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {p['text_tertiary']}; font-size: 11px;
            }}
            QPushButton:hover {{ color: {p['text_primary']}; }}
        """)
        clear_btn.clicked.connect(self._clear)
        toolbar_layout.addWidget(clear_btn)
        
        layout.addWidget(toolbar)
        
        # Output area
        self.output = ConsoleOutputWidget(self._theme)
        layout.addWidget(self.output, 1)
        
        # Input area
        self.input = ConsoleInputWidget(self._theme)
        self.input.command_submitted.connect(self._on_command)
        layout.addWidget(self.input)
        
    def set_theme(self, theme: str):
        self._theme = theme
        self.output.set_theme(theme)
        self.input.set_theme(theme)
        self._apply_toolbar_style()
        
    def _apply_toolbar_style(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT
        for child in self.findChildren(QLabel):
            child.setStyleSheet(f"color: {p['text_secondary']}; font-size: 11px;")
    
    def set_webview(self, webview):
        """Conecta o console a uma QWebEngineView para executar scripts e interceptar console.log."""
        self._current_webview = webview
        self.output.add_message(ConsoleMessage('info', 'Console conectado.'))
        
        # Interceptar console.log/warn/error da página web
        if webview:
            intercept_script = """
            (function() {
                if (window._reduxConsoleHooked) return;
                window._reduxConsoleHooked = true;
                var origLog = console.log;
                var origWarn = console.warn;
                var origError = console.error;
                var origInfo = console.info;
                
                function stringify(args) {
                    return Array.from(args).map(function(a) {
                        if (typeof a === 'object') {
                            try { return JSON.stringify(a, null, 2); }
                            catch(e) { return String(a); }
                        }
                        return String(a);
                    }).join(' ');
                }
                
                console.log = function() {
                    origLog.apply(console, arguments);
                    document.title = '::CONSOLE_LOG::' + stringify(arguments);
                };
                console.warn = function() {
                    origWarn.apply(console, arguments);
                    document.title = '::CONSOLE_WARN::' + stringify(arguments);
                };
                console.error = function() {
                    origError.apply(console, arguments);
                    document.title = '::CONSOLE_ERROR::' + stringify(arguments);
                };
                console.info = function() {
                    origInfo.apply(console, arguments);
                    document.title = '::CONSOLE_INFO::' + stringify(arguments);
                };
            })();
            """
            webview.page().runJavaScript(intercept_script)
            
            # Conectar ao titleChanged para capturar mensagens
            try:
                webview.page().titleChanged.connect(self._on_title_changed)
            except Exception:
                pass
    
    def _on_title_changed(self, title: str):
        """Captura mensagens de console interceptadas via titleChanged."""
        if title.startswith('::CONSOLE_LOG::'):
            self.output.add_message(ConsoleMessage('log', title[15:]))
        elif title.startswith('::CONSOLE_WARN::'):
            self.output.add_message(ConsoleMessage('warn', title[16:]))
        elif title.startswith('::CONSOLE_ERROR::'):
            self.output.add_message(ConsoleMessage('error', title[17:]))
        elif title.startswith('::CONSOLE_INFO::'):
            self.output.add_message(ConsoleMessage('info', title[16:]))
        
    def _on_command(self, text: str):
        """Executa um comando JavaScript no webview ativo."""
        self.output.add_message(ConsoleMessage('command', text))
        
        if not self._current_webview:
            self.output.add_message(ConsoleMessage('error', 'Nenhuma aba conectada ao console.'))
            return
        
        self._current_webview.page().runJavaScript(text, self._handle_result)
    
    @pyqtSlot(object)
    def _handle_result(self, result):
        """Exibe o resultado da execução do JS."""
        if result is None:
            self.output.add_message(ConsoleMessage('result', 'undefined'))
        elif isinstance(result, bool):
            self.output.add_message(ConsoleMessage('result', str(result).lower()))
        elif isinstance(result, (int, float)):
            self.output.add_message(ConsoleMessage('result', str(result)))
        elif isinstance(result, str):
            self.output.add_message(ConsoleMessage('result', result))
        elif isinstance(result, dict):
            self.output.add_message(ConsoleMessage('result', str(result)))
        elif isinstance(result, list):
            self.output.add_message(ConsoleMessage('result', f'[{len(result)} items]'))
        else:
            self.output.add_message(ConsoleMessage('result', str(result)))
    
    def add_log(self, text: str):
        self.output.add_message(ConsoleMessage('log', text))
    
    def add_error(self, text: str):
        self.output.add_message(ConsoleMessage('error', text))
    
    def add_warning(self, text: str):
        self.output.add_message(ConsoleMessage('warn', text))
    
    def add_info(self, text: str):
        self.output.add_message(ConsoleMessage('info', text))
    
    def _clear(self):
        self.output.clear()
