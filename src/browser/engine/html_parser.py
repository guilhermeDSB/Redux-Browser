import re
from typing import List, Dict, Optional

class DOMNode:
    """
    Representa um nó na Árvore DOM (Document Object Model).
    Pode ser um Elemento (tag) ou Texto.
    """
    def __init__(self, tag_name: str, parent: Optional['DOMNode'] = None):
        self.tag_name = tag_name.lower()
        self.attributes: Dict[str, str] = {}
        self.children: List['DOMNode'] = []
        self.parent = parent
        self.text_content: str = ""
        
        # Propriedade para debugging e visualização
        self._is_text = (self.tag_name == "#text")

    def add_child(self, child: 'DOMNode'):
        child.parent = self
        self.children.append(child)

    def print_tree(self, indent: int = 0) -> str:
        """Gera uma string de representação da árvore (para o DOM Viewer)"""
        space = "  " * indent
        if self._is_text:
            text = self.text_content.replace('\n', ' ').strip()
            if text:
                return f"{space}#text: \"{text}\"\n"
            return ""
        
        attrs_str = " ".join([f'{k}="{v}"' for k, v in self.attributes.items()])
        attrs_str = f" {attrs_str}" if attrs_str else ""
        
        res = f"{space}<{self.tag_name}{attrs_str}>\n"
        for child in self.children:
            res += child.print_tree(indent + 1)
        res += f"{space}</{self.tag_name}>\n"
        return res

class DOMTree:
    """
    Gerencia a árvore DOM a partir do nó raiz (geralmente <html>).
    Possui métodos de busca similares ao JavaScript.
    """
    def __init__(self, root: DOMNode):
        self.root = root

    def getElementById(self, id_str: str) -> Optional[DOMNode]:
        """Busca um elemento que possui o ID fornecido."""
        def _search(node: DOMNode) -> Optional[DOMNode]:
            if node.attributes.get("id") == id_str:
                return node
            for child in node.children:
                res = _search(child)
                if res: return res
            return None
        return _search(self.root)

    def getElementsByTagName(self, tag_str: str) -> List[DOMNode]:
        """Retorna uma lista de elementos com a tag fornecida."""
        tag_str = tag_str.lower()
        result = []
        def _search(node: DOMNode):
            if node.tag_name == tag_str:
                result.append(node)
            for child in node.children:
                _search(child)
        _search(self.root)
        return result

    def getElementsByClassName(self, class_str: str) -> List[DOMNode]:
        """Retorna lista de elementos que contêm a classe fornecida."""
        result = []
        def _search(node: DOMNode):
            classes = node.attributes.get("class", "").split()
            if class_str in classes:
                result.append(node)
            for child in node.children:
                _search(child)
        _search(self.root)
        return result


