"""
Redux Browser — Popup de extensão
Carrega popup.html diretamente via file:// com Chrome API shim.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineScript
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor

from browser.ui.theme import Theme


CHROME_SHIM = """
if (!window.chrome) window.chrome = {};
(function() {
    var _extId = 'EXT_ID_PLACEHOLDER';
    var _storagePrefix = '__redux_ext_' + _extId + '_';
    window.chrome.runtime = {
        id: _extId,
        getManifest: function(){ return {}; },
        getURL: function(p){ return p || ''; },
        sendMessage: function(){ var cb=arguments[arguments.length-1]; if(typeof cb==='function') cb(); },
        connect: function(){ return {onMessage:{addListener:function(){}},postMessage:function(){}}; },
        onMessage:{addListener:function(){},removeListener:function(){}},
        onInstalled:{addListener:function(){}},
        getBackgroundPage: function(cb){if(cb)cb(null);},
        reload: function(){},
        lastError: null
    };
    window.chrome.extension = {
        getURL: function(p){ return p || ''; },
        getBackgroundPage: function(){return null;},
        getViews: function(){return [];}
    };
    
    // Storage persistido via localStorage com prefixo por extensão
    function makeStorageArea(areaName) {
        var prefix = _storagePrefix + areaName + '_';
        return {
            get: function(keys, cb) {
                if (typeof keys === 'function') { cb = keys; keys = null; }
                if (!cb) cb = function(){};
                var result = {};
                if (!keys) {
                    for (var i = 0; i < localStorage.length; i++) {
                        var k = localStorage.key(i);
                        if (k.startsWith(prefix)) {
                            try { result[k.slice(prefix.length)] = JSON.parse(localStorage.getItem(k)); }
                            catch(e) { result[k.slice(prefix.length)] = localStorage.getItem(k); }
                        }
                    }
                } else {
                    var keyList = Array.isArray(keys) ? keys : (typeof keys === 'string' ? [keys] : Object.keys(keys));
                    var defaults = (typeof keys === 'object' && !Array.isArray(keys)) ? keys : {};
                    keyList.forEach(function(k) {
                        var v = localStorage.getItem(prefix + k);
                        if (v !== null) { try { result[k] = JSON.parse(v); } catch(e) { result[k] = v; } }
                        else if (k in defaults) { result[k] = defaults[k]; }
                    });
                }
                cb(result);
            },
            set: function(items, cb) {
                Object.keys(items || {}).forEach(function(k) {
                    localStorage.setItem(prefix + k, JSON.stringify(items[k]));
                });
                if (cb) cb();
            },
            remove: function(keys, cb) {
                (Array.isArray(keys) ? keys : [keys]).forEach(function(k) { localStorage.removeItem(prefix + k); });
                if (cb) cb();
            },
            clear: function(cb) {
                var toRemove = [];
                for (var i = 0; i < localStorage.length; i++) {
                    var k = localStorage.key(i);
                    if (k.startsWith(prefix)) toRemove.push(k);
                }
                toRemove.forEach(function(k) { localStorage.removeItem(k); });
                if (cb) cb();
            },
            getBytesInUse: function(cb) { if (cb) cb(0); }
        };
    }
    window.chrome.storage={local:makeStorageArea('local'),sync:makeStorageArea('sync'),managed:makeStorageArea('managed')};
    window.chrome.tabs={query:function(q,cb){if(cb)cb([]);},sendMessage:function(){var cb=arguments[arguments.length-1];if(typeof cb==='function')cb();},create:function(p){},onUpdated:{addListener:function(){}}};
    window.chrome.windows={getCurrent:function(o,cb){if(typeof o==='function'){cb=o;o={};}if(cb)cb({id:1});},getAll:function(o,cb){if(cb)cb([]);},create:function(p,cb){if(cb)cb({id:1});}};
    window.chrome.i18n={getMessage:function(k){return k||'';},getUILanguage:function(){return'en';}};
    window.chrome.browserAction={setBadgeText:function(){},setIcon:function(){},onClicked:{addListener:function(){}}};
    window.chrome.action=window.chrome.browserAction;
    window.chrome.contextMenus={create:function(p,cb){if(cb)cb();},removeAll:function(cb){if(cb)cb();},onClicked:{addListener:function(){}}};
    window.chrome.notifications={create:function(id,o,cb){if(cb)cb(id||'1');},clear:function(id,cb){if(cb)cb(true);},onClicked:{addListener:function(){}}};
    window.chrome.webRequest={onBeforeRequest:{addListener:function(){},removeListener:function(){}},onHeadersReceived:{addListener:function(){},removeListener:function(){}}};
    window.chrome.declarativeNetRequest={getDynamicRules:function(cb){if(cb)cb([]);},updateDynamicRules:function(o,cb){if(cb)cb();},getEnabledRulesets:function(cb){if(cb)cb([]);}};
    window.chrome.scripting={executeScript:function(d,cb){if(cb)cb([{result:null}]);},insertCSS:function(d,cb){if(cb)cb();}};
    window.chrome.permissions={contains:function(p,cb){if(cb)cb(true);},request:function(p,cb){if(cb)cb(true);}};
    window.chrome.webNavigation={onCommitted:{addListener:function(){}},onCompleted:{addListener:function(){}}};
    window.chrome.runtime.connect=function(){return{onMessage:{addListener:function(){}},onDisconnect:{addListener:function(){}},postMessage:function(){},disconnect:function(){},name:'',sender:null};};
})();
"""


class ExtensionPopup(QDialog):
    def __init__(self, extension, extension_manager, parent=None):
        super().__init__(parent)
        self.extension = extension
        
        current_theme = getattr(parent, 'current_theme', 'dark') if parent else 'dark'
        p = Theme.DARK if current_theme == "dark" else Theme.LIGHT
        
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 500)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QWidget(self)
        self.container.setObjectName("popupContainer")
        self.container.setStyleSheet(f"""
            QWidget#popupContainer {{
                background-color: {p['bg_primary']};
                border: 1px solid {p['border']};
                border-radius: 12px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView(self)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        
        # Inject shim via QWebEngineScript (runs before page JS)
        profile = self.web_view.page().profile()
        script = QWebEngineScript()
        script.setName("redux_shim")
        shim_with_id = CHROME_SHIM.replace("EXT_ID_PLACEHOLDER", extension.id)
        script.setSourceCode(shim_with_id)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        
        existing = [s for s in profile.scripts().toList() if s.name() == "redux_shim"]
        if not existing:
            profile.scripts().insert(script)
        
        self.web_view.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.web_view)
        
        # Load popup via file:// URL (usando QUrl.fromLocalFile para Windows)
        if extension.action and extension.action.default_popup:
            popup_path = extension.path / extension.action.default_popup
            if popup_path.exists():
                self.web_view.setUrl(QUrl.fromLocalFile(str(popup_path.resolve())))
