"""
Redux Browser — Motor de Bloqueio de Anúncios (estilo Brave / uBlock Origin)

Parser de filtros no formato Adblock Plus (ABP):
  - Regras de rede:  ||ads.example.com^  (bloqueia URLs)
  - Exceções:        @@||example.com^    (permite URLs)
  - Opções:          $script,image,third-party,domain=...
  - Regras cosméticas: ##.ad-banner     (oculta elementos)
  - Exceções cosméticas: #@#.ad-banner  (permite elementos)

Listas padrão (ativadas por padrão):
  - EasyList
  - EasyPrivacy
  - Lista BR (Adblock Warning Removal + Portuguese)

Performance:
  - Token hash-map para lookup O(1) de regras de rede (Brave-style)
  - Regras de hostname puro em set() para O(1) exact match
  - LazyRegex: compilação de regex sob demanda com descarte LRU
  - AdBlockRequest: pré-parseia URL uma vez, reutiliza no pipeline
  - Cache serializado em pickle para reload < 1s
"""

from __future__ import annotations

import os
import re
import pickle
import hashlib
import threading
from enum import Enum
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from browser.security.adblock_tokenizer import (
    tokenize_pattern, find_best_token, EMPTY_TOKEN,
)

if TYPE_CHECKING:
    from browser.security.adblock_request import AdBlockRequest


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ADBLOCK_DIR = os.path.expanduser("~/.redux_browser/adblock")

# Listas padrão
DEFAULT_FILTER_LISTS = {
    "easylist": {
        "name": "EasyList",
        "url": "https://easylist.to/easylist/easylist.txt",
        "enabled": True,
    },
    "easyprivacy": {
        "name": "EasyPrivacy",
        "url": "https://easylist.to/easylist/easyprivacy.txt",
        "enabled": True,
    },
    "peter_lowe": {
        "name": "Peter Lowe's Ad Server List",
        "url": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=adblockplus&showintro=0&mimetype=plaintext",
        "enabled": True,
    },
}

# Regras embutidas mínimas (proteção instantânea antes de baixar listas)
BUILTIN_RULES = """
||doubleclick.net^
||googlesyndication.com^
||googleadservices.com^
||google-analytics.com^
||googletagmanager.com^
||facebook.com/tr^
||facebook.net/signals^
||adnxs.com^
||adsrvr.org^
||advertising.com^
||outbrain.com^
||taboola.com^
||criteo.com^
||criteo.net^
||amazon-adsystem.com^
||moatads.com^
||scorecardresearch.com^
||quantserve.com^
||bluekai.com^
||exelator.com^
||turn.com^
||chartbeat.com^
||hotjar.com^
||mixpanel.com^
||segment.io^
||amplitude.com^
||branch.io^
||adjust.com^
||appsflyer.com^
||ads.yahoo.com^
||ad.doubleclick.net^
||pagead2.googlesyndication.com^
||tpc.googlesyndication.com^
||static.ads-twitter.com^
||analytics.twitter.com^
||ads-api.twitter.com^
||ads.linkedin.com^
||px.ads.linkedin.com^
||snap.licdn.com^
||bat.bing.com^
||ads.reddit.com^
||events.reddit.com^
||pixel.reddit.com^
||stats.wp.com^
||pixel.wp.com^
||connect.facebook.net/en_US/fbevents.js
||static.doubleclick.net^
||ad.atdmt.com^
||adserver.yahoo.com^
##.ad-banner
##.ad-container
##.ad-wrapper
##.ad-slot
##.ad-unit
##.adsbygoogle
##.ad-placement
##[id^="google_ads"]
##[id^="div-gpt-ad"]
##.sponsored-content
##.sponsored-post
##ins.adsbygoogle
##.ad-leaderboard
##.ad-sidebar
##.ad-footer
""".strip()


class AdBlockLevel(Enum):
    """Níveis de bloqueio de anúncios."""
    OFF = "off"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


# ---------------------------------------------------------------------------
# LazyRegex — compilação sob demanda com descarte LRU
# ---------------------------------------------------------------------------

