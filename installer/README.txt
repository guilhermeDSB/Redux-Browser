Este diretório contém os arquivos do instalador:

- redux_browser.iss  — Script do Inno Setup
- redux_browser.ico  — Ícone do app (substitua por um .ico real)

Para gerar o .ico a partir de um PNG:
  pip install Pillow
  python -c "from PIL import Image; Image.open('icon.png').save('installer/redux_browser.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
