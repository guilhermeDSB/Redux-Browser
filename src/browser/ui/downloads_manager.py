"""
Redux Browser — Gerenciador de Downloads
Gerencia arquivos baixados pelo navegador com tracking em tempo real.
"""

import os
import uuid
import json
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal


class DownloadState(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class DownloadItem:
    """Representa um download individual."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    filename: str = ""
    filepath: str = ""
    total_bytes: int = 0
    received_bytes: int = 0
    state: DownloadState = DownloadState.PENDING
    mime_type: str = ""
    speed: float = 0.0  # bytes/sec
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    error_string: str = ""
    
    @property
    def progress(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min(1.0, self.received_bytes / self.total_bytes)
    
    @property
    def is_finished(self) -> bool:
        return self.state in (DownloadState.COMPLETED, DownloadState.FAILED, DownloadState.CANCELLED)
    
    @property
    def status_text(self) -> str:
        if self.state == DownloadState.COMPLETED:
            return "Concluído"
        elif self.state == DownloadState.FAILED:
            return f"Falha: {self.error_string}"
        elif self.state == DownloadState.CANCELLED:
            return "Cancelado"
        elif self.state == DownloadState.PAUSED:
            return "Pausado"
        elif self.state == DownloadState.DOWNLOADING:
            if self.total_bytes > 0:
                received = self._format_size(self.received_bytes)
                total = self._format_size(self.total_bytes)
                speed = self._format_speed(self.speed)
                return f"{received} de {total} — {speed}"
            return f"{self._format_size(self.received_bytes)} baixados..."
        return "Pendente"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    @staticmethod
    def _format_speed(speed_bytes: float) -> str:
        if speed_bytes < 1024:
            return f"{speed_bytes:.0f} B/s"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes / 1024:.1f} KB/s"
        return f"{speed_bytes / (1024 * 1024):.1f} MB/s"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "filename": self.filename,
            "filepath": self.filepath,
            "total_bytes": self.total_bytes,
            "received_bytes": self.received_bytes,
            "state": self.state.value,
            "mime_type": self.mime_type,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "error_string": self.error_string
        }
    
    @staticmethod
    def from_dict(d: dict) -> 'DownloadItem':
        item = DownloadItem(
            id=d.get("id", str(uuid.uuid4())),
            url=d.get("url", ""),
            filename=d.get("filename", ""),
            filepath=d.get("filepath", ""),
            total_bytes=d.get("total_bytes", 0),
            received_bytes=d.get("received_bytes", 0),
            state=DownloadState(d.get("state", "pending")),
            mime_type=d.get("mime_type", ""),
            created_at=d.get("created_at", datetime.now().isoformat()),
            finished_at=d.get("finished_at"),
            error_string=d.get("error_string", "")
        )
        return item


class DownloadManager(QObject):
    """
    Gerenciador central de downloads do Redux Browser.
    Conecta-se ao signal downloadRequested do QWebEnginePage.
    """
    
    download_added = pyqtSignal(str)      # download_id
    download_updated = pyqtSignal(str)     # download_id
    download_finished = pyqtSignal(str)    # download_id
    download_removed = pyqtSignal(str)     # download_id
    
    STATE_FILE = os.path.expanduser("~/.redux_browser/downloads.json")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloads: Dict[str, DownloadItem] = {}
        self._active_qt_downloads = {}  # download_id -> QWebEngineDownloadItem
        self._load_state()
        
    @property
    def downloads_dir(self) -> str:
        d = os.path.expanduser("~/Downloads")
        os.makedirs(d, exist_ok=True)
        return d
    
    def get_all(self) -> List[DownloadItem]:
        return sorted(self._downloads.values(), 
                      key=lambda x: x.created_at, reverse=True)
    
    def get_active(self) -> List[DownloadItem]:
        return [d for d in self.get_all() if not d.is_finished]
    
    def get_completed(self) -> List[DownloadItem]:
        return [d for d in self.get_all() if d.state == DownloadState.COMPLETED]
    
    def get_download(self, download_id: str) -> Optional[DownloadItem]:
        return self._downloads.get(download_id)
    
    def start_download(self, q_webengine_download) -> DownloadItem:
        """Inicia um download a partir de QWebEngineDownloadRequest/QWebEngineDownloadItem."""
        filename = q_webengine_download.downloadFileName()
        url = q_webengine_download.url().toString()
        
        filepath = os.path.join(self.downloads_dir, filename)
        q_webengine_download.setDownloadDirectory(self.downloads_dir)
        q_webengine_download.accept()
        
        item = DownloadItem(
            id=str(uuid.uuid4()),
            url=url,
            filename=filename,
            filepath=filepath,
            state=DownloadState.DOWNLOADING,
            mime_type=q_webengine_download.mimeType()
        )
        
        self._downloads[item.id] = item
        self._active_qt_downloads[item.id] = q_webengine_download
        
        # Conectar sinais Qt
        q_webengine_download.downloadProgress.connect(
            lambda received, total: self._on_progress(item.id, received, total)
        )
        q_webengine_download.finished.connect(
            lambda: self._on_finished(item.id)
        )
        q_webengine_download.stateChanged.connect(
            lambda state: self._on_state_changed(item.id, state)
        )
        
        self.download_added.emit(item.id)
        self._save_state()
        return item
    
    def cancel_download(self, download_id: str):
        qt_dl = self._active_qt_downloads.get(download_id)
        if qt_dl:
            qt_dl.cancel()
        
        item = self._downloads.get(download_id)
        if item:
            item.state = DownloadState.CANCELLED
            self.download_updated.emit(download_id)
            self._save_state()
    
    def pause_download(self, download_id: str):
        qt_dl = self._active_qt_downloads.get(download_id)
        if qt_dl:
            qt_dl.pause()
        
        item = self._downloads.get(download_id)
        if item:
            item.state = DownloadState.PAUSED
            self.download_updated.emit(download_id)
    
    def resume_download(self, download_id: str):
        qt_dl = self._active_qt_downloads.get(download_id)
        if qt_dl:
            qt_dl.resume()
        
        item = self._downloads.get(download_id)
        if item:
            item.state = DownloadState.DOWNLOADING
            self.download_updated.emit(download_id)
    
    def remove_download(self, download_id: str):
        if download_id in self._downloads:
            del self._downloads[download_id]
        if download_id in self._active_qt_downloads:
            del self._active_qt_downloads[download_id]
        self.download_removed.emit(download_id)
        self._save_state()
    
    def open_file(self, download_id: str):
        item = self._downloads.get(download_id)
        if item and os.path.exists(item.filepath):
            import subprocess
            if os.name == 'nt':
                os.startfile(item.filepath)
            else:
                subprocess.Popen(['xdg-open', item.filepath])
    
    def open_folder(self, download_id: str):
        item = self._downloads.get(download_id)
        if item and os.path.exists(item.filepath):
            folder = os.path.dirname(item.filepath)
            import subprocess
            if os.name == 'nt':
                os.startfile(folder)
            else:
                subprocess.Popen(['xdg-open', folder])
    
    def clear_completed(self):
        to_remove = [did for did, dl in self._downloads.items() if dl.is_finished]
        for did in to_remove:
            self.remove_download(did)
    
    def _on_progress(self, download_id: str, received: int, total: int):
        item = self._downloads.get(download_id)
        if item:
            import time
            item.received_bytes = received
            item.total_bytes = total
            self.download_updated.emit(download_id)
    
    def _on_state_changed(self, download_id: str, state):
        from PyQt6.QtWebEngineCore import QWebEngineDownloadItem
        item = self._downloads.get(download_id)
        if not item:
            return
        
        state_map = {
            QWebEngineDownloadItem.DownloadState.DownloadInProgress: DownloadState.DOWNLOADING,
            QWebEngineDownloadItem.DownloadState.DownloadCompleted: DownloadState.COMPLETED,
            QWebEngineDownloadItem.DownloadState.DownloadCancelled: DownloadState.CANCELLED,
            QWebEngineDownloadItem.DownloadState.DownloadInterrupted: DownloadState.FAILED,
        }
        item.state = state_map.get(state, DownloadState.DOWNLOADING)
        self.download_updated.emit(download_id)
    
    def _on_finished(self, download_id: str):
        item = self._downloads.get(download_id)
        if item:
            item.finished_at = datetime.now().isoformat()
            if item.state != DownloadState.CANCELLED:
                item.state = DownloadState.COMPLETED
            self.download_finished.emit(download_id)
            self._save_state()
        
        if download_id in self._active_qt_downloads:
            del self._active_qt_downloads[download_id]
    
    def _save_state(self):
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        try:
            data = [d.to_dict() for d in self._downloads.values() if d.is_finished]
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _load_state(self):
        if not os.path.exists(self.STATE_FILE):
            return
        try:
            with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for d in data:
                    item = DownloadItem.from_dict(d)
                    self._downloads[item.id] = item
        except Exception:
            pass
