"""
Redux Browser — Custom URL Scheme Handler para extensões
Serve arquivos locais de extensões via redux-ext:// protocol.
"""

import mimetypes
from pathlib import Path
from PyQt6.QtCore import QUrl, QIODeviceBase
from PyQt6.QtWebEngineCore import QWebEngineUrlSchemeHandler, QWebEngineUrlScheme, QWebEngineUrlRequestJob


class ExtensionSchemeHandler(QWebEngineUrlSchemeHandler):
    """
    Handler para o esquema redux-ext:// que serve arquivos locais das extensões.
    URL: redux-ext://{ext_id}/path/to/file.css
    """
    
    SCHEME_NAME = b"redux-ext"
    
    def __init__(self, extensions_dir: Path, parent=None):
        super().__init__(parent)
        self.extensions_dir = extensions_dir
        self._registry = {}  # ext_id -> ext_dir mapping
        self._active_buffers = []  # prevent GC of buffers during request
    
    def register_extension(self, ext_id: str, ext_dir: Path):
        self._registry[ext_id] = ext_dir
    
    def unregister_extension(self, ext_id: str):
        self._registry.pop(ext_id, None)
    
    def requestStarted(self, request: QWebEngineUrlRequestJob):
        url = request.requestUrl()
        
        # URL format: redux-ext://ext_id/path/to/file
        host = url.host()  # ext_id
        path = url.path().lstrip('/')  # path/to/file
        
        if not host or not path:
            request.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return
        
        ext_dir = self._registry.get(host)
        if not ext_dir:
            ext_dir = self.extensions_dir / host
        
        file_path = ext_dir / path
        
        if not file_path.exists() or not file_path.is_file():
            request.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return
        
        # Security: prevent directory traversal
        try:
            file_path.resolve().relative_to(ext_dir.resolve())
        except ValueError:
            request.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
            return
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            mime_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
            
            buf = self._make_buffer(data, self)
            self._active_buffers.append(buf)
            buf.destroyed.connect(lambda: self._active_buffers.remove(buf) if buf in self._active_buffers else None)
            request.reply(mime_type.encode(), buf)
        except Exception as e:
            request.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
    
    @staticmethod
    def _make_buffer(data: bytes, parent=None):
        from PyQt6.QtCore import QBuffer, QByteArray
        buf = QBuffer(parent)
        buf.setData(QByteArray(data))
        buf.open(QIODeviceBase.OpenModeFlag.ReadOnly)
        return buf
    
    def get_url(self, ext_id: str, file_path: str) -> QUrl:
        """Generate a URL for an extension file."""
        return QUrl(f"redux-ext://{ext_id}/{file_path}")


def register_scheme():
    """Registra o esquema redux-ext:// no Chromium."""
    scheme = QWebEngineUrlScheme(ExtensionSchemeHandler.SCHEME_NAME)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.LocalScheme |
        QWebEngineUrlScheme.Flag.LocalAccessAllowed |
        QWebEngineUrlScheme.Flag.CorsEnabled |
        QWebEngineUrlScheme.Flag.FetchApiAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)
