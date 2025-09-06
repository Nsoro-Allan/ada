"""
A real-time, multimodal conversational AI script using Google's Gemini Live API
for language understanding and ElevenLabs for text-to-speech synthesis.
This version includes detailed diagnostic logging for debugging audio issues.
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
    def __init__(self, video_mode=DEFAULT_MODE):
        self.video_mode = video_mode
        self.out_queue_gemini = None
        self.response_queue_tts = None
        self.audio_in_queue_player = None
        self.session = None
        self.audio_stream = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q": break
            for q in [self.response_queue_tts, self.audio_in_queue_player]:
                while not q.empty(): q.get_nowait()
            await self.session.send(input=text or ".", end_of_turn=True)

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret: return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_io.getvalue()).decode()}

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None: break
            await asyncio.sleep(1.0)
            await self.out_queue_gemini.put(frame)
        cap.release()

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
            if frame is None: break
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
        while True:
            turn = self.session.receive()
            async for response in turn:
                if response.text:
                    print(response.text, end="", flush=True)
                    # --- DIAGNOSTIC ---
                    print(f"\n>>> [DEBUG] Queueing for TTS: '{response.text}'")
                    await self.response_queue_tts.put(response.text)
            print()
            await self.response_queue_tts.put(None)

    async def tts(self):
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id=eleven_flash_v2_5&output_format=pcm_24000"
        while True:
            # This outer loop waits for a conversational turn to start.
            # It won't connect until it has text to send.
            text_chunk = await self.response_queue_tts.get()
            if text_chunk is None:  # Handles turns where Gemini doesn't speak.
                self.response_queue_tts.task_done()
                continue

            try:
                # --- DIAGNOSTIC ---
                print(">>> [DEBUG] Attempting to connect to ElevenLabs WebSocket...")
                async with websockets.connect(uri) as websocket:
                    print(">>> [SUCCESS] ElevenLabs WebSocket Connected.")
                    await websocket.send(json.dumps({
                        "text": " ",
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                        "xi_api_key": ELEVENLABS_API_KEY,
                    }))

                    async def listen():
                        """Listens until isFinal is received or the connection closes."""
                        while True:
                            try:
                                message = await websocket.recv()
                                data = json.loads(message)
                                if data.get("audio"):
                                    print(">>> [DEBUG] Audio received from ElevenLabs, queueing for playback.")
                                    await self.audio_in_queue_player.put(base64.b64decode(data["audio"]))
                                elif data.get("isFinal"):
                                    print(">>> [DEBUG] isFinal received. Listener task finishing.")
                                    break
                                else:
                                    print(f">>> [DEBUG] Received non-audio message: {data}")
                            except websockets.exceptions.ConnectionClosed:
                                print(">>> [ERROR] ElevenLabs connection closed during listen.")
                                break
                            except Exception as e:
                                print(f">>> [ERROR] Error in ElevenLabs listen loop: {e}")
                                break
                    
                    # Start the listener task.
                    listen_task = asyncio.create_task(listen())

                    # Send the first text chunk we already have.
                    print(f">>> [DEBUG] Sending to ElevenLabs: '{text_chunk}'")
                    await websocket.send(json.dumps({"text": text_chunk + " "}))
                    self.response_queue_tts.task_done()

                    # Send the rest of the text chunks for this turn.
                    while True:
                        text_chunk = await self.response_queue_tts.get()
                        if text_chunk is None:
                            await websocket.send(json.dumps({"text": ""})) # Signal end of text.
                            self.response_queue_tts.task_done()
                            break
                        print(f">>> [DEBUG] Sending to ElevenLabs: '{text_chunk}'")
                        await websocket.send(json.dumps({"text": text_chunk + " "}))
                        self.response_queue_tts.task_done()
                    
                    # Wait for the listener to finish receiving all audio.
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
            print(">>> [INFO] Audio output stream is open.")
        except Exception as e:
            print(f">>> [FATAL ERROR] Could not open PyAudio stream: {e}")
            return

        while True:
            try:
                bytestream = await self.audio_in_queue_player.get()
                if bytestream:
                    # --- DIAGNOSTIC ---
                    print(f">>> [DEBUG] Playing audio chunk of size: {len(bytestream)} bytes")
                    await asyncio.to_thread(stream.write, bytestream)
                self.audio_in_queue_player.task_done()
            except Exception as e:
                print(f">>> [ERROR] Error in audio playback loop: {e}")

    async def run(self):
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session, asyncio.TaskGroup() as tg:
                self.session = session
                self.out_queue_gemini = asyncio.Queue(maxsize=20)
                self.response_queue_tts = asyncio.Queue()
                self.audio_in_queue_player = asyncio.Queue()
                print(">>> [INFO] Starting all tasks...")
                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.listen_audio())
                if self.video_mode == "camera": tg.create_task(self.get_frames())
                elif self.video_mode == "screen": tg.create_task(self.get_screen())
                tg.create_task(self.send_realtime())
                tg.create_task(self.receive_text())
                tg.create_task(self.tts())
                tg.create_task(self.play_audio())
                await send_text_task
                raise asyncio.CancelledError("User requested exit")
        except asyncio.CancelledError:
            print("\n>>> [INFO] Exiting application.")
        except Exception:
            traceback.print_exc()
        finally:
            if self.audio_stream and self.audio_stream.is_active():
                self.audio_stream.stop_stream()
                self.audio_stream.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", type=str, default=DEFAULT_MODE,
        help="pixels to stream from", choices=["camera", "screen", "none"]
    )
    args = parser.parse_args()
    main_loop = AudioLoop(video_mode=args.mode)
    try:
        asyncio.run(main_loop.run())
    except KeyboardInterrupt:
        pass
    finally:
        pya.terminate()
        print(">>> [INFO] Application terminated.")

