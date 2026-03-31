"""
Testes para os módulos Phase 1: adblock_tokenizer e adblock_request.

Valida:
  - Tokenização de URLs e padrões ABP
  - Hashing FNV-1a 32-bit
  - Seleção de melhor token
  - AdBlockRequest pré-parseado
  - Token hash-map matching no engine (integração)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ===========================================================================
# Tokenizer
# ===========================================================================

from browser.security.adblock_tokenizer import (
    tokenize, tokenize_pattern, find_best_token, EMPTY_TOKEN, _fnv1a_32,
)


class TestFNV1a(unittest.TestCase):
    """Testa hash FNV-1a 32-bit."""

    def test_deterministic(self):
        """Mesmo input → mesmo hash."""
        self.assertEqual(_fnv1a_32("ads"), _fnv1a_32("ads"))

    def test_different_inputs(self):
        """Inputs diferentes → hashes diferentes."""
        self.assertNotEqual(_fnv1a_32("ads"), _fnv1a_32("track"))

    def test_returns_int(self):
        """Resultado é int."""
        self.assertIsInstance(_fnv1a_32("test"), int)

    def test_32bit_range(self):
        """Hash cabe em 32 bits."""
        h = _fnv1a_32("example")
        self.assertGreaterEqual(h, 0)
        self.assertLessEqual(h, 0xFFFFFFFF)


class TestTokenize(unittest.TestCase):
    """Testa tokenize() para URLs."""

    def test_basic_url(self):
        """URL com path deve gerar tokens."""
        tokens = tokenize("https://ads.example.com/banner/ad.js")
        self.assertGreater(len(tokens), 0)
        self.assertIsInstance(tokens[0], int)

    def test_filters_bad_tokens(self):
        """Tokens genéricos (www, com, https) devem ser filtrados."""
        tokens = tokenize("https://www.example.com/index.html")
        bad_hashes = {_fnv1a_32(w) for w in ["https", "www", "com", "html", "index"]}
        for t in tokens:
            self.assertNotIn(t, bad_hashes)

    def test_empty_string(self):
        """String vazia → lista vazia."""
        self.assertEqual(tokenize(""), [])

    def test_only_bad_tokens(self):
        """URL com apenas tokens ruins → lista vazia."""
        tokens = tokenize("https://www.com/index.html")
        self.assertEqual(tokens, [])

    def test_short_tokens_filtered(self):
        """Tokens com 1 char são filtrados."""
        # "a" e "b" < 2 chars → filtrados
        tokens = tokenize("a/b/c")
        self.assertEqual(tokens, [])


class TestTokenizePattern(unittest.TestCase):
    """Testa tokenize_pattern() para padrões ABP."""

    def test_hostname_pattern(self):
        """||ads.example.com^ deve gerar tokens de 'ads' e 'example'."""
        tokens = tokenize_pattern("||ads.example.com^")
        self.assertGreater(len(tokens), 0)
        # "ads" deve estar presente (len >= 2, not bad)
        self.assertIn(_fnv1a_32("ads"), tokens)

    def test_wildcard_pattern(self):
        """Padrão com * deve tokenizar partes sem wildcard."""
        tokens = tokenize_pattern("/banner/*/ad.js")
        self.assertIn(_fnv1a_32("banner"), tokens)

    def test_strip_anchors(self):
        """Âncoras ||, |, ^ devem ser removidas antes de tokenizar."""
        t1 = tokenize_pattern("||doubleclick.net^")
        t2 = tokenize_pattern("doubleclick.net")
        # Devem gerar o mesmo conjunto de tokens base
        self.assertEqual(set(t1), set(t2))

    def test_empty_pattern(self):
        """Padrão vazio → tokens vazios."""
        self.assertEqual(tokenize_pattern(""), [])


class TestFindBestToken(unittest.TestCase):
    """Testa find_best_token()."""

    def test_empty_list(self):
        """Lista vazia → EMPTY_TOKEN."""
        self.assertEqual(find_best_token([]), EMPTY_TOKEN)

    def test_no_histogram(self):
        """Sem histograma, retorna primeiro token."""
        tokens = [111, 222, 333]
        self.assertEqual(find_best_token(tokens), 111)

    def test_with_histogram(self):
        """Com histograma, retorna token menos frequente."""
        tokens = [111, 222, 333]
        histogram = {111: 100, 222: 5, 333: 50}
        self.assertEqual(find_best_token(tokens, histogram), 222)

    def test_empty_token_constant(self):
        """EMPTY_TOKEN deve ser 0."""
        self.assertEqual(EMPTY_TOKEN, 0)


# ===========================================================================
# AdBlockRequest
# ===========================================================================

from browser.security.adblock_request import AdBlockRequest


class TestAdBlockRequest(unittest.TestCase):
    """Testa a classe AdBlockRequest."""

    def test_from_urls_basic(self):
        """from_urls deve criar request com campos calculados."""
        req = AdBlockRequest.from_urls(
            "https://ads.example.com/ad.js",
            "https://mysite.com/page",
            "script"
        )
        self.assertEqual(req.hostname, "ads.example.com")
        self.assertEqual(req.source_hostname, "mysite.com")
        self.assertEqual(req.resource_type, "script")
        self.assertTrue(req.is_third_party)

    def test_same_party(self):
        """Mesmo domínio → is_third_party = False."""
        req = AdBlockRequest.from_urls(
            "https://cdn.example.com/lib.js",
            "https://www.example.com/page"
        )
        self.assertFalse(req.is_third_party)

    def test_third_party_detection(self):
        """Domínios diferentes → is_third_party = True."""
        req = AdBlockRequest.from_urls(
            "https://tracker.evil.com/t.js",
            "https://good.com/page"
        )
        self.assertTrue(req.is_third_party)

    def test_url_lowered(self):
        """URL deve ser normalizada em minúsculas."""
        req = AdBlockRequest.from_urls("HTTPS://ADS.EXAMPLE.COM/AD.JS")
        self.assertEqual(req.url, "https://ads.example.com/ad.js")
        self.assertEqual(req.hostname, "ads.example.com")

    def test_tokens_populated(self):
        """Tokens devem ser calculados automaticamente."""
        req = AdBlockRequest.from_urls("https://ads.example.com/banner/ad.js")
        self.assertGreater(len(req.tokens), 0)
        self.assertIsInstance(req.tokens[0], int)

    def test_no_source_url(self):
        """Sem source_url, is_third_party é None."""
        req = AdBlockRequest.from_urls("https://ads.example.com/ad.js")
        self.assertIsNone(req.is_third_party)

    def test_extract_domain_with_port(self):
        """Domínio com porta deve ser extraído corretamente."""
        req = AdBlockRequest.from_urls("https://example.com:8080/page")
        self.assertEqual(req.hostname, "example.com")


# ===========================================================================
# Integração: Token Hash-Map no Engine
# ===========================================================================

from browser.security.adblock_engine import AdBlockEngine, ABPParser, NetworkRule


class TestTokenIndexIntegration(unittest.TestCase):
    """Testa que o engine usa token hash-map corretamente."""

    def setUp(self):
        self.engine = AdBlockEngine()

    def test_regex_rule_indexed_by_token(self):
        """Regra com wildcard deve ser indexada por token no hash-map."""
        self.engine.load_filters_from_text("/banner/*/ad.js")
        # Deve ter pelo menos uma entrada no token index
        total_indexed = sum(len(v) for v in self.engine._token_index_blocks.values())
        self.assertGreater(total_indexed, 0)

    def test_regex_rule_still_blocks(self):
        """Regra com wildcard indexada por token ainda bloqueia corretamente."""
        self.engine.load_filters_from_text("/banner/*/ad.js")
        self.assertTrue(self.engine.should_block(
            "https://example.com/banner/123/ad.js"
        ))

    def test_exception_indexed_by_token(self):
        """Exceção com regex deve ser indexada no token index de exceções."""
        self.engine.load_filters_from_text("@@/safe/*/content.js")
        total_indexed = sum(len(v) for v in self.engine._token_index_exceptions.values())
        self.assertGreater(total_indexed, 0)

    def test_hostname_rules_not_in_token_index(self):
        """Regras de hostname puro NÃO devem ir para o token index."""
        engine = AdBlockEngine()
        # Limpar regras embutidas
        engine._hostname_blocks.clear()
        engine._hostname_exceptions.clear()
        engine._token_index_blocks.clear()
        engine._token_index_exceptions.clear()
        engine.total_rules = 0

        engine.load_filters_from_text("||ads.test^")
        # Deve estar no hostname set, não no token index
        self.assertIn("ads.test", engine._hostname_blocks)
        total_token = sum(len(v) for v in engine._token_index_blocks.values())
        self.assertEqual(total_token, 0)

    def test_should_block_accepts_adblock_request(self):
        """should_block deve aceitar AdBlockRequest diretamente."""
        self.engine.load_filters_from_text("||tracker.evil.com^")
        req = AdBlockRequest.from_urls("https://tracker.evil.com/pixel.js")
        self.assertTrue(self.engine.should_block(req))

    def test_should_block_backward_compatible(self):
        """should_block deve continuar aceitando strings (API legada)."""
        self.engine.load_filters_from_text("||tracker.evil.com^")
        self.assertTrue(self.engine.should_block("https://tracker.evil.com/pixel.js"))

    def test_lazy_regex_serializable(self):
        """LazyRegex deve ser serializável via pickle."""
        import pickle
        from browser.security.adblock_engine import LazyRegex

        lr = LazyRegex(r"test.*pattern", 0)
        data = pickle.dumps(lr)
        lr2 = pickle.loads(data)
        self.assertEqual(lr2.pattern, r"test.*pattern")
        # Deve funcionar após desserialização
        self.assertIsNotNone(lr2.search("test_hello_pattern"))

    def test_cache_round_trip_with_token_index(self):
        """save_cache + load_cache deve preservar token indexes."""
        engine1 = AdBlockEngine()
        engine1.load_filters_from_text("/banner/*/ad.js\n||hostname.test^")
        engine1.save_cache()

        engine2 = AdBlockEngine()
        loaded = engine2.load_cache()
        self.assertTrue(loaded)

        # Hostname restaurado
        self.assertTrue(engine2.should_block("https://hostname.test/x"))
        # Regex via token index restaurado
        self.assertTrue(engine2.should_block("https://example.com/banner/123/ad.js"))


class TestLazyRegex(unittest.TestCase):
    """Testa a classe LazyRegex."""

    def test_search_compiles_on_demand(self):
        """search() deve compilar e funcionar."""
        from browser.security.adblock_engine import LazyRegex
        lr = LazyRegex(r"ads.*banner")
        result = lr.search("https://ads.example.com/banner")
        self.assertIsNotNone(result)

    def test_no_match(self):
        """search() retorna None se não combinar."""
        from browser.security.adblock_engine import LazyRegex
        lr = LazyRegex(r"ads.*banner")
        result = lr.search("https://example.com/safe")
        self.assertIsNone(result)

    def test_bool_truthy(self):
        """LazyRegex com padrão é truthy."""
        from browser.security.adblock_engine import LazyRegex
        lr = LazyRegex(r"test")
        self.assertTrue(bool(lr))

    def test_bool_falsy(self):
        """LazyRegex sem padrão é falsy."""
        from browser.security.adblock_engine import LazyRegex
        lr = LazyRegex("")
        self.assertFalse(bool(lr))

    def test_invalid_regex(self):
        """Regex inválido deve retornar None no search sem crash."""
        from browser.security.adblock_engine import LazyRegex
        lr = LazyRegex(r"[invalid")
        result = lr.search("test")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
