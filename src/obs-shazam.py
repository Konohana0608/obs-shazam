import os
import time
import asyncio
import shazamio
import numpy as np
import wave
import inspect
import threading
import obspython as obs
import sounddevice as sd
from scipy.io.wavfile import write

from platform import system
from os import makedirs, path

sys= system()
darwin = (sys == "Darwin")
cwd = path.dirname(path.realpath(__file__))
file_name = path.basename(__file__).removesuffix(".py")
settings_dir = "settings"
settings_file_name = f"{file_name}.json"

# Define the path to the output .txt file
output_file = "song_metadata.txt"

running = False
interval_seconds = 10

# Initialize Shazam API
shazam = shazamio.Shazam()

song_metadata: str = None
song_coverart: str = None
recognition_task = None

stats_dict = {}


# -------------------------------------------------------------------
class WindowCaptureSources:
    def __init__(self, sources):
        self.sources = sources


class MonitorCaptureSources:
    def __init__(self, windows, macos, linux):
        self.windows = windows
        self.macos = macos
        self.linux = linux

    def all_sources(self):
        return self.windows | self.macos | self.linux


class AppleSiliconCaptureSources:
    def __init__(self, sources):
        self.sources = sources


class CaptureSources:
    def __init__(self, window, monitor, applesilicon):
        self.window = window
        self.monitor = monitor
        self.applesilicon = applesilicon

    def mac_sources(self):
        return self.monitor.all_sources() | self.applesilicon.sources

    def all_sources(self):
        return self.window.sources | self.mac_sources()


# Matches against values returned by obs.obs_source_get_id(source).
# See populate_list_property_with_source_names() below.
SOURCES = CaptureSources(
    window=WindowCaptureSources({'ffmpeg_source', 'text_gpiplus_v2', 'wasapi_output_capture'}),
    monitor=MonitorCaptureSources(
        windows={'monitor_capture'},
        macos={'display_capture'},
        linux={'monitor_capture', 'xshm_input',
               'pipewire-desktop-capture-source'}
    ),
    applesilicon=AppleSiliconCaptureSources({'screen_capture','screen_capture'})
)


# -------------------------------------------------------------------
async def recognize_audio(audio_data):
    global song_metadata
    global song_coverart
    temp_song_metadata = None
    try:
        temp_song_metadata = await shazam.recognize_song(audio_data)
        if temp_song_metadata:
            print(temp_song_metadata)
            song_metadata = f"Song: {temp_song_metadata['track']['title']} by {temp_song_metadata['track']['subtitle']}"
            song_coverart = temp_song_metadata['track']['images']['coverart']
    except Exception as e:
        print(f"Error: {e}")

async def record_audio_async(filename, duration=10, sample_rate=44100):
    
    try:
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
    except Exception as e:
        print(e)


# Define the audio capture callback
"""
def audio_capture_callback(source, data):
    print("in audio capture callback")
    # source_name = obs.obs_data_get_string(cd, "source")
    print(samples)
    print(timestamp)
    print(type(data))
    print(len(data))
    assert False
    audio_data = data.data.tobytes()

    global recognition_task
    if recognition_task is None or recognition_task.done():
        recognition_task = asyncio.ensure_future(recognize_audio(audio_data, source_name))
"""
"""
def audio_capture_callback(source, data):
    # Process the audio data here
    print("in audio capture callback")
    print(data)
    try:
        song_metadata = shazam.recognize_song(data)
    except Exception as e:
        song_metadata = None

    print(song_metadata)
"""

# Define the callback to update song metadata
def update_song_metadata():
    global song_metadata
    global song_coverart
    global running

    while running:
        print(song_metadata)
        cd = stats_dict["text_output"]
        browser_s = stats_dict["browser_source"]

        """
        print(audio_source_name)
        print(type(audio_source_name))
        audio_source = obs.obs_get_source_by_name(str(audio_source_name))
        print(audio_source)
        """
        # source_name = obs.obs_data_get_string(cd, "source")
        try:
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(
                record_audio_async(
                    'F:\Melanie\OBS\python_code\obs-shazam\output.wav',
                    duration=10,
                    sample_rate=48000
                )
            )

            loop.run_until_complete(
                recognize_audio(
                    'F:\Melanie\OBS\python_code\obs-shazam\output.wav'
                )
            )

        except Exception as e:
            print("exception occured")
            print(e)

        if song_metadata:
            metadata_text = f"  {song_metadata}"
            source = obs.obs_get_source_by_name(cd)
            if source is not None:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "text", metadata_text)
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
                obs.obs_source_release(source)

        
        if song_coverart:
            source = obs.obs_get_source_by_name(browser_s)
            if source is not None:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "url", song_coverart)
                obs.obs_data_set_int(settings, "width", 400)
                obs.obs_data_set_int(settings, "height", 400)
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
                obs.obs_source_release(source)

        time.sleep(interval_seconds)

        """
        audio_data = obs.audio_output_get_data()
        audio_data = obs.obs_source_add_audio_capture_callback(
            source=audio_source,
            callback=audio_capture_callback,
            param=None,
        )
        """
        # obs_source_remove_audio_capture_callback
        """
    # Check if audio data is available
    if audio_data is not None:
        # Convert audio data to bytes
        audio_bytes = audio_data.data.tobytes()
        
        # Analyze the audio using Shazam
        try:
            song_metadata = shazam.identify_song(audio_bytes)
        except Exception as e:
            song_metadata = None
    """

