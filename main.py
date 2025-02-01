        # Generate unique keys using a counter
        if 'form_counter' not in st.session_state:
            st.session_state.form_counter = 0
            
        text_input_key = f"msg_input_{st.session_state.form_counter}"
        file_uploader_key = f"file_uploader_{st.session_state.form_counter}"

        text = st.text_input("Message", key=text_input_key)
        file = st.file_uploader("Attach file", type=[
            "png", "jpg", "jpeg", "pdf", "docx", "mp4"
        ], key=file_uploader_key)

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

                # Force UI refresh by incrementing form counter
                st.session_state.form_counter += 1
                st.rerun()

    # Auto-save every 2 minutes
    if time.time() - st.session_state.last_auto_save > 120:
        message_store.save_messages()
        st.session_state.last_auto_save = time.time()

    # Logout Button
    if st.button("Logout"):
        message_store.save_messages()
        st.session_state.auth = False
        st.experimental_rerun()

# Main App
if not st.session_state.auth:
    login()
else:
    chat_interface()
