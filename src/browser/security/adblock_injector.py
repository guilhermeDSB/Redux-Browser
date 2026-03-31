"""
Redux Browser — Injetor de Filtros Cosméticos para Ad Block

Injeta CSS/JS para ocultar elementos de anúncio via QWebEngineScript.
Segue exatamente o padrão do FarblingInjector.
"""

from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
from browser.security.adblock_engine import AdBlockEngine


class AdBlockInjector:
    """
    Injeta scripts de bloqueio cosmético nas páginas do QtWebEngine.
    
    Oculta elementos de anúncio via CSS (display:none!important)
    e observa mutações do DOM para capturar ads carregados dinamicamente.
    """

    SCRIPT_NAME = "redux_adblock_cosmetic"

    def __init__(self, engine: AdBlockEngine):
        self.engine = engine

    def inject(self, page: QWebEnginePage, domain: str) -> None:
        """
        Injeta filtros cosméticos para o domínio na página.
        
        Usa InjectionPoint.DocumentCreation para rodar ANTES
        de qualquer script da página (oculta ads antes de renderizar).
        """
        # Sempre limpar scripts anteriores
        self._remove_scripts(page)

        if not domain or self.engine.is_whitelisted(domain):
            return

        selectors = self.engine.get_cosmetic_selectors(domain)
        if not selectors:
            return

        js_code = self._generate_cosmetic_script(selectors)

        script = QWebEngineScript()
        script.setName(self.SCRIPT_NAME)
        script.setSourceCode(js_code)
        script.setInjectionPoint(
            QWebEngineScript.InjectionPoint.DocumentCreation
        )
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)

        page.scripts().insert(script)

    def _remove_scripts(self, page: QWebEnginePage) -> None:
        """Remove scripts de ad block anteriores."""
        for s in page.scripts().toList():
            if s.name() == self.SCRIPT_NAME:
                page.scripts().remove(s)

    def _generate_cosmetic_script(self, selectors: list) -> str:
        """
        Gera JavaScript para ocultar elementos de anúncio.
        
        Estratégia dupla:
        1. Injeta <style> com display:none!important (imediato, antes do render)
        2. MutationObserver para capturar elementos adicionados dinamicamente
        """
        # Escapar seletores para uso em JS string
        escaped = []
        for sel in selectors:
            escaped.append(sel.replace("\\", "\\\\").replace("'", "\\'").replace("\n", ""))

        selectors_js = ",".join(f"'{s}'" for s in escaped)

        return f"""
(function() {{
    'use strict';
    
    var SELECTORS = [{selectors_js}];
    var CSS_RULE = SELECTORS.join(',') + '{{display:none!important;visibility:hidden!important;height:0!important;min-height:0!important;max-height:0!important;overflow:hidden!important;}}';
    
    // 1. Injetar CSS imediatamente (antes do render)
    function injectStyle() {{
        var style = document.createElement('style');
        style.id = 'redux-adblock-css';
        style.type = 'text/css';
        style.textContent = CSS_RULE;
        (document.head || document.documentElement).appendChild(style);
    }}
    
    // 2. Remover elementos já existentes
    function hideExisting() {{
        for (var i = 0; i < SELECTORS.length; i++) {{
            try {{
                var els = document.querySelectorAll(SELECTORS[i]);
                for (var j = 0; j < els.length; j++) {{
                    els[j].style.setProperty('display', 'none', 'important');
                }}
            }} catch(e) {{}}
        }}
    }}
    
    // 3. MutationObserver para ads dinâmicos
    function observeDOM() {{
        if (!window.MutationObserver) return;
        
        var observer = new MutationObserver(function(mutations) {{
            var needsCheck = false;
            for (var m = 0; m < mutations.length; m++) {{
                if (mutations[m].addedNodes.length > 0) {{
                    needsCheck = true;
                    break;
                }}
            }}
            if (needsCheck) {{
                hideExisting();
            }}
        }});
        
        observer.observe(document.documentElement, {{
            childList: true,
            subtree: true
        }});
    }}
    
    // Executar imediatamente
    if (document.documentElement) {{
        injectStyle();
    }}
    
    // Quando DOM estiver pronto, ocultar existentes e observar
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', function() {{
            injectStyle();
            hideExisting();
            observeDOM();
        }});
    }} else {{
        hideExisting();
        observeDOM();
    }}
}})();
"""
