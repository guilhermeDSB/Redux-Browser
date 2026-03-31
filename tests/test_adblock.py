"""
Redux Browser — Testes do sistema de Bloqueio de Anúncios
Valida o parser ABP, matching de URLs, filtros cosméticos, whitelist e cache.
"""
import unittest
import sys
import os
import tempfile
import pickle

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.security.adblock_engine import (
    ABPParser,
    NetworkRule,
    CosmeticRule,
    AdBlockEngine,
    AdBlockLevel,
)


# ===========================================================================
# ABPParser — Parsing de regras
# ===========================================================================

class TestABPParserComments(unittest.TestCase):
    """Linhas ignoráveis (comentários, diretivas, vazias)."""

    def test_empty_line(self):
        self.assertIsNone(ABPParser.parse_line(""))

    def test_comment_line(self):
        self.assertIsNone(ABPParser.parse_line("! This is a comment"))

    def test_metadata_directive(self):
        self.assertIsNone(ABPParser.parse_line("[Adblock Plus 2.0]"))

    def test_whitespace_only(self):
        self.assertIsNone(ABPParser.parse_line("   "))


class TestABPParserNetworkRules(unittest.TestCase):
    """Parse de regras de rede (bloqueio/exceção de URL)."""

    def test_simple_hostname_block(self):
        """||ads.example.com^ deve gerar regra de hostname puro."""
        rule = ABPParser.parse_line("||ads.example.com^")
        self.assertIsInstance(rule, NetworkRule)
        self.assertTrue(rule.is_hostname_rule)
        self.assertEqual(rule.hostname, "ads.example.com")
        self.assertFalse(rule.is_exception)

    def test_exception_rule(self):
        """@@||example.com^ deve gerar exceção."""
        rule = ABPParser.parse_line("@@||example.com^")
        self.assertIsInstance(rule, NetworkRule)
        self.assertTrue(rule.is_exception)
        self.assertTrue(rule.is_hostname_rule)
        self.assertEqual(rule.hostname, "example.com")

    def test_pattern_with_wildcard(self):
        """Padrão com * deve gerar regex, não hostname puro."""
        rule = ABPParser.parse_line("||example.com/ads/*")
        self.assertIsInstance(rule, NetworkRule)
        self.assertFalse(rule.is_hostname_rule)
        self.assertIsNotNone(rule.regex)

    def test_options_third_party(self):
        """$third-party deve ser parsed corretamente."""
        rule = ABPParser.parse_line("||tracker.com^$third-party")
        self.assertIsInstance(rule, NetworkRule)
        self.assertTrue(rule.third_party)

    def test_options_first_party(self):
        """$~third-party marca first-party."""
        rule = ABPParser.parse_line("||local.com^$~third-party")
        self.assertIsInstance(rule, NetworkRule)
        self.assertFalse(rule.third_party)

    def test_options_resource_types(self):
        """$script,image deve popular resource_types."""
        rule = ABPParser.parse_line("||cdn.ads.com^$script,image")
        self.assertIsInstance(rule, NetworkRule)
        self.assertIn("script", rule.resource_types)
        self.assertIn("image", rule.resource_types)

    def test_options_domain(self):
        """$domain=example.com|~sub.example.com."""
        rule = ABPParser.parse_line("||ad.com^$domain=example.com|~sub.example.com")
        self.assertIsInstance(rule, NetworkRule)
        self.assertTrue(rule.domains.get("example.com"))
        self.assertFalse(rule.domains.get("sub.example.com"))

    def test_hostname_case_insensitive(self):
        """Hostnames devem ser normalizados para lowercase."""
        rule = ABPParser.parse_line("||ADS.Example.COM^")
        self.assertIsInstance(rule, NetworkRule)
        self.assertEqual(rule.hostname, "ads.example.com")


