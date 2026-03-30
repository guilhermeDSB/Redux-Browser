"""
Redux Browser — Gerenciador de Extensões
Controle central: instalar, remover, habilitar, desabilitar extensões.
Persiste estado em ~/.redux_browser/extensions/
"""

from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
import json
import shutil
import re
import urllib.request
from typing import Dict, List, Optional

from .extension_model import Extension, ExtensionState
from .manifest_parser import ManifestParser
from .crx_parser import CRXParser

class ExtensionManager(QObject):
    
    # Sinais Qt para UI
    extension_installed = pyqtSignal(str)    # extension_id
    extension_removed = pyqtSignal(str)      # extension_id
    extension_enabled = pyqtSignal(str)      # extension_id
    extension_disabled = pyqtSignal(str)     # extension_id
    extension_error = pyqtSignal(str, str)   # extension_id, error_msg
    extension_pinned = pyqtSignal(str)       # extension_id
    
    EXTENSIONS_DIR = Path.home() / ".redux_browser" / "extensions"
    STATE_FILE = Path.home() / ".redux_browser" / "extensions_state.json"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._extensions: Dict[str, Extension] = {}
        self._manifest_parser = ManifestParser()
        self._crx_parser = CRXParser()
        self.EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_installed_extensions()
    
    def install_from_crx(self, crx_path: Path) -> Extension:
        """Instala extensão a partir de arquivo .crx ou zip renomeado."""
        if not crx_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {crx_path}")
            
        temp_dir = self.EXTENSIONS_DIR / "_temp_install"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            
        try:
            self._crx_parser.extract(crx_path, temp_dir)
            ext = self._install_from_unpacked(temp_dir)
            self.extension_installed.emit(ext.id)
            return ext
        except Exception as e:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise e
    
    def install_from_folder(self, folder_path: Path) -> Extension:
        """Instala extensão carregada de forma descompactada."""
        ext = self._install_from_unpacked(folder_path, copy_files=False)
        self.extension_installed.emit(ext.id)
        return ext
        
    def _install_from_unpacked(self, folder_path: Path, copy_files: bool = True) -> Extension:
        manifest_path = folder_path / "manifest.json"
        
        try:
            ext = self._manifest_parser.parse(manifest_path)
            warnings = self._manifest_parser.validate(ext)
            if warnings:
                print(f"[ExtManager] Warnings em {ext.name}: {warnings}")
                
            dest_dir = self.EXTENSIONS_DIR / ext.id
            if copy_files:
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(folder_path, dest_dir)
                ext.path = dest_dir
                shutil.rmtree(folder_path) # Limpa temp
            
            ext.state = ExtensionState.ENABLED
            self._extensions[ext.id] = ext
            self._save_state()
            return ext
            
        except Exception as e:
            raise RuntimeError(f"Falha ao carregar extensão: {e}")
            
    def install_from_url(self, url: str) -> Extension:
        """Baixa de url CRX e instala."""
        # A API para baixar extensões Chrome envolve queries específicas (x-chrome-extension)
        # Por simplicidade, assumindo URL direta ao .crx
        try:
            temp_crx = self.EXTENSIONS_DIR / "temp_download.crx"
            urllib.request.urlretrieve(url, str(temp_crx))
            ext = self.install_from_crx(temp_crx)
            temp_crx.unlink()
            return ext
        except Exception as e:
            raise RuntimeError(f"Erro no download ou instalação: {e}")
    
    def uninstall(self, extension_id: str) -> bool:
        """Remove extensão completamente."""
        if extension_id not in self._extensions: return False
        
        ext = self._extensions[extension_id]
        
        # Só deletar se estiver gerenciada pelo diretório interno do redux (pra não deletar dev folders de fora)
        if ext.path and ext.path.is_relative_to(self.EXTENSIONS_DIR):
            try:
                shutil.rmtree(ext.path)
            except:
                pass
                
        del self._extensions[extension_id]
        self._save_state()
        self.extension_removed.emit(extension_id)
        return True
    
    def enable(self, extension_id: str) -> bool:
        if extension_id not in self._extensions: return False
        self._extensions[extension_id].state = ExtensionState.ENABLED
        self._save_state()
        self.extension_enabled.emit(extension_id)
        return True
    
    def disable(self, extension_id: str) -> bool:
        if extension_id not in self._extensions: return False
        self._extensions[extension_id].state = ExtensionState.DISABLED
        self._save_state()
        self.extension_disabled.emit(extension_id)
        return True
    
    def toggle_pinned(self, extension_id: str) -> bool:
        """Alterna se a extensão está fixada na toolbar."""
        if extension_id not in self._extensions: return False
        self._extensions[extension_id].pinned = not self._extensions[extension_id].pinned
        self._save_state()
        self.extension_pinned.emit(extension_id)
        return self._extensions[extension_id].pinned
    
    def get_pinned_extensions(self) -> List[Extension]:
        """Retorna extensões habilitadas e fixadas na toolbar."""
        return [e for e in self._extensions.values() 
                if e.state == ExtensionState.ENABLED and e.pinned and e.action]
    
    def get_extension(self, ext_id: str) -> Optional[Extension]:
        return self._extensions.get(ext_id)
    
    def get_all_extensions(self) -> List[Extension]:
        return list(self._extensions.values())
    
    def get_enabled_extensions(self) -> List[Extension]:
        return [e for e in self._extensions.values() if e.state == ExtensionState.ENABLED]
    
    def get_content_scripts_for_url(self, url: str) -> List[dict]:
        """
        Retorna dicionários de script configurados para injetar.
        """
        scripts_to_inject = []
        for ext in self.get_enabled_extensions():
            for cs in ext.content_scripts:
                matched = False
                for match in cs.matches:
                    if self._match_url_pattern(match, url):
                        matched = True
                        break
                        
                # Check excludes
                if matched:
                    for exclude in cs.exclude_matches:
                        if self._match_url_pattern(exclude, url):
                            matched = False
                            break
                            
                if matched:
                    for js_file in cs.js:
                        scripts_to_inject.append({
                            'extension_id': ext.id,
                            'ext_path': ext.path,
                            'file': js_file,
                            'type': 'js',
                            'run_at': cs.run_at,
                            'all_frames': cs.all_frames
                        })
                    for css_file in cs.css:
                        scripts_to_inject.append({
                            'extension_id': ext.id,
                            'ext_path': ext.path,
                            'file': css_file,
                            'type': 'css',
                            'run_at': cs.run_at,
                            'all_frames': cs.all_frames
                        })
                        
        return scripts_to_inject
    
    def reload_extension(self, extension_id: str) -> bool:
        ext = self._extensions.get(extension_id)
        if not ext: return False
        path = ext.path
        if not path: return False
        
        self.uninstall(extension_id)
        self.install_from_folder(path) # Re-read
        return True
    
    def _match_url_pattern(self, pattern: str, url: str) -> bool:
        if pattern == "<all_urls>": return True
        # Simplifica matching converting wildcards p/ regex
        pattern = pattern.replace('://', '://_SPLIT_')
        parts = pattern.split('://_SPLIT_')
        if len(parts) != 2: return False
        
        scheme_pat = parts[0].replace('*', '.*')
        host_path_pat = parts[1].replace('*', '.*').replace('?', '.')
        regex_pattern = f"^{scheme_pat}://{host_path_pat}$"
        
        return re.match(regex_pattern, url) is not None
    
    def _load_installed_extensions(self):
        state = self._load_state()
        
        for folder in self.EXTENSIONS_DIR.iterdir():
            if folder.is_dir():
                manifest = folder / "manifest.json"
                if manifest.exists():
                    try:
                        ext = self._manifest_parser.parse(manifest)
                        
                        # Resgatar estado salvo
                        saved_state = state.get(ext.id, {})
                        ext.state = ExtensionState(saved_state.get('state', 'enabled'))
                        
                        self._extensions[ext.id] = ext
                    except Exception as e:
                        print(f"[ExtManager] Erro carregando {folder}: {e}")
    
    def _save_state(self):
        state = {}
        for ext in self._extensions.values():
            state[ext.id] = {
                "state": ext.state.value,
                "version": ext.version
            }
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
            
    def _load_state(self) -> dict:
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
