import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.engine.html_parser import HTMLParser
from browser.engine.css_parser import CSSParser
from browser.engine.render_tree import RenderTree
from browser.engine.layout import LayoutEngine

class TestRenderTreeAndLayout(unittest.TestCase):
    def setUp(self):
        self.html_parser = HTMLParser()
        self.css_parser = CSSParser()

    def test_display_none_exclusion(self):
        html = '<div><p style="display: none;">Hidden</p><span>Show</span></div>'
        tree = self.html_parser.parse(html)
        
        render_tree = RenderTree(tree.root, self.css_parser)
        render_tree.build()
        
        # O P nao deve aparecer no render tree, apenas o span text
        children_tags = [n.dom_node.tag_name for n in render_tree.root.children]
        self.assertNotIn('p', children_tags)
        # Span shouldn't be in the tree if display is none
        self.assertNotIn('span', children_tags)

    def test_layout_box_model_calculation(self):
        html = '<div style="margin: 10px; padding: 5px; width: 100px;"></div>'
        tree = self.html_parser.parse(html)
        tree.root.attributes['style'] = 'margin: 10px; padding: 5px; width: 100px;'
        render_tree = RenderTree(tree.root, self.css_parser)
        render_tree.build()
        
        layout = LayoutEngine(800, 600)
        layout.layout(render_tree.root)
        
        box = render_tree.root.layout_box
        self.assertEqual(box.margin.x, 10.0)
        self.assertEqual(box.padding.x, 5.0)  # Padding is now correctly computed from style
        
if __name__ == "__main__":
    unittest.main()
