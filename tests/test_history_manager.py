import unittest
import sys
import os
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from browser.history.history_manager import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        # Cria um db temporário para nao sujar o principal do usuario
        self.test_path = "/tmp/redux_test_history.json"
        self.hm = HistoryManager(self.test_path)

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_add_and_persistence(self):
        self.hm.add_entry("tab1", "https://siteA.com", "Site A")
        self.hm.add_entry("tab1", "https://siteB.com", "Site B")
        
        # Testar memória local (per-tab stack)
        self.assertTrue(self.hm.can_go_back("tab1"))
        self.assertFalse(self.hm.can_go_forward("tab1"))
        
        # Testar histórico global
        global_hist = self.hm.get_history()
        self.assertEqual(len(global_hist), 2)
        # Mais recente primeiro
        self.assertEqual(global_hist[0].url, "https://siteB.com")

    def test_navigation_stack(self):
        self.hm.add_entry("tab_nav", "url1", "1")
        self.hm.add_entry("tab_nav", "url2", "2")
        self.hm.add_entry("tab_nav", "url3", "3")
        
        url_back = self.hm.go_back("tab_nav")
        self.assertEqual(url_back, "url2")
        self.assertTrue(self.hm.can_go_forward("tab_nav"))
        
        url_back2 = self.hm.go_back("tab_nav")
        self.assertEqual(url_back2, "url1")
        
        # Simula surfar pra outro lugar estando no meio do historico (Quebra a cadeia da frente)
        self.hm.add_entry("tab_nav", "url4", "4")
        self.assertFalse(self.hm.can_go_forward("tab_nav"))
        self.assertEqual(self.hm.go_back("tab_nav"), "url1")

    def test_private_mode_ignore(self):
        self.hm.add_entry("tab_priv", "https://secret.com", "Secret", is_private=True)
        # Historico global nao pode ter sido persistido
        global_hist = self.hm.get_history()
        self.assertEqual(len(global_hist), 0)

if __name__ == "__main__":
    unittest.main()
