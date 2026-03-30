import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView

sys.path.insert(0, os.path.abspath('src'))
from browser.security.brave_farbling import FarblingEngine, FarblingLevel
from browser.security.farbling_injector import FarblingInjector

app = QApplication(sys.argv)
engine = FarblingEngine(FarblingLevel.BALANCED)
injector = FarblingInjector(engine)

view = QWebEngineView()
injector.inject(view.page(), "localhost")

html_path = os.path.abspath("src/assets/default_pages/fingerprint_test.html")
url = QUrl.fromLocalFile(html_path)

def on_load_finished(ok):
    if not ok:
        print("FAIL: Could not load the diagnostic page")
        app.quit()
        return
    # Wait for async JS to finish
    QTimer.singleShot(5000, extract)

def extract():
    js = """
    (function() {
        const summary = document.getElementById('summary');
        const results = document.getElementById('results');
        const hash = document.getElementById('final-hash');
        return (summary ? summary.innerText : 'NO SUMMARY') + 
               '\\n\\n=== RESULTS ===\\n' + 
               (results ? results.innerText : 'NO RESULTS') +
               '\\n\\n=== HASH ===\\n' +
               (hash ? hash.innerText : 'NO HASH');
    })();
    """
    view.page().runJavaScript(js, print_and_quit)

def print_and_quit(result):
    with open("fingerprint_report.txt", "w", encoding="utf-8") as f:
        f.write("=== FINGERPRINT DIAGNOSTIC RESULTS ===\n")
        f.write(str(result))
    print("SAVED")
    app.quit()

view.loadFinished.connect(on_load_finished)
view.load(url)

# Inicia o loop de eventos (bloqueia até app.quit ser chamado)
app.exec()
