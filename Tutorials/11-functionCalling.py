# --- Core Imports ---
import asyncio
import base64
import io
import os
import sys
import traceback
import json
import websockets
import argparse
import threading
from html import escape

# --- PySide6 GUI Imports ---
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QLabel,
                               QVBoxLayout, QWidget, QLineEdit, QHBoxLayout,
                               QSizePolicy)
from PySide6.QtCore import QObject, Signal, Slot, Qt
from PySide6.QtGui import QImage, QPixmap, QFont, QFontDatabase, QTextCursor

# --- Media and AI Imports ---
import cv2
import pyaudio
import PIL.Image
from google import genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    sys.exit("Error: GEMINI_API_KEY not found. Please set it in your .env file.")
if not ELEVENLABS_API_KEY:
    sys.exit("Error: ELEVENLABS_API_KEY not found. Please check your .env file.")

# --- Configuration ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MODEL = "gemini-live-2.5-flash-preview"
VOICE_ID = 'pFZP5JQG7iQjIQuC4Bku'
DEFAULT_MODE = "camera"
MAX_OUTPUT_TOKENS = 100

# --- Initialize Clients ---
pya = pyaudio.PyAudio()

# ==============================================================================
# AI BACKEND LOGIC
# ==============================================================================
class AI_Core(QObject):
    """
    Handles all backend operations. Inherits from QObject to emit signals
    for thread-safe communication with the GUI.
    """
    text_received = Signal(str)
    end_of_turn = Signal()
    frame_received = Signal(QImage)
    search_results_received = Signal(list)
    code_being_executed = Signal(str, str)

    def __init__(self, video_mode=DEFAULT_MODE):
        super().__init__()
        self.video_mode = video_mode
        self.is_running = True
        self.client = genai.Client(api_key=GEMINI_API_KEY)

        create_folder = {
            "name": "create_folder",
            "description": "Creates a new folder at the specified path relative to the script's root directory.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "folder_path": {
                        "type": "STRING",
                        "description": "The path for the new folder (e.g., 'new_project/assets')."
                    }
                },
                "required": ["folder_path"]
            }
        }

        create_file = {
            "name": "create_file",
            "description": "Creates a new file with specified content at a given path.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "file_path": {
                        "type": "STRING",
                        "description": "The path for the new file (e.g., 'new_project/notes.txt')."
                    },
                    "content": {
                        "type": "STRING",
                        "description": "The content to write into the new file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }

        edit_file = {
            "name": "edit_file",
            "description": "Appends content to an existing file at a specified path.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "file_path": {
                        "type": "STRING",
                        "description": "The path of the file to edit (e.g., 'project/notes.txt')."
                    },
                    "content": {
                        "type": "STRING",
                        "description": "The content to append to the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
        
        tools = [{'google_search': {}}, {'code_execution': {}}, {"function_declarations": [create_folder, create_file, edit_file]}]
        
        self.config = {
            "response_modalities": ["TEXT"],
            "system_instruction": """You have access to tools for searching, code execution, and file system actions.
1.  For information or questions, use `Google Search`.
2.  For math or running python code, use `code_execution`.
3.  If the user asks to create a directory or folder, you must use the `create_folder` function.
4.  If the user asks to create a file with content, you must use the `create_file` function.
5.  If the user asks to add to, append, or edit an existing file, you must use the `edit_file` function.
Prioritize the most appropriate tool for the user's specific request.""",
            "tools": tools,
            "max_output_tokens": MAX_OUTPUT_TOKENS
        }
        self.session = None
        self.audio_stream = None
        self.out_queue_gemini = asyncio.Queue(maxsize=20)
        self.response_queue_tts = asyncio.Queue()
        self.audio_in_queue_player = asyncio.Queue()
        self.text_input_queue = asyncio.Queue()
        self.latest_frame = None
        self.tasks = []
        self.loop = asyncio.new_event_loop()

    def _create_folder(self, folder_path):
        """Creates a folder at the specified path and returns a status dictionary."""
        try:
            if not folder_path or not isinstance(folder_path, str):
                return {"status": "error", "message": "Invalid folder path provided."}
            
            if os.path.exists(folder_path):
                print(f">>> [FUNCTION CALL] Folder '{folder_path}' already exists.")
                return {"status": "skipped", "message": f"The folder '{folder_path}' already exists."}
            
            os.makedirs(folder_path)
            print(f">>> [FUNCTION CALL] Successfully created folder: {folder_path}")
            return {"status": "success", "message": f"Successfully created the folder at '{folder_path}'."}
        except Exception as e:
            print(f">>> [FUNCTION ERROR] Failed to create folder '{folder_path}': {e}")
            return {"status": "error", "message": f"An error occurred: {str(e)}"}

    def _create_file(self, file_path, content):
        """Creates a file with the specified content and returns a status dictionary."""
        try:
            if not file_path or not isinstance(file_path, str):
                return {"status": "error", "message": "Invalid file path provided."}
            
            if os.path.exists(file_path):
                print(f">>> [FUNCTION CALL] File '{file_path}' already exists.")
                return {"status": "skipped", "message": f"The file '{file_path}' already exists."}
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f">>> [FUNCTION CALL] Successfully created file: {file_path}")
            return {"status": "success", "message": f"Successfully created the file at '{file_path}'."}
        except Exception as e:
            print(f">>> [FUNCTION ERROR] Failed to create file '{file_path}': {e}")
            return {"status": "error", "message": f"An error occurred while creating the file: {str(e)}"}

    def _edit_file(self, file_path, content):
        """Appends content to an existing file and returns a status dictionary."""
        try:
            if not file_path or not isinstance(file_path, str):
                return {"status": "error", "message": "Invalid file path provided."}
            
            if not os.path.exists(file_path):
                print(f">>> [FUNCTION ERROR] File '{file_path}' does not exist.")
                return {"status": "error", "message": f"The file '{file_path}' does not exist. Please create it first."}
            
            with open(file_path, 'a') as f:
                f.write(content)
            print(f">>> [FUNCTION CALL] Successfully appended content to file: {file_path}")
            return {"status": "success", "message": f"Successfully appended content to the file at '{file_path}'."}
        except Exception as e:
            print(f">>> [FUNCTION ERROR] Failed to edit file '{file_path}': {e}")
            return {"status": "error", "message": f"An error occurred while editing the file: {str(e)}"}

    async def stream_camera_to_gui(self):
        """Streams camera feed to GUI at high FPS and stores the latest frame."""
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        while self.is_running:
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                await asyncio.sleep(0.01)
                continue

            self.latest_frame = frame
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
            self.frame_received.emit(qt_image.copy())

            await asyncio.sleep(0.033)  # Aim for ~30 FPS
        cap.release()
        print(">>> [INFO] Camera stream stopped.")

    async def send_frames_to_gemini(self):
        """Periodically sends the latest frame to Gemini at 1 FPS."""
        while self.is_running:
            await asyncio.sleep(1.0)
            if self.latest_frame is not None:
                frame_to_send = self.latest_frame
                frame_rgb = cv2.cvtColor(frame_to_send, cv2.COLOR_BGR2RGB)
                pil_img = PIL.Image.fromarray(frame_rgb)
                pil_img.thumbnail([1024, 1024])
                image_io = io.BytesIO()
                pil_img.save(image_io, format="jpeg")
                gemini_data = {"mime_type": "image/jpeg", "data": base64.b64encode(image_io.getvalue()).decode()}
                await self.out_queue_gemini.put(gemini_data)

    async def receive_text(self):
        """ 
        Receives text and tool calls, handles them correctly, and emits signals to the GUI.
        """
        while self.is_running:
            try:
                turn_urls = set()
                turn_code_content = ""
                turn_code_result = ""

                turn = self.session.receive()
                async for chunk in turn:
                    # --- 1. Handle Tool Calls (Function Calling) ---
                    if chunk.tool_call and chunk.tool_call.function_calls:
                        print(">>> [DEBUG] Detected tool call from model.")
                        function_responses = []
                        for fc in chunk.tool_call.function_calls:
                            if fc.name == "create_folder":
                                print(f"\n[Ada is calling function: {fc.name}]")
                                args = fc.args
                                folder_path = args.get("folder_path")
                                result = self._create_folder(folder_path=folder_path)
                                
                                function_responses.append({
                                    "id": fc.id,
                                    "name": fc.name,
                                    "response": result
                                })
                            
                            elif fc.name == "create_file":
                                print(f"\n[Ada is calling function: {fc.name}]")
                                args = fc.args
                                file_path = args.get("file_path")
                                content = args.get("content")
                                result = self._create_file(file_path=file_path, content=content)
                                
                                function_responses.append({
                                    "id": fc.id,
                                    "name": fc.name,
                                    "response": result
                                })
                            
                            elif fc.name == "edit_file":
                                print(f"\n[Ada is calling function: {fc.name}]")
                                args = fc.args
                                file_path = args.get("file_path")
                                content = args.get("content")
                                result = self._edit_file(file_path=file_path, content=content)
                                
                                function_responses.append({
                                    "id": fc.id,
                                    "name": fc.name,
                                    "response": result
                                })
                        
                        print(f">>> [DEBUG] Sending tool response: {function_responses}")
                        await self.session.send_tool_response(function_responses=function_responses)
                        continue

                    # --- 2. Handle Other Server Content (Search, Code Execution) ---
                    if chunk.server_content:
                        if (hasattr(chunk.server_content, 'grounding_metadata') and
                                chunk.server_content.grounding_metadata and
                                chunk.server_content.grounding_metadata.grounding_chunks):
                            for grounding_chunk in chunk.server_content.grounding_metadata.grounding_chunks:
                                if grounding_chunk.web and grounding_chunk.web.uri:
                                    turn_urls.add(grounding_chunk.web.uri)

                        model_turn = chunk.server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.executable_code is not None:
                                    code = part.executable_code.code
                                    if 'print(' in code or '\n' in code or 'import ' in code:
                                        print(f"\n[Ada is executing code...]")
                                        turn_code_content = code
                                    else:
                                        print(f"\n[Ada is searching for: {code}]")

                                if part.code_execution_result is not None:
                                    print(f"[Code execution result received]")
                                    turn_code_result = part.code_execution_result.output
                    
                    # --- 3. Handle Regular Text Response ---
                    if chunk.text:
                        self.text_received.emit(chunk.text)
                        await self.response_queue_tts.put(chunk.text)

                # --- End-of-turn logic to display tool activity ---
                if turn_code_content:
                    self.code_being_executed.emit(turn_code_content, turn_code_result)
                    self.search_results_received.emit([])
                elif turn_urls:
                    self.search_results_received.emit(list(turn_urls))
                    self.code_being_executed.emit("", "")
                else:
                    self.search_results_received.emit([])
                    self.code_being_executed.emit("", "")

                self.end_of_turn.emit()
                await self.response_queue_tts.put(None)
            except Exception:
                if not self.is_running: break
                traceback.print_exc()

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = pya.open(format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE, input=True, input_device_index=mic_info["index"], frames_per_buffer=CHUNK_SIZE)
        print(">>> [INFO] Microphone is listening...")
        while self.is_running:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, exception_on_overflow=False)
            if not self.is_running: break
            await self.out_queue_gemini.put({"data": data, "mime_type": "audio/pcm"})

    async def send_realtime(self):
        while self.is_running:
            msg = await self.out_queue_gemini.get()
            if not self.is_running: break
            await self.session.send(input=msg)
            self.out_queue_gemini.task_done()

    async def process_text_input_queue(self):
        while self.is_running:
            text = await self.text_input_queue.get()
            if text is None:
                self.text_input_queue.task_done()
                break
            if self.session:
                print(f">>> [INFO] Sending text to AI: '{text}'")
                for q in [self.response_queue_tts, self.audio_in_queue_player]:
                    while not q.empty(): q.get_nowait()
                await self.session.send_client_content(
                    turns=[{"role": "user", "parts": [{"text": text or "."}]}]
                )
            self.text_input_queue.task_done()

    async def tts(self):
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id=eleven_flash_v2_5&output_format=pcm_24000"
        while self.is_running:
            text_chunk = await self.response_queue_tts.get()
            if text_chunk is None or not self.is_running:
                self.response_queue_tts.task_done()
                continue
            try:
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({"text": " ", "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}, "xi_api_key": ELEVENLABS_API_KEY,}))
                    async def listen():
                        while self.is_running:
                            try:
                                message = await websocket.recv()
                                data = json.loads(message)
                                if data.get("audio"): await self.audio_in_queue_player.put(base64.b64decode(data["audio"]))
                                elif data.get("isFinal"): break
                            except websockets.exceptions.ConnectionClosed: break
                    listen_task = asyncio.create_task(listen())
                    await websocket.send(json.dumps({"text": text_chunk + " "}))
                    self.response_queue_tts.task_done()
                    while self.is_running:
                        text_chunk = await self.response_queue_tts.get()
                        if text_chunk is None:
                            await websocket.send(json.dumps({"text": ""}))
                            self.response_queue_tts.task_done()
                            break
                        await websocket.send(json.dumps({"text": text_chunk + " "}))
                        self.response_queue_tts.task_done()
                    await listen_task
            except Exception as e: print(f">>> [ERROR] TTS Error: {e}")

    async def play_audio(self):
        stream = await asyncio.to_thread(pya.open, format=pyaudio.paInt16, channels=CHANNELS, rate=RECEIVE_SAMPLE_RATE, output=True)
        print(">>> [INFO] Audio output stream is open.")
        while self.is_running:
            bytestream = await self.audio_in_queue_player.get()
            if bytestream and self.is_running:
                await asyncio.to_thread(stream.write, bytestream)
            self.audio_in_queue_player.task_done()

    async def main_task_runner(self, session):
        self.session = session
        print(">>> [INFO] Starting all backend tasks...")
        if self.video_mode == "camera":
            self.tasks.append(asyncio.create_task(self.stream_camera_to_gui()))
            self.tasks.append(asyncio.create_task(self.send_frames_to_gemini()))
        self.tasks.append(asyncio.create_task(self.listen_audio()))
        self.tasks.append(asyncio.create_task(self.send_realtime()))
        self.tasks.append(asyncio.create_task(self.receive_text()))
        self.tasks.append(asyncio.create_task(self.tts()))
        self.tasks.append(asyncio.create_task(self.play_audio()))
        self.tasks.append(asyncio.create_task(self.process_text_input_queue()))
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def run(self):
        try:
            async with self.client.aio.live.connect(model=MODEL, config=self.config) as session:
                await self.main_task_runner(session)
        except asyncio.CancelledError:
            print(f"\n>>> [INFO] AI Core run loop gracefully cancelled.")
        except Exception as e:
            print(f"\n>>> [ERROR] AI Core run loop encountered an error: {type(e).__name__}: {e}")
        finally:
            if self.is_running:
                self.stop()

    def start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run())

    @Slot(str)
    def handle_user_text(self, text):
        if self.is_running and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.text_input_queue.put(text), self.loop)

    async def shutdown_async_tasks(self):
        print(">>> [DEBUG] Shutting down async tasks...")
        if self.text_input_queue:
            await self.text_input_queue.put(None)
        for task in self.tasks:
            task.cancel()
        await asyncio.sleep(0.1)
        print(">>> [DEBUG] Async tasks shutdown complete.")

    def stop(self):
        if self.is_running and self.loop.is_running():
            self.is_running = False
            future = asyncio.run_coroutine_threadsafe(self.shutdown_async_tasks(), self.loop)
            try:
                future.result(timeout=5)
            except Exception as e:
                print(f">>> [ERROR] Timeout or error during async shutdown: {e}")
        
        if self.audio_stream and self.audio_stream.is_active():
            self.audio_stream.stop_stream()
            self.audio_stream.close()

