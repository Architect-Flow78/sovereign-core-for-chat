import hashlib
import re
import math
import sqlite3
import streamlit as st
import requests  # Будем слать запросы напрямую, без посредников
from collections import defaultdict, Counter, deque
from datetime import datetime

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="Sovereign Bridge", page_icon="🧬", layout="wide")

# Берем ключ
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"

# ============================================================
# ТВОЙ ЦЕЛЫЙ КОД (L0 и ОРГАНИЗМ) - БЕЗ ИЗМЕНЕНИЙ
# ============================================================
class L0FlowSDK:
    def __init__(self, db_path="l0_memory.db", tenant_id="Melnik_Creator"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.tenant_id = tenant_id
        self.bands = 8
        self.buckets = [defaultdict(list) for _ in range(self.bands)]
        self._init_db()
        self._load_index()

    def _init_db(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS memory 
            (atom_id TEXT PRIMARY KEY, content TEXT, msg_id TEXT, 
             tenant_id TEXT, timestamp DATETIME, entropy REAL)""")
        self.conn.commit()

    def _load_index(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT atom_id, content FROM memory WHERE tenant_id = ?", (self.tenant_id,))
        for aid, cnt in cursor.fetchall():
            self._map_to_lsh(aid, cnt)

    def _map_to_lsh(self, atom_id: str, content: str):
        for b in range(self.bands):
            h = hashlib.blake2b(content.encode(), digest_size=8, person=f"L0B{b}".encode()).digest()
            key = int.from_bytes(h, "big") % 1000000 
            if atom_id not in self.buckets[b][key]:
                self.buckets[b][key].append(atom_id)

    def ingest(self, message: str):
        msg_id = hashlib.blake2b(message.encode(), digest_size=8).hexdigest()
        for content in self._atomize(message):
            atom_id = hashlib.blake2b((content + self.tenant_id).encode(), digest_size=8).hexdigest()
            self.conn.execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)",
                           (atom_id, content, msg_id, self.tenant_id, datetime.now().isoformat(), 0.0))
            self._map_to_lsh(atom_id, content)
        self.conn.commit()

    def get_smart_context(self, query: str):
        candidates = Counter()
        for q_atom in self._atomize(query):
            for b in range(self.bands):
                h = hashlib.blake2b(q_atom.encode(), digest_size=8, person=f"L0B{b}".encode()).digest()
                key = int.from_bytes(h, "big") % 1000000
                for aid in self.buckets[b].get(key, []):
                    candidates[aid] += 1
        res = []
        for aid, _ in candidates.most_common(2):
            cursor = self.conn.cursor().execute("SELECT content FROM memory WHERE atom_id = ?", (aid,))
            row = cursor.fetchone()
            if row: res.append(row[0])
        return res

    def _atomize(self, text: str):
        text = text.lower().strip()
        return [text[i:i+24] for i in range(0, len(text)-24+1, 16)] if len(text) > 24 else [text]

class SovereignOrganism:
    def __init__(self):
        self.experience_log = deque(maxlen=1)
    def update(self, text):
        state = {"FLOW": len(text) > 5}
        self.experience_log.append(state)
        return state

# ============================================================
# ИНТЕРФЕЙС И ПРЯМОЙ ВЫЗОВ (ФИКС 404)
# ============================================================
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'sdk' not in st.session_state: st.session_state.sdk = L0FlowSDK()
if 'organism' not in st.session_state: st.session_state.organism = SovereignOrganism()

st.title("🧬 SOVEREIGN BRIDGE")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Твой импульс..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    st.session_state.sdk.ingest(prompt)
    hints = st.session_state.sdk.get_smart_context(prompt)
    context_str = "\n".join(hints) if hints else "Чисто."

    # ПРЯМОЙ HTTP ЗАПРОС К МОДЕЛИ (ОБХОД БАГА 404)
    with st.chat_message("assistant"):
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": f"Ты со-автор Мельника. Память: {context_str}\n\nЗапрос: {prompt}"}]
            }]
        }
        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                reply = r.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                reply = f"Ошибка сервера {r.status_code}: {r.text}"
        except Exception as e:
            reply = f"Ошибка связи: {e}"
        
        st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
