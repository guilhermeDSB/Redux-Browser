"""
Redux Browser — Configuração de Motores de Busca
Lista de motores de busca focados em privacidade e populares.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SearchEngine:
    name: str
    url_template: str  # {query} será substituído pela busca
    suggest_url: str = ""  # URL de sugestões (opcional)
    icon: str = ""  # emoji ou caminho
    is_private: bool = False


# Motores de busca focados em privacidade
PRIVATE_ENGINES = [
    SearchEngine(
        name="DuckDuckGo",
        url_template="https://duckduckgo.com/?q={query}",
        suggest_url="https://duckduckgo.com/ac/?q={query}&type=list",
        icon="🦆",
        is_private=True
    ),
    SearchEngine(
        name="Brave Search",
        url_template="https://search.brave.com/search?q={query}",
        icon="🦁",
        is_private=True
    ),
    SearchEngine(
        name="Startpage",
        url_template="https://www.startpage.com/do/dsearch?query={query}",
        icon="🔒",
        is_private=True
    ),
    SearchEngine(
        name="SearXNG",
        url_template="https://searx.be/search?q={query}",
        icon="🔍",
        is_private=True
    ),
    SearchEngine(
        name="Qwant",
        url_template="https://www.qwant.com/?q={query}",
        icon="🌐",
        is_private=True
    ),
    SearchEngine(
        name="Mojeek",
        url_template="https://www.mojeek.com/search?q={query}",
        icon="🔎",
        is_private=True
    ),
    SearchEngine(
        name="Ecosia",
        url_template="https://www.ecosia.org/search?q={query}",
        icon="🌳",
        is_private=False
    ),
]

# Motores de busca populares
POPULAR_ENGINES = [
    SearchEngine(
        name="Google",
        url_template="https://www.google.com/search?q={query}",
        suggest_url="https://suggestqueries.google.com/complete/search?client=firefox&q={query}",
        icon="G"
    ),
    SearchEngine(
        name="Bing",
        url_template="https://www.bing.com/search?q={query}",
        icon="B"
    ),
    SearchEngine(
        name="Yahoo",
        url_template="https://search.yahoo.com/search?p={query}",
        icon="Y"
    ),
    SearchEngine(
        name="Wikipedia",
        url_template="https://en.wikipedia.org/wiki/Special:Search?search={query}",
        icon="W"
    ),
    SearchEngine(
        name="GitHub",
        url_template="https://github.com/search?q={query}",
        icon="GH"
    ),
    SearchEngine(
        name="Stack Overflow",
        url_template="https://stackoverflow.com/search?q={query}",
        icon="SO"
    ),
]

# Todos os motores
ALL_ENGINES = PRIVATE_ENGINES + POPULAR_ENGINES

# Padrão: DuckDuckGo (focado em privacidade)
DEFAULT_ENGINE = PRIVATE_ENGINES[0]

# Motor padrão atual (pode ser trocado pelo usuário)
_current_engine = DEFAULT_ENGINE

# Restaurar motor de busca salvo nas preferências
try:
    from browser.config.settings_manager import get_settings
    _saved_name = get_settings().get("search_engine", "DuckDuckGo")
    for _eng in ALL_ENGINES:
        if _eng.name == _saved_name:
            _current_engine = _eng
            break
except Exception:
    pass


def get_current_engine() -> SearchEngine:
    return _current_engine


def set_current_engine(engine: SearchEngine):
    global _current_engine
    _current_engine = engine
    # Persistir a escolha
    try:
        from browser.config.settings_manager import get_settings
        get_settings().set("search_engine", engine.name)
    except Exception:
        pass


def get_engine_by_name(name: str) -> SearchEngine:
    for engine in ALL_ENGINES:
        if engine.name.lower() == name.lower():
            return engine
    return DEFAULT_ENGINE


def build_search_url(query: str, engine: SearchEngine = None) -> str:
    if engine is None:
        engine = _current_engine
    return engine.url_template.replace("{query}", query.replace(" ", "+"))


def is_search_query(text: str) -> bool:
    """Verifica se o texto é uma query de busca (não uma URL)."""
    text = text.strip()
    if not text:
        return False
    if "://" in text:
        return False
    if " " in text:
        return True
    if "." not in text:
        return True
    return False
