
import os
import csv
import re
import hashlib
from io import StringIO, BytesIO
from ..models import MediaFile
import pandas as pd
from django.core.files import File

def generate_speaker_id(speaker_name, channel_id):
    """
    Randomly and deterministically assign a speaker ID based on speaker name and channel.
    """
    name_and_chanel = speaker_name + str(channel_id)
    name_and_chanel = name_and_chanel.lower()
    hash_obj = hashlib.sha256(name_and_chanel.encode())
    hash_hex = hash_obj.hexdigest()

    return f"{hash_hex[:4]}-{hash_hex[4:8]}"

def convert_subtitles_to_metadata(subtitle_file_id):
    """
    Convert subtitle file to Metadata CSV file and saves that metadata file
    to the original file associated with the given subtitle file.
    """
    subtitle_file = MediaFile.objects.get(id=subtitle_file_id)

    try:
        metadata_content = get_metadata_content(subtitle_file_id)
        metadata_filename = f"{subtitle_file.source_file_name}.csv"
        metadata_file = File(BytesIO(metadata_content.getvalue().encode()), name=metadata_filename)

        cleaned_metadata_output = clean_metadata_file(metadata_file, subtitle_file)
        cleaned_metadata_file = File(BytesIO(cleaned_metadata_output.getvalue().encode()), name=metadata_filename)

        # Note: the metadata_file setter saves the metadata_file to the subtitle's source file.
        subtitle_file.metadata_file = cleaned_metadata_file
        subtitle_file.save()

    except Exception as e:
        raise Exception(f"Error converting subtitles to CSV: {str(e)}")


def get_metadata_content(subtitle_file_id):
    # Read subtitle file
    subtitle_file = MediaFile.objects.get(id=subtitle_file_id)
    subtitle_file.file.seek(0)
    content = subtitle_file.file.read().decode('utf-8')

    # Find [Events] section
    events_start = content.find('[Events]')
    if events_start == -1:
        raise ValueError("Invalid subtitle file format: [Events] section not found")

    # Extract events data
    events_data = content[events_start:].split('\n')

    # Parse header and data
    header = None
    rows = []
    for line in events_data:
        if line.startswith('Format:'):
            header = [col.strip() for col in line.replace('Format:', '').split(',')]
        elif line.startswith('Dialogue:'):
            row = line.replace('Dialogue:', '').split(',', len(header) - 1)
            rows.append(row)

    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)

    return output


'''
  The speaker name can either be in the Name column, Style column,
  or at the beginning of the caption text in brackets.
'''
def normalize_name_field(row):
    if pd.notna(row['Name']) and row['Name'].strip():
        return row['Name'].strip()

    if (pd.notna(row['Style']) and
        row['Style'].lower() != 'default' and
        row['Style'].strip()):
        return row['Style'].strip()

    if pd.notna(row['Text']):
        if match := re.match(r'\[([^\]]+)\]', row['Text']):
            return match.group(1).strip()

    return ''

def assign_speaker_id(speaker_name, channel_id):
    if not speaker_name:
        return ''
    return generate_speaker_id(speaker_name, channel_id)

def clean_metadata_file(metadata_file, subtitle_file):
    """Clean up CSV Metadata"""
    try:
        # Read CSV content
        metadata_file.file.seek(0)  # Reset file pointer to start
        content = metadata_file.file.read().decode('utf-8')

        # Parse CSV with specific headers
        expected_headers = ['Layer', 'Start', 'End', 'Style', 'Name', 'MarginL', 'MarginR', 'MarginV', 'Effect', 'Text']
        df = pd.read_csv(
            StringIO(content),
            encoding='utf-8',
            names=expected_headers if 'Layer' not in content.split('\n')[0] else None
        )

        # Clean text field
        if 'Text' in df.columns:
            df['Text'] = df['Text'].fillna('')  # Replace NaN with empty string
            df['Text'] = df['Text'].astype(str)  # Ensure text is string type
            df['Text'] = df['Text'].str.replace(r'\[.*?\]|\(.*?\)', '', regex=True)  # Remove brackets/parentheses
            df['Text'] = df['Text'].str.replace(r'^"?(\w+: )', '', regex=True)  # Remove speaker indicators
            df['Text'] = df['Text'].str.replace(r'\N', '')  # Remove line breaks
            df['Text'] = df['Text'].str.replace(r'♫', '')  # Remove music notes
            df['Text'] = df['Text'].str.strip()  # Remove leading/trailing whitespace

            # Remove empty rows
            df = df.dropna(subset=['Text'])
            df = df[df['Text'].str.strip() != '']
            df = df[~df['Text'].isin(['""', '" "', '"'])]

        df['speaker_name'] = df.apply(normalize_name_field, axis=1)
        df['speaker_id'] = df.apply(lambda row: assign_speaker_id(row['speaker_name'], subtitle_file.owner.id), axis=1)
        df['channel_id'] = subtitle_file.owner.id
        df['video_name'] = subtitle_file.source_file_name

        df = df.rename(columns={
          'Start': 'start_time',
          'End': 'end_time',
          'Text': 'caption_text',
        })

        columns_to_keep = ['speaker_name', 'start_time', 'end_time', 'caption_text', 'channel_id', 'video_name', 'speaker_id']
        df = df[columns_to_keep]
        
        # Iterate over unique speaker rows to populate the Speaker model:
        from apps.training_data.models import Speaker
        # Get the source file from the subtitle file. It could be the video/audio file associated with the caption.
        source_media = subtitle_file._source_file or subtitle_file
        unique_speakers = df[['speaker_name', 'speaker_id', 'channel_id']].drop_duplicates()
        for _, row in unique_speakers.iterrows():
            speaker, created = Speaker.objects.get_or_create(
                speaker_id=row['speaker_id'],
                defaults={
                    'name': row['speaker_name'],
                    'owner_id': row['channel_id'],
                }
            )
            # Add the current source media file to the many-to-many relationship.
            speaker.media_files.add(source_media)
            # Optionally: If you want to update extra fields later, do so here.

       # Save cleaned data
        output = StringIO()
        df.to_csv(output, index=False)
        return output

    except Exception as e:
        import traceback
        raise Exception(f"Error cleaning CSV Metadata: {str(e)}\n{traceback.format_exc()}")
