"""
Redux Browser — AdBlockRequest: representação pré-parseada de uma requisição HTTP

Em vez de re-parsear URL, hostname, tokens, third-party em cada chamada
a ``should_block``, criamos um único ``AdBlockRequest`` na camada de
interceptação (QWebEngineUrlRequestInterceptor) e reusamos em todo
o pipeline de matching.

Inspirado em adblock-rust ``Request`` e uBlock Origin ``NetFilteringEngine``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from browser.security.adblock_tokenizer import tokenize


# ---------------------------------------------------------------------------
# Helper: base domain simplificado (sem PSL completo)
# ---------------------------------------------------------------------------

def _get_base_domain(domain: str) -> str:
    """
    Extrai base domain simplificado (últimos 2 segmentos).
    Ex: "cdn.example.com" → "example.com"
        "www.example.co.uk" → "co.uk" (impreciso sem PSL, mas suficiente)
    """
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    return ".".join(parts[-2:])


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AdBlockRequest:
    """
    Representa uma requisição de rede pré-parseada para matching de adblock.

    Atributos:
        url:              URL completa em minúsculas
        hostname:         Hostname extraído (ex: "ads.example.com")
        source_url:       URL da página principal (first-party)
        source_hostname:  Hostname da página principal
        resource_type:    Tipo de recurso ABP (ex: "script", "image")
        is_third_party:   True se a requisição é cross-origin
        tokens:           Tokens numéricos (hashes) extraídos da URL
    """
    url: str
    hostname: str
    source_url: str = ""
    source_hostname: str = ""
    resource_type: str = ""
    is_third_party: Optional[bool] = None
    tokens: list[int] = field(default_factory=list)

    def __post_init__(self):
        """Calcula campos derivados automaticamente."""
        # Normalizar para minúsculas
        self.url = self.url.lower()
        self.hostname = self.hostname.lower() if self.hostname else self._extract_domain(self.url)
        self.source_url = self.source_url.lower() if self.source_url else ""
        self.source_hostname = (
            self.source_hostname.lower() if self.source_hostname
            else (self._extract_domain(self.source_url) if self.source_url else "")
        )

        # Calcular third-party se não fornecido
        if self.is_third_party is None and self.source_hostname:
            self.is_third_party = not self._is_same_party(
                self.hostname, self.source_hostname
            )

        # Tokenizar a URL
        if not self.tokens:
            self.tokens = tokenize(self.url)

    # ----- Helpers estáticos -----

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extrai hostname de uma URL."""
        try:
            if "://" in url:
                url = url.split("://", 1)[1]
            domain = url.split("/", 1)[0]
            domain = domain.split(":", 1)[0]
            return domain.lower()
        except Exception:
            return ""

    @staticmethod
    def _is_same_party(domain1: str, domain2: str) -> bool:
        """Verifica se dois domínios são same-party (mesmo eTLD+1 simplificado)."""
        if not domain1 or not domain2:
            return True
        if domain1 == domain2:
            return True
        if domain1.endswith("." + domain2) or domain2.endswith("." + domain1):
            return True
        # Comparar base domain (últimos 2 segmentos como heurística)
        base1 = _get_base_domain(domain1)
        base2 = _get_base_domain(domain2)
        return base1 == base2 and base1 != ""

    # ----- Fábrica conveniente -----

    @classmethod
    def from_urls(cls, url: str, source_url: str = "",
                  resource_type: str = "") -> "AdBlockRequest":
        """
        Cria um AdBlockRequest a partir de URLs brutas.

        Uso típico no interceptor:
            req = AdBlockRequest.from_urls(url, first_party_url, "script")
        """
        return cls(
            url=url,
            hostname="",           # será calculado em __post_init__
            source_url=source_url,
            source_hostname="",    # será calculado em __post_init__
            resource_type=resource_type,
        )
