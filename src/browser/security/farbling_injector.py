"""
Injetor de farbling no QtWebEngine.
Injeta o script de farbling ANTES de qualquer script da página.
"""

from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
from .brave_farbling import FarblingEngine, FarblingLevel


class FarblingInjector:
    """Injeta scripts de farbling nas páginas do QtWebEngine."""

    def __init__(self, engine: FarblingEngine):
        self.engine = engine

    def inject(self, page: QWebEnginePage, domain: str) -> None:
        """
        Injeta script de farbling na página.
        Usa InjectionPoint.DocumentCreation para rodar ANTES
        de qualquer script da página.
        """
        # Remover script anterior sempre
        self._remove_scripts(page)

        if self.engine.level == FarblingLevel.OFF:
            return

        js_code = self.engine.generate_farbling_script(domain)
        if not js_code:
            return

        script = QWebEngineScript()
        script.setName("redux_farbling")
        script.setSourceCode(js_code)
        script.setInjectionPoint(
            QWebEngineScript.InjectionPoint.DocumentCreation
        )
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)

        page.scripts().insert(script)

    def _remove_scripts(self, page: QWebEnginePage) -> None:
        """Remove scripts de farbling anteriores."""
        for s in page.scripts().toList():
            if s.name() == "redux_farbling":
                page.scripts().remove(s)
