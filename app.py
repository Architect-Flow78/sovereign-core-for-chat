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

# 3. БАЗА ДАННЫХ (Поддержка 6 колонок)
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("l0_memory.db", check_same_thread=False)
    # Создаем таблицу, если её нет (с запасом на 6 колонок)
    conn.execute("""CREATE TABLE IF NOT EXISTS memory 
        (atom_id TEXT PRIMARY KEY, content TEXT, msg_id TEXT, 
         tenant_id TEXT, timestamp DATETIME, entropy REAL)""")
    conn.commit()
    return conn

db = get_db_connection()

# 4. СОСТОЯНИЕ
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 5. ИНТЕРФЕЙС
st.title("🧬 SOVEREIGN BRIDGE")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 6. ЛОГИКА
if prompt := st.chat_input("Твой импульс..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Сохранение (строго 6 колонок, чтобы база не ругалась)
    try:
        atom_id = hashlib.md5(prompt.encode()).hexdigest()
        ts = datetime.now().isoformat()
        db.execute("INSERT OR IGNORE INTO memory VALUES (?, ?, ?, ?, ?, ?)", 
                   (atom_id, prompt, "msg", "Melnik", ts, 0.0))
        db.commit()
    except Exception as e:
        st.error(f"Ошибка памяти: {e}")

    # Ответ AI (Используем только стабильное имя)
    with st.chat_message("assistant"):
        try:
            # Инициализируем модель прямо здесь для обхода 404
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Берем контекст
            cursor = db.execute("SELECT content FROM memory ORDER BY ROWID DESC LIMIT 5")
            context = " ".join([row[0] for row in cursor.fetchall()])
            
            full_prompt = f"Ты со-автор Мельника. Принципы: Творец/Жертва. Твоя память: {context}\n\nЗапрос: {prompt}"
            response = model.generate_content(full_prompt)
            reply = response.text
        except Exception as e:
            reply = f"Система настраивается. Ошибка: {str(e)}"
        
        st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
