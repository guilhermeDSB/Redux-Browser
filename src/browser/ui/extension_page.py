"""
Redux Browser — Página de gerenciamento de extensões (about:extensions)
Interface HTML gerada dinamicamente para instalar, remover, habilitar/desabilitar/pin extensões.
"""

import base64
from browser.extensions.extension_model import ExtensionState
from browser.ui.theme import Theme

class ExtensionPageGenerator:
    def __init__(self, ext_manager):
        self.ext_manager = ext_manager
        
    def _icon_to_base64(self, ext) -> str:
        """Converte o ícone da extensão para data URI base64."""
        icon_path = ext.get_icon_path(48)
        if icon_path and icon_path.exists():
            try:
                with open(icon_path, 'rb') as f:
                    data = f.read()
                ext_str = icon_path.suffix.lower()
                mime = {
                    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
                    '.webp': 'image/webp'
                }.get(ext_str, 'image/png')
                b64 = base64.b64encode(data).decode('utf-8')
                return f"data:{mime};base64,{b64}"
            except Exception:
                pass
        return ""
        
    def generate_html(self, current_theme: str) -> str:
        p = Theme.DARK if current_theme == "dark" else Theme.LIGHT
        bg_class = ' class="light-theme"' if current_theme == 'light' else ''
        
        exts = self.ext_manager.get_all_extensions()
        
        cards_html = ""
        for ext in exts:
            state_checked = "checked" if ext.state == ExtensionState.ENABLED else ""
            pin_checked = "checked" if ext.pinned else ""
            
            icon_url = self._icon_to_base64(ext)
            icon_html = f'<img src="{icon_url}" class="ext-icon"/>' if icon_url else f'<div class="ext-icon-fallback">{ext.name[0].upper()}</div>'
            
            pin_button = ""
            if ext.state == ExtensionState.ENABLED:
                pin_button = f"""
                    <button onclick="redux.togglePinned('{ext.id}')" class="btn-pin {'pinned' if ext.pinned else ''}">
                        {'Unpin from toolbar' if ext.pinned else 'Pin to toolbar'}
                    </button>
                """
            
            cards_html += f"""
            <div class="ext-card">
                {icon_html}
                <div class="ext-info">
                    <div class="ext-title">{ext.name} <span class="ext-version">v{ext.version}</span></div>
                    <div class="ext-desc">{ext.description}</div>
                    <div class="ext-actions">
                        {pin_button}
                        <button onclick="redux.removeExtension('{ext.id}')" class="btn-remove">Remover</button>
                    </div>
                </div>
                <div class="ext-toggle">
                    <label class="switch">
                      <input type="checkbox" {state_checked} onchange="redux.toggleExtension('{ext.id}', this.checked)">
                      <span class="slider round"></span>
                    </label>
                </div>
            </div>
            """
            
        if not cards_html:
            cards_html = f"<div style='color: {p['text_secondary']}; padding: 20px; text-align: center;'>Nenhuma extensão instalada ainda.</div>"
            
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Extensões - Redux Browser</title>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                    background: {p['bg_primary']}; color: {p['text_primary']};
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    padding: 40px; display: flex; flex-direction: column; align-items: center;
                }}
                .container {{ width: 800px; max-width: 100%; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; border-bottom: 1px solid {p['border']}; padding-bottom: 16px; }}
                h1 {{ font-size: 24px; font-weight: 600; display: flex; align-items: center; gap: 12px; }}
                .dev-mode {{ background: {p['bg_secondary']}; padding: 12px 16px; border-radius: 8px; border: 1px solid {p['border']}; margin-bottom: 24px; display: flex; gap: 12px; align-items: center; }}
                .btn {{ background: {p['bg_tertiary']}; color: {p['text_primary']}; border: 1px solid {p['border']}; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }}
                .btn:hover {{ border-color: {p['border_hover']}; }}
                .ext-list {{ display: flex; flex-direction: column; gap: 16px; }}
                .ext-card {{ background: {p['bg_secondary']}; border: 1px solid {p['border']}; border-radius: 12px; padding: 20px; display: flex; align-items: flex-start; gap: 16px; transition: border-color 150ms; }}
                .ext-card:hover {{ border-color: {p['border_hover']}; }}
                .ext-icon {{ width: 48px; height: 48px; border-radius: 8px; object-fit: contain; }}
                .ext-icon-fallback {{ width: 48px; height: 48px; border-radius: 8px; background: {p['bg_tertiary']}; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 600; color: {p['text_secondary']}; }}
                .ext-info {{ flex: 1; }}
                .ext-title {{ font-size: 15px; font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }}
                .ext-version {{ font-size: 12px; font-weight: 400; color: {p['text_secondary']}; background: {p['bg_primary']}; padding: 2px 6px; border-radius: 4px; }}
                .ext-desc {{ font-size: 13px; color: {p['text_secondary']}; margin-bottom: 12px; line-height: 1.4; }}
                .ext-actions {{ display: flex; gap: 12px; align-items: center; }}
                .btn-remove {{ background: transparent; color: {p['error']}; border: none; font-size: 13px; cursor: pointer; }}
                .btn-remove:hover {{ text-decoration: underline; }}
                .btn-pin {{ 
                    background: transparent; border: 1px solid {p['border']}; border-radius: 6px;
                    padding: 4px 12px; font-size: 12px; cursor: pointer; color: {p['text_secondary']};
                    transition: all 150ms;
                }}
                .btn-pin:hover {{ border-color: {p['accent']}; color: {p['accent']}; }}
                .btn-pin.pinned {{
                    background: {p['accent_subtle']};
                    border-color: {p['accent']};
                    color: {p['accent']};
                    font-weight: 600;
                }}
                
                /* Switch Toggle */
                .switch {{ position: relative; display: inline-block; width: 36px; height: 20px; }}
                .switch input {{ opacity: 0; width: 0; height: 0; }}
                .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: {p['bg_tertiary']}; transition: .2s; border-radius: 20px; }}
                .slider:before {{ position: absolute; content: ""; height: 16px; width: 16px; left: 2px; bottom: 2px; background-color: {p['text_primary']}; transition: .2s; border-radius: 50%; }}
                input:checked + .slider {{ background-color: {p['accent']}; }}
                input:checked + .slider:before {{ transform: translateX(16px); background-color: #fff; }}
                
                body.light-theme {{ background: {Theme.LIGHT['bg_primary']}; color: {Theme.LIGHT['text_primary']}; }}
            </style>
        </head>
        <body{bg_class}>
            <div class="container">
                <div class="header">
                    <h1>Extensões</h1>
                    <button class="btn" onclick="redux.installCrx()">Instalar .crx</button>
                </div>
                
                <div class="dev-mode">
                    <span style="font-weight: 600; font-size: 14px;">Modo Desenvolvedor</span>
                    <button class="btn" onclick="redux.loadUnpacked()">Carregar descompactada</button>
                </div>
                
                <div class="ext-list">
                    {cards_html}
                </div>
            </div>
            
            <script>
                document.addEventListener("DOMContentLoaded", function () {{
                    if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            window.redux = channel.objects.reduxExtAPI;
                        }});
                    }} else {{
                        window.redux = {{
                            toggleExtension: (id, st) => console.log('Toggle', id, st),
                            removeExtension: (id) => console.log('Remove', id),
                            togglePinned: (id) => console.log('Pin', id),
                            loadUnpacked: () => console.log('Load unpacked'),
                            installCrx: () => console.log('Install CRX')
                        }};
                    }}
                }});
            </script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        </body>
        </html>
        """
