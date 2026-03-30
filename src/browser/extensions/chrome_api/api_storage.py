"""
Redux Browser — Implementação de chrome.storage
Armazena dados de extensões em JSON local.
Suporta storage.local, storage.sync e storage.session.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

class ChromeStorageAPI:
    
    STORAGE_DIR = Path.home() / ".redux_browser" / "extension_storage"
    
    def __init__(self, extension_id: str):
        self.extension_id = extension_id
        self.base_path = self.STORAGE_DIR / extension_id
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, area: str, keys: Any = None) -> Dict:
        """Lê dados do storage."""
        data = self._load_area(area)
        if keys is None:
            return data
        if isinstance(keys, str):
            return {keys: data.get(keys)}
        if isinstance(keys, list):
            return {k: data.get(k) for k in keys if k in data}
        if isinstance(keys, dict):
            return {k: data.get(k, v) for k, v in keys.items()}
        return {}
    
    def set(self, area: str, items: Dict) -> None:
        """Salva dados no storage."""
        data = self._load_area(area)
        data.update(items)
        self._save_area(area, data)
    
    def remove(self, area: str, keys: list) -> None:
        """Remove chaves do storage."""
        data = self._load_area(area)
        for k in keys:
            data.pop(k, None)
        self._save_area(area, data)
    
    def clear(self, area: str) -> None:
        """Limpa todo o storage de uma área."""
        self._save_area(area, {})
    
    def _load_area(self, area: str) -> Dict:
        """Carrega dados de uma área do storage."""
        # Sessions são mantidas em memória (não implementado full bridge via QtMessage),
        # local e sync salvam no mesmo local pois sync é mockado.
        file_path = self.base_path / f"{area}.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_area(self, area: str, data: Dict) -> None:
        """Salva dados de uma área do storage."""
        file_path = self.base_path / f"{area}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except:
            pass