# -------------------------------------------------------------------
def populate_list_property_with_source_names(list_property):
    """
    Updates Zoom Source's available options.

    Checks a source against SOURCES to determine availability.
    """
    global darwin
    global new_source

    print("Updating Source List")
    # zoom.update_sources()
    sources = obs.obs_enum_sources()
    for s in sources:
        print("___________________________________")
        name = obs.obs_source_get_name(s)
        print(name)
        stype = obs.obs_source_get_id(s)
        print(stype)

    if sources is not None:
        obs.obs_property_list_clear(list_property)
        obs.obs_property_list_add_string(list_property, "", "")
        for source in sources:
            source_type = obs.obs_source_get_id(source)
            if darwin and source_type not in SOURCES.all_sources():
                print(f"{obs.obs_source_get_name(source)} | {source_type} | {source}")
            # Print this value if a source isn't showing in the UI as expected
            # and add it to SOURCES above for either window or monitor capture.
            filter = SOURCES.all_sources() if not darwin else SOURCES.mac_sources()
            # if source_type in filter:
            name_val = name = obs.obs_source_get_name(source)
            name = name + "||" + source_type
            obs.obs_property_list_add_string(list_property, name_val, name)
        # zoom.source_load = True
    obs.source_list_release(sources)
    new_source = True
    print(f"New source: {str(new_source)}")


# Define the script description
def script_description():
    return "Analyze sound from a specified source and write song metadata to a .txt file."


def start_button_pressed(props, prop):
    print("Button Pressed")
    # obs.timer_add(update_song_metadata, 1000)
    global running
    if not running:
        running = True
        t = threading.Thread(target=update_song_metadata)
        t.daemon = True
        t.start()


def stop_button_pressed(props, prop):
    global running
    running = False


def callback(props, prop, *args):
    print("Executing Callback")
    prop_name = obs.obs_property_name(prop)
    print(prop_name)
    if prop_name == "source":
        p = obs.obs_properties_get(props, "source")
        stats_dict["audio_source"] = p
    elif prop_name == "textout":
        p = obs.obs_properties_get(props, "textout")
        stats_dict["text_output"] = p
  

# Define the script properties
def script_properties():
    props = obs.obs_properties_create()
    sources = obs.obs_properties_add_list(
        props,
        "browser_source",
        "Browser Source",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    populate_list_property_with_source_names(sources)

    text_output = obs.obs_properties_add_list(
        props,
        "textout",
        "Text Output",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    populate_list_property_with_source_names(text_output)

    obs.obs_properties_add_int(
        props=props,
        name="interval_seconds",
        description="Interval (seconds)",
        min=1,
        max=86400,
        step=1
    )

    start_button = obs.obs_properties_add_button(
        props, "button", "Start", start_button_pressed
    )

    stop_button = obs.obs_properties_add_button(
        props, "button", "Stop", stop_button_pressed
    )

    # obs.obs_property_set_modified_callback(b, callback)
    # obs.obs_property_set_modified_callback(sources, callback)
    # obs.obs_property_set_modified_callback(text_output, callback)

    return props


# Define the script save function
def script_save(settings):
    obs.obs_data_set_int(settings, "interval_seconds", interval_seconds)


# Initialize the script
def script_load(settings):
    global interval_seconds

    current_scene = obs.obs_frontend_get_current_scene()
    source = obs.obs_get_source_by_name("Audio Output Capture")
    scene = obs.obs_scene_from_source(current_scene)
    scene_item = obs.obs_scene_find_source(scene, "Audio Output Capture")
    print(source)
    print(scene_item)

    interval_seconds = obs.obs_data_get_int(settings, "interval_seconds")


def script_update(settings):
    global interval_seconds
    
    interval_seconds = obs.obs_data_get_int(settings, "interval_seconds")
    browser_source = obs.obs_data_get_string(settings, "browser_source")
    text_output = obs.obs_data_get_string(settings, "textout")
    stats_dict["browser_source"] = browser_source.split("|")[0]
    stats_dict["text_output"] = text_output.split("|")[0]


# Unload the script
def script_unload():
    obs.timer_remove(update_song_metadata)
    global recognition_task
    if recognition_task:
        recognition_task.cancel()


# Register the script
# obs.obs_register_script_description("Song Metadata Updater", script_description)