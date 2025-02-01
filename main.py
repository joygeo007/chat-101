import streamlit as st
import base64
import json
import requests
import os
import time
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from github import Github, InputFileContent

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

# GitHub Data Management
def get_messages():
    try:
        repo, gist = github_connect()
        content = gist.files["chat_history.json"].content
        return json.loads(decrypt(content))
    except:
        return []

def save_messages(messages):
    try:
        repo, gist = github_connect()
        encrypted = encrypt(json.dumps(messages))
        gist.edit(files={"chat_history.json": InputFileContent(encrypted)})
    except Exception as e:
        st.error(f"Error saving messages: {str(e)}")

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
if 'messages' not in st.session_state:
    st.session_state.messages = get_messages()
if 'last_saved' not in st.session_state:
    st.session_state.last_saved = 0

# Authentication
def login():
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if VALID_USERS.get(user) == pwd:
                st.session_state.auth = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")

# Chat Interface
def chat_interface():
    st.title(f"💌 {st.session_state.user}'s Secure Chat")
    
    # Display messages from session state
    for msg in st.session_state.messages:
        col = st.columns([1, 20])[1]
        with col:
            content = msg["content"]
            if msg["type"].startswith("image"):
                try:
                    file_data = read_file(content)
                    st.image(file_data, caption=msg.get("filename", ""), width=300)
                except Exception as e:
                    st.error(f"Error loading image: {str(e)}")
            elif msg["type"] != "text":
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

    # Message input
    with st.form("chat", clear_on_submit=True):
        text = st.text_input("Message", key="msg")
        file = st.file_uploader("Attach file", type=[
            "png", "jpg", "jpeg", "pdf", "docx", "mp4"
        ])
        
        if st.form_submit_button("Send"):
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
            
            st.session_state.messages.append(new_msg)
            
            # Save to GitHub if buffer size reached
            if len(st.session_state.messages) - st.session_state.last_saved >= BUFFER_SIZE:
                save_messages(st.session_state.messages)
                st.session_state.last_saved = len(st.session_state.messages)
            
            st.rerun()

    # Auto-save every 2 minutes
    if time.time() - st.session_state.get("last_auto_save", 0) > 120:
        save_messages(st.session_state.messages)
        st.session_state.last_auto_save = time.time()
        st.rerun()

    if st.button("Logout"):
        save_messages(st.session_state.messages)
        st.session_state.auth = False
        st.rerun()

    # Auto-refresh every 5 seconds
    st.experimental_rerun()

# Main App
if not st.session_state.auth:
    login()
else:
    chat_interface()
