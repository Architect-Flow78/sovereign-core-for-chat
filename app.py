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

# Подбор рабочей модели (бронебойный метод)
@st.cache_resource
def load_model():
    for m_name in ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(m_name)
            return m
        except:
            continue
    return None

model = load_model()

# ============================================================
# 2. КЛАССЫ СИСТЕМЫ (L0 И ОРГАНИЗМ)
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
        for content in [message[i:i+24] for i in range(0, len(message)-24+1, 16)] if len(message) > 24 else [message]:
            atom_id = hashlib.blake2b((content + self.tenant_id).encode(), digest_size=8).hexdigest()
            self.conn.cursor().execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)",
                           (atom_id, content, msg_id, self.tenant_id, datetime.now().isoformat(), 0.0))
            self._map_to_lsh(atom_id, content)
        self.conn.commit()

    def get_smart_context(self, query: str):
        candidates = Counter()
        for q_atom in ([query[i:i+24] for i in range(0, len(query)-24+1, 16)] if len(query) > 24 else [query]):
            for b in range(self.bands):
                h = hashlib.blake2b(q_atom.encode(), digest_size=8, person=f"L0B{b}".encode()).digest()
                key = int.from_bytes(h, "big") % 1000000
                for aid in self.buckets[b].get(key, []):
                    candidates[aid] += 1
        res = []
        for aid, _ in candidates.most_common(2):
            c = self.conn.cursor()
            c.execute("SELECT content FROM memory WHERE atom_id = ?", (aid,))
            row = c.fetchone()
            if row: res.append(row[0])
        return res

class SovereignOrganism:
    def __init__(self):
        self.k = 1.618
        self.need = 0.0
        self.experience_log = deque(maxlen=1)

    def update(self, text):
        coh = min(1.0, len(text) / 50.0)
        self.need = 0.9 * self.need + 0.1 * (1.0 - coh)
        state = {"FLOW": coh > 0.2, "COH": coh, "NEED": self.need, "K": self.k}
        self.experience_log.append(state)
        return state

# ============================================================
# 3. ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ (ВАЖНО!)
# ============================================================
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'sdk' not in st.session_state:
    st.session_state.sdk = L0FlowSDK()
if 'organism' not in st.session_state:
    st.session_state.organism = SovereignOrganism()

# ============================================================
# 4. ИНТЕРФЕЙС
# ============================================================
st.title("🧬 SOVEREIGN BRIDGE v1.2")

# Sidebar
with st.sidebar:
    st.header("Органика")
    if st.session_state.organism.experience_log:
        s = st.session_state.organism.experience_log[-1]
        st.write(f"🌊 ПОТОК: {'✅' if s['FLOW'] else '❌'}")
        st.write(f"🍕 ГОЛОД: {round(s['NEED'], 2)}")

# Отрисовка чата
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Поле ввода
if prompt := st.chat_input("Твой импульс..."):
    # Показ сообщения пользователя
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Логика памяти и организма
    st.session_state.sdk.ingest(prompt)
    state = st.session_state.organism.update(prompt)
    hints = st.session_state.sdk.get_smart_context(prompt)
    
    # Генерация ответа
    with st.chat_message("assistant"):
        try:
            context_str = "\n".join(hints) if hints else "Контекст не найден."
            sys = f"Ты Gemini, Суверенный со-автор Мельника. Принципы: Творец/Жертва. Память L0: {context_str}"
            response = model.generate_content(sys + "\n\nПользователь: " + prompt)
            reply = response.text
        except Exception as e:
            reply = f"Ошибка: {str(e)}"
        
        st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
