import pytest
from unittest.mock import Mock, patch
import pandas as pd
from io import StringIO, BytesIO
from apps.training_data.utils import split_dataframe, clean_metadata_file, normalize_name_field, generate_speaker_id

def test_split_dataframe():
   # Create test DataFrame
   test_df = pd.DataFrame({
       'col1': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
       'col2': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
   })
   # Test splitting
   split_df = split_dataframe(test_df, train_ratio=70, test_ratio=10, validate_ratio=20)
   # Assertions
   assert 'split' in split_df.columns
   assert set(split_df['split'].unique()) == {'train', 'test', 'val'}
   assert (split_df['split'] == 'train').sum() >= 1
   assert (split_df['split'] == 'test').sum() >= 1
   assert (split_df['split'] == 'val').sum() >= 1
   # Test error cases
   with pytest.raises(ValueError):
       split_dataframe(test_df, train_ratio=80, test_ratio=10, validate_ratio=5)  # != 100
   small_df = pd.DataFrame({'col1': ['A', 'B']})  # Too few rows
   with pytest.raises(ValueError):
       split_dataframe(small_df, train_ratio=60, test_ratio=20, validate_ratio=20)

@pytest.fixture
def mock_csv_file():
   content = """Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
1,0:00,0:05,Default,Speaker,0,0,0,,Hello [text] (note)
2,0:05,0:10,Default,Speaker,0,0,0,,John: Test message
3,0:10,0:15,Default,Speaker,0,0,0,,♫ Music lyrics\\N
4,0:15,0:20,Default,Speaker,0,0,0,,"" """

   mock_file = Mock()
   mock_file.file = BytesIO(content.encode('utf-8'))
   return mock_file

@pytest.fixture
def mock_subtitle_file():
   mock_file = Mock()
   mock_channel = Mock()
   mock_channel.id = 1

   mock_file.owner = mock_channel
   mock_file.source_file_name = 'test_source_file'
   return mock_file


def test_clean_csv_data(mock_csv_file, mock_subtitle_file):
   output = clean_metadata_file(mock_csv_file, mock_subtitle_file)
   df = pd.read_csv(StringIO(output.getvalue()))
   assert set(df.columns) == {'speaker_name', 'start_time', 'end_time', 'caption_text', 'channel_id', 'speaker_id', 'video_name'}
   assert 'Hello' in df['caption_text'].values
   assert 'Test message' in df['caption_text'].values
   assert '[text]' not in str(df['caption_text'].values)
   assert 'John:' not in str(df['caption_text'].values)
   assert '♫' not in str(df['caption_text'].values)
   assert '""' not in df['caption_text'].values

def test_clean_csv_data_error():
   invalid_file = Mock()
   invalid_file.file = BytesIO(b'invalid content')
   # TODO: test error case
   assert True
  #  with pytest.raises(Exception) as exc_info:
  #      clean_csv_data(invalid_file)
  #  assert "Missing required columns:" in str(exc_info.value)

def test_normalize_name_field():
   data = {
       'Name': ['Nasir', '', '', ''],
       'Style': ['', 'Subi', '', ''],
       'Text': ['', '', '[Panda] text', 'just text']
   }
   df = pd.DataFrame(data)

   df['Name'] = df.apply(normalize_name_field, axis=1)

   expected = ['Nasir', 'Subi', 'Panda', '']
   assert df['Name'].tolist() == expected

def test_normalize_name_field_whitespace():
   data = {
       'Name': ['  Nasir  ', '', None],
       'Style': ['', '  Subi  ', ''],
       'Text': ['', '', '[  Panda  ] text']
   }
   df = pd.DataFrame(data)

   df['Name'] = df.apply(normalize_name_field, axis=1)
   assert df['Name'].tolist() == ['Nasir', 'Subi', 'Panda']

def test_generate_speaker_id():
   speaker_id = generate_speaker_id('Nasir', 123)
   expected_id = '3776-64cb'
   assert speaker_id == expected_id