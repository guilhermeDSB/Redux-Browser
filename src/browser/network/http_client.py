import requests
import logging

class HttpClient:
    """
    Cliente HTTP nativo em Python para lidar com requisições 
    manuais do navegador (e.g. downloads, pre-fetch, APIs diretas), 
    independente do QtWebEngine.
    """
    def __init__(self, is_private: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ReduxBrowser/1.0 (Windows NT 10.0; Win64; x64) Baseado em Python/Requests"
        })
        self.is_private = is_private
        
        # Só inicializa cache se não estiver em aba anônima
        self.cache_manager = None
        if not self.is_private:
            from browser.cache.cache_manager import CacheManager
            self.cache_manager = CacheManager()
        
    def get(self, url, params=None, headers=None, follow_redirects=True, fingerprint_profile=None):
        """Realiza requisição GET com tratamento de erros. Intercepta Cache se possível."""
        try:
            req_headers = headers or {}
            
            # Headers de privacidade para modo privado
            if self.is_private:
                req_headers.setdefault('DNT', '1')
                req_headers.setdefault('Sec-GPC', '1')
            
            # 1. TENTA O CACHE LOCAL (GET limpo apenas)
            if self.cache_manager and not params:
                cached_data = self.cache_manager.get_cached_resource(url)
                if cached_data:
                    # Simula response basico para evitar a request
                    class CachedResponse:
                        status_code = 200
                        text = cached_data.decode('utf-8', errors='ignore')
                        content = cached_data
                        
                        def json(self):
                            import json
                            return json.loads(self.text)
                            
                    return CachedResponse()

            # 2. REALIZA REQUISIÇÃO REAL
            response = self.session.get(
                url, 
                params=params, 
                headers=req_headers, 
                allow_redirects=follow_redirects,
                timeout=15
            )
            response.raise_for_status()
            
            # 3. GRAVA NO CACHE SE FOR SUCESSO E PERMITIDO
            if self.cache_manager and response.status_code == 200:
                self.cache_manager.store_resource(url, response.content, response.headers)
                
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"[Network] Erro na requisição GET para {url}: {e}")
            return None

    def post(self, url, data=None, json_=None, headers=None, follow_redirects=True, fingerprint_profile=None):
        """Realiza requisição POST."""
        try:
            req_headers = headers or {}
            
            # Headers de privacidade para modo privado
            if self.is_private:
                req_headers.setdefault('DNT', '1')
                req_headers.setdefault('Sec-GPC', '1')
                
            response = self.session.post(
                url, 
                data=data,
                json=json_,
                headers=req_headers, 
                allow_redirects=follow_redirects,
                timeout=15
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"[Network] Erro na requisição POST para {url}: {e}")
            return None
