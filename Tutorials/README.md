Ada AI Tutorials
================

This document provides a step-by-step guide to setting up and running the various tutorials for the Ada AI assistant, which demonstrates different functionalities of the Gemini API.

### 1\. Prerequisites & Setup

Before you begin, you'll need to set up your Python environment and obtain the necessary API keys.

#### Step 1: Install Python and Create a Virtual Environment

It's highly recommended to use a virtual environment to manage your project's dependencies cleanly.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   # Create a new virtual environment  python -m venv venv  # Activate the virtual environment  # On Windows:  venv\Scripts\activate  # On macOS/Linux:  source venv/bin/activate   `

#### Step 2: Obtain API Keys

You'll need API keys for both the Gemini API and the ElevenLabs API.

*   **Gemini API:** Get your key from the [Google AI Studio](https://aistudio.google.com/app/apikey).
    
*   **ElevenLabs API:** Get your key from the [ElevenLabs website](https://elevenlabs.io/).
    

#### Step 3: Create the .env File

The tutorial scripts use a .env file to securely store your API keys. Create a file named .env in the root directory of your project and add the following lines, replacing the placeholders with your actual keys.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GEMINI_API_KEY="YOUR_GEMINI_API_KEY"  ELEVENLABS_API_KEY="YOUR_ELEVENLABS_API_KEY"   `

### 2\. Installing Dependencies

The dependencies required vary by tutorial. For simplicity, you can install all necessary packages at once with a single command.

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   pip install google-generativeai python-dotenv RealtimeSTT elevenlabs PySide6 opencv-python Pillow mss websockets   `

### 3\. Tutorial Guide

Here is a breakdown of each tutorial script and how to run it, from a basic text reply to a full multimodal AI assistant with a GUI.

#### 1\. 1-simpleReply.py

This script demonstrates a basic, non-streaming text generation request to the Gemini API. It sends a simple prompt and prints the response.

**To run:** python 1-simpleReply.py

#### 2\. 2-simpleReplyWithSystemInstructions.py

This script is similar to the first, but it adds a **system instruction** to the model's configuration. This allows you to give the model a persona or specific instructions to follow.

**To run:** python 2-simpleReplyWithSystemInstructions.py

#### 3\. 3-simpleReplyStreaming.py

This tutorial shows how to get a **streaming response** from the model. The response is printed chunk by chunk as it's received, which is useful for longer replies.

**To run:** python 3-simpleReplyStreaming.py

#### 4\. 4-chatWithGemini.py

This script introduces a basic **conversational chat loop**. It allows for continuous back-and-forth communication with the model.

**To run:** python 4-chatWithGemini.py

#### 5\. 5-speechToTextwithGemini.py

This tutorial integrates the RealtimeSTT library for **speech-to-text functionality**. You can speak to the application, and it will transcribe your words into text for the Gemini model.

**To run:** python 5-speechToTextwithGemini.py

#### 6\. 6-textToSpeechwithGemini.py

This script builds on the previous tutorial by adding **text-to-speech** using the ElevenLabs API. It transcribes your speech, gets a response from Gemini, and then plays the audio of the response.

**To run:** python 6-textToSpeechwithGemini.py

#### 7\. 7-geminiLiveApi.py

This is a more advanced script that demonstrates real-time, **multimodal conversation** using the Gemini Live API. It can process audio and visual input from your camera or screen.

**To run:** python 7-geminiLiveApi.py

#### 8\. 8-guiAda.py

This is the first of the tutorials that uses **PySide6 to create a graphical user interface**. It provides a visual chat window and a display for the video feed.

**To run:** python 8-guiAda.py

#### 9\. 9-googleSearch.py

This GUI application is a more advanced version of the previous one. It adds the **Google Search tool**, allowing Ada to look up information from the web to answer your questions.

**To run:** python 9-googleSearch.py

#### 10\. 10-codeExecution.py

This script is a powerful demonstration of **tool use** with Gemini. It enables the model to execute Python code to perform tasks like calculations or data manipulation.

**To run:** python 10-codeExecution.py

#### 11\. 11-functionCalling.py

This final GUI tutorial combines all previous functionalities, including **function calling** for both Google Search and code execution. This is the most complete example of the Ada AI assistant.

**To run:** python 11-functionCalling.py