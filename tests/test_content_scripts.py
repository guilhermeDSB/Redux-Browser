import pytest
from browser.extensions.content_script_loader import ContentScriptLoader
from browser.extensions.extension_manager import ExtensionManager
from PyQt6.QtWebEngineCore import QWebEngineScript

def test_map_run_at():
    loader = ContentScriptLoader(None)
    assert loader._map_run_at("document_start") == QWebEngineScript.InjectionPoint.DocumentCreation
    assert loader._map_run_at("document_end") == QWebEngineScript.InjectionPoint.DocumentReady
    assert loader._map_run_at("document_idle") == QWebEngineScript.InjectionPoint.Deferred
    assert loader._map_run_at("invalid") == QWebEngineScript.InjectionPoint.Deferred

def test_generate_shim():
    loader = ContentScriptLoader(None)
    shim = loader._generate_chrome_api_shim("test_ext_123")
    assert "test_ext_123" in shim
    assert "chrome.runtime.sendMessage" in shim
    assert "chrome.storage.local" in shim
