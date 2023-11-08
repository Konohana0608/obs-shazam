import pyaudio
import wave
import asyncio

sample_rate = 48000  # Sample rate
duration = 10  # Duration of recording

print("Recording...")

# Initialize an empty array to store audio data
audio_data = []

def callback(indata, frames, time, status):
    if status:
        print(f"Error in audio input: {status}")
    if indata.any():
        audio_data.append(indata.copy())

# Open an audio input stream
with sd.InputStream(callback=callback, channels=2, samplerate=sample_rate):
    await asyncio.sleep(duration)

print("Recording complete.")
print(audio_data)

# Save the recorded audio to a WAV file
if audio_data:
    print('in if statement')
    audio_data = np.concatenate(audio_data, axis=0)
    print(audio_data)
    with wave.open("output.wav", 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

sound  = True
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000
RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "output.wav"

p = pyaudio.PyAudio()

for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i))

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index = 0,
                frames_per_buffer=CHUNK)

print("recording")

frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("done recording")

stream.stop_stream()
stream.close()
p.terminate()
wf = wave.open(WAVE_OUTPUT_FILENAME, "wb")
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()