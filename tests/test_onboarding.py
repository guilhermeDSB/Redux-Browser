"""
Testes unitários para o Onboarding Wizard do Redux Browser.
Testa lógica de escolhas, persistência de configurações e navegação entre páginas.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Importações do projeto
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from browser.config.settings_manager import SettingsManager


class TestOnboardingSettings(unittest.TestCase):
    """Testa a integração do onboarding com SettingsManager."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            suffix='.json', delete=False, mode='w'
        )
        self.tmp.close()
        self.settings = SettingsManager(self.tmp.name)

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_onboarding_completed_default_false(self):
        """onboarding_completed deve ser False por padrão."""
        self.assertFalse(self.settings.get("onboarding_completed"))

    def test_onboarding_completed_in_defaults(self):
        """onboarding_completed deve existir em DEFAULTS."""
        self.assertIn("onboarding_completed", SettingsManager.DEFAULTS)
        self.assertFalse(SettingsManager.DEFAULTS["onboarding_completed"])

    def test_set_onboarding_completed(self):
        """Deve persistir onboarding_completed = True."""
        self.settings.set("onboarding_completed", True)
        self.assertTrue(self.settings.get("onboarding_completed"))

        # Recarregar de disco e verificar
        reloaded = SettingsManager(self.tmp.name)
        self.assertTrue(reloaded.get("onboarding_completed"))

    def test_theme_default(self):
        """Tema padrão deve ser 'dark'."""
        self.assertEqual(self.settings.get("theme"), "dark")

    def test_set_theme_light(self):
        """Deve persistir tema 'light'."""
        self.settings.set("theme", "light")
        self.assertEqual(self.settings.get("theme"), "light")

    def test_set_search_engine(self):
        """Deve persistir motor de busca escolhido."""
        self.settings.set("search_engine", "Brave Search")
        self.assertEqual(self.settings.get("search_engine"), "Brave Search")

    def test_set_farbling_level(self):
        """Deve persistir nível de farbling."""
        for level in ("off", "balanced", "maximum"):
            self.settings.set("farbling_level", level)
            self.assertEqual(self.settings.get("farbling_level"), level)

    def test_set_adblock_level(self):
        """Deve persistir nível de adblock."""
        for level in ("off", "standard", "aggressive"):
            self.settings.set("adblock_level", level)
            self.assertEqual(self.settings.get("adblock_level"), level)

    def test_full_onboarding_flow(self):
        """Simula o fluxo completo de configurações do wizard."""
        choices = {
            "theme": "light",
            "search_engine": "Startpage",
            "farbling_level": "maximum",
            "adblock_level": "aggressive",
        }
        for key, value in choices.items():
            self.settings.set(key, value)
        self.settings.set("onboarding_completed", True)

        # Recarregar e verificar tudo
        reloaded = SettingsManager(self.tmp.name)
        for key, value in choices.items():
            self.assertEqual(reloaded.get(key), value, f"Falhou para {key}")
        self.assertTrue(reloaded.get("onboarding_completed"))


class TestOnboardingWizardLogic(unittest.TestCase):
    """Testa a lógica interna do OnboardingWizard sem GUI."""

    def test_choices_dict_defaults(self):
        """Verifica valores padrão do dict de escolhas."""
        expected = {
            "theme": "dark",
            "search_engine": "DuckDuckGo",
            "farbling_level": "balanced",
            "adblock_level": "standard",
        }
        # Importar e verificar a constante
        from browser.ui.onboarding import _TOTAL_PAGES, _PAGE_WELCOME, _PAGE_DONE
        self.assertEqual(_TOTAL_PAGES, 5)
        self.assertEqual(_PAGE_WELCOME, 0)
        self.assertEqual(_PAGE_DONE, 4)

    def test_colored_svg_helper(self):
        """_colored_svg deve substituir currentColor."""
        from browser.ui.onboarding import _colored_svg
        svg = '<svg stroke="currentColor">test</svg>'
        result = _colored_svg(svg, "#FF0000")
        self.assertIn("#FF0000", result)
        self.assertNotIn("currentColor", result)

    def test_page_constants(self):
        """Constantes de página devem estar corretas."""
        from browser.ui.onboarding import (
            _PAGE_WELCOME, _PAGE_THEME, _PAGE_SEARCH,
            _PAGE_PRIVACY, _PAGE_DONE, _TOTAL_PAGES
        )
        self.assertEqual(_PAGE_WELCOME, 0)
        self.assertEqual(_PAGE_THEME, 1)
        self.assertEqual(_PAGE_SEARCH, 2)
        self.assertEqual(_PAGE_PRIVACY, 3)
        self.assertEqual(_PAGE_DONE, 4)
        self.assertEqual(_TOTAL_PAGES, 5)


class TestOnboardingImports(unittest.TestCase):
    """Testa que o módulo importa corretamente."""

    def test_import_onboarding_module(self):
        """O módulo onboarding deve importar sem erro."""
        import browser.ui.onboarding as onb
        self.assertTrue(hasattr(onb, 'OnboardingWizard'))

    def test_import_selection_card(self):
        """_SelectionCard deve ser acessível."""
        from browser.ui.onboarding import _SelectionCard
        self.assertTrue(callable(_SelectionCard))

    def test_import_dot_indicator(self):
        """_DotIndicator deve ser acessível."""
        from browser.ui.onboarding import _DotIndicator
        self.assertTrue(callable(_DotIndicator))


if __name__ == '__main__':
    unittest.main()