class LazyRegex:
    """
    Wrapper que armazena o padrão regex como string e só compila sob demanda.
    Permite serialização via pickle (re.Pattern não é serializável facilmente).
    Implementa descarte LRU global para limitar uso de memória.
    """

    _MAX_COMPILED = 50_000
    _compiled_cache: dict[str, re.Pattern] = {}
    _access_order: list[str] = []
    _lock = threading.Lock()

    __slots__ = ("_pattern_str", "_flags")

    def __init__(self, pattern_str: str, flags: int = re.IGNORECASE):
        self._pattern_str = pattern_str
        self._flags = flags

    @property
    def pattern(self) -> str:
        return self._pattern_str

    def search(self, text: str):
        """Compila sob demanda e faz search."""
        compiled = LazyRegex._compiled_cache.get(self._pattern_str)
        if compiled is None:
            try:
                compiled = re.compile(self._pattern_str, self._flags)
            except re.error:
                return None
            with LazyRegex._lock:
                LazyRegex._compiled_cache[self._pattern_str] = compiled
                LazyRegex._access_order.append(self._pattern_str)
                # Descarte LRU
                if len(LazyRegex._compiled_cache) > LazyRegex._MAX_COMPILED:
                    to_remove = LazyRegex._access_order[:1000]
                    for key in to_remove:
                        LazyRegex._compiled_cache.pop(key, None)
                    LazyRegex._access_order = LazyRegex._access_order[1000:]
        return compiled.search(text)

    def __bool__(self):
        return bool(self._pattern_str)

    def __getstate__(self):
        return {"pattern_str": self._pattern_str, "flags": self._flags}

    def __setstate__(self, state):
        self._pattern_str = state["pattern_str"]
        self._flags = state["flags"]


# ---------------------------------------------------------------------------
# Modelo de regras
# ---------------------------------------------------------------------------

@dataclass
class NetworkRule:
    """Uma regra de filtro de rede (bloqueio/exceção de URL)."""
    raw: str
    pattern: str
    is_exception: bool = False
    # Opções de tipo de recurso (vazio = todos)
    resource_types: set = field(default_factory=set)
    # Domínios onde a regra se aplica (vazio = todos)
    domains: dict = field(default_factory=dict)  # {domain: bool} True=include, False=exclude
    third_party: Optional[bool] = None  # None=ambos, True=só 3rd, False=só 1st
    # Para matching
    is_hostname_rule: bool = False
    hostname: str = ""
    regex: Optional[LazyRegex] = None
    # Token para indexação (Phase 1)
    token: int = EMPTY_TOKEN


@dataclass
class CosmeticRule:
    """Uma regra de filtro cosmético (ocultar elementos via CSS)."""
    raw: str
    selector: str
    is_exception: bool = False
    domains: list = field(default_factory=list)  # domínios específicos (vazio = global)


# ---------------------------------------------------------------------------
# Parser ABP
# ---------------------------------------------------------------------------

