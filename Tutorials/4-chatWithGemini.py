from google import genai              # Imports the main Gemini AI library
from google.genai import types        # Imports data types for configuring requests
import os                             # Imports the 'os' module for system interactions
from dotenv import load_dotenv        # Imports a function to load environment variables from a .env file

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variables
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)  # Creates a client instance for the Gemini API

# Check if the key was loaded successfully
if not api_key:                
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

print("Successfully configured Gemini with API key.")

chat = client.chats.create(model="gemini-2.5-flash",
                           config=types.GenerateContentConfig(
                               system_instruction="My name is Naz", 
                               thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables the model's "thinking" process for faster results
                            )
                        )

# Start an infinite loop to allow for continuous conversation.
while True:
    try:
        user_input = input("You: ")
        
        if user_input.lower() == "exit":
            print("Ending chat. Goodbye!")
            break

        # Send the user's input to the model and enable streaming.
        response = chat.send_message_stream(user_input)

        print("Gemini:", end="")
        for chunk in response:
            print(chunk.text, end="", flush=True)
        print() # Print a newline after the full response is received.

    except Exception as e:
        # Catch any exceptions and print an error message.
        print(f"An error occurred: {e}")