"""
Redux Browser — Sistema de Auto-Update
Verifica atualizações via GitHub Releases, baixa e instala automaticamente.
"""

import os
import sys
import json
import hashlib
import tempfile
import subprocess
from typing import Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QWidget, QGraphicsDropShadowEffect, QMessageBox
)
from PyQt6.QtGui import QColor

import requests

from browser.__version__ import APP_VERSION, UPDATE_CHECK_URL, APP_NAME
from browser.ui.theme import Theme


# ---------------------------------------------------------------------------
# Comparação de versões (sem dependência externa)
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> Tuple[int, ...]:
    """Converte '1.2.3' em (1, 2, 3) para comparação."""
    v = v.lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_newer(remote: str, local: str = APP_VERSION) -> bool:
    """Retorna True se *remote* é mais recente que *local*."""
    return _parse_version(remote) > _parse_version(local)


# ---------------------------------------------------------------------------
# Worker thread — verifica & baixa em segundo plano
# ---------------------------------------------------------------------------

class UpdateCheckWorker(QThread):
    """Thread que verifica se há atualização no GitHub Releases."""

    # Sinais: (version, download_url, release_notes, sha256)
    update_available = pyqtSignal(str, str, str, str)
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            resp = requests.get(UPDATE_CHECK_URL, timeout=10, headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            })
            if resp.status_code != 200:
                self.no_update.emit()
                return

            data = resp.json()
            tag = data.get("tag_name", "")
            remote_version = tag.lstrip("vV")

            if not is_newer(remote_version):
                self.no_update.emit()
                return

            # Procura o asset do instalador (.exe)
            download_url = ""
            sha256 = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "").lower()
                if name.endswith("_setup.exe") or name.endswith("_installer.exe") or (name.endswith(".exe") and "setup" in name):
                    download_url = asset.get("browser_download_url", "")
                elif name == "sha256.txt":
                    # Baixa o hash de verificação
                    try:
                        sha_resp = requests.get(asset["browser_download_url"], timeout=10)
                        sha256 = sha_resp.text.strip().split()[0]
                    except Exception:
                        pass

            if not download_url:
                # Fallback: primeiro .exe nos assets
                for asset in data.get("assets", []):
                    if asset.get("name", "").lower().endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

            if not download_url:
                self.no_update.emit()
                return

            notes = data.get("body", "") or ""
            self.update_available.emit(remote_version, download_url, notes, sha256)

        except requests.RequestException:
            self.error.emit("Não foi possível verificar atualizações.")
        except Exception as e:
            self.error.emit(str(e))


class DownloadWorker(QThread):
    """Thread que baixa o instalador com progresso."""

    progress = pyqtSignal(int, int)   # (bytes_downloaded, total_bytes)
    finished = pyqtSignal(str)         # caminho do arquivo baixado
    error = pyqtSignal(str)

    def __init__(self, url: str, sha256: str = "", parent=None):
        super().__init__(parent)
        self.url = url
        self.expected_sha256 = sha256

    def run(self):
        try:
            tmp_dir = os.path.join(tempfile.gettempdir(), "redux_update")
            os.makedirs(tmp_dir, exist_ok=True)

            filename = self.url.rsplit("/", 1)[-1] or "ReduxBrowser_Setup.exe"
            filepath = os.path.join(tmp_dir, filename)

            resp = requests.get(self.url, stream=True, timeout=60, headers={
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            })
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            sha = hashlib.sha256()

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
                        sha.update(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)

            # Verifica integridade
            if self.expected_sha256:
                actual = sha.hexdigest()
                if actual.lower() != self.expected_sha256.lower():
                    os.remove(filepath)
                    self.error.emit("Verificação de integridade falhou (SHA-256 inválido).")
                    return

            self.finished.emit(filepath)

        except requests.RequestException as e:
            self.error.emit(f"Erro no download: {e}")
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# UI — Dialog de atualização
# ---------------------------------------------------------------------------

