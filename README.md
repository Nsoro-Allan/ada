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

Follow these steps to get A.D.A. up and running on your local machine using the **Anaconda** environment manager.

### 1\. Prerequisites

Before you begin, ensure you have the following installed:

*   **Anaconda**: Download and install the Anaconda Distribution for your operating system. [Download Anaconda](https://www.anaconda.com/download)
    
*   **Git**: [Download Git](https://git-scm.com/downloads)
    
*   **Gemini API Key**: A key for the **Gemini-live-2.5-flash-preview** model. [Get an API Key](https://www.google.com/search?q=https://ai.google.dev/docs/genai_api_key)
    
*   **ElevenLabs API Key**: An API key for ElevenLabs Text-to-Speech (TTS). [Get an API Key](https://elevenlabs.io/)
    

### 2\. Create an Anaconda Environment

Open your Anaconda Prompt (on Windows) or terminal (on macOS/Linux). Create a new virtual environment to manage A.D.A.'s dependencies.

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   conda create --name ada-env python=3.10   `

Activate the newly created environment:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   conda activate ada-env   `

### 3\. Clone the Repository

Clone this project's repository from GitHub:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   git clone https://github.com/your-username/your-repo-name.git  cd your-repo-name   `

### 4\. Install Dependencies

With your Anaconda environment active, install all the required Python packages using the following commands.

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   pip install google-genai  pip install python-dotenv  pip install RealtimeSTT  pip install elevenlabs  pip install PySide6  pip install opencv-python  pip install Pillow  pip install mss  pip install websockets   `

> **Note**: If you encounter issues with PyAudio, you can install it using pip directly. On some Linux distributions, you may need to install development libraries.

### 5\. Configure API Keys

Create a .env file in the project's root directory to store your API keys securely.

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   touch .env   `

Add your API keys to the .env file:

Code snippet

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"  ELEVENLABS_API_KEY="YOUR_ELEVENLABS_API_KEY_HERE"   `

> **Important**: Do not share or commit your .env file to GitHub. The project's .gitignore file is configured to ignore it.

Usage
-----

### Running the Application

Ensure your ada-env environment is active, then run the main Python script:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python main.py   `

### Command-line Arguments

You can specify the initial video mode when launching the application:

*   \--mode camera: Starts with the webcam feed active.
    
*   \--mode screen: Starts with screen sharing active.
    
*   \--mode none: Starts without a video feed (default).
    

**Example**:

Bash

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   python main.py --mode camera   `

### Interacting with A.D.A.

*   **Voice**: The application listens in real-time. Simply speak to the assistant to begin a conversation.
    
*   **Text**: Use the input box to type commands or questions.
    
*   **Video Mode Buttons**: Use the "WEBCAM", "SCREEN", and "OFFLINE" buttons on the right panel to change the visual input source.
    

A.D.A. can answer questions, run code, manage files, open applications, and analyze content on your screen.