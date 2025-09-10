import os
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder

from google import genai
from google.genai import types

from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

def main():
    """
    The main function that runs the voice chat application.
    """
    # Load environment variables from a .env file
    load_dotenv()

    # --- API Key Configuration ---
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
    if not elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not found. Please set it in your .env file.")

    # --- Client Initialization ---
    try:
        # Initialize the Gemini client
        client = genai.Client(api_key=gemini_api_key)
        
        # Initialize the ElevenLabs client
        # The client automatically uses the ELEVENLABS_API_KEY environment variable
        elevenlabs = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        )
        print("Successfully configured Gemini and ElevenLabs.")
    except Exception as e:
        print(f"Error configuring API clients: {e}")
        return

    # --- Gemini Chat Session Setup ---
    chat = client.chats.create(model="gemini-2.5-flash",
                                     config=types.GenerateContentConfig(
                                         system_instruction="My name is Naz",
                                         thinking_config=types.ThinkingConfig(thinking_budget=0)
                                     )
                                    )

    # --- Real-time Speech-to-Text Setup ---
    recorder = AudioToTextRecorder(model="tiny.en", language="en", spinner=False)
    print("RealtimeSTT is ready. Say 'exit' or press Ctrl+C to end the chat.")

    # --- Main Chat Loop ---
    while True:
        try:
            # Get user input from the microphone
            print("You: ", end="", flush=True)
            user_input = recorder.text()
            print(user_input)
            
            # Check for exit condition
            if user_input.lower().strip() in ("exit", "exit."):
                print("Ending chat. Goodbye!")
                break

            # Send user input to Gemini and get a streaming response
            response_stream = chat.send_message_stream(user_input)

            print("Gemini:", end="", flush=True)
            
            # Use a list to collect text chunks for the full response
            full_response_chunks = []
            for chunk in response_stream:
                # Print the text as it comes in for a real-time feel
                print(chunk.text, end="", flush=True)
                full_response_chunks.append(chunk.text)
            
            print() # Add a newline after Gemini's text response

            # --- Text-to-Speech with ElevenLabs ---
            # Join the collected chunks to form the complete response text
            full_response_text = "".join(full_response_chunks).strip()

            if full_response_text:
                audio = elevenlabs.text_to_speech.convert(
                    text=full_response_text,
                    voice_id="pFZP5JQG7iQjIQuC4Bku",
                    model_id="eleven_flash_v2_5",
                    output_format="mp3_44100_128",
                )
                
                play(audio)

        except KeyboardInterrupt:
            print("\nEnding chat. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break
    
    # Cleanly shut down the recorder
    recorder.shutdown()

if __name__ == '__main__':
    main()
