import hashlib
import re
import math
import sqlite3
import streamlit as st
import google.generativeai as genai
from collections import defaultdict, Counter, deque
from datetime import datetime

# ============================================================
# 1. КОНФИГУРАЦИЯ И API
# ============================================================
st.set_page_config(page_title="Sovereign Bridge", page_icon="🧬", layout="wide")

# Инициализация API
API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"
genai.configure(api_key=API_KEY)

@st.cache_resource
def load_model():
    # Список имен моделей для перебора в случае 404
    for m_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(model_name=m_name)
            return m
        except:
            continue
    return None

model = load_model()

# ============================================================
# 2. КЛАССЫ СИСТЕМЫ
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
        self.conn.cursor().execute("""CREATE TABLE IF NOT EXISTS memory 
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
        atoms = [message[i:i+24] for i in range(0, len(message)-24+1, 16)] if len(message) > 24 else [message]
        for content in atoms:
            atom_id = hashlib.blake2b((content + self.tenant_id).encode(), digest_size=8).hexdigest()
            self.conn.cursor().execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)",
                           (atom_id
