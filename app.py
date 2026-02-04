import hashlib
import sqlite3
import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="Sovereign Bridge", layout="wide")

# 2. API КЛЮЧ И ФИКС 404 (Явно указываем v1)
API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"

# Хак для обхода ошибки 404 и версии v1beta
genai.configure(api_key=API_KEY, transport='rest') # Используем REST транспорт для стабильности

# 3. БАЗА ДАННЫХ
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("l0_memory.db", check_same_thread=False)
    # Если база кривая — сносим и создаем заново, чтобы не было ошибок по колонкам
    try:
        conn.execute("SELECT atom_id, content, msg_id, tenant_id, timestamp, entropy FROM memory LIMIT 1")
    except:
        conn.execute("DROP TABLE IF EXISTS memory")
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
st.title("🧬 SOVEREIGN BRIDGE v1.6")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 6. ЛОГИКА
if prompt := st.chat_input("Твой импульс..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Сохранение
    try:
        atom_id = hashlib.md5(prompt.encode()).hexdigest()
        ts = datetime.now().isoformat()
        db.execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)", 
                   (atom_id, prompt, "msg", "Melnik", ts, 0.0))
        db.commit()
    except Exception as e:
        st.error(f"Ошибка памяти: {e}")

    # ОТВЕТ AI
    with st.chat_message("assistant"):
        try:
            # Используем gemini-pro если flash не отвечает (для подстраховки)
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(f"Ты со-автор Мельника. Ответь: {prompt}")
            except:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(f"Ты со-автор Мельника. Ответь: {prompt}")
            
            reply = response.text
        except Exception as e:
            reply = f"Ярость системы: {str(e)}. Мельник, попробуй еще раз через минуту или проверь ключ."
        
        st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
