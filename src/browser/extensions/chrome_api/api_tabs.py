"""
Redux Browser — Implementação de chrome.tabs
Permite extensões interagirem com as abas do browser.
"""

class ChromeTabsAPI:
    def __init__(self, tab_widget):
        self.tab_widget = tab_widget
    
    def query(self, query_info: dict) -> list:
        """
        Retorna lista de abas que correspondem aos critérios.
        """
        results = []
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            # Verifica active e currentWindow
            if query_info.get("active") is True:
                if self.tab_widget.currentIndex() != i:
                    continue
            
            # TODO: Full URL pattern matching
            
            results.append(self.to_tab_info(i))
            
        return results
    
    def create(self, props: dict) -> dict:
        """Cria nova aba."""
        url = props.get("url", "about:home")
        active = props.get("active", True)
        
        new_tab = self.tab_widget.add_new_tab(url)
        if hasattr(self.tab_widget, 'indexOf') and active:
            idx = self.tab_widget.indexOf(new_tab)
            if idx >= 0:
                self.tab_widget.setCurrentIndex(idx)
        return {"id": id(new_tab), "url": url}
    
    def to_tab_info(self, tab_index: int) -> dict:
        """
        Converte uma aba do Redux Browser para o formato chrome.tabs.Tab.
        """
        tab = self.tab_widget.widget(tab_index)
        url = tab.web_view.url().toString() if hasattr(tab, 'web_view') else ""
        title = self.tab_widget.tabText(tab_index)
        
        return {
            "id": id(tab),
            "index": tab_index,
            "active": self.tab_widget.currentIndex() == tab_index,
            "url": url,
            "title": title,
            "status": "complete", # Mock simplificado
            "incognito": getattr(tab, "is_private", False)
        }
