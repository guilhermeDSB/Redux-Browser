import pytest
from pathlib import Path
import zipfile
import shutil
from browser.extensions.extension_manager import ExtensionManager
from browser.extensions.extension_model import ExtensionState

@pytest.fixture
def clean_manager(tmp_path):
    # Sobrescreve caminhos pro teste
    ExtensionManager.EXTENSIONS_DIR = tmp_path / "extensions"
    ExtensionManager.STATE_FILE = tmp_path / "extensions_state.json"
    manager = ExtensionManager()
    return manager

def test_install_from_folder(clean_manager, tmp_path):
    folder = tmp_path / "dummy_ext"
    folder.mkdir()
    (folder / "manifest.json").write_text('{"name":"Ext A", "version":"1.0", "manifest_version": 3}', encoding='utf-8')
    
    ext = clean_manager.install_from_folder(folder)
    assert ext.name == "Ext A"
    assert ext.state == ExtensionState.ENABLED
    assert ext.id in clean_manager._extensions

def test_disable_and_enable(clean_manager, tmp_path):
    folder = tmp_path / "dummy_ext2"
    folder.mkdir()
    (folder / "manifest.json").write_text('{"name":"Ext B", "version":"1.0", "manifest_version": 3}', encoding='utf-8')
    
    ext = clean_manager.install_from_folder(folder)
    assert ext.state == ExtensionState.ENABLED
    
    clean_manager.disable(ext.id)
    assert clean_manager.get_extension(ext.id).state == ExtensionState.DISABLED
    
    clean_manager.enable(ext.id)
    assert clean_manager.get_extension(ext.id).state == ExtensionState.ENABLED

def test_uninstall(clean_manager, tmp_path):
    folder = tmp_path / "dummy_ext3"
    folder.mkdir()
    (folder / "manifest.json").write_text('{"name":"Ext C", "version":"1.0", "manifest_version": 3}', encoding='utf-8')
    
    ext = clean_manager.install_from_folder(folder)
    ext_id = ext.id
    
    assert clean_manager.uninstall(ext_id) == True
    assert clean_manager.get_extension(ext_id) is None
