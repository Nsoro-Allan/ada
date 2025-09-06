import asyncio
from RealtimeSTT import AudioToTextRecorder

async def stt(self):
        """ Listens via microphone and puts transcribed text onto input_queue. (Kept Original Logic) """
        if self.recorder is None:
            print("Audio recorder (RealtimeSTT) is not initialized.")
            return

        print("Starting Speech-to-Text engine...")
        while True:
            try:
                # Blocking call handled in a thread
                text = await asyncio.to_thread(self.recorder.text)
                if text: # Only process if text is not empty
                    print(f"STT Detected: {text}")
                    await self.clear_queues() # Clear queues before adding new input
                    await self.input_queue.put(text) # Put transcribed text onto the input queue
            except asyncio.CancelledError:
                 print("STT task cancelled.")
                 break
            except Exception as e:
                print(f"Error in STT loop: {e}")
                # Add a small delay to prevent high CPU usage on continuous errors
                await asyncio.sleep(0.5)