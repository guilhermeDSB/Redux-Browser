"""
Redux Browser — Chrome Web Store Integration
Detecta páginas de extensão na Chrome Web Store e baixa .crx.
"""

import re
import os
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QUrl


# Chrome Web Store uses these domains
CWS_PATTERNS = [
    r'https?://chromewebstore\.google\.com/detail/[\w\-]+/([\w]{32})',
    r'https?://chrome\.google\.com/webstore/detail/[\w\-]+/([\w]{32})',
]

EXTENSION_ID_REGEX = re.compile(r'([a-z]{32})')

# Update URLs that Chromium uses for .crx downloads
CRX_UPDATE_URLS = [
    # CRX3 format (most recent)
    "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=131.0.0.0&acceptformat=crx3&x=id%3D{ext_id}%26installsource%3Dondemand%26uc",
    # Older format
    "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=49.0&x=id%3D{ext_id}%26installsource%3Dondemand%26uc",
    # Another variant
    "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0.0.0&x=id%3D{ext_id}%26installsource%3Dondemand%26uc",
]


def extract_extension_id(url: str) -> Optional[str]:
    """
    Extrai o ID da extensão de uma URL da Chrome Web Store.
    
    Exemplos de URLs:
    https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm
    https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm
    """
    # Pattern matching
    for pattern in CWS_PATTERNS:
        match = re.match(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Fallback: extract from path segments
    parsed = urllib.parse.urlparse(url)
    path_parts = parsed.path.rstrip('/').split('/')
    
    for part in path_parts:
        if len(part) == 32 and EXTENSION_ID_REGEX.match(part):
            return part
    
    return None


def is_chrome_web_store_url(url: str) -> bool:
    """Verifica se a URL é uma página de extensão da Chrome Web Store."""
    if not url:
        return False
    
    lower_url = url.lower()
    
    if 'chromewebstore.google.com/detail' in lower_url:
        return True
    if 'chrome.google.com/webstore/detail' in lower_url:
        return True
    
    return False


def get_extension_info_from_url(url: str) -> Optional[dict]:
    """
    Extrai informações da extensão a partir da URL da Chrome Web Store.
    Retorna dict com 'id' e 'name' (estimado do path).
    """
    ext_id = extract_extension_id(url)
    if not ext_id:
        return None
    
    # Try to get the name from URL path
    parsed = urllib.parse.urlparse(url)
    path_parts = parsed.path.rstrip('/').split('/')
    
    name = "Extensão"
    for part in path_parts:
        if len(part) < 32 and part not in ('detail', 'webstore', ''):
            name = part.replace('-', ' ').title()
            break
    
    return {
        'id': ext_id,
        'name': name,
        'url': url
    }


def download_crx(ext_id: str, dest_dir: str) -> Path:
    """
    Baixa o arquivo .crx de uma extensão da Chrome Web Store.
    Tenta múltiplas URLs de update até encontrar uma que funcione.
    """
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = Path(dest_dir) / f"{ext_id}.crx"
    
    last_error = None
    
    # Enable cookie handling for redirects
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPSHandler()
    )
    
    for update_url in CRX_UPDATE_URLS:
        url = update_url.format(ext_id=ext_id)
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': '*/*',
            })
            
            resp = opener.open(req, timeout=30)
            
            # Check if we got redirected to an error page
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                last_error = f"Recebido HTML em vez de CRX (Content-Type: {content_type})"
                continue
            
            data = resp.read()
            
            # Validate minimum CRX/ZIP size and magic bytes
            if len(data) < 100:
                last_error = "Arquivo muito pequeno (< 100 bytes)"
                continue
            
            # Check for CRX magic (Cr24) or ZIP magic (PK)
            if data[:4] != b'Cr24' and data[:2] != b'PK':
                last_error = f"Magic bytes inválidos: {data[:4]!r} (esperado Cr24 ou PK)"
                continue
            
            with open(dest_path, 'wb') as f:
                f.write(data)
            
            return dest_path
            
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            continue
        except Exception as e:
            last_error = str(e)
            continue
    
    raise RuntimeError(f"Não foi possível baixar a extensão {ext_id}. Google pode ter bloqueado o download. Último erro: {last_error}")
