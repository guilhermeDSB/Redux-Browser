from typing import List, Dict, Optional
from browser.engine.html_parser import DOMNode
from browser.engine.css_parser import CSSParser, StyleSheet

class RenderNode:
    """
    Nó da Árvore de Renderização (Render Tree).
    Combina um elemento DOM com seus Estilos Computados.
    Nós com `display: none` do DOM não entram na Render Tree.
    """
    def __init__(self, dom_node: DOMNode, styles: Dict[str, str], parent: Optional['RenderNode'] = None):
        self.dom_node = dom_node
        self.styles = styles
        self.parent = parent
        self.children: List['RenderNode'] = []
        
        # O Motor de Layout preencherá isso depois
        self.layout_box = None

    def add_child(self, child: 'RenderNode'):
        child.parent = self
        self.children.append(child)

class RenderTree:
    """
    Gerencia a Render Tree a partir do nó raiz.
    Responsável por varrer o DOM e gerar os RenderNodes com auxílio do CSSParser.
    """
    
    # Propriedades CSS que são herdadas do pai para o filho (ex: color, font-family)
    INHERITABLE_PROPS = {
        "color", "font-family", "font-size", "font-weight", "font-style",
        "text-align", "line-height", "text-decoration", "text-transform",
        "letter-spacing", "word-spacing", "white-space",
        "visibility", "cursor", "list-style", "list-style-type",
        "direction", "text-indent", "quotes",
    }

    def __init__(self, dom_root: DOMNode, css_parser: CSSParser):
        self.dom_root = dom_root
        self.css_parser = css_parser
        self.root: Optional[RenderNode] = None

    def build(self):
        """Constrói a árvore de renderização navegando o DOM recursivamente."""
        self.root = self._build_node(self.dom_root, None)

    def _build_node(self, dom_node: DOMNode, parent_render_node: Optional[RenderNode]) -> Optional[RenderNode]:
        """Processa um nó do DOM, computa estilos e anexa filhos recursivamente."""
        
        # Calcula estilo cascata (sem herança ainda)
        computed_styles = self.css_parser.compute_style(dom_node)
        
        # Herança: se uma propriedade inerente não estiver definida, pega do pai
        if parent_render_node:
            for prop in self.INHERITABLE_PROPS:
                if prop not in dom_node.attributes.get('style', '') and prop in parent_render_node.styles:
                    if prop not in computed_styles or computed_styles[prop] == self.css_parser.default_styles.get(prop):
                        computed_styles[prop] = parent_render_node.styles[prop]
                        
        # Se display: none, este nó e seus filhos não participam da Render Tree
        if computed_styles.get('display') == 'none':
            return None
            
        # Cria o nó
        render_node = RenderNode(dom_node, computed_styles, parent_render_node)
        
        # Recursão para os filhos
        for child_dom in dom_node.children:
            child_render = self._build_node(child_dom, render_node)
            if child_render:
                render_node.add_child(child_render)
                
        return render_node