class TestABPParserCosmeticRules(unittest.TestCase):
    """Parse de regras cosméticas (ocultação de elementos)."""

    def test_global_cosmetic(self):
        """##.ad-banner deve gerar regra cosmética global."""
        rule = ABPParser.parse_line("##.ad-banner")
        self.assertIsInstance(rule, CosmeticRule)
        self.assertEqual(rule.selector, ".ad-banner")
        self.assertFalse(rule.is_exception)
        self.assertEqual(rule.domains, [])

    def test_domain_specific_cosmetic(self):
        """example.com##.ad deve ser limitada ao domínio."""
        rule = ABPParser.parse_line("example.com##.ad")
        self.assertIsInstance(rule, CosmeticRule)
        self.assertEqual(rule.selector, ".ad")
        self.assertIn("example.com", rule.domains)

    def test_cosmetic_exception(self):
        """#@#.ad-banner é exceção cosmética."""
        rule = ABPParser.parse_line("#@#.ad-banner")
        self.assertIsInstance(rule, CosmeticRule)
        self.assertTrue(rule.is_exception)
        self.assertEqual(rule.selector, ".ad-banner")

    def test_domain_cosmetic_exception(self):
        """example.com#@#.sidebar-ad é exceção para um domínio."""
        rule = ABPParser.parse_line("example.com#@#.sidebar-ad")
        self.assertIsInstance(rule, CosmeticRule)
        self.assertTrue(rule.is_exception)
        self.assertIn("example.com", rule.domains)

    def test_multiple_domains_cosmetic(self):
        """a.com,b.com##.widget deve ter ambos os domínios."""
        rule = ABPParser.parse_line("a.com,b.com##.widget")
        self.assertIsInstance(rule, CosmeticRule)
        self.assertIn("a.com", rule.domains)
        self.assertIn("b.com", rule.domains)

    def test_attribute_selector(self):
        """##[id^=\"google_ads\"] deve funcionar."""
        rule = ABPParser.parse_line('##[id^="google_ads"]')
        self.assertIsInstance(rule, CosmeticRule)
        self.assertEqual(rule.selector, '[id^="google_ads"]')


# ===========================================================================
# AdBlockEngine — Matching de URLs
# ===========================================================================

class TestAdBlockEngineShouldBlock(unittest.TestCase):
    """Verifica should_block com regras carregadas."""

    def setUp(self):
        self.engine = AdBlockEngine()

    def test_blocks_builtin_hostname(self):
        """Hostnames das regras embutidas devem ser bloqueados."""
        self.assertTrue(self.engine.should_block("https://doubleclick.net/ad.js"))
        self.assertTrue(self.engine.should_block("https://googlesyndication.com/pagead"))

    def test_blocks_subdomain_of_builtin(self):
        """Subdomínios de hostnames bloqueados também bloqueiam."""
        self.assertTrue(self.engine.should_block("https://ad.doubleclick.net/ad"))
        self.assertTrue(self.engine.should_block(
            "https://pagead2.googlesyndication.com/pagead/show_ads.js"
        ))

    def test_allows_normal_url(self):
        """URLs normais não devem ser bloqueadas."""
        self.assertFalse(self.engine.should_block("https://www.google.com"))
        self.assertFalse(self.engine.should_block("https://github.com"))
        self.assertFalse(self.engine.should_block("https://stackoverflow.com"))

    def test_off_level_blocks_nothing(self):
        """AdBlockLevel.OFF não bloqueia nada."""
        self.engine.level = AdBlockLevel.OFF
        self.assertFalse(self.engine.should_block("https://doubleclick.net/ad.js"))

    def test_exception_overrides_block(self):
        """@@||host^ deve cancelar bloqueio de ||host^."""
        self.engine.load_filters_from_text("||blocked.test^\n@@||blocked.test^")
        self.assertFalse(self.engine.should_block("https://blocked.test/something"))

    def test_regex_rule_matching(self):
        """Regras com wildcard devem funcionar via regex."""
        self.engine.load_filters_from_text("||example.com/ads/*banner")
        self.assertTrue(self.engine.should_block("https://example.com/ads/top-banner"))
        self.assertFalse(self.engine.should_block("https://example.com/images/logo.png"))

    def test_third_party_option(self):
        """$third-party deve bloquear apenas requisições de terceiros."""
        self.engine.load_filters_from_text("||tracker.test^$third-party")
        # Third-party: first_party diferente
        self.assertTrue(self.engine.should_block(
            "https://tracker.test/pixel.gif",
            first_party_url="https://mysite.com/page"
        ))
        # First-party: mesmo domínio → não bloqueia
        self.assertFalse(self.engine.should_block(
            "https://tracker.test/pixel.gif",
            first_party_url="https://tracker.test/home"
        ))

    def test_resource_type_filter(self):
        """$script deve bloquear somente tipo 'script'."""
        self.engine.load_filters_from_text("||cdn.ads.test^$script")
        self.assertTrue(self.engine.should_block(
            "https://cdn.ads.test/ad.js", resource_type="script"
        ))
        self.assertFalse(self.engine.should_block(
            "https://cdn.ads.test/logo.png", resource_type="image"
        ))

    def test_blocked_count_increments(self):
        """Cada bloqueio deve incrementar o contador."""
        initial = self.engine.blocked_count
        self.engine.should_block("https://doubleclick.net/ad.js")
        self.assertEqual(self.engine.blocked_count, initial + 1)

    def test_reset_stats(self):
        """reset_stats deve zerar contadores."""
        self.engine.should_block("https://doubleclick.net/ad.js")
        self.engine.reset_stats()
        self.assertEqual(self.engine.blocked_count, 0)