class UpdateDialog(QDialog):
    """Dialog que mostra info da atualização e permite baixar/instalar."""

    def __init__(self, version: str, download_url: str, notes: str,
                 sha256: str = "", parent=None):
        super().__init__(parent)
        self.version = version
        self.download_url = download_url
        self.notes = notes
        self.sha256 = sha256
        self._download_worker: Optional[DownloadWorker] = None
        self._downloaded_path: Optional[str] = None

        current_theme = getattr(parent, 'current_theme', 'dark') if parent else 'dark'
        self._theme = current_theme
        self._setup_ui()

    def _setup_ui(self):
        p = Theme.DARK if self._theme == "dark" else Theme.LIGHT

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        container = QWidget(self)
        container.setObjectName("updateContainer")
        container.setStyleSheet(f"""
            QWidget#updateContainer {{
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

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        title = QLabel("🔄 Atualização Disponível")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {p['text_primary']};")
        layout.addWidget(title)

        # Versão
        ver_label = QLabel(f"Versão atual: <b>{APP_VERSION}</b>  →  Nova versão: <b>{self.version}</b>")
        ver_label.setStyleSheet(f"font-size: 13px; color: {p['text_secondary']};")
        layout.addWidget(ver_label)

        # Notas de release (até 500 chars)
        if self.notes:
            notes_text = self.notes[:500] + ("..." if len(self.notes) > 500 else "")
            notes_label = QLabel(notes_text)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet(f"""
                color: {p['text_secondary']};
                font-size: 12px;
                background: {p['bg_secondary']};
                border-radius: 8px;
                padding: 12px;
            """)
            layout.addWidget(notes_label)

        # Barra de progresso (oculta inicialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {p['bg_tertiary']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {p['accent']};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {p['text_tertiary']};")
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Botões
        btn_layout = QHBoxLayout()

        self.btn_later = QPushButton("Mais Tarde")
        self.btn_later.setStyleSheet(f"""
            QPushButton {{
                background: {p['bg_secondary']};
                color: {p['text_primary']};
                border: 1px solid {p['border']};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {p['bg_tertiary']}; }}
        """)
        self.btn_later.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_later)

        btn_layout.addStretch()

        self.btn_update = QPushButton("Baixar e Instalar")
        self.btn_update.setStyleSheet(f"""
            QPushButton {{
                background: {p['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {p['accent_hover']}; }}
        """)
        self.btn_update.clicked.connect(self._start_download)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

        self.resize(480, 320)
        self._drag_pos = None

    # -- Drag support --
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

    # -- Download & Install --
    def _start_download(self):
        self.btn_update.setEnabled(False)
        self.btn_update.setText("Baixando...")
        self.progress_bar.show()
        self.status_label.show()
        self.status_label.setText("Iniciando download...")

        self._download_worker = DownloadWorker(self.download_url, self.sha256, self)
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int(downloaded * 100 / total)
            self.progress_bar.setValue(pct)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(f"Baixando... {mb_done:.1f} MB / {mb_total:.1f} MB ({pct}%)")
        else:
            mb_done = downloaded / (1024 * 1024)
            self.status_label.setText(f"Baixando... {mb_done:.1f} MB")

    def _on_download_finished(self, filepath: str):
        self._downloaded_path = filepath
        self.progress_bar.setValue(100)
        self.status_label.setText("Download concluído! Iniciando instalação...")
        self.btn_update.setText("Instalar Agora")
        self.btn_update.setEnabled(True)
        self.btn_update.clicked.disconnect()
        self.btn_update.clicked.connect(self._install_update)
        # Auto-instalar após 2 segundos
        QTimer.singleShot(2000, self._install_update)

    def _on_download_error(self, error_msg: str):
        self.status_label.setText(f"❌ {error_msg}")
        self.status_label.setStyleSheet("font-size: 12px; color: #FF6B6B;")
        self.btn_update.setText("Tentar Novamente")
        self.btn_update.setEnabled(True)
        self.btn_update.clicked.disconnect()
        self.btn_update.clicked.connect(self._start_download)

    def _install_update(self):
        if not self._downloaded_path or not os.path.exists(self._downloaded_path):
            self.status_label.setText("❌ Arquivo de instalação não encontrado.")
            return

        self.status_label.setText("Iniciando instalador...")

        try:
            # Executa o instalador Inno Setup em modo silencioso
            subprocess.Popen(
                [self._downloaded_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/RESTARTAPPLICATIONS"],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
            # Fecha o browser para permitir a atualização
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            self.status_label.setText(f"❌ Não foi possível iniciar o instalador: {e}")


# ---------------------------------------------------------------------------
# Gerenciador de updates — API principal
# ---------------------------------------------------------------------------

class UpdateManager:
    """
    Gerencia verificação e instalação de atualizações.
    
    Uso:
        updater = UpdateManager(parent_window)
        updater.check_for_updates()          # silencioso (startup)
        updater.check_for_updates(silent=False)  # manual (menu)
    """

    def __init__(self, parent=None):
        self.parent = parent
        self._check_worker: Optional[UpdateCheckWorker] = None
        self._silent = True

    def check_for_updates(self, silent: bool = True):
        """
        Verifica atualizações no GitHub Releases.
        
        Args:
            silent: Se True, não mostra nada se não houver update.
                    Se False, mostra mensagem mesmo se estiver na versão mais recente.
        """
        self._silent = silent
        self._check_worker = UpdateCheckWorker()
        self._check_worker.update_available.connect(self._on_update_available)
        self._check_worker.no_update.connect(self._on_no_update)
        self._check_worker.error.connect(self._on_error)
        self._check_worker.start()

    def _on_update_available(self, version: str, url: str, notes: str, sha256: str):
        dialog = UpdateDialog(version, url, notes, sha256, parent=self.parent)
        dialog.exec()

    def _on_no_update(self):
        if not self._silent:
            QMessageBox.information(
                self.parent,
                "Sem Atualizações",
                f"Você já está na versão mais recente ({APP_VERSION})."
            )

    def _on_error(self, msg: str):
        if not self._silent:
            QMessageBox.warning(
                self.parent,
                "Erro ao Verificar Atualizações",
                msg
            )

    def schedule_startup_check(self, delay_ms: int = 8000):
        """Agenda verificação silenciosa após o startup."""
        QTimer.singleShot(delay_ms, lambda: self.check_for_updates(silent=True))
