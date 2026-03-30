import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class HistoryEntry:
    url: str
    title: str
    timestamp: str
    favicon_url: Optional[str] = None

class HistoryManager:
    """
    Controla o histórico de navegação per-tab para back/forward e histórico global persistido.
    Respeita tabs de Navegação Privada (neste caso ignore_save seria true).
    """
    # Limite máximo de entradas no histórico global
    MAX_HISTORY_SIZE = 10000
    
    def __init__(self, storage_path: str = "~/.redux_browser/history.json"):
        self.storage_path = os.path.expanduser(storage_path)
        
        # O estado de pilhas back/forward por aba (memoria efêmera)
        # Formato: { "tab_id": {"history": [HistoryEntry], "current_index": int} }
        self.tab_states: Dict[str, Dict] = {}
        
        # O Histórico Global de todo o navagedor (persistido em disco)
        self.global_history: List[HistoryEntry] = []
        
        self._load()

    def add_entry(self, tab_id: str, url: str, title: str, is_private: bool = False):
        if url.startswith("about:"): return # Nao salva meta pages
        
        entry = HistoryEntry(
            url=url, 
            title=title, 
            timestamp=datetime.now().isoformat()
        )
        
        # 1. Atualizar a Pilha Local da Tab
        if tab_id not in self.tab_states:
            self.tab_states[tab_id] = {"history": [], "current_index": -1}
            
        state = self.tab_states[tab_id]
        
        # Se fomos para trás e surfamos uma nova page, limpa a ramificação forward
        if state["current_index"] < len(state["history"]) - 1:
            state["history"] = state["history"][:state["current_index"] + 1]
            
        # Nao re-adiciona se a URL atual for exatamente igual à inserida (só de reload)
        if not state["history"] or state["history"][-1].url != url:
            state["history"].append(entry)
            state["current_index"] = len(state["history"]) - 1
            
        # 2. Persistir no Global se não for aba privada
        if not is_private:
            # Deduplicação: não adicionar se a URL mais recente for idêntica
            if self.global_history and self.global_history[0].url == url:
                # Atualiza o timestamp da entrada existente
                self.global_history[0].timestamp = entry.timestamp
                self.global_history[0].title = title
            else:
                self.global_history.insert(0, entry) # Insere no inicio pra ordem descrescente mais recente
            
            # Aplicar limite de tamanho
            if len(self.global_history) > self.MAX_HISTORY_SIZE:
                self.global_history = self.global_history[:self.MAX_HISTORY_SIZE]
            
            self._save()

    def can_go_back(self, tab_id: str) -> bool:
        state = self.tab_states.get(tab_id)
        return state and state["current_index"] > 0

    def can_go_forward(self, tab_id: str) -> bool:
        state = self.tab_states.get(tab_id)
        return state and state["current_index"] < len(state["history"]) - 1

    def go_back(self, tab_id: str) -> Optional[str]:
        if not self.can_go_back(tab_id): return None
        self.tab_states[tab_id]["current_index"] -= 1
        return self.tab_states[tab_id]["history"][self.tab_states[tab_id]["current_index"]].url

    def go_forward(self, tab_id: str) -> Optional[str]:
        if not self.can_go_forward(tab_id): return None
        self.tab_states[tab_id]["current_index"] += 1
        return self.tab_states[tab_id]["history"][self.tab_states[tab_id]["current_index"]].url
        
    def remove_tab_state(self, tab_id: str):
        if tab_id in self.tab_states:
            del self.tab_states[tab_id]

    def clear_history(self, tab_id: Optional[str] = None):
        """Se tab_id is None, esvazia do disco e global. Se não, reseta só local via backend."""
        if tab_id:
            self.tab_states[tab_id] = {"history": [], "current_index": -1}
        else:
            self.global_history.clear()
            self._save()
    
    def delete_entry(self, url: str, timestamp: str = None) -> bool:
        """Remove uma entrada específica do histórico global."""
        for i, entry in enumerate(self.global_history):
            if entry.url == url:
                if timestamp is None or entry.timestamp == timestamp:
                    self.global_history.pop(i)
                    self._save()
                    return True
        return False

    def get_history(self) -> List[HistoryEntry]:
        return self.global_history

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = [{"url": e.url, "title": e.title, "timestamp": e.timestamp} for e in self.global_history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] Erro ao salvar histórico: {e}")

    def _load(self):
        if not os.path.exists(self.storage_path): return
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.global_history = [HistoryEntry(**d) for d in data]
        except Exception as e:
            print(f"[History] Erro ao carregar histórico: {e}")