# ==============================================================================
# STYLED GUI APPLICATION
# ==============================================================================
class MainWindow(QMainWindow):
    user_text_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ada AI Assistant")
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(1280, 720)
        self.setFont(QFont("Inter", 10))
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1F22; }
            QWidget#left_panel, QWidget#middle_panel, QWidget#right_panel { background-color: #2B2D30; border-radius: 8px; }
            QLabel#tool_activity_title { color: #A0A0A0; font-weight: bold; font-size: 11pt; padding: 5px 0px; }
            QTextEdit#text_display { background-color: #2B2D30; color: #EAEAEA; font-size: 12pt; border: none; padding: 10px; }
            QLineEdit#input_box { background-color: #1E1F22; color: #EAEAEA; font-size: 11pt; border: 1px solid #4A4C50; border-radius: 8px; padding: 10px; }
            QLineEdit#input_box:focus { border: 1px solid #007ACC; }
            QLabel#video_label { border: none; background-color: #1E1F22; border-radius: 6px; }
            QLabel#tool_activity_display { background-color: #1E1F22; color: #A0A0A0; font-size: 9pt; border: 1px solid #4A4C50; border-radius: 6px; padding: 8px; }
            QScrollBar:vertical { border: none; background: #2B2D30; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #4A4C50; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # --- Left Section (Tool Activity) ---
        self.left_panel = QWidget()
        self.left_panel.setObjectName("left_panel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(15, 10, 15, 15)
        self.tool_activity_title = QLabel("Tool Activity")
        self.tool_activity_title.setObjectName("tool_activity_title")
        self.left_layout.addWidget(self.tool_activity_title)
        self.tool_activity_display = QLabel()
        self.tool_activity_display.setObjectName("tool_activity_display")
        self.tool_activity_display.setWordWrap(True)
        self.tool_activity_display.setAlignment(Qt.AlignTop)
        self.tool_activity_display.setOpenExternalLinks(True)
        self.tool_activity_display.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.left_layout.addWidget(self.tool_activity_display, 1)
        
        # --- Middle Section (Chat) ---
        self.middle_panel = QWidget()
        self.middle_panel.setObjectName("middle_panel")
        self.middle_layout = QVBoxLayout(self.middle_panel)
        self.middle_layout.setContentsMargins(0, 0, 0, 15)
        self.middle_layout.setSpacing(15)
        self.text_display = QTextEdit()
        self.text_display.setObjectName("text_display")
        self.text_display.setReadOnly(True)
        self.middle_layout.addWidget(self.text_display, 1)
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 0, 15, 0)
        self.input_box = QLineEdit()
        self.input_box.setObjectName("input_box")
        self.input_box.setPlaceholderText("Type your message to Ada here and press Enter...")
        self.input_box.returnPressed.connect(self.send_user_text)
        input_layout.addWidget(self.input_box)
        self.middle_layout.addWidget(input_container)

        # --- Right Section (Video) ---
        self.right_panel = QWidget()
        self.right_panel.setObjectName("right_panel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(15, 15, 15, 15)
        self.video_label = QLabel()
        self.video_label.setObjectName("video_label")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_layout.addWidget(self.video_label)
        
        self.main_layout.addWidget(self.left_panel, 2)
        self.main_layout.addWidget(self.middle_panel, 5)
        self.main_layout.addWidget(self.right_panel, 3)

        self.is_first_ada_chunk = True
        self.setup_backend_thread()

    def setup_backend_thread(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", type=str, default=DEFAULT_MODE, help="pixels to stream from", choices=["camera", "screen", "none"])
        args, unknown = parser.parse_known_args()
        
        self.ai_core = AI_Core(video_mode=args.mode)
        self.user_text_submitted.connect(self.ai_core.handle_user_text)
        self.ai_core.text_received.connect(self.update_text)
        self.ai_core.search_results_received.connect(self.update_search_results)
        self.ai_core.code_being_executed.connect(self.display_executed_code)
        self.ai_core.end_of_turn.connect(self.add_newline)
        self.ai_core.frame_received.connect(self.update_frame)
        
        self.backend_thread = threading.Thread(target=self.ai_core.start_event_loop)
        self.backend_thread.daemon = True
        self.backend_thread.start()

    def send_user_text(self):
        text = self.input_box.text().strip()
        if text:
            self.text_display.append(f"<p style='color:#0095FF; font-weight:bold;'>You:</p><p style='color:#EAEAEA;'>{escape(text)}</p>")
            self.user_text_submitted.emit(text)
            self.input_box.clear()

    @Slot(str)
    def update_text(self, text):
        if self.is_first_ada_chunk:
            self.is_first_ada_chunk = False
            self.text_display.append(f"<p style='color:#A0A0A0; font-weight:bold;'>Ada:</p>")
        cursor = self.text_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.text_display.verticalScrollBar().setValue(self.text_display.verticalScrollBar().maximum())

    @Slot(list)
    def update_search_results(self, urls):
        if not urls:
            if "Search Sources" in self.tool_activity_title.text():
                self.tool_activity_display.clear()
                self.tool_activity_title.setText("Tool Activity")
            return
        self.tool_activity_display.clear()
        self.tool_activity_title.setText("Search Sources")
        html_content = ""
        for i, url in enumerate(urls):
            try:
                display_text = url.split('//')[1].split('/')[0]
            except IndexError:
                display_text = url
            html_content += f'<p style="margin:0; padding: 4px;">{i+1}. <a href="{url}" style="color: #007ACC; text-decoration: none;">{display_text}</a></p>'
        self.tool_activity_display.setText(html_content)

    @Slot(str, str)
    def display_executed_code(self, code, result):
        if not code:
            if "Executing Code" in self.tool_activity_title.text():
                 self.tool_activity_display.clear()
                 self.tool_activity_title.setText("Tool Activity")
            return
        self.tool_activity_display.clear()
        self.tool_activity_title.setText("Executing Code")
        escaped_code = escape(code)
        html_content = f'<pre style="white-space: pre-wrap; word-wrap: break-word; font-family: Consolas, monaco, monospace; color: #D0D0D0; font-size: 9pt; line-height: 1.4;">{escaped_code}</pre>'
        if result:
            escaped_result = escape(result.strip())
            html_content += f"""
                <p style="color:#A0A0A0; font-weight:bold; margin-top:10px; margin-bottom: 5px; font-family: Inter;">Result:</p>
                <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: Consolas, monaco, monospace; color: #90EE90; font-size: 9pt;">{escaped_result}</pre>
            """
        self.tool_activity_display.setText(html_content)

    @Slot()
    def add_newline(self):
        if not self.is_first_ada_chunk:
             self.text_display.append("")
        self.is_first_ada_chunk = True

    @Slot(QImage)
    def update_frame(self, image):
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.video_label.setPixmap(scaled_pixmap)
            
    def closeEvent(self, event):
        print(">>> [INFO] Closing application...")
        self.ai_core.stop()
        event.accept()

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print(">>> [INFO] Application interrupted by user.")
    finally:
        pya.terminate()
        print(">>> [INFO] Application terminated.")