class HTMLParser:
    """
    Parser HTML5 Educacional (Simplificado).
    Transforma uma string HTML em uma DOMTree.
    """
    
    # Tags que não precisam ser fechadas intencionalmente
    SELF_CLOSING_TAGS = {
        "img", "input", "br", "hr", "meta", "link", "source",
        "area", "base", "col", "embed", "track", "wbr", "param"
    }
    
    # Tags cujo conteúdo deve ser tratado como texto bruto (não parseado como HTML)
    RAW_TEXT_TAGS = {"script", "style", "textarea", "pre", "code"}
    
    # Entidades HTML comuns
    HTML_ENTITIES = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
        "&apos;": "'", "&nbsp;": "\u00A0", "&copy;": "©",
        "&reg;": "®", "&trade;": "™", "&mdash;": "—",
        "&ndash;": "–", "&laquo;": "«", "&raquo;": "»",
        "&bull;": "•", "&hellip;": "…", "&euro;": "€",
        "&pound;": "£", "&yen;": "¥", "&cent;": "¢",
    }
    
    def __init__(self):
        self._pos = 0
        self._html = ""
        self._length = 0

    def parse(self, html_source: str) -> DOMTree:
        """Ponto de entrada: Recebe uma string HTML e retorna uma árvore DOM"""
        self._html = html_source
        self._pos = 0
        self._length = len(html_source)
        
        root = DOMNode("document")
        current_node = root
        
        while self._pos < self._length:
            if self._starts_with("<!--"):
                self._parse_comment()
            elif self._starts_with("</"):
                # Tag de fechamento
                tag_name = self._parse_closing_tag()
                # Tratamento de HTML malformado: se fechou uma tag que nunca abriu, ignora
                # Se fechou a tag atual, sobe um nível. Se fechou uma pai, sobe até ela.
                temp = current_node
                found = False
                while temp and temp.tag_name != "document":
                    if temp.tag_name == tag_name:
                        found = True
                        break
                    temp = temp.parent
                
                if found and current_node.parent:
                    while current_node.tag_name != tag_name and current_node.parent:
                        current_node = current_node.parent
                    current_node = current_node.parent # Sobe mais um pois fechou
            elif self._starts_with("<"):
                # Nova tag de abertura
                if self._html[self._pos+1:self._pos+2] == "!": # doctype
                    self._parse_doctype()
                    continue
                    
                node = self._parse_opening_tag()
                if node:
                    current_node.add_child(node)
                    if node.tag_name not in self.SELF_CLOSING_TAGS:
                        # Se for tag de texto bruto, extrair o conteúdo até o fechamento
                        if node.tag_name in self.RAW_TEXT_TAGS:
                            raw_content = self._parse_raw_text(node.tag_name)
                            if raw_content.strip():
                                text_node = DOMNode("#text")
                                text_node.text_content = raw_content
                                node.add_child(text_node)
                        else:
                            current_node = node
            else:
                # É um texto solto
                text = self._parse_text()
                decoded_text = self._decode_entities(text)
                if decoded_text.strip():
                    text_node = DOMNode("#text")
                    text_node.text_content = decoded_text
                    current_node.add_child(text_node)

        # Retorna a raiz tentada (buscando a tag html principal, senao document)
        html_nodes = root.children
        for n in html_nodes:
            if n.tag_name == 'html':
                return DOMTree(n)
        return DOMTree(root)

    # --- FUNÇÕES UTILITÁRIAS DE PARSING STRING ---

    def _eof(self) -> bool:
        return self._pos >= self._length

    def _next_char(self) -> str:
        if self._eof(): return ""
        ch = self._html[self._pos]
        self._pos += 1
        return ch

    def _peek(self) -> str:
        return "" if self._eof() else self._html[self._pos]

    def _starts_with(self, s: str) -> bool:
        return self._html.startswith(s, self._pos)

    def _consume_whitespace(self):
        while not self._eof() and self._peek().isspace():
            self._next_char()
            
    def _parse_doctype(self):
        """Ignora <!DOCTYPE html>"""
        while not self._eof() and self._peek() != ">":
            self._next_char()
        self._next_char() # consome ">"

    def _parse_comment(self):
        """Ignora <!-- comment -->"""
        self._pos += 4 # Skip <!--
        while not self._eof() and not self._starts_with("-->"):
            self._next_char()
        self._pos += 3 # Skip -->

    def _parse_text(self) -> str:
        """Lê texto até encontrar uma tag"""
        start = self._pos
        while not self._eof() and self._peek() != "<":
            self._next_char()
        return self._html[start:self._pos]

    def _decode_entities(self, text: str) -> str:
        """Decodifica entidades HTML comuns (&amp; -> &, &#39; -> ', etc.)"""
        if '&' not in text:
            return text
        # Substituir entidades nomeadas
        for entity, char in self.HTML_ENTITIES.items():
            text = text.replace(entity, char)
        # Substituir entidades numéricas decimais (&#123;)
        import re
        def _replace_decimal(m):
            try:
                return chr(int(m.group(1)))
            except (ValueError, OverflowError):
                return m.group(0)
        text = re.sub(r'&#(\d+);', _replace_decimal, text)
        # Substituir entidades hexadecimais (&#x1F;)
        def _replace_hex(m):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return m.group(0)
        text = re.sub(r'&#x([0-9a-fA-F]+);', _replace_hex, text)
        return text

    def _parse_raw_text(self, tag_name: str) -> str:
        """Lê conteúdo bruto até encontrar a tag de fechamento correspondente (e.g. </script>)"""
        close_tag = f"</{tag_name}"
        start = self._pos
        while not self._eof():
            if self._html[self._pos:self._pos + len(close_tag)].lower() == close_tag:
                content = self._html[start:self._pos]
                # Consome a tag de fechamento
                self._pos += len(close_tag)
                while not self._eof() and self._peek() != ">":
                    self._next_char()
                if not self._eof():
                    self._next_char()  # consome >
                return content
            self._next_char()
        return self._html[start:self._pos]

    def _parse_closing_tag(self) -> str:
        """Lê </tag>"""
        self._pos += 2 # Skip </
        tag_name = ""
        while not self._eof() and self._peek() != ">" and not self._peek().isspace():
            tag_name += self._next_char().lower()
            
        while not self._eof() and self._peek() != ">":
            self._next_char() # consome sujeira antes do >
            
        if not self._eof():
            self._next_char() # consome ">"
            
        return tag_name

    def _parse_opening_tag(self) -> Optional[DOMNode]:
        """Lê <tag id="x"> e retorna o DOMNode"""
        self._next_char() # Skip <
        
        # Lê o nome da tag
        tag_name = ""
        while not self._eof() and not self._peek().isspace() and self._peek() not in (">", "/"):
            tag_name += self._next_char().lower()
            
        if not tag_name:
            return None
            
        node = DOMNode(tag_name)
        
        # Lê atributos
        while not self._eof():
            self._consume_whitespace()
            if self._peek() in (">", "/"):
                break
                
            attr_name, attr_value = self._parse_attribute()
            if attr_name:
                node.attributes[attr_name.lower()] = attr_value
                
        # Consome > ou />
        if self._starts_with("/>"):
            self._pos += 2
            # Força como self_closing para essa tag específica
            node._is_self_closing_override = True 
        elif self._peek() == ">":
            self._next_char()
            
        return node

    def _parse_attribute(self) -> tuple[str, str]:
        """Lê key="value" ou key='value' ou key"""
        name = ""
        while not self._eof() and not self._peek().isspace() and self._peek() not in ("=", ">", "/"):
            name += self._next_char()
            
        if not name:
            # Caso de loop infinito com caracteres estranhos
            self._next_char()
            return "", ""
            
        self._consume_whitespace()
        value = ""
        
        if self._peek() == "=":
            self._next_char() # Skip =
            self._consume_whitespace()
            quote = self._peek()
            if quote in ('"', "'"):
                self._next_char() # Skip quote
                while not self._eof() and self._peek() != quote:
                    value += self._next_char()
                if not self._eof():
                    self._next_char() # Skip closing quote
            else:
                while not self._eof() and not self._peek().isspace() and self._peek() not in (">", "/"):
                    value += self._next_char()
                    
        return name, value