# ===========================================================================
# AdBlockEngine — Filtros cosméticos
# ===========================================================================

class TestAdBlockEngineCosmeticSelectors(unittest.TestCase):
    """Verifica get_cosmetic_selectors."""

    def setUp(self):
        self.engine = AdBlockEngine()

    def test_global_selectors_returned(self):
        """Seletores globais (##) devem aparecer para qualquer domínio."""
        self.engine.load_filters_from_text("##.ad-banner\n##.ad-slot")
        selectors = self.engine.get_cosmetic_selectors("anything.com")
        self.assertIn(".ad-banner", selectors)
        self.assertIn(".ad-slot", selectors)

    def test_domain_specific_selectors(self):
        """Seletores de domínio devem aparecer apenas para o domínio correto."""
        self.engine.load_filters_from_text("example.com##.sidebar-ad")
        self.assertIn(".sidebar-ad", self.engine.get_cosmetic_selectors("example.com"))
        self.assertNotIn(".sidebar-ad", self.engine.get_cosmetic_selectors("other.com"))

    def test_cosmetic_exception_removes_selector(self):
        """#@# deve impedir que um seletor global apareça."""
        self.engine.load_filters_from_text("##.ad-banner\nexample.com#@#.ad-banner")
        # Para example.com, .ad-banner deve ser removido pela exceção
        selectors = self.engine.get_cosmetic_selectors("example.com")
        self.assertNotIn(".ad-banner", selectors)
        # Para outro domínio, ainda aparece
        selectors = self.engine.get_cosmetic_selectors("other.com")
        self.assertIn(".ad-banner", selectors)

    def test_off_level_returns_empty(self):
        """Nível OFF retorna lista vazia."""
        self.engine.load_filters_from_text("##.ad-banner")
        self.engine.level = AdBlockLevel.OFF
        self.assertEqual(self.engine.get_cosmetic_selectors("test.com"), [])

    def test_aggressive_adds_extras(self):
        """Modo agressivo adiciona seletores extras."""
        self.engine.level = AdBlockLevel.AGGRESSIVE
        selectors = self.engine.get_cosmetic_selectors("test.com")
        self.assertIn("[class*='sponsor']", selectors)
        self.assertIn(".cookie-banner", selectors)

    def test_no_duplicate_selectors(self):
        """Seletores duplicados devem ser removidos."""
        self.engine.load_filters_from_text("##.ad-banner\n##.ad-banner")
        selectors = self.engine.get_cosmetic_selectors("test.com")
        count = selectors.count(".ad-banner")
        self.assertEqual(count, 1)

    def test_subdomain_inherits_parent_selectors(self):
        """sub.example.com deve herdar seletores de example.com."""
        self.engine.load_filters_from_text("example.com##.site-ad")
        selectors = self.engine.get_cosmetic_selectors("sub.example.com")
        self.assertIn(".site-ad", selectors)


# ===========================================================================
# AdBlockEngine — Whitelist
# ===========================================================================

