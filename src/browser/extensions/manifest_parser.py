"""
Redux Browser — Parser de manifest.json (Manifest V2 e V3)
Lê o manifest.json de uma extensão Chrome e cria um objeto Extension.
Resolve mensagens i18n (__MSG_extName__) do _locales.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from .extension_model import Extension, ManifestVersion, ContentScript, ActionConfig, Permission

class ManifestParser:
    REQUIRED_FIELDS = ["name", "version", "manifest_version"]
    
    SUPPORTED_PERMISSIONS = [
        "activeTab", "alarms", "bookmarks", "browsingData",
        "clipboardRead", "clipboardWrite", "contextMenus",
        "cookies", "downloads", "history", "notifications",
        "scripting", "storage", "tabs", "webNavigation",
        "webRequest", "declarativeNetRequest"
    ]
    
    # Pattern for i18n messages: __MSG_key__
    I18N_PATTERN = re.compile(r'^__MSG_(\w+)__$')
    
    def parse(self, manifest_path: Path) -> Extension:
        """
        Lê e parseia o manifest.json, retornando um objeto Extension.
        Converte Manifest V2 para V3 internamente.
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json não encontrado em {manifest_path}")
        
        ext_dir = manifest_path.parent
            
        with open(manifest_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError("manifest.json contém JSON inválido.")
        
        # Load i18n messages
        i18n_messages = self._load_i18n_messages(ext_dir, data.get("default_locale", "en"))
        
        # Valida campos requeridos
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(f"Campo obrigatório faltando no manifest.json: {field}")
        
        # Resolve i18n in name and description
        raw_name = data["name"]
        raw_description = data.get("description", "")
        resolved_name = self._resolve_i18n(raw_name, i18n_messages)
        resolved_description = self._resolve_i18n(raw_description, i18n_messages)
                
        ext = Extension(
            id=data.get("key", self._generate_extension_id(ext_dir)),
            name=resolved_name,
            version=data["version"]
        )
        ext.path = ext_dir
        ext.description = resolved_description
        ext.author = data.get("author", "")
        ext.homepage_url = data.get("homepage_url", "")
        
        ext.manifest_version = ManifestVersion.V2 if data["manifest_version"] == 2 else ManifestVersion.V3
        
        ext.icons = data.get("icons", {})
        
        ext.content_scripts = self._parse_content_scripts(data.get("content_scripts", []))
        
        # Converte actions V2 -> V3
        if "action" in data:
            ext.action = self._parse_action(data["action"], 3, i18n_messages)
        elif "browser_action" in data:
            ext.action = self._parse_action(data["browser_action"], 2, i18n_messages)
        elif "page_action" in data:
            ext.action = self._parse_action(data["page_action"], 2, i18n_messages)
            
        if "background" in data:
            ext.background = self._parse_background(data["background"], data["manifest_version"])
            
        ext.options_page = data.get("options_page")
        ext.options_ui = data.get("options_ui")
        
        # Permissões
        ext.permissions = self._parse_permissions(data.get("permissions", []))
        ext.optional_permissions = self._parse_permissions(data.get("optional_permissions", []))
        
        if "host_permissions" in data:
            ext.host_permissions = data["host_permissions"]
        elif ext.manifest_version == ManifestVersion.V2:
            host_perms = [p for p in data.get("permissions", []) if "://" in p or p == "<all_urls>"]
            ext.host_permissions = host_perms
            
        ext.web_accessible_resources = data.get("web_accessible_resources", [])
        
        return ext
    
    def _load_i18n_messages(self, ext_dir: Path, locale: str = "en") -> Dict[str, dict]:
        """
        Carrega mensagens i18n do _locales/{locale}/messages.json.
        Tenta o locale principal, fallback para en, fallback para pt_BR.
        """
        messages = {}
        
        # Tenta na ordem: locale solicitado, en, pt_BR
        locales_to_try = [locale, "en", "pt_BR", "pt"]
        
        for loc in locales_to_try:
            msg_path = ext_dir / "_locales" / loc / "messages.json"
            if not msg_path.exists():
                # Try locale variations (e.g., "pt_br" vs "pt-BR")
                for folder in (ext_dir / "_locales").iterdir() if (ext_dir / "_locales").exists() else []:
                    if folder.is_dir() and folder.name.lower().replace('-', '_') == loc.lower().replace('-', '_'):
                        msg_path = folder / "messages.json"
                        if msg_path.exists():
                            break
            
            if msg_path.exists():
                try:
                    with open(msg_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for key, val in data.items():
                            if key not in messages:
                                messages[key] = val
                except (json.JSONDecodeError, IOError):
                    continue
        
        return messages
    
    def _resolve_i18n(self, text: str, messages: Dict[str, dict]) -> str:
        """
        Resolve mensagens i18n como __MSG_extName__ para o valor real.
        """
        if not text:
            return text
        
        match = self.I18N_PATTERN.match(text.strip())
        if not match:
            return text
        
        key = match.group(1)
        
        # Chrome messages format: { "key": { "message": "value" } }
        if key in messages:
            msg_obj = messages[key]
            if isinstance(msg_obj, dict):
                return msg_obj.get("message", text)
            elif isinstance(msg_obj, str):
                return msg_obj
        
        return text
    
    def _parse_content_scripts(self, data: list) -> List[ContentScript]:
        scripts = []
        for cs in data:
            scripts.append(ContentScript(
                matches=cs.get("matches", []),
                js=cs.get("js", []),
                css=cs.get("css", []),
                run_at=cs.get("run_at", "document_idle"),
                all_frames=cs.get("all_frames", False),
                exclude_matches=cs.get("exclude_matches", []),
                match_about_blank=cs.get("match_about_blank", False)
            ))
        return scripts
    
    def _parse_action(self, data: dict, manifest_v: int, i18n_messages: Dict[str, dict] = None) -> ActionConfig:
        config = ActionConfig()
        if "default_popup" in data: config.default_popup = data["default_popup"]
        if "default_title" in data:
            title = data["default_title"]
            if i18n_messages:
                title = self._resolve_i18n(title, i18n_messages)
            config.default_title = title
        if "default_icon" in data:
            if isinstance(data["default_icon"], str):
                config.default_icon = {"16": data["default_icon"]}
            else:
                config.default_icon = data["default_icon"]
        return config
    
    def _parse_permissions(self, perm_list: list) -> List[Permission]:
        perms = []
        for p in perm_list:
            if "://" in p or p == "<all_urls>":
                continue
            
            supported = p in self.SUPPORTED_PERMISSIONS
            perms.append(Permission(name=p, granted=supported))
        return perms
    
    def _parse_background(self, data: dict, manifest_v: int) -> dict:
        if manifest_v == 2 and "scripts" in data:
            return {"service_worker": data["scripts"][0], "type": "module"}
        return data
    
    def _generate_extension_id(self, path: Path) -> str:
        m = hashlib.sha256()
        m.update(str(path.absolute()).encode('utf-8'))
        raw_hash = m.digest()[:16]
        
        ext_id = ""
        for b in raw_hash:
            ext_id += chr(97 + (b >> 4))
            ext_id += chr(97 + (b & 0x0F))
        return ext_id
    
    def validate(self, extension: Extension) -> List[str]:
        warnings = []
        for p in extension.permissions:
            if not p.granted:
                warnings.append(f"Permissão não suportada pelo Redux Browser: {p.name}")
        return warnings
