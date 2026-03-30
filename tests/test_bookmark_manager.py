import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from browser.bookmarks.bookmark_manager import BookmarkManager

class TestBookmarkManager(unittest.TestCase):
    def setUp(self):
        self.test_path = "/tmp/redux_test_bookmarks.json"
        if os.path.exists(self.test_path): os.remove(self.test_path)
        self.bm = BookmarkManager(self.test_path)

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_add_bookmark(self):
        bkm = self.bm.add_bookmark("My Site", "https://mysite.com")
        self.assertIsNotNone(bkm)
        self.assertEqual(bkm.title, "My Site")
        self.assertEqual(len(self.bm.root.children), 1)

    def test_folders_and_hierarchy(self):
        folder = self.bm.add_folder("Trabalho")
        bkm = self.bm.add_bookmark("Email", "mail.com", parent_id=folder.id)
        
        self.assertEqual(len(self.bm.root.children), 1) # A pasta
        self.assertEqual(len(folder.children), 1) # O site dentro dela
        
        # Testar load de disco
        bm2 = BookmarkManager(self.test_path)
        self.assertEqual(len(bm2.root.children), 1)
        self.assertEqual(bm2.root.children[0].title, "Trabalho")

    def test_removal(self):
        folder = self.bm.add_folder("Temp")
        resp = self.bm.remove_item(folder.id)
        self.assertTrue(resp)
        self.assertEqual(len(self.bm.root.children), 0)

if __name__ == "__main__":
    unittest.main()
