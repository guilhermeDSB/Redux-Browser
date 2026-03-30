from typing import Optional, List
from dataclasses import dataclass
from browser.engine.render_tree import RenderNode

@dataclass
class Rect:
    """Retângulo básico para cálculos geométricos"""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

class LayoutBox:
    """
    A caixa para o Box Model (margin, border, padding, content).
    Possui propriedades físicas na tela (absolute pos, width, height).
    """
    def __init__(self):
        self.content = Rect()
        
        # Simplificação: armazenamos como tuplas (top, right, bottom, left) ou valor fixo
        self.padding = Rect()
        self.border = Rect()
        self.margin = Rect()
        
    def total_width(self) -> float:
        """Largura total ocupada: Content + padding_h + border_h + margin_h"""
        return (self.margin.x + self.border.x + self.padding.x + 
                self.content.width + 
                self.padding.width + self.border.width + self.margin.width)
                
    def total_height(self) -> float:
        """Altura total ocupada"""
        return (self.margin.y + self.border.y + self.padding.y + 
                self.content.height + 
                self.padding.height + self.border.height + self.margin.height)

class LayoutEngine:
    """
    Responsável por calcular a dimensão e a posição (x, y) real 
    de cada nó na interface a partir da RenderTree.
    """
    def __init__(self, viewport_width: float, viewport_height: float):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def layout(self, root_node: RenderNode):
        """Ponto de entrada: Cria as LayoutBoxes e calcula o layout recursivo."""
        if not root_node: return
        
        root_node.layout_box = LayoutBox()
        root_node.layout_box.content.width = self.viewport_width
        root_node.layout_box.content.x = 0
        root_node.layout_box.content.y = 0
        
        self._layout_node(root_node)

    def _parse_length(self, val: str, parent_val: float, font_size: float = 16.0) -> float:
        """Converte px, %, ou em para float (fallback para 0)"""
        val = val.strip().lower()
        if val == 'auto' or val == '':
            return 0.0
        if val.endswith('px'):
            try: return float(val[:-2])
            except: return 0.0
        elif val.endswith('%'):
            try: return (float(val[:-1]) / 100.0) * parent_val
            except: return 0.0
        elif val.endswith('em'):
            try: return float(val[:-2]) * font_size
            except: return 0.0
        elif val.endswith('rem'):
            try: return float(val[:-3]) * 16.0  # rem é relativo ao root (16px padrão)
            except: return 0.0
        # Tentar parsear como número simples (sem unidade)
        try:
            return float(val)
        except:
            return 0.0

    def _layout_node(self, node: RenderNode):
        """Passo principal de Layout para Flow Layout (Block e Inline)"""
        # Se for inicializado
        if not node.layout_box:
            node.layout_box = LayoutBox()
            
        display = node.styles.get('display', 'inline')
        
        # 1. Configura a Largura (Width)
        self._calculate_width(node)
        
        # 2. Configura a Posição XY (Flow)
        self._calculate_position(node)
        
        # 3. Faz recursão para posicionar/dimencionar os filhos
        # Para Blocos, OS filhos inline acumulam horizontalmente, os blocks desce Y
        cursor_x = node.layout_box.content.x
        cursor_y = node.layout_box.content.y
        max_child_height_inline = 0
        
        for child in node.children:
            child.layout_box = LayoutBox()
            child_display = child.styles.get('display', 'inline')
            
            # Largura preliminar para os filhos (filhos pegam proporção relativa ao pai)
            child.layout_box.content.width = node.layout_box.content.width
            
            # Para flow block: empilha
            if child_display == 'block':
                # Desce o cursor em y se tivesse algum inline e zera o x
                if cursor_x > node.layout_box.content.x:
                    cursor_y += max_child_height_inline
                    cursor_x = node.layout_box.content.x
                    max_child_height_inline = 0
                
                # Seta posição e recursão
                child.layout_box.content.x = cursor_x
                child.layout_box.content.y = cursor_y
                self._layout_node(child) # recursao vai ajustar a altura!
                
                # Avança cursor Y
                cursor_y += child.layout_box.total_height()
                
            # Para flow inline: empilha horiz, desce quando quebra linha
            else:
                self._layout_node(child)
                # Verifica quebra de linha simplificada
                if cursor_x + child.layout_box.total_width() > node.layout_box.content.x + node.layout_box.content.width:
                    cursor_y += max_child_height_inline
                    cursor_x = node.layout_box.content.x
                    max_child_height_inline = 0
                    
                child.layout_box.content.x = cursor_x
                child.layout_box.content.y = cursor_y
                
                cursor_x += child.layout_box.total_width()
                max_child_height_inline = max(max_child_height_inline, child.layout_box.total_height())

        # Adiciona ultima linha caso terminasse em inline
        if cursor_x > node.layout_box.content.x:
            cursor_y += max_child_height_inline
            
        # 4. Configura Altura (Height) baseado no conteúdo (se não fixo)
        self._calculate_height(node, cursor_y - node.layout_box.content.y)

    def _calculate_width(self, node: RenderNode):
        """Avalia a largura. Blocos expandem pra 100% (-m-b-p) salvo se tiver height fixo."""
        box = node.layout_box
        style = node.styles
        
        # Font size para cálculos em
        font_size = self._parse_length(style.get('font-size', '16px'), 16.0)
        if font_size <= 0:
            font_size = 16.0
        
        # Placeholder simplificado para px e %
        parent_width = node.parent.layout_box.content.width if node.parent else self.viewport_width
        
        # Margins (lê propriedades expandidas ou shorthand)
        box.margin.y = self._parse_length(style.get('margin-top', '0px'), parent_width, font_size)  # top
        box.margin.x = self._parse_length(style.get('margin-left', style.get('margin', '0px').split()[0]), parent_width, font_size)  # left
        box.margin.width = self._parse_length(style.get('margin-right', style.get('margin', '0px').split()[0]), parent_width, font_size)  # right
        box.margin.height = self._parse_length(style.get('margin-bottom', '0px'), parent_width, font_size)  # bottom
        
        # Padding (lê propriedades expandidas ou shorthand)
        box.padding.y = self._parse_length(style.get('padding-top', '0px'), parent_width, font_size)  # top
        box.padding.x = self._parse_length(style.get('padding-left', style.get('padding', '0px').split()[0]), parent_width, font_size)  # left
        box.padding.width = self._parse_length(style.get('padding-right', style.get('padding', '0px').split()[0]), parent_width, font_size)  # right
        box.padding.height = self._parse_length(style.get('padding-bottom', '0px'), parent_width, font_size)  # bottom
        
        # Border width
        border_w = self._parse_length(style.get('border-width', '0px'), parent_width, font_size)
        box.border.x = border_w  # left
        box.border.width = border_w  # right
        box.border.y = border_w  # top
        box.border.height = border_w  # bottom
        
        # Default: Blocks preenchem tudo disponivel, Inline so o texto (trataremos no height)
        display = style.get('display', 'inline')
        if display == 'block':
            width_val = style.get('width', 'auto')
            if width_val != 'auto':
                w = self._parse_length(width_val, parent_width, font_size)
                box.content.width = w
            else:
                box.content.width = (parent_width - box.margin.x - box.margin.width
                                     - box.padding.x - box.padding.width
                                     - box.border.x - box.border.width)

    def _calculate_position(self, node: RenderNode):
        """Aplica margins, padding e bordas ao posicionamento do conteúdo."""
        box = node.layout_box
        
        # Atualiza o x/y do content para estar dentro de margens, bordas e padding
        box.content.x += box.margin.x + box.border.x + box.padding.x
        box.content.y += box.margin.y + box.border.y + box.padding.y

    def _calculate_height(self, node: RenderNode, children_height: float):
        """Determina a altura. Inline é base font-size, Block é a prop ou a altura dos filhos."""
        box = node.layout_box
        style = node.styles
        parent_width = node.parent.layout_box.content.width if node.parent else self.viewport_width
        
        # Se for texto / auto, a altura é do conteudo (estimativa via fontSize nos nos de texto)
        if node.dom_node.tag_name == "#text":
            fs = self._parse_length(style.get('font-size', '16px'), parent_width)
            if fs <= 0:
                fs = 16.0
            box.content.height = fs * 1.2  # line-height estimada
            # Largura baseada em font-size * 0.6 por caractere (melhor estimativa)
            box.content.width = len(node.dom_node.text_content) * (fs * 0.6) 
            return
            
        height_val = style.get('height', 'auto')
        if height_val != 'auto':
            box.content.height = self._parse_length(height_val, parent_width) # em tese é em relacao a height do pai
        else:
            box.content.height = children_height

        # Se for inline sem height (eg: img, span vazio) e nao for texto
        if style.get('display', 'inline') == 'inline' and children_height == 0 and node.dom_node.tag_name != "#text":
           box.content.height = 0
