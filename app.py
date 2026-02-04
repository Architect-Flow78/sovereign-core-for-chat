import hashlib
import sqlite3
import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="Sovereign Bridge", layout="wide")

# 2. API КЛЮЧ
API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"
genai.configure(api_key=API_KEY)

# 3. БАЗА ДАННЫХ
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("l0_memory.db", check_same_thread=False)
    conn.execute("DROP TABLE IF EXISTS memory") # Сносим нахрен старое, чтобы не было конфликтов
    conn.execute("""CREATE TABLE memory 
        (atom_id TEXT PRIMARY KEY, content TEXT, msg_id TEXT, 
         tenant_id TEXT, timestamp DATETIME, entropy REAL)""")
    conn.commit()
    return conn

db = get_db_connection()

# 4. СОСТОЯНИЕ
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 5. ИНТЕРФЕЙС
st.title("🧬 SOVEREIGN BRIDGE v1.7 (PRO-STABLE)")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 6. ЛОГИКА
if prompt := st.chat_input("Твой импульс..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Сохранение
    atom_id = hashlib.md5(prompt.encode()).hexdigest()
    db.execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)", 
               (atom_id, prompt, "msg", "Melnik", datetime.now().isoformat(), 0.0))
    db.commit()

    # ОТВЕТ AI (ТОЛЬКО GEMINI-PRO)
    with st.chat_message("assistant"):
        try:
            # Используем САМУЮ стабильную модель в истории Google API
            model = genai.GenerativeModel('gemini-pro') 
            response = model.generate_content(prompt)
            reply = response.text
        except Exception as e:
            reply = f"Финальный сбой: {str(e)}. Мельник, если снова 404, значит Google AI Studio отклоняет твой ключ."
        
        st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
