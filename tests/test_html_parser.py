import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.engine.html_parser import HTMLParser

class TestHTMLParser(unittest.TestCase):
    def setUp(self):
        self.parser = HTMLParser()

    def test_basic_parsing(self):
        html = '<html><body><h1>Redux</h1><p class="text">Browser</p></body></html>'
        tree = self.parser.parse(html)
        
        self.assertEqual(tree.root.tag_name, 'html')
        self.assertEqual(len(tree.root.children), 1)
        self.assertEqual(tree.root.children[0].tag_name, 'body')
        
    def test_malformed_html(self):
        html = '<div><p>Unclosed paragraph</div>'
        tree = self.parser.parse(html)
        
        div = tree.root.children[0]
        self.assertEqual(div.tag_name, 'div')
        # A tag p é forçada a fechar subindo a hierarquia
        p = div.children[0]
        self.assertEqual(p.tag_name, 'p')
        self.assertEqual(p.children[0].text_content, 'Unclosed paragraph')

    def test_queries(self):
        html = '<html><body><div id="main"><p class="red">Test</p></div></body></html>'
        tree = self.parser.parse(html)
        
        main_div = tree.getElementById('main')
        self.assertIsNotNone(main_div)
        self.assertEqual(main_div.tag_name, 'div')
        
        red_p = tree.getElementsByClassName('red')
        self.assertEqual(len(red_p), 1)
        self.assertEqual(red_p[0].tag_name, 'p')

if __name__ == "__main__":
    unittest.main()
