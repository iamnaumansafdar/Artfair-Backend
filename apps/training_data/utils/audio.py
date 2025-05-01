import os
import csv
from io import StringIO, BytesIO
import tempfile
from django.core.files import File
import torchaudio
from ..models import AudioSegment, MediaFile
import pandas as pd
from pydub import AudioSegment as PydubAudioSegment  # Renamed to avoid conflict
from torchaudio.transforms import Resample
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 16kHz is the default input rate for Whisper. Matching the input sample rate of the clips to what the model expects is important.
WHISPER_SAMPLE_RATE = 16000

'''
This homemade module takes the waveform of an audio file along with a row from the caption_data dataframe and outputs a clip starting/ending at the given timestamp.
You can use it over parallel processing threads for extra efficiency, since the audio conversion process can be slow. 
'''
def create_audio_clips(media_file_id): # Input the audio file (.wav) from the Full_Audio folder, and the caption file (.csv) from the Caption_CSVs folder.
    '''
    This method (timecode_to_milliseconds) will convert the string timecodes in the "Start" and "End" fields to millisecond values. Pydub and FFMPEG need the timestamps entered this way to trim the audio files.
    '''
    def timecode_to_milliseconds(timecode):
        still_timecode = ':' in str(timecode)
        
        if still_timecode:
            # Split the timecode into hours, minutes, seconds, and hundredths of a second
            hours, minutes, seconds = map(float, timecode.split(':'))
            
            # Convert the timecode to total milliseconds
            total_milliseconds = hours * 3600000 + minutes * 60000 + seconds * 1000
            return total_milliseconds
            
        else:
            return float(timecode) # Convert timecode to float incase it's a string

    media_file =  MediaFile.objects.get(id=media_file_id)
    
    if media_file.file_type == 'audio':
        audio_file = media_file.file
    else:    
        audio_file = media_file.processed_audio_file # .wav file 
    metadata_file = media_file.metadata_file # .csv file
    print(media_file, audio_file, metadata_file, 'Media_File_ID')

    metadata_file_content = metadata_file.read()
    csv_file_like_object = BytesIO(metadata_file_content) # Converts file content into a file-like object that can load into a pandas dataframe
    
    caption_data = pd.read_csv(csv_file_like_object)
    caption_data.columns = caption_data.columns.str.strip() # Removes leading spaces from header columns

    caption_data['start_time'] = caption_data['start_time'].apply(timecode_to_milliseconds)
    caption_data['end_time'] = caption_data['end_time'].apply(timecode_to_milliseconds)

    caption_data['index'] = range(1, len(caption_data) +1) # Adds an index field to each row. This helps in joining wav clip audio to specific captions later. Will be used in the "segment_audio" method.
  
    logger.info(f"Entries loaded successfully.")
    # Segment wav File by Caption Timecodes
    '''
    This method uses torchaudio to maniupulate audio files. It splits the work over multiple threads for speed. 
    There are other ways to do it, like pymad as a wrapper on top of mad. However, I had trouble getting those to work, and support seems to be old.

    Note: The following method expects input_audio to come in as an wav.
    '''
    audio_file.seek(0)
    audio_file_content = audio_file.read()
        
    logger.info("Loading audio for segmentation . . . ")
    
    # Save the audio content to a temporary file
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp_file:
        tmp_file.write(audio_file_content)
        tmp_file.flush()  # Flush internal buffer
        tmp_file.seek(0)  # Seek back to start of file (may not be needed)

        waveform, sample_rate = torchaudio.load(tmp_file.name)

    resampler = Resample(sample_rate, WHISPER_SAMPLE_RATE)
    resampled_waveform = resampler(waveform)
    waveform = resampled_waveform

    logger.info("Audio loaded. Ready to segment.")
    
    # Create a shell process that can divide the work to parallel jobs on different GPU threads
    def process_row(index, row):
        audio_path = create_segment(waveform, row, index, media_file)
        logger.info("Row %s: audio_path returned: %s", index, audio_path)
        caption_data.at[index, 'audio_path'] = audio_path
        caption_data.at[index, 'clip_number'] = index
        caption_data.at[index, 'full_path'] = f"{media_file.source_file_name}_Clip_{index}.wav"

    logger.info("Segmenting audio into caption-level clips")
    '''
    # Execute the clip segment creation process, parallelized across GPU or CPU threads.
    ## Adjust the number of workers based on your hardware's capability and the task's requirements
    with ThreadPoolExecutor(max_workers=12) as executor:
        executor.map(lambda x: process_row(*x), enumerate(caption_data.to_dict('records')))
    '''
    # Execute the clip segment creation process serially (no multithreading)
    caption_data.apply(lambda row: process_row(row.name, row), axis=1)

    # Update CSV Files to include audio file paths for later use as Training Data
    buffer = StringIO()
    caption_data.to_csv(buffer, index=False, quoting=csv.QUOTE_ALL)
    buffer.seek(0)

    # Convert to bytes for Django File object
    csv_bytes = buffer.getvalue().encode('utf-8')
    buffer_bytes = BytesIO(csv_bytes)
    buffer_bytes.seek(0) 

    # Save and overwrite the original file
    metadata_file.save(metadata_file.name, File(buffer_bytes))
    media_file.metadata_file = metadata_file
    media_file.save()

