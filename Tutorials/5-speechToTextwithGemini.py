from google import genai 
from google.genai import types
import os
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder
def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    client = genai.Client(api_key=api_key)

    print("API KEY IS FINEEEEE")

    chat= client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="MY NAME IS NAZ",
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        ),
    )

    recorder = AudioToTextRecorder(model="tiny.en", language="en", spinner=False)

    while True:
        print("You: ", end="", flush=True)
        user_input = recorder.text()
        print(user_input)
        if user_input.lower() == "exit":
            break

        response = chat.send_message_stream(user_input)
        for chunk in response:
            print(chunk.text, end="", flush=True)
        print()

if __name__ == '__main__':
    main()
