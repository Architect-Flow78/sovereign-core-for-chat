import hashlib
import sqlite3
import streamlit as st
import google.generativeai as genai
from collections import Counter

# 1. СТРОГО ПЕРВЫМ
st.set_page_config(page_title="Sovereign Bridge", layout="wide")

# 2. API КЛЮЧ
API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. БАЗА ДАННЫХ (L0)
def init_db():
    conn = sqlite3.connect("l0_memory.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS memory (atom_id TEXT PRIMARY KEY, content TEXT)")
    conn.commit()
    return conn

conn = init_db()

# 4. СОСТОЯНИЕ
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 5. ИНТЕРФЕЙС
st.title("🧬 SOVEREIGN BRIDGE")

# Отрисовка истории
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Поле ввода
if prompt := st.chat_input("Пиши здесь..."):
    # Показываем ввод
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Сохраняем в память
    atom_id = hashlib.md5(prompt.encode()).hexdigest()
    conn.execute("INSERT OR IGNORE INTO memory VALUES (?, ?)", (atom_id, prompt))
    conn.commit()

    # Ответ AI
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(f"Ты со-автор Мельника. Принципы: Творец/Жертва. Ответь на: {prompt}")
            reply = response.text
        except Exception as e:
            reply = f"Ошибка: {str(e)}"
        
        st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
