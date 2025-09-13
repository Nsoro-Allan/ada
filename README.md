Advanced Digital Assistant (A.D.A.)
===================================

A.D.A. is an advanced, real-time digital assistant built with Google's **Gemini-live-2.5-flash-preview** model. It features a responsive graphical user interface (GUI) using **PySide6**, real-time audio communication, and the ability to process live video from either a webcam or a screen share. A.D.A. is equipped with powerful tools for searching, code execution, and managing your local file system.

  

  

Features
--------

*   🗣️ **Real-time Conversation**: Seamless, low-latency voice-to-voice interaction powered by Google Gemini and ElevenLabs TTS.
    
*   👀 **Live Visual Input**: A.D.A. can see what you see, with the ability to switch between a live **webcam** feed and a **screen share**. This allows it to answer questions about on-screen content, debug code visually, or provide guidance as you work.
    
*   🛠️ **Integrated Tooling**: The assistant can perform a variety of actions by invoking powerful tools, including:
    
    *   **Google Search**: For real-time information retrieval.
        
    *   **Code Execution**: To run and debug Python code.
        
    *   **File System Management**: Create, edit, read, and list files and folders on your computer.
        
    *   **System Actions**: Open applications and websites.
        
*   🎨 **Dynamic UI**: A responsive and visually appealing GUI built with PySide6, featuring a **3D animated avatar** that pulses when the assistant is speaking.
    
*   💻 **Cross-Platform**: Designed to work on Windows, macOS, and Linux.
    

Setup
-----

Follow these steps to get A.D.A. up and running on your local machine.

### 1\. Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.10 or newer**: [Download Python](https://www.python.org/downloads/)
    
*   **Gemini API Key**: A key for the **Gemini-live-2.5-flash-preview** model. [Get an API Key](https://www.google.com/search?q=https://ai.google.dev/docs/genai_api_key)
    
*   **ElevenLabs API Key**: An API key for ElevenLabs Text-to-Speech (TTS). [Get an API Key](https://elevenlabs.io/)
    
*   **Git**: [Download Git](https://git-scm.com/downloads)
    

### 2\. Clone the Repository

Open your terminal or command prompt and clone this repository:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   git clone https://github.com/your-username/your-repo-name.git  cd your-repo-name   `

### 3\. Install Dependencies

Install the required Python packages using pip:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   pip install -r requirements.txt   `

> **Note**: This project relies on pyaudio, which can sometimes be tricky to install. If you encounter issues, refer to the [PyAudio installation guide](https://pypi.org/project/PyAudio/).

### 4\. Configure API Keys

Create a .env file in the root directory of the project. This file will store your secret API keys securely.

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   touch .env   `

Add your API keys to the .env file:

Code snippet

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"  ELEVENLABS_API_KEY="YOUR_ELEVENLABS_API_KEY_HERE"   `

> **Important**: Do not share your .env file or commit it to GitHub. It's already included in the .gitignore to prevent this.

Usage
-----

### Running the Application

To start A.D.A., run the main Python script from your terminal:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python main.py   `

### Command-line Arguments

You can specify the initial video mode using a command-line argument:

*   \--mode camera: Starts the application with the webcam feed active.
    
*   \--mode screen: Starts the application with screen sharing active.
    
*   \--mode none: Starts the application without any video feed (this is the default).
    

**Example**:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python main.py --mode camera   `

### Interacting with A.D.A.

*   **Voice**: The application listens for your voice in real-time. Simply start speaking to interact with the assistant.
    
*   **Text**: You can also type commands into the input box at the bottom of the screen.
    
*   **Video Mode Buttons**: Use the "WEBCAM", "SCREEN", and "OFFLINE" buttons on the right panel to switch between video input modes.
    

### A.D.A.'s Capabilities

*   **Ask questions**: "Who won the last Super Bowl?"
    
*   **Run code**: "Execute a Python script that prints 'Hello, World!' to the console."
    
*   **Manage files**: "Create a folder named project\_alpha and a file inside it called notes.txt with the text 'My project notes'."
    
*   **Open applications**: "Open Notepad."
    
*   **Analyze the screen**: "What is currently displayed on my screen?"
    

Troubleshooting
---------------

*   **"Error: GEMINI\_API\_KEY not found"**: Make sure you have created the .env file and correctly entered your GEMINI\_API\_KEY without any extra spaces or quotes.
    
*   **Audio issues**: Ensure your microphone is properly connected and configured as the default input device in your system settings.
    
*   **GUI not launching**: Verify that PySide6 is installed correctly. Try reinstalling with pip install --force-reinstall PySide6.
    
*   **Live video feed not working**: Check that your webcam drivers are up to date and that other applications are not using the camera. For screen share, ensure the application has the necessary permissions.