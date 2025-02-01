import streamlit as st
import base64
import json
import requests
import os
import time
import threading
import random
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from github import Github, InputFileContent
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(exist_ok=True)
VALID_USERS = {"Nana": "Kaoru", "Kaoru": "Nana"}
BUFFER_SIZE = 5
DARK_MODE = True

COLORS = {
    "background": "#0E1117" if DARK_MODE else "#FFFFFF",
    "user_message": "#2B547E" if DARK_MODE else "#89CFF0",
    "other_message": "#4A235A" if DARK_MODE else "#F8C8DC",
    "text": "#FFFFFF" if DARK_MODE else "#000000"
}

def github_connect():
    g = Github(st.secrets["GITHUB_TOKEN"])
    repo = g.get_repo(st.secrets["REPO_NAME"])
    gist = g.get_repo(st.secrets["GIST_ID"])
    return repo, gist

cipher = Fernet(st.secrets["ENCRYPTION_KEY"])

def encrypt(data):
    return cipher.encrypt(data.encode()).decode()

def decrypt(encrypted_data):
    return cipher.decrypt(encrypted_data.encode()).decode()

def store_file(file):
    encrypted = cipher.encrypt(file.read())
    file_path = f"{UPLOAD_DIR}/{datetime.now().timestamp()}_{file.name}"
    with open(file_path, "wb") as f:
        f.write(encrypted)
    return file_path

def read_file(file_path):
    with open(file_path, "rb") as f:
        return cipher.decrypt(f.read())

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

st.set_page_config(
    page_title="Secure Chat",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
    .fixed-bottom {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: {COLORS['background']};
        padding: 1rem;
        z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }}
    .input-row {{
        display: flex;
        gap: 8px;
        align-items: center;
    }}
    .text-input {{
        flex-grow: 1;
    }}
    .small-button {{
        padding: 8px 12px !important;
        min-width: auto !important;
    }}
    .auto-scroll {{
        max-height: calc(100vh - 120px);
        overflow-y: auto;
        padding-bottom: 100px;
    }}
    #scroll-anchor {{
        height: 0px;
        opacity: 0;
    }}
</style>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
""", unsafe_allow_html=True)

if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'last_saved' not in st.session_state:
    st.session_state.last_saved = 0
if 'last_auto_save' not in st.session_state:
    st.session_state.last_auto_save = 0
if 'form_counter' not in st.session_state:
    st.session_state.form_counter = 0
if 'render_counter' not in st.session_state:
    st.session_state.render_counter = 0

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

def display_messages():
    message_store = get_message_store()
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
    st.markdown('<div id="scroll-anchor"></div>', unsafe_allow_html=True)

def chat_interface():
    st_autorefresh(interval=5000, key="chat_refresh")
    st.title(f"💌 {st.session_state.user}'s Secure Chat")
    message_store = get_message_store()

    # Messages container
    with st.container():
        st.markdown('<div class="auto-scroll">', unsafe_allow_html=True)
        display_messages()
        st.markdown('</div>', unsafe_allow_html=True)

    # Auto-scroll and focus components
    components.html(f"""
    <div id="scroll-to-me"></div>
    <script>
        // Auto-scroll to bottom
        var anchor = document.getElementById("scroll-anchor");
        if (anchor) {{
            anchor.scrollIntoView({{behavior: "smooth"}});
        }}
        
        // Persistent focus on input
        var inputs = window.parent.document.querySelectorAll("input[type=text]");
        if (inputs && inputs.length > 0) {{
            // Focus on last input (should be message input)
            inputs[inputs.length - 1].focus();
            
            // Add event listener to maintain focus
            inputs[inputs.length - 1].addEventListener('blur', function() {{
                this.focus();
            }});
        }}
    </script>
    """, height=0, key=f"focus_script_{st.session_state.render_counter}")

    # Input form
    with st.markdown('<div class="fixed-bottom">', unsafe_allow_html=True):
        with st.form(key="chat_form", clear_on_submit=True):
            cols = st.columns([6, 1])
            with cols[0]:
                message = st.text_input(
                    "Message",
                    key=f"msg_input_{st.session_state.form_counter}",
                    label_visibility="collapsed",
                    placeholder="Type a message..."
                )
            with cols[1]:
                submitted = st.form_submit_button("➤", use_container_width=True)
                file = st.file_uploader(
                    "📎", 
                    type=["png","jpg","jpeg","pdf","docx","mp4"],
                    label_visibility="collapsed",
                    key=f"file_uploader_{st.session_state.form_counter}"
                )

    if submitted:
        if not message and not file:
            st.warning("Please enter a message or attach a file.")
        else:
            new_msg = {
                "sender": st.session_state.user,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "text",
                "content": message
            }
            if file:
                file_path = store_file(file)
                new_msg.update({
                    "type": file.type,
                    "content": file_path,
                    "filename": file.name
                })
            message_store.add_message(new_msg)
            if len(message_store.get_messages()) - st.session_state.last_saved >= BUFFER_SIZE:
                message_store.save_messages()
                st.session_state.last_saved = len(message_store.get_messages())
            st.session_state.form_counter += 1
            st.session_state.render_counter += 1  # Increment render counter
            st.rerun()

if not st.session_state.auth:
    login()
else:
    chat_interface()
