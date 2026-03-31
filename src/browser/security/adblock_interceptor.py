"""
Redux Browser — Interceptor de Requisições para Ad Block

Usa QWebEngineUrlRequestInterceptor para bloquear requisições de rede
(ads, trackers, analytics) antes que cheguem ao servidor.
"""

from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import pyqtSignal, QObject

from browser.security.adblock_engine import AdBlockEngine
from browser.security.adblock_request import AdBlockRequest


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Interceptor que bloqueia requisições de rede baseado no AdBlockEngine.

    Instalado no QWebEngineProfile via:
        profile.setUrlRequestInterceptor(interceptor)

    Emite sinais para atualizar badge de contagem na UI.
    """

    # Sinal emitido quando uma requisição é bloqueada: (blocked_url, page_domain)
    # NOTA: QWebEngineUrlRequestInterceptor herda de QObject,
    # então podemos usar pyqtSignal diretamente.
    blocked = pyqtSignal(str, str)

    # Mapeamento de ResourceType do Qt → tipos ABP
    _RESOURCE_TYPE_MAP = {
        0: "document",       # ResourceTypeMainFrame
        1: "subdocument",    # ResourceTypeSubFrame
        2: "stylesheet",     # ResourceTypeStylesheet
        3: "script",         # ResourceTypeScript
        4: "image",          # ResourceTypeImage
        5: "font",           # ResourceTypeFontResource
        6: "other",          # ResourceTypeSubResource
        7: "object",         # ResourceTypeObject
        8: "media",          # ResourceTypeMedia
        9: "other",          # ResourceTypeWorker
        10: "other",         # ResourceTypeSharedWorker
        11: "other",         # ResourceTypePrefetch
        12: "image",         # ResourceTypeFavicon
        13: "xhr",           # ResourceTypeXhr
        14: "ping",          # ResourceTypePing
        15: "other",         # ResourceTypeServiceWorker
        16: "other",         # ResourceTypeCspReport
        17: "other",         # ResourceTypePluginResource
        18: "other",         # ResourceTypeNavigationPreloadMainFrame
        19: "other",         # ResourceTypeNavigationPreloadSubFrame
        255: "other",        # ResourceTypeUnknown
    }

    def __init__(self, engine: AdBlockEngine, parent=None):
        super().__init__(parent)
        self.engine = engine

    def interceptRequest(self, info):
        """
        Chamado por QtWebEngine para cada requisição de rede.
        
        Args:
            info: QWebEngineUrlRequestInfo com URL, tipo, first-party, etc.
        """
        try:
            url = info.requestUrl().toString()
            
            # Nunca bloquear o frame principal (document) — isso impediria navegação
            resource_type_id = info.resourceType()
            if resource_type_id == 0:  # MainFrame
                return

            # Ignorar URLs internas
            scheme = info.requestUrl().scheme()
            if scheme in ("data", "blob", "redux-ext", "qrc", "file", "about"):
                return

            resource_type = self._RESOURCE_TYPE_MAP.get(resource_type_id, "other")
            first_party_url = info.firstPartyUrl().toString()

            # Criar AdBlockRequest pré-parseado (uma alocação por requisição)
            request = AdBlockRequest.from_urls(url, first_party_url, resource_type)

            if self.engine.should_block(request):
                info.block(True)
                try:
                    self.blocked.emit(url, request.source_hostname or request.hostname)
                except Exception:
                    pass

        except Exception:
            # Nunca deixar exceções escaparem do interceptor
            pass
