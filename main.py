def chat_interface():
    st.title(f"💌 {st.session_state.user}'s Secure Chat")

    # Create a placeholder for messages
    message_placeholder = st.empty()

    # Function to display messages
    def display_messages():
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

            # Update message display
            with message_placeholder.container():
                display_messages()

    # Add a Refresh button
    if st.button("Refresh"):
        st.session_state.messages = get_messages()
        with message_placeholder.container():
            display_messages()

    # Auto-save every 2 minutes
    if time.time() - st.session_state.get("last_auto_save", 0) > 120:
        save_messages(st.session_state.messages)
        st.session_state.last_auto_save = time.time()

    if st.button("Logout"):
        save_messages(st.session_state.messages)
        st.session_state.auth = False
        st.experimental_rerun()
