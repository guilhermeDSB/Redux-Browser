"""
Redux Browser - Testes do sistema de Farbling (Brave-style)
Valida o motor de farbling, seeds determinísticas, e JS gerado.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.security.brave_farbling import FarblingEngine, FarblingLevel


class TestFarblingSeeds(unittest.TestCase):
    """Testa a geração determinística de seeds."""

    def test_same_domain_same_session_same_seed(self):
        """Mesmo domínio + mesma sessão = mesma seed."""
        engine = FarblingEngine()
        seed1 = engine.get_domain_seed("google.com")
        seed2 = engine.get_domain_seed("google.com")
        self.assertEqual(seed1, seed2)

    def test_different_domain_different_seed(self):
        """Domínios diferentes = seeds diferentes."""
        engine = FarblingEngine()
        seed1 = engine.get_domain_seed("google.com")
        seed2 = engine.get_domain_seed("facebook.com")
        self.assertNotEqual(seed1, seed2)

    def test_different_session_different_seed(self):
        """Sessões diferentes = seeds diferentes."""
        engine1 = FarblingEngine()
        engine2 = FarblingEngine()
        seed1 = engine1.get_domain_seed("google.com")
        seed2 = engine2.get_domain_seed("google.com")
        self.assertNotEqual(seed1, seed2)

    def test_reset_session_changes_seeds(self):
        """Reset de sessão muda todas as seeds."""
        engine = FarblingEngine()
        seed_before = engine.get_domain_seed("test.com")
        engine.reset_session()
        seed_after = engine.get_domain_seed("test.com")
        self.assertNotEqual(seed_before, seed_after)

    def test_seed_is_32_bytes(self):
        """Seeds devem ter 32 bytes (SHA-256)."""
        engine = FarblingEngine()
        seed = engine.get_domain_seed("test.com")
        self.assertEqual(len(seed), 32)


class TestFarblingLevels(unittest.TestCase):
    """Testa os diferentes níveis de farbling."""

    def test_off_returns_empty_script(self):
        """Modo OFF retorna script vazio."""
        engine = FarblingEngine(FarblingLevel.OFF)
        script = engine.generate_farbling_script("google.com")
        self.assertEqual(script, "")

    def test_balanced_returns_nonempty_script(self):
        """Modo BALANCED retorna script com conteúdo."""
        engine = FarblingEngine(FarblingLevel.BALANCED)
        script = engine.generate_farbling_script("google.com")
        self.assertTrue(len(script) > 100)

    def test_maximum_returns_longer_script(self):
        """Modo MAXIMUM retorna script maior que BALANCED."""
        engine = FarblingEngine(FarblingLevel.MAXIMUM)
        script_max = engine.generate_farbling_script("google.com")
        engine.level = FarblingLevel.BALANCED
        script_bal = engine.generate_farbling_script("google.com")
        self.assertGreater(len(script_max), len(script_bal))

    def test_balanced_does_not_change_ua(self):
        """Modo balanced NÃO altera User-Agent."""
        engine = FarblingEngine(FarblingLevel.BALANCED)
        ua = engine.get_spoofed_user_agent("google.com")
        self.assertIsNone(ua)

    def test_maximum_does_not_change_ua(self):
        """Modo maximum também NÃO altera User-Agent (Brave approach)."""
        engine = FarblingEngine(FarblingLevel.MAXIMUM)
        ua = engine.get_spoofed_user_agent("google.com")
        self.assertIsNone(ua)


class TestFarblingScriptContent(unittest.TestCase):
    """Testa que o JS gerado contém as proteções corretas."""

    def setUp(self):
        self.engine = FarblingEngine(FarblingLevel.BALANCED)
        self.script = self.engine.generate_farbling_script("test.com")

    def test_balanced_has_canvas_farbling(self):
        """Modo balanced inclui farbling de canvas."""
        self.assertIn("getImageData", self.script)
        self.assertIn("toDataURL", self.script)
        self.assertIn("toBlob", self.script)

    def test_balanced_has_audio_farbling(self):
        """Modo balanced inclui farbling de áudio."""
        self.assertIn("AudioContext", self.script)
        self.assertIn("createAnalyser", self.script)
        self.assertIn("getFloatFrequencyData", self.script)

    def test_balanced_has_font_farbling(self):
        """Modo balanced inclui farbling de measureText."""
        self.assertIn("measureText", self.script)

    def test_balanced_has_screen_farbling(self):
        """Modo balanced inclui farbling de screen dimensions."""
        self.assertIn("screen.width", self.script)
        self.assertIn("screen.height", self.script)

    def test_balanced_no_navigator_spoofing(self):
        """Modo balanced NÃO spoofa navigator properties."""
        self.assertNotIn("navigator.userAgent", self.script)
        self.assertNotIn("navigator.platform", self.script)

    def test_balanced_has_timezone_reference(self):
        """Modo balanced referencia getTimezoneOffset (sem alterar valor real)."""
        self.assertIn("getTimezoneOffset", self.script)

    def test_js_has_native_code_protection(self):
        """Script protege toString das funções modificadas."""
        self.assertIn("[native code]", self.script)

    def test_js_uses_prng(self):
        """Script usa PRNG determinístico."""
        self.assertIn("prng", self.script)
        self.assertIn("SEED", self.script)

    def test_js_contains_seed(self):
        """Script contém a seed do domínio."""
        seed = self.engine.get_domain_seed("test.com")
        self.assertIn(seed.hex(), self.script)

    def test_maximum_has_webrtc_protection(self):
        """Modo maximum inclui proteção WebRTC."""
        engine = FarblingEngine(FarblingLevel.MAXIMUM)
        script = engine.generate_farbling_script("test.com")
        self.assertIn("RTCPeerConnection", script)
        self.assertIn("iceTransportPolicy", script)

    def test_maximum_has_battery_protection(self):
        """Modo maximum inclui proteção de Battery API."""
        engine = FarblingEngine(FarblingLevel.MAXIMUM)
        script = engine.generate_farbling_script("test.com")
        self.assertIn("getBattery", script)

    def test_balanced_has_webrtc_filtering(self):
        """Modo balanced inclui filtragem de ICE candidates WebRTC."""
        self.assertIn("RTCPeerConnection", self.script)

    def test_script_is_iife(self):
        """Script é envolvido em IIFE."""
        self.assertTrue(self.script.strip().startswith("(function()"))
        self.assertTrue(self.script.strip().endswith("})();"))

    def test_script_balanced_braces(self):
        """Script tem chaves e parênteses balanceados."""
        self.assertEqual(self.script.count('{'), self.script.count('}'))
        self.assertEqual(self.script.count('('), self.script.count(')'))


class TestFarblingDeterminism(unittest.TestCase):
    """Testa que o farbling é determinístico por domínio."""

    def test_same_domain_same_script(self):
        """Mesmo domínio gera mesmo script."""
        engine = FarblingEngine(FarblingLevel.BALANCED)
        script1 = engine.generate_farbling_script("google.com")
        script2 = engine.generate_farbling_script("google.com")
        self.assertEqual(script1, script2)

    def test_different_domain_different_script(self):
        """Domínios diferentes geram scripts diferentes."""
        engine = FarblingEngine(FarblingLevel.BALANCED)
        script1 = engine.generate_farbling_script("google.com")
        script2 = engine.generate_farbling_script("facebook.com")
        self.assertNotEqual(script1, script2)

    def test_farbling_value_deterministic(self):
        """get_farbling_value retorna o mesmo valor para mesmos inputs."""
        engine = FarblingEngine()
        v1 = engine.get_farbling_value("test.com", "canvas")
        v2 = engine.get_farbling_value("test.com", "canvas")
        self.assertEqual(v1, v2)

    def test_farbling_value_range(self):
        """get_farbling_value retorna valores entre -1 e 1."""
        engine = FarblingEngine()
        for domain in ["google.com", "facebook.com", "test.xyz", "example.org"]:
            v = engine.get_farbling_value(domain, "test_param")
            self.assertGreaterEqual(v, -1.0)
            self.assertLessEqual(v, 1.0)


if __name__ == '__main__':
    unittest.main()
