import google.generativeai as genai
import streamlit as st
import os
import json # Import the json library for saving data
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key from the environment
api_key = os.getenv("GOOGLE_API_KEY")

# --- IMPORTANT: Check if API key is loaded ---
if not api_key:
    st.error("Google API Key not found. Please create a .env file in the same directory as app.py "
             "and add GOOGLE_API_KEY='YOUR_ACTUAL_API_KEY_HERE'.")
    st.stop() # Stop the app if the API key is missing

# Configure the genai library with the retrieved API key
genai.configure(api_key=api_key)

# Initialize the Generative Model
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- Helper function to load knowledge files ---
def load_knowledge(filepath):
    """Reads a text file and returns its content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found. Please ensure it's in the same directory as app.py.")
        return None

# --- Streamlit App Interface ---

st.set_page_config(page_title="Fit Guy", page_icon="💪")
st.title("💪 Fit Guy: Your UrbanFit Assistant")
st.caption("Ask me anything about UrbanFit!")

# --- Initialize Chat in Streamlit's Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Load knowledge base and start chat on first run ---
if "gemini_chat" not in st.session_state:
    business_info = load_knowledge('business_info.txt')
    qna_data = load_knowledge('qna.txt')

    if business_info is not None and qna_data is not None:
        system_instructions = f"""
        You are a friendly and helpful customer service chatbot for UrbanFit. Your name is Fit Guy.
        First, look for an answer in the EXAMPLE QUESTIONS AND ANSWERS. If you can't find it there, use the GENERAL BUSINESS INFORMATION.
        If the answer isn't in either, politely say you don't have that information.
        Keep your answers clear and concise, with a confident and encouraging tone suitable for a fitness brand.

        EXAMPLE QUESTIONS AND ANSWERS:
        {qna_data}

        GENERAL BUSINESS INFORMATION:
        {business_info}
        """
        st.session_state.gemini_chat = model.start_chat(history=[
            {
                "role": "user",
                "parts": [system_instructions]
            },
            {
                "role": "model",
                "parts": ["Hello! I'm Fit Guy, the virtual assistant for UrbanFit. How can I help you get geared up today?"]
            }
        ])
    else:
        st.session_state.gemini_chat = None

# --- Display existing chat messages ---
for message in st.session_state.messages:
    role = message["role"]
    if role == "model":
        role = "assistant"
    with st.chat_message(role):
        st.markdown(message["content"])

# --- Handle User Input ---
if prompt := st.chat_input("What would you like to know?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if "gemini_chat" in st.session_state and st.session_state.gemini_chat is not None:
        try:
            response = st.session_state.gemini_chat.send_message(prompt)
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "model", "content": response.text})
        except Exception as e:
            st.error(f"An error occurred while getting a response from Fit Guy: {e}")
            st.session_state.messages.append({"role": "model", "content": "I apologize, I encountered an error. Could you please try asking again?"})
    else:
        st.error("Chat session not initialized. Please check file paths and API key.")

# --- Export Chat History Button ---
st.sidebar.title("Chat Tools")
if st.sidebar.button("Export Chat History"):
    if st.session_state.messages:
        # Prepare messages for export (Gemini history format is slightly different)
        export_messages = []
        for msg in st.session_state.messages:
            # Ensure 'parts' is a list of dictionaries with 'text' key
            # This is how Gemini API expects history, and it's good for consistency
            export_messages.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        # Define the path for the JSON file
        output_filepath = "chat_history.json"
        
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(export_messages, f, indent=4)
            st.sidebar.success(f"Chat history exported to {output_filepath}")
        except Exception as e:
            st.sidebar.error(f"Failed to export chat history: {e}")
    else:
        st.sidebar.warning("No messages to export yet!")

