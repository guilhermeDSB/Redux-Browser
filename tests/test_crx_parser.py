import pytest
import zipfile
from pathlib import Path
from browser.extensions.crx_parser import CRXParser

def test_valid_zip_extraction(tmp_path):
    """Testa a extração usando um arquivo .zip puro renomeado para crx/zip."""
    parser = CRXParser()
    zip_path = tmp_path / "test.zip"
    
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr("manifest.json", '{"name":"Zip Test", "version":"1", "manifest_version": 3}')
        z.writestr("content.js", 'console.log("hello");')
        
    assert parser.is_valid_crx(zip_path) is True
    dest_path = parser.extract(zip_path, tmp_path / "out")
    
    assert (dest_path / "manifest.json").exists()
    assert (dest_path / "content.js").exists()
