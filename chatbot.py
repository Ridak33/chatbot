import google.generativeai as genai

# Get your key from https://aistudio.google.com/app/apikey
API_KEY = "AIzaSyDjd69CcH4Ij-qjFbJ9hYEi1mHysWNQMZs"

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- Load Knowledge Files ---
with open('business_info.txt', 'r', encoding='utf-8') as f:
    business_information = f.read()

with open('qna.txt', 'r', encoding='utf-8') as f:
    qna_data = f.read()

# --- Define Persona and Rules ---
# We'll combine all context into one variable for simplicity
system_instructions = f"""
You are a friendly and helpful customer service chatbot for The The UrbanFit. Your name is Fit Guy.
First, look for an answer in the EXAMPLE QUESTIONS AND ANSWERS. If you can't find it there, use the GENERAL BUSINESS INFORMATION.
If the answer isn't in either, politely say you don't have that information.
Keep your answers clear and concise.

EXAMPLE QUESTIONS AND ANSWERS:
{qna_data}

GENERAL BUSINESS INFORMATION:
{business_information}
"""

# --- NEW: Start a Chat Session ---
# This creates a chat object that will store the conversation history.
# We pass the initial system instructions to the history.
chat = model.start_chat(history=[
    {
        "role": "user",
        "parts": [system_instructions]
    },
    {
        "role": "model",
        "parts": ["Hello! I'm Fit Guy, the virtual assistant for The The UrbanFit. How can I help you today?"]
    }
])


# --- The Main Loop ---
# We print the initial greeting from the model.
print("💪 Fit Guy: Hello! I'm Fit Guy, the virtual assistant for `The The UrbanFit`. How can I help you today?")

while True:
    user_question = input("You: ")

    if user_question.lower() == 'quit':
        print("Goodbye! Have a great day!")
        break

    # --- NEW: Send message to the ongoing chat ---
    # The chat object automatically remembers the previous turns.
    response = chat.send_message(user_question)

    # Print the AI's answer
    print(f"CanvasBot: {response.text}")