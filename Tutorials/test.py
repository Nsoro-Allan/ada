"""
A real-time, multimodal conversational AI script using Google's Gemini Live API
for language understanding and ElevenLabs for text-to-speech synthesis,
with a PySide6 Graphical User Interface (GUI).
"""

import asyncio
import base64
import io
import os
import sys
import traceback
import json
import websockets

import cv2
import pyaudio
import PIL.Image
import mss
import argparse

from google import genai
from dotenv import load_dotenv

# --- PySide6 Imports ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import (
    QThread, QObject, Signal, Slot, Qt, QTimer
)
from PySide6.QtGui import (
    QImage, QPixmap
)

# --- Load Environment Variables ---
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    sys.exit("Error: GEMINI_API_KEY not found. Please set it in your .env file.")
if not ELEVENLABS_API_KEY:
    sys.exit("Error: ELEVENLABS_API_KEY not found. Please check your .env file and ElevenLabs account.")

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

# --- Audio Configuration ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# --- API Configuration ---
MODEL = "gemini-live-2.5-flash-preview"
DEFAULT_MODE = "camera"
VOICE_ID = 'pFZP5JQG7iQjIQuC4Bku'

# --- Initialize Clients ---
client = genai.Client(api_key=GEMINI_API_KEY)
CONFIG = {
    "response_modalities": ["TEXT"],
    "system_instruction": "Your name is Ada, which stands for Advanced Design Assistant. You have a joking personality and are an Ai designed to help me with engineering project as well as day to day task. Adress me as Sir and speak in a british accent. Also keep replies precise.",
}
pya = pyaudio.PyAudio()


class AudioLoop:
    """
    Manages the real-time audio and video streams with Gemini and ElevenLabs.
    Modified to communicate with a GUI via a Worker class.
    """
    def __init__(self, video_mode, worker):
        self.video_mode = video_mode
        self.worker = worker  # Reference to the AsyncWorker
        self.out_queue_gemini = None
        self.response_queue_tts = None
        self.audio_in_queue_player = None
        self.session = None
        self.audio_stream = None
        self.user_text_queue = asyncio.Queue()

    async def send_text(self):
        """Replaced the original input() loop with one that reads from the GUI's queue."""
        while True:
            text = await self.user_text_queue.get()
            if text.lower() == "q": 
                break
            
            # Clear previous response queues before sending a new message
            for q in [self.response_queue_tts, self.audio_in_queue_player]:
                while not q.empty(): q.get_nowait()
            
            await self.session.send(input=text or ".", end_of_turn=True)
            self.user_text_queue.task_done()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret: 
            return None
        return frame # Return the raw OpenCV frame

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        if not cap.isOpened():
            print(">>> [ERROR] Could not open camera.")
            return

        while cap.isOpened():
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            
            # Emit the raw frame to the GUI thread
            self.worker.newFrameSignal.emit(frame)
            
            # Process for Gemini
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(frame_rgb)
            img.thumbnail([1024, 1024])
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg")
            gemini_frame = {"mime_type": "image/jpeg", "data": base64.b64encode(image_io.getvalue()).decode()}
            
            # Send to Gemini
            await self.out_queue_gemini.put(gemini_frame)
            await asyncio.sleep(0.1) # Shorter delay for more real-time feel
            
        cap.release()
        print(">>> [INFO] Camera released.")

    def _get_screen(self):
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            img = PIL.Image.open(io.BytesIO(png_bytes))
            image_io = io.BytesIO()
            img.convert("RGB").save(image_io, format="jpeg")
            return {"mime_type": "image/jpeg", "data": base64.b64encode(image_io.getvalue()).decode()}

    async def get_screen(self):
        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            await self.out_queue_gemini.put(frame)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue_gemini.get()
            await self.session.send(input=msg)
            self.out_queue_gemini.task_done()

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open, format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
            input=True, input_device_index=mic_info["index"], frames_per_buffer=CHUNK_SIZE
        )
        kwargs = {"exception_on_overflow": False}
        print(">>> [INFO] Microphone is listening...")
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue_gemini.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_text(self):
        """Sends received text to the GUI via a signal instead of printing."""
        while True:
            turn = self.session.receive()
            full_response = ""
            async for response in turn:
                if response.text:
                    full_response += response.text
                    self.worker.newTextSignal.emit(response.text) # Emit partial responses as they arrive
                    await self.response_queue_tts.put(response.text)
            self.worker.newTextSignal.emit("\n") # Add a newline to the GUI after a full turn
            await self.response_queue_tts.put(None)

    async def tts(self):
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id=eleven_flash_v2_5&output_format=pcm_24000"
        while True:
            text_chunk = await self.response_queue_tts.get()
            if text_chunk is None:
                self.response_queue_tts.task_done()
                continue
            try:
                async with websockets.connect(uri) as websocket:
                    await websocket.send(json.dumps({
                        "text": " ",
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                        "xi_api_key": ELEVENLABS_API_KEY,
                    }))
                    async def listen():
                        while True:
                            try:
                                message = await websocket.recv()
                                data = json.loads(message)
                                if data.get("audio"):
                                    await self.audio_in_queue_player.put(base64.b64decode(data["audio"]))
                                elif data.get("isFinal"):
                                    break
                            except websockets.exceptions.ConnectionClosed:
                                break
                    listen_task = asyncio.create_task(listen())
                    await websocket.send(json.dumps({"text": text_chunk + " "}))
                    self.response_queue_tts.task_done()
                    while True:
                        text_chunk = await self.response_queue_tts.get()
                        if text_chunk is None:
                            await websocket.send(json.dumps({"text": ""}))
                            self.response_queue_tts.task_done()
                            break
                        await websocket.send(json.dumps({"text": text_chunk + " "}))
                        self.response_queue_tts.task_done()
                    await listen_task
            except websockets.exceptions.WebSocketException as e:
                print(f">>> [ERROR] ElevenLabs WebSocket connection failed: {e}. Retrying in 5s.")
                await asyncio.sleep(5)
            except Exception as e:
                print(f">>> [ERROR] An unexpected error occurred in the TTS task: {e}")
                await asyncio.sleep(5)

    async def play_audio(self):
        try:
            stream = await asyncio.to_thread(
                pya.open, format=FORMAT, channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE, output=True
            )
        except Exception as e:
            print(f">>> [FATAL ERROR] Could not open PyAudio stream: {e}")
            return
        while True:
            try:
                bytestream = await self.audio_in_queue_player.get()
                if bytestream:
                    await asyncio.to_thread(stream.write, bytestream)
                self.audio_in_queue_player.task_done()
            except Exception as e:
                print(f">>> [ERROR] Error in audio playback loop: {e}")

    async def run_tasks(self):
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session, asyncio.TaskGroup() as tg:
                self.session = session
                self.out_queue_gemini = asyncio.Queue(maxsize=20)
                self.response_queue_tts = asyncio.Queue()
                self.audio_in_queue_player = asyncio.Queue()
                print(">>> [INFO] Starting all tasks...")
                tg.create_task(self.send_text())
                tg.create_task(self.listen_audio())
                if self.video_mode == "camera": 
                    tg.create_task(self.get_frames())
                elif self.video_mode == "screen": 
                    tg.create_task(self.get_screen())
                tg.create_task(self.send_realtime())
                tg.create_task(self.receive_text())
                tg.create_task(self.tts())
                tg.create_task(self.play_audio())
                await asyncio.Future()  # Keep the TaskGroup running indefinitely
        except asyncio.CancelledError:
            print("\n>>> [INFO] Async tasks cancelled.")
        except Exception:
            traceback.print_exc()
        finally:
            if self.audio_stream and self.audio_stream.is_active():
                self.audio_stream.stop_stream()
                self.audio_stream.close()

