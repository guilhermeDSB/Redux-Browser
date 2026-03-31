"""
Redux Browser — Tokenizador para Matching de Regras de Bloqueio

Inspirado em Brave's adblock-rust e uBlock Origin:
  - Divide URLs e padrões ABP em tokens numéricos (hashes)
  - Seleciona o "melhor" token (mais raro / seletivo) para indexação em hash-map
  - Permite lookup O(1) em vez de O(n) linear scan de regras

Separadores reconhecidos: / . ? = & - _ : ;
Tokens com menos de 2 caracteres ou muito genéricos são ignorados.
"""

from __future__ import annotations

import re
from typing import Sequence

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Regex para dividir em tokens alfanuméricos (2+ caracteres)
_TOKEN_RE = re.compile(r"[a-z0-9%]{2,}", re.IGNORECASE)

# Tokens muito comuns na web — não são bons para indexação
_BAD_TOKENS: frozenset[str] = frozenset({
    "http", "https", "www", "com", "net", "org", "js", "css", "php",
    "html", "htm", "asp", "aspx", "json", "xml", "png", "jpg", "jpeg",
    "gif", "svg", "ico", "woff", "woff2", "ttf", "eot", "mp4", "mp3",
    "webp", "webm", "index", "en", "us", "api", "static", "cdn",
    "min", "src", "img", "lib", "the", "and",
})

# Token especial para regras que não possuem nenhum token adequado
# (precisam ser verificadas contra toda requisição)
EMPTY_TOKEN: int = 0


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[int]:
    """
    Extrai tokens numéricos (hashes FNV-1a) de uma string (URL ou padrão).

    Retorna lista de hashes inteiros. Tokens ruins (genéricos) são filtrados.
    """
    tokens: list[int] = []
    for m in _TOKEN_RE.finditer(text.lower()):
        word = m.group()
        if word not in _BAD_TOKENS and len(word) >= 2:
            tokens.append(_fnv1a_32(word))
    return tokens


def tokenize_pattern(pattern: str) -> list[int]:
    """
    Tokeniza um padrão ABP, removendo wildcards e âncoras antes.

    Ex: "||ads.example.com^" → tokens de "ads", "example"
        "/banner/*/ad.js" → tokens de "banner", "ad"
    """
    # Remover âncoras ABP
    p = pattern
    if p.startswith("||"):
        p = p[2:]
    elif p.startswith("|"):
        p = p[1:]
    if p.endswith("|"):
        p = p[:-1]
    if p.endswith("^"):
        p = p[:-1]

    # Remover wildcards — dividir em pedaços sem *
    parts = p.split("*")

    tokens: list[int] = []
    for part in parts:
        for m in _TOKEN_RE.finditer(part.lower()):
            word = m.group()
            if word not in _BAD_TOKENS and len(word) >= 2:
                tokens.append(_fnv1a_32(word))
    return tokens


def find_best_token(tokens: Sequence[int],
                    token_histogram: dict[int, int] | None = None) -> int:
    """
    Seleciona o token mais seletivo (menos frequente) para indexação.

    Se ``token_histogram`` for fornecido, usa contagem de frequência real.
    Caso contrário, retorna o primeiro token disponível.

    Retorna ``EMPTY_TOKEN`` se a lista de tokens estiver vazia.
    """
    if not tokens:
        return EMPTY_TOKEN

    if token_histogram is None:
        # Sem histograma, retorna o primeiro token (heurística simples)
        return tokens[0]

    best = EMPTY_TOKEN
    best_count = float("inf")
    for t in tokens:
        count = token_histogram.get(t, 0)
        if count < best_count:
            best_count = count
            best = t
    return best


# ---------------------------------------------------------------------------
# Hashing FNV-1a 32-bit (rápido, boa distribuição)
# ---------------------------------------------------------------------------

_FNV_OFFSET_32 = 0x811C9DC5
_FNV_PRIME_32 = 0x01000193
_FNV_MASK_32 = 0xFFFFFFFF


def _fnv1a_32(s: str) -> int:
    """Hash FNV-1a 32-bit de uma string."""
    h = _FNV_OFFSET_32
    for c in s:
        h ^= ord(c)
        h = (h * _FNV_PRIME_32) & _FNV_MASK_32
    return h
