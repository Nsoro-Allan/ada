"""
A real-time, multimodal conversational AI class using Google's Gemini Live API
for language understanding and ElevenLabs for text-to-speech synthesis.
This refactored version is encapsulated into a class for easy reuse and extensibility.
"""

import asyncio
import base64
import io
import os
import sys
import traceback
import json
import websockets
import argparse
from typing import Optional

import cv2
import pyaudio
import PIL.Image
import mss
from google import genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

class ADA:
    """
    A class to encapsulate the functionality of a real-time, multimodal
    conversational AI assistant named ADA (Advanced Design Assistant).
    """

    # --- Audio Configuration ---
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    SEND_SAMPLE_RATE = 16000
    RECEIVE_SAMPLE_RATE = 24000
    CHUNK_SIZE = 1024

    # --- API Configuration ---
    GEMINI_MODEL = "gemini-live-2.5-flash-preview"
    ELEVENLABS_VOICE_ID = 'pFZP5JQG7iQjIQuC4Bku'
    ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"

    DEFAULT_SYSTEM_INSTRUCTION = (
        "Your name is Ada, which stands for Advanced Design Assistant. "
        "You have a joking personality and are an AI designed to help me with "
        "engineering projects as well as day-to-day tasks. Address me as Sir "
        "and speak in a British accent. Also, keep replies precise."
    )

    def __init__(self, video_mode: str = "camera", system_instruction: Optional[str] = None):
        """
        Initializes the ADA assistant.

        Args:
            video_mode (str): The video input mode. Can be "camera", "screen", or "none".
            system_instruction (Optional[str]): A custom system instruction for the AI.
                                                 If None, a default is used.
        """
        self.video_mode = video_mode
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")
        self._elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self._validate_api_keys()

        # --- Queues for data transfer between async tasks ---
        self.out_queue_gemini: Optional[asyncio.Queue] = None
        self.response_queue_tts: Optional[asyncio.Queue] = None
        self.audio_in_queue_player: Optional[asyncio.Queue] = None

        # --- Clients and Streams ---
        self.gemini_client = genai.Client(api_key=self._gemini_api_key)
        self.pyaudio_instance = pyaudio.PyAudio()
        self.session: Optional[genai.live.AsyncLiveSession] = None
        self.audio_stream: Optional[pyaudio.Stream] = None

        self.gemini_config = {
            "response_modalities": ["TEXT"],
            "system_instruction": system_instruction or self.DEFAULT_SYSTEM_INSTRUCTION,
        }
        
        # Ensure compatibility with older Python versions for asyncio.TaskGroup
        if sys.version_info < (3, 11, 0):
            import taskgroup, exceptiongroup
            asyncio.TaskGroup = taskgroup.TaskGroup
            asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

    def _validate_api_keys(self):
        """Checks if the necessary API keys are set."""
        if not self._gemini_api_key:
            sys.exit("Error: GEMINI_API_KEY not found. Please set it in your .env file.")
        if not self._elevenlabs_api_key:
            sys.exit("Error: ELEVENLABS_API_KEY not found. Please check your .env file.")

    async def _send_text_input(self):
        """Coroutine to handle text input from the user."""
        print(">>> [INFO] You can now type messages. Type 'q' and press Enter to exit.")
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            # Clear previous response queues to avoid playing old audio
            for q in [self.response_queue_tts, self.audio_in_queue_player]:
                while not q.empty():
                    q.get_nowait()
            if self.session:
                await self.session.send(input=text or ".", end_of_turn=True)

    # --- Video Frame Handling ---
    
    @staticmethod
    def _process_frame(frame_data, source_type: str) -> Optional[dict]:
        """Converts a video frame (from camera or screen) to a sendable format."""
        try:
            if source_type == 'camera':
                frame_rgb = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
                img = PIL.Image.fromarray(frame_rgb)
            elif source_type == 'screen':
                img = PIL.Image.open(io.BytesIO(frame_data))
                img = img.convert("RGB")
            else:
                return None

            img.thumbnail([1024, 1024])
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg")
            encoded_image = base64.b64encode(image_io.getvalue()).decode()
            return {"mime_type": "image/jpeg", "data": encoded_image}
        except Exception as e:
            print(f">>> [ERROR] Failed to process frame: {e}")
            return None

    async def _stream_camera_frames(self):
        """Coroutine to capture and queue frames from the webcam."""
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        if not cap.isOpened():
            print(">>> [ERROR] Could not open camera.")
            return
        while True:
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                break
            processed_frame = self._process_frame(frame, 'camera')
            if processed_frame and self.out_queue_gemini:
                await self.out_queue_gemini.put(processed_frame)
            await asyncio.sleep(1.0)  # Frame capture interval
        cap.release()

    async def _stream_screen_frames(self):
        """Coroutine to capture and queue frames from the screen."""
        with mss.mss() as sct:
            while True:
                sct_img = sct.grab(sct.monitors[1])
                png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                processed_frame = self._process_frame(png_bytes, 'screen')
                if processed_frame and self.out_queue_gemini:
                    await self.out_queue_gemini.put(processed_frame)
                await asyncio.sleep(1.0) # Frame capture interval

    # --- Audio Handling ---

    async def _listen_microphone(self):
        """Coroutine to listen to the microphone and queue audio data."""
        try:
            mic_info = self.pyaudio_instance.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                self.pyaudio_instance.open,
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=self.CHUNK_SIZE
            )
        except Exception as e:
            print(f">>> [FATAL ERROR] Could not open microphone stream: {e}")
            return
            
        print(">>> [INFO] Microphone is listening...")
        while True:
            try:
                data = await asyncio.to_thread(self.audio_stream.read, self.CHUNK_SIZE, exception_on_overflow=False)
                if self.out_queue_gemini:
                    await self.out_queue_gemini.put({"data": data, "mime_type": "audio/pcm"})
            except IOError as e:
                print(f">>> [ERROR] Microphone read error: {e}")
                break

    async def _play_audio_output(self):
        """Coroutine to play audio received from the TTS service."""
        try:
            stream = await asyncio.to_thread(
                self.pyaudio_instance.open,
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RECEIVE_SAMPLE_RATE,
                output=True
            )
            print(">>> [INFO] Audio output stream is open.")
        except Exception as e:
            print(f">>> [FATAL ERROR] Could not open PyAudio output stream: {e}")
            return

        while True:
            try:
                bytestream = await self.audio_in_queue_player.get()
                if bytestream:
                    await asyncio.to_thread(stream.write, bytestream)
                self.audio_in_queue_player.task_done()
            except Exception as e:
                print(f">>> [ERROR] Error in audio playback loop: {e}")

    # --- API Communication ---

    async def _send_to_gemini(self):
        """Coroutine to send data from the outgoing queue to Gemini."""
        while True:
            if self.out_queue_gemini and self.session:
                msg = await self.out_queue_gemini.get()
                await self.session.send(input=msg)
                self.out_queue_gemini.task_done()

    async def _receive_from_gemini(self):
        """Coroutine to receive text responses from Gemini and queue them for TTS."""
        while True:
            if self.session:
                turn = self.session.receive()
                async for response in turn:
                    if response.text:
                        print(response.text, end="", flush=True)
                        print(f"\n>>> [DEBUG] Queueing for TTS: '{response.text}'")
                        if self.response_queue_tts:
                            await self.response_queue_tts.put(response.text)
                print()
                if self.response_queue_tts:
                    await self.response_queue_tts.put(None) # Signal end of turn

    async def _run_tts(self):
        """Coroutine to handle Text-to-Speech with ElevenLabs."""
        uri = (
            f"wss://api.elevenlabs.io/v1/text-to-speech/{self.ELEVENLABS_VOICE_ID}"
            f"/stream-input?model_id={self.ELEVENLABS_MODEL_ID}&output_format=pcm_{self.RECEIVE_SAMPLE_RATE}"
        )
        while True:
            # Wait for a conversational turn to start
            text_chunk = await self.response_queue_tts.get()
            if text_chunk is None:
                self.response_queue_tts.task_done()
                continue

            try:
                print(">>> [DEBUG] Attempting to connect to ElevenLabs WebSocket...")
                async with websockets.connect(uri) as websocket:
                    print(">>> [SUCCESS] ElevenLabs WebSocket Connected.")
                    await websocket.send(json.dumps({
                        "text": " ",
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                        "xi_api_key": self._elevenlabs_api_key,
                    }))

                    async def tts_listen():
                        """Listens for audio data until the connection closes."""
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
                    
                    listen_task = asyncio.create_task(tts_listen())

                    # Send the first and subsequent text chunks for this turn
                    await websocket.send(json.dumps({"text": text_chunk + " "}))
                    self.response_queue_tts.task_done()
                    while True:
                        text_chunk = await self.response_queue_tts.get()
                        if text_chunk is None:
                            await websocket.send(json.dumps({"text": ""})) # Signal end of text
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


    def _cleanup(self):
        """Cleans up resources like audio streams."""
        print("\n>>> [INFO] Cleaning up resources...")
        if self.audio_stream and self.audio_stream.is_active():
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        self.pyaudio_instance.terminate()
        print(">>> [INFO] Application terminated.")

    async def run(self):
        """
        Starts the main application loop, initializing all tasks for the
        conversational AI.
        """
        try:
            async with self.gemini_client.aio.live.connect(
                model=self.GEMINI_MODEL, config=self.gemini_config
            ) as session, asyncio.TaskGroup() as tg:
                self.session = session
                self.out_queue_gemini = asyncio.Queue(maxsize=20)
                self.response_queue_tts = asyncio.Queue()
                self.audio_in_queue_player = asyncio.Queue()

                print(">>> [INFO] Starting all tasks...")
                
                # Core tasks
                tg.create_task(self._listen_microphone())
                tg.create_task(self._send_to_gemini())
                tg.create_task(self._receive_from_gemini())
                tg.create_task(self._run_tts())
                tg.create_task(self._play_audio_output())
                
                # Optional video task
                if self.video_mode == "camera":
                    tg.create_task(self._stream_camera_frames())
                elif self.video_mode == "screen":
                    tg.create_task(self._stream_screen_frames())

                # The text input task is the main loop driver
                send_text_task = tg.create_task(self._send_text_input())
                await send_text_task # This will run until user types 'q'
                
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            print("\n>>> [INFO] Exiting application as requested.")
        except Exception:
            traceback.print_exc()
        finally:
            self._cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run ADA, a real-time multimodal conversational AI."
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        default="camera",
        choices=["camera", "screen", "none"],
        help="Video source to stream to the AI."
    )
    args = parser.parse_args()

    ada_instance = ADA(video_mode=args.mode)
    
    try:
        asyncio.run(ada_instance.run())
    except KeyboardInterrupt:
        pass # The cleanup is handled within the run method's finally block
