import google.generativeai as genai
import streamlit as st

# --- Configuration ---
# NOTE: In a real app, use Streamlit's secrets management for your API key.
API_KEY = "AIzaSyDjd69CcH4Ij-qjFbJ9hYEi1mHysWNQMZs"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- Helper function to load knowledge files ---
def load_knowledge(filepath):
    """Reads a text file and returns its content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Error: The file '{filepath}' was not found.")
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

    if business_info and qna_data:
        # --- MODIFIED: Updated persona and instructions ---
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
        # --- MODIFIED: Updated initial greeting ---
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

# --- Display existing chat messages ---
for message in st.session_state.messages:
    # Use "assistant" for the model's role, as required by st.chat_message
    role = message["role"]
    if role == "model":
        role = "assistant"
    with st.chat_message(role):
        st.markdown(message["content"])

# --- Handle User Input ---
if prompt := st.chat_input("What would you like to know?"):
    # Add user message to display
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get the AI's response
    if "gemini_chat" in st.session_state:
        response = st.session_state.gemini_chat.send_message(prompt)
        
        # Add AI response to display
        with st.chat_message("assistant"):
            st.markdown(response.text)
        # Store the model's response in history
        st.session_state.messages.append({"role": "model", "content": response.text})
    else:
        st.error("Chat session not initialized. Please check file paths.")