class ABPParser:
    """Parser de regras no formato Adblock Plus."""

    # Tipos de recurso ABP → nomes internos
    RESOURCE_TYPE_MAP = {
        "script": "script",
        "image": "image",
        "stylesheet": "stylesheet",
        "object": "object",
        "xmlhttprequest": "xhr",
        "subdocument": "subdocument",
        "ping": "ping",
        "websocket": "websocket",
        "font": "font",
        "media": "media",
        "other": "other",
        "popup": "popup",
        "document": "document",
        "generichide": "generichide",
        "genericblock": "genericblock",
    }

    @staticmethod
    def parse_line(line: str):
        """
        Parse uma linha de filtro ABP.
        Retorna NetworkRule, CosmeticRule, ou None (comentário/inválido).
        """
        line = line.strip()

        # Ignorar linhas vazias, comentários, e diretivas de metadados
        if not line or line.startswith("!") or line.startswith("["):
            return None

        # ----- Regras Cosméticas -----
        # Formatos: ##selector, domain##selector, #@#selector, domain#@#selector
        if "##" in line or "#@#" in line:
            return ABPParser._parse_cosmetic(line)

        # ----- Regras de Rede -----
        return ABPParser._parse_network(line)

    @staticmethod
    def _parse_cosmetic(line: str):
        """Parse regra cosmética (##, #@#, #?#)."""
        is_exception = "#@#" in line

        if is_exception:
            parts = line.split("#@#", 1)
        elif "#?#" in line:
            parts = line.split("#?#", 1)
        else:
            parts = line.split("##", 1)

        if len(parts) != 2:
            return None

        domains_str, selector = parts
        selector = selector.strip()
        if not selector:
            return None

        domains = [d.strip() for d in domains_str.split(",") if d.strip()] if domains_str else []

        return CosmeticRule(
            raw=line,
            selector=selector,
            is_exception=is_exception,
            domains=domains,
        )

    @staticmethod
    def _parse_network(line: str):
        """Parse regra de rede (||, @@, $options)."""
        is_exception = line.startswith("@@")
        if is_exception:
            line = line[2:]

        # Separar padrão das opções
        options_str = ""
        if "$" in line:
            # Encontrar o último $ que não está dentro de regex
            dollar_pos = line.rfind("$")
            if dollar_pos > 0:
                options_str = line[dollar_pos + 1:]
                line = line[:dollar_pos]

        pattern = line.strip()
        if not pattern:
            return None

        # Parse opções
        resource_types = set()
        domains = {}
        third_party = None

        if options_str:
            for opt in options_str.split(","):
                opt = opt.strip().lower()
                if not opt:
                    continue

                if opt == "third-party":
                    third_party = True
                elif opt == "~third-party" or opt == "first-party":
                    third_party = False
                elif opt.startswith("domain="):
                    domain_str = opt[7:]
                    for d in domain_str.split("|"):
                        d = d.strip()
                        if d.startswith("~"):
                            domains[d[1:]] = False
                        elif d:
                            domains[d] = True
                elif opt in ABPParser.RESOURCE_TYPE_MAP:
                    resource_types.add(ABPParser.RESOURCE_TYPE_MAP[opt])
                elif opt.startswith("~") and opt[1:] in ABPParser.RESOURCE_TYPE_MAP:
                    pass  # Exclusões de tipo são ignoradas por simplicidade

        # Detectar regras de hostname puro: ||hostname^
        # Só usa fast-path de hostname se NÃO há opções de tipo/third-party
        is_hostname = False
        hostname = ""
        if pattern.startswith("||") and pattern.endswith("^"):
            candidate = pattern[2:-1]
            # Hostname puro: só alfanuméricos, pontos e hífens
            # Regras com resource_types ou third-party precisam passar por _matches_rule
            if candidate and re.match(r'^[a-zA-Z0-9.\-]+$', candidate) \
                    and not resource_types and third_party is None:
                is_hostname = True
                hostname = candidate.lower()

        # Compilar regex para regras com wildcards
        compiled_regex = None
        if not is_hostname:
            compiled_regex = ABPParser._compile_pattern(pattern)

        # Calcular token para indexação hash-map
        rule_token = EMPTY_TOKEN
        if not is_hostname:
            tokens = tokenize_pattern(pattern)
            rule_token = find_best_token(tokens)

        return NetworkRule(
            raw=("@@" if is_exception else "") + pattern + ("$" + options_str if options_str else ""),
            pattern=pattern,
            is_exception=is_exception,
            resource_types=resource_types,
            domains=domains,
            third_party=third_party,
            is_hostname_rule=is_hostname,
            hostname=hostname,
            regex=compiled_regex,
            token=rule_token,
        )

    @staticmethod
    def _compile_pattern(pattern: str) -> Optional[LazyRegex]:
        """Converte padrão ABP em LazyRegex (compila sob demanda)."""
        try:
            # Remover || do início (significa início de domínio)
            p = pattern
            if p.startswith("||"):
                p = p[2:]
                prefix = r"(?:^|://|\.)"
            elif p.startswith("|"):
                p = p[1:]
                prefix = "^"
            else:
                prefix = ""

            if p.endswith("|"):
                p = p[:-1]
                suffix = "$"
            else:
                suffix = ""

            # Escapar caracteres especiais, depois converter wildcards ABP
            p = re.escape(p)
            p = p.replace(r"\*", ".*")          # * → .*
            p = p.replace(r"\^", r"(?:[^\w.%-]|$)")  # ^ → separador
            p = p.replace(r"\|", "|")

            regex_str = prefix + p + suffix
            return LazyRegex(regex_str, re.IGNORECASE)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

