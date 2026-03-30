import unittest
import sys
import os

# Ajuste do path para importar módulos da source
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from browser.network.http_client import HttpClient

class TestHttpClient(unittest.TestCase):
    def setUp(self):
        self.client = HttpClient()

    def test_get_request_success(self):
        """Testa se uma requisição GET simples retorna HTTP 200"""
        response = self.client.get("https://httpbin.org/get")
        self.assertIsNotNone(response, "A resposta não deve ser None")
        self.assertEqual(response.status_code, 200)

    def test_user_agent_header(self):
        """Verifica se o header User-Agent customizado está sendo enviado"""
        response = self.client.get("https://httpbin.org/headers")
        self.assertIsNotNone(response)
        
        json_data = response.json()
        self.assertIn("headers", json_data)
        self.assertIn("ReduxBrowser", json_data["headers"]["User-Agent"])

if __name__ == "__main__":
    unittest.main()