def create_segment(input_waveform, row, index, media_file): # The row parameter is a row from the pandas dataframe: caption_data.
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # Enable this line instead to experiment with using GPU for processing. Will also need to edit lines in the create_segment method
    # Move the input audio to GPU if available
    # input_waveform = input_waveform.to(device)

    # Convert start & end timestamps to frames based on sample rate. By this point, the timestamp should be in milliseconds (i.e., ':' separators not present)
    start_timestamp = int(row['start_time'])
    end_timestamp = int(row['end_time'])

    start_frame = int(start_timestamp / 1000 * WHISPER_SAMPLE_RATE)
    end_frame = int(end_timestamp / 1000 * WHISPER_SAMPLE_RATE)

    # Extract the specific audio segment
    # Assuming the input_audio is already loaded and in the correct format
    segment = input_waveform[:, start_frame:end_frame]

    # Optional: Additional audio processing can go here

    # Move audio back to CPU for saving files.
    # segment = segment.to("cpu") # Audio is transferred back to CPU here to save the clip files if it was being processed on GPU.
    buffer = BytesIO()
    torchaudio.save(buffer, segment, WHISPER_SAMPLE_RATE, format="wav")
    buffer.seek(0)

    file_name = f"{os.path.splitext(media_file.original_filename)[0]}_Clip_{index}.wav"
    audio_clip_file = AudioSegment.objects.create(
        owner=media_file.owner,
        file_type='audio',
        original_filename=file_name,
        source_audio=media_file,
    )
    # Save the .wav file locally 
    audio_clip_file.segment_file_local.save(file_name, buffer, save=True)
    # Rewind buffer
    buffer.seek(0)
    # # Upload to S3
    audio_clip_file.segment_file_remote.save(file_name, buffer, save=True)
    audio_clip_file.refresh_from_db()
    # return the full filepath that will be used in the AudioPath column
    return audio_clip_file.segment_file_local.path

def process_audio(media_file):
  """
  Converts an audio file to wav if necessary, and saves it to the processed_audio_file field.
  """
  _, ext = os.path.splitext(media_file.file.name)
  is_aac = ext.lower() == '.aac'
#   ext = ext.lower()

#   if ext in (".aac", ".mp3"):
  if is_aac:
      # Convert to .wav and save that as the processed_audio_file
      media_file.file.seek(0)
      audio_file_content = media_file.file.read()
      with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp_file:
          audio = PydubAudioSegment.from_file(BytesIO(audio_file_content), format="aac")
          audio.export(tmp_file.name, format="wav")
          new_filename = media_file.file_name + '.wav'
          with open(tmp_file.name, 'rb') as f:
              media_file.processed_audio_file.save(new_filename, File(f), save=True)
  elif ext.lower() == ".wav":
      # If the format is already .wav, no further processing necessary - just save the original audio
      # to the processed_audio_file.
      media_file.processed_audio_file = media_file.file
      media_file.save()
