import pytest
from browser.extensions.chrome_api.api_storage import ChromeStorageAPI
import shutil
from pathlib import Path

@pytest.fixture
def storage():
    ChromeStorageAPI.STORAGE_DIR = Path("./test_storage_dir")
    api = ChromeStorageAPI("test_uuid_123")
    yield api
    if ChromeStorageAPI.STORAGE_DIR.exists():
        shutil.rmtree(ChromeStorageAPI.STORAGE_DIR)

def test_storage_set_get(storage):
    storage.set("local", {"theme": "dark", "count": 1})
    data = storage.get("local")
    assert data["theme"] == "dark"
    assert data["count"] == 1
    
    # Get params
    single = storage.get("local", "theme")
    assert single == {"theme": "dark"}

def test_storage_remove(storage):
    storage.set("sync", {"a": 1, "b": 2})
    storage.remove("sync", ["a"])
    data = storage.get("sync")
    assert "a" not in data
    assert data["b"] == 2

def test_storage_clear(storage):
    storage.set("local", {"xyz": 999})
    storage.clear("local")
    data = storage.get("local")
    assert data == {}
