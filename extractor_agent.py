import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
import gspread # Import the gspread library for Google Sheets interaction

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Define the name of your Google Sheet
GOOGLE_SHEET_NAME = "Chatbot Extracted Data" # <--- IMPORTANT: Change this to your actual Google Sheet name

# Define the path for credentials.json and the token.json
# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
# gspread will save its token here. We'll put it in a .gspread folder within your script's directory.
TOKEN_FILE_PATH = os.path.join(SCRIPT_DIR, ".gspread", "token.json")


# Ensure API key is available
if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file. Please set it.")
    exit("Exiting due to missing API key.")

# Configure the Generative AI model
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Define the path to your chat history file
CHAT_HISTORY_FILE = "chat_history.json"

# --- Function to load chat history ---
def load_chat_history(filepath):
    """Loads chat history from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Chat history file '{filepath}' not found. "
              "Please run your Streamlit app and export the chat history first.")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from '{filepath}': {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading '{filepath}': {e}")
        return None

# --- Function to extract information using Gemini API ---
def extract_information(conversation_text):
    """
    Uses the Gemini API to extract structured information from a conversation.
    """
    # Define the JSON schema for the desired output
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "customerName": {"type": "STRING", "description": "Full name of the customer, if mentioned. Infer from context if only first name is given."},
            "customerEmail": {"type": "STRING", "description": "Email address of the customer, if mentioned."},
            "customerPhone": {"type": "STRING", "description": "Phone number of the customer, if mentioned."},
            "orderId": {"type": "STRING", "description": "The order identification number, if mentioned, e.g., #XYZ123, 575."},
            "issuePriority": {"type": "STRING", "enum": ["Low", "Medium", "High", "Urgent", "Not Specified"], "description": "Priority level of the issue, inferred from urgency cues like 'urgently', 'next week', 'non urgent basis'."},
            "problemDescription": {"type": "STRING", "description": "Detailed description of the customer's problem or complaint, including product details (e.g., 'red t-shirt came blue')."},
            "solutionProvided": {"type": "STRING", "description": "Description of the solution or next steps proposed by the chatbot/agent."},
            "otherImportantDetails": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Any other critical or relevant information not covered by the above fields, such as specific product attributes (size, color, type), unusual requests, or additional context important for resolution."
            }
        },
        "required": ["problemDescription"] # Problem description is a mandatory field
    }

    # Craft the prompt for the Gemini model
    prompt = f"""
    You are an expert Information Extractor Agent. Your task is to analyze the following customer service conversation transcript
    and extract specific details into a structured JSON format. Pay close attention to context and infer
    information where necessary (e.g., priority from urgency cues, or full name if only first name is used consistently).

    Extract the following fields. If a field is not explicitly mentioned or cannot be inferred, omit it from the JSON.
    For 'otherImportantDetails', capture any crucial information that doesn't fit other categories.

    Conversation Transcript:
    ---
    {conversation_text}
    ---
    """

    try:
        # Prepare the payload for the Gemini API call
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        
        # Make the API call with the defined schema for structured output
        response = model.generate_content(
            contents=contents,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )

        # Parse the JSON response
        extracted_data = json.loads(response.text)
        return extracted_data

    except Exception as e:
        print(f"An error occurred during Gemini API extraction: {e}")
        print(f"Raw Gemini response (if available): {response.text if 'response' in locals() else 'N/A'}")
        return None

# --- Function to write to Google Sheet ---
def write_to_google_sheet(data_to_write):
    """
    Authenticates with Google Sheets using OAuth and writes extracted data to the specified sheet.
    """
    try:
        # Authenticate using OAuth, explicitly providing the path to credentials.json
        # and where to save/load the token.json
        print("Attempting gspread OAuth authentication...")
        # Ensure the directory for token.json exists
        token_dir = os.path.dirname(TOKEN_FILE_PATH)
        if not os.path.exists(token_dir):
            os.makedirs(token_dir)
            print(f"Created directory for gspread token: {token_dir}")

        gc = gspread.oauth(
            credentials_filename=CREDENTIALS_FILE_PATH,
            authorized_user_filename=TOKEN_FILE_PATH
        )
        print("gspread authentication successful.")
        
        # Open the spreadsheet by its name
        spreadsheet = gc.open(GOOGLE_SHEET_NAME)
        print(f"Successfully opened Google Sheet: '{GOOGLE_SHEET_NAME}'.")
        
        # Select the first worksheet
        worksheet = spreadsheet.sheet1
        
        # Define headers based on your response_schema properties
        headers = [
            "customerName", "customerEmail", "customerPhone", "orderId",
            "issuePriority", "problemDescription", "solutionProvided",
            "otherImportantDetails"
        ]

        # Check if the header row is empty and write headers if needed
        if not worksheet.row_values(1): # Check if the first row is empty
            worksheet.append_row(headers)
            print("Headers added to Google Sheet.")

        # Prepare the row data based on the extracted_info dictionary
        row_values = []
        for header in headers:
            value = data_to_write.get(header, "") # Get value, default to empty string if not present
            if isinstance(value, list):
                row_values.append(", ".join(value)) # Join list items with a comma
            else:
                row_values.append(str(value)) # Convert all values to string

        # Append the row to the worksheet
        worksheet.append_row(row_values)
        print(f"Successfully wrote data to Google Sheet '{GOOGLE_SHEET_NAME}'.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Google Sheet '{GOOGLE_SHEET_NAME}' not found. Please ensure the name is correct and it's shared with the Google account you authorized with.")
        exit("Exiting due to Spreadsheet not found.") # Exit on critical error
    except Exception as e:
        print(f"An error occurred while writing to Google Sheet: {e}")
        print(f"Please ensure 'credentials.json' is in the script's directory and you have authorized gspread in your browser.")
        exit("Exiting due to Google Sheet write error.") # Exit on critical error


# --- Main execution logic ---
if __name__ == "__main__":
    # Check if credentials.json exists in the script's directory
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        print(f"Error: 'credentials.json' not found at '{CREDENTIALS_FILE_PATH}'.")
        print("Please ensure you have downloaded and placed 'credentials.json' in the same directory as this script.")
        exit("Exiting due to missing credentials.json.")
    
    print(f"Attempting to load chat history from: {CHAT_HISTORY_FILE}")
    chat_messages = load_chat_history(CHAT_HISTORY_FILE)

    if chat_messages:
        # Combine messages into a single conversation string for extraction
        conversation_for_extraction = ""
        
        # Find the first actual user message to start the relevant conversation
        start_index = 0
        for i, msg in enumerate(chat_messages):
            if msg["role"] == "user" and "parts" in msg and msg["parts"] and "text" in msg["parts"][0]:
                # Crude check to skip initial system prompt, assuming it contains "system_instructions"
                if "system_instructions" not in msg["parts"][0]["text"]: 
                    start_index = i
                    break
        
        # Reconstruct conversation from the first actual interaction
        for i in range(start_index, len(chat_messages)):
            msg = chat_messages[i]
            role = "User" if msg["role"] == "user" else "Assistant"
            if "parts" in msg and msg["parts"] and "text" in msg["parts"][0]:
                conversation_for_extraction += f"{role}: {msg['parts'][0]['text']}\n"

        print("\n--- Full Conversation for Extraction ---")
        print(conversation_for_extraction)
        print("--------------------------------------\n")

        print("Attempting to extract information using Gemini...")
        extracted_info = extract_information(conversation_for_extraction)

        if extracted_info:
            print("\n--- Extracted Information (JSON) ---")
            print(json.dumps(extracted_info, indent=4))
            print("------------------------------------\n")

            print("Attempting to write extracted information to Google Sheet...")
            write_to_google_sheet(extracted_info)
            
        else:
            print("No information extracted or an error occurred during extraction.")
    else:
        print("Could not proceed with extraction as chat history was not loaded.")

