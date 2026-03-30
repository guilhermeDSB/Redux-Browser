import pytest
import json
from pathlib import Path
from browser.extensions.manifest_parser import ManifestParser
from browser.extensions.extension_model import ManifestVersion

def test_manifest_v3_parsing(tmp_path):
    parser = ManifestParser()
    manifest_data = {
        "manifest_version": 3,
        "name": "Redux Test",
        "version": "1.0",
        "action": {"default_popup": "popup.html"},
        "permissions": ["storage"]
    }
    m_file = tmp_path / "manifest.json"
    m_file.write_text(json.dumps(manifest_data), encoding='utf-8')
    ext = parser.parse(m_file)
    assert ext.name == "Redux Test"
    assert ext.manifest_version == ManifestVersion.V3
    assert ext.action.default_popup == "popup.html"
    assert len(ext.permissions) == 1
    assert ext.permissions[0].name == "storage"

def test_manifest_v2_to_v3_conversion(tmp_path):
    parser = ManifestParser()
    manifest_data = {
        "manifest_version": 2,
        "name": "Legacy",
        "version": "1.0",
        "browser_action": {"default_popup": "legacy.html"}
    }
    m_file = tmp_path / "manifest.json"
    m_file.write_text(json.dumps(manifest_data), encoding='utf-8')
    ext = parser.parse(m_file)
    assert ext.manifest_version == ManifestVersion.V2
    assert ext.action is not None
    assert ext.action.default_popup == "legacy.html"

def test_manifest_missing_fields(tmp_path):
    parser = ManifestParser()
    manifest_data = {"name": "No Version"}
    m_file = tmp_path / "manifest.json"
    m_file.write_text(json.dumps(manifest_data), encoding='utf-8')
    with pytest.raises(ValueError):
        parser.parse(m_file)
