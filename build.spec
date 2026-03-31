# -*- mode: python ; coding: utf-8 -*-
"""
Redux Browser — PyInstaller Build Spec
Empacota o navegador como .exe no modo onedir (obrigatório para QtWebEngine).

Uso:
    pyinstaller build.spec

Saída: dist/ReduxBrowser/ReduxBrowser.exe
"""

import sys
import os
from pathlib import Path

# Detecta o caminho do PyQt6 instalado para localizar os resources do QtWebEngine
import PyQt6
pyqt6_path = Path(PyQt6.__file__).parent

# Caminho do QtWebEngine (inclui Chromium subprocess, .pak, locales, etc.)
qtwe_path = pyqt6_path / "Qt6" / "bin"
qtwe_resources = pyqt6_path / "Qt6" / "resources"
qtwe_locales = pyqt6_path / "Qt6" / "translations" / "qtwebengine_locales"

# Binários extras necessários para QtWebEngine
extra_binaries = []

# QtWebEngineProcess.exe — o subprocess que Chromium precisa
qtwe_process = qtwe_path / "QtWebEngineProcess.exe"
if qtwe_process.exists():
    extra_binaries.append((str(qtwe_process), "PyQt6/Qt6/bin"))

# Recursos do Chromium (.pak files, icudtl.dat)
extra_datas = []

if qtwe_resources.exists():
    extra_datas.append((str(qtwe_resources), "PyQt6/Qt6/resources"))

if qtwe_locales.exists():
    extra_datas.append((str(qtwe_locales), "PyQt6/Qt6/translations/qtwebengine_locales"))

# Assets do projeto
extra_datas.append(('src/assets', 'assets'))

# Ícone do app (será criado pelo release script)
icon_file = 'installer/redux_browser.ico'
if not os.path.exists(icon_file):
    icon_file = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=extra_binaries,
    datas=extra_datas,
    hiddenimports=[
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.sip',
        'certifi',
        'requests',
        'requests.adapters',
        'urllib3',
        'charset_normalizer',
        'idna',
        # Módulos do projeto
        'browser',
        'browser.__version__',
        'browser.ui',
        'browser.ui.main_window',
        'browser.ui.tab',
        'browser.ui.tab_widget',
        'browser.ui.theme',
        'browser.ui.icons',
        'browser.ui.url_bar',
        'browser.ui.bookmarks_bar',
        'browser.ui.bookmarks_dialog',
        'browser.ui.history_dialog',
        'browser.ui.downloads_dialog',
        'browser.ui.downloads_manager',
        'browser.ui.console_widget',
        'browser.ui.dom_viewer',
        'browser.ui.fingerprint_panel',
        'browser.ui.extension_toolbar',
        'browser.ui.extension_popup',
        'browser.ui.extension_page',
        'browser.ui.cws_install_widget',
        'browser.network.http_client',
        'browser.engine.html_parser',
        'browser.engine.css_parser',
        'browser.engine.layout',
        'browser.engine.render_tree',
        'browser.security.brave_farbling',
        'browser.security.farbling_injector',
        'browser.security.adblock_engine',
        'browser.security.adblock_interceptor',
        'browser.security.adblock_injector',
        'browser.security.adblock_tokenizer',
        'browser.security.adblock_request',
        'browser.ui.adblock_panel',
        'browser.cache.cache_manager',
        'browser.history.history_manager',
        'browser.bookmarks.bookmark_manager',
        'browser.config.settings_manager',
        'browser.config.search_engines',
        'browser.extensions.extension_manager',
        'browser.extensions.extension_model',
        'browser.extensions.manifest_parser',
        'browser.extensions.crx_parser',
        'browser.extensions.content_script_loader',
        'browser.extensions.ext_url_handler',
        'browser.extensions.chrome_web_store',
        'browser.extensions.chrome_api.api_storage',
        'browser.extensions.chrome_api.api_tabs',
        'browser.updater.update_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'tests',
        'pytest',
        'setuptools',
        'pip',
        'distutils',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir mode
    name='ReduxBrowser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version_info=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReduxBrowser',
)
