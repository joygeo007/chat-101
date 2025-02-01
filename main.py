import streamlit as st
import base64
import json
import requests
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from github import Github, InputFileContent
from streamlit_autorefresh import st_autorefresh

# Configuration
UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(exist_ok=True)
VALID_USERS = {"Nana": "Kaoru", "Kaoru": "Nana"}
BUFFER_SIZE = 5  # Save to GitHub after 5 messages
DARK_MODE = True  # Set to False for light mode

# Color Scheme
COLORS = {
    "background": "#0E1117" if DARK_MODE else "#FFFFFF",
    "user_message": "#2B547E" if DARK_MODE else "#89CFF0",
    "other_message": "#4A235A" if DARK_MODE else "#F8C8DC",
    "text": "#FFFFFF" if DARK_MODE else "#000000"
}

# Initialize GitHub
def github_connect():
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(st.secrets["REPO_NAME"])
    gist = g.get_gist(st.secrets["GIST_ID"])
    return repo, gist

# Encryption
cipher = Fernet(st.secrets["ENCRYPTION_KEY"])

def encrypt(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt(encrypted_data):
    return cipher.decrypt(encrypted_data.encode()).decode()

# File Handling
def store_file(file):
    encrypted = cipher.encrypt(file.read())
    file_path = f"{UPLOAD_DIR}/{datetime.now().timestamp()}_{file.name}"
    
    with open(file_path, "wb") as f:
        f.write(encrypted)
    
    return file_path

def read_file(file_path):
    with open(file_path, "rb") as f:
        return cipher.decrypt(f.read())

# Message Store with Thread Safety
class MessageStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.messages = self.load_messages()

    def load_messages(self):
        try:
            repo, gist = github_connect()
            content = gist.files["chat_history.json"].content
            return json.loads(decrypt(content))
        except:
            return []

    def add_message(self, msg):
        with self.lock:
            self.messages.append(msg)

    def get_messages(self):
        with self.lock:
            return self.messages.copy()

    def save_messages(self):
        try:
            repo, gist = github_connect()
            encrypted = encrypt(json.dumps(self.messages))
            gist.edit(files={"chat_history.json": InputFileContent(encrypted)})
        except Exception as e:
            st.error(f"Error saving messages: {str(e)}")

@st.cache_resource
def get_message_store():
    return MessageStore()

# UI Setup
st.set_page_config(
    page_title="Secure Chat",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown(f"""
<style>
    body {{ background-color: {COLORS['background']}; }}
    .message {{
        padding: 1rem;
        border-radius: 15px;
        margin: 10px 0;
        max-width: 70%;
        color: {COLORS['text']};
        word-break: break-word;
    }}
    .user-message {{ 
        background-color: {COLORS['user_message']};
        margin-left: auto;
    }}
    .other-message {{
        background-color: {COLORS['other_message']};
        margin-right: auto;
    }}
    .timestamp {{
        font-size: 0.8rem;
        opacity: 0.7;
        margin-top: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# Session State Management
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'last_saved' not in st.session_state:
    st.session_state.last_saved = 0
if 'last_auto_save' not in st.session_state:
    st.session_state.last_auto_save = 0

# Authentication
def login():
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if VALID_USERS.get(user) == pwd:
                st.session_state.auth = True
                st.session_state.user = user
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# Chat Interface
def chat_interface():
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=5 * 1000, key="chat_refresh")

    st.title(f"💌 {st.session_state.user}'s Secure Chat")

    message_store = get_message_store()

    # Create a placeholder for messages
    message_placeholder = st.empty()

    # Function to display messages
    def display_messages():
        messages = message_store.get_messages()
        for msg in messages:
            col = st.columns([1, 20])[1]
            with col:
                content = msg["content"]
                if msg["type"].startswith("image"):
                    try:
                        file_data = read_file(content)
                        st.image(file_data, caption=msg.get("filename", ""), width=300)
                    except Exception as e:
                        st.error(f"Error loading image: {str(e)}")
                elif msg["type"] != "text" and os.path.exists(content):
                    try:
                        file_data = read_file(content)
                        st.download_button(
                            label=f"📎 {msg['filename']}",
                            data=file_data,
                            file_name=msg["filename"],
                            mime=msg["type"]
                        )
                    except Exception as e:
                        st.error(f"Error loading file: {str(e)}")
                else:
                    st.markdown(f"""
                    <div class="message {'user-message' if msg["sender"] == st.session_state.user else 'other-message'}">
                        <strong>{msg["sender"]}</strong><br>
                        {content}
                        <div class="timestamp">
                            {msg["timestamp"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # Display messages
    with message_placeholder.container():
        display_messages()

    # Message input
    with st.form("chat_form"):
        text_input_key = "msg_input"
        if text_input_key not in st.session_state:
            st.session_state[text_input_key] = ''
        text = st.text_input("Message", key=text_input_key)
        file = st.file_uploader("Attach file", type=[
            "png", "jpg", "jpeg", "pdf", "docx", "mp4"
        ], key='file_uploader')

        submitted = st.form_submit_button("Send")
        if submitted:
            if not text and not file:
                st.warning("Please enter a message or attach a file.")
            else:
                new_msg = {
                    "sender": st.session_state.user,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "text",
                    "content": text
                }

                if file:
                    file_path = store_file(file)
                    new_msg.update({
                        "type": file.type,
                        "content": file_path,
                        "filename": file.name
                    })

                message_store.add_message(new_msg)

                # Save to GitHub if buffer size reached
                if len(message_store.get_messages()) - st.session_state.last_saved >= BUFFER_SIZE:
                    message_store.save_messages()
                    st.session_state.last_saved = len(message_store.get_messages())

                # Clear the text input and file uploader
                st.session_state[text_input_key] = ''
                st.session_state['file_uploader'] = None

                # Update message display
                with message_placeholder.container():
                    display_messages()

    # Auto-save every 2 minutes
    if time.time() - st.session_state.last_auto_save > 120:
        message_store.save_messages()
        st.session_state.last_auto_save = time.time()

    # Logout Button
    if st.button("Logout"):
        message_store.save_messages()
        st.session_state.auth = False
        st.rerun()

# Main App
if not st.session_state.auth:
    login()
else:
    chat_interface()
