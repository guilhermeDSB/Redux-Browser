from typing import List, Dict, Optional
from dataclasses import dataclass
import re
from browser.engine.html_parser import DOMNode

@dataclass
class Specificity:
    """Modela a especificidade de um seletor CSS (inline, id, class, tag)"""
    inline: int = 0
    id_count: int = 0
    class_count: int = 0
    tag_count: int = 0

    def __lt__(self, other):
        if self.inline != other.inline: return self.inline < other.inline
        if self.id_count != other.id_count: return self.id_count < other.id_count
        if self.class_count != other.class_count: return self.class_count < other.class_count
        return self.tag_count < other.tag_count

    def __eq__(self, other):
        return (self.inline == other.inline and 
                self.id_count == other.id_count and 
                self.class_count == other.class_count and 
                self.tag_count == other.tag_count)

class CSSSelector:
    """Representa um único seletor (ex: 'div.container > p#texto')"""
    def __init__(self, raw_selector: str):
        self.raw = raw_selector.strip()
        self.specificity = self._calculate_specificity()
        
    def _calculate_specificity(self) -> Specificity:
        """Calcula a especificidade (a,b,c) ignorando seletores contextuais completos por ora"""
        ids = len(re.findall(r'#[\w-]+', self.raw))
        classes = len(re.findall(r'\.[\w-]+', self.raw)) + len(re.findall(r'\[.+?\]', self.raw)) + len(re.findall(r':[\w-]+', self.raw))
        # Remove ids e classes temporariamente para contar as tags
        temp = re.sub(r'[#.:][\w-]+', '', self.raw)
        temp = re.sub(r'\[.+?\]', '', temp)
        # Conta tags: palavras que sobram e não são combinadores >, +, ~
        tags = len([t for t in temp.replace('>', ' ').replace('+', ' ').replace('~', ' ').split() if t])
        
        return Specificity(id_count=ids, class_count=classes, tag_count=tags)

    def matches(self, node: DOMNode) -> bool:
        """
        Verifica se este seletor casa com o DOMNode.
        Suporta seletores simples (tag.class#id) e hierárquicos (ancestor descendant, parent > child).
        """
        if node.tag_name == "#text": return False
        
        # Separar o seletor em partes (combinadores: espaço, >, +, ~)
        parts = re.split(r'(\s*>\s*|\s+)', self.raw.strip())
        # Filtrar partes vazias
        parts = [p.strip() for p in parts if p.strip()]
        
        if not parts: return False
        
        # Se é um seletor simples (sem hierarquia)
        if len(parts) == 1:
            return self._matches_simple(parts[0], node)
        
        # Seletor hierárquico: verificar da direita para a esquerda
        # A parte mais à direita deve casar com o nó atual
        target_part = parts[-1]
        if not self._matches_simple(target_part, node):
            return False
        
        # Percorrer partes restantes da direita para a esquerda
        current = node
        i = len(parts) - 2
        while i >= 0:
            part = parts[i]
            if part == '>':
                # Combinador filho direto: o pai imediato deve casar com a parte anterior
                i -= 1
                if i < 0: return False
                current = current.parent
                if not current or current.tag_name == "document":
                    return False
                if not self._matches_simple(parts[i], current):
                    return False
            else:
                # Combinador descendente (espaço): qualquer ancestral deve casar
                found = False
                current = current.parent
                while current and current.tag_name != "document":
                    if self._matches_simple(part, current):
                        found = True
                        break
                    current = current.parent
                if not found:
                    return False
            i -= 1
        
        return True
    
    @staticmethod
    def _matches_simple(selector_part: str, node: DOMNode) -> bool:
        """Verifica se um seletor simples (sem combinadores) casa com o nó."""
        if not selector_part: return False
        if selector_part == '*': return True
        
        target = selector_part.strip()
        
        # tag matcher
        tag_match = re.match(r'^([a-zA-Z0-9-]+)', target)
        if tag_match:
            if node.tag_name != tag_match.group(1).lower():
                return False
                
        # id matcher
        ids = re.findall(r'#([\w-]+)', target)
        if ids:
            if node.attributes.get('id') != ids[0]:
                return False
                
        # class matcher
        classes = re.findall(r"\.([\w-]+)", target)
        if classes:
            node_classes = node.attributes.get('class', '').split()
            for cls in classes:
                if cls not in node_classes:
                    return False
        
        # Se o seletor é APENAS classes/ids sem tag, garantir que acertamos algo
        if not tag_match and not ids and not classes:
            return False
                    
        return True

class CSSRule:
    """Uma regra CSS contendo um ou mais seletores e blocos de declaração"""
    def __init__(self, selector_text: str, declarations: Dict[str, str]):
        self.selectors = [CSSSelector(s) for s in selector_text.split(',')]
        self.declarations = declarations

class StyleSheet:
    """Coleção de regras CSS extraídas"""
    def __init__(self):
        self.rules: List[CSSRule] = []

    def add_rules(self, css_text: str):
        """Parseia bloco CSS e adiciona as regras"""
        # Remove comentários CSS /* ... */
        css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
        
        # Encontra blocos:  seletor { prop: val; prop: val; }
        blocks = re.findall(r'([^{]+)\{([^}]+)\}', css_text)
        
        for selector_text, rbody in blocks:
            selector_text = selector_text.strip()
            if not selector_text or selector_text.startswith('@'): continue # ignora @media por ora
            
            declarations = {}
            for decl in rbody.split(';'):
                decl = decl.strip()
                if ':' in decl:
                    prop, val = decl.split(':', 1)
                    declarations[prop.strip()] = val.strip()
                    
            if declarations:
                self.rules.append(CSSRule(selector_text, declarations))

