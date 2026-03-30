"""
Redux Browser — Init do módulo de extensões.
"""
from .extension_model import Extension, ExtensionState, ManifestVersion, ContentScript, ActionConfig, Permission
from .manifest_parser import ManifestParser
from .crx_parser import CRXParser
from .extension_manager import ExtensionManager
from .content_script_loader import ContentScriptLoader
