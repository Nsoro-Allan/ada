import asyncio
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from a .env file
load_dotenv()

# Get API keys from environment variables
gemini_api_key = os.getenv("GEMINI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY") # This is in the original code but not used, kept for consistency

# Validate that the API keys are set
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY not found. Please set it in your .env file.")

# Configure the Gemini client
client = genai.Client(api_key=gemini_api_key)
model = "gemini-live-2.5-flash-preview"  # Note: The model name might need updating based on availability
config = {"response_modalities": ["TEXT"]}

async def main():
    """
    Main function to run a continuous chat session with the Gemini API.
    """
    print("Connecting to Gemini Live... Type 'quit' or 'exit' to end the chat.")
    try:
        # Establish a persistent connection to the live model
        async with client.aio.live.connect(model=model, config=config) as session:
            print("Connection successful! You can start chatting.")
            
            # Start a continuous loop for the chat conversation
            while True:
                # Prompt the user for input
                message = input("You: ")

                # Check if the user wants to end the chat
                if message.lower() in ["quit", "exit"]:
                    print("\nEnding chat session. Goodbye! 👋")
                    break

                # Send the user's message to the API
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True
                )
                
                print("Gemini: ", end="", flush=True)
                
                # Asynchronously receive and print the streaming response
                async for response in session.receive():
                    if response.text is not None:
                        print(response.text, end="")
                
                # Add a newline after the complete response for better formatting
                print()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())