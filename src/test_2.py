import shazamio
import pyaudio
import asyncio
import numpy as np
import speech_recognition
import sounddevice as sd
import numpy as np

from scipy.io.wavfile import write
from time import sleep



# Initialize Shazam API
shazam = shazamio.Shazam()

# Audio settings
audio_format = pyaudio.paInt16
sample_rate = 44100
chunk_size = 1024

# Create a PyAudio object
audio = pyaudio.PyAudio()

# Start audio stream
stream = audio.open(
    format=audio_format,
    channels=1,
    rate=sample_rate,
    input=True,
    frames_per_buffer=chunk_size
)
async def main():
    try:

        # Analyze audio data using Shazam
        song_metadata = await shazam.recognize_song("output.wav")

        if song_metadata:
            
            print(f"Song: {song_metadata['track']['title']} by {song_metadata['track']['subtitle']}")

    except Exception as e:
        print(f"Error: {e}")
loop = asyncio.get_event_loop_policy().get_event_loop()
loop.run_until_complete(main())
# Close the audio stream when done
stream.stop_stream()
stream.close()
audio.terminate()