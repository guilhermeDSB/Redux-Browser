import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.engine.html_parser import HTMLParser
from browser.engine.css_parser import CSSParser

class TestCSSParser(unittest.TestCase):
    def setUp(self):
        self.html_parser = HTMLParser()
        self.css_parser = CSSParser()

    def test_basic_css_parsing(self):
        css = "div { color: red; background: black; } p.text { font-size: 14px; }"
        self.css_parser.load_css(css)
        self.assertGreater(len(self.css_parser.stylesheet.rules), 0)

    def test_specificity_and_cascade(self):
        html = '<div id="box" class="container" style="margin: 10px;"></div>'
        tree = self.html_parser.parse(html)
        # global tag vs class vs id
        div = tree.root
        div.attributes['id'] = 'box'
        div.attributes['class'] = 'container'
        div.attributes['style'] = 'margin: 10px;'
        css = """
        div { color: blue; } 
        .container { color: green; }
        #box { color: red; }
        """
        self.css_parser.load_css(css)
        
        computed = self.css_parser.compute_style(div)
        
        # Cascade: Tag rule 'span' loses to class rule '.highlight' 
        self.assertEqual(computed['color'], 'red')
        # Inline style mantido
        self.assertEqual(computed['margin'], '10px')

if __name__ == "__main__":
    unittest.main()
