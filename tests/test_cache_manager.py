import unittest
import sys
import os
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from browser.cache.cache_manager import CacheManager

class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.test_path = os.path.join(os.path.dirname(__file__), '_test_cache_tmp')
        self.cm = CacheManager(self.test_path)

    def tearDown(self):
        self.cm.clear_cache()
        if os.path.exists(self.test_path):
            shutil.rmtree(self.test_path, ignore_errors=True)

    def test_store_and_retrieve(self):
        url = "https://cdn.example.com/style.css"
        data = b"body { color: red; }"
        
        self.cm.store_resource(url, data, {"Content-Type": "text/css"})
        retrieved = self.cm.get_cached_resource(url)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved, data)

    def test_cache_control_no_store(self):
        url = "https://api.example.com/data"
        data = b"{'secret': true}"
        
        # Forçando header de nao guardar em disco
        self.cm.store_resource(url, data, {"Cache-Control": "no-store, private"})
        
        retrieved = self.cm.get_cached_resource(url)
        self.assertIsNone(retrieved)

if __name__ == "__main__":
    unittest.main()
