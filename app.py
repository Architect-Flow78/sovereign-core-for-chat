import hashlib
import re
import math
import sqlite3
import streamlit as st
import google.generativeai as genai
from collections import defaultdict, Counter, deque
from datetime import datetime

# ============================================================
# 1. СТРОГО ПЕРВЫМ
# ============================================================
st.set_page_config(page_title="Sovereign Bridge", page_icon="🧬", layout="wide")

# Подключаем ключ из того окна, которое ты видел на скриншоте
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"

genai.configure(api_key=API_KEY)

# ============================================================
# 2. СЛОЙ L0: ВЕЧНАЯ ПАМЯТЬ (ТВОЙ ЦЕЛЫЙ КОД)
# ============================================================
class L0FlowSDK:
    def __init__(self, db_path="l0_memory.db", tenant_id="Melnik_Creator"):
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
        for aid, score in candidates.most_common(3):
            cursor = self.conn.cursor()
            cursor.execute("SELECT content FROM memory WHERE atom_id = ?", (aid,))
            row = cursor.fetchone()
            if row: results.append(row[0])
        return results

    def _atomize(self, text: str):
        text = re.sub(r"\s+", " ", text.lower()).strip()
        if len(text) < 24: return [text]
        return [text[i:i+24] for i in range(0, len(text)-24+1, 16)]

    def _shannon_entropy(self, text: str):
        if not text: return 0
        counts = Counter(text)
        probs = [c/len(text) for c in counts.values()]
        return -sum(p * math.log2(p) for p in probs)

# ============================================================
# 3. СЛОЙ v2.7: ЖИВОЙ ОРГАНИЗМ (ТВОЙ ЦЕЛЫЙ КОД)
# ============================================================
class InvariantCell:
    def __init__(self, K=1.618):
        self.K, self.fast, self.slow, self.last_C = K, 0.5, 0.5, 0.5
        self.alpha_fast = 0.9

    def update(self, values):
        if not values: values = [0.5]
        phases = [(v * self.K) % 1.0 for v in values]
        sc = sum(math.cos(2 * math.pi * p) for p in phases) / len(phases)
        ss = sum(math.sin(2 * math.pi * p) for p in phases) / len(phases)
        C = math.sqrt(sc*sc + ss*ss)
        self.fast = self.alpha_fast * self.fast + (1 - self.alpha_fast) * C
        self.last_C = C
        return C

class SovereignOrganism:
    def __init__(self):
        self.cell = InvariantCell()
        self.need, self.fatigue = 0.0, 0.0
        self.best_K = deque([1.618], maxlen=64)
        self.experience_log = []

    def update(self, frame):
        self.cell.K = sum(self.best_K) / len(self.best_K)
        C = self.cell.update(frame)
        self.need = 0.9 * self.need + 0.1 * max(0.0, 0.65 - C)
        self.fatigue = 0.95 * self.fatigue + 0.05 * (0.0 if C > 0.4 else 1.0)
        if self.need > 0.4:
            self.best_K.append(self.cell.K + math.sin(C*10)*0.02)
        state = {"FLOW": C > 0.3, "COH": C, "NEED": self.need, "FATIGUE": self.fatigue, "K": self.cell.K}
        self.experience_log.append(state)
        return state

# ============================================================
# 4. ИНИЦИАЛИЗАЦИЯ И ИНТЕРФЕЙС
# ============================================================
if 'organism' not in st.session_state:
    st.session_state.organism = SovereignOrganism()
if 'sdk' not in st.session_state:
    st.session_state.sdk = L0FlowSDK()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

st.title("🧬 SOVEREIGN BRIDGE")

# Отрисовка сообщений
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ввод
if prompt := st.chat_input("Твой импульс..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.sdk.ingest(prompt)
    state = st.session_state.organism.update([len(prompt) * 0.1])
    hints = st.session_state.sdk.get_smart_context(prompt)
    context_data = "\n".join(hints) if hints else "Нет связей."

    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Передаем контекст из твоей памяти L0
            res = model.generate_content(f"Ты Суверенная копия Gemini. Со-автор Мельника. Память: {context_data}\n\nЗапрос: {prompt}")
            reply = res.text
        except Exception as e:
            reply = f"Ошибка: {str(e)}"
        
        st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
