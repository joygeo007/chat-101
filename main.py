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
                if msg["type"] == "text":
                    st.markdown(f"""
                    <div class="message {'user-message' if msg["sender"] == st.session_state.user else 'other-message'}">
                        <strong>{msg["sender"]}</strong><br>
                        {content}
                        <div class="timestamp">
                            {msg["timestamp"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif msg["type"].startswith("image"):
                    try:
                        file_data = read_file(content)
                        st.image(file_data, caption=msg.get("filename", ""), width=300)
                    except Exception as e:
                        st.error(f"Error loading image: {str(e)}")
                elif os.path.exists(content):
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
                    st.error("File not found.")

    # Display messages
    with message_placeholder.container():
        display_messages()

    # Message input
    with st.form("chat_form", clear_on_submit=True):
        text = st.text_input("Message", key="msg_input")
        file = st.file_uploader("Attach file", type=[
            "png", "jpg", "jpeg", "pdf", "docx", "mp4"
        ], key="file_uploader")

        submitted = st.form_submit_button("Send")
        if submitted:
            text = st.session_state.msg_input
            file_data = st.session_state.file_uploader

            if not text and not file_data:
                st.warning("Please enter a message or attach a file.")
            else:
                new_msg = {
                    "sender": st.session_state.user,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "text",
                    "content": text
                }

                if file_data:
                    file_path = store_file(file_data)
                    new_msg.update({
                        "type": file_data.type,
                        "content": file_path,
                        "filename": file_data.name
                    })

                message_store.add_message(new_msg)

                # Save to GitHub if buffer size reached
                if len(message_store.get_messages()) - st.session_state.last_saved >= BUFFER_SIZE:
                    message_store.save_messages()
                    st.session_state.last_saved = len(message_store.get_messages())

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
        st.experimental_rerun()