class AsyncWorker(QObject):
    """
    A QObject to manage the asyncio loop in a separate thread.
    Communicates with the GUI using signals.
    """
    newTextSignal = Signal(str)
    newFrameSignal = Signal(object) # object here will be a numpy array from cv2
    
    def __init__(self, video_mode):
        super().__init__()
        self.video_mode = video_mode
        self.audio_loop = None

    @Slot()
    def run_async_loop(self):
        """Starts the asyncio event loop and runs the main application logic."""
        self.audio_loop = AudioLoop(self.video_mode, self)
        asyncio.run(self.audio_loop.run_tasks())

    @Slot(str)
    def send_user_message(self, text):
        """Receives a message from the GUI and puts it in the async queue."""
        if self.audio_loop and self.audio_loop.user_text_queue:
            asyncio.run_coroutine_threadsafe(
                self.audio_loop.user_text_queue.put(text),
                asyncio.get_event_loop()
            )

class MainWindow(QMainWindow):
    """
    The main GUI window for the application.
    """
    sendMessageSignal = Signal(str)
    
    def __init__(self, worker_thread, worker):
        super().__init__()
        self.setWindowTitle("Ada - Engineering Assistant")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.connect_signals(worker_thread, worker)

    def setup_ui(self):
        # AI Response Display
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setPlaceholderText("Ada's responses will appear here...")
        self.main_layout.addWidget(self.response_text)

        # Webcam Feed Display
        self.video_label = QLabel("Webcam Feed")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFrameShape(QFrame.StyledPanel)
        self.video_label.setMinimumSize(640, 480)
        self.main_layout.addWidget(self.video_label)

        # User Input Section
        input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type your message to Ada...")
        self.send_button = QPushButton("Send")
        
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(self.send_button)
        self.main_layout.addLayout(input_layout)

    def connect_signals(self, worker_thread, worker):
        # Connect signals from the worker to the main GUI
        worker.newTextSignal.connect(self.update_text_area)
        worker.newFrameSignal.connect(self.update_video_feed)
        
        # Connect signals from the GUI to the worker
        self.send_button.clicked.connect(self.send_message)
        self.input_line.returnPressed.connect(self.send_message)
        
        # Start the worker thread
        worker_thread.started.connect(worker.run_async_loop)
        worker_thread.start()

    @Slot(str)
    def update_text_area(self, text):
        """Slot to receive and append text from the worker thread."""
        self.response_text.insertPlainText(text)
        self.response_text.ensureCursorVisible()

    @Slot(object)
    def update_video_feed(self, frame):
        """Slot to receive a frame and display it in the QLabel."""
        if frame is not None:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

    def send_message(self):
        """Handles user input and sends it to the worker thread."""
        text = self.input_line.text().strip()
        if text:
            # Display user's message in the text area
            self.response_text.append(f"<b>You:</b> {text}\n")
            self.sendMessageSignal.emit(text)
            self.input_line.clear()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", type=str, default=DEFAULT_MODE,
        help="pixels to stream from", choices=["camera", "screen", "none"]
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    # Create the thread and the worker
    worker_thread = QThread()
    worker = AsyncWorker(video_mode=args.mode)
    worker.moveToThread(worker_thread)
    
    # Connect GUI signals to worker slots
    main_window = MainWindow(worker_thread, worker)
    main_window.sendMessageSignal.connect(worker.send_user_message)
    
    main_window.show()
    
    # Clean up on exit
    app.aboutToQuit.connect(worker_thread.quit)
    worker_thread.finished.connect(app.quit)

    sys.exit(app.exec())