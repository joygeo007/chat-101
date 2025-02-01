import streamlit as st
import base64
import json
import requests
import os
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from github import Github, InputFileContent

# Configuration
UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(exist_ok=True)
VALID_USERS = {"Nana": "Kaoru", "Kaoru": "Nana"}

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
    # Encrypt and store locally (for demo)
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
    repo, gist = github_connect()
    content = gist.files["chat_history.json"].content
    return json.loads(decrypt(content))

def save_messages(messages):
    try:
        repo, gist = github_connect()
        encrypted = encrypt(json.dumps(messages))
        
        # Create proper InputFileContent objects
        gist_file = gist.files.get("chat_history.json")
        if gist_file:
            new_content = InputFileContent(encrypted)
            gist.edit(files={"chat_history.json": new_content})
        else:
            # If file doesn't exist yet, create it
            gist.edit(files={"chat_history.json": InputFileContent(encrypted)})
            
    except Exception as e:
        st.error(f"Error saving messages: {str(e)}")
        raise e
        
# UI Setup
st.set_page_config(
    page_title="Secure Chat",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Authentication
if 'auth' not in st.session_state:
    st.session_state.auth = False

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
    
    # Load messages
    try:
        messages = get_messages()
    except:
        messages = []
    
    # Display messages
    for msg in messages:
        col = st.columns([1, 20])[1]
        with col:
            if msg["type"] == "text":
                st.markdown(f"""
                <div style='background: {"#ffd1dc" if msg["sender"] == st.session_state.user else "#cbe5ff"};
                            padding: 1rem;
                            border-radius: 1rem;
                            margin: 0.5rem 0;'>
                    <strong>{msg["sender"]}</strong><br>
                    {msg["content"]}
                    <div style='font-size:0.8rem;color:#666;'>
                        {msg["timestamp"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                try:
                    file_data = read_file(msg["content"])
                    st.download_button(
                        label=f"📎 {msg['filename']}",
                        data=file_data,
                        file_name=msg["filename"],
                        mime=msg["type"]
                    )
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")

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
            
            messages.append(new_msg)
            save_messages(messages)
            st.rerun()

    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# Main App
if not st.session_state.auth:
    login()
else:
    chat_interface()

# Auto-refresh every 5 seconds
st.markdown("""
<script>
setTimeout(function(){
    window.location.reload();
}, 5000);
</script>
""", unsafe_allow_html=True)
