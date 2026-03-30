# Redux Browser 🌐

Um navegador web personalizado construído do zero com **Python**, **PyQt6** e **QtWebEngine**, focado em privacidade e anti-fingerprinting.

## ✨ Funcionalidades

- 🔒 **Anti-Fingerprint** — Proteção estilo Brave com 3 níveis (off / balanced / maximum): Canvas, WebGL, Audio, Navigator, Screen, WebRTC, Performance e mais
- 🌐 **Motor de Renderização Próprio** — Parser HTML/CSS com suporte a seletores hierárquicos, `!important`, unidades `em`/`rem`, shorthand expansion
- 🧩 **Sistema de Extensões** — Compatibilidade com Chrome APIs (`chrome.storage`, `chrome.tabs`), content scripts, suporte a CRX
- 📑 **Gerenciamento Completo** — Favoritos, histórico (10K entradas, dedup), cache (LRU, TTL, ETag, 100MB), downloads com pause/resume
- 🛠️ **DevTools** — Console JavaScript, DOM Viewer, Painel de Fingerprint
- 🔄 **Auto-Update** — Sistema de atualização automática via GitHub Releases
- 🎨 **UI Tema Escuro** — Interface moderna inspirada em navegadores modernos

## 🚀 Instalação

### Requisitos
- Python 3.12+
- pip

### Executar do código fonte
```bash
git clone https://github.com/guilhermeDSB/Redux-Browser.git
cd Redux-Browser
pip install -r requirements.txt
python src/main.py
```

### Build do executável
```bash
pip install pyinstaller
python -m PyInstaller build.spec --clean --noconfirm
# Executável em dist/ReduxBrowser/ReduxBrowser.exe
```

## 🧪 Testes

```bash
python -m pytest tests/ -v
```

60 testes unitários cobrindo todos os módulos principais.

## 📁 Estrutura do Projeto

```
src/
├── main.py                    # Ponto de entrada
├── browser/
│   ├── __version__.py         # Versionamento centralizado
│   ├── engine/                # Motor de renderização (HTML/CSS parser, layout)
│   ├── extensions/            # Sistema de extensões + Chrome APIs
│   ├── network/               # Cliente HTTP
│   ├── security/              # Anti-fingerprint (Brave farbling)
│   ├── ui/                    # Interface gráfica (PyQt6)
│   ├── updater/               # Sistema de auto-update
│   ├── bookmarks/             # Gerenciador de favoritos
│   ├── cache/                 # Cache com LRU/TTL
│   ├── config/                # Configurações e search engines
│   └── history/               # Gerenciador de histórico
tests/                         # 60 testes unitários
scripts/                       # Scripts de build e release
installer/                     # Inno Setup installer config
```

## 📄 Licença

MIT License

## 👤 Autor

**guilhermeDSB**