class TestAdBlockEngineWhitelist(unittest.TestCase):
    """Testa funcionalidade de whitelist do usuário."""

    def setUp(self):
        self.engine = AdBlockEngine()

    def test_whitelist_prevents_blocking(self):
        """Domínio em whitelist não deve ter anúncios bloqueados."""
        self.engine.toggle_whitelist("doubleclick.net")
        self.assertFalse(self.engine.should_block(
            "https://doubleclick.net/ad.js",
            first_party_url="https://doubleclick.net/"
        ))

    def test_whitelist_prevents_cosmetic(self):
        """Domínio em whitelist não deve receber seletores cosméticos."""
        self.engine.load_filters_from_text("##.ad-banner")
        self.engine.toggle_whitelist("safe.com")
        self.assertEqual(self.engine.get_cosmetic_selectors("safe.com"), [])

    def test_toggle_whitelist_adds_removes(self):
        """toggle_whitelist alterna entre adicionar e remover."""
        self.assertTrue(self.engine.toggle_whitelist("test.com"))   # Adiciona → True
        self.assertTrue(self.engine.is_whitelisted("test.com"))
        self.assertFalse(self.engine.toggle_whitelist("test.com"))  # Remove → False
        self.assertFalse(self.engine.is_whitelisted("test.com"))

    def test_set_whitelist_replaces(self):
        """set_whitelist substitui a lista completa."""
        self.engine.toggle_whitelist("old.com")
        self.engine.set_whitelist(["new1.com", "new2.com"])
        self.assertFalse(self.engine.is_whitelisted("old.com"))
        self.assertTrue(self.engine.is_whitelisted("new1.com"))
        self.assertTrue(self.engine.is_whitelisted("new2.com"))

    def test_get_whitelist_sorted(self):
        """get_whitelist retorna lista ordenada."""
        self.engine.set_whitelist(["zzz.com", "aaa.com", "mmm.com"])
        self.assertEqual(self.engine.get_whitelist(), ["aaa.com", "mmm.com", "zzz.com"])


# ===========================================================================
# AdBlockEngine — Carregamento de filtros
# ===========================================================================

class TestAdBlockEngineLoading(unittest.TestCase):
    """Testa carregamento de regras e cache."""

    def test_load_filters_from_text(self):
        """Carregar texto com regras deve incrementar total_rules."""
        engine = AdBlockEngine()
        initial = engine.total_rules
        count = engine.load_filters_from_text(
            "||ads.test^\n##.banner\n! comment\n||track.test^"
        )
        self.assertEqual(count, 3)  # 2 network + 1 cosmetic (comment ignored)
        self.assertEqual(engine.total_rules, initial + 3)

    def test_load_filters_from_file(self):
        """Carregar de arquivo deve funcionar."""
        engine = AdBlockEngine()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write("||file-ads.test^\n##.file-banner\n")
            tmppath = f.name
        try:
            count = engine.load_filters_from_file(tmppath)
            self.assertEqual(count, 2)
            self.assertTrue(engine.should_block("https://file-ads.test/x"))
        finally:
            os.unlink(tmppath)

    def test_save_and_load_cache(self):
        """save_cache + load_cache deve restaurar estado."""
        engine1 = AdBlockEngine()
        engine1.load_filters_from_text("||cached.test^\n##.cached-ad")
        engine1.save_cache()

        engine2 = AdBlockEngine()
        loaded = engine2.load_cache()
        self.assertTrue(loaded)
        # Hostname block restaurado
        self.assertTrue(engine2.should_block("https://cached.test/ad"))
        # Cosmetic restaurado
        selectors = engine2.get_cosmetic_selectors("any.com")
        self.assertIn(".cached-ad", selectors)

    def test_builtin_rules_loaded_on_init(self):
        """Regras embutidas devem estar carregadas no __init__."""
        engine = AdBlockEngine()
        self.assertGreater(engine.total_rules, 0)
        self.assertTrue(engine.should_block("https://doubleclick.net/ad"))


# ===========================================================================
# AdBlockEngine — Extração de domínio (internals)
# ===========================================================================

class TestAdBlockEngineDomainExtraction(unittest.TestCase):
    """Testa _extract_domain."""

    def setUp(self):
        self.engine = AdBlockEngine()

    def test_https_url(self):
        self.assertEqual(self.engine._extract_domain("https://www.example.com/path"), "www.example.com")

    def test_http_url(self):
        self.assertEqual(self.engine._extract_domain("http://example.com:8080/page"), "example.com")

    def test_no_protocol(self):
        self.assertEqual(self.engine._extract_domain("example.com/path"), "example.com")

    def test_empty_string(self):
        self.assertEqual(self.engine._extract_domain(""), "")

    def test_uppercase_normalized(self):
        self.assertEqual(self.engine._extract_domain("HTTPS://EXAMPLE.COM/PAGE"), "example.com")


if __name__ == "__main__":
    unittest.main()
