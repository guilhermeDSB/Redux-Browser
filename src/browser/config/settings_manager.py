"""
Redux Browser — Gerenciador de Preferências Persistidas
Salva e restaura configurações do usuário (tema, motor de busca, farbling, zoom, etc.)
"""

import json
import os
from typing import Any, Optional


class SettingsManager:
    """
    Gerenciador centralizado de configurações do Redux Browser.
    Persiste preferências do usuário em ~/.redux_browser/preferences.json.
    """
    
    # Valores padrão
    DEFAULTS = {
        "theme": "dark",
        "search_engine": "DuckDuckGo",
        "farbling_level": "balanced",
        "bookmarks_bar_visible": False,
        "default_zoom": 1.0,
        "home_page": "about:home",
        "download_path": "",
        "last_window_width": 1280,
        "last_window_height": 800,
        "adblock_enabled": True,
        "adblock_level": "standard",
        "adblock_whitelist": [],
        "adblock_custom_filters": "",
        "adblock_lists": {},
        "onboarding_completed": False,
    }
    
    def __init__(self, settings_path: str = "~/.redux_browser/preferences.json"):
        self.settings_path = os.path.expanduser(settings_path)
        self._settings: dict = dict(self.DEFAULTS)
        self._load()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retorna o valor de uma configuração."""
        if default is not None:
            return self._settings.get(key, default)
        return self._settings.get(key, self.DEFAULTS.get(key))
    
    def set(self, key: str, value: Any):
        """Define e salva uma configuração."""
        self._settings[key] = value
        self._save()
    
    def get_all(self) -> dict:
        """Retorna todas as configurações."""
        return dict(self._settings)
    
    def reset(self):
        """Restaura todas as configurações para os padrões."""
        self._settings = dict(self.DEFAULTS)
        self._save()
    
    def _save(self):
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Erro ao salvar preferências: {e}")
    
    def _load(self):
        if not os.path.exists(self.settings_path):
            return
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Mesclar com defaults para garantir que novas keys existam
                for key, value in data.items():
                    self._settings[key] = value
        except Exception as e:
            print(f"[Settings] Erro ao carregar preferências: {e}")


# Instância global (singleton)
_instance: Optional[SettingsManager] = None

def get_settings() -> SettingsManager:
    """Retorna a instância global do SettingsManager."""
    global _instance
    if _instance is None:
        _instance = SettingsManager()
    return _instance
