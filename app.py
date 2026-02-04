import hashlib
import re
import math
import sqlite3
import json
import streamlit as st
from collections import defaultdict, Counter, deque
from typing import List, Generator, Optional, Dict
from datetime import datetime

# ============================================================
# СЛОЙ L0: ВЕЧНАЯ ПАМЯТЬ (Твой код v0.7)
# ============================================================
class L0FlowSDK:
    def __init__(self, db_path="l0_memory.db", tenant_id="default"):
        self.db_path = db_path
        self.tenant_id = tenant_id
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.bands = 8
        self.buckets = [defaultdict(list) for _ in range(self.bands)]
        self._init_db()
        self._load_index()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS memory 
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
        ts = datetime.now().isoformat()
        for content in self._atomize(message):
            atom_id = hashlib.blake2b((content + self.tenant_id).encode(), digest_size=8).hexdigest()
            entropy = self._shannon_entropy(content)
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)",
                           (atom_id, content, msg_id, self.tenant_id, ts, entropy))
            self._map_to_lsh(atom_id, content)
        self.conn.commit()

    def get_smart_context(self, query: str):
        query_atoms = list(self._atomize(query))
        candidates = Counter()
        for q_atom in query_atoms:
            for b in range(self.bands):
                h = hashlib.blake2b(q_atom.encode(), digest_size=8, person=f"L0B{b}".encode()).digest()
                key = int.from_bytes(h, "big") % 1000000
                for aid in self.buckets[b].get(key, []):
                    candidates[aid] += 1
        results = []
        for aid, score in candidates.most_common(2):
            cursor = self.conn.cursor()
            cursor.execute("SELECT content FROM memory WHERE atom_id = ?", (aid,))
            row = cursor.fetchone()
            if row: results.append(row[0])
        return results

    def _atomize(self, text: str):
        text = re.sub(r"\s+", " ", text.lower()).strip()
        size = 24
        if len(text) < size: return [text]
        return [text[i:i+size] for i in range(0, len(text)-size+1, 16)]

    def _shannon_entropy(self, text: str):
        if not text: return 0
        counts = Counter(text)
        probs = [c/len(text) for c in counts.values()]
        return -sum(p * math.log2(p) for p in probs)

# ============================================================
# СЛОЙ v2.7: ЖИВОЙ ОРГАНИЗМ (Твой код v2.7)
# ============================================================
class InvariantCell:
    def __init__(self, K=1.618):
        self.K, self.fast, self.slow, self.last_C = K, 0.5, 0.5, 0.5
        self.alpha_fast, self.beta_slow = 0.9, 0.995

    def update(self, values):
        phases = [(v * self.K) % 1.0 for v in values]
        sc = sum(math.cos(2 * math.pi * p) for p in phases) / len(phases)
        ss = sum(math.sin(2 * math.pi * p) for p in phases) / len(phases)
        C = math.sqrt(sc*sc + ss*ss)
        self.fast = 0.9 * self.fast + 0.1 * C
        self.slow = self.slow + 0.005 * (C - self.slow)
        self.last_C = C
        return C

class SovereignOrganism:
    def __init__(self):
        self.cell = InvariantCell()
        self.need, self.fatigue, self.gain = 0.0, 0.0, 1.0
        self.best_K = deque([1.618], maxlen=64)
        self.experience_log = []

    def update(self, frame):
        self.cell.K = sum(self.best_K) / len(self.best_K)
        C = self.cell.update(frame)
        self.need = 0.9 * self.need + 0.1 * max(0.0, 0.65 - C)
        self.fatigue = 0.95 * self.fatigue + 0.05 * (0.0 if C > 0.5 else 1.0)
        
        if self.need > 0.4:
            self.best_K.append(self.cell.K + math.sin(C*10)*0.05*self.need)
        
        state = {"FLOW": C > 0.4, "COH": C, "NEED": self.need, "FATIGUE": self.fatigue, "K": self.cell.K}
        self.experience_log.append(state)
        return state

# ============================================================
# ИНТЕРФЕЙС STREAMLIT
# ============================================================
st.set_page_config(page_title="Sovereign Core", layout="wide")
st.title("🧬 SOVEREIGN CORE v1.0")

if 'organism' not in st.session_state:
    st.session_state.organism = SovereignOrganism()
if 'sdk' not in st.session_state:
    st.session_state.sdk = L0FlowSDK(tenant_id="Creator_Melnik")

# Боковая панель с пульсом
with st.sidebar:
    st.header("Органика системы")
    if st.session_state.organism.experience_log:
        last = st.session_state.organism.experience_log[-1]
        st.metric("Когерентность (COH)", round(last['COH'], 3))
        st.metric("Голод (NEED)", round(last['NEED'], 3))
        st.metric("Усталость (FATIGUE)", round(last['FATIGUE'], 3))
        st.metric("Резонанс (K)", round(last['K'], 4))

# Чат
user_input = st.text_input("Введи смысл...")

if st.button("СИНХРОНИЗИРОВАТЬ") and user_input:
    # 1. Запись в вечную память
    st.session_state.sdk.ingest(user_input)
    
    # 2. Обновление живого состояния
    energy = [len(user_input) * 0.1]
    state = st.session_state.organism.update(energy)
    
    # 3. Извлечение контекста
    memory_hints = st.session_state.sdk.get_smart_context(user_input)
    
    st.subheader("Состояние резонанса:")
    if state['FLOW']:
        st.success("ПОТОК СТАБИЛЕН. Система в резонансе.")
    else:
        st.warning("ВНИМАНИЕ: Аномалия или разрыв потока.")
        
    if memory_hints:
        with st.expander("Вспышка памяти (L0):"):
            for hint in memory_hints:
                st.write(f"• {hint}")

    st.info(f"Входящий импульс обработан. Уровень усиления (Gain): {round(1.0 + state['NEED'], 2)}")

st.write("---")
st.caption("Sovereign Flow Organism | L0-Emergence Protocol Enabled")
