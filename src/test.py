import sounddevice as sd
import asyncio
import numpy as np
import wave

async def record_audio_async(filename, duration=10, sample_rate=44100):
    print("Recording...")

    # Initialize an empty array to store audio data
    audio_data = []

    def callback(indata, frames, time, status):
        if status:
            print(f"Error in audio input: {status}")
        if indata.any():
            audio_data.append(indata.copy())

    # Open an audio input stream
    with sd.InputStream(
        callback=callback, 
        channels=2,
        samplerate=sample_rate,
        dtype=np.int16
        ):
        await asyncio.sleep(duration)

    print("Recording complete.")

    # Save the recorded audio to a WAV file
    if audio_data:
        audio_data = np.concatenate(audio_data, axis=0)
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

if __name__ == '__main__':
    loop = asyncio.get_event_loop_policy().get_event_loop()
    loop.run_until_complete(record_audio_async('output.wav', duration=10, sample_rate=48000))
    # asyncio.run(record_audio_async('output.wav', duration=10, sample_rate=48000))