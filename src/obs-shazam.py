import os
import asyncio
import shazamio
import inspect
import obspython as obs

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

# Initialize Shazam API
shazam = shazamio.Shazam()

stats_dict = {
    "audio_source": None,
}

song_metadata = None
recognition_task = None


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
async def recognize_audio(audio_data, source_name):
    global song_metadata
    while song_metadata is None:
        try:
            song_metadata = await shazam.identify_song(audio_data)
            await asyncio.sleep(1)  # Adjust the polling interval as needed
        except Exception as e:
            song_metadata = None
    print(song_metadata)
    # update_song_metadata(source_name)

# Define the audio capture callback
def audio_capture_callback(cd, data):
    source_name = obs.obs_data_get_string(cd, "source")
    audio_data = data.data.tobytes()

    global recognition_task
    if recognition_task is None or recognition_task.done():
        recognition_task = asyncio.ensure_future(recognize_audio(audio_data, source_name))

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
    cd = stats_dict["text_output"]
    # source_name = obs.obs_data_get_string(cd, "source")
    try:
        audio_source = obs.obs_get_source_by_name(stats_dict["audio_source"])
    except:
        print("exception occured")

    # audio_data = obs.audio_output_get_data()
    audio_data = obs.obs_source_add_audio_capture_callback(
        audio_source,
        audio_capture_callback,
        None
    )
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

        if song_metadata:
            metadata_text = f"Currently Playing: {song_metadata['title']} by {song_metadata['artists']}"
            source = obs.obs_get_source_by_name(source_name)
            if source is not None:
                settings = obs.obs_data_create()
                obs.obs_data_set_string(settings, "text", metadata_text)
                obs.obs_source_update(source, settings)
                obs.obs_data_release(settings)
                obs.obs_source_release(source)

                # Write song metadata to a .txt file
                with open(output_file, "w") as file:
                    file.write(metadata_text)
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

def button_pressed(props, prop):
    print("Button Pressed")
    obs.timer_add(update_song_metadata, 1000)

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
        "source",
        "Audio Source",
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

    b = obs.obs_properties_add_button(
        props, "button", "refresh pressed 0 times", button_pressed
    )

    # obs.obs_property_set_modified_callback(b, callback)
    # obs.obs_property_set_modified_callback(sources, callback)
    # obs.obs_property_set_modified_callback(text_output, callback)

    return props

# Define the script save function
def script_save(settings):
    pass

# Initialize the script
def script_load(settings):
    current_scene = obs.obs_frontend_get_current_scene()
    source = obs.obs_get_source_by_name("Audio Output Capture")
    scene = obs.obs_scene_from_source(current_scene)
    scene_item = obs.obs_scene_find_source(scene, "Audio Output Capture")
    print(source)
    print(scene_item)
    
def script_update(settings):
    audio_source = obs.obs_data_get_string(settings, "source")
    text_output = obs.obs_data_get_string(settings, "textout")
    stats_dict["audio_output"] = audio_source.split("|")[0]
    stats_dict["text_output"] = text_output.split("|")[0]


# Unload the script
def script_unload():
    obs.timer_remove(update_song_metadata)
    global recognition_task
    if recognition_task:
        recognition_task.cancel()

# Register the script
# obs.obs_register_script_description("Song Metadata Updater", script_description)