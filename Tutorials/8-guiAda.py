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

# --- PySide6 GUI Imports ---
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QLabel, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout
from PySide6.QtCore import QObject, Signal, Slot, Qt
from PySide6.QtGui import QImage, QPixmap, QTextCursor

# --- Media and AI Imports ---
import cv2
import pyaudio
import PIL.Image
import mss
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

    def __init__(self, video_mode=DEFAULT_MODE):
        super().__init__()
        self.video_mode = video_mode
        self.is_running = True
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.config = {
            "response_modalities": ["TEXT"],
            "system_instruction": "Your name is Ada, which stands for Advanced Design Assistant. You have a joking personality and are an Ai designed to help me with engineering project as well as day to day task. Adress me as Sir and speak in a british accent. Also keep replies precise.",
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
        """ Receives text from Gemini and emits signals to the GUI and TTS. """
        while self.is_running:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if response.text:
                        self.text_received.emit(response.text)
                        await self.response_queue_tts.put(response.text)
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
        """Processes text input sent from the GUI and sends it to the AI."""
        while self.is_running:
            text = await self.text_input_queue.get()
            if text is None:
                self.text_input_queue.task_done()
                break
            if self.session:
                print(f">>> [INFO] Sending text to AI: '{text}'")
                for q in [self.response_queue_tts, self.audio_in_queue_player]:
                    while not q.empty(): q.get_nowait()
                await self.session.send(input=text or ".", end_of_turn=True)
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
        """Creates and gathers all main async tasks."""
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
        """Starts the asyncio event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run())

    @Slot(str)
    def handle_user_text(self, text):
        """This slot receives the text from GUI signal and puts it in the async queue."""
        if self.is_running and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.text_input_queue.put(text), self.loop)

    async def shutdown_async_tasks(self):
        """Coroutine to cancel all running tasks."""
        print(">>> [DEBUG] Shutting down async tasks...")
        if self.text_input_queue:
            await self.text_input_queue.put(None)
        for task in self.tasks:
            task.cancel()
        await asyncio.sleep(0.1)
        print(">>> [DEBUG] Async tasks shutdown complete.")

    def stop(self):
        """Thread-safe method to stop the asyncio loop and tasks."""
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
# GUI APPLICATION
# ==============================================================================
class MainWindow(QMainWindow):
    user_text_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ada AI Assistant")
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0;")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # --- Left Section (Blank) ---
        self.left_panel = QWidget()
        self.left_panel.setStyleSheet("background-color: #3c3f41; border-radius: 5px;")
        
        # --- Middle Section (Chat) ---
        self.middle_panel = QWidget()
        self.middle_layout = QVBoxLayout(self.middle_panel)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit { background-color: #3c3f41; color: #a9b7c6;
                        font-size: 16px; border: 1px solid #555; border-radius: 5px; }""")
        self.middle_layout.addWidget(self.text_display)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type your message to Ada here and press Enter...")
        self.input_box.setStyleSheet("""
            QLineEdit { background-color: #3c3f41; color: #a9b7c6; font-size: 14px;
                        border: 1px solid #555; border-radius: 5px; padding: 5px; }""")
        self.input_box.returnPressed.connect(self.send_user_text)
        self.middle_layout.addWidget(self.input_box)

        # --- Right Section (Video) ---
        self.right_panel = QWidget()
        # [FIXED] Re-add a maximum width to prevent the right panel from expanding uncontrollably.
        self.right_panel.setMaximumWidth(500)
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.video_label = QLabel()
        self.video_label.setStyleSheet("border: 2px solid #555; background-color: black; border-radius: 5px;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(self.video_label)
        
        # [FIXED] Revert stretch factors to prioritize the middle panel.
        self.main_layout.addWidget(self.left_panel, 1)
        self.main_layout.addWidget(self.middle_panel, 4)
        self.main_layout.addWidget(self.right_panel, 2)

        self.is_first_ada_chunk = True

        self.setup_backend_thread()

    def setup_backend_thread(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--mode", type=str, default=DEFAULT_MODE,
            help="pixels to stream from", choices=["camera", "screen", "none"]
        )
        args, unknown = parser.parse_known_args()
        
        self.ai_core = AI_Core(video_mode=args.mode)
        self.user_text_submitted.connect(self.ai_core.handle_user_text)
        self.ai_core.text_received.connect(self.update_text)
        self.ai_core.end_of_turn.connect(self.add_newline)
        self.ai_core.frame_received.connect(self.update_frame)
        
        self.backend_thread = threading.Thread(target=self.ai_core.start_event_loop)
        self.backend_thread.daemon = True
        self.backend_thread.start()

    def send_user_text(self):
        """This function is called when the user presses Enter in the input box."""
        text = self.input_box.text().strip()
        if text:
            self.text_display.append(f"<b style='color:#6DAEED;'>You:</b> {text}")
            self.user_text_submitted.emit(text)
            self.input_box.clear()

    @Slot(str)
    def update_text(self, text):
        """Handles streaming text, ensuring only the prefix is bold."""
        if self.is_first_ada_chunk:
            self.is_first_ada_chunk = False
            self.text_display.append(f"<b style='color:#A9B7C6;'>Ada:</b> {text}")
        else:
            self.text_display.insertPlainText(text)
        
        self.text_display.verticalScrollBar().setValue(self.text_display.verticalScrollBar().maximum())


    @Slot()
    def add_newline(self):
        """Called at the end of Ada's turn to reset the flag for the next turn."""
        self.is_first_ada_chunk = True

    @Slot(QImage)
    def update_frame(self, image):
        """Scales the pixmap to the container's width to ensure it fills the space."""
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaledToWidth(
            self.right_panel.width(),
            Qt.TransformationMode.SmoothTransformation
        )
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

