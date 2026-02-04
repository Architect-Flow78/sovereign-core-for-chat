import hashlib
import sqlite3
import streamlit as st
import google.generativeai as genai

# 1. КОНФИГУРАЦИЯ (Всегда первая строка)
st.set_page_config(page_title="Sovereign Bridge", layout="wide")

# 2. API КЛЮЧ
API_KEY = "AIzaSyCX69CN_OSfdjT-WlPeF3-g50Y4d3NMDdc"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. БАЗА ДАННЫХ (С кэшированием, чтобы не было OperationalError)
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("l0_memory.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS memory (atom_id TEXT PRIMARY KEY, content TEXT)")
    conn.commit()
    return conn

db = get_db_connection()

# 4. СОСТОЯНИЕ ЧАТА
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 5. ИНТЕРФЕЙС
st.title("🧬 SOVEREIGN BRIDGE")

# Отрисовка истории из памяти сессии
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Поле ввода
if prompt := st.chat_input("Твой импульс..."):
    # Добавляем в интерфейс сразу
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 6. СОХРАНЕНИЕ В L0 (Вечная память)
    try:
        atom_id = hashlib.md5(prompt.encode()).hexdigest()
        db.execute("INSERT OR IGNORE INTO memory VALUES (?, ?)", (atom_id, prompt))
        db.commit()
    except Exception as e:
        st.error(f"Ошибка памяти: {e}")

    # 7. ОТВЕТ AI
    with st.chat_message("assistant"):
        try:
            # Подтягиваем контекст (последние 3 записи из базы для "узнавания")
            cursor = db.execute("SELECT content FROM memory ORDER BY ROWID DESC LIMIT 3")
            history_context = " ".join([row[0] for row in cursor.fetchall()])
            
            sys_msg = f"Ты со-автор Мельника. Принципы: Творец/Жертва. Твоя память: {history_context}"
            response = model.generate_content(f"{sys_msg}\n\nЗапрос: {prompt}")
            reply = response.text
        except Exception as e:
            reply = f"Ошибка генерации: {str(e)}"
        
        st.write(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