class CSSParser:
    """
    Parser e Aplicador de CSS (Cascading Style Sheets).
    Responsável por calcular o estilo final de cada nó.
    """
    def __init__(self):
        self.stylesheet = StyleSheet()
        
        # Propriedades padrão iniciais globais
        self.default_styles = {
            "display": "block",
            "font-size": "16px",
            "font-family": "sans-serif",
            "color": "black",
            "margin": "0px",
            "padding": "0px",
            "background-color": "transparent"
        }
        
        # Estilos do user_agent (navegador)
        ua_css = """
        p, div, h1, h2, h3, h4, h5, h6, ul, ol, li, form { display: block; }
        span, a, img, b, i, strong, em { display: inline; }
        head, title, style, script, link, meta { display: none; }
        h1 { font-size: 2em; font-weight: bold; margin: 0.67em 0; }
        h2 { font-size: 1.5em; font-weight: bold; margin: 0.83em 0; }
        a { color: blue; text-decoration: underline; }
        b, strong { font-weight: bold; }
        i, em { font-style: italic; }
        """
        self.stylesheet.add_rules(ua_css)

    def load_css(self, css_text: str):
        """Adiciona mais CSS à stylesheet global do parser"""
        self.stylesheet.add_rules(css_text)

    def compute_style(self, node: DOMNode) -> Dict[str, str]:
        """Calcula o dicionário resultante das propriedades CSS para o nó"""
        computed = dict(self.default_styles)
        
        if node.tag_name == "#text":
            return computed

        # Acumula regras que deram match {(propriedade): (valor, especificidade, important)}
        matched_props: Dict[str, tuple] = {}
        
        # 1. Aplica regras internas/externas calculadas
        for rule in self.stylesheet.rules:
            for selector in rule.selectors:
                if selector.matches(node):
                    spec = selector.specificity
                    for prop, val in rule.declarations.items():
                        # Detectar !important
                        is_important = '!important' in val
                        clean_val = val.replace('!important', '').strip() if is_important else val
                        
                        if prop in matched_props:
                            existing_important = matched_props[prop][2]
                            # !important sempre vence não-important
                            if existing_important and not is_important:
                                continue
                            # Se ambos são important ou ambos não-important, comparar especificidade
                            if existing_important == is_important:
                                if spec < matched_props[prop][1]:
                                    continue
                        matched_props[prop] = (clean_val, spec, is_important)
                        
        for prop, (val, _, _) in matched_props.items():
            computed[prop] = val

        # 2. Especificidade Máxima: Estilo Inline na Tag (ex: <div style="color: red">)
        inline_style = node.attributes.get("style", "")
        if inline_style:
            for decl in inline_style.split(';'):
                decl = decl.strip()
                if ':' in decl:
                    prop, val = decl.split(':', 1)
                    computed[prop.strip()] = val.strip()

        # Merge de propriedades shorthand no momento de aplicar o inline/computed
        if "border" in computed:
            # ex: "1px solid black" -> pega o primeiro px
            m = re.search(r'(\d+)px', computed["border"])
            if m: computed["border-width"] = f"{m.group(1)}px"
        
        # Expandir shorthand margin (1-4 valores)
        self._expand_shorthand(computed, 'margin')
        # Expandir shorthand padding (1-4 valores)
        self._expand_shorthand(computed, 'padding')
        
        # Herdadas do pai: Algumas regras em CSS herdam (color, font-family, font-size)
        if node.parent and node.parent.tag_name != "document":
            # Aqui no parser standalone não temos o estilo do pai computado pronto
            pass # Será tratado corretamente no render_tree
            
        return computed
    
    @staticmethod
    def _expand_shorthand(computed: dict, prop: str):
        """Expande shorthand CSS (margin/padding) de 1-4 valores para top/right/bottom/left."""
        val = computed.get(prop, '0px').strip()
        if not val:
            return
        parts = val.split()
        if len(parts) == 1:
            # Todos iguais
            computed[f"{prop}-top"] = parts[0]
            computed[f"{prop}-right"] = parts[0]
            computed[f"{prop}-bottom"] = parts[0]
            computed[f"{prop}-left"] = parts[0]
        elif len(parts) == 2:
            # vertical | horizontal
            computed[f"{prop}-top"] = parts[0]
            computed[f"{prop}-right"] = parts[1]
            computed[f"{prop}-bottom"] = parts[0]
            computed[f"{prop}-left"] = parts[1]
        elif len(parts) == 3:
            # top | horizontal | bottom
            computed[f"{prop}-top"] = parts[0]
            computed[f"{prop}-right"] = parts[1]
            computed[f"{prop}-bottom"] = parts[2]
            computed[f"{prop}-left"] = parts[1]
        elif len(parts) >= 4:
            # top | right | bottom | left
            computed[f"{prop}-top"] = parts[0]
            computed[f"{prop}-right"] = parts[1]
            computed[f"{prop}-bottom"] = parts[2]
            computed[f"{prop}-left"] = parts[3]
