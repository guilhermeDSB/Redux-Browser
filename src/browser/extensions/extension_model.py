"""
Redux Browser — Modelo de dados de uma extensão Chrome.
Representa uma extensão carregada com todos seus metadados.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path
import json


class ManifestVersion(Enum):
    V2 = 2
    V3 = 3


class ExtensionState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    INSTALLING = "installing"


@dataclass
class ContentScript:
    """Definição de um content script."""
    matches: List[str]          # ["*://*.google.com/*", "<all_urls>"]
    js: List[str] = field(default_factory=list)       # ["content.js"]
    css: List[str] = field(default_factory=list)      # ["style.css"]
    run_at: str = "document_idle"    # document_start, document_end, document_idle
    all_frames: bool = False
    exclude_matches: List[str] = field(default_factory=list)
    match_about_blank: bool = False

    def to_dict(self):
        return {
            "matches": self.matches,
            "js": self.js,
            "css": self.css,
            "run_at": self.run_at,
            "all_frames": self.all_frames,
            "exclude_matches": self.exclude_matches,
            "match_about_blank": self.match_about_blank
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            matches=data.get("matches", []),
            js=data.get("js", []),
            css=data.get("css", []),
            run_at=data.get("run_at", "document_idle"),
            all_frames=data.get("all_frames", False),
            exclude_matches=data.get("exclude_matches", []),
            match_about_blank=data.get("match_about_blank", False)
        )


@dataclass
class ActionConfig:
    """Configuração do ícone na toolbar (browser_action/action)."""
    default_popup: Optional[str] = None     # "popup.html"
    default_icon: Optional[Dict[str, str]] = None  # {"16": "icon16.png", ...}
    default_title: Optional[str] = None     # Tooltip
    
    def to_dict(self):
        return {
            "default_popup": self.default_popup,
            "default_icon": self.default_icon,
            "default_title": self.default_title
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            default_popup=data.get("default_popup"),
            default_icon=data.get("default_icon"),
            default_title=data.get("default_title")
        )


@dataclass
class Permission:
    """Permissão solicitada pela extensão."""
    name: str           # "storage", "tabs", "activeTab", etc.
    granted: bool = False
    optional: bool = False
    
    def to_dict(self):
        return {"name": self.name, "granted": self.granted, "optional": self.optional}
        
    @classmethod
    def from_dict(cls, data: dict):
        return cls(name=data["name"], granted=data.get("granted", False), optional=data.get("optional", False))


@dataclass
class Extension:
    """
    Representa uma extensão Chrome completa.
    Contém todos os metadados parseados do manifest.json.
    """
    # Identificação
    id: str                              # Hash único ou ID da Chrome Web Store
    name: str                            # "uBlock Origin"
    version: str                         # "1.56.0"
    description: str = ""                # "Bloqueador de anúncios eficiente"
    manifest_version: ManifestVersion = ManifestVersion.V3
    
    # Caminhos
    path: Path = None                    # Diretório raiz da extensão
    
    # Estado
    state: ExtensionState = ExtensionState.DISABLED
    error_message: Optional[str] = None
    pinned: bool = False  # Se está fixado na toolbar
    
    # Metadados
    author: str = ""
    homepage_url: str = ""
    icons: Dict[str, str] = field(default_factory=dict)  # {"16": "icon16.png", ...}
    
    # Funcionalidade
    content_scripts: List[ContentScript] = field(default_factory=list)
    background: Optional[Dict[str, Any]] = None   # {"service_worker": "bg.js"}
    action: Optional[ActionConfig] = None
    options_page: Optional[str] = None             # "options.html"
    options_ui: Optional[Dict[str, Any]] = None
    
    # Permissões
    permissions: List[Permission] = field(default_factory=list)
    host_permissions: List[str] = field(default_factory=list)
    optional_permissions: List[Permission] = field(default_factory=list)
    
    # Web Accessible Resources
    web_accessible_resources: List[Dict] = field(default_factory=list)
    
    # Dados internos do Redux Browser
    storage_data: Dict[str, Any] = field(default_factory=dict)

    def get_icon_path(self, size: int = 32) -> Optional[Path]:
        """Retorna o caminho do ícone mais próximo do tamanho solicitado."""
        if not self.icons:
            return None
        sizes = sorted(self.icons.keys(), key=lambda x: abs(int(x) - size))
        if sizes:
            return self.path / self.icons[sizes[0]]
        return None

    def has_permission(self, perm_name: str) -> bool:
        """Verifica se a extensão tem uma permissão específica."""
        return any(p.name == perm_name and p.granted for p in self.permissions)

    def to_dict(self) -> dict:
        """Serializa para salvar estado."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "manifest_version": self.manifest_version.value,
            "path": str(self.path) if self.path else None,
            "state": self.state.value,
            "error_message": self.error_message,
            "pinned": self.pinned,
            "author": self.author,
            "homepage_url": self.homepage_url,
            "icons": self.icons,
            "content_scripts": [cs.to_dict() for cs in self.content_scripts],
            "background": self.background,
            "action": self.action.to_dict() if self.action else None,
            "options_page": self.options_page,
            "options_ui": self.options_ui,
            "permissions": [p.to_dict() for p in self.permissions],
            "host_permissions": self.host_permissions,
            "optional_permissions": [p.to_dict() for p in self.optional_permissions],
            "web_accessible_resources": self.web_accessible_resources
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Extension':
        """Desserializa estado salvo."""
        ext = cls(
            id=data["id"],
            name=data["name"],
            version=data["version"]
        )
        ext.description = data.get("description", "")
        ext.manifest_version = ManifestVersion(data.get("manifest_version", 3))
        
        path_str = data.get("path")
        ext.path = Path(path_str) if path_str else None
        
        state_str = data.get("state", "disabled")
        try:
            ext.state = ExtensionState(state_str)
        except ValueError:
            ext.state = ExtensionState.DISABLED
            
        ext.error_message = data.get("error_message")
        ext.pinned = data.get("pinned", False)
        ext.author = data.get("author", "")
        ext.homepage_url = data.get("homepage_url", "")
        ext.icons = data.get("icons", {})
        
        ext.content_scripts = [ContentScript.from_dict(cs) for cs in data.get("content_scripts", [])]
        ext.background = data.get("background")
        
        action_data = data.get("action")
        ext.action = ActionConfig.from_dict(action_data) if action_data else None
        
        ext.options_page = data.get("options_page")
        ext.options_ui = data.get("options_ui")
        
        ext.permissions = [Permission.from_dict(p) for p in data.get("permissions", [])]
        ext.host_permissions = data.get("host_permissions", [])
        ext.optional_permissions = [Permission.from_dict(p) for p in data.get("optional_permissions", [])]
        ext.web_accessible_resources = data.get("web_accessible_resources", [])
        
        return ext
