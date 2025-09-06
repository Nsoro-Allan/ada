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

response = client.models.generate_content_stream(
    model="gemini-2.5-flash",         # Specifies the model to use
    contents="Tell me a short story where I am the main charactere",       # The user's input for the model
    config=types.GenerateContentConfig(
        system_instruction="My name is Naz", 
        thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables the model's "thinking" process for faster results
    ),
)


for chunk in response:
    print(chunk.text, end="")                  # Prints the generated text from the model's response