import pytest
from browser.extensions.chrome_api.api_tabs import ChromeTabsAPI

class MockTab:
    def __init__(self, idx, url, title, active):
        self._url = url
        self._title = title
        self.active = active
        self.is_private = False
        
        class MockWebView:
            def url(self):
                class MockQUrl:
                    def toString(self): return url
                return MockQUrl()
        self.web_view = MockWebView()

class MockTabWidget:
    def __init__(self):
        self.tabs = [
            MockTab(0, "https://google.com", "Google", True),
            MockTab(1, "https://github.com", "GitHub", False)
        ]
        
    def count(self): return len(self.tabs)
    def widget(self, idx): return self.tabs[idx]
    def currentIndex(self): return 0
    def tabText(self, idx): return self.tabs[idx]._title
    def add_new_tab(self, url):
        t = MockTab(2, url, "New Tab", True)
        self.tabs.append(t)
        return t

@pytest.fixture
def api_tabs():
    widget = MockTabWidget()
    return ChromeTabsAPI(widget)
    
def test_query_active_tab(api_tabs):
    res = api_tabs.query({"active": True})
    assert len(res) == 1
    assert res[0]["url"] == "https://google.com"

def test_query_all_tabs(api_tabs):
    res = api_tabs.query({})
    assert len(res) == 2

def test_create_tab(api_tabs):
    res = api_tabs.create({"url": "about:extensions", "active": True})
    assert res["url"] == "about:extensions"
    assert api_tabs.tab_widget.count() == 3
