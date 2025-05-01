import numpy as np
import pandas as pd
from datasets import Dataset, DatasetDict, Audio
from huggingface_hub import login
from .audio import WHISPER_SAMPLE_RATE
from django.conf import settings
import logging
from apps.training_data.models import MediaFile
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Hugging Face Split names
TRAIN = "train"
TEST = "test"
VAL = "val"

def split_dataframe(df, train_ratio, test_ratio, validate_ratio):
    # Ensure all ratios are numbers
    train_ratio = float(train_ratio)
    test_ratio = float(test_ratio)
    validate_ratio = float(validate_ratio)
    if train_ratio + test_ratio + validate_ratio != 100:
        raise ValueError("Split ratios must sum to 100")

    n = len(df)
    # Ensure at least one row per split
    min_rows = 3
    if n < min_rows:
        raise ValueError(f"Need at least {min_rows} rows to split into train/test/val")

    # First assign one row to each split
    # df['split'] = None #  Initialize df['split'] = None, Pandas treats it as a float64 column.
    df['split'] = pd.Series(dtype="object")
    indices = np.random.choice(df.index, size=3, replace=False)
    df.loc[indices[0], 'split'] = TRAIN
    df.loc[indices[1], 'split'] = TEST
    df.loc[indices[2], 'split'] = VAL

    # Distribute remaining rows according to ratios
    remaining_indices = df[df['split'].isna()].index
    remaining_ratios = [train_ratio / 100, test_ratio / 100, validate_ratio / 100]
    remaining_ratios = [r / sum(remaining_ratios) for r in remaining_ratios]

    df.loc[remaining_indices, 'split'] = np.random.choice(
        [TRAIN, TEST, VAL],
        size=len(remaining_indices),
        p=remaining_ratios
    )

    return df

# def upload_to_huggingface(dataset, client_id):
#     """Upload dataset to HuggingFace"""
#     try:
#         # Fix missing values explicitly Added 1 line 67 - 70
#         for col in ['start_time', 'end_time', 'caption_text', 'speaker_name']:
#             if col in dataset.columns:
#                 dataset[col] = dataset[col].fillna('')
#         # Fix string columns by filling missing values with empty strings, added 3 line 72-75
#         string_columns = ['caption_text', 'speaker_name', 'video_name', 'speaker_id', 'full_path']
#         for col in string_columns:
#             if col in dataset.columns:
#                 dataset[col] = dataset[col].fillna('')
#         # Convert to HuggingFace dataset format
#         splits = {}
#         for split in [TRAIN, TEST, VAL]:
#             split_data = dataset[dataset['split'] == split]
#             # If a split is empty, skip it or handle it explicitly Added 2 line 81-83
#             if split_data.empty:
#                 continue

#             splits[split] = Dataset.from_pandas(split_data, preserve_index=False)

#         # Create dataset dictionary
#         hf_dataset = DatasetDict(splits)

#         # Add audio feature
#         for split in hf_dataset.keys():
#             hf_dataset[split] = hf_dataset[split].cast_column("audio_path", Audio(sampling_rate=WHISPER_SAMPLE_RATE))
#         # Upload to HuggingFace
#         login(token=settings.HF_TOKEN)  # This will use HF_TOKEN environment variable

#         # TODO: channel naming is still TBD. email's aren't valid because repo names can't contain 
#         # certain characters present in emails.
        
#         repo_id = f"{client_id}-Voice-Data"               # final repo name
#         logger.info("Pushing dataset to the Hub → %s", repo_id)

#         url = hf_dataset.push_to_hub(repo_id, private=True)
#         logger.info("✅  Upload finished. Dataset available at %s", url)
#         return url

#     except Exception as e:
#         raise Exception(f"Error uploading to HuggingFace: {str(e)}")


# --------------------------------------------------------------------------- #
# 2.  upload_to_huggingface  – now loads the CSV internally                  #
# --------------------------------------------------------------------------- #
def upload_to_huggingface(media_file_id):
    """
    • Read the single CSV stored in MediaFile.metadata_file  
    • Create train / val / test splits (if the column already exists we keep it)  
    • Push to HF Hub
    """
    try:
        # ------------------------------------------------------------------ #
        # Load CSV from S3 (or local disk)                                   #
        # ------------------------------------------------------------------ #
        media_file = MediaFile.objects.get(id=media_file_id)
        dataset = pd.read_csv(media_file.metadata_file, encoding="utf-8-sig")

        # Ensure a split column exists; create one if it doesn't
        if "split" not in dataset.columns:
            dataset["split"] = dataset.index.map(
                lambda i: TRAIN if i % 20 < 14           # ≈70 %
                else VAL  if i % 20 < 17                 # ≈15 %
                else TEST                                # ≈15 %
            )

        # ------------------------------------------------------------------ #
        # Clean NaNs                                                         #
        # ------------------------------------------------------------------ #
        for col in ['start_time', 'end_time', 'caption_text', 'speaker_name']:
            if col in dataset.columns:
                dataset[col] = dataset[col].fillna('')
        string_columns = ['caption_text', 'speaker_name',
                          'video_name', 'speaker_id', 'full_path']
        for col in string_columns:
            if col in dataset.columns:
                dataset[col] = dataset[col].fillna('')

        # ------------------------------------------------------------------ #
        # Build HF DatasetDict                                               #
        # ------------------------------------------------------------------ #
        splits = {}
        for split in [TRAIN, TEST, VAL]:
            split_data = dataset[dataset['split'] == split]
            if split_data.empty:                      # skip missing split
                continue
            splits[split] = Dataset.from_pandas(split_data, preserve_index=False)

        hf_dataset = DatasetDict(splits)

        # Cast audio column (if present)
        if "audio_path" in hf_dataset["train"].column_names:
            for split in hf_dataset.keys():
                hf_dataset[split] = hf_dataset[split].cast_column(
                    "audio_path", Audio(sampling_rate=WHISPER_SAMPLE_RATE)
                )

        # ------------------------------------------------------------------ #
        # Push to the Hub                                                    #
        # ------------------------------------------------------------------ #
        login(token=settings.HF_TOKEN)
        channel_id = media_file.channel_id
        repo_id = f"{channel_id}-Voice-Data"
        logger.info("Pushing dataset to the Hub → %s", repo_id)
        
        # commit message that contains client‑ID, media‑ID and file name
        commit_msg   = (
            f"Uploading Dataset for MediaFile {media_file_id},  "
            f"Client {channel_id}.  Original File {media_file.original_filename}"
        )

        url = hf_dataset.push_to_hub(repo_id, private=True, commit_message=commit_msg,)
        logger.info("✅  Upload finished. Dataset available at %s", url)
        return url

    except Exception as e:
        raise Exception(f"Error uploading to HuggingFace: {str(e)}")