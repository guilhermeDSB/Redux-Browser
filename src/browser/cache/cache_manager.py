import os
import hashlib
import json
import time
from typing import Optional, Dict

class CacheManager:
    """
    Gerencia cache de recursos no disco interceptando o HttpClient.
    Identifica recursos pela URL + ETag via Hash MD5 local caso não tenha ETag no Header.
    Suporta TTL (max-age/Expires), ETag condicional e limite de tamanho com LRU.
    """
    # Tamanho máximo do cache em bytes (100 MB)
    MAX_CACHE_SIZE = 100 * 1024 * 1024
    # TTL padrão quando não especificado (1 hora)
    DEFAULT_TTL = 3600
    
    def __init__(self, cache_dir: str = "~/.redux_browser/cache/"):
        self.cache_dir = os.path.expanduser(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.meta_path = os.path.join(self.cache_dir, "_cache_meta.json")
        self._meta = self._load_meta()
        
    def _create_filename(self, url: str) -> str:
        """Gera um arquivo MD5 curto perante a URL para o filesystem"""
        encoded = url.encode('utf-8')
        return hashlib.md5(encoded).hexdigest()

    def _get_path(self, url: str) -> str:
        return os.path.join(self.cache_dir, self._create_filename(url))
    
    def _load_meta(self) -> dict:
        """Carrega metadados do cache (TTL, ETag, timestamps)."""
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_meta(self):
        """Salva metadados do cache."""
        try:
            with open(self.meta_path, 'w') as f:
                json.dump(self._meta, f)
        except Exception:
            pass
    
    def _parse_max_age(self, headers: Dict[str, str]) -> int:
        """Extrai max-age do Cache-Control header."""
        cc = headers.get('Cache-Control', '')
        import re
        match = re.search(r'max-age=(\d+)', cc)
        if match:
            return int(match.group(1))
        
        # Fallback: Expires header
        expires = headers.get('Expires', '')
        if expires:
            try:
                from email.utils import parsedate_to_datetime
                exp_time = parsedate_to_datetime(expires).timestamp()
                ttl = int(exp_time - time.time())
                return max(0, ttl)
            except Exception:
                pass
        
        return self.DEFAULT_TTL

    def get_cached_resource(self, url: str) -> Optional[bytes]:
        """Tenta resgatar em disco a página ou recurso requisitado. Respeita TTL."""
        url_hash = self._create_filename(url)
        path = self._get_path(url)
        
        if not os.path.exists(path):
            return None
        
        # Verificar TTL
        meta = self._meta.get(url_hash, {})
        cached_at = meta.get('cached_at', 0)
        ttl = meta.get('ttl', self.DEFAULT_TTL)
        
        if time.time() - cached_at > ttl:
            # Cache expirado — invalidar
            self.invalidate(url)
            return None
        
        try:
            # Atualizar timestamp de acesso (LRU)
            meta['last_access'] = time.time()
            self._meta[url_hash] = meta
            
            with open(path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def get_etag(self, url: str) -> Optional[str]:
        """Retorna o ETag armazenado para uma URL (para requests condicionais)."""
        url_hash = self._create_filename(url)
        meta = self._meta.get(url_hash, {})
        return meta.get('etag')

    def store_resource(self, url: str, data: bytes, headers: Dict[str, str]):
        """Avalia heurísticas de HTTP Cache-Control antes de gravar."""
        
        # Heurísticas de Controle Reativo:
        cc = headers.get('Cache-Control', '').lower()
        if 'no-store' in cc or 'no-cache' in cc:
            # Requisito forte para nunca cachar esse call
            self.invalidate(url)
            return
        
        # Verificar limite de tamanho antes de gravar
        self._enforce_size_limit(len(data))
            
        # Grava!
        path = self._get_path(url)
        url_hash = self._create_filename(url)
        try:
            with open(path, 'wb') as f:
                f.write(data)
            
            # Salvar metadados (TTL, ETag, timestamps)
            self._meta[url_hash] = {
                'url': url,
                'cached_at': time.time(),
                'last_access': time.time(),
                'ttl': self._parse_max_age(headers),
                'etag': headers.get('ETag', ''),
                'size': len(data),
            }
            self._save_meta()
        except Exception as e:
            print(f"[CacheManager] Falha ao escrever {url}: {e}")
    
    def _enforce_size_limit(self, new_data_size: int):
        """Remove entradas LRU (Least Recently Used) se o cache excede MAX_CACHE_SIZE."""
        total_size = sum(m.get('size', 0) for m in self._meta.values()) + new_data_size
        
        if total_size <= self.MAX_CACHE_SIZE:
            return
        
        # Ordenar por last_access (mais antigos primeiro) e remover
        entries = sorted(self._meta.items(), key=lambda x: x[1].get('last_access', 0))
        
        for url_hash, meta in entries:
            if total_size <= self.MAX_CACHE_SIZE * 0.8:  # Libera até 80%
                break
            path = os.path.join(self.cache_dir, url_hash)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                total_size -= meta.get('size', 0)
                del self._meta[url_hash]
            except Exception:
                pass
        
        self._save_meta()

    def invalidate(self, url: str):
        path = self._get_path(url)
        url_hash = self._create_filename(url)
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        if url_hash in self._meta:
            del self._meta[url_hash]
            self._save_meta()

    def clear_cache(self):
        """Limpa todo o diretório de cache manual."""
        for filename in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, filename)
            try:
                if os.path.isfile(path): os.remove(path)
            except: pass
        self._meta.clear()
        self._save_meta()
