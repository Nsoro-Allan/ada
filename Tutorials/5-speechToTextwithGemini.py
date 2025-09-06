from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder

def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

    client = genai.Client(api_key=api_key)

    print("Successfully configured Gemini with API key.")

    chat = client.chats.create(model="gemini-2.5-flash",
                               config=types.GenerateContentConfig(
                                   system_instruction="My name is Naz",
                                   thinking_config=types.ThinkingConfig(thinking_budget=0)
                               )
                              )

    recorder = AudioToTextRecorder(model="tiny.en", language="en", spinner=False)
    print("RealtimeSTT is ready. Say 'exit' or press Ctrl+C to end the chat.")

    while True:
        try:
            print("You: ", end="", flush=True)
            user_input = recorder.text()
            print(user_input)
            
            if user_input.lower().strip() == "exit" or "exit.":
                print("Ending chat. Goodbye!")
                break

            response = chat.send_message_stream(user_input)

            print("Gemini:", end="")
            for chunk in response:
                print(chunk.text, end="", flush=True)
            print()

        except KeyboardInterrupt:
            print("\nEnding chat. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break
    
    recorder.shutdown()

if __name__ == '__main__':
    main()