class AdBlockEngine:
    """
    Motor de bloqueio de anúncios do Redux Browser.

    Indexa regras por domínio para lookup rápido O(1).
    Suporta listas no formato ABP (EasyList, EasyPrivacy, etc).
    """

    def __init__(self):
        self.level: AdBlockLevel = AdBlockLevel.STANDARD
        self._lock = threading.Lock()

        # Regras de rede — hostname puro (O(1) lookup)
        self._hostname_blocks: set = set()           # hostnames bloqueados
        self._hostname_exceptions: set = set()       # hostnames permitidos

        # Regras de rede — token hash-map (O(1) bucket lookup)
        # {token_hash: [NetworkRule, ...]}
        self._token_index_blocks: dict[int, list[NetworkRule]] = {}
        self._token_index_exceptions: dict[int, list[NetworkRule]] = {}

        # Regras cosméticas
        self._global_cosmetic: list = []             # seletores globais (sem domínio)
        self._domain_cosmetic: dict = {}             # {domain: [selectors]}
        self._cosmetic_exceptions: dict = {}         # {domain: set(selectors)} ou global

        # Domínios em whitelist (pelo usuário)
        self._whitelist: set = set()

        # Stats
        self.total_rules = 0
        self.blocked_count = 0
        self._blocked_per_domain: dict = {}

        # Estado de carregamento
        self._loaded = False
        self._loading = False

        # Histograma de tokens para seleção de "melhor token"
        self._token_histogram: dict[int, int] = {}

        # Carregar regras embutidas imediatamente
        self._load_builtin_rules()

    def _load_builtin_rules(self):
        """Carrega regras embutidas mínimas para proteção instantânea."""
        for line in BUILTIN_RULES.split("\n"):
            rule = ABPParser.parse_line(line)
            if rule:
                self._add_rule(rule)

    def _add_rule(self, rule):
        """Adiciona uma regra parsed ao engine."""
        if isinstance(rule, CosmeticRule):
            if rule.is_exception:
                if rule.domains:
                    for d in rule.domains:
                        self._cosmetic_exceptions.setdefault(d, set()).add(rule.selector)
                else:
                    self._cosmetic_exceptions.setdefault("*", set()).add(rule.selector)
            else:
                if rule.domains:
                    for d in rule.domains:
                        self._domain_cosmetic.setdefault(d, []).append(rule.selector)
                else:
                    self._global_cosmetic.append(rule.selector)
        elif isinstance(rule, NetworkRule):
            if rule.is_exception:
                if rule.is_hostname_rule:
                    self._hostname_exceptions.add(rule.hostname)
                else:
                    # Indexar exceção por token
                    bucket = self._token_index_exceptions.setdefault(rule.token, [])
                    bucket.append(rule)
                    self._token_histogram[rule.token] = self._token_histogram.get(rule.token, 0) + 1
            else:
                if rule.is_hostname_rule:
                    self._hostname_blocks.add(rule.hostname)
                else:
                    # Indexar bloqueio por token
                    bucket = self._token_index_blocks.setdefault(rule.token, [])
                    bucket.append(rule)
                    self._token_histogram[rule.token] = self._token_histogram.get(rule.token, 0) + 1
        self.total_rules += 1

    # ----- API pública -----

    def should_block(self, url_or_request, resource_type: str = "",
                     first_party_url: str = "") -> bool:
        """
        Verifica se uma URL deve ser bloqueada.

        Aceita tanto a API legada (strings) quanto um AdBlockRequest pré-parseado.

        Args:
            url_or_request: URL string ou AdBlockRequest pré-parseado
            resource_type: Tipo do recurso ('script', 'image', etc.) — ignorado se AdBlockRequest
            first_party_url: URL da página principal — ignorado se AdBlockRequest

        Returns:
            True se a URL deve ser bloqueada
        """
        if self.level == AdBlockLevel.OFF:
            return False

        # Suportar ambas as APIs
        from browser.security.adblock_request import AdBlockRequest
        if isinstance(url_or_request, AdBlockRequest):
            req = url_or_request
        else:
            req = AdBlockRequest.from_urls(
                str(url_or_request), first_party_url, resource_type
            )

        url_lower = req.url
        url_domain = req.hostname
        source_domain = req.source_hostname or url_domain

        # Verificar whitelist do usuário
        if source_domain and self._is_whitelisted_domain(source_domain):
            return False

        # 1. Verificar exceções de hostname (@@||host^)
        if url_domain and self._matches_hostname_set(url_domain, self._hostname_exceptions):
            return False

        # 2. Verificar exceções de rede via token index
        if self._check_token_index(self._token_index_exceptions, req):
            return False

        # 3. Verificar bloqueios de hostname (||host^)
        if url_domain and self._matches_hostname_set(url_domain, self._hostname_blocks):
            self._record_block(url_domain)
            return True

        # 4. Verificar regras de rede via token index
        if self._check_token_index(self._token_index_blocks, req):
            self._record_block(url_domain)
            return True

        return False

    def _check_token_index(self, index: dict[int, list[NetworkRule]],
                           req: "AdBlockRequest") -> bool:
        """
        Verifica se alguma regra no token-index corresponde à requisição.

        Para cada token da URL, busca o bucket correspondente no índice
        e testa as regras. Também verifica o bucket EMPTY_TOKEN (regras
        sem token útil que precisam ser testadas contra tudo).
        """
        # Tokens específicos da URL
        checked_buckets: set[int] = set()
        for token in req.tokens:
            if token in checked_buckets:
                continue
            checked_buckets.add(token)
            bucket = index.get(token)
            if bucket:
                for rule in bucket:
                    if self._matches_rule(rule, req.url, req.resource_type,
                                          req.source_url):
                        return True

        # Bucket de regras "sem token" (EMPTY_TOKEN = 0)
        if EMPTY_TOKEN not in checked_buckets:
            bucket = index.get(EMPTY_TOKEN)
            if bucket:
                for rule in bucket:
                    if self._matches_rule(rule, req.url, req.resource_type,
                                          req.source_url):
                        return True

        return False

    def get_cosmetic_selectors(self, domain: str) -> list:
        """
        Retorna seletores CSS para ocultar elementos numa página.

        Args:
            domain: O domínio da página

        Returns:
            Lista de seletores CSS
        """
        if self.level == AdBlockLevel.OFF:
            return []

        if self._is_whitelisted_domain(domain):
            return []

        domain = domain.lower()
        selectors = []

        # Coletar exceções aplicáveis: globais + do domínio e seus pais
        global_exceptions = self._cosmetic_exceptions.get("*", set())
        domain_exceptions = set()
        parts = domain.split(".")
        for i in range(len(parts)):
            d = ".".join(parts[i:])
            domain_exceptions.update(self._cosmetic_exceptions.get(d, set()))

        # Seletores globais (excluir exceções globais E do domínio)
        for sel in self._global_cosmetic:
            if sel not in global_exceptions and sel not in domain_exceptions:
                selectors.append(sel)

        # Seletores específicos do domínio

        # Verificar domínio e subdomínios
        parts = domain.split(".")
        for i in range(len(parts)):
            d = ".".join(parts[i:])
            for sel in self._domain_cosmetic.get(d, []):
                if sel not in domain_exceptions and sel not in global_exceptions:
                    selectors.append(sel)

        # No modo agressivo, adicionar seletores extras
        if self.level == AdBlockLevel.AGGRESSIVE:
            selectors.extend(self._get_aggressive_selectors())

        return list(dict.fromkeys(selectors))  # Dedup mantendo ordem

    def is_whitelisted(self, domain: str) -> bool:
        """Verifica se um domínio está na whitelist do usuário."""
        return self._is_whitelisted_domain(domain)

    def toggle_whitelist(self, domain: str) -> bool:
        """Alterna um domínio na whitelist. Retorna novo estado."""
        domain = domain.lower().strip()
        if domain in self._whitelist:
            self._whitelist.discard(domain)
            return False
        else:
            self._whitelist.add(domain)
            return True

    def set_whitelist(self, domains: list):
        """Define a whitelist completa."""
        self._whitelist = set(d.lower().strip() for d in domains if d.strip())

    def get_whitelist(self) -> list:
        """Retorna lista de domínios em whitelist."""
        return sorted(self._whitelist)

    def get_blocked_count(self) -> int:
        """Retorna total de requisições bloqueadas."""
        return self.blocked_count

    def reset_stats(self):
        """Reseta contadores de bloqueio."""
        self.blocked_count = 0
        self._blocked_per_domain.clear()

    # ----- Carregamento de filtros -----

    def load_filters_from_text(self, text: str):
        """Carrega regras a partir de texto (conteúdo de um arquivo de filtro)."""
        count = 0
        for line in text.split("\n"):
            rule = ABPParser.parse_line(line)
            if rule:
                self._add_rule(rule)
                count += 1
        return count

    def load_filters_from_file(self, filepath: str) -> int:
        """Carrega regras de um arquivo."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return self.load_filters_from_text(f.read())
        except Exception as e:
            print(f"[AdBlock] Erro ao carregar {filepath}: {e}")
            return 0

    def save_cache(self):
        """Serializa estado para reload rápido."""
        os.makedirs(ADBLOCK_DIR, exist_ok=True)
        cache_path = os.path.join(ADBLOCK_DIR, "engine_cache.pkl")
        try:
            data = {
                "hostname_blocks": self._hostname_blocks,
                "hostname_exceptions": self._hostname_exceptions,
                "token_index_blocks": self._token_index_blocks,
                "token_index_exceptions": self._token_index_exceptions,
                "global_cosmetic": self._global_cosmetic,
                "domain_cosmetic": self._domain_cosmetic,
                "cosmetic_exceptions": self._cosmetic_exceptions,
                "total_rules": self.total_rules,
                "token_histogram": self._token_histogram,
            }
            with open(cache_path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"[AdBlock] Erro ao salvar cache: {e}")

    def load_cache(self) -> bool:
        """Tenta carregar de cache serializado."""
        cache_path = os.path.join(ADBLOCK_DIR, "engine_cache.pkl")
        if not os.path.exists(cache_path):
            return False
        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)
            self._hostname_blocks = data.get("hostname_blocks", set())
            self._hostname_exceptions = data.get("hostname_exceptions", set())
            self._token_index_blocks = data.get("token_index_blocks", {})
            self._token_index_exceptions = data.get("token_index_exceptions", {})
            self._global_cosmetic = data.get("global_cosmetic", [])
            self._domain_cosmetic = data.get("domain_cosmetic", {})
            self._cosmetic_exceptions = data.get("cosmetic_exceptions", {})
            self.total_rules = data.get("total_rules", 0)
            self._token_histogram = data.get("token_histogram", {})
            self._loaded = True
            return True
        except Exception as e:
            print(f"[AdBlock] Cache inválido, recarregando: {e}")
            return False

    def load_all_lists(self, force_download: bool = False):
        """
        Carrega todas as listas de filtro configuradas.
        Tenta cache primeiro, depois arquivos locais, por último download.
        """
        if self._loading:
            return
        self._loading = True

        try:
            from browser.config.settings_manager import get_settings
            settings = get_settings()
            lists_config = settings.get("adblock_lists", DEFAULT_FILTER_LISTS)

            # Tentar cache primeiro (se não forçado)
            if not force_download and self.load_cache():
                self._loading = False
                self._loaded = True
                print(f"[AdBlock] Cache carregado: {self.total_rules} regras")
                return

            # Carregar de arquivos locais ou baixar
            os.makedirs(ADBLOCK_DIR, exist_ok=True)

            for list_id, list_info in lists_config.items():
                if not list_info.get("enabled", True):
                    continue

                local_path = os.path.join(ADBLOCK_DIR, f"{list_id}.txt")

                if os.path.exists(local_path) and not force_download:
                    count = self.load_filters_from_file(local_path)
                    print(f"[AdBlock] {list_info.get('name', list_id)}: {count} regras (local)")
                else:
                    # Download
                    count = self._download_list(list_id, list_info)
                    print(f"[AdBlock] {list_info.get('name', list_id)}: {count} regras (download)")

            # Carregar filtros customizados do usuário
            custom = settings.get("adblock_custom_filters", "")
            if custom.strip():
                count = self.load_filters_from_text(custom)
                print(f"[AdBlock] Filtros customizados: {count} regras")

            # Salvar cache para próximo startup
            self.save_cache()
            self._loaded = True

        except Exception as e:
            print(f"[AdBlock] Erro ao carregar listas: {e}")
        finally:
            self._loading = False

    def _download_list(self, list_id: str, list_info: dict) -> int:
        """Baixa uma lista de filtros."""
        url = list_info.get("url", "")
        if not url:
            return 0

        try:
            import requests
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Redux Browser AdBlock/1.0",
            })
            resp.raise_for_status()

            local_path = os.path.join(ADBLOCK_DIR, f"{list_id}.txt")
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(resp.text)

            return self.load_filters_from_text(resp.text)
        except Exception as e:
            print(f"[AdBlock] Falha ao baixar {list_info.get('name', list_id)}: {e}")
            return 0

    # ----- Internos -----

    def _extract_domain(self, url: str) -> str:
        """Extrai domínio de uma URL."""
        try:
            # Remove protocolo
            if "://" in url:
                url = url.split("://", 1)[1]
            # Remove path
            domain = url.split("/", 1)[0]
            # Remove porta
            domain = domain.split(":", 1)[0]
            return domain.lower()
        except Exception:
            return ""

    def _matches_hostname_set(self, url_domain: str, hostname_set: set) -> bool:
        """Verifica se o domínio ou qualquer ancestral está no set."""
        if url_domain in hostname_set:
            return True
        parts = url_domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in hostname_set:
                return True
        return False

    def _is_whitelisted_domain(self, domain: str) -> bool:
        """Verifica se o domínio está na whitelist do usuário."""
        domain = domain.lower()
        if domain in self._whitelist:
            return True
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self._whitelist:
                return True
        return False

    def _matches_rule(self, rule: NetworkRule, url: str,
                      resource_type: str, first_party_url: str) -> bool:
        """Verifica se uma URL corresponde a uma regra de rede."""
        # Verificar tipo de recurso
        if rule.resource_types and resource_type not in rule.resource_types:
            return False

        # Verificar third-party
        if rule.third_party is not None:
            url_domain = self._extract_domain(url)
            fp_domain = self._extract_domain(first_party_url) if first_party_url else ""
            is_third_party = fp_domain and url_domain and not (
                url_domain == fp_domain or
                url_domain.endswith("." + fp_domain) or
                fp_domain.endswith("." + url_domain)
            )
            if rule.third_party != is_third_party:
                return False

        # Verificar domínios da regra ($domain=)
        if rule.domains:
            fp_domain = self._extract_domain(first_party_url) if first_party_url else ""
            if not self._domain_matches(fp_domain, rule.domains):
                return False

        # Verificar padrão regex
        if rule.regex:
            return bool(rule.regex.search(url))

        return False

    def _domain_matches(self, domain: str, rule_domains: dict) -> bool:
        """Verifica se o domínio corresponde às restrições da regra."""
        if not domain:
            return not any(v for v in rule_domains.values())

        has_includes = any(v for v in rule_domains.values())

        for d, included in rule_domains.items():
            if domain == d or domain.endswith("." + d):
                return included

        return not has_includes

    def _record_block(self, domain: str):
        """Registra um bloqueio para estatísticas."""
        self.blocked_count += 1
        self._blocked_per_domain[domain] = self._blocked_per_domain.get(domain, 0) + 1

    def _get_aggressive_selectors(self) -> list:
        """Seletores extras para modo agressivo."""
        return [
            "[class*='sponsor']",
            "[class*='promoted']",
            "[class*='advertisement']",
            "[id*='sponsor']",
            "[id*='promoted']",
            "[data-ad]",
            "[data-ads]",
            "[data-ad-slot]",
            "[data-ad-client]",
            "[data-google-query-id]",
            "iframe[src*='doubleclick']",
            "iframe[src*='googlesyndication']",
            "iframe[src*='facebook.com/plugins']",
            ".cookie-banner",
            ".cookie-consent",
            ".cookie-notice",
            "#cookie-banner",
            "#cookie-consent",
            "#cookie-notice",
            ".newsletter-popup",
            ".newsletter-modal",
            ".subscribe-popup",
        ]
