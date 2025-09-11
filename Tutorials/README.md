Ada AI Tutorials Guide
======================

This document provides a step-by-step guide to setting up and running the various tutorials for the Ada AI assistant, which demonstrates different functionalities of the Gemini API.

### 1\. Prerequisites & Setup

Before you begin, you'll need to set up your Python environment and obtain the necessary API keys.

#### Step 1: Install Python and Create a Virtual Environment

It's highly recommended to use a virtual environment to manage your project's dependencies cleanly.

```
# Create a new virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

```

#### Step 2: Obtain API Keys

You'll need API keys for both the Gemini API and the ElevenLabs API.

-   **Gemini API:** Get your key from the [Google AI Studio](https://aistudio.google.com/app/apikey "null").

-   **ElevenLabs API:** Get your key from the [ElevenLabs website](https://elevenlabs.io/ "null").

#### Step 3: Create the .env File

The tutorial scripts use a `.env` file to securely store your API keys. Create a file named `.env` in the root directory of your project and add the following lines, replacing the placeholders with your actual keys.

```
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
ELEVENLABS_API_KEY="YOUR_ELEVENLABS_API_KEY"

```

### 2\. Installing Dependencies

The dependencies required vary by tutorial. For simplicity, you can install all necessary packages at once with a single command.

```
pip install google-genai python-dotenv RealtimeSTT elevenlabs PySide6 opencv-python Pillow mss websockets

```

### 3\. Tutorial Guide

Here is a breakdown of each tutorial script and how to run it, from a basic text reply to a full multimodal AI assistant with a GUI.

#### 1\. `1-simpleReply.py`

This script demonstrates a basic, non-streaming text generation request to the Gemini API. It sends a simple prompt and prints the response.

**To run:**  `python Tutorials/1-simpleReply.py`

**Code Breakdown:**

-   It initializes the Gemini client with your API key.

-   The `client.models.generate_content()` function sends the prompt "What is my name" to the "gemini-2.5-flash" model.

-   It then prints the `text` attribute of the response, which contains the generated text.

#### 2\. `2-simpleReplyWithSystemInstructions.py`

This script is similar to the first, but it adds a **system instruction** to the model's configuration. This allows you to give the model a persona or specific instructions to follow.

**To run:**  `python Tutorials/2-simpleReplyWithSystemInstructions.py`

**Code Breakdown:**

-   The key difference is the `config` parameter in the `generate_content` call.

-   `system_instruction="My name is Naz"` tells the model foundational information. Now, when you ask "What is my name", it will respond with "Your name is Naz."

#### 3\. `3-simpleReplyStreaming.py`

This tutorial shows how to get a **streaming response** from the model. The response is printed chunk by chunk as it's received, which is useful for longer replies.

**To run:**  `python Tutorials/3-simpleReplyStreaming.py`

**Code Breakdown:**

-   Instead of `generate_content`, this script uses `generate_content_stream`.

-   It then iterates through the response object, printing each `chunk.text` as it arrives. This creates a typewriter-like effect in the console.

#### 4\. `4-chatWithGemini.py`

This script introduces a basic **conversational chat loop**. It allows for continuous back-and-forth communication with the model.

**To run:**  `python Tutorials/4-chatWithGemini.py`

**Code Breakdown:**

-   It creates a chat session using `client.chats.create()`, which maintains conversation history.

-   The `while True:` loop continuously prompts the user for input.

-   `chat.send_message_stream(user_input)` sends the user's message to the chat session and gets a streaming response back.

-   The loop breaks if the user types "exit".

#### 5\. `5-speechToTextwithGemini.py`

This tutorial integrates the `RealtimeSTT` library for **speech-to-text functionality**. You can speak to the application, and it will transcribe your words into text for the Gemini model.

**To run:**  `python Tutorials/5-speechToTextwithGemini.py`

**Code Breakdown:**

-   It initializes an `AudioToTextRecorder` to capture and transcribe audio from your microphone.

-   `user_input = recorder.text()` waits for you to speak and returns the transcribed text.

-   The transcribed text is then sent to the Gemini chat session as in the previous tutorial.

#### 6\. `6-textToSpeechwithGemini.py`

This script builds on the previous tutorial by adding **text-to-speech** using the ElevenLabs API. It transcribes your speech, gets a response from Gemini, and then plays the audio of the response.

**To run:**  `python Tutorials/6-textToSpeechwithGemini.py`

**Code Breakdown:**

-   It initializes the `ElevenLabs` client using your API key.

-   After receiving the full text response from Gemini, it uses `elevenlabs.text_to_speech.convert()` to generate audio data.

-   The `play(audio)` function then plays the generated audio through your speakers.

#### 7\. `7-geminiLiveApi.py`

This is a more advanced script that demonstrates real-time, **multimodal conversation** using the Gemini Live API. It can process audio and visual input from your camera or screen.

**To run:**  `python Tutorials/7-geminiLiveApi.py`

**Code Breakdown:**

-   This script uses `asyncio` for concurrent operations (handling audio, video, and API communication simultaneously).

-   `client.aio.live.connect()` establishes a persistent, real-time connection to the Gemini Live API.

-   It creates separate asynchronous tasks for:

    -   Sending audio from the microphone (`listen_audio`).

    -   Sending video frames from the camera (`get_frames`) or screen (`get_screen`).

    -   Receiving text responses from Gemini (`receive_text`).

    -   Converting the text responses to speech (`tts`).

    -   Playing the generated audio (`play_audio`).

#### 8\. `8-guiAda.py`

This is the first of the tutorials that uses **PySide6 to create a graphical user interface**. It provides a visual chat window and a display for the video feed.

**To run:**  `python Tutorials/8-guiAda.py`

**Code Breakdown:**

-   It uses the `PySide6` library to create the main window, text display, input box, and video label.

-   The `AI_Core` class runs in a separate thread to handle the backend AI and media processing without freezing the GUI.

-   PySide6's `Signal` and `Slot` mechanism is used for thread-safe communication between the backend (`AI_Core`) and the GUI (`MainWindow`). For example, when the AI core receives text, it emits a `text_received` signal, which is connected to the `update_text` slot in the main window to update the chat display.

#### 9\. `9-googleSearch.py`

This GUI application is a more advanced version of the previous one. It adds the **Google Search tool**, allowing Ada to look up information from the web to answer your questions.

**To run:**  `python Tutorials/9-googleSearch.py`

**Code Breakdown:**

-   The `tools` configuration for the Gemini model is updated to include `{'google_search': {}}`.

-   The `receive_text` function is modified to check for `grounding_metadata` in the server response, which contains the URLs of the search results.

-   A new signal, `search_results_received`, is added to send the list of URLs to the GUI.

-   The GUI is updated with a "Search Sources" panel to display the links that Ada used to find information.

#### 10\. `10-codeExecution.py`

This script is a powerful demonstration of **tool use** with Gemini. It enables the model to execute Python code to perform tasks like calculations or data manipulation.

**To run:**  `python Tutorials/10-codeExecution.py`

**Code Breakdown:**

-   The `tools` configuration now includes `{'code_execution': {}}`.

-   The `receive_text` function is enhanced to detect `executable_code` and `code_execution_result` in the model's response.

-   A new signal, `code_being_executed`, is used to send the code and its output to the GUI.

-   The GUI's left panel is now a versatile "Tool Activity" panel that can display either search results or the code being executed and its result.

#### 11\. `11-functionCalling.py`

This final GUI tutorial demonstrates **function calling**, allowing the AI to interact with your local file system.

**To run:**  `python Tutorials/11-functionCalling.py`

**Code Breakdown:**

-   This script defines several custom functions in Python (`_create_folder`, `_create_file`, `_edit_file`).

-   The `tools` configuration is expanded to include `function_declarations` for these custom functions, describing them to the model.

-   The `receive_text` function now handles `chunk.tool_call`, checks which function the model wants to use, executes the corresponding Python function (e.g., `_create_folder`), and sends the result back to the model using `session.send_tool_response`. This allows the AI to perform actions like creating folders and files on your computer based on your commands.
