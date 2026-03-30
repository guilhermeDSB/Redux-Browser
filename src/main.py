import sys
import os

# Detecta se está rodando como .exe empacotado (PyInstaller)
if getattr(sys, 'frozen', False):
    # PyInstaller onedir: sys._MEIPASS é o diretório do bundle
    _base_path = sys._MEIPASS
else:
    _base_path = os.path.dirname(os.path.abspath(__file__))

# Garante que o diretório base está no path para imports funcionarem
sys.path.insert(0, _base_path)

# MUST register custom URL scheme BEFORE QApplication is created
from browser.extensions.ext_url_handler import register_scheme
register_scheme()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineCore import QWebEngineProfile
from browser.ui.main_window import MainWindow
from browser.extensions.ext_url_handler import ExtensionSchemeHandler
from browser.__version__ import APP_NAME, APP_VERSION, APP_AUTHOR
from pathlib import Path

def main():
    """
    Ponto de entrada principal do navegador.
    Inicializa o loop de eventos Qt e exibe a janela.
    """
    import traceback
    import atexit
    
    # Diretório de dados do usuário
    _user_data_dir = os.path.expanduser("~/.redux_browser")
    os.makedirs(_user_data_dir, exist_ok=True)
    _crash_log = os.path.join(_user_data_dir, "crash.log")

    def _except_hook(exc_type, exc_value, exc_tb):
        """Salva crashes em ~/.redux_browser/crash.log e chama o handler original."""
        try:
            with open(_crash_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    
    sys.excepthook = _except_hook
    
    # Limpa arquivos temporários do Redux Browser ao sair
    def _cleanup_temp_files():
        import tempfile, shutil
        tmp_dir = os.path.join(tempfile.gettempdir(), "redux_browser")
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
    atexit.register(_cleanup_temp_files)
    
    # Inicializa a aplicação Qt
    app = QApplication(sys.argv)
    
    # Metadados da aplicação (centralizados em __version__.py)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)
    
    # Register custom URL scheme handler for extensions
    extensions_dir = Path(os.path.expanduser("~/.redux_browser/extensions"))
    ext_handler = ExtensionSchemeHandler(extensions_dir)
    profile = QWebEngineProfile.defaultProfile()
    profile.installUrlSchemeHandler(b"redux-ext", ext_handler)
    
    # Cria e exibe a janela principal
    window = MainWindow()
    window._ext_scheme_handler = ext_handler  # keep reference
    window.show()
    
    # Inicia o loop de eventos
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
