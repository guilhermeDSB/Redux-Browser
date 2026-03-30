"""
Redux Browser — Carregador de Content Scripts
Injeta content scripts e CSS das extensões nas páginas web.
"""

from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
from urllib.parse import urlparse
from typing import List

class ContentScriptLoader:
    """
    Carrega content scripts de extensões habilitadas nas páginas.
    """
    
    def __init__(self, extension_manager):
        self.ext_manager = extension_manager
    
    def inject_scripts_for_page(self, page: QWebEnginePage, url: str):
        self._clear_extension_scripts(page)
        
        scripts = self.ext_manager.get_content_scripts_for_url(url)
        js_scripts = [s for s in scripts if s['type'] == 'js']
        css_scripts = [s for s in scripts if s['type'] == 'css']
        
        for script_info in js_scripts:
            js_content = self._read_script_file(script_info)
            if not js_content: continue
            
            chrome_api_shim = self._generate_chrome_api_shim(script_info['extension_id'])
            full_script = chrome_api_shim + "\n" + js_content
            
            qs = QWebEngineScript()
            qs.setName(f"ext_{script_info['extension_id']}_{script_info['file']}")
            qs.setSourceCode(full_script)
            qs.setInjectionPoint(self._map_run_at(script_info['run_at']))
            qs.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
            qs.setRunsOnSubFrames(script_info.get('all_frames', False))
            
            page.scripts().insert(qs)
        
        for css_info in css_scripts:
            css_content = self._read_css_file(css_info)
            if css_content:
                self._inject_css(page, css_content, css_info['extension_id'])
                
    def _read_script_file(self, script_info: dict) -> str:
        fpath = script_info['ext_path'] / script_info['file']
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
            
    def _read_css_file(self, css_info: dict) -> str:
        fpath = css_info['ext_path'] / css_info['file']
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
    
    def _generate_chrome_api_shim(self, extension_id: str) -> str:
        return f'''
        (function() {{
            'use strict';
            
            if (typeof chrome === 'undefined') {{
                window.chrome = {{}};
            }}
            
            const EXTENSION_ID = '{extension_id}';
            
            // ========== chrome.runtime ==========
            chrome.runtime = chrome.runtime || {{}};
            chrome.runtime.id = EXTENSION_ID;
            
            chrome.runtime.sendMessage = function(message, callback) {{
                const event = new CustomEvent('redux_ext_message', {{
                    detail: {{
                        extensionId: EXTENSION_ID,
                        message: message,
                        id: Math.random().toString(36).substr(2)
                    }}
                }});
                
                if (callback) {{
                    const responseHandler = function(e) {{
                        if (e.detail.responseToId === event.detail.id) {{
                            window.removeEventListener('redux_ext_response', responseHandler);
                            callback(e.detail.response);
                        }}
                    }};
                    window.addEventListener('redux_ext_response', responseHandler);
                }}
                
                window.dispatchEvent(event);
            }};
            
            chrome.runtime.onMessage = {{
                _listeners: [],
                addListener: function(fn) {{ this._listeners.push(fn); }},
                removeListener: function(fn) {{
                    this._listeners = this._listeners.filter(l => l !== fn);
                }},
                hasListener: function(fn) {{
                    return this._listeners.includes(fn);
                }}
            }};
            
            window.addEventListener('redux_ext_to_content', function(e) {{
                if (e.detail.extensionId === EXTENSION_ID) {{
                    chrome.runtime.onMessage._listeners.forEach(fn => {{
                        fn(e.detail.message, e.detail.sender, function(response) {{
                            window.dispatchEvent(new CustomEvent('redux_ext_response', {{
                                detail: {{ responseToId: e.detail.id, response: response }}
                            }}));
                        }});
                    }});
                }}
            }});
            
            chrome.runtime.getURL = function(path) {{
                return 'chrome-extension://' + EXTENSION_ID + '/' + path;
            }};
            
            // ========== chrome.storage ==========
            chrome.storage = chrome.storage || {{}};
            
            function createStorageArea(areaName) {{
                const PREFIX = `redux_ext_${{EXTENSION_ID}}_${{areaName}}_`;
                return {{
                    get: function(keys, callback) {{
                        const result = {{}};
                        if (typeof keys === 'string') keys = [keys];
                        if (keys === null) {{
                            for (let i = 0; i < localStorage.length; i++) {{
                                const key = localStorage.key(i);
                                if (key.startsWith(PREFIX)) {{
                                    const realKey = key.substring(PREFIX.length);
                                    try {{ result[realKey] = JSON.parse(localStorage.getItem(key)); }}
                                    catch(e) {{ result[realKey] = localStorage.getItem(key); }}
                                }}
                            }}
                        }} else if (Array.isArray(keys)) {{
                            keys.forEach(k => {{
                                const val = localStorage.getItem(PREFIX + k);
                                if (val !== null) {{
                                    try {{ result[k] = JSON.parse(val); }} catch(e) {{ result[k] = val; }}
                                }}
                            }});
                        }} else if (typeof keys === 'object') {{
                            Object.keys(keys).forEach(k => {{
                                const val = localStorage.getItem(PREFIX + k);
                                result[k] = val !== null ? JSON.parse(val) : keys[k];
                            }});
                        }}
                        if (callback) callback(result);
                        return Promise.resolve(result);
                    }},
                    set: function(items, callback) {{
                        Object.keys(items).forEach(k => {{
                            localStorage.setItem(PREFIX + k, JSON.stringify(items[k]));
                        }});
                        if (callback) callback();
                        return Promise.resolve();
                    }},
                    remove: function(keys, callback) {{
                        if (typeof keys === 'string') keys = [keys];
                        keys.forEach(k => localStorage.removeItem(PREFIX + k));
                        if (callback) callback();
                        return Promise.resolve();
                    }},
                    clear: function(callback) {{
                        const toRemove = [];
                        for (let i = 0; i < localStorage.length; i++) {{
                            if (localStorage.key(i).startsWith(PREFIX)) toRemove.push(localStorage.key(i));
                        }}
                        toRemove.forEach(k => localStorage.removeItem(k));
                        if (callback) callback();
                        return Promise.resolve();
                    }}
                }};
            }}
            
            chrome.storage.local = createStorageArea('local');
            chrome.storage.sync = createStorageArea('sync');
            chrome.storage.session = createStorageArea('session');
            
            // ========== chrome.i18n ==========
            chrome.i18n = chrome.i18n || {{}};
            chrome.i18n.getMessage = function(messageName) {{ return messageName; }};
            chrome.i18n.getUILanguage = function() {{ return navigator.language || 'en'; }};
            
        }})();
        '''
    
    def _map_run_at(self, run_at: str) -> QWebEngineScript.InjectionPoint:
        mapping = {
            "document_start": QWebEngineScript.InjectionPoint.DocumentCreation,
            "document_end": QWebEngineScript.InjectionPoint.DocumentReady,
            "document_idle": QWebEngineScript.InjectionPoint.Deferred,
        }
        return mapping.get(run_at, QWebEngineScript.InjectionPoint.Deferred)
    
    def _clear_extension_scripts(self, page: QWebEnginePage):
        scripts = page.scripts()
        for s in scripts.toList():
            if s.name().startswith("ext_"):
                scripts.remove(s)
    
    def _inject_css(self, page: QWebEnginePage, css_content: str, ext_id: str):
        css_content_escaped = css_content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        js_injector = f"""
        (function() {{
            const style = document.createElement('style');
            style.id = 'redux-ext-css-{ext_id}';
            style.textContent = `{css_content_escaped}`;
            (document.head || document.documentElement).appendChild(style);
        }})();
        """
        page.runJavaScript(js_injector, QWebEngineScript.ScriptWorldId.ApplicationWorld)
