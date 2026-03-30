# Redux Browser

Navegador web moderno construído com Python e PyQt6 com fins educacionais, possuindo uma engine customizada auxiliar.

## Funcionalidades
- Interface PyQt6 com "Speed Dial" e Redux Branding.
- Toggle de Motor: Transite entre o robusto **QtWebEngine** e o didático **Redux Engine**.
- **Redux Engine**:
  - Parser HTML5 e DOM Tree customizados.
  - Parser CSS com regras de especificidade e cascata.
  - Render Tree iterativa descartando nós `display: none`.
  - Flow Layout em tempo de execução calculando Box Models interativamente.
- **DevTools**: Inspect sidebar para visualização em tempo real de propriedades DOM e Estilos computados.

## Requisitos Prévios
- Python 3.11+
- Dependências em `requirements.txt`

## Como rodar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o projeto:
   ```bash
   python src/main.py
   ```

## Testes
Rode a bateria de testes integrados:
```bash
python -m unittest discover tests
```
