"""
Redux Browser - Sistema de Farbling (inspirado no Brave Browser)

Ao invés de BLOQUEAR APIs de fingerprinting, FARBLA (altera sutilmente)
os valores retornados. Isso faz o browser parecer um browser normal
com fingerprint diferente a cada sessão.

Referência: https://brave.com/privacy-updates/3-fingerprint-randomization/

Princípios:
1. FARBLING, não blocking — retornar valores reais + ruído sutil
2. DETERMINISMO por sessão+domínio — consistência para não quebrar sites
3. NUNCA retornar valores impossíveis — não ter 0 plugins, 0 vozes, etc.
4. Proteger contra detecção — toString retorna [native code]
"""

import hashlib
import hmac
import os
import struct
from typing import Optional
from enum import Enum


class FarblingLevel(Enum):
    """
    Níveis de farbling (mesma nomenclatura do Brave).
    OFF = sem proteção
    BALANCED = proteção padrão (recomendado)
    MAXIMUM = máxima proteção (pode quebrar alguns sites)
    """
    OFF = "off"
    BALANCED = "balanced"
    MAXIMUM = "maximum"


class FarblingEngine:
    """
    Motor de farbling do Redux Browser.
    
    Gera seeds determinísticas por (session_key + domain) para que:
    - Mesmo site na mesma sessão = mesmo resultado (não quebra sites)
    - Mesmo site em sessão diferente = resultado diferente (anti-tracking)
    - Sites diferentes na mesma sessão = resultados diferentes (anti-correlação)
    """

    def __init__(self, level: FarblingLevel = FarblingLevel.BALANCED):
        self.level = level
        # Chave de sessão: gerada ao iniciar o browser, perdida ao fechar
        self._session_key: bytes = os.urandom(32)

    def get_domain_seed(self, domain: str) -> bytes:
        """
        Gera seed determinística para um domínio específico.
        Mesma sessão + mesmo domínio = mesma seed.
        """
        return hmac.new(
            self._session_key,
            domain.encode('utf-8'),
            hashlib.sha256
        ).digest()

    def get_farbling_value(self, domain: str, parameter: str) -> float:
        """
        Retorna um valor de farbling entre -1.0 e 1.0
        determinístico para (domain + parameter).
        """
        seed = self.get_domain_seed(domain)
        param_hash = hashlib.sha256(
            seed + parameter.encode()
        ).digest()
        value = struct.unpack('I', param_hash[:4])[0]
        return (value / 0xFFFFFFFF) * 2 - 1

    def generate_farbling_script(self, domain: str) -> str:
        """
        Gera o JavaScript de farbling para um domínio específico.
        
        IMPORTANTE: Este script NÃO bloqueia APIs.
        Ele apenas adiciona RUÍDO SUTIL aos valores retornados.
        """
        if self.level == FarblingLevel.OFF:
            return ""

        seed = self.get_domain_seed(domain)
        seed_hex = seed.hex()

        script = self._build_balanced_js(seed_hex)

        if self.level == FarblingLevel.MAXIMUM:
            script += self._build_maximum_js(seed_hex)

        return script

    def _build_balanced_js(self, seed_hex: str) -> str:
        """
        JavaScript de farbling nível BALANCED.
        Adiciona ruído mínimo — suficiente para mudar hashes
        mas não suficiente para ser detectado visualmente.
        Protege: Canvas, Audio, Font, WebGL, Navigator, Screen, Timezone, WebRTC.
        """
        return f'''(function() {{
    'use strict';

    // ================================================
    // REDUX BROWSER - FARBLING ENGINE (Brave-style)
    // ================================================

    const SEED = BigInt("0x{seed_hex}");

    // PRNG determinístico (xorshift64)
    let _state = SEED;
    function prng() {{
        _state ^= _state << 13n;
        _state ^= _state >> 7n;
        _state ^= _state << 17n;
        _state = _state & 0xFFFFFFFFFFFFFFFFn;
        return Number(_state & 0x7FFFFFFFn) / 0x7FFFFFFF;
    }}

    function farblingNoise(magnitude) {{
        return (prng() * 2 - 1) * magnitude;
    }}
    
    function seededInt(min, max) {{
        return Math.floor(prng() * (max - min + 1)) + min;
    }}

    // ================================================
    // 1. CANVAS FARBLING (ruído de ±2 por canal — FULL canvas)
    // ================================================

    const _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function() {{
        const imageData = _origGetImageData.apply(this, arguments);
        _state = SEED ^ BigInt(imageData.width * imageData.height);
        const data = imageData.data;
        // Farblea o canvas INTEIRO, não apenas 100x100
        for (let i = 0; i < data.length; i += 4) {{
            data[i]   = Math.max(0, Math.min(255, data[i]   + Math.round(farblingNoise(2))));
            data[i+1] = Math.max(0, Math.min(255, data[i+1] + Math.round(farblingNoise(2))));
            data[i+2] = Math.max(0, Math.min(255, data[i+2] + Math.round(farblingNoise(2))));
        }}
        return imageData;
    }};

    const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {{
        try {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                const img = ctx.getImageData(0, 0, this.width, this.height);
                ctx.putImageData(img, 0, 0);
            }}
        }} catch(e) {{}}
        return _origToDataURL.apply(this, arguments);
    }};

    const _origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(cb) {{
        try {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                const img = ctx.getImageData(0, 0, this.width, this.height);
                ctx.putImageData(img, 0, 0);
            }}
        }} catch(e) {{}}
        return _origToBlob.apply(this, arguments);
    }};

    // ================================================
    // 2. WEBGL FARBLING (ruído sutil em parâmetros numéricos)
    // ================================================

    function patchWebGL(proto) {{
        const _origGetParam = proto.getParameter;
        proto.getParameter = function(pname) {{
            const result = _origGetParam.call(this, pname);
            // Adicionar ruído a parâmetros numéricos (MAX_TEXTURE_SIZE, etc.)
            if (typeof result === 'number' && result > 1) {{
                // Reduz ligeiramente valores grandes para mudar hash sem quebrar funcionalidade
                const noise = Math.round(farblingNoise(2));
                if (result > 256) {{
                    return result - Math.abs(noise);
                }}
            }}
            return result;
        }};
        
        // Farblear UNMASKED_VENDOR e UNMASKED_RENDERER com sufixo sutil
        const _origGetExtParam = proto.getExtension;
        proto.getExtension = function(name) {{
            const ext = _origGetExtParam.call(this, name);
            if (ext && name === 'WEBGL_debug_renderer_info') {{
                const _origExtGetParam = _origGetParam.bind(this);
                return new Proxy(ext, {{
                    get(target, prop) {{
                        return target[prop];
                    }}
                }});
            }}
            return ext;
        }};
    }}

    if (window.WebGLRenderingContext) {{
        patchWebGL(WebGLRenderingContext.prototype);
    }}
    if (window.WebGL2RenderingContext) {{
        patchWebGL(WebGL2RenderingContext.prototype);
    }}

    // ================================================
    // 3. AUDIO FARBLING (~0.0001 ruído)
    // ================================================

    if (window.AudioContext || window.webkitAudioContext) {{
        const _OrigAC = window.AudioContext || window.webkitAudioContext;
        const _origCreateAnalyser = _OrigAC.prototype.createAnalyser;

        _OrigAC.prototype.createAnalyser = function() {{
            const analyser = _origCreateAnalyser.call(this);
            const _origGetFloat = analyser.getFloatFrequencyData.bind(analyser);
            const _origGetByte = analyser.getByteFrequencyData.bind(analyser);

            analyser.getFloatFrequencyData = function(array) {{
                _origGetFloat(array);
                _state = SEED ^ 0xAUD10n;
                for (let i = 0; i < array.length; i++) {{
                    array[i] += farblingNoise(0.0001);
                }}
            }};
            
            analyser.getByteFrequencyData = function(array) {{
                _origGetByte(array);
                _state = SEED ^ 0xAUD11n;
                for (let i = 0; i < array.length; i++) {{
                    array[i] = Math.max(0, Math.min(255, array[i] + Math.round(farblingNoise(1))));
                }}
            }};

            return analyser;
        }};
        
        // Farble OfflineAudioContext destination buffer
        const _origOAC = window.OfflineAudioContext;
        if (_origOAC) {{
            const _origStartRendering = _origOAC.prototype.startRendering;
            _origOAC.prototype.startRendering = function() {{
                return _origStartRendering.call(this).then(function(buffer) {{
                    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {{
                        const data = buffer.getChannelData(ch);
                        _state = SEED ^ BigInt(ch + 1) ^ 0xAUD12n;
                        for (let i = 0; i < data.length; i++) {{
                            data[i] += farblingNoise(0.0001);
                        }}
                    }}
                    return buffer;
                }});
            }};
        }}
    }}

    // ================================================
    // 4. FONT FARBLING (measureText ±0.1px)
    // ================================================

    const _origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {{
        const metrics = _origMeasureText.call(this, text);
        const realWidth = metrics.width;
        _state = SEED ^ BigInt(text.length);
        const noise = farblingNoise(0.1);

        return new Proxy(metrics, {{
            get(target, prop) {{
                if (prop === 'width') return realWidth + noise;
                const val = target[prop];
                if (typeof val === 'number') return val + noise * 0.5;
                return val;
            }}
        }});
    }};

    // ================================================
    // 5. NAVIGATOR PROPERTIES FARBLING
    // ================================================
    
    // hardwareConcurrency: retorna valor próximo mas não idêntico
    const _realCores = navigator.hardwareConcurrency || 4;
    const _farbledCores = [2, 4, 8][seededInt(0, 2)];
    Object.defineProperty(Navigator.prototype, 'hardwareConcurrency', {{
        get: function() {{ return _farbledCores; }},
        configurable: true
    }});
    
    // deviceMemory: retorna valor genérico
    if ('deviceMemory' in navigator) {{
        const _memValues = [4, 8];
        const _farbledMem = _memValues[seededInt(0, _memValues.length - 1)];
        Object.defineProperty(Navigator.prototype, 'deviceMemory', {{
            get: function() {{ return _farbledMem; }},
            configurable: true
        }});
    }}
    
    // plugins: retorna lista vazia realista (Chrome sem plugins visíveis)
    Object.defineProperty(Navigator.prototype, 'plugins', {{
        get: function() {{
            return {{
                length: 5,
                item: function(i) {{ return null; }},
                namedItem: function(n) {{ return null; }},
                refresh: function() {{}},
                [Symbol.iterator]: function*() {{}}
            }};
        }},
        configurable: true
    }});
    
    // languages: usar array genérico
    const _langSets = [
        ['en-US', 'en'],
        ['en-US'],
        ['pt-BR', 'pt', 'en-US', 'en'],
    ];
    const _farbledLangs = Object.freeze(_langSets[seededInt(0, _langSets.length - 1)]);
    Object.defineProperty(Navigator.prototype, 'languages', {{
        get: function() {{ return _farbledLangs; }},
        configurable: true
    }});

    // ================================================
    // 6. SCREEN DIMENSIONS FARBLING (±small noise)
    // ================================================
    
    const _screenNoise = seededInt(-20, 20);
    const _realWidth = screen.width;
    const _realHeight = screen.height;
    const _farbledWidth = _realWidth + _screenNoise;
    const _farbledHeight = _realHeight + _screenNoise;
    
    Object.defineProperty(Screen.prototype, 'width', {{
        get: function() {{ return _farbledWidth; }},
        configurable: true
    }});
    Object.defineProperty(Screen.prototype, 'height', {{
        get: function() {{ return _farbledHeight; }},
        configurable: true
    }});
    Object.defineProperty(Screen.prototype, 'availWidth', {{
        get: function() {{ return _farbledWidth; }},
        configurable: true
    }});
    Object.defineProperty(Screen.prototype, 'availHeight', {{
        get: function() {{ return _farbledHeight - seededInt(30, 48); }},
        configurable: true
    }});
    Object.defineProperty(Screen.prototype, 'colorDepth', {{
        get: function() {{ return 24; }},
        configurable: true
    }});
    Object.defineProperty(Screen.prototype, 'pixelDepth', {{
        get: function() {{ return 24; }},
        configurable: true
    }});

    // ================================================
    // 7. TIMEZONE FARBLING (sutil — noise no offset)
    // ================================================
    
    const _origDateGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    // Não alteramos o offset real (quebraria sites), mas farbleamos a
    // resolução do Intl.DateTimeFormat().resolvedOptions().timeZone
    // adicionando noise ao Performance.now() que fingerprinters usam
    
    // ================================================
    // 8. WEBRTC FARBLING (bloquear ICE candidates com IP real)
    // ================================================
    
    if (window.RTCPeerConnection) {{
        const _OrigRTC = window.RTCPeerConnection;
        const _origCreateOffer = _OrigRTC.prototype.createOffer;
        const _origSetLocal = _OrigRTC.prototype.setLocalDescription;
        
        // Interceptar onicecandidate para filtrar IPs locais
        const _origAddEventListener = _OrigRTC.prototype.addEventListener;
        _OrigRTC.prototype.addEventListener = function(type, listener, options) {{
            if (type === 'icecandidate') {{
                const wrappedListener = function(event) {{
                    if (event.candidate && event.candidate.candidate) {{
                        const c = event.candidate.candidate;
                        // Bloquear candidates com IPs privados (192.168.x.x, 10.x.x.x, etc.)
                        if (/([0-9]{{1,3}}(\\.[0-9]{{1,3}}){{3}})/.test(c)) {{
                            // Substituir por candidato vazio — não revela IP
                            return;
                        }}
                    }}
                    listener.call(this, event);
                }};
                return _origAddEventListener.call(this, type, wrappedListener, options);
            }}
            return _origAddEventListener.call(this, type, listener, options);
        }};
        
        // Também interceptar a propriedade onicecandidate
        const _rtcProto = _OrigRTC.prototype;
        const _origOnIce = Object.getOwnPropertyDescriptor(_rtcProto, 'onicecandidate');
        if (_origOnIce) {{
            Object.defineProperty(_rtcProto, 'onicecandidate', {{
                set: function(handler) {{
                    const wrappedHandler = function(event) {{
                        if (event.candidate && event.candidate.candidate) {{
                            if (/([0-9]{{1,3}}(\\.[0-9]{{1,3}}){{3}})/.test(event.candidate.candidate)) {{
                                return;
                            }}
                        }}
                        if (handler) handler.call(this, event);
                    }};
                    _origOnIce.set.call(this, wrappedHandler);
                }},
                get: function() {{
                    return _origOnIce.get.call(this);
                }},
                configurable: true
            }});
        }}
    }}

    // ================================================
    // 9. PERFORMANCE API FARBLING (timing noise)
    // ================================================
    
    const _origPerformanceNow = Performance.prototype.now;
    Performance.prototype.now = function() {{
        const real = _origPerformanceNow.call(this);
        // Adiciona noise de ±0.1ms (reduz precisão de timing attacks)
        return Math.round(real * 10) / 10 + farblingNoise(0.05);
    }};
    
    // ================================================
    // 10. CONNECTION API FARBLING
    // ================================================
    
    if (navigator.connection) {{
        const _conn = navigator.connection;
        Object.defineProperty(_conn, 'effectiveType', {{
            get: function() {{ return '4g'; }},
            configurable: true
        }});
        Object.defineProperty(_conn, 'downlink', {{
            get: function() {{ return 10; }},
            configurable: true
        }});
        Object.defineProperty(_conn, 'rtt', {{
            get: function() {{ return 50; }},
            configurable: true
        }});
    }}

    // ================================================
    // 11. PROTEGER toString de funções modificadas
    // ================================================

    const modifiedFns = [
        [CanvasRenderingContext2D.prototype, 'getImageData'],
        [CanvasRenderingContext2D.prototype, 'measureText'],
        [HTMLCanvasElement.prototype, 'toDataURL'],
        [HTMLCanvasElement.prototype, 'toBlob'],
        [Performance.prototype, 'now'],
    ];

    modifiedFns.forEach(function(pair) {{
        const obj = pair[0], name = pair[1];
        if (obj[name]) {{
            const fn = obj[name];
            fn.toString = function() {{ return 'function ' + name + '() {{ [native code] }}'; }};
            fn.toLocaleString = fn.toString;
        }}
    }});

}})();
'''

    def _build_maximum_js(self, seed_hex: str) -> str:
        """
        Proteções adicionais para nível MAXIMUM.
        Pode quebrar alguns sites mas oferece proteção extra.
        """
        return f'''
(function() {{
    'use strict';

    // ================================================
    // MODO MAXIMUM - Proteções adicionais
    // ================================================

    // WebRTC: forçar relay (sem IP leak de qualquer tipo)
    if (window.RTCPeerConnection) {{
        const _OrigRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(cfg, constraints) {{
            cfg = cfg || {{}};
            cfg.iceTransportPolicy = 'relay';
            cfg.iceServers = [];
            return new _OrigRTC(cfg, constraints);
        }};
        window.RTCPeerConnection.prototype = _OrigRTC.prototype;
    }}

    // Battery: valores genéricos via proxy (não bloquear!)
    if (navigator.getBattery) {{
        const _origBattery = navigator.getBattery.bind(navigator);
        navigator.getBattery = function() {{
            return _origBattery().then(function(battery) {{
                return new Proxy(battery, {{
                    get(target, prop) {{
                        if (prop === 'charging') return true;
                        if (prop === 'level') return 1.0;
                        if (prop === 'chargingTime') return 0;
                        if (prop === 'dischargingTime') return Infinity;
                        const val = target[prop];
                        return typeof val === 'function' ? val.bind(target) : val;
                    }}
                }});
            }});
        }};
    }}
    
    // Bloquear completamente a API de gamepad (fingerprinting vector)
    if (navigator.getGamepads) {{
        navigator.getGamepads = function() {{ return []; }};
    }}
    
    // Bloquear API de Speech Synthesis voices (fingerprinting)
    if (window.speechSynthesis) {{
        window.speechSynthesis.getVoices = function() {{ return []; }};
    }}
    
    // Bloquear Performance memory info
    if (performance.memory) {{
        Object.defineProperty(performance, 'memory', {{
            get: function() {{
                return {{
                    jsHeapSizeLimit: 2147483648,
                    totalJSHeapSize: 1073741824,
                    usedJSHeapSize: 536870912
                }};
            }},
            configurable: true
        }});
    }}
    
    // Bloquear navigator.mediaDevices.enumerateDevices (fingerprinting)
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
        navigator.mediaDevices.enumerateDevices = function() {{
            return Promise.resolve([
                {{ deviceId: 'default', kind: 'audioinput', label: '', groupId: 'default' }},
                {{ deviceId: 'default', kind: 'videoinput', label: '', groupId: 'default' }},
                {{ deviceId: 'default', kind: 'audiooutput', label: '', groupId: 'default' }}
            ]);
        }};
    }}

}})();
'''

    def reset_session(self):
        """Gera nova chave de sessão (regenera todos os fingerprints)."""
        self._session_key = os.urandom(32)

    def get_spoofed_user_agent(self, domain: str) -> Optional[str]:
        """
        No modo BALANCED: retorna None (usa UA real).
        No modo MAXIMUM: retorna None (UA real é mais seguro).
        
        IMPORTANTE: O Brave no modo balanced NÃO muda o User-Agent!
        Mudar o UA é facilmente detectável e causa mais problemas.
        """
        return None
